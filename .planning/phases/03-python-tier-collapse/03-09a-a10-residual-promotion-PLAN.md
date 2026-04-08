---
phase: 03-python-tier-collapse
plan: 09a
type: execute
wave: 9
depends_on: [03-01, 03-02, 03-03, 03-04, 03-05, 03-06, 03-07, 03-08]
files_modified:
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
  - ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi
  - ClassicLib-rs/python-bindings/classic-database-py/classic_database.pyi
  - ClassicLib-rs/python-bindings/classic-scangame-py/classic_scangame.pyi
  - ClassicLib-rs/python-bindings/classic-registry-py/classic_registry.pyi
  - ClassicLib-rs/python-bindings/classic-perf-py/classic_perf.pyi
  - ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi
  - ClassicLib-rs/python-bindings/classic-message-py/classic_message.pyi
  - ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi
  - ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi
  - ClassicLib-rs/python-bindings/classic-version-py/classic_version.pyi
  - ClassicLib-rs/python-bindings/classic-resource-py/classic_resource.pyi
  - ClassicLib-rs/python-bindings/classic-xse-py/classic_xse.pyi
  - ClassicLib-rs/python-bindings/classic-web-py/classic_web.pyi
  - ClassicLib-rs/python-bindings/classic-update-py/classic_update.pyi
  - ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py
autonomous: true
requirements: [PYT-02, PYT-04, PYT-05, PYT-06]
must_haves:
  truths:
    - "A10 residuals are sourced FRESH from parity_diff_report.json (gaps field — NOT rust_api_surface.json as the old Plan 09 erroneously specified); each residual has gap_type in {rust_unmapped, python_unmapped} with tier == 'tier2'"
    - "Plan 09a explicitly EXCLUDES classic-file-io-core / file_io owner from residual scanning — Plan 08 owns ALL file_io contract rows including any discovered residuals (R3 Plan 08/09 coordination)"
    - "Fail-closed residual handling: if ANY residual symbol has no corresponding -py wrapper, Plan 09a STOPS, writes PLAN-09a-BLOCKERS.md with the exact wrapper-less symbol list, and exits without silently skipping"
    - "For every residual symbol with an existing -py wrapper: one contract row authored + stub updated + per-class smoke test added in the same atomic commit"
    - "runtime_coverage_registry.json gains one python-tier1-<owner> selector entry per owner module receiving residual rows"
    - "5-step verification chain exits 0 at plan close"
  artifacts:
    - path: "docs/implementation/python_api_parity/baseline/parity_contract.json"
      provides: "tier1Mappings.length = 358 + (verified residual count from parity_diff_report.json::gaps, excluding file_io) — R9 propagation: Plan 08 ends at 358, not 359"
    - path: "ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py"
      provides: "Per-class smoke tests for each promoted residual #[pyclass] across the 14 residual-receiving owner modules"
      min_lines: 60
  key_links:
    - from: "test_promoted_residuals_smoke.py"
      to: "newly-promoted residual contract rows"
      via: "import classic_<owner>; Class(); method()"
      pattern: "import classic_(yaml|database|scangame|registry|perf|settings|message|path|constants|version|resource|xse|web|update)"
---

<objective>
Promote A10 residual rows — newly-surfaced symbols from the 14 currently-untracked crates (excluding file_io, which Plan 08 owns) discovered after Plan 1's `RUST_TARGET_CRATES` expansion and all subsequent promotions (Plans 02-08). Use FRESH data from `parity_diff_report.json::gaps` filtered by `tier == 'tier2'`, NOT the stale Plan 1 snapshot or `rust_api_surface.json`.

Per the locked architectural decision (Option C from review divergence), Plan 09a is FAIL-CLOSED:
- Any residual symbol without a matching `-py` wrapper STOPS the plan and produces `PLAN-09a-BLOCKERS.md` with the blocker list
- No "Phase 6 follow-up" silent skips
- The plan either (a) promotes every residual OR (b) exits with a blocker list requiring user intervention

Plan 09a is split from the old single Plan 09 per the review consensus recommendation. The structural cleanup (deleting tier2 gap branches in generate_baseline.py, removing tierDefinitions.tier2, flipping the xfail test) is isolated in the follow-on Plan 09b.

