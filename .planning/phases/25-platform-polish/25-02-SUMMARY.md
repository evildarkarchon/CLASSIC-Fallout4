---
phase: 25-platform-polish
plan: 02
subsystem: infra
tags: [windows-subsystem, tauri-winres, manifest, dpi-awareness, static-crt, renderer-fallback, self-healing]

# Dependency graph
requires:
  - phase: 25-01
    provides: "File logging infrastructure, tracing macros, tauri-winres build-dep, renderer-software feature"
provides:
  - "Production-ready main() with 10-step startup sequence"
  - "Windows manifest with per-monitor-v2 DPI awareness"
  - "Embedded CLASSIC.ico in release .exe via tauri-winres"
  - "Static CRT linking for MSVC distribution builds"
  - "Skia-to-software renderer fallback chain"
  - "Self-healing startup for corrupted state/settings files"
  - "Console-less release build (windows_subsystem = windows)"
  - "Default 800x600 window size with off-screen position validation"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [renderer fallback via BackendSelector, self-healing with catch_unwind, crate-local .cargo/config.toml for static CRT]

key-files:
  created:
    - rust/ui-applications/classic-gui/assets/classic-gui.manifest
    - rust/ui-applications/classic-gui/.cargo/config.toml
  modified:
    - rust/ui-applications/classic-gui/build.rs
    - rust/ui-applications/classic-gui/src/main.rs
    - rust/ui-applications/classic-gui/src/state.rs
    - rust/ui-applications/classic-gui/src/lib.rs
    - .gitignore

key-decisions:
  - "Crate-local .cargo/config.toml for static CRT (scoped to GUI binary, not PyO3 crates)"
  - "catch_unwind wraps state/settings load for self-healing (normal parse errors already handled by unwrap_or_default)"
  - "Off-screen validation range: -200 to 10000 logical pixels"
  - "800x600 default window size when no saved geometry"
  - "Renderer fallback: Skia -> software -> exit(1)"

patterns-established:
  - "BackendSelector renderer fallback: try preferred, catch error, try fallback"
  - "Self-healing state load: catch_unwind + delete corrupted file + return defaults"
  - "Crate-local .cargo/config.toml for distribution-specific build flags"

# Metrics
duration: 9min
completed: 2026-02-06
---

# Phase 25 Plan 02: Windows Subsystem, Resource Embedding, and Production Startup Summary

**Console-less release build with embedded icon/manifest, Skia-to-software renderer fallback, self-healing state, and 800x600 default geometry**

## Performance

- **Duration:** 9 min
- **Started:** 2026-02-06T05:43:34Z
- **Completed:** 2026-02-06T05:53:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created Windows application manifest with per-monitor-v2 DPI awareness, Windows 10/11 compatibility, UTF-8 active code page, long path awareness
- Updated build.rs to embed CLASSIC.ico and manifest in release .exe via tauri-winres
- Added crate-local .cargo/config.toml for static CRT linking (eliminates VCRUNTIME140.dll dependency)
- Restructured main() into 10-step production startup sequence: logging -> renderer -> runtime -> self-healing state -> window -> restore -> callbacks -> init flag -> event loop -> save
- Added init_renderer() with Skia-to-software fallback chain using BackendSelector API
- Added load_state_with_healing() with catch_unwind for corrupted JSON/YAML files
- Default 800x600 window when no saved geometry; off-screen position validation (-200..10000 range)
- Console suppressed in release builds via windows_subsystem = "windows" attribute
- All 39 existing tests pass unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Create manifest, update build.rs, add static CRT config** - `c55d52a7` (feat)
2. **Task 2: Overhaul main() with logging, renderer fallback, self-healing, console suppression** - `3f049998` (feat)

## Files Created/Modified
- `rust/ui-applications/classic-gui/assets/classic-gui.manifest` - Windows manifest with PerMonitorV2 DPI, UTF-8, long path awareness
- `rust/ui-applications/classic-gui/.cargo/config.toml` - Crate-local static CRT linking for MSVC
- `rust/ui-applications/classic-gui/build.rs` - Embeds CLASSIC.ico and manifest via tauri-winres
- `rust/ui-applications/classic-gui/src/main.rs` - Production startup: logging, renderer fallback, self-healing, console suppression, default geometry
- `rust/ui-applications/classic-gui/src/state.rs` - Made state_file_path() public for self-healing access
- `rust/ui-applications/classic-gui/src/lib.rs` - Added state_file_path re-export
- `.gitignore` - Added exception for crate-local .cargo/config.toml

## Decisions Made
- Crate-local .cargo/config.toml for static CRT scoped only to GUI binary (not workspace-level, which would affect PyO3 crates)
- catch_unwind wraps load_window_state() and load_settings() for self-healing; normal parse errors already handled by existing .ok().unwrap_or_default() chains
- Off-screen position validation uses -200..10000 range to handle disconnected monitors while allowing slightly-off-screen window positions
- 800x600 default window size when no saved geometry exists (reasonable default per user decision)
- Renderer fallback chain: Skia -> software -> fatal exit. If both renderers fail, the log file captures the error before process::exit(1)
- Updated .gitignore to whitelist crate-local .cargo directory alongside existing workspace .cargo exception

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated .gitignore for crate-local .cargo/config.toml**
- **Found during:** Task 1 (creating .cargo/config.toml)
- **Issue:** .gitignore excluded all .cargo/ directories; the new crate-local config.toml was invisible to git
- **Fix:** Added `!rust/ui-applications/classic-gui/.cargo/` and `!rust/ui-applications/classic-gui/.cargo/config.toml` exceptions
- **Files modified:** .gitignore
- **Verification:** `git check-ignore` confirms file is no longer ignored
- **Committed in:** c55d52a7 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix -- without it the .cargo/config.toml would not be tracked in version control.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 25 Platform Polish is now complete (both plans done)
- The GUI is distribution-ready: console-less, logged, DPI-aware, self-healing, with embedded icon
- Release binary at 25.2 MB with static CRT (no runtime DLL dependencies)
- All 39 tests pass
- Ready for Phase 26 (AsyncBridge audit) or distribution

## Self-Check: PASSED

---
*Phase: 25-platform-polish*
*Completed: 2026-02-06*
