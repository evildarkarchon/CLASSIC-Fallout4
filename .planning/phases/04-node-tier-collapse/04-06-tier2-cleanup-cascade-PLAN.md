---
phase: 04-node-tier-collapse
plan: 06
plan_id: 04-06
title: Tier-2 Cleanup Atomic Cascade + Final Verification (M7 pattern)
type: execute
wave: 5
depends_on: [04-02, 04-03, 04-04, 04-05]
files_modified:
  - .planning/phases/04-node-tier-collapse/04-06-TIER2-CASCADE-AUDIT.md
  - .planning/STATE.md
  - .planning/ROADMAP.md
  - tools/node_api_parity/generate_baseline.py
  - tools/node_api_parity/tests/test_check_parity_gate.py
  - docs/implementation/node_api_parity/baseline/parity_contract.json
  - docs/implementation/node_api_parity/baseline/parity_contract.md
  - docs/implementation/node_api_parity/baseline/parity_diff_report.json
  - docs/implementation/node_api_parity/baseline/parity_diff_report.md
  - docs/implementation/node_api_parity/baseline/rust_api_surface.json
  - docs/implementation/node_api_parity/baseline/node_api_surface.json
  - docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json
  - docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md
  - docs/implementation/node_api_parity/baseline/tier1_gate_report.md
  - docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json
  - ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_contract.json
  - ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_contract.md
  - ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_diff_report.json
  - ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_diff_report.md
  - ClassicLib-rs/node-bindings/classic-node/parity-artifacts/rust_api_surface.json
  - ClassicLib-rs/node-bindings/classic-node/parity-artifacts/node_api_surface.json
  - ClassicLib-rs/node-bindings/classic-node/parity-artifacts/runtime_coverage_summary.json
  - ClassicLib-rs/node-bindings/classic-node/parity-artifacts/runtime_coverage_summary.md
  - ClassicLib-rs/node-bindings/classic-node/parity-artifacts/tier1_gate_report.md
autonomous: true
requirements_addressed: [NODE-02, NODE-03, NODE-04, NODE-06]
requirements: [NODE-02, NODE-03, NODE-04, NODE-06]
must_haves:
  truths:
    - "TASK 1 ONLY: Pre-deletion cascade audit. Runs a recursive ripgrep search for `tier2_gap_total|rust_unmapped|node_unmapped|tierDefinitions.*tier2|tierDefinitions\\[\"tier2\"\\]|tierDefinitions\\['tier2'\\]|Tier 2 Gaps|GLOBAL_FCX_HANDLER` across tools/node_api_parity/, docs/implementation/node_api_parity/, ClassicLib-rs/node-bindings/classic-node/, .github/workflows/, *.ps1 files. The regex matches bracket-subscript syntax per LOW concern. Classify each hit and record remediation plan in `04-06-TIER2-CASCADE-AUDIT.md`. This is the gatekeeping artifact — no deletion starts until the audit is complete."
    - "TASK 2 M7 ATOMIC CASCADE (single commit): (a) Delete `gap_type=rust_unmapped` and `gap_type=node_unmapped` loop branches in `tools/node_api_parity/generate_baseline.py::generate_diff_report()` (lines ~463-489 per RESEARCH.md — RE-VERIFY line numbers with Select-String before editing because earlier plans may have shifted them). (b) Delete `tier2_gap_total` from the `summary` dict (line ~511). (c) Delete the `Tier 2 Gaps` markdown column from `render_diff_markdown()` — TWO edit locations: header line AND cell expression (line ~558 + ~583); both MUST be edited atomically per MEDIUM concern. (d) Delete the `handoff_map` tier column reference (line ~623 per RESEARCH.md)."
    - "TASK 2 continuation (same atomic commit): (e) Delete `tierDefinitions.tier2` from `parity_contract.json`. (f) Empty `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json::entries` to `[]` — preserve file shape for Phase 6 to delete the file itself (DOC-03). (g) Delete the GLOBAL_FCX_HANDLER backlog row from the same file (per A2)."
    - "TASK 2 continuation (same atomic commit): (h) Flip `tools/node_api_parity/tests/test_check_parity_gate.py::test_tier2_definition_removed_after_plan_6` by REMOVING its `@pytest.mark.xfail(strict=True)` decorator — it now passes as a normal test. (i) Update `test_tier1_contract_total_baseline_floor` assertion to reflect the final post-promotion floor — Phase 4 close target is 261 + 66 (Plan 2) + 34 (Plan 3 H2-reconciled) + 7 (Plan 4 D1-restored) + ~15 (Plan 5 residuals) = ~383; compute the real value at execution time from the post-pipeline refreshed baseline, not the estimate."
    - "TASK 2 continuation (same atomic commit): (j) Run `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local` — the script internally invokes both `generate_baseline.py --write-baseline` and `check_parity_gate.py --update-baseline`, so no pre-invocation is needed. The placeholder-resolution loop (Phase 2c.1) may require iterating the full pipeline multiple times until pytest passes; the working tree stays UNCOMMITTED across retry iterations (U3 re-sequencing). (k) Confirm `runtime_coverage_summary.json::summary.deferred_total == 0`. (l) Run `bun run test:bun && bun run test:node` for smoke coverage."
    - "The entire Task 2 work lands in ONE atomic commit. Splitting any of these steps across commits creates bisect-breaking intermediate states where `tierDefinitions.tier2` is deleted but `gap_type=rust_unmapped` branches still emit tier2 rows — gate fails. Phase 3 Plan 09b precedent enforces single-commit M7 discipline."
    - "NODE-06 primary gate: `runtime_coverage_summary.json::summary.deferred_total == 0`. A4 clarifies this is the SOLE criterion — `tier2_gap_total` self-resolves via the branch deletion in step (a). No separate verification step for tier2_gap_total."
    - "TASK 3: Final verification sweep. Runs full test suite (bun:test + node:test), full gate (parity:gate:local), dts:freshness:check, and prints runtime_coverage_summary.md. Records pass/fail in the SUMMARY. U4 success criterion rewording: no Tier-2 SEMANTICS remain in generated baselines (`parity_contract.json`, `node_api_surface.json`, `parity_diff_report.json`); the governance backlog file `deferred_runtime_backlog.json` is PRESERVED but emptied (`entries: []`) until Phase 6 DOC-03 deletion."
    - "TASK 3 continuation: Phase 4 CLOSED confirmation artifact written to 04-06-SUMMARY.md with final tier1Mappings count, final deferred_total, and green status across all 5 gates (parity + bun test + node test + dts freshness + contract guard). STATE.md and ROADMAP.md are EDITED as part of Task 3 Steps 4-6 (included in files_modified per H3 frontmatter reconciliation)."
  artifacts:
    - path: ".planning/phases/04-node-tier-collapse/04-06-TIER2-CASCADE-AUDIT.md"
      provides: "Pre-deletion ripgrep audit with every match classified (CODE_WRITE, CODE_READ, DOCS_PROSE, TEST_ASSERTION, BASELINE_JSON, HISTORICAL_COMMENT, OUT_OF_SCOPE_PHASE_6) and remediation status per file"
      min_lines: 50
    - path: "tools/node_api_parity/generate_baseline.py"
      provides: "Cleaned generate_diff_report() with no Tier-2 gap branches, no tier2_gap_total, no Tier 2 Gaps markdown column (header + cell both deleted atomically)"
    - path: "tools/node_api_parity/tests/test_check_parity_gate.py"
      provides: "test_tier2_definition_removed_after_plan_6 passes without xfail; test_tier1_contract_total_baseline_floor updated to final post-promotion count"
    - path: "docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json"
      provides: "entries=[] (empty array, file shape preserved for Phase 6 DOC-03 deletion per U4 success-criterion rewording)"
    - path: "docs/implementation/node_api_parity/baseline/parity_contract.json"
      provides: "tierDefinitions has only tier1; final tier1Mappings count"
    - path: "docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json"
      provides: "summary.deferred_total == 0 (NODE-06 primary success criterion)"
    - path: "ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_contract.json"
      provides: "Mirror of docs/implementation baseline refreshed by parity:gate:local — added to files_modified per H3 frontmatter reconciliation"
    - path: "ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_contract.md"
      provides: "Mirror of docs/implementation baseline refreshed by parity:gate:local — added to files_modified per H3 frontmatter reconciliation"
    - path: ".planning/STATE.md"
      provides: "Task 3 Steps 4-6 edits marking Phase 4 CLOSED (H3 frontmatter reconciliation)"
    - path: ".planning/ROADMAP.md"
      provides: "Task 3 Step 5 edit checking Phase 4 as complete (H3 frontmatter reconciliation)"
  key_links:
    - from: "tools/node_api_parity/tests/test_check_parity_gate.py::test_tier2_definition_removed_after_plan_6"
      to: "parity_contract.json::tierDefinitions"
      via: "xfail flipped to passing in the same commit as the tier2 deletion"
      pattern: "tier2.*not in"
    - from: "docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json::entries == []"
      to: "runtime_coverage_summary.json::summary.deferred_total == 0"
      via: "build_coverage_summary registry_only fallback (Phase 3 Scenario E empirical proof)"
      pattern: "entries.*\\[\\]"
    - from: "tools/node_api_parity/generate_baseline.py (post-deletion)"
      to: "parity_diff_report.json (no more tier2_gap_total key)"
      via: "M7 atomic cascade single commit"
      pattern: "tier2_gap_total"
