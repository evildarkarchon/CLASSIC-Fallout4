---
phase: 01-yaml-settings-merge
plan: 01
subsystem: infra
tags: [rust, workspace, refactor, yaml, settings, crate-merge, cxx, napi]

# Dependency graph
requires: []
provides:
  - classic_settings_core::YamlOperations, YamlError, YamlCacheStats, yaml_cache_stats, reset_yaml_cache_stats, clear_global_yaml_cache, merge_keys re-exports
  - Absorbed yaml-core source, tests, and benches with preserved git blame history
  - Rust workspace buildable with classic-yaml-core removed and classic-yaml-py out of members
affects: [01-02-PLAN, 01-03-PLAN, binding parity gates]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Crate merge pattern: git mv first for blame, then content edits + consumer migration in a second commit"
    - "Prefix-rename collisions on merge (CacheStats -> YamlCacheStats, cache_stats -> yaml_cache_stats, reset_cache_stats -> reset_yaml_cache_stats)"
    - "Temporary workspace member removal to preserve buildability when a path dep is deleted while the dependent crate directory lives on"

key-files:
  created:
    - ClassicLib-rs/business-logic/classic-settings-core/src/yaml_ops.rs
    - ClassicLib-rs/business-logic/classic-settings-core/src/yaml_merge.rs
    - ClassicLib-rs/business-logic/classic-settings-core/tests/yaml_integration_tests.rs
    - ClassicLib-rs/business-logic/classic-settings-core/tests/yaml_dead_code_audit.rs
    - ClassicLib-rs/business-logic/classic-settings-core/benches/yaml_benchmarks.rs
  modified:
    - ClassicLib-rs/Cargo.toml
    - ClassicLib-rs/business-logic/classic-settings-core/src/lib.rs
    - ClassicLib-rs/business-logic/classic-settings-core/Cargo.toml
    - ClassicLib-rs/business-logic/classic-config-core/Cargo.toml
    - ClassicLib-rs/business-logic/classic-config-core/src/lib.rs
    - ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs
    - ClassicLib-rs/business-logic/classic-config-core/src/config.rs
    - ClassicLib-rs/business-logic/classic-version-registry-core/Cargo.toml
    - ClassicLib-rs/business-logic/classic-version-registry-core/src/registry.rs
    - ClassicLib-rs/business-logic/classic-version-registry-core/src/error.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/yaml.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs
    - ClassicLib-rs/node-bindings/classic-node/Cargo.toml
    - ClassicLib-rs/node-bindings/classic-node/src/yaml.rs
    - ClassicLib-rs/.idea/ClassicLib-rs.iml
    - ClassicLib-rs/.idea/workspace.xml
    - .idea/CLASSIC-Fallout4.iml
  deleted:
    - ClassicLib-rs/business-logic/classic-yaml-core/ (directory)

key-decisions:
  - "Task 1 is rename-only (pure git mv) to preserve blame via git log --follow"
  - "Task 2 coordinates content edits, consumer migration, yaml-core deletion, and yaml-py workspace-member removal in a single compile-green commit"
  - "classic-yaml-py stays on disk but is dropped from workspace members to keep cargo build --workspace green through Wave 1; deletion deferred to plan 01-02"
  - "CacheStats/cache_stats/reset_cache_stats from yaml-core renamed to YamlCacheStats/yaml_cache_stats/reset_yaml_cache_stats to avoid collision with settings-core cache API (D-03)"

patterns-established:
  - "Crate absorption workflow: (1) git mv rename commit, (2) coordinated content-edit commit, (3) end wave with workspace buildable"

requirements-completed: [YAML-01, YAML-02, YAML-03]

# Metrics
duration: ~45 min
completed: 2026-04-11
---

# Phase 01 Plan 01: YAML -> Settings Merge (Rust core) Summary

**classic-yaml-core absorbed into classic-settings-core with blame-preserving git mv, D-03 CacheStats prefix-rename, and all workspace consumers (config-core, version-registry-core, scanlog-core, cpp-bridge, classic-node) migrated; workspace builds, settings-core tests pass, benches compile, clippy and fmt clean.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2 (both atomic commits)
- **Files modified:** 24 in Task 2 commit + 5 renames in Task 1 commit
- **Commits:** 2 task commits + 1 metadata commit (pending)

## Accomplishments

