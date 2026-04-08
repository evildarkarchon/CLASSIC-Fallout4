---
phase: 03-python-tier-collapse
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tools/python_api_parity/generate_baseline.py
  - tools/python_api_parity/check_parity_gate.py
  - tools/python_api_parity/tests/__init__.py
  - tools/python_api_parity/tests/test_generate_baseline_targets.py
  - tools/python_api_parity/tests/test_check_parity_gate.py
  - tools/python_api_parity/tests/test_pitfall2_guard.py
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
requirements: [PYT-01, PYT-03]
must_haves:
  truths:
    - "RUST_TARGET_CRATES contains exactly 19 entries (18 -core business-logic crates + 1 foundation classic-shared-py); classic-crashgen-settings-core is excluded"
    - "PYTHON_TARGET_MODULES contains exactly 19 entries mirroring the Rust crate list"
    - "Pitfall 2 guard fires non-zero on a synthetic missing-rustSymbol contract row with the canonical diagnostic text"
    - "Existing 59 Tier-1 contract rows still pass the gate after adding the guard (gate exits 0 on the unchanged contract)"
    - "Sizing report (tier2_gap_total per owner) for newly-surfaced symbols from the 16 currently-untracked crates is captured in the plan SUMMARY for downstream Plans 6/7/8 budgets"
  artifacts:
    - path: "tools/python_api_parity/generate_baseline.py"
      provides: "Expanded RUST_TARGET_CRATES (19 entries), PYTHON_TARGET_MODULES (19 entries), RUST_OWNER_BY_CRATE (19 entries), PYTHON_OWNER_BY_MODULE (19 entries), SQUAD_BY_OWNER (covering 17 new owner labels + aux)"
      contains: "classic-shared-py.*foundation/classic-shared-py/src/lib.rs"
    - path: "tools/python_api_parity/check_parity_gate.py"
      provides: "validate_contract_rust_symbols() Pitfall 2 guard helper called from main() before generate_diff_report()"
      contains: "def validate_contract_rust_symbols"
    - path: "tools/python_api_parity/tests/test_generate_baseline_targets.py"
      provides: "PYT-01 unit guard: every RUST_TARGET_CRATES entry parses to a non-empty symbol list"
    - path: "tools/python_api_parity/tests/test_check_parity_gate.py"
      provides: "PYT-03 snapshot guard: tier1_contract_total invariant test for Plan 9 cleanup"
    - path: "tools/python_api_parity/tests/test_pitfall2_guard.py"
      provides: "D-05 unit test for validate_contract_rust_symbols() with synthetic contract"
    - path: "docs/implementation/python_api_parity/baseline/parity_contract.json"
      provides: "Refreshed baseline (still 59 Tier-1 rows; ownerModules enum extended to 20 entries: scanlog, config, version_registry, aux, yaml, database, file_io, scangame, registry, perf, settings, message, path, constants, version, resource, xse, web, update, shared)"
    - path: "docs/implementation/python_api_parity/baseline/rust_api_surface.json"
      provides: "Refreshed surface from 19 crates; len(scope.target_crates) == 19"
  key_links:
    - from: "tools/python_api_parity/generate_baseline.py::parse_rust_surface()"
      to: "ClassicLib-rs/foundation/classic-shared-py/src/lib.rs"
      via: "RUST_TARGET_CRATES['classic-shared-py'] entry"
      pattern: "classic-shared-py.*foundation/classic-shared-py/src/lib\\.rs"
    - from: "tools/python_api_parity/check_parity_gate.py::main()"
      to: "validate_contract_rust_symbols()"
      via: "called between parse_rust_surface() and generate_diff_report()"
      pattern: "validate_contract_rust_symbols\\(contract, rust_manifest\\)"
---

<objective>
Expand the Python parity tooling to enumerate all 19 binding pairs (18 business-logic `-core` crates + 1 foundation `classic-shared-py`) and add the mechanical Pitfall 2 guard assertion to `check_parity_gate.py`. This is the keystone plan: every downstream Phase 3 plan depends on the expanded `RUST_TARGET_CRATES` / `PYTHON_TARGET_MODULES` to discover symbols and gate them. Without this plan landing first, none of the promotion plans can verify their work.

Purpose: Establish the gate enforcement scaffolding for Phase 3 promotions. Land the long-term Pitfall 2 invariant before any contract row is touched.

Output:
- Expanded `tools/python_api_parity/generate_baseline.py` (5 dicts grow from 3 → 19/20 entries)
- New `validate_contract_rust_symbols()` helper in `tools/python_api_parity/check_parity_gate.py` wired into `main()`
- 4 new Wave 0 test files under `tools/python_api_parity/tests/` proving the expansion and guard
- Refreshed parity baseline (existing 59 Tier-1 rows still pass; tier2_gap_total surfaces newly-discoverable symbols for downstream sizing)
- Sizing report in plan SUMMARY: per-owner tier2_gap_total counts after expansion (informs Plan 6/7/8 task budgets per A10)
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
@./CLAUDE.md
@./AGENTS.md
@.agents/skills/classic-project-guide/SKILL.md

<interfaces>
<!-- Current generate_baseline.py constants (lines 24-52) — replace verbatim with the 19-entry expansion in Task 2 -->

