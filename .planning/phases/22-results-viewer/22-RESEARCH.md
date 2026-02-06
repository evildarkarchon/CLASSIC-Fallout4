# Phase 22: Results Viewer - Research

**Researched:** 2026-02-05
**Domain:** Slint GUI - master-detail list/viewer with filtering, text display, clipboard
**Confidence:** HIGH

## Summary

This phase adds a Results tab to the existing Slint GUI that shows scan reports in a master-detail layout. The left panel lists reports (from `ScanResult.reports: Vec<AnalysisResult>`) with search/filter, and the right panel displays the selected report as plain text (monospace, read-only, selectable, scrollable). A custom draggable splitter divides the two panels.

The current GUI holds `ScanResult` in memory after scanning (in `scan.rs`) but does not pass it to the Results tab or write reports to disk. Phase 22 must bridge this gap by storing scan results in shared state and exposing them to the UI via Slint models.

**Primary recommendation:** Use Slint's `StandardListView` for the report list (simple text items), `TextEdit` in read-only mode for the viewer, a custom `TouchArea`-based splitter for the draggable divider, and `arboard` crate for the "Copy All" clipboard operation. Filter the list model using Slint's built-in `FilterModel` from Rust. Avoid `StandardTableView` -- it is heavyweight for a simple filename+timestamp list and complicates the sortable header interaction.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Side-by-side master-detail: report list on left, viewer on right
- Report list takes ~25% width (narrow list, maximize viewer space)
- Draggable splitter between list and viewer panels (user-resizable)
- Empty state (no reports): centered message with action button that switches to Main Options tab to start a scan
- Each row shows: report filename + timestamp
- Default sort: filename descending (naming convention embeds date-time, so this approximates newest-first)
- Clickable column header to toggle ascending/descending sort
- Selected report has highlighted row background (distinct from unselected)
- Search box placed at top of the list panel (scoped to list filtering)
- Instant filter as user types (no Enter required)
- Searches filenames only (not report content)
- Auto-select first report when list populates
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

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| slint | 1.15.0 | UI framework (already in workspace) | Existing project dependency |
| arboard | 3.x | System clipboard access for "Copy All" | De facto Rust clipboard crate, maintained by 1Password |

### Supporting (Already in Project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| parking_lot | workspace | Mutex for shared state | Report data shared between scan callback and UI |
| classic-scanlog-core | workspace | AnalysisResult struct | Source of report data |
| classic-file-io-core | workspace | LogCollector, AUTOSCAN patterns | Report file naming conventions |

### Not Needed
| Instead of | Why Not |
|------------|---------|
| copypasta | arboard is more actively maintained, better Windows support |
| clipboard crate | Deprecated, arboard is the successor |
| StandardTableView | Too heavyweight for a simple list; sorting callbacks and column definitions add complexity without benefit for a 1-column display with a header |

**Installation:**
```toml
# Add to rust/ui-applications/classic-gui/Cargo.toml
arboard = "3"
```

## Architecture Patterns

### Data Flow: Scan Results to Results Tab

The current scan flow ends with `ScanResult` returned in the completion callback (main.rs line 208-219). This result contains `Vec<AnalysisResult>`, each with `report_lines: Vec<String>` and `log_path: String`. The data lives only in the callback closure and is not stored.

**Pattern: Shared Report State**

Store scan results in `AppState` (already exists as `Arc<Mutex<AppState>>`) and populate Slint models from it:

```
Scan completes
  -> ScanResult returned in completion callback
  -> Extract reports into AppState.reports
  -> Convert to Slint model data (ReportEntry structs)
  -> Set VecModel on MainWindow
  -> Auto-select first item
  -> Auto-switch to Results tab (already implemented)
```

### Recommended .slint Structure

```
ui/
  main.slint                    # MainWindow (modify Results tab)
  widgets/
    path_input.slint            # Existing
    report_list.slint           # NEW: Report list with search + header
    report_viewer.slint         # NEW: Text viewer with Copy All button
    splitter.slint              # NEW: Draggable splitter handle
```

### Recommended Rust Module Structure

```
src/
  main.rs          # Existing (add report model population)
  lib.rs           # Existing (add re-exports)
  scan.rs          # Existing (unchanged)
  state.rs         # Existing (add report persistence to AppState)
  worker.rs        # Existing (unchanged)
  results.rs       # NEW: Report model management, filtering, sorting
```

