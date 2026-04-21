# Architecture Patterns

**Domain:** Cache eviction, pattern caching, and state management integration for a layered Rust workspace
**Researched:** 2026-04-04
**Confidence:** HIGH (based on direct source inspection of all affected crates)

## Recommended Architecture

The changes span five concerns across four architectural layers. The critical insight is that each concern touches a different layer boundary, but they share a common theme: replacing unbounded or per-call constructs with bounded, session-aware alternatives. The existing codebase already demonstrates the correct patterns in adjacent modules -- the work is largely about applying established patterns to the remaining outliers.

### Layer Map (bottom-up, showing what changes where)

```
Foundation
  classic-shared-core           -- no changes needed

Business Logic (-core crates)
  classic-yaml-core             -- YAML_CACHE: DashMap -> bounded LRU
  classic-settings-core         -- SETTINGS_CACHE: DashMap -> bounded LRU
  classic-file-io-core          -- HASH_CACHE: DashMap -> bounded LRU
  classic-scanlog-core
    mod_detector.rs             -- AhoCorasick integration for detect_mods_important
    fcx_handler.rs              -- reset_global_state contention fix
    orchestrator.rs             -- session-boundary FCX reset contract

C++ Bridge
  classic-cpp-bridge/scanner.rs -- Lazy<LogParser>, FCX reset function

Binding Surfaces
  classic-node/scanlog.rs       -- FCX reset + ConfigIssue list exposure + Lazy<LogParser>
  (classic-cpp-bridge CXX FFI)  -- new extern "Rust" entry for fcx_reset_global_state
```

## Component Boundaries

| Component | Responsibility | Communicates With | Change Scope |
|-----------|---------------|-------------------|--------------|
| `classic-yaml-core` | YAML file parsing + caching | All config-loading crates downstream | Internal cache replacement; public API unchanged |
| `classic-settings-core` | Settings YAML caching with caller-keyed entries | Config-core, bridge yaml module | Internal cache replacement; public API unchanged |
| `classic-file-io-core` | File hashing with global cache | Bridge files module, scangame | Internal cache replacement; public API unchanged |
| `classic-scanlog-core::mod_detector` | Mod detection via pattern matching | Orchestrator (caller), config-core (data) | Internal pattern compilation strategy; function signatures unchanged |
| `classic-scanlog-core::fcx_handler` | Process-wide FCX state singleton | Orchestrator, bridge scanner, node scanlog | Fix `reset_global_state`; no signature change |
| `classic-cpp-bridge::scanner` | CXX FFI for crash log analysis | C++ CLI/GUI frontends | Add `Lazy<LogParser>`, add `fcx_reset_global_state` FFI fn |
| `classic-node::scanlog` | NAPI-RS binding for scanlog | Node/Bun consumers | Add `resetFcxGlobalState`, `getFcxConfigIssues` exports, `Lazy<LogParser>` |

## Data Flow

### 1. Cache Eviction Flow (YAML_CACHE, SETTINGS_CACHE, HASH_CACHE)

**Current flow:**
```
Caller -> cache.get(key) -> DashMap lookup (unbounded)
  miss -> parse/compute -> cache.insert(key, value) -> DashMap grows forever
```

**Target flow:**
```
Caller -> cache.get(key) -> quick_cache::Cache lookup (bounded, concurrent)
  miss -> parse/compute -> cache.insert(key, value) -> auto-evicts LRU on capacity
```

**Why `quick_cache::sync::Cache` instead of `RwLock<LruCache>`:** The codebase already uses `quick_cache` in `FileIOCore.read_cache` (classic-file-io-core/core.rs:99). It provides lock-free concurrent reads with built-in LRU eviction, matching the existing DashMap concurrent access pattern. Using `RwLock<LruCache>` would serialize all reads -- a regression for the YAML and settings caches that serve concurrent scan workers.

**Boundary contract:** The public APIs (`load_yaml_file`, `get_cached`, `hash_file`, `clear_cache`, `cache_stats`) do NOT change. The cache is an internal implementation detail. Callers see identical behavior except that very old entries may be evicted under memory pressure.

**Data flow direction:**
- `YAML_CACHE`: Written by `YamlOperations::load_yaml_file()`, read by all config-loading paths, cleared by `clear_global_yaml_cache()`
- `SETTINGS_CACHE`: Written by `load_settings_sync/async`, read by `get_cached()`, cleared by `clear_cache()`
- `HASH_CACHE`: Written by `FileHasher::hash_file()`, read by same, cleared by `FileHasher::clear_cache()`

### 2. AhoCorasick Pattern Caching Flow (mod_detector)

