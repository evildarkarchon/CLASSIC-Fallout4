## ADDED Requirements

### Requirement: Global Connection Budget Enforcement
Rust database pool initialization SHALL enforce a global connection budget across all active database pools rather than applying a full limit independently to each pool.

#### Scenario: Initialize with multiple database files
- **WHEN** multiple database files are initialized in one database pool instance
- **THEN** the sum of effective per-database connection limits does not exceed the configured global connection budget

#### Scenario: Initialize with single database file
- **WHEN** only one database file is initialized
- **THEN** the effective per-database connection limit uses the global budget within configured bounds

### Requirement: Deterministic Per-Pool Budget Distribution
The connection budgeting subsystem SHALL distribute global budget across database pools using a deterministic policy with a documented minimum allocation per pool.

#### Scenario: Distribute budget across N active pools
- **WHEN** N active database pools are created
- **THEN** each pool receives an allocation computed from the documented policy and minimum-per-pool rule

#### Scenario: Handle budget under-allocation edge case
- **WHEN** global budget is lower than ideal aggregate minimums
- **THEN** the allocator applies the documented fallback policy and maintains a valid nonzero allocation plan

### Requirement: Budget Recalculation on Pool Topology Change
The system SHALL support recalculation of effective per-pool allocations when the active database pool set changes.

#### Scenario: Reinitialize with different database path count
- **WHEN** active database file count changes due to reinitialization
- **THEN** effective allocation is recomputed using the same global budget and distribution policy

#### Scenario: Manual budget update at runtime
- **WHEN** a caller updates the global connection budget at runtime
- **THEN** subsequent pool allocation decisions use the updated budget value

### Requirement: Connection Budget Observability
Connection statistics SHALL expose global budget and effective allocation details needed for tuning.

#### Scenario: Read connection tuning metrics
- **WHEN** statistics are requested
- **THEN** reported metrics include enough information to determine configured global budget and effective allocation behavior
