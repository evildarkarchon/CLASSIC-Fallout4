# Plan 09b — Tier-2 Cascade Audit (M8 recursive search)

**Generated:** 2026-04-08T21:58:40Z (Task 1)
**Plan:** 03-python-tier-collapse / 09b-tier2-cleanup-and-final-sweep
**Purpose:** Enumerate every reader of `tier2_gap_total` / `python_unmapped` / `rust_unmapped` / `tierDefinitions.*tier2` / `"tier2"` across the whole repo BEFORE Task 2 deletes them, so no consumer is silently broken (M8 fix from REVIEWS Round 2).

## Search command (M8 fix — recursive, NOT selective glob)

```powershell
$rgPattern = 'tier2_gap_total|python_unmapped|rust_unmapped|tierDefinitions.*tier2|"tier2"'
$scopeDirs = @(
    'tools',
    'ClassicLib-rs/python-bindings',
    'ClassicLib-rs/foundation',
    'docs/api',
    'docs/implementation/python_api_parity',
    'docs/implementation/node_api_parity',
    '.github'
)
foreach ($d in $scopeDirs) {
    Get-ChildItem -Path $d -Recurse -File -Include *.py,*.md,*.json,*.yml,*.yaml,*.ps1 -ErrorAction SilentlyContinue |
        Select-String -Pattern $rgPattern -ErrorAction SilentlyContinue
}
# Also repo-root *.ps1
Get-ChildItem -Path . -Filter *.ps1 -File | Select-String -Pattern $rgPattern
```

## Total hits: **6768** across **28 files**

Per-file breakdown (from the live search):

| File | Hits |
|---|---:|
| `ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.json` | 9 |
| `ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json` | 1013 |
| `ClassicLib-rs/python-bindings/parity-artifacts/rust_api_surface.json` | 3 |
| `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` | 1 |
| `ClassicLib-rs/python-bindings/tests/test_binding_coverage_tooling.py` | 2 |
| `ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py` | 1 |
| `docs/implementation/node_api_parity/baseline/handoff_map.md` | 63 |
| `docs/implementation/node_api_parity/baseline/node_api_surface.json` | 44 |
| `docs/implementation/node_api_parity/baseline/parity_contract.json` | 1 |
| `docs/implementation/node_api_parity/baseline/parity_diff_report.json` | 203 |
| `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json` | 205 |
| `docs/implementation/node_api_parity/baseline/rust_api_surface.json` | 63 |
| `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` | 101 |
| `docs/implementation/node_api_parity/governance/per_wave_acceptance_template.md` | 1 |
| `docs/implementation/node_api_parity/governance/tier2_wave_manifest.json` | 392 |
| `docs/implementation/python_api_parity/baseline/parity_contract.json` | 1 |
| `docs/implementation/python_api_parity/baseline/parity_diff_report.json` | 9 |
| `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json` | 1013 |
| `docs/implementation/python_api_parity/baseline/rust_api_surface.json` | 3 |
| `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json` | 1202 |
| `docs/implementation/python_api_parity/governance/tier2_wave_manifest.json` | 2404 |
| `tools/cxx_api_parity/tests/test_gate.py` | 1 |
| `tools/node_api_parity/generate_baseline.py` | 10 |
| `tools/node_api_parity/generate_deferred_backlog.py` | 4 |
| `tools/python_api_parity/generate_baseline.py` | 12 |
| `tools/python_api_parity/generate_wave_manifest.py` | 4 |
| `tools/python_api_parity/tests/test_check_parity_gate.py` | 2 |
| (self) `_tmp_cascade_audit.ps1` | 1 |

## Hits by file (classified with remediation status)

### `tools/python_api_parity/generate_baseline.py` — 12 hits

- **L277**: `"tier": "tier1" if symbol in tier1_rust_symbols else "tier2",` — **CODE_CLASSIFICATION (parse_rust_surface)**
  - Remediation: **LOAD-BEARING INTERNAL — DO NOT TOUCH**. This is the parser tier attribution that labels each rust symbol on `rust_api_surface.json`. It becomes effectively vestigial once the gap branches are gone (the "tier2" label no longer drives any gap emission), but the expression itself is harmless and removing it is a Phase 6 sweep concern.
