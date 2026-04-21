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
  - tools/python_api_parity/tests/conftest.py
  - tools/python_api_parity/tests/test_generate_baseline_targets.py
  - tools/python_api_parity/tests/test_check_parity_gate.py
  - tools/python_api_parity/tests/test_pitfall2_guard.py
  - tools/python_api_parity/tests/test_owner_render_drift.py
  - docs/implementation/python_api_parity/baseline/parity_contract.json
  - docs/implementation/python_api_parity/baseline/parity_contract.md
  - docs/implementation/python_api_parity/baseline/parity_diff_report.json
  - docs/implementation/python_api_parity/baseline/parity_diff_report.md
  - docs/implementation/python_api_parity/baseline/rust_api_surface.json
  - docs/implementation/python_api_parity/baseline/python_api_surface.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
  - docs/implementation/python_api_parity/baseline/tier1_gate_report.md
  - .planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md
autonomous: true
requirements: [PYT-01, PYT-03]
must_haves:
  truths:
    - "RUST_TARGET_CRATES contains exactly 19 entries (18 -core business-logic crates + 1 foundation classic-shared-py); classic-crashgen-settings-core is excluded"
    - "PYTHON_TARGET_MODULES contains exactly 19 entries mirroring the Rust crate list"
    - "Pitfall 2 guard fires non-zero on a synthetic missing-rustSymbol contract row with the canonical diagnostic text"
    - "Existing 59 Tier-1 contract rows still pass the gate after adding the guard (gate exits 0 on the unchanged contract)"
    - "Pre-Phase Pitfall 4 audit (Task 0) confirms every #[pyclass] in every -py crate has a matching m.add_class::<>()?; in its #[pymodule] function, OR the audit produces an actionable blocker list that is fixed before Tasks 1-4 proceed"
    - "Test files use a central conftest.py for sys.path bootstrap (no per-file sys.path.insert calls) — test collection is hermetic and does not pollute global sys.path"
    - "test_tier1_contract_total_baseline_floor asserts == 59 exactly for the Plan 01 snapshot (per-plan progression tests enforce downstream increments)"
    - "test_tier2_definition_removed_after_plan_9 uses strict=True on xfail so a premature tier2 removal is detected as a passing xfail failure"
    - "Owner-rendering drift guard test exists: render_diff_markdown() iterates a single-source-of-truth _OWNER_RENDER_ORDER derived from RUST_OWNER_BY_CRATE keys (not a hard-coded tuple)"
    - "Sizing report (tier2_gap_total per owner) for newly-surfaced symbols from the 16 currently-untracked crates is captured in the plan SUMMARY for downstream Plans 6/7/8 budgets"
  artifacts:
    - path: ".planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md"
      provides: "Pre-phase Pitfall 4 audit report: every #[pyclass] -> m.add_class::<>() registration enumerated with PASS/FAIL markers per -py crate"
    - path: "tools/python_api_parity/tests/conftest.py"
      provides: "Central sys.path bootstrap for tooling tests; replaces per-file sys.path.insert calls"
    - path: "tools/python_api_parity/generate_baseline.py"
      provides: "Expanded RUST_TARGET_CRATES (19 entries), PYTHON_TARGET_MODULES (19 entries), RUST_OWNER_BY_CRATE (19 entries), PYTHON_OWNER_BY_MODULE (19 entries), SQUAD_BY_OWNER (covering 17 new owner labels + aux); module-level _OWNER_RENDER_ORDER constant derived from RUST_OWNER_BY_CRATE keys; render_diff_markdown() iterates _OWNER_RENDER_ORDER, not a hard-coded tuple"
      contains: "classic-shared-py.*foundation/classic-shared-py/src/lib.rs"
    - path: "tools/python_api_parity/check_parity_gate.py"
      provides: "validate_contract_rust_symbols() Pitfall 2 guard helper called from main() before generate_diff_report()"
      contains: "def validate_contract_rust_symbols"
    - path: "tools/python_api_parity/tests/test_generate_baseline_targets.py"
      provides: "PYT-01 unit guard: every RUST_TARGET_CRATES entry parses to a non-empty symbol list"
    - path: "tools/python_api_parity/tests/test_check_parity_gate.py"
      provides: "PYT-03 snapshot guard: tier1_contract_total invariant test for Plan 9 cleanup; strict=True xfail on tier2 removal assertion"
    - path: "tools/python_api_parity/tests/test_pitfall2_guard.py"
      provides: "D-05 unit test for validate_contract_rust_symbols() with synthetic contract"
    - path: "tools/python_api_parity/tests/test_owner_render_drift.py"
      provides: "Drift guard: asserts _OWNER_RENDER_ORDER is derived from RUST_OWNER_BY_CRATE.values() (no divergence allowed)"
    - path: "docs/implementation/python_api_parity/baseline/parity_contract.json"
      provides: "Refreshed baseline (still 59 Tier-1 rows; ownerModules dict extended to 20 entries: scanlog, config, version_registry, aux, yaml, database, file_io, scangame, registry, perf, settings, message, path, constants, version, resource, xse, web, update, shared)"
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
    - from: "tools/python_api_parity/generate_baseline.py::render_diff_markdown()"
      to: "_OWNER_RENDER_ORDER (module-level constant)"
      via: "for owner in _OWNER_RENDER_ORDER loop"
      pattern: "_OWNER_RENDER_ORDER"
