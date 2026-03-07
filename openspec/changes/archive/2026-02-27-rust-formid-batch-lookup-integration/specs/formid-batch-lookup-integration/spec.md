## ADDED Requirements

### Requirement: Batch FormID Value Resolution in Rust Scan Pipeline
The Rust scan pipeline SHALL resolve FormID values using batched database lookups for eligible FormID/plugin pairs rather than issuing one database query per pair.

#### Scenario: Resolve multiple FormIDs with one batch operation
- **WHEN** a log produces multiple FormID/plugin lookup candidates and database value display is enabled
- **THEN** the pipeline performs batched lookup operations through the Rust database batch API

#### Scenario: Handle large lookup sets with bounded batch size
- **WHEN** the number of FormID/plugin lookup candidates exceeds the configured batch size
- **THEN** the pipeline executes multiple batches and merges results without dropping candidates

### Requirement: Output Parity with Existing FormID Reporting
Batch integration SHALL preserve existing FormID report behavior for successfully resolved and unresolved values.

#### Scenario: Preserve report structure for resolved values
- **WHEN** a FormID value is found through batch lookup
- **THEN** the resulting report line keeps the existing format and field ordering used by current Rust output

#### Scenario: Preserve fallback behavior for unresolved values
- **WHEN** a FormID value is not found through batch lookup
- **THEN** the resulting report line omits only the value field and preserves the existing fallback output format

### Requirement: Case-Insensitive Plugin Matching and Duplicate Normalization
Batch integration SHALL preserve case-insensitive plugin matching semantics and correctly handle duplicate lookup candidates that normalize to the same database key.

#### Scenario: Match plugin name regardless of case
- **WHEN** a lookup candidate uses a plugin name with different letter casing than database rows
- **THEN** the batch lookup resolves using case-insensitive plugin matching semantics

#### Scenario: Map normalized duplicate candidates to caller-visible keys
- **WHEN** multiple input lookup candidates normalize to the same case-insensitive key
- **THEN** all relevant caller-visible keys receive the resolved value using first-match-wins behavior for collisions