### Pattern 1: Slint Model for Report List

Reports need to be displayed in a list. Slint models bridge Rust data to UI.

**Slint side:**
```slint
// Define the report entry struct visible to Slint
export struct ReportEntry {
    filename: string,
    timestamp: string,
    // Index into the full reports array (for content lookup)
    source-index: int,
}
```

**Rust side:**
```rust
use slint::{ModelRc, VecModel, SharedString};
use std::rc::Rc;

// Create model from scan results
let model = Rc::new(VecModel::default());
for (i, result) in scan_result.reports.iter().enumerate() {
    let filename = extract_filename(&result.log_path);
    let timestamp = extract_timestamp(&filename);
    model.push(ReportEntry {
        filename: SharedString::from(&filename),
        timestamp: SharedString::from(&timestamp),
        source_index: i as i32,
    });
}
let model_rc = ModelRc::from(model.clone());
window.set_report_list_model(model_rc);
```

### Pattern 2: FilterModel for Search

Slint provides `FilterModel` that wraps a source model and applies a predicate. When the search text changes, call `reset()` to re-evaluate the filter.

**Rust side:**
```rust
use slint::FilterModel;

// Create filter model wrapping the source VecModel
let search_text = Arc::new(Mutex::new(String::new()));
let search_text_clone = search_text.clone();

let filter_model = Rc::new(FilterModel::new(model.clone(), move |entry: &ReportEntry| {
    let search = search_text_clone.lock();
    if search.is_empty() {
        return true;
    }
    entry.filename.to_lowercase().contains(&search.to_lowercase())
}));

// When search text changes (callback from LineEdit):
window.on_search_changed(move |text| {
    *search_text.lock() = text.to_string();
    filter_model.reset(); // Re-evaluate filter
    // Auto-select first result if any
});
```

### Pattern 3: Custom Splitter Widget

Slint does not have a built-in splitter widget. Build one using TouchArea with `ew-resize` cursor.

**Slint side:**
```slint
// Source: https://docs.slint.dev/latest/docs/slint/guide/development/custom-controls/
component Splitter inherits TouchArea {
    width: 6px;
    mouse-cursor: ew-resize;

    Rectangle {
        width: 100%;
        height: 100%;
        background: @linear-gradient(90deg, transparent, #555555, transparent);
        border-radius: 2px;
    }
}
```

**Usage in parent layout:**
```slint
HorizontalLayout {
    // Left panel (report list)
    list-panel := Rectangle {
        width: splitter.x;
        min-width: 150px;
        // ... report list content
    }

    splitter := Splitter {
        x: root.width * 0.25; // Default 25%
        height: 100%;

        moved => {
            self.x = min(root.width * 0.6,
                        max(150px, self.x + self.mouse-x - self.pressed-x));
        }
    }

    // Right panel (viewer)
    viewer-panel := Rectangle {
        width: root.width - splitter.x - splitter.width;
        // ... viewer content
    }
}
```

### Pattern 4: Read-Only TextEdit for Viewer

TextEdit with `read-only: true` supports text selection and Ctrl+C natively.

```slint
TextEdit {
    text: root.report-content;
    read-only: true;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
    wrap: word-wrap;
    horizontal-stretch: 1;
    vertical-stretch: 1;
}
```

### Pattern 5: Clipboard Copy via arboard

For the "Copy All" button, use `arboard` crate since it works regardless of TextEdit focus state.

```rust
use arboard::Clipboard;

window.on_copy_all(move || {
    let text = window_weak.upgrade()
        .map(|w| w.get_report_content().to_string())
        .unwrap_or_default();

    if let Ok(mut clipboard) = Clipboard::new() {
        let _ = clipboard.set_text(text);
    }
});
```

**Important:** On Windows, arboard's clipboard is a global object that can only be opened on one thread at once. Since Slint callbacks run on the UI thread, this is safe.

### Pattern 6: Sort Toggle via Rust Callback

Instead of StandardTableView's sort callbacks, implement a clickable header row in .slint that invokes a Rust callback to re-sort the model.

```slint
// Clickable header
HorizontalBox {
    TouchArea {
        clicked => { root.toggle-sort(); }
        HorizontalBox {
            Text { text: "Report"; }
            Text { text: root.sort-ascending ? "^" : "v"; font-size: 10px; }
        }
    }
}
```

