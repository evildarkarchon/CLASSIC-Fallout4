---
phase: 3
reviewers: [claude, codex]
reviewed_at: 2026-04-08T02:29:03-07:00
plans_reviewed:
  - 03-01-tooling-expansion-PLAN.md
  - 03-02-scanlog-wave1-parsing-primitives-PLAN.md
  - 03-03-scanlog-wave2-detection-and-analysis-PLAN.md
  - 03-04-scanlog-wave3a-orchestration-core-PLAN.md
  - 03-05-scanlog-wave3b-report-standalone-PLAN.md
  - 03-06-config-promotion-PLAN.md
  - 03-07-version-registry-promotion-PLAN.md
  - 03-08-classic-shared-and-file-io-aux-PLAN.md
  - 03-09-tier2-cleanup-and-final-sweep-PLAN.md
---

# Cross-AI Plan Review — Phase 3: Python Tier Collapse

> Independent peer review by Claude Opus 4.6 (separate session) and Codex (GPT-5.4). Both reviewers received the same 428KB prompt containing PROJECT.md, ROADMAP, REQUIREMENTS, CONTEXT.md (with Research Amendments A1–A10), RESEARCH.md, VALIDATION.md, and all 9 PLAN.md files.

---

## Consensus Summary

Both reviewers converged on **Plan 09 being the weakest link** (scope too large + unsound residual discovery + architectural gap) and on **Plans 06/07 failing D-07 via hasattr-only tests**. They diverged primarily on Plan 01's execution-time risks (Claude flagged sys.path + ownerModules race; Codex flagged none) and Plan 08's aux cleanup instruction (Codex caught a concrete file-path error Claude missed).

### Agreed Strengths (both reviewers)

- Research Amendments A1–A10 are integrated well — A6 (Wave 3 sub-module naming) and A7 (9-plan split with report standalone) are honored consistently
- A1 (`pub use` targets `-core/lib.rs`, not `-py/lib.rs`) is correctly verified across Plans 02–07
- A3 (Pitfall 2 guard fires ~0 rows) is noted in every promotion plan
- A8 (`RuntimeStats` via factory; `classic_shared.pyi` already complete) is honored in Plan 08
- Pitfall 2 guard shape in Plan 01 matches RESEARCH Q4 recommendation
- Per-plan atomic commit cadence (D-06) and baseline refresh cadence (D-03) are enforced
- Sequential wave ordering is the correct default (shared baseline files make parallelism risky)

### Agreed Concerns (both reviewers — highest priority)

| # | Concern | Severity | Affected Plans |
|---|---------|:--:|---|
| 1 | **hasattr-only smoke tests violate D-07** (""construct + call one real method"") | HIGH | 06, 07 (both reviewers HIGH); 02, 03, 04, 05 (MEDIUM — partial coverage gaps) |
| 2 | **Plan 09 A10 residual discovery is unsound / under-specified** — sources residuals from wrong file, allows skipping symbols without wrappers, contradicts `deferred_total == 0` goal | HIGH | 09 |
| 3 | **Constructor signatures guessed without verification** — tests scaffold `Class({})` or `Class(positional)` without reading `#[pymethods] fn new` | MEDIUM-HIGH | 02, 03, 04, 05, 08 |
| 4 | **Tier-2 migration rows not enumerated concretely** — plans say ""delete 4 rows"" or ""delete 1 row"" without specifying `coverageId` values | MEDIUM-HIGH | 06, 07 |
| 5 | **RustOrchestrator / ReportGenerator / AnalysisResult weakly exercised** — stops at construction or non-None check | MEDIUM | 04, 05 |

### Divergent Views

- **Plan 01 Risk Assessment**: Claude says MEDIUM-HIGH (flagging sys.path pollution in test files and `ownerModules` hand-edit vs `--write-baseline` regenerate race). Codex says LOW. Claude's concerns are executable risks that only surface at implementation time — Codex may have given them less weight because they're TDD fixup issues, not architectural flaws.
- **Plan 08 `python-deferred-aux-297` cleanup target**: Codex flags HIGH ("The plan tells the executor to delete `python-deferred-aux-297` from the runtime registry, but that id lives in `deferred_runtime_backlog.json`, not in `runtime_coverage_registry.json`."). Claude didn't mention this specific error — it appears Claude missed the file-path precision check while focusing on broader architectural coordination.
- **Plan 09 architectural fix**: Claude recommends KEEPING gap detection as a renamed `tier1_unmapped` (preserving visibility into unmapped Rust symbols). Codex recommends fail-closed residual sourcing from `parity_diff_report.json`. Both agree the current design is broken; they propose different fixes.
- **Plan 09 should be split**: Claude explicitly recommends Plan 09a (residuals) + Plan 09b (cleanup). Codex says "I do not think a brand-new Phase 3 plan is strictly required if Plan 09 is tightened, but one additional 'residual wrapper closure' plan would be justified if Plan 1's A10 report shows symbols without Python wrappers." Claude is more aggressive on scope-splitting.

### Unique Findings

**Unique to Codex (not in Claude):**
- Plan 01: Missing drift guard for hard-coded owner rendering tuple at `generate_baseline.py:682`
- Plan 02: `testSuite` comma-joined string schema mismatch (registry schema defines scalar `testSuite`, not a list)
- Plan 08: **python-deferred-aux-297 lives in `deferred_runtime_backlog.json:3702`, not `runtime_coverage_registry.json`** — plan's delete instruction targets the wrong file

**Unique to Claude (not in Codex):**
- Plan 01: `sys.path.insert` pollution in test files — pytest collection may hit `ModuleNotFoundError`
- Plan 01: `ownerModules` hand-edit vs `--write-baseline` regenerate race
- Plan 03: `GLOBAL_FCX_HANDLER` as a contract row is architecturally suspect (static, not module-level Python attr)
- Plan 03: FCX global state test isolation — needs `conftest.py` reset fixture
- Plan 07: `UnknownVersionStrategy` vs `UnknownVersionHandling` naming unresolved
- Plan 08: `contractIdsHash` placeholder handling — need to verify `generate_baseline.py` recomputes selector hashes
- Plan 08/09: **file_io coordination conflict** — Plan 08 claims 5 file_io rows but Plan 09 tries to promote A10 residuals from `classic-file-io-core`; who owns the rest?
- Plan 09: `tier2_gap_total` deletion cascade effects unenumerated
- Cross-phase: Missing Pitfall 4 upfront audit (every `#[pyclass]` has matching `m.add_class::<>()?;`)
- Cross-phase: `classic-crashgen-settings-core` type routing unresolved — types flow through 3 bindings per A5, but contract schema doesn't handle multi-binding re-use

---

## Recommended Revision Targets (if running `/gsd:plan-phase 3 --reviews`)

**HIGH priority (both reviewers agree):**
1. **Plan 06/07**: Rewrite smoke tests to use YAML fixtures / `VersionRegistry::default()` singleton rather than `hasattr` checks. Enumerate exact `coverageId` values for Tier-2 migrations.
2. **Plan 09**: Split into 09a (residuals) + 09b (cleanup). Change residual source from `rust_api_surface.json` → `parity_diff_report.json`. Resolve the unmapped-symbol architecture (either rename to `tier1_unmapped` per Claude, or fail-closed per Codex).
3. **Plan 08**: Fix the aux entry cleanup target (`deferred_runtime_backlog.json`, NOT `runtime_coverage_registry.json`).
4. **Plan 08/09 coordination**: Explicitly assign ALL file_io rows to Plan 08 and exclude file_io from Plan 09 residuals.

**MEDIUM priority:**
5. **Plans 02–05**: Pre-Task-1 step: read every `#[pymethods] fn new` in affected `-py` crates and record exact constructor signatures before scaffolding tests.
6. **Plan 01**: Replace `sys.path.insert` with `conftest.py`; verify `generate_baseline.py --write-baseline` `ownerModules` handling before hand-editing.
7. **Plan 03**: Exclude `GLOBAL_FCX_HANDLER` from contract rows; add FCX state reset fixture in `conftest.py`.
8. **Plan 04**: Upgrade `ScanProgressPhase` test from `dir()` to specific variant access; add at least one `CrashgenRegistry` method call.
9. **Plan 05**: Add fixture-backed `ReportGenerator.generate()` call via minimal `AnalysisResult`.
10. **Plan 07**: Grep `classic-version-registry-core/src/lib.rs` for exact enum name before authoring contract rows.