---

<objective>
Expand the Python parity tooling to enumerate all 19 binding pairs (18 business-logic `-core` crates + 1 foundation `classic-shared-py`) and add the mechanical Pitfall 2 guard assertion to `check_parity_gate.py`. This is the keystone plan: every downstream Phase 3 plan depends on the expanded `RUST_TARGET_CRATES` / `PYTHON_TARGET_MODULES` to discover symbols and gate them. Without this plan landing first, none of the promotion plans can verify their work.

Purpose: Establish the gate enforcement scaffolding for Phase 3 promotions. Land the long-term Pitfall 2 invariant before any contract row is touched. ALSO: run a pre-phase Pitfall 4 audit (every `#[pyclass]` must have a matching `m.add_class::<>()?;` in its `#[pymodule]`) before any promotion plan proceeds.

Output:
- Pre-phase Pitfall 4 audit report at `.planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md`
- `tools/python_api_parity/tests/conftest.py` for central sys.path handling (replaces per-file sys.path.insert pollution)
- Expanded `tools/python_api_parity/generate_baseline.py` (5 dicts grow from 3 → 19/20 entries; `_OWNER_RENDER_ORDER` derived from `RUST_OWNER_BY_CRATE` keys)
- New `validate_contract_rust_symbols()` helper in `tools/python_api_parity/check_parity_gate.py` wired into `main()`
- 5 new Wave 0 test files under `tools/python_api_parity/tests/` (baseline targets, gate snapshots, Pitfall 2 guard, owner drift guard)
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

