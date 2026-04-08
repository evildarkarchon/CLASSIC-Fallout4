---
phase: 03-python-tier-collapse
plan: 03
type: execute
wave: 3
depends_on: [03-01, 03-02]
files_modified:
  - ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs
  - ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
  - ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave2_smoke.py
  - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
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
    - "All 58 scanlog Wave 2 deferred entries (mod_detector + suspect_scanner + settings_validator + fcx_handler + gpu_detector) are promoted to parity_contract.json tier1Mappings"
    - "classic_scanlog.pyi covers every Wave 2 pythonExportPath (FcxResetError from quick-260406-syy lands here)"
    - "test_promoted_scanlog_wave2_smoke.py contains per-class tests for PySuspectScanner, PySettingsValidator, PyFcxModeHandler, PyGpuDetector, PyGpuInfo, PyConfigIssue + grouped test for detect_mods_* free functions"
    - "5-step verification chain exits 0 at plan close; tier1Mappings.length == 191 (133 + 58)"
  artifacts:
    - path: "ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi"
      provides: "Stub entries for all 58 Wave 2 promoted symbols"
      contains: "class SuspectScanner:"
    - path: "ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave2_smoke.py"
      provides: "Per-class + grouped smoke tests"
      min_lines: 100
    - path: "docs/implementation/python_api_parity/baseline/parity_contract.json"
      provides: "tier1Mappings.length = 191 after Plan 03 commit"
  key_links:
    - from: "classic_scanlog.pyi::class FcxModeHandler"
      to: "classic-scanlog-core::fcx_handler::FcxModeHandler (via PyFcxModeHandler wrapper)"
      via: "parity_contract.json tier1Mapping row"
      pattern: "\"id\":\\s*\"scanlog\\.fcx_handler\\."
---

<objective>
Promote 58 deferred Python parity entries for scanlog Wave 2 (detection & analysis) to the single enforced Tier-1 contract. Wave 2 covers 5 sub-modules of `classic-scanlog-core`: `mod_detector` (9), `suspect_scanner` (8), `settings_validator` (10), `fcx_handler` (21), `gpu_detector` (10) — totaling 58 rows per RESEARCH.md Question 2.

Per A3, all Wave 2 symbols are already `pub use`d at `classic-scanlog-core/src/lib.rs`, so dominant work is contract rows + stub + smoke tests + registry refresh. Note: `FcxResetError` from quick task 260406-syy lives in `fcx_handler` and is promoted here alongside the rest of Wave 2.

Purpose: Land the scanlog Wave 2 promotion (detection & analysis layer) following the same pattern as Plan 02.

Output:
- 58 new `tier1Mappings` rows in `parity_contract.json` (Wave 2 sub-modules)
- Updated `classic_scanlog.pyi` covering every promoted `pythonExportPath`
- New `test_promoted_scanlog_wave2_smoke.py` with ~10-13 pytest functions
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
@.planning/phases/03-python-tier-collapse/03-01-SUMMARY.md
@.planning/phases/03-python-tier-collapse/03-02-SUMMARY.md
@./CLAUDE.md
@./AGENTS.md

<interfaces>
<!-- Wave 2 inventory from RESEARCH.md Question 2 + Question 6 -->

Wave 2 sub-modules (58 total rows):
- mod_detector: 9 rows (free functions: detect_mods_single, detect_mods_double, detect_mods_important, detect_mods_batch)
- suspect_scanner: 8 rows (PySuspectScanner class)
- settings_validator: 10 rows (PySettingsValidator class)
- fcx_handler: 21 rows (PyFcxModeHandler + PyConfigIssue + GLOBAL_FCX_HANDLER + FcxResetError)
- gpu_detector: 10 rows (PyGpuDetector + PyGpuInfo + PyGpuVendor enum)

Key wrappers (Python-facing names):
- `SuspectScanner` (from PySuspectScanner)
- `SettingsValidator` (from PySettingsValidator)
- `FcxModeHandler` (from PyFcxModeHandler)
- `ConfigIssue` (from PyConfigIssue — factory via FcxModeHandler)
- `GpuDetector` (from PyGpuDetector)
- `GpuInfo` (from PyGpuInfo)
- `GpuVendor` (from PyGpuVendor enum)
- Exception class: `FcxResetError` (from classic-scanlog-core::fcx_handler::FcxResetError)

