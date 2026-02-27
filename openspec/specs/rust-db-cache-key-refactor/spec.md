# rust-db-cache-key-refactor Specification

## Purpose
TBD - created by archiving change rust-db-cache-key-refactor. Update Purpose after archive.
## Requirements
### Requirement: Typed Normalized Cache Key Semantics
Rust database caching SHALL use a normalized key representation that preserves existing lookup equivalence semantics for table, FormID, and plugin dimensions.

#### Scenario: Equivalent keys normalize consistently
- **WHEN** two lookup requests represent equivalent logical keys under normalization rules
- **THEN** both requests resolve to the same cache key identity

#### Scenario: Distinct keys remain distinct
- **WHEN** two lookup requests differ on any non-equivalent key component
- **THEN** the cache key representation keeps them as distinct entries

### Requirement: Case-Insensitive Plugin Matching Parity
Cache key behavior SHALL preserve case-insensitive plugin matching parity with existing lookup semantics.

#### Scenario: Plugin case variation across requests
- **WHEN** requests use different letter casing for the same plugin name
- **THEN** cache lookup behavior treats them as equivalent keys

#### Scenario: Batch and single lookup consistency
- **WHEN** identical logical lookups are executed via single and batch APIs
- **THEN** both paths use compatible key equivalence behavior for cache hit/miss outcomes

### Requirement: Hot-Path Key Construction Efficiency
Cache key construction SHALL avoid repeated formatted-string key composition in hot lookup paths.

#### Scenario: Repeated single lookup workload
- **WHEN** high-frequency single lookups execute
- **THEN** key construction does not rely on per-lookup formatted composite string assembly

#### Scenario: Repeated batch lookup workload
- **WHEN** high-frequency batch lookups execute
- **THEN** key construction avoids redundant normalization and composite string churn per lookup candidate

### Requirement: Cache Behavior Compatibility
The refactor SHALL preserve observable cache behavior contract for callers.

#### Scenario: Existing cache-dependent tests run after refactor
- **WHEN** current cache hit/miss behavior tests execute after key refactor
- **THEN** they continue to pass without API contract changes

