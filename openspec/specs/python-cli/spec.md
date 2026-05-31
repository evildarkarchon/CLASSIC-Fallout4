## Purpose

Define the maintained Python binding CLI behavior for binding-backed workflows, diagnostics, compliance discovery, stable automation output, and process-level validation.

## Requirements

### Requirement: Python CLI exposes maintained invocation paths
The maintained Python binding workspace SHALL provide a Python CLI named `classic-py` and a module entry point named `classic_py_cli` for running CLASSIC binding-backed workflows.

#### Scenario: Contributor runs the console script
- **WHEN** a contributor invokes `uv run --project python-bindings classic-py --help` from the repository
- **THEN** the command launches the maintained Python CLI and displays the available command groups without requiring a custom wrapper script

#### Scenario: Contributor runs the module entry point
- **WHEN** a contributor invokes `uv run --project python-bindings python -m classic_py_cli --help` from the repository
- **THEN** the command launches the same CLI behavior exposed by the `classic-py` console script

### Requirement: Python CLI command handlers use public bindings
Python CLI commands that perform CLASSIC product behavior SHALL call maintained public `classic_*` Python binding modules instead of reimplementing Rust-owned business logic in Python.

#### Scenario: Required binding is available
- **WHEN** a contributor runs a product command such as `classic-py version parse`, `classic-py config main-version`, or `classic-py file hash`
- **THEN** the command loads the required public binding module and derives the product result from that binding call

#### Scenario: Required binding is unavailable
- **WHEN** a command requires a `classic_*` module that cannot be imported because the PyO3 wheel is missing or stale
- **THEN** the command exits with binding import/build status and reports the missing binding instead of silently falling back to Python logic

### Requirement: Python CLI provides binding diagnostics
The Python CLI SHALL provide diagnostics that identify importable binding modules, unavailable modules, environment readiness, and binding build prerequisites.

#### Scenario: Contributor lists binding modules
- **WHEN** a contributor runs `classic-py bindings list --json`
- **THEN** the CLI emits a machine-readable list of expected binding modules with import status and available public-surface metadata where discoverable

#### Scenario: Contributor checks local readiness
- **WHEN** a contributor runs `classic-py doctor`
- **THEN** the CLI reports whether the uv environment, rebuilt PyO3 wheels, fixture paths, and required tools are present, and classifies setup failures separately from product failures

### Requirement: Python CLI supports stable output contracts
The Python CLI SHALL support concise human-readable output and stable JSON envelopes for automation.

#### Scenario: Automation requests JSON output
- **WHEN** a contributor or CI job passes `--json` to a command
- **THEN** the CLI writes one primary JSON envelope to stdout with `schemaVersion`, command identity, success status, summary or error data, and artifact paths

#### Scenario: JSON output is enabled during a verbose run
- **WHEN** a command is run with `--json` and diagnostic or progress messages are produced
- **THEN** diagnostics and progress are written to stderr so stdout remains parseable JSON

#### Scenario: Binding exception reaches the CLI boundary
- **WHEN** a public binding raises a typed Python exception during a command
- **THEN** the CLI preserves the original module name, exception type, and message in structured error output

### Requirement: Python CLI preserves stable exit semantics
The Python CLI SHALL return stable process exit codes that distinguish successful commands, completed product or compliance failures, usage/configuration failures, binding import/build failures, and interruption.

#### Scenario: Command succeeds
- **WHEN** a CLI command completes its requested workflow successfully
- **THEN** the process exits with status `0`

#### Scenario: Command completes with findings or failed scenarios
- **WHEN** a product or compliance command completes but reports scan errors, validation findings, or failed scenarios
- **THEN** the process exits with status `1`

#### Scenario: Command cannot start because of usage or configuration
- **WHEN** argument parsing, repository discovery, fixture discovery, or startup configuration fails before the workflow can run
- **THEN** the process exits with status `2`

#### Scenario: Command cannot load required bindings
- **WHEN** required Python binding modules cannot be imported or are detected as missing rebuilt wheels
- **THEN** the process exits with status `3`

#### Scenario: Command is interrupted
- **WHEN** a contributor interrupts the command before completion
- **THEN** the process exits with status `4`

### Requirement: Python CLI provides compliance scenario discovery
The Python CLI SHALL maintain a data-backed compliance scenario catalog that can be listed, explained, tested, and used for report generation.

