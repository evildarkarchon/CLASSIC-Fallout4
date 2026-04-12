---
status: passed
phase: 01-yaml-settings-merge
must_have_score: 10/10
requirements_covered: [YAML-01, YAML-02, YAML-03, YAML-04]
requirements_missing: []
date: 2026-04-10
verifier: Claude (gsd-verifier)
---

# Phase 1: YAML -> Settings Merge Verification Report

**Phase Goal (ROADMAP.md):** classic-yaml-core no longer exists as a separate crate; all its public API is available from classic-settings-core with no consumer-visible behavior change.

**Verified:** 2026-04-10
**Status:** passed (10/10 must-haves verified)
**Mode:** Initial verification (no prior VERIFICATION.md)

---

## Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every public yaml-core type/function/re-export is accessible from classic-settings-core at same API surface | PASS | `classic-settings-core/src/yaml_ops.rs` + `yaml_merge.rs` absorbed; flat re-exports in `src/lib.rs` (YamlOperations, YamlError, YamlCacheStats, yaml_cache_stats, reset_yaml_cache_stats, clear_global_yaml_cache, merge_keys) |
| 2 | No crate in workspace depends on `classic-yaml-core` | PASS | `grep classic-yaml-core **/Cargo.toml` returns zero matches |
| 3 | classic-yaml-core directory deleted and removed from workspace members | PASS | `ClassicLib-rs/business-logic/classic-yaml-core/` absent; `ClassicLib-rs/Cargo.toml` no longer lists it |
| 4 | All three binding crates (C++, Node, Python) compile against settings-core import path with existing tests passing | PASS | Plan 01-02 SUMMARY: cargo test --workspace green, bun test 986/0, node test 17/0, classic-cli build 17 unit + 24 integration pass, Python smoke test green |
| 5 | `cargo build --workspace` and `cargo test --workspace` succeed with zero failures | PASS | Documented across 01-01, 01-02, 01-03 SUMMARYs (commit `ec596e0e`, `7b97bf2b`, `8456be21`) |

---

## Must-Haves Evaluation

