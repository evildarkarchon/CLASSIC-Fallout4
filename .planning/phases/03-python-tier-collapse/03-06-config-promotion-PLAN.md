---
phase: 03-python-tier-collapse
plan: 06
type: execute
wave: 6
depends_on: [03-01, 03-02, 03-03, 03-04, 03-05]
files_modified:
  - ClassicLib-rs/business-logic/classic-config-core/src/lib.rs
  - ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi
  - ClassicLib-rs/python-bindings/tests/test_promoted_config_smoke.py
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
    - "All 22 deferred config entries plus 4 Tier-2 runtime-verified config rows are promoted to parity_contract.json tier1Mappings"
    - "classic_config.pyi covers every promoted symbol; mypy --strict clean"
    - "test_promoted_config_smoke.py constructs every promoted #[pyclass] (CrashgenEntryRaw, CoreModEntry, CoreModExclude, ModConflictEntry, ModSolutionEntry/Criteria, SuspectErrorRule, SuspectStackRule, SuspectStackCountRule, etc.) and calls one method or accesses one field per class"
    - "5-step verification chain exits 0 at plan close; tier1Mappings.length == 313 (287 + 26)"
  artifacts:
    - path: "ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi"
      provides: "Stub entries for all 26 config promoted symbols"
      contains: "class CrashgenEntryRaw:"
    - path: "ClassicLib-rs/python-bindings/tests/test_promoted_config_smoke.py"
      provides: "Per-class smoke tests for promoted config types"
      min_lines: 80
    - path: "docs/implementation/python_api_parity/baseline/parity_contract.json"
      provides: "tier1Mappings.length = 313 after Plan 06 commit; new selector entry python-tier1-config bumped"
  key_links:
    - from: "classic_config.pyi::class CrashgenEntryRaw"
      to: "classic-config-core::CrashgenEntryRaw (from classic-crashgen-settings-core re-export per A5)"
      via: "parity_contract.json tier1Mapping row"
      pattern: "scanlog\\.config\\.|config\\.CrashgenEntryRaw"
---

<objective>
Promote the 22 deferred Python parity entries for `classic-config-core` plus 4 Tier-2 runtime-verified rows (per Question 1: "22 + 4" = 26 net rows). Per A5, `classic-crashgen-settings-core` does NOT have its own `-py` adapter — its types (`SuspectErrorRule`, `SuspectStackRule`, `ModConflictEntry`, etc.) are re-exported through `classic-config-core` and surfaced via `classic-config-py`. Per A3, all symbols are already `pub use`d at `classic-config-core/src/lib.rs` lines 17-21.

Purpose: Land the config module promotion. This is the second of three "core domain" promotion plans (after scanlog Waves 1-3b, before version_registry).

Output:
- 26 new `tier1Mappings` rows in `parity_contract.json` (config sub-modules)
- Updated `classic_config.pyi` covering every promoted `pythonExportPath`
- New `test_promoted_config_smoke.py` with ~8-12 pytest functions
- `runtime_coverage_registry.json::python-tier1-config` selector row refreshed (bumped contractCount)
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
@.planning/phases/03-python-tier-collapse/03-05-SUMMARY.md
@./CLAUDE.md

<interfaces>
<!-- Config inventory from RESEARCH.md Question 1 -->

22 deferred backlog entries + 4 Tier-2 runtime-verified migrations = 26 net rows

