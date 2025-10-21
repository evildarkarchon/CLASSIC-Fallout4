# TUI Feature Parity Implementation Plan

This document outlines a phased approach to bring the Rust TUI (`classic-tui`) to feature parity with the Python GUI (`CLASSIC_Interface.py`).

## Current State Assessment

### Python GUI Features (Complete Reference)
1. **Main Tab**
   - ✅ Staging mods folder picker (interactive)
   - ✅ Custom scan folder picker (interactive)
   - ✅ Crash logs scan with progress
   - ✅ Game files scan with progress
   - ✅ Papyrus monitor toggle
   - ✅ Update check toggle
   - ✅ Results output viewer
   - ✅ Audio notifications (scan complete, errors)
   - ✅ Thread-safe concurrent scanning

2. **Backups Tab**
   - ✅ XSE backup/restore/remove operations
   - ✅ ReShade backup/restore/remove operations
   - ✅ Vulkan backup/restore/remove operations
   - ✅ ENB backup/restore/remove operations
   - ✅ Backup existence checking
   - ✅ Visual feedback for available restores

3. **Articles Tab**
   - ✅ Clickable links to help resources
   - ✅ Categories: Installation, Common Issues, Advanced Topics
   - ✅ External browser integration

4. **Results Tab**
   - ✅ File watcher for auto-refresh of reports
   - ✅ Report list with sorting
   - ✅ Report viewer with syntax highlighting
   - ✅ Search/filter functionality
   - ✅ Pastebin upload integration
   - ✅ Copy to clipboard
   - ✅ Open in external editor

5. **Settings Dialog**
   - ✅ Tabbed settings interface
   - ✅ Path management (game paths, tools)
   - ✅ Scan options (FCX mode, FormID values, stat logging)
   - ✅ Output options (move unsolved logs, simplify logs)
   - ✅ Update check toggle
   - ✅ Save/Cancel/Reset to defaults

6. **Core Features**
   - ✅ Update checking with GitHub API
   - ✅ Window geometry persistence
   - ✅ Thread management for background tasks
   - ✅ Error dialogs with clipboard copy
   - ✅ Custom error dialog system

### TUI Current Implementation
1. **Main Screen**
   - ✅ Folder display (read-only)
   - ✅ Crash logs scan button (F5)
   - ✅ Game files scan button (F6)
   - ✅ Papyrus monitor toggle (F7)
   - ✅ Update check checkbox (display only)
   - ✅ Output viewer with scrolling
   - ✅ Progress indicators
   - ⚠️ Folder pickers (scaffolded but not functional)
   - ❌ Audio notifications
   - ❌ Advanced error display

2. **Settings Screen**
   - ✅ Basic settings navigation
   - ✅ Toggle FCX mode, FormID values, stat logging
   - ✅ Save settings (S key)
   - ❌ Path management
   - ❌ Advanced options
   - ❌ Reset to defaults

3. **Papyrus Screen**
   - ✅ Basic screen layout
   - ✅ Status indicator (Active/Stopped)
   - ✅ Stats display structure
   - ❌ Real-time log monitoring
   - ❌ Stats calculation and updates
   - ❌ Error/warning highlighting

4. **Help Screen**
   - ✅ Basic help screen
   - ❌ Comprehensive keyboard shortcuts
   - ❌ Feature documentation

5. **Missing Screens**
   - ❌ Backups screen
   - ❌ Articles/Resources screen
   - ❌ Results viewer screen

## Implementation Phases

### Phase 1: Core Functionality Completion (Foundation)
**Goal:** Complete half-implemented features and establish solid base functionality.

#### 1.1 Folder Management (Priority: HIGH)
- [ ] **Implement interactive folder picker**
  - Create TUI folder browser widget
  - Support navigation with arrow keys
  - Display current directory path
  - Allow selection with Enter key
  - Files: `classic-tui/src/widgets/folder_picker.rs`

- [ ] **Connect folder pickers to app state**
  - Update staging folder on selection
  - Update custom scan folder on selection
  - Persist to YAML configuration
  - Files: `classic-tui/src/handlers/folder_handler.rs`

- [ ] **Add folder validation**
  - Use `ClassicLib.ScanLog.Util.is_valid_custom_scan_path`
  - Display validation errors
  - Prevent invalid selections
  - Files: `classic-tui/src/validators/path_validator.rs`

