# Feature Landscape: Codebase Health Milestone

**Domain:** Rust codebase health, tech debt removal, performance hardening, binding parity
**Researched:** 2026-04-04
**Overall Confidence:** HIGH

## Executive Summary

This milestone addresses every concern surfaced during the codebase audit of CLASSIC's 19 business-logic crates, 3 binding surfaces (CXX, PyO3, NAPI-RS), and supporting infrastructure. The features are not user-facing -- they are engineering health improvements that make the codebase more maintainable, performant, and correct. The features naturally cluster into six concern categories: dead code removal, deprecated API migration, singleton/state management, cache eviction, regex optimization, and binding parity. All features are scoped to resolve specific audit findings.

---

## Table Stakes

Features that **must** be completed or the codebase health goal is unmet. If any of these are skipped, the audit remains open.

### TS-1: Dead Code Removal

Remove all `#[allow(dead_code)]` items identified in the audit. Every one of these hides potential future dead-code warnings and signals unfinished work.

| Item | Location | Complexity | Notes |
|------|----------|------------|-------|
| `SEGMENT_BOUNDARIES` static | `classic-scanlog-core/src/parser.rs:70` | Low | Pure deletion. No callers. Named-section parsing via `parse_all_sections_arc` is canonical. |
| `YamlFormatConfig` struct + field | `classic-yaml-core/src/lib.rs:507` | Low | Reserved-for-future field never shipped. Remove struct and `format_config` field from `YamlOperations`. |
| `PluginAnalyzer.case_cache` field | `classic-scanlog-core/src/plugin_analyzer.rs:67` | Low | `Arc<DashMap>` allocated per orchestrator but never written or read. Remove field. |
| `PyGpuDetector.inner` field | `classic-scanlog-py/src/gpu_detector.rs:118` | Low | `GpuDetector` methods are static; binding holds unused instance. Convert to stateless Python class. |

**Best practice for dead code across FFI boundaries:** Before removing any public Rust symbol, verify it does not appear in:
1. The Python parity surface (`rust_api_surface.json`, `python_api_surface.json`)
2. The Node parity surface (NAPI `#[napi]` exports)
3. The C++ bridge (`#[cxx::bridge]` declarations)

For this milestone, all four items are crate-internal or binding-internal -- none are cross-boundary public APIs. Deletion is safe without deprecation cycles.

**Confidence:** HIGH -- all items verified in source with `#[allow(dead_code)]` annotations.

---

### TS-2: Deprecated API Migration and Removal

Complete the migration of all callers away from deprecated APIs, then delete the deprecated methods.

| Deprecated API | Deprecation Version | Remaining Callers | Migration Target | Complexity |
|----------------|--------------------|--------------------|------------------|------------|
| `LogParser::parse_segments` | 9.0.0 | None (shim only) | `parse_all_sections_arc` | Low |
| `LogParser::parse_segments_parallel` | 9.0.0 | Python binding `classic-scanlog-py/src/parser.rs:98` | `parse_all_sections_arc` | Medium |
| `CrashgenVersion::is_outdated` | 0.2.0 | Tests (with `#[allow(deprecated)]`), Python `generate_suspect_section` legacy path | `check_version_status()` | Medium |

**Migration approach:**

1. **Python binding `parse_segments_parallel` caller:** Replace with a wrapper that calls `parse_all_sections_arc` and reshapes the return value to match the Python-facing type signature. The Python binding type contract (`classic_scanlog.pyi`) must be updated simultaneously.

2. **Python `generate_suspect_section` legacy method:** Migrate to call `generate_suspect_section_header` + `generate_suspect_found_footer` separately. Mark the Python method as deprecated in the `.pyi` stub before removal.

3. **Test callers of `is_outdated`:** Rewrite tests to exercise `check_version_status()` instead. Delete `#[allow(deprecated)]` guards.

4. **Final removal:** After all callers are migrated, delete the deprecated methods. The crate-level lint `deprecated = "deny"` (already set in `classic-scanlog-core/Cargo.toml`) will prevent any new `#[allow(deprecated)]` from sneaking back.

