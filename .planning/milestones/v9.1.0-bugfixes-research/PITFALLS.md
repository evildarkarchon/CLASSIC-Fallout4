# Domain Pitfalls: Rust Codebase Health & Cleanup

**Domain:** Rust workspace cleanup with FFI boundaries (CXX/PyO3/NAPI-RS), global state refactoring, and performance-critical path optimization
**Researched:** 2026-04-04
**Confidence:** HIGH (verified against codebase source, official docs, and known Cargo/crate behaviors)

---

## Critical Pitfalls

Mistakes that cause broken consumers, data corruption, or require rework of entire phases.

### Pitfall 1: Removing Deprecated Core APIs Breaks FFI Consumers Silently

**What goes wrong:** Deleting `parse_segments_parallel` or `is_outdated` from core crates causes a Rust compilation failure in the core crate tests (because `deprecated = "deny"` is set in `classic-scanlog-core`'s own `[lints.rust]`), but the real danger is that downstream FFI consumers (the Python binding in `classic-scanlog-py/src/parser.rs:98` which calls `parse_segments_parallel` with `#[allow(deprecated)]`) break silently at link time rather than with a clear API migration error. Similarly, `classic-scanlog-py/src/report.rs:307` re-exposes the legacy `is_outdated` equivalent without its own deprecation annotation, so Python consumers have no warning at all.

**Why it happens:** Deprecation annotations in Rust only affect Rust callers. PyO3 wrappers suppress the warning with `#[allow(deprecated)]` and expose a clean Python-facing API. When the core method is removed, the PyO3 binding fails to compile, but the Python consumers never received a deprecation warning. CXX bridge consumers are similarly opaque -- the C++ side sees a function signature, not Rust deprecation metadata.

**Consequences:**
- Python consumers calling `parse_segments_parallel` get a hard break with no migration warning
- The `generate_suspect_section` Python method silently calls the deprecated `is_outdated` path; removing the core method breaks the Python report API
- Node/C++ consumers have no visibility into which Rust APIs are deprecated underneath their binding layer
- Parity gates (`check_parity_gate.py`, `parity:gate:local`) will catch compile-time breakage but NOT catch missing deprecation warnings in the binding-facing APIs

**Prevention:**
1. **Binding-side deprecation first:** Before removing any core API, add explicit deprecation warnings at every binding surface. For Python: emit `warnings.warn("...", DeprecationWarning)` from the PyO3 wrapper. For Node: mark the function with `@deprecated` in `index.d.ts` or emit a console warning.
2. **Two-phase removal:** Phase A: add binding-surface deprecation warnings + migrate binding internals to new API. Phase B (next milestone or after a release cycle): remove the core deprecated method.
3. **Grep for `#[allow(deprecated)]`:** Currently 7 call sites across `classic-scanlog-core` tests and `classic-scanlog-py`. Every `#[allow(deprecated)]` must be migrated before the underlying method can be removed.
4. **Parity gate check:** After migrating bindings, run both `check_parity_gate.py` and `parity:gate:local` to confirm no function signature changes.

**Detection:**
- Search for `#[allow(deprecated)]` across the entire workspace -- any hit is a migration blocker
- Python consumers calling removed methods get `ImportError` or `AttributeError` at runtime
- Node binding build fails at `napi build` step

**Phase to address:** Must be the FIRST work item in any deprecated-API-removal phase. Do not remove core methods until all binding callers are migrated.

---

### Pitfall 2: FCX Global State Reset Silently No-Ops Under Contention

**What goes wrong:** `FcxModeHandler::reset_global_state()` at `fcx_handler.rs:295-298` uses `try_lock()` on `GLOBAL_FCX_HANDLER`. If ANY thread holds the mutex (e.g., a concurrent batch scan is running), the reset is silently skipped. The next scan session inherits stale FCX state -- detected issues from a previous scan appear in the new scan's results.

**Why it happens:** The `try_lock()` pattern was chosen to avoid deadlock in concurrent contexts, but the tradeoff is silent failure. The docstring says "thread-safe and can be called from multiple threads without risk of data races" which is technically true but misleading -- it IS safe from data races, but it is NOT safe from stale state.

**Consequences:**
- Stale FCX `detected_issues` from scan N appear in scan N+1 results
- C++ bridge and Node bindings don't even call `reset_global_state()` at all (documented in CONCERNS.md), so every multi-scan session in those bindings accumulates FCX state
- This is a correctness bug, not just a performance issue -- users see wrong results

**Prevention:**
1. **Replace `try_lock()` with `lock()` and a timeout.** If the lock cannot be acquired within a reasonable window (e.g., 100ms), log a warning and return an error rather than silently succeeding.
2. **Add reset calls to C++ bridge and Node binding scan entry points.** The bridge `scan_crashlogs_batch` and Node `scanLogsBatch` must call `reset_global_state()` BEFORE initiating a new scan session.
3. **Make reset observable:** Change `reset_global_state()` to return a `Result<(), FcxResetError>` or `bool` so callers know whether the reset actually happened.
4. **Test the contention case:** Hold the mutex from a spawned thread, call `reset_global_state()`, assert that either it blocks until success or returns an error -- never silently succeeds.

**Detection:**
- FCX results contain issues from a scan that was not the current one
- Repeated scans in the same process show growing `detected_issues` lists
- Integration tests that run two scans in sequence see ghost results from scan 1 in scan 2

**Phase to address:** Must be addressed in the FCX hardening phase, BEFORE exposing FCX reset to C++ bridge and Node bindings. Fix the reset mechanism first, then wire it to new binding surfaces.

---

### Pitfall 3: AhoCorasick Match Semantics Differ From Regex in Ways That Change Results

**What goes wrong:** Replacing per-entry `Regex::new` in `detect_mods_important` (mod_detector.rs:524) with an AhoCorasick automaton changes which mods are detected, because AhoCorasick's default `MatchKind::Standard` reports the first match found by the automaton walk, not the leftmost-longest match that `Regex` returns.

**Why it happens:** Three distinct semantic differences between AhoCorasick and Regex:

1. **Match reporting order:** AhoCorasick `Standard` mode reports matches "as they are seen" during automaton traversal. If pattern "Mod" and pattern "ModManager" are both in the automaton and the text contains "ModManager", `Standard` mode will report "Mod" because it's found first during traversal. Regex with alternation `Mod|ModManager` (longest-first-sorted, as the current code does) would match "ModManager".

2. **Substring vs whole-pattern:** AhoCorasick matches anywhere within the haystack, like `str::contains()`. The current `detect_mods_important` code escapes its patterns with `regex::escape` and wraps in `(?i)`, effectively doing case-insensitive substring search. This IS equivalent to AhoCorasick with `ascii_case_insensitive(true)`, but ONLY if `MatchKind::LeftmostLongest` is used.

3. **Overlapping patterns:** If mod entries have patterns where one is a prefix/substring of another (e.g., "ENB" vs "ENBSeries"), AhoCorasick `Standard` will match "ENB" and skip "ENBSeries" at the same position. `LeftmostFirst` would also prefer "ENB" if it was added first. Only `LeftmostLongest` preserves the current regex behavior.

**Consequences:**
- Mods with shorter names that are prefixes of other mods get false-positive matches
- Mods with longer names that contain shorter mod names as prefixes get missed
- GPU-specific mod detection logic (`entry.gpu` checks) fires on wrong mods
- Results differ between pre-optimization and post-optimization code, breaking parity

**Prevention:**
1. **Use `MatchKind::LeftmostLongest`** when building the AhoCorasick automaton. This is the closest semantic equivalent to the current regex behavior.
2. **Use `ascii_case_insensitive(true)`** on the builder to match the current `(?i)` behavior.
3. **Sort patterns longest-first** before adding to the automaton, matching the existing `detect_mods_single` sort pattern.
4. **Write before/after parity tests:** Run both the regex path and the AhoCorasick path against the same input data and assert identical match sets before removing the regex path.
5. **Handle exclusions post-match:** The current per-entry loop checks `is_excluded()` before matching. With AhoCorasick, match all patterns first, then apply exclusion filtering. This changes the control flow and requires careful preservation of the `gpu_mismatch` / `gpu_matches_user` per-entry logic.

**Detection:**
- Before/after criterion benchmarks should include result comparison, not just timing
- Parity tests showing different mod detection results for the same input
- Existing test fixtures should be run against both paths

**Phase to address:** Performance optimization phase. Build AhoCorasick implementation alongside existing regex path, run parity tests, then swap.

**Sources:**
- [AhoCorasick MatchKind documentation](https://docs.rs/aho-corasick/latest/aho_corasick/enum.MatchKind.html)
- [Regex issue #891 - AhoCorasick for literal alternations](https://github.com/rust-lang/regex/issues/891)

---

### Pitfall 4: Replacing Unbounded DashMap Caches with LRU Introduces Performance Regression

**What goes wrong:** The project plan calls for adding LRU capacity eviction to `YAML_CACHE` (DashMap in `classic-yaml-core`), `SETTINGS_CACHE` (DashMap in `classic-settings-core`), and `HASH_CACHE` (DashMap in `classic-file-io-core`). Wrapping a DashMap in an LRU layer introduces lock contention on every access because LRU requires updating a doubly-linked list (reordering the accessed element to the front) on every GET, not just on INSERT.

**Why it happens:** DashMap uses shard-level locking -- concurrent reads to different shards don't contend. An LRU wrapper requires exclusive write access to the ordering structure on every read, converting all reads into writes from a concurrency perspective. The `lru` crate (already in the workspace at `0.16.3`) is single-threaded and requires an external mutex. The `quick_cache` crate (already in workspace at `0.6`, already used in `classic-file-io-core/src/core.rs`) is lock-free and concurrent.

**Consequences:**
- Batch scanning of 50+ crash logs (the primary use case) hits the cache on every mod detection call across all Rayon threads
- Single-mutex LRU becomes a serialization point for parallel scan operations
- Throughput regression on the hot path, potentially worse than the unbounded DashMap it replaces
- Under-sized LRU capacity causes cache thrashing: entries evicted and re-loaded in a tight loop

**Prevention:**
1. **Use `quick_cache::sync::Cache` instead of `lru` + `Mutex`/`DashMap`.** This is already a workspace dependency and already used in `classic-file-io-core` for file content caching. It provides lock-free concurrent LRU semantics without requiring an external mutex.
2. **Size caches based on measured workloads:** Instrument current cache sizes under real workloads before choosing capacity. The YAML cache typically holds 5-15 files; setting capacity to 32-64 is safe. The hash cache grows with scanned files; capacity should be at least 2x the typical scan batch size.
3. **Benchmark before and after with criterion:** The benchmark must use `detect_mods_batch` on a realistic number of crash logs to exercise concurrent cache access under contention.
4. **Keep `clear()` methods:** All three caches already expose `clear()` functions. The `quick_cache` `Cache` type supports `clear()`.
5. **Preserve `DashMap` iteration semantics:** `YAML_CACHE` has `get_yaml_cache_stats()` which iterates over entries to sum sizes. `quick_cache` does NOT support iteration. If stats collection is needed, track size metadata separately (e.g., an `AtomicUsize` incremented on insert, decremented on evict).

**Detection:**
- Criterion benchmarks showing throughput regression after cache replacement
- Higher lock contention in `perf` or `tokio-console` traces during batch scans
- Cache hit rate drops below 90% (indicates capacity too small)

**Phase to address:** Cache bounding phase. Benchmark first to establish baseline, then swap implementation.

---

## Moderate Pitfalls

Mistakes that cause delays, test failures, or subtle behavioral changes.

### Pitfall 5: `map_copy()` on Windows Doubles Memory Usage for Large Files

**What goes wrong:** Switching from `Mmap::map()` to `MmapOptions::new().map_copy()` in `read_file_mmap` (file-io-core/src/core.rs:1050) eliminates the TOCTOU issue but creates a copy-on-write mapping. On Windows, this means the OS allocates physical memory pages for the private copy as soon as ANY read triggers a page fault, because Windows' copy-on-write for file mappings backed by `PAGE_WRITECOPY` protection commits pages differently than Linux's lazy CoW.

**Why it happens:** `map_copy()` uses `PAGE_WRITECOPY` protection on Windows via `CreateFileMapping` + `MapViewOfFile`. While Linux lazily shares pages until a write occurs, Windows may commit pages to the page file immediately for CoW mappings. For read-only access (which is all `read_file_mmap` does), this is unnecessary overhead.

**Consequences:**
- Files >1MB (the mmap threshold) use roughly 2x the memory: one copy in the filesystem cache, one in the process's private page set
- For a batch scan of 50+ crash logs where some are multi-MB, this adds up
- Performance regression from additional page fault handling

**Prevention:**
1. **Use `map_copy_read_only()` instead of `map_copy()`.** This was added to `memmap2` to provide CoW semantics with read-only access -- the mapping is isolated from external changes but doesn't allocate private pages for writes (since writes are prohibited). This is the correct choice for a read-only scan path.
2. **Benchmark the three options:** `map()` (current, unsafe), `map_copy()` (CoW with write), `map_copy_read_only()` (CoW read-only). Criterion benchmark on a representative set of large crash log files.
3. **The function is already `async` and calls `File::open` synchronously.** Consider whether the sync `File::open` + mmap is actually better than `tokio::fs::read` for the file sizes involved (1-10MB). Profile both paths.

**Detection:**
- Working set memory increases after switching mmap strategy
- Criterion benchmarks show throughput regression on the `read_file_mmap` path
- Windows Task Manager shows higher "Commit charge" per scan process

**Phase to address:** Security/TOCTOU hardening phase.

**Sources:**
- [memmap2 MmapOptions documentation](https://docs.rs/memmap2/latest/memmap2/struct.MmapOptions.html)
- [Windows memory-mapped file IO behavior](https://www.jeremyong.com/winapi/io/2024/11/03/windows-memory-mapped-file-io/)

---

### Pitfall 6: Workspace Dependency Promotion Silently Enables Unwanted Features

**What goes wrong:** Promoting `winreg = "0.52"` and `phf = { version = "0.13.1", features = ["macros"] }` to `[workspace.dependencies]` can silently enable features in crates that did not previously use them, because Cargo's dependency resolver unifies features across the entire workspace.

**Why it happens:** Cargo follows an additive feature model. When `phf` is declared at the workspace level with `features = ["macros"]`, every crate that depends on `phf` (even if only one today) gets the `macros` feature. If a second crate later adds `phf` without `features = ["macros"]`, it still gets `macros` because the workspace-level declaration includes it. The inverse problem is worse: if the workspace declares `phf` WITHOUT `macros`, but `classic-constants-core` needs `macros`, the crate must add `features = ["macros"]` to its local `{ workspace = true }` declaration -- and this is easy to forget, causing a build failure.

**Consequences:**
- Build failures when a crate needs a feature the workspace didn't declare
- Unnecessary compile-time dependencies (PHF macros trigger proc-macro compilation in crates that don't use compile-time maps)
- For `winreg`: Windows-only dependency leaks into cross-compilation targets unless properly gated with `[target.'cfg(windows)'.dependencies]`

**Prevention:**
1. **Declare workspace deps with the minimal feature set.** Add features at the crate level: `phf = { workspace = true, features = ["macros"] }` in `classic-constants-core`.
2. **Gate `winreg` on Windows target** at the workspace level: `[workspace.dependencies] winreg = { version = "0.52", ... }` AND at the crate level: `[target.'cfg(windows)'.dependencies] winreg = { workspace = true }`.
3. **Test cross-compilation** (even if not targeting Linux in production) to catch accidental Windows-only dependency leaks.
4. **Check the default-features interaction:** Known Cargo issue [#12162](https://github.com/rust-lang/cargo/issues/12162) -- if the workspace sets `default-features = false`, individual crates cannot re-enable default features easily. For `winreg` and `phf`, keep `default-features = true` at the workspace level.

**Detection:**
- `cargo build` succeeds but `cargo build --target x86_64-unknown-linux-gnu` fails (if ever attempted)
- Feature unification warnings in `cargo tree -e features`
- Build time increases from proc-macro compilation in crates that don't need it

**Phase to address:** Dependency management phase. Small and mechanical, but verify with `cargo tree` after promotion.

**Sources:**
- [Cargo workspace dependencies and default-features issue](https://github.com/rust-lang/cargo/issues/12162)
- [Cargo features documentation](https://doc.rust-lang.org/cargo/reference/features.html)

---

### Pitfall 7: Criterion Benchmarks Measure Wrong Thing Due to Optimizer Elision

**What goes wrong:** Adding criterion benchmarks for `detect_mods_important`, `detect_mods_single`, and `detect_mods_batch` shows unrealistically fast times because LLVM optimizes away the computation. The benchmark calls a function, discards the result, and the optimizer removes the entire call chain.

**Why it happens:** Criterion uses `iter()` which takes a closure. If the closure's return value is never used (or if the inputs are compile-time constants), LLVM's optimization passes can eliminate the computation entirely. This is especially likely for:
- Functions that return `Vec<String>` where the Vec is immediately dropped
- Functions where inputs don't change between iterations (constant folding)
- Functions with no observable side effects

**Consequences:**
- Benchmarks show sub-microsecond times for operations that actually take milliseconds
- Before/after comparisons are meaningless
- Decisions based on benchmark data lead to wrong optimization choices
- Benchmark results don't reproduce in real workloads

**Prevention:**
1. **Use `criterion::black_box()` on ALL inputs AND outputs.** Both matter. Inputs prevent constant folding; output prevents dead code elimination.
   ```rust
   b.iter(|| {
       let result = detect_mods_important(
           black_box(&entries),
           black_box(&plugins),
           black_box(Some("NVIDIA")),
           black_box(&modules),
       );
       black_box(result)
   })
   ```
2. **Use `iter_batched()` for setup-heavy benchmarks.** When testing regex/AhoCorasick compilation separately from matching, use `iter_batched` with `BatchSize::SmallInput` to separate setup from the measured operation.
3. **Disable quick-mode:** Never run criterion with `--quick`. Quick mode reduces sample size and skips warm-up, making benchmarks susceptible to frequency scaling, thermal throttling, and context switches.
4. **Pin CPU frequency** on the benchmark machine (Windows: set power plan to "High Performance"). Turbo boost causes variance between runs.
5. **Verify benchmarks are measuring what you think:** Add an assertion inside the benchmark closure (only during development) to confirm the result is non-empty. Remove the assertion for actual timing runs.
6. **Note version inconsistency:** The workspace declares `criterion` at multiple versions -- `classic-scanlog-core` uses `criterion 0.6.0` in dev-dependencies while the stack analysis mentions `0.5/0.6/0.8`. Standardize on one version across all benchmark targets.

**Detection:**
- Benchmark shows <1us for a function that processes 100+ regex patterns against thousands of strings
- "Performance improved by 99%" without code changes between runs (optimizer behavior changed)
- Results don't match wall-clock profiling with `cargo flamegraph`

**Phase to address:** Performance benchmarking phase. Set up the benchmark harness correctly before measuring any optimizations.

**Sources:**
- [Criterion FAQ - optimizer issues](https://bheisler.github.io/criterion.rs/book/faq.html)
- [Criterion unstable benchmarks issue #485](https://github.com/bheisler/criterion.rs/issues/485)

---

### Pitfall 8: Test Isolation Breaks When Refactoring Global Singletons

**What goes wrong:** The codebase has multiple global singletons: `GLOBAL_FCX_HANDLER` (parking_lot Mutex), `YAML_CACHE` (DashMap via Lazy), `SETTINGS_CACHE` (DashMap via Lazy), `HASH_CACHE` (DashMap via LazyLock), and `VersionRegistry` (OnceLock). Refactoring any of these (e.g., replacing DashMap with quick_cache, changing the lock type on FCX handler) can break test isolation because Rust tests run in parallel within a single process by default.

**Why it happens:** `cargo test` runs all `#[test]` functions in the same binary as parallel threads. Global statics are shared across all tests. If test A populates `YAML_CACHE` and test B expects it empty, B fails non-deterministically based on execution order. The existing code already handles this with `YAML_CACHE.clear()` calls in test setup (e.g., `classic-yaml-core/src/lib.rs:1490`), but refactoring the cache type can break these clear patterns.

**Consequences:**
- Tests pass when run individually (`cargo test -- test_name`) but fail when run together (`cargo test`)
- Non-deterministic CI failures ("it worked on my machine")
- Replacing DashMap with quick_cache breaks existing `.clear()` and `.contains_key()` calls in tests because the APIs differ
- OnceLock-based singletons (VersionRegistry) CANNOT be reset at all -- tests must accept the first-initialized value

**Prevention:**
1. **Preserve the test-clearing API.** When replacing cache implementations, ensure `clear()` remains available with identical semantics. `quick_cache::sync::Cache` has `.clear()`, so this works. But `quick_cache` does NOT have `.contains_key()` -- tests using `YAML_CACHE.contains_key(...)` assertions must be rewritten.
2. **Run tests with `-- --test-threads=1`** as a validation step after global state refactoring to confirm no ordering dependency.
3. **Add `#[cfg(test)] pub fn reset_for_tests()` methods** to global singleton wrappers so test cleanup is explicit and maintained.
4. **Do not attempt to make VersionRegistry resettable.** The PROJECT.md explicitly marks this as out of scope ("OnceLock design is intentional; process-restart isolation is acceptable").
5. **For FCX handler refactoring:** If changing from `try_lock()` to `lock()`, ensure the test that holds the mutex during contention testing doesn't deadlock the entire test suite.

**Detection:**
- `cargo test` passes locally but fails in CI (different thread scheduling)
- Tests that previously passed start failing after cache refactoring
- Deadlock in test suite (no output, process hangs) after changing lock types

**Phase to address:** Every phase that touches global state. Add singleton reset-for-tests methods early.

---

### Pitfall 9: Workspace Lint Configuration Is Not Inherited

**What goes wrong:** The workspace `Cargo.toml` defines `[workspace.lints.rust]` with `deprecated = "deny"` and `unused = "deny"`, but NO crate in the workspace has `[lints] workspace = true`. Each crate that uses lints defines its own `[lints.rust]` section (e.g., `classic-scanlog-core/Cargo.toml:84`). Adding a new crate or modifying lint policies at the workspace level has no effect.

**Why it happens:** Cargo requires crates to opt-in to workspace lint inheritance with `[lints] workspace = true`. Simply defining `[workspace.lints]` does not propagate. The workspace and crate definitions are currently independent, and they happen to match only because they were manually synchronized.

**Consequences:**
- Changing the workspace lint level (e.g., upgrading `missing_docs` from "warn" to "deny") does nothing
- New crates added to the workspace get Rust's defaults unless they copy the lint section
- Inconsistent lint enforcement across crates -- some may be stricter than others
- The workspace lint section gives a false sense of centralized control

**Prevention:**
1. **If centralizing lints is desired:** Add `[lints] workspace = true` to every crate's `Cargo.toml` and remove crate-local `[lints.rust]` sections. But be aware this is a significant change -- some crates have stricter lints (like `unsafe_code = "deny"`) that would need to be either promoted to workspace level or kept as crate-level overrides.
2. **If keeping per-crate lints:** Document that `[workspace.lints]` is NOT the source of truth and that lint policy lives in each crate. Consider removing the workspace lint section to avoid confusion.
3. **Either way, do not assume workspace lints are enforced.** Verify by checking each crate's `Cargo.toml`.

**Detection:**
- `cargo clippy` passes despite workspace-level lint changes
- New crate has no lint section and compiles with default (lenient) lints
- grep for `[lints.rust]` or `[lints] workspace` across Cargo.toml files

**Phase to address:** Dependency/workspace management phase. Decide on lint strategy and execute uniformly.

---

## Minor Pitfalls

Mistakes that cause annoyance, confusion, or wasted time but are recoverable.

### Pitfall 10: Cached LogParser in C++ Bridge Creates Thread-Safety Concern

**What goes wrong:** Replacing per-call `LogParser::new(None)` in `detect_crash_pattern` (scanner.rs:671) with a `Lazy<LogParser>` or `LazyLock<LogParser>` at module level introduces a shared mutable state concern. `LogParser` has a `PatternCache` (DashMap) that is populated during matching. If `detect_crash_pattern` is called from multiple threads via the C++ bridge (which is possible during batch scans), the shared `LogParser` instance must be confirmed thread-safe.

**Why it happens:** The fix seems obvious ("just cache it!") but `LogParser` may hold state that changes during parsing. The `PatternCache` inside it uses DashMap, which IS thread-safe, but `add_pattern` modifications to the pattern set during concurrent reads could produce inconsistent results.

**Prevention:**
1. **Verify `LogParser` is `Send + Sync` at compile time:** Add a static assertion `const _: () = { fn assert_send_sync<T: Send + Sync>() {} assert_send_sync::<LogParser>(); };`
2. **Do not allow pattern mutation after initialization.** The cached parser should be initialized once with the full pattern set and never modified.
3. **Prefer `LazyLock<LogParser>` over `Lazy<Mutex<LogParser>>`.** If the parser is truly read-only after initialization, no mutex is needed.

**Detection:**
- Data races or inconsistent match results under high concurrency
- Miri or thread sanitizer detects concurrent access violations
- Batch scans return different results than single scans

**Phase to address:** Performance optimization phase, specifically the C++ bridge parser caching work.

---

### Pitfall 11: `detect_mods_important` Refactoring Loses Per-Entry Exclusion Logic

**What goes wrong:** Converting the per-entry loop in `detect_mods_important` to a bulk AhoCorasick match loses the ability to check `is_excluded()` and per-entry `gpu` fields BEFORE deciding whether a match matters. The current control flow is: for each entry, check exclusion, THEN match. A bulk AhoCorasick approach matches everything first, then must retroactively apply exclusion and GPU logic.

**Why it happens:** AhoCorasick finds ALL pattern matches in a single pass over the haystack. There's no way to "skip" certain patterns during the search based on external state (like exclusion lists or GPU presence).

**Prevention:**
1. **Two-phase approach:** Run AhoCorasick to get all raw matches, then filter matches through the per-entry exclusion and GPU logic in a second pass.
2. **Map AhoCorasick match IDs back to entries:** Use `PatternID` from AhoCorasick matches to index back into the entries slice, retrieving the associated `exclude_when`, `gpu`, `name`, and `description` fields.
3. **Preserve the "entry not found" branch:** The current code emits "not installed" messages for entries where the GPU matches but the mod wasn't found. This negative-result logic must survive the refactoring.

**Detection:**
- Missing "not installed" messages for expected-but-absent mods
- GPU mismatch warnings no longer appearing
- Exclusion logic no longer filtering results

**Phase to address:** Performance optimization phase, alongside Pitfall 3 (AhoCorasick semantics).

---

### Pitfall 12: `zerovec` Workaround Breaks Silently on Slint Upgrade

**What goes wrong:** `classic-shared-core` has a dev-dependency `zerovec = { version = "0.11", features = ["alloc"] }` documented as a workaround for Slint's transitive `icu_properties` dependency. Upgrading Slint from 1.15.0 to a newer version may change the `icu_properties` version, which may change the `zerovec` version requirement, breaking the workaround.

**Why it happens:** The workaround pins a specific `zerovec` version. Slint's dependency chain is: `slint -> icu_properties -> zerovec`. If Slint upgrades `icu_properties`, which upgrades `zerovec` to 0.12+, the pinned `0.11` dev-dependency conflicts.

**Prevention:**
1. **Add a CI check** that builds `classic-shared-core` with the `gui-bridge` feature in isolation and fails with a clear message if the zerovec workaround is stale.
2. **Add a `# FIXME` comment** in the Cargo.toml referencing the upstream Slint issue number so it's findable by grep.
3. **Test the `gui-bridge` feature specifically** after any Slint version bump.

**Detection:**
- Build fails with zerovec version conflict after Slint upgrade
- Feature-gated `gui-bridge` build fails in CI while default build succeeds

**Phase to address:** Dependency management phase.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Severity | Mitigation |
|---|---|---|---|
| Deprecated API removal | Silent FFI consumer breakage (#1) | CRITICAL | Binding-side deprecation warnings first, two-phase removal |
| FCX state hardening | Silent no-op reset under contention (#2) | CRITICAL | Replace `try_lock()` with timeout-based lock, return Result |
| AhoCorasick optimization | Semantic mismatch with regex (#3) | CRITICAL | Use `LeftmostLongest` match kind, parity tests |
| Cache bounding (LRU) | Throughput regression from lock contention (#4) | HIGH | Use `quick_cache` (already in workspace), not `lru` + Mutex |
| mmap TOCTOU fix | Memory doubling on Windows (#5) | MODERATE | Use `map_copy_read_only()`, benchmark three strategies |
| Workspace dep promotion | Feature flag unification (#6) | MODERATE | Declare minimal features at workspace, add at crate level |
| Criterion benchmarks | Optimizer elision, meaningless numbers (#7) | MODERATE | `black_box()` all inputs/outputs, disable quick mode |
| Global state refactoring | Test isolation breakage (#8) | MODERATE | Preserve clear() API, add reset_for_tests() methods |
| Workspace lints | Not actually inherited (#9) | LOW | Decide: centralize with `workspace = true` or document per-crate policy |
| Bridge parser caching | Thread safety of shared LogParser (#10) | LOW | Static Send+Sync assertion, read-only after init |
| AhoCorasick refactoring | Lost exclusion/GPU logic (#11) | MODERATE | Two-phase match-then-filter, preserve negative-result branches |
| Slint dep workaround | Breaks on Slint upgrade (#12) | LOW | CI feature-gate check, FIXME comment |

## CLASSIC-Specific Considerations

Given this codebase's architecture, several pitfalls compound:

1. **Three binding surfaces multiply API removal risk.** A deprecated method in core must be checked against C++ bridge (CXX), Python (PyO3), and Node (NAPI-RS) consumers. Each binding framework has different deprecation signaling mechanisms. CXX has none. PyO3 can emit Python `DeprecationWarning`. NAPI-RS can mark TypeScript declarations with `@deprecated` JSDoc.

2. **Parallel scan architecture magnifies cache contention.** `detect_mods_batch` uses `par_iter()` across crash logs. Every cache access inside the parallel closure is a potential contention point. Replacing DashMap (sharded locks, read-friendly) with anything that requires write locks on read (standard LRU) will serialize the parallel scan path.

3. **The `deprecated = "deny"` lint in crate-local `[lints.rust]` means you cannot add `#[deprecated]` annotations to existing code AND keep it compiling in the same commit.** The workflow must be: (a) add the deprecated annotation, (b) in the SAME commit, update all callers in that crate, (c) in a LATER commit, update callers in other crates. Or temporarily change `deprecated = "deny"` to `deprecated = "warn"`.

4. **The "parity gate" tooling is your safety net.** Both `check_parity_gate.py` (Python) and `parity:gate:local` (Node) compare binding surfaces against core API shapes. Run these AFTER every binding-touching change. They catch function signature changes but NOT behavioral regressions (semantic parity).

5. **Windows-primary development means Windows-specific mmap/memory behavior is the default case**, not an edge case. All benchmarks and memory measurements should be done on Windows, not Linux/macOS.

## Sources

### Official Documentation (HIGH confidence)
- [AhoCorasick MatchKind](https://docs.rs/aho-corasick/latest/aho_corasick/enum.MatchKind.html) -- match semantic differences
- [memmap2 MmapOptions](https://docs.rs/memmap2/latest/memmap2/struct.MmapOptions.html) -- map vs map_copy vs map_copy_read_only
- [Cargo Features](https://doc.rust-lang.org/cargo/reference/features.html) -- additive feature model
- [Criterion FAQ](https://bheisler.github.io/criterion.rs/book/faq.html) -- optimizer elision, black_box

### GitHub Issues (MEDIUM confidence)
- [Cargo #12162 - workspace deps and default-features](https://github.com/rust-lang/cargo/issues/12162)
- [Criterion #485 - unstable benchmarks](https://github.com/bheisler/criterion.rs/issues/485)
- [Regex #891 - AhoCorasick for literal alternations](https://github.com/rust-lang/regex/issues/891)

### Codebase Source (HIGH confidence)
- `classic-scanlog-core/src/fcx_handler.rs:295-298` -- try_lock silent drop
- `classic-scanlog-core/src/mod_detector.rs:524` -- per-entry regex compilation
- `classic-file-io-core/src/core.rs:1050` -- unsafe Mmap::map
- `classic-yaml-core/src/lib.rs:156` -- unbounded YAML_CACHE DashMap
- `classic-settings-core/src/cache.rs:18` -- unbounded SETTINGS_CACHE DashMap
- `classic-file-io-core/src/hash.rs:51` -- unbounded HASH_CACHE DashMap
- `classic-scanlog-py/src/parser.rs:98` -- #[allow(deprecated)] on FFI boundary
- `ClassicLib-rs/Cargo.toml:187-189` -- workspace lints not inherited by any crate

---

*Pitfalls research: 2026-04-04*
