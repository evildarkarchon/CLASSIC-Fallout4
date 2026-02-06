---
phase: 25-platform-polish
plan: 01
subsystem: infra
tags: [tracing, logging, tracing-appender, renderer-software, tauri-winres]

# Dependency graph
requires:
  - phase: 24-settings-dialog
    provides: "GUI application with settings persistence and eprintln! calls"
provides:
  - "File logging infrastructure via tracing-appender"
  - "All eprintln! replaced with tracing::warn! macros"
  - "renderer-software Slint fallback feature"
  - "tauri-winres build dependency for Windows resource embedding"
affects: [25-02-windows-subsystem]

# Tech tracking
tech-stack:
  added: [tracing-appender 0.2, tauri-winres 0.3, tracing-subscriber fmt]
  patterns: [file-based logging with WorkerGuard lifetime, tracing macros for structured logging]

key-files:
  created:
    - rust/ui-applications/classic-gui/src/logging.rs
  modified:
    - rust/Cargo.toml
    - rust/ui-applications/classic-gui/Cargo.toml
    - rust/ui-applications/classic-gui/src/lib.rs
    - rust/ui-applications/classic-gui/src/main.rs
    - rust/ui-applications/classic-gui/src/settings.rs

key-decisions:
  - "tracing::warn! for all eprintln! replacements (non-fatal save/load errors, not application errors)"
  - "Log file truncated on each launch (fresh start, not appended)"
  - "data_dir() for log location (logs are data, not config)"

patterns-established:
  - "WorkerGuard pattern: init_logging() returns guard that must be held for app lifetime"
  - "tracing macros for all diagnostic output (no eprintln! in GUI crate)"

# Metrics
duration: 7min
completed: 2026-02-06
---

# Phase 25 Plan 01: File Logging & eprintln! Replacement Summary

**File logging via tracing-appender with WorkerGuard, all 12 eprintln! calls replaced with tracing::warn!, renderer-software fallback added**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-06T05:34:06Z
- **Completed:** 2026-02-06T05:41:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Created logging.rs module with init_logging() returning WorkerGuard for app-lifetime file logging
- Replaced all 12 eprintln! calls (10 in main.rs, 2 in settings.rs) with tracing::warn! macros
- Added renderer-software as secondary GPU fallback path in Slint features
- Added tauri-winres build dependency (needed by Plan 02 for Windows resource embedding)
- All 39 existing tests pass unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Add dependencies and create logging module** - `4bdf1ba5` (feat)
2. **Task 2: Replace all eprintln! calls with tracing macros** - `33375b89` (feat)

## Files Created/Modified
- `rust/ui-applications/classic-gui/src/logging.rs` - File logging initialization with tracing-appender, non-blocking writer, WorkerGuard
- `rust/Cargo.toml` - Added tracing-appender workspace dependency
- `rust/ui-applications/classic-gui/Cargo.toml` - Added tracing/tracing-subscriber/tracing-appender deps, renderer-software feature, tauri-winres build-dep
- `rust/ui-applications/classic-gui/src/lib.rs` - Registered logging module and re-export
- `rust/ui-applications/classic-gui/src/main.rs` - Replaced 10 eprintln! with tracing::warn!
- `rust/ui-applications/classic-gui/src/settings.rs` - Replaced 2 eprintln! with tracing::warn!

## Decisions Made
- Used tracing::warn! for all replacements (these are non-fatal recovery paths, not errors)
- Log file is truncated on each launch via fs::File::create() before rolling::never() appender
- Log directory uses data_dir() (not config_dir) since logs are data, not configuration
- Falls back to current working directory if ProjectDirs returns None

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Logging infrastructure ready for Plan 02 to add windows_subsystem = "windows" attribute
- tauri-winres build dependency in place for Windows resource embedding (Plan 02)
- All stderr output captured to file, safe for console-less Windows distribution
- init_logging() ready to be called at top of main() (Plan 02 wiring)

## Self-Check: PASSED

---
*Phase: 25-platform-polish*
*Completed: 2026-02-06*
