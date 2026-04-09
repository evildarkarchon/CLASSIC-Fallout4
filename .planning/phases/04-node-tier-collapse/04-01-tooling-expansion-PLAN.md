---
phase: 04-node-tier-collapse
plan: 01
plan_id: 04-01
title: Tooling Expansion + Bidirectional Guard + A10 Sizing + Env Smoke
type: execute
wave: 0
depends_on: []
files_modified:
  - tools/node_api_parity/generate_baseline.py
  - tools/node_api_parity/check_parity_gate.py
  - tools/node_api_parity/tests/__init__.py
  - tools/node_api_parity/tests/conftest.py
  - tools/node_api_parity/tests/test_generate_baseline_targets.py
  - tools/node_api_parity/tests/test_check_parity_gate.py
  - tools/node_api_parity/tests/test_validate_contract_surface.py
  - .planning/phases/04-node-tier-collapse/04-01-A10-sizing.json
  - .planning/phases/04-node-tier-collapse/04-01-A10-sizing.md
  - docs/implementation/node_api_parity/baseline/parity_contract.json
  - docs/implementation/node_api_parity/baseline/parity_contract.md
  - docs/implementation/node_api_parity/baseline/parity_diff_report.json
  - docs/implementation/node_api_parity/baseline/parity_diff_report.md
  - docs/implementation/node_api_parity/baseline/rust_api_surface.json
  - docs/implementation/node_api_parity/baseline/node_api_surface.json
  - docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json
  - docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md
  - docs/implementation/node_api_parity/baseline/tier1_gate_report.md
autonomous: true
requirements_addressed: [NODE-01]
requirements: [NODE-01]
must_haves:
  truths:
    - "`tools/node_api_parity/generate_baseline.py::RUST_TARGET_CRATES` contains AT LEAST 19 entries (the original 10 plus 9 new; `>= 19` not `== 19` so Plan 5 can absorb a 20th crate without blocking Plan 1) — every entry points to a lib.rs that `parse_rust_surface()` parses to a non-empty symbol list"
    - "`RUST_FULL_INVENTORY_CRATES` set and `include_rust_symbol()` filter function are deleted from `generate_baseline.py`; `parse_rust_surface()` returns every public symbol for every tracked crate"
    - "`tools/node_api_parity/check_parity_gate.py::validate_contract_surface()` exists as a bidirectional guard that FAILS-CLOSED on malformed row shapes: missing rustSymbol, missing nodeExport on non-@rust rows, empty rows (neither field present). Only `rustSymbol.endswith('@rust')` skips the Node-side check. Runs unconditionally on every gate invocation."
    - "The guard's diagnostic output explicitly names the failing side AND the malformed shape: (a) `row {id} missing rustSymbol`, (b) `row {id} is normal-shape but missing nodeExport`, (c) `row {id} is empty (no rustSymbol and no nodeExport)`, (d) Rust-side miss says 'Add `pub use <sub_module>::<symbol>;` to `<rustCrate>/lib.rs`' (using `rustCrate` when present, `<unknown>` fallback), (e) Node-side miss says 'Rust function still uses snake_case or <name> is a typo. Run `bun run build` to refresh index.d.ts.'"
    - "Contract rows with `rustSymbol` ending in `@rust` are the ONLY rows that skip the Node-side check (A7 precedent from Phase 3 Scenario E). A row with no `nodeExport` AND no `@rust` suffix is MALFORMED and MUST fire the guard (H1 fail-closed hardening)."
    - "`bun run build` end-to-end smoke test succeeds: `napi build --release --platform --manifest-path ./Cargo.toml` produces the native `.node` file; `tsc -p tsconfig.json` produces `dist/cli/*.js`; `bun run dts:freshness:check` exits 0"
    - "A10 sizing report at `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.{json,md}` lists per-owner DEFERRED ROW counts sourced from BOTH `docs/implementation/node_api_parity/baseline/parity_diff_report.json::gaps` (PRIMARY) AND `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json` (cross-validation). Plans 2–5 read this before sizing their task budgets. Per U2, the primary source is the live diff inventory, not the coverage summary alone."
    - "Pytest test files exist under `tools/node_api_parity/tests/` covering: (a) every `RUST_TARGET_CRATES` entry parses to non-empty symbol list, (b) synthetic contract rows exercise ALL branches of the bidirectional guard INCLUDING fail-closed rejection of 3 malformed row shapes (H1), (c) floor baseline test asserts tier1Mapping count (used to detect regressions in later plans), (d) `test_tier2_definition_removed_after_plan_6` as `@pytest.mark.xfail(strict=True)` (flipped to passing in Plan 6)"
    - "`bun run parity:gate:local` exits 0 against the expanded contract (no Rust source changes in Plan 1 — the gate still passes because the 261 existing tier1Mappings remain valid and only the surface JSONs grow)"
  artifacts:
    - path: "tools/node_api_parity/generate_baseline.py"
      provides: "RUST_TARGET_CRATES expanded to 19 entries (>=19 not ==19); RUST_FULL_INVENTORY_CRATES + include_rust_symbol() deleted; RUST_OWNER_BY_CRATE and SQUAD_BY_OWNER extended for the 9 new owners (matching Phase 3 Python owner structure per A5)"
      contains: "classic-crashgen-settings-core"
    - path: "tools/node_api_parity/check_parity_gate.py"
      provides: "validate_contract_surface() bidirectional guard with rustCrate-aware diagnostics, @rust proxy-row handling, AND fail-closed rejection of malformed rows (H1)"
      contains: "def validate_contract_surface"
    - path: "tools/node_api_parity/tests/test_generate_baseline_targets.py"
      provides: "Per-crate parse_rust_surface() non-empty assertion preventing path typos (Pitfall 5 guard)"
      min_lines: 30
    - path: "tools/node_api_parity/tests/test_validate_contract_surface.py"
      provides: "Unit tests for bidirectional guard — synthetic contracts + surfaces + expected diagnostics; includes fail-closed fixtures for 3 malformed row shapes (H1)"
      min_lines: 120
    - path: "tools/node_api_parity/tests/test_check_parity_gate.py"
      provides: "test_tier1_contract_total_baseline_floor (Plan 1 snapshot) and test_tier2_definition_removed_after_plan_6 (xfail strict=true)"
      min_lines: 40
    - path: ".planning/phases/04-node-tier-collapse/04-01-A10-sizing.json"
      provides: "Per-owner deferred row count breakdown sourced from parity_diff_report.json::gaps (PRIMARY per U2) + runtime_coverage_summary.json (cross-validation); read by Plans 2-5 to size task budgets"
    - path: ".planning/phases/04-node-tier-collapse/04-01-A10-sizing.md"
      provides: "Human-readable sizing table mirroring the JSON; lists surplus/deficit relative to Plan-skeleton estimates; documents the dual-source reconciliation"
  key_links:
    - from: "tools/node_api_parity/check_parity_gate.py::main()"
      to: "tools/node_api_parity/check_parity_gate.py::validate_contract_surface()"
      via: "unconditional call between parse_node_surface() and generate_diff_report()"
      pattern: "validate_contract_surface\\(contract, rust_manifest, node_manifest\\)"
    - from: "tools/node_api_parity/generate_baseline.py::RUST_TARGET_CRATES"
      to: "Plans 2-5 promotion targets"
      via: "parse_rust_surface() enumeration feeds rust_api_surface.json which the guard validates against"
      pattern: "classic-crashgen-settings-core"
    - from: ".planning/phases/04-node-tier-collapse/04-01-A10-sizing.{json,md}"
      to: "Plans 2-5 task budgets"
      via: "planner reads per-owner counts from parity_diff_report.json::gaps (PRIMARY per U2) before writing downstream plans"
      pattern: "owner.*count"