#### Scenario: Contributor lists compliance scenarios
- **WHEN** a contributor runs `classic-py compliance list --json`
- **THEN** the CLI emits each scenario ID, owner binding module, covered public exports, command invocation, fixture requirements, expected exit code, blocking profile membership, and failure classification hints

#### Scenario: Contributor explains one scenario
- **WHEN** a contributor runs `classic-py compliance explain <scenario-id>`
- **THEN** the CLI displays the scenario purpose, binding owner, covered exports, command line, expected behavior, fixture requirements, and likely failure classifications

### Requirement: Python CLI runs binding smoke and compliance profiles
The Python CLI SHALL execute binding smoke checks and compliance profiles through command handlers and public binding modules, while delegating source-level gates to existing canonical tools where applicable.

#### Scenario: Smoke profile runs representative binding calls
- **WHEN** a contributor runs `classic-py compliance run --profile smoke` after rebuilding Python bindings
- **THEN** the CLI imports maintained binding owner modules, runs representative no-network scenarios from the catalog, and reports scenario results without invoking unrelated network-dependent checks

#### Scenario: Python CI profile delegates source-level gates
- **WHEN** CI runs `classic-py compliance run --profile python-ci`
- **THEN** the CLI includes CLI scenario evidence and delegates parity, stub validation, runtime coverage, or canonical binding compliance checks to the existing repository tools where the profile requires source-level validation

#### Scenario: Focused surface profile is requested
- **WHEN** a contributor runs `classic-py compliance run --profile surface:<name>`
- **THEN** the CLI runs the blocking scenarios owned by the requested binding surface and excludes unrelated surfaces from the focused result set

### Requirement: Python CLI writes compliance reports
The Python CLI SHALL write structured compliance reports that support local troubleshooting and CI evidence without requiring terminal output scraping.

#### Scenario: Compliance run writes reports
- **WHEN** a contributor runs `classic-py compliance run` with report output enabled or default compliance artifact output
- **THEN** the CLI writes JSON and Markdown reports containing command lines, profile, environment summary, scenario results, covered exports, generated artifact paths, and failure classifications

#### Scenario: Compliance failure is classified
- **WHEN** a compliance scenario or delegated gate fails
- **THEN** the report classifies the failure using the canonical binding compliance vocabulary, including local environment failure, stale generated artifact, stale baseline, missing runtime coverage, policy/source contradiction, or true binding compliance gap

### Requirement: Python CLI supports binding-backed product workflows
The Python CLI SHALL provide selected product command groups for configuration, paths, versions, files, database lookup, update metadata, XSE detection, scan logs, and scan game checks when the corresponding public bindings are available.

#### Scenario: Contributor runs deterministic utility workflows
- **WHEN** a contributor runs fixture-backed commands for config inspection, path validation, version parsing, file hashing, or database lookup
- **THEN** each command returns useful text output and equivalent JSON output derived from the corresponding binding module

#### Scenario: Contributor scans crash logs through Python bindings
- **WHEN** a contributor runs `classic-py scan logs` with a fixture or explicit scan path
- **THEN** the CLI invokes the maintained scanlog binding workflow, summarizes processed logs and report artifacts, and applies stable scan exit semantics

#### Scenario: Network-dependent update checks are outside default smoke
- **WHEN** the default smoke profile runs
- **THEN** update or web-backed commands that require live network access are skipped, mocked, or covered only by deterministic fixture-backed behavior

### Requirement: Python CLI is validated through process-level tests
The Python CLI SHALL be covered by tests that invoke command entry points as subprocesses and verify output, exit codes, binding diagnostics, and report artifacts.

#### Scenario: Process test validates help and JSON output
- **WHEN** the CLI test suite runs in a prepared Python binding environment
- **THEN** tests invoke `classic-py --help` and representative `--json` commands as subprocesses and assert exit status, stdout JSON validity, and stderr separation

#### Scenario: Process test simulates missing bindings
- **WHEN** tests simulate unavailable `classic_*` modules
- **THEN** the CLI returns binding import/build status and emits explicit prerequisite diagnostics instead of masking the failure

#### Scenario: Compliance process test validates smoke reports
- **WHEN** tests run the smoke compliance profile with rebuilt bindings and fixtures
- **THEN** they verify scenario results, report files, covered export metadata, and failure classification fields
