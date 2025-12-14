## ADDED Requirements

### Requirement: Factory Pattern Component Instantiation
The OrchestratorCore MUST use factory functions from `ClassicLib/integration/factory.py` to instantiate all acceleration-capable components instead of direct class instantiation.

#### Scenario: RecordScanner uses factory
- **WHEN** OrchestratorCore initializes
- **THEN** it MUST call `get_record_scanner(yamldata)` instead of `RecordScanner(yamldata)`
- **AND** handle None return gracefully with appropriate error handling

#### Scenario: Rust acceleration active
- **WHEN** Rust `classic_scanlog` module is available
- **THEN** `get_record_scanner()` MUST return Rust-accelerated implementation
- **AND** provide 40x performance improvement over Python

#### Scenario: Python fallback
- **WHEN** Rust module is unavailable or `CLASSIC_DISABLE_RUST=1`
- **THEN** `get_record_scanner()` MUST return Python implementation
- **AND** maintain identical API and output

### Requirement: Path Operations Factory Support
The integration factory MUST provide `get_path_operations()` with Python fallback for game path detection and registry queries.

#### Scenario: Path operations with Rust
- **WHEN** Rust `classic_path` module is available
- **THEN** `get_path_operations()` MUST return Rust-accelerated implementation
- **AND** provide 10-50x performance improvement for registry operations

#### Scenario: Path operations Python fallback
- **WHEN** Rust module is unavailable
- **THEN** `get_path_operations()` MUST return Python fallback implementation
- **AND** NOT return None (current behavior being fixed)

### Requirement: Integration Test Coverage
All factory-provided components MUST have integration tests verifying Rust usage when available.

#### Scenario: RecordScanner integration test
- **WHEN** test runs with Rust available
- **THEN** test MUST verify `get_record_scanner()` returns Rust implementation
- **AND** verify output parity with Python implementation

#### Scenario: Performance regression detection
- **WHEN** performance integration tests run
- **THEN** tests MUST verify Rust implementations meet expected speedup thresholds
- **AND** fail if performance degrades below 50% of expected speedup

## MODIFIED Requirements

### Requirement: Record Scanner Integration
The Rust orchestrator MUST integrate RecordScanner via factory pattern for named record detection in crash callstacks, using `get_record_scanner()` to enable automatic Rust acceleration.

#### Scenario: Named record found
- **WHEN** callstack contains known record patterns
- **THEN** the report MUST include matched record information

#### Scenario: Factory-based instantiation
- **WHEN** OrchestratorCore requires RecordScanner
- **THEN** it MUST use `get_record_scanner(yamldata)` factory function
- **AND** NOT directly instantiate `RecordScanner` class