- **L294**: same pattern in different parse helper — **LOAD-BEARING INTERNAL**.
- **L312**: same — **LOAD-BEARING INTERNAL**.
- **L330**: same — **LOAD-BEARING INTERNAL**.
- **L419**: `else "tier2",` — tier labeling fallback in a parse helper — **LOAD-BEARING INTERNAL**.
- **L473**: same — **LOAD-BEARING INTERNAL**.
- **L506**: same — **LOAD-BEARING INTERNAL**.
- **L678**: `"gap_type": "rust_unmapped",` — **CODE_WRITE (emission)**.
  - Remediation: Task 2 Step 2 deletes the entire L672-689 `for rust_item in rust_symbols:` block.
- **L679**: `"tier": "tier2",` inside the rust_unmapped gap emission — **CODE_WRITE** (part of same block).
  - Remediation: deleted with Block 1.
- **L697**: `"gap_type": "python_unmapped",` — **CODE_WRITE (emission)**.
  - Remediation: Task 2 Step 3 deletes the entire L691-708 `for py_item in python_exports:` block.
- **L698**: `"tier": "tier2",` inside the python_unmapped gap emission — **CODE_WRITE** (part of same block).
  - Remediation: deleted with Block 2.
- **L728**: `"tier2_gap_total": sum(1 for gap in gaps if gap["tier"] == "tier2"),` — **CODE_WRITE (emission)**.
  - Remediation: Task 2 Step 4 deletes the line.
- **L776**: `"| Owner Module | Tier 1 Gaps | Tier 2 Gaps |"` — **CODE_WRITE (markdown header)**.
  - Remediation: Task 2 Step 5 drops the column header.
- **L783**: `f"| \`{owner}\` | {tier_counts.get('tier1', 0)} | {tier_counts.get('tier2', 0)} |"` — **CODE_WRITE (markdown cell)**.
  - Remediation: Task 2 Step 5 drops the trailing cell.

Note: L276 (`| Owner Module | Tier 1 Gaps | Tier 2 Gaps |`) and L777 (`|---|---:|---:|`) also need to be updated as part of Task 2 Step 5 dropping the column.

### `tools/python_api_parity/tests/test_check_parity_gate.py` — 2 hits

- **L55**: `assert "tier2" not in tier_definitions,` — **TEST_ASSERTION (positive gate)**
  - Remediation: Task 2 Step 7 will REMOVE the `@pytest.mark.xfail(...)` decorator at L44-51 (the decorator block is WHERE the only `tier2` references are in this file — the assertion itself remains load-bearing and passes after tier2 is deleted from the contract).
- **L56**: `"Plan 9b must delete tierDefinitions.tier2 from parity_contract.json"` — **TEST_ASSERTION (error message)**
  - Remediation: No edit. The message is forward-compatible ("must delete"); the test passes once tier2 is gone.

### `ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py` — 1 hit

- **L170**: `assert report["gaps"][1]["gap_type"] == "python_unmapped"` — **TEST_ASSERTION (C4 fix target)**
  - Remediation: Task 2 Step 8 replaces L170 with `assert len(report["gaps"]) == 1` IN THE SAME COMMIT as the generate_baseline.py branch deletion (M7 atomicity).

### `tools/python_api_parity/generate_wave_manifest.py` — 4 hits

- **L138**: `and entry.get("tier") == "tier2"` — **OUT_OF_SCOPE_PHASE_6 (CODE)**
- **L145**: `and entry.get("tier") == "tier2"` — **OUT_OF_SCOPE_PHASE_6 (CODE)**
- **L154**: `[row for row in diff_report.get("gaps", []) if row.get("tier") == "tier2"],` — **OUT_OF_SCOPE_PHASE_6 (CODE)**
- **L175**: `"tier": "tier2",` — **OUT_OF_SCOPE_PHASE_6 (CODE)**
  - Remediation: `generate_wave_manifest.py` produces `docs/implementation/python_api_parity/governance/tier2_wave_manifest.json`. Phase 6 DOC-02/DOC-04 owns deleting the governance directory, which includes deleting this generator and its output. Plan 09b does NOT touch this file.
  - Note: after Plan 09b empties `deferred_runtime_backlog.json::entries`, running this manifest generator would produce an empty output; it remains functional but vestigial.