**Confidence:** HIGH -- all callers are enumerated in CONCERNS.md and verified in source.

---

### TS-3: Legacy Settings Fallback Elimination

Eliminate the `scan_all_settings_legacy_bucketed` code path in `SettingsValidator`.

| Aspect | Detail |
|--------|--------|
| **Current state** | `scan_all_settings` falls back to legacy path when `CrashgenEntry` is `None` |
| **Risk** | Two structurally different validation paths produce inconsistent results |
| **Complexity** | Medium |

**Approach:**
1. Add a tracing warning when the legacy path activates (immediate, enables detection).
2. Add an assertion test that standard production crashgen configs never hit the legacy path.
3. Audit all config sources to confirm `CrashgenEntry` is always populated for production YAML files.
4. Once confirmed, gate the legacy path behind a `#[deprecated]` marker, then remove it.

**Confidence:** HIGH -- the code path is clearly identified and the structured `CrashgenEntry` approach is canonical.

---

### TS-4: Python FormID Legacy Map Deprecation Warning

Add a deprecation warning when `PyFormIDAnalyzerCore::new` receives `mods_single` as a plain `PyDict` (legacy map format) instead of the structured `ModSolutionEntry` sequence.

| Aspect | Detail |
|--------|--------|
| **Current state** | `legacy_mod_map_to_entries()` silently converts old format |
| **Target state** | Emit `DeprecationWarning` via `PyErr::warn` when legacy dict detected |
| **Complexity** | Low |

**Approach:** Use PyO3's `PyErr::warn(py, pyo3::exceptions::PyDeprecationWarning, "...")` at the detection point. Do NOT remove the legacy path in this milestone -- the constraint says "deprecation warning first, not immediate removal."

**Confidence:** HIGH -- PyO3 `PyErr::warn` is the standard pattern for Python deprecation warnings from Rust.

---

### TS-5: FCX Global State Hardening

Fix the silent-drop-on-contention bug in `GLOBAL_FCX_HANDLER.reset_global_state()` and expose reset/access across all binding surfaces.

| Sub-feature | Complexity | Notes |
|-------------|------------|-------|
| Fix `try_lock()` silent drop | Medium | Replace `try_lock()` with blocking `lock()` or return `Result<(), ResetError>` so callers know reset failed. |
| Expose reset in C++ bridge | Low | Add `reset_fcx_global_state()` to CXX bridge extern block. Call before each scan session. |
| Expose reset in Node bindings | Low | Add `resetFcxState()` NAPI function. Call before each scan session. |
| Expose `ConfigIssue` list in Node | Medium | Define `JsConfigIssue` NAPI struct mirroring Rust `ConfigIssue`. Expose via `getFcxIssues()`. |

**Best practice for resettable singletons:** The current `parking_lot::Mutex` wrapping is correct for a resettable singleton. The problem is `try_lock()` -- in a long-running process, a failed reset is a correctness bug, not a performance optimization. Use `.lock()` (which never fails with `parking_lot` -- no poisoning) or at minimum return an error rather than silently succeeding.

**Alternative considered:** Replace `Lazy<Mutex<FcxModeHandler>>` with a scoped handler passed through the orchestrator. Rejected -- this would be a major API redesign, out of scope for a health milestone.

**Confidence:** HIGH -- the `try_lock()` behavior is directly observable in source; `parking_lot::Mutex::lock()` is non-poisoning and documented.

---

### TS-6: Cache Bounded Eviction

Add capacity limits to the three unbounded global caches identified in the audit.

| Cache | Current Type | Location | Eviction Strategy | Complexity |
|-------|-------------|----------|-------------------|------------|
| `YAML_CACHE` | `Lazy<DashMap<PathBuf, CachedYaml>>` | `classic-yaml-core/src/lib.rs:156` | LRU by access time | Medium |
| `SETTINGS_CACHE` | `Lazy<DashMap<String, Arc<Vec<Yaml>>>>` | `classic-settings-core/src/cache.rs:18` | LRU by access time | Medium |
| `HASH_CACHE` | `LazyLock<Arc<DashMap<PathBuf, String>>>` | `classic-file-io-core/src/hash.rs:51` | LRU by access time | Medium |

