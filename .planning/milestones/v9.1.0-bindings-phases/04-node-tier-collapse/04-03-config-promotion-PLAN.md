---
phase: 04-node-tier-collapse
plan: 03
plan_id: 04-03
title: Config Promotion (11 @rust proxy + 23 normal = 34 rows — ModConflictEntry removed per Issue 4 reconciliation with Plan 5)
type: execute
wave: 2
depends_on: [04-02]
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
  - ClassicLib-rs/business-logic/classic-config-core/src/lib.rs
  - ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs
  - ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json
  - ClassicLib-rs/node-bindings/classic-node/__test__/config.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs
autonomous: false
requirements_addressed: [NODE-02, NODE-03, NODE-04, NODE-05]
requirements: [NODE-02, NODE-03, NODE-04, NODE-05]
must_haves:
  truths:
    - "All deferred config Node parity entries promoted to enforced Tier-1 rows. Post-Issue-4 target: **11 proxy + 23 normal = 34 rows total**. ModConflictEntry is handled by Plan 5 as a normal row (Issue 4 reconciliation); it is NOT authored here."
    - "11 Rust-only config symbols get @rust-suffix proxy rows (classes/enums: ConfigError, CoreModEntry, CoreModExclude, CrashgenEntryRaw, ModSolutionCriteria, ModSolutionEntry, SuspectErrorRule, SuspectStackCountRule, SuspectStackRule; free functions: format_registry_game_version, resolve_registry_version_info). ModConflictEntry is NOT on this list — it has a Node binding (`JsModConflictEntry` at `classic-node/src/config.rs` line 44, `#[napi(object)]` verified 2026-04-08) and is promoted as a NORMAL row by Plan 5 Task 1 per Issue 4 reconciliation."
    - "23 Node-exposed config entries get normal rows with camelCase nodeExport (consts: DEFAULT_CACHE_CLEANUP_INTERVAL, DEFAULT_CACHE_CLEANUP_THRESHOLD, DEFAULT_QUERY_CACHE_CAPACITY; interfaces: HashCacheStats, JsAnalysisConfig, JsConfigIssue, JsFcxConfigIssue, JsGameScanConfig, JsIntegrityConfig, JsPathDetectionResult, JsTomlConfigIssue, JsXseConfig; const_enum: JsEnbConfigResult; class: JsConfigDuplicateDetector; functions: clearHashCache, detectConfigDuplicates, getDefaultCacheCleanupInterval, getDefaultCacheCleanupThreshold, getDefaultQueryCacheCapacity, getFcxConfigIssues, getHashCacheStats, needsPathDetection, resetHashCacheStats)."
    - "No business logic changes in classic-config-core or classic-node/src/config.rs — this phase EXPOSES existing bindings. `pub use` re-exports MAY be added to `classic-config-core/src/lib.rs` AND/OR `classic-crashgen-settings-core/src/lib.rs` if the bidirectional guard demands them (Phase 3 A2/Pitfall 8 precedent); `files_modified` lists these lib.rs paths for frontmatter honesty. No index.d.ts regeneration needed since no NAPI wrappers change."
    - "Smoke tests append to __test__/config.spec.ts as new describe blocks with REAL-SHAPE assertions (not shallow `toBeDefined()` no-ops per MEDIUM concern). At least one representative test lands in runtime.node.test.mjs for cross-runtime verification."
    - "runtime_coverage_registry.json updated via new dedicated selector OR bumped existing selector (with _stable_id_hash recomputed)."
    - "bun run parity:gate:local exits 0 at plan close; runtime_coverage_summary.json::per_owner.config.deferred == 0. Plan 03's deferred target is zero. Any residuals surfaced by H2's cross-crate routing are absorbed by Plan 05's aux cleanup."
    - "Every new row carries a `rustCrate` field per A3. Cross-crate routing: proxy rows route to `classic-config-core` OR `classic-crashgen-settings-core` per the live `rust_api_surface.json` lookup — the routing is symbol-specific, not uniform. The `rustCrate` value for each proxy row comes from the surface JSON at row-authoring time, not from a hard-coded set (e.g., `ConfigError` routes to `classic-config-core`; `SuspectErrorRule` and `ModSolutionCriteria` route to `classic-crashgen-settings-core`)."
  artifacts:
    - path: "docs/implementation/node_api_parity/baseline/parity_contract.json"
      provides: "tier1Mappings grows by 34 rows (11 proxy + 23 normal); all new rows carry rustCrate with cross-crate routing (classic-config-core OR classic-crashgen-settings-core per live rust_api_surface.json lookup)"
      contains: "classic-config-core"
    - path: "ClassicLib-rs/node-bindings/classic-node/__test__/config.spec.ts"
      provides: "New describe blocks for each config class/interface/function group with real-shape assertions"
      min_lines: 40
    - path: "ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs"
      provides: "At least one new test per D-TEST-02 — e.g. detectConfigDuplicates or getHashCacheStats cross-runtime call"
    - path: "ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json"
      provides: "Config selector updated to cover the new rows with recomputed contractIdsHash"
    - path: "ClassicLib-rs/business-logic/classic-config-core/src/lib.rs"
      provides: "`pub use` re-exports added IF AND ONLY IF the bidirectional guard demands them at row-landing time"
    - path: "ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs"
      provides: "`pub use` re-exports added IF AND ONLY IF the bidirectional guard demands them at row-landing time for crashgen_settings source symbols"
  key_links:
    - from: "parity_contract.json::tier1Mappings config @rust proxy rows"
      to: "classic-config-core OR classic-crashgen-settings-core public items (ConfigError, SuspectErrorRule, etc.) per live surface lookup"
      via: "bidirectional guard's Rust-side check against rust_api_surface.json"
      pattern: "\"rustCrate\":\\s*\"classic-(config|crashgen-settings)-core\""
    - from: "parity_contract.json::tier1Mappings config normal rows"
      to: "index.d.ts config exports (JsAnalysisConfig, getHashCacheStats, etc.)"
      via: "bidirectional guard's Node-side check against node_api_surface.json"
      pattern: "\"nodeExport\":\\s*\"(getHashCacheStats|JsAnalysisConfig|detectConfigDuplicates)\""
    - from: "__test__/config.spec.ts new describe blocks"
      to: "bun:test per-module smoke verification"
      via: "bun run test:bun invocation"
      pattern: "describe\\(.*config"