**LOW priority:**
11. **Plan 01**: Add owner-rendering drift guard; change `>= 59` to `== 59`; use `strict=True` on xfail tests.
12. **Plan 02**: Fix `testSuite` comma-joined schema — use multiple registry entries.

---


## Claude Review (Opus 4.6 — separate session)

# Phase 3 Cross-AI Plan Review — v9.1.0-bindings Python Tier Collapse

**Reviewer:** Claude Opus 4.6 (1M context)
**Review date:** 2026-04-08
**Plans reviewed:** 03-01 through 03-09 (9 plans)

---

## Plan 03-01: Tooling Expansion

### Summary
Keystone plan that expands `RUST_TARGET_CRATES`/`PYTHON_TARGET_MODULES` from 3 to 19, adds the Pitfall 2 guard to `check_parity_gate.py`, creates Wave 0 test scaffolding, and captures an A10 sizing report. Well-structured and TDD-oriented, with correct honoring of A5 (excludes `classic-crashgen-settings-core`) and A3 (guard fires on ~0 rows). However, it has real-world integration pitfalls around import paths and baseline generation semantics.

### Strengths
- Explicit verification that `'classic-crashgen-settings-core' not in RUST_TARGET_CRATES` (Task 1 test) honors A5
- TDD Red→Green flow with test scaffolding in Task 1, implementation in Tasks 2-3, verification in Task 4
- A10 sizing report in Task 4 Step 4 is correctly captured for downstream plan budgets
- Pitfall 2 guard shape (standalone `validate_contract_rust_symbols` helper) matches RESEARCH Q4 recommendation
- `_OWNER_RENDER_ORDER` constant addresses the hard-coded 4-owner tuple at line 682 of `render_diff_markdown()`

### Concerns
- **HIGH — sys.path manipulation in test files**: Task 1's test files use `sys.path.insert(0, str(REPO_ROOT / "tools" / "python_api_parity"))` and then `from generate_baseline import ...`. This pollutes sys.path globally and conflicts with any existing `tools.python_api_parity.generate_baseline` import path. If the repo uses package-style imports elsewhere, pytest collection will produce `ModuleNotFoundError` or double-import issues. Recommend `importlib.util.spec_from_file_location` or a proper `conftest.py` with the path insertion.

- **HIGH — `parity_contract.json::ownerModules` hand-edit vs `--write-baseline` race**: Task 4 Step 1 says to hand-edit `ownerModules` enum, then Step 2 runs `generate_baseline.py --write-baseline`. If `--write-baseline` regenerates `ownerModules` from scratch (or derives it from `RUST_OWNER_BY_CRATE`), the manual edit is overwritten. The plan says "Adapt the JSON shape if `ownerModules` is an object rather than an array" but doesn't verify whether `generate_baseline.py` treats `ownerModules` as authoritative. **Recommend reading `generate_baseline.py::generate_parity_contract()` first** to confirm whether it emits `ownerModules` from the dict constants or preserves existing values.

- **MEDIUM — `_OWNER_RENDER_ORDER` placement ambiguity**: Task 2 says "Define `_OWNER_RENDER_ORDER` at module top-level near line 53, just below `SQUAD_BY_OWNER`" — line numbers shift after the 19-entry expansion. Recommend an explicit anchor text like "Insert after the closing `}` of `SQUAD_BY_OWNER` dict and before any function definitions."

- **MEDIUM — `test_tier1_contract_total_baseline_floor` uses `>= 59`**: Plan 01 Task 4 only refreshes the baseline — it does NOT add new rows. So `tier1Mappings.length` should remain exactly 59 after Plan 01. Using `>= 59` as the floor makes the test effectively unenforceable. Recommend `== 59` for Plan 01's snapshot with an explicit comment that Plans 2-8 bump this number.

- **MEDIUM — `test_check_parity_gate.py::test_tier2_definition_removed_after_plan_9` uses `strict=False`**: With `strict=False`, an xfail test that accidentally passes doesn't fail. This means if `tierDefinitions.tier2` is removed prematurely (e.g., by Plan 02 accidentally), the xfail still passes silently. Recommend `strict=True` (or just document the expected execution order clearly).

- **LOW — A10 sizing report captured in PowerShell, not Python**: Task 4 Step 4 uses PowerShell to extract `gap_counts_by_owner_tier`. This means the sizing data is human-only and not programmatically consumable by Plan 09. Recommend writing the sizing data to `.planning/phases/03-python-tier-collapse/03-01-A10-sizing.json` (machine-readable) in addition to the SUMMARY prose.

### Suggestions
1. Add a `conftest.py` under `tools/python_api_parity/tests/` that handles the sys.path insertion once, then all test files can use clean `from generate_baseline import ...` imports.
2. Before Task 4 Step 1, read `generate_baseline.py::generate_parity_contract()` to verify `ownerModules` handling.
3. Convert the A10 sizing PowerShell one-liner to a proper Python script at `tools/python_api_parity/size_residuals.py` that writes machine-readable output.
4. Change `test_tier1_contract_total_baseline_floor` from `>= 59` to `== 59` with a comment.

### Risk Assessment
**MEDIUM-HIGH** — As the keystone plan, any failure here cascades. The sys.path pollution and `ownerModules` hand-edit/regenerate interaction are real blockers that may force re-work mid-execution.

---

## Plan 03-02: Scanlog Wave 1 (Parsing Primitives)

### Summary
Promotes 74 Wave 1 scanlog rows across 6 sub-modules (parser, formid, formid_analyzer, record_scanner, plugin_analyzer, patterns). Correctly honors A3 (no `pub use` additions expected). The plan establishes the per-class smoke test pattern that downstream waves copy. The primary concern is scaffolded test signatures that depend on PyO3 wrapper details the plan doesn't fully verify upfront.

### Strengths
- 74-row target matches RESEARCH Q2 count precisely (20+10+16+11+12+5)
- Task 1 explicitly verifies A3 by grepping `classic-scanlog-core/src/lib.rs` lines 46-71
- Atomic single-commit pattern per D-06 is enforced across all 4 tasks
- Task 4 correctly bumps `runtime_coverage_registry.json::python-tier1-scanlog::contractCount` from 20 → 94 with matching math

### Concerns
- **HIGH — Constructor signatures guessed in Task 3 scaffold**: The smoke test scaffold uses `RustFormIDAnalyzer({})`, `FormIDAnalyzerCore({})`, `PatternMatcher([])` — all passing raw empty containers. RESEARCH Q6 correctly notes "Verify exact constructor signatures" but the scaffold ASSUMES these shapes. If any wrapper requires a config struct or keyword args (e.g., `RustFormIDAnalyzer(config={"patterns": [...]})`), the test fails on first run. Recommend Task 1 reads each wrapper's `#[pymethods] fn new` BEFORE authoring scaffold tests, then the scaffold uses verified signatures.

- **HIGH — `ScanOutput` test is hollow**: The `test_scan_output_field_access_after_parse` test constructs a LogParser, calls `parse_all_sections([])`, then asserts `result is not None`. This doesn't exercise `ScanOutput` at all — `parse_all_sections` returns a dict, not a `ScanOutput`. The plan acknowledges this: "Implementer: verify exact factory path from classic-scanlog-py/src/parser.rs" — but without resolution, the test satisfies PYT-05 on a technicality (imports OK) without actual `ScanOutput` construction. **Pitfall 4 risk**: if `ScanOutput` exists in the `.pyi` but isn't registered via `m.add_class::<>()`, the test won't catch it.

- **MEDIUM — `testSuite` multi-file semantics undefined**: Task 4 Step 1 suggests `"testSuite": "ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py,ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py"` (comma-separated). RESEARCH §Question 7 explicitly states that `testSuite` stores **a single file path**, not a list. The plan says "Or whatever multi-file separator the existing schema uses; check other entries for precedent" — but the schema doesn't have precedent for multi-file. Recommend either (a) creating multiple registry entries (one per test file), or (b) using only the new file and leaving the old one as unreferenced runtime backup.