---

<objective>
Final cleanup plan for Phase 4. Mirrors Phase 3 Plan 09b's M7 atomic cascade pattern exactly. Four concerns:

1. **Pre-deletion cascade audit** (Task 1 — standalone commit): Enumerate every reader of `tier2_gap_total`, `rust_unmapped`, `node_unmapped`, `tierDefinitions.*tier2` (including bracket-subscript syntax per LOW concern), and `GLOBAL_FCX_HANDLER` via recursive ripgrep across `tools/node_api_parity/`, `docs/implementation/node_api_parity/`, `ClassicLib-rs/node-bindings/classic-node/`, `.github/workflows/`, and `*.ps1` scripts. Classify each hit and record the remediation status BEFORE deletion. Write the audit to `.planning/phases/04-node-tier-collapse/04-06-TIER2-CASCADE-AUDIT.md` as the gatekeeping artifact. This matches Phase 3 M8 fix (recursive search, not selective globs).

2. **Structural Tier-2 cleanup atomic cascade** (Task 2 — SINGLE atomic commit): All of the following edits land in ONE commit:
   - Delete `gap_type=rust_unmapped` and `gap_type=node_unmapped` loop branches in `generate_baseline.py::generate_diff_report()` (re-verify line numbers before editing; they may have shifted since Plan 1)
   - Delete `tier2_gap_total` from the `summary` dict
   - Delete the `Tier 2 Gaps` markdown column from `render_diff_markdown()` — TWO locations (header + cell), both MUST be deleted atomically per MEDIUM concern
   - Delete `handoff_map` tier column if present
   - Delete `tierDefinitions.tier2` from `parity_contract.json`
   - Empty `deferred_runtime_backlog.json::entries` to `[]` (preserve file shape per Phase 6 DOC-03)
   - Delete the GLOBAL_FCX_HANDLER entry from the backlog before emptying (per A2)
   - Flip `test_tier2_definition_removed_after_plan_6` xfail decorator — test becomes normal passing
   - Update `test_tier1_contract_total_baseline_floor` to the final post-promotion floor (placeholder resolution per U3 — iterative loop, working tree stays uncommitted until pytest passes)
   - Refresh baselines via a single `bun run parity:gate:local` pipeline invocation per placeholder-resolution iteration — no pre-invocations, no double-writes
   - Confirm `runtime_coverage_summary.json::summary.deferred_total == 0`

   Splitting any of these across commits creates a bisect-breaking intermediate state: e.g., deleting `tierDefinitions.tier2` while the `rust_unmapped` branch still emits tier2 rows → gate fails. Phase 3 Plan 09b's M7 pattern is the mandatory precedent.

3. **Final verification sweep** (Task 3 — standalone task): Run the full test suite, full gate, dts:freshness:check. Confirm every success criterion from ROADMAP Phase 4 is met. Record in SUMMARY.

4. **Phase CLOSED artifact**: Final status written to `.planning/phases/04-node-tier-collapse/04-06-tier2-cleanup-cascade-SUMMARY.md` marking Phase 4 complete.

Per A4: `deferred_total == 0` is the sole NODE-06 criterion. `tier2_gap_total` self-resolves via the branch deletion in Task 2 step (a) — no separate verification required.

