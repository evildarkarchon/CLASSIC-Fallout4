---
phase: 03-python-tier-collapse
plan: 09b
type: execute
wave: 10
depends_on: [03-01, 03-02, 03-03, 03-04, 03-05, 03-06, 03-07, 03-08, 03-09a]
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
autonomous: true
requirements: [PYT-02, PYT-03, PYT-04, PYT-06]
must_haves:
  truths:
    - "generate_baseline.py::generate_diff_report() lines 574-610 (the gap_type=rust_unmapped / python_unmapped tier=tier2 branches) are deleted — safe only after Plan 09a has promoted every residual"
    - "parity_contract.json::tierDefinitions.tier2 key is deleted — structural single-tier collapse complete"
    - "summary.tier2_gap_total key is removed from generate_diff_report() return value; Task 2 pre-work enumerates every reader of this key in tools/, docs/, ClassicLib-rs/ and explicitly updates each reader (hard-code 0 or delete the read)"
    - "Inline Tier-2 comments in tools/python_api_parity/*.py are swept (cosmetic only)"
    - "Plan 01's test_tier2_definition_removed_after_plan_9 xfail flips from strict=True xfail to passing"
    - "Final mypy --strict sweep across ALL 19 .pyi files exits 0 (includes validate_stubs.py cross-check)"
    - "Final parity gate run exits 0 with runtime_coverage_summary.json::summary.deferred_total == 0 (PYT-06)"
    - "PYT-06 coverage completeness PowerShell one-liner (from VALIDATION.md) returns 0 missing rows"
  artifacts:
    - path: "tools/python_api_parity/generate_baseline.py"
      provides: "Cleaned generate_diff_report() with no Tier-2 gap branches"
    - path: "docs/implementation/python_api_parity/baseline/parity_contract.json"
      provides: "Final tier1Mappings; tierDefinitions has only tier1"
    - path: "docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json"
      provides: "summary.deferred_total == 0 (PYT-06)"
  key_links:
    - from: "tools/python_api_parity/tests/test_check_parity_gate.py::test_tier2_definition_removed_after_plan_9"
      to: "parity_contract.json::tierDefinitions"
      via: "snapshot test asserting tier2 absence (xfail flipped to passing)"
      pattern: "tier2.*not in"
---

<objective>
Final cleanup plan for Phase 3. Three concerns, ALL SAFE because Plan 09a has already promoted every residual with a wrapper (or failed closed):

1. **Tier-2 structural cleanup (A9):** Delete the dead code paths in `generate_baseline.py::generate_diff_report()` lines 574-610 (the `gap_type=rust_unmapped` / `python_unmapped` branches that produce `tier=tier2` rows). Also delete `summary.tier2_gap_total` and `parity_contract.json::tierDefinitions.tier2`. Sweep inline "Tier-2" comments.

2. **tier2_gap_total cascade cleanup:** Before deletion, enumerate every reader of `summary["tier2_gap_total"]` across `tools/`, `docs/`, and `ClassicLib-rs/`. Update each reader explicitly (hard-code 0 or delete the read entirely) — do NOT rely on dict `.get(key, 0)` silently hiding the deletion.

3. **Final verification sweep:** Run `mypy --strict` across ALL 19 `.pyi` files + `validate_stubs.py` cross-check + final parity gate. After this plan, `runtime_coverage_summary.json::summary.deferred_total == 0` (PYT-06) AND the coverage completeness PowerShell one-liner returns 0 missing rows.

Plan 01's xfail test (`test_tier2_definition_removed_after_plan_9`) flips from strict=True xfail to passing.

Output:
- Cleaned `generate_baseline.py` (lines 574-610 deleted; tier2_gap_total removed)
- All tier2_gap_total readers explicitly updated
- `parity_contract.json::tierDefinitions.tier2` deleted
- Inline comment sweep across `tools/python_api_parity/*.py`
- Plan 01 xfail flipped to passing (strict=True enforcement caught correctly)
- Final 5-step verification chain exits 0
- `runtime_coverage_summary.json::summary.deferred_total == 0`
- Coverage completeness PowerShell one-liner returns 0 missing rows
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
@.planning/phases/03-python-tier-collapse/03-09a-SUMMARY.md
@./CLAUDE.md

<interfaces>
<!-- A9 cleanup targets (VERIFIED against live generate_baseline.py lines 574-610) -->

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

Also delete `tier2_gap_total` from the summary dict at line 630:
```python
        "tier2_gap_total": sum(1 for gap in gaps if gap["tier"] == "tier2"),
```

<!-- parity_contract.json tierDefinitions cleanup -->

