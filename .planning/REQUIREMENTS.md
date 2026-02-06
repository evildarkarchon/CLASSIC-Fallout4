# Requirements: CLASSIC v9.0.0 Slint GUI

**Defined:** 2026-02-05
**Core Value:** Rust-native GUI using Slint -- all business logic and UI in Rust, no Python dependency

## v9.0.0 Requirements

Requirements for Slint GUI core workflow. Each maps to roadmap phases.

### Infrastructure

- [x] **INFRA-01**: Slint 1.15.0 crate created in rust/ui-applications/classic-gui/
- [x] **INFRA-02**: Build system configured with slint-build and Skia renderer
- [x] **INFRA-03**: Async bridge connects Slint UI to existing Tokio runtime
- [x] **INFRA-04**: Worker thread pattern established for long-running operations
- [x] **INFRA-05**: Application launches and displays main window

### Core UI

- [x] **UI-01**: Main window with application title and icon
- [x] **UI-02**: Dark theme applied (fluent-dark style)
- [x] **UI-03**: Tabbed interface with Main Options and Results tabs
- [x] **UI-04**: Standard controls render correctly (buttons, inputs, checkboxes)
- [x] **UI-05**: Window resizing works with proper layout

### Scanning

- [x] **SCAN-01**: User can trigger crash log scan from main tab
- [x] **SCAN-02**: Progress indicator shows scan progress with percentage
- [x] **SCAN-03**: User can cancel running scan
- [x] **SCAN-04**: Scan completion displays summary (logs scanned, issues found)
- [x] **SCAN-05**: Scan integrates with existing OrchestratorCore via async bridge

### Results Viewer

- [x] **RSLT-01**: Report list displays available scan reports
- [x] **RSLT-02**: Report list shows timestamp, status, and file size
- [x] **RSLT-03**: User can search/filter report list
- [x] **RSLT-04**: Selecting report displays content in viewer panel
- [x] **RSLT-05**: Markdown content renders with proper formatting (headers, lists, code blocks)
- [x] **RSLT-06**: Report viewer supports scrolling for long reports
- [x] **RSLT-07**: User can copy text from report viewer

### Settings

- [x] **SETT-01**: Settings tab accessible from main tab widget
- [x] **SETT-02**: Settings tab has sub-tabbed layout (General, Scanning, Paths)
- [x] **SETT-03**: User can select game version from dropdown
- [x] **SETT-04**: User can configure scan options (switches)
- [x] **SETT-05**: User can browse and set folder paths (using rfd file dialogs)
- [x] **SETT-06**: Settings persist via ClassicConfig YAML save-on-change
- [x] **SETT-07**: Live save-on-change with Reset to Defaults (replaces OK/Cancel per design decision)

### Platform

- [x] **PLAT-01**: Application runs on Windows 10/11
- [x] **PLAT-02**: Application handles high-DPI displays correctly
- [x] **PLAT-03**: GPU renderer fallback to software if needed

## Future Requirements (v9.1.0+)

Deferred to subsequent milestones. Not in current roadmap.

### File Backup Tab
- **BKUP-01**: User can backup XSE/ENB/ReShade files
- **BKUP-02**: User can restore backed up files
- **BKUP-03**: User can remove mod framework files

### Articles Tab
- **ARTC-01**: Grid of resource links
- **ARTC-02**: Links open in default browser

### Game File Scanning
- **GAME-01**: User can trigger game file scan
- **GAME-02**: Game file scan results displayed

### Papyrus Monitoring
- **PAPY-01**: User can start/stop Papyrus monitoring
- **PAPY-02**: Monitoring dialog shows live statistics

### Additional Features
- **MISC-01**: About dialog
- **MISC-02**: Update checking
- **MISC-03**: Pastebin log fetch

## Out of Scope

| Feature | Reason |
|---------|--------|
| PySide6/Qt replacement in v9.0.0 | Slint GUI runs alongside Qt initially; deprecation in v9.1.0+ |
| egui/iced frameworks | Slint chosen for declarative syntax |
| Runtime theme switching | Slint limitation -- style is compile-time |
| Native markdown in Slint | Experimental feature; using pulldown-cmark instead |
| Linux/macOS support | Windows-first; cross-platform in future |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 19 | Complete |
| INFRA-02 | Phase 19 | Complete |
| INFRA-03 | Phase 19 | Complete |
| INFRA-04 | Phase 19 | Complete |
| INFRA-05 | Phase 19 | Complete |
| UI-01 | Phase 20 | Complete |
| UI-02 | Phase 20 | Complete |
| UI-03 | Phase 20 | Complete |
| UI-04 | Phase 20 | Complete |
| UI-05 | Phase 20 | Complete |
| SCAN-01 | Phase 21 | Complete |
| SCAN-02 | Phase 21 | Complete |
| SCAN-03 | Phase 21 | Complete |
| SCAN-04 | Phase 21 | Complete |
| SCAN-05 | Phase 21 | Complete |
| RSLT-01 | Phase 22 | Complete |
| RSLT-02 | Phase 22 | Complete |
| RSLT-03 | Phase 22 | Complete |
| RSLT-04 | Phase 22 | Complete |
| RSLT-05 | Phase 23 | Complete |
| RSLT-06 | Phase 22 | Complete |
| RSLT-07 | Phase 22 | Complete |
| SETT-01 | Phase 24 | Complete |
| SETT-02 | Phase 24 | Complete |
| SETT-03 | Phase 24 | Complete |
| SETT-04 | Phase 24 | Complete |
| SETT-05 | Phase 24 | Complete |
| SETT-06 | Phase 24 | Complete |
| SETT-07 | Phase 24 | Complete |
| PLAT-01 | Phase 25 | Complete |
| PLAT-02 | Phase 25 | Complete |
| PLAT-03 | Phase 25 | Complete |

**Coverage:**
- v9.0.0 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0

---
*Requirements defined: 2026-02-05*
*Last updated: 2026-02-06 -- Phase 25 complete*
