---
phase: 03-python-tier-collapse
plan: 09
type: execute
wave: 9
depends_on: [03-01, 03-02, 03-03, 03-04, 03-05, 03-06, 03-07, 03-08]
files_modified:
  - tools/python_api_parity/generate_baseline.py
  - tools/python_api_parity/check_parity_gate.py
  - tools/python_api_parity/tests/test_check_parity_gate.py
  - docs/implementation/python_api_parity/baseline/parity_contract.json
  - docs/implementation/python_api_parity/baseline/parity_contract.md
  - docs/implementation/python_api_parity/baseline/parity_diff_report.json
  - docs/implementation/python_api_parity/baseline/parity_diff_report.md
  - docs/implementation/python_api_parity/baseline/rust_api_surface.json
  - docs/implementation/python_api_parity/baseline/python_api_surface.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
  - docs/implementation/python_api_parity/baseline/tier1_gate_report.md
  - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
autonomous: true
requirements: [PYT-02, PYT-06, HARM-03, HARM-04]
must_haves:
  truths:
    - "All A10 residual rows from newly-surfaced symbols (the 16 untracked crates discovered after Plan 1) are promoted as additional tier1Mappings — typically ~50-150 rows per the A10 sizing report from Plan 1"
    - "generate_baseline.py::generate_diff_report() lines 574-610 (the gap_type=rust_unmapped / python_unmapped tier=tier2 branches) are deleted — cosmetic dead-code removal after all symbols are promoted"
    - "parity_contract.json::tierDefinitions.tier2 key is deleted — single-tier model is structurally enforced in the contract schema"
    - "Inline comments referring to 'Tier-2' in tools/python_api_parity/*.py are removed (cosmetic sweep)"
    - "Final mypy --strict sweep across ALL 19 .pyi files exits 0"
    - "Final parity gate run exits 0 with runtime_coverage_summary.json::summary.deferred_total == 0 (PYT-06 satisfied)"
    - "test_tier2_definition_removed_after_plan_9 from Plan 1's test_check_parity_gate.py changes from xfail to passing (the eventual invariant is now true)"
  artifacts:
    - path: "tools/python_api_parity/generate_baseline.py"
      provides: "Cleaned generate_diff_report() with no Tier-2 gap branches"
    - path: "docs/implementation/python_api_parity/baseline/parity_contract.json"
      provides: "Final tier1Mappings (>= 359 + A10 residuals); tierDefinitions has only tier1"
      contains: "tier1"
    - path: "docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json"
      provides: "summary.deferred_total == 0 (PYT-06)"
  key_links:
    - from: "tools/python_api_parity/tests/test_check_parity_gate.py::test_tier2_definition_removed_after_plan_9"
      to: "parity_contract.json::tierDefinitions"
      via: "snapshot test asserting tier2 absence"
      pattern: "tier2.*not in"
---

<objective>
Final cleanup plan for Phase 3. Three concerns:

1. **A10 residual promotion:** Promote any remaining symbols newly-surfaced from the 16 currently-untracked crates by Plan 1's RUST_TARGET_CRATES expansion. The Plan 1 SUMMARY captured per-owner `tier2_gap_total` counts; this plan promotes them in the same atomic fashion as Plans 2-8.

2. **Tier-2 structural cleanup (A9):** After all symbols are promoted, the dead code paths in `generate_baseline.py::generate_diff_report()` lines 574-610 (the `gap_type=rust_unmapped` / `python_unmapped` branches that produce `tier=tier2` rows) produce zero rows. Delete them. Also delete `tierDefinitions.tier2` from `parity_contract.json` and sweep inline "Tier-2" comments.

3. **Final verification sweep:** Run `mypy --strict` across ALL 19 `.pyi` files (not just one), then run the final parity gate. After this plan, `runtime_coverage_summary.json::summary.deferred_total == 0` (PYT-06).

Per A9, `check_parity_gate.py` has NO skip flag to remove. The cleanup is in `generate_baseline.py`, `parity_contract.json::tierDefinitions`, and inline comments.

Per A10, the residual row count from newly-surfaced symbols was estimated at ~50-150 in Plan 1. The exact count comes from the Plan 1 SUMMARY's sizing report.