Output:
- Fresh residual discovery from `parity_diff_report.json::gaps`
- Grouped-by-owner contract row additions (excluding file_io)
- Per-owner `.pyi` stub updates for residual rows
- New `test_promoted_residuals_smoke.py` with one test per promoted #[pyclass]
- New `python-tier1-<owner>` selector entries in `runtime_coverage_registry.json`
- OR: `PLAN-09a-BLOCKERS.md` with the wrapper-less symbol list and STOP
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
@./AGENTS.md

<interfaces>
<!-- Residual source: parity_diff_report.json::gaps (NOT rust_api_surface.json) -->

From tools/python_api_parity/generate_baseline.py::generate_diff_report() (VERIFIED lines 574-610):
The diff report contains a `gaps` list (not `gap_rows`). Each entry has shape:
```json
{
  "gap_type": "rust_unmapped" | "python_unmapped" | "tier1_missing_rust" | ...,
  "tier": "tier1" | "tier2",
  "owner_module": "yaml" | "database" | ...,
  "rust_symbol": "SomeType",
  "python_module": "classic_yaml" | null,
  "python_export": "SomeType" | null,
  "crate": "classic-yaml-core",
  "kind": "struct" | "enum" | "function"
}
```
Filter `gaps` where `tier == "tier2"` AND `owner_module != "file_io"` (Plan 08 owns file_io). These are the residual promotion candidates.

<!-- Wrapper existence check -->