```rust
// Rust side: re-sort and replace model
window.on_toggle_sort(move || {
    let mut ascending = state.lock().sort_ascending;
    ascending = !ascending;
    state.lock().sort_ascending = ascending;

    let mut entries: Vec<ReportEntry> = /* collect from model */;
    if ascending {
        entries.sort_by(|a, b| a.filename.cmp(&b.filename));
    } else {
        entries.sort_by(|a, b| b.filename.cmp(&a.filename));
    }
    model.set_vec(entries);
});
```

### Anti-Patterns to Avoid
- **Don't use StandardTableView for a simple list:** It requires `[[StandardListViewItem]]` (array of arrays) and column definitions. For a single-column list with a custom header, it adds complexity without benefit.
- **Don't read report files from disk for display:** Reports are already in memory as `ScanResult.reports[i].report_lines`. Reading from disk would be slower and require knowing the file path.
- **Don't create a new Tokio task for clipboard:** Clipboard operations are synchronous and fast. Running them in the UI callback is fine.
- **Don't share VecModel across threads:** `ModelRc` is not `Send`. All model mutations must happen on the UI thread via `upgrade_in_event_loop`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| List filtering | Custom filter loop rebuilding model | `slint::FilterModel` | Handles index mapping, auto-updates on source changes |
| System clipboard | Platform-specific Win32 API calls | `arboard` crate | Cross-platform, handles Windows global clipboard locking |
| Text selection + copy | Custom selection overlay | `TextEdit { read-only: true }` | Built-in text selection, Ctrl+C, context menu |
| Scrollable text view | Custom scroll logic | `TextEdit` | Natively scrollable when content exceeds bounds |
| Sort indicator UI | Complex icon rendering | Simple Text element with "^"/"v" | Minimal, clear, fits fluent-dark theme |

## Common Pitfalls

### Pitfall 1: Model Updates From Wrong Thread
**What goes wrong:** Attempting to modify a `VecModel` from an async/background task causes panic or undefined behavior.
**Why it happens:** `ModelRc` and `VecModel` are not `Send` -- they can only be used on the UI thread.
**How to avoid:** Always use `upgrade_in_event_loop` to update models from async contexts. Store report data in `Arc<Mutex<>>` state, then populate models in UI thread callbacks.
**Warning signs:** "cannot be sent between threads safely" compiler error.

### Pitfall 2: FilterModel Stale State
**What goes wrong:** Filter doesn't update when search text changes because the closure captures an immutable value.
**Why it happens:** The filter closure captures a snapshot, not a live reference. Slint's `FilterModel` only re-evaluates when `reset()` is called.
**How to avoid:** Capture an `Arc<Mutex<String>>` in the filter closure. Update the mutex value when search text changes, then call `filter_model.reset()`.
**Warning signs:** Search box text changes but list doesn't filter.

### Pitfall 3: Splitter Position Not Constrained
**What goes wrong:** User drags splitter off-screen or makes a panel 0-width.
**Why it happens:** No min/max constraints on splitter position.
**How to avoid:** Use `min()` and `max()` in the `moved` callback to clamp between minimum panel widths (e.g., 150px minimum list width, 200px minimum viewer width).
**Warning signs:** Panel disappears during resize.

### Pitfall 4: Empty State vs Filtered Empty
**What goes wrong:** User types a search query matching nothing and sees the same "no reports" empty state as when no scan has been done.
**Why it happens:** Both states show an empty list but have different meanings.
**How to avoid:** Track two states separately: (1) no reports loaded at all (show "Run a scan" prompt), (2) filter matches nothing (show "No matching reports" text in list area). Use a property like `has-reports` to distinguish.
**Warning signs:** User confusion about whether they need to scan or refine search.

### Pitfall 5: Report Content Not Updating on Selection Change
**What goes wrong:** Clicking a different report in the list doesn't change the viewer content.
**Why it happens:** Missing callback connection between list selection and report content property.
**How to avoid:** Wire `current-item-changed` callback to update the `report-content` string property from the `AnalysisResult.report_lines` stored in state.
**Warning signs:** Viewer always shows the first report regardless of selection.