---

<objective>
Promote all deferred config Node parity entries to enforced Tier-1 rows. Structure mirrors Plan 2 exactly — two groups: **11 `@rust`-suffix proxy rows** for Rust-only symbols (ModConflictEntry removed per Issue 4 reconciliation), **23 normal rows** for Node-exposed entries. Total **34 new rows** (11 + 23). No Rust business logic changes; `pub use` re-exports may be added if the bidirectional guard demands them. Every new row carries a `rustCrate` field per A3, but the value is NOT uniform — some rows route to `classic-config-core`, others to `classic-crashgen-settings-core` (per H2 cross-crate routing via live `rust_api_surface.json` lookup).

**Issue 4 reconciliation note**: `ModConflictEntry` was originally listed as a proxy-row candidate but was found to have a live Node binding (`JsModConflictEntry` at `classic-node/src/config.rs` line 44 via `#[napi(object)]`, verified 2026-04-08). Plan 5 Task 1 promotes it as a normal row under `rustCrate: classic-config-core`. Plan 3's proxy count drops from 12 → 11, and the total from 35 → 34. The Phase 4 net row count is preserved because Plan 5 contributes the missing row.

**H2 count reconciliation (review pass)**: All counts in this plan reflect the post-Issue-4 numbers: **11 proxy + 23 normal = 34 total**. Any lingering references to 12/23/35 in the text below should be treated as stale and updated.

The 26-vs-34 count discrepancy (runtime_coverage_summary may report 26, diff report may report 34 or 35) is reconciled at execution time from `docs/implementation/node_api_parity/baseline/parity_diff_report.json::gaps` (primary source per U2 — the same source Plan 1 A10 sizing uses) filtered by `ownerModule: "config"`. The authoritative number for task budgeting is the gap-inventory count; the authoritative number for NODE-06 is `runtime_coverage_summary.json::per_owner.config.deferred == 0`.

Purpose:
- Eliminate config from the deferred backlog (per-owner.config.deferred → 0)
- Exercise the Plan 2 pattern on a second owner module to prove repeatability
- Prepare the contract for Plan 4 (version_registry) and Plan 5 (aux) to run against a smaller, cleaner residual set

Output:
- **34 new tier1Mappings rows (11 proxy + 23 normal)** in `parity_contract.json`
- Possible `pub use` additions to `classic-config-core/src/lib.rs` and/or `classic-crashgen-settings-core/src/lib.rs` if the guard demands them
- New describe blocks in `__test__/config.spec.ts`
- At least one new representative test in `runtime.node.test.mjs`
- Refreshed baseline artifacts + runtime_coverage_registry.json
- Gate exit 0 with config deferred count dropped to 0
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
@.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json
@.planning/phases/03-python-tier-collapse/03-06-config-promotion-SUMMARY.md
@./CLAUDE.md
@./AGENTS.md

<notes>
**Issue 4 reconciliation (2026-04-08)**: Plan 3 originally listed 12 proxy rows including `ModConflictEntry`. Cross-plan check revealed `JsModConflictEntry` exists at `ClassicLib-rs/node-bindings/classic-node/src/config.rs` line 44 as `#[napi(object)] pub struct JsModConflictEntry`, with `impl From<&ModConflictEntry> for JsModConflictEntry` at line 128. `ModConflictEntry` therefore HAS a Node binding and belongs in the normal-row set, not the proxy set. Plan 5 Task 1 owns the normal row (`rustCrate: classic-config-core`, `nodeExport: JsModConflictEntry`, `nodeKind: interface`). Plan 3 drops `ModConflictEntry` from its proxy list, bringing the proxy count from 12 → 11 and the total from 35 → 34. The Phase 4 net row count is preserved because Plan 5 contributes the missing row.