#### 1.2 Papyrus Monitoring (Priority: HIGH)
- [ ] **Implement real-time log monitoring**
  - Port `PapyrusMonitorWorker` logic to Rust
  - Use `classic_scanlog_core::papyrus` module
  - Implement async file watching
  - Files: `classic-tui/src/handlers/papyrus_handler.rs`

- [ ] **Connect stats calculation**
  - Parse dumps, stacks, warnings, errors
  - Calculate error/warning ratio
  - Update timestamp on changes
  - Files: `classic-tui/src/ui/papyrus_screen.rs`

- [ ] **Add real-time stats display**
  - Color-coded status indicators
  - Auto-refresh display
  - Scrollable log output
  - Files: `classic-tui/src/ui/papyrus_screen.rs`

#### 1.3 Scan Operations Enhancement (Priority: MEDIUM)
- [ ] **Implement proper scan handlers**
  - Use `classic_scanlog_core` for crash log scanning
  - Use game file scanning from `classic-file-io-core`
  - Emit progress updates to UI
  - Handle errors gracefully
  - Files: `classic-tui/src/handlers/scan_handler.rs`

- [ ] **Add scan results display**
  - Show summary statistics
  - Display matched patterns
  - Show resolved FormIDs
  - List suspects
  - Files: `classic-tui/src/ui/results_screen.rs`

- [ ] **Implement error handling**
  - Display detailed error messages
  - Show error context
  - Offer retry options
  - Files: `classic-tui/src/ui/error_dialog.rs`

### Phase 2: Backup Operations (New Feature)
**Goal:** Add complete backup/restore functionality matching Python GUI.

#### 2.1 Backup Screen UI
- [ ] **Create backup operations screen**
  - Add to `UiState` enum
  - Create screen layout
  - Add navigation (F8 key)
  - Files: `classic-tui/src/ui/backup_screen.rs`

- [ ] **Design backup UI layout**
  - Section per backup type (XSE, ReShade, Vulkan, ENB)
  - Three buttons per section: Backup, Restore, Remove
  - Status indicators for existing backups
  - Files: `classic-tui/src/ui/backup_screen.rs`

#### 2.2 Backup Operations Logic
- [ ] **Port backup functionality**
  - Use `ClassicLib.ScanGame.manage_game_files` logic
  - Implement backup creation
  - Implement restore from backup
  - Implement backup removal
  - Files: `classic-tui/src/handlers/backup_handler.rs`

- [ ] **Add backup existence checking**
  - Scan backup directories on startup
  - Enable/disable restore buttons
  - Update UI state
  - Files: `classic-tui/src/handlers/backup_handler.rs`

- [ ] **Implement operation feedback**
  - Progress indicators for large operations
  - Success/failure messages
  - Confirmation dialogs
  - Files: `classic-tui/src/ui/backup_screen.rs`

### Phase 3: Results Viewer (Complex Feature)
**Goal:** Implement comprehensive results viewing and management.

#### 3.1 Results Screen Foundation
- [ ] **Create results viewer screen**
  - Add to `UiState` enum
  - Split-pane layout (list + viewer)
  - Navigation (F9 key)
  - Files: `classic-tui/src/ui/results_screen.rs`

- [ ] **Implement report list**
  - Scan `Crash Logs/Reports/` directory
  - Display report filenames with timestamps
  - Sort by date (newest first)
  - Keyboard navigation
  - Files: `classic-tui/src/widgets/report_list.rs`

#### 3.2 Report Viewing
- [ ] **Implement report viewer**
  - Load and display selected report
  - Syntax highlighting for important patterns
  - Scrollable content
  - Line numbers
  - Files: `classic-tui/src/widgets/report_viewer.rs`

- [ ] **Add search functionality**
  - Search within current report
  - Highlight matches
  - Navigate between matches (n/N keys)
  - Files: `classic-tui/src/widgets/report_viewer.rs`

#### 3.3 File Watching (Advanced)
- [ ] **Implement file watcher**
  - Monitor `Crash Logs/Reports/` directory
  - Detect new reports
  - Auto-refresh list
  - Use `notify` crate
  - Files: `classic-tui/src/handlers/file_watcher.rs`

