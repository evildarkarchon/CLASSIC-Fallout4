# Project Research Summary

**Project:** CLASSIC Codebase Health Milestone
**Domain:** Rust workspace cleanup — dead code, deprecated APIs, global state, cache bounding, pattern optimization, binding parity
**Researched:** 2026-04-04
**Confidence:** HIGH

## Executive Summary

This milestone is a pure engineering-health effort across CLASSIC's 19 business-logic crates and three binding surfaces (CXX, PyO3, NAPI-RS). It resolves every open finding from the codebase audit: four dead-code items, three deprecated APIs with binding-surface callers still present, one correctness bug in FCX global state reset, three unbounded global caches, one TOCTOU-unsafe mmap path, per-call regex and LogParser allocation in hot paths, and scattered workspace housekeeping gaps. None of the changes are user-facing. The codebase already contains all the patterns and dependencies needed to execute — `quick_cache` is already in the workspace and used in `classic-file-io-core`, AhoCorasick is already used in multiple scanlog modules, and `parking_lot::Mutex` is already the lock type for FCX state. The work is applying established patterns to the remaining outliers, not introducing new dependencies or new architecture.

The recommended execution order, based on feature dependencies, is: (1) deprecated API migration with binding-surface deprecation warnings first (unblocks dead code removal), (2) dead code removal, (3) FCX state hardening with binding exposure, then in parallel (4) bounded cache replacement, (5) regex and LogParser pattern caching with benchmarks, and (6) mmap TOCTOU fix. Housekeeping items (workspace dep promotion, Proton path wiring, test gap fills, documentation) can be slotted in at any point. The Python FormID deprecation warning is fully independent.

The primary risks are all semantic-correctness risks, not complexity risks. Removing deprecated core APIs before migrating FFI consumers silently breaks Python and Node bindings with no warning. Replacing per-entry `Regex::new` with AhoCorasick without using `LeftmostLongest` match kind changes which mods are detected. Replacing `DashMap` caches with anything requiring write locks on read would serialize the parallel `par_iter()` scan path. All three risks are well-understood and have clear, documented mitigations.

**Note on STACK.md scope:** The STACK.md produced during this research covers the *Slint GUI milestone* (replacing the Python/PySide6 GUI with a native Rust/Slint frontend), not this health milestone. Its recommendations (Slint 1.15.0, `pulldown-cmark`, `slint-build`, Skia renderer) are out of scope here. The stack for this health milestone is fully satisfied by existing workspace dependencies. The zerovec workaround item (TS-12) is the only stack-adjacent task — it should be checked against Slint 1.15.0 since the workaround may already be resolved.

---

## Key Findings

### Recommended Stack

No new crate dependencies are required. All tools needed are already in the workspace:

**Existing workspace crates to apply:**
- `quick_cache 0.6` — bounded concurrent LRU cache; already used in `classic-file-io-core`; lock-free concurrent reads, no mutex on read path
- `aho-corasick` — multi-pattern literal matching; already used in `record_scanner.rs`, `patterns.rs`, `plugin_analyzer.rs`
- `parking_lot::Mutex` — non-poisoning blocking mutex; already the lock type in `fcx_handler.rs`
- `xxhash-rust` — fast hash for cache keying (mod list hash); already a workspace dependency
- `criterion 0.6` — benchmark harness; already a dev-dependency with harness in `classic-scanlog-core/benches/`
- `memmap2` — `MmapOptions::map_copy_read_only()` is the correct mmap fix; already a dependency

**Two mechanical workspace changes needed:**
- Promote `winreg = "0.52"` and `phf = "0.13.1"` to `[workspace.dependencies]`
- Gate `winreg` on `[target.'cfg(windows)'.dependencies]` at crate level

### Expected Features

All 14 table-stakes features (TS-1 through TS-14) are audit-driven and required to close the milestone. All 4 researchers converge on the same priorities and implementation approach.