### `tools/node_api_parity/generate_baseline.py` — 10 hits

- All hits — **OUT_OF_SCOPE_PHASE_4**
  - Remediation: Phase 4 (Node Tier Collapse) owns the identical cleanup on the Node side. Plan 09b does NOT touch this file.

### `tools/node_api_parity/generate_deferred_backlog.py` — 4 hits

- All hits — **OUT_OF_SCOPE_PHASE_4**
  - Remediation: Phase 4 ownership.

### `docs/implementation/python_api_parity/baseline/parity_contract.json` — 1 hit

- **tierDefinitions.tier2 key** — **CONFIG_JSON**
  - Remediation: Task 2 Step 6 deletes via `json.load` / `del` / `json.dump` (in the same atomic commit as the generate_baseline.py edits).

### `docs/implementation/python_api_parity/baseline/parity_diff_report.json` — 9 hits

- 9 hits combining `"tier": "tier2"`, `"tier2_gap_total": N`, `gap_type: rust_unmapped|python_unmapped`, and gap count references — **BASELINE_JSON (auto-generated)**
  - Remediation: Task 2 Step 11 baseline refresh drops all these mechanically once the emission code is deleted.

### `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json` — 1013 hits

- All hits are `"tier": "tier2"` inside `trackedSurface` rows where the deferred backlog entries were injected by `build_coverage_summary`'s `registry_only` fallback — **BASELINE_JSON (auto-generated)**
  - Remediation: Task 3 empties the deferred backlog (C3 endgame), Task 3 Step 2 refreshes the baseline, and the 1013 hits drop to 0 (well, whatever rows remain come from the one preserved `python-tier2-config-runtime` registry fixture row).
  - Note: after the empty-backlog refresh, the count goes from 1013 down to ~2 (the `classic_version` + `warn_outdated` @property field rows that remain in the test fixture registry).

### `docs/implementation/python_api_parity/baseline/rust_api_surface.json` — 3 hits

- `"tier": "tier2"` attribution on 3 specific rust symbols — **BASELINE_JSON (auto-generated)**
  - Remediation: generated by `parse_rust_surface` L277/L294/etc. Since those LOAD-BEARING INTERNAL tier labels are preserved, these 3 hits ALSO persist after Task 2. They do not affect gate behavior — they're dead metadata until Phase 6 sweeps them.

### `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json` — 1202 hits

- **1202 backlog entries, each with `classification="deferred"` and `tier="tier2"`** — **GOVERNANCE_JSON (C3 TARGET)**
  - Remediation: Task 3 empties `entries` to `[]`. Top-level `schemaVersion` / `binding` keys preserved. Phase 6 DOC-02/DOC-04 owns deleting the file later.

### `docs/implementation/python_api_parity/governance/tier2_wave_manifest.json` — 2404 hits

- Every wave entry has tier2 metadata — **OUT_OF_SCOPE_PHASE_6**
  - Remediation: Phase 6 DOC-02/DOC-04 owns deleting the entire `governance/` directory. Plan 09b does NOT touch this file.

### `ClassicLib-rs/python-bindings/parity-artifacts/**` — 1025 hits across 3 files

- `parity_diff_report.json` (9 hits), `runtime_coverage_summary.json` (1013 hits), `rust_api_surface.json` (3 hits) — **BASELINE_MIRROR (auto-generated)**
  - Remediation: mirror of `docs/implementation/python_api_parity/baseline/`; same remediation as baseline — auto-refreshed by Task 2 + Task 3 baseline refreshes.

### `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` — 1 hit

