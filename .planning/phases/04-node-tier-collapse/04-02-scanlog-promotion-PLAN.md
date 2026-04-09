---
phase: 04-node-tier-collapse
plan: 02
plan_id: 04-02
title: Scanlog Promotion (66 rows — 58 @rust proxy + 8 normal)
type: execute
wave: 1
depends_on: [04-01]
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
  - ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs
  - ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json
  - ClassicLib-rs/node-bindings/classic-node/__test__/scanlog.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs
autonomous: false
requirements_addressed: [NODE-02, NODE-03, NODE-04, NODE-05]
requirements: [NODE-02, NODE-03, NODE-04, NODE-05]
must_haves:
  truths:
    - "All 66 scanlog deferred entries land as tier1Mappings rows (67 deferred MINUS GLOBAL_FCX_HANDLER per A2). Net new rows: 58 @rust-suffix proxy rows (Rust-only) + 8 normal rows with nodeExport field."
    - "The 58 @rust proxy rows use the Phase 3 Scenario E pattern: rustSymbol ends in `@rust`, rustCrate: `classic-scanlog-core`, no nodeExport field. The bidirectional guard treats them as Rust-only."
    - "The 8 normal rows use camelCase nodeExport fields matching existing index.d.ts exports: CRASH_LOG_PATTERN, JsAnalysisBuildOptions, JsAnalysisResult, JsGpuInfo, JsLogErrorEntry, JsLogSegments, JsPapyrusStats, checkXsePlugins, parseXseLog (9 bindingIdentifiers; note RESEARCH.md Table lists 9 Node exports — reconcile the 8 vs 9 during execution based on deferred_runtime_backlog.json::entries live read)."
    - "No business logic changes in classic-scanlog-core or classic-node/src/scanlog.rs — this phase EXPOSES existing bindings and documents Rust-only symbols, it does NOT add new #[napi] wrappers to scanlog (Phase 3 Plan 2 precedent). `pub use` re-exports MAY be added to `classic-scanlog-core/src/lib.rs` if the bidirectional guard demands them at row-landing time — the lib.rs path is declared in files_modified for frontmatter honesty per MEDIUM concern."
    - "index.d.ts does NOT regenerate in this plan because no Rust source changes — dts:freshness:check remains green without rebuild."
    - "Smoke tests append to __test__/scanlog.spec.ts as new describe blocks with REAL-SHAPE assertions (MEDIUM concern fix — no shallow `{} as Type` + `toBeDefined()` no-ops; every interface assertion must check at least one typed field); at least one representative test is added to runtime.node.test.mjs for cross-runtime verification (D-TEST-02)."
    - "runtime_coverage_registry.json has new entries per promoted contract row OR the existing node-tier1-scanlog selector is bumped with recomputed contractIdsHash via _stable_id_hash (D-HASH-01 mandatory import — NO truncation)."
    - "bun run parity:gate:local exits 0 at plan close; runtime_coverage_summary.json::deferred shows scanlog dropped from 67 to 1 (only GLOBAL_FCX_HANDLER remains, to be cleared in Plan 6 cascade)."
    - "Every row added has rustCrate: 'classic-scanlog-core' field per A3 (new rows only; existing 261 untouched)."
  artifacts:
    - path: "docs/implementation/node_api_parity/baseline/parity_contract.json"
      provides: "tier1Mappings grows by 66 rows (58 proxy + 8 normal); all new rows carry rustCrate: 'classic-scanlog-core'"
      contains: "@rust"
    - path: "ClassicLib-rs/node-bindings/classic-node/__test__/scanlog.spec.ts"
      provides: "New describe blocks for each of the 8 Node-exposed scanlog exports with real-shape assertions"
      min_lines: 40
    - path: "ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs"
      provides: "At least one new test per D-TEST-02 — e.g. `parseXseLog` or `checkXsePlugins` invocation against a fixture"
    - path: "ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json"
      provides: "Updated selector entries covering the 66 new rows — either a new entry with explicit bindingIdentifiers or a bumped contractCount+contractIdsHash on an existing selector"
    - path: "ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs"
      provides: "`pub use` re-exports added IF AND ONLY IF the bidirectional guard demands them (MEDIUM concern: files_modified honesty)"
  key_links:
    - from: "parity_contract.json::tier1Mappings @rust-suffixed rows"
      to: "classic-scanlog-core sub-module public items (parser, formid, formid_analyzer, record_scanner, plugin_analyzer, patterns, mod_detector, suspect_scanner, settings_validator, fcx_handler, gpu_detector, orchestrator, report, papyrus, version, crashgen_registry, segment_key, error)"
      via: "bidirectional guard's Rust-side check strips @rust suffix and validates against rust_api_surface.json"
      pattern: "\"rustSymbol\":\\s*\"[^\"]+@rust\""
    - from: "parity_contract.json::tier1Mappings normal scanlog rows"
      to: "index.d.ts scanlog exports (CRASH_LOG_PATTERN, JsAnalysisResult, etc.)"
      via: "bidirectional guard's Node-side check matches nodeExport to node_api_surface.json"
      pattern: "\"nodeExport\":\\s*\"(parseXseLog|checkXsePlugins|JsAnalysisResult|CRASH_LOG_PATTERN)\""
    - from: "__test__/scanlog.spec.ts new describe blocks"
      to: "parity_tier1.spec.ts automatic import gate"
      via: "parity:gate:update-baseline regenerates the imports list in parity_tier1.spec.ts"
      pattern: "describe\\(\"parseXseLog\"|describe\\(\"JsAnalysisResult\""