From tools/python_api_parity/generate_baseline.py (lines 24-52):
```python
RUST_TARGET_CRATES: dict[str, str] = {
    "classic-scanlog-core": "ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs",
    "classic-config-core": "ClassicLib-rs/business-logic/classic-config-core/src/lib.rs",
    "classic-version-registry-core": "ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs",
}
RUST_OWNER_BY_CRATE: dict[str, str] = {
    "classic-scanlog-core": "scanlog",
    "classic-config-core": "config",
    "classic-version-registry-core": "version_registry",
}
PYTHON_TARGET_MODULES: dict[str, str] = {
    "classic_scanlog": "ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi",
    "classic_config": "ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi",
    "classic_version_registry": "ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi",
}
PYTHON_OWNER_BY_MODULE: dict[str, str] = {
    "classic_scanlog": "scanlog",
    "classic_config": "config",
    "classic_version_registry": "version_registry",
}
SQUAD_BY_OWNER: dict[str, str] = {
    "scanlog": "Squad A (scanlog/config)",
    "config": "Squad A (scanlog/config)",
    "version_registry": "Squad B (version-registry)",
}
```

From tools/python_api_parity/check_parity_gate.py (lines 169-171, where the guard call site lands):
```python
rust_manifest = parse_rust_surface(repo_root, tier1_rust_symbols)
python_manifest = parse_python_surface(repo_root, tier1_python_exports)
diff_report = generate_diff_report(contract, rust_manifest, python_manifest)
```

