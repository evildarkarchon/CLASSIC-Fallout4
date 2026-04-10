---
phase: 3
reviewers: [claude, codex]
reviewed_at: 2026-04-08T19:23:15-07:00
review_round: 2
plans_reviewed:
  - 03-01-tooling-expansion-PLAN.md
  - 03-02-scanlog-wave1-parsing-primitives-PLAN.md
  - 03-03-scanlog-wave2-detection-and-analysis-PLAN.md
  - 03-04-scanlog-wave3a-orchestration-core-PLAN.md
  - 03-05-scanlog-wave3b-report-standalone-PLAN.md
  - 03-06-config-promotion-PLAN.md
  - 03-07-version-registry-promotion-PLAN.md
  - 03-08-classic-shared-and-file-io-aux-PLAN.md
  - 03-09a-a10-residual-promotion-PLAN.md
  - 03-09b-tier2-cleanup-and-final-sweep-PLAN.md
review_scope: "09a and 09b only (rewritten 2026-04-08 as a scoped revision of the original monolithic Plan 09). Plans 01-08 are SHIPPED (SUMMARY.md files on disk; 'Complete 03-XX' commits) and explicitly excluded from re-review."
supersedes: "Round 1 REVIEWS.md (2026-04-08T02:29:03-07:00) which reviewed the original monolithic Plan 09. That review's HIGH concerns drove the split into 09a and 09b."
---

# Cross-AI Plan Review — Phase 3: Python Tier Collapse (Round 2)

> Independent peer review by Claude Opus 4.6 (separate CLI session) and Codex (GPT-5.4). Both reviewers received the same ~600 KB prompt containing PROJECT.md, ROADMAP, REQUIREMENTS, CONTEXT.md (with Research Amendments A1–A10), RESEARCH.md, VALIDATION.md, all 10 PLAN.md files, and the Plan 08 SUMMARY.md ground-truth document. Prompt explicitly instructed reviewers to focus on 09a/09b and to NOT re-flag issues with shipped plans 01-08. Round 1 review (earlier today) drove the 09a/09b split; this Round 2 review validates the rewrite.

---

## Consensus Summary

**Both reviewers converged on two HIGH-severity findings that the planner and internal plan-checker both missed** — and that have the potential to block Phase 3 closure. They also converged on the overall assessment that the rewrite is a meaningful improvement over the old monolithic Plan 09 but contains critical correctness issues that must be resolved BEFORE `/gsd:execute-phase 3` runs.

### Agreed Strengths (both reviewers)

- **Ground-truth sourcing is correct**: 09a sources residuals from `parity_diff_report.json::gaps` (not the stale `rust_api_surface.json` from the old Plan 09 or the stale Plan 01 `03-01-A10-sizing.json` snapshot). Both reviewers flagged this as the right A10-driven shape.
- **R3/R9 exclusions are locked down**: `EXCLUDED_OWNERS = {"file_io", "shared"}` and `EXCLUDED_RUST_SYMBOLS = {"GLOBAL_FCX_HANDLER"}` are named constants with inline citations; 09a treats Plan 08 as frozen ground truth and hard-pins `file_io == 95` and `shared == 61`.
- **Pre-deletion cascade audit (09b Task 1)**: Both reviewers praised this as the right response to REVIEWS Round 1 concern #5 about silent `.get(key, 0)` hides — writing an audit file as a gatekeeping artifact is good discipline.
- **19-stub explicit enumeration with foundation/classic-shared-py outlier**: Both reviewers noted that the explicit hard-coded 19-stub list including the non-`python-bindings/` outlier avoids the "18 under python-bindings, 1 elsewhere" miss.
- **Line-number re-verification (09b Task 2 Step 1)**: Both praised the `Select-String` re-grep before editing `generate_baseline.py` as a good safeguard against drift from 09a.
- **PYT-06 coverage completeness one-liner copied verbatim from VALIDATION.md**: No drift risk between gate definition and verification.

### Agreed HIGH Concerns (both reviewers converged)

| # | Concern | Severity | Evidence |
|---|---------|:--:|---|
| **H1** | **09a Task 0 fail-closed wrapper check is fundamentally broken** — the grep-based check searches for `pub fn` / `pub struct Py<Name>` / `impl Py<Name>` patterns, but PyO3 `#[pymethods] impl Py<Class> { fn method() }` blocks use bare `fn` (NOT `pub fn`). Additionally, `gap_type == rust_unmapped` residuals by definition have no `-py` wrapper (they use `@rust` proxy rows). **Impact**: Every method residual across 14 owners will be classified `reason=no_wrapper_found`, written to `03-09a-BLOCKERS.md`, and halted via `raise SystemExit`. Plan 09a will very likely halt at Task 0 before Task 1 can run. | HIGH | Claude: detailed PyO3 pattern analysis; Codex: "only proves textual wrapper presence by grep; does not prove crate-root export visibility, Python export-path alignment, or stub coverage" |
| **H2** | **The path from current `deferred_total` to `deferred_total == 0` is unjustified** — Plan 08 SUMMARY records `deferred_total=1040` (down from 1042 after adding 156 rows — ratio ~1%). Linearly projected, 09a's ~600 rows reduces deferred_total by only ~6-12, ending near 1028-1034, NOT 0. Plan 09b's structural deletion of `generate_diff_report()` gap branches does NOT touch `deferred_runtime_backlog.json`, which is owned by Phase 6 per the DOC-02/DOC-04 boundary. The `deferred_total` metric in `runtime_coverage_summary.json` is computed from a lookup against the backlog file, not from the `gaps` array — deleting `tier2_gap_total` and markdown columns in 09b is not sufficient. **Plan 09a's own interface block admits**: _"After Plan 09a, deferred_total should be exactly 1 (the R9 GLOBAL_FCX_HANDLER excluded symbol) plus any non-promoted entries the deferred backlog still tracks separately from the gap report."_ — this contradicts the Plan 09b closure gate at Task 4 Step 4. | HIGH | Claude: traced to DOC-02/DOC-04 boundary + cited Plan 08 empirical ratio; Codex: traced to `build_coverage_summary()` L313 in `binding_parity_runtime_coverage.py` |

