# Phase 19: Foundation and Async Bridge - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Slint GUI crate setup with async Tokio integration. Application builds, launches, and demonstrates worker thread communication with UI thread via progress callbacks. This is the scaffold that all subsequent UI phases build upon.

</domain>

<decisions>
## Implementation Decisions

### Error Presentation
- Modal dialogs for async operation errors (blocking, ensures user sees error)
- Expandable details: simple user-friendly message with "Show details" button for technical info
- Context-dependent retry: offer retry button only for operations that make sense to retry (network failures yes, parse errors no)

### Progress Feedback Style
- Progress callbacks carry percentage + message ("45% — Scanning crash-2024-01-15.log")
- Update frequency: every item processed (most responsive)
- Operation-specific cancellation: some operations cancellable, others run to completion
- Visual: progress bar + status text below (e.g., "Processing 45 of 100 files...")

### Initial Window Content
- Full scaffold: tabs, buttons, empty results panel, progress area — complete shell
- Match current Python GUI dimensions for familiarity
- Full branding: CLASSIC icon and title in window title bar

### Claude's Discretion
- Error dialog severity levels (warning vs critical visual distinction)
- Specific throttling if UI updates cause performance issues
- Exact layout and spacing within the scaffold

</decisions>

<specifics>
## Specific Ideas

- Window should match current PySide6 interface dimensions — users should feel familiar
- Skeleton UI lets early testing catch layout issues before functionality is added
- Progress bar pattern from Phase 19 will be reused by Phase 21 (Scan Operations)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 19-foundation-and-async-bridge*
*Context gathered: 2026-02-05*