**Current flow (detect_mods_important):**
```
for each entry in CoreModEntry list:
    Regex::new(escape(entry.detect))  -- compiled per entry per call
    pattern.is_match(all_text)
```

**Target flow:**
```
hash = xxhash(entry list contents)
if cached_automaton[hash] exists:
    automaton = cached_automaton[hash]
else:
    patterns = entries.map(|e| e.detect.to_lowercase())
    automaton = AhoCorasick::builder()
        .ascii_case_insensitive(true)
        .build(patterns)
    cached_automaton[hash] = automaton

for match in automaton.find_iter(all_text):
    entry = entries[match.pattern_id]  -- AhoCorasick preserves pattern index
    // apply gpu/exclusion logic per matched entry
```

**Why AhoCorasick over combined regex alternation:** `detect_mods_important` has per-entry semantics (gpu checks, exclusions) that require knowing WHICH pattern matched. AhoCorasick's `Match` includes `pattern()` -- the index of the matched pattern. This is exactly how `record_scanner.rs` and `patterns.rs` already work in this crate. Regex alternation loses pattern identity without named captures, which adds complexity.

**Why entries need a two-pass approach:** AhoCorasick searches for ALL matches. But `detect_mods_important` has per-entry exclusion checks (`is_excluded`) that must run BEFORE reporting a match. The recommended approach:
1. Build the AhoCorasick automaton from all entry detect strings
2. Run `find_iter` on `all_text` to get all matches
3. For each match, look up the source entry by `match.pattern().as_usize()` index
4. Apply `is_excluded` and gpu logic on the source entry
5. Skip excluded entries, emit output for non-excluded matches

**Boundary contract:** The function signature of `detect_mods_important` does not change. The `entries: &[CoreModEntry]` parameter is the cache key source -- hash the serialized detect strings.

**Data flow direction:**
- `OrchestratorCore` calls `detect_mods_important` with `config.mods_important` entries
- Entries come from `AnalysisConfig` which is built from YAML at scan session start
- Within a session, entries are stable -- the cache key does not change between logs in a batch
- Cache should be module-level `Lazy<Mutex<LruCache<u64, Arc<AhoCorasick>>>>` with small capacity (8-16 entries, since there is typically one mod list per session)

### 3. Bridge-Level Parser Caching Flow

**Current flow:**
```
detect_crash_pattern(content) {
    let parser = LogParser::new(None).unwrap();  // allocates + compiles patterns EVERY call
    parser.parse_crash_header(lines)
}
```

**Target flow:**
```
static BRIDGE_PARSER: Lazy<LogParser> = Lazy::new(|| LogParser::new(None).unwrap());

detect_crash_pattern(content) {
    BRIDGE_PARSER.parse_crash_header(lines)  // reuses compiled patterns
}
```

**Why `Lazy<LogParser>` (not `Lazy<Mutex<LogParser>>`):** `LogParser` uses internal `Arc<RwLock<LruCache>>` for its segment and pattern caches, plus `Arc<DashMap>` for custom patterns. The `parse_crash_header` method takes `&self` (shared reference). It is already designed for concurrent use. No external mutex is needed.

**Boundary contract:** The CXX FFI signature `fn detect_crash_pattern(content: &str) -> String` does not change. Same for `detect_vr_log`. The `Lazy` static is module-private.

**Note about Node bindings:** The same pattern applies to `parse_log_segments`, `extract_form_ids`, `extract_plugin_list`, and `detect_crash_pattern` in `classic-node/scanlog.rs`, which all call `LogParser::new(None)` per invocation. These should use a module-level `Lazy<LogParser>` too.

### 4. FCX State Reset Flow

**Current flow (broken):**
```
FcxModeHandler::reset_global_state() {
    if let Some(mut handler) = GLOBAL_FCX_HANDLER.try_lock() {  // NON-BLOCKING
        handler.reset();
    }
    // If lock is held: SILENTLY DOES NOTHING -- stale state persists
}
```

**Target flow:**
```
FcxModeHandler::reset_global_state() {
    let mut handler = GLOBAL_FCX_HANDLER.lock();  // BLOCKING -- waits for lock
    handler.reset();
}
```

**Why blocking lock instead of try_lock:** The `try_lock` was defensive programming, but it defeats the purpose of a reset. The caller is explicitly asking "clear all FCX state before my scan session." If another scan is still holding the lock, the correct behavior is to wait -- the prior scan will release the lock when its FCX operations complete. A `try_lock` that silently fails is a bug, not a feature.