From docs/implementation/python_api_parity/baseline/parity_contract.json (VERIFIED — ownerModules is a dict, NOT an array; generate_baseline.py does NOT touch this key and it is hand-maintained):
```json
"ownerModules": {
  "scanlog": { "description": "..." },
  "config": { "description": "..." },
  "version_registry": { "description": "..." },
  "aux": { "description": "..." }
}
```
Note: --write-baseline does NOT regenerate `ownerModules`. Hand-edit is safe; re-read the file post-refresh to confirm entries remain.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 0: Pre-Phase Pitfall 4 audit — verify every #[pyclass] has matching m.add_class::<>()?;</name>
  <files>
    .planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md
  </files>
  <read_first>
    - Every ClassicLib-rs/python-bindings/*-py/src/lib.rs file (find the #[pymodule] fn and enumerate m.add_class::<>() calls)
    - Every ClassicLib-rs/python-bindings/*-py/src/**/*.rs file (find #[pyclass] declarations)
    - ClassicLib-rs/foundation/classic-shared-py/src/lib.rs (also in scope)
  </read_first>
  <action>
    Pre-Phase audit: every `#[pyclass]` in every `-py` crate MUST have a matching `m.add_class::<TypeName>()?;` in its `#[pymodule]` function. If any class is declared but not registered, every downstream Phase 3 smoke test for that class will fail with `AttributeError`, producing misleading Pitfall 4 symptoms. Fix now, before promotion work.

    Step 1: Enumerate every `#[pyclass]` declaration with PowerShell:
    ```powershell
    $results = @()
    $pyCrates = Get-ChildItem -Path ClassicLib-rs/python-bindings -Directory -Filter "classic-*-py"
    $pyCrates += Get-Item ClassicLib-rs/foundation/classic-shared-py
    foreach ($crate in $pyCrates) {
        $crateName = $crate.Name
        $srcDir = Join-Path $crate.FullName "src"
        if (-not (Test-Path $srcDir)) { continue }

        # Find all #[pyclass] declarations
        $pyclasses = Select-String -Path (Join-Path $srcDir "*.rs") -Pattern '#\[pyclass' -Recurse
        $classNames = @()
        foreach ($match in $pyclasses) {
            # Parse the struct/enum name on the next non-attribute line
            $file = $match.Path
            $lineNum = $match.LineNumber
            $allLines = Get-Content $file
            for ($i = $lineNum; $i -lt [Math]::Min($lineNum + 5, $allLines.Count); $i++) {
                if ($allLines[$i] -match '^\s*(?:pub\s+)?(?:struct|enum)\s+(\w+)') {
                    $classNames += @{ File = $file; Line = $lineNum; Name = $Matches[1] }
                    break
                }
            }
        }

        # Find m.add_class<>() calls in lib.rs
        $libRs = Join-Path $srcDir "lib.rs"
        $addClassCalls = @()
        if (Test-Path $libRs) {
            $addClassMatches = Select-String -Path $libRs -Pattern 'm\.add_class::<(\w+)>'
            $addClassCalls = $addClassMatches | ForEach-Object { $_.Matches.Groups[1].Value }
        }

        # Compute diff
        foreach ($cls in $classNames) {
            $registered = $addClassCalls -contains $cls.Name
            $results += [PSCustomObject]@{
                Crate = $crateName
                File = (Split-Path $cls.File -Leaf)
                Line = $cls.Line
                PyClass = $cls.Name
                Registered = $registered
            }
        }
    }

    # Emit audit report markdown
    $missing = $results | Where-Object { -not $_.Registered }
    $report = @()
    $report += "# Phase 3 Plan 01 — Pitfall 4 Audit Report"
    $report += ""
    $report += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    $report += ""
    if ($missing.Count -eq 0) {
        $report += "## STATUS: PASS"
        $report += ""
        $report += "All $($results.Count) #[pyclass] declarations across $(($results.Crate | Select-Object -Unique).Count) -py crates have matching m.add_class::<>() registrations in their #[pymodule] function."
    } else {
        $report += "## STATUS: FAIL"
        $report += ""
        $report += "The following #[pyclass] declarations are NOT registered via m.add_class::<>()?; — Phase 3 smoke tests WILL fail with AttributeError for these classes until fixed:"
        $report += ""
        $report += "| Crate | File | Line | #[pyclass] |"
        $report += "|-------|------|------|------------|"
        foreach ($m in $missing) {
            $report += "| $($m.Crate) | $($m.File) | $($m.Line) | $($m.PyClass) |"
        }
        $report += ""
        $report += "### Remediation"
        $report += ""
        $report += "For each missing registration: add `m.add_class::<PyClassName>()?;` to the `#[pymodule]` function in the crate's `src/lib.rs`. Commit the fix BEFORE proceeding to Task 1."
    }
    $report += ""
    $report += "## Full Audit Table"
    $report += ""
    $report += "| Crate | File | Line | #[pyclass] | Registered |"
    $report += "|-------|------|------|------------|:----------:|"
    foreach ($r in $results | Sort-Object Crate, File, Line) {
        $flag = if ($r.Registered) { "PASS" } else { "FAIL" }
        $report += "| $($r.Crate) | $($r.File) | $($r.Line) | $($r.PyClass) | $flag |"
    }
    $report | Set-Content .planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md
    Write-Host "Audit complete: $($results.Count) classes audited, $($missing.Count) missing registrations"
    if ($missing.Count -gt 0) { exit 1 }
    ```

    Step 2: Write the audit output to `.planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md`.

    Step 3: If the audit shows FAIL, STOP Plan 01 and fix the missing registrations. The fixes land as part of Plan 01 (same atomic commit as Tasks 1-4) — they are a prerequisite, not a separate plan. For each missing registration, add `m.add_class::<PyXxx>()?;` to the appropriate `#[pymodule]` function. Re-run Step 1; the second audit MUST show PASS before Task 1 begins.

    Step 4: If PASS, commit the audit file and proceed to Task 1.

    NOTE: If the audit finds a structural issue (e.g., a `#[pyclass]` that legitimately should NOT be exported because it's an internal helper), document the exclusion inline in the audit report under a "Known Exclusions" heading with a rationale.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "if (-not (Test-Path '.planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md')) { Write-Error 'Audit file missing'; exit 1 }; $content = Get-Content '.planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md' -Raw; if ($content -match 'STATUS: FAIL' -and $content -notmatch 'Known Exclusions') { Write-Error 'Audit FAIL — fix missing m.add_class::<>() registrations before proceeding'; exit 1 }; Write-Host 'Pitfall 4 audit PASS'"</automated>
  </verify>
  <acceptance_criteria>
    - File `.planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md` exists
    - File contains either "STATUS: PASS" OR (a FAIL with explicit "Known Exclusions" section documenting each intentional exclusion)
    - Every `#[pyclass]` across all `*-py/src/**/*.rs` files has a documented registration status
    - If audit was FAIL initially, missing registrations are fixed in source files before Task 1 starts (re-run audit MUST show PASS)
  </acceptance_criteria>
  <done>Pre-phase Pitfall 4 audit report committed; all #[pyclass] registrations verified or remediated.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 1: Wave 0 — Create tooling test scaffolding with central conftest.py (PYT-01, PYT-03, D-05 unit guards)</name>
  <files>
    tools/python_api_parity/tests/__init__.py
    tools/python_api_parity/tests/conftest.py
    tools/python_api_parity/tests/test_generate_baseline_targets.py
    tools/python_api_parity/tests/test_check_parity_gate.py
    tools/python_api_parity/tests/test_pitfall2_guard.py
    tools/python_api_parity/tests/test_owner_render_drift.py
  </files>
  <read_first>
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md (full file)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Validation Architecture" + §"Wave 0 Gaps" (lines 83-128) + §"Question 4" (lines 466-545)
    - .planning/phases/03-python-tier-collapse/03-VALIDATION.md §"Wave 0 Requirements"
    - tools/python_api_parity/generate_baseline.py (full file — understand parse_rust_surface signature, owner_module names, return shape of `entries`)
    - tools/python_api_parity/check_parity_gate.py (full file — understand main() flow, sys.path append, where guard call lands)
  </read_first>
  <behavior>
    R6 change: Use a central `conftest.py` for sys.path handling. Individual test files do NOT contain `sys.path.insert(...)` calls. `conftest.py` handles the path bootstrap once; test files use `from generate_baseline import ...` and `from check_parity_gate import ...` directly.

    Test 1 (test_generate_baseline_targets.py — `test_every_rust_target_parses_to_nonempty_symbols`):
      - Imports `RUST_TARGET_CRATES`, `parse_rust_surface` from `generate_baseline` (via conftest.py sys.path bootstrap)
      - Iterates every (crate_name, rel_path) entry; for each calls `parse_rust_surface(repo_root, set())` and asserts the returned manifest has at least one entry whose `crate == crate_name`
      - Asserts `len(RUST_TARGET_CRATES) == 19`
      - Asserts `'classic-shared-py' in RUST_TARGET_CRATES`
      - Asserts `'classic-crashgen-settings-core' not in RUST_TARGET_CRATES` (per A5)
    Test 2 (test_generate_baseline_targets.py — `test_every_python_target_pyi_file_exists`):
      - Asserts every `.pyi` path in `PYTHON_TARGET_MODULES.values()` resolves to an existing file under repo_root
      - Asserts `len(PYTHON_TARGET_MODULES) == 19`
      - Asserts `'classic_shared' in PYTHON_TARGET_MODULES` and the path equals `'ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi'`
    Test 3 (test_generate_baseline_targets.py — `test_owner_dicts_are_consistent`):
      - Asserts `set(RUST_OWNER_BY_CRATE.keys()) == set(RUST_TARGET_CRATES.keys())`
      - Asserts `set(PYTHON_OWNER_BY_MODULE.keys()) == set(PYTHON_TARGET_MODULES.keys())`
      - Asserts every owner value in both owner dicts is a key in `SQUAD_BY_OWNER`
      - Asserts `'aux' in SQUAD_BY_OWNER` (file_io aux entry needs a squad label)
    Test 4 (test_check_parity_gate.py — `test_tier1_contract_total_baseline_floor`):
      - Loads `docs/implementation/python_api_parity/baseline/parity_contract.json`
      - Asserts `len(contract['tier1Mappings']) == 59` (EXACT count per R7 — Plan 01 only refreshes baseline, does not add rows; Plans 02-08 bump this per progression).
    Test 5 (test_check_parity_gate.py — `test_tier2_definition_removed_after_plan_9` with strict=True xfail per R7):
      - `@pytest.mark.xfail(strict=True, reason='tier2 definition removal lands in Plan 9 (PYT-03); asserts the eventual invariant')`
      - Asserts `'tier2' not in contract['tierDefinitions']`
      - With strict=True, this test MUST continue to xfail until Plan 9 lands the deletion; if tier2 is removed prematurely by Plans 02-08, the xfail becomes a passing failure (strict catches it).
    Test 6 (test_pitfall2_guard.py — `test_validate_contract_rust_symbols_passes_when_all_present`):
      - Constructs a synthetic `contract = {'tier1Mappings': [{'id': 'test.foo', 'rustSymbol': 'FooStruct', 'rustCrate': 'classic-test-core'}]}`
      - Constructs a synthetic `rust_manifest = {'symbols': [{'symbol': 'FooStruct'}]}`
      - Asserts `validate_contract_rust_symbols(contract, rust_manifest) == []`
    Test 7 (test_pitfall2_guard.py — `test_validate_contract_rust_symbols_fails_when_symbol_missing`):
      - Constructs `contract = {'tier1Mappings': [{'id': 'test.foo', 'rustSymbol': 'MissingStruct', 'rustCrate': 'classic-test-core'}]}`
      - Constructs `rust_manifest = {'symbols': [{'symbol': 'OtherStruct'}]}`
      - Calls `diagnostics = validate_contract_rust_symbols(contract, rust_manifest)`
      - Asserts `len(diagnostics) == 1`
      - Asserts `"Pitfall 2" in diagnostics[0]`
      - Asserts `"test.foo" in diagnostics[0]`
      - Asserts `"MissingStruct" in diagnostics[0]`
      - Asserts `"classic-test-core" in diagnostics[0]`
    Test 8 (test_pitfall2_guard.py — `test_validate_contract_rust_symbols_fails_when_rustSymbol_missing_from_row`):
      - Constructs `contract = {'tier1Mappings': [{'id': 'test.foo', 'rustCrate': 'classic-test-core'}]}` (no rustSymbol field)
      - Constructs `rust_manifest = {'symbols': []}`
      - Asserts `len(validate_contract_rust_symbols(contract, rust_manifest)) == 1`
      - Asserts `"missing 'rustSymbol'" in diagnostics[0]`
    Test 9 (test_owner_render_drift.py — `test_owner_render_order_matches_rust_owner_by_crate`):
      - Imports `_OWNER_RENDER_ORDER`, `RUST_OWNER_BY_CRATE` from generate_baseline
      - Asserts `set(_OWNER_RENDER_ORDER) == set(RUST_OWNER_BY_CRATE.values()) | {"aux"}` (single source of truth — owners derived from RUST_OWNER_BY_CRATE plus the aux label)
      - Asserts the rendering function iterates this constant (grep the source file for `for owner in _OWNER_RENDER_ORDER:`)
  </behavior>
  <action>
    Create the 6 test files. Use `from __future__ import annotations` at the top of each `*.py` file. The `__init__.py` is empty.

    For `conftest.py` (R6 — centralizes sys.path handling; individual test files do NOT use sys.path.insert):
    ```python
    """Central pytest fixture/conftest for tools/python_api_parity/tests.

    Sets sys.path once so test files can use clean imports:
        from generate_baseline import RUST_TARGET_CRATES
        from check_parity_gate import validate_contract_rust_symbols

    This replaces per-file sys.path.insert pollution that would conflict
    with package-style imports elsewhere in the repo.
    """
    from __future__ import annotations

    import sys
    from pathlib import Path

    REPO_ROOT = Path(__file__).resolve().parents[3]
    TOOLS_DIR = REPO_ROOT / "tools" / "python_api_parity"

    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    ```

    For `test_generate_baseline_targets.py`:
    ```python
    """PYT-01 unit guard: every RUST_TARGET_CRATES / PYTHON_TARGET_MODULES entry parses cleanly."""
    from __future__ import annotations

    from pathlib import Path

    # sys.path bootstrap handled by conftest.py
    from generate_baseline import (  # noqa: E402
        PYTHON_OWNER_BY_MODULE,
        PYTHON_TARGET_MODULES,
        RUST_OWNER_BY_CRATE,
        RUST_TARGET_CRATES,
        SQUAD_BY_OWNER,
        parse_rust_surface,
    )

    REPO_ROOT = Path(__file__).resolve().parents[3]


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

    For `test_check_parity_gate.py` (R7: exact 59 floor, strict=True xfail):
    ```python
    """PYT-03 snapshot guard: tier1_contract_total invariant for Plan 9 cleanup."""
    from __future__ import annotations

    import json
    from pathlib import Path

    import pytest

    REPO_ROOT = Path(__file__).resolve().parents[3]
    CONTRACT_PATH = REPO_ROOT / "docs" / "implementation" / "python_api_parity" / "baseline" / "parity_contract.json"


    def test_tier1_contract_total_baseline_floor() -> None:
        """Plan 1 baseline: exactly 59 Tier-1 rows.

        Plan 01 only refreshes the baseline; it does NOT add rows. Subsequent
        plans bump this number per per-plan progression:
          - Plan 02: 59 -> 133 (+74 scanlog Wave 1)
          - Plan 03: 133 -> 190 (+57 scanlog Wave 2, per R9 GLOBAL_FCX_HANDLER exclusion)
          - Plan 04: 190 -> 240 (+50 scanlog Wave 3a)
          - Plan 05: 240 -> 286 (+46 scanlog Wave 3b report)
          - Plan 06: 286 -> 312 (+26 config)
          - Plan 07: 312 -> 347 (+35 version_registry)
          - Plan 08: 347 -> 358 (+11 classic_shared + file_io initial; Plan 08 also claims any residual classic_file_io rows found post-refresh)
          - Plan 09a: 358 -> 358 + residual A10 count
        The exact equality below is the Plan 01 snapshot; later plans supersede
        it with their own snapshot assertions.
        """
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        assert len(contract["tier1Mappings"]) == 59, (
            f"Plan 01 baseline expects exactly 59 Tier-1 rows, got {len(contract['tier1Mappings'])}"
        )


    @pytest.mark.xfail(
        strict=True,
        reason="tier2 definition removal lands in Plan 9b (PYT-03); this test asserts the eventual invariant. strict=True catches premature deletion by Plans 02-08 as a passing xfail failure.",
    )
    def test_tier2_definition_removed_after_plan_9() -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        tier_definitions = contract.get("tierDefinitions", {})
        assert "tier2" not in tier_definitions, (
            "Plan 9b must delete tierDefinitions.tier2 from parity_contract.json"
        )
    ```

    For `test_pitfall2_guard.py`:
    ```python
    """D-05 unit test for validate_contract_rust_symbols (Pitfall 2 guard)."""
    from __future__ import annotations

    # sys.path bootstrap handled by conftest.py
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

    For `test_owner_render_drift.py` (LOW — drift guard for rendering order):
    ```python
    """LOW drift guard: _OWNER_RENDER_ORDER must derive from RUST_OWNER_BY_CRATE + aux, not a hard-coded tuple."""
    from __future__ import annotations

    # sys.path bootstrap handled by conftest.py
    from generate_baseline import (  # noqa: E402
        RUST_OWNER_BY_CRATE,
        _OWNER_RENDER_ORDER,
    )


    def test_owner_render_order_matches_rust_owner_by_crate_values() -> None:
        """The rendering order must be a superset of owners derived from RUST_OWNER_BY_CRATE.

        Hard-coding the tuple (as at line 682 originally) invites drift when
        RUST_OWNER_BY_CRATE grows. This test enforces: every key in
        RUST_OWNER_BY_CRATE.values() must appear in _OWNER_RENDER_ORDER, plus
        the special 'aux' label for the file_io aux entry.
        """
        expected_owners = set(RUST_OWNER_BY_CRATE.values()) | {"aux"}
        actual_owners = set(_OWNER_RENDER_ORDER)
        missing = expected_owners - actual_owners
        extra = actual_owners - expected_owners
        assert not missing, f"_OWNER_RENDER_ORDER is missing owners: {missing}"
        # Extras are allowed if intentional, but flag them for review:
        assert not extra, (
            f"_OWNER_RENDER_ORDER has extra owners not in RUST_OWNER_BY_CRATE: {extra}"
        )
    ```

    NOTE: tests will FAIL until Tasks 2 + 3 land — this is intentional TDD RED. Commit the failing tests in this task; Task 4 turns them GREEN.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest tools/python_api_parity/tests -q --no-header --collect-only 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - File `tools/python_api_parity/tests/__init__.py` exists (empty)
    - File `tools/python_api_parity/tests/conftest.py` exists with central sys.path bootstrap
    - File `tools/python_api_parity/tests/test_generate_baseline_targets.py` exists with 9 test functions and NO `sys.path.insert(...)` calls
    - File `tools/python_api_parity/tests/test_check_parity_gate.py` exists with `== 59` assertion and `strict=True` xfail marker
    - File `tools/python_api_parity/tests/test_pitfall2_guard.py` exists with 3 test functions and NO `sys.path.insert(...)` calls
    - File `tools/python_api_parity/tests/test_owner_render_drift.py` exists with the drift guard test
    - `pytest --collect-only` returns 14 test items without collection errors (imports work because conftest.py bootstraps sys.path)
    - Tests fail with assertion failures (TDD RED state — Tasks 2-4 fix)
  </acceptance_criteria>
  <done>The 6 Wave 0 test files exist on disk; pytest can collect them via conftest.py bootstrap; failures match the TDD RED state expected before Tasks 2-4 land the implementation.</done>
</task>

<task type="auto">
  <name>Task 2: Expand RUST_TARGET_CRATES, PYTHON_TARGET_MODULES, and owner/squad dicts in generate_baseline.py; introduce _OWNER_RENDER_ORDER derived from RUST_OWNER_BY_CRATE</name>
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
</automated>
  </verify>
  <acceptance_criteria>
    - `tools/python_api_parity/generate_baseline.py` lines 24-52 contain the 19-entry expansion
    - `RUST_TARGET_CRATES` has 19 entries with `'classic-shared-py'` mapping to `'ClassicLib-rs/foundation/classic-shared-py/src/lib.rs'`
    - `RUST_TARGET_CRATES` does NOT contain `'classic-crashgen-settings-core'`
    - `PYTHON_TARGET_MODULES` has 19 entries with `'classic_shared'` mapping to `'ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi'`
    - `SQUAD_BY_OWNER` contains the `'aux'` key
    - `_OWNER_RENDER_ORDER` constant exists at module level, derived from RUST_OWNER_BY_CRATE + 'aux' label
    - `render_diff_markdown()` iterates `_OWNER_RENDER_ORDER`, NOT a hard-coded tuple
  </acceptance_criteria>
  <done>Module-level dicts grown to 19 entries each; sorted owner render order constant derived from RUST_OWNER_BY_CRATE; smoke import succeeds; drift guard test passes.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Add validate_contract_rust_symbols() Pitfall 2 guard to check_parity_gate.py</name>
  <files>
    tools/python_api_parity/check_parity_gate.py
  </files>
  <read_first>
    - tools/python_api_parity/check_parity_gate.py (full file)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md Question 4 (lines 466-545)
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md D-05 + Research Amendment A3
    - tools/python_api_parity/tests/test_pitfall2_guard.py (the test file from Task 1)
  </read_first>
  <behavior>
    The Task 1 test cases define the contract. Function signature:
    ```python
    def validate_contract_rust_symbols(
        contract: dict[str, Any],
        rust_manifest: dict[str, Any],
    ) -> list[str]:
    ```
    Pure function (no I/O); returns empty list on success; populated list with error strings on failure.
  </behavior>
  <action>
    Add the helper function and wire it into `main()`. Place the function between the existing imports (around line 28-29) and `render_tier1_gate_markdown()` at line 31.

    Insert this function (paste verbatim from RESEARCH.md Question 4):

    ```python
    def validate_contract_rust_symbols(
        contract: dict[str, Any],
        rust_manifest: dict[str, Any],
    ) -> list[str]:
        """Pitfall 2 guard: every Tier-1 contract row's rustSymbol must appear
        in the parsed Rust surface.

        Returns a list of human-readable diagnostic strings; empty list means
        success. Failing fast here keeps downstream tier1_missing_rust noise
        out of the diff report when the root cause is a missing pub use at
        the -core/lib.rs surface (per Phase 3 D-05; see RESEARCH A1).
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

    Then wire it into `main()`. After `rust_manifest = parse_rust_surface(...)` and before `diff_report = generate_diff_report(...)`, insert:

    ```python
        # Pitfall 2 guard (Phase 3 D-05) — fail FAST before downstream diff generation.
        pitfall2_diagnostics = validate_contract_rust_symbols(contract, rust_manifest)
        if pitfall2_diagnostics:
            print("\n".join(pitfall2_diagnostics), file=sys.stderr)
            return 1
    ```

    Also ensure `import sys` and `from typing import Any` are present at the top of the file.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest tools/python_api_parity/tests/test_pitfall2_guard.py -v 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `tools/python_api_parity/check_parity_gate.py` contains `def validate_contract_rust_symbols(`
    - The call site is BEFORE `generate_diff_report(...)` in `main()`
    - All 3 tests in `test_pitfall2_guard.py` pass (TDD GREEN)
    - `python -m pytest tools/python_api_parity/tests/test_pitfall2_guard.py -v` exits 0
  </acceptance_criteria>
  <done>Pitfall 2 guard helper exists, is wired into main() before diff generation, and all test_pitfall2_guard.py tests pass.</done>
</task>

<task type="auto">
  <name>Task 4: Update parity_contract.json::ownerModules dict, refresh baseline, capture A10 sizing report</name>
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
    - docs/implementation/python_api_parity/baseline/parity_contract.json (full file)
    - tools/python_api_parity/generate_baseline.py (post-Task-2 — run `grep -n 'ownerModules' tools/python_api_parity/generate_baseline.py`; expected ZERO matches confirming the key is hand-maintained and --write-baseline does NOT regenerate it)
    - tools/python_api_parity/check_parity_gate.py (post-Task-3)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md Question 3 and Open Questions item 2
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md Research Amendment A10
  </read_first>
  <action>
    R6 Pre-step: Verify ownerModules handling BEFORE editing. Run:
    ```powershell
    Select-String -Path tools/python_api_parity/generate_baseline.py -Pattern 'ownerModules'
    ```
    Expected: ZERO matches (the key is hand-maintained in parity_contract.json, NOT regenerated by --write-baseline). If any matches exist, the hand-edit below MAY be overwritten — in that case, the executor must add the expansion to generate_parity_contract() in the Python source instead of hand-editing the JSON. The current code does NOT emit ownerModules, so Step 1 below is safe.

    Step 1: Edit parity_contract.json. The ownerModules key is a DICT (verified live: see line 9 of parity_contract.json). Current shape:
    ```json
    "ownerModules": {
      "scanlog": { "description": "Crash log orchestration, parsing, and analysis APIs." },
      "config": { "description": "YAML data and runtime configuration APIs." },
      "version_registry": { "description": "Game version lookup and compatibility APIs." },
      "aux": { "description": "Auxiliary modules outside core phase-1 workflow APIs." }
    }
    ```
    Add 16 new dict entries (preserve the existing 4):
    ```json
    "yaml": { "description": "classic_yaml binding (classic-yaml-py wrapping classic-yaml-core)" },
    "database": { "description": "classic_database binding (classic-database-py wrapping classic-database-core)" },
    "file_io": { "description": "classic_file_io binding (classic-file-io-py wrapping classic-file-io-core)" },
    "scangame": { "description": "classic_scangame binding (classic-scangame-py wrapping classic-scangame-core)" },
    "registry": { "description": "classic_registry binding (classic-registry-py wrapping classic-registry-core)" },
    "perf": { "description": "classic_perf binding (classic-perf-py wrapping classic-perf-core)" },
    "settings": { "description": "classic_settings binding (classic-settings-py wrapping classic-settings-core)" },
    "message": { "description": "classic_message binding (classic-message-py wrapping classic-message-core)" },
    "path": { "description": "classic_path binding (classic-path-py wrapping classic-path-core)" },
    "constants": { "description": "classic_constants binding (classic-constants-py wrapping classic-constants-core)" },
    "version": { "description": "classic_version binding (classic-version-py wrapping classic-version-core)" },
    "resource": { "description": "classic_resource binding (classic-resource-py wrapping classic-resource-core)" },
    "xse": { "description": "classic_xse binding (classic-xse-py wrapping classic-xse-core)" },
    "web": { "description": "classic_web binding (classic-web-py wrapping classic-web-core)" },
    "update": { "description": "classic_update binding (classic-update-py wrapping classic-update-core)" },
    "shared": { "description": "classic_shared foundation binding (classic-shared-py under foundation/)" }
    ```
    Final ownerModules has 20 entries.

    Step 2: Refresh baseline (D-03 cadence):
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    ```
    IMPORTANT: After this runs, re-read parity_contract.json and verify the 20 ownerModules entries are still present. If they were erased, the pre-step verification was incorrect — revert and add the expansion to the Python source instead.

    Step 3: Run the gate to verify exit 0:
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline"
    ```

    Step 4: Capture A10 sizing report as machine-readable JSON (not PowerShell inline):
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import json, pathlib; diff = json.loads(pathlib.Path('docs/implementation/python_api_parity/baseline/parity_diff_report.json').read_text(encoding='utf-8')); per_owner = diff.get('gap_counts_by_owner_tier', {}); sizing = {o: c.get('tier2', 0) for o, c in per_owner.items() if c.get('tier2', 0) > 0}; out = {'per_owner_tier2_gap_total': sizing, 'total_tier2_gap_total': sum(sizing.values())}; pathlib.Path('.planning/phases/03-python-tier-collapse/03-01-A10-sizing.json').write_text(json.dumps(out, indent=2), encoding='utf-8'); print(json.dumps(out, indent=2))"
    ```

    Step 5: Run new tooling tests (TDD GREEN):
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest tools/python_api_parity/tests -v
    ```
    Expected: 13 passing + 1 strict=True xfail.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root . ; if ($LASTEXITCODE -ne 0) { exit 1 }; python -m pytest tools/python_api_parity/tests -q"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json` contains 20 ownerModules dict entries (4 original + 16 new) AFTER `--write-baseline` runs
    - `rust_api_surface.json` `scope.target_crates` has length 19
    - `check_parity_gate.py --repo-root .` exits 0 (59 Tier-1 rows still pass with Pitfall 2 guard active)
    - `pytest tools/python_api_parity/tests -q` reports 13 passing, 1 strict=True xfail
    - `.planning/phases/03-python-tier-collapse/03-01-A10-sizing.json` exists with machine-readable per-owner sizing data
    - All 9 baseline files have refreshed timestamps
  </acceptance_criteria>
  <done>Baseline refreshed via D-03 cadence; gate exits 0 with 59 Tier-1 rows + Pitfall 2 guard active; A10 sizing report captured in machine-readable form + SUMMARY.</done>
</task>

</tasks>

<verification>
After all 5 tasks land, run the 5-step verification chain:
1. `python tools/python_api_parity/check_parity_gate.py --repo-root .` — exit 0
2. `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings` — exit 0
3. `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python` — informational only (no module rebuild needed in Plan 1)
4. `uv run python -m pytest tools/python_api_parity/tests ClassicLib-rs/python-bindings/tests -q` — exit 0
5. `mypy --strict` — no .pyi changes in Plan 1, skip (full sweep is Plan 09b Task 4)
</verification>

<success_criteria>
- Pre-phase Pitfall 4 audit completed; all #[pyclass] registrations verified or fixed (Task 0)
- Central conftest.py handles sys.path bootstrap; no per-file sys.path.insert pollution
- `RUST_TARGET_CRATES.length == 19`, `PYTHON_TARGET_MODULES.length == 19`
- `_OWNER_RENDER_ORDER` derived from RUST_OWNER_BY_CRATE + 'aux' label (LOW drift guard)
- `validate_contract_rust_symbols()` wired into check_parity_gate.py main() before generate_diff_report()
- Existing 59 Tier-1 rows still pass (no regression)
- All Wave 0 test files exist; 13 tests pass + 1 strict=True xfail
- A10 sizing captured as machine-readable JSON AND in SUMMARY
- Atomic single commit per D-06
</success_criteria>

<output>
After completion, create `.planning/phases/03-python-tier-collapse/03-01-SUMMARY.md` containing:
- Files modified summary
- Pitfall 4 audit outcome (PASS or fixed-then-PASS with list of remediated registrations)
- The A10 sizing table — REQUIRED for downstream plans
- Confirmation that gate exits 0 with 59 Tier-1 rows + Pitfall 2 guard active
- Note any unexpected newly-surfaced symbols requiring follow-up plan budget adjustments
</output>
