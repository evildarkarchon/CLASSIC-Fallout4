---
phase: 5
reviewers: [claude]
reviewed_at: 2026-04-06T00:07:34.9497765-07:00
reviewed_at_note: external claude CLI review
plans_reviewed: [05-01-PLAN.md, 05-02-PLAN.md, 05-03-PLAN.md, 05-04-PLAN.md]
---

# Cross-AI Plan Review - Phase 5

## the agent Review

Now I have a grounded understanding of the actual code. Here's my review.

---

# Phase 5 Plan Review: Pattern Caching and Performance

## Plan 05-01: Bounded Matcher Caches for single/double/batch + LazyLock Static Regexes

### Summary

Solid plan that correctly identifies the per-call regex compilation hotspot in `detect_mods_single` and `detect_mods_double`, and targets cross-call caching via the repo's established `LazyLock + quick_cache` pattern. The plan appropriately splits into two tasks (caching + LazyLock migration) and has clear acceptance criteria. However, it has two factual errors about the codebase that will cause implementation friction.

### Strengths
- Correctly follows the Phase 4 `LazyLock<Cache<K, Arc<V>>>` pattern from `classic-settings-core/src/cache.rs`
- TDD approach: write tests first, then implementation
- Doesn't over-scope: leaves `detect_mods_important` to 05-02
- Cache capacity of 64 is a reasonable starting point matching repo precedent
- Explicit acceptance criteria with greppable patterns

### Concerns
- **HIGH**: `files_modified` lists `ClassicLib-rs/business-logic/classic-scanlog-core/src/tests/mod.rs`, but mod_detector tests are **inline in `mod_detector.rs` itself** (lines 756-1505). There is no separate `tests/mod.rs` for these. The executor will either create a new file (fragmenting tests) or waste time looking for the wrong file.
- **HIGH**: `classic-scanlog-core/Cargo.toml` does **not** have `quick_cache` as a dependency. It has `aho-corasick`, `regex`, `xxhash-rust`, but `quick_cache` is only in `classic-settings-core` and `classic-yaml-core`. The plan doesn't mention adding this dependency, and neither `Cargo.toml` nor `files_modified` lists it.
- **MEDIUM**: `detect_mods_batch` already compiles the regex **once** outside the Rayon `par_iter()` loop. The real win for batch is cross-call reuse (same YAML dict, different crash logs), not hoisting out of parallel work. The plan's framing ("hoists compilation out of its per-item work") is misleading about where the actual gain is.
- **LOW**: Task 2 says "Convert static regexes in the touched `mod_detector` file from older lazy-init patterns to `std::sync::LazyLock`" — but `mod_detector.rs` currently has **zero** lazy statics or `once_cell` usage. All regex compilation is inline. The task should say "introduce `LazyLock` for patterns that are constant across calls" rather than "convert from older lazy-init patterns."

### Suggestions
- Add `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml` to `files_modified` and include a step to add `quick_cache = { workspace = true }` as a dependency
- Fix test file path: change `src/tests/mod.rs` to `src/mod_detector.rs` (inline test section) or explicitly state that new tests should be added to the existing inline `#[cfg(test)] mod tests` block
- Clarify that `detect_mods_batch` already hoists regex out of the parallel loop — the cache benefit is **cross-call** reuse when the same YAML dict is used across multiple batch invocations
- Note that `mod_detector.rs` currently has no lazy statics to "convert"; Task 2 should be framed as "introduce `LazyLock` for eligible constant patterns" if any exist, or scoped to only the patterns touched by Task 1