**Must have (table stakes — all 14 are required):**
- TS-1: Remove 4 `#[allow(dead_code)]` items (`SEGMENT_BOUNDARIES`, `YamlFormatConfig`, `PluginAnalyzer.case_cache`, `PyGpuDetector.inner`) — all crate-internal, safe to delete
- TS-2: Migrate all callers off `parse_segments_parallel`, `is_outdated`, and legacy `generate_suspect_section`; delete deprecated methods — must precede TS-1
- TS-3: Eliminate `scan_all_settings_legacy_bucketed` code path in `SettingsValidator`
- TS-4: Add `DeprecationWarning` via `PyErr::warn` when `PyFormIDAnalyzerCore::new` receives legacy `PyDict` format — warning only, legacy path not removed
- TS-5: Fix `GLOBAL_FCX_HANDLER.reset_global_state()` `try_lock` silent drop; expose reset in C++ bridge and Node bindings
- TS-6: Replace `YAML_CACHE`, `SETTINGS_CACHE`, `HASH_CACHE` unbounded `DashMap` instances with `quick_cache::sync::Cache` (capacities: 256, 128, 1024)
- TS-7: Switch `read_file_mmap` from `Mmap::map()` to `MmapOptions::map_copy_read_only()` (NOT `map_copy()` — see pitfalls)
- TS-8: Cache compiled regex/AhoCorasick in mod detector hot paths; cache `LogParser` as `Lazy<LogParser>` in C++ bridge and Node binding
- TS-9: Promote `winreg` and `phf` to workspace-level dependencies
- TS-10: Wire `construct_proton_docs_path` into Linux docs-path discovery flow
- TS-11: Add tests for FCX contention reset, legacy settings path assertion, Linux Proton path, Node FCX state carryover, C++ bridge parser allocation regression
- TS-12: Document or resolve the `zerovec` workaround dev-dependency in `classic-shared-core`
- TS-13: Commit generated `index.d.ts` snapshot with CI freshness check for Node bindings
- TS-14: Add criterion benchmarks proving each performance improvement (caches, mod detector, mmap)

**Should have (differentiators, not audit-driven):**
- D-1: Replace `once_cell::sync::Lazy` with `std::sync::LazyLock` for consistency — codebase is currently mixed; new cache code should use `LazyLock`
- D-2: Return `Result<(), FcxResetError>` from `reset_global_state()` for observable failure signaling
- D-3: Expose unified `CacheStats` struct across all three bounded caches

**Defer to later milestones:**
- D-5 (TUI dep workspace promotion) — explicitly out of scope per PROJECT.md
- All Slint GUI features (STACK.md scope) — separate milestone
- Python FormID legacy path removal — warning added now, removal is a future milestone
- VersionRegistry OnceLock redesign — explicitly out of scope

### Architecture Approach

The changes span five concern areas across four architectural layers. A critical cross-cutter finding from all three non-STACK researchers: **every change is internally contained and public APIs do not change.** The three unbounded cache replacements follow identical patterns. The AhoCorasick integration follows the exact pattern already used in `record_scanner.rs`. The FCX fix is a one-line change, followed by mechanical binding exposure using `papyrus_reset` as the CXX pattern template.

**Three independent workstreams (can parallelize once deprecated API migration completes):**

- **Workstream A — Bounded Caches:** `classic-yaml-core` YAML_CACHE, `classic-settings-core` SETTINGS_CACHE, `classic-file-io-core` HASH_CACHE. Replace `Lazy<DashMap>` with `LazyLock<Cache<K,V>>`. Preserve `clear()` and `cache_stats()` APIs. Track size metadata with atomic counters since `quick_cache` does not support iteration.

- **Workstream B — Pattern Caching:** `detect_mods_important` AhoCorasick automaton cached by xxhash of entry detect strings (capacity 8); `detect_mods_single/double/batch` regex cached by mod list hash; `Lazy<LogParser>` in C++ bridge `scanner.rs` and Node binding `scanlog.rs`. Function signatures unchanged.

- **Workstream C — FCX State:** `try_lock()` to `lock()` in `fcx_handler.rs` (one line); add `fn fcx_reset_global_state()` to CXX bridge `extern "Rust"` block; add `#[napi] fn reset_fcx_global_state()` and `get_fcx_config_issues()` to Node binding.

