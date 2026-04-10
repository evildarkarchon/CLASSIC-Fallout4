---
phase: 02-cxx-bridge-surface-expansion
plan: "07"
subsystem: cxx-bridge
tags:
  - cxx
  - config
  - database
  - suspect-rules
  - formid
  - cxxs-05
  - cxxs-07
  - pitfall-6
dependency_graph:
  requires:
    - 02-01 (build.rs baseline)
    - 02-02 (path/constants/web bridge widening)
    - 02-03 (version registry/XSE bridge widening)
    - 02-04 (scangame bridge widening)
    - 02-05 (config initial widening)
    - 02-06 (scangame toml/wrye/integrity/setup widening)
  provides:
    - SuspectErrorRuleDto + yaml_data_suspects_error_rules() in classic::config (CXXS-07)
    - SuspectStackRuleMetadataDto + yaml_data_suspects_stack_rules_metadata() in classic::config (CXXS-07, Pitfall 6 flattened)
    - SuspectStackCountRuleDto + yaml_data_suspects_stack_count_rules_for_id() in classic::config (CXXS-07, Pitfall 6 flattened)
    - FormIdEntryDto + db_pool_get_entry_typed() + db_pool_get_entries_batch_typed() in classic::database (CXXS-05)
  affects:
    - parity baseline (314 entries)
tech_stack:
  patterns:
    - CXX shared struct DTO with Vec<String> fields (Pitfall 6 safe)
    - Flattened metadata DTO + separate per-rule count getter (Pitfall 6 fix for nested Vec<Struct>)
    - Positional repackaging pattern for hit-only HashMap → Vec<DTO>
    - Fail-soft bridge contract (empty Vec on error, found: false on miss)
key_files:
  modified:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
    - docs/implementation/cxx_api_parity/baseline/rust_api_surface.json
decisions:
  - "Suspect-stack rules flattened into SuspectStackRuleMetadataDto (no nested Vec<Struct>) + separate yaml_data_suspects_stack_count_rules_for_id() getter (Pitfall 6 fix per Codex HIGH correction)"
  - "FormIdEntryDto.found derived from Ok(Some(_)) rather than !value.is_empty() for semantic accuracy"
  - "db_pool_get_entries_batch_typed passes batch_size=100 to core for UI responsiveness balance"
  - "D-11 N/A justified: no current call sites for typed FormID lookups or suspect-rule readers in classic-cli/classic-gui (grep evidence documented)"
metrics:
  duration_secs: 562
  completed_date: "2026-04-08"
  tasks_completed: 3
  files_changed: 7
---

# Phase 02 Plan 07: Config Suspect Rules and Database Typed — Summary

**One-liner:** Widened CXX config bridge with flattened suspect-rule DTOs (CXXS-07, Pitfall 6 cleared) and database bridge with positional-repackaging typed FormID API (CXXS-05, documented hit-only contract).

## What Was Built

### Task 1: config.rs CXXS-07 suspect-rule typed API

Added 3 shared structs and 3 bridge functions to `src/config.rs`, all additive per D-08:

**New shared structs in `#[cxx::bridge(namespace = "classic::config")]`:**
- `SuspectErrorRuleDto { id, name, severity, main_error_contains_any: Vec<String> }`
- `SuspectStackRuleMetadataDto { id, name, severity, main_error_required_any, main_error_optional_any, stack_contains_any, exclude_if_stack_contains_any }` — NO `stack_contains_at_least` field (Pitfall 6 fix)
- `SuspectStackCountRuleDto { substring, count: u32 }` — returned by separate getter

**New bridge functions:**
- `yaml_data_suspects_error_rules(data: &YamlData) -> Vec<SuspectErrorRuleDto>` — full error-rule set
- `yaml_data_suspects_stack_rules_metadata(data: &YamlData) -> Vec<SuspectStackRuleMetadataDto>` — flattened metadata only
- `yaml_data_suspects_stack_count_rules_for_id(data: &YamlData, rule_id: &str) -> Vec<SuspectStackCountRuleDto>` — per-rule count rules keyed by id

**Pitfall 6 confirmation:** `SuspectStackRuleMetadataDto` has NO `Vec<Struct>` field — only `Vec<String>` fields (matches the existing `YamlDataModSolutionCriteria` precedent). `stack_contains_at_least: Vec<SuspectStackCountRule>` from the core type is surfaced via the separate getter, not embedded in the metadata DTO. `grep -n 'stack_contains_at_least: Vec<' src/config.rs` returns NOTHING.

**6 new tests:**
- `test_yaml_data_suspects_error_rules_empty`
- `test_yaml_data_suspects_error_rules_populated`
- `test_yaml_data_suspects_stack_rules_metadata_no_count_rules_field`
- `test_yaml_data_suspects_stack_count_rules_unknown_id_returns_empty`
- `test_yaml_data_suspects_stack_count_rules_known_id_returns_populated`
- `test_yaml_data_suspects_error_keys_still_works_d08_regression`
- `test_yaml_data_suspects_stack_keys_still_works_d08_regression`

Result: 13 config tests pass (7 existing + 6 new).

### Task 2: database.rs CXXS-05 typed FormID API

Added 1 shared struct and 2 bridge functions to `src/database.rs`, all additive per D-08:

**New shared struct in `#[cxx::bridge(namespace = "classic::database")]`:**
- `FormIdEntryDto { formid, plugin, value, found: bool }` — with full doc comment explaining `found: false` semantics

