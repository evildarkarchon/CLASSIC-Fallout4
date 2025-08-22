# Results Viewer Tab Implementation Plan

## Overview
This document outlines the implementation plan for adding a Results Viewer tab to the CLASSIC GUI interface. The tab will display scan reports in a two-panel layout: a list of available reports on the left and a markdown-rendered report viewer on the right.

## Architecture Design

### Component Structure
```
ClassicLib/Interface/
├── ResultsViewerMixin.py        # Main results viewer logic (new)
├── ResultsViewerWidgets.py      # Custom widgets for results display (new)
├── TabSetupMixin.py             # Update to add results tab
└── StyleSheets.py               # Update with results viewer styles
```

### Key Components

#### 1. ResultsViewerMixin Class
**Location**: `ClassicLib/Interface/ResultsViewerMixin.py`
- **Purpose**: Manages the results viewer tab functionality
- **Responsibilities**:
  - Scan for available report files
  - Handle report selection
  - Manage report loading and display
  - Implement refresh functionality
  - Handle file watching for new reports

**Key Methods**:
- `setup_results_tab()` - Initialize the results viewer UI
- `scan_for_reports()` - Find all -AUTOSCAN.md files
- `load_report(report_path)` - Load and display selected report
- `refresh_reports_list()` - Update the reports list
- `watch_for_changes()` - Monitor for new/modified reports
- `export_report()` - Export selected report to different formats
- `delete_report()` - Remove selected report with confirmation

#### 2. Custom Widgets
**Location**: `ClassicLib/Interface/ResultsViewerWidgets.py`

##### ReportListWidget (QListWidget)
- Custom list widget for displaying available reports
- Features:
  - Custom item display with report metadata (date, size, status)
  - Sorting options (by date, name, status)
  - Search/filter functionality
  - Context menu for report operations
  - Visual indicators for report status (solved/unsolved/incomplete)

##### MarkdownViewer (QTextBrowser)
- Extended QTextBrowser for markdown rendering
- Features:
  - Native markdown support (Qt 6.x)
  - Custom CSS styling for consistent appearance
  - Hyperlink handling
  - Copy functionality
  - Print support
  - Zoom controls

##### ReportMetadataWidget (QWidget)
- Display report metadata and statistics
- Shows:
  - Scan date/time
  - Original crash log name
  - Number of issues found
  - Scan duration
  - Report status

### UI Layout Design

