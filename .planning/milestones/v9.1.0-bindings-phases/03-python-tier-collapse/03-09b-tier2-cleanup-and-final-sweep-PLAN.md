---
phase: 03-python-tier-collapse
plan: 09b
type: execute
wave: 10
depends_on: [03-01, 03-02, 03-03, 03-04, 03-05, 03-06, 03-07, 03-08, 03-09a]
files_modified:
  - .planning/phases/03-python-tier-collapse/03-09b-TIER2-CASCADE-AUDIT.md
  - tools/python_api_parity/generate_baseline.py
  - tools/python_api_parity/tests/test_check_parity_gate.py
  - ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py
  - docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json
  - docs/implementation/python_api_parity/baseline/parity_contract.json
  - docs/implementation/python_api_parity/baseline/parity_contract.md
  - docs/implementation/python_api_parity/baseline/parity_diff_report.json
  - docs/implementation/python_api_parity/baseline/parity_diff_report.md
  - docs/implementation/python_api_parity/baseline/rust_api_surface.json
  - docs/implementation/python_api_parity/baseline/python_api_surface.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
  - docs/implementation/python_api_parity/baseline/tier1_gate_report.md
  - ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.json
  - ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.md
  - ClassicLib-rs/python-bindings/parity-artifacts/python_api_surface.json
  - ClassicLib-rs/python-bindings/parity-artifacts/rust_api_surface.json
  - ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json
  - ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.md
  - ClassicLib-rs/python-bindings/parity-artifacts/tier1_gate_report.md
autonomous: true
requirements: [PYT-02, PYT-03, PYT-04, PYT-06]
must_haves:
  truths:
    - "Pre-deletion tier2_gap_total / python_unmapped / rust_unmapped / tierDefinitions.tier2 cascade audit uses a recursive ripgrep search across the entire repo (M8 fix), NOT a selective glob list. The search scope includes tools/python_api_parity/, tools/cxx_api_parity/, tools/*.py (repo-root), ClassicLib-rs/python-bindings/, docs/api/, docs/implementation/python_api_parity/, .github/workflows/, and *.ps1. Audit file 03-09b-TIER2-CASCADE-AUDIT.md records both the ripgrep command used AND the total match count. Each hit is classified (CODE_WRITE / CODE_READ / DOCS_PROSE / TEST_ASSERTION / BASELINE_JSON / HISTORICAL_COMMENT / OUT_OF_SCOPE_PHASE_4). Load-bearing matches (e.g., tier1_* variable names) are explicitly excluded."
    - "tools/python_api_parity/generate_baseline.py::generate_diff_report() has its `for rust_item in rust_symbols` loop (currently L672-689) and `for py_item in python_exports` loop (currently L691-708) DELETED. Line numbers MUST be re-verified with `Select-String -Pattern 'rust_unmapped|python_unmapped'` BEFORE editing because Plan 09a may have shifted them via any new imports."
    - "tools/python_api_parity/generate_baseline.py: `tier2_gap_total` key (currently L728) is DELETED from the `summary` dict in `generate_diff_report()`. The `Tier 2 Gaps` markdown column (currently L778) and its cell expression (currently L783) are also DELETED from `render_diff_markdown()`."
    - "parity_contract.json::tierDefinitions.tier2 key is DELETED."
    - "ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py L170 (C4 fix): the assertion `assert report['gaps'][1]['gap_type'] == 'python_unmapped'` is UPDATED in the SAME commit as the generate_baseline.py branch deletion. Because the python_unmapped branch is gone, the test's synthetic contract produces only 1 gap (tier1_missing_python from the deliberate contract mismatch), so the assertion becomes `assert len(report['gaps']) == 1` (or equivalent that asserts the python_unmapped branch no longer fires). The existing `tier1_missing_python` assertion at L169 is UNCHANGED."
    - "Plan 01's test_tier2_definition_removed_after_plan_9 (tools/python_api_parity/tests/test_check_parity_gate.py:44-57) has its @pytest.mark.xfail(strict=True) decorator REMOVED and passes as a normal test in the same commit as the tierDefinitions.tier2 deletion."
    - "M7 fix: Task 2 and Task 3 are ATOMICALLY COMBINED into a single commit that contains (a) the generate_baseline.py edits, (b) the test_python_parity_tooling.py assertion update, (c) the test_check_parity_gate.py xfail flip, (d) the parity_contract.json::tierDefinitions.tier2 deletion, (e) the baseline refresh (generate_baseline.py --write-baseline + check_parity_gate.py --update-baseline), AND (f) any new test assertions added in Task 2. This prevents a bisect-breaking intermediate state where a new test reads stale parity_diff_report.json data."
    - "C3 endgame: docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json::entries is EMPTIED to `[]` (the file stays with schemaVersion+binding+entries shape; only entries[] is cleared). This is the empirically-verified REQUIRED step to drive `deferred_total` to 0 — the `build_coverage_summary` registry_only fallback at L264-292 picks up deferred backlog entries even after their gap rows are removed, so emptying the gap source alone is INSUFFICIENT. Phase 3 hygiene (the backlog contents no longer reflect the promoted state) is scope-appropriate; Phase 6 DOC-02/DOC-04 owns DELETING the file/directory, not editing its contents."
    - "Final mypy --strict sweep runs in ONE command with all 19 stub paths as arguments (L13 fix: single run catches cross-stub type references that per-file foreach cannot detect). Explicit 19-stub enumeration — no globs; the foundation/classic-shared-py stub is in the list because validate_stubs.py does not discover it (M11)."
    - "validate_stubs.py --fail-on-warnings exits 0 against the full parity contract (cross-check runtime vs stub divergence for the 18 python-bindings crates; classic_shared coverage is handled by the mypy sweep)."
    - "Final parity gate run exits 0 with `runtime_coverage_summary.json::summary.deferred_total == 0` (PYT-06 primary success criterion per ROADMAP L87 + REQUIREMENTS.md L39)."
    - "PYT-06 coverage completeness PowerShell one-liner from VALIDATION.md returns 0 missing rows (every tier1Mapping has matching runtime coverage in trackedSurface)."
    - "Claude reviewer suggestion #6: IF the final gate fails with `deferred_total != 0`, the failure path prints a diagnostic dump of stuck deferred backlog entries BEFORE `exit 1` so the operator can see exactly which entries still classify as deferred instead of a bare `exit 1`."
  artifacts:
    - path: "tools/python_api_parity/generate_baseline.py"
      provides: "Cleaned generate_diff_report() with no Tier-2 gap branches; no tier2_gap_total summary key; no Tier-2 markdown column"
    - path: "tools/python_api_parity/tests/test_check_parity_gate.py"
      provides: "test_tier2_definition_removed_after_plan_9 passes without xfail decorator"
    - path: "ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py"
      provides: "L169-170 assertion updated to match post-branch-deletion state (C4 fix)"
    - path: "docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json"
      provides: "entries=[] (empty) — all Phase 3 promotions have reached tier1; the backlog no longer tracks any deferred items because there are none post-Phase-3"
    - path: "docs/implementation/python_api_parity/baseline/parity_contract.json"
      provides: "Final tier1Mappings (~1100+); tierDefinitions has only tier1"
    - path: "docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json"
      provides: "summary.deferred_total == 0 (PYT-06 satisfied)"
    - path: ".planning/phases/03-python-tier-collapse/03-09b-TIER2-CASCADE-AUDIT.md"
      provides: "Recursive ripgrep cascade audit with classified hits and remediation status per file"
  key_links:
    - from: "tools/python_api_parity/tests/test_check_parity_gate.py::test_tier2_definition_removed_after_plan_9"
      to: "parity_contract.json::tierDefinitions"
      via: "snapshot test asserting 'tier2' not in tierDefinitions (xfail flipped to passing)"
      pattern: "tier2.*not in"
    - from: "ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py L169-170"
      to: "generate_baseline.py::generate_diff_report (post-deletion)"
      via: "updated assertion that the python_unmapped branch no longer fires (C4 fix)"
      pattern: "gaps.*len.*== 1|python_unmapped"
    - from: "docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json::entries == []"
      to: "runtime_coverage_summary.json::summary.deferred_total == 0"
      via: "build_coverage_summary registry_only fallback (L264-292) yields 0 deferred items when backlog is empty (Scenario E empirical proof in Plan 09a DRY-RUN-PROJECTION.md)"
      pattern: "entries.*\\[\\]"
