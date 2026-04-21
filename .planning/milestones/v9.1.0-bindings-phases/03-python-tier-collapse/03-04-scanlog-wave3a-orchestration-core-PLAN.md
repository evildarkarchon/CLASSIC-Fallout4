---
phase: 03-python-tier-collapse
plan: 04
type: execute
wave: 4
depends_on: [03-01, 03-02, 03-03]
files_modified:
  - ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs
  - ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
  - ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave3a_smoke.py
  - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
  - .planning/phases/03-python-tier-collapse/03-04-CONSTRUCTOR-INVENTORY.md
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
    - "All ~50 scanlog Wave 3a deferred entries (orchestrator + papyrus + version + crashgen_registry + segment_key + error sub-modules) are promoted to parity_contract.json tier1Mappings"
    - "classic_scanlog.pyi covers every Wave 3a pythonExportPath (AnalysisConfig, AnalysisResult, CancellationToken, Orchestrator, PapyrusAnalyzer, PapyrusStats, CrashgenVersion, CrashgenVersionStatus, CrashgenRegistry, CheckId, CrashgenEntry, SegmentKey, ScanLogError, PapyrusError)"
    - "test_promoted_scanlog_wave3a_smoke.py covers every promoted #[pyclass] (orchestrator + papyrus + version + crashgen_registry + segment_key) + grouped free-fn tests for parse_crashgen_version/check_crashgen_version_status"
    - "5-step verification chain exits 0 at plan close; tier1Mappings.length == 240 (190 + 50; R9 Plan 03 excluded GLOBAL_FCX_HANDLER)"
  artifacts:
    - path: "ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi"
      provides: "Stub entries for ~50 Wave 3a promoted symbols (orchestration core, not report)"
      contains: "class RustOrchestrator:"
    - path: "ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave3a_smoke.py"
      provides: "Per-class + grouped smoke tests for orchestration & output symbols (excluding report)"
      min_lines: 130
    - path: "docs/implementation/python_api_parity/baseline/parity_contract.json"
      provides: "tier1Mappings.length = 240 after Plan 04 commit"
  key_links:
    - from: "classic_scanlog.pyi::class RustOrchestrator"
      to: "classic-scanlog-core::orchestrator::Orchestrator (via PyRustOrchestrator wrapper)"
      via: "parity_contract.json tier1Mapping row"
      pattern: "\"id\":\\s*\"scanlog\\.orchestrator\\."
---

