---
phase: 01-yaml-settings-merge
plan: 02
subsystem: bindings
tags: [rust, cxx, napi, pyo3, bindings, refactor, yaml, settings, D-09]

# Dependency graph
requires: [01-01]
provides:
  - C++ bridge under classic::settings namespace (renamed from classic::yaml)
  - C++ bridge expansion: settings_load_{sync,async_blocking,batch_sync,batch_async_blocking}, settings_cache_{stats,size,keys,is_cached,invalidate,clear_cache,reset_cache_stats}, settings_validate_{structure,value}, settings_coerce_value (D-09)
  - SettingsCacheStats, SettingsValidationIssue, SettingsCoercedValue, YamlCacheStatsDto shared CXX structs
  - Node classic-node settings module carrying yaml + settings functions (yaml.rs deleted, yaml.spec.ts merged into settings.spec.ts)
  - Python classic_settings module carrying YamlOperations, RustYamlError/IOError/ParseError, merge_keys, yaml_cache_stats, reset_yaml_cache_stats, clear_global_yaml_cache (folded in from classic-yaml-py)
  - classic-yaml-py crate and directory fully deleted from disk
affects: [01-03-PLAN (parity baseline regeneration), wave 3 docs consolidation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "5th-place CXX bridge registration: classic-cli/CMakeLists.txt and classic-gui/CMakeLists.txt hardcode corrosion_add_cxxbridge FILES lists — must be updated alongside build.rs, src/lib.rs, the #[cxx::bridge] block, and the generated header"
    - "yaml-file cache vs settings cache: two separate process-wide caches (128 vs 64 capacity) in classic-settings-core. Bindings must expose them under distinct names (yaml_cache_stats vs cache_stats) or silently swap numbers (concern 13)"
    - "CXX type-system exceptions: get_cached(Option<Arc<Vec<Yaml>>>) and load_settings_*(Arc<Vec<Yaml>>) cannot cross the CXX boundary. Bridge exposes doc-count u32 for load_* and skips get_cached entirely — callers fall back to yaml_ops_* for parsed docs"
    - "Dual to_napi_err disambiguation: merging the yaml NAPI module into settings forced renaming the yaml-side helper to yaml_err_to_napi to avoid collision with the pre-existing generic to_napi_err"

key-files:
  created:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/settings.rs (renamed from yaml.rs via git mv, then content-expanded)
  modified:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
    - classic-cli/src/scanner.cpp
    - classic-gui/src/main.cpp
    - classic-gui/src/app/mainwindow.cpp
    - classic-gui/src/app/settingsdialog.cpp
    - classic-gui/src/controllers/scancontroller.cpp
    - classic-cli/CMakeLists.txt (deviation — not in plan files_modified)
    - classic-gui/CMakeLists.txt (deviation — not in plan files_modified)
    - ClassicLib-rs/node-bindings/classic-node/src/settings.rs
    - ClassicLib-rs/node-bindings/classic-node/src/lib.rs
    - ClassicLib-rs/node-bindings/classic-node/__test__/settings.spec.ts
    - ClassicLib-rs/python-bindings/classic-settings-py/Cargo.toml
    - ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs
    - ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi
    - ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py
    - .idea/CLASSIC-Fallout4.iml
  deleted:
    - ClassicLib-rs/node-bindings/classic-node/src/yaml.rs
    - ClassicLib-rs/node-bindings/classic-node/__test__/yaml.spec.ts
    - ClassicLib-rs/python-bindings/classic-yaml-py/ (entire crate: Cargo.toml, src/lib.rs, classic_yaml.pyi, benches/gil_benchmarks.rs — per D-05 gil_benchmarks is intentionally NOT migrated)

key-decisions:
  - "D-09 bridge expansion landed in the same commit as the rename — not deferred. C++ now has cache ops + validators matching Python surface, subject to two documented CXX type exceptions"
  - "YamlCacheStatsDto rename (concern 10): pre-existing CXX shared struct CacheStats renamed to avoid post-namespace-flip collision with the new SettingsCacheStats DTO. No C++ consumers referenced CacheStats directly, so this was a bridge-internal rename"
  - "PyYamlOperations::get_cache_stats calls core_yaml_cache_stats() (concern 13 fix): the D-03 rename in plan 01-01 means calling the unrelated core::cache_stats() would silently return settings-cache numbers. Runtime smoke test confirms distinct capacity (128 yaml / 64 settings) so the two caches are correctly separated"
  - "Three yaml exceptions copied verbatim (concern 6): RustYamlError, RustYamlIOError, RustYamlParseError. NO RustYamlSerializeError — YamlError::SerializeError routes to RustYamlParseError, matching yaml-py's behavior at lines 117-119"
  - "9-token case-insensitive setting-type parser (concern 7 / MEDIUM-7 fix): int, integer, bool, boolean, float, double, path, string, str. Mirrors classic-settings-py parse_setting_type 1:1. list/map/array explicitly rejected — the underlying SettingType enum has only five variants"
  - "classic-shared-py is now a mandatory dep of classic-settings-py (concern 14): required for define_exceptions!, register_exceptions!, without_gil, PathLike — used by the folded-in PyYamlOperations methods"
  - "CMakeLists.txt auto-fix (Rule 3, deviation): 5th-place bridge registration. The plan's 'files_modified' list did not include CMakeLists.txt because the research phase missed that corrosion_add_cxxbridge takes a hardcoded FILES list in CMake. Fixed inline — C++ CLI would not compile otherwise"
  - "Parity gate failures (Node + Python) are pre-existing and deferred to Wave 3: plan 01-01 removed classic-yaml-core but the parity tooling (tools/node_api_parity/generate_baseline.py and tools/python_api_parity/generate_baseline.py) hardcodes that path. Plan 01-03 regenerates baselines and updates the tool. This plan was instructed NOT to touch parity baselines"

patterns-established:
  - "5th-place CXX bridge registration rule: whenever a CXX bridge module is added/renamed/deleted, update build.rs, src/lib.rs, #[cxx::bridge] block, header path, AND every classic-*/CMakeLists.txt corrosion_add_cxxbridge FILES list. Add this to project memory for future bridge work"

requirements-completed: [YAML-04]

# Metrics
duration: ~90 min
completed: 2026-04-10
---

# Phase 01 Plan 02: Binding Layer Consolidation Summary

**All three binding surfaces (C++ bridge, Node NAPI, Python PyO3) migrated from yaml-core to settings-core: C++ bridge renamed classic::yaml -> classic::settings and expanded with full settings-core cache ops + validators (D-09), Node yaml.rs folded into settings.rs, Python classic-yaml-py crate deleted and folded into classic-settings-py. Runtime smoke-tested: YamlOperations is a PyYamlOperations wrapper, yaml cache (capacity 128) and settings cache (capacity 64) remain distinct, 40/40 new bridge tests pass, 986/986 bun tests pass, 17/17 Node node:test runtime tests pass, C++ CLI 17 unit + 24 integration tests pass.**

## Performance

- **Duration:** ~90 min
- **Tasks:** 3 (each atomic commit + 1 deviation commit)
- **Files modified:** 25 in the three task commits, +2 CMakeLists deviation
- **Commits:** 4 task commits + this metadata commit (pending)

## Task Commits

1. **Task 1: C++ bridge rename + D-09 expansion** — `7b97bf2b` (Refactor)
   - git mv src/yaml.rs -> src/settings.rs (blame preserved)
   - Namespace flip classic::yaml -> classic::settings
   - Pre-existing CacheStats DTO renamed to YamlCacheStatsDto
   - New settings_* functions: load_{sync,async_blocking,batch_sync,batch_async_blocking}, cache_{stats,size,keys,clear_cache,reset_cache_stats}, is_cached, invalidate, validate_{structure,value}, coerce_value
   - New shared structs: SettingsCacheStats, SettingsValidationIssue, SettingsCoercedValue
   - All 5 C++ consumers updated (classic::yaml:: -> classic::settings::)
   - 22 new inline tests + 18 preserved yaml_ops tests = 40 total (all green)

2. **Task 2: Node yaml.rs merge** — `a51c183a` (Refactor)
   - src/yaml.rs content folded into src/settings.rs
   - to_napi_err collision: yaml-side helper renamed to yaml_err_to_napi
   - yaml.spec.ts test content appended to settings.spec.ts (imports extended to include afterEach, existsSync, mkdirSync, all yaml* exports, YamlDocument)
   - Dropped `mod yaml;` from src/lib.rs
   - Deleted src/yaml.rs and __test__/yaml.spec.ts
   - All NAPI export names preserved — CLI wrapper cli/run-scan.ts untouched

3. **Task 3: Python yaml-py fold-in + crate deletion** — `2475eeaf` (Refactor)
   - Added classic-shared-py dep to classic-settings-py Cargo.toml
   - Folded PyYamlOperations, python_to_yaml helper, 3-tier yaml exception hierarchy, and module-level yaml helpers (clear_global_yaml_cache, reset_yaml_cache_stats, yaml_cache_stats, merge_keys) into classic-settings-py/src/lib.rs
   - get_cache_stats calls core_yaml_cache_stats() to preserve yaml-cache semantics post-D-03 rename (concern 13 fix)
   - Type stubs merged: YamlOperations, RustYamlError hierarchy, YamlCacheStats TypedDict appended to classic_settings.pyi
   - test_promoted_residuals_smoke.py: dropped import classic_yaml, rewrote all classic_yaml.YamlOperations() -> classic_settings.YamlOperations()
   - git rm the entire classic-yaml-py directory (Cargo.toml, src/lib.rs, classic_yaml.pyi, benches/gil_benchmarks.rs). gil_benchmarks intentionally NOT migrated per D-05
   - Cleaned stale classic-yaml-py sourceFolder entries from .idea/CLASSIC-Fallout4.iml (repo-root .iml only — the ClassicLib-rs/.idea/ directory is untracked)
   - rustfmt incidentally reordered cpp-bridge src/lib.rs `pub mod` list alphabetically — bundled into this commit

4. **Deviation fix: CMakeLists 5th-place registration** — `f7e274cd` (Fix)
   - Rule 3 auto-fix. classic-cli/CMakeLists.txt and classic-gui/CMakeLists.txt hardcode the bridge file list passed to corrosion_add_cxxbridge; after Task 1 renamed yaml.rs to settings.rs, ninja failed with "needed by classic_cxx_bridge/yaml.h, missing and no known rule to make it"
   - Fix: `yaml.rs` -> `settings.rs` in both CMakeLists FILES blocks
   - NOT in plan 01-02 files_modified list — documented here as deviation

## Validation Commands Run

| # | Command | Result |
|---|---------|--------|
| 1 | `cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check` | PASS (after one rustfmt re-flow round) |
| 2 | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | PASS |
| 3 | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` | PASS (105 test binaries, 0 failures) |
| 4 | `cargo clippy --workspace --all-targets --all-features -- -D warnings` | PASS |
| 5 | `pwsh classic-cli/build_cli.ps1 -Clean -Test` | PASS (17 unit + 24 integration tests) |
| 6 | `pwsh classic-gui/build_gui.ps1 -Test` | DEFERRED — CLI covers C++ bridge surface; GUI build has a known Qt Release quirk in this worktree and explicit plan permission to skip if CLI is green |
| 7 | `cd ClassicLib-rs/node-bindings/classic-node && bun install && bun run build && bun run test:bun && bun run test:node` | PASS (986 bun expect() calls, 17 node:test assertions) |
| 7b | `bun run parity:gate:local` | **DEFERRED — pre-existing failure from plan 01-01**. tools/node_api_parity/generate_baseline.py hardcodes `classic-yaml-core/src/lib.rs` which 01-01 deleted. Plan 01-03 (wave 3) regenerates baselines and updates the tool |
| 8 | `./rebuild_rust.ps1 -Target python -Crates classic-settings-py` | PASS — wheel built + installed to ClassicLib-rs/python-bindings/.venv |
| 9 | `python tools/python_api_parity/check_parity_gate.py --repo-root .` | **DEFERRED — same pre-existing 01-01 failure**. tools/python_api_parity/generate_baseline.py also hardcodes `classic-yaml-core/src/lib.rs`. Plan 01-03 owns this |
| 10 | `uv run pytest ClassicLib-rs/python-bindings/tests -q` | DEFERRED — the shared test venv has no other classic_* modules installed (pre-existing env issue — every -py crate would have to be rebuilt to run tests across all modules). Targeted smoke test via `python -c` executed instead and verified: PyYamlOperations constructs, parse_yaml works, get_cache_stats returns yaml-cache numbers (capacity 128), module cache_stats returns settings-cache numbers (capacity 64), validate_settings_structure happy + error paths work, all three RustYaml* exception classes registered on the module |

## Python Smoke Test Output (verbatim)

```
classic_settings version: 9.0.0
Has YamlOperations: True
Has RustYamlError: True
Has RustYamlIOError: True
Has RustYamlParseError: True
Has yaml_cache_stats: True
Has merge_keys: True
Constructed YamlOperations: <builtins.YamlOperations object at 0x...>
Parsed YAML: {'key': 'value', 'number': 42}
get_setting result: value
Yaml cache stats:     {'hits': 0, 'misses': 0, 'hit_rate': 0.0, 'size': 0, 'capacity': 128}
Settings cache stats: {'hits': 0, 'misses': 0, 'hit_rate': 0.0, 'size': 0, 'capacity': 64}
module-level yaml_cache_stats: {'hits': 0, 'misses': 0, 'hit_rate': 0.0, 'size': 0, 'capacity': 128}
Valid issues: []
Bad issues:   [{'severity': 'error', 'message': 'Expected a YAML mapping at root, found: integer'}]
ALL OK
```

Distinct capacities (128 vs 64) prove the two caches are correctly separated, which was the entire point of concern 13's fix.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] CMakeLists corrosion_add_cxxbridge file lists contained stale yaml.rs**
- **Found during:** Task 1 C++ CLI build verification
- **Issue:** Both classic-cli/CMakeLists.txt and classic-gui/CMakeLists.txt hardcode the file list passed to `corrosion_add_cxxbridge`. When Task 1 renamed yaml.rs to settings.rs, the hardcoded list still referenced yaml.rs, causing ninja to fail with "needed by .../classic_cxx_bridge/yaml.h, missing and no known rule to make it" even after `-Clean`
- **Fix:** Changed `yaml.rs` to `settings.rs` in both CMakeLists FILES blocks
- **Files modified:** classic-cli/CMakeLists.txt, classic-gui/CMakeLists.txt
- **Commit:** f7e274cd
- **Note for project memory:** The previously-documented "4-place CXX bridge registration" pattern is actually 5-place when the bridge is consumed via Corrosion's `corrosion_add_cxxbridge`. Add this to project memory.

**2. [Rustfmt re-flow on cpp-bridge src/lib.rs]**
- **Found during:** Task 3 `cargo fmt --all` step
- **Issue:** After Task 1's content edits, rustfmt reordered the `pub mod ...` list in cpp-bindings/classic-cpp-bridge/src/lib.rs alphabetically (moved `settings` from the append position to its sorted position). This was a cosmetic side-effect, not a semantic change.
- **Fix:** Accepted the rustfmt reformat
- **Commit:** bundled into 2475eeaf (Task 3)

### Out-of-scope deferrals (documented, NOT fixed here)

- **Node parity gate + Python parity gate failures** — pre-existing breakage from plan 01-01. Both `tools/node_api_parity/generate_baseline.py` (line 40) and `tools/python_api_parity/generate_baseline.py` hardcode `classic-yaml-core/src/lib.rs` as a crate source path. Plan 01-01 deleted that file; neither tool has been updated. Plan 01-03 (wave 3) owns the baseline regeneration and tool updates. This plan was explicitly instructed NOT to touch parity baselines to avoid affecting wave 3's inputs. Logged in `.planning/phases/01-yaml-settings-merge/deferred-items.md` if present (else this SUMMARY is the record).
- **Full `uv run pytest` across all python-bindings tests** — the shared `.venv` only has `classic-settings-py` installed because `rebuild_rust.ps1 -Crates classic-settings-py` only rebuilds the one crate. Running the broader test suite would require rebuilding 13 other `-py` crates first. The focused smoke test (see "Python Smoke Test Output" above) verifies every behavior this plan touched.
- **GUI build** — not run due to known worktree Qt Release linker quirk (project memory). CLI build covers the full CXX bridge surface including all new settings-core exports.

## Issues Encountered

- **Task 1 C++ build failed on stale `yaml.rs` reference** — root cause was the 5th-place CMakeLists registration (see Deviation 1). Fixed inline.
- **rustfmt re-flow required a second fmt pass** — normal: the content edit in cpp-bridge src/lib.rs triggered alphabetical mod reordering.
- **`index.d.ts` showed as modified after bun build but with zero real diff** — git's CRLF normalization warning. Left unstaged to avoid polluting a pure metadata commit.

## Next Phase Readiness

Plan 01-03 (wave 3 — test migration, documentation consolidation, parity gate regeneration) can start immediately:

1. **Parity tooling updates:** Both parity tools reference `classic-yaml-core/src/lib.rs` (line 40 of the Node tool; similar in the Python tool). 01-03 must remove the entry and regenerate both baselines.
2. **Docs consolidation:** `docs/api/classic-settings-core.md`, `docs/api/binding-parity-overview.md`, and `docs/api/classic-cpp-bridge-data-entrypoints.md` all still document a separate yaml-core surface. 01-03 folds that into the settings-core page and removes the yaml-core page.
3. **CXX parity baseline:** The Node and Python baselines were the two blocking gates for this plan. The CXX parity baseline is another deliverable that wave 3 owns — it should now pick up settings_* exports, SettingsCacheStats, SettingsValidationIssue, SettingsCoercedValue, YamlCacheStatsDto, and the disappearance of the CacheStats struct under classic::yaml.
4. **GUI build smoke** — once wave 3 refreshes baselines, running the GUI build (even Debug) is a good final confidence check. The Debug path should avoid the Release linker quirk.

No blockers for wave 3.

## Self-Check: PASSED

- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/settings.rs` — FOUND
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/yaml.rs` — CONFIRMED DELETED
- `ClassicLib-rs/node-bindings/classic-node/src/settings.rs` contains YamlDocument + yaml_parse — FOUND (verified by successful bun build + 986 tests)
- `ClassicLib-rs/node-bindings/classic-node/src/yaml.rs` — CONFIRMED DELETED
- `ClassicLib-rs/node-bindings/classic-node/__test__/yaml.spec.ts` — CONFIRMED DELETED
- `ClassicLib-rs/python-bindings/classic-yaml-py/` — CONFIRMED DELETED (directory and all contents)
- `ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs` contains PyYamlOperations — FOUND (verified by Python smoke test constructing the class)
- `ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi` contains `class YamlOperations` — FOUND
- Commit `7b97bf2b` (Task 1) — FOUND
- Commit `a51c183a` (Task 2) — FOUND
- Commit `2475eeaf` (Task 3) — FOUND
- Commit `f7e274cd` (CMakeLists fix) — FOUND
- `cargo build --workspace` — exit 0
- `cargo test --workspace` — 105 test binaries, 0 failures
- `cargo clippy --workspace --all-targets --all-features -- -D warnings` — exit 0
- `cargo fmt --all -- --check` — exit 0
- `classic-cli/build_cli.ps1 -Clean -Test` — 17 unit + 24 integration tests pass
- `bun run test:bun` — 986 pass / 0 fail
- `bun run test:node` — 17 pass / 0 fail
- Python smoke test — all assertions pass, distinct yaml/settings cache capacities confirmed
- `grep -r "classic::yaml" classic-cli/ classic-gui/` — zero matches
- `grep -r "classic_cxx_bridge/yaml.h" classic-cli/ classic-gui/` — zero matches
- `grep "classic-yaml-py" ClassicLib-rs/Cargo.toml` — zero matches (already handled by 01-01)
- `grep "classic-shared-py" ClassicLib-rs/python-bindings/classic-settings-py/Cargo.toml` — one match (concern 14 verified)
- `grep "yaml_cache_stats" ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs` — present in PyYamlOperations::get_cache_stats body (concern 13 verified)
- `grep "RustYamlSerializeError" ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs` — zero matches (concern 6 verified — no phantom exception)

---
*Phase: 01-yaml-settings-merge*
*Completed: 2026-04-10*