**H2 crashgen ownership routing (review pass)**: The earlier draft hard-coded a set of crashgen_settings types inside the proxy-row builder helper script. This is brittle and coupled the plan to a static assumption about which types live where. The corrected approach is to **look up each Rust-only symbol in `docs/implementation/node_api_parity/baseline/rust_api_surface.json` at execution time** (post-Plan-1 refresh) and use the `crate` field reported there as the authoritative `rustCrate` value. This makes the routing self-adjusting if a symbol moves between crates in future phases.
</notes>

<interfaces>
<!-- Config deferred inventory from RESEARCH.md §Deferred Entry Inventory -->

**11 Rust-only config symbols for @rust proxy rows** (H2 reconciliation: 12 → 11 because ModConflictEntry has a Node binding):

Classes/enums: `ConfigError`, `CoreModEntry`, `CoreModExclude`, `CrashgenEntryRaw`, `ModSolutionCriteria`, `ModSolutionEntry`, `SuspectErrorRule`, `SuspectStackCountRule`, `SuspectStackRule`. (9)

Free functions: `format_registry_game_version`, `resolve_registry_version_info`. (2)

Total: **11 proxy rows**.

**ModConflictEntry reconciliation note**: The original planning assumed 12 proxy rows. Checker Issue 4 flagged that `ModConflictEntry` IS bound at `classic-node/src/config.rs` line 44-53 via `#[napi(object)] pub struct JsModConflictEntry { mod_a, mod_b, name_a, name_b, description, fix, ... }` and wrapped by `impl From<&ModConflictEntry> for JsModConflictEntry` at line 128. The symbol belongs in the normal set, not the proxy set. Plan 5 Task 1 already lists `JsModConflictEntry` as a normal row with `rustCrate: classic-config-core`; Plan 3 now drops it from the proxy list (12 → 11).

**23 Node-exposed config entries needing normal contract rows**:

Consts (3): `DEFAULT_CACHE_CLEANUP_INTERVAL`, `DEFAULT_CACHE_CLEANUP_THRESHOLD`, `DEFAULT_QUERY_CACHE_CAPACITY`.

Interfaces (9): `HashCacheStats`, `JsAnalysisConfig`, `JsConfigIssue`, `JsFcxConfigIssue`, `JsGameScanConfig`, `JsIntegrityConfig`, `JsPathDetectionResult`, `JsTomlConfigIssue`, `JsXseConfig`.

const_enum (1): `JsEnbConfigResult`.

Class (1): `JsConfigDuplicateDetector`.

Functions (9): `clearHashCache`, `detectConfigDuplicates`, `getDefaultCacheCleanupInterval`, `getDefaultCacheCleanupThreshold`, `getDefaultQueryCacheCapacity`, `getFcxConfigIssues`, `getHashCacheStats`, `needsPathDetection`, `resetHashCacheStats`.

Total: **23 normal rows**.

**Grand total: 11 + 23 = 34 contract rows** (per Issue 4 reconciliation + H2 sweep). If `runtime_coverage_summary.json` reports 26, the discrepancy is de-duplication across tracked-surface rows — executor reconciles by reading the live backlog and using the authoritative count as the target.

**Phase 3 precedent**: `.planning/phases/03-python-tier-collapse/03-06-config-promotion-SUMMARY.md` documents the same structural pattern for Python (including the @rust proxy application to crashgen_settings types with no PyO3 wrappers).

**Row shape** (same as Plan 2):
- Proxy: `{"id": "config.<sub>.<sym>@rust", "tier": "tier1", "ownerModule": "config", "rustCrate": "<classic-config-core or classic-crashgen-settings-core>", "rustSymbol": "<sym>@rust", "rustKind": "<kind>"}`
- Normal: `{"id": "config.<sub>.<sym>", "tier": "tier1", "ownerModule": "config", "rustCrate": "<classic-config-core>", "rustSymbol": "<underlying rust symbol>", "nodeExport": "<camelCase>", "nodeKind": "<kind>"}`