```
┌─────────────────────────────────────────────────────────────┐
│                        Results Tab                          │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────┬────────────────────────────────────────┐│
│ │  Reports List    │         Report Viewer                  ││
│ │                  │                                        ││
│ │ [Search...]      │  ┌──────────────────────────────────┐ ││
│ │                  │  │     Report Metadata              │ ││
│ │ ○ crash-2024...  │  │ Date: 2024-01-15 14:30          │ ││
│ │ ● crash-2024...  │  │ Status: Solved                  │ ││
│ │ ○ crash-2024...  │  │ Issues: 5 found                 │ ││
│ │                  │  └──────────────────────────────────┘ ││
│ │                  │                                        ││
│ │                  │  ┌──────────────────────────────────┐ ││
│ │                  │  │                                  │ ││
│ │                  │  │   Markdown Rendered Report       │ ││
│ │                  │  │                                  │ ││
│ │                  │  │   # CLASSIC Auto-Scan Report     │ ││
│ │                  │  │   ## Summary                     │ ││
│ │                  │  │   ...                            │ ││
│ │                  │  │                                  │ ││
│ │                  │  └──────────────────────────────────┘ ││
│ │                  │                                        ││
│ │ [Refresh] [Del]  │  [Export] [Print] [−][100%][+]        ││
│ └─────────────────┴────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Implementation Steps

### Phase 1: Core Infrastructure (Priority: High)
1. **Create ResultsViewerMixin class**
   - Implement basic mixin structure
   - Add TYPE_CHECKING stubs for MainWindow integration
   - Create placeholder methods for core functionality

2. **Update TabSetupMixin**
   - Add `setup_results_tab()` method
   - Create results_tab widget
   - Integrate with existing tab structure

3. **Basic Report Discovery**
   - Implement `scan_for_reports()` method
   - Search in "Crash Logs" directory
   - Support custom scan folders
   - Filter for -AUTOSCAN.md files

### Phase 2: UI Components (Priority: High)
1. **Create ReportListWidget**
   - Extend QListWidget
   - Implement custom item rendering
   - Add selection signals
   - Basic sorting functionality

2. **Create MarkdownViewer**
   - Extend QTextBrowser
   - Configure markdown rendering
   - Apply custom styling
   - Handle hyperlinks

3. **Layout Implementation**
   - Use QSplitter for resizable panels
   - Set appropriate size ratios (30/70 default)
   - Add toolbar buttons
   - Apply consistent styling

### Phase 3: Core Functionality (Priority: High)
1. **Report Loading**
   - Implement `load_report()` method
   - Parse markdown content
   - Handle encoding issues
   - Display in viewer

2. **Report Management**
   - Refresh functionality
   - Delete with confirmation
   - Handle missing files gracefully
   - Error handling and user feedback

3. **Integration**
   - Connect to MainWindow
   - Add to tab widget
   - Test with existing scan workflow

### Phase 4: Enhanced Features (Priority: Medium)
1. **Search and Filter**
   - Add search box to reports list
   - Filter by date range
   - Filter by status (solved/unsolved)
   - Quick search in report content

2. **Report Metadata**
   - Extract metadata from reports
   - Display in metadata widget
   - Show statistics and summary

3. **Export Functionality**
   - Export to PDF (using QPrinter)
   - Export to HTML
   - Copy to clipboard
   - Save to different location

### Phase 5: Advanced Features (Priority: Low)
1. **File Watching**
   - Monitor for new reports
   - Auto-refresh on changes
   - Notification for new reports

2. **Report Comparison**
   - Compare two reports side-by-side
   - Highlight differences
   - Track improvement over time

3. **Report Templates**
   - Custom CSS themes
   - User-configurable styles
   - Print templates

## Technical Considerations

### Dependencies
- **PySide6.QtWidgets**: Core UI components
- **PySide6.QtCore**: Signals, slots, file watching
- **PySide6.QtGui**: Text formatting, printing
- **pathlib**: File system operations
- **re**: Report parsing and filtering

### Performance Optimization
- Lazy loading of report content
- Caching of parsed reports
- Efficient file scanning with glob patterns
- Asynchronous report loading for large files
- Virtual scrolling for long report lists

### Error Handling
- Graceful handling of missing/corrupted reports
- User-friendly error messages
- Logging of errors for debugging
- Recovery mechanisms for file access issues

### Threading Considerations
- File scanning in background thread
- Non-blocking UI during report loading
- Progress indicators for long operations
- Thread-safe report list updates

## Testing Strategy

### Unit Tests
- Test report discovery logic
- Test markdown rendering
- Test file operations
- Test metadata extraction

### Integration Tests
- Test tab integration with MainWindow
- Test workflow from scan to view
- Test concurrent operations
- Test error scenarios

### UI Tests
- Test responsive layout
- Test user interactions
- Test keyboard shortcuts
- Test accessibility features

## File Structure Details

### Report Storage
- **Primary Location**: `./Crash Logs/`
- **Naming Convention**: `crash-YYYY-MM-DD-HHMMSS-AUTOSCAN.md`
- **Custom Folders**: Defined in settings
- **Backup Location**: `./CLASSIC Backup/Unsolved Logs/`

### Report Format
```markdown
# CLASSIC AUTOSCAN REPORT
## Scan Information
- Date: YYYY-MM-DD HH:MM:SS
- Original Log: crash-YYYY-MM-DD-HHMMSS.log
- Status: [SOLVED/UNSOLVED/INCOMPLETE]