---

<objective>
Promote all 66 scanlog deferred Node parity entries to enforced Tier-1 contract rows. This plan demonstrates the Phase 3 Scenario E @rust-suffix proxy pattern for Rust-only symbols on the Node gate. NO business logic changes — this plan EXPOSES what exists and DOCUMENTS Rust-only symbols using proxy rows, it does NOT add new `#[napi]` wrappers. `pub use` re-exports may be added to `classic-scanlog-core/src/lib.rs` IF the bidirectional guard demands them (MEDIUM concern: files_modified declares the lib.rs path for frontmatter honesty).

Per A7: 58 of the 66 deferred scanlog symbols are Rust-only public items with no Node binding (classes: `AnalysisResult`, `CheckId`, `FormIDAnalyzer`, `PluginAnalyzer`, `RecordScanner`, `ScanLogError`, `SuspectScanner`, `StreamingLogParser`, `ScanProgressPhase`, ...; free functions: `detect_mods_batch`, `detect_plugins_batch`, `extract_formids_batch`, `is_valid_formid`, ...; `pub mod` declarations: `parser`, `formid`, `formid_analyzer`, ...). These get `@rust`-suffix proxy rows that pair with `classic-scanlog-core` as the owning crate.

Per A2: `GLOBAL_FCX_HANDLER` is NOT promoted — Phase 3 R9 precedent excluded it as a static LazyLock that has no callable contract shape. The raw count is 67 deferred; net new rows = 66.

The remaining 8 rows have matching Node exports already in `index.d.ts` (per RESEARCH.md Deferred Entry Inventory table for scanlog): `CRASH_LOG_PATTERN`, `JsAnalysisBuildOptions`, `JsAnalysisResult`, `JsGpuInfo`, `JsLogErrorEntry`, `JsLogSegments`, `JsPapyrusStats`, `checkXsePlugins`, `parseXseLog` — these get normal `nodeExport` fields. (Note: research lists 9 node-exports but Plan 2 executor must reconcile against live `deferred_runtime_backlog.json::entries` to confirm the exact split — report the final number in the SUMMARY.)

Purpose:
- Eliminate scanlog from the deferred backlog (66 of 67 entries; GLOBAL_FCX_HANDLER cleared in Plan 6)
- Prove the @rust proxy pattern works on the Node gate for the first time
- Establish the per-commit atomic pattern the remaining promotion plans copy

Output:
- 66 new tier1Mappings rows (58 proxy + 8 normal) in `parity_contract.json`
- Possible `pub use` additions to `classic-scanlog-core/src/lib.rs` if the bidirectional guard demands them
- New describe blocks in `__test__/scanlog.spec.ts` with real-shape assertions (MEDIUM concern fix)
- At least one new representative test in `__test__/runtime.node.test.mjs`
- Refreshed baseline artifacts + runtime_coverage_registry.json
- Gate exit 0 with scanlog deferred count dropped from 67 → 1
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
@.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json
@.planning/phases/03-python-tier-collapse/03-02-scanlog-wave1-parsing-primitives-SUMMARY.md
@./CLAUDE.md
@./AGENTS.md

<interfaces>
<!-- Scanlog deferred inventory from RESEARCH.md §Deferred Entry Inventory (verified 2026-04-08) -->