Output:
- ~50-150 additional tier1Mappings rows for A10 residuals (final tier1Mappings.length is ~410-510 depending on residual count; baseline Plan 1-8 progression: 59 → 133 → 191 → 241 → 287 → 313 → 348 → 359 + residuals)
- Stub updates for whichever crates have residual rows (depends on A10 sizing report)
- Smoke test additions for any residual #[pyclass] types
- Cleaned `generate_baseline.py` (lines 574-610 deleted)
- `parity_contract.json::tierDefinitions.tier2` deleted
- Inline comment sweep across `tools/python_api_parity/*.py`
- Final 5-step verification chain exits 0
- `runtime_coverage_summary.json::summary.deferred_total == 0`
- xfail test from Plan 1 (test_tier2_definition_removed_after_plan_9) flips to passing
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
@.planning/phases/03-python-tier-collapse/03-08-SUMMARY.md
@./CLAUDE.md

<interfaces>
<!-- A9 cleanup targets -->

From tools/python_api_parity/generate_baseline.py lines 574-610 (paste verbatim — delete this exact block):
```python
    for rust_item in rust_symbols:
        symbol = rust_item["symbol"]
        if symbol in tier1_rust_symbols:
            continue
        gaps.append(
            {
                "gap_type": "rust_unmapped",
                "tier": "tier2",
                "owner_module": rust_item["owner_module"],
                "squad": SQUAD_BY_OWNER[rust_item["owner_module"]],
                "rust_symbol": symbol,
                "python_module": None,
                "python_export": None,
                "reason": "Rust public symbol is outside Tier-1 mapping scope (deferred).",
                "crate": rust_item["crate"],
                "kind": rust_item["kind"],
            }
        )

    for py_item in python_exports:
        pair = (py_item["module"], py_item.get("export_path", py_item["export"]))
        if pair in tier1_python_pairs:
            continue
        gaps.append(
            {
                "gap_type": "python_unmapped",
                "tier": "tier2",
                "owner_module": py_item["owner_module"],
                "squad": SQUAD_BY_OWNER[py_item["owner_module"]],
                "rust_symbol": None,
                "python_module": py_item["module"],
                "python_export": py_item["export"],
                "python_export_path": py_item.get("export_path", py_item["export"]),
                "reason": "Python export is outside Tier-1 mapping scope (deferred).",
                "kind": py_item["kind"],
            }
        )
```

After deletion, the only `gaps.append(...)` calls remaining are the `tier1_*` status branches earlier in `generate_diff_report()`.

Also delete `tier2_gap_total` from the summary dict (line 630 area):
```python
        "tier2_gap_total": sum(1 for gap in gaps if gap["tier"] == "tier2"),
```

The summary key removal cascades to consumers — verify no other code reads `summary["tier2_gap_total"]` (search, replace if needed).

<!-- parity_contract.json tierDefinitions cleanup -->