From tools/python_api_parity/generate_baseline.py::render_diff_markdown() (line 682, hard-coded owner enum that must be updated):
```python
for owner in ("scanlog", "config", "version_registry", "aux"):
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wave 0 — Create tooling test scaffolding (PYT-01, PYT-03, D-05 unit guards)</name>
  <files>
    tools/python_api_parity/tests/__init__.py
    tools/python_api_parity/tests/test_generate_baseline_targets.py
    tools/python_api_parity/tests/test_check_parity_gate.py
    tools/python_api_parity/tests/test_pitfall2_guard.py
  </files>
  <read_first>
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md (full file)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Validation Architecture" + §"Wave 0 Gaps" (lines 83-128) + §"Question 4" (lines 466-545)
    - .planning/phases/03-python-tier-collapse/03-VALIDATION.md §"Wave 0 Requirements"
    - tools/python_api_parity/generate_baseline.py (full file — understand parse_rust_surface signature, owner_module names, return shape of `entries`)
    - tools/python_api_parity/check_parity_gate.py (full file — understand main() flow, sys.path append, where guard call lands)
  </read_first>
  <behavior>
    Test 1 (test_generate_baseline_targets.py — `test_every_rust_target_parses_to_nonempty_symbols`):
      - Imports `RUST_TARGET_CRATES`, `parse_rust_surface` from `tools.python_api_parity.generate_baseline`
      - Iterates every (crate_name, rel_path) entry; for each calls `parse_rust_surface(repo_root, set())` and asserts the returned manifest has at least one entry whose `crate == crate_name`
      - Asserts `len(RUST_TARGET_CRATES) == 19`
      - Asserts `'classic-shared-py' in RUST_TARGET_CRATES`
      - Asserts `'classic-crashgen-settings-core' not in RUST_TARGET_CRATES` (per A5)
      - Repo root is `Path(__file__).resolve().parents[3]` (climbs up from tools/python_api_parity/tests to repo root)
    Test 2 (test_generate_baseline_targets.py — `test_every_python_target_pyi_file_exists`):
      - Asserts every `.pyi` path in `PYTHON_TARGET_MODULES.values()` resolves to an existing file under repo_root
      - Asserts `len(PYTHON_TARGET_MODULES) == 19`
      - Asserts `'classic_shared' in PYTHON_TARGET_MODULES` and the path equals `'ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi'`
    Test 3 (test_generate_baseline_targets.py — `test_owner_dicts_are_consistent`):
      - Asserts `set(RUST_OWNER_BY_CRATE.keys()) == set(RUST_TARGET_CRATES.keys())`
      - Asserts `set(PYTHON_OWNER_BY_MODULE.keys()) == set(PYTHON_TARGET_MODULES.keys())`
      - Asserts every owner value in both owner dicts is a key in `SQUAD_BY_OWNER`
      - Asserts `'aux' in SQUAD_BY_OWNER` (file_io aux entry needs a squad label)
    Test 4 (test_check_parity_gate.py — `test_tier1_contract_total_snapshot_baseline`):
      - Loads `docs/implementation/python_api_parity/baseline/parity_contract.json`
      - Asserts `len(contract['tier1Mappings']) >= 59` (the Plan 1 baseline; later plans add rows; this is a regression floor)
      - Asserts `'tier2' not in contract.get('tierDefinitions', {}) or True` (this assertion is rewritten in Plan 9; for Plan 1 it's a placeholder that documents the eventual invariant via a `xfail` marker on the strict path)
      - Use `pytest.mark.xfail(reason='tier2 removal lands in Plan 9 (PYT-03)')` decorator on a separate `test_tier2_definition_removed_after_plan_9` function so the snapshot is in place but does not block Plan 1.
    Test 5 (test_pitfall2_guard.py — `test_validate_contract_rust_symbols_passes_when_all_present`):
      - Constructs a synthetic `contract = {'tier1Mappings': [{'id': 'test.foo', 'rustSymbol': 'FooStruct', 'rustCrate': 'classic-test-core'}]}`
      - Constructs a synthetic `rust_manifest = {'symbols': [{'symbol': 'FooStruct'}]}`
      - Asserts `validate_contract_rust_symbols(contract, rust_manifest) == []`
    Test 6 (test_pitfall2_guard.py — `test_validate_contract_rust_symbols_fails_when_symbol_missing`):
      - Constructs `contract = {'tier1Mappings': [{'id': 'test.foo', 'rustSymbol': 'MissingStruct', 'rustCrate': 'classic-test-core'}]}`
      - Constructs `rust_manifest = {'symbols': [{'symbol': 'OtherStruct'}]}`
      - Calls `diagnostics = validate_contract_rust_symbols(contract, rust_manifest)`
      - Asserts `len(diagnostics) == 1`
      - Asserts `"Pitfall 2" in diagnostics[0]`
      - Asserts `"test.foo" in diagnostics[0]`
      - Asserts `"MissingStruct" in diagnostics[0]`
      - Asserts `"classic-test-core" in diagnostics[0]`
    Test 7 (test_pitfall2_guard.py — `test_validate_contract_rust_symbols_fails_when_rustSymbol_missing_from_row`):
      - Constructs `contract = {'tier1Mappings': [{'id': 'test.foo', 'rustCrate': 'classic-test-core'}]}` (no rustSymbol field)
      - Constructs `rust_manifest = {'symbols': []}`
      - Asserts `len(validate_contract_rust_symbols(contract, rust_manifest)) == 1`
      - Asserts `"missing 'rustSymbol'" in diagnostics[0]`
  </behavior>
  <action>
    Create the 4 test files. Use `from __future__ import annotations` at the top of each `*.py` file. The `__init__.py` is empty.

    For `test_generate_baseline_targets.py`:
    ```python
    """PYT-01 unit guard: every RUST_TARGET_CRATES / PYTHON_TARGET_MODULES entry parses cleanly."""
    from __future__ import annotations

    import sys
    from pathlib import Path

    REPO_ROOT = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(REPO_ROOT / "tools" / "python_api_parity"))
    sys.path.insert(0, str(REPO_ROOT / "tools"))

    from generate_baseline import (  # noqa: E402
        PYTHON_OWNER_BY_MODULE,
        PYTHON_TARGET_MODULES,
        RUST_OWNER_BY_CRATE,
        RUST_TARGET_CRATES,
        SQUAD_BY_OWNER,
        parse_rust_surface,
    )


    def test_rust_target_crates_count_is_19() -> None:
        assert len(RUST_TARGET_CRATES) == 19, (
            f"Expected 19 RUST_TARGET_CRATES (18 business-logic + classic-shared-py), "
            f"got {len(RUST_TARGET_CRATES)}"
        )


    def test_classic_shared_py_is_in_rust_target_crates() -> None:
        assert "classic-shared-py" in RUST_TARGET_CRATES
        assert RUST_TARGET_CRATES["classic-shared-py"] == (
            "ClassicLib-rs/foundation/classic-shared-py/src/lib.rs"
        )


    def test_classic_crashgen_settings_core_is_excluded() -> None:
        # Per Phase 3 RESEARCH.md Assumption Correction A5: this crate has no -py adapter
        assert "classic-crashgen-settings-core" not in RUST_TARGET_CRATES


    def test_every_rust_target_parses_to_nonempty_symbols() -> None:
        manifest = parse_rust_surface(REPO_ROOT, set())
        symbols_by_crate: dict[str, int] = {}
        for entry in manifest["symbols"]:
            symbols_by_crate[entry["crate"]] = symbols_by_crate.get(entry["crate"], 0) + 1
        for crate_name in RUST_TARGET_CRATES:
            assert symbols_by_crate.get(crate_name, 0) > 0, (
                f"Crate '{crate_name}' parsed to zero symbols — check the lib.rs path"
            )


    def test_python_target_modules_count_is_19() -> None:
        assert len(PYTHON_TARGET_MODULES) == 19


    def test_classic_shared_pyi_path_is_correct() -> None:
        assert "classic_shared" in PYTHON_TARGET_MODULES
        assert PYTHON_TARGET_MODULES["classic_shared"] == (
            "ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi"
        )


    def test_every_pyi_file_exists_on_disk() -> None:
        for module_name, rel_path in PYTHON_TARGET_MODULES.items():
            full_path = REPO_ROOT / rel_path
            assert full_path.exists(), (
                f"PYTHON_TARGET_MODULES['{module_name}'] -> {rel_path} does not exist"
            )


    def test_owner_dict_keys_match_target_dict_keys() -> None:
        assert set(RUST_OWNER_BY_CRATE.keys()) == set(RUST_TARGET_CRATES.keys())
        assert set(PYTHON_OWNER_BY_MODULE.keys()) == set(PYTHON_TARGET_MODULES.keys())


    def test_every_owner_label_is_in_squad_by_owner() -> None:
        for owner in RUST_OWNER_BY_CRATE.values():
            assert owner in SQUAD_BY_OWNER, (
                f"Owner '{owner}' missing from SQUAD_BY_OWNER"
            )
        for owner in PYTHON_OWNER_BY_MODULE.values():
            assert owner in SQUAD_BY_OWNER, (
                f"Owner '{owner}' missing from SQUAD_BY_OWNER"
            )
        # The aux owner is needed for the file-io aux entry (Plan 8)
        assert "aux" in SQUAD_BY_OWNER, (
            "SQUAD_BY_OWNER must include 'aux' for the classic_file_io.FileHasher.cache_size entry"
        )
    ```

    For `test_check_parity_gate.py`:
    ```python
    """PYT-03 snapshot guard: tier1_contract_total invariant for Plan 9 cleanup."""
    from __future__ import annotations

    import json
    from pathlib import Path

    import pytest

    REPO_ROOT = Path(__file__).resolve().parents[3]
    CONTRACT_PATH = REPO_ROOT / "docs" / "implementation" / "python_api_parity" / "baseline" / "parity_contract.json"


    def test_tier1_contract_total_baseline_floor() -> None:
        """Plan 1 baseline: at least 59 Tier-1 rows. Plans 2-8 will add rows;
        Plan 9 final state should be 362 (= 59 + 285 + 12 + 6) per RESEARCH A4."""
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        assert len(contract["tier1Mappings"]) >= 59


    @pytest.mark.xfail(
        reason="tier2 definition removal lands in Plan 9 (PYT-03); test asserts the eventual invariant",
        strict=False,
    )
    def test_tier2_definition_removed_after_plan_9() -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        tier_definitions = contract.get("tierDefinitions", {})
        assert "tier2" not in tier_definitions, (
            "Plan 9 must delete tierDefinitions.tier2 from parity_contract.json"
        )
    ```

    For `test_pitfall2_guard.py`:
    ```python
    """D-05 unit test for validate_contract_rust_symbols (Pitfall 2 guard)."""
    from __future__ import annotations

    import sys
    from pathlib import Path

    REPO_ROOT = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(REPO_ROOT / "tools" / "python_api_parity"))
    sys.path.insert(0, str(REPO_ROOT / "tools"))

    from check_parity_gate import validate_contract_rust_symbols  # noqa: E402


    def test_validate_passes_when_all_symbols_present() -> None:
        contract = {
            "tier1Mappings": [
                {"id": "test.foo", "rustSymbol": "FooStruct", "rustCrate": "classic-test-core"}
            ]
        }
        rust_manifest = {"symbols": [{"symbol": "FooStruct"}]}
        diagnostics = validate_contract_rust_symbols(contract, rust_manifest)
        assert diagnostics == []


    def test_validate_fails_when_symbol_missing() -> None:
        contract = {
            "tier1Mappings": [
                {"id": "test.foo", "rustSymbol": "MissingStruct", "rustCrate": "classic-test-core"}
            ]
        }
        rust_manifest = {"symbols": [{"symbol": "OtherStruct"}]}
        diagnostics = validate_contract_rust_symbols(contract, rust_manifest)
        assert len(diagnostics) == 1
        assert "Pitfall 2" in diagnostics[0]
        assert "test.foo" in diagnostics[0]
        assert "MissingStruct" in diagnostics[0]
        assert "classic-test-core" in diagnostics[0]


    def test_validate_fails_when_rustSymbol_field_missing() -> None:
        contract = {
            "tier1Mappings": [
                {"id": "test.bar", "rustCrate": "classic-test-core"}
            ]
        }
        rust_manifest = {"symbols": []}
        diagnostics = validate_contract_rust_symbols(contract, rust_manifest)
        assert len(diagnostics) == 1
        assert "missing 'rustSymbol'" in diagnostics[0]
    ```

    NOTE: tests will FAIL until Tasks 2 + 3 land — this is intentional TDD RED. Commit the failing tests in this task; Task 4 turns them GREEN.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest tools/python_api_parity/tests -q --no-header 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - File `tools/python_api_parity/tests/__init__.py` exists (empty)
    - File `tools/python_api_parity/tests/test_generate_baseline_targets.py` exists with 8 test functions
    - File `tools/python_api_parity/tests/test_check_parity_gate.py` exists with 1 normal + 1 xfail test
    - File `tools/python_api_parity/tests/test_pitfall2_guard.py` exists with 3 test functions
    - Tests fail with `ImportError` or assertion failure for the 19-count tests (TDD RED state — Task 4 fixes)
    - `pytest tools/python_api_parity/tests -q --collect-only` collects all 12 test functions without import errors at collection time (the imports themselves work because they reference symbols that exist or will exist after Task 2)
  </acceptance_criteria>
  <done>The 4 Wave 0 test files exist on disk; pytest can collect them; failures match the TDD RED state expected before Tasks 2-4 land the implementation.</done>
</task>

<task type="auto">
  <name>Task 2: Expand RUST_TARGET_CRATES, PYTHON_TARGET_MODULES, and owner/squad dicts in generate_baseline.py</name>
  <files>
    tools/python_api_parity/generate_baseline.py
  </files>
  <read_first>
    - tools/python_api_parity/generate_baseline.py (lines 1-100, 160-230, 670-700)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 3" (lines 285-465) — paste-ready expansion table
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Assumption Correction A5" (excludes classic-crashgen-settings-core)
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"Research Amendments A5"
  </read_first>
  <action>
    Replace lines 24-52 of `tools/python_api_parity/generate_baseline.py` with the 19-entry expansion. Use this exact text (paste verbatim — every value comes from RESEARCH.md Question 3 verified against the live filesystem):

    ```python
    RUST_TARGET_CRATES: dict[str, str] = {
        # Existing 3 (preserved for stability)
        "classic-scanlog-core":          "ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs",
        "classic-config-core":           "ClassicLib-rs/business-logic/classic-config-core/src/lib.rs",
        "classic-version-registry-core": "ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs",
        # Phase 3 additions — 16 more
        "classic-yaml-core":              "ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs",
        "classic-database-core":          "ClassicLib-rs/business-logic/classic-database-core/src/lib.rs",
        "classic-file-io-core":           "ClassicLib-rs/business-logic/classic-file-io-core/src/lib.rs",
        "classic-scangame-core":          "ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs",
        "classic-registry-core":          "ClassicLib-rs/business-logic/classic-registry-core/src/lib.rs",
        "classic-perf-core":              "ClassicLib-rs/business-logic/classic-perf-core/src/lib.rs",
        "classic-settings-core":          "ClassicLib-rs/business-logic/classic-settings-core/src/lib.rs",
        "classic-message-core":           "ClassicLib-rs/business-logic/classic-message-core/src/lib.rs",
        "classic-path-core":              "ClassicLib-rs/business-logic/classic-path-core/src/lib.rs",
        "classic-constants-core":         "ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs",
        "classic-version-core":           "ClassicLib-rs/business-logic/classic-version-core/src/lib.rs",
        "classic-resource-core":          "ClassicLib-rs/business-logic/classic-resource-core/src/lib.rs",
        "classic-xse-core":               "ClassicLib-rs/business-logic/classic-xse-core/src/lib.rs",
        "classic-web-core":               "ClassicLib-rs/business-logic/classic-web-core/src/lib.rs",
        "classic-update-core":            "ClassicLib-rs/business-logic/classic-update-core/src/lib.rs",
        # foundation crate (Phase 3 D-09 / HARM-03)
        "classic-shared-py":              "ClassicLib-rs/foundation/classic-shared-py/src/lib.rs",
        # NOTE: classic-crashgen-settings-core is INTENTIONALLY EXCLUDED — its symbols flow
        # through classic-config-py / classic-scanlog-py / classic-scangame-py wrappers
        # (see .planning/phases/03-python-tier-collapse/03-RESEARCH.md A5).
    }

    RUST_OWNER_BY_CRATE: dict[str, str] = {
        "classic-scanlog-core":          "scanlog",
        "classic-config-core":           "config",
        "classic-version-registry-core": "version_registry",
        "classic-yaml-core":              "yaml",
        "classic-database-core":          "database",
        "classic-file-io-core":           "file_io",
        "classic-scangame-core":          "scangame",
        "classic-registry-core":          "registry",
        "classic-perf-core":              "perf",
        "classic-settings-core":          "settings",
        "classic-message-core":           "message",
        "classic-path-core":              "path",
        "classic-constants-core":         "constants",
        "classic-version-core":           "version",
        "classic-resource-core":          "resource",
        "classic-xse-core":               "xse",
        "classic-web-core":               "web",
        "classic-update-core":            "update",
        "classic-shared-py":              "shared",
    }

    PYTHON_TARGET_MODULES: dict[str, str] = {
        "classic_scanlog":          "ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi",
        "classic_config":           "ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi",
        "classic_version_registry": "ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi",
        "classic_yaml":             "ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi",
        "classic_database":         "ClassicLib-rs/python-bindings/classic-database-py/classic_database.pyi",
        "classic_file_io":          "ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi",
        "classic_scangame":         "ClassicLib-rs/python-bindings/classic-scangame-py/classic_scangame.pyi",
        "classic_registry":         "ClassicLib-rs/python-bindings/classic-registry-py/classic_registry.pyi",
        "classic_perf":             "ClassicLib-rs/python-bindings/classic-perf-py/classic_perf.pyi",
        "classic_settings":         "ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi",
        "classic_message":          "ClassicLib-rs/python-bindings/classic-message-py/classic_message.pyi",
        "classic_path":             "ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi",
        "classic_constants":        "ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi",
        "classic_version":          "ClassicLib-rs/python-bindings/classic-version-py/classic_version.pyi",
        "classic_resource":         "ClassicLib-rs/python-bindings/classic-resource-py/classic_resource.pyi",
        "classic_xse":              "ClassicLib-rs/python-bindings/classic-xse-py/classic_xse.pyi",
        "classic_web":              "ClassicLib-rs/python-bindings/classic-web-py/classic_web.pyi",
        "classic_update":           "ClassicLib-rs/python-bindings/classic-update-py/classic_update.pyi",
        "classic_shared":           "ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi",
    }

    PYTHON_OWNER_BY_MODULE: dict[str, str] = {
        "classic_scanlog":          "scanlog",
        "classic_config":           "config",
        "classic_version_registry": "version_registry",
        "classic_yaml":             "yaml",
        "classic_database":         "database",
        "classic_file_io":          "file_io",
        "classic_scangame":         "scangame",
        "classic_registry":         "registry",
        "classic_perf":             "perf",
        "classic_settings":         "settings",
        "classic_message":          "message",
        "classic_path":             "path",
        "classic_constants":        "constants",
        "classic_version":          "version",
        "classic_resource":         "resource",
        "classic_xse":              "xse",
        "classic_web":              "web",
        "classic_update":           "update",
        "classic_shared":           "shared",
    }

    SQUAD_BY_OWNER: dict[str, str] = {
        # Existing
        "scanlog":          "Squad A (scanlog/config)",
        "config":           "Squad A (scanlog/config)",
        "version_registry": "Squad B (version-registry)",
        # New owners (collapse onto existing two squads to minimize churn — see RESEARCH Q3 recommendation)
        "yaml":      "Squad A (scanlog/config)",
        "database":  "Squad B (version-registry)",
        "file_io":   "Squad A (scanlog/config)",
        "scangame":  "Squad B (version-registry)",
        "registry":  "Squad B (version-registry)",
        "perf":      "Squad B (version-registry)",
        "settings":  "Squad A (scanlog/config)",
        "message":   "Squad B (version-registry)",
        "path":      "Squad B (version-registry)",
        "constants": "Squad B (version-registry)",
        "version":   "Squad B (version-registry)",
        "resource":  "Squad B (version-registry)",
        "xse":       "Squad B (version-registry)",
        "web":       "Squad B (version-registry)",
        "update":    "Squad B (version-registry)",
        "shared":    "Squad B (version-registry)",
        "aux":       "Squad B (version-registry)",  # for the file-io aux entry (Plan 8)
    }
    ```

    Then update `render_diff_markdown()` line 682 (the hard-coded owner tuple). Find the line:
    ```python
    for owner in ("scanlog", "config", "version_registry", "aux"):
    ```
    Replace with:
    ```python
    # Iterate all known owners (Phase 3 D-01 expansion); fall back to known order for stable output.
    _OWNER_RENDER_ORDER = (
        "scanlog", "config", "version_registry", "yaml", "database", "file_io",
        "scangame", "registry", "perf", "settings", "message", "path", "constants",
        "version", "resource", "xse", "web", "update", "shared", "aux",
    )
    for owner in _OWNER_RENDER_ORDER:
    ```
    (Define `_OWNER_RENDER_ORDER` at module top-level near line 53, just below `SQUAD_BY_OWNER`. Then `render_diff_markdown()` references it.)
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "from tools.python_api_parity.generate_baseline import RUST_TARGET_CRATES, PYTHON_TARGET_MODULES, SQUAD_BY_OWNER; assert len(RUST_TARGET_CRATES) == 19; assert len(PYTHON_TARGET_MODULES) == 19; assert 'classic-shared-py' in RUST_TARGET_CRATES; assert 'classic_shared' in PYTHON_TARGET_MODULES; assert 'aux' in SQUAD_BY_OWNER; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `tools/python_api_parity/generate_baseline.py` lines 24-52 contain the 19-entry expansion (run `grep -c "classic-" tools/python_api_parity/generate_baseline.py | head -5` shows ~38+ matches)
    - `RUST_TARGET_CRATES` has 19 entries with `'classic-shared-py'` mapping to `'ClassicLib-rs/foundation/classic-shared-py/src/lib.rs'`
    - `RUST_TARGET_CRATES` does NOT contain `'classic-crashgen-settings-core'`
    - `PYTHON_TARGET_MODULES` has 19 entries with `'classic_shared'` mapping to `'ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi'`
    - `SQUAD_BY_OWNER` contains the `'aux'` key
    - `_OWNER_RENDER_ORDER` constant defined at module level and `render_diff_markdown()` iterates it
    - `python -c "from tools.python_api_parity.generate_baseline import ...; assert len(...) == 19"` exits 0
  </acceptance_criteria>
  <done>Module-level dicts grown to 19 entries each; sorted owner render order constant defined and consumed; smoke import succeeds.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Add validate_contract_rust_symbols() Pitfall 2 guard to check_parity_gate.py</name>
  <files>
    tools/python_api_parity/check_parity_gate.py
  </files>
  <read_first>
    - tools/python_api_parity/check_parity_gate.py (full file)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 4" (lines 466-545) — paste-ready function body and call site
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"D-05" + §"Research Amendment A3"
    - tools/python_api_parity/tests/test_pitfall2_guard.py (the test file from Task 1 — the function must satisfy these tests)
  </read_first>
  <behavior>
    The Task 1 test cases (`test_validate_passes_when_all_symbols_present`, `test_validate_fails_when_symbol_missing`, `test_validate_fails_when_rustSymbol_field_missing`) define the contract.

    Function signature:
    ```python
    def validate_contract_rust_symbols(
        contract: dict[str, Any],
        rust_manifest: dict[str, Any],
    ) -> list[str]:
    ```

    Pure function (no I/O); returns empty list on success; populated list with error strings on failure. Caller decides what to do with the list.
  </behavior>
  <action>
    Add the helper function and wire it into `main()`. Place the function between the existing imports (around line 28-29) and `render_tier1_gate_markdown()` at line 31.

    Insert this function (paste verbatim from RESEARCH.md Question 4):

    ```python
    def validate_contract_rust_symbols(
        contract: dict[str, Any],
        rust_manifest: dict[str, Any],
    ) -> list[str]:
        """Pitfall 2 guard: every Tier-1 contract row's `rustSymbol` must appear
        in the parsed Rust surface.

        Returns a list of human-readable diagnostic strings; empty list means
        success. Failing fast here keeps downstream `tier1_missing_rust` noise
        out of the diff report when the root cause is a missing `pub use` at
        the `-core/lib.rs` surface (per Phase 3 D-05; see RESEARCH A1: the
        `pub use` belongs in `-core/lib.rs`, NOT `-py/lib.rs`).
        """
        rust_symbols: set[str] = {
            item["symbol"] for item in rust_manifest.get("symbols", [])
        }
        diagnostics: list[str] = []
        for mapping in contract.get("tier1Mappings", []):
            rust_symbol = mapping.get("rustSymbol")
            if not rust_symbol:
                diagnostics.append(
                    f"Pitfall 2: contract row '{mapping.get('id', '<unknown>')}' is missing 'rustSymbol'."
                )
                continue
            if rust_symbol not in rust_symbols:
                diagnostics.append(
                    "Pitfall 2: contract row '{id}' references rustSymbol '{rust_symbol}' "
                    "which is not in the parsed Rust surface for crate '{crate}'. "
                    "Add 'pub use <sub_module>::{rust_symbol};' to "
                    "'ClassicLib-rs/business-logic/{crate}/src/lib.rs' (or the appropriate "
                    "foundation/-py lib.rs for classic_shared) before promoting this row.".format(
                        id=mapping["id"],
                        rust_symbol=rust_symbol,
                        crate=mapping.get("rustCrate", "<unknown>"),
                    )
                )
        return diagnostics
    ```

    Then wire it into `main()`. After line 169 (`rust_manifest = parse_rust_surface(...)`) and before line 171 (`diff_report = generate_diff_report(...)`), insert:

    ```python
        rust_manifest = parse_rust_surface(repo_root, tier1_rust_symbols)
        python_manifest = parse_python_surface(repo_root, tier1_python_exports)

        # Pitfall 2 guard (Phase 3 D-05) — fail FAST before downstream diff generation.
        # Catches contract rows whose rustSymbol is not visible at the -core/lib.rs surface,
        # which would otherwise surface as noisy tier1_missing_rust gap rows.
        pitfall2_diagnostics = validate_contract_rust_symbols(contract, rust_manifest)
        if pitfall2_diagnostics:
            print("\n".join(pitfall2_diagnostics), file=sys.stderr)
            return 1

        diff_report = generate_diff_report(contract, rust_manifest, python_manifest)
    ```

    Also ensure `import sys` and `from typing import Any` are present at the top of the file (read line 1-15 of check_parity_gate.py — `sys` and `Any` are already imported per the existing imports; verify before submitting).
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest tools/python_api_parity/tests/test_pitfall2_guard.py -v 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `tools/python_api_parity/check_parity_gate.py` contains `def validate_contract_rust_symbols(`
    - `tools/python_api_parity/check_parity_gate.py` contains `pitfall2_diagnostics = validate_contract_rust_symbols(contract, rust_manifest)` inside `main()`
    - The call site is BEFORE `generate_diff_report(...)` in `main()`
    - All 3 tests in `test_pitfall2_guard.py` pass (TDD GREEN)
    - `python -m pytest tools/python_api_parity/tests/test_pitfall2_guard.py -v` exits 0
  </acceptance_criteria>
  <done>Pitfall 2 guard helper exists, is wired into main() before diff generation, and all test_pitfall2_guard.py tests pass.</done>
</task>

<task type="auto">
  <name>Task 4: Update parity_contract.json::ownerModules enum, refresh baseline, and capture A10 sizing report</name>
  <files>
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
    - docs/implementation/python_api_parity/baseline/parity_contract.json (full file — current state, 59 tier1Mappings, 4 ownerModules)
    - tools/python_api_parity/generate_baseline.py (post-Task-2 — verify the dicts grew)
    - tools/python_api_parity/check_parity_gate.py (post-Task-3 — verify the guard is wired)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 3" §"RUST_OWNER_BY_CRATE discrepancy" (lines 446-462) — ownerModules enum update
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Open Questions" item 2 (lines 967-971) — A10 sizing requirement
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"Research Amendment A10"
  </read_first>
  <action>
    Step 1: Edit `docs/implementation/python_api_parity/baseline/parity_contract.json`. Find the `ownerModules` array (or object) and extend it to include 16 new owner descriptions in addition to the existing 4. The current shape (read it first) determines whether to add an array element or an object key. Likely shape:
    ```json
    "ownerModules": [
      {"id": "scanlog", "description": "..."},
      {"id": "config", "description": "..."},
      {"id": "version_registry", "description": "..."},
      {"id": "aux", "description": "Auxiliary surfaces with deferred runtime verification"}
    ]
    ```
    Add these 16 new entries (use this exact text):
    ```json
    {"id": "yaml", "description": "classic_yaml binding (classic-yaml-py wrapping classic-yaml-core)"},
    {"id": "database", "description": "classic_database binding (classic-database-py wrapping classic-database-core)"},
    {"id": "file_io", "description": "classic_file_io binding (classic-file-io-py wrapping classic-file-io-core)"},
    {"id": "scangame", "description": "classic_scangame binding (classic-scangame-py wrapping classic-scangame-core)"},
    {"id": "registry", "description": "classic_registry binding (classic-registry-py wrapping classic-registry-core)"},
    {"id": "perf", "description": "classic_perf binding (classic-perf-py wrapping classic-perf-core)"},
    {"id": "settings", "description": "classic_settings binding (classic-settings-py wrapping classic-settings-core)"},
    {"id": "message", "description": "classic_message binding (classic-message-py wrapping classic-message-core)"},
    {"id": "path", "description": "classic_path binding (classic-path-py wrapping classic-path-core)"},
    {"id": "constants", "description": "classic_constants binding (classic-constants-py wrapping classic-constants-core)"},
    {"id": "version", "description": "classic_version binding (classic-version-py wrapping classic-version-core)"},
    {"id": "resource", "description": "classic_resource binding (classic-resource-py wrapping classic-resource-core)"},
    {"id": "xse", "description": "classic_xse binding (classic-xse-py wrapping classic-xse-core)"},
    {"id": "web", "description": "classic_web binding (classic-web-py wrapping classic-web-core)"},
    {"id": "update", "description": "classic_update binding (classic-update-py wrapping classic-update-core)"},
    {"id": "shared", "description": "classic_shared foundation binding (classic-shared-py under foundation/)"}
    ```
    (Adapt the JSON shape if `ownerModules` is an object rather than an array.)

    Step 2: Run the baseline generator to refresh all 9 artifacts in lockstep (D-03 cadence):
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    ```
    This regenerates `parity_contract.json` (ID hashes recomputed), `parity_contract.md`, `rust_api_surface.json`, `python_api_surface.json`, `parity_diff_report.json`, `parity_diff_report.md`, `runtime_coverage_summary.json`, `runtime_coverage_summary.md`, and `tier1_gate_report.md`.

    Step 3: Run the gate to verify it still exits 0 with the existing 59 Tier-1 rows AND the new Pitfall 2 guard:
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline"
    ```
    Expected: exit code 0, output contains "Tier-1 parity gate passed."

    Step 4: Capture the A10 sizing report. After the gate run, read `docs/implementation/python_api_parity/baseline/parity_diff_report.json` and extract `gap_counts_by_owner_tier` (or equivalent). Use this PowerShell snippet:
    ```powershell
    $diff = Get-Content 'docs/implementation/python_api_parity/baseline/parity_diff_report.json' -Raw | ConvertFrom-Json
    Write-Host "tier2_gap_total per owner (newly-surfaced symbols from 16 untracked crates):"
    foreach ($owner in $diff.gap_counts_by_owner_tier.PSObject.Properties.Name | Sort-Object) {
        $tier2 = $diff.gap_counts_by_owner_tier.$owner.tier2
        if ($tier2 -gt 0) { Write-Host "  $owner : $tier2 newly-surfaced rows" }
    }
    Write-Host "Total tier2_gap_total: $($diff.summary.tier2_gap_total)"
    ```
    Capture the output and include it in the plan SUMMARY for downstream Plans 6/7/8 to size their task budgets.

    Step 5: Run the new tooling tests — they should all pass now (TDD GREEN):
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest tools/python_api_parity/tests -v
    ```
    Expected: 11 passing + 1 xfail (the `test_tier2_definition_removed_after_plan_9` is expected to xfail until Plan 9).
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root . ; if ($LASTEXITCODE -ne 0) { exit 1 }; python -m pytest tools/python_api_parity/tests -q"</automated>
  </verify>
  <acceptance_criteria>
    - `docs/implementation/python_api_parity/baseline/parity_contract.json` contains 20 ownerModules entries (4 original + 16 new)
    - `docs/implementation/python_api_parity/baseline/rust_api_surface.json` `scope.target_crates` has length 19
    - `docs/implementation/python_api_parity/baseline/python_api_surface.json` reflects the 19 Python modules
    - `python tools/python_api_parity/check_parity_gate.py --repo-root .` exits 0 (existing 59 Tier-1 rows still pass with Pitfall 2 guard active)
    - `pytest tools/python_api_parity/tests -q` reports 11 passing, 1 xfailed
    - Plan SUMMARY includes a "tier2_gap_total per owner" report (the A10 sizing data) — this is captured in the SUMMARY artifact, not in code
    - All 9 baseline files in `docs/implementation/python_api_parity/baseline/` have refreshed `generated_at_utc` timestamps
  </acceptance_criteria>
  <done>Baseline refreshed via D-03 cadence; gate exits 0 with 59 Tier-1 rows + Pitfall 2 guard active; A10 sizing report captured in SUMMARY for downstream plan budgets.</done>
</task>

</tasks>

<verification>
After all 4 tasks land, run the 5-step verification chain:
1. `python tools/python_api_parity/check_parity_gate.py --repo-root .` — exit 0 (existing 59 rows still pass with Pitfall 2 guard)
2. `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings` — exit 0
3. `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python` (no module rebuild needed in Plan 1, but verify discovery works) — informational only
4. `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest tools/python_api_parity/tests ClassicLib-rs/python-bindings/tests -q` — exit 0
5. `mypy --strict` — no .pyi changes in Plan 1, skip
</verification>

<success_criteria>
- `RUST_TARGET_CRATES.length == 19`, `PYTHON_TARGET_MODULES.length == 19`, `'classic-shared-py' in RUST_TARGET_CRATES`, `'classic-crashgen-settings-core' not in RUST_TARGET_CRATES`
- `validate_contract_rust_symbols()` exists in `check_parity_gate.py`, called from `main()` before `generate_diff_report()`
- Existing 59 Tier-1 contract rows still pass the gate (no regression)
- All 4 Wave 0 test files exist; 11 tests pass + 1 xfail
- Baseline artifacts refreshed in lockstep (D-03 cadence)
- A10 sizing report captured in SUMMARY: per-owner `tier2_gap_total` counts from newly-surfaced symbols across the 16 untracked crates
- Atomic single commit per D-06: all 9 baseline files + 4 source/test files + plan SUMMARY in one commit
</success_criteria>

<output>
After completion, create `.planning/phases/03-python-tier-collapse/03-01-SUMMARY.md` containing:
- Files modified summary
- The A10 sizing table (tier2_gap_total per owner) — REQUIRED for downstream plans
- Confirmation that gate exits 0 with 59 Tier-1 rows + Pitfall 2 guard active
- Note any unexpected newly-surfaced symbols requiring follow-up plan budget adjustments
</output>