- **L265**: `"tier": "tier2",` inside the `python-tier2-config-runtime` test fixture entry — **TEST_FIXTURE (preserved per Plan 06 decision)**
  - Classification: **KEEP AS-IS** (NOT in Plan 09b `files_modified` list). Per STATE.md Plan 06 decision: "preserved python-tier2-config-runtime (not deleted as plan instructed) because its 2 bindings are @property methods the Python surface parser skips". The registry entry covers `classic_config.YamlData.classic_version` and `classic_config.YamlData.warn_outdated` with `classification="runtime_verified"` (not "deferred"), so it does NOT contribute to `deferred_total`.
  - Semantic note: after Task 2 deletes `tierDefinitions.tier2`, the `tier: "tier2"` label on this row becomes cosmetically stale. `build_coverage_summary` at L204 only propagates the `tier` field into `trackedSurface` as descriptive metadata — no filtering logic reads it — so the label is harmless. A future Phase 6 sweep can either re-label it "tier1" or delete the row entirely.
  - **No edit required in Plan 09b.**

### `ClassicLib-rs/python-bindings/tests/test_binding_coverage_tooling.py` — 2 hits

- **L62**: `"tier": "tier2",` inside a synthetic test fixture (`gap_type: "node_unmapped"`) — **TEST_FIXTURE**
- **L69**: same — **TEST_FIXTURE**
  - Classification: **KEEP AS-IS**. These are fabricated test inputs to `build_coverage_summary`, NOT production data. The test exercises the consumer's handling of a synthetic Node diff report, so the `node_unmapped` / `tier2` values are test-local. They neither import from nor are exported to `generate_baseline.py`.
  - **No edit required in Plan 09b.**

### `tools/cxx_api_parity/tests/test_gate.py` — 1 hit

- **L78**: `assert not any(k.startswith("tier2") for k in data)` — **TEST_ASSERTION (positive gate)**
  - Classification: **LOAD-BEARING**. Phase 1 Plan D-04 decided the CXX parity gate would never have a Tier-2 concept; this assertion enforces that invariant. It remains green and stays untouched.
  - **No edit required.**

### `docs/implementation/node_api_parity/**` — 1073 hits across 8 files

- Every hit — **OUT_OF_SCOPE_PHASE_4**
  - Remediation: Phase 4 (Node Tier Collapse) owns Node-side cleanup entirely.

### `.github/workflows/**` — 0 hits

Confirmed clean. No CI workflow references `tier2_gap_total` directly.

### `*.ps1` build scripts at repo root — 0 hits (excluding the audit helper itself)

Confirmed clean. No build script references `tier2_gap_total`.

### `docs/api/**` — 0 hits

Confirmed clean. API docs do not reference the removed surface.

## Load-bearing exclusions (DO NOT TOUCH)

The following matches are DIFFERENT identifiers and must NOT be altered or swept:

- `tier1_missing_rust`, `tier1_missing_python`, `tier1_signature_mismatch` — load-bearing gate metric names in `summary` dict
- `tier1_gap_total` — still present in the summary dict after Task 2
- `tier1_contract_total` — load-bearing metric
- `"tier1"` string literal — used in `parse_rust_surface` tier attribution (generate_baseline.py L277/L294/L312/L330)
- `"tier2"` string literal INSIDE `parse_rust_surface` (L277, L294, L312, L330, L419, L473, L506) — these are the tier attribution ternary expressions; they become effectively dead after Task 2 deletes the gap branches, but the expressions themselves are harmless and do not need explicit removal per the plan's explicit instruction: "Sweep only what Task 2 leaves as dead COMMENTS, not as dead code expressions."
- `runtime_coverage_registry.json` L265 `python-tier2-config-runtime` — **preserved test fixture** (Plan 06 decision)
- `test_binding_coverage_tooling.py` L62/L69 — synthetic Node-side test fixtures, unrelated to Python deletion
- `test_gate.py` L78 (cxx_api_parity) — positive assertion that tier2 is GONE from CXX — already load-bearing green
- All node-side `tools/node_api_parity/` and `docs/implementation/node_api_parity/` hits — Phase 4 ownership
- All `governance/tier2_wave_manifest.json` + `tier2_backlog_and_governance.md` references — Phase 6 ownership

## Classification summary