For each residual symbol, the executor must verify a corresponding -py wrapper exists by grepping `ClassicLib-rs/python-bindings/classic-<owner>-py/src/**/*.rs` for `#[pyclass]` with a matching rename OR for a `#[pyfunction]`. If no wrapper exists, the symbol goes to PLAN-09a-BLOCKERS.md.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Discover fresh A10 residuals from parity_diff_report.json::gaps (NOT rust_api_surface.json); fail-closed on wrapper-less symbols</name>
  <files>
    .planning/phases/03-python-tier-collapse/03-09a-residual-inventory.md
  </files>
  <read_first>
    - docs/implementation/python_api_parity/baseline/parity_diff_report.json (post-Plan-08 state — the gaps list is the source of truth)
    - tools/python_api_parity/generate_baseline.py (lines 574-610 — confirm the gap_type values used for residuals: "rust_unmapped" and "python_unmapped")
    - Every ClassicLib-rs/python-bindings/classic-*-py/src/**/*.rs file (to grep for #[pyclass] / #[pyfunction] matching each residual)
  </read_first>
  <action>
    Step 1: Run `generate_baseline.py --write-baseline` to ensure `parity_diff_report.json` reflects the post-Plan-08 state. Then read `parity_diff_report.json::gaps` and filter:
    ```python
    residuals = [
        g for g in diff['gaps']
        if g['tier'] == 'tier2'
        and g['owner_module'] != 'file_io'  # Plan 08 owns file_io
        and g['gap_type'] in ('rust_unmapped', 'python_unmapped')
    ]
    ```

    Step 2: Group residuals by `owner_module`. Record each residual as `(owner, symbol, rust_path, gap_type, crate)`.

    Step 3: For each residual, verify wrapper existence:
    ```python
    # Pseudocode for the wrapper-existence check
    for residual in residuals:
        owner = residual['owner_module']
        symbol = residual['rust_symbol'] or residual['python_export']
        py_crate_dir = f"ClassicLib-rs/python-bindings/classic-{owner.replace('_', '-')}-py/src"
        # Grep for #[pyclass] or #[pyfunction] that matches this symbol (allowing Py prefix)
        wrapper_exists = grep_for_pyclass_or_pyfunction(py_crate_dir, symbol)
        if not wrapper_exists:
            blockers.append(residual)
    ```

    Step 4: If `len(blockers) > 0`:
      - Write `PLAN-09a-BLOCKERS.md` with the exact wrapper-less symbol list, grouped by owner
      - STOP the plan with an error message: "Plan 09a BLOCKED: N residual symbols have no -py wrapper. See PLAN-09a-BLOCKERS.md. Options: (1) add the wrappers manually and re-run Plan 09a, (2) split a new closure plan (Plan 09c) to author the wrappers, OR (3) document the symbols as genuinely internal (update classic-crashgen-settings-core-style exclusion list)."
      - Exit code 1
      - Do NOT proceed to Tasks 2-4

    Step 5: If `len(blockers) == 0`:
      - Write `03-09a-residual-inventory.md` with the full residual list grouped by owner module
      - Each entry: (symbol, rust_path, python_export_path derived from wrapper, kind)
      - Proceed to Task 2
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import json, pathlib; p = pathlib.Path('.planning/phases/03-python-tier-collapse/03-09a-residual-inventory.md'); b = pathlib.Path('.planning/phases/03-python-tier-collapse/PLAN-09a-BLOCKERS.md'); assert p.exists() or b.exists(), 'Either inventory or blockers file MUST exist'; print('OK: inventory={}, blockers={}'.format(p.exists(), b.exists()))"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_diff_report.json::gaps` read fresh (not from stale Plan 01 snapshot)
    - Every residual grouped by owner module (excluding file_io)
    - Each residual checked for wrapper existence via grep of `ClassicLib-rs/python-bindings/classic-*-py/src/**/*.rs`
    - EITHER: `03-09a-residual-inventory.md` exists with all residuals having wrappers (proceed to Task 2)
    - OR: `PLAN-09a-BLOCKERS.md` exists with wrapper-less symbols AND Plan 09a STOPS before Task 2 (fail-closed; no silent skip to Phase 6)
  </acceptance_criteria>
  <done>Fresh residual inventory captured; wrapper existence verified; plan either proceeds or fails closed with blocker list.</done>
</task>

<task type="auto">
  <name>Task 2: Author contract rows + stub updates + per-class smoke tests for residuals, grouped by owner module</name>
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
  </files>
  <read_first>
    - .planning/phases/03-python-tier-collapse/03-09a-residual-inventory.md (from Task 1)
    - Each owner's `-py/src/**/*.rs` files for the wrappers matching inventory entries (exact `#[pymethods] fn new` signatures before authoring tests)
  </read_first>
  <action>
    Step 1: For each owner-module group in the inventory:
      - Author one tier1Mapping row per residual symbol (shape matches Plans 02-08)
      - Add stub entries to the corresponding `classic_<owner>.pyi` for each `pythonExportPath`
      - Author per-class smoke tests in `test_promoted_residuals_smoke.py` grouped by owner:
        ```python
        # ============ yaml ============
        def test_classic_yaml_<ClassName>_smoke() -> None:
            obj = classic_yaml.<ClassName>(...)  # verify constructor from -py/src
            result = obj.<method>(...)  # call at least one real method
            assert result is not None
        # ... etc
        ```

    Step 2: For each smoke test, verify the constructor signature from the `-py` source BEFORE authoring the test (do not guess). Use the same pattern as the Plan 02-08 constructor inventory step.

    Step 3: Commit all contract rows + stubs + tests in a single atomic batch (D-06). Do NOT regenerate baseline yet — Task 4 handles it.

    IMPORTANT constraints:
    - Plan 09a explicitly EXCLUDES `classic-file-io-core` / `file_io` from residuals (Plan 08 owns all file_io rows)
    - If a residual is a function (not a class), skip the constructor but add a function-call smoke test
    - If a residual is an enum, test variant access (`assert hasattr(classic_<owner>.<Enum>, "<Variant>")`)
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import json; c = json.loads(open('docs/implementation/python_api_parity/baseline/parity_contract.json').read()); file_io_residual_count = sum(1 for m in c['tier1Mappings'] if m.get('ownerModule') == 'file_io' and m.get('rustCrate') == 'classic-file-io-core'); total = len(c['tier1Mappings']); print(f'tier1Mappings.length = {total}, file_io rows = {file_io_residual_count}'); assert total >= 358"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length >= 358` + (inventory count) — R9: Plan 08 ends at 358 post-GLOBAL_FCX_HANDLER exclusion, not 359
    - Zero file_io residuals added by Plan 09a (file_io is Plan 08's domain)
    - Every new row has a `pythonExportPath` verified against a real `-py` wrapper
    - `test_promoted_residuals_smoke.py` has at least one test per promoted `#[pyclass]`
    - Each stub file (`.pyi`) is updated for its residuals
  </acceptance_criteria>
  <done>Residuals promoted (contract + stub + tests); file_io excluded; atomic commit.</done>
</task>

<task type="auto">
  <name>Task 3: Add runtime_coverage_registry.json selector entries for each residual-receiving owner module</name>
  <files>
    ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
    - .planning/phases/03-python-tier-collapse/03-09a-residual-inventory.md
  </read_first>
  <action>
    For each owner module receiving residual rows (from the inventory), ADD a new selector entry `python-tier1-<owner>` to `runtime_coverage_registry.json::entries`:

    ```json
    {
      "coverageId": "python-tier1-<owner>",
      "classification": "runtime_verified",
      "ownerModule": "<owner>",
      "tier": "tier1",
      "contractSelector": { "ownerModule": "<owner>", "tier": "tier1" },
      "contractCount": <residual row count for this owner>,
      "contractIdsHash": "<computed>",
      "verificationMode": "workflow_smoke",
      "testSuite": "ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py",
      "testCaseId": "<owner>-residuals-smoke"
    }
    ```

    contractIdsHash: before committing, verify whether `generate_baseline.py --write-baseline` auto-recomputes selector `contractIdsHash` values (grep `contractIdsHash` in generate_baseline.py and in tools/binding_parity_runtime_coverage.py). If it does, the placeholder `"<computed>"` is fine — Task 4's baseline refresh will populate it. If it does NOT, compute the hash directly via `hashlib.sha256(','.join(sorted(matching_contract_ids)).encode()).hexdigest()[:16]` before committing.

    Do NOT add a selector for `file_io` (Plan 08 already owns it).
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import json; r = json.loads(open('ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json').read()); new_selectors = [e for e in r['entries'] if e.get('coverageId', '').startswith('python-tier1-') and e['coverageId'] not in ('python-tier1-config','python-tier1-scanlog','python-tier1-version-registry','python-tier1-shared','python-tier1-file_io')]; print(f'New residual selector entries: {len(new_selectors)}'); assert len(new_selectors) >= 1"</automated>
  </verify>
  <acceptance_criteria>
    - New `python-tier1-<owner>` selector entries exist for every owner in the inventory (excluding file_io)
    - Each entry has matching `contractCount` and a computed `contractIdsHash` (no placeholder strings after Task 4)
  </acceptance_criteria>
  <done>Registry updated with residual selectors; file_io excluded.</done>
</task>

<task type="auto">
  <name>Task 4: Refresh baseline, run 5-step verification chain</name>
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
    - docs/implementation/python_api_parity/baseline/parity_contract.json (post-Tasks-1-3)
  </read_first>
  <action>
    Step 1: Refresh baseline:
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    ```

    Step 2: Run 5-step plan-close verification chain:
    ```powershell
    python tools/python_api_parity/check_parity_gate.py --repo-root .
    python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings
    pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
    # mypy --strict sweep is deferred to Plan 09b Task 4 (full 19-stub sweep)
    ```

    All 4 commands must exit 0.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root .; if ($LASTEXITCODE -ne 0) { exit 1 }; python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py -q"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length` equals 358 + residual count (from inventory) — R9 propagation
    - `parity_diff_report.json::summary.tier1_missing_rust == 0`, `tier1_missing_python == 0`
    - `runtime_coverage_summary.json::summary.tier1_missing_runtime_total == 0` (new selectors cover all residual rows)
    - All 4 verification steps exit 0
  </acceptance_criteria>
  <done>Plan 09a commit gate-green; residuals fully promoted (no wrapper-less skips); ready for Plan 09b cleanup.</done>
</task>

</tasks>

<verification>
4-step verification chain (mypy --strict sweep deferred to Plan 09b).
</verification>

<success_criteria>
- Fresh residual discovery from parity_diff_report.json::gaps (NOT stale Plan 01 snapshot)
- file_io explicitly excluded (Plan 08's domain)
- Fail-closed behavior: wrapper-less symbols produce PLAN-09a-BLOCKERS.md and STOP (no silent skips)
- Every residual with wrapper → contract row + stub + smoke test + registry selector
- 4-step verification chain exits 0
- Plan 09b (next wave) can proceed to structural cleanup
</success_criteria>

<output>
Create `.planning/phases/03-python-tier-collapse/03-09a-SUMMARY.md` containing:
- Residual inventory reference (link to 03-09a-residual-inventory.md)
- Blocker status (NONE or list with remediation plan)
- Files modified
- Final tier1Mappings.length after Plan 09a
- Verification results
- Notes for Plan 09b (the cleanup plan that depends on this one)
</output>
