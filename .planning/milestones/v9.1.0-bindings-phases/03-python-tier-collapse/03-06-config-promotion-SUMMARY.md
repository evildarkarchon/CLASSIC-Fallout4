---
phase: 03-python-tier-collapse
plan: 06
subsystem: python-parity
tags: [python, parity-gate, pyo3, config, crashgen-settings, tier-collapse]

# Dependency graph
requires:
  - phase: 03-python-tier-collapse
    provides: Plan 05 completed the 4-wave scanlog promotion track (tier1Mappings=286); this plan opens the config crate promotion track
provides:
  - 28 new Tier-1 contract rows for classic-config-core promotion (15 rust-only @rust-suffixed + 11 python-only dunder/factory + 2 Tier-2 migrations)
  - parity_contract.json::tier1Mappings grows from 286 to 314 entries
  - python-tier1-config runtime selector contractCount bumped from 15 to 43 with recomputed contractIdsHash (90a8f039181858fd8aeb5af9e0ab2d9f1b1a2256fcfe31800a2bf6f5ed04eee0)
  - python-tier1-config-plan06-promoted aux runtime entry with 13 explicit bindingIdentifiers pointing at test_promoted_config_smoke.py
  - python-tier2-config-application-dir-runtime deleted (its 2 bindings migrated to tier1Mappings as real contract rows)
  - python-tier2-config-runtime PRESERVED (its 2 @property bindings cannot be tier1 rows — see decisions)
  - test_promoted_config_smoke.py with 13 per-class + fixture-backed tests (324 lines)
  - 03-06-CONSTRUCTOR-INVENTORY.md documenting verified classic-config-py surface
  - _build_config_rows.py helper for reproducibility
  - First non-scanlog promotion plan lands clean — proves the Wave 1/3a pattern generalizes to other owner modules
affects: [03-07, 03-08, 03-09a, 03-09b]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Plan 06 reuses the Wave 1 @rust-suffix pattern for rust-only symbols paired with the nearest Python class (YamlData for all yamldata.rs types; ClassicConfig for the `config` module marker; clear_yaml_cache for the `get_runtime` re-export)"
    - "Plan 06 first demonstrates the Wave 3a tier-2 preservation precedent in a different owner module — preserving python-tier2-config-runtime because its 2 property bindings cannot become tier1 rows"
    - "Dotted ID scheme continues: config.<submodule>.<symbol> (config.config.*, config.yamldata.*, config.shared.*) with @rust suffix for rust-only proxy rows"
    - "Minimal .pyi update: existing classic_config.pyi already declared all 28 promoted symbols from prior phase work; Task 2 was a verified no-op (like Wave 2) — no commit created"

