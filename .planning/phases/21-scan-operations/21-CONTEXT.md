# Phase 21: Scan Operations - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

User can trigger, monitor, and cancel crash log scans through the GUI. This phase wires the existing OrchestratorCore business logic to UI controls with real-time progress feedback. Report viewing and settings management are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Scan Initiation
- Scan button always enabled — F4SE directory is auto-detected, optional secondary path configurable
- Only error case: no logs found at all (no paths to validate upfront)
- Scan button transforms into Cancel button during scan (single button, dual purpose)
- Stay on Main Options tab during scan — user controls navigation
- Immediate progress display on click (no "Starting..." state)

### Progress Visualization
- Progress bar shows percentage + current filename being scanned
- Progress appears in status bar area at bottom of window (visible across all tabs)
- Indeterminate animation while discovering/enumerating logs, then switch to determinate progress
- Status bar auto-clears after delay when scan completes

### Cancellation Behavior
- No confirmation dialog — cancel immediately on click
- Keep partial results — reports from completed logs are preserved
- Status shows 'Cancelled (X of Y logs)' message indicating progress achieved
- Button reverts to 'Scan' immediately after cancel processes

### Completion Summary
- Status bar shows count only (e.g., 'Scanned 12 logs')
- Auto-switch to Results tab on successful completion
- Zero logs: 'No crash logs found' in status bar, stay on Main Options (no auto-switch)
- Errors included in count: 'Scanned 10 logs (2 errors)'

### Claude's Discretion
- Exact status bar clear delay timing
- Status bar styling and animation details
- Indeterminate → determinate transition smoothness
- Button state transition animations

</decisions>

<specifics>
## Specific Ideas

- Button morphing (Scan ↔ Cancel) should feel like a single unified control
- Status bar is the consistent feedback channel — stays visible regardless of active tab
- Auto-switch to Results only on successful scan with results (not on cancel or zero logs)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 21-scan-operations*
*Context gathered: 2026-02-05*