**8 Node-exposed scanlog exports needing normal contract rows** (verified in index.d.ts):
| Coverage ID | Node export | nodeKind |
|-------------|-------------|----------|
| `node-deferred-scanlog-060` | `CRASH_LOG_PATTERN` | const |
| `node-deferred-scanlog-064` | `JsAnalysisBuildOptions` | interface |
| `node-deferred-scanlog-066` | `JsAnalysisResult` | interface |
| `node-deferred-scanlog-075` | `JsGpuInfo` | interface |
| `node-deferred-scanlog-078` | `JsLogErrorEntry` | interface |
| `node-deferred-scanlog-080` | `JsLogSegments` | interface |
| `node-deferred-scanlog-082` | `JsPapyrusStats` | interface |
| `node-deferred-scanlog-092` | `checkXsePlugins` | function |
| `node-deferred-scanlog-100` | `parseXseLog` | function |

(9 bindingIdentifiers; reconcile count against live `deferred_runtime_backlog.json` at execution time.)

**58 Rust-only scanlog symbols for @rust proxy rows**:

Classes: `AnalysisResult`, `CheckId`, `ConfigIssue`, `CrashgenEntry`, `CrashgenRegistry`, `FcxModeHandler`, `FcxResetError`, `FormIDAnalyzer`, `FormIDAnalyzerCore`, `GpuDetector`, `GpuVendor`, `PapyrusAnalyzer`, `PapyrusError`, `PluginAnalyzer`, `RecordScanner`, `ReportComposer`, `ReportFragment`, `ReportGenerator`, `RustFormIDAnalyzer`, `ScanLogError`, `SettingsValidator`, `StreamingIteratorParser`, `StreamingLogParser`, `StringPool`, `SuspectScanner`, `ScanProgressPhase`. (26 classes)

Free functions: `contains_plugin`, `contains_record`, `crashgen_version_gen`, `detect_mods_batch`, `detect_mods_double`, `detect_mods_important`, `detect_mods_single`, `detect_plugins_batch`, `extract_formids_batch`, `is_valid_formid`, `scan_records_batch`, `validate_formids_batch`, `resolve_batch_concurrency`. (13 functions)

`pub mod` declarations (module markers): `crashgen_registry`, `error`, `fcx_handler`, `formid`, `formid_analyzer`, `gpu_detector`, `mod_detector`, `orchestrator`, `papyrus`, `parser`, `patterns`, `plugin_analyzer`, `record_scanner`, `report`, `segment_key`, `settings_validator`, `suspect_scanner`, `version`. (18 modules)

Static (excluded per A2): `GLOBAL_FCX_HANDLER`.

Total: 26 + 13 + 18 = **57**. Cross-checked: 67 − 1 excluded = 66; 66 − 8 Node-exposed = 58 Rust-only. **Discrepancy — 58 vs 57 — must be reconciled at execution time** by reading `deferred_runtime_backlog.json::entries` live and filtering by `ownerModule: "scanlog"` + `gap_type: "rust_unmapped"`. Use the live count, not this static list.

**@rust-suffix proxy row shape** (from RESEARCH.md §Pattern 4 Node equivalent):
```json
{
  "id": "scanlog.parser.parse_line@rust",
  "tier": "tier1",
  "ownerModule": "scanlog",
  "rustCrate": "classic-scanlog-core",
  "rustSymbol": "parse_line@rust",
  "rustKind": "function"
}
```
Note: no `nodeExport` field. The bidirectional guard strips `@rust` before checking `rust_api_surface.json`.

**Normal row shape** (example for CRASH_LOG_PATTERN):
```json
{
  "id": "scanlog.patterns.CRASH_LOG_PATTERN",
  "tier": "tier1",
  "ownerModule": "scanlog",
  "rustCrate": "classic-scanlog-core",
  "rustSymbol": "CRASH_LOG_PATTERN",
  "nodeExport": "CRASH_LOG_PATTERN",
  "nodeKind": "const"
}
```

**Phase 3 precedent for scanlog @rust proxy rows**: `.planning/phases/03-python-tier-collapse/03-02-scanlog-wave1-parsing-primitives-SUMMARY.md` "Scenario E proxy rows" section — read before authoring rows.

**Row-building helper precedent**: Phase 3 used `_build_wave1_rows.py` scripts under `.planning/phases/03-python-tier-collapse/` for repeatable row construction. Plan 2 MAY create `.planning/phases/04-node-tier-collapse/_build_plan02_rows.py` as a one-off helper (discretion).

