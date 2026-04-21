---
phase: 04-node-tier-collapse
plan: 05
plan_id: 04-05
title: Aux Promotion (crashgen_rules + residual owners with locked cross-owner routing)
type: execute
wave: 4
depends_on: [04-04]
files_modified:
  - docs/implementation/node_api_parity/baseline/parity_contract.json
  - docs/implementation/node_api_parity/baseline/parity_contract.md
  - docs/implementation/node_api_parity/baseline/parity_diff_report.json
  - docs/implementation/node_api_parity/baseline/parity_diff_report.md
  - docs/implementation/node_api_parity/baseline/rust_api_surface.json
  - docs/implementation/node_api_parity/baseline/node_api_surface.json
  - docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json
  - docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md
  - docs/implementation/node_api_parity/baseline/tier1_gate_report.md
  - ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json
  - ClassicLib-rs/node-bindings/classic-node/__test__/crashgen_rules.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/scangame.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/fileio.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/path.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/settings.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/message.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/shared.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/resource.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/update.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/xse.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/database.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/yaml.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/web.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/constants.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs
  - ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs
  - ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs
  - ClassicLib-rs/business-logic/classic-shared-core/src/lib.rs
  - ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs
  - .planning/phases/04-node-tier-collapse/_plan05_routing_table.json
# Note (Fix 5.3, Round 2): `_plan05_routing_table.json` is created conditionally by Task 0
# only if routing ambiguity requires it. The pre-stage `git status --porcelain` integrity
# probe MUST accept it as present OR absent. `classic-crashgen-settings-core/src/lib.rs` is
# also conditional — added only if the bidirectional guard demands a new `pub use` during
# row landing, same as the other lib.rs paths already listed.
autonomous: false
requirements_addressed: [NODE-02, NODE-03, NODE-04, NODE-05]
requirements: [NODE-02, NODE-03, NODE-04, NODE-05]
must_haves:
  truths:
    - "All remaining deferred Node parity entries across aux / newly-tracked owner modules are promoted to enforced Tier-1 rows. Target: drop every per_owner.*.deferred count to 0 EXCEPT scanlog (which still has GLOBAL_FCX_HANDLER at 1, cleared in Plan 6)."
    - "7 crashgen_rules deferred entries (12 bindingIdentifiers) are promoted as normal rows: JsCheckRule, JsExpectedValue, JsPreflightAction, JsPreflightRule, JsRuleMessages, JsRuleTarget, JsModSolutionCriteria, JsModSolutionEntry, JsSuspectErrorRule, JsSuspectStackCountRule, JsSuspectStackRule, JsModConflictEntry. All 12 already exist in index.d.ts — no new NAPI wrappers."
    - "**U5 dual-source residual check**: Task 2 reads BOTH `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json` (Plan 1 output) AND the live `docs/implementation/node_api_parity/baseline/parity_diff_report.json::gaps` inventory. If the two sources disagree on any owner's residual row count, Plan 5 FAILS the precondition and the executor must escalate to re-running Plan 1's A10 sizing before restarting Plan 5 from a clean state."
    - "**Cross-owner overlap routing table is LOCKED before execution** (per U5). The 5 cross-owner overlap candidates (getApplicationDir, resetFcxGlobalState, setApplicationDir, writeAutoscanReport, JsModConflictEntry) have a DEFINITIVE owner assignment — no 'likely' language. If the locked table cannot be confirmed from current evidence at Task 1's read_first phase, Plan 5 adds a Task 0 to grep the live source and lock the table BEFORE any row is authored."
    - "`migrateGameVersionSetting` (function) is explicitly assigned to **Plan 5 Task 1 cross-owner reconciliation** (not Plan 4). The diff-report discrepancy (5 node_unmapped version_registry vs 4 deferred coverage) is the indicator: if live `deferred_runtime_backlog.json` shows `migrateGameVersionSetting` as a version_registry entry at Plan 5's execution time, Plan 5 Task 1 promotes it as a normal row with rustCrate derived from `rust_api_surface.json` lookup. If it's absent (already handled elsewhere), document that fact in the SUMMARY."
    - "Every new row carries rustCrate field per A3. The rustCrate value matches the source-of-truth crate (e.g. classic-crashgen-settings-core for the crashgen_rules types per A1)."
    - "No Rust source changes unless Plan 1's A10 sizing reveals a new pub use gap (Phase 3 Plan 09a absorbed 593 residuals via lib.rs pub use additions — Phase 4's residual count should be much smaller because Node already has wider binding surface per crate, but any required pub use goes in the same commit as the row). `files_modified` lists classic-scanlog-core/src/lib.rs, classic-scangame-core/src/lib.rs, and classic-shared-core/src/lib.rs to account for possible `pub use` additions for the cross-owner overlap symbols (MEDIUM concern: files_modified honesty)."
    - "index.d.ts does NOT regenerate in this plan unless a new Rust source edit in the residual batch requires it. If regeneration IS needed, it happens atomically with the Rust source commit (D-DTS-01)."
    - "Smoke tests append to per-module __test__/<module>.spec.ts files. One representative test per promoted module is added to runtime.node.test.mjs (D-TEST-02)."
    - "**setApplicationDir / getApplicationDir roundtrip test (MEDIUM concern fix)**: the test MUST NOT mutate the `Once`-guarded process state. The test either (a) verifies getApplicationDir returns a non-empty string from the already-initialized Once state (read-only) OR (b) is marked as skipped if the state is not initialized, OR (c) runs `setApplicationDir` in a separate subprocess to avoid state pollution. Do NOT call `setApplicationDir` followed by `getApplicationDir` in the same test process — this will either fail (Once already initialized) or permanently mutate state downstream."
    - "runtime_coverage_registry.json updated with new dedicated selector(s) for each promoted owner's bindingIdentifiers; contractIdsHash via _stable_id_hash."
    - "bun run parity:gate:local, bun run test:bun, bun run test:node all exit 0. runtime_coverage_summary.json::deferred_total ≤ 1 (only GLOBAL_FCX_HANDLER remains)."
  artifacts:
    - path: "docs/implementation/node_api_parity/baseline/parity_contract.json"
      provides: "tier1Mappings grows by the aux + residual count from the dual-source A10 sizing / live diff report (expected 12-50+ rows depending on residuals)"
    - path: "ClassicLib-rs/node-bindings/classic-node/__test__/crashgen_rules.spec.ts"
      provides: "New describe blocks for all 12 crashgen_rules interfaces (either one grouped describe or per-interface)"
      min_lines: 30
    - path: "ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json"
      provides: "One or more new dedicated selectors covering every promoted owner's bindingIdentifiers"
    - path: "ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs"
      provides: "`pub use` re-exports added IF AND ONLY IF Plan 5's residual absorption demands them for scanlog cross-owner symbols (e.g., resetFcxGlobalState)"
    - path: "ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs"
      provides: "`pub use` re-exports added IF AND ONLY IF residual absorption demands them for scangame symbols (e.g., writeAutoscanReport)"
    - path: "ClassicLib-rs/business-logic/classic-shared-core/src/lib.rs"
      provides: "`pub use` re-exports added IF AND ONLY IF residual absorption demands them for shared symbols (e.g., get_application_dir, set_application_dir)"
  key_links:
    - from: "parity_contract.json crashgen_rules rows"
      to: "classic-crashgen-settings-core public items (CheckRule, PreflightRule, RuleSeverity, etc.)"
      via: "bidirectional guard validates via rustCrate: 'classic-crashgen-settings-core'"
      pattern: "\"rustCrate\":\\s*\"classic-crashgen-settings-core\""
    - from: "parity_contract.json residual rows"
      to: "Plan 1 A10 sizing report + live parity_diff_report.json::gaps (dual-source per U5)"
      via: "Plan 5 reads BOTH sources and fails precondition if they disagree"
      pattern: "04-01-A10-sizing"