**Alternative considered: `reset_global_state_or_error() -> Result<()>`** -- this would be more explicit, but adds error handling at every call site. Since `parking_lot::Mutex` never poisons (unlike `std::sync::Mutex`), the blocking lock is safe and simpler.

**Boundary exposure:**

| Surface | Current | Target |
|---------|---------|--------|
| Rust core | `FcxModeHandler::reset_global_state()` | Fix to use blocking lock |
| C++ bridge | Not exposed | Add `fn fcx_reset_global_state()` in `scanner.rs` ffi block |
| Node binding | Not exposed | Add `#[napi] pub fn reset_fcx_global_state()` |
| Python binding | Already exposed via `PyFcxModeHandler.reset_global_state` | Verify it delegates correctly |

**Call sites for reset:** Before each scan session start:
- C++ bridge: `orchestrator_new()` or `build_full_scan_config()` should call reset internally, AND expose a standalone reset for callers who want explicit control
- Node binding: `process_log()` and `process_logs_batch()` should call reset internally before scan, AND expose standalone `resetFcxGlobalState()`
- Orchestrator core: `OrchestratorCore::new()` is the natural place for automatic reset

### 5. Singleton Interaction with Test Isolation

**VersionRegistry (OnceLock):**
- Initialized once per process lifetime. Cannot be reloaded.
- Test isolation: Tests that need different registry data MUST run in separate processes. This is an explicit design decision (documented in PROJECT.md "Out of Scope").
- Impact on this milestone: None. The LRU cache and FCX changes do not interact with VersionRegistry.

**FcxModeHandler (Mutex):**
- Mutable per-session state behind `parking_lot::Mutex`.
- Test isolation: Tests MUST call `reset_global_state()` in setup. Since `parking_lot::Mutex` is not poisoning, a panicked test does not break subsequent tests -- but stale state does.
- Impact on this milestone: The fix from `try_lock` to `lock` improves test isolation because reset always succeeds.

**Interaction between singletons:**
- `VersionRegistry` feeds `AnalysisConfig` via `build_analysis_config_from_yaml`
- `FcxModeHandler` is driven by `AnalysisConfig.fcx_mode`
- They do NOT share state. No circular dependency.

## Component Dependency Graph (for changed components only)

```
classic-yaml-core (cache change)
    ^
    |
classic-settings-core (cache change)    classic-file-io-core (cache change)
    ^                                        ^
    |                                        |
classic-config-core (unchanged)         classic-scangame-core (unchanged)
    ^
    |
classic-scanlog-core
  |-- mod_detector.rs (AhoCorasick)
  |-- fcx_handler.rs (reset fix)
  |-- orchestrator.rs (session reset call)
    ^
    |
classic-cpp-bridge/scanner.rs (Lazy<LogParser>, fcx_reset FFI)
    ^                                    ^
    |                                    |
classic-cli (unchanged)          classic-gui (unchanged)

classic-node/scanlog.rs (Lazy<LogParser>, fcx_reset + ConfigIssue NAPI)
```

## Suggested Build Order (Dependencies Between Changes)

Changes group into three independent workstreams that can be parallelized, plus a final integration step.

### Workstream A: Bounded Caches (independent of B and C)

**Order matters within this workstream due to shared pattern:**

1. **classic-yaml-core YAML_CACHE** -- Add `quick_cache` dependency (already in workspace), replace `Lazy<DashMap<PathBuf, CachedYaml>>` with `LazyLock<Cache<PathBuf, CachedYaml>>`. Requires `CachedYaml` to implement `Clone + Send + Sync + 'static` (it already implements `Clone`; check `Send`/`Sync` -- `Arc<Yaml>` and `SystemTime` are both Send+Sync, and `Option<String>` is too, so this is satisfied). Update `cache_stats()` to use external atomic counters rather than cache iteration. Update tests that check `YAML_CACHE.contains_key()` to use the new API. Default capacity: 256 entries (covers typical CLASSIC installations with ~20-50 YAML files, with headroom for testing).

2. **classic-settings-core SETTINGS_CACHE** -- Same pattern as step 1. Replace `Lazy<DashMap<String, Arc<Vec<Yaml>>>>` with `LazyLock<Cache<String, Arc<Vec<Yaml>>>>`. Default capacity: 128 entries.

3. **classic-file-io-core HASH_CACHE** -- Same pattern as step 1. Replace `LazyLock<Arc<DashMap<PathBuf, String>>>` with `LazyLock<Cache<PathBuf, String>>`. Default capacity: 1024 entries (hash cache sees more unique keys during game-scan workflows).