Find the `tierDefinitions` block in parity_contract.json. Likely shape:
```json
"tierDefinitions": {
  "tier1": {"description": "...enforced..."},
  "tier2": {"description": "...deferred..."}
}
```
Delete the `tier2` key.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Promote A10 residual rows from newly-surfaced symbols across the 16 untracked crates</name>
  <files>
    docs/implementation/python_api_parity/baseline/parity_contract.json
    ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi
    ClassicLib-rs/python-bindings/classic-database-py/classic_database.pyi
    ClassicLib-rs/python-bindings/classic-scangame-py/classic_scangame.pyi
    ClassicLib-rs/python-bindings/classic-registry-py/classic_registry.pyi
    ClassicLib-rs/python-bindings/classic-perf-py/classic_perf.pyi
    ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi
    ClassicLib-rs/python-bindings/classic-message-py/classic_message.pyi
    ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi
    ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi
    ClassicLib-rs/python-bindings/classic-version-py/classic_version.pyi
    ClassicLib-rs/python-bindings/classic-resource-py/classic_resource.pyi
    ClassicLib-rs/python-bindings/classic-xse-py/classic_xse.pyi
    ClassicLib-rs/python-bindings/classic-web-py/classic_web.pyi
    ClassicLib-rs/python-bindings/classic-update-py/classic_update.pyi
    ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py
    ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
  </files>
  <read_first>
    - .planning/phases/03-python-tier-collapse/03-01-SUMMARY.md (A10 sizing report — per-owner tier2_gap_total counts after Plan 1's expansion)
    - docs/implementation/python_api_parity/baseline/parity_diff_report.json (current per-owner gap_counts_by_owner_tier — what's left after Plans 2-8)
    - docs/implementation/python_api_parity/baseline/rust_api_surface.json (newly-surfaced symbols from the 16 untracked crates)
    - For each owner with residuals: read the corresponding -core/lib.rs and -py/src/lib.rs to author rows (e.g., classic-yaml-core/src/lib.rs, classic-yaml-py/src/lib.rs)
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"Research Amendment A10"
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Open Questions item 2" (lines 967-971)
  </read_first>
  <action>
    Step 1: Read the A10 sizing report from `03-01-SUMMARY.md`. This tells you exactly how many residual rows need promotion per owner module. Example expected output from Plan 1:
    ```
    yaml      : 12 newly-surfaced rows
    database  : 8 newly-surfaced rows
    file_io   : 0 (covered by Plan 8)
    scangame  : 23 newly-surfaced rows
    registry  : 4 newly-surfaced rows
    perf      : 6 newly-surfaced rows
    settings  : 5 newly-surfaced rows
    message   : 7 newly-surfaced rows
    path      : 11 newly-surfaced rows
    constants : 9 newly-surfaced rows
    version   : 5 newly-surfaced rows
    resource  : 4 newly-surfaced rows
    xse       : 6 newly-surfaced rows
    web       : 7 newly-surfaced rows
    update    : 5 newly-surfaced rows
    Total residual: ~112 rows (within 50-150 estimate)
    ```

    Step 2: Run `parse_rust_surface()` against the current state and extract every entry where `tier == 'tier2'` (these are the residual gap rows that need promotion):
    ```powershell
    python tools/python_api_parity/generate_baseline.py --repo-root .
    $surface = Get-Content 'docs/implementation/python_api_parity/baseline/rust_api_surface.json' -Raw | ConvertFrom-Json
    $residuals = $surface.symbols | Where-Object { $_.tier -eq 'tier2' }
    Write-Host "Residual symbols: $($residuals.Count)"
    $residuals | Group-Object owner_module | ForEach-Object { Write-Host "  $($_.Name): $($_.Count)" }
    ```

    Step 3: For each residual symbol, author one tier1Mapping row. Group by owner_module so the work for each crate stays atomic. For each row:
    - Extract `rustSymbol`, `rustCrate`, `rustKind` from the parser output
    - Compute `pythonModule` (e.g., `classic_yaml`) and `pythonExportPath` from the corresponding `-py` wrapper:
      - If a wrapper exists with a matching `#[pyclass(name = "...")]`, use the renamed name
      - If no wrapper exists yet, the row CANNOT be promoted — surface a planning error and document in the SUMMARY (this becomes a follow-up task for a future milestone)
    - Use the same row shape as Plans 2-8

    Step 4: For each owner module receiving residual rows, update the corresponding `.pyi` stub to cover the new pythonExportPaths. Hand-edit only (anti-feature: stubgen).

    Step 5: Create `test_promoted_residuals_smoke.py` with one smoke test per residual `#[pyclass]`. Group by module:
    ```python
    """Per-class smoke tests for Phase 3 Plan 09 — A10 residual promotions."""
    from __future__ import annotations

    # Test imports for each module that received residual rows
    import classic_yaml
    import classic_database
    # ... etc

    def test_classic_yaml_residual_class_smoke() -> None:
        # Construct + minimal method call for each yaml residual
        ...
    # ... one test per residual #[pyclass]
    ```

    Step 6: Update `runtime_coverage_registry.json`:
    - For each owner module receiving residuals, ADD a new selector entry `python-tier1-<owner>` (or update existing) with the correct contractCount
    - Selector entries (one per residual-receiving owner): `python-tier1-yaml`, `python-tier1-database`, `python-tier1-scangame`, `python-tier1-registry`, `python-tier1-perf`, `python-tier1-settings`, `python-tier1-message`, `python-tier1-path`, `python-tier1-constants`, `python-tier1-version`, `python-tier1-resource`, `python-tier1-xse`, `python-tier1-web`, `python-tier1-update`

    Step 7: Insert all residual rows into `parity_contract.json::tier1Mappings`. Final length depends on A10 sizing.

    Step 8: Do NOT regenerate the baseline yet — Task 4 handles atomic refresh.

    EXECUTOR NOTE: This task may discover that some residual symbols have NO `-py` wrapper. In that case, the planner-correct outcome is to either (a) skip them and document as Phase 6 follow-up, OR (b) hold the entire Plan 9 and create a new gap closure plan. Choose (a) by default and note in SUMMARY.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import json; c = json.loads(open('docs/implementation/python_api_parity/baseline/parity_contract.json').read()); print(f'tier1Mappings.length = {len(c[\"tier1Mappings\"])}'); assert len(c['tier1Mappings']) >= 359"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length >= 359 + (A10 residual count)`
    - Every residual row has a valid `rustSymbol` matching the parsed Rust surface
    - Every residual row has a valid `pythonExportPath` (skipped rows are documented in SUMMARY as Phase 6 follow-up)
    - Each affected `.pyi` file gained stub entries for its residual rows
    - `test_promoted_residuals_smoke.py` has at least one test per residual `#[pyclass]` (or tests are documented as not-applicable for non-class symbols)
  </acceptance_criteria>
  <done>A10 residuals promoted; remaining symbols (if any) documented for Phase 6 follow-up.</done>
</task>

<task type="auto">
  <name>Task 2: A9 cleanup — delete generate_diff_report() Tier-2 gap branches; delete tierDefinitions.tier2; sweep comments</name>
  <files>
    tools/python_api_parity/generate_baseline.py
    docs/implementation/python_api_parity/baseline/parity_contract.json
    tools/python_api_parity/check_parity_gate.py
    tools/python_api_parity/tests/test_check_parity_gate.py
  </files>
  <read_first>
    - tools/python_api_parity/generate_baseline.py (lines 560-650 — find and delete the Tier-2 gap branches)
    - tools/python_api_parity/check_parity_gate.py (full file — sweep "Tier-2" comments only; per A9, no skip flag exists)
    - docs/implementation/python_api_parity/baseline/parity_contract.json (find tierDefinitions block)
    - tools/python_api_parity/tests/test_check_parity_gate.py (Plan 1's xfail test — flip from xfail to passing)
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"Research Amendment A9"
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Where Tier-2 skip logic actually lives" (lines 975-989)
  </read_first>
  <action>
    Step 1: Delete the Tier-2 gap branches in `generate_baseline.py`. Find the block at lines ~574-610 (the `for rust_item in rust_symbols` and `for py_item in python_exports` loops that append `gap_type=rust_unmapped` / `python_unmapped` rows with `tier=tier2`). Delete the entire block. Also delete the `"tier2_gap_total"` entry from the `summary` dict around line 630.

    After deletion, the `summary` dict should have:
    ```python
    summary = {
        "tier1_contract_total": len(contract_results),
        "tier1_matched": status_counts.get("matched", 0),
        "tier1_missing_rust": status_counts.get("missing_rust", 0),
        "tier1_missing_python": status_counts.get("missing_python", 0),
        "tier1_signature_mismatch": status_counts.get("signature_mismatch", 0),
        "total_gaps": len(gaps),
        "tier1_gap_total": sum(1 for gap in gaps if gap["tier"] == "tier1"),
        # tier2_gap_total REMOVED — Phase 3 D-09 single-tier collapse
    }
    ```

    Search for any other readers of `summary["tier2_gap_total"]` in the codebase (likely in `check_parity_gate.py` and the rendering helpers). Replace them with hard-coded 0 or delete the read entirely. Use grep to find:
    ```powershell
    Select-String -Path tools/python_api_parity/*.py -Pattern "tier2_gap_total"
    Select-String -Path tools/binding_parity_runtime_coverage.py -Pattern "tier2_gap_total"
    ```

    Step 2: Delete `tierDefinitions.tier2` from `parity_contract.json`. Find the `tierDefinitions` block and remove the `tier2` key. The result should leave only `tier1`:
    ```json
    "tierDefinitions": {
      "tier1": {"description": "Enforced parity contract — every row must match Rust and Python surfaces."}
    }
    ```

    Step 3: Sweep inline "Tier-2" comments in `tools/python_api_parity/*.py`:
    ```powershell
    Select-String -Path tools/python_api_parity/*.py -Pattern "[Tt]ier.?2"
    ```
    For each match: if it's a comment referring to the now-removed concept, delete or rewrite to "single-tier" / "Phase 3 collapse". If it's load-bearing code (e.g., the variable name `tier1_rust_symbols`), leave it.

    Step 4: Update `tools/python_api_parity/tests/test_check_parity_gate.py`. The Plan 1 xfail test:
    ```python
    @pytest.mark.xfail(reason="tier2 definition removal lands in Plan 9 (PYT-03)", strict=False)
    def test_tier2_definition_removed_after_plan_9() -> None:
        ...
    ```
    Remove the `@pytest.mark.xfail` decorator. The test should now pass (the assertion `'tier2' not in tierDefinitions` is now true).

    Also add a new test asserting `tier2_gap_total` no longer appears in the summary:
    ```python
    def test_tier2_gap_total_removed_from_summary() -> None:
        """Plan 9 A9 cleanup: tier2_gap_total no longer in parity_diff_report summary."""
        diff = json.loads(REPO_ROOT.joinpath('docs/implementation/python_api_parity/baseline/parity_diff_report.json').read_text(encoding='utf-8'))
        assert 'tier2_gap_total' not in diff['summary']
    ```
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "Select-String -Path tools/python_api_parity/generate_baseline.py -Pattern 'gap_type.*rust_unmapped|gap_type.*python_unmapped|tier2_gap_total' -Quiet; if (`$LASTEXITCODE -eq 0) { Write-Error 'Tier-2 references still present in generate_baseline.py'; exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest tools/python_api_parity/tests/test_check_parity_gate.py -v"</automated>
  </verify>
  <acceptance_criteria>
    - `tools/python_api_parity/generate_baseline.py` does NOT contain `gap_type.*rust_unmapped`, `gap_type.*python_unmapped`, or `tier2_gap_total` anywhere
    - `parity_contract.json::tierDefinitions` does NOT contain a `tier2` key
    - `tools/python_api_parity/tests/test_check_parity_gate.py::test_tier2_definition_removed_after_plan_9` is no longer marked xfail and passes
    - New test `test_tier2_gap_total_removed_from_summary` passes
    - No "Tier-2" comments remain in `tools/python_api_parity/*.py` (load-bearing code like `tier1_*` variable names is OK to keep)
    - All existing Phase 3 tooling tests still pass
  </acceptance_criteria>
  <done>A9 cleanup complete: dead code paths deleted, schema collapsed to single tier, comments swept, tests updated.</done>
</task>

<task type="auto">
  <name>Task 3: Final mypy --strict sweep across all 19 .pyi files</name>
  <files>
    (Read-only on stub files; this task only RUNS mypy and reports failures)
  </files>
  <read_first>
    - All 19 .pyi files listed in PYTHON_TARGET_MODULES (post-Plan-1 expansion)
    - tools/python_api_parity/generate_baseline.py::PYTHON_TARGET_MODULES (source of truth for the 19 paths)
  </read_first>
  <action>
    Run `mypy --strict` against every `.pyi` file in `PYTHON_TARGET_MODULES`. Fail fast on the first error.

    PowerShell loop:
    ```powershell
    $stubs = @(
        "ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi",
        "ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi",
        "ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi",
        "ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi",
        "ClassicLib-rs/python-bindings/classic-database-py/classic_database.pyi",
        "ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi",
        "ClassicLib-rs/python-bindings/classic-scangame-py/classic_scangame.pyi",
        "ClassicLib-rs/python-bindings/classic-registry-py/classic_registry.pyi",
        "ClassicLib-rs/python-bindings/classic-perf-py/classic_perf.pyi",
        "ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi",
        "ClassicLib-rs/python-bindings/classic-message-py/classic_message.pyi",
        "ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi",
        "ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi",
        "ClassicLib-rs/python-bindings/classic-version-py/classic_version.pyi",
        "ClassicLib-rs/python-bindings/classic-resource-py/classic_resource.pyi",
        "ClassicLib-rs/python-bindings/classic-xse-py/classic_xse.pyi",
        "ClassicLib-rs/python-bindings/classic-web-py/classic_web.pyi",
        "ClassicLib-rs/python-bindings/classic-update-py/classic_update.pyi",
        "ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi"
    )
    $failures = 0
    foreach ($stub in $stubs) {
        Write-Host "mypy --strict $stub"
        uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict $stub
        if ($LASTEXITCODE -ne 0) {
            Write-Host "FAILED: $stub" -ForegroundColor Red
            $failures++
        }
    }
    if ($failures -gt 0) {
        Write-Host "Total failures: $failures" -ForegroundColor Red
        exit 1
    }
    Write-Host "All 19 .pyi files passed mypy --strict" -ForegroundColor Green
    ```

    If any file fails, fix the stub and re-run. Common failures:
    - PyO3 0.27 type mapping mismatch — fix the annotation
    - Missing return type annotation — add explicit return type
    - Generic type without parameters — add type parameters
    - Forward reference not quoted — add string quotes or `from __future__ import annotations`

    The fix lands in this task (no separate plan).
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "$stubs = @('ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi','ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi','ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi','ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi','ClassicLib-rs/python-bindings/classic-database-py/classic_database.pyi','ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi','ClassicLib-rs/python-bindings/classic-scangame-py/classic_scangame.pyi','ClassicLib-rs/python-bindings/classic-registry-py/classic_registry.pyi','ClassicLib-rs/python-bindings/classic-perf-py/classic_perf.pyi','ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi','ClassicLib-rs/python-bindings/classic-message-py/classic_message.pyi','ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi','ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi','ClassicLib-rs/python-bindings/classic-version-py/classic_version.pyi','ClassicLib-rs/python-bindings/classic-resource-py/classic_resource.pyi','ClassicLib-rs/python-bindings/classic-xse-py/classic_xse.pyi','ClassicLib-rs/python-bindings/classic-web-py/classic_web.pyi','ClassicLib-rs/python-bindings/classic-update-py/classic_update.pyi','ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi'); $f=0; foreach ($s in $stubs) { uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict $s; if ($LASTEXITCODE -ne 0) { $f++ } }; if ($f -gt 0) { exit 1 }"</automated>
  </verify>
  <acceptance_criteria>
    - All 19 `.pyi` files pass `mypy --strict` individually
    - No file produces type errors
    - PYT-04 satisfied across all 19 binding stubs
  </acceptance_criteria>
  <done>Final mypy --strict sweep across all 19 stubs exits 0.</done>
</task>

<task type="auto">
  <name>Task 4: Refresh baseline, run final 5-step verification chain, confirm deferred_total == 0</name>
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
    - docs/implementation/python_api_parity/baseline/parity_contract.json (post-Tasks-1-2 state)
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"Goal: PYT-06 deferred_total == 0"
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Assumption Correction A4" (deferred_total is the gate-relevant number)
  </read_first>
  <action>
    Step 1: Refresh the baseline:
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    ```

    Step 2: Run the full 5-step plan-close verification chain:
    ```powershell
    python tools/python_api_parity/check_parity_gate.py --repo-root .
    python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings
    pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests tools/python_api_parity/tests -q
    ```
    (Step 5 mypy already done in Task 3.)

    Step 3: Verify PYT-06 — confirm `runtime_coverage_summary.json::summary.deferred_total == 0`:
    ```powershell
    $summary = Get-Content 'docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json' -Raw | ConvertFrom-Json
    if ($summary.summary.deferred_total -ne 0) {
        Write-Error "PYT-06 FAILED: deferred_total = $($summary.summary.deferred_total), expected 0"
        exit 1
    }
    Write-Host "PYT-06 SATISFIED: deferred_total = 0"
    ```

    Step 4: Run the coverage completeness PowerShell one-liner from VALIDATION.md to confirm every contract row has runtime coverage:
    ```powershell
    $contract = Get-Content 'docs/implementation/python_api_parity/baseline/parity_contract.json' -Raw | ConvertFrom-Json
    $diff = Get-Content 'docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json' -Raw | ConvertFrom-Json
    $missing = @()
    foreach ($row in $contract.tier1Mappings) {
        $found = $diff.trackedSurface | Where-Object { $_.trackedType -eq 'contract_row' -and $_.contractId -eq $row.id -and $_.classification -eq 'runtime_verified' }
        if (-not $found) { $missing += $row.id }
    }
    if ($missing.Count -gt 0) {
        Write-Error "MISSING runtime coverage for: $($missing -join ', ')"
        exit 1
    }
    Write-Host "All tier1Mappings have runtime coverage"
    ```

    If anything fails, fix inside this plan and re-run.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root .; if ($LASTEXITCODE -ne 0) { exit 1 }; python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests tools/python_api_parity/tests -q; if ($LASTEXITCODE -ne 0) { exit 1 }; $s = Get-Content 'docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json' -Raw | ConvertFrom-Json; if ($s.summary.deferred_total -ne 0) { Write-Error 'PYT-06 NOT SATISFIED'; exit 1 }; Write-Host 'PYT-06 SATISFIED: deferred_total = 0'"</automated>
  </verify>
  <acceptance_criteria>
    - `python tools/python_api_parity/check_parity_gate.py --repo-root .` exits 0
    - `python ClassicLib-rs/validate_stubs.py --fail-on-warnings` exits 0
    - `pwsh rebuild_rust.ps1 -Target python` exits 0
    - `pytest ClassicLib-rs/python-bindings/tests tools/python_api_parity/tests -q` exits 0
    - `runtime_coverage_summary.json::summary.deferred_total == 0` (PYT-06 satisfied)
    - `parity_diff_report.json::summary.tier1_missing_rust == 0`, `tier1_missing_python == 0`, `tier1_signature_mismatch == 0`
    - `parity_diff_report.json::summary` does NOT contain a `tier2_gap_total` key
    - All tier1Mappings have matching runtime coverage (no MISSING_RUNTIME entries from completeness one-liner)
    - The Plan 1 xfail test (`test_tier2_definition_removed_after_plan_9`) passes without xfail marker
  </acceptance_criteria>
  <done>Phase 3 complete: gate green, deferred_total == 0, all 5 verification steps pass, single-tier model structurally enforced.</done>
</task>

</tasks>

<verification>
Final verification chain:
1. `python tools/python_api_parity/check_parity_gate.py --repo-root .` — exit 0
2. `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract ... --fail-on-warnings` — exit 0
3. `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python` — exit 0 (full rebuild)
4. `uv run pytest ClassicLib-rs/python-bindings/tests tools/python_api_parity/tests -q` — exit 0
5. mypy --strict over all 19 .pyi files (Task 3) — exit 0

Phase 3 success criterion: `runtime_coverage_summary.json::summary.deferred_total == 0` (PYT-06).
</verification>

<success_criteria>
- A10 residuals promoted (~50-150 additional rows from the 16 untracked crates)
- A9 cleanup: `generate_baseline.py` lines 574-610 deleted, `tier2_gap_total` removed from summary, `tierDefinitions.tier2` deleted, "Tier-2" comments swept
- Final mypy --strict sweep across all 19 stubs exits 0
- 5-step verification chain exits 0
- `runtime_coverage_summary.json::summary.deferred_total == 0` (PYT-06)
- `parity_contract.json::tier1Mappings.length` reflects all 285 + 12 + 6 + A10 residuals (final ~410-510 depending on residual count)
- Plan 1 xfail test flips to passing
- Phase 3 complete; Phase 6 governance file deletion is now unblocked (but is NOT part of Phase 3 — Phase 6 owns DOC-02/DOC-04)

NOTE on parallel execution: Per the planning directive, Plans 2-9 run sequentially (waves 2-9) by default to avoid merge conflicts on the shared baseline files (parity_contract.json, parity_diff_report.json, etc.). If a future contributor opts into a merge-queue strategy, the plans CAN be parallelized — but the safe default is sequential.
</success_criteria>

<output>
Create `.planning/phases/03-python-tier-collapse/03-09-SUMMARY.md` with:
- Files modified (final list)
- A10 residual row count promoted
- Final tier1Mappings.length
- 5-step verification chain results
- PYT-06 evidence (deferred_total = 0)
- Confirmation that the Plan 1 xfail test now passes
- Note: Phase 3 complete; Phase 6 owns governance file deletion (DOC-02/DOC-04)
</output>
