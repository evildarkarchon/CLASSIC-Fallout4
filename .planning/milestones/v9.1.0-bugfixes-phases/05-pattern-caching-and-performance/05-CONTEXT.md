# Phase 5: Pattern Caching and Performance - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove repeated pattern and parser construction from the scanlog hot paths by caching compiled matchers in `classic-scanlog-core`, reusing a cached parser for the C++ bridge crash-pattern helper, and proving the change with Criterion benchmarks. This phase stays inside the named performance paths and benchmark evidence; it does not broaden into binding API redesigns, unrelated hotspot cleanup outside the touched paths, or a repo-wide `Lazy` to `LazyLock` sweep.

</domain>

<decisions>
## Implementation Decisions

### Important-mod matcher
- **D-01:** `detect_mods_important` moves from per-entry `Regex::new(...)` calls to an `Aho-Corasick` matcher.
- **D-02:** The matcher should use `LeftmostLongest` semantics when overlaps need disambiguation.
- **D-03:** Matching should continue to operate over one combined lowercase text surface built from plugin names plus XSE module names, to stay closest to current behavior.
- **D-04:** The old regex-per-entry path must not be removed until fixture-backed parity is proven against the existing behavior.

### Shared pattern cache
- **D-05:** `detect_mods_single`, `detect_mods_double`, and `detect_mods_batch` should share internal compile/normalization helpers where that directly reduces duplicated hot-path setup, but they should not be forced into one universal cache abstraction.
- **D-06:** Compiled pattern caches should be process-wide and bounded, not per-run and not unbounded.
- **D-07:** The cache/backend pattern should reuse the established `LazyLock` + `quick_cache` approach already used for new global caches in this repo.
- **D-08:** Cache keys should come from normalized content hashes of the mod-list inputs, and normal lifecycle should be hash-keyed reuse plus bounded eviction rather than manual reset hooks.

### Benchmark proof
- **D-09:** Phase 5 benchmark proof should extend the existing `classic-scanlog-core` Criterion bench setup rather than introducing a new bridge-only benchmark harness by default.
- **D-10:** Benchmarks should use both real crash-log fixtures and synthetic hotspot-focused inputs so the work is both realistic and isolatable.
- **D-11:** Before/after evidence should use local Criterion baseline save/compare flows; raw baseline captures should stay out of git unless a later request explicitly asks for a shareable export.
- **D-12:** Each locked hotspot should show measurable improvement, or the implementation should explain why a chosen structural change is still required.

### Optimization breadth
- **D-13:** Phase 5 may take a broader cleanup pass inside the already-touched `mod_detector` and C++ bridge files instead of limiting itself to the exact current call sites.
- **D-14:** Adjacent regex/static-init cleanup inside those touched files is in scope when it directly supports the locked hotspot work.
- **D-15:** Supporting cleanup may still land even if it is not independently benchmark-visible, as long as it directly enables the locked Phase 5 performance changes or removes duplicate hot-path setup.
- **D-16:** Similar hotspots discovered outside the locked Phase 5 paths should be recorded and deferred, not folded into scope automatically.

### the agent's Discretion
- Exact cache capacities and key-shape details for the new pattern caches, as long as they stay bounded and hash-keyed.
- Exact helper names and internal factoring used to share compile/normalization logic across the touched functions.
- Exact benchmark group names, input sizes, and how the bridge crash-pattern hotspot is represented inside the existing scanlog bench harness.

</decisions>

<specifics>
## Specific Ideas

- Treat the existing `STATE.md` blocker as non-negotiable: `detect_mods_important` semantic parity must be proven before the old regex path is removed.
- The benchmark story should measure the C++ bridge parser-allocation hotspot through the existing scanlog Criterion scaffolding instead of adding a new bridge benchmark harness unless planning later proves that is insufficient.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone contract
- `.planning/ROADMAP.md` - Phase 5 goal, requirements, and success criteria.
- `.planning/PROJECT.md` - milestone constraints, active performance work, and the "no unbounded caches" core value.
- `.planning/REQUIREMENTS.md` - `PERF-01`, `PERF-02`, `PERF-03`, `PERF-04`, and `CONS-04`.
- `.planning/STATE.md` - carry-forward decisions from prior phases plus the explicit parity blocker for the Aho-Corasick migration.
- `.planning/phases/04-bounded-cache-replacement/04-CONTEXT.md` - the locked repo pattern for new `LazyLock`-backed bounded caches.
- `.planning/codebase/CONCERNS.md` - original hotspot audit for `mod_detector` and bridge parser allocation.

### Public API and contract docs
- `docs/api/README.md` - required reading order and the rule to update docs when public Rust or bridge-facing behavior changes.
- `docs/api/classic-scanlog-core.md` - current scanlog-core public surface, including `mod_detector` helpers and `LogParser` behavior.
- `docs/api/classic-cpp-bridge-data-entrypoints.md` - current `detect_crash_pattern` bridge behavior and fail-soft contract.

### Hotspot source files
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs` - current regex-heavy implementations of `detect_mods_single`, `detect_mods_double`, `detect_mods_important`, and `detect_mods_batch`.
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` - current per-call `LogParser::new(None)` use in `detect_crash_pattern`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml` - existing dependencies already available for this phase (`aho-corasick`, `quick_cache` via workspace, `xxhash-rust`, Criterion).

### Benchmark infrastructure
- `ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs` - existing Criterion harness and real crash-log fixtures to extend.
- `ClassicLib-rs/criterion.toml` - workspace Criterion baseline/output policy.
- `performance_baselines/README.md` - repo policy for keeping raw Rust baseline captures local by default.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs`: existing Criterion setup, real crash-log fixtures, and shared benchmark conventions.
- `ClassicLib-rs/criterion.toml`: workspace-level Criterion configuration already set up for local baselines and HTML reports.
- `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs`, `ClassicLib-rs/business-logic/classic-settings-core/src/cache.rs`, and `ClassicLib-rs/business-logic/classic-file-io-core/src/hash.rs`: established `LazyLock` + bounded `quick_cache` patterns.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs`: existing lowercase normalization and combined-pattern construction that can be factored into shared helpers.
- `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml`: `aho-corasick`, `regex`, `xxhash-rust`, and Criterion are already available in the workspace.

### Established Patterns
- Business logic stays in Rust core; bridge layers stay thin and adapt core behavior instead of inventing parallel logic.
- New global caches in touched code should be bounded and initialized with `LazyLock`, matching Phase 4.
- Performance evidence uses Criterion with local baselines rather than committed raw benchmark directories.
- Behavior-sensitive replacements should prove parity against existing fixtures before old implementations are removed.

### Integration Points
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs` is the main core hotspot for Phase 5.
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` is the bridge hotspot for cached parser reuse.
- `ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs` is the intended benchmark home for this phase.
- `docs/api/classic-scanlog-core.md` and `docs/api/classic-cpp-bridge-data-entrypoints.md` are the contract docs most likely to need updates when implementation lands.

</code_context>

<deferred>
## Deferred Ideas

- `ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs` has separate synchronous parser utilities that also construct `LogParser::new(None)` per call; note this as a later hotspot unless Phase 5 work proves it is required for the locked goals.
- Repo-wide `once_cell::sync::Lazy` to `LazyLock` conversion remains Phase 7, not Phase 5.

</deferred>

---

*Phase: 05-pattern-caching-and-performance*
*Context gathered: 2026-04-05*
