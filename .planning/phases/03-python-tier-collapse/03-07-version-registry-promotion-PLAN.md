---
phase: 03-python-tier-collapse
plan: 07
type: execute
wave: 7
depends_on: [03-01, 03-02, 03-03, 03-04, 03-05, 03-06]
files_modified:
  - ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs
  - ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi
  - ClassicLib-rs/python-bindings/tests/test_promoted_version_registry_smoke.py
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
    - "All 34 deferred version_registry entries plus 1 Tier-2 runtime-verified row are promoted to parity_contract.json tier1Mappings"
    - "classic_version_registry.pyi covers every promoted symbol (MatchConfidence, MatchResult, VersionMatcher, VersionInfo, AddressLibFormat, AddressLibraryConfig, CompatibleRange, CrashgenConfig, LogLevel, UnknownVersionStrategy, XseConfig, VersionRegistryError, etc.)"
    - "test_promoted_version_registry_smoke.py covers every promoted #[pyclass] with at least one construct/access test"
    - "5-step verification chain exits 0 at plan close; tier1Mappings.length == 348 (313 + 35)"
  artifacts:
    - path: "ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi"
      provides: "Stub entries for all 35 version_registry promoted symbols"
      contains: "class VersionMatcher:"
    - path: "ClassicLib-rs/python-bindings/tests/test_promoted_version_registry_smoke.py"
      provides: "Per-class smoke tests for promoted version_registry types"
      min_lines: 100
    - path: "docs/implementation/python_api_parity/baseline/parity_contract.json"
      provides: "tier1Mappings.length = 348 after Plan 07 commit; python-tier1-version-registry selector bumped"
  key_links:
    - from: "classic_version_registry.pyi::class VersionMatcher"
      to: "classic-version-registry-core::VersionMatcher (via PyVersionMatcher wrapper)"
      via: "parity_contract.json tier1Mapping row"
      pattern: "version_registry\\.|VersionMatcher"
---

<objective>
Promote the 34 deferred Python parity entries for `classic-version-registry-core` plus 1 Tier-2 runtime-verified row (per Question 1: 34 + 1 = 35 net rows). Per A3, all symbols are already `pub use`d at `classic-version-registry-core/src/lib.rs` lines 55-60.

Purpose: Land the version_registry module promotion. This is the third "core domain" promotion plan.

Output:
- 35 new `tier1Mappings` rows in `parity_contract.json` (version_registry sub-modules)
- Updated `classic_version_registry.pyi` covering every promoted `pythonExportPath`
- New `test_promoted_version_registry_smoke.py` with ~10-12 pytest functions
- `runtime_coverage_registry.json::python-tier1-version-registry` selector row refreshed
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
@.planning/phases/03-python-tier-collapse/03-06-SUMMARY.md
@./CLAUDE.md

<interfaces>
<!-- version_registry inventory from RESEARCH.md Question 1 (34 + 1 = 35 net rows) -->

Already pub use'd at classic-version-registry-core/src/lib.rs lines 55-60 (per A3):
- VersionRegistryError
- MatchConfidence
- MatchResult
- VersionMatcher
- AddressLibFormat
- AddressLibraryConfig
- CompatibleRange
- CrashgenConfig
- LogLevel
- UnknownVersionHandling
- UnknownVersionStrategy
- VersionInfo
- XseConfig

