# Phase 23: Markdown Renderer - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform the plain-text report viewer (currently a `TextEdit` with Consolas font) into a formatted markdown display. The viewer renders report content with styled headers, bullet lists, code blocks, and inline formatting. This phase delivers markdown rendering for the existing results viewer — no new tabs, navigation, or report management features.

</domain>

<decisions>
## Implementation Decisions

### Visual hierarchy
- Headers use size + weight differentiation (no color distinction)
- H1 largest + bold, H2 medium + bold, H3 small + bold
- No horizontal rule separators under headers
- Explicit markdown horizontal rules (`---`) render as thin visible lines
- Uniform text color for body and headers — headers stand out through size+weight only

### Code block styling
- Fenced code blocks get a subtle background rectangle (slightly different shade from viewer background)
- No border around code blocks — background alone provides delineation
- Inline code (`backtick`) gets a background pill highlight (like GitHub/Discord style)
- No syntax highlighting — plain monospace text in code blocks (crash logs don't benefit)
- Code block line overflow behavior: Claude's discretion (pick what works best for report content in Slint)

### Content density
- Vertical spacing between elements: Claude's discretion (optimize for crash log report lengths)
- Bullet lists use visual bullet markers (bullet characters, not indentation alone)
- Nested lists use indent + different marker characters per level (e.g., bullet, circle, square)
- Content fills full width of the viewer panel — no max-width cap

### Copy behavior
- "Copy All" button copies **original markdown source** (raw text with `#`, `**`, triple-backtick markers preserved)
- Partial text selection should be supported if technically feasible
- Partial selection copies **rendered text** (no markdown syntax markers)
- **Fallback**: If partial text selection is too difficult with custom Slint rendering, "Copy All" alone is acceptable — partial selection is nice-to-have, not blocking

### Claude's Discretion
- Code block line overflow behavior (horizontal scroll vs word wrap)
- Vertical spacing between markdown elements (tight vs comfortable)
- Technical approach for rendering (component tree, custom drawing, etc.)
- Exact font sizes for H1, H2, H3
- Spacing for bullet list nesting indentation

</decisions>

<specifics>
## Specific Ideas

- Current viewer is a Slint `TextEdit` in `report_viewer.slint` — this will need to be replaced or augmented
- Reports are crash log analyses, not source code — syntax highlighting adds no value
- The `pulldown-cmark` crate is already identified as the markdown parser (noted in STATE.md)
- Inline code pills should feel like GitHub/Discord inline code rendering
- Nested bullet markers should use distinct characters per level (filled circle, open circle, square)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 23-markdown-renderer*
*Context gathered: 2026-02-05*
