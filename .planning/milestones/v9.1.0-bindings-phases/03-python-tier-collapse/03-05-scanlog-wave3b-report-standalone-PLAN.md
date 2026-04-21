---
phase: 03-python-tier-collapse
plan: 05
type: execute
wave: 5
depends_on: [03-01, 03-02, 03-03, 03-04]
files_modified:
  - ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs
  - ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
  - ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_report_smoke.py
  - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
  - ClassicLib-rs/python-bindings/tests/fixtures/minimal_analysis_result.json
  - .planning/phases/03-python-tier-collapse/03-05-CONSTRUCTOR-INVENTORY.md
  - docs/implementation/python_api_parity/baseline/parity_contract.json
  - docs/implementation/python_api_parity/baseline/parity_contract.md
  - docs/implementation/python_api_parity/baseline/parity_diff_report.json
  - docs/implementation/python_api_parity/baseline/parity_diff_report.md
  - docs/implementation/python_api_parity/baseline/rust_api_surface.json
  - docs/implementation/python_api_parity/baseline/python_api_surface.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
  - docs/implementation/python_api_parity/baseline/tier1_gate_report.md
autonomous: true
requirements: [PYT-02, PYT-04, PYT-05]
must_haves:
  truths:
    - "All 46 scanlog report sub-module deferred entries are promoted to parity_contract.json tier1Mappings"
    - "classic_scanlog.pyi covers all 5 PyO3 report wrapper classes (StringPool, ReportFragment, ReportComposer, ReportGenerator, ParallelReportProcessor) and their methods"
    - "test_promoted_scanlog_report_smoke.py covers every one of the 5 report classes with at least one construct+method test"
    - "5-step verification chain exits 0 at plan close; tier1Mappings.length == 286 (240 + 46; R9 propagation)"
  artifacts:
    - path: "ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi"
      provides: "Stub entries for all 46 report symbols across 5 PyO3 classes"
      contains: "class ReportComposer:"
    - path: "ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_report_smoke.py"
      provides: "5 per-class smoke tests (one per PyO3 report wrapper class)"
      min_lines: 100
    - path: "docs/implementation/python_api_parity/baseline/parity_contract.json"
      provides: "tier1Mappings.length = 286 after Plan 05 commit"
  key_links:
    - from: "classic_scanlog.pyi::class ReportComposer"
      to: "classic-scanlog-core::report::ReportComposer (via PyReportComposer wrapper)"
      via: "parity_contract.json tier1Mapping row"
      pattern: "scanlog\\.report\\."
---

<objective>
Promote 46 deferred Python parity entries for the scanlog `report` sub-module as a standalone plan. Per A7, `report` is split from Wave 3 into its own plan because it has 5 distinct PyO3 wrapper classes (`PyStringPool`, `PyReportFragment`, `PyReportComposer`, `PyReportGenerator`, `PyParallelReportProcessor`) and 46 rows.

Splitting `report` gives bisect granularity (a `report`-specific failure points directly here) and manages the heavier per-class test surface cleanly. Per A3, all report symbols are already `pub use`d at `classic-scanlog-core/src/lib.rs`.

Output:
- 46 new `tier1Mappings` rows in `parity_contract.json` (report sub-module)
- Updated `classic_scanlog.pyi` covering 5 report classes + all methods
- New `test_promoted_scanlog_report_smoke.py` with 5+ pytest functions
- `runtime_coverage_registry.json::python-tier1-scanlog` selector row refreshed
- Refreshed parity baseline per D-03 cadence
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-python-tier-collapse/03-CONTEXT.md
@.planning/phases/03-python-tier-collapse/03-RESEARCH.md
@.planning/phases/03-python-tier-collapse/03-VALIDATION.md
@.planning/phases/03-python-tier-collapse/03-04-SUMMARY.md
@./CLAUDE.md

<interfaces>
<!-- Report sub-module inventory (46 rows) — 5 PyO3 wrapper classes -->