### Pitfall 6: Timestamp Extraction Fragility
**What goes wrong:** Timestamp parsing fails on unexpected filenames.
**Why it happens:** Crash log filenames follow a convention but may vary.
**How to avoid:** Use file modification time (`std::fs::metadata().modified()`) as a reliable fallback. Parse filename timestamp as a best-effort enrichment. The CONTEXT.md decision to sort by filename descending means timestamp display is informational, not functional.
**Warning signs:** "Unknown" timestamps in the list.

## Code Examples

### Complete Splitter Widget (Slint)
```slint
// Source: Adapted from https://docs.slint.dev/latest/docs/slint/guide/development/custom-controls/
component Splitter inherits TouchArea {
    width: 6px;
    mouse-cursor: ew-resize;

    Rectangle {
        width: 100%;
        height: 100%;
        background: self.parent.pressed ? #888888 : #555555;
        border-radius: 2px;
    }
}
```

### Report Entry Struct (Slint)
```slint
export struct ReportEntry {
    filename: string,
    timestamp: string,
    source-index: int,
}
```

### VecModel Creation and Population (Rust)
```rust
// Source: https://docs.slint.dev/latest/docs/rust/slint/struct.VecModel
use slint::{ModelRc, VecModel, SharedString};
use std::rc::Rc;

fn populate_report_model(
    reports: &[AnalysisResult],
) -> Rc<VecModel<ReportEntry>> {
    let model = Rc::new(VecModel::default());

    // Sort by filename descending (newest first per CONTEXT.md)
    let mut entries: Vec<_> = reports.iter().enumerate()
        .map(|(i, r)| {
            let filename = Path::new(&r.log_path)
                .file_name()
                .map(|f| f.to_string_lossy().to_string())
                .unwrap_or_else(|| "unknown".to_string());
            let timestamp = extract_timestamp_from_filename(&filename);
            ReportEntry {
                filename: SharedString::from(&filename),
                timestamp: SharedString::from(&timestamp),
                source_index: i as i32,
            }
        })
        .collect();

    entries.sort_by(|a, b| b.filename.cmp(&a.filename)); // Descending
    model.set_vec(entries);
    model
}
```

### FilterModel with Search (Rust)
```rust
// Source: https://docs.slint.dev/latest/docs/rust/slint/struct.FilterModel
use slint::FilterModel;
use std::sync::Arc;
use parking_lot::Mutex;

let search_text = Arc::new(Mutex::new(String::new()));
let search_clone = search_text.clone();

let filtered = Rc::new(FilterModel::new(
    model.clone(),
    move |entry: &ReportEntry| {
        let query = search_clone.lock();
        if query.is_empty() {
            return true;
        }
        entry.filename.to_lowercase()
            .contains(&query.to_lowercase())
    },
));
```

### Clipboard Copy (Rust)
```rust
// Using arboard for "Copy All" button
// Source: https://docs.rs/arboard/latest/arboard/struct.Clipboard.html
use arboard::Clipboard;

fn copy_to_clipboard(text: &str) -> bool {
    match Clipboard::new() {
        Ok(mut clipboard) => clipboard.set_text(text).is_ok(),
        Err(_) => false,
    }
}
```