- **MEDIUM — Row ID scheme uses `scanlog.parser.LogParser.parse_all_sections`** but PyO3 method rows historically use dotted notation without the class prefix in existing tier1Mappings. Plan should verify the existing 20 scanlog Tier-1 row IDs use the same `sub_module.Class.method` shape.

- **LOW — Serial execution risk for `detect_mods_important`**: Phase 2 noted that `detect_mods_important` tests need `serial_test::serial` annotation due to shared cache state. Wave 1 doesn't touch mod_detector (that's Wave 2), so this isn't blocking here, but Task 3 should note the pattern for Wave 2.

### Suggestions
1. Add a pre-Task-3 verification step that reads every `#[pymethods] fn new` in `classic-scanlog-py/src/parser.rs`, `formid.rs`, `formid_analyzer.rs`, `record_scanner.rs`, `plugin_analyzer.rs`, `patterns.rs` and records exact constructor signatures.
2. Rewrite `test_scan_output_field_access_after_parse` to go through the actual `ScanOutput` factory path once verified.
3. Create separate `python-tier1-scanlog-promoted` registry entry pointing at `test_promoted_scanlog_wave1_smoke.py`, leave the existing entry untouched.

### Risk Assessment
**MEDIUM** — Test scaffolding needs executor-side fix-up for ~6 classes; low architectural risk but real execution-time friction.

---

## Plan 03-03: Scanlog Wave 2 (Detection and Analysis)

### Summary
Promotes 58 Wave 2 rows (mod_detector, suspect_scanner, settings_validator, fcx_handler, gpu_detector). Critical integration point: `FcxResetError` from quick-260406-syy lands here. The main concerns are FCX global state test isolation and promotion of `GLOBAL_FCX_HANDLER` as a contract row.

### Strengths
- Explicit integration of FcxResetError from quick-260406-syy resolution is tracked in the `truths` frontmatter
- Clear 21-row breakdown for fcx_handler matching RESEARCH Q2
- Proper GPU enum variant coverage (NVIDIA/AMD/INTEL/UNKNOWN)

### Concerns
- **HIGH — `GLOBAL_FCX_HANDLER` as a contract row is suspect**: Task 1 explicitly includes `GLOBAL_FCX_HANDLER` (a `pub static`) in the 21 fcx_handler rows. While `parse_rust_surface()` handles `pub static` per RESEARCH §Reusable Assets, the `pythonExportPath` for a static doesn't map to any Python-importable symbol. The "Python-facing" side of a Rust `LazyLock` is typically a function that returns a lock guard, not a module-level attribute. Plan should either (a) exclude `GLOBAL_FCX_HANDLER` from the promotion list, or (b) explicitly document the `pythonKind` mapping for statics.

- **HIGH — FCX global state test isolation**: `test_fcx_mode_handler_construct_and_get_issues` constructs `FcxModeHandler(ignore_missing=True)` and reads global state. Without serial execution marking, parallel pytest runs (via `pytest -n auto` or similar) cause cross-test state pollution. Phase 2 explicitly noted this: "Pre-existing FCX global-state tests annotated with serial_test::serial to fix test isolation race". The Python test file needs equivalent — either `pytest.mark.flaky` and serial execution, or explicit `reset_fcx_global_state()` calls in test fixtures.

- **MEDIUM — `FcxModeHandler(ignore_missing=True)` signature is assumed**: Task 3 uses this constructor call, but the actual PyO3 signature could differ (e.g., requires a config dict, takes positional args only). Verify from `classic-scanlog-py/src/fcx_handler.rs::#[pymethods]`.

- **MEDIUM — `hasattr(classic_scanlog.GpuVendor, "NVIDIA")` tests**: GPU enum variants registered via `#[pyclass(eq, eq_int)]` are accessible via class attribute lookup, but `hasattr` only verifies the attribute NAME exists — not the enum semantics. If `PyGpuVendor` uses `#[pyo3(name = "...")]` renames, `NVIDIA`/`AMD`/`INTEL`/`UNKNOWN` may not be the actual variant names. Recommend direct access like `classic_scanlog.GpuVendor.NVIDIA` to force a real attribute lookup.

- **LOW — Task 4 deletes no Tier-2 registry rows**: Unlike Plan 06 and 07, Plan 03 doesn't delete any existing explicit-binding Tier-2 entries from `runtime_coverage_registry.json`. If the existing registry has a `python-tier2-scanlog-*-runtime` entry for FcxResetError (added by quick-260406-syy), it should be deleted here. Verify whether such an entry exists and delete if present.

### Suggestions
1. Exclude `GLOBAL_FCX_HANDLER` from the contract row list; document as an internal helper, not a public Python API.
2. Add a `conftest.py` fixture at `ClassicLib-rs/python-bindings/tests/conftest.py` that resets FCX global state before each `fcx_handler`-related test.
3. Verify `FcxModeHandler` constructor signature from `fcx_handler.rs::#[pymethods] fn new` before authoring the test.
4. Search for existing `python-tier2-*fcx*` registry entries and delete them in Task 4.

### Risk Assessment
**MEDIUM-HIGH** — FCX state management is historically flaky across binding boundaries. The static promotion is also architecturally questionable.

---

## Plan 03-04: Scanlog Wave 3a (Orchestration Core)

### Summary
Promotes ~50 Wave 3a rows across 6 sub-modules (orchestrator, papyrus, version, crashgen_registry, segment_key, error), explicitly excluding the report sub-module which gets its own Plan 05 per A7. Correctly honors A6 by using the real sub-module names (no `crashgen_rules` or `core_mod_convert` references).

### Strengths
- A6 honored: plan explicitly notes "No `scanlog.crashgen_rules.` or `scanlog.core_mod_convert.` IDs are authored"
- Clear separation from report (Plan 05)
- 14 test functions target matches D-07's per-class minimum
- Uses `dir()` discovery for enum variants (defensive against unknown variant names)

### Concerns
- **HIGH — `AnalysisConfig("Fallout4", False)` signature is fragile**: The plan scaffold assumes positional args `(game: str, fcx_mode: bool)`. If `AnalysisConfig` uses named arguments or takes an enum instead of a string (e.g., `Game.Fallout4` from `classic_constants`), the test fails. Verify from `classic-scanlog-py/src/orchestrator.rs::PyAnalysisConfig::new`.

- **HIGH — `RustOrchestrator` coverage is thin**: The only test is `construct_and_cancel` — it constructs, calls `cancel()`, and doesn't exercise `process_log`. This is below D-07 intent ("calls one real method"). `cancel()` on a cancellation token that hasn't been used is nearly a no-op. For stronger coverage, either (a) provide a minimal crash log fixture under `tests/fixtures/` and call `process_log`, or (b) explicitly document that `RustOrchestrator` requires fixture-backed integration testing outside this smoke suite.

- **MEDIUM — `ScanProgressPhase` enum variants via `dir()`**: The test uses `[name for name in dir(classic_scanlog.ScanProgressPhase) if not name.startswith("_")]` and asserts `len(attrs) > 0`. This is fragile: if `ScanProgressPhase` gets any new method added to it, the test still passes even if the actual variants (`QUEUED`, `SCANNING`, etc.) disappear. Recommend direct variant access for each expected variant.

- **MEDIUM — `CrashgenVersion` constructor signature uncertain**: Test uses `classic_scanlog.parse_crashgen_version("1.2.3")` instead of the class constructor. This is the correct approach given the factory pattern, but the plan doesn't explicitly verify that direct `CrashgenVersion(...)` construction is disallowed or allowed. If the class has `#[new]`, the constructor should be tested too.

- **MEDIUM — `CrashgenRegistry` construction bare**: `test_crashgen_registry_construct` only asserts `registry is not None`. No method call. This fails D-07's "calls one real method" requirement.

- **LOW — Row count target (50) may not match actual**: Plan says "50 rows" but RESEARCH Q2 shows Wave 3a = orchestrator(23) + papyrus(15) + version(5) + crashgen_registry(4) + segment_key(1) + error(2) = 50 exactly. If any sub-module has a different count after `parse_rust_surface()` refreshes, the `>= 50` assertion may fail.