**Key architectural consensus across all researchers:** Use `quick_cache::sync::Cache` exclusively for new bounded caches — not `lru + Mutex`, not `DashMap + manual eviction`. The parallel `par_iter()` scan path in `detect_mods_batch` makes write-lock-on-read caches a correctness regression. `quick_cache` is the only workspace option with lock-free concurrent reads.

### Critical Pitfalls

1. **Silent FFI consumer breakage when removing deprecated APIs** — The Python binding at `classic-scanlog-py/src/parser.rs:98` calls `parse_segments_parallel` with `#[allow(deprecated)]`; removing the core method breaks the Python API with no prior deprecation warning to Python callers. CXX consumers have no visibility into Rust deprecation metadata at all. Prevention: two-phase removal — migrate binding internals and emit `DeprecationWarning` at binding surface first; delete core method only after all `#[allow(deprecated)]` guards are gone (currently 7 sites across the workspace).

2. **FCX reset silent no-op under contention** — `try_lock()` in `reset_global_state()` silently skips the reset if any thread holds the mutex. Neither the C++ bridge nor Node bindings call reset at all, so every multi-scan session in those surfaces accumulates stale FCX state. This is a correctness bug: users see detected issues from prior scans in current results. Prevention: blocking `lock()` (non-poisoning in `parking_lot`); explicit reset calls added to all scan entry points.

3. **AhoCorasick match semantics differ from Regex** — Default `MatchKind::Standard` reports first match during automaton traversal, not leftmost-longest. A pattern "ENB" will match before "ENBSeries" at the same position, changing detection results relative to the current regex behavior. Prevention: use `AhoCorasickBuilder::new().ascii_case_insensitive(true).match_kind(MatchKind::LeftmostLongest)`; sort patterns longest-first; run before/after parity tests against known fixtures before removing the regex path.

4. **Cache replacement with `lru + Mutex` causes throughput regression** — `lru::LruCache` requires a write lock on every read to update ordering. This serializes `par_iter()` scan workers on a single mutex. Prevention: use `quick_cache::sync::Cache` exclusively — already proven in `classic-file-io-core`, lock-free concurrent reads, built-in LRU eviction.

5. **mmap `map_copy()` doubles memory on Windows** — `map_copy()` uses `PAGE_WRITECOPY` and Windows commits private pages immediately even for read-only access. Prevention: use `map_copy_read_only()` specifically; benchmark all three strategies (map, map_copy, map_copy_read_only) on Windows before committing.

---

## Implications for Roadmap

The feature dependency graph from FEATURES.md drives the phase order directly. TS-2 must precede TS-1. The FCX core fix must precede binding exposure. All three workstreams (A, B, C) are independent of each other and can parallelize after Phase 1.

### Phase 1: Deprecated API Migration and Dead Code Removal

**Rationale:** TS-2 blocks TS-1. The `deprecated = "deny"` lint means adding `#[deprecated]` annotations and migrating callers must be carefully sequenced. Clearing the deprecated API surface early reduces the blast radius for all subsequent changes and confirms the parity gates work correctly before any behavioral changes land.

**Delivers:** All deprecated methods removed (`parse_segments_parallel`, `is_outdated`, legacy `generate_suspect_section`), all 7 `#[allow(deprecated)]` guards gone, 4 dead-code items deleted, Python parity surface updated and parity gate passing.

**Addresses:** TS-1, TS-2

**Avoids:** Pitfall 1 (silent FFI consumer breakage) — binding callers migrated and binding-surface warnings emitted before any core method is deleted

**Implementation note:** The `deprecated = "deny"` lint requires a careful sequence within this phase: (a) temporarily relax lint to `warn`, (b) add `#[deprecated]`, (c) migrate all callers in the crate, (d) migrate PyO3/NAPI callers and emit binding-surface deprecation warnings, (e) delete the deprecated method, (f) restore `deprecated = "deny"`. Run parity gates after each binding migration.

---

### Phase 2: FCX Global State Hardening

**Rationale:** Correctness bug — stale state between scan sessions produces wrong user-visible results in multi-scan scenarios. This is the highest-priority behavioral fix. Independent of Phase 1 in terms of code but benefits from Phase 1 reducing noise.