- All public API of classic-yaml-core (YamlOperations, YamlError, YamlCacheStats, yaml_cache_stats, reset_yaml_cache_stats, clear_global_yaml_cache, merge_keys) re-exported from classic_settings_core with preserved semantics.
- Source, integration tests, dead-code audit test, and criterion benchmark migrated via `git mv` so `git log --follow` walks through original yaml-core history.
- Every workspace consumer (classic-config-core, classic-version-registry-core, classic-scanlog-core, classic-cpp-bridge, classic-node) now pulls from classic_settings_core; the classic-yaml-core crate directory is deleted and the workspace member list no longer contains classic-yaml-core or classic-yaml-py.
- `cargo build --workspace`, `cargo test -p classic-settings-core`, `cargo bench -p classic-settings-core --no-run`, `cargo clippy --workspace --all-targets --all-features -- -D warnings`, and `cargo fmt --all -- --check` all exit 0.
- IntelliJ `.iml` and `.idea/workspace.xml` entries for yaml-core removed (both ClassicLib-rs/.idea and repo-root .idea); new `classic-settings-core/tests` + `classic-settings-core/benches` source folders added to ClassicLib-rs.iml.

## Task Commits

1. **Task 1: git mv yaml-core into settings-core** — `3276fd20` (Refactor) — 5 file renames, 0 content edits
2. **Task 2: content edits, dep absorption, consumer migration, yaml-core removal** — `ec596e0e` (Refactor) — 24 files changed, 103 insertions, 161 deletions

**Plan metadata commit:** pending (SUMMARY + STATE + ROADMAP)

## Files Created/Modified

### Created (via git mv — history preserved)
- `ClassicLib-rs/business-logic/classic-settings-core/src/yaml_ops.rs` — YamlOperations, YamlError, YamlCacheStats, yaml_cache_stats, reset_yaml_cache_stats, clear_global_yaml_cache, YAML_CACHE (formerly classic-yaml-core/src/lib.rs)
- `ClassicLib-rs/business-logic/classic-settings-core/src/yaml_merge.rs` — merge_keys (formerly classic-yaml-core/src/merge.rs)
- `ClassicLib-rs/business-logic/classic-settings-core/tests/yaml_integration_tests.rs`
- `ClassicLib-rs/business-logic/classic-settings-core/tests/yaml_dead_code_audit.rs`
- `ClassicLib-rs/business-logic/classic-settings-core/benches/yaml_benchmarks.rs`

