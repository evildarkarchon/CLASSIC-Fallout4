## Purpose

Define requirements for lock-free `DatabasePool` statistics updates and removal of dead `CacheKey` allocation work in batch lookups.

## Requirements

### Requirement: DatabasePool statistics use atomic counters
`DatabasePool` SHALL store query statistics (`total_queries`, `cache_hits`, `cache_misses`, `total_connections`, `active_connections`) as `AtomicU64` fields rather than fields on a `RwLock`-protected struct, enabling lock-free concurrent updates.

#### Scenario: Stats updated without write-lock
- **WHEN** `get_entry()` or `get_entries_batch()` records a cache hit, cache miss, or query count
- **THEN** the update SHALL complete via an atomic fetch-add, acquiring no `RwLock` or `Mutex`

#### Scenario: Stats snapshot still retrievable
- **WHEN** `DatabasePool::get_stats()` is called
- **THEN** it SHALL return a `PoolStatistics` value populated by reading all atomic counters with `Relaxed` ordering

#### Scenario: Batch stats scale linearly without lock contention
- **WHEN** `get_entries_batch()` is called with N FormID pairs
- **THEN** stats SHALL be updated exactly N times with no write-lock acquisitions

### Requirement: Dead CacheKey allocation removed from batch loop
The `get_entries_batch()` method SHALL NOT construct a `CacheKey` object in the per-FormID loop if that object is immediately discarded.

#### Scenario: No dead allocation
- **WHEN** `get_entries_batch()` processes a batch of FormID pairs
- **THEN** no `CacheKey::new()` call SHALL be made unless the resulting value is actually used for a cache lookup or insertion

### Requirement: External API of DatabasePool is unchanged
All public methods of `DatabasePool` (`new`, `initialize`, `get_entry`, `get_entries_batch`, `get_stats`, `close`) SHALL retain the same signatures and semantics.

#### Scenario: Existing callers compile unchanged
- **WHEN** existing code calling `DatabasePool::new()` or `get_entries_batch()` is compiled after this change
- **THEN** no call-site modifications SHALL be required