**Delivers:** `reset_global_state()` is blocking (`lock()` instead of `try_lock()`); C++ bridge exposes `fcx_reset_global_state()` in `extern "Rust"` block; Node binding exposes `resetFcxGlobalState()` and `getFcxConfigIssues()`; all scan entry points call reset before session start; FCX contention test and Node FCX state carryover test added.

**Addresses:** TS-5, partial TS-11 (FCX contention test, Node FCX state carryover test)

**Avoids:** Pitfall 2 (silent no-op reset), Pitfall 10 (LogParser thread-safety — verify `Send + Sync` with static assertion before caching)

---

### Phase 3: Bounded Cache Replacement (Workstream A)

**Rationale:** Memory safety for long-running processes. Independent of Phases 1 and 2. Can begin in parallel with Phase 2. The three caches follow identical replacement patterns — `classic-yaml-core` YAML_CACHE establishes the template for `classic-settings-core` and `classic-file-io-core`.

**Delivers:** `YAML_CACHE` (cap 256), `SETTINGS_CACHE` (cap 128), `HASH_CACHE` (cap 1024) replaced with `quick_cache::sync::Cache`; `clear()` and `cache_stats()` APIs preserved; size metadata tracked via atomic counters; `reset_for_tests()` methods added to prevent test isolation breakage; before/after criterion benchmarks.

**Addresses:** TS-6, partial TS-11 (test isolation), partial TS-14 (cache benchmarks)

**Avoids:** Pitfall 4 (throughput regression from `lru + Mutex`) — `quick_cache` only; Pitfall 8 (test isolation breakage) — `clear()` preserved, `reset_for_tests()` added; note that `quick_cache` does NOT support `.contains_key()` or iteration — tests using `YAML_CACHE.contains_key()` assertions must be rewritten

---

### Phase 4: Pattern Caching and Performance Optimization (Workstream B)

**Rationale:** Highest performance impact. AhoCorasick parity validation is the gating risk — benchmarks must include result comparison, not just timing. Set up criterion correctly before measuring.

**Delivers:** `detect_mods_important` uses AhoCorasick with `LeftmostLongest` (or `str::contains` for purely escaped literal patterns — verify which paths are literal-only); `detect_mods_single/double/batch` cache compiled regex keyed by xxhash of mod list; `Lazy<LogParser>` in C++ bridge `scanner.rs` and Node `scanlog.rs`; before/after criterion benchmarks with `black_box()` on all inputs and outputs.

**Addresses:** TS-8, partial TS-14 (pattern and bridge benchmarks)

**Avoids:** Pitfall 3 (AhoCorasick semantic mismatch) — `LeftmostLongest` + longest-first sort + parity tests before removing regex path; Pitfall 7 (optimizer elision in benchmarks) — `black_box()` all inputs and outputs; Pitfall 11 (lost per-entry exclusion logic) — two-phase match-then-filter using `match.pattern().as_usize()` to index back into entries slice

---

### Phase 5: mmap TOCTOU Fix

**Rationale:** Low-complexity, high-safety-value, but has a Windows-specific pitfall (`map_copy()` vs `map_copy_read_only()`) that makes it worth isolating for explicit benchmarking.

**Delivers:** `read_file_mmap` uses `map_copy_read_only()`; before/after memory and throughput benchmarks on Windows for all three mmap strategies.

**Addresses:** TS-7, partial TS-14 (mmap benchmarks)

**Avoids:** Pitfall 5 (Windows memory doubling) — `map_copy_read_only()` specifically, benchmarked on Windows

---

### Phase 6: Python FormID Deprecation Warning

**Rationale:** Fully independent, lowest risk item. Separated to prevent it from being absorbed and forgotten in a larger phase.

**Delivers:** `PyFormIDAnalyzerCore::new` emits `PyErr::warn(py, PyDeprecationWarning, "...")` when receiving legacy `PyDict` format. Legacy conversion path NOT removed.

**Addresses:** TS-4

**Avoids:** Anti-Feature AF-2 (do not remove Python FormID legacy map path in this milestone)

---

### Phase 7: Workspace Housekeeping

**Rationale:** Low-risk, low-complexity. Does not block any other phase. Groups the remaining independent audit items.