### Modified
- `ClassicLib-rs/Cargo.toml` — removed `business-logic/classic-yaml-core` and `python-bindings/classic-yaml-py` from members
- `ClassicLib-rs/business-logic/classic-settings-core/src/lib.rs` — declared `yaml_merge`/`yaml_ops` modules and added flat re-exports
- `ClassicLib-rs/business-logic/classic-settings-core/Cargo.toml` — added indexmap, serde_json, criterion dev-dep, `[[bench]] yaml_benchmarks`
- `ClassicLib-rs/business-logic/classic-settings-core/src/yaml_ops.rs` — module doc refresh, CacheStats→YamlCacheStats rename, dropped `mod merge;` + `pub use merge::merge_keys;`
- `ClassicLib-rs/business-logic/classic-settings-core/tests/yaml_integration_tests.rs` — rewrote imports + call sites for settings-core + renamed stats helpers
- `ClassicLib-rs/business-logic/classic-settings-core/tests/yaml_dead_code_audit.rs` — fixed `include_str!` to point at `../src/yaml_ops.rs` and `yaml_integration_tests.rs`, cosmetic crate name in assertion
- `ClassicLib-rs/business-logic/classic-settings-core/benches/yaml_benchmarks.rs` — rewrote import to settings-core
- `ClassicLib-rs/business-logic/classic-config-core/{Cargo.toml, src/lib.rs, src/yamldata.rs, src/config.rs}` — dropped yaml-core dep, imports flipped to settings-core
- `ClassicLib-rs/business-logic/classic-version-registry-core/{Cargo.toml, src/registry.rs, src/error.rs}` — added settings-core dep, imports flipped
- `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml` — removed yaml-core dep line (no source usage)
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/{Cargo.toml, src/yaml.rs, src/scanner.rs, src/config.rs}` — dropped yaml-core dep, imports flipped, alias `CacheStats as YamlCacheStats` collapsed per D-03
- `ClassicLib-rs/node-bindings/classic-node/{Cargo.toml, src/yaml.rs}` — same pattern
- `ClassicLib-rs/.idea/ClassicLib-rs.iml` — removed 3 yaml-core sourceFolder entries, added settings-core tests/benches entries
- `ClassicLib-rs/.idea/workspace.xml` — removed yaml-core `<package>` entry
- `.idea/CLASSIC-Fallout4.iml` — removed 4 stale yaml-core sourceFolder entries

### Deleted
- `ClassicLib-rs/business-logic/classic-yaml-core/` — entire directory (Cargo.toml plus any leftover empty dirs after rename)

## Decisions Made

- **Task-1 rename-only commit for blame preservation** — splitting the rename from content edits keeps `git log --follow` walking through the original yaml-core commits.
- **Drop classic-yaml-py from workspace members, not disk** — yaml-py still declares `classic-yaml-core` as a path dep. Dropping it from members is enough to keep `cargo build --workspace` green at Wave 1's boundary while leaving the directory for plan 01-02 to fold into classic-settings-py.
- **Collapse cpp-bridge/node `CacheStats as YamlCacheStats` alias** — after D-03 the exported name is already `YamlCacheStats`, so the `use ... as ...` alias becomes redundant.

## Deviations from Plan

None — plan executed exactly as written. The only minor adjustments were:
- The consolidated `use classic_settings_core::{YamlOperations, load_yaml_merged_async};` form in classic-config-core/src/config.rs (vs. two separate `use` lines) — this is a cleaner form that rustfmt then re-ordered; functionally identical to what the plan described.
- Created `tests/` and `benches/` directories under classic-settings-core via explicit `mkdir -p` before `git mv`, because Windows git's similarity detection did not auto-create the parent directories (the plan predicted git would, but on Windows it didn't). No content impact.

## Issues Encountered

- **Fmt check initially showed diff after content edits** — resolved by running `cargo fmt --all` (rustfmt re-sorted `use` lines). This is the normal fmt round trip and not a semantic issue.
- **PowerShell-in-Bash quoting** — Windows PowerShell invocations with inline `$var` expressions conflicted with Bash variable expansion; switched to script-file invocation pattern for the few in-place text rewrites.

## Next Phase Readiness

Plan 01-02 (wave 2) can start immediately:
- `classic-yaml-py/` still on disk with source intact — ready to be folded into `classic-settings-py`.
- `cpp-bindings/classic-cpp-bridge/src/yaml.rs` now uses `classic_settings_core::{YamlCacheStats, YamlOperations, yaml_cache_stats}`; wave 2 can rename the bridge module (`yaml_ops` → `settings_ops`?) as D-02 dictates.
- CXX and Node parity-artifact JSON files still contain stale yaml-core references; wave 3 regenerates them.
- Node binary `classic-node.win32-x64-msvc.node` still contains stale yaml-core strings (it's a build artifact) — wave 2/3 rebuild will refresh it.

No blockers.

## Self-Check: PASSED

- `ClassicLib-rs/business-logic/classic-settings-core/src/yaml_ops.rs` — FOUND
- `ClassicLib-rs/business-logic/classic-settings-core/src/yaml_merge.rs` — FOUND
- `ClassicLib-rs/business-logic/classic-settings-core/tests/yaml_integration_tests.rs` — FOUND
- `ClassicLib-rs/business-logic/classic-settings-core/tests/yaml_dead_code_audit.rs` — FOUND
- `ClassicLib-rs/business-logic/classic-settings-core/benches/yaml_benchmarks.rs` — FOUND
- Commit `3276fd20` — FOUND (Task 1 rename)
- Commit `ec596e0e` — FOUND (Task 2 content)
- `ClassicLib-rs/business-logic/classic-yaml-core/` — CONFIRMED DELETED
- `cargo build --workspace` — exit 0
- `cargo test -p classic-settings-core` — 171 + 1 + 13 passing, 0 failed
- `cargo bench -p classic-settings-core --no-run` — exit 0
- `cargo clippy --workspace --all-targets --all-features -- -D warnings` — exit 0
- `cargo fmt --all -- --check` — exit 0

---
*Phase: 01-yaml-settings-merge*
*Completed: 2026-04-11*