**Key technical detail:** `quick_cache::sync::Cache` does NOT support `.iter()` like DashMap does. The `cache_stats()` functions in yaml-core and settings-core currently iterate the cache to compute total bytes or list keys. Options:
- **Option A (recommended):** Track stats externally with atomic counters (entry count, total bytes) updated on insert/remove. Increment on insert, decrement when a known key is evicted or explicitly removed.
- **Option B:** Accept approximate stats. `quick_cache` provides `.len()` for entry count. Total bytes can be tracked via an `AtomicUsize` incremented on insert and decremented on eviction (using `quick_cache`'s `Lifecycle` trait).

### Workstream B: Pattern Caching (independent of A and C)

1. **detect_mods_important AhoCorasick** -- Add a module-level `Lazy<Mutex<LruCache<u64, Arc<AhoCorasick>>>>` in `mod_detector.rs`. Hash the detect strings from `entries` using xxhash (already a dependency: `xxhash-rust`). On cache miss, build the automaton. On cache hit, reuse it. The AhoCorasick `find_iter` returns `Match` with `.pattern()` index, which maps back to the `entries` slice by position. Handle per-entry gpu/exclusion logic post-match. Capacity: 8 entries (typically 1-2 mod lists per session).

2. **detect_mods_single/double/batch regex caching** -- Similar approach, but these already build a single combined regex alternation per call. Cache the compiled `Regex` keyed by a hash of the sorted mod patterns. This is lower priority since the single-regex approach is already reasonably fast.

3. **Bridge-level Lazy<LogParser>** -- Add `static BRIDGE_PARSER: Lazy<LogParser>` in `classic-cpp-bridge/scanner.rs`. Use in `detect_crash_pattern`. Trivial change.

4. **Node binding Lazy<LogParser>** -- Same pattern in `classic-node/scanlog.rs` for `parse_log_segments`, `extract_form_ids`, `extract_plugin_list`, `detect_crash_pattern`. These all currently call `LogParser::new(None)` per invocation.

### Workstream C: FCX State Management (independent of A and B)

1. **Fix `reset_global_state` in fcx_handler.rs** -- Change `try_lock()` to `lock()`. Single-line change.

2. **Add automatic reset in OrchestratorCore** -- Call `FcxModeHandler::reset_global_state()` at the start of `OrchestratorCore::process_log()` or in the orchestrator's scan-session initialization path. This ensures every scan session starts clean.

3. **Expose reset in C++ bridge** -- Add `fn fcx_reset_global_state()` to the `extern "Rust"` block in `scanner.rs`. Implementation: call `FcxModeHandler::reset_global_state()`.

4. **Expose reset + ConfigIssue in Node binding** -- Add `#[napi] pub fn reset_fcx_global_state()` and `#[napi] pub fn get_fcx_config_issues() -> Vec<JsConfigIssue>` in `scanlog.rs`. Define `JsConfigIssue` as a NAPI-compatible struct mirroring `ConfigIssue`.

### Integration Step (after all workstreams)

- **Criterion benchmarks** -- Before/after benchmarks for:
  - YAML cache operations (bounded vs unbounded)
  - `detect_mods_important` with AhoCorasick vs per-entry regex
  - `detect_crash_pattern` with cached vs per-call parser
- **Parity gates** -- Run Python and Node parity gates to verify no binding contract changes
- **C++ build** -- Rebuild bridge and verify CXX header generation includes `fcx_reset_global_state`

## Patterns to Follow

### Pattern 1: quick_cache for Global Concurrent Caches

**What:** Replace unbounded `DashMap` globals with bounded `quick_cache::sync::Cache`
**When:** Any static/global cache that grows with input diversity and is read concurrently
**Existing example:** `FileIOCore.read_cache` in `classic-file-io-core/core.rs:99`

```rust
use quick_cache::sync::Cache;
use std::sync::LazyLock;

static YAML_CACHE: LazyLock<Cache<PathBuf, CachedYaml>> =
    LazyLock::new(|| Cache::new(256));
```

**Note:** This also modernizes from `once_cell::sync::Lazy` to `std::sync::LazyLock` (available since Rust 1.80, workspace requires 1.85+). The codebase mixes both; new code should prefer `LazyLock`.

### Pattern 2: AhoCorasick with Pattern-Index Lookup

**What:** Replace per-entry `Regex::new` with a single AhoCorasick automaton
**When:** Multiple literal (or near-literal) patterns need matching against the same text, and you need to know which pattern matched
**Existing example:** `RecordScanner` in `classic-scanlog-core/record_scanner.rs:17`

```rust
use aho_corasick::{AhoCorasick, AhoCorasickBuilder};

let automaton = AhoCorasickBuilder::new()
    .ascii_case_insensitive(true)
    .build(&patterns)?;

for mat in automaton.find_iter(text) {
    let pattern_index = mat.pattern().as_usize();
    let entry = &entries[pattern_index];
    // per-entry logic here
}
```

### Pattern 3: Module-Level Lazy Singleton for Expensive Constructors

**What:** Hold a `Lazy<T>` at module scope for objects that are expensive to construct and safe to share
**When:** Constructor is called per-invocation but the object is thread-safe and stateless (or uses internal caching)
**Existing example:** `GLOBAL_FCX_HANDLER` in `classic-scanlog-core/fcx_handler.rs:23`

```rust
use once_cell::sync::Lazy;  // or std::sync::LazyLock

static BRIDGE_PARSER: Lazy<LogParser> = Lazy::new(|| {
    LogParser::new(None).expect("LogParser pattern compilation failed")
});
```

### Pattern 4: CXX FFI Function Exposure

**What:** Expose a new Rust function through the CXX bridge
**When:** C++ frontends need access to new Rust functionality
**Existing example:** `papyrus_reset` in `classic-cpp-bridge/scanner.rs:818,941`

```rust
// Implementation function (outside ffi module)
fn fcx_reset_global_state() {
    classic_scanlog_core::FcxModeHandler::reset_global_state();
}

// Inside #[cxx::bridge] mod ffi { extern "Rust" { ... } }
fn fcx_reset_global_state();
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: RwLock<LruCache> for High-Concurrency Global Caches

**What:** Wrapping `lru::LruCache` in `RwLock` for a process-wide static cache
**Why bad:** Even read operations on `LruCache` require a write lock (to update LRU ordering). This serializes all concurrent readers. The `LogParser`'s internal caches use this pattern but are instance-scoped (one parser, few concurrent readers). For process-wide caches like YAML_CACHE that serve all scan workers simultaneously, this would be a concurrency regression compared to the current DashMap.
**Instead:** Use `quick_cache::sync::Cache` which handles LRU eviction internally with fine-grained locking.

### Anti-Pattern 2: try_lock for Mandatory State Operations

**What:** Using `Mutex::try_lock()` for operations that MUST succeed
**Why bad:** If the lock cannot be acquired, the operation is silently skipped. For FCX reset, this means stale state from a prior scan leaks into the next session.
**Instead:** Use `Mutex::lock()` (blocking). If you need non-blocking semantics, return an error: `try_lock().ok_or(ResetContention)` -- but never silently skip.

### Anti-Pattern 3: Per-Call Pattern Compilation in Hot Paths

**What:** Calling `Regex::new()` or building an AhoCorasick automaton inside a function that runs per-log or per-entry in a batch
**Why bad:** Pattern compilation is O(n) in pattern length and involves memory allocation. When scanning 100+ logs with 200+ mod entries, this costs seconds of CPU time for work that produces identical results.
**Instead:** Cache compiled patterns keyed by their input. If inputs are stable within a session (they are -- config is loaded once), a simple hash-based LRU cache eliminates all recompilation.

## Scalability Considerations

| Concern | Desktop (1-10 logs) | Batch scan (100+ logs) | Long-running server |
|---------|---------------------|----------------------|---------------------|
| YAML_CACHE | 20-50 entries, no eviction needed | Same -- config loaded once | Needs eviction; 256 cap sufficient |
| SETTINGS_CACHE | 5-10 entries | Same | Needs eviction; 128 cap sufficient |
| HASH_CACHE | 50-200 files | 500-2000 files | Needs eviction; 1024 cap with possible resize |
| AhoCorasick cache | 1 automaton per session | Same (entries stable) | LRU evicts old sessions; 8 cap sufficient |
| LogParser cache | 1 instance, reused | Same | Same -- `Lazy` singleton |
| FCX state | Reset per scan | Reset before batch | Reset before each session |

## Sources

- Direct source inspection of all affected files (HIGH confidence -- no external sources needed for architecture analysis of existing code)
- `quick_cache` v0.6 API: already used in `classic-file-io-core/core.rs` (established pattern)
- `aho-corasick` v1.1 API: already used in `patterns.rs`, `record_scanner.rs`, `plugin_analyzer.rs` (established pattern)
- `parking_lot::Mutex` v0.12: already used in `fcx_handler.rs` (established pattern)
- `lru` v0.16: already used in `parser.rs` and `core.rs` for instance-scoped caches (established pattern)

---

*Architecture analysis: 2026-04-04*