## Issues Found
### Critical Issues
- Issue 1 description
- Issue 2 description

### Warnings
- Warning 1
- Warning 2

## Recommendations
- Recommendation 1
- Recommendation 2
```

## Configuration Options

### Settings (YAML)
```yaml
ResultsViewer:
  DefaultSplitRatio: 30  # Percentage for list panel
  MarkdownCSS: "default"  # CSS theme name
  AutoRefresh: true       # Auto-refresh on new reports
  RefreshInterval: 5000   # Milliseconds
  ShowMetadata: true      # Show metadata panel
  SortOrder: "date_desc"  # Default sort order
```

## Implementation Timeline

### Week 1
- Core infrastructure setup
- Basic UI components
- Simple report loading

### Week 2
- Complete core functionality
- Integration with MainWindow
- Basic testing

### Week 3
- Enhanced features (search, filter)
- Export functionality
- Comprehensive testing

### Week 4
- Advanced features (if time permits)
- Documentation
- Final testing and polish

## Success Criteria

### Functional Requirements
- ✓ Users can view list of all scan reports
- ✓ Users can select and view report content
- ✓ Reports render with proper markdown formatting
- ✓ Users can refresh the reports list
- ✓ Users can delete unwanted reports
- ✓ Users can export reports

### Non-Functional Requirements
- ✓ Responsive UI with no freezing
- ✓ Reports load within 1 second
- ✓ Supports 1000+ reports in list
- ✓ Maintains CLASSIC's visual consistency
- ✓ Follows existing code patterns

## Risk Mitigation

### Technical Risks
1. **Large Report Files**
   - Mitigation: Implement streaming/chunked loading
   - Fallback: Limit display to first N lines with "Load More"

2. **Markdown Rendering Issues**
   - Mitigation: Test with various report formats
   - Fallback: Plain text display option

3. **Performance with Many Reports**
   - Mitigation: Virtual scrolling, pagination
   - Fallback: Limit initial load, lazy loading

### User Experience Risks
1. **Complex UI**
   - Mitigation: Keep interface simple and intuitive
   - Solution: Follow existing CLASSIC UI patterns

2. **Lost Reports**
   - Mitigation: Confirmation dialogs for delete
   - Solution: Move to trash instead of permanent delete

## Future Enhancements

### Version 2.0
- Report analytics and trends
- Batch operations on multiple reports
- Report sharing functionality
- Integration with external tools
- Custom report templates
- Report annotations and notes

### Version 3.0
- Machine learning insights
- Automated report categorization
- Predictive analysis
- Report collaboration features
- Cloud backup integration

## Appendix: Code Examples

### Basic Mixin Structure
```python
class ResultsViewerMixin:
    if TYPE_CHECKING:
        results_tab: QWidget
        results_list: QListWidget
        markdown_viewer: QTextBrowser

    def setup_results_tab(self) -> None:
        """Initialize the results viewer tab."""
        layout = QHBoxLayout(self.results_tab)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - reports list
        left_panel = self.create_reports_panel()

        # Right panel - viewer
        right_panel = self.create_viewer_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 700])

        layout.addWidget(splitter)
```

### Report Discovery
```python
def scan_for_reports(self) -> list[Path]:
    """Scan for available report files."""
    reports = []

    # Primary location
    crash_logs_dir = Path.cwd() / "Crash Logs"
    if crash_logs_dir.exists():
        reports.extend(crash_logs_dir.glob("*-AUTOSCAN.md"))

    # Custom locations from settings
    custom_path = self.get_custom_scan_path()
    if custom_path and custom_path.exists():
        reports.extend(custom_path.glob("*-AUTOSCAN.md"))

    # Sort by modification time (newest first)
    reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    return reports
```

## Conclusion

This implementation plan provides a comprehensive roadmap for adding a Results Viewer tab to the CLASSIC GUI. The modular design ensures easy maintenance and future enhancements while maintaining consistency with the existing codebase. The phased approach allows for incremental development and testing, ensuring a stable and polished final product.