| Category | File count | Hit count |
|---|---:|---:|
| CODE_WRITE (Task 2 deletion targets) | 1 | 5 targeted lines in generate_baseline.py |
| CODE_CLASSIFICATION (load-bearing internal parser labels) | 1 | 7 |
| TEST_ASSERTION (C4 fix + xfail flip) | 2 | 3 |
| TEST_FIXTURE (keep as-is) | 2 | 3 |
| POSITIVE_ASSERTION (load-bearing green — do not touch) | 1 | 1 |
| CONFIG_JSON (Task 2 Step 6 target) | 1 | 1 |
| GOVERNANCE_JSON (Task 3 C3 target) | 1 | 1202 |
| BASELINE_JSON (auto-regenerated by Task 2/Task 3 refresh) | 8 | ~3056 |
| OUT_OF_SCOPE_PHASE_4 (Node side) | 9 | ~1083 |
| OUT_OF_SCOPE_PHASE_6 (governance + wave manifest generator) | 2 | 2408 |
| **Total in-scope for Plan 09b remediation** | **6** | **6 code + 1 json config + 1 governance empty** |

## Remediation plan (routed to tasks)

| File | Remediation | Task | Commit atomicity |
|---|---|:-:|---|
| `tools/python_api_parity/generate_baseline.py` L672-708 | Delete Blocks 1+2 (rust_unmapped, python_unmapped loops) | 2 | SAME commit as Task 2 |
| `tools/python_api_parity/generate_baseline.py` L728 | Delete `tier2_gap_total` summary key | 2 | SAME commit as Task 2 |
| `tools/python_api_parity/generate_baseline.py` L776-783 | Drop Tier-2 markdown column | 2 | SAME commit as Task 2 |
| `docs/implementation/python_api_parity/baseline/parity_contract.json` | Delete `tierDefinitions.tier2` | 2 | SAME commit |
| `tools/python_api_parity/tests/test_check_parity_gate.py` L44-51 | Remove `@pytest.mark.xfail` decorator | 2 | SAME commit |
| `tools/python_api_parity/tests/test_check_parity_gate.py` (new function) | Add `test_tier2_gap_total_removed_from_summary` | 2 | SAME commit |
| `ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py` L170 (C4) | Replace `gaps[1]` assertion with `len(gaps) == 1` | 2 | SAME commit |
| `docs/implementation/python_api_parity/baseline/**` + `ClassicLib-rs/python-bindings/parity-artifacts/**` | Refresh baseline + mirror (auto-drops `tier2_gap_total`, `rust_unmapped`, `python_unmapped` gap rows, Tier-2 markdown column, auto-drops tierDefinitions.tier2 from the regenerated contract) | 2 | SAME commit (M7 atomicity) |
| `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json::entries` | Set to `[]` (C3 endgame) | 3 | Separate commit |
| `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.{json,md}` + mirror | Refresh after backlog empty (drops 1013 `tier: "tier2"` rows from trackedSurface) | 3 | Same commit as Task 3 |

## Summary

- **Total hits within Phase 3 scope:** 6 code sites (Task 2 targets) + 1 JSON config key (Task 2) + 1 governance file (Task 3) + 1 test assertion (C4) + 1 xfail decorator (Plan 01 flip).
- **Total hits classified OUT_OF_SCOPE_PHASE_4:** 1083 (all Node-side).
- **Total hits classified OUT_OF_SCOPE_PHASE_6:** 2408 (governance wave manifest + generate_wave_manifest.py).
- **Total load-bearing exclusions:** 12 (parse_rust_surface ternaries + 2 test fixtures + 1 positive test assertion + tier1_* metric names).
- **Auto-regenerated baseline hits:** ~3056 (drop mechanically after Task 2 + Task 3 refreshes).
- **Plan 09b deletion footprint:** 5 code lines (generate_baseline.py) + 1 contract key + 1 xfail decorator + 1 test assertion update + 1 backlog empty + baseline refreshes. Everything else is either auto-regenerated, out of scope, or load-bearing.

## Audit complete — Task 2 has full visibility of deletion targets, C4 fix target, and load-bearing exclusions. Task 3 has C3 endgame target confirmed (1202 backlog entries to empty).