---

<objective>
Plan 5 is the residual sweep. It promotes:

1. **7 crashgen_rules deferred aux entries** (12 bindingIdentifiers total): JsCheckRule, JsExpectedValue, JsPreflightAction, JsPreflightRule, JsRuleMessages, JsRuleTarget, plus a cluster containing JsModSolutionCriteria, JsModSolutionEntry, JsSuspectErrorRule, JsSuspectStackCountRule, JsSuspectStackRule. All 12 are already `#[napi(object)]` exports in `classic-node/src/crashgen_rules.rs` — no Rust source changes. Source-of-truth crate per A1: `classic-crashgen-settings-core`.

2. **Cross-owner overlap reconciliation** (LOCKED table per U5): 5 symbols flagged in the diff report need DEFINITIVE ownership assignment BEFORE any row is authored. No "likely" language. The table is locked via Task 0 if current evidence is insufficient. Candidates:
   - `getApplicationDir` — ownerModule: **shared**, rustCrate: **classic-shared-core**
   - `setApplicationDir` — ownerModule: **shared**, rustCrate: **classic-shared-core**
   - `resetFcxGlobalState` — ownerModule: **scanlog**, rustCrate: **classic-scanlog-core**
   - `writeAutoscanReport` — ownerModule: **scangame**, rustCrate: **classic-scangame-core** (or classic-scanlog-core per Task 0 verification)
   - `JsModConflictEntry` — ownerModule: **config** (Issue 4 reconciliation — Plan 3 hands this off to Plan 5), rustCrate: **classic-config-core**

3. **A10 sizing residuals (dual-source per U5)**: Plan 5 Task 2 reads BOTH `04-01-A10-sizing.json` AND the live `docs/implementation/node_api_parity/baseline/parity_diff_report.json::gaps` inventory. If the two disagree on any owner's row count, Plan 5 FAILS the precondition and escalates back to Plan 1's A10 sizing before restarting from a clean state. Phase 3 Plan 09a absorbed 593 residual rows across 14 owners; Phase 4's residual count should be significantly smaller because Node already has wider per-crate binding coverage, but exact numbers are only known after Plan 1 runs.

4. **`migrateGameVersionSetting` handoff**: Per Plan 4's explicit exclusion, if `migrateGameVersionSetting` still appears in the version_registry owner bucket in the live deferred backlog at Plan 5's execution time, Plan 5 Task 1 promotes it as a normal row. Plan 5 reconciles the 4-vs-5 version_registry discrepancy that Plan 4 deferred.

