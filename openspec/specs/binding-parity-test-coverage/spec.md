## Purpose

Define how maintained Node and Python bindings account for runtime parity coverage, deferred surface, and regression gating relative to the Rust core.

## Requirements

### Requirement: Binding parity coverage inventory
The system SHALL maintain generated coverage inventories for maintained Node and Python bindings that classify each tracked surface relative to the Rust core as runtime-verified, contract-mapped, deferred, or newly uncovered.

#### Scenario: Coverage inventory refresh after parity tooling runs
- **WHEN** Node or Python parity baseline tooling is executed for a maintained binding surface
- **THEN** the generated artifacts include per-owner-module totals and a classification for every discovered tracked export or mapping row

#### Scenario: Newly introduced surface lacks coverage classification
- **WHEN** parity tooling detects a new binding export or mapped Rust symbol that is not represented in coverage metadata
- **THEN** the parity output reports it as newly uncovered instead of silently excluding it from coverage accounting

### Requirement: Tier-1 binding surfaces require runtime verification
The system SHALL provide direct runtime verification for every Tier-1 callable binding export and representative runtime verification for each Tier-1 data model export in maintained Node and Python bindings.

#### Scenario: Tier-1 callable export is validated
- **WHEN** local or CI runtime parity suites execute for a maintained binding
- **THEN** every Tier-1 callable export is invoked through the binding surface with assertions on representative success behavior or stable error behavior

#### Scenario: Tier-1 data model export is not directly callable
- **WHEN** a Tier-1 class, enum, or result type has no standalone workflow entry point
- **THEN** runtime parity suites verify it through construction, returned values, field inspection, or another binding-facing path that exercises the exported type

### Requirement: Deferred parity surface must remain explicit
The system SHALL publish any deferred binding parity surface with enough ownership and planning metadata to support systematic coverage expansion.

#### Scenario: Surface is intentionally deferred
- **WHEN** maintainers leave a tracked Node or Python surface outside the current runtime-verified or Tier-1 set
- **THEN** published parity backlog artifacts record its owner module, defer reason, and planned revisit trigger or wave

#### Scenario: Coverage wave completes
- **WHEN** a parity expansion wave is delivered
- **THEN** the published backlog and coverage artifacts show which surfaces moved into runtime-verified or contract-mapped coverage and how remaining deferred totals changed

### Requirement: Coverage regressions are gated
The system SHALL fail parity maintenance checks when tracked Node or Python surfaces change without refreshed coverage artifacts or when Tier-1 runtime verification regresses.

#### Scenario: Tier-1 promotion lacks runtime evidence
- **WHEN** a binding API is added to Tier-1 parity coverage
- **THEN** local and CI checks fail until runtime coverage metadata and runtime tests exist for that promoted surface

#### Scenario: Tracked surface changes without refreshed artifacts
- **WHEN** public Rust symbols or maintained binding exports change in a tracked parity module
- **THEN** parity checks require regenerated coverage artifacts and report any newly uncovered surfaces or loss of Tier-1 runtime verification