### Agreed MEDIUM Concerns

- **09b adds a test that depends on state that only exists after a later task** (09b Task 2 adds `test_tier2_gap_total_removed_from_summary` which reads `parity_diff_report.json`, but the refresh doesn't happen until Task 3 — bisect-breaking intermediate state). Both reviewers flagged this as a commit-sequencing correctness issue.
- **09b's cascade audit scope is narrower than its "every reader" claim**. Codex: "selective-glob based, not a repo-wide recursive search." Claude: enumerated the missing paths — `.github/workflows/*.yml`, `tools/cxx_api_parity/*.py`, repo-root `tools/*.py`, `.ps1` build scripts.

### Divergent Views

- **How `deferred_total` is computed** (root cause): Claude traced it to `deferred_runtime_backlog.json` being read by `runtime_coverage_summary.json`'s builder (Phase 6 territory per DOC-02/DOC-04). Codex traced it to `build_coverage_summary()` L313 reading `trackedSurface` classifications in `binding_parity_runtime_coverage.py`. Both conclude the plan's assumption is wrong, but the exact root cause differs — one of them may be more accurate. **Recommended action**: empirically trace the computation path on a scratch branch before replanning.
- **09a hash algorithm** (unique to Codex): Codex flagged that 09a Task 3 hardcodes `contractIdsHash = sha256[:16]` but the live `_stable_id_hash` in `tools/binding_parity_runtime_coverage.py:57` uses full 64-char SHA-256 over newline-joined sorted IDs. This would produce `registry_mismatch_total > 0` at gate time. Claude did not flag this — likely because Claude focused on execution-time halting issues (wrapper check) rather than gate-time hash mismatches. Codex's finding is code-verified and should be treated as HIGH.
- **Constructor inventory scale concern** (unique to Claude): Claude flagged that Plans 02-08 each had a dedicated Task 0 `CONSTRUCTOR-INVENTORY.md`, but Plan 09a embeds constructor verification inline in Task 1 Step 2 despite being 10× larger (14 owners × 6-10 classes each ≈ 80+ classes vs Plan 08's 2 owners). This re-introduces the REVIEWS Round 1 concern #3 (constructor guessing) at scale. Codex did not raise this.
- **Test scaffolding tooling** (unique to Claude): Claude projected that Plan 09a requires 100-150 hand-authored smoke tests and noted that Plan 08's 6 "Rule 1 test assumption bugs" at 49-test scale predict 12-18 bugs at 100-150-test scale without scaffolding tooling. Recommended authoring `_scaffold_plan09a_tests.py`. Codex did not raise this.

### Unique Findings

**Unique to Claude** (not in Codex):
- **Method residual pattern bug specific to PyO3** — Claude identified that `#[pymethods] impl Py<Class> { fn method() }` blocks use bare `fn`, not `pub fn`, which the grep check doesn't anticipate. Plan 09a's author knew about this case but only fixed it for `SCANLOG_METHOD_RESIDUALS` (4 methods); the other 14 owners hit the bug.
- **rust-only residual handling via @rust proxy** — Claude cited Plan 08's precedent at `_build_plan08_rows.py:261-283` where `gap_type=rust_unmapped` residuals use a paired `@rust`-suffixed proxy row with a Python anchor class. The 09a wrapper check doesn't handle this at all.
- **Residual count discrepancy with STATE.md** — Plan 09a: 736 total; STATE.md: ~913 total; 21-row delta across 7 owners. Suggests stale numbers or scope leakage.
- **No dry-run projection step** — Plan 09a doesn't empirically verify its 600 rows will resolve the expected number of deferred backlog entries before committing to the 09b `deferred_total == 0` gate.
- **Plan 09b Task 4 lacks a diagnostic dump** — On `deferred_total != 0`, the gate just does `exit 1` without listing which backlog entries are stuck, giving the operator no actionable recovery info.
- **`testSuite` scalar-vs-array convention (R8 precedent)** — Plan 02 established that new smoke suites get a SEPARATE selector entry, not a bump to an existing one. Plan 09a bumps `python-tier1-scanlog` to 251 and implicitly assumes the existing testSuite covers 4 new method residuals which actually live in `test_promoted_residuals_smoke.py`.
- **mypy --strict run-per-file vs run-all** — Per-file foreach loop won't detect cross-stub type references (e.g., if `classic_scanlog.pyi` imports a type from `classic_config.pyi`).

**Unique to Codex** (not in Claude):
- **contractIdsHash algorithm mismatch** — Codex verified `_stable_id_hash` in the live tooling source uses full 64-char SHA-256, not 16-char truncation. Plan 09a's acceptance criterion at line 820 would fail.
- **Existing test asserts `python_unmapped` exists** — `ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py:169-170` already asserts `python_unmapped` in the diff report, and this test file is NOT in Plan 09b's declared write set. Plan 09b will regress this shipped test when it deletes the key.
- **`validate_stubs.py` does not cover classic_shared** — The validator only walks `ClassicLib-rs/python-bindings` crates ending in `-py` (L318, L333-352). There is no `foundation/` handling, so `classic_shared` is only protected by the explicit mypy step.
- **`python-tier2-scanlog-runtime` stale registry semantics** — The preserved tier-2 entry at `runtime_coverage_registry.json:275-287` currently points to the exact 4 methods that 09a promotes to tier-1. Plan needs to explain the intended post-state.

---

## Claude Opus 4.6 Review (separate CLI session)

### Summary

The rewrite of Plans 09a and 09b is a meaningful improvement over the monolithic Plan 09 — the surgical split isolates residual promotion (09a) from structural cleanup (09b), the helper-script pattern generalizes Plan 08's proven template, and the 19-stub mypy sweep is explicitly enumerated rather than glob-matched. However, **two HIGH-severity issues threaten Phase 3 closure**: (1) the fail-closed wrapper-existence check in 09a Task 0 is fundamentally wrong for method residuals and rust-only residuals and will false-close on hundreds of legitimate symbols, halting the plan before Task 1; and (2) the mechanical path from the current `deferred_total=1040` (per Plan 08 SUMMARY) to Plan 09b's `deferred_total == 0` gate is unjustified by evidence — Plan 08 reduced deferred_total by only 2 when adding 156 rows, so the linear projection suggests 09a will not get anywhere near 0, and 09b has no task that explicitly resolves the remainder. Plan 09b is otherwise solid; 09a needs surgery before execution.

### Strengths

- **Ground-truth source change**: 09a Task 0 sources residuals from `parity_diff_report.json::gaps` (post-refresh) rather than the stale Plan 01 `03-01-A10-sizing.json` snapshot — this is the correct pattern.
- **R3/R9 locked exclusions**: `EXCLUDED_OWNERS = {"file_io", "shared"}` and `EXCLUDED_RUST_SYMBOLS = {"GLOBAL_FCX_HANDLER"}` are named constants with inline citations. Acceptance criteria verify `file_io_count == 95` and `shared_count == 61` exactly — strong anti-regression against Plan 08.
- **Plan 08 template reuse**: Same-row dedup via `already_covered_rust_symbols`, multi-owner routing maps, atomic-per-task commits — all proven in the predecessor plan.
- **Line-number re-verification**: 09b Task 2 Step 1 re-greps generate_baseline.py before editing, protecting against any drift from 09a.
- **Pre-deletion cascade audit (09b Task 1)**: This is a direct response to the REVIEWS HIGH concern about silent `.get(key, 0)` hides — writing the audit to a file as gatekeeping artifact is good discipline.
- **19-stub explicit enumeration (09b Task 4)**: Hard-coded array of 19 paths including the foundation/classic-shared-py outlier, with `$stubs.Count -ne 19` guard. No glob risk.
- **xfail flip pattern**: 09b Task 2 Steps 7–9 cleanly promote Plan 01's `test_tier2_definition_removed_after_plan_9` from strict-xfail to passing in the same commit that deletes the dependency.
- **Pre-task Rule 2 stub audit (09a Task 0 Step 2)**: Correctly anticipates the Plan 08 lesson that enrolling new owners surfaces pre-existing stub holes.
- **PYT-06 coverage completeness one-liner copied verbatim from VALIDATION.md**: No drift risk between gate definition and verification.

### Concerns

#### HIGH

- **HIGH — 09a Task 0 wrapper-existence check false-closes on method residuals** (Plan 09a lines ~175-225, the `find_wrapper` / `bare = symbol.split(".")[-1]` logic).
  - For a residual like `{"python_export_path": "PatternMatcher.has_match", "gap_type": "python_unmapped"}`, `bare` resolves to `"has_match"` and the candidate list searches for `pub fn has_match`, `pub struct Pyhas_match`, `impl Pyhas_match`, etc.
  - **PyO3 methods in `#[pymethods] impl Py<Class> { fn method() }` blocks use bare `fn`, NOT `pub fn`.** The check has no candidate that matches this pattern.
  - The only candidate that might match is `name = "has_match"`, which requires an explicit `#[pyo3(name = "has_match")]` attribute — but by convention Python-facing method names match the Rust method name directly, so no explicit `name =` attribute exists for the common case.
  - **Impact**: Every method residual from scangame (many), path, database, etc. will be classified as `reason=no_wrapper_found` and appended to `03-09a-BLOCKERS.md`, halting Plan 09a at Task 0 via `raise SystemExit`.
  - **Evidence**: Plan 09a hardcodes the 4 scanlog methods in `SCANLOG_METHOD_RESIDUALS` precisely to bypass this issue — the author knew about the method case but only fixed it for scanlog. All other method residuals across 14 owners will hit the bug.
  - **Fix required before execution**: For method residuals (detected by `"." in python_export_path`), verify the OUTER class wrapper exists, not the bare method name. OR special-case methods to skip the wrapper check since the class-level row covers them.

- **HIGH — 09a Task 0 wrapper-existence check also false-closes on rust-only residuals** (same location).
  - For `gap_type=rust_unmapped` residuals (e.g., `{"rust_symbol": "SomeCoreType", "rust_symbol": "GameTarget"}`), the check searches `classic-<owner>-py/src/` for a wrapper. But rust-only residuals BY DEFINITION have no `-py` wrapper — that's why they need `@rust`-suffixed proxy rows paired with a Python anchor class (per Plan 08's precedent at `_build_plan08_rows.py` lines 261-283).
  - The Plan 09a check will classify every rust-only residual as `reason=no_wrapper_found` and block.
  - **Fix required**: Skip wrapper existence check entirely for `gap_type == "rust_unmapped"` residuals — the `@rust` proxy row approach makes it irrelevant.

- **HIGH — The path from current `deferred_total=1040` to `deferred_total == 0` is unjustified** (Plan 09b Task 4 Step 4 success gate).
  - Plan 08 SUMMARY explicitly records: _"deferred_total=1040 (down from 1042 — the 2 similarity gaps moved from deferred to contract)"_.
  - Plan 08 added 156 contract rows but reduced deferred_total by only 2. The contract-row-to-deferred-reduction ratio in the multi-owner promotion scope is ~1%.
  - Plan 09a promotes ~600 net rows. Linearly projected: deferred_total reduction ≈ 6-12, ending near ~1028-1034.
  - Plan 09b's Tasks 1–3 perform structural deletion of `generate_diff_report()` gap branches. **This does NOT touch `deferred_runtime_backlog.json`** — Phase 6 owns that file per the DOC-02/DOC-04 boundary. The `deferred_total` metric in `runtime_coverage_summary.json` is computed from a lookup against the backlog file, not from the `gaps` array.
  - **No task in 09a or 09b explicitly drives `deferred_total` to 0**, yet Plan 09b Task 4 Step 4 asserts it as a gate that will `exit 1` on failure with no recovery path.
  - Plan 09a's own interface block admits: _"After Plan 09a, deferred_total should be exactly 1 (the R9 GLOBAL_FCX_HANDLER excluded symbol still in deferred backlog) plus any non-promoted entries the deferred backlog still tracks separately from the gap report."_ — this contradicts the Plan 09b closure gate.
  - **Required verification before execution**: Run the helper in dry-run mode against a scratch branch to empirically measure the deferred_total delta, then decide whether additional explicit backlog handling is needed OR whether the "1040" number is actually stale/different metric.

#### MEDIUM

- **MEDIUM — No dedicated Task 0 CONSTRUCTOR-INVENTORY.md for Plan 09a** (Plans 02-08 all had this as a separate pre-task). Plan 09a embeds constructor verification inside Task 1 Step 2 via inline routing-map comments, but with 14 owners and ~80+ classes, this is a scale jump from Plan 08 (2 owners). REVIEWS Concern #3 flagged Plan 04's constructor guessing failure mode; the Plan 09a pattern re-introduces that risk at 10× scale. **Suggest**: Add Task 0 Step 0 that writes `03-09a-CONSTRUCTOR-INVENTORY.md` with verified signatures for every class in every owner, matching the Plans 02-08 pattern.

- **MEDIUM — Plan 09b Task 2 commits leave the repo in a data-inconsistent state** (Plan 09b Task 2 Step 10 + Task 3 Step 2).
  - Task 2 deletes `tierDefinitions.tier2` from `parity_contract.json` and deletes the gap branches from `generate_baseline.py`, but does NOT regenerate `parity_diff_report.json` (which still contains `tier2_gap_total: 736`).
  - Task 2 also adds a new test `test_tier2_gap_total_removed_from_summary` that reads `parity_diff_report.json::summary` — this test will FAIL at Task 2's commit and only pass after Task 3's baseline refresh.
  - If anyone runs `pytest tools/python_api_parity/tests -q` between the Task 2 and Task 3 commits (e.g., a CI pipeline, a git hook, or a bisect), they'll see a failing test.
  - **Suggest**: Either combine Tasks 2+3 into a single atomic commit OR have Task 2 NOT add the new test (move the new-test addition to Task 3, where baseline is already refreshed). The acceptance criterion at Task 2 already requires the xfail flip test passes — it doesn't need the new test to also exist yet.

- **MEDIUM — Cascade audit path list missing .github/workflows, tools/cxx_api_parity, and CI config** (Plan 09b Task 1 Step 1 `$paths` array).
  - Audited paths: `tools/python_api_parity/*.py`, `tools/node_api_parity/*.py`, `docs/api/*.md`, `docs/implementation/python_api_parity/*.md`, `ClassicLib-rs/python-bindings/*.py`, `ClassicLib-rs/python-bindings/tests/*.py`, `ClassicLib-rs/*.py`.
  - Not audited: `.github/workflows/*.yml`, `.github/workflows/*.yaml`, `ci*.yml`, `tools/cxx_api_parity/*.py` (should be zero hits per Phase 1 D-04 but verify), `*.ps1` build scripts, `tools/*.py` root-level, `docs/api/binding-*.md`.
  - If any CI job or build script reads `tier2_gap_total` from the JSON, the deletion will silently break it.
  - **Suggest**: Expand `$paths` to include `.github/`, `*.ps1`, `tools/*.py` (top-level), and `tools/cxx_api_parity/`.

- **MEDIUM — No dry-run projection step for `deferred_total` reduction** (Plan 09a Task 0 or Task 4).
  - Plan 09a doesn't pre-verify that its 600 planned rows will resolve the expected number of deferred backlog entries. Plan 08 SUMMARY empirically showed a 1% reduction ratio in similar scope; if this holds, 09b's gate fails.
  - **Suggest**: Add a Task 0 Step 6 that loads `deferred_runtime_backlog.json`, intersects with the planned contract-row binding identifiers, and reports `projected_deferred_total_after_plan_09a` so the operator can decide whether to proceed.

- **MEDIUM — Residual count discrepancy with STATE.md** (Plan 09a frontmatter vs STATE.md Blockers).
  - Plan 09a: `scangame=213, path=83, constants=58, ..., total=736`
  - STATE.md: `scangame=218, path=85, constants=59, ..., total=~913`
  - Differences span 7 owners with 21 total rows unaccounted for.
  - Plan 09a claims "verified 2026-04-09 against post-Plan-08 parity_diff_report.json" but STATE.md's numbers are from Plan 01's A10 sizing. A 21-row delta is small relative to the total but non-zero, suggesting either Plans 02-08 resolved some rows outside their scanlog/config/version_registry/shared/file_io focus (unexpected) OR the numbers are simply snapshots from different times.
  - **Suggest**: Have Task 0 Step 1 explicitly re-refresh the baseline and commit the ground-truth count BEFORE Task 1 runs, so any downstream assertion uses the post-refresh count, not the frontmatter literal.

- **MEDIUM — Scale of hand-authored smoke tests in Plan 09a Task 2** (expected 80-150 tests).
  - Plan 08 authored 49 tests with a Task 0 method inventory as input; Plan 09a expects 2-3× more tests without a comparable pre-task inventory.
  - The plan provides a test template but no helper script to scaffold tests from the routing map. With ~14 owners × 6-10 tests each plus rust-only guards, hand-authoring 100+ tests in a single task is error-prone.
  - **Suggest**: Author a scaffolding helper (`_scaffold_plan09a_tests.py`) that reads `_build_plan09a_rows.py`'s routing maps and emits test skeletons, then hand-verify/tune each one. The Plan 08 SUMMARY's 6 Rule-1 test assumption bugs at 49-test scale predict ~12-18 bugs at 100-150-test scale without tooling.

#### LOW

- **LOW — Audit classifications not mechanically verified** (Plan 09b Task 1 Step 2). The cascade audit asks the executor to classify each hit as `CODE_READ | DOCS_PROSE | TEST_ASSERTION | BASELINE_JSON | HISTORICAL_COMMENT`, but the acceptance criterion only checks the file exists and contains certain strings. A sloppy classification could hide a real consumer under `HISTORICAL_COMMENT`. Low severity because the 09b verification chain would catch a broken consumer via test failures.

- **LOW — `testSuite` field scalar-vs-array convention** (Plan 09a Task 3 — the 14 new selector entries).
  - Plan 02 established that `testSuite` is a scalar string and created a SEPARATE selector entry for new smoke suites rather than comma-joining (R8 pattern). Plan 08 followed this by NOT bumping the existing `python-tier1-shared` and `python-tier1-file_io` entries.
  - Plan 09a's Task 3 Step 2 BUMPS the existing `python-tier1-scanlog` contractCount to 251 and implicitly assumes the existing testSuite points at a suite that covers the new 4 method residuals — but those 4 tests are in `test_promoted_residuals_smoke.py`, not the existing scanlog suites.
  - The gate's `testSuite` is informational/metadata (the check is via `contractSelector` + hash), so this is mostly a documentation nit, but it's inconsistent with the Plan 02 R8 precedent that the other 14 new selectors use `testSuite: .../test_promoted_residuals_smoke.py`.
  - **Suggest**: Either create a separate `python-tier1-scanlog-wave10-residuals` selector for the 4 method residuals (R8 precedent) OR update the existing `python-tier1-scanlog` selector's testSuite to a list/multi-suite hint.

- **LOW — Acceptance criterion for Task 1 `tier1Mappings >= 1100` is imprecise** (Plan 09a Task 1 verify).
  - 505 baseline + 736 residuals - dedup savings = somewhere between 1100 and 1240. The plan uses `>= 1100` as a floor but doesn't capture the actual number in the SUMMARY for Plan 09b to reference.
  - Plan 09b's own acceptance doesn't reference an exact tier1Mappings count either.
  - **Suggest**: Have Task 4 SUMMARY record the exact post-plan number so Plan 09b can cross-check it hasn't drifted.

- **LOW — 09a excludes `tools/node_api_parity/tests` from cascade audit but 09b does** (Plan 09b Task 1 Step 1). Minor path-list asymmetry; not a correctness issue.

- **LOW — mypy --strict run-per-file vs run-all** (Plan 09b Task 4 Step 1). The foreach loop runs mypy once per stub. Running mypy once with all 19 files passed as arguments would be faster and catch any cross-stub type-reference issues (e.g., if classic_scanlog.pyi references a type from classic_config.pyi). The current per-file approach won't detect these.

### Suggestions

1. **Rewrite 09a Task 0 wrapper check with method-aware logic**:
   ```python
   def find_wrapper(owner, residual) -> Path | None:
       if residual["gap_type"] == "rust_unmapped":
           return Path("<rust-only, uses @rust proxy>")  # skip check
       py_path = residual.get("python_export_path", "")
       if "." in py_path:
           # Method residual — verify class wrapper exists, not method bare name
           class_name = py_path.split(".")[0]
           return find_class_wrapper(owner, class_name)
       # Top-level residual — use current bare-name search
       return find_symbol_wrapper(owner, residual.get("python_export") or residual.get("rust_symbol"))
   ```

2. **Add `_build_plan09a_rows.py --dry-run` mode** that reports:
   - Projected `tier1Mappings.length` after promotion
   - Projected `deferred_total` after promotion (by intersecting planned binding identifiers with `deferred_runtime_backlog.json::entries`)
   - Count of residuals that would fall through to the wrapper check (and thus potentially hit BLOCKERS)

   Run this at Task 0 BEFORE Task 1 so the operator can assess whether Plan 09b's deferred_total gate will be reachable.

3. **Add Plan 09a Task 0 constructor inventory step** (match Plans 02-08 pattern):
   - Read every `#[pymethods] impl Py<Class> { #[new] fn new }` across all 14 owner `-py/src/*.rs` files
   - Write `.planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md`
   - Task 2's smoke tests read this file for signatures rather than embedding the verification in routing-map comments

4. **Combine Plan 09b Tasks 2+3 into a single atomic commit** OR move `test_tier2_gap_total_removed_from_summary` from Task 2 to Task 3. The current split creates a bisect-breaking intermediate state.

5. **Expand Plan 09b Task 1 cascade audit paths**:
   ```powershell
   $paths = @(
       # ... existing paths ...
       '.github/workflows/*.yml', '.github/workflows/*.yaml',
       'tools/cxx_api_parity/*.py',
       'tools/*.py',  # repo-root tools
       'rebuild_rust.ps1',
       'ClassicLib-rs/*.py'  # already present — note top-level only
   )
   ```

6. **Add a Plan 09b Task 4 diagnostic dump** BEFORE the `deferred_total == 0` assertion: if non-zero, print the list of offending backlog entries with owner/binding identifier so the operator has actionable info rather than a bare `exit 1`. Something like:
   ```powershell
   if ($summary.summary.deferred_total -ne 0) {
       $backlog = Get-Content 'docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json' -Raw | ConvertFrom-Json
       $contract_bindings = @{}  # build map from tier1Mappings
       $stuck = $backlog.entries | Where-Object { -not $contract_bindings.ContainsKey($_.bindingIdentifiers[0]) }
       $stuck | ForEach-Object { Write-Host "STUCK: $($_.coverageId) -> $($_.bindingIdentifiers -join ', ')" }
       Write-Error "PYT-06 FAILED with $($stuck.Count) stuck entries"
       exit 1
   }
   ```

7. **Run `mypy --strict` in batch (one command) rather than per-file**:
   ```powershell
   uv run ... mypy --strict @stubs
   ```
   Catches cross-stub type reference issues; also faster.

### Risk Assessment

**HIGH** — Plan 09a will very likely halt at Task 0 due to the wrapper-existence check false-closing on method and rust-only residuals, preventing Task 1 from running at all. Even if Task 0 is fixed manually at execution time, Plan 09b's final `deferred_total == 0` gate has no clear path to success: Plan 08's empirical ratio (156 rows → 2 deferred reduction) projects 09a's 600 rows will reduce deferred_total by ~6-12, ending nowhere near 0. PYT-06 is the milestone-closing gate, so this blocks Phase 3 completion.

Plan 09b in isolation is well-designed (cascade audit, line-number re-verification, explicit 19-stub enumeration, xfail flip, verbatim coverage-completeness one-liner) and would be LOW-MEDIUM risk if 09a delivered a clean tier1Mappings state and the deferred_total mechanics were verified. The risks are concentrated at the 09a wrapper check and the unverified deferred_total pathway — both addressable with a few hours of pre-execution work but both critical to resolve before running Task 1 of 09a.

**Recommended gate before execution**: Resolve both HIGH concerns (wrapper check logic + deferred_total dry-run projection) on a scratch branch before committing Plan 09a Task 0. If the dry-run shows deferred_total would land at ~300-400 after 09a+09b, scope an additional explicit backlog-handling task BEFORE 09b's final gate rather than discovering the gap at plan close.

---

## Codex (GPT-5.4) Review

### Summary

09a and 09b are a major improvement over the old monolithic Plan 09. The sequencing is mostly right: 09a does residual promotion, 09b does structural cleanup and final verification. The remaining problems are not architectural, but they are real correctness issues: 09a's registry-hash instructions do not match the live selector implementation, 09b's cleanup plan does not fully account for existing tests/readers, and both plans slightly overstate how `deferred_total` reaches zero.

### Strengths

- 09a correctly treats Plan 08 as frozen ground truth and hard-pins `file_io == 95` and `shared == 61`, which is consistent with Plan 08's shipped summary.
- 09a now sources residuals from live `parity_diff_report.json::gaps` and explicitly excludes `GLOBAL_FCX_HANDLER`, `file_io`, and `shared`, which is the right A10-driven shape.
- 09a's fail-closed `03-09a-BLOCKERS.md` concept is directionally correct and much safer than silent skipping.
- 09b's pre-delete cascade audit and explicit line-number re-verification are good safeguards before touching `tools/python_api_parity/generate_baseline.py` around line 672.
- 09b's mypy sweep explicitly includes the foundation stub path `ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi`, which avoids the common "18 under python-bindings, 1 elsewhere" miss.

### Concerns

- **HIGH** — 09a Task 3 / must_haves hardcodes `contractIdsHash` as `sha256[:16]`, and its acceptance check enforces a 16-char hash (09a line 820). The live selector engine uses **full SHA-256** over newline-joined sorted IDs, not 16 chars: see `tools/binding_parity_runtime_coverage.py::_stable_id_hash` (L57) and selector validation at L81-103. **If executed as written, 09a will produce `registry_mismatch_total > 0` and fail the gate.**
- **HIGH** — 09a says 09b will drop `deferred_total` to 0 "mechanically" after Tier-2 branch deletion (09a lines 925 and 949). That is not how the current tooling works. `deferred_total` is computed from `trackedSurface` classifications in `tools/binding_parity_runtime_coverage.py::build_coverage_summary()` L221, specifically L313. Deleting `tier2_gap_total` and markdown columns in 09b is **not sufficient** if any deferred-classified rows survive 09a.
- **HIGH** — 09a's fail-closed wrapper test at line 50 only proves textual wrapper presence by grep. It does not prove crate-root export visibility, Python export-path alignment, or stub coverage. False positives can pass Task 0 and only explode later during row authoring or verification.
- **HIGH** — 09b says every affected reader will be audited and updated (lines 31 and 71), but an existing test already asserts `python_unmapped` exists in `ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py:169-170`. That file is **not in 09b's declared write set**. If 09b deletes `python_unmapped`/`rust_unmapped` without updating that test, it will regress shipped tooling tests.
- **MEDIUM** — 09b's explicit 19-stub mypy list is correct, but its `validate_stubs.py` cross-check does not actually cover `classic_shared`. The validator only walks `ClassicLib-rs/python-bindings` crates ending in `-py` (L318, L333-352). There is no foundation handling, so `classic_shared` is only protected by the explicit mypy step, not by the secondary validator.
- **MEDIUM** — 09b's cascade-audit method is good, but its search scope at Task 1 line 278 is narrower than its "every reader" claim. It is selective-glob based, not a repo-wide recursive search.
- **MEDIUM** — 09a promotes the four scanlog method residuals into `python-tier1-scanlog` (lines 231, 805-807), but also says `python-tier2-scanlog-runtime` is preserved (line 233). That preserved tier-2 entry currently points to those exact four methods in `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json:275-287`. The plan needs to explain the intended post-state, otherwise registry semantics become stale.
- **LOW** — 09a's `tier1Mappings >= 1100` acceptance threshold at line 582 is too loose to prove A10 correctness by owner. It can pass with the wrong distribution.

### Suggestions

- Change 09a's hash instructions to exactly match `_stable_id_hash`: full 64-char SHA-256 of newline-joined sorted IDs. Better yet, compute hashes by importing the function or by running the same helper code path.
- Strengthen 09a's BLOCKERS gate so it validates against parsed Rust/Python surfaces, not grep hits. The blocker should fail if a symbol lacks a real crate-root export, a resolvable Python export path, or stub presence.
- Add an explicit 09a postcondition: enumerate all remaining `deferred`-classified tracked rows from `runtime_coverage_summary.json`, and require that the only allowed residual before 09b is the intentional R9 exclusion set. That makes 09b's PYT-06 target falsifiable.
- Add `test_python_parity_tooling.py` to 09b's write set and update/remove the `python_unmapped` expectation in the same commit as the branch deletion.
- Clarify in 09b that `validate_stubs.py` covers 18 `python-bindings` crates, while `classic_shared` is covered by explicit mypy unless the validator is extended to scan `foundation/`.
- Replace 09b's selective-glob cascade audit with a recursive `rg` over the repo for `tier2_gap_total|python_unmapped|rust_unmapped|tierDefinitions.*tier2`.
- Either retire or repurpose `python-tier2-scanlog-runtime` once those four methods become tier1, so registry semantics stay aligned with the contract.

### Risk Assessment

**HIGH**

The rewrite is much better, but if executed literally it is still likely to fail at the endgame. The two biggest risks are concrete and code-backed: 09a's hash algorithm is wrong for the live selector engine, and 09b's cleanup plan does not yet fully cover the known test surface it is invalidating. Once those are fixed, the overall strategy drops to medium risk.

**Tokens used:** 301,964

---

## Recommended Revision Targets (if running `/gsd:plan-phase 3 --reviews`)

**CRITICAL (both reviewers agree — HARD BLOCKERS before execution):**

1. **09a Task 0 wrapper-existence check — fundamentally broken for method and rust-only residuals**. Rewrite the `find_wrapper` helper per Claude's suggestion #1: skip the check for `gap_type == rust_unmapped`, and for method residuals (`"." in python_export_path`) verify the OUTER class wrapper exists, not the bare method name. This prevents Plan 09a from halting at Task 0 on hundreds of legitimate symbols.

2. **09a contractIdsHash algorithm — wrong (sha256[:16] vs full 64-char)**. Rewrite 09a Task 3 must_haves and line 820 acceptance to match `_stable_id_hash` in `tools/binding_parity_runtime_coverage.py:57`. Prefer importing the function or running the same helper code path rather than reimplementing.

3. **09b deferred_total path to 0 — unjustified, contradicted by plan's own interface block**. Two independent traces (Claude: DOC-02/DOC-04 backlog-file ownership; Codex: `build_coverage_summary()` L313 trackedSurface classifications) both conclude the plan's assumption is wrong. **Required pre-execution verification**: empirically trace the `deferred_total` computation path on a scratch branch, and either (a) scope an explicit backlog-handling task before 09b's final gate, (b) prove the metric collapses mechanically given the planned row additions, or (c) adjust the PYT-06 gate to a reachable target given the Phase 3 ÷ Phase 6 ownership boundary.

4. **09b missing write: `test_python_parity_tooling.py:169-170`** — existing test asserts `python_unmapped` exists; will regress when 09b deletes the branch. Add this file to 09b `files_modified` and update/remove the assertion in the same commit as the deletion.

**HIGH (one reviewer raised, converging with the other's analysis):**

5. **Add Plan 09a Task 0 CONSTRUCTOR-INVENTORY.md** (Claude's finding — matches Plans 02-08 precedent). 14 owners × 6-10 classes is a scale jump from Plan 08's 2 owners. Re-introduces Round 1 REVIEWS concern #3 (constructor guessing) at 10× scale.

6. **Add `_build_plan09a_rows.py --dry-run` projection** (Claude's finding) — pre-verify projected `tier1Mappings.length`, projected `deferred_total`, and count of residuals that would hit the wrapper-check BLOCKERS funnel. Run at Task 0 before Task 1 commits anything.

**MEDIUM (targeted fixes):**

7. Combine Plan 09b Tasks 2+3 into a single atomic commit (or move `test_tier2_gap_total_removed_from_summary` from Task 2 to Task 3) to avoid bisect-breaking intermediate state.

8. Expand Plan 09b Task 1 cascade audit to include `.github/workflows/`, `tools/cxx_api_parity/`, repo-root `tools/*.py`, and `*.ps1` build scripts. Replace selective-glob with recursive `rg` over the repo.

9. Resolve the residual count discrepancy (Plan 09a: 736 vs STATE.md: ~913, 21-row delta) by re-refreshing the baseline in Task 0 Step 1 and using the post-refresh count as ground truth.

10. Author a scaffolding helper `_scaffold_plan09a_tests.py` to generate the 100-150 smoke-test skeletons from the routing map, then hand-verify/tune each. Plan 08's 6 Rule-1 bugs at 49-test scale predict 12-18 bugs at 09a's scale without tooling.

11. Clarify `validate_stubs.py` scope — it covers 18 `python-bindings` crates but NOT `classic_shared` (foundation path). Either extend the validator or document explicitly that `classic_shared` is protected only by the explicit mypy step.

12. Retire or repurpose `python-tier2-scanlog-runtime` registry entry (currently points to the 4 methods 09a promotes — stale semantics after promotion).

**LOW (polish):**

13. 09b: run `mypy --strict @stubs` in one command to catch cross-stub type references, not per-file.
14. 09a Task 1: capture exact post-plan `tier1Mappings` count in SUMMARY for 09b to cross-check.
15. 09a Task 3: either create a separate `python-tier1-scanlog-wave10-residuals` selector (R8 precedent) or update `python-tier1-scanlog` testSuite to reference `test_promoted_residuals_smoke.py`.

---

## Recommended Next Action

Given that both reviewers independently raised HIGH-severity findings that would halt or invalidate Plan 09a execution, **do NOT run `/gsd:execute-phase 3` as-is**. Two recovery paths:

- **Path A (targeted patching)**: Apply fixes #1-4 manually to 09a/09b on a scratch branch, then run the empirical `deferred_total` trace. If the trace reveals the PYT-06 gate is structurally unreachable in Phase 3 alone (Phase 6 owns the backlog), escalate to a phase-scope discussion before any execution.

- **Path B (formal replan)**: Run `/gsd:plan-phase 3 --reviews` which will feed this REVIEWS.md back into gsd-planner, which will rewrite 09a/09b to address all CRITICAL/HIGH items structurally. This is the cleaner path but consumes more context.

The **deferred_total path** (CRITICAL #3) is the most important single finding — it may reveal that Phase 3's PYT-06 gate was scoped with an incorrect mental model of how the metric is computed, and that a cross-phase boundary adjustment with Phase 6 is required regardless of how 09a's wrapper check is fixed.