Existing 24 Tier-1 version_registry rows are already enrolled. Adding 35 brings total to 59.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Enumerate version_registry symbols, verify lib.rs coverage, author 35 contract rows</name>
  <files>
    ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs
    docs/implementation/python_api_parity/baseline/parity_contract.json
  </files>
  <read_first>
    - ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs (full file — verify A3 lines 55-60)
    - ClassicLib-rs/business-logic/classic-version-registry-core/src/registry.rs (source of truth for VersionMatcher, VersionInfo, etc.)
    - ClassicLib-rs/python-bindings/classic-version-registry-py/src/lib.rs (PyO3 wrapper layout)
    - ClassicLib-rs/python-bindings/classic-version-registry-py/src/*.rs (every wrapper file)
    - docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json (filter ownerModule=version_registry)
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json (find python-tier2-version-registry-runtime entry)
    - docs/implementation/python_api_parity/baseline/parity_contract.json
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 1" (lines 188-218)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 6 — version_registry" (lines 751-756)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Assumption Correction A3"
    - .planning/phases/03-python-tier-collapse/03-01-SUMMARY.md (A10 sizing report)
  </read_first>
  <action>
    Step 1: Verify A3 — confirm every deferred version_registry symbol is already `pub use`d at `classic-version-registry-core/src/lib.rs` lines 55-60. Add narrow `pub use` if missing.

    Step 2: Author 35 tier1Mapping rows. Use IDs prefixed with `version_registry.<sub_area>.<name>`. Coverage:
    - **34 deferred entries:** Each is one row from deferred_runtime_backlog.json
    - **1 Tier-2 runtime-verified migration:** From runtime_coverage_registry.json

    Specific symbols to enroll (verify exact names from -py wrapper sources):
    - VersionRegistryError (exception class)
    - MatchConfidence enum + variants
    - MatchResult class + getters
    - VersionMatcher class + methods
    - VersionInfo class + getters
    - AddressLibFormat enum + variants
    - AddressLibraryConfig class
    - CompatibleRange class
    - CrashgenConfig class
    - LogLevel enum
    - UnknownVersionStrategy enum (or UnknownVersionHandling — verify which name)
    - XseConfig class

    Row shape:
    ```
    {
      "id": "version_registry.<area>.<name>",
      "rustSymbol": "<core symbol>",
      "rustCrate": "classic-version-registry-core",
      "rustKind": "struct" or "enum" or "function",
      "pythonModule": "classic_version_registry",
      "pythonExportPath": "<Python name>",
      "pythonKind": "class" or "method" or "function",
      "pythonArity": <int or null>,
      "ownerModule": "version_registry",
      "tier": "tier1"
    }
    ```

    Step 3: Insert into `parity_contract.json::tier1Mappings`. Final length: 313 + 35 = 348.

    Step 4: Do NOT regenerate baseline until Task 4.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import json; c = json.loads(open('docs/implementation/python_api_parity/baseline/parity_contract.json').read()); rows = [m for m in c['tier1Mappings'] if m.get('ownerModule') == 'version_registry']; print(f'version_registry rows total: {len(rows)}'); assert len(rows) >= 59, f'Expected >=59 (24 existing + 35 new), got {len(rows)}'"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length == 348`
    - At least 35 NEW version_registry rows added (total ~59 = 24 existing + 35 new)
    - Every new row has `ownerModule == 'version_registry'`, `tier == 'tier1'`
    - Key symbols present: VersionRegistryError, MatchConfidence, VersionMatcher, AddressLibFormat, CrashgenConfig, XseConfig
    - `classic-version-registry-core/src/lib.rs` `pub use` block verified (per A3)
  </acceptance_criteria>
  <done>35 version_registry contract rows authored.</done>
</task>

<task type="auto">
  <name>Task 2: Update classic_version_registry.pyi with promoted stub entries</name>
  <files>
    ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi (full file)
    - ClassicLib-rs/python-bindings/classic-version-registry-py/src/*.rs (all wrapper files)
    - docs/implementation/python_api_parity/baseline/parity_contract.json (35 new rows from Task 1)
  </read_first>
  <action>
    Hand-edit `classic_version_registry.pyi` to add stub entries. Match existing style.

    Key additions (verify all signatures from PyO3 sources):
    ```python
    class VersionRegistryError(Exception):
        """Base exception for version registry errors."""
        ...

    class MatchConfidence:
        """Match confidence enum."""
        EXACT: MatchConfidence
        HIGH: MatchConfidence
        LOW: MatchConfidence
        NONE: MatchConfidence

    class MatchResult:
        """Result of a version match operation."""
        confidence: MatchConfidence
        version: str | None
        # ... fields

    class VersionMatcher:
        """Version matcher for game binaries."""
        def __init__(self) -> None: ...
        def match_version(self, path: str) -> MatchResult: ...
        # ... methods

    class VersionInfo:
        """Information about a registered version."""
        name: str
        version: str
        # ... fields

    class AddressLibFormat:
        """Address library format enum."""
        AE: AddressLibFormat
        SE: AddressLibFormat
        # ... variants

    class AddressLibraryConfig:
        """Address library configuration."""
        # ...

    class CompatibleRange:
        """Compatible version range."""
        # ...

    class CrashgenConfig:
        """Crashgen plugin configuration."""
        # ...

    class LogLevel:
        """Log level enum."""
        DEBUG: LogLevel
        INFO: LogLevel
        WARN: LogLevel
        ERROR: LogLevel

    class UnknownVersionStrategy:
        """Strategy for unknown versions."""
        # ...

    class XseConfig:
        """XSE loader configuration."""
        # ...
    ```

    Verify enum variant names against the actual `#[pyclass(eq, eq_int)]` declarations in the -py source.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `classic_version_registry.pyi` contains all promoted classes (VersionRegistryError, MatchConfidence, MatchResult, VersionMatcher, VersionInfo, AddressLibFormat, AddressLibraryConfig, CompatibleRange, CrashgenConfig, LogLevel, UnknownVersionStrategy, XseConfig)
    - `mypy --strict classic_version_registry.pyi` exits 0
  </acceptance_criteria>
  <done>version_registry stub additions complete; mypy clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create test_promoted_version_registry_smoke.py</name>
  <files>
    ClassicLib-rs/python-bindings/tests/test_promoted_version_registry_smoke.py
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py (existing reference)
    - ClassicLib-rs/python-bindings/classic-version-registry-py/src/*.rs (constructor signatures)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 6 — version_registry" (lines 751-756)
  </read_first>
  <behavior>
    Per D-07 per-class smoke tests. Target: ~10-12 tests.

    Tests:
    - `test_version_registry_error_is_exception_class`
    - `test_match_confidence_enum_constants`
    - `test_match_result_field_access` (via factory or direct)
    - `test_version_matcher_construct_and_match` (minimal call)
    - `test_version_info_class_exists`
    - `test_address_lib_format_enum_constants`
    - `test_address_library_config_class_exists`
    - `test_compatible_range_class_exists`
    - `test_crashgen_config_class_exists`
    - `test_log_level_enum_constants`
    - `test_unknown_version_strategy_enum_or_class_exists`
    - `test_xse_config_class_exists`
  </behavior>
  <action>
    Create `test_promoted_version_registry_smoke.py`:

    ```python
    """Per-class smoke tests for Phase 3 Plan 07 — classic-version-registry-py promotions.

    Covers 35 promoted contract rows (34 deferred + 1 Tier-2 migration).
    """
    from __future__ import annotations

    import classic_version_registry


    def test_version_registry_error_is_exception_class() -> None:
        assert issubclass(classic_version_registry.VersionRegistryError, Exception)


    def test_match_confidence_enum_constants() -> None:
        attrs = [name for name in dir(classic_version_registry.MatchConfidence) if not name.startswith("_")]
        assert len(attrs) > 0


    def test_match_result_class_exists() -> None:
        assert hasattr(classic_version_registry, "MatchResult")


    def test_version_matcher_construct() -> None:
        matcher = classic_version_registry.VersionMatcher()
        assert matcher is not None


    def test_version_info_class_exists() -> None:
        assert hasattr(classic_version_registry, "VersionInfo")


    def test_address_lib_format_enum_constants() -> None:
        attrs = [name for name in dir(classic_version_registry.AddressLibFormat) if not name.startswith("_")]
        assert len(attrs) > 0


    def test_address_library_config_class_exists() -> None:
        assert hasattr(classic_version_registry, "AddressLibraryConfig")


    def test_compatible_range_class_exists() -> None:
        assert hasattr(classic_version_registry, "CompatibleRange")


    def test_crashgen_config_class_exists() -> None:
        assert hasattr(classic_version_registry, "CrashgenConfig")


    def test_log_level_enum_constants() -> None:
        attrs = [name for name in dir(classic_version_registry.LogLevel) if not name.startswith("_")]
        assert len(attrs) > 0


    def test_unknown_version_strategy_class_exists() -> None:
        assert hasattr(classic_version_registry, "UnknownVersionStrategy")


    def test_xse_config_class_exists() -> None:
        assert hasattr(classic_version_registry, "XseConfig")
    ```

    Executor notes:
    - Many version_registry types are constructed via deserialization from YAML, not direct Python constructors. The `hasattr` smoke is the minimum.
    - Where a class HAS a constructor, upgrade to construct + call one method.
    - Verify each `#[pyclass]` is registered in `classic-version-registry-py/src/lib.rs::classic_version_registry` (Pitfall 4 protection).
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_version_registry; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_version_registry_smoke.py -v 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - File exists with at least 12 test functions
    - All promoted version_registry classes referenced
    - `pytest` exits 0 after rebuild
  </acceptance_criteria>
  <done>version_registry smoke tests pass.</done>
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
    - Bump `python-tier1-version-registry::contractCount` from 24 to 59 (= 24 existing + 35 new)
    - Append `test_promoted_version_registry_smoke.py` to its testSuite
    - DELETE the 1 Tier-2 explicit-binding `python-tier2-version-registry-runtime` row (if present) — its data is now in tier1Mappings

    Step 2: Refresh baseline per D-03.

    Step 3: Run 5-step verification chain.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root .; if ($LASTEXITCODE -ne 0) { exit 1 }; python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_version_registry_smoke.py -q; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length == 348`
    - `runtime_coverage_registry.json::python-tier1-version-registry::contractCount == 59`
    - 5-step verification chain exits 0
  </acceptance_criteria>
  <done>Plan 07 commit gate-green; 348 Tier-1 rows; version_registry promotion complete.</done>
</task>

</tasks>

<verification>
5-step verification chain (non-negotiable).
</verification>

<success_criteria>
- 35 new version_registry contract rows (tier1Mappings 313 → 348)
- 1 Tier-2 explicit binding row migrated
- version_registry smoke test file with ~12 tests passing
- 5-step verification chain exits 0
</success_criteria>

<output>
Create `.planning/phases/03-python-tier-collapse/03-07-SUMMARY.md` with files modified, tier1Mappings.length (348), verification results.
</output>