**Recommended approach:** Use the `quick_cache` crate (already a workspace dependency, version 0.6) to replace unbounded `DashMap` instances. `quick_cache::sync::Cache` provides:
- Bounded capacity with automatic eviction
- Lock-free concurrent access (no global mutex)
- Built-in frequency/recency-aware eviction (inspired by Caffeine/W-TinyLFU)
- Already used successfully in `classic-file-io-core` for file content caching

**Why `quick_cache` over alternatives:**
- `moka` is the other major option but adds a heavier dependency (background maintenance thread). `quick_cache` is already in the workspace and has proven itself in `classic-file-io-core`.
- `lru` crate (also in workspace) requires external `RwLock` wrapping for concurrent access -- already used in `LogParser` but less ergonomic for global statics.
- Wrapping `DashMap` with manual eviction logic is error-prone and duplicates what `quick_cache` provides.

**Capacity sizing recommendations:**
- `YAML_CACHE`: 128 entries (typical CLASSIC session loads ~20-40 distinct YAML files; 128 gives generous headroom).
- `SETTINGS_CACHE`: 64 entries (settings files are fewer and larger).
- `HASH_CACHE`: 1024 entries (file hashing is high-throughput during scan; larger capacity avoids thrashing).

**Confidence:** HIGH -- `quick_cache` is already proven in the codebase.

---

### TS-7: Mmap TOCTOU Safety

Switch `read_file_mmap` from `Mmap::map()` to `MmapOptions::map_copy()` for copy-on-write safety.