Per A2: GLOBAL_FCX_HANDLER is explicitly cleared in Task 2 (deleted from the backlog in the same commit that empties `entries[]`). After Task 2, `deferred_total` includes zero scanlog entries.

**Per U4 (success criterion rewording)**: Phase 4 closes with "no Tier-2 SEMANTICS in generated baselines (`parity_contract.json`, `node_api_surface.json`, `parity_diff_report.json`), and the governance backlog file `deferred_runtime_backlog.json` preserved but emptied (`entries: []`) until Phase 6 DOC-03 deletion." This reflects the actual Phase 4/6 scope boundary.

Output:
- Cascade audit file
- ONE atomic M7 commit landing all structural cleanup
- Final gate-green state with `deferred_total == 0`
- Phase 4 CLOSED summary
- STATE.md and ROADMAP.md updates
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
@.planning/phases/04-node-tier-collapse/04-CONTEXT.md
@.planning/phases/04-node-tier-collapse/04-RESEARCH.md
@.planning/phases/04-node-tier-collapse/04-VALIDATION.md
@.planning/phases/04-node-tier-collapse/04-REVIEWS.md
@.planning/phases/04-node-tier-collapse/04-01-tooling-expansion-SUMMARY.md
@.planning/phases/04-node-tier-collapse/04-02-scanlog-promotion-SUMMARY.md
@.planning/phases/04-node-tier-collapse/04-03-config-promotion-SUMMARY.md
@.planning/phases/04-node-tier-collapse/04-04-version-registry-and-pe-version-SUMMARY.md
@.planning/phases/04-node-tier-collapse/04-05-aux-promotion-SUMMARY.md
@.planning/phases/03-python-tier-collapse/03-09b-tier2-cleanup-and-final-sweep-PLAN.md
@.planning/phases/03-python-tier-collapse/03-09b-tier2-cleanup-and-final-sweep-SUMMARY.md
@./CLAUDE.md
@./AGENTS.md

<interfaces>
<!-- Line numbers are from RESEARCH.md §Sources (verified 2026-04-08) — RE-VERIFY before editing -->

**Deletion targets in `tools/node_api_parity/generate_baseline.py`** (current lines — verify with Select-String first):

- Line ~456: start of `gap_type=rust_unmapped` branch — delete the entire `for rust_item in rust_symbols:` loop that appends rust_unmapped gaps
- Line ~475: start of `gap_type=node_unmapped` branch — delete the entire `for node_item in node_exports:` loop that appends node_unmapped gaps
- Line ~511: `"tier2_gap_total": <expression>` key in the `summary` dict — delete this line
- Line ~558: `| Tier 2 Gaps |` markdown column header in `render_diff_markdown()` — delete
- Line ~583: cell expression computing the Tier 2 Gaps value — delete (**MEDIUM concern: TWO locations — header + cell — must be deleted atomically. Deleting only one produces a malformed markdown table (header column count != row column count).**)
- Line ~623: `handoff_map` tier column — delete reference if present

**Deletion target in `docs/implementation/node_api_parity/baseline/parity_contract.json`**:
- Delete the `"tierDefinitions": { "tier2": {...} }` nested object — keep `"tierDefinitions": { "tier1": {...} }` (if the file uses a tierDefinitions object; confirm with grep before editing).

**Empty target in `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json`**:
- Change `"entries": [...101 entries...]` to `"entries": []` — preserve the top-level schema (schemaVersion, binding, entries) so Phase 6 can delete the entire file in DOC-03.

**Test file updates** (`tools/node_api_parity/tests/test_check_parity_gate.py`):

Before:
```python
@pytest.mark.xfail(strict=True, reason="Plan 6 atomic cascade deletes tierDefinitions.tier2 — test flips to passing then")
def test_tier2_definition_removed_after_plan_6():
    contract = json.loads(PARITY_CONTRACT.read_text(encoding="utf-8"))
    tier_defs = contract.get("tierDefinitions", {})
    assert "tier2" not in tier_defs, "tierDefinitions.tier2 still present (Plan 6 will remove it)"
```

After:
```python
def test_tier2_definition_removed_after_plan_6():
    contract = json.loads(PARITY_CONTRACT.read_text(encoding="utf-8"))
    tier_defs = contract.get("tierDefinitions", {})
    assert "tier2" not in tier_defs, "tierDefinitions.tier2 should be removed as of Plan 6"
```

And `test_tier1_contract_total_baseline_floor`:
```python
def test_tier1_contract_total_baseline_floor():
    """Phase 4 close floor: tier1Mappings must not regress below the final post-promotion count."""
    contract = json.loads(PARITY_CONTRACT.read_text(encoding="utf-8"))
    tier1 = contract.get("tier1Mappings", [])
    # Post-Plan-5 floor — read from SUMMARY files for the actual number
    assert len(tier1) >= <COMPUTED_FLOOR>, f"tier1Mappings regressed below Phase 4 floor: {len(tier1)}"
```

**Floor calculation (updated per corrected counts)**: `<COMPUTED_FLOOR>` is the actual count from the refreshed baseline. Rough estimate using H2 + D1 corrected counts: `261 (start) + 66 (Plan 2) + 34 (Plan 3 H2) + 7 (Plan 4 D1-restored) + ~15 (Plan 5 residuals — executor computes exact number) = ~383`. The real value comes from reading the post-pipeline `parity_contract.json::tier1Mappings` length after Phase 2b runs.

**Phase 3 Plan 09b M7 precedent** (mandatory read): `.planning/phases/03-python-tier-collapse/03-09b-tier2-cleanup-and-final-sweep-PLAN.md` lines 33-74 — exact M7 atomic commit structure.

