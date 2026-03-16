## ADDED Requirements

### Requirement: Native frontends support targeted crash-log scans
The native CLASSIC frontends SHALL support a targeted scan mode that scopes a run to user-selected crash-log files or directories instead of the standard managed-directory discovery flow.

#### Scenario: GUI scan starts from dropped inputs
- **WHEN** a user drops one or more crash-log files or directories into the GUI and starts a crash-log scan
- **THEN** the GUI SHALL resolve those dropped inputs for that run and SHALL scan only the logs produced from that explicit selection

#### Scenario: CLI scan starts from explicit path arguments
- **WHEN** a user invokes `classic-cli` with one or more explicit crash-log file or directory paths
- **THEN** the CLI SHALL resolve those path arguments for that run and SHALL scan only the logs produced from that explicit selection

### Requirement: Explicit input resolution is deterministic and bounded
The targeted-input resolver SHALL expand explicit inputs into a stable deduplicated list of crash logs without silently widening scan scope beyond what the user selected.

#### Scenario: Directory input expands matching logs recursively
- **WHEN** a targeted input is a directory
- **THEN** the resolver SHALL search that directory recursively for files matching the supported crash-log pattern and SHALL exclude unrelated files

#### Scenario: Duplicate selections do not produce duplicate scans
- **WHEN** the same crash log is selected more than once, including through both a direct file path and a parent directory
- **THEN** the resolver SHALL include that log only once in the final scan list while preserving first-seen order for the remaining logs

#### Scenario: Invalid targeted inputs are surfaced without widening scope
- **WHEN** one or more targeted inputs are unreadable, missing, or do not resolve to supported crash logs
- **THEN** the frontend SHALL surface those rejected inputs to the user and SHALL continue only with the valid resolved logs

### Requirement: GUI targeted-input state is visible and ephemeral
The GUI SHALL present targeted-input state separately from the persisted Custom Scan Folder setting and SHALL allow the user to clear that state before returning to standard discovery.

#### Scenario: Dropped inputs remain visible before scan start
- **WHEN** a user drops files or directories into the GUI
- **THEN** the GUI SHALL show that a targeted selection is pending and SHALL indicate what will be scanned before the scan begins

#### Scenario: Clearing targeted inputs restores normal discovery
- **WHEN** a user clears the pending targeted selection
- **THEN** subsequent GUI scans SHALL return to the standard discovery workflow, including any saved Custom Scan Folder behavior

### Requirement: CLI explicit paths preserve legacy compatibility boundaries
The native CLI SHALL keep the existing `--scan-path` directory workflow available while adding explicit targeted path arguments.

#### Scenario: Legacy directory override remains supported
- **WHEN** a user invokes `classic-cli --scan-path <directory>` without explicit targeted path arguments
- **THEN** the CLI SHALL continue the existing directory-based discovery workflow for that run

#### Scenario: Mixed targeted and legacy path modes are rejected
- **WHEN** a user invokes `classic-cli` with both explicit targeted path arguments and `--scan-path`
- **THEN** the CLI SHALL reject the invocation before scanning and SHALL report that the path-selection modes cannot be combined

### Requirement: Targeted scans preserve in-place report generation
Targeted crash-log scans SHALL write `-AUTOSCAN.md` reports adjacent to the resolved source logs instead of relocating those logs into the managed `Crash Logs` directory first.

#### Scenario: Explicitly selected external log keeps adjacent report output
- **WHEN** a targeted scan succeeds for a crash log located outside the managed `Crash Logs` directory
- **THEN** CLASSIC SHALL write the generated `-AUTOSCAN.md` report next to that source log