### Suggestions
1. Read `classic-scanlog-py/src/orchestrator.rs::PyAnalysisConfig` first to determine exact constructor signature.
2. Upgrade `test_scan_progress_phase_enum_constants` to check for specific variants (`QUEUED`, `SCANNING`, `REPORT_BUILD`, `COMPLETED` or whatever the real variants are).
3. Add at least one `CrashgenRegistry` method call (e.g., `registry.len()` or `registry.is_empty()`) to satisfy D-07.
4. If `RustOrchestrator.process_log` can run with an empty string, add a minimal call. Otherwise add a tests/fixtures stub.

### Risk Assessment
**MEDIUM** — Thin orchestrator coverage is the main gap; likely to pass gate but weak on D-07 intent.

---

## Plan 03-05: Scanlog Wave 3b (Report Standalone)

### Summary
Promotes 46 report sub-module rows across 5 PyO3 wrapper classes (StringPool, ReportFragment, ReportComposer, ReportGenerator, ParallelReportProcessor). Per A7, splitting report from Wave 3 improves bisect granularity and manages the heavier test surface. The concerns center on thin per-class coverage.

### Strengths
- A7 honored: explicit split rationale documented
- Clear 5-class focus
- Correct row math (241 → 287 = +46)

### Concerns
- **HIGH — Test coverage is below stated minimum**: The plan targets "5+ tests, one per class minimum" but D-07 requires "at least one method per promoted module" AND per-class tests with real method calls. 46 rows spread across 5 classes = ~9 rows per class on average, but the scaffold only tests 5 classes + 1 hasattr check. Rows on individual methods (e.g., `ReportComposer.compose_chunk`, `ReportGenerator.format_header`) get zero direct coverage. While D-07 allows grouped tests, the plan should add more depth here.

- **HIGH — `test_report_fragment_constructed_via_composer` uses only `hasattr`**: `assert hasattr(classic_scanlog, "ReportFragment")` doesn't construct, doesn't access fields, and doesn't exercise runtime. This fails Pitfall 4 protection — a `#[pyclass]` without `m.add_class::<>()?;` registration would still pass this test as long as the type is in the stub file.

- **MEDIUM — `StringPool` tests don't verify semantic correctness**: `test_string_pool_clear_after_intern` calls `intern("a")`, `intern("b")`, `clear()`, and then only asserts `pool is not None`. Should assert `len(pool) == 0` (if `__len__` exposed) or re-intern and check for a new identity.

- **MEDIUM — `ReportGenerator.generate(empty_result)` not actually called**: `test_report_generator_construct` only constructs and asserts non-None. The scaffold says "minimal generate call" but the test doesn't make one. For `generate` to be called, a valid `AnalysisResult` is needed — either pass `None` (may throw) or build via Wave 3a's `RustOrchestrator` (dependency coupling).

- **LOW — 46-row target fragile**: If the parser attributes some report helper functions to `scanlog.report.*` differently than the backlog file expects, the count could drift by ±3. The `>= 46` assertion allows upward drift but not downward.

### Suggestions
1. Add per-method tests for at least the most common methods on each of the 5 classes (compose, generate, process, intern, etc.) to bring coverage to ~10-12 tests total.
2. Replace `test_report_fragment_constructed_via_composer` with a real construction via `ReportComposer.compose([])` and field access on the returned fragment.
3. For `ReportGenerator.generate`, use a minimal hand-constructed `AnalysisResult` fixture or mark the test as requiring a fixture file.

### Risk Assessment
**MEDIUM** — Coverage thin but structurally sound; likely to pass but weak on D-07 intent.

---

## Plan 03-06: Config Promotion

### Summary
Promotes 22 deferred config entries + 4 Tier-2 runtime-verified migrations (26 rows). Honors A5 (`classic-crashgen-settings-core` types flow through config) and A3 (already `pub use`d). Main concerns: D-07 violation via hasattr-only testing and ambiguous Tier-2 migration row identification.

### Strengths
- A5 honored: `classic-crashgen-settings-core` explicitly referenced as flowing through config
- A3 honored: references to lines 17-21 of `classic-config-core/src/lib.rs`
- Includes 4 Tier-2 migration rows (runtime-verified bindings that need contract enrollment)

### Concerns
- **HIGH — D-07 violation via `hasattr` testing**: 10 of 11 test functions in `test_promoted_config_smoke.py` use ONLY `hasattr(classic_config, "ClassName")`. This is class-existence verification, not D-07's "constructs an instance and calls one real method". The plan acknowledges: "These types are typically constructed via YAML deserialization... The `hasattr` smoke is the minimum acceptable." But this materially weakens PYT-05 for the config module. Recommend loading a minimal YAML via `YamlDataCore::from_str(...)` and inspecting the deserialized classes — this exercises the factory path and satisfies D-07.

- **HIGH — 4 Tier-2 migration rows not explicitly identified**: Task 1 Step 2 says "Walk `runtime_coverage_registry.json` for entries like `python-tier2-config-runtime` or similar — these have `bindingIdentifiers` but no matching `tier1Mapping`". This is vague. Plan should enumerate the 4 specific `bindingIdentifier` strings or `coverageId` values so the executor can match them deterministically. RESEARCH §Question 1 gives the count but not the specific IDs.

- **HIGH — Task 4 deletes 4 Tier-2 entries without identifying which 4**: Task 4 Step 1 says "DELETE the 4 Tier-2 explicit-binding rows that are now covered by tier1 contract rows". Without specific IDs, the executor could delete wrong rows. Recommend listing the exact `coverageId` values to delete.

- **MEDIUM — Row ID prefix `config.<sub_area>.<name>` is ambiguous**: Existing 15 Tier-1 config rows may use a flat `config.<name>` scheme without sub_area. Plan should verify the existing prefix scheme and match it.

- **MEDIUM — `YamlDataCore` methods not covered in stub updates**: Task 2 says "Plus any new methods on the existing `YamlDataCore` class" but doesn't enumerate them. The 22 deferred config rows likely include `YamlDataCore` methods that need both stub additions AND tests.

### Suggestions
1. Rewrite `test_promoted_config_smoke.py` to use a YAML fixture:
   ```python
   def test_crashgen_entry_raw_deserialized_from_yaml(tmp_path):
       yaml_file = tmp_path / "test.yaml"
       yaml_file.write_text("CLASSIC_Pre_Main_Settings: ...")
       data = classic_config.YamlDataCore.from_file(str(yaml_file))
       entries = data.crashgen_entries()  # verify exact method name
       assert len(entries) > 0
       assert isinstance(entries[0], classic_config.CrashgenEntryRaw)
   ```
2. In Task 1, explicitly enumerate the 4 Tier-2 migration `coverageId` values from `runtime_coverage_registry.json`.
3. In Task 4, specify the exact `coverageId` list to delete.
4. Verify existing Tier-1 config row ID scheme (`config.<name>` vs `config.<sub_area>.<name>`) before authoring new rows.

### Risk Assessment
**MEDIUM-HIGH** — hasattr-only testing materially weakens PYT-05; Tier-2 row ambiguity could cause wrong deletions.

---

## Plan 03-07: Version Registry Promotion

### Summary
Promotes 34 deferred version_registry entries + 1 Tier-2 migration (35 rows). Same concerns as Plan 06 — hasattr-only testing and Tier-2 row ambiguity. Also has unresolved `UnknownVersionStrategy` vs `UnknownVersionHandling` naming uncertainty.

### Strengths
- A3 honored: references `classic-version-registry-core/src/lib.rs` lines 55-60
- Clean 12-test scaffold matching class count
- Enum variant discovery via `dir()`

### Concerns
- **HIGH — D-07 violation via `hasattr` testing (identical to Plan 06)**: 11 of 12 test functions use `hasattr(classic_version_registry, "ClassName")`. Same weakness as Plan 06. Version registry types are typically loaded via the `VersionRegistry::default()` or `get_version_registry()` singleton — the test should actually USE one and inspect returned values.

- **HIGH — `UnknownVersionStrategy` vs `UnknownVersionHandling` unresolved**: RESEARCH §Question 6 Wave 3a (line 751) references both names. `classic-version-registry-core/src/lib.rs` line 55-60 likely exports only one. If the plan authors a contract row for `UnknownVersionStrategy` and the actual exported symbol is `UnknownVersionHandling`, the Pitfall 2 guard from Plan 01 will fire. Worse, if the stub uses the wrong name, `mypy --strict` will flag it. **Recommend explicit verification before Task 1** by grepping the exact name in `classic-version-registry-core/src/lib.rs`.

