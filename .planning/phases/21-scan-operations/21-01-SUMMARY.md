---
phase: 21-scan-operations
plan: 01
subsystem: gui
tags: [slint, orchestrator, scanlog, logcollector, async, progress, cancellation]

# Dependency graph
requires:
  - phase: 19-02
    provides: AsyncBridge wiring, worker pattern, ScanWindowProperties trait
  - phase: 20-02
    provides: State persistence, path inputs, browse dialogs
provides:
  - Real crash log scanning via OrchestratorCore
  - LogCollector-based log discovery
  - Morphing Scan/Cancel button
  - Indeterminate/determinate progress transition
  - Auto-switch to Results tab on completion
  - Status bar auto-clear after delay
affects: [22-results-display, 24-settings]

# Tech tracking
tech-stack:
  added:
    - classic-scanlog-core (OrchestratorCore, AnalysisConfig, AnalysisResult)
    - classic-file-io-core (LogCollector)
  patterns:
    - scan_crash_logs async orchestration (discovery + analysis phases)
    - ScanResult with format_status for UI display
    - Morphing button via Slint conditional text/action
    - Indeterminate progress via negative value convention
    - Auto-clear status with spawn_background timer

key-files:
  created:
    - rust/ui-applications/classic-gui/src/scan.rs
  modified:
    - rust/ui-applications/classic-gui/Cargo.toml
    - rust/ui-applications/classic-gui/src/lib.rs
    - rust/ui-applications/classic-gui/ui/main.slint
    - rust/ui-applications/classic-gui/src/main.rs

key-decisions:
  - "Morphing single button replaces separate Scan and Cancel buttons per CONTEXT.md"
  - "Negative progress value (-1.0) signals indeterminate mode to ProgressIndicator"
  - "OrchestratorCore created per scan with minimal AnalysisConfig (full config deferred to Phase 24)"
  - "5-second auto-clear delay for status bar after scan completes"
  - "Auto-switch to Results tab only on success with results (not cancel or zero logs)"

patterns-established:
  - "Scan orchestration: LogCollector discovery -> OrchestratorCore analysis loop"
  - "Progress convention: -1.0 = indeterminate, 0-100 = determinate percentage"
  - "ScanResult struct with format_status() for consistent status messages"

# Metrics
duration: 6min
completed: 2026-02-06
---

# Phase 21 Plan 01: Scan Operations Summary

**Real OrchestratorCore crash log analysis wired to morphing Scan/Cancel button with indeterminate/determinate progress**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-06T00:04:02Z
- **Completed:** 2026-02-06T00:09:59Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Replaced simulate_scan placeholder with real OrchestratorCore crash log analysis
- LogCollector discovers crash logs from configured base folder
- Single morphing button toggles between "Scan Crash Logs" and "Cancel"
- Indeterminate progress animation during discovery, determinate percentage during analysis
- Auto-switch to Results tab on successful scan completion

## Task Commits

Each task was committed atomically:

1. **Task 1: Add business logic dependencies** - `e68c1a7e` (chore)
2. **Task 2: Create scan module with OrchestratorCore integration** - `92e9bd6c` (feat)
3. **Task 3: Update UI for morphing button and wire scan callback** - `9c9b066d` (feat)

## Files Created/Modified
- `rust/ui-applications/classic-gui/Cargo.toml` - Added classic-scanlog-core and classic-file-io-core dependencies
- `rust/ui-applications/classic-gui/src/scan.rs` - Scan orchestration with LogCollector and OrchestratorCore
- `rust/ui-applications/classic-gui/src/lib.rs` - Export scan module and types
- `rust/ui-applications/classic-gui/ui/main.slint` - Morphing button, indeterminate progress support
- `rust/ui-applications/classic-gui/src/main.rs` - Wire scan_crash_logs, auto-switch, auto-clear

## Decisions Made
- **Morphing button:** Single button with conditional text/action per CONTEXT.md decision, replacing separate Scan and Cancel buttons
- **Negative progress convention:** -1.0 signals indeterminate mode to ProgressIndicator (Slint `indeterminate` property bound to `scan-progress < 0`)
- **Minimal AnalysisConfig:** Created per-scan with `AnalysisConfig::new("Fallout4", false)` -- full YAML-based configuration deferred to Phase 24 (Settings)
- **5-second auto-clear:** Status bar clears after 5 seconds post-completion via `AsyncBridge::spawn_background` timer
- **Conditional auto-switch:** Results tab only on success with non-empty results, not on cancel or "no logs found"

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Scan orchestration complete and functional
- OrchestratorCore runs with minimal config (basic analysis without suspect patterns or mod databases)
- Full analysis configuration (YAML settings, suspect patterns, mod databases) requires Phase 24 (Settings)
- Results storage for Phase 22 (Results Display) will need Vec<AnalysisResult> passed from scan completion
- worker.rs with simulate_scan preserved for reference (future cleanup)

---
*Phase: 21-scan-operations*
*Completed: 2026-02-06*