Free function group in mod_detector (one grouped test):
- `detect_mods_single`, `detect_mods_double`, `detect_mods_important`, `detect_mods_batch`
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Enumerate Wave 2 symbols, verify -core/lib.rs coverage, author 58 contract rows</name>
  <files>
    ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs
    docs/implementation/python_api_parity/baseline/parity_contract.json
  </files>
  <read_first>
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs (full file — verify A3)
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/suspect_scanner.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/settings_validator.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/gpu_detector.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/mod_detector.rs (PyO3 wrapper signatures)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/suspect_scanner.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/settings_validator.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/gpu_detector.rs
    - docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json (filter ownerModule=scanlog Wave 2 sub-modules)
    - docs/implementation/python_api_parity/baseline/parity_contract.json
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 2" (lines 237-281)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 6 — Wave 2" (lines 710-722)
    - .planning/phases/quick/260406-syy-resolve-the-newly-uncovered-python-parit/ (context for FcxResetError)
  </read_first>
  <action>
    Step 1: Verify A3 for Wave 2. Confirm every deferred symbol in mod_detector/suspect_scanner/settings_validator/fcx_handler/gpu_detector is already `pub use`d at `classic-scanlog-core/src/lib.rs`. If any missing, add a narrow `pub use` (expected: 0 per A3 spot-check at lines 46-71).

    Step 2: Author 58 tier1Mapping rows with the same shape as Plan 02:
    ```json
    {
      "id": "scanlog.<sub_module>.<python_export_path>",
      "rustSymbol": "<core symbol>",
      "rustCrate": "classic-scanlog-core",
      "rustKind": "...",
      "pythonModule": "classic_scanlog",
      "pythonExportPath": "...",
      "pythonKind": "...",
      "pythonArity": <int or null>,
      "ownerModule": "scanlog",
      "tier": "tier1"
    }
    ```

    Coverage targets:
    - **mod_detector (9 rows):** 4 free functions (`detect_mods_single`, `detect_mods_double`, `detect_mods_important`, `detect_mods_batch`) + 5 supporting types/helpers
    - **suspect_scanner (8 rows):** `SuspectScanner` class + its `#[pymethods]`
    - **settings_validator (10 rows):** `SettingsValidator` class + its `#[pymethods]`
    - **fcx_handler (21 rows):** `FcxModeHandler` class + methods, `ConfigIssue` class + getters, `GLOBAL_FCX_HANDLER` static, `FcxResetError` exception
    - **gpu_detector (10 rows):** `GpuDetector` class + methods, `GpuInfo` class + getters, `GpuVendor` enum + variants

    Step 3: Insert all 58 rows into `parity_contract.json::tier1Mappings` (sort alphabetically by ID). Final length: 133 + 58 = 191.

    Step 4: Do NOT regenerate the baseline yet — Task 4 handles atomic refresh.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import json; c = json.loads(open('docs/implementation/python_api_parity/baseline/parity_contract.json').read()); rows = [m for m in c['tier1Mappings'] if m.get('ownerModule') == 'scanlog' and m['id'].startswith(('scanlog.mod_detector.', 'scanlog.suspect_scanner.', 'scanlog.settings_validator.', 'scanlog.fcx_handler.', 'scanlog.gpu_detector.'))]; print(f'Wave 2 rows: {len(rows)}'); assert len(rows) >= 58"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length == 191` (= 133 from post-Plan-02 + 58 Wave 2)
    - At least 58 rows have IDs starting with `scanlog.mod_detector.`, `scanlog.suspect_scanner.`, `scanlog.settings_validator.`, `scanlog.fcx_handler.`, or `scanlog.gpu_detector.`
    - Every new row has `ownerModule == 'scanlog'`, `tier == 'tier1'`, non-empty `rustSymbol` and `pythonExportPath`
    - FcxResetError has a contract row (from quick-260406-syy resolution)
    - `classic-scanlog-core/src/lib.rs` grep shows `pub use` coverage for all 58 symbols
  </acceptance_criteria>
  <done>58 Wave 2 contract rows authored; -core/lib.rs pub use verified.</done>