**Delivers:**
- `winreg` and `phf` promoted to `[workspace.dependencies]` with `winreg` gated on `cfg(windows)` (TS-9)
- `construct_proton_docs_path` wired to Linux docs-path discovery, unit tested with mock Proton prefix (TS-10)
- `zerovec` workaround checked against Slint 1.15+ — documented or removed (TS-12)
- Node `index.d.ts` committed as snapshot with CI freshness check (TS-13)
- Workspace lint centralization decision made and implemented or documented (Pitfall 9)

**Addresses:** TS-9, TS-10, TS-12, TS-13

**Avoids:** Pitfall 6 (workspace dep feature unification) — minimal features at workspace level, additive features at crate level; Pitfall 9 (workspace lints not inherited) — explicit decision, not silent assumption

---

### Phase 8: Test Gap Fill and Final Validation

**Rationale:** Validates that all fixes actually work under the conditions that originally exposed the bugs. Consolidates remaining test gaps and runs full parity gate suite.

**Delivers:** Full TS-11 test coverage (legacy settings path assertion, Linux Proton path discovery mock test, remaining contention tests); full Python and Node parity gate run; C++ bridge rebuild verification; criterion benchmark suite complete.

**Addresses:** TS-11 (remaining gaps), TS-14 (complete benchmark suite), full audit closure

---

### Phase Ordering Rationale

- TS-2 must precede TS-1 — deprecated API shims reference patterns that dead code depends on; the `deprecated = "deny"` lint prevents safe concurrent migration.
- FCX core fix (Phase 2) must precede binding exposure — cannot expose a broken reset API to C++ and Node consumers.
- Workstreams A (caches), B (patterns), and C (FCX) are independent of each other; Phases 3-5 can parallelize after Phase 1.
- Benchmarks (TS-14) are exit criteria for their respective phases, not a standalone final phase.
- Housekeeping (Phase 7) does not block any other phase and can be done in parallel with anything.

### Research Flags

**Phases needing closer attention during implementation:**

- **Phase 1 (Deprecated API Migration):** The `deprecated = "deny"` lint sequencing is subtle. The Python binding `generate_suspect_section` legacy path (`report.rs:307`) exposes `is_outdated` equivalent behavior without its own deprecation annotation — this indirect exposure must be traced before removing `is_outdated` from core.
- **Phase 4 (Pattern Optimization):** AhoCorasick semantic parity against the current regex behavior must be verified against concrete test fixtures before the regex path is removed. Determine whether `detect_mods_important` patterns are purely escaped literals (use `str::contains`) or have any actual regex structure (use AhoCorasick) — research says escaped literals but implementation must confirm.
- **Phase 5 (mmap TOCTOU):** Windows behavior of `map_copy_read_only()` must be validated empirically on Windows, not inferred from Linux behavior. Benchmark required.

**Phases with standard, well-documented patterns:**

- **Phase 2 (FCX Hardening):** One-line core fix; bridge exposure mirrors `papyrus_reset` exactly.
- **Phase 3 (Cache Replacement):** Pattern proven in `classic-file-io-core`; three caches are mechanical repeats.
- **Phase 6 (Python FormID Warning):** Straightforward `PyErr::warn` PyO3 API.
- **Phase 7 (Housekeeping):** All items mechanical with no runtime behavior changes.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All dependencies verified in workspace; no new libraries needed; patterns verified in source |
| Features | HIGH | All 14 table-stakes items verified with exact file locations and line numbers in FEATURES.md |
| Architecture | HIGH | Direct source inspection of all affected files; all patterns already established in codebase |
| Pitfalls | HIGH | All critical pitfalls verified against source, official crate docs, and known Cargo/Windows behaviors |

**Overall confidence: HIGH**

All four research files converge on the same implementation approaches with no contradictions. The only MEDIUM-confidence item is TS-10 (Proton path integration point) where the exact integration call site needs exploration during implementation.

### Consensus Points Across Researchers

Strong agreement on these specific points (mentioned independently by multiple research tracks):