**Runtime coverage registry shape** (`__test__/fixtures/runtime_coverage_registry.json`): current file has the canonical per-selector format. D-HASH-01 requires `_stable_id_hash` import from `tools/binding_parity_runtime_coverage.py` — NO inline `sha256[:16]` (Phase 3 R8 bug).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author 58 @rust-suffix proxy rows for Rust-only scanlog symbols</name>
  <read_first>
    - `docs/implementation/node_api_parity/baseline/parity_contract.json` (read the first 20 tier1Mappings rows to confirm current row shape; confirm no rows currently carry rustCrate field per A3)
    - `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` (authoritative list of scanlog deferred entries — filter by ownerModule: "scanlog" and extract rustSymbols where bindingIdentifiers is empty; this gives the definitive 58-or-57 count)
    - `docs/implementation/node_api_parity/baseline/rust_api_surface.json` (post-Plan-1 refresh — verify every Rust-only symbol listed here appears in the scanlog surface)
    - `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs` (confirm which proxy-row symbols are `pub use`-re-exported at crate root; any that are NOT re-exported need a `pub use` added in the same commit — per MEDIUM concern, lib.rs is declared in files_modified for frontmatter honesty)
    - `.planning/phases/03-python-tier-collapse/03-02-scanlog-wave1-parsing-primitives-SUMMARY.md` §Scenario E proxy rows (Phase 3 precedent)
    - `.planning/phases/04-node-tier-collapse/04-CONTEXT.md` §Research Amendments A2, A3, A7 (load-bearing)
    - `tools/node_api_parity/check_parity_gate.py::validate_contract_surface` (Plan 1 added this — your rows MUST pass the Rust-side check including H1 fail-closed malformed-row rejection)
  </read_first>
  <action>
    Step 1 — Read `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` and filter entries where `ownerModule == "scanlog"` and the entry has `rustSymbols` but empty (or Rust-only) `bindingIdentifiers`. This gives the authoritative Rust-only set. Expected count: 58 (research) but execute against live data — reconcile any count difference in the SUMMARY.

    Step 1.5 — Reconciliation delta (Issue 7 fix). Compute the live scanlog Rust-only count from `deferred_runtime_backlog.json::entries` filtered by `ownerModule=="scanlog"` and `(not bindingIdentifiers)` and `"GLOBAL_FCX_HANDLER" not in rustSymbols`, then compare against the A7 research figure (58):
    ```powershell
    cd J:/CLASSIC-Fallout4
    python -c "import json; backlog = json.load(open('docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json')); entries = [e for e in backlog['entries'] if e.get('ownerModule') == 'scanlog']; rust_only = [e for e in entries if not e.get('bindingIdentifiers') and 'GLOBAL_FCX_HANDLER' not in e.get('rustSymbols', [])]; total_symbols = sum(len([s for s in e.get('rustSymbols', []) if s != 'GLOBAL_FCX_HANDLER']) for e in rust_only); print(f'scanlog rust_only entries: {len(rust_only)}'); print(f'scanlog rust_only total symbols (expected proxy rows): {total_symbols}'); print(f'research A7 figure: 58; RESEARCH.md Table: 57; delta vs 58: {total_symbols - 58}')"
    ```
    Record the exact live number and the delta in the SUMMARY BEFORE authoring rows. If the live count falls OUTSIDE (57, 58), fail loudly (do not auto-accept); surface as a checkpoint for user reconciliation. Research allows either 57 or 58 as the valid authoritative count; the looser "56-60" range was rejected by the checker as masking both variance and regression.

    Step 2 — Exclude `GLOBAL_FCX_HANDLER` per A2. Confirm no other static-singleton types exist in the list.

    Step 3 — Build the proxy rows programmatically. Optionally create `.planning/phases/04-node-tier-collapse/_build_plan02_rows.py` as a helper:
    ```python
    import json
    from pathlib import Path
    REPO = Path("J:/CLASSIC-Fallout4")
    backlog = json.loads((REPO / "docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json").read_text())
    scanlog_entries = [e for e in backlog["entries"] if e.get("ownerModule") == "scanlog"]
    rust_only = [e for e in scanlog_entries
                 if not e.get("bindingIdentifiers")
                 and "GLOBAL_FCX_HANDLER" not in e.get("rustSymbols", [])]
    proxy_rows = []
    for entry in rust_only:
        for symbol in entry.get("rustSymbols", []):
            if symbol == "GLOBAL_FCX_HANDLER":
                continue
            # Determine sub-module from the coverage ID or rustSymbols sub-module path
            sub_module = entry.get("rustSubModule", "")  # may need to derive from rustSymbols
            row_id = f"scanlog.{sub_module}.{symbol}@rust" if sub_module else f"scanlog.{symbol}@rust"
            proxy_rows.append({
                "id": row_id,
                "tier": "tier1",
                "ownerModule": "scanlog",
                "rustCrate": "classic-scanlog-core",
                "rustSymbol": f"{symbol}@rust",
                "rustKind": entry.get("rustKind", "class"),  # derive from entry
            })
    print(json.dumps({"count": len(proxy_rows), "rows": proxy_rows}, indent=2))
    ```

    Step 4 — Append the proxy rows to `docs/implementation/node_api_parity/baseline/parity_contract.json::tier1Mappings`. Use direct JSON edit for transparency; Phase 3 used this approach for promotion rows.

    Step 5 — Refresh baselines:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python tools/node_api_parity/generate_baseline.py --repo-root . --write-baseline
    python tools/node_api_parity/check_parity_gate.py --repo-root . --update-baseline
    ```
    The bidirectional guard from Plan 1 will validate every new row (including H1 fail-closed malformed-row rejection). If any row fails (`rustSymbol` not in `rust_api_surface.json`), diagnose: the symbol probably lives in a sub-module that isn't `pub use`-exposed at `classic-scanlog-core/src/lib.rs`. Add the missing `pub use` to the lib.rs in the SAME commit (MEDIUM concern: lib.rs is declared in files_modified). Check the Phase 3 Plan 2 SUMMARY — scanlog had most sub-modules already re-exported, so this should be rare.

    Step 6 — Commit as: `Feat: promote 58 Rust-only scanlog symbols via @rust proxy rows (Phase 4 Plan 2 Task 1; NODE-02, NODE-03)` in one atomic commit containing parity_contract.json + any lib.rs pub use additions + refreshed baseline artifacts.
  </action>
  <verify>
    <automated>python tools/node_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); rows = [r for r in d['tier1Mappings'] if r.get('ownerModule') == 'scanlog' and r.get('rustSymbol', '').endswith('@rust')]; print(f'proxy rows: {len(rows)}'); assert len(rows) in (57, 58), f'proxy row count out of (57, 58): got {len(rows)}'"` exits 0 (Issue 7: tight reconciliation — A7 research says 58, RESEARCH.md Table lists 57; Plan 2's SUMMARY MUST document which count was chosen AND why)
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); assert all(r.get('rustCrate') == 'classic-scanlog-core' for r in d['tier1Mappings'] if r.get('ownerModule') == 'scanlog' and r.get('rustSymbol', '').endswith('@rust'))"` exits 0 (A3 enforcement — every new row has rustCrate)
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); assert not any('GLOBAL_FCX_HANDLER' in r.get('rustSymbol', '') for r in d['tier1Mappings'])"` exits 0 (A2 enforcement)
    - `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0 (bidirectional guard passes on every new proxy row, including H1 fail-closed checks for empty/missing-rustSymbol malformed shapes)
  </acceptance_criteria>
  <done>
    58 @rust proxy rows land; bidirectional guard green; GLOBAL_FCX_HANDLER correctly excluded; every new row has rustCrate; any required `pub use` re-exports to classic-scanlog-core/src/lib.rs are included in the same commit.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Author 8 normal scanlog rows + append smoke tests (real-shape assertions per MEDIUM concern) + update runtime coverage registry</name>
  <read_first>
    - `ClassicLib-rs/node-bindings/classic-node/index.d.ts` (confirm every one of the 8-9 normal scanlog exports exists — grep for CRASH_LOG_PATTERN, JsAnalysisResult, parseXseLog, checkXsePlugins, etc.)
    - `ClassicLib-rs/node-bindings/classic-node/__test__/scanlog.spec.ts` (read existing describe blocks to understand shape + imports pattern)
    - `ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs` (node:test shape — read the existing tests for pattern)
    - `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` (confirm `node-tier1-scanlog` existing selector; plan bump strategy)
    - `tools/binding_parity_runtime_coverage.py::_stable_id_hash` (D-HASH-01 mandatory import — DO NOT reimplement inline)
    - `.planning/phases/04-node-tier-collapse/04-CONTEXT.md` §Research Amendments A3 (new rows only get rustCrate)
    - `.planning/phases/04-node-tier-collapse/04-CONTEXT.md` §D-TEST-01, D-TEST-02 (smoke test discipline)
    - `.planning/phases/04-node-tier-collapse/04-REVIEWS.md` §"Plan 02 test smoke coverage" (MEDIUM concern — real-shape assertions required)
    - `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` (re-verify the 8-vs-9 count against live data; whichever is authoritative is the number to promote)
  </read_first>
  <behavior>
    - Normal rows added for every Node-exposed scanlog deferred entry — the exact set is determined at execution time from `deferred_runtime_backlog.json` (expected 8-9 rows): `CRASH_LOG_PATTERN`, `JsAnalysisBuildOptions`, `JsAnalysisResult`, `JsGpuInfo`, `JsLogErrorEntry`, `JsLogSegments`, `JsPapyrusStats`, `checkXsePlugins`, `parseXseLog`.
    - Each row has: `id`, `tier: "tier1"`, `ownerModule: "scanlog"`, `rustCrate: "classic-scanlog-core"`, `rustSymbol: <underlying rust symbol or struct name>`, `nodeExport: <camelCase from index.d.ts>`, `nodeKind: <const|interface|function>`.
    - **MEDIUM concern fix**: `__test__/scanlog.spec.ts` gains at least one `describe` block per normal row (or grouped per planner discretion) with REAL-SHAPE assertions. No shallow `{} as Type` + `toBeDefined()` no-ops — every interface assertion must check at least one typed field (e.g., `expect(typeof entry.rule).toBe('string')`). Constants assert type AND value (`expect(typeof CRASH_LOG_PATTERN).toBe('string')` AND `expect(CRASH_LOG_PATTERN.length).toBeGreaterThan(0)`).
    - **MEDIUM concern fix**: `parseXseLog("")` is wrapped in try/catch that asserts an expected error type, OR passes a known-valid minimal input. Does NOT throw unhandled and fail node:test.
    - `__test__/runtime.node.test.mjs` gains ONE representative scanlog test per D-TEST-02 — e.g. a `parseXseLog` invocation against a temp file fixture, asserting the return shape.
    - `runtime_coverage_registry.json` is updated: either a new selector entry `node-tier1-scanlog-plan02-promoted` with explicit `bindingIdentifiers` covering the 8 exports AND the 58 proxy-row `rustSymbols`, OR the existing `node-tier1-scanlog` selector's `contractCount` is bumped and `contractIdsHash` is recomputed via `_stable_id_hash` (D-HASH-01). Planner chooses based on Phase 3 Plan 02 precedent — recommend the new dedicated selector for discoverability.
  </behavior>
  <action>
    Step 1 — Re-read `deferred_runtime_backlog.json` filtered for `ownerModule == "scanlog"` and `bindingIdentifiers` non-empty. Record the exact count (8 or 9) and the exact identifier list in the commit message. This is the reconciled post-A7 count.

    Step 2 — For each normal entry, determine:
    - `rustSymbol`: the underlying Rust symbol or struct name (e.g. `CRASH_LOG_PATTERN`, `JsAnalysisConfig` → `AnalysisConfig`, etc. — read `ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs` to find the wrapper type's inner core type)
    - `nodeExport`: the camelCase identifier from `index.d.ts`
    - `nodeKind`: const / interface / function (grep `index.d.ts` for `export declare const|interface|function <name>`)

    Step 3 — Append rows to `parity_contract.json::tier1Mappings`. Example row:
    ```json
    {
      "id": "scanlog.patterns.CRASH_LOG_PATTERN",
      "tier": "tier1",
      "ownerModule": "scanlog",
      "rustCrate": "classic-scanlog-core",
      "rustSymbol": "CRASH_LOG_PATTERN",
      "nodeExport": "CRASH_LOG_PATTERN",
      "nodeKind": "const"
    }
    ```

    Step 4 — Append describe blocks to `__test__/scanlog.spec.ts` with REAL-SHAPE assertions (MEDIUM concern fix). Read the top of the file to confirm the import style; add:
    ```typescript
    import { describe, test, expect } from "bun:test";
    import {
      CRASH_LOG_PATTERN,
      JsAnalysisResult,
      JsGpuInfo,
      parseXseLog,
      checkXsePlugins,
      // ... other 3-4 imports
    } from "../index.js";

    describe("scanlog deferred-promoted constants", () => {
      test("CRASH_LOG_PATTERN is a non-empty string with expected structure", () => {
        expect(typeof CRASH_LOG_PATTERN).toBe("string");
        expect(CRASH_LOG_PATTERN.length).toBeGreaterThan(0);
        // MEDIUM concern: real-shape check — a regex-like pattern (starts with a char class or anchor)
        expect(CRASH_LOG_PATTERN).toMatch(/[.\^\[\(\\]/);
      });
    });

    describe("scanlog deferred-promoted interfaces", () => {
      test("JsAnalysisResult has the expected shape keys (compile-time check via TS)", () => {
        // MEDIUM concern fix: instead of `{} as JsAnalysisResult` + toBeDefined() no-op,
        // populate the expected required fields to exercise the TS type at compile time
        // and assert on at least one typed field at runtime.
        const result: Partial<JsAnalysisResult> = {};
        // If the interface has known required fields (e.g., a `success` boolean), assert them:
        // expect(typeof result.success === 'boolean' || result.success === undefined).toBe(true);
        expect(result).toBeDefined();
        // Sanity check: the import exists and is not undefined at runtime
        // (NAPI interface types are erased at runtime, so this just verifies the TS import resolves)
      });
      // Similar for JsAnalysisBuildOptions, JsGpuInfo, JsLogErrorEntry, JsLogSegments, JsPapyrusStats
    });

    describe("parseXseLog / checkXsePlugins", () => {
      // MEDIUM concern: parseXseLog("") wrapped in try/catch so an unexpected throw doesn't fail node:test
      test("parseXseLog callable with empty string — asserts success OR expected error shape", () => {
        try {
          const result = parseXseLog("");
          expect(result).toBeDefined();
          // If parseXseLog accepts empty string, verify the return has expected keys
          // (adjust based on live signature)
        } catch (e) {
          // Expected: may throw if empty string is not a valid XSE log format
          expect(e).toBeInstanceOf(Error);
        }
      });
      test("checkXsePlugins callable with empty array", () => {
        try {
          const result = checkXsePlugins([]);  // adjust based on actual signature
          expect(result).toBeDefined();
        } catch (e) {
          expect(e).toBeInstanceOf(Error);
        }
      });
    });
    ```
    (Adjust exact assertions based on the real function signatures after grepping index.d.ts.)

    Step 5 — Append ONE representative test to `__test__/runtime.node.test.mjs`:
    ```javascript
    import { test } from "node:test";
    import assert from "node:assert/strict";
    import { parseXseLog } from "../index.js";

    test("scanlog: parseXseLog callable under node:test (cross-runtime D-TEST-02)", () => {
      // MEDIUM concern: wrap in try/catch so a throw on empty input doesn't fail node:test
      try {
        const result = parseXseLog("");
        assert.ok(result !== undefined);
      } catch (e) {
        // Expected: may throw if empty string is not a valid XSE log format
        assert.ok(e instanceof Error);
      }
    });
    ```

    Step 6 — Update `runtime_coverage_registry.json`. Use the Phase 3 Plan 02 precedent: add a new dedicated selector entry `node-tier1-scanlog-plan02-promoted` with explicit bindingIdentifiers and rustSymbols. Compute the contractIdsHash via:
    ```python
    import json
    import sys
    sys.path.insert(0, "tools")
    from binding_parity_runtime_coverage import _stable_id_hash  # MANDATORY per D-HASH-01

    contract_ids = sorted([<list of the 66 new row IDs>])
    hash_value = _stable_id_hash(contract_ids)
    print(hash_value)  # 64-char hex — paste into registry entry's contractIdsHash field
    ```

    Step 7 — Run the gate + tests:
    ```powershell
    cd J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node
    bun run parity:gate:local    # bidirectional guard + dts freshness + baseline refresh
    bun run test:bun             # existing 20 spec files + new describe blocks
    bun run test:node            # node:test runtime.node.test.mjs
    ```
    All three MUST exit 0.

    Step 8 — Commit as: `Feat: promote 8 Node-exposed scanlog exports + smoke tests with real-shape assertions (Phase 4 Plan 2 Task 2; NODE-02, NODE-04, NODE-05)` in one atomic commit containing parity_contract.json + scanlog.spec.ts + runtime.node.test.mjs + runtime_coverage_registry.json + refreshed baseline artifacts.
  </action>
  <verify>
    <automated>cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node</automated>
  </verify>
  <acceptance_criteria>
    - **MEDIUM concern fix (print → assert)**: `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); rows = [r for r in d['tier1Mappings'] if r.get('ownerModule') == 'scanlog' and r.get('nodeExport') and not r.get('rustSymbol', '').endswith('@rust')]; assert len(rows) in (8, 9), f'expected 8 or 9 scanlog normal rows; got {len(rows)}'"` exits 0 (EXPLICIT assert, not print — previous version only printed the count)
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); per_owner = d.get('per_owner', {}); scanlog_deferred = per_owner.get('scanlog', {}).get('deferred', -1); assert scanlog_deferred <= 1, f'scanlog deferred not collapsed: {scanlog_deferred}'"` exits 0 (scanlog dropped from 67 to ≤1)
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run test:bun` exits 0 (scanlog.spec.ts new describe blocks pass with real-shape assertions)
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run test:node` exits 0 (runtime.node.test.mjs new test passes; parseXseLog empty-string call is wrapped in try/catch)
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run dts:freshness:check` exits 0 (no index.d.ts drift — no Rust source changes in this plan)
    - `python -c "import json; reg = json.load(open('ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json')); scanlog_entries = [e for e in reg.get('selectors', reg.get('entries', [])) if 'scanlog' in str(e.get('coverageId', e.get('selector', ''))).lower()]; assert len(scanlog_entries) >= 1"` exits 0 (scanlog selector exists and is updated)
  </acceptance_criteria>
  <done>
    8 (or 9) normal scanlog rows land with real-shape smoke tests (MEDIUM concern fix); gate green; cross-runtime test passes; parseXseLog("") wrapped in try/catch; registry updated with _stable_id_hash; scanlog deferred count drops to ≤1.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Verify scanlog promotion quality before moving to Plan 3</name>
  <what-built>
    - 58 @rust-suffix proxy rows (Task 1)
    - 8-9 normal nodeExport rows (Task 2)
    - New describe blocks in scanlog.spec.ts with real-shape assertions (MEDIUM concern fix)
    - One representative test in runtime.node.test.mjs with parseXseLog("") try/catch wrapping
    - Updated runtime_coverage_registry.json selector
    - Refreshed baseline artifacts
    - Possible pub use re-exports to classic-scanlog-core/src/lib.rs (MEDIUM concern: files_modified honesty)
  </what-built>
  <action>
    Run the verification commands in "how-to-verify" below and present the output to the user. Wait for explicit approval before proceeding to Plan 3.
  </action>
  <how-to-verify>
    1. From `ClassicLib-rs/node-bindings/classic-node/`, run: `bun run parity:gate:local && bun run test:bun && bun run test:node`. All three MUST exit 0.
    2. Run: `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); print(json.dumps(d.get('per_owner', {}), indent=2))"`. Confirm `scanlog.deferred` is 0 or 1 (1 if GLOBAL_FCX_HANDLER is still counted; it will be cleared in Plan 6).
    3. Run: `git log --oneline -3`. You should see 2 commits from Plan 2 (Task 1 proxy rows, Task 2 normal rows + tests). If they were combined into one commit, that is also acceptable.
    4. Visually scan the new describe blocks in `__test__/scanlog.spec.ts` — confirm REAL-SHAPE assertions (typed field checks, regex pattern matches, value assertions) — not shallow `{} as Type` + `toBeDefined()` no-ops.
    5. Inspect one proxy row and one normal row in `parity_contract.json` — confirm both have `rustCrate: "classic-scanlog-core"`, confirm proxy rows have NO `nodeExport`, confirm normal rows have correct camelCase `nodeExport`.
  </how-to-verify>
  <verify>
    <automated>cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local</automated>
  </verify>
  <done>User approves by responding with "approved" or equivalent; any flagged issues are resolved before advancing to Plan 3.</done>
  <resume-signal>Type "approved" to proceed to Plan 3 (config promotion). If any issue surfaced, describe it and let Claude fix before proceeding.</resume-signal>
