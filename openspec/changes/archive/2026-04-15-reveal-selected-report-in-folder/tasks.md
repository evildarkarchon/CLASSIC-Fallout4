## 1. Results action routing

- [x] 1.1 Confirm `ReportListWidget` emits the currently selected report path for `openFolderRequested` and does not substitute a default directory on its own.
- [x] 1.2 Update `ResultsController::onOpenFolder()` to prefer the selected existing report file as the primary target for the `Open Folder` action.
- [x] 1.3 If direct file reveal is unavailable, open the selected report's containing folder before considering any report-directory fallback.
- [x] 1.4 Preserve deterministic fallback ordering for invalid selections: primary report directory first, then the first configured report directory, otherwise no browser launch.

## 2. Platform browser integration

- [x] 2.1 Keep `revealFileInFileBrowser()` and `openFolderInFileBrowser()` as the controller seams for browser launches so the behavior stays testable.
- [x] 2.2 Ensure the Windows reveal path uses `explorer.exe` with `/select,<native path>` so Explorer highlights the selected report file.
- [x] 2.3 Ensure the non-Windows fallback opens the selected report's containing directory rather than failing the action outright.

## 3. Verification

- [x] 3.1 Add or update `classic-gui/tests/test_resultscontroller.cpp` to cover revealing a selected report located outside the primary report directory.
- [x] 3.2 Add or update controller tests for the no-selection and missing-selected-file fallback paths.
- [x] 3.3 Add or update a controller test that verifies no browser launch occurs when there is no valid selected report and no configured report directory.
- [x] 3.4 Run the relevant `classic-gui` test target and manually verify on Windows that clicking `Open Folder` highlights the selected report in Explorer.
