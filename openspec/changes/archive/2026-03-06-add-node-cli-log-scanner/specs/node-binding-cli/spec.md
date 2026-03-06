## ADDED Requirements

### Requirement: Node binding CLI performs end-to-end crash log scans
The maintained Node bindings package SHALL provide a Node-native CLI whose default execution path performs real crash-log scanning through the maintained binding surface.

#### Scenario: Contributor runs the Node CLI with scan defaults
- **WHEN** a contributor invokes the packaged Node CLI without a subcommand from `ClassicLib-rs/node-bindings/classic-node`
- **THEN** the CLI resolves the required scan inputs, loads the native binding, and executes the crash-log scan workflow instead of only running a smoke test

#### Scenario: Binding load fails before scanning starts
- **WHEN** the CLI cannot load the native binding or initialize the required runtime/configuration state
- **THEN** it exits with a fatal non-zero status and reports the startup failure instead of silently succeeding

### Requirement: Node binding CLI mirrors the native scan workflow
The Node CLI SHALL follow the same core scan workflow as `classic-cli` for data discovery, log discovery, batch analysis, report generation, and run summaries.

#### Scenario: CLI resolves standard scan locations
- **WHEN** a contributor runs the CLI without a custom scan-path override
- **THEN** the CLI uses CLASSIC path conventions to resolve the data/config roots, derive the relevant docs or XSE scan folder, and search the managed crash-log locations used by the native CLI

#### Scenario: CLI scans a custom log directory
- **WHEN** a contributor provides `--scan-path <path>`
- **THEN** the CLI includes that directory in the scan workflow while preserving the rest of the standard CLASSIC scan behavior

#### Scenario: Successful scans generate reports
- **WHEN** the CLI successfully analyzes one or more crash logs
- **THEN** it writes `-AUTOSCAN.md` reports adjacent to the processed logs and prints a completion summary for the run

### Requirement: Node binding CLI supports native-style scan controls
The Node CLI SHALL support the core scan options needed to reproduce the official CLI workflow through the Node bindings.

#### Scenario: Contributor selects game and scan options
- **WHEN** a contributor passes options such as `--game`, `--game-version`, `--fcx-mode`, `--show-fid-values`, or `--simplify-logs`
- **THEN** the CLI applies those values to the binding-backed scan configuration for the run

#### Scenario: Contributor sets batch concurrency
- **WHEN** a contributor passes `--max-concurrent <n>`
- **THEN** the CLI bounds concurrent log processing for that run using supported binding-backed scan behavior instead of ignoring the option

#### Scenario: Contributor requests version output
- **WHEN** a contributor passes `--version`
- **THEN** the CLI prints version information and exits without starting a scan

### Requirement: Node binding CLI preserves native-style exit semantics
The Node CLI SHALL return stable exit codes that distinguish successful runs, partial scan failures, and fatal startup/configuration failures.

#### Scenario: No logs are found
- **WHEN** the CLI completes discovery and finds no crash logs to scan
- **THEN** it reports that no logs were found and exits with status `0`

#### Scenario: One or more log scans fail but the run completes
- **WHEN** the CLI finishes the batch and at least one log result reports a scan error
- **THEN** it reports the completed run and exits with status `1`

#### Scenario: Startup or configuration fails before batch completion
- **WHEN** the CLI cannot complete required startup, path resolution, or configuration loading for the scan run
- **THEN** it exits with status `2`

### Requirement: Node binding CLI remains usable for automation and diagnostics
The maintained Node bindings package SHALL expose the CLI through package-managed invocation paths and support automation-friendly diagnostics or structured output.

#### Scenario: Contributor runs the packaged CLI entrypoint
- **WHEN** a contributor invokes the documented package script or package binary entry for the Node CLI
- **THEN** the command launches the maintained `classic-node` CLI without requiring a custom shell wrapper

#### Scenario: Automation requests structured results or diagnostics
- **WHEN** a contributor or CI workflow requests machine-readable output or runtime diagnostics from the Node CLI
- **THEN** the CLI emits structured scan or startup information suitable for scripting and troubleshooting