Key types from classic-config-core/src/lib.rs (lines 17-21 — already pub use'd per A3):
- ConfigError
- CoreModEntry
- CoreModExclude
- CrashgenEntryRaw
- ModConflictEntry
- ModSolutionCriteria
- ModSolutionEntry
- SuspectErrorRule
- SuspectStackCountRule
- SuspectStackRule
- YamlDataCore
- format_registry_game_version (free fn)
- resolve_registry_version_info (free fn)

Existing 15 Tier-1 config rows already enrolled. Adding ~26 more brings the total to ~41.

PER A5: classic-crashgen-settings-core types flow through classic-config-py wrappers. Plan 06 contract rows have rustCrate=classic-config-core (since the parser reads classic-config-core/src/lib.rs).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Enumerate config symbols, verify lib.rs coverage, author 26 contract rows</name>
  <files>
    ClassicLib-rs/business-logic/classic-config-core/src/lib.rs
    docs/implementation/python_api_parity/baseline/parity_contract.json
  </files>
  <read_first>
    - ClassicLib-rs/business-logic/classic-config-core/src/lib.rs (full file — verify A3 lines 17-21)
    - ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs (YamlDataCore source of truth)
    - ClassicLib-rs/python-bindings/classic-config-py/src/lib.rs (PyO3 wrapper layout)
    - ClassicLib-rs/python-bindings/classic-config-py/src/*.rs (every wrapper file — get exact pythonExportPath names)
    - docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json (filter ownerModule=config)
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json (find existing python-tier2-config-runtime entries — these are the 4 migration candidates)
    - docs/implementation/python_api_parity/baseline/parity_contract.json
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 1" (lines 188-218) — config row counts
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Assumption Correction A5" (classic-crashgen-settings-core flows through config)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Assumption Correction A3" (config symbols already pub use'd)
    - .planning/phases/03-python-tier-collapse/03-01-SUMMARY.md (A10 sizing report — check for newly-surfaced config symbols)
  </read_first>
  <action>
    Step 1: Verify A3 — confirm every deferred config symbol is already `pub use`d at `classic-config-core/src/lib.rs` lines 17-21. If any new symbol is missing, add a narrow `pub use` line.

    Step 2: Author 26 tier1Mapping rows. Use IDs prefixed with `config.<sub_area>.<name>`. Coverage:
    - **22 deferred entries:** Each is one row. Walk `deferred_runtime_backlog.json` filtered to `ownerModule == "config"`, extract the bindingIdentifier, derive the rustSymbol from the corresponding `-py/src/*.rs` wrapper file, and author the row.
    - **4 Tier-2 runtime-verified migrations:** Walk `runtime_coverage_registry.json` for entries like `python-tier2-config-runtime` or similar — these have `bindingIdentifiers` but no matching `tier1Mapping`. Each becomes one new tier1Mapping row.

    Row shape:
    ```
    {
      "id": "config.<sub_area>.<name>",
      "rustSymbol": "<core symbol>",
      "rustCrate": "classic-config-core",
      "rustKind": "struct" or "enum" or "function",
      "pythonModule": "classic_config",
      "pythonExportPath": "<Python name>",
      "pythonKind": "class" or "function",
      "pythonArity": <int or null>,
      "ownerModule": "config",
      "tier": "tier1"
    }
    ```

    Specifically expected entries (from Q1 + spot-check at lines 17-21 of classic-config-core/src/lib.rs):
    - CrashgenEntryRaw (class) + its #[pymethods]
    - CoreModEntry, CoreModExclude (classes + helpers)
    - ModConflictEntry, ModSolutionEntry, ModSolutionCriteria
    - SuspectErrorRule, SuspectStackRule, SuspectStackCountRule
    - format_registry_game_version, resolve_registry_version_info (free fns)
    - YamlDataCore methods/getters
    - 4 Tier-2 runtime-verified bindings (whatever runtime_coverage_registry shows)

    Step 3: Insert into `parity_contract.json::tier1Mappings`. Final length: 287 + 26 = 313.

    Step 4: Do NOT regenerate baseline until Task 4.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import json; c = json.loads(open('docs/implementation/python_api_parity/baseline/parity_contract.json').read()); rows = [m for m in c['tier1Mappings'] if m.get('ownerModule') == 'config' and m['id'].startswith('config.')]; print(f'config rows total: {len(rows)}'); assert len(rows) >= 41, f'Expected >=41 (15 existing + 26 new), got {len(rows)}'"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length == 313`
    - At least 26 NEW config rows added (total config rows ~41 = 15 existing + 26 new)
    - Every new row has `ownerModule == 'config'`, `tier == 'tier1'`, valid `rustSymbol` referencing classic-config-core surface
    - Key symbols present: CrashgenEntryRaw, ModConflictEntry, SuspectErrorRule, SuspectStackRule, YamlDataCore-related rows
    - `classic-config-core/src/lib.rs` `pub use` block verified (per A3)
  </acceptance_criteria>
  <done>26 config contract rows authored.</done>
</task>

<task type="auto">
  <name>Task 2: Update classic_config.pyi with config stub entries</name>
  <files>
    ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi (full file)
    - ClassicLib-rs/python-bindings/classic-config-py/src/*.rs (all wrapper files — exact #[pymethods] signatures)
    - docs/implementation/python_api_parity/baseline/parity_contract.json (26 new config rows from Task 1)
  </read_first>
  <action>
    Hand-edit `classic_config.pyi` to add stub entries for all 26 new config rows. Match the existing stub style.

    Key additions (verify exact signatures from PyO3 sources):
    ```python
    class CrashgenEntryRaw:
        """Raw crashgen settings entry from YAML."""
        name: str
        version: str
        # ... fields from #[pyo3(get)]

    class CoreModEntry:
        """Core mod entry from YAML configuration."""
        # ...

    class CoreModExclude:
        """Core mod exclusion entry."""
        # ...

    class ModConflictEntry:
        """A documented mod conflict."""
        mod_a: str
        mod_b: str
        description: str

    class ModSolutionCriteria:
        """Criteria for mod solution applicability."""
        # ...

    class ModSolutionEntry:
        """A documented mod solution."""
        # ...

    class SuspectErrorRule:
        """Suspect error rule from YAML."""
        # ...

    class SuspectStackRule:
        """Suspect stack rule with depth limits."""
        # ...

    class SuspectStackCountRule:
        """Stack count threshold rule."""
        # ...

    def format_registry_game_version(version: str) -> str: ...
    def resolve_registry_version_info(text: str) -> dict[str, str] | None: ...
    ```

    Plus any new methods on the existing `YamlDataCore` class.

    Preserve all existing docstrings and annotations.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `classic_config.pyi` contains class declarations for all promoted classes (CrashgenEntryRaw, CoreModEntry, CoreModExclude, ModConflictEntry, ModSolutionCriteria, ModSolutionEntry, SuspectErrorRule, SuspectStackRule, SuspectStackCountRule)
    - Top-level free functions present (format_registry_game_version, resolve_registry_version_info)
    - `mypy --strict classic_config.pyi` exits 0
  </acceptance_criteria>
  <done>Config stub additions complete; mypy clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create test_promoted_config_smoke.py</name>
  <files>
    ClassicLib-rs/python-bindings/tests/test_promoted_config_smoke.py
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py (existing config test reference)
    - ClassicLib-rs/python-bindings/classic-config-py/src/*.rs (constructor signatures)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 6 — config" (lines 744-749)
  </read_first>
  <behavior>
    Per D-07: per-class smoke test. Each promoted #[pyclass] needs at least one construct/access test.
    Target: ~8-12 test functions.

    Tests:
    - `test_crashgen_entry_raw_field_access` — construct via factory or direct, check name/version
    - `test_core_mod_entry_smoke`
    - `test_core_mod_exclude_smoke`
    - `test_mod_conflict_entry_field_access`
    - `test_mod_solution_entry_smoke`
    - `test_mod_solution_criteria_smoke`
    - `test_suspect_error_rule_smoke`
    - `test_suspect_stack_rule_smoke`
    - `test_suspect_stack_count_rule_smoke`
    - `test_format_registry_game_version_smoke` (free fn)
    - `test_resolve_registry_version_info_smoke` (free fn)
    - `test_yaml_data_core_promoted_methods_smoke` (group test for new YamlDataCore methods)
  </behavior>
  <action>
    Create `test_promoted_config_smoke.py`:

    ```python
    """Per-class smoke tests for Phase 3 Plan 06 — classic-config-py promotions.

    Covers 26 promoted contract rows (22 deferred + 4 Tier-2 migrations).
    """
    from __future__ import annotations

    import classic_config


    def test_format_registry_game_version_smoke() -> None:
        result = classic_config.format_registry_game_version("1.10.163")
        assert isinstance(result, str)


    def test_resolve_registry_version_info_smoke() -> None:
        result = classic_config.resolve_registry_version_info("")
        # May return None or empty dict
        assert result is None or isinstance(result, dict)


    def test_crashgen_entry_raw_class_exists() -> None:
        # CrashgenEntryRaw may be constructible only via YAML deserialization
        assert hasattr(classic_config, "CrashgenEntryRaw")


    def test_core_mod_entry_class_exists() -> None:
        assert hasattr(classic_config, "CoreModEntry")


    def test_core_mod_exclude_class_exists() -> None:
        assert hasattr(classic_config, "CoreModExclude")


    def test_mod_conflict_entry_class_exists() -> None:
        assert hasattr(classic_config, "ModConflictEntry")


    def test_mod_solution_entry_class_exists() -> None:
        assert hasattr(classic_config, "ModSolutionEntry")


    def test_mod_solution_criteria_class_exists() -> None:
        assert hasattr(classic_config, "ModSolutionCriteria")


    def test_suspect_error_rule_class_exists() -> None:
        assert hasattr(classic_config, "SuspectErrorRule")


    def test_suspect_stack_rule_class_exists() -> None:
        assert hasattr(classic_config, "SuspectStackRule")


    def test_suspect_stack_count_rule_class_exists() -> None:
        assert hasattr(classic_config, "SuspectStackCountRule")
    ```

    Executor notes:
    - These types are typically constructed via YAML deserialization (`YamlDataCore::from_str`), not direct Python constructors. The `hasattr` smoke is the minimum acceptable.
    - Where a class HAS a Python constructor, upgrade the test to construct + call one method.
    - For full data flow, use the existing test fixture pattern from `test_tier1_parity_smoke.py` (e.g., load a minimal YAML via YamlDataCore and read out a populated CrashgenEntryRaw).
    - Verify each `#[pyclass]` actually has `m.add_class::<>()?;` registration in `classic-config-py/src/lib.rs::classic_config` — if not, the smoke test will hit `AttributeError` (Pitfall 4).
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_config; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_config_smoke.py -v 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - File exists with at least 11 test functions
    - All promoted config classes referenced
    - `pytest` exits 0 after rebuild
  </acceptance_criteria>
  <done>Config smoke tests pass.</done>
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
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json (full file — find python-tier1-config and python-tier2-config-* entries)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 7 — Path A selector recommendation" (lines 829-860)
  </read_first>
  <action>
    Step 1: Update `runtime_coverage_registry.json`:
    - Bump `python-tier1-config::contractCount` from 15 to 41 (= 15 existing + 26 new)
    - Append `test_promoted_config_smoke.py` to its testSuite field
    - DELETE the 4 Tier-2 explicit-binding rows that are now covered by tier1 contract rows (their bindingIdentifiers are now in tier1Mappings)

    Step 2: Refresh baseline:
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    ```

    Step 3: Run 5-step verification chain:
    ```powershell
    python tools/python_api_parity/check_parity_gate.py --repo-root .
    python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings
    pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_config
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi
    ```
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root .; if ($LASTEXITCODE -ne 0) { exit 1 }; python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_config_smoke.py -q; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length == 313`
    - `runtime_coverage_registry.json::python-tier1-config::contractCount == 41`
    - 4 Tier-2 explicit config registry rows DELETED (their data now lives in tier1Mappings)
    - 5-step verification chain exits 0
  </acceptance_criteria>
  <done>Plan 06 commit gate-green; 313 Tier-1 rows; config promotion complete.</done>
</task>

</tasks>

<verification>
5-step verification chain (non-negotiable).
</verification>

<success_criteria>
- 26 new config contract rows (tier1Mappings 287 → 313)
- 4 Tier-2 explicit binding rows migrated to tier1 contract rows
- Config smoke test file with ~11+ tests passing
- 5-step verification chain exits 0
</success_criteria>

<output>
Create `.planning/phases/03-python-tier-collapse/03-06-SUMMARY.md` with files modified, tier1Mappings.length (313), verification results.
</output>