- [ ] **Add auto-scroll option**
  - Toggle auto-scroll to newest
  - Visual indicator when new report arrives
  - Files: `classic-tui/src/ui/results_screen.rs`

### Phase 4: Settings Enhancement
**Goal:** Expand settings to match Python GUI capabilities.

#### 4.1 Path Management Settings
- [ ] **Add path settings section**
  - Game installation path
  - Documents folder path
  - Mods folder path
  - Custom scan path
  - Files: `classic-tui/src/ui/settings/paths_tab.rs`

- [ ] **Implement path editing**
  - Text input for paths
  - Folder picker integration
  - Path validation
  - Files: `classic-tui/src/ui/settings/paths_tab.rs`

#### 4.2 Advanced Settings
- [ ] **Add advanced options**
  - Performance settings (thread count, batch size)
  - Database settings
  - Logging verbosity
  - Files: `classic-tui/src/ui/settings/advanced_tab.rs`

- [ ] **Implement tabbed settings**
  - Multiple setting categories
  - Tab navigation (Tab/Shift+Tab)
  - Consistent layout
  - Files: `classic-tui/src/ui/settings_screen.rs`

#### 4.3 Settings Persistence
- [ ] **Add reset to defaults**
  - Reset individual settings
  - Reset entire categories
  - Confirmation dialog
  - Files: `classic-tui/src/handlers/settings_handler.rs`

- [ ] **Improve save/load**
  - Save on change vs. explicit save
  - Validation before save
  - Error handling for corrupted YAML
  - Files: `classic-tui/src/handlers/settings_handler.rs`

### Phase 5: Articles/Resources Screen
**Goal:** Add help resources and documentation access.

#### 5.1 Articles Screen UI
- [ ] **Create articles browser screen**
  - Add to `UiState` enum
  - Categorized list layout
  - Navigation (F10 key)
  - Files: `classic-tui/src/ui/articles_screen.rs`

- [ ] **Organize articles by category**
  - Installation guides
  - Common issues
  - Advanced topics
  - Keyboard shortcuts reference
  - Files: `classic-tui/src/ui/articles_screen.rs`

#### 5.2 Article Content
- [ ] **Implement article viewer**
  - Markdown rendering in terminal
  - Scrollable content
  - Code block highlighting
  - Files: `classic-tui/src/widgets/article_viewer.rs`

- [ ] **Add external link support**
  - Detect URLs in articles
  - Open in system browser
  - Confirmation before opening
  - Use `open` crate
  - Files: `classic-tui/src/handlers/article_handler.rs`

### Phase 6: Advanced Features
**Goal:** Add polish and quality-of-life features.

#### 6.1 Update Checking
- [ ] **Implement update checker**
  - Port `UpdateManager` logic
  - GitHub API integration
  - Version comparison
  - Files: `classic-tui/src/handlers/update_handler.rs`

- [ ] **Add update notification UI**
  - Non-intrusive notification
  - Show update details
  - Open release page option
  - Files: `classic-tui/src/ui/update_notification.rs`

#### 6.2 Enhanced Error Dialogs
- [ ] **Create error dialog widget**
  - Port `CustomErrorDialog` design
  - Show error title, message, details
  - Copy to clipboard support
  - Files: `classic-tui/src/widgets/error_dialog.rs`

- [ ] **Add clipboard integration**
  - Copy error text
  - Copy report content
  - System clipboard support
  - Use `clipboard` crate
  - Files: `classic-tui/src/handlers/clipboard_handler.rs`

#### 6.3 Configuration Persistence
- [ ] **Add window state persistence**
  - Remember last active screen
  - Remember scroll positions
  - Remember selected items
  - Files: `classic-tui/src/state/persistence.rs`

- [ ] **Implement session recovery**
  - Restore interrupted scans
  - Restore file positions
  - Files: `classic-tui/src/state/session.rs`

### Phase 7: Polish and Optimization
**Goal:** Refinement and performance optimization.

#### 7.1 UI Polish
- [ ] **Improve visual feedback**
  - Loading spinners
  - Progress bars for all operations
  - Status messages
  - Files: Various UI modules

- [ ] **Add keyboard shortcuts help**
  - Context-sensitive help
  - Comprehensive shortcut list
  - Quick reference overlay (?)
  - Files: `classic-tui/src/ui/help_overlay.rs`

