---
phase: 04-bounded-cache-replacement
plan: 06
subsystem: api
tags: [cxx, cache-stats, bindings, rust, docs]
requires:
  - phase: 04-01
    provides: canonical YAML CacheStats contract and bounded cache behavior
  - phase: 04-02
    provides: canonical settings CacheStats contract and reset helpers
  - phase: 04-03
    provides: canonical hash CacheStats contract and bounded cache behavior
provides:
  - explicit C++ cache stats helpers for YAML, settings, and hash caches
  - CXX-safe CacheStats DTOs for classic::yaml, classic::config, and classic::files
  - contributor docs clarifying that Phase 4 closed C++ cache observability gaps
affects: [classic-cpp-bridge, classic-gui, bindings, docs]
tech-stack:
  added: []
  patterns: [thin CXX cache DTO adapters, cache-size-as-stats adapter, binding parity documentation]
key-files:
  created: []
  modified:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/yaml.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/files.rs
    - docs/api/classic-cpp-bridge-data-entrypoints.md
    - docs/api/binding-parity-overview.md
key-decisions:
  - "Keep C++ cache logic thin by forwarding Rust core CacheStats into CXX-safe DTOs instead of reimplementing observability in the bridge."
  - "Preserve existing *_cache_size helpers as compatibility adapters over the canonical five-field cache stats contract."
patterns-established:
  - "C++ bridge cache observability should expose explicit stats/reset helpers per namespace while keeping cache semantics in Rust core crates."
  - "Binding parity docs should call out when C++ gains explicit cache stats coverage so contributors do not infer stale parity gaps."
requirements-completed: [CONS-03]
duration: 11min
completed: 2026-04-06
---

# Phase 04 Plan 06: C++ Cache Stats Surface Summary

**C++ bridge cache stats entrypoints for YAML, settings, and hashes with matching parity docs across the active binding surfaces.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-06T04:42:00Z
- **Completed:** 2026-04-06T04:53:09Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added explicit `classic::yaml`, `classic::config`, and `classic::files` cache stats helpers that forward the canonical Rust `CacheStats` contract into CXX-safe DTOs.
- Preserved older C++ size helpers as thin adapters over the new stats surface instead of introducing parallel cache-count contracts.
- Updated the C++ bridge and parity overview docs so contributors can see that Phase 4 closed cache stats visibility gaps for C++ alongside Node and Python.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add explicit C++ cache stats entrypoints for YAML, settings, and hashes** - `0dbefcc9` (feat)
2. **Task 2: Document the new C++ cache stats surface and parity position** - `433f6a80` (docs)

**Plan metadata:** pending

## Files Created/Modified
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml` - Added the missing `classic-settings-core` dependency required for the new `classic::config` settings cache helpers.
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/yaml.rs` - Added the CXX-safe `CacheStats` DTO plus `yaml_ops_cache_stats()` and a stats-backed `yaml_ops_cache_size()` adapter.
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` - Added `settings_cache_clear()`, `settings_cache_stats()`, `settings_cache_size()`, and `reset_settings_cache_stats()` plus bridge coverage tests.
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/files.rs` - Added `hash_cache_clear()`, `hash_cache_stats()`, `hash_cache_size()`, and `reset_hash_cache_stats()` plus bridge coverage tests.
- `docs/api/classic-cpp-bridge-data-entrypoints.md` - Documented the new cache stats helpers and the namespace ownership split across `classic::yaml`, `classic::config`, and `classic::files`.
- `docs/api/binding-parity-overview.md` - Updated parity notes to state that cache stats coverage now exists across C++, Node, and Python for Phase 4.

## Decisions Made
- Kept the bridge layer adapter-only: cache stats are computed in Rust core crates and only reshaped for CXX transport.
- Kept legacy `*_cache_size` helpers as compatibility shims over the canonical stats DTO instead of removing them mid-phase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing `classic-settings-core` bridge dependency**
- **Found during:** Task 1 (Add explicit C++ cache stats entrypoints for YAML, settings, and hashes)
- **Issue:** `classic-cpp-bridge` did not depend on `classic-settings-core`, so the new `classic::config` cache helpers could not compile.
- **Fix:** Added `classic-settings-core` to `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml` and completed the settings cache forwarders.
- **Files modified:** `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml`, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs`
- **Verification:** `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml --lib`; `cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml`
- **Committed in:** `0dbefcc9`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The dependency fix was required to complete the planned C++ settings cache surface; no broader architecture change was introduced.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 4 now has explicit cache stats coverage across all three binding surfaces for YAML, settings, and hash caches.
- Downstream C++ frontend work can consume the new bridge helpers without adding new cache semantics outside Rust core.

## Self-Check: PASSED

---
*Phase: 04-bounded-cache-replacement*
*Completed: 2026-04-06*
