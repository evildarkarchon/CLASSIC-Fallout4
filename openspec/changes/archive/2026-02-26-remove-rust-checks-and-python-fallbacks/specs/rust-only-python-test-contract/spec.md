## ADDED Requirements

### Requirement: Python tests validate Rust-required behavior only
Python test suites SHALL validate only the supported Rust-mandatory runtime contract and MUST NOT assert successful execution via Python fallback paths.

#### Scenario: Legacy fallback test is removed or rewritten
- **WHEN** a test case expects successful behavior through a Python fallback implementation
- **THEN** that test SHALL be removed or rewritten to assert Rust-backed behavior

### Requirement: Test fixtures assume binding prerequisites
Shared Python test fixtures and setup code MUST assume required Rust bindings are built and installed before test execution.

#### Scenario: Test run with bindings installed
- **WHEN** tests are executed in a correctly prepared environment
- **THEN** fixtures SHALL initialize runtime dependencies without optional-Rust branching

#### Scenario: Test run without required bindings
- **WHEN** tests are executed without required Rust bindings
- **THEN** tests that depend on Rust bindings SHALL fail with explicit prerequisite diagnostics rather than switching to fallback implementations

### Requirement: CI enforces Rust binding prerequisite for Python tests
Continuous integration workflows that run Python tests MUST build and install required Rust bindings before executing the Python test matrix.

#### Scenario: CI pipeline for Python tests
- **WHEN** CI starts the Python test job
- **THEN** the job SHALL include a binding build-and-install step before invoking pytest