Find the `tierDefinitions` block (line 5 of parity_contract.json — VERIFIED). Current shape:
```json
"tierDefinitions": {
  "tier1": "Must-have Python APIs required by maintained integration workflows.",
  "tier2": "Deferred or lower-priority APIs outside initial gate scope."
}
```
Delete the `tier2` key.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Delete Tier-2 gap branches in generate_baseline.py::generate_diff_report()</name>
  <files>
    tools/python_api_parity/generate_baseline.py
  </files>
  <read_first>
    - tools/python_api_parity/generate_baseline.py (lines 560-650 — find and delete the Tier-2 gap branches)
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"Research Amendment A9"
  </read_first>
  <action>
    Delete the Tier-2 gap branches in `generate_baseline.py`. Find the block at lines ~574-610 (the `for rust_item in rust_symbols` and `for py_item in python_exports` loops that append `gap_type=rust_unmapped` / `python_unmapped` rows with `tier=tier2`). Delete the entire block.

    After deletion, the only `gaps.append(...)` calls remaining are the `tier1_*` status branches earlier in `generate_diff_report()`.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "$content = Get-Content tools/python_api_parity/generate_baseline.py -Raw; if ($content -match 'rust_unmapped' -or $content -match 'python_unmapped') { Write-Error 'Tier-2 gap branches still present'; exit 1 }; Write-Host 'OK'"</automated>
  </verify>
  <acceptance_criteria>
    - `generate_baseline.py` contains NO occurrences of `rust_unmapped` or `python_unmapped` literal strings
    - The `for rust_item in rust_symbols` residual loop is deleted
    - The `for py_item in python_exports` residual loop is deleted
  </acceptance_criteria>
  <done>Tier-2 gap branches deleted; only tier1_* status branches remain in generate_diff_report().</done>
</task>

<task type="auto">
  <name>Task 2: PRE-WORK — enumerate every reader of tier2_gap_total; delete the key and explicitly update each reader</name>
  <files>
    tools/python_api_parity/generate_baseline.py
    tools/python_api_parity/check_parity_gate.py
    docs/implementation/python_api_parity/baseline/parity_contract.json
    tools/python_api_parity/tests/test_check_parity_gate.py
  </files>
  <read_first>
    - tools/python_api_parity/generate_baseline.py (find the summary dict around line 630)
    - tools/python_api_parity/check_parity_gate.py
    - Full recursive grep output for tier2_gap_total
  </read_first>
  <action>
    PRE-WORK REQUIRED (per R_HIGH Plan 09 tier2_gap_total cascade): Before deleting, enumerate every reader:
    ```powershell
    $hits = Select-String -Path tools/*.py,tools/**/*.py,docs/**/*.md,docs/**/*.json,ClassicLib-rs/**/*.py,ClassicLib-rs/**/*.rs,ClassicLib-rs/**/*.ps1 -Pattern 'tier2_gap_total' -SimpleMatch 2>$null
    foreach ($hit in $hits) {
        Write-Host "$($hit.Path):$($hit.LineNumber): $($hit.Line.Trim())"
    }
    Write-Host "Total hits: $($hits.Count)"
    ```

    For EACH hit in the output, update the reader explicitly:
    - In Python source: replace `summary["tier2_gap_total"]` or `summary.get("tier2_gap_total", 0)` with the literal `0`, OR delete the read entirely if unused
    - In Markdown/docs: update the prose (e.g., "Tier-2 gap total: X" → remove or rewrite as single-tier description)
    - In JSON baselines: the `--write-baseline` refresh in Task 5 will remove them automatically once the Python source stops emitting them
    - In tests: update assertions to match the new summary shape

    Do NOT rely on dict `.get(key, 0)` silently hiding the deletion. Each reader must be explicitly updated.

    Step 1 — Delete the key from the summary dict in `generate_baseline.py`:
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

    Step 2 — Delete `tierDefinitions.tier2` from `parity_contract.json`. Find:
    ```json
    "tierDefinitions": {
      "tier1": "Must-have Python APIs required by maintained integration workflows.",
      "tier2": "Deferred or lower-priority APIs outside initial gate scope."
    }
    ```
    After:
    ```json
    "tierDefinitions": {
      "tier1": "Must-have Python APIs required by maintained integration workflows."
    }
    ```

    Step 3 — Update Plan 01's `test_check_parity_gate.py::test_tier2_definition_removed_after_plan_9`. Remove the `@pytest.mark.xfail(strict=True, ...)` decorator. The test should now pass (the assertion `'tier2' not in tierDefinitions` is now true). Because the xfail was `strict=True`, removing the decorator is the correct flip — if we left `strict=True` and the test started passing, strict xfail would fail; removing the decorator turns it into a normal passing test.

    Step 4 — Add a new test asserting `tier2_gap_total` no longer appears in the summary:
    ```python
    def test_tier2_gap_total_removed_from_summary() -> None:
        """Plan 9b A9 cleanup: tier2_gap_total no longer in parity_diff_report summary."""
        diff = json.loads(
            (REPO_ROOT / 'docs' / 'implementation' / 'python_api_parity' / 'baseline' / 'parity_diff_report.json').read_text(encoding='utf-8')
        )
        assert 'tier2_gap_total' not in diff['summary'], (
            "tier2_gap_total should be removed from parity_diff_report.json::summary by Plan 9b"
        )

    def test_tier1_contract_total_updated_after_plan_9a() -> None:
        """After Plan 9a + 9b, tier1Mappings includes all residuals."""
        contract = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
        # Plan 9a adds residuals beyond Plan 08's 358 (R9: GLOBAL_FCX_HANDLER excluded); minimum floor is 358
        assert len(contract['tier1Mappings']) >= 358
    ```
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "$hits = Select-String -Path tools/python_api_parity/*.py -Pattern 'tier2_gap_total'; if ($hits) { Write-Error ('Still found tier2_gap_total in: ' + ($hits.Path -join ', ')); exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest tools/python_api_parity/tests/test_check_parity_gate.py -v"</automated>
  </verify>
  <acceptance_criteria>
    - `tier2_gap_total` cascade enumeration performed via Select-String across tools/, docs/, ClassicLib-rs/
    - Every reader explicitly updated (no silent `.get(key, 0)` hides)
    - `generate_baseline.py::generate_diff_report()` summary dict does NOT contain `tier2_gap_total`
    - `parity_contract.json::tierDefinitions` does NOT contain a `tier2` key
    - Plan 01's `test_tier2_definition_removed_after_plan_9` passes WITHOUT the `@pytest.mark.xfail` decorator
    - New test `test_tier2_gap_total_removed_from_summary` passes
  </acceptance_criteria>
  <done>tier2_gap_total cascade enumerated and cleaned; tierDefinitions.tier2 deleted; xfail flipped to passing; all existing Phase 3 tooling tests still pass.</done>