- `quick_cache` is the correct cache replacement — both FEATURES.md and ARCHITECTURE.md independently reach this conclusion; PITFALLS.md reinforces it by documenting the specific throughput regression from `lru + Mutex`
- AhoCorasick is already established in the codebase; the new use in `detect_mods_important` is an extension of an existing pattern, not a new dependency
- `deprecated = "deny"` lint ordering is a real constraint that must be planned for, not assumed away
- Criterion `black_box()` on both inputs and outputs is required — optimizer elision is a documented risk for these specific function shapes
- `map_copy_read_only()` not `map_copy()` — the distinction is Windows-specific and non-obvious

### Gaps to Address

- **Proton path integration point (TS-10):** Function exists and signature is known; the Linux docs-path discovery call site needs exploration during implementation. MEDIUM confidence.
- **zerovec workaround (TS-12):** Unknown whether Slint 1.15.0 (current workspace: 1.14.1) resolves the transitive `icu_properties` conflict. Check by upgrading Slint and running the `gui-bridge` feature build in isolation before deciding between documentation-only or actual removal.
- **D-1 (`once_cell` to `LazyLock`) scope:** If Phase 3 already uses `LazyLock` for new cache code, a targeted sweep of the three changed crates costs little additional effort. This could be folded into Phase 3 rather than deferred entirely.
- **Workspace lint centralization:** Decide before Phase 7 executes. The workspace `[workspace.lints]` section is currently not inherited by any crate — it gives false confidence. Either centralize with `workspace = true` in every crate's `Cargo.toml`, or remove the misleading workspace section and document per-crate policy.

---

## Sources

### Primary (HIGH confidence — official documentation)

- [memmap2 MmapOptions docs](https://docs.rs/memmap2/latest/memmap2/struct.MmapOptions.html) — `map_copy_read_only()` API, Windows `PAGE_WRITECOPY` behavior
- [AhoCorasick MatchKind docs](https://docs.rs/aho-corasick/latest/aho_corasick/enum.MatchKind.html) — `LeftmostLongest` semantics vs `Standard`
- [quick_cache docs](https://docs.rs/quick_cache/latest/quick_cache/) — lock-free concurrent cache API, no-iteration constraint
- [parking_lot Mutex docs](https://docs.rs/parking_lot/latest/parking_lot/type.Mutex.html) — non-poisoning blocking behavior
- [Criterion FAQ](https://bheisler.github.io/criterion.rs/book/faq.html) — optimizer elision, `black_box` usage requirements
- [Cargo Features docs](https://doc.rust-lang.org/cargo/reference/features.html) — additive feature model, workspace dep behavior

### Secondary (HIGH confidence — direct codebase inspection)

- `classic-scanlog-core/src/fcx_handler.rs:295-298` — `try_lock()` silent drop, verified in source
- `classic-scanlog-core/src/mod_detector.rs:524` — per-entry `Regex::new()`, verified in source
- `classic-file-io-core/src/core.rs:1050` — `Mmap::map()` in `read_file_mmap`, verified in source
- `classic-yaml-core/src/lib.rs:156` — unbounded `YAML_CACHE` DashMap, verified in source
- `classic-settings-core/src/cache.rs:18` — unbounded `SETTINGS_CACHE` DashMap, verified in source
- `classic-file-io-core/src/hash.rs:51` — unbounded `HASH_CACHE` DashMap, verified in source
- `classic-scanlog-py/src/parser.rs:98` — `#[allow(deprecated)]` on FFI boundary, verified in source
- `classic-scanlog-core/benches/scanlog_benchmarks.rs` — existing criterion harness, verified in source
- `classic-file-io-core/core.rs:99` — `quick_cache` already in use (established pattern)
- `record_scanner.rs`, `patterns.rs`, `plugin_analyzer.rs` — AhoCorasick already in use (established pattern)

### Tertiary (MEDIUM confidence — GitHub issues and community)

- [Cargo #12162](https://github.com/rust-lang/cargo/issues/12162) — workspace deps and default-features interaction
- [Regex #891](https://github.com/rust-lang/regex/issues/891) — AhoCorasick for literal alternations in the regex crate
- [Criterion #485](https://github.com/bheisler/criterion.rs/issues/485) — unstable benchmark causes and `black_box` requirements

---

*Research completed: 2026-04-04*
*Ready for roadmap: yes*
