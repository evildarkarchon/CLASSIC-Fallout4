## ADDED Requirements

### Requirement: Results tab reveals the selected report file

The Qt desktop GUI SHALL treat the currently selected Results-tab report as the primary target of the `Open Folder` action.

When the selected report path is non-empty, exists, and points to a file, the GUI SHALL ask the platform file browser to reveal that exact file. On platforms where direct file selection is unavailable or fails, the GUI SHALL open the containing folder of the selected report instead.

#### Scenario: Selected report in a custom report directory is revealed
- **WHEN** the user selects a report whose file path is `D:/Some Custom Reports/crash-2025-03-01-00-00-00-AUTOSCAN.md` and clicks `Open Folder`
- **THEN** the GUI attempts to reveal `D:/Some Custom Reports/crash-2025-03-01-00-00-00-AUTOSCAN.md` in the platform file browser
- **AND** the GUI does not jump directly to the default crash-log directory

#### Scenario: File-selection fallback opens the selected report directory
- **WHEN** the user clicks `Open Folder` for an existing selected report but platform-specific file reveal is unavailable
- **THEN** the GUI opens the containing directory of the selected report
- **AND** the containing directory matches the parent folder of the selected report file

### Requirement: Results tab uses deterministic fallback when the selected report is unavailable

If the Results-tab `Open Folder` action is triggered with no valid selected report file, the GUI SHALL fall back to the primary report directory. If no primary report directory is configured, it SHALL fall back to the first configured report directory. If no report directories are configured, the GUI SHALL not attempt to open an arbitrary or inferred folder.

The GUI MUST NOT prefer the primary report directory over a valid selected report file.

#### Scenario: No selection falls back to the primary report directory
- **WHEN** the user clicks `Open Folder` and there is no current report selection
- **THEN** the GUI opens the configured primary report directory

#### Scenario: Missing selected file falls back to the primary report directory
- **WHEN** the user had selected a report but that report file no longer exists when `Open Folder` is clicked
- **THEN** the GUI opens the configured primary report directory
- **AND** the GUI does not attempt to reveal the missing file path

#### Scenario: No configured report directories results in no browser launch
- **WHEN** the user clicks `Open Folder`, there is no valid selected report file, and the controller has no configured report directories
- **THEN** the GUI does not launch the platform file browser
- **AND** the action completes without opening an unrelated folder
