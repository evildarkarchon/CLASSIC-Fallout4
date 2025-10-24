# TUI Feature Parity Implementation Plan

This document outlines a phased approach to bring the Rust TUI (`classic-tui`) to feature parity with the Python GUI (`CLASSIC_Interface.py`).

**IMPORTANT**: The Rust TUI is a **pure Rust application** that uses only the `-core` crates (business logic). It does NOT depend on Python or PyO3 bindings. If functionality is needed that doesn't exist in a `-core` crate yet, it must be implemented in Rust first before being used in the TUI.

## Architectural Overview

### Pure Rust Design Principles

The Rust TUI follows a fundamentally different architecture from the Python GUI:

**Python GUI Architecture:**
```
Python Application → PyO3 Bindings (-py crates) → Business Logic (-core crates)
```

**Rust TUI Architecture:**
```
Rust TUI → Business Logic (-core crates directly)
```

### Key Advantages

1. **No FFI Overhead**: Direct Rust function calls, no Python-Rust boundary crossing
2. **No Python Runtime**: Runs completely standalone, no Python installation required
3. **Better Performance**: No GIL, no type conversions, no PyO3 overhead
4. **Smaller Binary**: No Python interpreter bundled
5. **Better Error Messages**: Native Rust error handling throughout

### Implementation Guidelines

**✅ DO:**
- Use `-core` crates directly (`classic-scanlog-core`, `classic-file-io-core`, etc.)
- Implement missing functionality in appropriate `-core` crate first
- Share Tokio runtime via `classic-shared::get_runtime()`
- Follow Rust 2024 patterns and idioms
- Use proper async/await patterns throughout

**❌ DON'T:**
- Import any Python code or PyO3 bindings
- Reference `ClassicLib.*` modules (those are Python-only)
- Use `-py` crates (those are PyO3 bindings for Python)
- Try to "port" Python code directly (redesign in idiomatic Rust instead)
- Block the UI thread with long-running operations

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
   - ❌ Audio notifications (skip, not wanted in TUI)
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
  - Persist to YAML configuration using `classic-yaml-core`
  - Use `classic-config-core::ClassicConfig` for configuration management
  - Files: `classic-tui/src/handlers/folder_handler.rs`

- [ ] **Add folder validation**
  - **REQUIRES**: Path validation logic in `classic-file-io-core` or `classic-scanlog-core`
  - Implement Rust equivalent of path validation (check if directory exists, is readable, etc.)
  - Display validation errors in TUI
  - Prevent invalid selections
  - Files: `classic-tui/src/validators/path_validator.rs`

#### 1.2 Papyrus Monitoring (Priority: HIGH)
- [ ] **Implement real-time log monitoring**
  - **REQUIRES**: Papyrus monitoring functionality in `classic-scanlog-core`
  - If not available, implement Papyrus log parsing and monitoring in `classic-scanlog-core` first
  - Use `notify` crate for async file watching
  - Integrate with Tokio runtime from `classic-shared`
  - Files: `classic-scanlog-core/src/papyrus.rs` (if new), `classic-tui/src/handlers/papyrus_handler.rs`

- [ ] **Connect stats calculation**
  - Parse dumps, stacks, warnings, errors from Papyrus logs
  - Calculate error/warning ratio
  - Update timestamp on changes
  - Use stats calculation from `classic-scanlog-core` if available
  - Files: `classic-tui/src/handlers/papyrus_handler.rs`, `classic-tui/src/ui/papyrus_screen.rs`

- [ ] **Add real-time stats display**
  - Color-coded status indicators (green/yellow/red based on error rate)
  - Auto-refresh display on file changes
  - Scrollable log output with syntax highlighting
  - Files: `classic-tui/src/ui/papyrus_screen.rs`

#### 1.3 Scan Operations Enhancement (Priority: MEDIUM)
- [ ] **Implement proper scan handlers**
  - Use `classic-scanlog-core::orchestrator` for crash log scanning orchestration
  - Use `classic-scanlog-core::parser` for log parsing
  - Use `classic-file-io-core` for file I/O operations
  - Use `classic-database-core` for FormID lookups
  - Emit progress updates to UI via channels or callbacks
  - Handle errors gracefully with proper error types
  - Files: `classic-tui/src/handlers/scan_handler.rs`

- [ ] **Add scan results display**
  - Show summary statistics (files scanned, patterns matched)
  - Display matched patterns with context
  - Show resolved FormIDs from database lookups
  - List suspect mods/plugins
  - Format output similar to Python GUI reports
  - Files: `classic-tui/src/ui/results_screen.rs`