### TextEdit Read-Only Viewer (Slint)
```slint
// Source: https://docs.slint.dev/latest/docs/slint/reference/std-widgets/views/textedit/
import { TextEdit } from "std-widgets.slint";

TextEdit {
    text: root.report-content;
    read-only: true;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
    wrap: word-wrap;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| StandardListView only | StandardListView + FilterModel | Slint 1.2+ | Built-in filtering eliminates manual model rebuild |
| Manual clipboard via Win32 | arboard crate | 2023+ | Cross-platform clipboard in 3 lines |
| No splitter widget | TouchArea-based custom splitter | Ongoing | Slint has open issue #6949 for built-in splitter, not yet implemented |

**Deprecated/outdated:**
- `rust-clipboard` crate: Unmaintained, replaced by `arboard`
- `copypasta` crate: Less actively maintained than `arboard`

## RSLT Requirements Mapping

| Requirement | Implementation Approach |
|-------------|------------------------|
| RSLT-01: Report list displays available scan reports | VecModel populated from ScanResult.reports, shown in StandardListView |
| RSLT-02: Report list shows timestamp, status, file size | Custom list item showing filename + timestamp (status/size from CONTEXT: filename + timestamp only) |
| RSLT-03: User can search/filter report list | LineEdit + FilterModel with instant filtering on text change |
| RSLT-04: Selecting report displays content in viewer panel | current-item-changed callback updates report-content property |
| RSLT-06: Report viewer supports scrolling | TextEdit natively scrolls when content exceeds bounds |
| RSLT-07: User can copy text from report viewer | TextEdit read-only supports Ctrl+C; "Copy All" button uses arboard |

## Open Questions

1. **Report content source: memory vs disk?**
   - What we know: Currently, `ScanResult.reports` holds `Vec<AnalysisResult>` with `report_lines` in memory. The GUI does NOT call `write_reports_batch()` to save to disk.
   - What's unclear: Should the Results tab show in-memory reports only (from the current scan), or should it also discover previously-written AUTOSCAN files on disk?
   - Recommendation: Start with in-memory reports from the current scan. This is simpler, faster, and matches the current data flow. Disk-based report discovery can be added later. The scan module already has the data; we just need to pass it through AppState.

2. **Font availability on Windows**
   - What we know: "Cascadia Code" is bundled with Windows Terminal and VS Code but may not be installed on all Windows systems. "Consolas" is universally available on Windows.
   - Recommendation: Use font-family fallback chain: `"Cascadia Code", "Consolas", "Courier New", monospace`. Slint will use the first available font.

3. **StandardListView vs custom ListView for report list**
   - What we know: StandardListView only shows a single `text` field per item. The CONTEXT.md says each row shows "report filename + timestamp". StandardListView cannot show two fields per row natively.
   - Recommendation: Use a custom `ListView` with a delegate that renders both filename and timestamp. Alternatively, concatenate them into a single string for StandardListView (e.g., "crash-2024-01-15.log  |  Jan 15, 2024"). The custom approach is better for future extensibility (Phase 23 may want status indicators).

## Sources

### Primary (HIGH confidence)
- [Slint TextEdit docs](https://docs.slint.dev/latest/docs/slint/reference/std-widgets/views/textedit/) - read-only, font-family, wrap, copy/paste API
- [Slint StandardListView docs](https://docs.slint.dev/latest/docs/slint/reference/std-widgets/views/standardlistview/) - model, current-item, callbacks
- [Slint StandardTableView docs](https://docs.slint.dev/latest/docs/slint/reference/std-widgets/views/standardtableview/) - columns, sort callbacks (evaluated but not recommended)
- [Slint VecModel docs](https://docs.rs/slint/latest/slint/struct.VecModel.html) - push, set_vec, from_slice
- [Slint FilterModel docs](https://docs.slint.dev/latest/docs/rust/slint/struct.FilterModel) - new, reset, source_model
- [Slint ModelRc docs](https://docs.slint.dev/latest/docs/rust/slint/struct.ModelRc) - from VecModel, type mappings
- [Slint TouchArea docs](https://docs.slint.dev/latest/docs/slint/reference/gestures/toucharea/) - mouse-cursor, pressed-x/y
- [Slint Custom Controls guide](https://docs.slint.dev/latest/docs/slint/guide/development/custom-controls/) - splitter widget pattern
- [Slint Clipboard API](https://docs.slint.dev/latest/docs/rust/slint/platform/enum.Clipboard) - platform clipboard enum
- [TableColumn struct](https://docs.slint.dev/latest/docs/rust/slint/struct.TableColumn) - column definition for tables

### Secondary (MEDIUM confidence)
- [Slint splitter discussion #343](https://github.com/slint-ui/slint/discussions/343) - community splitter patterns with proportion tracking
- [arboard crate](https://github.com/1Password/arboard) - clipboard crate by 1Password
- [Slint splitter feature request #6949](https://github.com/slint-ui/slint/issues/6949) - confirms no built-in splitter yet

### Tertiary (LOW confidence)
- None - all findings verified with official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Slint 1.15.0 confirmed in workspace Cargo.toml, arboard is de facto standard
- Architecture: HIGH - Patterns verified with official Slint docs and existing project code
- Pitfalls: HIGH - Based on official API constraints (ModelRc not Send, FilterModel reset requirement)
- Splitter implementation: MEDIUM - Based on community patterns and official guide, but no built-in widget exists

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (Slint is stable at 1.15.0, patterns unlikely to change)
