## Why

The Results tab's `Open Folder` action should help users act on the report they have selected, but today that action can behave like a generic crash-log shortcut and land in the default report location instead of the directory that actually contains the selected report. This is especially confusing when the selected report lives in a custom scan/report directory, because the user asked to open one report and Explorer appears somewhere else.

## What Changes

- Make the Results tab `Open Folder` action reveal the selected report file in the platform file browser when the selected report exists.
- If direct file selection is unavailable, fall back to opening the selected report's containing folder instead of jumping straight to the default crash-log directory.
- Only fall back to the primary Results report directory when there is no valid selected report path or the selected report no longer exists.
- Add or update GUI controller tests that cover selected-report reveal, no-selection fallback, and missing-file fallback behavior.
- Keep the change confined to the Qt GUI results flow; no Rust workspace, bridge, CLI, TUI, Python, or Node binding behavior changes.

## Capabilities

### New Capabilities
- `results-report-folder-reveal`: Defines how the Qt Results tab resolves the `Open Folder` action for a selected report, including file reveal behavior and fallback rules when the selected file cannot be revealed.

### Modified Capabilities
<!-- None. There is no existing OpenSpec capability covering Results-tab report-folder navigation. -->

## Impact

- **Affected code**: `classic-gui/src/controllers/resultscontroller.cpp`, `classic-gui/src/controllers/resultscontroller.h`, `classic-gui/src/widgets/reportlistwidget.cpp`, and `classic-gui/tests/test_resultscontroller.cpp`.
- **Affected systems**: The Qt desktop GUI (`classic-gui/`) and its interaction with the platform file browser (`explorer.exe` on Windows, `QDesktopServices` fallback elsewhere).
- **APIs and bindings**: None. No public Rust, CXX bridge, Python, or Node API contract changes.
- **Dependencies**: No new third-party dependency; uses existing Qt facilities (`QProcess`, `QDesktopServices`, `QFileInfo`, `QDir`).
- **Risk**: Low and frontend-local. The main risk is incorrect fallback ordering causing Explorer to open the wrong directory when a selected report path is stale or empty.