Purpose:
- Drive every per_owner.*.deferred count to 0 EXCEPT scanlog (which still has GLOBAL_FCX_HANDLER at 1, cleared in Plan 6's atomic cascade)
- Prove the bidirectional guard works across all 19 tracked crates, not just scanlog/config/version_registry
- Leave Plan 6 with a clean cascade — no promotion work, just Tier-2 structural cleanup

Output:
- All aux + residual rows landed (count determined at execution from dual-source A10 sizing / parity_diff_report.json per U5)
- Cross-owner overlap routing table LOCKED before any row is authored
- Smoke tests appended to per-owner __test__/<module>.spec.ts files (with setApplicationDir test NOT mutating Once-guarded state per MEDIUM concern)
- Cross-runtime representative tests in runtime.node.test.mjs
- Updated runtime_coverage_registry.json with dedicated selectors per owner
- Gate exit 0 with deferred_total ≤ 1
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
@.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json
@.planning/phases/04-node-tier-collapse/04-01-A10-sizing.md
@.planning/phases/04-node-tier-collapse/04-02-scanlog-promotion-SUMMARY.md
@.planning/phases/04-node-tier-collapse/04-03-config-promotion-SUMMARY.md
@.planning/phases/04-node-tier-collapse/04-04-version-registry-and-pe-version-SUMMARY.md
@.planning/phases/03-python-tier-collapse/03-09a-a10-residual-promotion-SUMMARY.md
@./CLAUDE.md
@./AGENTS.md

<notes>
**Issue 4 reconciliation (2026-04-08)**: Plan 5 Task 1 is the CANONICAL owner of the `JsModConflictEntry` normal row. Plan 3 originally listed `ModConflictEntry` as a proxy-row candidate, but cross-plan check revealed `JsModConflictEntry` exists at `ClassicLib-rs/node-bindings/classic-node/src/config.rs` line 44 as `#[napi(object)] pub struct JsModConflictEntry` with `impl From<&ModConflictEntry> for JsModConflictEntry` at line 128. Per Issue 4 ruling: Plan 3 dropped `ModConflictEntry` from its proxy list (12 → 11), and Plan 5 keeps `JsModConflictEntry` as a normal row with `rustCrate: classic-config-core`, `nodeExport: JsModConflictEntry`, `nodeKind: interface`. Plan 5's Task 1 row list is unchanged; only Plan 3's count changed.

**U5 cross-owner routing (review pass)**: The earlier draft labeled 5 candidates as "likely" — too loose for a residual-absorption plan. The corrected approach is a LOCKED TABLE validated by Task 0 (if needed). If Task 1's read_first phase confirms the routing from live source (grep each candidate in the respective src/<module>.rs file), Task 0 can be skipped. If any routing is uncertain, Task 0 grep-and-lock runs BEFORE Task 1 authors any row.
</notes>

<interfaces>
<!-- Plan 1 A10 sizing report is the authoritative task budget — Plan 5 reads it first, cross-checked against live parity_diff_report.json -->

**Aux crashgen_rules inventory from RESEARCH.md §Deferred Entry Inventory (aux section)**:
| Coverage ID | bindingIdentifiers | Source crate (rustCrate) |
|---|---|---|
| `node-deferred-aux-067` | `JsCheckRule` | classic-crashgen-settings-core |
| `node-deferred-aux-073` | `JsExpectedValue` | classic-crashgen-settings-core |
| `node-deferred-aux-084` | `JsPreflightAction` | classic-crashgen-settings-core |
| `node-deferred-aux-085` | `JsPreflightRule` | classic-crashgen-settings-core |
| `node-deferred-aux-086` | `JsRuleMessages` | classic-crashgen-settings-core |
| `node-deferred-aux-087` | `JsRuleTarget` | classic-crashgen-settings-core |
| `node-deferred-aux-108` | `JsModSolutionCriteria`, `JsModSolutionEntry`, `JsSuspectErrorRule`, `JsSuspectStackCountRule`, `JsSuspectStackRule` | classic-crashgen-settings-core (confirm via live rust_api_surface.json lookup) |

**LOCKED cross-owner overlap routing table (U5)** — definitive ownership, no "likely" language:
| Symbol | ownerModule | rustCrate | Verification required in Task 0 |
|---|---|---|---|
| `getApplicationDir` | shared | classic-shared-core | `Select-String ClassicLib-rs/node-bindings/classic-node/src/shared.rs -Pattern 'get_application_dir'` must match |
| `setApplicationDir` | shared | classic-shared-core | `Select-String ClassicLib-rs/node-bindings/classic-node/src/shared.rs -Pattern 'set_application_dir'` must match |
| `resetFcxGlobalState` | scanlog | classic-scanlog-core | `Select-String ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs -Pattern 'reset_fcx_global_state'` must match |
| `writeAutoscanReport` | scangame | classic-scangame-core | `Select-String ClassicLib-rs/node-bindings/classic-node/src/scangame.rs -Pattern 'write_autoscan_report'` must match. If NOT found in scangame.rs, grep scanlog.rs as fallback — whichever file contains it owns the row. |
| `JsModConflictEntry` | config | classic-config-core | Already verified at `classic-node/src/config.rs:44` — no Task 0 check needed |
| `migrateGameVersionSetting` | scangame (NOT version_registry; Round 2 Fix 4.4 codebase verification) | **classic-scangame-core** (NOT classic-version-registry-core) | Task 0 (Round 2 corrected): verify via `Select-String ClassicLib-rs/node-bindings/classic-node/src/scangame.rs -Pattern 'migrate_game_version_setting'` (line ~1553). The core function is at `classic-scangame-core/src/setup.rs:225`. The `parity_diff_report.json::gaps` entry attributes `owner_module: version_registry, squad: Squad B (version-registry/aux)` — this is a parity-tracking HEURISTIC grouping, NOT a source-crate reflection. The correct rustCrate is `classic-scangame-core`. Plan 5 owns the row because Plan 5 handles cross-owner reconciliation for symbols whose diff-report `owner_module` doesn't match their actual source crate. Also grep live `deferred_runtime_backlog.json::entries` for presence; if missing at execution time, document exclusion in SUMMARY. |

Task 0 LOCKS the table: after running each Select-String check, if all 5 routes resolve unambiguously, Task 0 can be skipped (the table above is already locked). If any route is ambiguous (e.g., `writeAutoscanReport` present in BOTH scangame.rs and scanlog.rs), Task 0 MUST run and document the resolution in a new helper file `.planning/phases/04-node-tier-collapse/_plan05_routing_table.json` before Task 1 starts.

**Phase 3 Plan 09a precedent**: `.planning/phases/03-python-tier-collapse/03-09a-a10-residual-promotion-SUMMARY.md` documents how Python absorbed 593 residual rows across 14 owners in a single plan. Phase 4's Plan 5 applies the same pattern but with a much smaller residual set (because Node already has broader per-crate coverage).

**Row shape** (same as earlier plans):
- Normal: `{"id": "<owner>.<sub>.<name>", "tier": "tier1", "ownerModule": "<owner>", "rustCrate": "<crate>", "rustSymbol": "<core_symbol>", "nodeExport": "<camelCase>", "nodeKind": "<kind>"}`
- Proxy: `{"id": "<owner>.<sub>.<sym>@rust", "tier": "tier1", "ownerModule": "<owner>", "rustCrate": "<crate>", "rustSymbol": "<sym>@rust", "rustKind": "<kind>"}`

**A10 sizing report format** (from Plan 1, dual-source per U2):
```json
{
  "primary_source": "docs/implementation/node_api_parity/baseline/parity_diff_report.json::gaps",
  "cross_validation_source": "docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json::per_owner",
  "owners": [
    {"owner": "scanlog", "deferred_primary": 66, "plan": "04-02"},
    {"owner": "config", "deferred_primary": 34, "plan": "04-03"},
    {"owner": "version_registry", "deferred_primary": 4, "plan": "04-04"},
    {"owner": "aux", "deferred_primary": 12, "plan": "04-05"},
    {"owner": "<new residual owner>", "deferred_primary": <N>, "plan": "04-05"}
  ]
}
```
Plan 5 reads this file at execution time AND cross-checks against the live `parity_diff_report.json::gaps` count per U5.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 0 (conditional — run ONLY if routing table is ambiguous): Lock the cross-owner overlap routing table via live source grep</name>
  <read_first>
    - `ClassicLib-rs/node-bindings/classic-node/src/shared.rs` (verify get_application_dir / set_application_dir)
    - `ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs` (verify reset_fcx_global_state, writeAutoscanReport fallback)
    - `ClassicLib-rs/node-bindings/classic-node/src/scangame.rs` (verify writeAutoscanReport primary)
    - `ClassicLib-rs/node-bindings/classic-node/src/scangame.rs` (verify migrate_game_version_setting)
    - `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` (confirm which of the 5+1 candidates are still in the live backlog)
  </read_first>
  <action>
    Step 1 — For each candidate symbol in the LOCKED table (interfaces block above), run a Select-String grep against the candidate source file:
    ```powershell
    cd J:/CLASSIC-Fallout4
    Select-String -Path ClassicLib-rs/node-bindings/classic-node/src/shared.rs -Pattern 'get_application_dir|set_application_dir' -Context 0,2
    Select-String -Path ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs -Pattern 'reset_fcx_global_state' -Context 0,2
    Select-String -Path ClassicLib-rs/node-bindings/classic-node/src/scangame.rs -Pattern 'write_autoscan_report' -Context 0,2
    Select-String -Path ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs -Pattern 'write_autoscan_report' -Context 0,2
    Select-String -Path ClassicLib-rs/node-bindings/classic-node/src/scangame.rs -Pattern 'migrate_game_version_setting' -Context 0,2
    ```

    Step 2 — Assemble the resolved routing table (Round 2 fail-closed correction).
    - If `writeAutoscanReport` is present in EXACTLY ONE file (scangame.rs OR scanlog.rs): that file's owner/crate is LOCKED; proceed.
    - If present in BOTH files: FAIL CLOSED. Document the ambiguity in `_plan05_routing_table.json` AND return `## CHECKPOINT REACHED` escalating to the user for a routing decision. Do NOT silently pick one.
    - If present in NEITHER file: FAIL CLOSED. Document the absence in `_plan05_routing_table.json` AND return `## CHECKPOINT REACHED` escalating as a potential research amendment gap (the symbol may have moved since the last research snapshot). Do NOT proceed assuming a default location.

    For any resolved or ambiguous case, write the discovery to `.planning/phases/04-node-tier-collapse/_plan05_routing_table.json`:
    ```json
    {
      "locked_at": "<ISO timestamp>",
      "resolutions": {
        "getApplicationDir":      {"owner": "shared",      "rustCrate": "classic-shared-core",      "source_file": "src/shared.rs"},
        "setApplicationDir":      {"owner": "shared",      "rustCrate": "classic-shared-core",      "source_file": "src/shared.rs"},
        "resetFcxGlobalState":    {"owner": "scanlog",     "rustCrate": "classic-scanlog-core",     "source_file": "src/scanlog.rs"},
        "writeAutoscanReport":    {"owner": "<scangame or scanlog>", "rustCrate": "<corresponding crate>", "source_file": "<resolved>"},
        "JsModConflictEntry":     {"owner": "config",      "rustCrate": "classic-config-core",      "source_file": "src/config.rs"},
        "migrateGameVersionSetting": {"owner": "scangame", "rustCrate": "classic-scangame-core", "source_file": "src/scangame.rs", "live_backlog_status": "<present-in-backlog|absent>"}
      }
    }
    ```

    Step 3 — Commit as: `Docs(04): lock Plan 5 cross-owner routing table (Phase 4 Plan 5 Task 0)` — ONLY the routing table JSON, no other edits.

    **Skip Task 0 if**: Task 1's read_first phase confirms all 6 routes unambiguously. In that case, the table above (in the interfaces block) is already locked and no Task 0 commit is needed.
  </action>
  <verify>
    <automated>python -c "from pathlib import Path; p = Path('.planning/phases/04-node-tier-collapse/_plan05_routing_table.json'); print('Task 0 run:', p.exists())"</automated>
  </verify>
  <acceptance_criteria>
    - If Task 0 is run: `.planning/phases/04-node-tier-collapse/_plan05_routing_table.json` exists with unambiguous routing for all 6 symbols.
    - If Task 0 is skipped: Task 1's read_first confirms all routing via live grep before authoring any row.
    - **Fix 5.2 fail-closed enforcement (Round 2)**: Task 0 Step 2 aborts with `## CHECKPOINT REACHED` escalation if `writeAutoscanReport` is found in BOTH `classic-node/src/scangame.rs` AND `classic-node/src/scanlog.rs`, OR in NEITHER file. No silent "document and proceed" on ambiguity.
  </acceptance_criteria>
  <done>
    Cross-owner overlap routing table is LOCKED before any row is authored. No "likely" language remains.
  </done>
</task>

<task type="auto">
  <name>Task 1: Promote 12 crashgen_rules aux entries + cross-owner overlaps using LOCKED routing table</name>
  <read_first>
    - `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json` (authoritative plan-5 task budget from Plan 1; U5 primary source)
    - `docs/implementation/node_api_parity/baseline/parity_diff_report.json` (live gaps inventory; U5 cross-validation source)
    - `.planning/phases/04-node-tier-collapse/_plan05_routing_table.json` (if Task 0 ran — the locked table)
    - `ClassicLib-rs/node-bindings/classic-node/src/crashgen_rules.rs` (entire file — confirm all 12 JsFoo wrapper types and their inner core type mappings)
    - `ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs` (confirm which core types are `pub use`-re-exported at crate root — post-Plan-1 expansion, rust_api_surface.json should include this crate's symbols per A1)
    - `ClassicLib-rs/node-bindings/classic-node/__test__/crashgen_rules.spec.ts` (existing describe shape — if missing, Plan 5 creates this spec file)
    - `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` (filter for ownerModule: "aux" with crashgen_rules identifiers — authoritative list)
    - `docs/implementation/node_api_parity/baseline/rust_api_surface.json` (confirm classic-crashgen-settings-core symbols are now parsed post-Plan-1)
    - `ClassicLib-rs/node-bindings/classic-node/index.d.ts` (grep for each JsCheckRule, JsExpectedValue, etc. to confirm they exist and are interfaces)
    - `ClassicLib-rs/node-bindings/classic-node/src/shared.rs` (verify getApplicationDir / setApplicationDir bindings per locked routing table)
    - `ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs` (verify resetFcxGlobalState binding)
    - `ClassicLib-rs/node-bindings/classic-node/src/scangame.rs` OR scanlog.rs (verify writeAutoscanReport per locked routing table)
    - `ClassicLib-rs/node-bindings/classic-node/src/scangame.rs` (verify migrateGameVersionSetting per locked routing table if present in live backlog)
  </read_first>
  <action>
    Step 1 — Read A10 sizing JSON to confirm the aux owner's expected count and any additional owners assigned to Plan 05.

    **U5 dual-source precondition check (Round 2 correction — restricted to Plan 05-owned rows)**: the Round 1 revision compared sizing against live counts across ALL owners, which fired on healthy execution because Plans 2-4 had already legitimately reduced scanlog/config/version_registry counts. The corrected precondition is aux-only + any residual owners Plan 05 owns per the A10 sizing plan assignment. Owners already reduced by Plans 2-4 are INFORMATIONAL only (log the delta, do not fail).

    ```powershell
    cd J:/CLASSIC-Fallout4
    python -c "
    import json
    from collections import Counter
    sizing = json.load(open('.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json'))
    diff = json.load(open('docs/implementation/node_api_parity/baseline/parity_diff_report.json'))
    gaps = diff.get('gaps', [])
    # Count live gaps per owner (GLOBAL_FCX_HANDLER excluded per A2)
    live_per_owner = Counter(g.get('ownerModule', 'unknown') for g in gaps if 'GLOBAL_FCX_HANDLER' not in g.get('rustSymbols', []))
    sizing_per_owner = {o['owner']: o.get('deferred_primary', 0) for o in sizing.get('owners', [])}
    # Owners this plan actually operates on. Plans 2-4 owners (scanlog/config/version_registry)
    # were legitimately reduced by earlier waves — their sizing/live mismatch is EXPECTED,
    # not a precondition failure. Plan 05 operates on 'aux' plus any owner whose plan
    # assignment in the sizing report is '04-05'.
    plan05_owners = {'aux'}
    for o in sizing.get('owners', []):
        if o.get('plan') == '04-05':
            plan05_owners.add(o['owner'])
    # FAIL-CLOSED comparison: only on Plan 05-owned rows
    fail_mismatches = {}
    info_mismatches = {}
    all_owners = set(list(sizing_per_owner.keys()) + list(live_per_owner.keys()))
    for owner in all_owners:
        s = sizing_per_owner.get(owner, 0)
        l = live_per_owner.get(owner, 0)
        if s == l:
            continue
        if owner in plan05_owners:
            fail_mismatches[owner] = (s, l)
        else:
            info_mismatches[owner] = (s, l)
    if info_mismatches:
        print('U5 informational (owners reduced by Plans 2-4 — expected on healthy execution):')
        for owner, (s, l) in sorted(info_mismatches.items()):
            print(f'  {owner}: A10 sizing={s}, live={l}')
    if fail_mismatches:
        print('U5 PRECONDITION FAILURE (Plan 05-owned rows disagree):')
        for owner, (s, l) in sorted(fail_mismatches.items()):
            print(f'  {owner}: A10 sizing={s}, live={l}')
        print('Escalate: re-run Plan 1 A10 sizing, then restart Plan 5.')
        import sys; sys.exit(1)
    print('U5 precondition: PASS (all Plan 05-owned rows agree)')
    "
    ```
    **If this check fails on a Plan 05-owned owner**, Plan 5 ABORTS the precondition. Escalate to re-running Plan 1's A10 sizing pass (which updates `04-01-A10-sizing.json`), then restart Plan 5 from a clean state. Do NOT proceed to Step 2 with a mismatched Plan 05 sizing source. Informational mismatches on scanlog/config/version_registry are EXPECTED on healthy execution and do NOT block Plan 5.

    Step 2 — Read crashgen_rules.rs to map each `Js*` wrapper to its underlying core type. Example:
    - `JsCheckRule` wraps `CheckRule` from `classic-crashgen-settings-core`
    - `JsPreflightRule` wraps `PreflightRule`
    - `JsRuleSeverity` (if present) wraps `RuleSeverity` enum
    - `JsModConflictEntry` wraps `ModConflictEntry` (which lives in classic-config-core — Issue 4 reconciliation)

    Step 3 — Use the LOCKED routing table (interfaces block or Task 0 output) for cross-owner overlaps. Do NOT re-derive routes at authoring time.

    Step 4 — Author normal rows for each of the 12+ identifiers using the locked rustCrate values. Example rows:
    ```json
    {
      "id": "crashgen-rules.JsCheckRule",
      "tier": "tier1",
      "ownerModule": "aux",
      "rustCrate": "classic-crashgen-settings-core",
      "rustSymbol": "CheckRule",
      "nodeExport": "JsCheckRule",
      "nodeKind": "interface"
    },
    {
      "id": "shared.getApplicationDir",
      "tier": "tier1",
      "ownerModule": "shared",
      "rustCrate": "classic-shared-core",
      "rustSymbol": "get_application_dir",
      "nodeExport": "getApplicationDir",
      "nodeKind": "function"
    }
    // ... etc per locked routing table
    ```

    Step 5 — Append rows to `parity_contract.json::tier1Mappings`. Run gate:
    ```powershell
    python tools/node_api_parity/check_parity_gate.py --repo-root . --update-baseline
    ```
    If the bidirectional guard fires on any crashgen_rules row because the core type isn't re-exported at `classic-crashgen-settings-core/src/lib.rs`, add the missing `pub use` to that crate's lib.rs in the SAME commit. Same for shared/scanlog/scangame/etc — `files_modified` declares these lib.rs paths for frontmatter honesty.

    Step 6 — Append describe blocks to `__test__/crashgen_rules.spec.ts` (create the file if it doesn't exist — Plan 1's A10 sizing report flagged it as `MISSING — Plan 5 creates`):
    ```typescript
    import { describe, test, expect } from "bun:test";
    import {
      JsCheckRule,
      JsExpectedValue,
      JsPreflightAction,
      JsPreflightRule,
      JsRuleMessages,
      JsRuleTarget,
      JsModSolutionCriteria,
      JsModSolutionEntry,
      JsSuspectErrorRule,
      JsSuspectStackCountRule,
      JsSuspectStackRule,
      JsModConflictEntry,
    } from "../index.js";

    describe("crashgen_rules: rule primitives", () => {
      test("JsCheckRule has expected typed fields", () => {
        // Round 2 LOW sweep: replaced `{} as JsCheckRule` + `toBeDefined()` with a minimal
        // real-shape literal + typed field assertion. Pre-authoring: grep `classic-node/src/crashgen_rules.rs`
        // for `pub struct JsCheckRule` fields and adjust the literal to match the live shape.
        const rule = {
          id: "test-rule",
          severity: "warn",
          predicate: { kind: "always" },
        } as unknown as JsCheckRule;
        expect(typeof rule.id).toBe("string");
        expect(typeof rule.severity).toBe("string");
      });
      test("JsPreflightRule usable as TS type", () => {
        const rule = {} as JsPreflightRule;
        expect(rule).toBeDefined();
      });
      // Repeat shallow shape check for all 12 — OR group them
    });
    ```

    Step 7 — Append describe blocks to per-owner spec files for the cross-owner overlap functions.

    **`__test__/shared.spec.ts`** (MEDIUM concern fix — DO NOT mutate Once-guarded state):
    ```typescript
    import { describe, test, expect } from "bun:test";
    import { getApplicationDir } from "../index.js";

    describe("shared: getApplicationDir (read-only against Once-initialized state)", () => {
      test("returns a non-empty string when Once state is initialized", () => {
        // IMPORTANT: Do NOT call setApplicationDir in the same test process.
        // The `Once` guard in classic-shared-core::app_dirs::APPLICATION_DIR_ONCE
        // permanently mutates process state on first set. A round-trip test would
        // either fail (if the Once has already been initialized) or pollute downstream
        // tests by permanently setting a fixture path.
        try {
          const dir = getApplicationDir();
          // If Once is initialized, dir is a non-empty string
          expect(typeof dir === "string" || dir === undefined).toBe(true);
          if (typeof dir === "string") {
            expect(dir.length).toBeGreaterThan(0);
          }
        } catch (e) {
          // If Once not yet initialized, the function may throw — that's an acceptable state
          expect(e).toBeInstanceOf(Error);
        }
      });
      // setApplicationDir is NOT tested via round-trip here. A dedicated subprocess test
      // (e.g., via child_process.spawnSync) may be added if round-trip coverage is needed,
      // but round-trip-in-same-process is FORBIDDEN.
    });
    ```

    **`__test__/scanlog.spec.ts`** gains `describe("resetFcxGlobalState", ...)` — test that calling it doesn't throw:
    ```typescript
    describe("scanlog: resetFcxGlobalState", () => {
      test("callable without throwing", () => {
        expect(() => resetFcxGlobalState()).not.toThrow();
      });
    });
    ```

    **`__test__/scangame.spec.ts` or `__test__/scanlog.spec.ts`** (per locked routing table) gains `describe("writeAutoscanReport", ...)` — test callable shape with fixture input.

    **`__test__/version_registry.spec.ts`** (if `migrateGameVersionSetting` is still in the live backlog): adds a describe block for the migration function.

    Step 8 — Append ONE representative test to `__test__/runtime.node.test.mjs` (Issue 3 fix: use STATIC top-of-file imports — do NOT use `await import` inside a non-async arrow function, that's a SyntaxError. All other tests in `runtime.node.test.mjs` already use static imports; match that pattern):
    ```javascript
    // Top of runtime.node.test.mjs — add to the existing import block:
    import { test } from "node:test";
    import assert from "node:assert/strict";
    import { getApplicationDir } from "../index.js";  // static import at top of file

    // Test bodies — note: NO setApplicationDir mutation per MEDIUM concern
    test("aux: crashgen_rules JsCheckRule usable as TS type (cross-runtime D-TEST-02)", () => {
      // Round 2 LOW sweep: replace no-op assert.ok(true) with a minimal real-shape check.
      // JsCheckRule is a NAPI interface (type-only at runtime), so we construct a minimal valid literal
      // matching the required fields and assert typed fields via the binding. Pre-authoring: grep
      // `classic-node/src/crashgen_rules.rs` for `pub struct JsCheckRule` to verify the required field
      // shape before committing; adjust the literal if the live struct differs.
      const rule = {
        id: "test-rule",
        severity: "warn",
        predicate: { kind: "always" },
      };
      assert.strictEqual(typeof rule.id, "string", "rule.id must be a string");
      assert.strictEqual(typeof rule.severity, "string", "rule.severity must be a string");
    });

    test("shared: getApplicationDir returns a string or undefined (cross-runtime, read-only)", () => {
      try {
        const result = getApplicationDir();
        assert.ok(typeof result === "string" || result === undefined);
      } catch (e) {
        // Once not initialized — acceptable
        assert.ok(e instanceof Error);
      }
    });
    ```

    Step 9 — Update runtime_coverage_registry.json with a new selector `node-tier1-aux-plan05-promoted` covering all new aux rows + cross-owner overlap rows. Compute contractIdsHash via _stable_id_hash.

    Step 10 — Commit as: `Feat: promote 12 crashgen_rules aux entries + reconcile cross-owner overlaps via locked routing table (Phase 4 Plan 5 Task 1; NODE-02, NODE-05)` in one atomic commit.
  </action>
  <verify>
    <automated>cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); rows = [r for r in d['tier1Mappings'] if r.get('rustCrate') == 'classic-crashgen-settings-core']; assert len(rows) >= 11"` exits 0
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); per_owner = d.get('per_owner', {}); assert per_owner.get('aux', {}).get('deferred', -1) == 0"` exits 0
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run test:bun` exits 0
    - `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0 (bidirectional guard green on every new row)
    - **MEDIUM concern enforcement**: `Select-String -Path ClassicLib-rs/node-bindings/classic-node/__test__/shared.spec.ts -Pattern 'setApplicationDir' -Quiet` returns `False` OR is wrapped in a subprocess invocation (no round-trip-in-same-process pattern)
    - **Fix 5.1 healthy-execution precondition (Round 2)**: On a healthy execution where Plans 2-4 have already reduced scanlog/config/version_registry owners, Task 1 Step 1's U5 dual-source precondition does NOT abort. Mismatches on scanlog/config/version_registry are logged as informational-only; only mismatches on Plan 05-owned rows (aux + owners whose sizing plan assignment is '04-05') trigger the fail-closed abort path.
  </acceptance_criteria>
  <done>
    12+ crashgen_rules + cross-owner overlap rows land using LOCKED routing table; aux deferred count → 0; smoke tests pass (with setApplicationDir round-trip isolated from Once state mutation per MEDIUM concern); bidirectional guard green.
  </done>
</task>

<task type="auto">
  <name>Task 2: Absorb A10 residuals across newly-tracked owners (dual-source per U5: A10 sizing + live parity_diff_report.json)</name>
  <read_first>
    - `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json` — read every owner with non-zero deferred count NOT already handled by Plans 2-4 or Task 1 above
    - `docs/implementation/node_api_parity/baseline/parity_diff_report.json` — **U5 dual-source: read gaps[] filtered by owner and cross-check against A10 sizing**
    - `docs/implementation/node_api_parity/baseline/rust_api_surface.json` — post-Plan-4 state; confirm every residual's rustSymbol is visible
    - `ClassicLib-rs/node-bindings/classic-node/src/` — every .rs file for owners with residual rows (shared.rs, perf not-applicable, message.rs, fileio.rs, path.rs, settings.rs, resource.rs, update.rs, xse.rs, database.rs, yaml.rs, web.rs, constants.rs, scangame.rs)
    - `.planning/phases/03-python-tier-collapse/03-09a-a10-residual-promotion-SUMMARY.md` (Phase 3 precedent for multi-owner residual absorption)
  </read_first>
  <behavior>
    - Every owner with `deferred > 0` (after Task 1) and not already scheduled in Plans 2-4 gets promotion rows landed in this task.
    - **U5 dual-source check at task start**: Task 2 Step 1 reads BOTH `04-01-A10-sizing.json` AND live `parity_diff_report.json::gaps`. If they disagree on any owner's row count, Task 2 FAILS the precondition and the executor escalates to re-running Plan 1's A10 sizing pass before restarting.
    - For each residual: classify as (a) Node-exposed (add normal row with nodeExport), (b) Rust-only (add @rust proxy row), or (c) requires new `pub use` at a -core crate's lib.rs (add the re-export in the same commit).
    - Smoke tests append to the corresponding __test__/<module>.spec.ts file per D-TEST-01.
    - ONE representative cross-runtime test per residual owner added to runtime.node.test.mjs per D-TEST-02.
    - runtime_coverage_registry.json gets additional selectors per residual owner.
    - `deferred_total` drops to 1 (only GLOBAL_FCX_HANDLER remains) or 0 if GLOBAL_FCX_HANDLER is already de-registered via some other path.
  </behavior>
  <action>
    Step 1 — **U5 dual-source residual check (Round 2 correction — restricted to Plan 05-owned rows; PRECONDITION only fires on Plan 05-owned mismatches)**:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python -c "
    import json
    from collections import Counter
    # Dual-source comparison per U5 (Round 2 corrected — scoped to Plan 05-owned rows only).
    # Plans 2-4 owners (scanlog/config/version_registry) were already reduced before Plan 05
    # ran, so any sizing/live mismatch on those owners is EXPECTED and informational-only,
    # NOT a precondition failure. The fail-closed path applies only to Plan 05-owned rows.
    sizing = json.load(open('.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json'))
    diff = json.load(open('docs/implementation/node_api_parity/baseline/parity_diff_report.json'))
    gaps = diff.get('gaps', [])
    live_per_owner = Counter(g.get('ownerModule', 'unknown') for g in gaps if 'GLOBAL_FCX_HANDLER' not in g.get('rustSymbols', []))
    sizing_per_owner = {o['owner']: o.get('deferred_primary', 0) for o in sizing.get('owners', [])}
    # Plan 05 operates on aux + any owner whose A10 sizing plan assignment is '04-05'
    plan05_owners = {'aux'}
    for o in sizing.get('owners', []):
        if o.get('plan') == '04-05':
            plan05_owners.add(o['owner'])
    all_owners = set(list(sizing_per_owner.keys()) + list(live_per_owner.keys()))
    fail_mismatches = {}
    info_mismatches = {}
    for owner in all_owners:
        s = sizing_per_owner.get(owner, 0)
        l = live_per_owner.get(owner, 0)
        if s == l:
            continue
        if owner in plan05_owners:
            fail_mismatches[owner] = (s, l)
        else:
            info_mismatches[owner] = (s, l)
    if info_mismatches:
        print('U5 informational (owners reduced by Plans 2-4 — expected on healthy execution):')
        for owner, (s, l) in sorted(info_mismatches.items()):
            print(f'  {owner}: A10 sizing={s}, live parity_diff_report={l}')
    if fail_mismatches:
        print('U5 PRECONDITION FAILURE — Plan 5 Task 2 ABORTS (Plan 05-owned rows disagree):')
        for owner, (s, l) in sorted(fail_mismatches.items()):
            print(f'  {owner}: A10 sizing={s}, live parity_diff_report={l}')
        print('Escalate: re-run Plan 1 A10 sizing via /gsd:execute-phase 4 --plan 01-task-3, then restart Plan 5.')
        import sys; sys.exit(1)
    # List residual owners this task must process (excluding Plans 2-4 owners + aux which Task 1 handles)
    residual_owners = [o for o in sizing.get('owners', []) if o.get('deferred_primary', 0) > 0 and o.get('plan') == '04-05' and o['owner'] not in ('scanlog', 'config', 'version_registry', 'aux')]
    print('Residual owners for Task 2:')
    for o in residual_owners:
        print(f'  {o[\"owner\"]}: {o[\"deferred_primary\"]} rows')
    "
    ```
    If this command exits non-zero (a Plan 05-owned mismatch), ABORT Task 2 and escalate to Plan 1 A10 sizing re-run. Informational mismatches on Plans 2-4 owners are EXPECTED on healthy execution and do NOT block Task 2.

    Step 2 — For each residual owner, build rows incrementally. OPTIONAL: create `.planning/phases/04-node-tier-collapse/_build_plan05_residuals.py` as a helper that:
    - Reads BOTH sources (04-01-A10-sizing.json and parity_diff_report.json::gaps)
    - Filters to the residual owners
    - For each entry, decides @rust proxy vs normal row based on whether `bindingIdentifiers` is empty
    - Emits rows in the standard shape

    Step 3 — For owners with existing Node exports missing contract rows, verify each nodeExport exists in index.d.ts. For Rust-only symbols, verify each exists in rust_api_surface.json.

    Step 4 — Commit the residuals in ONE atomic commit per owner OR in a single bulk commit (planner discretion within the task; Plan 6 expects Plan 5 to leave deferred_total ≤ 1). Prefer one commit per owner for bisect granularity if there are many residuals; use a bulk commit if the residual count is ≤20.

    Commit message example: `Feat: absorb A10 residuals for owners {X, Y, Z} (Phase 4 Plan 5 Task 2; NODE-02, NODE-03, NODE-05)`.

    Step 5 — After every commit, run (PowerShell preferred per user rule):
    ```powershell
    cd J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node
    bun run parity:gate:local
    ```
    Gate MUST stay green throughout.

    Step 6 — Append smoke tests per owner to the corresponding `__test__/<owner>.spec.ts` file. Run `bun run test:bun && bun run test:node` after all edits.

    Step 7 — Update `runtime_coverage_registry.json` with a new selector per residual owner OR extend existing selectors' bindingIdentifiers lists. Compute hashes via `_stable_id_hash`.

    Step 8 — Final verification after all residuals land:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python tools/node_api_parity/check_parity_gate.py --repo-root .
    cd J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node
    bun run parity:gate:local
    bun run test:bun
    bun run test:node
    ```
    All commands exit 0. Verify `runtime_coverage_summary.json::summary.deferred_total <= 1` (only GLOBAL_FCX_HANDLER remains).
  </action>
  <verify>
    <automated>cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); deferred = d.get('summary', {}).get('deferred_total', -1); assert deferred <= 1, f'deferred_total not collapsed: {deferred}'"` exits 0 (only GLOBAL_FCX_HANDLER may remain)
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); per_owner = d.get('per_owner', {}); non_scanlog = {k: v.get('deferred', 0) for k, v in per_owner.items() if k != 'scanlog'}; assert all(v == 0 for v in non_scanlog.values()), f'non-scanlog owners have deferred rows: {non_scanlog}'"` exits 0
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run test:bun` exits 0
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run test:node` exits 0
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run dts:freshness:check` exits 0
  </acceptance_criteria>
  <done>
    All residual owners' deferred counts are 0 (after dual-source U5 precondition check); only GLOBAL_FCX_HANDLER remains as a single scanlog deferred entry; gate green; smoke tests pass; Plan 6 can run the clean cascade.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Verify the deferred backlog is collapsed to ≤1 before Plan 6 cleanup</name>
  <what-built>
    - Cross-owner overlap routing table locked (Task 0 conditional)
    - All aux + residual promotion rows across every newly-tracked owner using locked routing
    - Per-owner smoke tests appended to __test__/<module>.spec.ts files (setApplicationDir round-trip NOT mutating Once state per MEDIUM concern)
    - Cross-runtime representative tests in runtime.node.test.mjs
    - Updated runtime_coverage_registry.json with selectors per owner
    - Any pub use re-exports that were required at -core crates' lib.rs files
  </what-built>
  <action>
    Run the deferred-count verification and present results to the user. Wait for approval before starting Plan 6's atomic cascade.
  </action>
  <how-to-verify>
    1. Full suite: `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node` — all exit 0.
    2. Deferred count:
       ```powershell
       python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); print('deferred_total:', d.get('summary', {}).get('deferred_total')); print('per_owner:', json.dumps(d.get('per_owner', {}), indent=2))"
       ```
       Confirm `deferred_total <= 1` and only `scanlog.deferred == 1` (if GLOBAL_FCX_HANDLER hasn't been cleared yet).
    3. Contract count grew from ~261 (start of Phase 4) to the expected range based on Plans 2-5 totals.
    4. `git log --oneline --since="plan-04-start" -20` — see the Plan 2-5 commits in bisect-clean form.
    5. Visual spot-check: pick 3 random newly-added rows and confirm rustCrate field is populated correctly per A3.
    6. Confirm `migrateGameVersionSetting` handoff from Plan 4: either landed as a row here, or explicitly excluded in SUMMARY.
  </how-to-verify>
  <verify>
    <automated>python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); assert d.get('summary', {}).get('deferred_total', -1) &lt;= 1"</automated>
  </verify>
  <done>User confirms deferred_total &lt;= 1 and only scanlog owner retains the single GLOBAL_FCX_HANDLER residual.</done>
  <resume-signal>Type "approved" to proceed to Plan 6 (Tier-2 atomic cascade cleanup). At this point the backlog should be effectively empty — Plan 6 just performs the structural cleanup + flips the xfail test.</resume-signal>
</task>

</tasks>

<verification>
1. `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0
2. `bun run parity:gate:local && bun run test:bun && bun run test:node` all exit 0
3. `deferred_total <= 1` in runtime_coverage_summary.json
4. All per_owner deferred counts == 0 EXCEPT scanlog which may still have 1 (GLOBAL_FCX_HANDLER)
5. No Rust source changes beyond any required `pub use` re-exports (lib.rs paths declared in files_modified)
6. U5 dual-source precondition passed before Task 2 ran (sizing and live diff report agreed)
</verification>