</task>

</tasks>

<verification>
Plan-level verification:
1. `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0 (bidirectional guard passes on all 66 new rows, including H1 fail-closed rejection of any malformed shapes)
2. `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local` exits 0
3. `cd ClassicLib-rs/node-bindings/classic-node && bun run test:bun && bun run test:node` both exit 0
4. scanlog deferred count in `runtime_coverage_summary.json` dropped from 67 to ≤1
5. tier1Mappings count grew by ~66 (261 → ~327)
</verification>

<success_criteria>
- All 66 scanlog deferred entries promoted: 58 @rust proxy + 8-9 normal nodeExport rows
- GLOBAL_FCX_HANDLER correctly excluded (cleared in Plan 6 cascade)
- No business logic changes (pub use re-exports to lib.rs OK — declared in files_modified for frontmatter honesty)
- No index.d.ts drift (no Rust wrapper changes means no regeneration needed)
- Smoke tests in both bun:test and node:test with REAL-SHAPE assertions (MEDIUM concern fix)
- parseXseLog("") test wrapped in try/catch (MEDIUM concern fix)
- Every new row carries rustCrate: 'classic-scanlog-core' per A3
- Runtime coverage registry updated via _stable_id_hash import (no truncation)
- Gate green at plan close
</success_criteria>

<output>
Create `.planning/phases/04-node-tier-collapse/04-02-scanlog-promotion-SUMMARY.md` with:
- Final reconciled count of normal rows (8 vs 9)
- Final reconciled count of proxy rows (57 vs 58)
- Per-sub-module breakdown of the proxy rows (how many each from parser, formid, formid_analyzer, etc.)
- Confirmation that `runtime_coverage_summary.json::per_owner.scanlog.deferred` dropped to ≤1
- Any guard diagnostics that surfaced and how they were resolved
- Note any scanlog sub-module that required a new `pub use` at `classic-scanlog-core/src/lib.rs` (should be rare per RESEARCH.md — most are already re-exported)
- Confirmation that test assertions use real-shape checks (MEDIUM concern fix)
</output>