### Risk Assessment: **MEDIUM**
The plan is architecturally sound but the wrong test file path and missing Cargo.toml dependency will cause implementation delays. An autonomous executor hitting these issues may make incorrect decisions (creating a new test file, or failing to compile because `quick_cache` isn't available).

---

## Plan 05-02: Aho-Corasick Migration for detect_mods_important

### Summary

The highest-risk plan in the phase, correctly isolated with a parity-first approach. The TDD structure (write parity tests before swapping implementation) directly addresses the STATE.md blocker. The two-task split is well-designed: Task 1 creates the safety net, Task 2 makes the change. The plan is appropriately conservative about removing the legacy path.

### Strengths
- Parity-first: tests written before implementation swap — directly addresses the non-negotiable STATE.md blocker
- Private legacy helper pattern allows direct old-vs-new comparison in tests
- Correctly preserves existing `exclude_when`, GPU, and output formatting logic untouched
- Explicit that legacy path stays until parity is proven
- Overlap-sensitive test case addresses `LeftmostLongest` semantics specifically
- No unnecessary caching abstraction — just replaces the matching engine

### Concerns
- **HIGH**: Same test file path issue as 05-01 — references `src/tests/mod.rs` but tests are inline in `mod_detector.rs` (line 756+). The existing `detect_mods_important` tests are part of the inline `#[cfg(test)] mod tests` block.
- **MEDIUM**: The plan doesn't address how the Aho-Corasick automaton is built per-call vs. cached. Currently `detect_mods_important` compiles one `Regex::new(format!("(?i){}", ...))` per entry. The AC automaton would be built once per call from all entries. But if the same `entries` slice is passed repeatedly (which it is — it comes from `AnalysisConfig.mods_core`), there's a caching opportunity the plan doesn't mention. This is fine for correctness but means PERF-02 may not deliver maximum improvement since automaton construction still happens every call.
- **MEDIUM**: The current implementation uses `(?i)` flag for case-insensitive matching per entry. The plan says to lowercase patterns and search the lowercase surface, but the current code already lowercases the combined text surface (`plugins_text`, `modules_text`). Need to verify the `detect` field values from `CoreModEntry` — if some contain regex metacharacters (not just literals), the Aho-Corasick approach breaks because AC is literal-only. The plan assumes D-01 that these are escaped literals, but the actual `CoreModEntry.detect` values should be verified.
- **LOW**: `depends_on: []` means this can run in parallel with 05-01. Both modify `mod_detector.rs`. If truly executed in parallel (wave 1), merge conflicts are guaranteed. The wave system should handle this, but the `depends_on` should arguably include `05-01` to avoid conflicts in the same file.

### Suggestions
- Fix test file path to `mod_detector.rs` inline tests
- Add a defensive note: if any `CoreModEntry.detect` value contains regex metacharacters (not pure literals), the AC build should escape them or fall back — the research says "escaped literals" but the plan should verify this assumption during implementation
- Consider whether the AC automaton should be cached (cross-call reuse for same `entries` slice) or just built per-call. Even without caching, eliminating N per-entry regex compilations down to one AC build is a major win, but the plan should be explicit about this choice
- Consider adding `depends_on: [05-01]` to avoid merge conflicts in `mod_detector.rs`, or at minimum acknowledge the parallel-edit risk

### Risk Assessment: **MEDIUM**
The semantic risk is well-managed by the parity-first approach. The main risks are: (1) potential merge conflicts with 05-01 if truly parallel, (2) the assumption that all `detect` values are pure literals, and (3) the wrong test file path. The plan's conservative approach (keep legacy path until parity proven) is the right call.

---

## Plan 05-03: Cached Bridge Parser for detect_crash_pattern

### Summary

The simplest and lowest-risk plan in the phase. The change is mechanical: replace `LogParser::new(None)` with a `LazyLock<LogParser>` static. The plan correctly scopes to just the bridge file and adds positive test coverage (currently only an empty-input test exists). Clean and well-bounded.

### Strengths
- Minimal blast radius — one function, one file, one static
- Adds positive test coverage that's currently missing (only `test_detect_crash_pattern_empty` exists)
- Correctly keeps bridge as adapter-only
- TDD approach for the test task
- Doc update included in scope

### Concerns
- **MEDIUM**: The plan doesn't verify that `LogParser` is `Send + Sync` (required for `LazyLock<LogParser>` in a static). From the code, `LogParser` uses internal `LruCache` and other state. If it's not `Sync`, the `LazyLock` approach won't compile. The plan should note this check or have a fallback (e.g., `LazyLock<Mutex<LogParser>>`).
- **MEDIUM**: `LogParser` has internal caches (`clear_caches()` method exists). If the static singleton accumulates cache state across many calls, it could grow unbounded or cause stale results. The plan should consider whether `parse_crash_header()` relies on internal parser state that could cause issues when shared across calls.
- **LOW**: The test task says "a representative crash header produces a positive pattern result" but doesn't specify where the test fixture comes from. The existing benchmarks have three real crash log fixtures that could be reused.

### Suggestions
- Add a pre-implementation check: verify `LogParser: Send + Sync` (or at minimum that it compiles in `LazyLock`). If not, document the fallback approach.
- Note whether `LogParser`'s internal caches are a concern for a long-lived singleton — `parse_crash_header` may or may not use them, and the LRU caches may be bounded already.
- Suggest reusing one of the existing benchmark fixtures (`SAMPLE_LOG_SMALL`, etc.) for the positive test case rather than creating a new synthetic fixture.

### Risk Assessment: **LOW**
This is a straightforward optimization. The `Send + Sync` question is the only real uncertainty, and it's easily resolved at implementation time. The plan is well-scoped and unlikely to cause regressions.

---

## Plan 05-04: Criterion Benchmark Proof

### Summary

Well-structured benchmark plan that correctly depends on the three implementation plans (wave 2). The approach of extending the existing harness rather than creating a new one follows repo conventions. The local-baseline documentation task is a good addition for contributor guidance.

### Strengths
- Correct wave 2 dependency — benchmarks only make sense after implementation lands
- Extends existing `scanlog_benchmarks.rs` harness rather than creating a new one
- Includes both real fixtures and synthetic inputs per D-10
- Separates setup cost from hot-path measurement
- Documents the local baseline workflow for future contributors
- `performance_baselines/README.md` update ensures the workflow is discoverable

### Concerns
- **MEDIUM**: The plan says to add a "bridge-style crash-pattern benchmark helper" inside `scanlog_benchmarks.rs`. But `scanlog_benchmarks.rs` is in `classic-scanlog-core` while the bridge code is in `classic-cpp-bridge`. To benchmark the bridge pattern, the bench would need to replicate the bridge's `detect_crash_pattern` logic (create parser, parse header, extract main_error) as a Rust helper. This is fine per D-09 but should be explicit that this is a Rust-side replica, not an actual bridge call.
- **MEDIUM**: The plan doesn't specify what "measurable improvement" means quantitatively. D-12 says "each locked hotspot should show measurable improvement, or the implementation should explain why." The plan should set expectations: is 10% improvement sufficient? 2x? Criterion's noise threshold? Without this, the benchmark task has no clear pass/fail criterion.
- **LOW**: The plan lists `performance_baselines/README.md` in `files_modified` but the benchmark file's acceptance criteria don't include a `--test` run to verify benchmarks compile and execute. The verify command is `--list` which only lists benchmark names, not runs them.

### Suggestions
- Clarify that the "bridge-style crash-pattern benchmark" is a Rust helper that mirrors the bridge pattern (per-call LogParser vs cached LogParser), not an actual FFI benchmark
- Add guidance on what constitutes "measurable improvement" — Criterion's default confidence interval (95%) should detect meaningful changes, but the plan should note that if a benchmark shows no change, the implementation rationale should be documented
- Consider adding `cargo bench ... -- --test` to verification to ensure benchmarks actually compile and run (not just list)

### Risk Assessment: **LOW**
Benchmark plans carry minimal code risk. The main risk is producing benchmarks that don't clearly prove improvement, but the existing Criterion infrastructure and fixture strategy mitigate this well.

---

## Cross-Plan Concerns

| Issue | Severity | Plans Affected |
|-------|----------|----------------|
| Wrong test file path (`src/tests/mod.rs` vs inline in `mod_detector.rs`) | **HIGH** | 05-01, 05-02 |
| Missing `quick_cache` in `classic-scanlog-core/Cargo.toml` | **HIGH** | 05-01 |
| Parallel modification of `mod_detector.rs` by 05-01 and 05-02 (both wave 1, `depends_on: []`) | **MEDIUM** | 05-01, 05-02 |
| `LogParser` Send+Sync not verified for LazyLock usage | **MEDIUM** | 05-03 |
| No quantitative threshold for "measurable improvement" | **MEDIUM** | 05-04 |

## Overall Phase Assessment

**Overall Risk: MEDIUM**

The plans are architecturally sound and follow the project's established patterns well. The phase decomposition is logical: implementation first (wave 1), benchmarks second (wave 2). The parity-first approach for the highest-risk change (Aho-Corasick migration) is the right call.

The two **HIGH** issues (wrong test file path and missing `quick_cache` dependency) are straightforward to fix but will cause autonomous executors to stumble. The parallel-edit concern between 05-01 and 05-02 is the most structurally significant — either 05-02 should depend on 05-01, or the plans should acknowledge they'll touch different sections of `mod_detector.rs` and the executor should handle merge carefully.

Fix the two HIGH issues before execution, and these plans will deliver the phase goals cleanly.

---

## Consensus Summary

Only one external reviewer was run in this pass (`claude`), so the summary below reflects that single independent review rather than cross-reviewer consensus.

### Agreed Strengths
- The overall phase decomposition is sound: implementation work first, benchmark proof after implementation lands.
- The plans generally follow established repo patterns, especially the Phase 4 `LazyLock` plus bounded-cache direction.
- The parity-first structure for `05-02` is the right way to manage the highest semantic-risk change.
- `05-03` and `05-04` are well-scoped and avoid unnecessary new harnesses or bridge redesign.

### Agreed Concerns
- **HIGH:** `05-01` and `05-02` point at `ClassicLib-rs/business-logic/classic-scanlog-core/src/tests/mod.rs`, but the relevant tests live inline in `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs`.
- **HIGH:** `05-01` assumes `quick_cache` is already available in `classic-scanlog-core`, but `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml` is not currently listed in `files_modified` and the dependency addition is not planned explicitly.
- **MEDIUM:** `05-01` and `05-02` both modify `mod_detector.rs` in wave 1 with no dependency edge, creating avoidable merge/conflict risk.
- **MEDIUM:** `05-03` should explicitly verify that a module-level `LazyLock<LogParser>` is valid for the actual `LogParser` type and does not introduce unwanted shared-state behavior.
- **MEDIUM:** `05-04` should define what counts as a meaningful benchmark improvement and ideally verify benchmark execution, not just listing.

### Divergent Views
- Not applicable in this run: only one external reviewer was requested and executed.