key-files:
  created:
    - .planning/phases/03-python-tier-collapse/03-06-CONSTRUCTOR-INVENTORY.md
    - .planning/phases/03-python-tier-collapse/_build_config_rows.py
    - ClassicLib-rs/python-bindings/tests/test_promoted_config_smoke.py
  modified:
    - docs/implementation/python_api_parity/baseline/parity_contract.json
    - docs/implementation/python_api_parity/baseline/parity_diff_report.json
    - docs/implementation/python_api_parity/baseline/parity_diff_report.md
    - docs/implementation/python_api_parity/baseline/rust_api_surface.json
    - docs/implementation/python_api_parity/baseline/python_api_surface.json
    - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
    - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
    - ClassicLib-rs/python-bindings/parity-artifacts/* (regenerated via check_parity_gate.py --update-baseline)
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json

key-decisions:
  - "ID scheme: Plan 06 promoted rows use dotted config.<sub_module>.<symbol> (config.config.*, config.yamldata.*, config.shared.*) to match the existing Wave 1/3a precedent; legacy kebab-case IDs (config-classic-config-class etc.) preserved for the original 15 config rows"
  - "PyClass inventory correction: The plan's <interfaces> block assumed CrashgenEntryRaw/CoreModEntry/CoreModExclude/ModConflictEntry/ModSolutionCriteria/ModSolutionEntry/SuspectErrorRule/SuspectStackRule/SuspectStackCountRule are all promoted #[pyclass] types. Reality: NONE have PyO3 wrappers in classic-config-py. They surface only as dict/list items inside PyYamlData getters (lib.rs:894-1014). All 10 types routed via @rust-suffixed proxy rows paired with YamlData — matches Wave 1/3a pattern"
  - "R15 canonical owner rule applied: crashgen_settings types (SuspectErrorRule, SuspectStackRule, ModConflictEntry, ModSolutionEntry/Criteria, CrashgenEntryRaw) have ONE contract row each in the config owner module. These types are NOT re-exported separately through scanlog or scangame bindings with distinct pythonExportPath, so no duplicate rows are needed"
  - "Deferred backlog count divergence from plan: plan claimed 22 deferred config entries but actual backlog has 26 (Plan 01 regeneration grew raw counts from 285 to 1202). The plan's 22 was from Research Amendment A4's pre-regen value. Adopted ground truth: all 26 deferred entries promoted"
  - "Tier-2 preservation precedent (Wave 3a): python-tier2-config-runtime was NOT deleted despite the plan instructing deletion. Its 2 bindings (classic_config.YamlData.classic_version / warn_outdated) are Python-side @property methods; the Python surface parser skips @property decorators per generate_baseline.py::_is_property_decorator line 378. Authoring tier1 contract rows for these identifiers would fail the gate with tier1_missing_python > 0. Wave 3a's python-tier2-scanlog-runtime preservation is the direct precedent"
  - "Only 2 of 4 plan-promised Tier-2 migrations were genuine: get_application_dir + set_application_dir are top-level #[pyfunction]s visible in python_api_surface.json and promoted cleanly. The other 2 (classic_version, warn_outdated) remain as runtime-verified Tier-2 entries"
  - "Test discipline: Task 3 marked tdd='true' but all PyO3 wrappers already exist in the built wheel — tests were authored directly (not via RED/GREEN/REFACTOR) since there is no production code to write. Committed as Test: prefix per Wave 1/3a precedent. 13/13 tests passed on first run (zero fix iterations)"
  - "Math reconciliation: 26 deferred + 2 tier-2 migrations = 28 new tier1 rows → tier1Mappings = 286 + 28 = 314. Plan scaffold expected 312 (286 + 26); final count is 2 higher because the plan's denominator was wrong"
  - "Task 2 .pyi update was a verified no-op: the existing classic_config.pyi already contains every Python identifier referenced by the 28 new rows (verified via automated cross-check against python_api_surface.json — 0 missing). mypy --strict passes. No commit created per no-empty-commits protocol (Wave 1/2/3b precedent)"

patterns-established:
  - "Pattern: The Wave 1 @rust-suffix proxy pattern generalizes cleanly from scanlog to config. Any owner module where rust types lack Python wrappers (because bindings convert them to dicts/lists) can route those rust symbols via @rust-suffixed contract rows paired with the nearest Python class"
  - "Pattern: Tier-2 preservation criteria are structural, not discretionary. If a tier-2 bindingIdentifier references something the Python surface parser cannot see (@property methods, pure-runtime-introspected attributes), the tier-2 entry MUST be preserved even when the plan instructs deletion. This is the Wave 3a refusal pattern restated at the contract-row authoring step"
  - "Pattern: Fixture-backed smoke tests cover rust-only types indirectly. When rust types have no Python constructor (surface only through dict-bearing getters), smoke tests deserialize a known-valid YAML fixture via YamlData.from_yaml_content and exercise the getters — every getter call in the PyO3 wrapper exercises the corresponding rust type's conversion code path"

requirements-completed: [PYT-02, PYT-04, PYT-05]

# Metrics
duration: 8min
completed: 2026-04-08
---

# Phase 3 Plan 06: classic-config-core Promotion Summary

**Promoted 28 config parity entries (26 deferred + 2 Tier-2 migrations) to enforced Tier-1; tier1Mappings grew 286 -> 314; the Wave 1 @rust-suffix pattern successfully generalized from scanlog to config for rust types that have no PyO3 wrappers; Wave 3a tier-2 preservation precedent reapplied for the 2 @property-based Tier-2 bindings; 13-test fixture-backed smoke suite passed on first run; full 5-step verification chain green.**

## Performance

- **Duration:** 8 minutes (7m 40s)
- **Started:** 2026-04-08T23:48:14Z
- **Completed:** 2026-04-08T23:55:54Z
- **Tasks:** 4 (Task 0 inventory + Tasks 1-4 implementation; Task 2 verified no-op)
- **Files modified:** 17 (3 created + 14 modified, including regenerated baseline + parity-artifacts)

## Accomplishments

- **Constructor inventory (Task 0):** Read `classic-config-core/src/lib.rs`, `classic-config-py/src/lib.rs` (full 1151 lines), and all relevant sources. Verified A3 lines 17-21 — every deferred symbol is already `pub use`d at the core lib.rs surface (zero re-exports needed). Discovered and documented 3 critical plan-scaffold divergences:
  1. **No PyO3 wrappers for CrashgenEntryRaw/CoreModEntry/CoreModExclude/ModConflictEntry/ModSolutionEntry/ModSolutionCriteria/SuspectErrorRule/SuspectStackRule/SuspectStackCountRule.** These surface only as dict/list items inside PyYamlData getters. Routed via @rust-suffixed proxy rows (Wave 1 precedent).
  2. **Plan's "22 deferred config" count was from pre-Plan-01 backlog.** Actual backlog now has 26 config entries; adopted ground truth.
  3. **2 of 4 Tier-2 bindings are @property-based** (`classic_config.YamlData.classic_version` and `warn_outdated`) — Python surface parser skips @property per `generate_baseline.py::_is_property_decorator` line 378. Preserved `python-tier2-config-runtime` per Wave 3a precedent.

- **28 contract rows authored (Task 1):** Built `_build_config_rows.py` helper that splits the 26 config backlog entries (15 rust-only + 11 python-only) and adds 2 Tier-2 migrations (get_application_dir, set_application_dir). Every row has `ownerModule='config'`, `tier='tier1'`, non-empty `rustSymbol` + `pythonExportPath` resolvable through the parsed surfaces. Per-submodule counts:
  - `config.config.*`: 9 rows (ClassicConfig/PathConfig/YamlSource dunders + `config` module marker)
  - `config.yamldata.*`: 15 rows (10 @rust type proxies + YamlData dunders + create_yamldata + 2 free-fn @rust + yamldata marker)
  - `config.shared.*`: 3 rows (get_application_dir, set_application_dir, get_runtime@rust)
  
  Helper script asserts 28 total with no duplicate IDs and verifies every `pythonExportPath` exists in `python_api_surface.json` before writing the contract. Final tier1Mappings = 314 (286 + 28).

- **Verified no-op .pyi update (Task 2):** Verified by automated cross-check that the existing `classic_config.pyi` (532 lines) already contains every Python identifier referenced by the 28 new contract rows (extracted from python_api_surface.json — 0 missing). `mypy --strict` already passes. Skipped Task 2 commit since there's nothing to change. Documented the no-op here.

- **13-test smoke suite (Task 3):** Authored `test_promoted_config_smoke.py` (324 lines) with per-class construction tests and fixture-backed YamlData deserialization. Tests use exact constructor signatures from the constructor inventory:
  - `test_path_config_constructs_with_defaults` + `_with_all_fields` (2 tests for PathConfig)
  - `test_classic_config_default_constructs` (ClassicConfig + validate_paths)
  - `test_yaml_source_classattrs_and_dunders` + `test_yaml_source_path_and_display_name_methods` (2 tests covering all 7 classattrs + 6 methods)
  - `test_yaml_data_from_yaml_content_fixture` (deserialization + all 6 dict-bearing getters)
  - `test_yaml_data_init_signature_exercised` (__init__ error path)
  - `test_yaml_data_structured_mod_solu_with_real_rules` (ModSolutionEntry + ModSolutionCriteria via real Mods_SOLU YAML)
  - `test_create_yamldata_factory_function` + `test_clear_yaml_cache_call` + `test_get_and_set_application_dir_roundtrip` (3 free function tests)
  - `test_config_exception_classes_hierarchy` (RustConfigError + IOError + ParseError)
  - `test_rust_only_symbols_in_core_surface` (Pitfall 2 guard asserting all 15 rust-only symbols exist in classic-config-core)

  Runs in 0.08s; 13/13 passed on first run with zero fix iterations (repeat of the Wave 3b first-run-clean achievement).

- **Runtime registry update (Task 4):**
  - `python-tier1-config` selector entry: `contractCount` 15 → 43, `contractIdsHash` recomputed to `90a8f039181858fd8aeb5af9e0ab2d9f1b1a2256fcfe31800a2bf6f5ed04eee0` (sha256 of 43 sorted config tier1 IDs).
  - `python-tier2-config-application-dir-runtime` DELETED — its 2 bindings (`get_application_dir`, `set_application_dir`) are now tier1 contract rows.
  - `python-tier2-config-runtime` PRESERVED — its 2 bindings (`classic_version`, `warn_outdated`) are `@property` methods invisible to the surface parser. Deleting would orphan runtime coverage per Wave 3a precedent.
  - `python-tier1-config-plan06-promoted` aux entry added with 13 explicit `bindingIdentifiers` pointing at `test_promoted_config_smoke.py`.

- **Baseline refresh (Task 4):** Regenerated all baseline + parity-artifacts files via `generate_baseline.py --output-dir docs/implementation/python_api_parity/baseline` and `check_parity_gate.py --update-baseline`. All baseline JSON/MD artifacts in lockstep with the 314-row contract.

- **Gate green:** `check_parity_gate.py` exits 0 with `Tier-1 parity gate passed.`; `tier1_contract_total = 314`, `tier1_missing_runtime_total = 0`, `registry_mismatch_total = 0`, `deferred_total = 1070` (down from 1084).

## Task Commits

Each task was committed atomically:

1. **Task 0: Constructor inventory** — `6ccfaaf2` (Docs)
2. **Task 1: 28 config contract rows + helper script** — `b2ac0f9c` (Feat)
3. **Task 2: .pyi update** — *no commit, verified no-op (all identifiers already in stub from prior phases; mypy --strict clean)*
4. **Task 3: Config smoke test suite** — `a6d4c2b6` (Test)
5. **Task 4: Runtime registry + baseline refresh** — `f3e12163` (Feat)

## Files Created/Modified

### Created

- `.planning/phases/03-python-tier-collapse/03-06-CONSTRUCTOR-INVENTORY.md` — Verified classic-config-py surface inventory; documents PyClass wrappers, rust-only symbols, tier-2 preservation analysis
- `.planning/phases/03-python-tier-collapse/_build_config_rows.py` — Reproducible helper script that generates the 28 contract rows from the deferred backlog
- `ClassicLib-rs/python-bindings/tests/test_promoted_config_smoke.py` — 13 pytest functions covering the 28 promoted config rows with R1-compliant fixture-backed construction (324 lines)

### Modified

- `docs/implementation/python_api_parity/baseline/parity_contract.json` — `tier1Mappings` grew from 286 to 314 entries; 28 new config rows added with dotted `config.<submodule>.<symbol>` IDs
- `docs/implementation/python_api_parity/baseline/{rust_api_surface,python_api_surface,parity_diff_report,runtime_coverage_summary}.{json,md}` — All 6 regenerated baseline artifacts reflect the 314-row contract (baseline/parity_contract.md unchanged — it's a static narrative file, not regenerated per plan)
- `ClassicLib-rs/python-bindings/parity-artifacts/{rust_api_surface,python_api_surface,parity_diff_report,runtime_coverage_summary,tier1_gate_report}.{json,md}` — Tracked generated artifacts mirror the baseline
- `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` — Bumped `python-tier1-config` (15→43, new hash); deleted `python-tier2-config-application-dir-runtime`; preserved `python-tier2-config-runtime`; added `python-tier1-config-plan06-promoted` aux entry with 13 binding identifiers

## Decisions Made

- **No PyO3 wrappers for crashgen_settings types**: The plan assumed CrashgenEntryRaw, CoreModEntry, CoreModExclude, ModConflictEntry, ModSolutionCriteria, ModSolutionEntry, SuspectErrorRule, SuspectStackRule, SuspectStackCountRule are promoted #[pyclass] types. Reading `classic-config-py/src/lib.rs` (full 1151 lines) showed NONE have PyO3 wrappers — they surface only as dict/list items inside PyYamlData getters (lib.rs:894-1014). Contract rows routed via @rust-suffixed proxy pattern paired with `YamlData`. This is the exact Wave 1 `StreamingLogParser`/`StreamingIteratorParser` precedent restated for config.

- **R15 canonical owner rule**: crashgen_settings types have ONE contract row in the config owner module. These types are re-exported from `classic-crashgen-settings-core` through `classic-config-core` (lib.rs:17-21), and consumed by `classic-scanlog-py` and `classic-scangame-py` — but those bindings don't expose the types with a distinct `pythonExportPath`. Per R15, no duplicate rows are needed in scanlog/scangame owner modules.

- **Deferred backlog count divergence**: The plan's "22 deferred config entries" came from RESEARCH.md Amendment A4 which cited `deferred_runtime_backlog.json` raw=22. Plan 01 regenerated the backlog from 285 to 1202 entries (per STATE.md decision). Current count is 26 config entries. Adopted ground truth (26) instead of the stale number (22). Documented as a Rule 1 deviation. Final row count is 2 higher than the plan promised (314 vs 312).

- **Tier-2 preservation for property bindings**: The plan instructed deleting both `python-tier2-config-runtime` and `python-tier2-config-application-dir-runtime`. Only the second one is safe to delete. The first has 2 bindings (`classic_config.YamlData.classic_version`, `classic_config.YamlData.warn_outdated`) that are Python-side `@property` methods. The Python surface parser skips `@property` decorators per `generate_baseline.py::_is_property_decorator` line 378 — any tier1 contract row claiming `pythonExportPath=YamlData.classic_version` would fail the gate with `tier1_missing_python > 0`. Preserved per Wave 3a precedent. Documented as a Rule 1 deviation.

- **Plan math reconciliation**: 26 deferred + 2 real Tier-2 migrations = 28 net new tier1 rows → tier1Mappings = 286 + 28 = 314 (not 312). Accepted; the plan's denominator was wrong.

- **Task 2 .pyi update was a verified no-op**: Like Wave 1/2/3b precedent, the existing pyi already contained all 28 promoted symbols. No commit created per no-empty-commits protocol. Documented in this summary.

- **Test discipline (Wave 1/3b precedent)**: Test file authored directly without RED/GREEN/REFACTOR cycle because all PyO3 wrappers already exist in the built wheel. Committed as `Test:` prefix. 13/13 tests passed on first run.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan assumption that crashgen_settings types are #[pyclass] wrappers**

- **Found during:** Task 0 (Constructor inventory)
- **Issue:** The plan's `<interfaces>` block and Task 3 `<action>` explicitly list `CrashgenEntryRaw`, `CoreModEntry`, `CoreModExclude`, `ModConflictEntry`, `ModSolutionCriteria`, `ModSolutionEntry`, `SuspectErrorRule`, `SuspectStackRule`, `SuspectStackCountRule` as promoted `#[pyclass]` types with direct Python constructors. The plan's test scaffold shows `classic_config.ModConflictEntry(mod_a="...", mod_b="...")`, `classic_config.SuspectErrorRule(name="...", severity="...", message="...")`, etc.
- **Root cause:** Reading `classic-config-py/src/lib.rs` in full (1151 lines) revealed that NONE of these types have `#[pyclass]` wrappers. The PyO3 layer converts them to Python dicts/lists inside `PyYamlData` getter methods (e.g., `suspect_error_rules` at line 894 builds a `PyList` of `PyDict` objects). The only `#[pyclass]` wrappers in classic-config-py are `PyPathConfig`, `PyYamlSource`, `PyClassicConfig`, and `PyYamlData`.
- **Fix:** Routed all 10 rust-only types through `@rust`-suffixed proxy contract rows paired with `YamlData` (Wave 1 precedent for `StreamingLogParser`/`StreamingIteratorParser`). The smoke test exercises these types indirectly by deserializing PARITY_*_YAML fixtures through `YamlData.from_yaml_content(...)` and calling the dict/list-bearing getters. A `test_rust_only_symbols_in_core_surface` Pitfall 2 guard asserts all 15 rust-only symbols exist in the parsed classic-config-core Rust surface, providing second-layer protection against drift.
- **Files modified:** `_build_config_rows.py` (rust_only_map), `test_promoted_config_smoke.py` (fixture-backed tests), `03-06-CONSTRUCTOR-INVENTORY.md`
- **Verification:** Pitfall 2 guard passes (all 15 symbols in rust_api_surface.json); contract diff has 0 missing_python; gate exits 0; smoke test 13/13 passed
- **Committed in:** `6ccfaaf2` (inventory), `b2ac0f9c` (rows), `a6d4c2b6` (tests)

**2. [Rule 1 - Bug] Deferred backlog count stale in plan (22 vs 26)**

- **Found during:** Task 1 (Authoring contract rows)
- **Issue:** The plan's must_haves, action block, and verify assertion all use "22 deferred config entries" (plus 4 Tier-2 = 26 total → tier1Mappings=312). Research Amendment A4 cited `deferred_runtime_backlog.json` raw=22. The actual current backlog has 26 config entries (Plan 01 regenerated the backlog from 285 to 1202 via `generate_wave_manifest.py`).
- **Root cause:** The plan was authored against pre-Plan-01 backlog counts. Plan 01's decision log entry in STATE.md documents: "Deferred backlog expanded from 285 to 1202 entries via generate_wave_manifest.py regeneration." Plan 06 references the stale number.
- **Fix:** Adopted ground-truth numbers from the current `deferred_runtime_backlog.json`. All 26 deferred config entries promoted (not 22). Net new tier1 rows = 26 + 2 Tier-2 migrations = 28 (not 26). Final tier1Mappings = 286 + 28 = 314 (not 312). Documented in constructor inventory before any code was written.
- **Files modified:** `_build_config_rows.py` (assertion `len == 26`), `parity_contract.json`, `03-06-CONSTRUCTOR-INVENTORY.md`
- **Verification:** Gate exits 0 with 314 tier1 rows; helper script's `assert len(config_deferred) == 26` passes; summary `tier1_contract_total == 314`
- **Committed in:** `b2ac0f9c`

**3. [Rule 1 - Bug] Plan instructed deletion of python-tier2-config-runtime (would orphan runtime coverage)**

- **Found during:** Task 0 (Constructor inventory, tier-2 migration analysis)
- **Issue:** The plan's Task 4 action block says "DELETE the following exact Tier-2 explicit-binding registry entries: `python-tier2-config-runtime` (covered 2 bindings: `classic_config.YamlData.classic_version`, `classic_config.YamlData.warn_outdated`) ... Both entries are safe to delete because their 4 bindings are now in tier1Mappings as promoted rows from Task 1."
- **Root cause:** Verified against `classic_config.pyi` lines 120-122 and 284-286 that `classic_version` and `warn_outdated` are declared with `@property` decorators. Verified against `generate_baseline.py::_is_property_decorator` (line 378) that the Python surface parser skips `@property`/`.setter`/`.deleter`. Verified against `python_api_surface.json` that `YamlData.classic_version` and `YamlData.warn_outdated` are NOT in the surface (only `__init__`, `__repr__`, `from_yaml_content` appear as `YamlData.*`). Contract rows claiming `pythonExportPath=YamlData.classic_version` would fail the gate with `tier1_missing_python > 0`. Deleting the tier-2 registry entry without promoting the bindings would orphan 2 runtime-verified coverage rows.
- **Fix:** Preserved `python-tier2-config-runtime` per Wave 3a precedent (same refusal pattern as the Plan 04 executor's decision to preserve `python-tier2-scanlog-runtime`). Deleted only `python-tier2-config-application-dir-runtime` (its 2 bindings ARE visible `#[pyfunction]` free fns that CAN be promoted). Net tier-2 migrations = 2 (not 4).
- **Files modified:** `runtime_coverage_registry.json`, `_build_config_rows.py` (only 2 migrations, not 4), `03-06-CONSTRUCTOR-INVENTORY.md`
- **Verification:** Gate's `registry_mismatch_total == 0` and `tier1_missing_runtime_total == 0`; coverage summary shows `python-tier2-config-runtime` still listed as runtime_verified with its 2 bindings intact
- **Committed in:** `f3e12163`

**4. [Rule 1 - Bug] Task 2 .pyi update was already complete**

- **Found during:** Task 2 (.pyi update verification)
- **Issue:** The plan describes Task 2 as a substantive hand-edit adding stub entries for all 26 new config rows. The plan's Task 2 scaffold shows class declarations for `CrashgenEntryRaw`, `CoreModEntry`, `ModConflictEntry`, `SuspectErrorRule`, etc. — but since these types have no PyO3 wrappers (Deviation 1), they cannot be declared as classes in the pyi.
- **Fix:** Verified by automated cross-check that the existing 532-line `classic_config.pyi` already contains every Python identifier from the 28 new contract rows (extracted `pythonExportPath` values, checked each against `python_api_surface.json` — 0 missing). Ran `mypy --strict classic_config.pyi` — passes with no issues. Skipped the Task 2 commit (no-empty-commits protocol). This matches the Wave 1/2/3b precedent where prior phase work had already populated the stub.
- **Files modified:** None
- **Verification:** Gate's `tier1_missing_python == 0`; mypy --strict clean
- **Committed in:** Not applicable (no changes)

---

**Total deviations:** 4 Rule 1 auto-fixes. All corrected wrong assumptions in the plan scaffold about (a) which rust types have Python wrappers, (b) deferred backlog current count, (c) tier-2 binding promotability, and (d) the existing .pyi state. None changed the plan's intent or output shape beyond numeric tolerance.

## Authentication Gates

None — all work is internal to Python parity tooling and registry.

## Issues Encountered

- **Pre-existing pytest failures in unrelated test files**: Not touched (scope boundary per deferred-items.md logged during Wave 1).

## User Setup Required

None — no external service configuration required.

## Verification Results (5-Step Chain)

| Step | Command | Result |
|---|---|---|
| 1 | `python tools/python_api_parity/check_parity_gate.py --repo-root .` | **PASS** (`Tier-1 parity gate passed.`; 314/314 matched, 0 drift, 0 newly_uncovered, 0 registry mismatches, 0 tier1_missing_runtime) |
| 2 | `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/.../parity_contract.json --fail-on-warnings` | **PASS** (3/3 crates passed, 0 errors, 0 warnings) |
| 3 | `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python -Crates classic_config` | **PASS** (wheel built + installed + verified) |
| 4 | `pytest ClassicLib-rs/python-bindings/tests/test_promoted_config_smoke.py -q` | **PASS** (13/13 in 0.08s) |
| 5 | `mypy --strict ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi` | **PASS** (`Success: no issues found in 1 source file`) |

## Next Phase Readiness

- **Plan 07 (version_registry promotion) is ready to execute.** The Wave 1/3a pattern now has proven generalization beyond scanlog (Plan 06 is the first non-scanlog promotion plan). Plan 07 can follow the same shape: constructor inventory first → dotted ID scheme with @rust proxies → fixture-backed smoke tests → selector+aux registry updates → 5-step verification.
- **Reusable helper:** `_build_config_rows.py` is a template for Plan 07 — change the owner module filter, the rust_only_map/python_only_map, and the sub-module routing.
- **Tier-1 floor:** Plan 01 tooling tests that assert `tier1_contract_total >= N` should be bumped — current snapshot is 314. Plans 07-09 will push toward 350-500+.
- **Tier-2 preservation has 2 precedents now** (Wave 3a scanlog + Plan 06 config). This pattern should be codified in the phase's `patterns-established` rollup when Plan 09b lands the final Tier-2 cleanup.

## Self-Check: PASSED

Verification performed after SUMMARY.md draft:

**Files created check:**
- `.planning/phases/03-python-tier-collapse/03-06-CONSTRUCTOR-INVENTORY.md` — FOUND
- `.planning/phases/03-python-tier-collapse/_build_config_rows.py` — FOUND
- `ClassicLib-rs/python-bindings/tests/test_promoted_config_smoke.py` — FOUND

**Commits check:**
- `6ccfaaf2` Docs(03-06): Add config promotion constructor inventory artifact — FOUND
- `b2ac0f9c` Feat(03-06): Add 28 config tier1 contract rows for Plan 06 promotion — FOUND
- `a6d4c2b6` Test(03-06): Add fixture-backed smoke tests for Plan 06 config promotions — FOUND
- `f3e12163` Feat(03-06): Refresh parity baseline and runtime registry for config promotion — FOUND

**Verification commands:**
- `check_parity_gate.py --repo-root .` — EXIT 0 (Tier-1 parity gate passed)
- `validate_stubs.py --fail-on-warnings` — EXIT 0 (3/3 crates, 0 errors)
- `pytest test_promoted_config_smoke.py -q` — EXIT 0 (13 passed)
- `mypy --strict classic_config.pyi` — EXIT 0 (no issues)

---
*Phase: 03-python-tier-collapse*
*Completed: 2026-04-08*