</task>

<task type="auto">
  <name>Task 2: Update classic_scanlog.pyi with Wave 2 stub entries</name>
  <files>
    ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi (current post-Plan-02 state)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/mod_detector.rs (exact #[pymethods] + #[pyfunction] signatures)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/suspect_scanner.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/settings_validator.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs (exact PyFcxModeHandler constructor signature + FcxResetError shape)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/gpu_detector.rs (including PyGpuVendor enum definition)
    - docs/implementation/python_api_parity/baseline/parity_contract.json (58 Wave 2 rows from Task 1)
  </read_first>
  <action>
    Hand-edit `classic_scanlog.pyi` to add stub entries for every Wave 2 contract row's `pythonExportPath`. Follow the Plan 02 style for consistency. Key additions:

    ```python
    # ==========================================================================
    # Wave 2: Detection & Analysis
    # ==========================================================================

    # mod_detector (grouped free functions)
    def detect_mods_single(text: str, mods: dict[str, str]) -> list[str]:
        """Single-pattern mod detection against a crash log string."""
        ...

    def detect_mods_double(text: str, mods: list[tuple[str, str]]) -> list[str]:
        """Double-pattern mod detection (two substrings both required)."""
        ...

    def detect_mods_important(plugins: list[str], warnings: dict[str, str]) -> list[tuple[str, str]]:
        """Important-mod detection with exclude rules."""
        ...

    def detect_mods_batch(logs: list[str], mods: dict[str, str]) -> list[list[str]]:
        """Batched variant of detect_mods_single."""
        ...

    # suspect_scanner
    class SuspectScanner:
        """Suspect crash cause scanner."""
        def __init__(self, config: dict) -> None: ...
        def scan(self, log_text: str) -> list[dict]: ...
        # ... all other #[pymethods]

    # settings_validator
    class SettingsValidator:
        """Validates CLASSIC settings against the merged schema."""
        def __init__(self, config: dict) -> None: ...
        def validate(self, settings: dict) -> list[str]: ...
        # ... all other #[pymethods]

    # fcx_handler
    class ConfigIssue:
        """A configuration issue detected by FcxModeHandler."""
        severity: str
        message: str
        path: str
        # ... all #[pyo3(get)] fields

    class FcxModeHandler:
        """FCX mode configuration validator and reset coordinator."""
        def __init__(self, ignore_missing: bool = False) -> None: ...
        def get_issues(self) -> list[ConfigIssue]: ...
        def reset(self) -> None: ...
        # ... all other #[pymethods]

    class FcxResetError(Exception):
        """Raised when FCX state reset cannot proceed (e.g., contention or already clean)."""
        ...

    # gpu_detector
    class GpuVendor:
        """GPU vendor enum."""
        NVIDIA: GpuVendor
        AMD: GpuVendor
        INTEL: GpuVendor
        UNKNOWN: GpuVendor

    class GpuInfo:
        """Information about a detected GPU."""
        def name(self) -> str: ...
        def vendor(self) -> GpuVendor: ...
        # ... getters

    class GpuDetector:
        """GPU detection from crash log system info."""
        def __init__(self) -> None: ...
        def detect_gpu(self, lines: list[str]) -> GpuInfo | None: ...
        # ... other methods
    ```

    Verify every type (`ConfigIssue`, `GpuInfo`, `GpuVendor`) matches the actual PyO3 signature in `-py/src/*.rs`. Use the exact return type shapes (e.g., `list[str]`, `dict[str, str]`, `tuple[A, B]`, `X | None`).

    Preserve existing docstrings.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `classic_scanlog.pyi` contains `class SuspectScanner:`, `class SettingsValidator:`, `class FcxModeHandler:`, `class ConfigIssue:`, `class GpuDetector:`, `class GpuInfo:`, `class GpuVendor:`, `class FcxResetError`
    - `classic_scanlog.pyi` contains top-level `def detect_mods_single(`, `def detect_mods_double(`, `def detect_mods_important(`, `def detect_mods_batch(`
    - `mypy --strict classic_scanlog.pyi` exits 0
  </acceptance_criteria>
  <done>Wave 2 stub additions clean; mypy --strict passes.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create test_promoted_scanlog_wave2_smoke.py</name>
  <files>
    ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave2_smoke.py
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py (reference style from Plan 02)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/mod_detector.rs (grouping contract)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/suspect_scanner.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/settings_validator.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs (FcxModeHandler constructor requires careful handling — may need mocked state or tmp_path fixture)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/gpu_detector.rs
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 6 — Wave 2" (lines 710-722)
  </read_first>
  <behavior>
    Per D-07 per-class + grouped free-fn tests:
    - `test_mod_detector_free_functions_group` — calls detect_mods_single/double/important/batch with minimal empty input
    - `test_suspect_scanner_scan_empty` — constructs SuspectScanner({}), calls scan("")
    - `test_settings_validator_validate_empty` — constructs SettingsValidator({}), calls validate({})
    - `test_fcx_mode_handler_construct_and_get_issues` — constructs FcxModeHandler(ignore_missing=True), calls get_issues()
    - `test_config_issue_field_access` — gets a ConfigIssue via FcxModeHandler, checks severity attribute
    - `test_fcx_reset_error_is_exception_class` — asserts FcxResetError is a subclass of Exception
    - `test_gpu_detector_detect_empty` — constructs GpuDetector(), calls detect_gpu([])
    - `test_gpu_info_field_access` — constructs via detector, checks name() getter
    - `test_gpu_vendor_enum_constants` — accesses NVIDIA/AMD/INTEL/UNKNOWN variants

    Target: ~9-13 test functions.
  </behavior>
  <action>
    Create `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave2_smoke.py`:

    ```python
    """Per-class smoke tests for Phase 3 Plan 03 — scanlog Wave 2 (detection & analysis).

    Covers 58 promoted contract rows across 5 sub-modules: mod_detector,
    suspect_scanner, settings_validator, fcx_handler, gpu_detector.
    """
    from __future__ import annotations

    import classic_scanlog


    # ========================================================================
    # mod_detector sub-module (grouped free functions)
    # ========================================================================

    def test_mod_detector_free_functions_group() -> None:
        """Grouped test for detect_mods_single/double/important/batch."""
        single = classic_scanlog.detect_mods_single("", {})
        assert isinstance(single, (list, tuple))

        double = classic_scanlog.detect_mods_double("", [])
        assert isinstance(double, (list, tuple))

        important = classic_scanlog.detect_mods_important([], {})
        assert isinstance(important, (list, tuple))

        batch = classic_scanlog.detect_mods_batch([], {})
        assert isinstance(batch, (list, tuple))


    # ========================================================================
    # suspect_scanner sub-module
    # ========================================================================

    def test_suspect_scanner_construct_and_scan_empty() -> None:
        scanner = classic_scanlog.SuspectScanner({})
        result = scanner.scan("")
        assert result is not None


    # ========================================================================
    # settings_validator sub-module
    # ========================================================================

    def test_settings_validator_construct_and_validate_empty() -> None:
        validator = classic_scanlog.SettingsValidator({})
        result = validator.validate({})
        assert result is not None


    # ========================================================================
    # fcx_handler sub-module
    # ========================================================================

    def test_fcx_mode_handler_construct_and_get_issues() -> None:
        # Constructor signature verified from classic-scanlog-py/src/fcx_handler.rs
        handler = classic_scanlog.FcxModeHandler(ignore_missing=True)
        issues = handler.get_issues()
        assert isinstance(issues, (list, tuple))


    def test_config_issue_field_access_after_construction() -> None:
        handler = classic_scanlog.FcxModeHandler(ignore_missing=True)
        issues = handler.get_issues()
        # Empty-state smoke — if there are issues, verify field access works
        if issues:
            first = issues[0]
            assert hasattr(first, "severity")
            assert isinstance(first.severity, str)


    def test_fcx_reset_error_is_exception_class() -> None:
        assert issubclass(classic_scanlog.FcxResetError, Exception)


    # ========================================================================
    # gpu_detector sub-module
    # ========================================================================

    def test_gpu_detector_construct_and_detect_empty() -> None:
        detector = classic_scanlog.GpuDetector()
        result = detector.detect_gpu([])
        # Empty input may return None or empty-state GpuInfo
        assert result is None or hasattr(result, "name")


    def test_gpu_vendor_enum_constants_exist() -> None:
        assert hasattr(classic_scanlog.GpuVendor, "NVIDIA")
        assert hasattr(classic_scanlog.GpuVendor, "AMD")
        assert hasattr(classic_scanlog.GpuVendor, "INTEL")
        assert hasattr(classic_scanlog.GpuVendor, "UNKNOWN")


    def test_gpu_info_returned_from_detector(tmp_path) -> None:
        # Minimal smoke — if detector returns GpuInfo for a synthetic stub, check fields
        detector = classic_scanlog.GpuDetector()
        info = detector.detect_gpu([])
        if info is not None:
            name = info.name()
            assert isinstance(name, str)
    ```

    Executor notes:
    - Verify `FcxModeHandler` constructor signature from `classic-scanlog-py/src/fcx_handler.rs` — if the Rust signature is `new(ignore_missing: bool) -> PyFcxModeHandler` the call is `FcxModeHandler(True)` or `FcxModeHandler(ignore_missing=True)` depending on `#[pyo3(signature = ...)]`.
    - If the constructor signature is different (e.g., takes a config dict), adjust accordingly.
    - If `FcxModeHandler.get_issues()` has global state concerns, consider using `classic_scanlog.reset_fcx_global_state()` or similar helper from the quick-260406-syy resolution to avoid test pollution.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_scanlog; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave2_smoke.py -v 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - File exists with at least 9 `def test_*` functions
    - Tests cover every Wave 2 `#[pyclass]` (SuspectScanner, SettingsValidator, FcxModeHandler, ConfigIssue, GpuDetector, GpuInfo, GpuVendor) + FcxResetError + mod_detector grouped free functions
    - `pytest test_promoted_scanlog_wave2_smoke.py -v` exits 0 after rebuild
  </acceptance_criteria>
  <done>Wave 2 smoke test file created, all tests pass against rebuilt wheel.</done>
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
    - .planning/phases/03-python-tier-collapse/03-02-SUMMARY.md (previous contractCount)
  </read_first>
  <action>
    Step 1: Update `runtime_coverage_registry.json::python-tier1-scanlog`:
    - Bump `contractCount` from Plan 02 value (94) to 152 (= 94 + 58 Wave 2)
    - Append `test_promoted_scanlog_wave2_smoke.py` to the `testSuite` field

    Step 2: Refresh baseline per D-03:
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    ```

    Step 3: Run the 5-step verification chain:
    ```powershell
    python tools/python_api_parity/check_parity_gate.py --repo-root .
    python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings
    pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_scanlog
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
    ```

    All 5 steps must exit 0. If any step fails, fix and re-run.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root .; if ($LASTEXITCODE -ne 0) { exit 1 }; python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave2_smoke.py -q; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi"</automated>
  </verify>
  <acceptance_criteria>
    - `runtime_coverage_registry.json::python-tier1-scanlog::contractCount == 152`
    - `parity_contract.json::tier1Mappings.length == 191`
    - All 5 verification steps exit 0
    - `parity_diff_report.json::summary.tier1_missing_rust == 0`, `tier1_missing_python == 0`
    - `runtime_coverage_summary.json::summary.tier1_missing_runtime_total == 0`
  </acceptance_criteria>
  <done>Plan 03 commit gate-green; 191 Tier-1 rows; 5-step chain exits 0.</done>
</task>

</tasks>

<verification>
Plan-close 5-step verification chain (non-negotiable, same as Plan 02).
</verification>

<success_criteria>
- 58 new Wave 2 contract rows (tier1Mappings grew from 133 to 191)
- FcxResetError promoted (quick-260406-syy resolution integrated)
- Wave 2 smoke test file with ~9-13 tests passing
- 5-step verification chain exits 0
- Atomic single commit per D-06
</success_criteria>

<output>
Create `.planning/phases/03-python-tier-collapse/03-03-SUMMARY.md` with files modified, final tier1Mappings.length (191), smoke test count, verification results.
</output>