**New bridge functions:**
- `db_pool_get_entry_typed(pool: &DbPool, formid: &str, plugin: &str) -> FormIdEntryDto` — `found` derived from `Ok(Some(_))`, not `!value.is_empty()`
- `db_pool_get_entries_batch_typed(pool: &DbPool, formids: &[String], plugins: &[String]) -> Vec<FormIdEntryDto>` — positional repackaging with documented hit-only contract

**Batch lookup contract documented (Codex MEDIUM correction):**
- Core `get_entries_batch` returns HIT-ONLY HashMap — misses absent from map
- Wrapper repackages into ONE DTO per input pair — `result[i]` corresponds to `(formids[i], plugins[i])`
- Length mismatch returns empty Vec (fail-soft)
- Empty input returns empty Vec immediately (no runtime cost)
- Internal batch_size=100 (SQL overhead vs UI responsiveness balance)
- C++ callers requesting >1000 entries should chunk on their side

**6 new tests:**
- `test_db_pool_get_entry_typed_uninitialized_returns_not_found`
- `test_db_pool_get_entries_batch_typed_empty_returns_empty`
- `test_db_pool_get_entries_batch_typed_length_mismatch_returns_empty`
- `test_db_pool_get_entries_batch_typed_positional_repackaging`
- `test_db_pool_get_entry_still_works_d08_regression`
- `test_db_pool_get_entries_batch_still_works_d08_regression`

Result: 10 database tests pass (4 existing + 6 new). 285 total bridge tests pass.

### Task 3: Builds, baseline refresh, D-11 N/A justification

**Incremental builds:** Both `build_cli.ps1 -Test` (24/24 passed) and `build_gui.ps1 -Test` (10/10 passed) pass.

**D-09 baseline refresh:** `generate_baseline.py --write-baseline` updated `parity_contract.json` to 314 entries (+9 from 305). `check_parity_gate.py --repo-root .` exits 0 with 0 drift.

**D-11 N/A justification (Codex MEDIUM correction — grep evidence at execution time):**
```
grep -rn 'db_pool_get_entry|db_pool_get_entries_batch' classic-cli/src/ classic-gui/src/
→ NO MATCHES (FormID typed API D-11 N/A confirmed)

grep -rn 'yaml_data_suspects_|SuspectErrorRule|SuspectStackRule' classic-cli/src/ classic-gui/src/
→ NO MATCHES (suspect-rule readers D-11 N/A confirmed)

grep -rn 'classic::config::yaml_data_' classic-cli/src/ classic-gui/src/
→ NO MATCHES (config bridge consumers D-11 N/A confirmed)
```

The new typed surfaces remain available for future consumer migration (e.g., Phase 5/6 plans).

## Deviations from Plan

### Auto-fixed Issues

None.

### Plan Deviations

**1. FormIdEntryDto.found uses Ok(Some(_)) semantics, not !value.is_empty()**
- The plan's action code used `let found = !value.is_empty()` as the derivation
- The implementation uses `Ok(Some(v)) => (v, true), Ok(None) => (_, false), Err(_) => (_, false)` instead
- Rationale: semantically accurate — a DB entry with an empty string value would incorrectly show as `found: false` with the heuristic approach
- This is a Rule 1 (bug fix) deviation applied inline

**2. Test helper `make_yaml_data_with_suspect_rules` uses `std::mem::forget(temp)`**
- The tempdir guard must stay alive for the test to use the fixture YAML files
- Since `yaml_data_load` reads them synchronously, `forget` is needed to prevent cleanup before the data is loaded
- Test-only code, no production impact

## D-11 N/A Verification

Status: **N/A** — justified with execution-time grep evidence above.

The new typed surfaces are available for future Phase migration but have no current C++ consumer in `classic-cli/` or `classic-gui/`. Adding an artificial consumer purely to satisfy D-11 would be padding (Codex review explicitly allows N/A "if a plan has TRULY no real caller after investigation").

## Parity Baseline Delta

| Change | Module | Type | Name |
|--------|--------|------|------|
| ADDED | config | struct | SuspectErrorRuleDto |
| ADDED | config | struct | SuspectStackRuleMetadataDto |
| ADDED | config | struct | SuspectStackCountRuleDto |
| ADDED | config | fn | yaml_data_suspects_error_rules |
| ADDED | config | fn | yaml_data_suspects_stack_rules_metadata |
| ADDED | config | fn | yaml_data_suspects_stack_count_rules_for_id |
| ADDED | database | struct | FormIdEntryDto |
| ADDED | database | fn | db_pool_get_entry_typed |
| ADDED | database | fn | db_pool_get_entries_batch_typed |
| REMOVED | config | — | (none — D-08 additive) |
| REMOVED | database | — | (none — D-08 additive) |

## Known Stubs

None. All new bridge functions delegate entirely to core Rust implementations.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` | FOUND |
| `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs` | FOUND |
| `docs/implementation/cxx_api_parity/baseline/parity_contract.json` | FOUND |
| `.planning/phases/02-cxx-bridge-surface-expansion/02-07-config-suspect-rules-and-database-typed-SUMMARY.md` | FOUND |
| Commit `805f01e8` (config CXXS-07) | FOUND |
| Commit `bc6d8bed` (database CXXS-05) | FOUND |
| Commit `e6613f71` (D-09 baseline) | FOUND |
| All 285 bridge tests pass | VERIFIED |
| build_cli.ps1 -Test: 24/24 passed | VERIFIED |
| build_gui.ps1 -Test: 10/10 passed | VERIFIED |
| parity gate exits 0 at 314 entries | VERIFIED |
| Pitfall 6 cleared (no Vec<Struct> field in returned Vec shape) | VERIFIED |
