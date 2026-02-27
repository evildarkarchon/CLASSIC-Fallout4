## Why

Current Rust pool sizing applies the same max connection value per database pool, which can over-allocate total connections when multiple databases are attached. We need global connection budgeting to improve efficiency and avoid resource spikes.

## What Changes

- Introduce total connection budget logic for Rust database pools across all active database files.
- Allocate per-database pool limits from the global budget using a deterministic distribution policy.
- Add runtime recalculation/rebalance hooks when database path sets change.
- Improve pool statistics visibility to reflect effective per-pool and global connection limits.

## Capabilities

### New Capabilities
- `rust-db-connection-budgeting`: Manage Rust database connections using a global budget distributed across active database pools.

### Modified Capabilities
- (none)

## Impact

- Affected code:
  - `ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs`
  - Bindings that expose stats and tuning knobs
- Runtime impact:
  - Reduced risk of over-provisioned SQLite connections
  - More stable behavior on systems with multiple FormID database files
- No intended breaking change to consumer-facing lookup APIs.