**Phase 3 Scenario E empirical proof** (why emptying backlog is mandatory, not optional): `03-09a-DRY-RUN-PROJECTION.md` Scenario E. The `build_coverage_summary` registry_only fallback in `tools/binding_parity_runtime_coverage.py` consumes backlog entries to compute `deferred_total` even after their gap rows are removed. Emptying the backlog alone is INSUFFICIENT (branches still emit rows); deleting the branches alone is INSUFFICIENT (backlog fallback still fires). BOTH must happen in the same commit.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Pre-deletion cascade audit (recursive ripgrep + classification)</name>
  <read_first>
    - `.planning/phases/03-python-tier-collapse/03-09b-tier2-cleanup-and-final-sweep-PLAN.md` §Task 1 (Phase 3 precedent for the audit shape — classification categories, output format)
    - `.planning/phases/03-python-tier-collapse/03-09b-TIER2-CASCADE-AUDIT.md` (Phase 3 actual audit output as reference)
    - `.planning/phases/04-node-tier-collapse/04-CONTEXT.md` §Research Amendments A2, A4 (GLOBAL_FCX_HANDLER explicit, deferred_total sole criterion)
    - `.planning/phases/04-node-tier-collapse/04-REVIEWS.md` §"U3 — Plan 06 Task 2 Step 5 chicken-and-egg" (understand the placeholder-resolution loop)
  </read_first>
  <action>
    Step 1 — Run recursive ripgrep for the Tier-2 cascade keywords. From repo root (use PowerShell per user rule):
    ```powershell
    cd J:/CLASSIC-Fallout4
    # Issue 14 fix: include "Tier 2 Gaps" with spaces to catch markdown table headers
    # LOW concern fix: extend tierDefinitions regex to catch bracket-subscript syntax
    rg --line-number --no-heading "tier2_gap_total|rust_unmapped|node_unmapped|tierDefinitions\.?tier2|tierDefinitions\[['""]tier2['""]\]|Tier 2 Gaps|GLOBAL_FCX_HANDLER" `
      --glob "!**/node_modules/**" `
      --glob "!**/target/**" `
      --glob "!**/.git/**" `
      --glob "!**/dist/**" `
      --glob "!**/*.lock" `
      tools/node_api_parity/ `
      docs/implementation/node_api_parity/ `
      ClassicLib-rs/node-bindings/classic-node/ `
      .github/workflows/ `
      *.ps1 2>$null
    ```

    Step 2 — Write the audit to `.planning/phases/04-node-tier-collapse/04-06-TIER2-CASCADE-AUDIT.md` with:
    - Header documenting the exact ripgrep command and the total match count
    - A table of every hit classified as:
      - CODE_WRITE — code that writes/produces the cascade symbol; MUST be deleted in Task 2 (e.g., `generate_baseline.py` branches)
      - CODE_READ — code that reads the cascade symbol; MUST be updated to not depend on it (e.g., a test assertion)
      - DOCS_PROSE — prose mentions in markdown; can stay (describes deprecated concept) OR should be updated
      - TEST_ASSERTION — test asserting the symbol exists; MUST be flipped (e.g., the xfail test)
      - BASELINE_JSON — generated artifact containing the symbol; refreshed by Task 2's baseline regen
      - HISTORICAL_COMMENT — rationale/audit trail that should be preserved
      - OUT_OF_SCOPE_PHASE_6 — governance files Phase 6 will delete; leave in place
      - LOAD_BEARING_EXCLUDED — false positive (e.g., a variable name `tier1_foo` matching `tier2` by accident)
    - A "Task 2 Action Plan" section listing exactly which files Task 2 must edit, in which order, within the single atomic commit

    Step 3 — Commit as: `Docs(04): pre-deletion cascade audit for Tier-2 cleanup (Phase 4 Plan 6 Task 1)` with only the audit file.
  </action>
  <verify>
    <automated>python -c "from pathlib import Path; assert Path('.planning/phases/04-node-tier-collapse/04-06-TIER2-CASCADE-AUDIT.md').exists()"</automated>
  </verify>
  <acceptance_criteria>
    - `Test-Path .planning/phases/04-node-tier-collapse/04-06-TIER2-CASCADE-AUDIT.md` returns `True` (PowerShell-native per user rule)
    - `(Get-Content .planning/phases/04-node-tier-collapse/04-06-TIER2-CASCADE-AUDIT.md).Count -ge 50` returns `True` (at least 50 lines)
    - Audit file contains the literal ripgrep command used (for reproducibility)
    - Audit file classifies every hit into one of the 8 categories
    - Audit file contains a "Task 2 Action Plan" section naming the exact files to edit
  </acceptance_criteria>
  <done>
    Cascade audit written. Every reference to tier2_gap_total / rust_unmapped / node_unmapped / tierDefinitions.tier2 (including bracket-subscript syntax per LOW concern) / GLOBAL_FCX_HANDLER has been classified. Task 2 has an explicit action plan.
  </done>
</task>