| Aspect | Detail |
|--------|--------|
| **Current state** | `Mmap::map()` with documented safety invariants |
| **Target state** | `MmapOptions::new().map_copy(&file)` for COW semantics |
| **Complexity** | Low |
| **Performance impact** | Negligible for read-only workloads -- COW pages are not copied until written (which never happens in CLASSIC's read-only path) |

**Why this matters:** On Windows, another process can modify a file while it is memory-mapped. `map_copy()` creates a copy-on-write mapping where the process gets a private view -- external modifications do not affect the mapped data. Since CLASSIC only reads mmap'd data and never writes, the COW overhead is effectively zero.

**Confidence:** HIGH -- `memmap2::MmapOptions::map_copy()` is documented and the performance characteristics are well-understood for read-only workloads.

---

### TS-8: Regex Optimization in Mod Detector Hot Paths

Cache compiled regex patterns in `detect_mods_single`, `detect_mods_double`, `detect_mods_batch`, and `detect_mods_important`.

| Sub-feature | Complexity | Impact |
|-------------|------------|--------|
| Cache combined alternation pattern in `detect_mods_single`/`double`/`batch` | Medium | Eliminate per-call `Regex::new()` for the same mod list |
| Replace per-entry regex in `detect_mods_important` with AhoCorasick or `str::contains` | Medium | Eliminate N separate `Regex::new()` calls per invocation |
| Cache `LogParser` in C++ bridge `detect_crash_pattern` | Low | Eliminate per-call `LogParser::new()` rebuilding all compiled patterns |

**Best practice analysis for `detect_mods_important`:**

The current code does `Regex::new(&format!("(?i){}", regex::escape(&entry.detect.to_lowercase())))` per entry. Since `regex::escape` produces a literal string, this is equivalent to a case-insensitive `str::contains` check. There are three valid approaches:

1. **`str::contains` with lowercased inputs (simplest, recommended):** Since both the detect pattern and the search text are already lowercased, replace the regex with `all_text.contains(&entry.detect.to_lowercase())`. Zero compilation overhead. This is the right answer because the patterns are all escaped literals -- no regex features are used.

2. **AhoCorasick automaton (best for large entry lists):** Pre-build an `AhoCorasick` automaton from all detect strings, scan the text once, then map matches back to entries. Ideal if the entry list is large (>50 patterns). The crate is already used extensively in `record_scanner.rs`, `patterns.rs`, and `plugin_analyzer.rs`.

3. **HashSet lookup (best for exact-match):** If patterns are always full plugin names (not substrings), a `HashSet` lookup is O(1). But the current logic does substring matching against concatenated text, so this only works with structural changes.

**Recommendation:** Use approach 1 (`str::contains`) for `detect_mods_important` since patterns are escaped literals. Use approach 2 (AhoCorasick) for the combined alternation patterns in `detect_mods_single`/`double`/`batch` if caching the compiled `Regex` is not sufficient -- but caching the `Regex` keyed by a hash of the mod list is simpler and adequate since the same mod list is reused across a scan session.

**Caching strategy for combined patterns:** Key the cache by a hash of the sorted mod list entries (using `xxhash` which is already a workspace dependency). Invalidate on config reload. Store in a module-level `LazyLock<RwLock<HashMap<u64, Regex>>>` or use `quick_cache::sync::Cache`.

**C++ bridge `LogParser` caching:** Replace `LogParser::new(None).unwrap()` in `detect_crash_pattern` with a `LazyLock<LogParser>` at module scope. `LogParser` is `Send + Sync` (it stores `Arc`-wrapped caches internally), so this is safe.

**Confidence:** HIGH -- the regex-escape-to-literal equivalence is verifiable in source. AhoCorasick patterns are already established in the codebase.

---

### TS-9: Workspace Dependency Promotion

Promote `winreg` and `phf` to workspace-level dependencies.

| Dependency | Current Location | Complexity |
|------------|-----------------|------------|
| `winreg = "0.52"` | `classic-path-core/Cargo.toml` only | Low |
| `phf = "0.13.1"` | `classic-constants-core/Cargo.toml` only | Low |

**Approach:** Add to `[workspace.dependencies]` in root `Cargo.toml`, replace crate-local pins with `winreg = { workspace = true }`.

**Confidence:** HIGH -- mechanical change.

---

### TS-10: Proton Path Wiring

Wire up `construct_proton_docs_path` to the Linux docs-path discovery workflow rather than deleting it.

| Aspect | Detail |
|--------|--------|
| **Current state** | Function exists but is dead code (`#[allow(dead_code)]`) |
| **Target state** | Called from Linux docs-path discovery; tested with mock Proton prefix |
| **Complexity** | Medium |

**Approach:** Integrate into the `discover_docs_path` Linux code path. Add unit tests with a temporary directory mimicking a Proton prefix structure.

**Confidence:** MEDIUM -- the function exists and its signature is known, but the Linux docs-path discovery integration point needs exploration during implementation.

---

### TS-11: Test Coverage for Identified Gaps

Add test coverage for the five specific gaps identified in the audit.

| Test Gap | Priority | Complexity |
|----------|----------|------------|
| FCX contention reset (silent drop on `try_lock`) | Medium | Medium -- requires concurrent test setup |
| Legacy settings path assertion (standard configs do NOT hit legacy path) | Medium | Low -- assert on known production config |
| Linux Proton path discovery | Medium | Medium -- needs mock Proton prefix |
| Node binding FCX state carryover | Low | Medium -- needs Node test harness |
| C++ bridge `detect_crash_pattern` parser allocation regression | Low | Low -- criterion benchmark, not unit test |

**Confidence:** HIGH -- all gaps are precisely specified with file locations.

---

### TS-12: Zerovec Workaround Documentation

Document or resolve the `zerovec` workaround dependency in `classic-shared-core`.

| Aspect | Detail |
|--------|--------|
| **Current state** | Dev-dependency workaround for Slint/icu_properties transitive dep |
| **Complexity** | Low |
| **Approach** | Add workspace-level comment referencing the upstream issue; check if Slint 1.15+ resolved it |

**Confidence:** MEDIUM -- the workaround may already be unnecessary with current Slint version.

---

### TS-13: Node `index.d.ts` Build Requirement

Document or commit the Node `index.d.ts` build-first requirement.

| Aspect | Detail |
|--------|--------|
| **Current state** | `package.json` declares types but file is gitignored and only generated post-build |
| **Complexity** | Low |
| **Approach** | Commit a generated `index.d.ts` snapshot with a CI freshness check (already partially exists via `dts:freshness:check`) |

**Confidence:** HIGH -- the CI tooling already exists; this is a documentation/process gap.

---

### TS-14: Criterion Benchmarks for Performance Changes

Add before/after criterion benchmarks proving each performance improvement.

| Benchmark Target | What to Measure | Complexity |
|-----------------|-----------------|------------|
| `detect_mods_important` | Latency per call with 50+ entry list | Medium |
| `detect_mods_single`/`batch` | Latency with cached vs uncached regex | Medium |
| `detect_crash_pattern` (bridge) | Latency with cached vs per-call `LogParser` | Low |
| Mmap `map_copy` vs `map` | Read throughput for 1MB+ files | Low |

**Note:** Criterion benchmarks already have infrastructure in `classic-scanlog-core/benches/scanlog_benchmarks.rs`. Extend, do not create a parallel framework.

**Confidence:** HIGH -- criterion is already a dev-dependency with existing benchmark harness.

---

## Differentiators

Go-beyond improvements that are **valuable but not strictly required** by the audit findings.

### D-1: Replace `once_cell` with `std::sync::LazyLock`

| Aspect | Detail |
|--------|--------|
| **Rationale** | `LazyLock` is stable since Rust 1.80; `once_cell::sync::Lazy` is the third-party predecessor. Some crates already use `LazyLock`, others use `once_cell`. |
| **Complexity** | Low (mechanical find-replace per crate) |
| **Value** | Reduces external dependency, unifies initialization pattern across codebase |

**Current state in codebase:** Mixed -- `classic-shared-core`, `classic-file-io-core`, and `classic-node` use `std::sync::LazyLock`. `classic-yaml-core`, `classic-settings-core`, `classic-registry-core`, and `classic-perf-core` still use `once_cell::sync::Lazy`. This is a consistency improvement, not a correctness fix.

---

### D-2: Structured Error Returns for FCX Reset

Instead of just fixing the `try_lock` silent drop, return a `Result<(), FcxResetError>` from `reset_global_state()` that callers can log or propagate. This makes failures observable across all surfaces, not just non-silent.

| Aspect | Detail |
|--------|--------|
| **Complexity** | Low |
| **Value** | Callers can distinguish "reset succeeded" from "reset was unnecessary" from "reset failed" |

---

### D-3: Cache Metrics Unification

All three bounded caches (YAML, settings, hash) should expose a consistent `CacheStats` struct with hits, misses, hit rate, size, and capacity. `SETTINGS_CACHE` already has this pattern; extend to `YAML_CACHE` and `HASH_CACHE`.

| Aspect | Detail |
|--------|--------|
| **Complexity** | Low |
| **Value** | Enables runtime observability for cache sizing tuning |

---

### D-4: Compile-Time Regex Validation

For static patterns (crash patterns, section headers), use the `regex!` proc-macro or `LazyLock` with `Regex::new().unwrap()` to move compilation failure from runtime to startup. This is already the pattern in `LogParser` but not in `mod_detector`.

| Aspect | Detail |
|--------|--------|
| **Complexity** | Low |
| **Value** | Faster feedback on broken patterns; eliminates runtime `Result` propagation for known-good patterns |

---

### D-5: TUI Dependency Workspace Promotion

Promote `ratatui`, `arboard`, `crossterm`, and `open` to workspace dependencies for consistency with the rest of the codebase.

| Aspect | Detail |
|--------|--------|
| **Complexity** | Low |
| **Value** | Central version management |
| **PROJECT.md Decision** | Explicitly marked out-of-scope ("TUI deps are local to one crate") |

**Include only if** the milestone scope is broadened. Respect the PROJECT.md decision boundary.

---

## Anti-Features

Things to deliberately **NOT** do in this cleanup milestone.

### AF-1: Do NOT Redesign Singleton Architecture

**What to avoid:** Replacing `OnceLock`/`Lazy` singletons (VersionRegistry, YAML_CACHE, FCX handler) with dependency-injection or scoped-lifetime patterns.

**Why:** Singleton patterns are architectural decisions baked into the crate layering. Redesigning them changes APIs across all 3 binding surfaces and violates the "no major binding API redesigns" constraint. The health milestone fixes specific bugs (silent reset failure, unbounded growth) without structural rewrites.

**The VersionRegistry OnceLock is explicitly out of scope** per PROJECT.md -- process-restart isolation is acceptable for registry reloads.

---

### AF-2: Do NOT Remove Python FormID Legacy Map Path

**What to avoid:** Deleting `legacy_mod_map_to_entries()` or rejecting legacy `PyDict` input.

**Why:** PROJECT.md constraint: "Python FormID legacy map format gets deprecation warning first, not immediate removal." This milestone adds the warning; a future milestone removes the path.

---

### AF-3: Do NOT Add New Features

**What to avoid:** Adding new user-facing functionality, new crate capabilities, or new binding surface methods beyond what is needed to fix parity gaps.

**Why:** This is purely a health/hardening milestone. New features risk scope creep and complicate verification.

---

### AF-4: Do NOT Bulk-Refactor Error Handling

**What to avoid:** Migrating all crates from `anyhow` to `thiserror`, or vice versa, or introducing a codebase-wide error taxonomy.

**Why:** Error handling works. Individual crates use appropriate patterns. A bulk migration risks regressions with no audit-driven justification.

---

### AF-5: Do NOT Optimize Working Code Without Benchmarks

**What to avoid:** Preemptive optimization of code paths not identified in the audit. No "while we're here, let's also optimize X" changes.

**Why:** The audit identified specific performance bottlenecks (`detect_mods_important`, per-call `LogParser::new`, unbounded caches). Only those warrant optimization. Other code paths should be left alone unless criterion benchmarks reveal a regression.

---

### AF-6: Do NOT Touch CXX `unsafe extern "C++"` Blocks

**What to avoid:** Attempting to remove or restructure the `unsafe extern "C++"` declaration for `ScanBatchProgressCallback`.

**Why:** CXX manages the safety boundary. Per PROJECT.md: "CXX framework manages this; no action needed beyond version upgrades."

---

### AF-7: Do NOT Introduce New Runtimes or Async Patterns

**What to avoid:** Adding a background eviction thread for caches, using `tokio::spawn` for cache maintenance, or introducing any new runtime.

**Why:** ONE RUNTIME RULE. `quick_cache` handles eviction inline during cache operations (no background thread). This is the correct pattern for the existing architecture.

---

## Feature Dependencies

```
TS-2 (Deprecated API migration)
    |
    +-- Must complete BEFORE TS-1 (Dead code removal)
    |   (deprecated shims reference patterns that dead code depends on)
    |
    +-- TS-4 (Python FormID deprecation warning) is INDEPENDENT
    |   (different crate, different API surface)
    |
TS-3 (Legacy settings elimination)
    |
    +-- TS-11 test gap: "legacy path not hit for standard configs"
    |   (test should be added BEFORE or WITH the elimination)

TS-5 (FCX hardening)
    |
    +-- Expose in C++ bridge (depends on fix in core)
    +-- Expose in Node bindings (depends on fix in core)
    +-- TS-11 test gaps: FCX contention, Node FCX state carryover
    |   (tests should accompany or immediately follow the fix)

TS-6 (Cache eviction) -- INDEPENDENT of all other features
    |
    +-- Can be done in any order
    +-- TS-14 benchmarks should measure before/after

TS-7 (Mmap TOCTOU) -- INDEPENDENT
    |
    +-- TS-14 benchmark to prove no regression

TS-8 (Regex optimization) -- INDEPENDENT
    |
    +-- TS-14 benchmarks REQUIRED (before/after proof)

TS-9 (Workspace deps) -- INDEPENDENT, can be done anytime

TS-10 (Proton path) -- INDEPENDENT
    |
    +-- TS-11 test gap: Linux Proton path

TS-12 (Zerovec docs) -- INDEPENDENT
TS-13 (Node index.d.ts) -- INDEPENDENT
TS-14 (Benchmarks) -- depends on TS-6, TS-7, TS-8 being in progress
```

---

## MVP Recommendation

**Priority order based on dependency chain and risk:**

1. **TS-8: Regex optimization** -- highest performance impact, most complex, benefits from early benchmarking. Start with `detect_mods_important` (the `str::contains` conversion is the clearest win).

2. **TS-5: FCX hardening** -- correctness bug (silent state corruption). Fix core first, then wire bindings.

3. **TS-2: Deprecated API migration** -- unblocks dead code removal and reduces surface area.

4. **TS-1: Dead code removal** -- low risk, high clarity improvement. Do after TS-2.

5. **TS-6: Cache eviction** -- memory safety for long-running processes. Independent, medium complexity.

6. **TS-7: Mmap TOCTOU** -- low complexity, high safety value.

7. **TS-3: Legacy settings elimination** -- medium complexity, needs test coverage first.

8. **TS-9, TS-10, TS-12, TS-13** -- low-complexity housekeeping, can fill gaps.

9. **TS-4: Python FormID warning** -- lowest risk, independent.

10. **TS-11, TS-14: Tests and benchmarks** -- accompany their corresponding features, not a separate phase.

**Defer to later milestones:**
- D-1 (`once_cell` to `LazyLock` migration) -- nice but not audit-driven
- D-5 (TUI dep promotion) -- explicitly out of scope per PROJECT.md

---

## Sources

### Official Documentation
- [Rust `OnceLock` std docs](https://doc.rust-lang.org/std/sync/struct.OnceLock.html)
- [Rust `LazyLock` std docs](https://doc.rust-lang.org/std/sync/struct.LazyLock.html)
- [memmap2 `MmapOptions::map_copy` docs](https://docs.rs/memmap2/latest/memmap2/struct.MmapOptions.html)
- [aho-corasick crate docs](https://docs.rs/aho-corasick/latest/aho_corasick/)
- [quick_cache crate docs](https://docs.rs/quick_cache/latest/quick_cache/)
- [moka cache (alternative considered)](https://github.com/moka-rs/moka)
- [parking_lot Mutex (non-poisoning)](https://docs.rs/parking_lot/latest/parking_lot/type.Mutex.html)

### Codebase Verification
- All file locations and code patterns verified against current source in `ClassicLib-rs/`
- `aho-corasick` already used in `record_scanner.rs`, `patterns.rs`, `plugin_analyzer.rs`, `logs.rs`
- `quick_cache` already used in `classic-file-io-core/src/core.rs`
- `lru` already used in `classic-scanlog-core/src/parser.rs` and `classic-file-io-core/src/core.rs`
- Criterion benchmark harness already exists in `classic-scanlog-core/benches/scanlog_benchmarks.rs`

### Web Research
- [Rust caching strategies (2026)](https://oneuptime.com/blog/post/2026-02-01-rust-caching-strategies/view) -- MEDIUM confidence
- [Aho-Corasick optimization for literal alternation (regex issue #891)](https://github.com/rust-lang/regex/issues/891) -- HIGH confidence
- [Global mutable singletons in Rust (2026)](https://oneuptime.com/blog/post/2026-01-25-global-mutable-singletons-rust/view) -- MEDIUM confidence
- [Rust mmap safety discussion](https://users.rust-lang.org/t/is-there-no-safe-way-to-use-mmap-in-rust/70338) -- HIGH confidence