- **HIGH — 1 Tier-2 migration row not identified**: Same issue as Plan 06 — plan references "1 Tier-2 runtime-verified migration" but doesn't identify which specific `coverageId` from `runtime_coverage_registry.json`.

- **MEDIUM — `VersionMatcher()` constructor may not be parameterless**: Test assumes `VersionMatcher()` with no args. The actual constructor may take a config or registry reference. Verify from `classic-version-registry-py/src/*.rs`.

- **MEDIUM — Enum constant tests with `dir()`**: `test_match_confidence_enum_constants` asserts `len(attrs) > 0` — same weakness as Plan 04. Should test specific variants.

### Suggestions
1. Before Task 1, grep `classic-version-registry-core/src/lib.rs` for exact enum name (`UnknownVersionStrategy` or `UnknownVersionHandling`).
2. Identify the exact `coverageId` of the 1 Tier-2 migration row.
3. Rewrite tests to use `get_version_registry()` singleton and actually look up versions.
4. Add specific enum variant tests (MatchConfidence.EXACT, etc.).

### Risk Assessment
**MEDIUM-HIGH** — hasattr issue + naming uncertainty could cause gate failures at plan close.

---

## Plan 03-08: classic_shared + file_io aux

### Summary
Wires `classic_shared` with 6 contract rows (HARM-03, HARM-04) and promotes 5 file_io rows (1 aux + 4 Tier-2 runtime-verified FileHasher cache helpers). Correctly honors A2 (aux belongs to file_io, not classic_shared), A8 (RuntimeStats via factory; `classic_shared.pyi` already complete), and D-10 4-step verification chain. Strong plan overall.

### Strengths
- A2 honored: explicit "the 1 aux entry belongs to file_io, NOT classic_shared"
- A8 honored: `test_classic_shared_smoke.py` explicitly uses `get_runtime_stats()` factory with prominent warning comment
- `classic_shared.pyi` is VERIFIED (not edited) per A8
- D-10 4-step wiring chain is explicit and testable
- 6-row contract matches D-09 exactly (PathHandler, StringProcessor, RustPerformanceMonitor, RuntimeStats, get_runtime_stats, is_runtime_healthy)
- New selector entries (`python-tier1-shared`, `python-tier1-file_io`) follow RESEARCH §Question 7 Path A recommendation

### Concerns
- **HIGH — Plan 08/09 file_io coordination conflict**: Plan 08 Task 1 authors 5 file_io rows: `file_io.FileHasher` + cache_size + cache_stats + reset_cache_stats + clear_cache. But Plan 01's `RUST_TARGET_CRATES` expansion adds `classic-file-io-core/src/lib.rs`, which surfaces ALL public `classic-file-io-core` symbols as tier2_gap_total. Plan 09 Task 1 then tries to promote "A10 residual rows from 14+ untracked crates" — including file_io. If Plan 08 claims only 5 file_io rows but Plan 09 wants more, which plan owns the rest? **Recommend Plan 08 explicitly claims ALL file_io rows** (including residuals) OR Plan 09 explicitly skips file_io (already covered by Plan 08). Currently unclear.

- **MEDIUM — PathHandler/StringProcessor/RustPerformanceMonitor method names guessed**: Task 3 test scaffold uses `normalize("  hello  ")`, `split_path("a/b/c")`, `record_metric("test_op", 1)` with `hasattr` fallbacks. If these method names are wrong, the `else: assert mon is not None` fallback turns the test into a no-op. Since `classic_shared.pyi` is already complete (per A8), the plan could simply READ the stub to extract exact method names.

- **MEDIUM — `contractIdsHash` placeholder handling**: Task 4 Step 1 writes `"contractIdsHash": "<recomputed by generate_baseline.py>"` as a literal string placeholder. If `generate_baseline.py --write-baseline` doesn't auto-recompute selector hashes (unclear whether it does), this placeholder remains in the file and the gate fails with `registry_mismatch_total > 0`. **Recommend either (a) verifying `generate_baseline.py` selector hash recomputation behavior, or (b) computing the hash in Task 1 using `_stable_id_hash` directly.

- **MEDIUM — `test_file_hasher_clear_cache_smoke` assumes clear → size == 0**: Test asserts `hasher.cache_size() == 0` after `clear_cache()`. This assumes cache_size counts ENTRIES, not BYTES. If `cache_size` reports bytes and an empty cache has non-zero overhead, the test fails. Verify semantics from `classic-file-io-core/src/hasher.rs`.

- **LOW — `RuntimeStats.is_healthy` field access**: Test asserts `stats.is_healthy is True`. If the stub declares this as a getter method rather than an attribute, the call becomes `stats.is_healthy()` and the comparison fails. Verify from the stub file.

### Suggestions
1. Read `classic_shared.pyi` to extract exact method names for `PathHandler`, `StringProcessor`, `RustPerformanceMonitor`, then rewrite the scaffold without `hasattr` fallbacks.
2. Add an explicit note to Plan 09 that file_io is OWNED by Plan 08, and Plan 09 must exclude `classic-file-io-core` from residual promotion.
3. Verify `generate_baseline.py --write-baseline` selector hash recomputation OR compute hashes in Task 1 using `hashlib.sha256(','.join(sorted(ids)).encode())[:16]`.
4. Add a verification step in Task 4 that asserts `contractIdsHash` is a valid 16-char hex string (not the placeholder).

### Risk Assessment
**MEDIUM** — Strong plan overall; the Plan 08/09 file_io coordination is the main architectural concern. classic_shared wiring likely works.

---

## Plan 03-09: Tier-2 Cleanup and Final Sweep

### Summary
Final cleanup plan addressing three concerns: (1) A10 residual promotion from 14+ untracked crates, (2) A9 structural cleanup (delete Tier-2 gap branches in `generate_baseline.py`, delete `tierDefinitions.tier2`, sweep comments), (3) final mypy `--strict` sweep across all 19 stubs and PYT-06 verification. Most concerning plan in the phase.

### Strengths
- A9 honored correctly: cleanup lands in `generate_baseline.py` lines 574-610 (not `check_parity_gate.py`)
- A10 residual handling is explicit
- Final 5-step verification chain includes mypy across all 19 stubs
- PYT-06 verification via `deferred_total == 0` check
- Flips Plan 01 xfail test to passing

### Concerns
- **HIGH — A10 residual scope is undersized for a single plan**: Task 1 expects to "Promote any remaining symbols... ~50-150 additional rows per A10" across 14+ modules, authoring contract rows + stubs + tests for each. The plan allocates this to a single atomic commit. By comparison, Plan 02 promotes 74 rows for ONE crate (scanlog Wave 1) and is already complex. Plan 09 tries to do ~50-150 rows across 14 crates, each needing its own stub updates and smoke tests. **This should be 2-4 separate plans, not 1**. Recommend splitting into: Plan 09a (A10 residual promotion, per-crate sub-tasks), Plan 09b (A9 cleanup + mypy sweep + PYT-06 verification).

- **HIGH — Handling of symbols without -py wrappers is architecturally unclear**: Task 1 EXECUTOR NOTE says "some residual symbols have NO -py wrapper... skip them and document as Phase 6 follow-up". But after Task 2 deletes the tier2 gap branches, unmapped Rust symbols become INVISIBLE to the gate. PYT-06 (`deferred_total == 0`) is satisfied, but the actual parity goal ("no Tier-2 deferrals, no narrowing") is violated because genuinely unmapped symbols are hidden. **Recommend Plan 09 instead KEEP the gap detection** (fail the gate on unmapped Rust symbols) and only delete the `tier2` label / re-classify as `tier1_missing_python`. This preserves visibility while achieving the single-tier goal.

- **HIGH — Deleting `summary["tier2_gap_total"]` has unknown cascade effects**: Task 2 says to delete `tier2_gap_total` from the summary dict and "Search for any other readers... Replace them with hard-coded 0 or delete the read entirely." Downstream consumers include: `check_parity_gate.py` rendering code, `runtime_coverage_summary.json` builders, `tier1_gate_report.md` templates. The plan doesn't enumerate all readers. Recommend `grep -r "tier2_gap_total" tools/ docs/` to find all consumers BEFORE the deletion, and update each explicitly.

