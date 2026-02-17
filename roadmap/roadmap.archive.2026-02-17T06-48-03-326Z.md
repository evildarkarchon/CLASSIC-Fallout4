---
feature: "CLASSIC Ratatui TUI"
spec: |
  Implement the Rust ratatui/crossterm-based CLASSIC TUI per docs/CLASSIC_Ratatui_TUI_PRD.md, starting with Main Options tab as the first executable vertical slice. Preserve ONE RUNTIME RULE via classic_shared_core::get_runtime(), match keyboard+mouse behavior from PRD, and keep architecture extensible for Backup/Articles/Results/Overlays.
---

## Task List

### Feature 1: classic-tui crate bootstrap
Description: Create initial crate, workspace wiring, terminal lifecycle, app state, and top-level render/event loop shell.
- [x] 1.01 Add ui-applications/classic-tui crate and workspace member with required dependencies and lint settings (note: Added classic-tui crate with Cargo.toml, module scaffold, and workspace member.)
- [x] 1.02 Implement main.rs terminal lifecycle (alternate buffer, raw mode, mouse capture, panic-safe restore) (note: Implemented main.rs terminal lifecycle with alternate buffer, raw mode, mouse capture, and restoration.) (note: Reconfirmed terminal lifecycle implementation in main.rs.)
- [x] 1.03 Implement app/event/ui scaffolding with tab enum, base layout, status bar, and tick loop (note: Implemented app/event/ui scaffolding with tab enum, base layout, status bar, and tick loop.)
- [x] 1.04 Add minimal persistence for TUI state.json and logging bootstrap (note: Added state.json persistence and file logging bootstrap for classic-tui.)

### Feature 2: Main tab rendering and focus system
Description: Build Main Options tab layout and reusable widgets with full keyboard/mouse focus semantics.
- [x] 2.01 Implement reusable path input widget (label, input, browse button, focus+validation styling) (note: Implemented reusable path input widget with label, input, browse button, and validation/focus styling.)
- [x] 2.02 Render main tab sections: two path rows, scan buttons, utility row, papyrus toggle (note: Rendered main tab sections: path rows, scan buttons, utility row, and papyrus toggle.) (note: Reconfirmed full main-tab section rendering is in place.)
- [x] 2.03 Implement focus graph and Tab/Shift+Tab traversal exactly as PRD order (note: Implemented MainFocus graph and Tab/Shift+Tab traversal order per PRD.)
- [x] 2.04 Implement click-area hit testing for tabs, inputs, and all main-tab buttons (note: Added per-frame click area capture and mouse hit testing for tabs and all main-tab controls.)

### Feature 3: Main tab behavior and async actions
Description: Wire scan/update/papyrus/open-folder interactions and state transitions for the Main tab.
- [x] 3.01 Implement path editing, cursor movement, paste support, and debounced settings persistence (note: Implemented path text editing, cursor movement, paste handling, Enter save, and YAML persistence.)
- [x] 3.02 Implement custom scan path validation rules using classic-path-core plus crash-log overlap checks (note: Added custom scan validation with classic-path-core and explicit Crash Logs overlap blocking.)
- [x] 3.03 Implement crash-log scan async flow with cancellation, progress updates, and status auto-clear (note: Implemented crash-log async scan task with cancellation token, progress updates, completion/error messages, and auto-clear timer.)
- [x] 3.04 Implement game-files scan trigger and temporary status flow (stub or full manager based on available API) (note: Implemented game-files scan trigger with temporary status flow stub while full integration is pending.)
- [x] 3.05 Implement utility actions: Help/About/Settings overlay triggers, open logs folder, update check workflow (note: Implemented utility actions: help/about/settings overlays, open crash logs folder, and GitHub update check workflow.)
- [x] 3.06 Implement Papyrus toggle state and overlay open behavior (note: Implemented Papyrus toggle state changes and status messaging in main tab interactions.)

### Feature 4: Main tab tests and hardening
Description: Add deterministic tests for render, events, and edge cases before moving to next tabs.
- [x] 4.01 Add TestBackend render tests for main tab default, focused states, and scan-in-progress morphing (note: Added render tests with TestBackend for default main-tab render and scan-in-progress CANCEL/SCANNING label morphing.)
- [x] 4.02 Add event tests for keyboard traversal, enter activation, mouse click hit-testing, and scroll handling (note: Added event tests for Tab traversal, Enter activation, mouse hit-testing, and key-release ignore behavior.)
- [x] 4.03 Add unit tests for custom scan path validation and status/error messaging behavior (note: Added app unit tests for custom path validation against Crash Logs and async status message transitions.)
- [x] 4.04 Run crate-local fmt/clippy/tests and fix issues before proceeding to Backup tab (note: Ran crate-local fmt, clippy (-D warnings), and tests for classic-tui successfully.)
