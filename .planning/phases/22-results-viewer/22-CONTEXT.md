# Phase 22: Results Viewer - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

User can browse and view scan reports in the Results tab. This phase delivers the report list, search/filter, viewer panel, scrolling, and text copy. Markdown rendering is explicitly Phase 23 (RSLT-05) -- the viewer shows plain text initially.

</domain>

<decisions>
## Implementation Decisions

### Panel layout
- Side-by-side master-detail: report list on left, viewer on right
- Report list takes ~25% width (narrow list, maximize viewer space)
- Draggable splitter between list and viewer panels (user-resizable)
- Empty state (no reports): centered message with action button that switches to Main Options tab to start a scan

### Report list presentation
- Each row shows: report filename + timestamp
- Default sort: filename descending (naming convention embeds date-time, so this approximates newest-first)
- Clickable column header to toggle ascending/descending sort
- Selected report has highlighted row background (distinct from unselected)

### Search/filter behavior
- Search box placed at top of the list panel (scoped to list filtering)
- Instant filter as user types (no Enter required)
- Searches filenames only (not report content)
- Auto-select first report when list populates

### Viewer interaction
- Plain text display with monospace font (Phase 23 adds markdown formatting)
- Native text selection (click-drag + Ctrl+C) for partial copy
- "Copy All" button at top-right of viewer panel for full report clipboard copy
- Auto-select and display first report when list has items (no empty viewer state on load)
- Instant display -- no loading indicator (reports are small files)
- Scrollable viewer for long reports

### Claude's Discretion
- No-results behavior when search filter matches nothing (empty list vs dimming)
- Exact splitter widget implementation
- Monospace font choice and text sizing
- Scroll behavior details (scroll position reset on report switch, etc.)
- "Copy All" button styling and feedback (e.g., brief "Copied!" text)

</decisions>

<specifics>
## Specific Ideas

- Sort by filename descending because timestamp-based sorting has been unreliable historically -- the standard naming convention includes a date-time stamp in the filename, making alphabetical sort a reliable proxy for chronological
- Empty state should actively prompt the user to scan, not just inform -- include a button that navigates to Main Options tab

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 22-results-viewer*
*Context gathered: 2026-02-05*