---

<objective>
Final cleanup plan for Phase 3. Four concerns, all empirically grounded in live code reads (`tools/binding_parity_runtime_coverage.py::build_coverage_summary` and `tools/python_api_parity/generate_baseline.py::generate_diff_report`) and re-verified against the cross-AI peer review findings:

1. **Pre-deletion cascade audit (Round 1 REVIEWS #5 + Round 2 M8)**: Enumerate every reader of `tier2_gap_total`, `python_unmapped`, `rust_unmapped`, and `tierDefinitions.*tier2` via a recursive ripgrep search (NOT selective globs) covering tools/, ClassicLib-rs/, docs/, .github/, and `*.ps1` scripts. Classify each hit and record the remediation status BEFORE deletion. Write the audit to `.planning/phases/03-python-tier-collapse/03-09b-TIER2-CASCADE-AUDIT.md` as the gatekeeping artifact.

2. **Structural Tier-2 cleanup + test assertion update (Round 2 C4 + M7)**: Delete the `rust_unmapped`/`python_unmapped` gap branches in `generate_baseline.py::generate_diff_report()` (L672-708; re-verify line numbers before editing). Delete `tier2_gap_total` from the summary dict (L728). Drop the `Tier 2 Gaps` column from `render_diff_markdown()`. Delete `parity_contract.json::tierDefinitions.tier2`. **Update `ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py` L170 in the SAME commit** so the existing test that asserts `python_unmapped` exists no longer fails. Flip Plan 01's `test_tier2_definition_removed_after_plan_9` xfail decorator. Regenerate baseline + artifacts mirror AND add the `test_tier2_gap_total_removed_from_summary` test AS PART OF THIS SAME COMMIT (M7 atomic fix — prevents the bisect-breaking intermediate state where a new test reads stale `parity_diff_report.json`). Sweep inline Tier-2 comments.

3. **C3 endgame — empty deferred backlog**: Empirically verified on live code (see `03-09a-DRY-RUN-PROJECTION.md` Scenario E): `deferred_total` cannot reach 0 unless `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json::entries` is emptied. The `build_coverage_summary` `registry_only` fallback (L264-292) picks up every deferred backlog entry regardless of whether its gap row survived the baseline refresh. Therefore Plan 09b Task 3 empties the backlog entries to `[]`, preserving the file's schemaVersion+binding+entries shape. This is legitimate Phase 3 hygiene — it does not cross the Phase 6 DOC-02/DOC-04 boundary because Phase 6 owns DELETING the governance directory, not editing its contents. Phase 3 reaching `deferred_total == 0` is the PYT-06 requirement per ROADMAP L87; reaching it requires this hygiene step.

4. **Final PYT-06 verification sweep (Round 1 REVIEWS #7 + L13)**: Run `mypy --strict` in ONE command with all 19 stub paths (explicit enumeration; no globs; includes `foundation/classic-shared-py/classic_shared.pyi` because validate_stubs.py does NOT discover it per M11). Run `validate_stubs.py --fail-on-warnings` as a separate cross-check. Run the full 5-step parity gate chain. Verify `runtime_coverage_summary.json::summary.deferred_total == 0`. Run the PYT-06 coverage completeness PowerShell one-liner from VALIDATION.md. If the final gate fails for ANY reason, dump diagnostic info BEFORE `exit 1` so the operator has actionable recovery info (Claude suggestion #6).

After Plan 09b commits:
- `check_parity_gate.py --repo-root .` exits 0
- `runtime_coverage_summary.json::summary.deferred_total == 0` (Phase 3 success criterion 5)
- `mypy --strict` across all 19 `.pyi` files exits 0 (PYT-04 success criterion 3)
- `pytest ClassicLib-rs/python-bindings/tests -q` exits 0 (PYT-05 success criterion 2)
- `import classic_shared; classic_shared.get_runtime_stats(); classic_shared.is_runtime_healthy()` works (HARM-03 success criterion 4)
- `parity_contract.json::tierDefinitions` contains ONLY `tier1`
- `deferred_runtime_backlog.json::entries == []`
- Phase 3 is CLOSED; Phase 6 governance-directory deletion (DOC-02/DOC-04) is unblocked.
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
@.planning/phases/03-python-tier-collapse/03-REVIEWS.md
@.planning/phases/03-python-tier-collapse/03-08-classic-shared-and-file-io-aux-SUMMARY.md
@.planning/phases/03-python-tier-collapse/03-09a-a10-residual-promotion-PLAN.md
@./CLAUDE.md
@./AGENTS.md

<interfaces>
<!-- ============================================================================ -->
<!-- LIVE CODE CITATIONS — verified 2026-04-08 by Python REPL and source read     -->
<!-- ============================================================================ -->

<!-- A9 deletion targets — LIVE line numbers from current post-Plan-08 generate_baseline.py -->
<!-- IMPORTANT: Plan 09a may shift these by a few lines. Task 1 Step 1 RE-VERIFIES with Select-String before editing. -->

**Block 1 — gap_type=rust_unmapped loop (CURRENT L672-689, verified 2026-04-08):**
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
```

**Block 2 — gap_type=python_unmapped loop (CURRENT L691-708):**
```python
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

**Block 3 — summary dict tier2_gap_total (CURRENT L728):**
```python
    summary = {
        "tier1_contract_total": len(contract_results),
        "tier1_matched": status_counts.get("matched", 0),
        "tier1_missing_rust": status_counts.get("missing_rust", 0),
        "tier1_missing_python": status_counts.get("missing_python", 0),
        "tier1_signature_mismatch": status_counts.get("signature_mismatch", 0),
        "total_gaps": len(gaps),
        "tier1_gap_total": sum(1 for gap in gaps if gap["tier"] == "tier1"),
        "tier2_gap_total": sum(1 for gap in gaps if gap["tier"] == "tier2"),  # DELETE
    }
```

**Block 4 — render_diff_markdown Tier-2 column (CURRENT L778-784):**
```python
    lines.extend(
        (
            "",
            "## Gap Counts By Owner/Tier",
            "",
            "| Owner Module | Tier 1 Gaps | Tier 2 Gaps |",   # REMOVE " Tier 2 Gaps |"
            "|---|---:|---:|",                                 # REMOVE second "---:"
        )
    )
    for owner in _OWNER_RENDER_ORDER:
        tier_counts = diff_report["gap_counts_by_owner_tier"].get(owner, {})
        lines.append(
            f"| `{owner}` | {tier_counts.get('tier1', 0)} | {tier_counts.get('tier2', 0)} |"  # REMOVE trailing cell
        )
```

<!-- C4 test assertion fix — LIVE file: ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py L169-170 -->

```python
    assert report["gaps"][0]["gap_type"] == "tier1_missing_python"
    assert report["gaps"][1]["gap_type"] == "python_unmapped"  # <-- MUST UPDATE
```

Context: this assertion exists inside `test_generate_diff_report_flags_missing_contract_python_export_identifier`. The test builds a synthetic contract with 1 tier1Mapping that intentionally lacks a pythonExportPath, a synthetic rust_manifest with the symbol, and a synthetic python_manifest with a different unrelated export. Before Plan 09b: `generate_diff_report` produces 2 gaps (`tier1_missing_python` for the contract row + `python_unmapped` for the unrelated python export). After Plan 09b deletes the python_unmapped branch, only 1 gap is produced. Fix in the SAME commit:

```python
    assert report["gaps"][0]["gap_type"] == "tier1_missing_python"
    assert len(report["gaps"]) == 1  # Plan 9b removed python_unmapped/rust_unmapped branches
```

<!-- parity_contract.json tierDefinitions current shape -->
```json
"tierDefinitions": {
  "tier1": "Must-have Python APIs required by maintained integration workflows.",
  "tier2": "Deferred or lower-priority APIs outside initial gate scope."
}
```
After Plan 09b:
```json
"tierDefinitions": {
  "tier1": "Must-have Python APIs required by maintained integration workflows."
}
```

<!-- Plan 01 xfail decorator (LIVE: tools/python_api_parity/tests/test_check_parity_gate.py:44-57) -->
```python
@pytest.mark.xfail(
    strict=True,
    reason=(
        "tier2 definition removal lands in Plan 9b (PYT-03); this test asserts "
        "the eventual invariant. strict=True catches premature deletion by "
        "Plans 02-08 as a passing xfail failure."
    ),
)
def test_tier2_definition_removed_after_plan_9() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    tier_definitions = contract.get("tierDefinitions", {})
    assert "tier2" not in tier_definitions, (
        "Plan 9b must delete tierDefinitions.tier2 from parity_contract.json"
    )
```
Plan 09b Task 1 DELETES the `@pytest.mark.xfail(...)` decorator block (8 lines L44-51). Leaves the test function body unchanged.

<!-- VALIDATION.md PYT-06 coverage completeness one-liner (copy verbatim) -->
```powershell
$contract = Get-Content 'docs/implementation/python_api_parity/baseline/parity_contract.json' -Raw | ConvertFrom-Json
$diff = Get-Content 'docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json' -Raw | ConvertFrom-Json
$contract.tier1Mappings | Where-Object {
    $row = $_
    -not ($diff.trackedSurface | Where-Object {
        $_.trackedType -eq 'contract_row' -and $_.contractId -eq $row.id -and $_.classification -eq 'runtime_verified'
    })
} | ForEach-Object { "MISSING_RUNTIME: $($_.id) ($($_.rustSymbol) -> $($_.pythonModule).$($_.pythonExportPath))" }
```
Returns 0 output rows when complete. Any output row is a PYT-06 failure.

<!-- Full 19-stub list (explicit, not glob) for mypy --strict sweep -->
```
ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi
ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi
ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi
ClassicLib-rs/python-bindings/classic-database-py/classic_database.pyi
ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi
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
ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi
```
Exactly 19 files. The last path is under `foundation/`, the other 18 under `python-bindings/`. Per M11, validate_stubs.py at L318 only walks `python-bindings/` so it covers 18 of the 19; the foundation one is covered ONLY by the explicit mypy command in Task 4 Step 1.

<!-- C3 decisive empirical facts (verified 2026-04-08 via Python REPL) -->

Live `deferred_runtime_backlog.json::entries` contains 1,202 items as of 2026-04-08, all with classification="deferred". Scenarios tested with `build_coverage_summary`:

| Scenario | deferred_registry | diff_report.gaps | deferred_total | newly_uncovered_total | Passes gate? |
|---|---|---|---|---|---|
| A (current) | 1202 entries | all tier2 gaps (735 + file_io/shared) | 1040 | 0 | No (tier1 gaps present, but no new_uncovered) |
| B (empty) | entries: [] | same as A | 0 | 732 | NO — newly_uncovered fires |
| C (09b tier2 deletion alone) | unchanged | tier2 gaps all removed from gaps | 1008 | 0 | NO — deferred_total != 0 |
| **D (09b tier2 deletion + empty backlog)** | entries: [] | tier2 gaps all removed from gaps | **0** | **0** | **YES — all gates pass** |

Scenario D is the required endgame. Task 3 sets `deferred_registry.entries = []` to reach it. This is the EMPIRICAL PROOF that emptying the backlog is both necessary and sufficient for PYT-06 when combined with Plan 09a's promotions and Plan 09b's structural deletion.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: PRE-WORK — recursive ripgrep cascade audit covering tools/, ClassicLib-rs/, docs/, .github/, repo-root tools/*.py, and *.ps1 (M8 fix) + classify every hit + write 03-09b-TIER2-CASCADE-AUDIT.md</name>
  <files>
    .planning/phases/03-python-tier-collapse/03-09b-TIER2-CASCADE-AUDIT.md
  </files>
  <read_first>
    - tools/python_api_parity/generate_baseline.py (the primary deletion target — verify L672-708, L728, L778-784)
    - tools/python_api_parity/check_parity_gate.py (should have 0 hits after Plan 01)
    - tools/python_api_parity/tests/test_check_parity_gate.py (contains xfail test to flip in Task 2)
    - ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py (contains the L170 python_unmapped assertion — C4 fix target)
    - tools/cxx_api_parity/ (verify 0 hits per Phase 1 D-04)
    - tools/node_api_parity/generate_baseline.py (has its own rust_unmapped/python_unmapped branches — these are PHASE 4 SCOPE, NOT Phase 3; classify as OUT_OF_SCOPE_PHASE_4)
  </read_first>
  <action>
    **Step 1 — Recursive ripgrep cascade audit** (M8 fix: replace selective glob with recursive rg):
    ```powershell
    $rgPattern = 'tier2_gap_total|python_unmapped|rust_unmapped|tierDefinitions.*tier2|"tier2"'
    # Use rg via uv/pip installed or Select-String if rg unavailable. PowerShell native:
    $allHits = Get-ChildItem -Path tools\, ClassicLib-rs\python-bindings\, ClassicLib-rs\foundation\, docs\api\, docs\implementation\python_api_parity\, .github\, docs\implementation\node_api_parity\ -Recurse -File -Include *.py,*.md,*.json,*.yml,*.yaml,*.ps1 -ErrorAction SilentlyContinue | Select-String -Pattern $rgPattern -ErrorAction SilentlyContinue
    # Also include repo-root tools/*.py and *.ps1
    $rootHits = Get-ChildItem -Path .\tools\, .\ -Filter *.py -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch '\\\\[^\\\\]+\\\\[^\\\\]+\\\\' } | Select-String -Pattern $rgPattern -ErrorAction SilentlyContinue
    $rootPs1 = Get-ChildItem -Path .\ -Filter *.ps1 -ErrorAction SilentlyContinue | Select-String -Pattern $rgPattern -ErrorAction SilentlyContinue
    $all = @($allHits) + @($rootHits) + @($rootPs1)
    $total = $all.Count
    Write-Host "Total cascade hits: $total"
    $all | Group-Object Path | Sort-Object Name | ForEach-Object { Write-Host "  $($_.Name): $($_.Count) hits" }
    ```

    **Step 2 — Write `.planning/phases/03-python-tier-collapse/03-09b-TIER2-CASCADE-AUDIT.md`** with:

    ```markdown
    # Plan 09b — Tier-2 Cascade Audit (M8 recursive search)

    **Generated:** (Task 1 timestamp)
    **Search command:** `Get-ChildItem -Recurse -Include ... | Select-String -Pattern 'tier2_gap_total|python_unmapped|rust_unmapped|tierDefinitions.*tier2|"tier2"'`
    **Search scope:** tools/, ClassicLib-rs/python-bindings/, ClassicLib-rs/foundation/, docs/api/, docs/implementation/python_api_parity/, docs/implementation/node_api_parity/, .github/, repo-root tools/*.py, repo-root *.ps1
    **Total hits:** <N>

    ## Hits by file (classified)

    ### tools/python_api_parity/generate_baseline.py
    - **L672-689**: `for rust_item in rust_symbols: ... gap_type: "rust_unmapped"` — **CODE_WRITE (emission)**
      - Remediation: Task 2 Step 2 deletes the entire loop.
    - **L691-708**: `for py_item in python_exports: ... gap_type: "python_unmapped"` — **CODE_WRITE (emission)**
      - Remediation: Task 2 Step 3 deletes the entire loop.
    - **L728**: `"tier2_gap_total": sum(1 for gap in gaps if gap["tier"] == "tier2"),` — **CODE_WRITE (emission)**
      - Remediation: Task 2 Step 4 deletes the line.
    - **L778-784**: `"| Owner Module | Tier 1 Gaps | Tier 2 Gaps |"` and cell expression — **CODE_WRITE (markdown)**
      - Remediation: Task 2 Step 5 drops the column.

    ### tools/python_api_parity/tests/test_check_parity_gate.py
    - **L44-51**: `@pytest.mark.xfail(strict=True, ...)` decorator on `test_tier2_definition_removed_after_plan_9` — **TEST_DECORATOR**
      - Remediation: Task 2 Step 7 removes the decorator.

    ### ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py
    - **L170**: `assert report["gaps"][1]["gap_type"] == "python_unmapped"` — **TEST_ASSERTION (C4 fix target)**
      - Remediation: Task 2 Step 8 replaces with `assert len(report["gaps"]) == 1` in the SAME commit as the branch deletion.

    ### docs/implementation/python_api_parity/baseline/parity_contract.json
    - **tierDefinitions.tier2 key** — **CONFIG_JSON**
      - Remediation: Task 2 Step 6 deletes via json.load/del/json.dump.

    ### docs/implementation/python_api_parity/baseline/parity_diff_report.json
    - **summary.tier2_gap_total: N** — **BASELINE_JSON (auto-generated)**
      - Remediation: Task 2 Step 10 baseline refresh drops the key mechanically.

    ### docs/implementation/python_api_parity/baseline/parity_contract.md
    - **Tier-2 references in prose** — **DOCS_PROSE** (may or may not exist)
      - Remediation: Task 2 Step 10 baseline refresh regenerates the markdown (if it's auto-generated) OR Task 2 Step 11 hand-edits.

    ### docs/implementation/python_api_parity/baseline/parity_diff_report.md
    - **Tier 2 Gaps column in rendered markdown** — **BASELINE_MARKDOWN (auto-generated)**
      - Remediation: Task 2 Step 10 baseline refresh drops the column mechanically.

    ### docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json
    - **Every entry has classification="deferred"** — **GOVERNANCE_JSON**
      - Remediation: Task 3 empties entries to [] (C3 endgame). This is the EMPIRICALLY REQUIRED step to drive deferred_total to 0.

    ### docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md
    - Tier-2 references in prose — **DOCS_PROSE**
      - Remediation: OUT OF SCOPE — Phase 6 DOC-02/DOC-04 owns DELETING this entire directory. Plan 09b does NOT touch this file.

    ### docs/implementation/python_api_parity/governance/tier2_wave_manifest.json
    - Tier-2 wave manifest — **GOVERNANCE_JSON**
      - Remediation: OUT OF SCOPE — Phase 6 ownership (same as above).

    ### tools/node_api_parity/generate_baseline.py
    - **L463**: `gap_type: "rust_unmapped"` — **OUT_OF_SCOPE_PHASE_4**
    - **L511**: `"tier2_gap_total": ...` — **OUT_OF_SCOPE_PHASE_4**
      - Remediation: Phase 4 (Node Tier Collapse) owns the identical cleanup on the Node side. Plan 09b does NOT touch this file.

    ### docs/implementation/node_api_parity/**
    - All hits — **OUT_OF_SCOPE_PHASE_4**

    ### tools/cxx_api_parity/
    - Expected 0 hits per Phase 1 D-04. Confirmed by this audit: <N> hits (should be 0; if non-zero, INVESTIGATE).

    ### .github/workflows/
    - Expected 0 hits (CI does not reference tier2_gap_total directly). Confirmed: <N> hits.

    ### *.ps1 build scripts
    - Expected 0 hits. Confirmed: <N> hits.

    ## Load-bearing exclusions (DO NOT TOUCH)

    The following matches are DIFFERENT identifiers and must NOT be altered:
    - `tier1_missing_rust`, `tier1_missing_python`, `tier1_signature_mismatch` — load-bearing gate metric names
    - `tier1_gap_total` — still present in the summary dict after Task 2
    - `tier1_contract_total` — load-bearing metric
    - `"tier1"` string literal — used in parse_rust_surface tier attribution (generate_baseline.py L277, L294, etc.)
    - `"tier2"` string literal INSIDE parse_rust_surface (the tier attribution logic that runs on individual rust symbols; does NOT read the summary key) — these become dead after Task 2's gap branches are deleted, but the expressions themselves are harmless and do not need explicit removal. Sweep only what Task 2 leaves as dead COMMENTS, not as dead code expressions.

    ## Summary
    - Total hits within Phase 3 scope: <N>
    - Total hits classified OUT_OF_SCOPE_PHASE_4: <M>
    - Total hits classified OUT_OF_SCOPE_PHASE_6: <K>
    - Total load-bearing exclusions: <L>
    - Remediation in Task 2: <N - K> (everything Task 2 touches)
    - Remediation in Task 3 (governance file empty): 1 (deferred_runtime_backlog.json::entries)
    ```

    **Step 3 — Atomic commit for the audit**:
    ```powershell
    git add .planning/phases/03-python-tier-collapse/03-09b-TIER2-CASCADE-AUDIT.md
    git commit -m "Docs(03-09b): Tier-2 cascade audit (recursive ripgrep; M8 fix from REVIEWS)"
    ```
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "if (-not (Test-Path .planning/phases/03-python-tier-collapse/03-09b-TIER2-CASCADE-AUDIT.md)) { Write-Error 'audit file missing'; exit 1 }; $content = Get-Content .planning/phases/03-python-tier-collapse/03-09b-TIER2-CASCADE-AUDIT.md -Raw; if ($content -notmatch 'generate_baseline.py') { Write-Error 'audit must reference generate_baseline.py'; exit 1 }; if ($content -notmatch 'L672|L728|line 672|line 728') { Write-Error 'audit must reference deletion line numbers'; exit 1 }; if ($content -notmatch 'test_python_parity_tooling.py') { Write-Error 'audit must include C4 target test_python_parity_tooling.py'; exit 1 }; if ($content -notmatch 'L170|line 170') { Write-Error 'audit must reference C4 L170 assertion'; exit 1 }; if ($content -notmatch 'deferred_runtime_backlog.json') { Write-Error 'audit must address C3 deferred backlog'; exit 1 }; if ($content -notmatch 'OUT_OF_SCOPE_PHASE_4') { Write-Error 'audit must classify Node targets as OUT_OF_SCOPE_PHASE_4'; exit 1 }; if ($content -notmatch 'OUT_OF_SCOPE_PHASE_6|Phase 6') { Write-Error 'audit must recognize Phase 6 boundary for governance dir'; exit 1 }; if ($content -notmatch 'Load-bearing exclusions') { Write-Error 'audit must enumerate load-bearing exclusions'; exit 1 }; if ($content -notmatch 'Remediation') { Write-Error 'audit must document per-file remediation'; exit 1 }; if ($content -notmatch 'Search command|ripgrep|Select-String') { Write-Error 'audit must document the search command (M8 fix)'; exit 1 }; Write-Host 'Cascade audit valid'"</automated>
  </verify>
  <acceptance_criteria>
    - File `.planning/phases/03-python-tier-collapse/03-09b-TIER2-CASCADE-AUDIT.md` exists.
    - File documents the recursive search command used (M8 fix — NOT selective glob).
    - File references `tools/python_api_parity/generate_baseline.py` with specific line numbers (L672/L691/L728/L778).
    - File references `ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py` L170 as a C4 remediation target.
    - File references `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json` as the C3 remediation target (emptied in Task 3).
    - File classifies `tools/node_api_parity/**` and `docs/implementation/node_api_parity/**` hits as `OUT_OF_SCOPE_PHASE_4`.
    - File classifies `docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md` and `tier2_wave_manifest.json` as `OUT_OF_SCOPE_PHASE_6` (Phase 6 owns directory deletion).
    - File contains a "Load-bearing exclusions" section with at least `tier1_missing_rust`, `tier1_gap_total`, `"tier1"` string literal.
    - File records the total hit count and per-file hit counts.
    - Commit message follows convention: `Docs(03-09b): Tier-2 cascade audit (recursive ripgrep; M8 fix from REVIEWS)`.
  </acceptance_criteria>
  <done>Cascade audit complete using recursive ripgrep; every hit classified with remediation status; Task 2 has the full deletion target list including the C4 fix and Task 3 has the C3 endgame target.</done>
</task>

<task type="auto">
  <name>Task 2: ATOMIC structural cleanup — delete gap branches + tier2_gap_total + markdown column + tierDefinitions.tier2 + update test_python_parity_tooling.py L170 (C4) + flip xfail + sweep inline comments + refresh baseline + add test_tier2_gap_total_removed_from_summary — all in ONE commit (M7 fix)</name>
  <files>
    tools/python_api_parity/generate_baseline.py
    tools/python_api_parity/tests/test_check_parity_gate.py
    ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py
    docs/implementation/python_api_parity/baseline/parity_contract.json
    docs/implementation/python_api_parity/baseline/parity_contract.md
    docs/implementation/python_api_parity/baseline/parity_diff_report.json
    docs/implementation/python_api_parity/baseline/parity_diff_report.md
    docs/implementation/python_api_parity/baseline/rust_api_surface.json
    docs/implementation/python_api_parity/baseline/python_api_surface.json
    docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
    docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
    docs/implementation/python_api_parity/baseline/tier1_gate_report.md
    ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.json
    ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.md
    ClassicLib-rs/python-bindings/parity-artifacts/python_api_surface.json
    ClassicLib-rs/python-bindings/parity-artifacts/rust_api_surface.json
    ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json
    ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.md
    ClassicLib-rs/python-bindings/parity-artifacts/tier1_gate_report.md
  </files>
  <read_first>
    - .planning/phases/03-python-tier-collapse/03-09b-TIER2-CASCADE-AUDIT.md (Task 1 output — the full target list)
    - tools/python_api_parity/generate_baseline.py (read the current state; RE-VERIFY line numbers with `Select-String -Pattern 'rust_unmapped|python_unmapped|tier2_gap_total|Tier 2 Gaps'` BEFORE editing)
    - tools/python_api_parity/tests/test_check_parity_gate.py (L44-57 — xfail decorator)
    - ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py (L100-175 — the test_generate_diff_report_flags_missing_contract_python_export_identifier test that contains L170)
    - docs/implementation/python_api_parity/baseline/parity_contract.json (tierDefinitions block near the top)
  </read_first>
  <action>
    **Step 1 — Re-verify line numbers** (Plan 09a may have shifted them):
    ```powershell
    Select-String -Path tools/python_api_parity/generate_baseline.py -Pattern 'rust_unmapped|python_unmapped|tier2_gap_total|Tier 2 Gaps' | ForEach-Object { "L$($_.LineNumber): $($_.Line.Trim())" }
    ```
    Expected output (approximate; actual may differ by a few lines):
    - Lxxx: `"gap_type": "rust_unmapped",`
    - Lxxx: `"gap_type": "python_unmapped",`
    - Lxxx: `"tier2_gap_total": sum(1 for gap in gaps if gap["tier"] == "tier2"),`
    - Lxxx: `"| Owner Module | Tier 1 Gaps | Tier 2 Gaps |",`
    - Lxxx: `f"| \`{owner}\` | {tier_counts.get('tier1', 0)} | {tier_counts.get('tier2', 0)} |"`

    Use the RE-VERIFIED line numbers for the following edits.

    **Step 2 — Delete Block 1 (rust_unmapped loop)**: Find the `for rust_item in rust_symbols:` line immediately followed by `if symbol in tier1_rust_symbols: continue` and the `gaps.append({"gap_type": "rust_unmapped", ...})` call. Delete the entire ~18-line block.

    **Step 3 — Delete Block 2 (python_unmapped loop)**: Find the `for py_item in python_exports:` line immediately followed by the `pair = (...)` / `if pair in tier1_python_pairs: continue` and the `gaps.append({"gap_type": "python_unmapped", ...})` call. Delete the entire ~18-line block.

    **Step 4 — Delete tier2_gap_total from summary dict**: Find the line `"tier2_gap_total": sum(1 for gap in gaps if gap["tier"] == "tier2"),` and delete the entire line. The `summary` dict retains `tier1_contract_total`, `tier1_matched`, `tier1_missing_rust`, `tier1_missing_python`, `tier1_signature_mismatch`, `total_gaps`, `tier1_gap_total`.

    **Step 5 — Drop the Tier-2 column from render_diff_markdown()**:
    - Replace `"| Owner Module | Tier 1 Gaps | Tier 2 Gaps |"` with `"| Owner Module | Tier 1 Gaps |"`.
    - Replace `"|---|---:|---:|"` with `"|---|---:|"`.
    - Replace `f"| \`{owner}\` | {tier_counts.get('tier1', 0)} | {tier_counts.get('tier2', 0)} |"` with `f"| \`{owner}\` | {tier_counts.get('tier1', 0)} |"`.

    **Step 6 — Delete tierDefinitions.tier2 from parity_contract.json**:
    ```python
    import json
    path = "docs/implementation/python_api_parity/baseline/parity_contract.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "tier2" in data.get("tierDefinitions", {}):
        del data["tierDefinitions"]["tier2"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print("Deleted tierDefinitions.tier2")
    ```

    **Step 7 — Flip Plan 01 xfail test**: Open `tools/python_api_parity/tests/test_check_parity_gate.py`. Find the 8-line `@pytest.mark.xfail(strict=True, reason=(...))` decorator block immediately preceding `def test_tier2_definition_removed_after_plan_9() -> None:`. DELETE the entire decorator (including the trailing `)` line). Leave the test function body unchanged.

    **Step 8 — C4 fix: update test_python_parity_tooling.py L170 in the SAME commit**:

    Open `ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py` and find the function `test_generate_diff_report_flags_missing_contract_python_export_identifier` (around L123). At the end of that function (around L169-170), the assertions currently read:
    ```python
        assert report["gaps"][0]["gap_type"] == "tier1_missing_python"
        assert report["gaps"][1]["gap_type"] == "python_unmapped"
    ```
    Replace L170 with:
    ```python
        assert len(report["gaps"]) == 1, (
            "Plan 9b removed rust_unmapped / python_unmapped gap branches; "
            "only tier1_missing_python should remain for this synthetic contract"
        )
    ```
    Leave L169 (the `tier1_missing_python` assertion) unchanged.

    **Step 9 — Add test_tier2_gap_total_removed_from_summary** (in test_check_parity_gate.py, IMMEDIATELY after the flipped `test_tier2_definition_removed_after_plan_9`):
    ```python
    def test_tier2_gap_total_removed_from_summary() -> None:
        """Plan 9b A9 cleanup: tier2_gap_total is no longer emitted by generate_baseline.

        This test passes AFTER Task 2 Step 11 refreshes the baseline in the SAME commit.
        M7 fix: combining Tasks 2+3 prevents a bisect-breaking intermediate where this
        test reads a stale parity_diff_report.json with tier2_gap_total still present.
        """
        diff = json.loads(
            (REPO_ROOT / "docs" / "implementation" / "python_api_parity" / "baseline" / "parity_diff_report.json").read_text(encoding="utf-8")
        )
        assert "tier2_gap_total" not in diff["summary"], (
            "Plan 9b must remove tier2_gap_total from parity_diff_report.json::summary"
        )
    ```

    **Step 10 — Inline Tier-2 comment sweep** (run and fix any lingering comments that describe dead code):
    ```powershell
    Select-String -Path tools/python_api_parity/*.py,tools/python_api_parity/tests/*.py -Pattern '#.*[Tt]ier.?2|"""[Tt]ier.?2' -ErrorAction SilentlyContinue | ForEach-Object {
        "$($_.Path):$($_.LineNumber): $($_.Line.Trim())"
    }
    ```
    For each match: if it refers to removed concepts (tier2 branches, tier2_gap_total, tier2 backlog), DELETE or rewrite; if it's a load-bearing `tier1_` or `"tier1"` match, LEAVE UNTOUCHED.

    **Step 11 — Refresh baseline + artifacts mirror** (this step is PART OF THE SAME COMMIT as the code edits; M7 fix):
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    pwsh -ExecutionPolicy Bypass -Command "uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline"
    ```

    **Step 12 — Run the added + flipped tests to confirm green state** BEFORE committing:
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest tools/python_api_parity/tests/test_check_parity_gate.py::test_tier2_definition_removed_after_plan_9 tools/python_api_parity/tests/test_check_parity_gate.py::test_tier2_gap_total_removed_from_summary ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py::test_generate_diff_report_flags_missing_contract_python_export_identifier -v
    ```
    Expected: all three PASS. If any fails, fix the issue and re-run before committing.

    **Step 13 — SINGLE atomic commit** (M7 fix — all edits + baseline refresh + new test + updated assertion in ONE commit):
    ```powershell
    git add tools/python_api_parity/generate_baseline.py tools/python_api_parity/tests/test_check_parity_gate.py ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py docs/implementation/python_api_parity/baseline/ ClassicLib-rs/python-bindings/parity-artifacts/
    git commit -m "Refactor(03-09b): Delete Tier-2 gap branches + tier2_gap_total + tierDefinitions.tier2 + fix C4 test assertion + flip xfail + refresh baseline (atomic per M7)"
    ```
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "$gb = Get-Content tools/python_api_parity/generate_baseline.py -Raw; if ($gb -match 'rust_unmapped') { Write-Error 'generate_baseline.py still contains rust_unmapped'; exit 1 }; if ($gb -match 'python_unmapped') { Write-Error 'generate_baseline.py still contains python_unmapped'; exit 1 }; if ($gb -match 'tier2_gap_total') { Write-Error 'generate_baseline.py still contains tier2_gap_total'; exit 1 }; if ($gb -match 'Tier 2 Gaps') { Write-Error 'generate_baseline.py still contains Tier 2 Gaps column'; exit 1 }; if ($gb -match 'tier_counts\.get\\(.tier2') { Write-Error 'generate_baseline.py still contains tier2 markdown cell expression'; exit 1 }; $c = Get-Content docs/implementation/python_api_parity/baseline/parity_contract.json -Raw | ConvertFrom-Json; if ($c.tierDefinitions.PSObject.Properties.Name -contains 'tier2') { Write-Error 'parity_contract.json still contains tierDefinitions.tier2'; exit 1 }; $t = Get-Content tools/python_api_parity/tests/test_check_parity_gate.py -Raw; if ($t -match '@pytest\\.mark\\.xfail[^)]*test_tier2_definition_removed') { Write-Error 'xfail decorator still present on test_tier2_definition_removed_after_plan_9'; exit 1 }; if ($t -notmatch 'test_tier2_gap_total_removed_from_summary') { Write-Error 'new test_tier2_gap_total_removed_from_summary not added'; exit 1 }; $tp = Get-Content ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py -Raw; if ($tp -match 'report..gaps...1...gap_type. == .python_unmapped') { Write-Error 'C4 fix not applied: L170 python_unmapped assertion still present'; exit 1 }; if ($tp -notmatch 'len\\(report..gaps..\\) == 1') { Write-Error 'C4 fix incomplete: len() assertion missing'; exit 1 }; $diff = Get-Content docs/implementation/python_api_parity/baseline/parity_diff_report.json -Raw | ConvertFrom-Json; if ($diff.summary.PSObject.Properties.Name -contains 'tier2_gap_total') { Write-Error 'parity_diff_report.json::summary still contains tier2_gap_total after refresh'; exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest tools/python_api_parity/tests/test_check_parity_gate.py::test_tier2_definition_removed_after_plan_9 tools/python_api_parity/tests/test_check_parity_gate.py::test_tier2_gap_total_removed_from_summary ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py::test_generate_diff_report_flags_missing_contract_python_export_identifier -v; if ($LASTEXITCODE -ne 0) { Write-Error 'Task 2 test trio failed'; exit 1 }; Write-Host 'Task 2 OK (atomic M7 + C4 fix verified)'"</automated>
  </verify>
  <acceptance_criteria>
    - `tools/python_api_parity/generate_baseline.py` does NOT contain `rust_unmapped`, `python_unmapped`, `tier2_gap_total`, `Tier 2 Gaps`, or `tier_counts.get('tier2', 0)`.
    - `docs/implementation/python_api_parity/baseline/parity_contract.json::tierDefinitions` does NOT contain a `tier2` key.
    - `docs/implementation/python_api_parity/baseline/parity_diff_report.json::summary` does NOT contain `tier2_gap_total` (verified via ConvertFrom-Json property check).
    - `tools/python_api_parity/tests/test_check_parity_gate.py::test_tier2_definition_removed_after_plan_9` does NOT have a `@pytest.mark.xfail` decorator.
    - `tools/python_api_parity/tests/test_check_parity_gate.py` contains a new function `def test_tier2_gap_total_removed_from_summary() -> None:`.
    - `ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py` L170 area contains `assert len(report["gaps"]) == 1` (C4 fix) and does NOT contain `report["gaps"][1]["gap_type"] == "python_unmapped"`.
    - Running the test trio `test_tier2_definition_removed_after_plan_9 + test_tier2_gap_total_removed_from_summary + test_generate_diff_report_flags_missing_contract_python_export_identifier` exits 0.
    - Both `docs/implementation/python_api_parity/baseline/` and `ClassicLib-rs/python-bindings/parity-artifacts/` are refreshed in the same commit.
    - Commit message: `Refactor(03-09b): Delete Tier-2 gap branches + tier2_gap_total + tierDefinitions.tier2 + fix C4 test assertion + flip xfail + refresh baseline (atomic per M7)`.
    - The commit contains exactly ONE commit (not a sequence) per M7 fix — no bisect-breaking intermediate state.
  </acceptance_criteria>
  <done>All structural Tier-2 code + test updates + baseline refresh committed atomically; C4 fix applied; M7 atomicity preserved.</done>
</task>

<task type="auto">
  <name>Task 3: C3 ENDGAME — empty deferred_runtime_backlog.json::entries + refresh baseline + verify deferred_total == 0</name>
  <files>
    docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json
    docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
    docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
    ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json
    ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.md
  </files>
  <read_first>
    - tools/binding_parity_runtime_coverage.py L221-330 (build_coverage_summary — specifically L264-292 registry_only fallback that drives the need for this step)
    - docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json (current state; 1,202 entries expected)
    - .planning/phases/03-python-tier-collapse/03-09a-DRY-RUN-PROJECTION.md (scenarios A-D: only Scenario D with entries=[] + tier2 branches deleted yields deferred_total=0)
    - .planning/phases/03-python-tier-collapse/03-09a-a10-residual-promotion-SUMMARY.md (specifically the "POST-09a deferred_total" number)
  </read_first>
  <action>
    **Step 1 — Empty the backlog entries** (C3 endgame; legitimate Phase 3 hygiene):
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "
import json
from pathlib import Path
p = Path('docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json')
data = json.loads(p.read_text(encoding='utf-8'))
old_count = len(data.get('entries', []))
print(f'Current entries: {old_count}')
data['entries'] = []
p.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
print(f'Emptied entries (was {old_count}, now 0)')
print('Preserved: schemaVersion, binding, any other top-level keys')
for k in sorted(data.keys()):
    print(f'  {k}: {type(data[k]).__name__}')
"
    ```

    **Step 2 — Refresh baseline + artifacts mirror** (so runtime_coverage_summary.json reflects the empty-backlog state):
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    pwsh -ExecutionPolicy Bypass -Command "uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline"
    ```

    **Step 3 — Verify deferred_total is now 0**:
    ```powershell
    $summary = Get-Content 'docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json' -Raw | ConvertFrom-Json
    Write-Host "POST-C3 METRICS:"
    Write-Host "  deferred_total: $($summary.summary.deferred_total)"
    Write-Host "  newly_uncovered_total: $($summary.summary.newly_uncovered_total)"
    Write-Host "  tier1_missing_runtime_total: $($summary.summary.tier1_missing_runtime_total)"
    Write-Host "  registry_mismatch_total: $($summary.summary.registry_mismatch_total)"
    if ($summary.summary.deferred_total -ne 0) {
        # DIAGNOSTIC DUMP per Claude suggestion #6 — BEFORE exit 1
        Write-Host "`n=== DIAGNOSTIC DUMP: stuck deferred items ==="
        $stuck = $summary.trackedSurface | Where-Object { $_.classification -eq 'deferred' }
        $stuck | ForEach-Object { Write-Host "  STUCK: trackedId=$($_.trackedId) owner=$($_.ownerModule) rustSymbol=$($_.rustSymbol)" }
        Write-Error "C3 FAILED: deferred_total = $($summary.summary.deferred_total), expected 0. Something other than deferred_runtime_backlog.json is contributing — investigate."
        exit 1
    }
    if ($summary.summary.newly_uncovered_total -ne 0) {
        Write-Error "C3 FAILED: newly_uncovered_total = $($summary.summary.newly_uncovered_total). This means emptying the backlog caused tier2 gaps to reclassify — Plan 09b Task 2 tier2 branch deletion did not fire."
        exit 1
    }
    Write-Host "C3 ENDGAME: deferred_total = 0, newly_uncovered_total = 0"
    ```

    **Step 4 — Atomic commit**:
    ```powershell
    git add docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json docs/implementation/python_api_parity/baseline/ ClassicLib-rs/python-bindings/parity-artifacts/
    git commit -m "Chore(03-09b): C3 endgame — empty deferred_runtime_backlog.json::entries + refresh baseline; deferred_total=0"
    ```
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "$b = Get-Content docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json -Raw | ConvertFrom-Json; if ($b.entries.Count -ne 0) { Write-Error \"entries should be empty, got $($b.entries.Count)\"; exit 1 }; if (-not $b.PSObject.Properties.Name -contains 'schemaVersion') { Write-Error 'schemaVersion key should be preserved'; exit 1 }; $s = Get-Content docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json -Raw | ConvertFrom-Json; if ($s.summary.deferred_total -ne 0) { Write-Error \"deferred_total must be 0, got $($s.summary.deferred_total)\"; exit 1 }; if ($s.summary.newly_uncovered_total -ne 0) { Write-Error \"newly_uncovered_total must be 0, got $($s.summary.newly_uncovered_total)\"; exit 1 }; Write-Host 'Task 3 OK: deferred_total=0, newly_uncovered_total=0'"</automated>
  </verify>
  <acceptance_criteria>
    - `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json::entries` is an empty array `[]`.
    - The file's top-level `schemaVersion` and `binding` keys are preserved (file shape is intact; only entries cleared).
    - `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json::summary.deferred_total == 0`.
    - `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json::summary.newly_uncovered_total == 0` (if this fails, Task 2 did not correctly delete the tier2 branches; Task 3 cannot proceed without Task 2 being correct).
    - `ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json` is refreshed to match.
    - Commit message: `Chore(03-09b): C3 endgame — empty deferred_runtime_backlog.json::entries + refresh baseline; deferred_total=0`.
  </acceptance_criteria>
  <done>C3 endgame achieved: deferred backlog emptied; deferred_total == 0 empirically verified via live gate artifact; runtime_coverage_summary.md reports 0 deferred.</done>
</task>

<task type="auto">
  <name>Task 4: Final PYT-06 verification sweep — single-command mypy --strict across all 19 .pyi files (L13) + validate_stubs.py + 5-step chain + deferred_total == 0 + PYT-06 coverage completeness one-liner + diagnostic dump on failure</name>
  <files>
    .planning/phases/03-python-tier-collapse/03-09b-tier2-cleanup-and-final-sweep-SUMMARY.md
  </files>
  <read_first>
    - .planning/phases/03-python-tier-collapse/03-VALIDATION.md (the PYT-06 coverage completeness PowerShell one-liner at "## Coverage Completeness Criterion" — copy verbatim)
    - All 19 .pyi files enumerated in the <interfaces> block (verify existence before running mypy; missing file = plan failure)
    - .planning/phases/03-python-tier-collapse/03-09a-a10-residual-promotion-SUMMARY.md (cross-check the post-09a tier1Mappings count against the post-09b count — they should be equal because 09b does NOT add contract rows, only deletes non-contract branches)
  </read_first>
  <action>
    **Step 1 — Final mypy --strict sweep across ALL 19 .pyi files in ONE command** (L13 fix: single run catches cross-stub type references; per-file foreach does not):
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
    if ($stubs.Count -ne 19) { Write-Error "Expected exactly 19 stubs, got $($stubs.Count)"; exit 1 }
    foreach ($stub in $stubs) {
        if (-not (Test-Path $stub)) { Write-Error "Missing stub: $stub"; exit 1 }
    }
    # L13 fix: single mypy invocation with all 19 files as arguments (catches cross-stub refs)
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict @stubs
    if ($LASTEXITCODE -ne 0) { Write-Error "mypy --strict FAILED on the 19-stub sweep"; exit 1 }
    Write-Host "All 19 .pyi files passed mypy --strict in single invocation (L13 fix)"
    ```

    **Step 2 — validate_stubs.py cross-check** (covers 18 of 19; classic_shared already covered by Step 1):
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings
    if ($LASTEXITCODE -ne 0) { Write-Error "validate_stubs.py failed"; exit 1 }
    Write-Host "validate_stubs.py: 0 errors, 0 warnings (18 python-bindings crates)"
    ```

    **Step 3 — Full 5-step plan-close verification chain**:
    ```powershell
    # Step 3a: Parity gate
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python tools/python_api_parity/check_parity_gate.py --repo-root .
    if ($LASTEXITCODE -ne 0) { Write-Error "Step 3a FAILED"; exit 1 }

    # Step 3b: validate_stubs (re-run as part of formal chain; already passed in Step 2)
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings
    if ($LASTEXITCODE -ne 0) { Write-Error "Step 3b FAILED"; exit 1 }

    # Step 3c: Wheel rebuild for all 19 owners
    pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
    if ($LASTEXITCODE -ne 0) { Write-Error "Step 3c FAILED"; exit 1 }

    # Step 3d: Full test suite
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests tools/python_api_parity/tests -q
    if ($LASTEXITCODE -ne 0) { Write-Error "Step 3d FAILED"; exit 1 }

    # Step 3e: mypy --strict already completed in Step 1
    Write-Host "5-step chain GREEN"
    ```

    **Step 4 — PYT-06 deferred_total assertion + diagnostic dump on failure** (Claude suggestion #6):
    ```powershell
    $summary = Get-Content 'docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json' -Raw | ConvertFrom-Json
    Write-Host "POST-09b METRICS:"
    Write-Host "  tier1_contract_total: $($summary.summary.tier1_contract_total)"
    Write-Host "  deferred_total: $($summary.summary.deferred_total)"
    Write-Host "  newly_uncovered_total: $($summary.summary.newly_uncovered_total)"
    Write-Host "  tier1_missing_runtime_total: $($summary.summary.tier1_missing_runtime_total)"
    Write-Host "  registry_mismatch_total: $($summary.summary.registry_mismatch_total)"
    if ($summary.summary.deferred_total -ne 0) {
        Write-Host "`n=== DIAGNOSTIC DUMP: stuck deferred items ==="
        $stuck = @($summary.trackedSurface | Where-Object { $_.classification -eq 'deferred' })
        Write-Host "Total stuck deferred items: $($stuck.Count)"
        $stuck | Select-Object -First 20 | ForEach-Object {
            Write-Host "  STUCK: trackedId=$($_.trackedId) trackedType=$($_.trackedType) owner=$($_.ownerModule) rustSymbol=$($_.rustSymbol) bindingIdentifier=$($_.bindingIdentifier)"
        }
        if ($stuck.Count -gt 20) { Write-Host "  ... and $($stuck.Count - 20) more" }
        Write-Error "PYT-06 FAILED: deferred_total = $($summary.summary.deferred_total), expected 0. See diagnostic dump above for which items are stuck."
        exit 1
    }
    if ($summary.summary.tier1_missing_runtime_total -ne 0) { Write-Error "PYT-06 FAILED: tier1_missing_runtime_total != 0"; exit 1 }
    if ($summary.summary.registry_mismatch_total -ne 0) { Write-Error "PYT-06 FAILED: registry_mismatch_total != 0"; exit 1 }
    if ($summary.summary.newly_uncovered_total -ne 0) { Write-Error "PYT-06 FAILED: newly_uncovered_total != 0"; exit 1 }
    Write-Host "PYT-06 SATISFIED: deferred_total = 0, newly_uncovered_total = 0, tier1_missing_runtime_total = 0, registry_mismatch_total = 0"
    ```

    **Step 5 — PYT-06 coverage completeness PowerShell one-liner** (copy verbatim from VALIDATION.md):
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
        Write-Host "MISSING runtime coverage for $($missing.Count) rows:"
        $missing[0..([Math]::Min(9, $missing.Count - 1))] | ForEach-Object {
            Write-Host "  MISSING_RUNTIME: $($_.id) ($($_.rustSymbol) -> $($_.pythonModule).$($_.pythonExportPath))"
        }
        Write-Error "PYT-06 coverage completeness FAILED"
        exit 1
    }
    Write-Host "PYT-06 coverage completeness: all $($contract.tier1Mappings.Count) tier1Mappings have runtime coverage"
    ```

    **Step 6 — Write SUMMARY.md and final atomic commit**:
    ```powershell
    git add .planning/phases/03-python-tier-collapse/03-09b-tier2-cleanup-and-final-sweep-SUMMARY.md
    git commit -m "Docs(03-09b): Plan 09b SUMMARY — Phase 3 closed, deferred_total=0, all 19 stubs mypy clean"
    ```
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "$stubs = @('ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi','ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi','ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi','ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi','ClassicLib-rs/python-bindings/classic-database-py/classic_database.pyi','ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi','ClassicLib-rs/python-bindings/classic-scangame-py/classic_scangame.pyi','ClassicLib-rs/python-bindings/classic-registry-py/classic_registry.pyi','ClassicLib-rs/python-bindings/classic-perf-py/classic_perf.pyi','ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi','ClassicLib-rs/python-bindings/classic-message-py/classic_message.pyi','ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi','ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi','ClassicLib-rs/python-bindings/classic-version-py/classic_version.pyi','ClassicLib-rs/python-bindings/classic-resource-py/classic_resource.pyi','ClassicLib-rs/python-bindings/classic-xse-py/classic_xse.pyi','ClassicLib-rs/python-bindings/classic-web-py/classic_web.pyi','ClassicLib-rs/python-bindings/classic-update-py/classic_update.pyi','ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi'); if ($stubs.Count -ne 19) { exit 1 }; foreach ($s in $stubs) { if (-not (Test-Path $s)) { Write-Error \"Missing $s\"; exit 1 } }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict @stubs; if ($LASTEXITCODE -ne 0) { Write-Error 'mypy --strict single-invocation failed'; exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python tools/python_api_parity/check_parity_gate.py --repo-root .; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests tools/python_api_parity/tests -q; if ($LASTEXITCODE -ne 0) { exit 1 }; $s = Get-Content docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json -Raw | ConvertFrom-Json; if ($s.summary.deferred_total -ne 0) { Write-Error \"deferred_total=$($s.summary.deferred_total), expected 0\"; exit 1 }; if ($s.summary.newly_uncovered_total -ne 0) { exit 1 }; if ($s.summary.tier1_missing_runtime_total -ne 0) { exit 1 }; if ($s.summary.registry_mismatch_total -ne 0) { exit 1 }; Write-Host 'Plan 09b all acceptance criteria met; Phase 3 CLOSED'"</automated>
  </verify>
  <acceptance_criteria>
    - All 19 .pyi files exist at the exact paths listed in <interfaces> (NOT glob; explicit enumeration).
    - `mypy --strict @stubs` SINGLE command with all 19 paths passed as arguments exits 0 (L13 fix).
    - `validate_stubs.py --fail-on-warnings` exits 0 (M11: 18 of 19 stubs; classic_shared coverage is from mypy Step 1).
    - `check_parity_gate.py --repo-root .` exits 0.
    - `rebuild_rust.ps1 -Target python` exits 0.
    - `pytest ClassicLib-rs/python-bindings/tests tools/python_api_parity/tests -q` exits 0.
    - `runtime_coverage_summary.json::summary.deferred_total == 0` (C3 endgame + PYT-06 primary gate).
    - `runtime_coverage_summary.json::summary.newly_uncovered_total == 0`.
    - `runtime_coverage_summary.json::summary.tier1_missing_runtime_total == 0`.
    - `runtime_coverage_summary.json::summary.registry_mismatch_total == 0`.
    - PYT-06 coverage completeness PowerShell one-liner returns 0 missing rows.
    - `parity_diff_report.json::summary` does NOT contain `tier2_gap_total`.
    - `parity_contract.json::tierDefinitions` contains ONLY `tier1`.
    - `test_tier2_definition_removed_after_plan_9` passes without xfail decorator.
    - `test_tier2_gap_total_removed_from_summary` passes.
    - `test_generate_diff_report_flags_missing_contract_python_export_identifier` passes with the updated `len(report["gaps"]) == 1` assertion (C4 fix).
    - If `deferred_total != 0`, the failure path prints a diagnostic dump of stuck items before exit 1 (Claude suggestion #6).
    - Commit message follows convention: `Docs(03-09b): Plan 09b SUMMARY — Phase 3 closed, deferred_total=0, all 19 stubs mypy clean`.
  </acceptance_criteria>
  <done>Phase 3 CLOSED. All 19 stubs mypy clean. deferred_total = 0. PYT-06 satisfied. Phase 6 DOC-02/DOC-04 governance deletion unblocked.</done>
</task>

</tasks>

<verification>
Plan 09b final verification = Phase 3 close-out gate:

1. `uv run ... python tools/python_api_parity/check_parity_gate.py --repo-root .` — exit 0
2. `uv run ... python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings` — exit 0
3. `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python` — exit 0 (all 19 wheels)
4. `uv run ... python -m pytest ClassicLib-rs/python-bindings/tests tools/python_api_parity/tests -q` — exit 0
5. `uv run ... mypy --strict @stubs` (single command, 19 files) — exit 0

PLUS PYT-06 gates:
- `runtime_coverage_summary.json::summary.deferred_total == 0` (Phase 3 success criterion 5, ROADMAP L87)
- PYT-06 coverage completeness PowerShell one-liner returns 0 missing rows (VALIDATION.md §Coverage Completeness Criterion)

PLUS structural assertions:
- `tools/python_api_parity/generate_baseline.py` contains NO `rust_unmapped` / `python_unmapped` / `tier2_gap_total` / `Tier 2 Gaps` / `tier_counts.get('tier2', 0)` literals
- `parity_contract.json::tierDefinitions` contains ONLY `tier1`
- `parity_diff_report.json::summary` does NOT contain `tier2_gap_total`
- `deferred_runtime_backlog.json::entries == []`
- Plan 01's `test_tier2_definition_removed_after_plan_9` passes without an xfail decorator
- `test_tier2_gap_total_removed_from_summary` exists and passes
- `test_python_parity_tooling.py::test_generate_diff_report_flags_missing_contract_python_export_identifier` passes with updated `len(gaps) == 1` assertion (C4 fix)
</verification>

<success_criteria>
- Recursive cascade audit captured in `03-09b-TIER2-CASCADE-AUDIT.md` using ripgrep (M8 fix)
- Tier-2 gap branches deleted from `generate_baseline.py::generate_diff_report()`
- `tier2_gap_total` summary key deleted
- `Tier 2 Gaps` column removed from `render_diff_markdown()`
- `parity_contract.json::tierDefinitions.tier2` deleted
- `test_python_parity_tooling.py` L170 updated to match post-deletion state (C4 fix) — SAME commit as the branch deletion
- Plan 01 xfail flipped
- Task 2 and baseline refresh + new test in SINGLE atomic commit (M7 fix — no bisect-breaking intermediate)
- C3 endgame: `deferred_runtime_backlog.json::entries == []` (Task 3)
- Final mypy --strict sweep across ALL 19 explicit .pyi paths in ONE command (L13 fix) exits 0
- validate_stubs.py --fail-on-warnings cross-check passes
- 5-step verification chain exits 0
- PYT-06 satisfied: `runtime_coverage_summary.json::summary.deferred_total == 0` AND coverage completeness one-liner returns 0 missing rows
- On failure, diagnostic dump of stuck deferred items prints BEFORE exit 1 (Claude suggestion #6)
- Phase 3 CLOSED; Phase 6 DOC-02/DOC-04 governance directory deletion unblocked
</success_criteria>

<output>
Create `.planning/phases/03-python-tier-collapse/03-09b-tier2-cleanup-and-final-sweep-SUMMARY.md` with:

- **Files modified** — final list from git log
- **Cascade audit results** — total hits, classification breakdown, per-file remediation status
- **Structural deletions** — exact before/after line counts for generate_baseline.py's gap branches, summary dict, render_diff_markdown
- **C4 fix** — confirmation that `test_python_parity_tooling.py` L170 was updated in the SAME commit as the branch deletion
- **C3 endgame** — confirmation that `deferred_runtime_backlog.json::entries` was emptied in Task 3, and the empirical drop from (post-09a deferred_total recorded in 09a SUMMARY) to 0 in the post-Task-3 runtime_coverage_summary.json
- **Final tier1Mappings.length** — should equal post-09a count (09b does not add rows)
- **5-step verification chain** — exit code table
- **PYT-06 evidence**:
  - `runtime_coverage_summary.json::summary.deferred_total` value = 0
  - PYT-06 coverage completeness one-liner output = 0 missing rows
  - `runtime_coverage_summary.json::summary` full payload snapshot
- **mypy --strict 19-stub sweep results** — single-command output (L13 fix)
- **Plan 01 xfail flip confirmation** — `test_tier2_definition_removed_after_plan_9` passes without decorator
- **test_tier2_gap_total_removed_from_summary** — new test passes
- **Phase 3 close-out notes**:
  - All 5 ROADMAP Phase 3 success criteria verified
  - All 8 Phase 3 requirement IDs (PYT-01..PYT-06, HARM-03, HARM-04) marked complete
  - Phase 6 DOC-02/DOC-04 governance directory deletion is unblocked
  - REVIEWS.md Round 2 CRITICAL findings C1-C4 all structurally resolved
  - REVIEWS.md Round 2 HIGH findings H5-H6 all addressed in Plan 09a
  - REVIEWS.md Round 2 MEDIUM findings M7-M12 addressed (with M12 in 09a Task 3)
  - REVIEWS.md Round 2 LOW findings L13-L15 addressed (L13 L15 in 09b; L14 in 09a SUMMARY)
  - Any carry-over concerns — expected NONE
</output>