- **HIGH — Task 2 test `test_tier2_gap_total_removed_from_summary` uses raw `REPO_ROOT.joinpath(...)`**: The test file `tools/python_api_parity/tests/test_check_parity_gate.py` was created in Plan 01 with `REPO_ROOT = Path(__file__).resolve().parents[3]`. If Plan 01's sys.path/import structure conflicts, this test won't resolve the correct path. Same import-hygiene concern as Plan 01.

- **MEDIUM — Plan 01 A10 sizing report may be stale**: Plan 01 captures per-owner `tier2_gap_total` counts at Plan 01 close. But by the time Plan 09 executes, Plans 02-08 have promoted hundreds of symbols, changing the rust_api_surface state. The A10 sizing from Plan 01 may no longer match Plan 09's actual state. Recommend **re-running the sizing query at the start of Plan 09 Task 1** to get fresh counts, not relying on the Plan 01 snapshot.

- **MEDIUM — PYT-04 mypy sweep mixes stub-only vs. module mode**: Task 3 runs `mypy --strict <stub.pyi>` on each stub individually. This validates the stub in isolation but doesn't verify the stub matches the actual `.pyd` module at runtime. RESEARCH mentions `validate_stubs.py` handles this cross-check, but mypy alone doesn't.

- **LOW — Task 1 Step 6 registry entry additions miss ownerModules**: Task 1 Step 6 adds selector entries for 14+ owners (`python-tier1-yaml`, `python-tier1-database`, etc.) but Plan 01 only added ownerModules descriptions to parity_contract.json, not runtime_coverage_registry.json. The registry schema may also need ownerModule enum updates.

- **LOW — `deferred_total == 0` doesn't verify completeness**: `runtime_coverage_summary.json::summary.deferred_total == 0` can be achieved by deleting all deferred entries without actually promoting them. The coverage completeness PowerShell one-liner from VALIDATION.md is the real check. Task 4 Step 4 runs this check — good, but the success criterion should emphasize BOTH checks.

### Suggestions
1. **Split Plan 09 into Plan 09a (A10 residual promotion) and Plan 09b (A9 cleanup + PYT-06 verification)**. Plan 09a can further sub-divide by crate cluster (foundation crates, utility crates, etc.).
2. **Keep gap detection for unmapped Rust symbols** — instead of deleting the tier2 branches, rename them to `tier1_unmapped` with a non-zero exit code. This preserves visibility.
3. Run `grep -rn "tier2_gap_total" tools/ docs/ ClassicLib-rs/` BEFORE Task 2 and enumerate every reader in the plan.
4. Re-run the A10 sizing query at the start of Task 1 (not from Plan 01 SUMMARY).
5. Add `validate_stubs.py` as a separate verification step alongside mypy to catch runtime/stub divergence.

### Risk Assessment
**HIGH** — Scope is too large for a single plan; unmapped symbol handling has architectural implications; Task 2 cascade effects unverified.

---

## Overall Phase Assessment

### Do the 9 plans collectively achieve the phase goal?

**Partially.** The plans CORRECTLY address the 285 deferred backlog entries (285 + 12 Tier-2 migrations + 6 classic_shared + 5 file_io = 308 net rows → tier1Mappings 59→367). With A10 residuals handled in Plan 09, final state reaches ~410-510 rows.

**PYT-06 (`deferred_total == 0`) is technically achievable** but the current Plan 09 design risks achieving it by deleting visibility rather than completing coverage. The architectural question — what happens when a Rust public API has no Python wrapper — is not cleanly resolved.

### Is the plan ordering correct?

**Yes, mostly.** Sequential waves 1-9 are correct because all plans touch `parity_contract.json`. Parallel execution would cause merge conflicts on shared baseline files.

However:
- **Plans 06 and 07 (config, version_registry) could run in parallel to scanlog plans** if the baseline refresh were done last. Currently sequential is the safe default.
- **Plan 09 should probably be 2 plans** (09a residuals, 09b cleanup) to reduce atomic commit risk.

### Are there missing plans or tasks?

**YES:**

1. **Missing: classic-crashgen-settings-core type routing plan**. Per A5, types like `SuspectErrorRule`, `SuspectStackRule`, `ModConflictEntry` flow through `classic-config-py`, `classic-scanlog-py`, AND `classic-scangame-py`. Plan 06 only mentions config. Are the same types promoted 3 times (once per binding) or once with cross-module references? The contract schema doesn't handle this case — needs explicit resolution.

2. **Missing: Pitfall 4 upfront verification**. Plans rely on `m.add_class::<PyXxx>()?;` being present in `#[pymodule]` functions. If a class exists in `.pyi` but isn't registered, tests fail with `AttributeError`. Recommend a pre-Phase-3 audit task that grep-checks every `#[pyclass]` has a corresponding `m.add_class::<>()?;`.

3. **Missing: Phase 3 / Phase 4 coordination mechanism**. CONTEXT notes that `tools/binding_parity_runtime_coverage.py` should not be edited simultaneously by Phase 3 and Phase 4. No plan establishes this coordination (e.g., file locking, phase-awareness check).

4. **Missing: Tier-2 registry row deletion scope**. Plans 06, 07, 08 delete existing Tier-2 explicit-binding entries without enumerating them. A pre-Phase-3 audit should list every Tier-2 entry currently in `runtime_coverage_registry.json` and assign each to a specific plan for deletion.

### Architectural concerns cutting across multiple plans

1. **hasattr-only testing in Plans 06 and 07 violates D-07**. Config and version_registry plans test class existence only, not method calls. This is a systemic weakness that should be addressed either by updating D-07 to allow hasattr-only for deserialization-constructed types, or by adding YAML fixture-based tests.

2. **Constructor signature guessing is systemic**. Plans 02, 03, 04, 05, 08 all scaffold constructor calls without upfront verification. A 1-hour pre-Phase-3 task that reads every `#[pymethods] fn new` across all `-py` wrappers and records signatures would eliminate this category of failures.

3. **Selector hash recomputation behavior is unverified**. Plans 02-08 all bump `contractCount` in existing selector entries and rely on `generate_baseline.py --write-baseline` to recompute `contractIdsHash`. If this flag does NOT recompute hashes, every plan fails at close with `registry_mismatch_total > 0`. Verify in Plan 01.

4. **Plan 09 scope is too large**. A10 residual promotion + A9 cleanup + final mypy sweep + PYT-06 verification is 4-5 plans worth of work in one atomic commit. Split it.

5. **Post-Phase-3 gap detection**. Deleting the tier2 gap branches removes visibility into unmapped symbols. The Pitfall 2 guard added in Plan 01 catches contract→Rust drift, but NOT Rust→contract drift (new Rust symbols not in contract). This needs a replacement mechanism.

### Research Amendments A1-A10 Honoring

| Amendment | Honored | Plans | Notes |
|-----------|---------|-------|-------|
| A1 (`pub use` in `-core`, not `-py`) | ✓ | 02-07 | Tasks explicitly grep `-core/lib.rs` |
| A2 (aux belongs to file_io, not classic_shared) | ✓ | 08 | Explicit note in truths |
| A3 (Pitfall 2 fires ~0 rows) | ✓ | 02-07 | Every plan notes "per A3 expected 0 new lines" |
| A4 (285 + 12 + 6 = 303 counts) | ✓ | 01-09 | Math consistent across plans |
| A5 (crashgen-settings-core excluded) | ✓ | 01 | Test asserts exclusion; **but** downstream type routing unresolved |
| A6 (Wave 3 sub-module list corrected) | ✓ | 04 | Explicit "no crashgen_rules/core_mod_convert" |
| A7 (9-plan structure, report standalone) | ✓ | 04, 05 | Plan 05 is standalone report |
| A8 (RuntimeStats factory; stub complete) | ✓ | 08 | Explicit factory use + no stub edit |
| A9 (cleanup in generate_baseline.py) | ✓ | 09 | Task 2 targets correct file |
| A10 (sizing report in Plan 01, promotion in Plan 09) | ⚠ | 01, 09 | Sizing captured but stale-by-Plan-9 risk |

