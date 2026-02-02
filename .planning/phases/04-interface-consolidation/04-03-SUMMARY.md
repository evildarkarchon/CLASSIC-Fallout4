---
phase: 04-interface-consolidation
plan: 03
subsystem: io
tags: [yaml, sync, module-structure, imports]

# Dependency graph
requires:
  - phase: 04-02
    provides: sync_adapters and bridge_helpers removed, AsyncBridge as sole sync pattern
provides:
  - YAML sync/ subdirectory eliminated -- cache.py and convenience.py at yaml/ level
  - Phase 4 interface consolidation complete (all 3 plans done)
affects: [05-fallback-pruning]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Flat module layout: yaml/cache.py and yaml/convenience.py instead of yaml/sync/ subpackage"

key-files:
  created:
    - ClassicLib/io/yaml/cache.py
    - ClassicLib/io/yaml/convenience.py
  modified:
    - ClassicLib/io/yaml/__init__.py
    - ClassicLib/support/resources.py
    - tests/fixtures/singleton_fixtures.py
    - tests/core/test_resource_loader_unit.py
    - tests/yaml/test_yaml_sync_wrapper_unit.py
    - tests/yaml/test_yaml_cache_unit.py
    - tests/yaml/test_yaml_batch_operations_unit.py

key-decisions:
  - "No internal import changes needed in cache.py (already used absolute paths to async_ and types)"
  - "GUI smoke test revealed pre-existing file path resolution bug (not a Phase 4 regression)"

patterns-established:
  - "Flat yaml/ layout: sync convenience functions live alongside async_ submodule, not in nested sync/ subpackage"

# Metrics
duration: 8min
completed: 2026-02-02
---

# Phase 4 Plan 3: YAML Sync Directory Consolidation Summary

**Eliminated yaml/sync/ subdirectory -- cache.py and convenience.py moved to yaml/ level, completing Phase 4 interface consolidation**

## Performance

- **Duration:** ~8 min (execution) + checkpoint pause for GUI verification
- **Started:** 2026-02-02
- **Completed:** 2026-02-02
- **Tasks:** 2 (1 auto + 1 checkpoint)
- **Files modified:** 10 (3 deleted, 2 created, 5 updated)

## Accomplishments

- Moved YamlSettingsCache from yaml/sync/cache.py to yaml/cache.py
- Moved yaml_settings, classic_settings, yaml_cache from yaml/sync/convenience.py to yaml/convenience.py
- Deleted yaml/sync/ directory entirely (3 files: __init__.py, cache.py, convenience.py)
- Updated all 7 files with direct sync submodule imports (production and test code)
- GUI smoke test confirmed AsyncBridge chain works correctly through moved files
- All 1885 tests pass (1 pre-existing flaky performance benchmark excluded)

## Task Commits

Each task was committed atomically:

1. **Task 1: Move sync files to parent yaml/ directory and update imports** - `51c99b6f` (feat)
2. **Task 2: GUI smoke test verification** - checkpoint approved (no commit, verification only)

## Files Created/Modified

- `ClassicLib/io/yaml/cache.py` - YamlSettingsCache singleton (moved from sync/cache.py)
- `ClassicLib/io/yaml/convenience.py` - yaml_settings, classic_settings, yaml_cache (moved from sync/convenience.py)
- `ClassicLib/io/yaml/__init__.py` - Updated imports from new locations
- `ClassicLib/io/yaml/sync/` - Deleted entirely (cache.py, convenience.py, __init__.py)
- `ClassicLib/support/resources.py` - Updated direct import path
- `tests/fixtures/singleton_fixtures.py` - Updated direct import path
- `tests/core/test_resource_loader_unit.py` - Updated mock paths (6 occurrences)
- `tests/yaml/test_yaml_sync_wrapper_unit.py` - Mock path auto-updated
- `tests/yaml/test_yaml_cache_unit.py` - Mock path auto-updated
- `tests/yaml/test_yaml_batch_operations_unit.py` - Mock path auto-updated

## Decisions Made

- **No internal import changes in cache.py**: The file already used absolute imports to `ClassicLib.io.yaml.async_.core` and `ClassicLib.io.yaml.types`, so moving it up one directory required zero internal changes.
- **convenience.py single import fix**: Only one import needed updating (`from ClassicLib.io.yaml.sync.cache` to `from ClassicLib.io.yaml.cache`).
- **GUI smoke test observation**: The GUI revealed a pre-existing file path resolution issue with CLASSIC Settings.yaml that is unrelated to Phase 4 changes. The async chain through the moved files (convenience.py -> cache.py -> AsyncBridge -> async core) works correctly without deadlock.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Pre-existing GUI issue**: The GUI smoke test showed a file path resolution error when creating CLASSIC Settings.yaml. This is a pre-existing bug in `classic_settings()` that uses `Path("CLASSIC Settings.yaml")` (relative path) rather than resolving against the application directory. Not a regression from Phase 4 -- the same code existed before the move. The async chain through the moved files functions correctly.
- **Pre-existing flaky test**: `test_detect_mods_scaling` performance benchmark fails intermittently. Unrelated to Phase 4 changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 4 (Interface Consolidation) is now complete. All 3 plans executed:
- 04-01: FormIDAnalyzer.py sync wrapper removed
- 04-02: create_sync_wrapper, bridge_helpers.py, sync_adapters.py removed
- 04-03: YAML sync/ directory consolidated

The codebase now has exactly two async patterns:
1. **Native async** (CLI/TUI) - direct `await` calls
2. **AsyncBridge** (GUI) - `AsyncBridge.run_async()` for sync-to-async bridging

Ready for Phase 5 (Fallback Pruning). Reminder: Phase 5 requires PyInstaller build verification before and after changes.

---
*Phase: 04-interface-consolidation*
*Completed: 2026-02-02*