**H2 rustCrate lookup (replaces hard-coded set)**: The correct way to determine `rustCrate` for each proxy-row symbol is to query `docs/implementation/node_api_parity/baseline/rust_api_surface.json` post-Plan-1 refresh:
```python
import json
from pathlib import Path
surface = json.loads(Path("docs/implementation/node_api_parity/baseline/rust_api_surface.json").read_text())
by_symbol = {s["symbol"]: s.get("crate") for s in surface.get("symbols", [])}
# For each Rust-only symbol:
rust_crate = by_symbol.get(symbol)  # e.g. by_symbol["SuspectErrorRule"] → "classic-crashgen-settings-core"
if rust_crate is None:
    raise ValueError(f"Symbol {symbol} not found in rust_api_surface.json — Plan 1 may have missed a pub use")
```
This is the source of truth. Do NOT use a hard-coded set of crashgen_settings symbols.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author 11 @rust proxy rows for Rust-only config symbols (cross-crate routing per live rust_api_surface.json)</name>
  <read_first>
    - `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` (filter ownerModule: "config"; extract rustSymbols with empty bindingIdentifiers to get authoritative Rust-only set)
    - `docs/implementation/node_api_parity/baseline/rust_api_surface.json` (post-Plan-1 refresh; H2 load-bearing — this is the authoritative source for `rustCrate` routing per symbol; every proxy row's underlying symbol must appear here with a non-null `crate` field)
    - `docs/implementation/node_api_parity/baseline/parity_diff_report.json` (the PRIMARY source per U2 — cross-reference config gaps with A10 sizing)
    - `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs` (confirm which of the 11 Rust-only symbols are `pub use`-re-exported at crate root; any that are NOT re-exported need a `pub use` added in a separate sub-task — same pattern as Phase 3 Plan 6)
    - `ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs` (confirm the crashgen_settings source symbols are re-exported at crate root; post-Plan-1, the generate_baseline.py surface parser walks this crate's lib.rs)
    - `.planning/phases/03-python-tier-collapse/03-06-config-promotion-SUMMARY.md` §"Wave 1 @rust-suffix proxy pattern to crashgen_settings types" (precedent: Python applied @rust proxy pattern to the same classes for the same reason)
    - `.planning/phases/04-node-tier-collapse/04-CONTEXT.md` §Research Amendments A3
    - `.planning/phases/04-node-tier-collapse/04-REVIEWS.md` §"H2 — Plan 03 count drift + crashgen crate ownership inconsistency"
    - `docs/implementation/node_api_parity/baseline/parity_contract.json` (confirm current row count after Plan 2 commits)
    - `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json` (read the config owner's per-primary gap count; cross-reference against the 11 proxy + 23 normal decomposition)
  </read_first>
  <action>
    Step 1 — Read `deferred_runtime_backlog.json` filtered for `ownerModule == "config"` and entries where `bindingIdentifiers` is empty. This is the authoritative Rust-only set. Expected: 11 (post-Issue-4; ModConflictEntry is in the normal set, not proxy). Reconcile any variance in the SUMMARY.

    Step 2 — **H2 cross-crate routing (REPLACES hard-coded set)**: For each Rust-only symbol, query `docs/implementation/node_api_parity/baseline/rust_api_surface.json` (post-Plan-1 refresh) to find the authoritative `crate` attribution:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python -c "
    import json
    from pathlib import Path
    surface = json.loads(Path('docs/implementation/node_api_parity/baseline/rust_api_surface.json').read_text())
    by_symbol = {s['symbol']: s.get('crate') for s in surface.get('symbols', [])}
    candidates = ['ConfigError', 'CoreModEntry', 'CoreModExclude', 'CrashgenEntryRaw',
                  'ModSolutionCriteria', 'ModSolutionEntry', 'SuspectErrorRule',
                  'SuspectStackCountRule', 'SuspectStackRule',
                  'format_registry_game_version', 'resolve_registry_version_info']
    for sym in candidates:
        crate = by_symbol.get(sym)
        if crate is None:
            print(f'MISSING: {sym} not in rust_api_surface.json — need pub use at its source crate')
        else:
            print(f'{sym} -> {crate}')
    "
    ```
    For each `MISSING` symbol, determine the source crate (likely `classic-config-core` or `classic-crashgen-settings-core`), add a `pub use <path>::<symbol>;` to that crate's `src/lib.rs`, re-run `generate_baseline.py --write-baseline`, and re-run the lookup. Repeat until every candidate maps to a real crate. Record every `pub use` addition in the SUMMARY (files_modified frontmatter already declares both lib.rs paths for honesty).

    Note: The crashgen_settings types (e.g., `SuspectErrorRule`, `ModSolutionCriteria`, `CrashgenEntryRaw`) likely live in `classic-crashgen-settings-core`. The config-internal types (e.g., `ConfigError`, `CoreModEntry`) likely live in `classic-config-core`. Use the live surface lookup as the source of truth — do NOT hard-code which is which.

    Step 3 — Build the 11 proxy rows using the live rust_api_surface.json lookup. Use a helper script at `.planning/phases/04-node-tier-collapse/_build_plan03_proxy_rows.py` if it improves transparency:
    ```python
    import json
    from pathlib import Path
    REPO = Path("J:/CLASSIC-Fallout4")
    backlog = json.loads((REPO / "docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json").read_text())
    surface = json.loads((REPO / "docs/implementation/node_api_parity/baseline/rust_api_surface.json").read_text())
    by_symbol = {s["symbol"]: s.get("crate") for s in surface.get("symbols", [])}
    config_entries = [e for e in backlog["entries"] if e.get("ownerModule") == "config"]
    rust_only = [e for e in config_entries if not e.get("bindingIdentifiers")]
    proxy_rows = []
    for entry in rust_only:
        for symbol in entry.get("rustSymbols", []):
            # Issue 4 fix: ModConflictEntry REMOVED from proxy set — Plan 5 Task 1 promotes it as a normal row.
            if symbol == "ModConflictEntry":
                continue  # handled by Plan 5 as normal row; do NOT emit proxy row
            # H2 fix: look up rustCrate from live surface, NOT a hard-coded set
            rust_crate = by_symbol.get(symbol)
            if rust_crate is None:
                raise ValueError(
                    f"Symbol '{symbol}' not found in rust_api_surface.json. "
                    f"Add 'pub use <path>::{symbol};' to its source crate's lib.rs and re-run "
                    f"generate_baseline.py --write-baseline."
                )
            proxy_rows.append({
                "id": f"config.{symbol}@rust",
                "tier": "tier1",
                "ownerModule": "config",
                "rustCrate": rust_crate,
                "rustSymbol": f"{symbol}@rust",
                "rustKind": entry.get("rustKind", "class"),
            })
    print(f"Built {len(proxy_rows)} proxy rows (expected 11)")
    print(json.dumps(proxy_rows, indent=2))
    ```

    Step 4 — Append proxy rows to `parity_contract.json::tier1Mappings`. Refresh baselines:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python tools/node_api_parity/generate_baseline.py --repo-root . --write-baseline
    python tools/node_api_parity/check_parity_gate.py --repo-root . --update-baseline
    ```
    If the bidirectional guard fires on any row, the underlying Rust symbol isn't visible at its declared rustCrate lib.rs — add the missing `pub use` to the correct crate and retry.

    Step 5 — Commit as: `Feat: promote 11 Rust-only config symbols via @rust proxy rows with cross-crate routing (Phase 4 Plan 3 Task 1; NODE-02, NODE-03)` with parity_contract.json, any lib.rs pub use additions, and refreshed baselines in ONE atomic commit.
  </action>
  <verify>
    <automated>python tools/node_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); rows = [r for r in d['tier1Mappings'] if r.get('ownerModule') == 'config' and r.get('rustSymbol', '').endswith('@rust')]; assert len(rows) == 11, f'expected 11 proxy rows (H2 post-Issue-4 count), got {len(rows)}'"` exits 0
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); rows = [r for r in d['tier1Mappings'] if r.get('ownerModule') == 'config' and r.get('rustSymbol', '').endswith('@rust')]; syms = {r['rustSymbol'].removesuffix('@rust') for r in rows}; assert 'ModConflictEntry' not in syms, 'Issue 4: ModConflictEntry must not appear as proxy row (Plan 5 promotes it as normal)'"` exits 0
    - **H2 cross-crate routing enforcement**: `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); rows = [r for r in d['tier1Mappings'] if r.get('ownerModule') == 'config' and r.get('rustSymbol', '').endswith('@rust')]; assert all(r.get('rustCrate') in ('classic-config-core', 'classic-crashgen-settings-core') for r in rows), 'every proxy row must route to classic-config-core or classic-crashgen-settings-core per H2 cross-crate lookup'; rustCrates = {r.get('rustCrate') for r in rows}; assert len(rustCrates) >= 1, 'rustCrate routing set was empty'"` exits 0
    - **H2 surface-lookup verification**: `python -c "import json; surface = json.load(open('docs/implementation/node_api_parity/baseline/rust_api_surface.json')); by_sym = {s['symbol']: s.get('crate') for s in surface.get('symbols', [])}; contract = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); proxy_rows = [r for r in contract['tier1Mappings'] if r.get('ownerModule') == 'config' and r.get('rustSymbol', '').endswith('@rust')]; mismatches = [(r['rustSymbol'].removesuffix('@rust'), r['rustCrate'], by_sym.get(r['rustSymbol'].removesuffix('@rust'))) for r in proxy_rows if by_sym.get(r['rustSymbol'].removesuffix('@rust')) != r['rustCrate']]; assert not mismatches, f'rustCrate-surface mismatches: {mismatches}'"` exits 0
    - `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0
  </acceptance_criteria>
  <done>
    11 config @rust proxy rows land (ModConflictEntry excluded per Issue 4 — promoted as normal row by Plan 5); every row's rustCrate value agrees with `rust_api_surface.json`'s authoritative crate attribution (H2); bidirectional guard green; any required `pub use` re-exports added atomically.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Author 23 normal config rows + append smoke tests with real-shape assertions + update runtime coverage registry</name>
  <read_first>
    - `ClassicLib-rs/node-bindings/classic-node/index.d.ts` (grep for each of the 23 expected exports: DEFAULT_CACHE_CLEANUP_INTERVAL, HashCacheStats, JsAnalysisConfig, JsEnbConfigResult, JsConfigDuplicateDetector, clearHashCache, etc.)
    - `ClassicLib-rs/node-bindings/classic-node/__test__/config.spec.ts` (existing describe shape)
    - `ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs`
    - `ClassicLib-rs/node-bindings/classic-node/src/config.rs` (confirm the Rust wrapper types' inner core symbols — e.g. JsAnalysisConfig wraps AnalysisConfig, etc. — so rustSymbol can be set correctly)
    - `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` (filter ownerModule: "config", bindingIdentifiers non-empty — gives the authoritative Node-exposed set)
    - `tools/binding_parity_runtime_coverage.py::_stable_id_hash` (D-HASH-01)
  </read_first>
  <behavior>
    - 23 normal tier1Mappings rows added with correct `rustSymbol` → `nodeExport` pairing (camelCase on Node side).
    - Each row has rustCrate: "classic-config-core" (verified via rust_api_surface.json lookup for each symbol). The 23 normal rows all resolve to classic-config-core because their NAPI wrappers delegate to `classic_config_core::*` — no cross-crate routing for the normal set in Plan 3 (the crashgen_rules normal rows are owned by Plan 5).
    - config.spec.ts gains describe blocks for each class/interface/function group. The describe block count is discretionary; at minimum one describe per semantic group (consts, interfaces, functions, duplicate-detector class).
    - **MEDIUM concern fix**: test assertions must use REAL-SHAPE checks, not shallow `toBeDefined()` or `{} as Type` no-ops. Each interface test must assert at least ONE typed field (e.g., `expect(typeof stats.hits).toBe('number')`).
    - runtime.node.test.mjs gains ONE representative config test — e.g. `getHashCacheStats()` call asserting the return shape `{ hits, misses, ... }`.
    - runtime_coverage_registry.json updated: new dedicated selector OR bumped existing with recomputed _stable_id_hash.
  </behavior>
  <action>
    Step 1 — Read `deferred_runtime_backlog.json` filtered for `ownerModule == "config"` with non-empty `bindingIdentifiers`. Expected: 23 entries / 23 bindingIdentifiers. Record the reconciled count.

    Step 2 — For each entry, determine the `rustSymbol` by reading `ClassicLib-rs/node-bindings/classic-node/src/config.rs` — grep for the Js-prefixed wrapper and identify its inner core type. Example: `JsAnalysisConfig` wraps `AnalysisConfig` from `classic-config-core`. For simple consts like `DEFAULT_CACHE_CLEANUP_INTERVAL`, the rustSymbol IS the const name directly.

    Step 3 — Author 23 normal rows. Example rows (one per nodeKind — const, interface, class, function):
    ```json
    {
      "id": "config.caches.DEFAULT_CACHE_CLEANUP_INTERVAL",
      "tier": "tier1",
      "ownerModule": "config",
      "rustCrate": "classic-config-core",
      "rustSymbol": "DEFAULT_CACHE_CLEANUP_INTERVAL",
      "nodeExport": "DEFAULT_CACHE_CLEANUP_INTERVAL",
      "nodeKind": "const"
    },
    {
      "id": "config.analysis.JsAnalysisConfig",
      "tier": "tier1",
      "ownerModule": "config",
      "rustCrate": "classic-config-core",
      "rustSymbol": "AnalysisConfig",
      "nodeExport": "JsAnalysisConfig",
      "nodeKind": "interface"
    },
    {
      "id": "config.duplicate_detector.JsConfigDuplicateDetector",
      "tier": "tier1",
      "ownerModule": "config",
      "rustCrate": "classic-config-core",
      "rustSymbol": "ConfigDuplicateDetector",
      "nodeExport": "JsConfigDuplicateDetector",
      "nodeKind": "class"
    },
    {
      "id": "config.hash_cache.getHashCacheStats",
      "tier": "tier1",
      "ownerModule": "config",
      "rustCrate": "classic-config-core",
      "rustSymbol": "get_hash_cache_stats",
      "nodeExport": "getHashCacheStats",
      "nodeKind": "function"
    }
    ```
    Issue 8 note: The class row (`JsConfigDuplicateDetector`) is explicit per-class because classes in NAPI-RS have both a constructor and multiple methods; each promoted class gets ONE row for the class symbol itself (not one row per method). Phase 3 precedent for per-class rows: see `.planning/phases/03-python-tier-collapse/03-06-config-promotion-SUMMARY.md` if it exists — grep for the Phase 3 plan that handled `DuplicateDetector`-equivalent rows. If Phase 3 used per-method rows, reconcile during execution and document the choice in Plan 3's SUMMARY.

    Step 4 — Append rows to `parity_contract.json::tier1Mappings` via Edit tool. Run gate:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python tools/node_api_parity/check_parity_gate.py --repo-root . --update-baseline
    ```
    Bidirectional guard validates every row. If any `rustSymbol` fails (not in rust_api_surface.json), check whether classic-config-core needs a `pub use` addition — this is the Phase 3 A2/Pitfall 8 scenario. Add the `pub use` in the same commit.

    Step 5 — Append describe blocks to `__test__/config.spec.ts` with REAL-SHAPE assertions (MEDIUM concern fix — no shallow `toBeDefined()` no-ops):
    ```typescript
    import { describe, test, expect } from "bun:test";
    import {
      DEFAULT_CACHE_CLEANUP_INTERVAL,
      DEFAULT_CACHE_CLEANUP_THRESHOLD,
      DEFAULT_QUERY_CACHE_CAPACITY,
      getDefaultCacheCleanupInterval,
      getDefaultCacheCleanupThreshold,
      getDefaultQueryCacheCapacity,
      getHashCacheStats,
      resetHashCacheStats,
      clearHashCache,
      detectConfigDuplicates,
      getFcxConfigIssues,
      needsPathDetection,
      JsConfigDuplicateDetector,
    } from "../index.js";

    describe("config: cache constants", () => {
      test("DEFAULT_CACHE_CLEANUP_INTERVAL is a positive number", () => {
        expect(typeof DEFAULT_CACHE_CLEANUP_INTERVAL).toBe("number");
        expect(DEFAULT_CACHE_CLEANUP_INTERVAL).toBeGreaterThan(0);
      });
      test("getDefaultCacheCleanupInterval returns the const value", () => {
        expect(getDefaultCacheCleanupInterval()).toBe(DEFAULT_CACHE_CLEANUP_INTERVAL);
      });
      // Similar real-shape assertions for THRESHOLD and QUERY_CACHE_CAPACITY
      test("DEFAULT_CACHE_CLEANUP_THRESHOLD is a positive number", () => {
        expect(typeof DEFAULT_CACHE_CLEANUP_THRESHOLD).toBe("number");
        expect(DEFAULT_CACHE_CLEANUP_THRESHOLD).toBeGreaterThan(0);
      });
      test("DEFAULT_QUERY_CACHE_CAPACITY is a positive integer", () => {
        expect(typeof DEFAULT_QUERY_CACHE_CAPACITY).toBe("number");
        expect(Number.isInteger(DEFAULT_QUERY_CACHE_CAPACITY)).toBe(true);
        expect(DEFAULT_QUERY_CACHE_CAPACITY).toBeGreaterThan(0);
      });
    });

    describe("config: hash cache stats", () => {
      test("getHashCacheStats returns a stats shape with numeric fields", () => {
        const stats = getHashCacheStats();
        expect(stats).toBeDefined();
        expect(typeof stats.hits).toBe("number");
        expect(typeof stats.misses).toBe("number");
      });
      // MEDIUM concern (LOW): explicit ordering via sequential awaits to avoid Bun parallelism races
      test("resetHashCacheStats followed by getHashCacheStats shows cleared state", async () => {
        resetHashCacheStats();
        // Force sequential ordering to avoid implicit concurrent describe-block races
        await Promise.resolve();
        const stats = getHashCacheStats();
        expect(stats.hits).toBe(0);
        expect(stats.misses).toBe(0);
      });
      test("clearHashCache is callable without throwing", () => {
        expect(() => clearHashCache()).not.toThrow();
      });
    });

    describe("config: duplicate detector class + helpers", () => {
      test("JsConfigDuplicateDetector can be instantiated", () => {
        const det = new JsConfigDuplicateDetector();  // adjust if constructor takes args
        expect(det).toBeDefined();
        // Real-shape check: the instance should be an object with prototype
        expect(typeof det).toBe("object");
      });
      test("detectConfigDuplicates callable with empty input returns an array-like result", () => {
        const result = detectConfigDuplicates([]);  // adjust signature based on live index.d.ts
        expect(result).toBeDefined();
      });
    });

    describe("config: fcx + path detection helpers", () => {
      test("getFcxConfigIssues callable (may throw if no config loaded — asserts error shape)", () => {
        // may throw if no config is loaded — wrap in try and assert on error type
        try {
          const issues = getFcxConfigIssues();
          expect(Array.isArray(issues) || issues === undefined || typeof issues === "object").toBe(true);
        } catch (e) {
          expect(e).toBeInstanceOf(Error);
        }
      });
      test("needsPathDetection returns boolean", () => {
        const result = needsPathDetection("");  // adjust arg based on live signature
        expect(typeof result).toBe("boolean");
      });
    });
    ```
    (Adjust exact assertions based on actual index.d.ts — grep for each function signature before writing the test body. Real-shape smoke tests per MEDIUM concern — no shallow `{} as Type` + `toBeDefined()`.)

    Step 6 — Append cross-runtime test to `__test__/runtime.node.test.mjs`:
    ```javascript
    import { test } from "node:test";
    import assert from "node:assert/strict";
    import { getHashCacheStats, resetHashCacheStats } from "../index.js";

    test("config: getHashCacheStats callable under node:test (cross-runtime D-TEST-02)", () => {
      resetHashCacheStats();
      const stats = getHashCacheStats();
      assert.ok(stats !== undefined);
      assert.strictEqual(typeof stats.hits, "number");
    });
    ```

    Step 7 — Update `runtime_coverage_registry.json`. Create new selector `node-tier1-config-plan03-promoted` with explicit bindingIdentifiers covering the 23 new rows AND rustSymbols covering the 11 proxy rows. Compute `contractIdsHash` via `_stable_id_hash` from `tools.binding_parity_runtime_coverage`.

    Step 8 — Full verification:
    ```powershell
    cd J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node
    bun run parity:gate:local
    bun run test:bun
    bun run test:node
    ```
    All three MUST exit 0.

    Step 9 — Commit as: `Feat: promote 23 Node-exposed config entries + smoke tests (Phase 4 Plan 3 Task 2; NODE-02, NODE-04, NODE-05)` in one atomic commit.
  </action>
  <verify>
    <automated>cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); rows = [r for r in d['tier1Mappings'] if r.get('ownerModule') == 'config' and r.get('nodeExport') and not r.get('rustSymbol', '').endswith('@rust')]; assert len(rows) >= 23, f'expected 23 normal rows; got {len(rows)}'"` exits 0
    - **H2 total row count sanity check**: `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); config_rows = [r for r in d['tier1Mappings'] if r.get('ownerModule') == 'config']; proxy = [r for r in config_rows if r.get('rustSymbol', '').endswith('@rust')]; normal = [r for r in config_rows if r.get('nodeExport') and not r.get('rustSymbol', '').endswith('@rust')]; print(f'proxy={len(proxy)}, normal={len(normal)}, total={len(proxy)+len(normal)}'); assert len(proxy) + len(normal) >= 34, f'Plan 3 total row count below H2 target of 34: got {len(proxy)+len(normal)}'"` exits 0
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); per_owner = d.get('per_owner', {}); config_deferred = per_owner.get('config', {}).get('deferred', -1); assert config_deferred == 0, f'config deferred not 0: {config_deferred}'"` exits 0
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run test:bun` exits 0
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run test:node` exits 0
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run dts:freshness:check` exits 0
  </acceptance_criteria>
  <done>
    23 normal config rows land with real-shape smoke tests; Plan 3 total 11 proxy + 23 normal = 34 rows; bun:test and node:test both pass; config deferred count drops to 0; registry updated via _stable_id_hash.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Verify config promotion before moving to Plan 4</name>
  <what-built>
    - 11 @rust proxy rows for Rust-only config symbols with cross-crate routing (Task 1)
    - 23 normal rows for Node-exposed config entries (Task 2)
    - Plan 3 total: **34 new rows** (11 + 23)
    - New describe blocks in config.spec.ts with real-shape assertions
    - One representative test in runtime.node.test.mjs
    - Updated runtime_coverage_registry.json selector
    - Possible `pub use` additions to classic-config-core and/or classic-crashgen-settings-core lib.rs
  </what-built>
  <action>
    Run the verification commands below and present results to the user. Wait for explicit approval before advancing to Plan 4.
  </action>
  <how-to-verify>
    1. `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node` — all exit 0
    2. `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); print(json.dumps(d.get('per_owner', {}), indent=2))"` — confirm `config.deferred == 0` and `scanlog.deferred ≤ 1`
    3. Row-count sanity: `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); config_rows = [r for r in d['tier1Mappings'] if r.get('ownerModule') == 'config']; print(f'config rows total: {len(config_rows)}; expected at least 34 new rows added vs Plan 2 baseline')"`
    4. rustCrate routing sanity: spot-check 3 proxy rows — at least one MUST have `rustCrate: classic-crashgen-settings-core` (for a crashgen_settings symbol) and at least one MUST have `rustCrate: classic-config-core` (for a config-internal symbol).
    5. Visual scan of new config.spec.ts describe blocks — confirm real-shape assertions, not shallow `toBeDefined()` no-ops.
    6. `git log --oneline -3` — see Plan 3 commits
  </how-to-verify>
  <verify>
    <automated>cd ClassicLib-rs/node-bindings/classic-node &amp;&amp; bun run parity:gate:local</automated>
  </verify>
  <done>User approves by responding with "approved" or equivalent; per_owner.config.deferred == 0 is confirmed; Plan 3 landed the expected 11+23=34 rows with correct cross-crate rustCrate routing per H2.</done>
  <resume-signal>Type "approved" to proceed to Plan 4 (version_registry + HARM-01/02 PE-version).</resume-signal>