**A10 has a timing issue**: sizing captured at Plan 01 close, consumed at Plan 09 start, but the underlying rust_api_surface changes continuously across Plans 02-08. The Plan 01 snapshot may be stale.

### Pitfall 2 Guard Assertion (Plan 01)

**Correctly specified.** The function signature, error message format, and call site (before `generate_diff_report`) all match RESEARCH Q4. The three test cases (passes-when-present, fails-when-missing, fails-when-rustSymbol-field-missing) cover the contract. Minor concern: the error message template uses `"ClassicLib-rs/business-logic/{crate}/src/lib.rs"` but classic_shared lives under `ClassicLib-rs/foundation/classic-shared-py/src/lib.rs` — the message notes this as "(or the appropriate foundation/-py lib.rs for classic_shared)" which is acceptable.

### classic_shared Wiring (Plan 08 / HARM-03, HARM-04)

**Correctly honors A8.** The D-10 4-step chain is explicit and the `RuntimeStats` factory usage is prominently documented with a CRITICAL comment. The main concern is Plan 08/09 file_io coordination (see Plan 08 HIGH concerns).

### Plan 09 Tier-2 Cleanup (A9)

**Partially correct.** The cleanup targets the right files (`generate_baseline.py` lines 574-610, `parity_contract.json::tierDefinitions`). BUT:
- Deleting `summary["tier2_gap_total"]` has unverified cascade effects
- Removing gap detection hides unmapped symbols (architectural concern)
- Scope is too large for a single plan

### A10 Residual Promotion

**Undersized.** Plan 09 Task 1 allocates a single task for ~50-150 rows across 14+ crates with stubs and tests. Historically, plans of this size fail or run grossly over budget. Recommend splitting.

---

## Summary Verdict

**Overall Phase Risk: MEDIUM-HIGH**

Plans 01, 04, 05, 08 are solid with minor concerns. Plans 02, 03 have execution-time friction around scaffolded constructor signatures. Plans 06, 07 have D-07 violations via hasattr-only testing. Plan 09 is architecturally underspecified around unmapped symbols and scope-wise too large.

**Recommended changes before execution:**

1. **Plan 01**: Fix sys.path handling in test files; verify `generate_baseline.py --write-baseline` ownerModules handling.
2. **Plans 02-05**: Add pre-Task-1 step to read all `#[pymethods] fn new` and record exact constructor signatures.
3. **Plans 06, 07**: Rewrite smoke tests to use YAML fixtures and actually exercise deserialization paths.
4. **Plan 08**: Explicitly claim all file_io rows (not just 5) OR explicitly exclude file_io from Plan 09 residuals.
5. **Plan 09**: **Split into 09a (residuals) + 09b (cleanup)**. Resolve unmapped symbol architecture: keep gap detection as `tier1_unmapped` rather than deleting. Enumerate all `tier2_gap_total` consumers before deletion.
6. **Cross-phase**: Add a pre-Phase-3 Pitfall 4 audit task verifying every `#[pyclass]` has matching `m.add_class::<>()?;` registration.

**If executed as-is**, Phase 3 will likely complete PYT-01, PYT-02, PYT-03, PYT-04, HARM-03, HARM-04 successfully. **PYT-05** is at risk due to thin smoke test coverage in Plans 06-07. **PYT-06** is technically achievable but may hide genuine coverage gaps through Plan 09's gap-branch deletion.

The plans collectively demonstrate deep research (RESEARCH.md amendments A1-A10 are well-integrated) and strong discipline around the atomic commit cadence (D-06) and per-plan baseline refresh (D-03). The main gaps are around test quality depth (D-07 enforcement) and Plan 09's scope/architecture.


---

## Codex Review (GPT-5.4 — high reasoning effort)

**Plan 03-01**
Summary: Strong keystone plan. It correctly centers the 19-target expansion, A10 sizing, and the Pitfall 2 guard, and it matches the real parser/gate architecture in [generate_baseline.py:160](J:/CLASSIC-Fallout4/tools/python_api_parity/generate_baseline.py:160) and [check_parity_gate.py:116](J:/CLASSIC-Fallout4/tools/python_api_parity/check_parity_gate.py:116).
Strengths:
- Correctly honors A1/A3/A5/A10 by targeting `-core/lib.rs`, excluding `classic-crashgen-settings-core`, and requiring a post-expansion sizing report.
- The Pitfall 2 guard shape is well specified and should fail at the right place, before diff generation.
Concerns:
- `LOW`: The plan’s test inventory is good, but it does not explicitly guard the hard-coded owner rendering tuple in [generate_baseline.py:682](J:/CLASSIC-Fallout4/tools/python_api_parity/generate_baseline.py:682), which will drift once owner modules expand.
Suggestions:
- Add one tooling test asserting rendered owner sections are derived from `ownerModules` or another single source of truth, not the current hard-coded tuple at [generate_baseline.py:682](J:/CLASSIC-Fallout4/tools/python_api_parity/generate_baseline.py:682).
Risk Assessment: LOW — this plan is materially sound and is the best-specified plan in the set.

**Plan 03-02**
Summary: Good decomposition for Wave 1 and mostly aligned with A3, but the smoke-test depth is weaker than the plan claims, which undercuts Pitfall 4 protection.
Strengths:
- Wave split matches A7 and keeps contract/stub/test/baseline updates atomic.
- It correctly treats `pub use` as verification-first rather than the main workload.
Concerns:
- `MEDIUM`: Several tests stop at construction or non-`None` checks instead of one real method/field use for each promoted class, especially `ScanOutput`, `StreamingLogParser`, and `StreamingIteratorParser` in [03-02-scanlog-wave1-parsing-primitives-PLAN.md:392](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-02-scanlog-wave1-parsing-primitives-PLAN.md:392) and [03-02-scanlog-wave1-parsing-primitives-PLAN.md:395](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-02-scanlog-wave1-parsing-primitives-PLAN.md:395).
- `LOW`: The registry step uses a comma-joined `testSuite` string, but the registry schema only defines a scalar `testSuite` field in [runtime_coverage_registry.json:6](J:/CLASSIC-Fallout4/ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json:6).
Suggestions:
- Strengthen the smoke file so every promoted `#[pyclass]` gets one actual method/field assertion, not just existence.
Risk Assessment: MEDIUM — likely executable, but runtime-verification quality is softer than intended.

**Plan 03-03**
Summary: The wave sizing and module selection are right, but this plan has a real risk of leaving some fcx/gpu surface only nominally covered.
Strengths:
- Correctly follows A7’s Wave 2 composition and keeps `fcx_handler` in the right layer.
- The contract/stub flow is otherwise coherent.
Concerns:
- `MEDIUM`: `GLOBAL_FCX_HANDLER` is named in scope, but the stub/test tasks do not clearly show how that static/export is represented or exercised; see [03-03-scanlog-wave2-detection-and-analysis-PLAN.md:85](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-03-scanlog-wave2-detection-and-analysis-PLAN.md:85).
- `MEDIUM`: `GpuInfo` and `GpuVendor` coverage is weak; several tests degrade to `hasattr` or best-effort branches in [03-03-scanlog-wave2-detection-and-analysis-PLAN.md:393](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-03-scanlog-wave2-detection-and-analysis-PLAN.md:393) and [03-03-scanlog-wave2-detection-and-analysis-PLAN.md:398](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-03-scanlog-wave2-detection-and-analysis-PLAN.md:398).
Suggestions:
- Make `GLOBAL_FCX_HANDLER` explicit in the contract and add one deterministic smoke path for it; also require one getter/method assertion for `GpuInfo`.
Risk Assessment: MEDIUM — sound structure, but some promoted rows may end up under-verified.