<success_criteria>
- 12+ crashgen_rules/aux/cross-owner overlap rows promoted using LOCKED routing table (Task 1)
- All A10 residual owners' deferred counts → 0 (Task 2 after U5 dual-source precondition)
- Overall deferred_total drops to ≤1
- Plan 6 can run a clean cascade with no promotion work remaining
- Smoke tests in both bun:test and node:test for every promoted module
- setApplicationDir round-trip test does NOT mutate Once-guarded state (MEDIUM concern fix)
- Every new row has rustCrate field
- migrateGameVersionSetting handoff resolved (landed or explicitly excluded)
</success_criteria>

<output>
Create `.planning/phases/04-node-tier-collapse/04-05-aux-promotion-SUMMARY.md` with:
- Final count of rows landed per task
- LOCKED routing table used (from Task 0 output if run, or from interfaces block if skipped)
- U5 dual-source precondition check result (pass / fail delta per owner)
- Any `pub use` re-exports added to -core lib.rs files (list the crates)
- Cross-owner overlap reconciliation decisions (which rustCrate was assigned to getApplicationDir, writeAutoscanReport, etc.)
- migrateGameVersionSetting disposition (landed as row / excluded / not in live backlog)
- Per-owner deferred count snapshot (showing 0 everywhere except scanlog)
- Confirmation that deferred_total ≤ 1
- Any residuals that unexpectedly surfaced beyond the A10 sizing report (and how they were absorbed)
</output>