- [ ] **Implement error handling**
  - Create error dialog widget for TUI
  - Display detailed error messages from `classic-shared::errors`
  - Show error context (file path, operation, etc.)
  - Offer retry options where applicable
  - Allow copying error details to clipboard
  - Files: `classic-tui/src/ui/error_dialog.rs`, `classic-tui/src/widgets/error_dialog.rs`

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
- [ ] **Implement backup functionality in Rust**
  - **REQUIRES**: Backup/restore logic in `classic-file-io-core` or new module
  - If not available, implement in `classic-file-io-core::backup` module:
    - Backup creation (copy files to backup directory with timestamps)
    - Restore from backup (copy files back to original location)
    - Backup removal (delete backup directory)
    - Backup validation (check integrity before restore)
  - Handle XSE, ReShade, Vulkan, and ENB file patterns
  - Files: `classic-file-io-core/src/backup.rs` (if new), `classic-tui/src/handlers/backup_handler.rs`

- [ ] **Add backup existence checking**
  - Scan backup directories on startup
  - Check for valid backups of each type (XSE, ReShade, Vulkan, ENB)
  - Enable/disable restore buttons based on availability
  - Update UI state with backup status
  - Files: `classic-tui/src/handlers/backup_handler.rs`

- [ ] **Implement operation feedback**
  - Progress indicators for large file operations
  - Success/failure messages with details
  - Confirmation dialogs before destructive operations
  - Use async operations to avoid blocking UI
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
  - Sort by filename in descending order (avoids parallel scanning metadata issues).
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

#### 3.3 File Watching (Advanced) (Skip, too complex, stick with refresh after scan and manual refresh)
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
  - **REQUIRES**: Update checking logic in Rust
  - Use `reqwest` crate for GitHub API calls
  - Implement version comparison logic
  - Check latest release from GitHub repository
  - Parse version strings and compare with current version
  - Files: `classic-tui/src/handlers/update_handler.rs`

- [ ] **Add update notification UI**
  - Non-intrusive notification banner or popup
  - Show update details (version, release notes summary)
  - Open release page in browser option (use `open` crate)
  - Dismiss notification capability
  - Files: `classic-tui/src/ui/update_notification.rs`

#### 6.2 Enhanced Error Dialogs
- [ ] **Create error dialog widget**
  - Design TUI-appropriate error dialog layout
  - Show error title, message, and detailed information
  - Stack trace display when available
  - Copy to clipboard support (press 'C' to copy)
  - Scrollable error details for long messages
  - Color-coded severity (error=red, warning=yellow, info=blue)
  - Files: `classic-tui/src/widgets/error_dialog.rs`

- [ ] **Add clipboard integration**
  - Copy error text with full context
  - Copy report content to clipboard
  - System clipboard support using `clipboard` or `arboard` crate
  - Visual confirmation when copied
  - Fallback message if clipboard unavailable
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

