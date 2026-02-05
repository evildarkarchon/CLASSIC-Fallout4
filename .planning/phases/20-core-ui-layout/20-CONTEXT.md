# Phase 20: Core UI Layout - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Main window shell with layout, theming, and tabbed interface. Establishes visual foundation: title/icon, dark theme rendering, tab structure (Main Options / Results / Settings), and basic controls (buttons, inputs, checkboxes). Layout must handle window resizing gracefully.

Not in scope: Scan logic (Phase 21), results display (Phase 22), settings dialog content (Phase 24).

</domain>

<decisions>
## Implementation Decisions

### Window Appearance
- Title bar: "Crash Log Auto Scanner and Setup Integrity Checker v9.0.0" (full name with version)
- Default size: 800×600 (compact)
- State persistence: Yes — remember window position and size per-tab between sessions
- Resizing: Resizable with minimum floor (prevents layout breaking)

### Tab Organization
- Three tabs: Main Options, Results, Settings
- Tab position: Top horizontal bar (standard layout)
- Main Options content: Folder browsers + scan buttons (no game selector — Fallout 4 only currently)
- Default tab on launch: Main Options

### Theme & Colors
- Theme mode: Dark only (fluent-dark style, no light mode)
- Accent color: Windows blue (#0078D4)
- Visual hierarchy: Subtle contrast between panels/backgrounds
- Status colors: Standard semantic — red (errors), yellow (warnings), green (success)

### Control Layout
- Scan button: Bottom-center of Main Options tab
- Path inputs: Text field + Browse button (editable path with dialog)
- Option grouping: Labeled sections with headers (e.g., "Scan Options")

### Claude's Discretion
- Spacing density — balance readability with compact window size
- Minimum window dimensions (suggested: 640×480)
- Exact typography choices within Slint fluent-dark
- Panel/card border styling

</decisions>

<specifics>
## Specific Ideas

- Per-tab window state: If user resizes while on Results tab, that size persists separately from Main Options size
- No game selector yet — program only supports Fallout 4; game selection deferred until multi-game support added

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-core-ui-layout*
*Context gathered: 2026-02-05*