<task type="auto">
  <name>Task 2: M7 ATOMIC CASCADE — single commit deleting Tier-2 branches + tier2 definition + empty backlog + flip xfail (with U3 placeholder-resolution loop)</name>
  <read_first>
    - `.planning/phases/04-node-tier-collapse/04-06-TIER2-CASCADE-AUDIT.md` (Task 1 output — this is the action plan)
    - `tools/node_api_parity/generate_baseline.py` (entire file — re-verify line numbers for rust_unmapped, node_unmapped, tier2_gap_total, Tier 2 Gaps column; Phase 3 precedent noted line numbers shift between plans)
    - `docs/implementation/node_api_parity/baseline/parity_contract.json` (read `tierDefinitions` key; confirm it has a `tier2` sub-key)
    - `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` (read entire `entries` array; confirm GLOBAL_FCX_HANDLER is still there)
    - `tools/node_api_parity/tests/test_check_parity_gate.py` (Plan 1 scaffold with xfail test + floor test)
    - `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json` (read current `summary.deferred_total`; expect 1 or 0 depending on whether GLOBAL_FCX_HANDLER is still counted)
    - `.planning/phases/03-python-tier-collapse/03-09b-tier2-cleanup-and-final-sweep-SUMMARY.md` (Phase 3 precedent confirmation that M7 atomic cascade works)
    - `.planning/phases/04-node-tier-collapse/04-REVIEWS.md` §"U3 — Plan 06 Task 2 Step 5 test floor re-sequencing" (load-bearing — defines the Phase 2c.1 placeholder-resolution loop explicitly)
    - `tools/binding_parity_runtime_coverage.py::build_coverage_summary` lines 221-330 (understand the registry_only fallback path that picks up backlog entries)
  </read_first>
  <behavior>
    - ALL of the following edits land in ONE git commit. NO intermediate commits.
    - `generate_baseline.py` has no `gap_type=rust_unmapped` branch, no `gap_type=node_unmapped` branch, no `tier2_gap_total` key, no `Tier 2 Gaps` markdown column (header AND cell both deleted atomically), no `handoff_map` tier column
    - `parity_contract.json::tierDefinitions` has only `tier1` (no `tier2` sub-key)
    - `deferred_runtime_backlog.json::entries == []` (file shape preserved, contents empty; GLOBAL_FCX_HANDLER is gone along with everything else)
    - `test_tier2_definition_removed_after_plan_6` no longer has `@pytest.mark.xfail` decorator; runs as a normal passing test
    - `test_tier1_contract_total_baseline_floor` assertion updated to the final post-promotion count (read from the refreshed baseline via placeholder resolution loop per U3)
    - `runtime_coverage_summary.json::summary.deferred_total == 0` post-commit
    - `runtime_coverage_summary.md` header shows `Deferred: **0**`
    - `bun run parity:gate:local` exits 0
    - `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0
  </behavior>
  <action>
    **DO NOT COMMIT PARTIALLY**. All edits below MUST be staged and committed together in ONE git commit. Splitting creates bisect-breaking intermediate states. This plan EXPLICITLY PROHIBITS separate commits inside Task 2 — Phase 3 Plan 09b's M7 pattern is the mandatory precedent and demands single-commit atomicity. If any verification step fails, fix within the same uncommitted working tree; do NOT `git commit --amend` or `git commit` progress separately.

    **BLOCKER Issue 1 fix**: Phase 3 Plan 09b's actual shape was "ALL source edits first, then ONE invocation of `parity:gate:local` as the single verification pipeline". The previous Plan 6 draft ran `generate_baseline.py --write-baseline` and `check_parity_gate.py --update-baseline` MANUALLY (Step 6) before running `bun run parity:gate:local` (Step 8), which INTERNALLY re-invokes both of those scripts — creating a double-write race where Step 6's artifacts can be silently overwritten by Step 8 with no rollback hook. The corrected pipeline is: (1) make ALL source edits, (2) run `bun run parity:gate:local` ONCE per placeholder-resolution iteration, (3) verify outputs, (4) iterate if pytest fails (U3), (5) enumerate + stage + commit.

    Step 1 — Re-verify line numbers in `tools/node_api_parity/generate_baseline.py`:
    ```powershell
    Select-String -Path tools/node_api_parity/generate_baseline.py -Pattern "rust_unmapped|node_unmapped|tier2_gap_total|Tier 2 Gaps"
    ```
    Note the exact line numbers. They may differ from the RESEARCH.md references (lines 456-489 / 511 / 558 / 623) if earlier plans touched generate_baseline.py. Use the live line numbers in your edits.

    ---

    **Phase 2a: ALL SOURCE EDITS (no script invocations yet)**

    Step 2 — Edit `tools/node_api_parity/generate_baseline.py`:
    - Delete the `for rust_item in rust_symbols:` loop that emits `gap_type=rust_unmapped` gaps (lines 463-475 region — re-verify with Select-String).
    - Delete the `for node_item in node_exports:` loop that emits `gap_type=node_unmapped` gaps (lines 476-489 region).
    - Delete the `"tier2_gap_total": ...` key from the `summary` dict literal (around line 511).
    - **MEDIUM concern — Tier 2 Gaps column: delete BOTH locations atomically**. The markdown column has TWO edit locations that MUST be edited together:
      1. **Header line** (around line 558) — the `| Tier 2 Gaps |` column in the table header
      2. **Cell expression** (around line 583) — the cell value computation in the per-row iteration
      Deleting only one produces a malformed markdown table (header column count ≠ row column count). After the edit, add a verification command to the acceptance criteria:
      ```powershell
      # Verify the markdown table is well-formed after the edit — header column count must match row column count
      Select-String -Path tools/node_api_parity/generate_baseline.py -Pattern '\| Tier 2 Gaps \|' -Quiet
      # Should return False (not present anywhere)
      ```
    - Delete the `handoff_map` tier column if present (around line 623; ripgrep audit flags the exact line).
    - Do NOT run `generate_baseline.py` yet — the pipeline invocation happens ONCE in Phase 2b below.

    Step 3 — Edit `docs/implementation/node_api_parity/baseline/parity_contract.json`:
    - Delete the `tier2` sub-key from `tierDefinitions`. Leave `tier1` intact.
    - (The actual edit is tiny — removing one JSON object entry from the nested `tierDefinitions` object.)

    Step 4 — Edit `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json`:
    - First: remove the `GLOBAL_FCX_HANDLER` row from `entries[]` (per A2) along with every other row in a single operation: change `"entries": [<array>]` to `"entries": []`.
    - Preserve the top-level shape: `{"schemaVersion": ..., "binding": "node", "entries": [], ...}`
    - Do NOT delete the file (Phase 6 DOC-03 owns deletion).

    Step 5 — Edit `tools/node_api_parity/tests/test_check_parity_gate.py`:
    - Remove the `@pytest.mark.xfail(strict=True, ...)` decorator from `test_tier2_definition_removed_after_plan_6`. It now runs as a normal test.
    - For `test_tier1_contract_total_baseline_floor`: set the assertion to use a PLACEHOLDER `<COMPUTED_FLOOR>` sentinel (e.g., a comment + a temporary value of `-1`). The actual value is resolved by the Phase 2c.1 loop below.

    ---

    **Phase 2b: SINGLE VERIFICATION PIPELINE — `bun run parity:gate:local` invoked ONCE**

    Step 6 — Run the single atomic verification pipeline ONCE. `bun run parity:gate:local` INTERNALLY runs `generate_baseline.py --write-baseline` and `check_parity_gate.py --update-baseline` exactly once, refreshing the baseline artifacts atomically. Do NOT pre-invoke those Python scripts — that would create a double-write race (Issue 1 root cause):
    ```powershell
    # PowerShell preferred per user rule; if from Git Bash, source tools/use_msvc_from_git_bash.sh first
    cd J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node
    bun run parity:gate:local
    ```
    **Retry discipline (MEDIUM concern fix)**: If the pipeline fails due to a TRANSIENT issue (e.g., a filesystem hiccup or a race with the parity-artifacts writer), allow EXACTLY ONE retry. If the second invocation also fails, ABORT the atomic pipeline — do not retry a third time. Fix within the same uncommitted working tree and restart Phase 2a (re-apply source edits if they were reverted during debugging, then re-enter Phase 2b from the top).

    If the failure is a genuine diagnostic (e.g., bidirectional guard firing on a row, `deferred_total != 0`), do NOT retry — fix the underlying cause first.

    ---

    **Phase 2c: POST-PIPELINE VERIFICATION (read-only assertions)**

    Step 7 — Verify `runtime_coverage_summary.json::summary.deferred_total == 0`:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); dt = d.get('summary', {}).get('deferred_total'); print('deferred_total:', dt); assert dt == 0, f'deferred_total != 0 — cascade incomplete: got {dt}'"
    ```
    MUST exit 0 with `deferred_total: 0`. If non-zero: either the `gap_type` branches still emit rows (check Step 2 edit) OR the backlog still has entries (check Step 4 edit). BOTH must hold for `deferred_total` to reach 0 (Phase 3 Scenario E empirical proof: the `build_coverage_summary` registry_only fallback in `tools/binding_parity_runtime_coverage.py` consumes backlog entries even after their gap rows are removed — emptying the backlog alone is INSUFFICIENT, deleting the branches alone is INSUFFICIENT, BOTH must happen in the same working tree before the pipeline runs).

    ---

    **Phase 2c.1: PLACEHOLDER RESOLUTION LOOP (U3 re-sequencing — explicit loop)**

    The `test_tier1_contract_total_baseline_floor` placeholder (`<COMPUTED_FLOOR>`) must be resolved against the refreshed `parity_contract.json::tier1Mappings` count, and the pytest run must PASS with the resolved value. This loop is EXPLICIT — it may iterate multiple times until convergence. The working tree stays UNCOMMITTED across iterations.

    Step 7.1 — Read the refreshed `tier1Mappings` count from `parity_contract.json` (Phase 2b's output):
    ```powershell
    cd J:/CLASSIC-Fallout4
    python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); print('tier1Mappings count:', len(d.get('tier1Mappings', [])))"
    ```
    Record the printed count (e.g., 383).

    Step 7.2 — Edit `tools/node_api_parity/tests/test_check_parity_gate.py`: replace the `<COMPUTED_FLOOR>` placeholder (from Step 5) with the actual count from Step 7.1. Example:
    ```python
    assert len(tier1) >= 383, f"tier1Mappings regressed below Phase 4 floor: {len(tier1)}"
    ```

    Step 7.3 — Re-run `bun run parity:gate:local` (Phase 2c.1 re-verification — confirms the new floor still passes the full pipeline):
    ```powershell
    cd J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node
    bun run parity:gate:local
    ```
    MUST exit 0.

    Step 7.4 — Run pytest to confirm the updated test passes:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python -m pytest tools/node_api_parity/tests/test_check_parity_gate.py -v
    ```
    BOTH tests MUST pass normally (floor test passes with the resolved value; xfail test passes without xfail decorator).

    **If pytest FAILS in Step 7.4**: the working tree STAYS UNCOMMITTED. The executor iterates the entire atomic cycle from Phase 2a — do NOT commit a failing state. Possible causes:
    - The floor value drifted between Step 7.1 and Step 7.3 (another pipeline run changed the count). Re-read the count and iterate.
    - The xfail decorator wasn't actually removed in Step 5. Re-check the edit.
    - The `tierDefinitions.tier2` deletion wasn't actually landed in Step 3. Re-verify the JSON.

    The loop terminates when: `bun run parity:gate:local` exits 0 AND `pytest` exits 0 AND `deferred_total == 0`. Only then proceed to Phase 2d.

    ---

    **Phase 2d: REMAINING SMOKE COVERAGE + ENUMERATE + STAGE + SINGLE ATOMIC COMMIT**

    Step 8 — Run the remaining smoke coverage:
    ```powershell
    cd J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node
    bun run test:bun
    bun run test:node
    ```
    Both MUST exit 0. `bun run parity:gate:local` in Phase 2b/2c.1 already ran `dts:freshness:check`, so no need to re-run.

    Step 9 — Pre-stage integrity probe (H3 frontmatter reconciliation): run `git status --porcelain` and assert that the working tree contains ONLY the declared file set from `files_modified`. Fail-closed on unexpected entries:
    ```powershell
    cd J:/CLASSIC-Fallout4
    git status --porcelain
    ```
    Expected to list exactly the files under `files_modified` (minus `.planning/STATE.md` and `.planning/ROADMAP.md` which Task 3 touches, NOT Task 2):
    - `tools/node_api_parity/generate_baseline.py`
    - `tools/node_api_parity/tests/test_check_parity_gate.py`
    - `docs/implementation/node_api_parity/baseline/*.json` and `*.md` (all 9 files)
    - `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json`
    - `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/*.json` and `*.md` (all 7 files listed in files_modified)

    If the porcelain output contains unexpected files (e.g., stray `.tmp_*` or editor swap files), STOP and investigate — do not add them to the commit. If legitimate files are missing (e.g., `parity-artifacts/parity_contract.json` isn't staged because `bun run parity:gate:local` didn't refresh it), that is a pipeline bug — fix and re-run Phase 2b.

    Step 10 — `git add` every enumerated file from Step 9 and commit in ONE atomic operation:
    ```powershell
    cd J:/CLASSIC-Fallout4
    git add tools/node_api_parity/generate_baseline.py `
            tools/node_api_parity/tests/test_check_parity_gate.py `
            docs/implementation/node_api_parity/baseline/parity_contract.json `
            docs/implementation/node_api_parity/baseline/parity_contract.md `
            docs/implementation/node_api_parity/baseline/parity_diff_report.json `
            docs/implementation/node_api_parity/baseline/parity_diff_report.md `
            docs/implementation/node_api_parity/baseline/rust_api_surface.json `
            docs/implementation/node_api_parity/baseline/node_api_surface.json `
            docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json `
            docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md `
            docs/implementation/node_api_parity/baseline/tier1_gate_report.md `
            docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json `
            ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_contract.json `
            ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_contract.md `
            ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_diff_report.json `
            ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_diff_report.md `
            ClassicLib-rs/node-bindings/classic-node/parity-artifacts/rust_api_surface.json `
            ClassicLib-rs/node-bindings/classic-node/parity-artifacts/node_api_surface.json `
            ClassicLib-rs/node-bindings/classic-node/parity-artifacts/runtime_coverage_summary.json `
            ClassicLib-rs/node-bindings/classic-node/parity-artifacts/runtime_coverage_summary.md `
            ClassicLib-rs/node-bindings/classic-node/parity-artifacts/tier1_gate_report.md

    git commit -m "Refactor: M7 atomic Tier-2 cleanup cascade (Phase 4 Plan 6 Task 2; NODE-02, NODE-03, NODE-06)"
    ```

    The commit message body should detail:
    - Deleted `generate_baseline.py`: `rust_unmapped` branch, `node_unmapped` branch, `tier2_gap_total` key, `Tier 2 Gaps` markdown column (header + cell both removed atomically), `handoff_map` tier column
    - Deleted `parity_contract.json::tierDefinitions.tier2`
    - Emptied `deferred_runtime_backlog.json::entries` (GLOBAL_FCX_HANDLER cleared per A2)
    - Flipped `test_tier2_definition_removed_after_plan_6` xfail to normal
    - Updated `test_tier1_contract_total_baseline_floor` assertion to <COMPUTED_FLOOR> (actual value)
    - Final `deferred_total: 0` (NODE-06 primary criterion satisfied)
    - Single `bun run parity:gate:local` invocation per placeholder-resolution iteration (no double-write race per BLOCKER Issue 1 fix; one retry allowed on transient failure per MEDIUM concern)
    - M7 atomic per Phase 3 Plan 09b precedent — any split would create bisect-breaking intermediate state
  </action>
  <verify>
    <automated>python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); assert d.get('summary', {}).get('deferred_total') == 0"</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); assert d.get('summary', {}).get('deferred_total') == 0"` exits 0 (NODE-06 primary criterion)
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); assert 'tier2' not in d.get('tierDefinitions', {})"` exits 0
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json')); assert d.get('entries') == []"` exits 0
    - `Select-String -Path tools/node_api_parity/generate_baseline.py -Pattern 'tier2_gap_total' -Quiet` returns `False` (NOT found — symbol deleted)
    - `Select-String -Path tools/node_api_parity/generate_baseline.py -Pattern 'rust_unmapped' -Quiet` returns `False` (NOT found — branch deleted)
    - `Select-String -Path tools/node_api_parity/generate_baseline.py -Pattern 'node_unmapped' -Quiet` returns `False` (NOT found — branch deleted)
    - `Select-String -Path tools/node_api_parity/generate_baseline.py -Pattern '\| Tier 2 Gaps \|' -Quiet` returns `False` (MEDIUM concern: both header AND cell deleted; markdown table is well-formed)
    - `Select-String -Path tools/node_api_parity/tests/test_check_parity_gate.py -Pattern 'pytest.mark.xfail' -Quiet` returns `False` (NOT found — xfail removed)
    - `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0
    - `python -m pytest tools/node_api_parity/tests/ -v` exits 0 (all tests pass as normal, no xfail)
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local` exits 0
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run test:bun` exits 0
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run test:node` exits 0
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run dts:freshness:check` exits 0
    - `git log -1 --format="%s"` shows "Refactor: M7 atomic Tier-2 cleanup cascade (Phase 4 Plan 6 Task 2; NODE-02, NODE-03, NODE-06)" (the atomic commit)
  </acceptance_criteria>
  <done>
    M7 atomic cleanup cascade landed in one commit. `deferred_total == 0`. Tier-2 SEMANTICS removed from generate_baseline.py, parity_contract.json, and the test suite (per U4 rewording; `deferred_runtime_backlog.json` is preserved with empty entries). GLOBAL_FCX_HANDLER cleared. Gate green on all 5 verification surfaces (Python gate, bun gate, bun test, node test, dts freshness). Phase 4 CLOSED bar the final SUMMARY write.
  </done>
</task>

<task type="auto">
  <name>Task 3: Final verification sweep + Phase 4 CLOSED artifact + STATE.md and ROADMAP.md updates</name>
  <read_first>
    - `.planning/phases/04-node-tier-collapse/04-06-TIER2-CASCADE-AUDIT.md` (Task 1 audit — record in SUMMARY that it was honored)
    - `.planning/ROADMAP.md` §Phase 4 Success Criteria (5 criteria — SUMMARY must confirm all 5)
    - `.planning/REQUIREMENTS.md` §NODE-01..06 + HARM-01, HARM-02 (record status of each in SUMMARY)
    - All 5 prior plan SUMMARY files (to aggregate total row counts and confirm no gaps)
    - `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md` (human-readable summary — copy key figures into SUMMARY)
    - `docs/implementation/node_api_parity/baseline/parity_contract.json` (get final tier1Mappings count)
  </read_first>
  <action>
    Step 1 — Run the full verification sweep one more time (MEDIUM concern: this final rerun is framed as a NO-OP verification; assert the output does not differ from the Task 2 pipeline output). Capture exit codes for the SUMMARY:
    ```powershell
    cd J:/CLASSIC-Fallout4
    # Python gate
    python tools/node_api_parity/check_parity_gate.py --repo-root .
    python -m pytest tools/node_api_parity/tests/ -v

    # Node gate + tests — this is a NO-OP verification post Task 2's atomic commit;
    # should not produce any diff against the committed parity-artifacts. If it does,
    # something drifted and must be investigated before marking Phase 4 CLOSED.
    cd J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node
    bun run parity:gate:local
    bun run test:bun
    bun run test:node
    bun run dts:freshness:check

    # Print key metrics
    cd J:/CLASSIC-Fallout4
    python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); print('deferred_total:', d.get('summary', {}).get('deferred_total')); print('per_owner:', json.dumps(d.get('per_owner', {}), indent=2))"
    python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); print('tier1Mappings count:', len(d.get('tier1Mappings', [])))"

    # MEDIUM concern: verify the final gate rerun did not produce any parity-artifacts diff
    git status --porcelain ClassicLib-rs/node-bindings/classic-node/parity-artifacts/
    ```
    ALL commands MUST exit 0. The final `git status --porcelain` on parity-artifacts MUST be empty (no diff against the Task 2 commit). Record each exit code in the SUMMARY.

    Step 2 — Write `.planning/phases/04-node-tier-collapse/04-06-tier2-cleanup-cascade-SUMMARY.md` with:
    - Header: Phase 4 CLOSED, date, final commit SHA
    - Task 1 audit summary (total matches classified, any surprise LOAD_BEARING_EXCLUDED entries)
    - Task 2 atomic cascade confirmation (one commit SHA, all 5 gates green)
    - Placeholder-resolution loop iteration count (how many Phase 2c.1 iterations were needed to converge)
    - Task 3 final verification table mapping each ROADMAP Phase 4 Success Criterion → PASS/FAIL + evidence
    - Final metric table:
      | Metric | Phase 4 Start | Phase 4 Close |
      |--------|---------------|---------------|
      | tier1Mappings | 261 | <final count — expect ~383 based on 261 + 66 (Plan 2) + 34 (Plan 3 H2) + 7 (Plan 4 D1-restored) + ~15 (Plan 5 residuals)> |
      | deferred_total | 109 | 0 |
      | GLOBAL_FCX_HANDLER in backlog | yes | no (cleared Task 2) |
      | tierDefinitions.tier2 | present | absent (deleted Task 2) |
      | `validate_contract_surface()` guard | absent | present (Plan 1, with H1 fail-closed hardening) |
      | HARM-01/02 PE-version exports | absent | present (Plan 4, including D1-restored version-pe-shape row) |
    - Requirement closure table:
      | Requirement | Status | Evidence |
      |-------------|--------|----------|
      | NODE-01 | ✓ | RUST_TARGET_CRATES >= 19 (Plan 1) |
      | NODE-02 | ✓ | All deferred rows promoted across Plans 2-5 (66 + 34 + 7 + ~15 = ~122 net rows added) |
      | NODE-03 | ✓ | Tier-2 semantics removed in generated baselines (Task 2); governance backlog preserved but emptied until Phase 6 DOC-03 per U4 |
      | NODE-04 | ✓ | index.d.ts regenerated atomically (Plan 4) + freshness gate green |
      | NODE-05 | ✓ | bun run test:bun && test:node exit 0 |
      | NODE-06 | ✓ | deferred_total == 0 (Task 2 verified) |
      | HARM-01 | ✓ | extractPeVersion + isValidPePath NAPI exports (Plan 4); pub use is_valid_executable_path landed per A6 with U1 cross-binding probe green |
      | HARM-02 | ✓ | JsPeVersion typed object {major, minor, patch, build} (Plan 4); version-pe-shape row restored per D1 |
    - Known follow-ups for Phase 5 (CI enforcement) and Phase 6 (governance file deletion, HARM-05 doc)

    Step 3 — Commit as: `Docs(04): Phase 4 Node Tier Collapse CLOSED (Phase 4 Plan 6 Task 3)` with only the SUMMARY file.

    Step 4 — Update `.planning/STATE.md`:
    - `status: Phase 4 CLOSED`
    - `stopped_at: Phase 5 planning pending`
    - `last_activity: <today>`
    - Add key decisions entries summarizing Phase 4 outcomes to the Accumulated Context section

    Step 5 — Update `.planning/ROADMAP.md` Phase 4 entry to `[x]` checked with completion date.

    Step 6 — Commit STATE.md + ROADMAP.md updates as: `Docs(state): Phase 4 CLOSED; ROADMAP updated`.
  </action>
  <verify>
    <automated>python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); assert d.get('summary', {}).get('deferred_total') == 0"</automated>
  </verify>
  <acceptance_criteria>
    - `Test-Path .planning/phases/04-node-tier-collapse/04-06-tier2-cleanup-cascade-SUMMARY.md` returns `True`
    - `Select-String -Path .planning/phases/04-node-tier-collapse/04-06-tier2-cleanup-cascade-SUMMARY.md -Pattern 'Phase 4 CLOSED' -Quiet` returns `True`
    - `Select-String -Path .planning/phases/04-node-tier-collapse/04-06-tier2-cleanup-cascade-SUMMARY.md -Pattern 'deferred_total.*0' -Quiet` returns `True`
    - `Select-String -Path .planning/STATE.md -Pattern 'Phase 4.*CLOSED' -Quiet` returns `True`
    - `Select-String -Path .planning/ROADMAP.md -Pattern '\[x\].*Phase 4.*Node Tier Collapse' -Quiet` returns `True`
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node` exits 0 (final NO-OP verification)
  </acceptance_criteria>
  <done>
    Phase 4 CLOSED artifact written. STATE.md updated. ROADMAP.md updated. All 8 requirements (NODE-01..06, HARM-01, HARM-02) marked as satisfied with evidence. Phase 5 (CI enforcement) and Phase 6 (documentation reset) are unblocked.
  </done>
</task>

</tasks>

<verification>
Plan-level:
1. `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0
2. `python -m pytest tools/node_api_parity/tests/ -v` exits 0 (all tests pass normally, no xfail markers)
3. `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node && bun run dts:freshness:check` all exit 0
4. `runtime_coverage_summary.json::summary.deferred_total == 0`
5. `parity_contract.json::tierDefinitions` has only `tier1`
6. `deferred_runtime_backlog.json::entries == []` (preserved file shape per U4)
7. `Select-String -Path tools/node_api_parity/generate_baseline.py -Pattern 'tier2_gap_total|rust_unmapped|node_unmapped' -Quiet` returns `False` (none found)
8. M7 atomic commit exists with all cleanup changes in a single commit
</verification>

<success_criteria>
All 5 ROADMAP Phase 4 success criteria satisfied:
1. `bun run parity:gate:local` exits zero; 0 deferred entries; 0 Tier-1 drift ✓
2. `bun run test:bun && bun run test:node` pass with smoke tests per promoted module ✓
3. `bun run dts:freshness:check` passes against committed `index.d.ts` ✓
4. `extractPeVersion(path)` returns `{major, minor, patch, build}` typed object (HARM-01, HARM-02) ✓
5. **(U4 rewording)** `runtime_coverage_summary.md` reports `deferred_total == 0`; no Tier-2 SEMANTICS remain in generated baselines (`parity_contract.json`, `node_api_surface.json`, `parity_diff_report.json`); the governance backlog file `deferred_runtime_backlog.json` is preserved but emptied (`entries: []`) until Phase 6 DOC-03 deletion ✓

Phase 4 CLOSED.
</success_criteria>

<output>
`.planning/phases/04-node-tier-collapse/04-06-tier2-cleanup-cascade-SUMMARY.md` as specified in Task 3. SUMMARY must contain:
- Task 1 audit confirmation
- Task 2 atomic commit SHA and verification matrix
- Phase 2c.1 placeholder-resolution loop iteration count (how many times the loop converged)
- Task 3 requirement closure table (all 8 requirements ✓)
- Phase 4 CLOSED declaration
- Hand-off notes for Phase 5 (CI enforcement) and Phase 6 (documentation reset)
</output>