</task>

</tasks>

<verification>
1. `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0
2. `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node` all exit 0
3. config deferred count = 0
4. scanlog deferred count ≤ 1 (unchanged from Plan 2)
5. Plan 3 row total: **11 proxy + 23 normal = 34 rows** (H2 reconciliation)
</verification>

<success_criteria>
- **11 proxy + 23 normal = 34 new config rows promoted** (H2 post-Issue-4 reconciliation)
- Gate green with bidirectional guard passing every new row
- config.deferred drops to 0 in per_owner summary
- Smoke tests in bun:test and node:test with real-shape assertions (MEDIUM concern fix)
- No business logic changes (pub use re-exports OK if demanded by the guard)
- All new rows carry rustCrate field per A3 with correct cross-crate routing per H2 (classic-config-core OR classic-crashgen-settings-core)
</success_criteria>

<output>
Create `.planning/phases/04-node-tier-collapse/04-03-config-promotion-SUMMARY.md` with:
- Final reconciled counts: **11 proxy + 23 normal = 34 rows** (H2)
- Cross-crate rustCrate routing distribution (how many rows → classic-config-core, how many → classic-crashgen-settings-core)
- Any `pub use` re-exports added to classic-config-core or classic-crashgen-settings-core lib.rs
- Guard diagnostics that surfaced and remediation
- Confirmation that per_owner.config.deferred == 0
</output>