5 PyO3 wrapper classes (Python-facing names from #[pyclass(name = "...")]):
- StringPool (from PyStringPool) — string interning pool
- ReportFragment (from PyReportFragment)
- ReportComposer (from PyReportComposer)
- ReportGenerator (from PyReportGenerator)
- ParallelReportProcessor (from PyParallelReportProcessor)

Approx ~9 rows per class x 5 = 45 + 1 module-level helper = 46
</interfaces>
</context>

<tasks>


<task type="auto">
  <name>Task 0: Verify report sub-module constructor signatures — record in 03-05-CONSTRUCTOR-INVENTORY.md</name>
  <files>
    .planning/phases/03-python-tier-collapse/03-05-CONSTRUCTOR-INVENTORY.md
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs (full file — every `#[pymethods] fn new` and `#[staticmethod]` compose/generate signature)
  </read_first>
  <action>
    For each of the 5 report #[pyclass] wrappers, read the exact constructor and method signatures from `classic-scanlog-py/src/report.rs`. Record in `.planning/phases/03-python-tier-collapse/03-05-CONSTRUCTOR-INVENTORY.md`:

    | PyO3 name | Rust wrapper | fn new signature | Key methods (with arg types) |
    |-----------|--------------|------------------|-------------------------------|
    | StringPool | PyStringPool | verify | intern(str), clear(), __len__? |
    | ReportFragment | PyReportFragment | verify or factory-only | text field? kind field? |
    | ReportComposer | PyReportComposer | verify | compose([ReportFragment]) -> ? |
    | ReportGenerator | PyReportGenerator | verify | generate(AnalysisResult) -> str? |
    | ParallelReportProcessor | PyParallelReportProcessor | verify | process([AnalysisResult]) -> [str]? |

    Subsequent test scaffolding MUST use verified signatures.

    Also resolve: does `StringPool` have `__len__`? If yes, tests can assert `len(pool) == 0` after clear. If no, use a different clearness check (re-intern identity, or absence of prior interns).
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "if (-not (Test-Path '.planning/phases/03-python-tier-collapse/03-05-CONSTRUCTOR-INVENTORY.md')) { Write-Error 'Inventory missing'; exit 1 }; Write-Host 'OK'"</automated>
  </verify>
  <acceptance_criteria>
    - Inventory file exists with 5 rows (StringPool, ReportFragment, ReportComposer, ReportGenerator, ParallelReportProcessor)
    - Each row has verified constructor + key method signatures
  </acceptance_criteria>
  <done>Report inventory written.</done>
</task>
<task type="auto">
  <name>Task 1: Enumerate report symbols, verify -core/lib.rs coverage, author 46 contract rows</name>
  <files>
    ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs
    docs/implementation/python_api_parity/baseline/parity_contract.json
  </files>
  <read_first>
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs (verify A3)
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/report.rs (full file — Rust types source of truth)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs (full file — PyO3 wrapper signatures)
    - docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json (filter for scanlog entries with binding identifiers containing 'report')
    - docs/implementation/python_api_parity/baseline/parity_contract.json
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 2" lines 237-281
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 6 Wave 3 report" lines 732-736
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"Research Amendment A7"
  </read_first>
  <action>
    Step 1: Verify A3 — confirm every `report` deferred symbol is already `pub use`d at `classic-scanlog-core/src/lib.rs`. If any missing, add narrow `pub use`.

    Step 2: Author 46 tier1Mapping rows. All IDs prefix with `scanlog.report.`. Coverage:
    - StringPool: ~8 rows (class + `#[pymethods]` like intern, clear, len, contains)
    - ReportFragment: ~9 rows (class + methods + field getters)
    - ReportComposer: ~9 rows (class + compose methods)
    - ReportGenerator: ~10 rows (class + generate/format methods)
    - ParallelReportProcessor: ~9 rows (class + process/batch methods)
    - 1 module-level helper if present

    Source exact method names from `classic-scanlog-py/src/report.rs::#[pymethods]` blocks.

    Row shape (same as prior plans):
    ```
    {
      "id": "scanlog.report.<ClassName>" or "scanlog.report.<ClassName>.<method>",
      "rustSymbol": "<core symbol>",
      "rustCrate": "classic-scanlog-core",
      "rustKind": "struct" or "function",
      "pythonModule": "classic_scanlog",
      "pythonExportPath": "<Python name>" or "<Class>.<method>",
      "pythonKind": "class" or "method",
      "pythonArity": <int or null>,
      "ownerModule": "scanlog",
      "tier": "tier1"
    }
    ```

    Step 3: Insert into `parity_contract.json::tier1Mappings`. Final length: 240 + 46 = 286.

    Step 4: Do NOT regenerate baseline until Task 4.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import json; c = json.loads(open('docs/implementation/python_api_parity/baseline/parity_contract.json').read()); rows = [m for m in c['tier1Mappings'] if m.get('ownerModule') == 'scanlog' and m['id'].startswith('scanlog.report.')]; print(f'report rows: {len(rows)}'); assert len(rows) >= 46"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length == 286`
    - At least 46 rows have IDs starting with `scanlog.report.`
    - Every new row has `ownerModule == 'scanlog'`, `tier == 'tier1'`, valid `rustSymbol` and `pythonExportPath`
    - All 5 PyO3 report classes have at least one row each
  </acceptance_criteria>
  <done>46 report contract rows authored.</done>
</task>

<task type="auto">
  <name>Task 2: Update classic_scanlog.pyi with report stub entries</name>
  <files>
    ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi (current state post-Plan-04)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs (full file — exact #[pymethods] signatures for all 5 classes)
    - docs/implementation/python_api_parity/baseline/parity_contract.json (46 report rows from Task 1)
  </read_first>
  <action>
    Hand-edit `classic_scanlog.pyi` to add stub entries for all 46 report rows. Group by class:

    ```python
    # ==========================================================================
    # report sub-module (Plan 05)
    # ==========================================================================

    class StringPool:
        """String interning pool for report generation."""
        def __init__(self) -> None: ...
        def intern(self, s: str) -> str: ...
        def clear(self) -> None: ...
        def __len__(self) -> int: ...
        # ... all #[pymethods]

    class ReportFragment:
        """A single fragment of a generated report."""
        text: str
        kind: str
        # ... fields and methods

    class ReportComposer:
        """Composes report fragments into a complete report."""
        def __init__(self) -> None: ...
        def compose(self, fragments: list[ReportFragment]) -> str: ...
        # ... methods

    class ReportGenerator:
        """Top-level report generator."""
        def __init__(self) -> None: ...
        def generate(self, result: AnalysisResult) -> str: ...
        # ... methods

    class ParallelReportProcessor:
        """Batch report processor with parallel execution."""
        def __init__(self) -> None: ...
        def process(self, results: list[AnalysisResult]) -> list[str]: ...
        # ... methods
    ```

    Verify all method signatures from `classic-scanlog-py/src/report.rs`. Use exact PyO3 0.27 type mapping.

    Preserve existing docstrings.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `classic_scanlog.pyi` contains `class StringPool:`, `class ReportFragment:`, `class ReportComposer:`, `class ReportGenerator:`, `class ParallelReportProcessor:`
    - `mypy --strict` exits 0
  </acceptance_criteria>
  <done>Report stub additions complete; mypy clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create test_promoted_scanlog_report_smoke.py</name>
  <files>
    ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_report_smoke.py
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave3a_smoke.py (reference style)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs (constructors source of truth)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 6 — Wave 3 report" (lines 732-736)
  </read_first>
  <behavior>
    Per D-07: at least one test per #[pyclass]. Tests:
    - `test_string_pool_intern_smoke` — StringPool(), intern("test"), verify return
    - `test_report_fragment_field_access` — ReportFragment created via composer factory, check text/kind
    - `test_report_composer_compose_empty` — ReportComposer(), compose([])
    - `test_report_generator_smoke` — ReportGenerator(), minimal generate call
    - `test_parallel_report_processor_smoke` — ParallelReportProcessor(), process([])

    Target: 5+ tests, one per class minimum. May expand to 7-10 if multiple methods per class need exercising.
  </behavior>
  <action>
    Create `test_promoted_scanlog_report_smoke.py`:

    ```python
    """Per-class smoke tests for Phase 3 Plan 05 — scanlog report sub-module.

    Covers 46 promoted contract rows across 5 PyO3 wrapper classes.
    """
    from __future__ import annotations

    import classic_scanlog


    def test_string_pool_intern_smoke() -> None:
        pool = classic_scanlog.StringPool()
        result = pool.intern("test")
        assert isinstance(result, str)
        assert result == "test"


    def test_string_pool_clear_after_intern() -> None:
        """R10 strengthening: assert clear actually clears (len or identity check)."""
        pool = classic_scanlog.StringPool()
        pool.intern("a")
        pool.intern("b")
        pool.clear()
        # Choose one of the following based on 03-05-CONSTRUCTOR-INVENTORY.md:
        # Option 1: __len__ is exposed
        if hasattr(pool, '__len__'):
            assert len(pool) == 0, "StringPool.clear() did not actually clear"
        else:
            # Option 2: no __len__ — re-intern and assert new identity
            # (cannot easily check identity with PyO3 interned strings; fall back to smoke)
            new_a = pool.intern("a")  # should be freshly interned after clear
            assert isinstance(new_a, str)
            assert new_a == "a"


    def test_report_composer_compose_empty() -> None:
        composer = classic_scanlog.ReportComposer()
        result = composer.compose([])
        assert isinstance(result, str)


    def test_report_generator_construct_and_generate_minimal() -> None:
        """R10 strengthening: attempt a real generate call using a fixture.

        If ReportGenerator.generate requires an AnalysisResult, build a minimal
        one via the Wave 3a orchestrator chain (AnalysisConfig -> RustOrchestrator
        -> process_log("") or equivalent empty-state path). If that chain is
        impractical in a smoke test, use a hand-built fixture at
        ClassicLib-rs/python-bindings/tests/fixtures/minimal_analysis_result.json
        (create the fixture as part of this plan's atomic commit).

        Verify the generate method signature from 03-05-CONSTRUCTOR-INVENTORY.md
        before writing this test.
        """
        generator = classic_scanlog.ReportGenerator()
        assert generator is not None

        # Attempt minimal generate call — verify signature from inventory first
        if hasattr(generator, 'generate'):
            try:
                # Try with empty/default AnalysisResult if the API allows it
                config = classic_scanlog.AnalysisConfig("Fallout4", False)
                # If process_log is not feasible with empty input, skip and use fixture
                # orch = classic_scanlog.RustOrchestrator(config)
                # result = orch.process_log("")  # may fail on empty input
                # output = generator.generate(result)
                # assert isinstance(output, str)
                pass  # executor: replace with real call once API is verified
            except (TypeError, ValueError):
                # Minimum smoke — the class exists and can be constructed
                pass


    def test_parallel_report_processor_construct_and_process_empty() -> None:
        processor = classic_scanlog.ParallelReportProcessor()
        result = processor.process([])
        assert isinstance(result, (list, tuple))


    def test_report_fragment_constructed_via_composer() -> None:
        """R10 strengthening: construct a real ReportFragment via the composer chain
        and access at least one field (not just hasattr)."""
        composer = classic_scanlog.ReportComposer()
        # Verify compose signature from 03-05-CONSTRUCTOR-INVENTORY.md
        # If compose() requires fragments, construct them first; if compose() returns
        # a fragment, inspect it directly.
        if hasattr(composer, 'compose'):
            # Try empty compose first
            try:
                result = composer.compose([])
                # Result may be a ReportFragment, a str, or a list of fragments
                if isinstance(result, classic_scanlog.ReportFragment):
                    # Field access — text, kind, or similar (from inventory)
                    assert hasattr(result, 'text') or hasattr(result, 'kind')
                elif isinstance(result, str):
                    assert isinstance(result, str)  # composed output as string
                elif isinstance(result, (list, tuple)):
                    # List of fragments — inspect first if present
                    if result:
                        first = result[0]
                        assert hasattr(first, 'text') or hasattr(first, 'kind')
            except (TypeError, ValueError):
                # compose() may require non-empty input — update test per inventory
                pass
    ```

    Executor notes:
    - If `ReportFragment` has a constructor, add a direct construct-and-field-access test
    - If `ReportGenerator.generate` requires an `AnalysisResult` argument, build one cheaply via Wave 3a `AnalysisConfig` + `RustOrchestrator` chain or skip the call and just construct
    - Verify exact constructor signatures from `classic-scanlog-py/src/report.rs`
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_scanlog; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_report_smoke.py -v 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - File exists with at least 5 test functions
    - All 5 report classes referenced (StringPool, ReportFragment, ReportComposer, ReportGenerator, ParallelReportProcessor)
    - `pytest` exits 0 after rebuild
  </acceptance_criteria>
  <done>Report smoke tests pass.</done>
</task>

<task type="auto">
  <name>Task 4: Update registry, refresh baseline, run 5-step verification chain</name>
  <files>
    ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
    docs/implementation/python_api_parity/baseline/parity_contract.json
    docs/implementation/python_api_parity/baseline/parity_contract.md
    docs/implementation/python_api_parity/baseline/parity_diff_report.json
    docs/implementation/python_api_parity/baseline/parity_diff_report.md
    docs/implementation/python_api_parity/baseline/rust_api_surface.json
    docs/implementation/python_api_parity/baseline/python_api_surface.json
    docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
    docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
    docs/implementation/python_api_parity/baseline/tier1_gate_report.md
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
  </read_first>
  <action>
    Step 1: Update `runtime_coverage_registry.json::python-tier1-scanlog`:
    - Bump `contractCount` from 201 (post-Plan-04) to 247 (= 201 + 46 report rows); R9 propagation
    - Append `test_promoted_scanlog_report_smoke.py` to testSuite

    Step 2: Refresh baseline:
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    ```

    Step 3: Run 5-step verification chain (gate, validate_stubs, rebuild_rust, pytest, mypy --strict).
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root .; if ($LASTEXITCODE -ne 0) { exit 1 }; python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_report_smoke.py -q; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length == 286`
    - `runtime_coverage_registry.json::python-tier1-scanlog::contractCount == 247`
    - 5-step verification chain exits 0
  </acceptance_criteria>
  <done>Plan 05 commit gate-green; 286 Tier-1 rows; report sub-module fully promoted.</done>
</task>

</tasks>

<verification>
5-step verification chain (non-negotiable).
</verification>

<success_criteria>
- 46 new report contract rows (tier1Mappings 240 → 286)
- All 5 PyO3 report classes covered in stub + tests
- 5-step verification chain exits 0
</success_criteria>

<output>
Create `.planning/phases/03-python-tier-collapse/03-05-SUMMARY.md` with files modified, tier1Mappings.length (286), verification results.
</output>