</task>

<task type="auto">
  <name>Task 3: Sweep inline Tier-2 comments in tools/python_api_parity/*.py</name>
  <files>
    tools/python_api_parity/generate_baseline.py
    tools/python_api_parity/check_parity_gate.py
  </files>
  <read_first>
    - tools/python_api_parity/*.py (sweep for "Tier-2" or "tier-2" in comments)
  </read_first>
  <action>
    Sweep inline Tier-2 comments:
    ```powershell
    Select-String -Path tools/python_api_parity/*.py -Pattern '[Tt]ier.?2' | Where-Object { $_.Line -match '#|"""|\s*"' }
    ```
    For each comment match:
    - If it refers to the now-removed concept, delete or rewrite to "single-tier" / "Phase 3 collapse"
    - If it's load-bearing code (e.g., the variable name `tier1_rust_symbols`), leave it

    This is a cosmetic sweep — no behavior change.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "$hits = Select-String -Path tools/python_api_parity/*.py -Pattern '# .*[Tt]ier.?2' 2>$null; if ($hits) { Write-Host 'Review remaining:'; $hits | ForEach-Object { Write-Host \"$($_.Path):$($_.LineNumber): $($_.Line.Trim())\" }; Write-Host 'Manual review acceptable for load-bearing references'; } else { Write-Host 'OK: no Tier-2 comments'; }"</automated>
  </verify>
  <acceptance_criteria>
    - No `# Tier-2` or `# tier-2` comments referring to the deleted concept remain in `tools/python_api_parity/*.py`
    - Load-bearing code (`tier1_*` variable names) untouched
  </acceptance_criteria>
  <done>Inline Tier-2 comments swept.</done>
</task>

<task type="auto">
  <name>Task 4: Final mypy --strict sweep across all 19 .pyi files + validate_stubs.py + 5-step verification chain + PYT-06 check</name>
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
    - All 19 .pyi files listed in PYTHON_TARGET_MODULES (post-Plan-1 expansion)
    - tools/python_api_parity/generate_baseline.py::PYTHON_TARGET_MODULES (source of truth)
  </read_first>
  <action>
    Step 1: Refresh baseline (D-03):
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    ```

    Step 2: Run mypy --strict against every .pyi in PYTHON_TARGET_MODULES:
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
    if ($failures -gt 0) { exit 1 }
    Write-Host "All 19 .pyi files passed mypy --strict" -ForegroundColor Green
    ```

    Step 3: Run `validate_stubs.py` as separate verification (catches runtime/stub divergence not caught by mypy alone):
    ```powershell
    python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings
    ```

    Step 4: Run full 5-step verification chain:
    ```powershell
    python tools/python_api_parity/check_parity_gate.py --repo-root .
    python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings
    pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests tools/python_api_parity/tests -q
    # mypy already run in Step 2
    ```

    Step 5: Verify PYT-06 — `deferred_total == 0`:
    ```powershell
    $summary = Get-Content 'docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json' -Raw | ConvertFrom-Json
    if ($summary.summary.deferred_total -ne 0) {
        Write-Error "PYT-06 FAILED: deferred_total = $($summary.summary.deferred_total), expected 0"
        exit 1
    }
    Write-Host "PYT-06 SATISFIED: deferred_total = 0"
    ```

    Step 6: Run PYT-06 coverage completeness PowerShell one-liner from VALIDATION.md (confirm 0 missing rows):
    ```powershell
    $contract = Get-Content 'docs/implementation/python_api_parity/baseline/parity_contract.json' -Raw | ConvertFrom-Json
    $diff = Get-Content 'docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json' -Raw | ConvertFrom-Json
    $missing = @($contract.tier1Mappings | Where-Object {
        $row = $_
        -not ($diff.trackedSurface | Where-Object {
            $_.trackedType -eq 'contract_row' -and $_.contractId -eq $row.id -and $_.classification -eq 'runtime_verified'
        })
    })
    if ($missing.Count -gt 0) {
        Write-Error "MISSING runtime coverage for $($missing.Count) rows: $($missing[0..4].id -join ', ')..."
        exit 1
    }
    Write-Host "Coverage completeness: all $($contract.tier1Mappings.Count) tier1Mappings have runtime coverage"
    ```

    If anything fails, fix inside this plan and re-run. Do NOT commit partial state.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root .; if ($LASTEXITCODE -ne 0) { exit 1 }; python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests tools/python_api_parity/tests -q; if ($LASTEXITCODE -ne 0) { exit 1 }; $s = Get-Content 'docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json' -Raw | ConvertFrom-Json; if ($s.summary.deferred_total -ne 0) { Write-Error 'PYT-06 NOT SATISFIED'; exit 1 }; Write-Host 'PYT-06 SATISFIED'"</automated>
  </verify>
  <acceptance_criteria>
    - All 19 `.pyi` files pass `mypy --strict` individually
    - `validate_stubs.py --fail-on-warnings` exits 0 (cross-checks runtime/stub divergence)
    - `check_parity_gate.py` exits 0
    - `rebuild_rust.ps1 -Target python` exits 0
    - `pytest ClassicLib-rs/python-bindings/tests tools/python_api_parity/tests -q` exits 0
    - `runtime_coverage_summary.json::summary.deferred_total == 0` (PYT-06 satisfied)
    - PYT-06 coverage completeness PowerShell one-liner returns 0 missing rows (every tier1Mapping has runtime coverage)
    - `parity_diff_report.json::summary` does NOT contain `tier2_gap_total`
    - Plan 01's `test_tier2_definition_removed_after_plan_9` passes (xfail removed)
  </acceptance_criteria>
  <done>Phase 3 complete: gate green, deferred_total == 0, all 5 verification steps pass, single-tier model structurally enforced, coverage completeness verified.</done>
</task>

</tasks>

<verification>
Final 5-step verification chain:
1. `check_parity_gate.py` — exit 0
2. `validate_stubs.py --fail-on-warnings` — exit 0
3. `rebuild_rust.ps1 -Target python` — exit 0
4. `pytest ClassicLib-rs/python-bindings/tests tools/python_api_parity/tests -q` — exit 0
5. `mypy --strict` over all 19 .pyi files (Task 4 Step 2) — exit 0

PLUS:
- `runtime_coverage_summary.json::summary.deferred_total == 0` (PYT-06)
- PYT-06 coverage completeness PowerShell one-liner returns 0 missing rows
</verification>

<success_criteria>
- A9 cleanup complete: `generate_baseline.py` lines 574-610 deleted; `tier2_gap_total` removed from summary; every reader explicitly updated; `tierDefinitions.tier2` deleted
- Inline Tier-2 comments swept
- Final mypy --strict sweep across all 19 stubs exits 0
- validate_stubs.py cross-check passes
- 5-step verification chain exits 0
- PYT-06 satisfied: `runtime_coverage_summary.json::summary.deferred_total == 0` AND coverage completeness one-liner returns 0 missing rows
- Plan 01 xfail flipped to passing test
- Phase 3 complete; Phase 6 governance file deletion is now unblocked (Phase 6 owns DOC-02/DOC-04)
</success_criteria>

<output>
Create `.planning/phases/03-python-tier-collapse/03-09b-SUMMARY.md` with:
- Files modified (final list)
- tier2_gap_total cascade enumeration results (reader list)
- Final tier1Mappings.length
- 5-step verification chain results
- PYT-06 evidence (deferred_total = 0 AND coverage completeness one-liner output)
- Confirmation that the Plan 1 xfail test now passes
- Phase 3 close-out note: Phase 6 owns governance file deletion (DOC-02/DOC-04)
</output>
