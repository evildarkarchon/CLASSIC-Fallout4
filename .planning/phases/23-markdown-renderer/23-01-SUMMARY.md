---
phase: 23-markdown-renderer
plan: 01
subsystem: ui
tags: [pulldown-cmark, markdown, slint, scrollview, block-rendering]

# Dependency graph
requires:
  - phase: 22-results-viewer
    provides: ReportViewer component, report-content property, Copy All callback
provides:
  - Markdown parser (pulldown-cmark) converting report strings to typed blocks
  - Block-based ScrollView renderer replacing TextEdit in report viewer
  - MarkdownBlock struct shared between Rust and Slint
  - Styled rendering for 6 block types (heading, paragraph, code, rule, list, blockquote)
affects: [24-settings, 25-polish]

# Tech tracking
tech-stack:
  added: [pulldown-cmark 0.13]
  patterns: [block-model-pattern, type-discriminated-struct, dual-property-pattern]

key-files:
  created:
    - rust/ui-applications/classic-gui/src/markdown.rs
    - rust/ui-applications/classic-gui/ui/widgets/types.slint
  modified:
    - rust/Cargo.toml
    - rust/ui-applications/classic-gui/Cargo.toml
    - rust/ui-applications/classic-gui/src/lib.rs
    - rust/ui-applications/classic-gui/src/main.rs
    - rust/ui-applications/classic-gui/ui/main.slint
    - rust/ui-applications/classic-gui/ui/widgets/report_viewer.slint

key-decisions:
  - "types.slint for shared struct: Avoids circular imports between main.slint and report_viewer.slint"
  - "Block-level formatting flattening: Bold/italic applied per-block not inline, matching CLASSIC report style"
  - "Dual property pattern: report-content (raw markdown for Copy All) + report-blocks (parsed for rendering)"
  - "Rectangle indent spacer: Used for list item indentation instead of padding-left on HorizontalLayout"

patterns-established:
  - "Block model pattern: Parse markdown to flat Vec<MarkdownBlock>, render via Slint for-loop with conditional if per block-type"
  - "Shared types file: types.slint exports structs imported by both main.slint and widget files"
  - "Type-discriminated struct: Integer block_type field with constants (0-5) replaces Rust enum for Slint compatibility"

# Metrics
duration: 9min
completed: 2026-02-06
---

# Phase 23 Plan 01: Markdown Renderer Summary

**pulldown-cmark parser with block-model Slint renderer replacing TextEdit for styled report display**

## Performance

- **Duration:** 9 min
- **Started:** 2026-02-06T03:21:03Z
- **Completed:** 2026-02-06T03:29:51Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Created markdown parser with pulldown-cmark producing typed MarkdownBlock structs for all 6 block types
- Replaced TextEdit-based report viewer with ScrollView + VerticalLayout block renderer with styled headings, code blocks, list items, blockquotes, and horizontal rules
- Wired markdown parsing into all 4 report display paths (scan completion, selection, search, sort) while preserving raw markdown Copy All behavior
- Added 13 unit tests for markdown parsing covering all block types and edge cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Create markdown parser with pulldown-cmark** - `74958b7b` (feat)
2. **Task 2: Rewrite report viewer Slint UI for block rendering** - `3fb9e355` (feat)
3. **Task 3: Wire markdown parsing into report callbacks** - `f2dd6dfc` (feat)

## Files Created/Modified
- `rust/ui-applications/classic-gui/src/markdown.rs` - Markdown parser: parse_markdown() + MarkdownBlock struct + 13 tests
- `rust/ui-applications/classic-gui/ui/widgets/types.slint` - Shared MarkdownBlock struct definition for Slint
- `rust/ui-applications/classic-gui/ui/widgets/report_viewer.slint` - Block-based ScrollView renderer with 6 block types
- `rust/ui-applications/classic-gui/ui/main.slint` - MarkdownBlock import/export, report-blocks property
- `rust/ui-applications/classic-gui/src/main.rs` - update_report_blocks() helper wired into all display paths
- `rust/ui-applications/classic-gui/src/lib.rs` - markdown module declaration and re-exports
- `rust/ui-applications/classic-gui/Cargo.toml` - pulldown-cmark dependency
- `rust/Cargo.toml` - pulldown-cmark workspace dependency

## Decisions Made
- **types.slint for shared struct:** Created a dedicated types.slint file to avoid circular imports between main.slint and report_viewer.slint when sharing the MarkdownBlock struct
- **Block-level formatting flattening:** Bold/italic state detected during parsing is applied to the entire block, not inline. This matches CLASSIC report format where formatting is at the line level.
- **Rectangle indent spacer for list items:** HorizontalLayout does not support padding-left in Slint, so a Rectangle with computed width serves as the indent spacer
- **Depth-based bullet markers:** Filled bullet (depth 1), open circle (depth 2), small square (depth 3+) for visual list nesting

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] HorizontalLayout import not from std-widgets**
- **Found during:** Task 2 (Slint UI rewrite)
- **Issue:** HorizontalLayout is a built-in Slint element, not an export from std-widgets.slint. IDE diagnostic caught the invalid import.
- **Fix:** Removed HorizontalLayout from the std-widgets import line; it is available as a built-in element.
- **Files modified:** rust/ui-applications/classic-gui/ui/widgets/report_viewer.slint
- **Verification:** cargo build -p classic-gui succeeds
- **Committed in:** 3fb9e355 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor import fix. No scope creep.

## Issues Encountered
- Unused variable/import lint errors (`in_heading`, `in_code_block`, `CodeBlockKind`, `MarkdownBlockData`) from deny(unused) lint -- resolved by removing tracking variables that were set but never read, and removing unused type alias import

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Markdown renderer is fully functional for all block types used in CLASSIC reports
- Copy All preserves raw markdown source as specified
- Ready for Phase 24 (Settings) or Phase 25 (Polish)
- Potential polish items: inline code pill highlighting, cross-block text selection

## Self-Check: PASSED

---
*Phase: 23-markdown-renderer*
*Completed: 2026-02-06*
