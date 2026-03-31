## ADDED Requirements

### Requirement: Orchestrator reuses shared derived log data across analyzers
The Rust scanlog orchestrator SHALL prepare and reuse shared derived views of a crash log across analyzer phases instead of repeatedly rebuilding equivalent intermediate data for the same log.

#### Scenario: Shared callstack-derived data is reused
- **WHEN** multiple analyzer phases require normalized or combined callstack-derived data for the same log
- **THEN** the orchestrator SHALL reuse a shared derived representation rather than independently rebuilding equivalent data for each analyzer phase

#### Scenario: Shared plugin-derived data is reused
- **WHEN** multiple analyzer phases require plugin-derived structures from the same parsed log
- **THEN** the orchestrator SHALL reuse a shared derived representation rather than reparsing or rematerializing equivalent plugin data per phase

### Requirement: Efficiency changes preserve scan result behavior
Pipeline efficiency improvements SHALL preserve existing scan correctness, report semantics, and fail-soft behavior for successful and failed log analyses.

#### Scenario: Successful scan output remains behaviorally equivalent
- **WHEN** a log that previously scanned successfully is analyzed after the efficiency changes
- **THEN** the resulting scan outcome and report content SHALL preserve the same user-visible analysis semantics and ordering expectations as before the change

#### Scenario: Failure behavior remains fail-soft
- **WHEN** a log encounters an analysis failure after the efficiency changes
- **THEN** the orchestrator SHALL continue to produce the same class of terminal failure outcome without causing unrelated logs in the batch to fail

### Requirement: Hot-path performance diagnostics remain observable
The scan pipeline SHALL expose lightweight diagnostics at orchestration boundaries sufficient to attribute heavy-log cost to major scan phases.

#### Scenario: Per-log phase timings can be observed
- **WHEN** diagnostic instrumentation is enabled for a batch scan
- **THEN** the pipeline SHALL make major per-log phase timings observable for phases such as setup, parse, analyze, and finalize

#### Scenario: Heavy-log regressions are attributable
- **WHEN** a representative heavy-log batch regresses in throughput or smoothness after future changes
- **THEN** the available diagnostics SHALL be sufficient to identify whether the regression originates in progress event handling, shared orchestration phases, or analyzer hot paths
