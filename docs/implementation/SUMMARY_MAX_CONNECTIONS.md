# Global DB Connection Budget Summary

## Behavior Change

`classic-database-core::DatabasePool` now treats `max_connections` as a **global connection budget** shared across all active database pools in an instance.

Previously, the same `max_connections` value was applied to every pool independently (effectively multiplying total connections by DB count).

## Allocation Policy

For `N` active DB paths and configured budget `B`:

1. **Configured budget** = `B` (from constructor / `set_max_connections()` / `recalculate_max_connections()`).
2. **Effective budget** = `max(B, N)` (low-budget clamp keeps each pool nonzero).
3. **Deterministic split**:
   - `base = effective_budget / N`
   - `remainder = effective_budget % N`
   - Each pool gets `base`, and the first `remainder` pools (stable sorted path order) get `+1`.

This guarantees:

- Nonzero allocation per active DB pool.
- Sum of per-pool allocations equals effective budget.
- Stable remainder distribution across rebuilds.

## Runtime Update Semantics

- `set_max_connections(value)` updates configuration only.
- `recalculate_max_connections()` updates configuration only (CPU-based policy, clamped to `8..64`).
- Existing pools keep their current allocations until:
  - `initialize(...)` is called, or
  - `rebalance_connections()` is called.

Use `rebalance_connections()` for immediate reallocation of currently tracked DB paths.

## Observability Fields

`PoolStatistics` now includes connection-budget metrics:

- `configured_connection_budget`
- `effective_connection_budget`
- `active_pool_count`
- `min_pool_allocation`
- `max_pool_allocation`
- `allocation_spread`

Bindings (Python / Node) surface these fields through `get_stats()`.

## Binding Surface Additions

- Python `DatabasePool`:
  - `rebalance_connections()` (async)
  - updated global-budget docs for `set_max_connections()`
- Node `JsDatabasePool`:
  - `rebalanceConnections()` (async)
  - `JsPoolStatistics` now includes budget/allocation fields

## Compatibility

Lookup behavior remains compatible:

- single lookup (`get_entry`)
- batch lookup (`get_entries_batch` / `batch_lookup`)
- missing-entry semantics

Only connection budgeting semantics changed from per-pool cap to global budget allocation.