### 1. classic-yaml-core fully removed
- `ClassicLib-rs/business-logic/classic-yaml-core/` — **absent** (ls error)
- `ClassicLib-rs/Cargo.toml` grep `classic-yaml-core` — **0 matches**
- `**/Cargo.toml` grep `classic-yaml-core` — **0 matches**
- `**/*.rs` grep `classic_yaml_core` — 6 matches, all in doc/comment strings (migration-marker D-14 phrasing in `yaml_ops.rs`, `lib.rs`, `yaml_integration_tests.rs`, `config-core/tests/integration_tests.rs`, `classic-settings-py/src/lib.rs`, `classic-node/src/settings.rs`). **No live `use` statements, no `extern crate`.**
- `tools/` grep — only `tools/parity_contract_merge_owner.py` contains `classic-yaml-core` string (the merge helper's scheduled delete entry, not a live dependency)
- **PASS**

### 2. classic-yaml-py fully removed
- `ClassicLib-rs/python-bindings/classic-yaml-py/` — **absent** (ls error)
- Workspace member — already dropped in 01-01, deletion finalized in 01-02 commit `2475eeaf`
- YamlOperations exposed from `classic-settings-py/src/lib.rs` — 17 matches on `class YamlOperations|RustYamlError|yaml_cache_stats`
- **PASS**

### 3. C++ bridge `yaml` renamed to `settings` with D-09 expansion
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/yaml.rs` — **absent**
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/settings.rs` — **present**
- `build.rs` line 8: `"src/settings.rs"` — **present**, no yaml.rs
- `src/lib.rs` line 75: `pub mod settings;` — **present**, no yaml mod
- `classic-cli/CMakeLists.txt:44: settings.rs` — **present**, no yaml.rs
- `classic-gui/CMakeLists.txt:49: settings.rs` — **present**, no yaml.rs
- `settings.rs` contains 45 matches across `settings_cache_stats|settings_validate_|settings_coerce_value` — **D-09 surface present**
- **PASS**

### 4. Node binding consolidation
- `ClassicLib-rs/node-bindings/classic-node/src/yaml.rs` — **absent**
- `ClassicLib-rs/node-bindings/classic-node/src/settings.rs` — **present**
- `src/lib.rs:37: mod settings;` — only settings module declared; no `mod yaml;`
- Test file `__test__/yaml.spec.ts` deleted; content folded into `settings.spec.ts` (per plan 01-02 commit `a51c183a`)
- **PASS**

### 5. Parity gates baseline reparenting
- `docs/implementation/python_api_parity/baseline/parity_contract.json` grep `classic-yaml-core|classic_yaml_core` — **0 matches**
- `docs/implementation/node_api_parity/baseline/parity_contract.json` — **0 matches**
- `docs/implementation/*/baseline/*_contract.json` grep `"ownerModule": "yaml"` — **0 matches**
- `ClassicLib-rs/python-bindings/parity-artifacts/rust_api_surface.json` grep `classic-yaml-core` — **0 matches**
- Gates reported PASS in plan 01-03 SUMMARY: CXX 333 entries, Node 705 tier1 rows, Python 613 tier1 rows, 0 drift across all three
- **PASS** (with one cosmetic drift noted under Observations)

### 6. Docs consolidation
- `docs/api/classic-yaml-core.md` — **absent** (deleted in commit `8b4c6c57`)
- `docs/api/README.md` grep `classic-yaml-core|classic_yaml` — **0 matches**
- `docs/api/classic-settings-core.md` contains `## YAML Operations` section starting at line 479 with YamlOperations, YamlFormatConfig, YamlCacheStats, `yaml_cache_stats()`, `reset_yaml_cache_stats()`, YamlError variants, `merge_keys()`, C++ bridge `classic::settings` surface documentation, and runnable usage example
- `docs/api/binding-parity-overview.md` contains Phase 1 consolidation note and lists `classic-settings-core (absorbed the former yaml-core)` with `settings.rs` across all three binding columns
- **PASS**

### 7. Requirements traceability (YAML-01..YAML-04)

| Req | Definition | Delivered Artifact | Evidence |
|-----|-----------|-------------------|----------|
| YAML-01 | yaml-core source modules relocated into settings-core with same public API surface | `yaml_ops.rs`, `yaml_merge.rs` under `classic-settings-core/src/` | Plan 01-01 commit `ec596e0e`; tests, benches, and integration tests moved via `git mv` |
| YAML-02 | All workspace crates importing from yaml-core now import from settings-core | classic-config-core, classic-version-registry-core, classic-scanlog-core, classic-cpp-bridge, classic-node Cargo.toml + source migrations | Plan 01-01 commit `ec596e0e`; no `use classic_yaml_core::` remains in any .rs file |
| YAML-03 | classic-yaml-core removed from Cargo.toml workspace members and directory deleted | Directory absent; `ClassicLib-rs/Cargo.toml` has no reference | Plan 01-01 commit `ec596e0e` |
| YAML-04 | Binding crates (C++, Node, Python) referenced yaml-core types are updated to settings-core import path | C++ bridge renamed+expanded (D-09); Node yaml.rs folded; Python classic-yaml-py folded into classic-settings-py | Plan 01-02 commits `7b97bf2b`, `a51c183a`, `2475eeaf`, `f7e274cd`; Plan 01-03 commit `8456be21` closes parity loop |

**All 4 requirements SATISFIED.** REQUIREMENTS.md confirms all four checked `[x]`.

### 8. Phase Goal Statement (ROADMAP.md)
Goal text: *"classic-yaml-core no longer exists as a separate crate; all its public API is available from classic-settings-core with no consumer-visible behavior change"*
- Crate removed: YES
- Public API available from settings-core: YES (flat re-exports, YamlOperations class wrapper, D-09 bridge expansion matching Python surface)
- No consumer-visible behavior change: YES per Python smoke test output (yaml cache capacity still 128, settings cache still 64, parse/validate paths match)
- **PASS**

### 9. Human verification items
ROADMAP.md does not declare human_verification for phase 1. This phase is pure refactor + binding consolidation. No UAT items. `human_needed: none`.

### 10. Known limitations (acknowledged, not gaps)
- **GUI Qt Release build skipped** — documented worktree Qt Release linker quirk. classic-cli covers the full CXX bridge surface including all D-09 settings_* exports. Documented in 01-02 and 01-03 SUMMARYs.
- **2 pre-existing pytest failures** in `test_parity_gate_tooling.py::test_update_baseline_flag_refreshes_stale_baseline` — unsupported `--deferred-registry` flag. Pre-existing on this branch before phase 1, verified via git stash by executor. Not a phase 1 gap.

---

## Observations (non-blocking)

**Stale `docs/implementation/*/rust_api_surface.json` snapshots.** The files `docs/implementation/python_api_parity/baseline/rust_api_surface.json` and `docs/implementation/node_api_parity/baseline/rust_api_surface.json` still list `classic-yaml-core` as a target crate (lines 8 and 15 respectively) and reference `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs` as a source file. Their `generated_at_utc` is 2026-04-10 but they were NOT in the file list of commit `8456be21` (the Task 3 regeneration commit).

**Why this is NOT a gap:**
- `rust_api_surface.json` is a WRITE-ONLY output artifact of both `check_parity_gate.py` and `generate_baseline.py` (confirmed by inspecting `tools/python_api_parity/check_parity_gate.py:237`).
- The gate's drift check (`tracked_artifact_names` at line 259) covers only `parity_diff_report.{json,md}` and `runtime_coverage_summary.{json,md}` — NOT `rust_api_surface.json`.
- The authoritative committed copy at `ClassicLib-rs/python-bindings/parity-artifacts/rust_api_surface.json` IS clean (0 matches).
- The actual `parity_contract.json` files (what the gate consumes as input) ARE clean.
- Plan 01-03 SUMMARY claims all three gates PASS green with 0 drift — consistent with `parity_contract.json` being the authoritative contract.

**Recommendation:** A follow-up `gsd:quick` to regenerate the two stale baseline snapshots under `docs/implementation/` for cleanliness. This is cosmetic and does not block phase 1 goal achievement.

---

## Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| YAML-01 | 01-01 | SATISFIED | `yaml_ops.rs`, `yaml_merge.rs` under classic-settings-core |
| YAML-02 | 01-01 | SATISFIED | 0 `classic-yaml-core` refs in any Cargo.toml |
| YAML-03 | 01-01 | SATISFIED | Directory deleted, workspace members cleaned |
| YAML-04 | 01-02, 01-03 | SATISFIED | All three bindings migrated; parity contracts reparented |

All 4 phase-declared requirement IDs have concrete codebase evidence and are marked `[x]` complete in REQUIREMENTS.md. No orphaned requirements.

---

## Anti-Patterns Scan

No blocker anti-patterns. Historical `classic-yaml-core` / `classic_yaml_core` mentions in `.rs` files are intentional D-14 migration-marker comments for contributor discoverability and are not stubs or dead code. Migration markers follow the backticked `yaml-core` convention per plan 01-03 key_decisions.

---

## Gaps Summary

**None.** Phase 1 achieved its goal across all 10 verification checks. All 4 requirement IDs (YAML-01..YAML-04) satisfied. Only observation is a cosmetic drift in two snapshot files (`docs/implementation/*/rust_api_surface.json`) that are regenerated on every gate run and do not block the parity contracts or gate pass/fail.

---

## Verification Details

**Commits verified (git log):**
- `3276fd20` — Task 1 git mv (blame-preserving rename)
- `ec596e0e` — Task 2 content edits + consumer migration
- `7b97bf2b` — C++ bridge rename + D-09 expansion
- `a51c183a` — Node yaml merge
- `2475eeaf` — Python yaml-py fold-in + crate deletion
- `f7e274cd` — CMakeLists 5th-place registration fix
- `8b4c6c57` — Docs consolidation
- `21702a8a` — Parity contract merge helper
- `0f81d043` — Contract + registry + generator edits
- `8456be21` — Baseline regeneration

**Grep evidence:**
```
ClassicLib-rs/Cargo.toml (classic-yaml-core)           : 0
**/Cargo.toml (classic-yaml-core)                      : 0
**/*.rs (classic_yaml_core) live use/extern             : 0
**/*.rs (classic_yaml_core) comments/docs               : 6 (D-14 migration markers)
docs/api/README.md (classic-yaml-core)                 : 0
docs/implementation/*/baseline/parity_contract.json    : 0
parity-artifacts/rust_api_surface.json                 : 0
classic-cli/CMakeLists.txt                              : settings.rs present, yaml.rs absent
classic-gui/CMakeLists.txt                              : settings.rs present, yaml.rs absent
cpp-bridge settings.rs (D-09 surface markers)          : 45 matches
classic-settings-py/src/lib.rs YamlOperations surface  : 17 matches
```

---

_Verified: 2026-04-10_
_Verifier: Claude (gsd-verifier)_
_Phase: 01-yaml-settings-merge_