- [ ] **Implement themes**
  - Color scheme support
  - High-contrast mode
  - Custom color configuration
  - Files: `classic-tui/src/ui/theme.rs`

#### 7.2 Performance Optimization
- [ ] **Optimize rendering**
  - Lazy loading for large lists
  - Incremental rendering
  - Efficient diff updates
  - Files: Various UI modules

- [ ] **Optimize file operations**
  - Use Rust acceleration throughout
  - Batch operations
  - Async I/O
  - Files: `classic-tui/src/handlers/`

#### 7.3 Testing
- [ ] **Add integration tests**
  - Screen navigation
  - Scan operations
  - Settings persistence
  - Files: `classic-tui/tests/integration/`

- [ ] **Add UI tests**
  - Widget behavior
  - Keyboard handling
  - Layout calculations
  - Files: `classic-tui/tests/ui/`

## Implementation Priority Matrix

### Critical Path (Must Have for 1.0)
1. ✅ Folder management (Phase 1.1)
2. ✅ Papyrus monitoring (Phase 1.2)
3. ✅ Scan operations (Phase 1.3)
4. ✅ Backup operations (Phase 2)
5. ✅ Results viewer foundation (Phase 3.1, 3.2)

### High Priority (Should Have for 1.0)
1. Settings enhancement (Phase 4)
2. Error dialogs (Phase 6.2)
3. File watching (Phase 3.3)

### Medium Priority (Nice to Have)
1. Articles screen (Phase 5)
2. Update checking (Phase 6.1)
3. UI polish (Phase 7.1)

### Low Priority (Future Enhancements)
1. Themes (Phase 7.1)
2. Session recovery (Phase 6.3)
3. Advanced optimizations (Phase 7.2)

## Technical Dependencies

### Rust Crates Needed
- ✅ `ratatui` - Terminal UI framework (already included)
- ✅ `crossterm` - Terminal control (already included)
- ✅ `tokio` - Async runtime (already included)
- ✅ `classic-*-core` - Business logic crates (already available)
- [ ] `notify` - File system watching (NEW)
- [ ] `clipboard` - System clipboard access (NEW)
- [ ] `open` - Open URLs in browser (NEW)
- [ ] `reqwest` - HTTP client for update checks (NEW)
- [ ] `pulldown-cmark` - Markdown parsing for articles (NEW)

### Integration Points
- ✅ `classic_scanlog_core` - Log parsing
- ✅ `classic_file_io_core` - File I/O
- ✅ `classic_database_core` - FormID lookups
- ✅ `classic_yaml_core` - Configuration
- ✅ `classic_config_core` - Settings management

## Success Metrics

### Feature Completeness
- **100%** of Python GUI main tab features
- **100%** of backup operations
- **90%+** of results viewer features (pastebin may be deferred)
- **80%+** of settings options

### User Experience
- **Sub-50ms** UI response time
- **Consistent** keyboard navigation across all screens
- **Clear** visual feedback for all actions
- **Helpful** error messages

### Code Quality
- **80%+** test coverage for new code
- **Zero** compiler warnings
- **Comprehensive** inline documentation
- **Clean** architecture following Rust best practices

## Notes

### Differences from Python GUI (Intentional)
1. **TUI-specific adaptations:**
   - No window geometry (terminal-based)
   - No audio notifications (terminal limitation)
   - Simplified dialogs (terminal constraints)
   - Keyboard-only navigation

2. **Improvements over GUI:**
   - Faster startup (Rust vs. Python)
   - Lower memory usage
   - SSH-friendly (no X11 required)
   - Better scriptability

### Future Enhancements (Beyond Feature Parity)
1. **Mouse support** - Optional mouse interaction
2. **Color customization** - User-defined color schemes
3. **Macro recording** - Record and replay command sequences
4. **Plugin system** - Extensibility for custom features
5. **Remote monitoring** - Monitor scans from SSH session

## Conclusion

This plan provides a clear roadmap to bring `classic-tui` to feature parity with the Python GUI while maintaining TUI-appropriate design choices. The phased approach allows for incremental development and testing, ensuring quality at each stage.

**Estimated Total Implementation Time:** 4-6 weeks for critical path + high priority items.

**Current Progress:** ~25% (basic scaffolding complete)

**Next Steps:** Begin Phase 1.1 (Folder Management) implementation.