<objective>
Promote ~50 deferred Python parity entries for scanlog Wave 3a (orchestration core, excluding report which is its own Plan 05). Wave 3a covers 6 sub-modules of `classic-scanlog-core`: `orchestrator` (~23), `papyrus` (~15), `version` (5), `crashgen_registry` (4), `segment_key` (1), `error` (2) — totaling ~50 rows per RESEARCH.md Question 2 (Wave 3 is 96 total, minus report's 46).

Per A6, the correct sub-module list is `orchestrator, report, papyrus, version, crashgen_registry, segment_key, error` (NOT `crashgen_rules` or `core_mod_convert` which don't exist in `-core`). Per A3, all Wave 3a symbols are already `pub use`d.

Purpose: Land the scanlog Wave 3a promotion (orchestration & output minus report). Report is split into Plan 05 for bisect clarity and to manage the heavier 46-row test surface.

Output:
- ~50 new `tier1Mappings` rows in `parity_contract.json` (Wave 3a sub-modules)
- Updated `classic_scanlog.pyi` covering Wave 3a symbols
- New `test_promoted_scanlog_wave3a_smoke.py` with ~10-14 pytest functions
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
@.planning/phases/03-python-tier-collapse/03-03-SUMMARY.md
@./CLAUDE.md

<interfaces>
<!-- Wave 3a inventory (Wave 3 96 minus report 46 = 50 rows) from RESEARCH.md Question 2 -->

Wave 3a sub-modules:
- orchestrator: 23 rows (PyAnalysisConfig + PyAnalysisResult + PyCancellationToken + PyRustOrchestrator + ScanProgressPhase + resolve_batch_concurrency helpers)
- papyrus: 15 rows (PyPapyrusAnalyzer + PyPapyrusStats + PapyrusError + papyrus_logging helpers)
- version: 5 rows (PyCrashgenVersion + PyCrashgenVersionStatus + parse_crashgen_version + check_crashgen_version_status + crashgen_version_gen)
- crashgen_registry: 4 rows (CheckId + CrashgenEntry + CrashgenRegistry)
- segment_key: 1 row
- error: 2 rows (ScanLogError)

Key wrappers (Python-facing names):
- `AnalysisConfig` (from PyAnalysisConfig)
- `AnalysisResult` (from PyAnalysisResult)
- `CancellationToken` (from PyCancellationToken)
- `RustOrchestrator` (from PyRustOrchestrator) — note the rename to RustOrchestrator
- `ScanProgressPhase` (enum)
- `PapyrusAnalyzer` (from PyPapyrusAnalyzer)
- `PapyrusStats` (from PyPapyrusStats)
- `PapyrusError` (exception)
- `CrashgenVersion` (from PyCrashgenVersion)
- `CrashgenVersionStatus` (enum from PyCrashgenVersionStatus)
- `CrashgenRegistry`, `CrashgenEntry`, `CheckId`
- `ScanLogError` (exception)

Free function groups:
- version: `parse_crashgen_version`, `check_crashgen_version_status`, `crashgen_version_gen`
- orchestrator: `resolve_batch_concurrency`
- papyrus: `papyrus_logging` module-level helpers
</interfaces>
</context>

<tasks>


<task type="auto">
  <name>Task 0: Verify Wave 3a constructor signatures — record in 03-04-CONSTRUCTOR-INVENTORY.md</name>
  <files>
    .planning/phases/03-python-tier-collapse/03-04-CONSTRUCTOR-INVENTORY.md
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/orchestrator.rs (especially PyAnalysisConfig::new — verify exact argument types and defaults)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/papyrus.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/version.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/crashgen_registry.rs (or wherever CrashgenRegistry lives — if in -core only, wrap location)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/segment_key.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/error.rs
  </read_first>
  <action>
    For each Wave 3a #[pyclass] wrapper this plan promotes, read the `#[pymethods] fn new` signature from its -py source file. Record to `.planning/phases/03-python-tier-collapse/03-04-CONSTRUCTOR-INVENTORY.md`:

    | PyO3 name | Rust wrapper | Source file | fn new signature | Notes |
    |-----------|--------------|-------------|------------------|-------|
    | AnalysisConfig | PyAnalysisConfig | orchestrator.rs | verify exact game-arg type: str vs enum | first-class constructor |
    | AnalysisResult | PyAnalysisResult | orchestrator.rs | factory only | via RustOrchestrator.process_log |
    | CancellationToken | PyCancellationToken | orchestrator.rs | verify | likely parameterless |
    | RustOrchestrator | PyRustOrchestrator | orchestrator.rs | takes AnalysisConfig | |
    | ScanProgressPhase | PyScanProgressPhase | orchestrator.rs | enum — no constructor | verify variant names (QUEUED, SCANNING, REPORT_BUILD, COMPLETED, etc.) |
    | PapyrusAnalyzer | PyPapyrusAnalyzer | papyrus.rs | verify | |
    | PapyrusStats | PyPapyrusStats | papyrus.rs | factory only | via analyzer.analyze() |
    | PapyrusError | PyPapyrusError | papyrus.rs | exception class | issubclass(Exception) check |
    | CrashgenVersion | PyCrashgenVersion | version.rs | verify has `#[new]` or only factory via parse_crashgen_version | |
    | CrashgenVersionStatus | PyCrashgenVersionStatus | version.rs | enum | verify variant names |
    | CrashgenRegistry | PyCrashgenRegistry | crashgen_registry.rs or core equivalent | verify exact constructor + method names (len, is_empty, list_crashgens?) |
    | CrashgenEntry | PyCrashgenEntry | crashgen_registry.rs | factory only | |
    | CheckId | PyCheckId | crashgen_registry.rs | factory only | |
    | SegmentKey | PySegmentKey | segment_key.rs | verify | |
    | ScanLogError | PyScanLogError | error.rs | exception class | |

    All subsequent tests MUST use verified signatures.

    CRITICAL: Resolve the `ScanProgressPhase` variant names specifically. The Plan 04 tests use `dir()` discovery, which is replaced by direct variant access per R10. Record the EXACT variant names in the inventory (e.g., `QUEUED`, `SCANNING`, `REPORT_BUILD`, `COMPLETED`, or whatever the enum actually has).

    Also verify the `CrashgenRegistry` method surface — `len()`, `is_empty()`, `list_crashgens()`, `get()`, etc. At least one concrete method must exist for R10 testing.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "if (-not (Test-Path '.planning/phases/03-python-tier-collapse/03-04-CONSTRUCTOR-INVENTORY.md')) { Write-Error 'Inventory missing'; exit 1 }; Write-Host 'Constructor inventory present'"</automated>
  </verify>
  <acceptance_criteria>
    - Inventory file exists with one row per Wave 3a #[pyclass]
    - ScanProgressPhase variant names verified from source
    - CrashgenRegistry method surface verified from source
  </acceptance_criteria>
  <done>Wave 3a constructor inventory written; all wrapper signatures verified.</done>
</task>
<task type="auto">
  <name>Task 1: Enumerate Wave 3a symbols, verify -core/lib.rs coverage, author ~50 contract rows</name>
  <files>
    ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs
    docs/implementation/python_api_parity/baseline/parity_contract.json
  </files>
  <read_first>
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs (full file — verify A3)
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/papyrus.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/crashgen_registry.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/segment_key.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/error.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/orchestrator.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/papyrus.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/version.rs
    - docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json (filter scanlog Wave 3a sub-modules)
    - docs/implementation/python_api_parity/baseline/parity_contract.json
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 2" (lines 237-281) — Wave 3 per-sub-module counts
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 6 — Wave 3" (lines 723-742)
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"Research Amendment A6" (correct sub-module names)
  </read_first>
  <action>
    Step 1: Verify A3 — all Wave 3a symbols already `pub use`d at `classic-scanlog-core/src/lib.rs`. If any missing, add narrow `pub use`.

    Step 2: Author ~50 tier1Mapping rows for Wave 3a sub-modules:
    - **orchestrator (~23 rows):** `AnalysisConfig` class + `#[pymethods]`, `AnalysisResult` class + getters, `CancellationToken` class + methods, `RustOrchestrator` class + methods, `ScanProgressPhase` enum, `resolve_batch_concurrency` free fn
    - **papyrus (~15 rows):** `PapyrusAnalyzer` class + methods, `PapyrusStats` class + getters, `PapyrusError` exception, `papyrus_logging` module-level helpers
    - **version (5 rows):** `CrashgenVersion` class, `CrashgenVersionStatus` enum, `parse_crashgen_version`/`check_crashgen_version_status`/`crashgen_version_gen` free fns
    - **crashgen_registry (4 rows):** `CheckId`, `CrashgenEntry`, `CrashgenRegistry`
    - **segment_key (1 row):** whatever symbol is in the deferred backlog
    - **error (2 rows):** `ScanLogError` class + related helpers

    Use the same row shape as Plans 02/03. IDs: `scanlog.orchestrator.AnalysisConfig`, `scanlog.papyrus.PapyrusAnalyzer`, etc.

    Step 3: Insert into `parity_contract.json::tier1Mappings`. Final length: 190 + 50 = 240.

    Step 4: Do NOT regenerate baseline until Task 4.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import json; c = json.loads(open('docs/implementation/python_api_parity/baseline/parity_contract.json').read()); rows = [m for m in c['tier1Mappings'] if m.get('ownerModule') == 'scanlog' and m['id'].startswith(('scanlog.orchestrator.', 'scanlog.papyrus.', 'scanlog.version.', 'scanlog.crashgen_registry.', 'scanlog.segment_key.', 'scanlog.error.'))]; print(f'Wave 3a rows: {len(rows)}'); assert len(rows) >= 50  # Wave 3a still 50; the R9 offset only affected Wave 2"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length == 240`
    - At least 50 rows have IDs starting with one of `scanlog.orchestrator.`, `scanlog.papyrus.`, `scanlog.version.`, `scanlog.crashgen_registry.`, `scanlog.segment_key.`, `scanlog.error.`
    - No `scanlog.crashgen_rules.` or `scanlog.core_mod_convert.` IDs are authored (per A6 — those sub-modules don't exist in `-core`)
    - `classic-scanlog-core/src/lib.rs` grep shows `pub use` coverage
  </acceptance_criteria>
  <done>50 Wave 3a contract rows authored per A6 corrected sub-module list.</done>
</task>

<task type="auto">
  <name>Task 2: Update classic_scanlog.pyi with Wave 3a stub entries</name>
  <files>
    ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi (post-Plan-03 state)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/orchestrator.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/papyrus.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/version.rs
    - (crashgen_registry / segment_key / error types — check classic-scanlog-core/src/ and any wrapper file)
    - docs/implementation/python_api_parity/baseline/parity_contract.json (Wave 3a rows from Task 1)
  </read_first>
  <action>
    Hand-edit `classic_scanlog.pyi` to add Wave 3a stub entries. Keep style consistent with Plans 02/03. Key additions:

    ```python
    # ==========================================================================
    # Wave 3a: Orchestration Core (report is separate in Plan 05)
    # ==========================================================================

    # orchestrator
    class AnalysisConfig:
        """Configuration for the scan orchestrator."""
        def __init__(self, game: str, fcx_mode: bool) -> None: ...
        def set_crashgen_name(self, name: str) -> None: ...
        # ... all #[pymethods]

    class AnalysisResult:
        """Result of a scan orchestration run."""
        def success(self) -> bool: ...
        def logs_processed(self) -> int: ...
        # ... getters

    class CancellationToken:
        """Cancellation token for cooperative scan cancellation."""
        def __init__(self) -> None: ...
        def cancel(self) -> None: ...
        def is_cancelled(self) -> bool: ...

    class RustOrchestrator:
        """Crash log scan orchestrator."""
        def __init__(self, config: AnalysisConfig) -> None: ...
        def cancel(self) -> None: ...
        def process_log(self, path: str) -> AnalysisResult: ...
        # ... other methods

    class ScanProgressPhase:
        """Scan progress phase enumeration."""
        QUEUED: ScanProgressPhase
        SCANNING: ScanProgressPhase
        REPORT_BUILD: ScanProgressPhase
        COMPLETED: ScanProgressPhase

    def resolve_batch_concurrency(cpu_count: int, log_count: int) -> int:
        """Compute recommended concurrency for a batch scan."""
        ...

    # papyrus
    class PapyrusStats:
        """Papyrus script error statistics."""
        def total_errors(self) -> int: ...
        # ... getters

    class PapyrusAnalyzer:
        """Papyrus log analyzer."""
        def __init__(self) -> None: ...
        def analyze(self, text: str) -> PapyrusStats: ...

    class PapyrusError(Exception):
        """Raised on papyrus analysis failures."""
        ...

    # version
    class CrashgenVersion:
        """Crashgen plugin version."""
        def __init__(self, version_string: str) -> None: ...
        def to_tuple(self) -> tuple[int, int, int]: ...

    class CrashgenVersionStatus:
        """Version comparison result enum."""
        UP_TO_DATE: CrashgenVersionStatus
        OUTDATED: CrashgenVersionStatus
        UNKNOWN: CrashgenVersionStatus

    def parse_crashgen_version(text: str) -> CrashgenVersion | None: ...
    def check_crashgen_version_status(current: CrashgenVersion, latest: CrashgenVersion) -> CrashgenVersionStatus: ...
    def crashgen_version_gen(raw: str) -> str: ...

    # crashgen_registry
    class CheckId:
        """Identifier for a crashgen registry check."""
        ...

    class CrashgenEntry:
        """A single crashgen registry entry."""
        ...

    class CrashgenRegistry:
        """Registry of crashgen checks."""
        def __init__(self) -> None: ...
        # ... methods

    # segment_key
    class SegmentKey:
        """Parser segment key identifier."""
        ...

    # error
    class ScanLogError(Exception):
        """Raised on crash log analysis failures."""
        ...
    ```

    Verify every name against the real PyO3 sources. Particularly:
    - Constructor signature for `AnalysisConfig` (verify game type — likely `str` or enum)
    - `RustOrchestrator.process_log` may be async — if so, use `async def` or regular `def` depending on how PyO3 exposes it
    - `ScanProgressPhase` enum variants — confirm exact names
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `classic_scanlog.pyi` contains class declarations for all Wave 3a classes: AnalysisConfig, AnalysisResult, CancellationToken, RustOrchestrator, ScanProgressPhase, PapyrusAnalyzer, PapyrusStats, PapyrusError, CrashgenVersion, CrashgenVersionStatus, CheckId, CrashgenEntry, CrashgenRegistry, SegmentKey, ScanLogError
    - Free functions present: `def resolve_batch_concurrency(`, `def parse_crashgen_version(`, `def check_crashgen_version_status(`, `def crashgen_version_gen(`
    - `mypy --strict classic_scanlog.pyi` exits 0
  </acceptance_criteria>
  <done>Wave 3a stub additions clean; mypy passes.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create test_promoted_scanlog_wave3a_smoke.py</name>
  <files>
    ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave3a_smoke.py
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave2_smoke.py (reference style)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/orchestrator.rs (constructor + methods source of truth)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/papyrus.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/version.rs
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 6 — Wave 3" (lines 723-742)
  </read_first>
  <behavior>
    Per D-07 per-class + grouped free-fn tests:
    - `test_analysis_config_construct` — AnalysisConfig("Fallout4", False), set_crashgen_name("Buffout 4")
    - `test_cancellation_token_construct_and_check` — CancellationToken(), cancel(), is_cancelled()
    - `test_rust_orchestrator_construct_and_cancel` — constructor + cancel (cheap — no full process_log)
    - `test_analysis_result_field_access` — get via minimal orchestrator path
    - `test_scan_progress_phase_enum` — access QUEUED/SCANNING/etc
    - `test_papyrus_analyzer_analyze_empty`
    - `test_papyrus_stats_field_access`
    - `test_papyrus_error_is_exception_class`
    - `test_crashgen_version_construct_and_to_tuple`
    - `test_crashgen_version_status_enum`
    - `test_version_free_functions_group` — parse_crashgen_version, check_crashgen_version_status, crashgen_version_gen
    - `test_crashgen_registry_construct`
    - `test_scan_log_error_is_exception_class`
    - `test_resolve_batch_concurrency_smoke`

    Target: ~12-14 tests.
  </behavior>
  <action>
    Create `test_promoted_scanlog_wave3a_smoke.py` following the Plan 02/03 pattern:

    ```python
    """Per-class smoke tests for Phase 3 Plan 04 — scanlog Wave 3a (orchestration core)."""
    from __future__ import annotations

    import classic_scanlog


    # orchestrator
    def test_analysis_config_construct_and_setter() -> None:
        config = classic_scanlog.AnalysisConfig("Fallout4", False)
        config.set_crashgen_name("Buffout 4")
        assert config is not None


    def test_cancellation_token_smoke() -> None:
        token = classic_scanlog.CancellationToken()
        assert token.is_cancelled() is False
        token.cancel()
        assert token.is_cancelled() is True


    def test_rust_orchestrator_construct_and_cancel() -> None:
        """R10 strengthening: construct + cancel + inspect token/state beyond mere non-None."""
        config = classic_scanlog.AnalysisConfig("Fallout4", False)  # verify arg type from inventory
        orch = classic_scanlog.RustOrchestrator(config)
        # Inspect state before cancel
        if hasattr(orch, 'is_cancelled'):
            assert orch.is_cancelled() is False
        orch.cancel()
        if hasattr(orch, 'is_cancelled'):
            assert orch.is_cancelled() is True
        elif hasattr(orch, 'cancel_token'):
            token = orch.cancel_token()
            assert token is not None


    def test_scan_progress_phase_enum_constants() -> None:
        """R10 strengthening: access specific variants by name (not dir() length).

        Variant names verified from 03-04-CONSTRUCTOR-INVENTORY.md (read from
        classic-scanlog-py/src/orchestrator.rs before this test was authored).
        Executor: replace the placeholder names below with the REAL variant names
        extracted from the inventory.
        """
        # Example expected variants (VERIFY from source — update per inventory):
        # QUEUED, SCANNING, REPORT_BUILD, COMPLETED
        assert classic_scanlog.ScanProgressPhase.QUEUED is not None
        assert classic_scanlog.ScanProgressPhase.SCANNING is not None
        assert classic_scanlog.ScanProgressPhase.COMPLETED is not None
        # Add any other variants from the inventory


    def test_resolve_batch_concurrency_smoke() -> None:
        result = classic_scanlog.resolve_batch_concurrency(4, 100)
        assert isinstance(result, int)
        assert result > 0


    # papyrus
    def test_papyrus_analyzer_analyze_empty() -> None:
        analyzer = classic_scanlog.PapyrusAnalyzer()
        stats = analyzer.analyze("")
        assert stats is not None


    def test_papyrus_stats_field_access() -> None:
        analyzer = classic_scanlog.PapyrusAnalyzer()
        stats = analyzer.analyze("")
        # Minimal field access — exact field names from papyrus.rs
        assert stats is not None


    def test_papyrus_error_is_exception_class() -> None:
        assert issubclass(classic_scanlog.PapyrusError, Exception)


    # version
    def test_crashgen_version_parse_and_to_tuple() -> None:
        version = classic_scanlog.parse_crashgen_version("1.2.3")
        if version is not None:
            tup = version.to_tuple()
            assert isinstance(tup, tuple)
            assert len(tup) >= 2


    def test_crashgen_version_status_enum_exists() -> None:
        attrs = [name for name in dir(classic_scanlog.CrashgenVersionStatus) if not name.startswith("_")]
        assert len(attrs) > 0


    def test_version_free_functions_group() -> None:
        v1 = classic_scanlog.parse_crashgen_version("1.0.0")
        v2 = classic_scanlog.parse_crashgen_version("1.0.1")
        if v1 is not None and v2 is not None:
            status = classic_scanlog.check_crashgen_version_status(v1, v2)
            assert status is not None
        # crashgen_version_gen with minimal input
        gen = classic_scanlog.crashgen_version_gen("")
        assert isinstance(gen, str)


    # crashgen_registry
    def test_crashgen_registry_construct_and_query() -> None:
        """R10 strengthening: construct AND call at least one method (len/is_empty/list_crashgens)."""
        registry = classic_scanlog.CrashgenRegistry()
        # Verify method surface from 03-04-CONSTRUCTOR-INVENTORY.md
        # At least one of these should exist on an empty registry:
        if hasattr(registry, '__len__'):
            assert len(registry) == 0
        elif hasattr(registry, 'is_empty'):
            assert registry.is_empty() is True
        elif hasattr(registry, 'list_crashgens'):
            result = registry.list_crashgens()
            assert isinstance(result, (list, tuple))
        else:
            raise AssertionError(
                "CrashgenRegistry needs at least one inspection method (len/is_empty/list_crashgens). "
                "Verify from classic-scanlog-py/src/crashgen_registry.rs and update test."
            )


    # error
    def test_scan_log_error_is_exception_class() -> None:
        assert issubclass(classic_scanlog.ScanLogError, Exception)
    ```

    Executor notes:
    - `AnalysisConfig` constructor signature — verify from `orchestrator.rs` if it takes game name as `str`, enum, or tuple
    - `RustOrchestrator.process_log` likely needs a fixture crash log — skip full process, just test construct+cancel
    - `ScanProgressPhase` variant names come from `#[pyclass]` declaration — use `dir()` discovery rather than hard-coding for safety
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_scanlog; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave3a_smoke.py -v 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - File exists with at least 12 test functions
    - Tests cover AnalysisConfig, CancellationToken, RustOrchestrator, ScanProgressPhase, PapyrusAnalyzer, PapyrusStats, PapyrusError, CrashgenVersion, CrashgenVersionStatus, CrashgenRegistry, ScanLogError + free fn group
    - `pytest` exits 0 after rebuild
  </acceptance_criteria>
  <done>Wave 3a smoke tests pass.</done>
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
    Step 1: Update `runtime_coverage_registry.json`:
    - Bump `python-tier1-scanlog::contractCount` from 151 (post-Plan-03) to 201 (= 151 + 50 Wave 3a)
    - ADD a new selector entry `python-tier1-scanlog-wave3a-promoted` (scalar testSuite per R8 pattern) pointing at `test_promoted_scanlog_wave3a_smoke.py`
    - DELETE `python-tier2-scanlog-runtime` (coverageId) — VERIFIED entry contains 4 bindings: `classic_scanlog.CrashgenVersion.to_tuple` (Wave 3a — promoted by THIS plan), `classic_scanlog.LogParser.find_errors` (Wave 1 — Plan 02), `classic_scanlog.PatternMatcher.find_all` (Wave 1 — Plan 02), `classic_scanlog.PatternMatcher.has_match` (Wave 1 — Plan 02). All 4 bindings are now enrolled in tier1Mappings after Plan 04 commits, so the Tier-2 explicit entry is safe to delete here.

    Step 2: Refresh baseline:
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    ```

    Step 3: 5-step verification chain (as Plan 02/03).
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root .; if ($LASTEXITCODE -ne 0) { exit 1 }; python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave3a_smoke.py -q; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length == 240`
    - `runtime_coverage_registry.json::python-tier1-scanlog::contractCount == 202`
    - 5-step verification chain exits 0
  </acceptance_criteria>
  <done>Plan 04 commit gate-green; 240 Tier-1 rows.</done>
</task>

</tasks>

<verification>
5-step verification chain (non-negotiable).
</verification>

<success_criteria>
- 50 new Wave 3a contract rows (tier1Mappings 190 → 240)
- No `crashgen_rules` or `core_mod_convert` sub-module references (per A6)
- Wave 3a smoke test file with ~12-14 tests passing
- 5-step verification chain exits 0
</success_criteria>

<output>
Create `.planning/phases/03-python-tier-collapse/03-04-SUMMARY.md` with files modified, tier1Mappings.length (240), verification results.
</output>