---

<objective>
Phase 4 Plan 1 is the keystone. Expand `tools/node_api_parity/generate_baseline.py::RUST_TARGET_CRATES` from 10 to 19 entries (matching Phase 3's set PLUS `classic-crashgen-settings-core` per research amendment A1). Delete `RUST_FULL_INVENTORY_CRATES` + `include_rust_symbol()` so every tracked crate produces full public-symbol output. Add the bidirectional `validate_contract_surface()` guard to `check_parity_gate.py` that FAILS-CLOSED on malformed row shapes (per H1 hardening: missing rustSymbol, missing nodeExport on non-@rust rows, empty rows — all must fire diagnostics). Run `bun run build` end-to-end as a PowerShell smoke test to verify the executor's Node/napi/MSVC environment works before any promotion plan depends on it. Produce an A10-style sizing report at `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.{json,md}` sourced from BOTH `parity_diff_report.json::gaps` (PRIMARY per U2) AND `runtime_coverage_summary.json` (cross-validation) so Plans 2–5 know their actual task budgets before they start. No Rust source changes in this plan.

Purpose:
- De-risk the keystone before promotion work starts (Phase 3 Plan 01 precedent)
- Catch `bun run build` env failures in Plan 1, not as a downstream blocker (D-DTS-02)
- Front-load the A10 sizing to avoid Phase 3 Plan 09a's 593-row residual surprise (D-PLAN-05). **U2 fix**: primary source is `parity_diff_report.json::gaps` (the live diff inventory), NOT `runtime_coverage_summary.json` alone — the 109 deferred entries come from tracked-surface expansion INSIDE the same backlog entries, not "8 extra entries" in the summary.
- Guarantee that every row authored in Plans 2-5 gets a bidirectional check before landing AND that malformed rows are REJECTED (D-TOOL-03/04 + H1 fail-closed hardening)

Output:
- 19-entry `RUST_TARGET_CRATES` in `generate_baseline.py` (plus `RUST_OWNER_BY_CRATE` / `SQUAD_BY_OWNER` extensions per A5)
- `validate_contract_surface()` helper in `check_parity_gate.py` wired into `main()` unconditionally, with fail-closed diagnostics for malformed row shapes (H1)
- 5 pytest files under `tools/node_api_parity/tests/` (Wave 0 scaffolding) including automated fail-closed fixtures
- Dual-source sizing report consumed by Plans 2-5
- Refreshed baseline artifacts — gate still green against the 261 existing tier1Mappings
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
@./CLAUDE.md
@./AGENTS.md

<interfaces>
<!-- Key live source anchors from RESEARCH.md Sources section — verified 2026-04-08 -->

**Current `RUST_TARGET_CRATES` shape** (10 entries, `tools/node_api_parity/generate_baseline.py` line 24):
```python
RUST_TARGET_CRATES: dict[str, str] = {
    "classic-scanlog-core":          "ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs",
    "classic-config-core":           "ClassicLib-rs/business-logic/classic-config-core/src/lib.rs",
    "classic-version-registry-core": "ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs",
    # ... 7 more entries (see live source)
}
```

**Expand to 19 entries** (per A1, A5 — Phase 3's full set INCLUDING `classic-crashgen-settings-core`). Pre-state verified 2026-04-08: live file already contains the 10 keys `classic-scanlog-core`, `classic-config-core`, `classic-version-registry-core`, `classic-file-io-core`, `classic-path-core`, `classic-settings-core`, `classic-message-core`, `classic-perf-core`, `classic-registry-core`, `classic-shared-core`. The 9 NEW entries to add (set difference between the target 19 and the enumerated original 10) are:
```python
"classic-yaml-core":               "ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs",
"classic-version-core":            "ClassicLib-rs/business-logic/classic-version-core/src/lib.rs",
"classic-web-core":                "ClassicLib-rs/business-logic/classic-web-core/src/lib.rs",
"classic-crashgen-settings-core":  "ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs",
"classic-update-core":             "ClassicLib-rs/business-logic/classic-update-core/src/lib.rs",
"classic-xse-core":                "ClassicLib-rs/business-logic/classic-xse-core/src/lib.rs",
"classic-database-core":           "ClassicLib-rs/business-logic/classic-database-core/src/lib.rs",
"classic-scangame-core":           "ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs",
"classic-constants-core":          "ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs",
```
Note: The Step 0 pre-state assertion must confirm the live count is 10 before Step 2 mutates it. If the live count differs, abort and reconcile (the planner assumed exactly 10 entries today).

**Phase 3 reference for `validate_contract_surface()` shape** (Python Pitfall 2 guard at `tools/python_api_parity/check_parity_gate.py` lines 31-76):
The Python version validates ONE direction (rustSymbol only). Phase 4 extends it to BOTH directions AND adds fail-closed handling of malformed rows per H1.

**H1 fail-closed row shapes to reject**:
1. **Missing `rustSymbol`** (any shape, any nodeExport) → diagnostic `"row {id} missing rustSymbol"` — no row should be authored without a Rust-side anchor.
2. **Missing `nodeExport` AND `rustSymbol` does not end in `@rust`** → diagnostic `"row {id} is normal-shape but missing nodeExport"` — only `@rust` proxy rows are allowed to lack a nodeExport field.
3. **Empty row** (neither `rustSymbol` nor `nodeExport` present) → diagnostic `"row {id} is empty (no rustSymbol and no nodeExport)"` — an empty row is always a bug.

Only `rustSymbol.endswith("@rust")` allows the Node-side check to be skipped. All three malformed shapes MUST fire diagnostics; none may silently pass.

**Lines to delete in `generate_baseline.py`**:
- `RUST_FULL_INVENTORY_CRATES` set (around line 50-54)
- `include_rust_symbol()` function (around line 64-70)
- Every callsite of `include_rust_symbol()` inside `parse_rust_surface()` — replace with unconditional "include every symbol"

**Phase 3 Plan 01 precedent file** (already committed): `.planning/phases/03-python-tier-collapse/03-01-tooling-expansion-PLAN.md`

**Phase 3 Plan 01 sizing output format** (reference for Task 4): `.planning/phases/03-python-tier-collapse/03-01-A10-sizing.json` — top-level `{ "owners": [{ "owner": "scanlog", "deferred": 67, "tier1": ... }, ...], "total_deferred": N }` shape.

**U2 PRIMARY source schema** — `docs/implementation/node_api_parity/baseline/parity_diff_report.json::gaps` (verified 2026-04-08):
```json
{
  "gaps": [
    {
      "id": "node-deferred-scanlog-060",
      "gap_type": "rust_unmapped" | "node_unmapped",
      "ownerModule": "scanlog",
      "rustSymbols": [...],
      "bindingIdentifiers": [...],
      "tier": "tier2"
    },
    ...
  ]
}
```
Each `gap` is ONE deferred row. Count `gaps[]` entries filtered by `ownerModule` to get per-owner deferred row counts. This is load-bearing for Plan 5's residual absorption — do NOT use `runtime_coverage_summary.json::per_owner.*.deferred` as the primary count.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Expand RUST_TARGET_CRATES from 10 to 19 + delete inventory filter + extend owner/squad maps</name>
  <read_first>
    - `tools/node_api_parity/generate_baseline.py` (entire file — you are modifying it; read to confirm current RUST_TARGET_CRATES contents + line numbers for RUST_FULL_INVENTORY_CRATES and include_rust_symbol)
    - `.planning/phases/04-node-tier-collapse/04-CONTEXT.md` §Research Amendments (A1, A3, A5 are load-bearing)
    - `.planning/phases/04-node-tier-collapse/04-RESEARCH.md` §Open Questions 1 and 5 (confirm 19-crate decision + distinct owner labels)
    - `tools/python_api_parity/generate_baseline.py` lines 24-150 (reference shape for RUST_TARGET_CRATES + SQUAD_BY_OWNER expansion)
    - `.planning/phases/03-python-tier-collapse/03-01-tooling-expansion-PLAN.md` (precedent for keystone tooling expansion)
    - `ClassicLib-rs/node-bindings/classic-node/src/crashgen_rules.rs` (confirm direct classic-crashgen-settings-core binding exists — this is the A1 rationale)
    - `docs/implementation/node_api_parity/baseline/rust_api_surface.json` (reference: confirm where `classic-crashgen-settings-core` rows belong — ownership decision source)
  </read_first>
  <behavior>
    - `RUST_TARGET_CRATES` contains exactly 19 keys after edit (10 original + 9 new, listed verbatim in the interfaces block above). `classic-crashgen-settings-core` IS present.
    - `RUST_FULL_INVENTORY_CRATES` is deleted. `include_rust_symbol()` is deleted. Every callsite is replaced with "include unconditionally".
    - `RUST_OWNER_BY_CRATE` has 19 entries with distinct owner labels matching Phase 3 structure (per A5: `shared`, `perf`, `registry` stay distinct — do NOT collapse to `aux`). Exact Phase 3 labels: `scanlog`, `config`, `version_registry`, `shared`, `perf`, `registry`, `message`, `file_io`, `path`, `settings`, `yaml`, `version`, `web`, `xse`, `database`, `scangame`, `constants`, `crashgen_settings`, `update`.
    - **Owner fallback tightening (MEDIUM concern fix)**: Every crate MUST have an explicit owner label. There is NO "default to aux if no match" fallback. If a `classic-crashgen-settings-core` row falls through (no explicit owner), the sizing pipeline FAILS LOUD — do not silently bucket unresolved rows to aux.
    - `SQUAD_BY_OWNER` is extended to cover the new owners (Phase 3 had two squads; match that pattern or document the choice).
    - Pytest `tools/node_api_parity/tests/test_generate_baseline_targets.py::test_every_target_crate_parses_non_empty` exists and passes: for each `(crate, path)` in `RUST_TARGET_CRATES`, imports the module and asserts `parse_rust_surface({crate: path}, ...)` returns a non-empty symbol list — catches Pitfall 5 path typos.
    - **`>= 19` not `== 19` assertion (MEDIUM concern fix)**: Test uses `assert len(RUST_TARGET_CRATES) >= 19` (not `== 19`) so Plan 5's A10 residual absorption can add a 20th crate without blocking Plan 1. Rationale: tight equality is hostile to future discovery; floor is the load-bearing semantic.
  </behavior>
  <action>
    Step 0 — Pre-state enumeration (CRITICAL — Issue 5 fix). Before editing, capture the current `RUST_TARGET_CRATES` keys to verify the 10 → 19 expansion math. From repo root (PowerShell preferred per user rule):
    ```powershell
    cd J:/CLASSIC-Fallout4
    python -c "import sys; sys.path.insert(0, 'tools/node_api_parity'); import generate_baseline as gb; assert len(gb.RUST_TARGET_CRATES) == 10, f'unexpected pre-state: {len(gb.RUST_TARGET_CRATES)}'; print('PRE-STATE keys (10):', sorted(gb.RUST_TARGET_CRATES.keys()))"
    ```
    Record the exact 10 keys printed in the SUMMARY's "Pre-state" section. Verified pre-state (2026-04-08): the live file at `tools/node_api_parity/generate_baseline.py` lines 24-35 contains exactly these 10 entries: `classic-scanlog-core`, `classic-config-core`, `classic-version-registry-core`, `classic-file-io-core`, `classic-path-core`, `classic-settings-core`, `classic-message-core`, `classic-perf-core`, `classic-registry-core`, `classic-shared-core`. The 9 NEW entries to add are: `classic-yaml-core`, `classic-version-core`, `classic-web-core`, `classic-crashgen-settings-core`, `classic-update-core`, `classic-xse-core`, `classic-database-core`, `classic-scangame-core`, `classic-constants-core`. Confirm by computing the set difference between the target 19 and the enumerated original 10 — do NOT hardcode the 9. Verify `classic-crashgen-settings-core` (per A1) appears in the final list AND is NOT in the original 10. The pre-state enumeration assertion MUST pass before Step 1 begins; if the live file already has != 10 entries, abort and reconcile in the SUMMARY (planning assumed pre-state of 10).

    Step 1 — Create the Wave 0 test scaffold first (TDD order):
    - Create `tools/node_api_parity/tests/__init__.py` as empty file
    - Create `tools/node_api_parity/tests/conftest.py` that adds `tools/node_api_parity/` to `sys.path` (mirror `tools/python_api_parity/tests/conftest.py`)
    - Create `tools/node_api_parity/tests/test_generate_baseline_targets.py` with:
      ```python
      def test_every_target_crate_parses_non_empty():
          import generate_baseline as gb
          from pathlib import Path
          repo_root = Path(__file__).resolve().parents[3]
          # MEDIUM concern fix: `>= 19` not `== 19` so Plan 5 can add a 20th crate
          # without blocking Plan 1. Floor is load-bearing; tight equality is hostile.
          assert len(gb.RUST_TARGET_CRATES) >= 19, f"expected >= 19 entries, got {len(gb.RUST_TARGET_CRATES)}"
          for crate, rel in gb.RUST_TARGET_CRATES.items():
              path = repo_root / rel
              assert path.is_file(), f"{crate}: path does not exist: {path}"
              surface = gb.parse_rust_surface({crate: rel}, repo_root=repo_root)
              symbols = surface.get("symbols", [])
              assert len(symbols) > 0, f"{crate}: parse_rust_surface returned 0 symbols — likely a path typo or empty lib.rs"
      ```
    - Run the test — it MUST fail initially (RUST_TARGET_CRATES still has 10 entries). This is the RED state.

    Step 2 — Edit `tools/node_api_parity/generate_baseline.py`:
    - Add the 9 new entries to `RUST_TARGET_CRATES` (exact paths in the interfaces block). Confirm with `Read` that every `lib.rs` path exists. Use `Edit` tool not `Write`.
    - Delete the `RUST_FULL_INVENTORY_CRATES` set declaration (read the file first to find exact line numbers; do not guess).
    - Delete the `include_rust_symbol()` function.
    - Replace every callsite of `include_rust_symbol(...)` with an unconditional `True` or remove the `if` branch entirely. (Use Grep to find all callsites in `generate_baseline.py` before editing.)
    - Extend `RUST_OWNER_BY_CRATE` to cover the 9 new crates. Use the exact label set from Phase 3 (see read_first). Distinct owners per A5 — do NOT collapse `shared`/`perf`/`registry` to `aux`. **Crashgen routing**: `classic-crashgen-settings-core` gets an explicit owner label. If the Phase 3 Python owner map uses a specific label (e.g., `crashgen_settings`), mirror it. Do NOT leave it unresolved — if no explicit owner is assigned, the owner-selection pipeline must FAIL LOUD (MEDIUM concern: no silent default to aux).
    - Extend `SQUAD_BY_OWNER` to cover the new owners (you may add them to the existing squads or extend the squad dict; the squad concept is not load-bearing for the gate's exit code per CONTEXT Claude's Discretion).
    - Do NOT touch the `tier='tier2'` label assignments at lines 190/210/230/250 — those stay as vestigial labels and are swept in Plan 6.

    Step 3 — Re-run `python -m pytest tools/node_api_parity/tests/test_generate_baseline_targets.py -q` from the repo root. MUST exit 0 (GREEN state). If any crate returns 0 symbols, the path is wrong — fix the path, re-run.

    Step 4 — Refresh baselines:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python tools/node_api_parity/generate_baseline.py --repo-root . --write-baseline
    python tools/node_api_parity/check_parity_gate.py --repo-root . --update-baseline
    ```
    Gate may still pass (the 261 existing rows are still valid); the surface JSONs just grow to include the newly-tracked crates' symbols.

    Commit as: `Refactor: expand Node RUST_TARGET_CRATES from 10 to 19 crates (Phase 4 Plan 1 Task 1; NODE-01)` with the test file, generate_baseline.py edits, and refreshed baselines in ONE commit.
  </action>
  <verify>
    <automated>python -m pytest tools/node_api_parity/tests/test_generate_baseline_targets.py -q</automated>
  </verify>
  <acceptance_criteria>
    - **Pre-state assertion (Step 0)**: `python -c "import sys; sys.path.insert(0, 'tools/node_api_parity'); import generate_baseline as gb; assert len(gb.RUST_TARGET_CRATES) == 10"` exits 0 BEFORE the edit (run via a subprocess with the un-modified tree, OR use git stash + restore)
    - `python -c "import sys; sys.path.insert(0, 'tools/node_api_parity'); import generate_baseline as gb; assert len(gb.RUST_TARGET_CRATES) >= 19" ` exits 0 (MEDIUM concern fix: `>= 19` not `== 19`)
    - `python -c "import sys; sys.path.insert(0, 'tools/node_api_parity'); import generate_baseline as gb; PRE10={'classic-scanlog-core','classic-config-core','classic-version-registry-core','classic-file-io-core','classic-path-core','classic-settings-core','classic-message-core','classic-perf-core','classic-registry-core','classic-shared-core'}; new_set = set(gb.RUST_TARGET_CRATES.keys()) - PRE10; assert len(new_set) >= 9, f'expected >= 9 new entries, got {len(new_set)}: {sorted(new_set)}'"` exits 0 (set-difference verification, not hardcoded)
    - `python -c "import sys; sys.path.insert(0, 'tools/node_api_parity'); import generate_baseline as gb; assert 'classic-crashgen-settings-core' in gb.RUST_TARGET_CRATES"` exits 0 (A1 enforcement — must appear post-edit AND must NOT have appeared pre-edit)
    - `python -c "import sys; sys.path.insert(0, 'tools/node_api_parity'); import generate_baseline as gb; assert not hasattr(gb, 'RUST_FULL_INVENTORY_CRATES')"` exits 0
    - `python -c "import sys; sys.path.insert(0, 'tools/node_api_parity'); import generate_baseline as gb; assert not hasattr(gb, 'include_rust_symbol')"` exits 0
    - **Owner fallback fail-loud check (MEDIUM)**: `python -c "import sys; sys.path.insert(0, 'tools/node_api_parity'); import generate_baseline as gb; assert 'classic-crashgen-settings-core' in gb.RUST_OWNER_BY_CRATE, 'classic-crashgen-settings-core must have an explicit owner label — no default-to-aux fallback'"` exits 0
    - `python -m pytest tools/node_api_parity/tests/test_generate_baseline_targets.py -q` exits 0
    - `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0 (gate still passes)
  </acceptance_criteria>
  <done>
    RUST_TARGET_CRATES >= 19 entries, inventory filter deleted, owner/squad maps extended with explicit labels (no silent default to aux), test passing, baselines refreshed, gate green.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add bidirectional validate_contract_surface() guard (H1 fail-closed) to check_parity_gate.py + Wave 0 test scaffold</name>
  <read_first>
    - `tools/node_api_parity/check_parity_gate.py` (entire file — you are modifying main() to call the new guard)
    - `tools/python_api_parity/check_parity_gate.py` lines 31-76 (Phase 3 one-directional precedent to extend)
    - `.planning/phases/04-node-tier-collapse/04-CONTEXT.md` §Research Amendments A3, A7 (rustCrate on new rows only; @rust-suffix proxy rows)
    - `.planning/phases/04-node-tier-collapse/04-RESEARCH.md` §Pattern 3 (bidirectional guard shape + example diagnostic text)
    - `.planning/phases/04-node-tier-collapse/04-RESEARCH.md` §Pattern 4 (@rust proxy row shape)
    - `.planning/phases/04-node-tier-collapse/04-REVIEWS.md` §"H1 — Plan 01 validate_contract_surface() fail-closed hardening" (load-bearing — defines all 3 malformed shapes)
    - `docs/implementation/node_api_parity/baseline/parity_contract.json` (read first 50 tier1Mapping rows to understand current shape — no rustCrate field, no @rust suffix)
  </read_first>
  <behavior>
    - `validate_contract_surface(contract, rust_manifest, node_manifest) -> list[str]` exists in `check_parity_gate.py` and is called unconditionally inside `main()` between `parse_node_surface()` and `generate_diff_report()`.
    - **H1 fail-closed shapes (CRITICAL)**: The function iterates every `tier1Mappings` row and rejects ALL of the following malformed shapes with explicit diagnostics before performing surface lookups:
      1. **Empty row** — if both `rustSymbol` AND `nodeExport` are missing → diagnostic `"row {id} is empty (no rustSymbol and no nodeExport)"`
      2. **Missing rustSymbol** — if `rustSymbol` is missing (any `nodeExport` state) → diagnostic `"row {id} missing rustSymbol"`
      3. **Missing nodeExport on non-proxy row** — if `rustSymbol` is present AND does NOT end in `@rust` AND `nodeExport` is missing → diagnostic `"row {id} is normal-shape but missing nodeExport"`
    - After the H1 malformed-shape rejections, the function asserts two positive conditions:
      1. If `rustSymbol` is present AND (not a proxy OR stripped of `@rust`): `effective_rust_symbol ∈ rust_symbols`. Failing rows append a diagnostic with Rust-side remediation hint using `rustCrate` field when present, falling back to `<unknown>` for legacy rows.
      2. If `nodeExport` is present AND `rustSymbol` does NOT end in `@rust`: `nodeExport ∈ node_exports`. Failing rows append a diagnostic with Node-side remediation hint referencing `bun run build` + index.d.ts refresh.
    - **ONLY `rustSymbol.endswith("@rust")` skips the Node-side check.** A row missing `nodeExport` without the `@rust` suffix is malformed and fires diagnostic (2) above.
    - If `diagnostics` is non-empty after the walk, `main()` prints each message to stderr and exits with code 2 (matching Phase 3 Pitfall 2 guard behavior).
    - Pytest `tools/node_api_parity/tests/test_validate_contract_surface.py` has AT LEAST 9 test cases: (a) empty contract → empty diagnostics, (b) valid rustSymbol+nodeExport → empty diagnostics, (c) missing rustSymbol on normal row → "missing rustSymbol" diagnostic, (d) missing nodeExport on normal row → "normal-shape but missing nodeExport" diagnostic, (e) empty row (both missing) → "empty" diagnostic, (f) @rust-suffix row with no nodeExport → only Rust-side check (suffix stripped, no malformed rejection), (g) Rust-side miss produces rustCrate-aware remediation hint, (h) Node-side miss produces `bun run build` hint, (i) row with rustCrate absent → diagnostic uses `<unknown>` fallback.
  </behavior>
  <action>
    Step 1 — Create `tools/node_api_parity/tests/test_validate_contract_surface.py` with failing tests (RED). Schema verification (Issue 13): the live `docs/implementation/node_api_parity/baseline/rust_api_surface.json` has top-level `symbols` array with each entry as `{"symbol": "...", "kind": "...", "crate": "...", ...}`; `node_api_surface.json` has top-level `exports` array with each entry as `{"export": "...", "kind": "...", "owner_module": "...", ...}`. The synthetic fixtures below match the live shape exactly (verified 2026-04-08 by reading the first 50 lines of each file). The minimum keys the guard reads are `symbol` and `export` — additional fields are optional in the test fixture.
    ```python
    import pytest
    # import check_parity_gate as gate  # will be importable once sys.path is set via conftest

    @pytest.fixture
    def rust_manifest():
        # Live schema: top-level "symbols" array, each entry has {"symbol": str, "kind": str, "crate": str, ...}
        return {"symbols": [{"symbol": "parse_version"}, {"symbol": "extract_pe_version"}, {"symbol": "FormIDAnalyzer"}]}

    @pytest.fixture
    def node_manifest():
        # Live schema: top-level "exports" array, each entry has {"export": str, "kind": str, "owner_module": str, ...}
        return {"exports": [{"export": "parseVersion"}, {"export": "extractPeVersion"}, {"export": "JsAnalysisConfig"}]}

    def test_empty_contract_empty_diagnostics(rust_manifest, node_manifest):
        import check_parity_gate as gate
        diagnostics = gate.validate_contract_surface({"tier1Mappings": []}, rust_manifest, node_manifest)
        assert diagnostics == []

    def test_valid_row_empty_diagnostics(rust_manifest, node_manifest):
        import check_parity_gate as gate
        contract = {"tier1Mappings": [
            {"id": "row-1", "rustSymbol": "parse_version", "nodeExport": "parseVersion"}
        ]}
        assert gate.validate_contract_surface(contract, rust_manifest, node_manifest) == []

    # ============ H1 FAIL-CLOSED TESTS (MALFORMED ROW REJECTION) ============

    def test_h1_empty_row_is_rejected(rust_manifest, node_manifest):
        """H1: row with NEITHER rustSymbol NOR nodeExport MUST fire a diagnostic."""
        import check_parity_gate as gate
        contract = {"tier1Mappings": [
            {"id": "empty-row"}  # no rustSymbol, no nodeExport
        ]}
        diagnostics = gate.validate_contract_surface(contract, rust_manifest, node_manifest)
        assert len(diagnostics) >= 1
        assert any("empty-row" in d and ("empty" in d.lower() or "missing" in d.lower()) for d in diagnostics)

    def test_h1_missing_rust_symbol_is_rejected(rust_manifest, node_manifest):
        """H1: row with nodeExport but NO rustSymbol MUST fire 'missing rustSymbol'."""
        import check_parity_gate as gate
        contract = {"tier1Mappings": [
            {"id": "no-rust-row", "nodeExport": "parseVersion"}
        ]}
        diagnostics = gate.validate_contract_surface(contract, rust_manifest, node_manifest)
        assert len(diagnostics) >= 1
        assert any("no-rust-row" in d and "rustSymbol" in d for d in diagnostics)

    def test_h1_normal_row_missing_node_export_is_rejected(rust_manifest, node_manifest):
        """H1: row with rustSymbol (no @rust) and NO nodeExport MUST fire 'normal-shape but missing nodeExport'."""
        import check_parity_gate as gate
        contract = {"tier1Mappings": [
            {"id": "no-node-row", "rustSymbol": "parse_version", "rustCrate": "classic-version-core"}
        ]}
        diagnostics = gate.validate_contract_surface(contract, rust_manifest, node_manifest)
        assert len(diagnostics) >= 1
        assert any("no-node-row" in d and "nodeExport" in d for d in diagnostics)

    def test_h1_at_rust_proxy_without_node_export_is_accepted(rust_manifest, node_manifest):
        """H1: ONLY @rust-suffixed rows may omit nodeExport. Proxy row with FormIDAnalyzer@rust is valid."""
        import check_parity_gate as gate
        contract = {"tier1Mappings": [
            {"id": "proxy-row", "rustSymbol": "FormIDAnalyzer@rust", "rustCrate": "classic-scanlog-core"}
        ]}
        # FormIDAnalyzer IS in rust_manifest (suffix stripped), no nodeExport to check — should pass
        diagnostics = gate.validate_contract_surface(contract, rust_manifest, node_manifest)
        assert diagnostics == []

    # ============ POSITIVE SURFACE-MISS DIAGNOSTICS ============

    def test_missing_rust_symbol_diagnostic(rust_manifest, node_manifest):
        import check_parity_gate as gate
        contract = {"tier1Mappings": [
            {"id": "row-bad", "rustSymbol": "missing_fn", "nodeExport": "parseVersion",
             "rustCrate": "classic-version-core"}
        ]}
        diagnostics = gate.validate_contract_surface(contract, rust_manifest, node_manifest)
        assert len(diagnostics) >= 1
        assert any("missing_fn" in d and "classic-version-core" in d and "pub use" in d for d in diagnostics)

    def test_missing_node_export_diagnostic(rust_manifest, node_manifest):
        import check_parity_gate as gate
        contract = {"tier1Mappings": [
            {"id": "row-bad", "rustSymbol": "parse_version", "nodeExport": "parse_version"}
        ]}
        diagnostics = gate.validate_contract_surface(contract, rust_manifest, node_manifest)
        assert len(diagnostics) >= 1
        # Node-side miss surfaces the camelCase/snake_case hint
        assert any("parse_version" in d and ("bun run build" in d or "index.d.ts" in d) for d in diagnostics)

    def test_at_rust_suffix_rust_missing_diagnostic(rust_manifest, node_manifest):
        """@rust proxy row where the stripped symbol is NOT in rust_manifest → Rust-side diagnostic."""
        import check_parity_gate as gate
        contract = {"tier1Mappings": [
            {"id": "proxy-missing", "rustSymbol": "missing_type@rust", "rustCrate": "classic-scanlog-core"}
        ]}
        diagnostics = gate.validate_contract_surface(contract, rust_manifest, node_manifest)
        assert len(diagnostics) >= 1
        assert any("missing_type" in d and "classic-scanlog-core" in d for d in diagnostics)

    def test_missing_rust_crate_fallback(rust_manifest, node_manifest):
        """Legacy row without rustCrate → diagnostic uses <unknown> fallback."""
        import check_parity_gate as gate
        contract = {"tier1Mappings": [
            {"id": "legacy-row", "rustSymbol": "missing_fn", "nodeExport": "parseVersion"}
        ]}
        diagnostics = gate.validate_contract_surface(contract, rust_manifest, node_manifest)
        assert len(diagnostics) >= 1
        assert any("<unknown>" in d for d in diagnostics)
    ```
    Run the test — all 10 tests MUST fail (`validate_contract_surface` doesn't exist yet). This is RED.

    Step 2 — Edit `tools/node_api_parity/check_parity_gate.py`:
    - Add `validate_contract_surface(contract, rust_manifest, node_manifest)` at module level (before `main()`). The implementation implements H1 fail-closed behavior:
      ```python
      def validate_contract_surface(contract, rust_manifest, node_manifest):
          """Bidirectional guard with H1 fail-closed malformed-row rejection.

          Rejects:
          - Rows missing rustSymbol (any shape)
          - Rows missing nodeExport when rustSymbol does NOT end in @rust
          - Empty rows (neither field present)

          Accepts:
          - rustSymbol + nodeExport (normal rows) — checks both directions
          - rustSymbol@rust with no nodeExport (proxy rows) — checks only Rust side
          """
          rust_symbols = {item["symbol"] for item in rust_manifest.get("symbols", [])}
          node_exports = {item["export"] for item in node_manifest.get("exports", [])}
          diagnostics = []
          for mapping in contract.get("tier1Mappings", []):
              row_id = mapping.get("id", "<unknown>")
              rust_symbol = mapping.get("rustSymbol")
              node_export = mapping.get("nodeExport")
              rust_crate = mapping.get("rustCrate", "<unknown>")

              # H1 fail-closed: empty row
              if rust_symbol is None and node_export is None:
                  diagnostics.append(
                      f"Row '{row_id}' is empty (no rustSymbol and no nodeExport)."
                  )
                  continue

              # H1 fail-closed: missing rustSymbol
              if rust_symbol is None:
                  diagnostics.append(
                      f"Row '{row_id}' missing rustSymbol."
                  )
                  continue

              is_proxy = isinstance(rust_symbol, str) and rust_symbol.endswith("@rust")

              # H1 fail-closed: normal-shape row with missing nodeExport
              # Only @rust proxy rows are allowed to omit nodeExport.
              if not is_proxy and node_export is None:
                  diagnostics.append(
                      f"Row '{row_id}' is normal-shape but missing nodeExport "
                      f"(only @rust proxy rows may omit nodeExport)."
                  )
                  continue

              effective_rust_symbol = rust_symbol[:-len("@rust")] if is_proxy else rust_symbol

              # Positive: Rust-side lookup
              if effective_rust_symbol and effective_rust_symbol not in rust_symbols:
                  diagnostics.append(
                      f"Row '{row_id}' rustSymbol '{effective_rust_symbol}' not in rust surface. "
                      f"Add 'pub use <sub_module>::{effective_rust_symbol};' to {rust_crate}/lib.rs."
                  )

              # Positive: Node-side lookup (skipped for @rust proxy rows)
              if not is_proxy and node_export and node_export not in node_exports:
                  diagnostics.append(
                      f"Row '{row_id}' nodeExport '{node_export}' not in node surface (index.d.ts). "
                      f"Either the Rust function still uses snake_case (NAPI auto-converts to camelCase), "
                      f"or '{node_export}' is a typo. Run `bun run build` to refresh index.d.ts and check "
                      f"whether the export was actually generated."
                  )
          return diagnostics
      ```
    - In `main()`, call the guard unconditionally between `parse_node_surface()` and `generate_diff_report()`:
      ```python
      # After rust_manifest and node_manifest are loaded:
      guard_diagnostics = validate_contract_surface(contract, rust_manifest, node_manifest)
      if guard_diagnostics:
          print("validate_contract_surface() found contract↔surface drift:", file=sys.stderr)
          for msg in guard_diagnostics:
              print(f"  - {msg}", file=sys.stderr)
          sys.exit(2)
      ```
    - Read the current `main()` to find the exact insertion point. Use Grep for `parse_node_surface` to locate.

    Step 3 — Re-run pytest. All 10 tests MUST pass (GREEN).

    Step 4 — Run the full gate against the live repo:
    ```powershell
    python tools/node_api_parity/check_parity_gate.py --repo-root .
    ```
    MUST exit 0 against the existing 261 tier1Mappings (none have `@rust` suffix, all `nodeExport` values match camelCase identifiers in `index.d.ts`, all `rustSymbol` values exist in the newly-expanded `rust_api_surface.json`). If any existing row now fires a diagnostic, that row was already broken and Plan 1 fixes it OR documents it in the commit message as an acceptable residual to be caught by Plans 2-5.

    Commit as: `Feat: add bidirectional validate_contract_surface guard with H1 fail-closed malformed-row rejection to Node parity gate (Phase 4 Plan 1 Task 2; NODE-01)` in one commit containing test + gate edits + baseline refresh if any.
  </action>
  <verify>
    <automated>python -m pytest tools/node_api_parity/tests/test_validate_contract_surface.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -m pytest tools/node_api_parity/tests/test_validate_contract_surface.py -q` exits 0 (all 10 tests pass including the 3 H1 fail-closed fixtures)
    - `python -c "import sys; sys.path.insert(0, 'tools/node_api_parity'); import check_parity_gate as g; assert callable(getattr(g, 'validate_contract_surface', None))"` exits 0
    - `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0 (live gate against expanded surface still passes)
    - **H1 fail-closed automation (MEDIUM concern fix — replaces manual 'inject bad row' step)**: the 3 H1 test cases (`test_h1_empty_row_is_rejected`, `test_h1_missing_rust_symbol_is_rejected`, `test_h1_normal_row_missing_node_export_is_rejected`) are part of the pytest run above — no manual injection step needed.
  </acceptance_criteria>
  <done>
    Bidirectional guard exists with H1 fail-closed rejection of 3 malformed row shapes, is called unconditionally, has 10 passing unit tests including automated malformed-row fixtures, live gate still exits 0. Plan 2-5 promotions will now be blocked at commit time if any row fails bidirectional validation OR any row has a malformed shape.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: bun run build env smoke test + A10 sizing report (dual-source per U2) + xfail baseline floor test + Plan 6 snapshot test</name>
  <read_first>
    - `ClassicLib-rs/node-bindings/classic-node/package.json` (confirm `build`, `parity:gate:local`, `dts:freshness:check`, `test:bun`, `test:node` scripts)
    - `ClassicLib-rs/node-bindings/classic-node/index.d.ts` (first 50 lines — confirm it exists and is committed)
    - `tools/node_api_parity/check_dts_freshness.py` (understand freshness gate mechanics — `bun run build:debug` + `git diff -- index.d.ts`)
    - `tools/binding_parity_runtime_coverage.py` lines 221-371 (`build_coverage_summary` and its deferred_total emission path — needed for sizing report cross-validation)
    - `.planning/phases/03-python-tier-collapse/03-01-A10-sizing.json` (format precedent)
    - `.planning/phases/04-node-tier-collapse/04-CONTEXT.md` §Research Amendments A2, A4 (GLOBAL_FCX_HANDLER excluded; deferred_total is the sole NODE-06 metric)
    - `.planning/phases/04-node-tier-collapse/04-REVIEWS.md` §"U2 — Plan 01 A10 sizing source fix" (load-bearing: primary source is `parity_diff_report.json::gaps`, NOT `runtime_coverage_summary.json` alone)
    - `docs/implementation/node_api_parity/baseline/parity_diff_report.json` (**PRIMARY SOURCE per U2** — read `gaps[]` for per-owner deferred row counts)
    - `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json` (cross-validation source only — do NOT use as primary count)
    - `docs/implementation/node_api_parity/baseline/parity_contract.json` (for `test_tier1_contract_total_baseline_floor` snapshot value)
  </read_first>
  <behavior>
    - `bun run build` exits 0 from `ClassicLib-rs/node-bindings/classic-node/` directory; `index.d.ts` mtime is updated; `bun run dts:freshness:check` exits 0 immediately after.
    - **U2 fix**: `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json` is sourced from BOTH `parity_diff_report.json::gaps` (PRIMARY) AND `runtime_coverage_summary.json::per_owner` (cross-validation). Per-owner deferred row counts are derived from `parity_diff_report.json::gaps[]` filtered by `ownerModule`, NOT from coverage delta math. The cross-validation step explicitly compares the two sources and flags any discrepancy.
    - `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.md` exists with a human-readable markdown table mirroring the JSON plus a per-owner surplus/deficit column showing how the actual count compares to Plan-skeleton estimates (scanlog=66, config=23-26, version_registry=4, aux=7-12 + HARM=3).
    - `tools/node_api_parity/tests/test_check_parity_gate.py` exists with two tests:
      1. `test_tier1_contract_total_baseline_floor` — asserts `len(parity_contract["tier1Mappings"]) >= 261` (Plan 1 snapshot; Plans 2-5 increase this)
      2. `test_tier2_definition_removed_after_plan_6` — marked `@pytest.mark.xfail(strict=True, reason="Plan 6 atomic cascade deletes tierDefinitions.tier2")`, asserts `"tier2" not in parity_contract.get("tierDefinitions", {})`. Flips to passing in Plan 6.
  </behavior>
  <action>
    Step 1 — Run `bun run build` end-to-end smoke test. From `ClassicLib-rs/node-bindings/classic-node/` directory, run (prefer PowerShell per user rule). If invoking from Git Bash, source `tools/use_msvc_from_git_bash.sh` first to prevent Git's `link.exe` from shadowing the MSVC linker (CLAUDE.md Key Gotcha):
    ```powershell
    # PowerShell entry point (preferred per user rule):
    cd J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node
    bun install                    # refresh node_modules (idempotent)
    bun run build                  # napi build --release --platform + tsc
    bun run dts:freshness:check    # verify index.d.ts unchanged after fresh build
    ```
    Git Bash equivalent (only if PowerShell is unavailable):
    ```bash
    cd J:/CLASSIC-Fallout4
    source tools/use_msvc_from_git_bash.sh   # MUST be sourced before bun run build
    cd ClassicLib-rs/node-bindings/classic-node
    bun install && bun run build && bun run dts:freshness:check
    ```
    If any step fails, this is a Plan 1 blocker — diagnose and fix (common causes: MSVC linker shadowing from Git Bash → source `tools/use_msvc_from_git_bash.sh`; missing `VCPKG_ROOT` → set it; stale `classic-node.win32-x64-msvc.node` → delete and rebuild). Document the root cause in the commit message.

    Step 2 — Generate the A10 sizing report (**U2 dual-source fix**):

    **Primary source (U2 load-bearing)**: Read `docs/implementation/node_api_parity/baseline/parity_diff_report.json` and compute per-owner deferred row counts directly from the `gaps[]` array:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python -c "
    import json
    from collections import Counter
    diff = json.load(open('docs/implementation/node_api_parity/baseline/parity_diff_report.json'))
    gaps = diff.get('gaps', [])
    # Exclude GLOBAL_FCX_HANDLER per A2
    filtered = [g for g in gaps if 'GLOBAL_FCX_HANDLER' not in g.get('rustSymbols', [])]
    per_owner_primary = Counter(g.get('ownerModule', 'unknown') for g in filtered)
    print('PRIMARY (parity_diff_report.json::gaps):', dict(per_owner_primary))
    print('TOTAL (primary):', sum(per_owner_primary.values()))
    "
    ```

    **Cross-validation source**: Read `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json::per_owner`:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python -c "
    import json
    summary = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json'))
    per_owner_cross = {k: v.get('deferred', 0) for k, v in summary.get('per_owner', {}).items()}
    total = summary.get('summary', {}).get('deferred_total', summary.get('deferred_total'))
    print('CROSS (runtime_coverage_summary.json::per_owner):', per_owner_cross)
    print('TOTAL (cross):', total)
    "
    ```

    **Explicit reconciliation**: Compare the two sources per-owner. If they disagree, document the delta AND use the PRIMARY source (parity_diff_report.json::gaps) as the authoritative count in `04-01-A10-sizing.json`. The summary is for sanity-check only.

    Then write `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json` with schema:
    ```json
    {
      "generated_at": "<ISO timestamp>",
      "primary_source": "docs/implementation/node_api_parity/baseline/parity_diff_report.json::gaps",
      "cross_validation_source": "docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json::per_owner",
      "total_deferred_primary": <N from gaps[] count>,
      "total_deferred_cross": <N from summary.deferred_total>,
      "reconciliation_delta": <primary - cross>,
      "note": "Primary source is parity_diff_report.json::gaps (U2 fix). Per-owner counts derive from the gap inventory, not from coverage delta math. scanlog count is 66 not 67 per A2 (GLOBAL_FCX_HANDLER excluded per Phase 3 R9 precedent).",
      "owners": [
        {"owner": "scanlog", "deferred_primary": <N>, "deferred_cross": <N>, "tier1_current": <N>, "plan": "04-02"},
        {"owner": "config", "deferred_primary": <N>, "deferred_cross": <N>, "tier1_current": <N>, "plan": "04-03"},
        {"owner": "version_registry", "deferred_primary": 4, "deferred_cross": 4, "tier1_current": <N>, "plan": "04-04", "plus_harm_rows": 3},
        {"owner": "aux", "deferred_primary": <N>, "deferred_cross": <N>, "tier1_current": <N>, "plan": "04-05"}
      ],
      "residual_candidates": "<list of owners where primary count > 0 and not scheduled in Plans 2-4 — Plan 5 absorbs these>"
    }
    ```
    Write `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.md` as a human-readable table mirroring the JSON + a "Task Budget Summary" bullet list listing each plan's expected task count range + an explicit "Primary vs Cross Reconciliation" section documenting any per-owner delta.

    Step 2.5 — `__test__/*.spec.ts` enumeration (Issue 10 fix). Enumerate every spec file under `ClassicLib-rs/node-bindings/classic-node/__test__/` and record the discovered list in `04-01-A10-sizing.md` so Plan 5's per-owner test-append targets are pre-validated:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python -c "from pathlib import Path; root = Path('ClassicLib-rs/node-bindings/classic-node/__test__'); files = sorted(p.name for p in root.glob('*.spec.ts')); print(f'count: {len(files)}'); [print(f'  - {f}') for f in files]"
    ```
    Expected: 20 existing spec files (verified 2026-04-08): `cli`, `config`, `constants`, `database`, `fileio`, `message`, `parity_tier1`, `path`, `regression_drift`, `resource`, `scangame`, `scanlog`, `settings`, `shared`, `update`, `version`, `version_registry`, `web`, `xse`, `yaml`. Note: `crashgen_rules.spec.ts` does NOT exist today — Plan 5 Task 1 creates it (this is intentional; record as `MISSING — Plan 5 creates`). For each crate in `RUST_TARGET_CRATES`, map to its expected spec file via the owner module label and verify in the sizing report whether the spec file exists or is `MISSING`. Append a "Spec File Inventory" table to `04-01-A10-sizing.md`.

    Step 2.6 — 101-vs-109 deferred-count reconciliation (Issue 12 + U2 fix). The backlog `entries[]` count is NOT the primary source per U2. The primary source is `parity_diff_report.json::gaps[]`. Document the 3-way delta (backlog, diff gaps, coverage summary) in `04-01-A10-sizing.md`:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python -c "
    import json
    backlog = json.load(open('docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json'))
    diff = json.load(open('docs/implementation/node_api_parity/baseline/parity_diff_report.json'))
    summary = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json'))
    print(f'backlog.entries count: {len(backlog[\"entries\"])}')
    print(f'parity_diff_report.gaps count: {len(diff.get(\"gaps\", []))}')
    deferred = summary.get('summary', {}).get('deferred_total', summary.get('deferred_total'))
    print(f'runtime_coverage_summary.deferred_total: {deferred}')
    "
    ```
    Pin the numerator to the PRIMARY source (`parity_diff_report.json::gaps` count). Document every delta in `04-01-A10-sizing.md`. Per A4, NODE-06's pass criterion is `deferred_total == 0` from `runtime_coverage_summary.json` — the SUMMARY is the LANDING criterion, but the PRIMARY SOURCE for Plan 5 task budgeting is the live diff gap inventory.

    Step 3 — Create `tools/node_api_parity/tests/test_check_parity_gate.py`:
    ```python
    import json
    from pathlib import Path
    import pytest

    REPO_ROOT = Path(__file__).resolve().parents[3]
    PARITY_CONTRACT = REPO_ROOT / "docs/implementation/node_api_parity/baseline/parity_contract.json"

    def test_tier1_contract_total_baseline_floor():
        """Plan 1 snapshot: tier1Mappings must not regress below 261 (Plans 2-5 raise this)."""
        contract = json.loads(PARITY_CONTRACT.read_text(encoding="utf-8"))
        tier1 = contract.get("tier1Mappings", [])
        # Update this assertion in Plan 6 to reflect the final post-promotion floor
        assert len(tier1) >= 261, f"tier1Mappings regressed: {len(tier1)} < 261"

    @pytest.mark.xfail(strict=True, reason="Plan 6 atomic cascade deletes tierDefinitions.tier2 — test flips to passing then")
    def test_tier2_definition_removed_after_plan_6():
        contract = json.loads(PARITY_CONTRACT.read_text(encoding="utf-8"))
        tier_defs = contract.get("tierDefinitions", {})
        assert "tier2" not in tier_defs, "tierDefinitions.tier2 still present (Plan 6 will remove it)"
    ```
    Run the tests — `test_tier1_contract_total_baseline_floor` MUST pass (261 is the current count); `test_tier2_definition_removed_after_plan_6` MUST fail with xfail marker (the tier2 key is still present). This is the expected state at Plan 1 close.

    Step 4 — Commit:
    - Commit bun run build smoke results as the commit message footnote (no code change unless Task 1's baseline refresh affected index.d.ts, which it shouldn't since no Rust source edit was made).
    - Stage: A10 sizing json+md, test_check_parity_gate.py.
    - Commit as: `Feat: add Node Plan 1 A10 sizing report (dual-source per U2) + xfail baseline floor tests (Phase 4 Plan 1 Task 3; NODE-01)`.
  </action>
  <verify>
    <automated>python -m pytest tools/node_api_parity/tests/test_check_parity_gate.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run build && bun run dts:freshness:check` both exit 0 (run once to verify, do not commit `index.d.ts` change if none)
    - `Test-Path .planning/phases/04-node-tier-collapse/04-01-A10-sizing.json` returns `True` (PowerShell-native per user rule)
    - `Test-Path .planning/phases/04-node-tier-collapse/04-01-A10-sizing.md` returns `True`
    - **U2 primary-source enforcement**: `python -c "import json; d = json.load(open('.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json')); assert d.get('primary_source') == 'docs/implementation/node_api_parity/baseline/parity_diff_report.json::gaps', 'Sizing report must declare primary_source as parity_diff_report.json::gaps per U2'"` exits 0
    - `python -c "import json; d = json.load(open('.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json')); assert 'total_deferred_primary' in d and 'total_deferred_cross' in d and 'reconciliation_delta' in d, 'U2 dual-source schema missing'"` exits 0
    - `python -c "import json; d = json.load(open('.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json')); scanlog = next(o for o in d['owners'] if o['owner'] == 'scanlog'); assert scanlog['deferred_primary'] in (66, 67), f'scanlog primary count unexpected: {scanlog[\"deferred_primary\"]}'"` exits 0 (A2 enforcement; allow 66 or 67 depending on how GLOBAL_FCX_HANDLER filtering lands)
    - `python -m pytest tools/node_api_parity/tests/test_check_parity_gate.py -q` exits 0 (floor test passes, xfail test xfails as expected)
    - `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0
  </acceptance_criteria>
  <done>
    bun run build smoke verified, A10 sizing report published with dual-source primary/cross schema per U2, pytest scaffold for Plans 2-6 exists, gate still green.
  </done>
</task>

</tasks>

<verification>
Plan-level sanity check:
1. `python -m pytest tools/node_api_parity/tests/ -q` — all 4 test files pass (test_generate_baseline_targets, test_validate_contract_surface including the 3 H1 fixtures, test_check_parity_gate — with expected xfail on tier2 test)
2. `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0
3. `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local` exits 0
4. A10 sizing JSON and MD both exist under `.planning/phases/04-node-tier-collapse/` with dual-source schema per U2
5. `git log --oneline -3` shows exactly 3 commits for the 3 tasks (or fewer if any task's edits were empty)
</verification>

<success_criteria>
- NODE-01 fully satisfied: `RUST_TARGET_CRATES` covers every business-logic crate with a Node binding (>= 19 entries); `RUST_FULL_INVENTORY_CRATES` deleted
- Plans 2-5 have the bidirectional guard available to validate every row they author, AND the guard fails-closed on malformed shapes (H1)
- Plans 2-5 have the A10 sizing report available to budget tasks — dual-source per U2 (primary: parity_diff_report.json::gaps)
- No regression in the 261 existing tier1Mappings (gate still exits 0)
- Wave 0 test scaffold in place for Plans 2-6 (floor + xfail tests + 3 H1 fail-closed fixtures)
- Owner selection fails loud on unresolved crates (no silent default-to-aux fallback)
</success_criteria>

<output>
After completion, create `.planning/phases/04-node-tier-collapse/04-01-tooling-expansion-SUMMARY.md` per the standard summary template. The SUMMARY MUST record:
- Whether `bun run build` succeeded on first attempt or required env fixes (and what those fixes were)
- The final `RUST_TARGET_CRATES` count and its delta vs prior (19 vs 10)
- The A10 sizing report's per-owner breakdown (table) showing BOTH primary (gaps) AND cross (coverage summary) counts, plus the reconciliation delta per U2
- Any existing 261 rows that fired the new bidirectional guard and how they were handled
- Confirmation that the xfail test is still xfailing (Plan 6 flips it)
- Confirmation that the 3 H1 fail-closed tests pass automatically (no manual row injection required)
</output>
