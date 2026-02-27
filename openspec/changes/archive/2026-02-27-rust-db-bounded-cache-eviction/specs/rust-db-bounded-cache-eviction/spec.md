## ADDED Requirements

### Requirement: Bounded Query Cache Capacity
The Rust database query cache SHALL enforce a configured maximum capacity and SHALL evict entries deterministically when capacity is exceeded.

#### Scenario: Cache insert exceeds capacity
- **WHEN** inserting a new cache entry would exceed configured cache capacity
- **THEN** the cache evicts entries according to the configured eviction policy and remains at or below capacity

#### Scenario: Capacity respected during sustained lookup workload
- **WHEN** sustained lookup traffic continuously inserts new keys
- **THEN** cache size remains bounded and does not grow unbounded over time

### Requirement: Expired Entry Cleanup Lifecycle
The Rust database cache subsystem SHALL remove expired entries through explicit cleanup behavior in addition to on-access eviction.

#### Scenario: Periodic cleanup removes expired entries
- **WHEN** periodic cleanup executes and expired entries exist
- **THEN** expired entries are removed without affecting non-expired entries

#### Scenario: Lookup ignores stale entry after expiration
- **WHEN** a previously cached entry has expired and is queried
- **THEN** the stale entry is treated as a miss and is not returned as a valid cache hit

### Requirement: Cache Observability for Operations
The cache subsystem SHALL expose operational counters for cache lifecycle events relevant to performance tuning.

#### Scenario: Report eviction and cleanup activity
- **WHEN** eviction or cleanup activity occurs
- **THEN** cache statistics expose counts sufficient to identify cache pressure and stale-entry churn

#### Scenario: Preserve existing hit/miss visibility
- **WHEN** cache operations are reported
- **THEN** hit and miss metrics remain available for caller-visible performance diagnostics