**Plan 03-04**
Summary: The Wave 3a split is the right response to A7, but this plan still carries too many “verify exact name later” placeholders for a large contract-writing plan.
Strengths:
- Correctly repairs the old Wave 3 shape by using `crashgen_registry`, `segment_key`, and `error` per A6/A7.
- Splitting report into a separate plan is the right call.
Concerns:
- `MEDIUM`: Several key interface names and signatures are still provisional, including `RustOrchestrator` and async/enum details, in [03-04-scanlog-wave3a-orchestration-core-PLAN.md:93](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-04-scanlog-wave3a-orchestration-core-PLAN.md:93) and [03-04-scanlog-wave3a-orchestration-core-PLAN.md:280](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-04-scanlog-wave3a-orchestration-core-PLAN.md:280).
- `MEDIUM`: Some smoke tests again settle for construction/non-`None`, especially around `AnalysisResult`, `PapyrusStats`, and registry objects.
Suggestions:
- Front-load a stricter symbol inventory step before authoring rows, and require one getter/method assertion for `AnalysisResult` and one real enum/value assertion for the version slice.
Risk Assessment: MEDIUM — the split is correct, but the execution instructions are not fully closed over the real interface.

**Plan 03-05**
Summary: Good isolation of the heavy `report` surface, but the smoke strategy is too weak for the most complex scanlog submodule in the phase.
Strengths:
- Correctly singles out the 46-row `report` slice, which is exactly where the scanlog asymmetry sits.
- Contract-row accounting and baseline progression are clear.
Concerns:
- `MEDIUM`: `ReportGenerator` is only constructed, not exercised, in [03-05-scanlog-wave3b-report-standalone-PLAN.md:271](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-05-scanlog-wave3b-report-standalone-PLAN.md:271).
- `MEDIUM`: `ReportFragment` is not actually instantiated or inspected; the test only checks symbol existence in [03-05-scanlog-wave3b-report-standalone-PLAN.md:279](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-05-scanlog-wave3b-report-standalone-PLAN.md:279).
Suggestions:
- Require a minimal synthetic `AnalysisResult` fixture so `ReportGenerator.generate(...)` and one fragment-producing path run for real.
Risk Assessment: MEDIUM — the plan shape is right, but Pitfall 4 protection is not yet at the level the plan claims.

**Plan 03-06**
Summary: Scope and counts are right, but this is the first plan where the smoke-test design materially conflicts with D-07.
Strengths:
- Correctly incorporates A5 by routing `classic-crashgen-settings-core` types through config.
- Contract-row and registry migration counts are internally consistent.
Concerns:
- `HIGH`: Most promoted classes are only checked with `hasattr(...)` in [03-06-config-promotion-PLAN.md:297](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-06-config-promotion-PLAN.md:297) through [03-06-config-promotion-PLAN.md:330](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-06-config-promotion-PLAN.md:330), which does not satisfy “construct every promoted `#[pyclass]` and call one method or access one field.”
- `MEDIUM`: The 4 migrated Tier-2 rows are not enumerated concretely, which makes it harder to verify that the intended bindings were actually promoted.
Suggestions:
- Replace symbol-existence smokes with fixture-backed deserialization or factory-based field-access tests for each config class, and list the exact 4 migrated runtime rows by binding identifier.
Risk Assessment: HIGH — as written, this can go green while still missing meaningful runtime coverage.

**Plan 03-07**
Summary: Similar to Plan 06: good scope, weak runtime proof. It likely promotes the rows, but it does not yet prove the promoted types are genuinely usable.
Strengths:
- Correctly leans on A3 and uses the right version-registry symbol inventory.
- Registry migration and count progression are easy to audit.
Concerns:
- `HIGH`: Many tests are only `hasattr`/class-exists checks, including `MatchResult`, `VersionInfo`, `AddressLibraryConfig`, `CompatibleRange`, `CrashgenConfig`, `UnknownVersionStrategy`, and `XseConfig` in [03-07-version-registry-promotion-PLAN.md:310](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-07-version-registry-promotion-PLAN.md:310) and following.
- `MEDIUM`: The single migrated Tier-2 row is not named explicitly, so reviewers cannot verify the migration target from the plan alone.
Suggestions:
- Require one real matcher call and one field-access path for the major structs, and identify the migrated runtime row explicitly in Task 1.
Risk Assessment: HIGH — same core problem as Plan 06, with weaker-than-required runtime verification.

**Plan 03-08**
Summary: The `classic_shared` intent mostly honors A2/A8, but one cleanup instruction is factually wrong and should be fixed before execution.
Strengths:
- Correctly uses the renamed Python names and factory-based `RuntimeStats` access, consistent with A8 and the real module surface in [classic-shared-py/src/lib.rs:322](J:/CLASSIC-Fallout4/ClassicLib-rs/foundation/classic-shared-py/src/lib.rs:322).
- Correctly keeps the aux/file-io work adjacent to `classic_shared`, which matches A2.
Concerns:
- `HIGH`: The plan tells the executor to delete `python-deferred-aux-297` from the runtime registry, but that id lives in [deferred_runtime_backlog.json:3702](J:/CLASSIC-Fallout4/docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json:3702), not in [runtime_coverage_registry.json:75](J:/CLASSIC-Fallout4/ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json:75).
- `MEDIUM`: `files_modified` includes `classic-shared-py/src/lib.rs` even though the plan’s own A8 framing says wiring should be pure verification.
Suggestions:
- Remove the instruction to delete `python-deferred-aux-297`; instead verify that its deferred entry is no longer counted after promotion. Also remove `classic-shared-py/src/lib.rs` from planned writes unless a real failure appears.
Risk Assessment: MEDIUM — HARM-03/HARM-04 are mostly specified correctly, but the cleanup step is wrong as written.

**Plan 03-09**
Summary: The A9 cleanup portion is mostly right, but the A10 residual strategy is the biggest defect in the phase plan set.
Strengths:
- Correctly recognizes that the structural cleanup belongs in `generate_baseline.py`, `parity_contract.json::tierDefinitions`, and comments, not in `check_parity_gate.py`.
- Correctly targets removal of the Tier-2 gap branches around [generate_baseline.py:574](J:/CLASSIC-Fallout4/tools/python_api_parity/generate_baseline.py:574) and the `tier2_gap_total` summary key at [generate_baseline.py:630](J:/CLASSIC-Fallout4/tools/python_api_parity/generate_baseline.py:630).
Concerns:
- `HIGH`: The residual-discovery method is unsound; `rust_api_surface.json` is not the residual backlog, and filtering it for “tier2” is not a reliable promotion source in [03-09-tier2-cleanup-and-final-sweep-PLAN.md:207](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-09-tier2-cleanup-and-final-sweep-PLAN.md:207).
- `HIGH`: The plan explicitly allows skipping residuals with no wrapper and documenting them as follow-up in [03-09-tier2-cleanup-and-final-sweep-PLAN.md:219](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-09-tier2-cleanup-and-final-sweep-PLAN.md:219) and [03-09-tier2-cleanup-and-final-sweep-PLAN.md:249](J:/CLASSIC-Fallout4/.planning/phases/03-python-tier-collapse/03-09-tier2-cleanup-and-final-sweep-PLAN.md:249), which contradicts the phase goal `deferred_total == 0`.
Suggestions:
- Make residual promotion fail-closed: source residuals from `parity_diff_report.json`/coverage outputs after Plan 8, not from raw surface files, and if wrappers are missing, split an additional closure plan rather than punting to Phase 6.
Risk Assessment: HIGH — this is the main reason the 9 plans do not yet guarantee phase completion.

**Overall Phase Assessment**
Collectively, the 9 plans do not yet guarantee `runtime_coverage_summary.json::summary.deferred_total == 0`. The biggest blockers are Plan 09’s permissive A10 fallback, Plan 08’s wrong cleanup target for `python-deferred-aux-297`, and the fact that Plans 06-07, plus parts of 02-05, rely on symbol-existence smokes that do not satisfy the D-07/Pitfall 4 bar.

The ordering is otherwise good. Sequential waves are the correct default because the phase repeatedly rewrites shared baseline artifacts and the runtime registry. There are small parallel opportunities inside a plan, but not much safe plan-level parallelism beyond what the roadmap already says.

The scope is close but not fully closed. I do not think a brand-new Phase 3 plan is strictly required if Plan 09 is tightened, but one additional “residual wrapper closure” plan would be justified if Plan 1’s A10 report shows symbols without Python wrappers. Cross-cutting architectural concern: too much of the phase can still “pass” through contract/stub churn while leaving runtime proof shallow. The plans should uniformly require real fixture-backed construction or method/field access for promoted `#[pyclass]` surfaces, especially in config and version_registry.