#### 7.4 Documentation Audit
- [ ] **Document all existing code**
  - Audit all existing `classic-tui` source files for missing documentation
  - Add `///` doc comments to all public items (structs, enums, functions, fields, variants)
  - Follow [Rust Documentation Standards](../CLAUDE.md#rust-documentation-standards)
  - Verify zero documentation warnings: `cargo check -p classic-tui 2>&1 | grep "missing documentation"`
  - **CRITICAL**: This is a required task - all existing code must be documented before 1.0 release
  - Files: All files in `classic-tui/src/`

- [ ] **Add crate-level documentation**
  - Add comprehensive `//!` documentation to `main.rs` and `lib.rs`
  - Document module purposes in each `mod.rs`
  - Include usage examples where appropriate
  - Files: `classic-tui/src/main.rs`, `classic-tui/src/lib.rs`, all `mod.rs` files

## Implementation Priority Matrix

### Critical Path (Must Have for 1.0)
1. ✅ Folder management (Phase 1.1)
2. ✅ Papyrus monitoring (Phase 1.2)
3. ✅ Scan operations (Phase 1.3)
4. ✅ Backup operations (Phase 2)
5. ✅ Results viewer foundation (Phase 3.1, 3.2)

### High Priority (Should Have for 1.0)
1. Documentation audit for all existing code (Phase 7.4) - **REQUIRED**
2. Settings enhancement (Phase 4)
3. Error dialogs (Phase 6.2)
4. File watching (Phase 3.3)

### Medium Priority (Nice to Have)
1. Articles screen (Phase 5)
2. Update checking (Phase 6.1)
3. UI polish (Phase 7.1)

### Low Priority (Future Enhancements)
1. Themes (Phase 7.1)
2. Session recovery (Phase 6.3)
3. Advanced optimizations (Phase 7.2)

## Technical Dependencies

### Architecture Notes
**The Rust TUI is a pure Rust application** that:
- Uses ONLY the `-core` crates (business logic) - NO Python or PyO3
- Accesses business logic directly without FFI overhead
- Can run completely standalone without Python installation
- Shares the global Tokio runtime via `classic-shared::get_runtime()`

**If functionality is missing from `-core` crates:**
1. Implement it in the appropriate `-core` crate first (e.g., `classic-scanlog-core`, `classic-file-io-core`)
2. Ensure it follows pure Rust patterns (no PyO3 dependencies)
3. Document the new functionality following Rust Documentation Standards
4. Then integrate it into the TUI

### Rust Crates Needed
**Already Available:**
- ✅ `ratatui` - Terminal UI framework
- ✅ `crossterm` - Terminal control
- ✅ `tokio` - Async runtime (shared via `classic-shared`)
- ✅ `classic-scanlog-core` - Log parsing, pattern matching, FormID analysis
- ✅ `classic-file-io-core` - File I/O, encoding detection, DDS parsing
- ✅ `classic-database-core` - SQLite connection pooling, FormID lookups
- ✅ `classic-yaml-core` - YAML operations (yaml-rust2)
- ✅ `classic-config-core` - Configuration management
- ✅ `classic-shared` - Runtime, errors, utilities

**To Be Added:**
- [ ] `notify` - File system watching for Papyrus monitor and results viewer
- [ ] `arboard` - System clipboard access (more reliable than `clipboard` crate)
- [ ] `open` - Open URLs in browser for articles
- [ ] `reqwest` - HTTP client for update checks (with rustls-tls feature)
- [ ] `pulldown-cmark` - Markdown parsing for articles viewer

**May Need Implementation in `-core` crates:**
- [ ] Path validation in `classic-file-io-core` or `classic-scanlog-core`
- [ ] Papyrus log monitoring in `classic-scanlog-core::papyrus`
- [ ] Backup/restore operations in `classic-file-io-core::backup`

### Integration Points (Pure Rust)
- ✅ `classic-scanlog-core::orchestrator` - Log scanning orchestration
- ✅ `classic-scanlog-core::parser` - Log parsing
- ✅ `classic-scanlog-core::formid` - FormID analysis
- ✅ `classic-scanlog-core::patterns` - Pattern matching
- ✅ `classic-file-io-core::core` - File I/O operations
- ✅ `classic-file-io-core::encoding` - Encoding detection
- ✅ `classic-database-core::pool_sqlx` - Database pool management
- ✅ `classic-yaml-core` - YAML operations
- ✅ `classic-config-core::ClassicConfig` - Configuration management
- ✅ `classic-shared::runtime::get_runtime()` - Shared async runtime

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
- **Complete documentation** for all public items following [Rust Documentation Standards](../CLAUDE.md#rust-documentation-standards)
  - All `pub struct`, `pub enum`, `pub fn`, `pub mod` must have `///` doc comments
  - All public struct fields and enum variants must be documented
  - **CRITICAL**: All existing code that remains must be documented to these standards
  - Missing documentation warnings are treated as errors
- **Clean** architecture following Rust best practices

## Notes

### Documentation Requirements (CRITICAL)

**All existing code that remains in `classic-tui` must be fully documented** according to the [Rust Documentation Standards](../CLAUDE.md#rust-documentation-standards) defined in CLAUDE.md. This is a **non-negotiable requirement** for the 1.0 release.

**Key requirements:**
- All `pub struct`, `pub enum`, `pub fn`, `pub mod` must have `///` doc comments
- All public struct fields and enum variants must be documented
- Crate-level (`//!`) documentation required in `main.rs`, `lib.rs`, and module files
- Follow Rust API Guidelines for documentation style
- Missing documentation warnings are treated as errors
- Verify with: `cargo check -p classic-tui 2>&1 | grep "missing documentation"`

**Why this matters:**
- Maintains code quality standards across the entire CLASSIC project
- Ensures maintainability for future contributors
- Provides in-editor documentation via rust-analyzer
- Required for professional-grade Rust projects

See [Phase 7.4: Documentation Audit](#74-documentation-audit) for implementation details.

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
