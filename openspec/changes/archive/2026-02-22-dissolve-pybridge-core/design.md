## Context

`classic-pybridge-core` (`business-logic/classic-pybridge-core/`) is a three-file pure-Rust `rlib` crate containing:
- `metrics.rs`: Global `DashMap`-backed bridge operation counters wrapped in a redundant outer `parking_lot::RwLock`
- `runtime.rs`: Thin wrappers around `classic_shared_core::get_runtime()` (`is_runtime_available`, `get_runtime_info`, `execute_on_runtime`)
- `lib.rs`: Re-exports of the above

Its sole consumer is `classic-pybridge-py` (`python-bindings/classic-pybridge-py/`), which defines its own PyO3 versions of the same types (`BridgeOperationType`, `BridgeMetrics`, `RuntimeInfo`) and converts between them with `From` impls. This creates a 3-hop call chain (Python → py-types → From-conversion → core-types → logic) where 2 hops suffice.

## Goals / Non-Goals

**Goals:**
- Remove `classic-pybridge-core` as a separate crate
- Move its logic directly into `classic-pybridge-py/src/metrics.rs` and `src/runtime.rs`
- Fix the redundant `parking_lot::RwLock<ThreadMetrics { DashMap }>` — replace with a bare `DashMap` static
- Update all `Cargo.toml` files accordingly
- Document the architectural exception in CLAUDE.md, AGENTS.md, GEMINI.md
- Migrate tests from `-core` to `-py`

**Non-Goals:**
- Changing the Python-facing API of `classic_pybridge` (module name, functions, types)
- Changing the behavior of metrics or runtime helpers
- Touching any other binding crate

## Decisions

### 1. Inline logic as sub-modules, not a single flat file

Move `metrics.rs` and `runtime.rs` as-is into `classic-pybridge-py/src/`, then `mod metrics; mod runtime;` in `lib.rs`. This keeps the same logical separation without the extra crate boundary.

**Why not flatten everything into `lib.rs`?** `lib.rs` already has ~260 lines of PyO3 glue. Flattening would make it unwieldy.

**Alternative**: Keep `-core` but move it to `foundation/`. Rejected — the code volume (3 small files) doesn't warrant a standalone crate; absorbing it is simpler.

### 2. Replace `Lazy<Arc<RwLock<ThreadMetrics>>>` with `Lazy<DashMap<...>>`

`ThreadMetrics` was a struct containing only a single `DashMap`. The outer `RwLock` added a second lock acquisition on every metric record with no benefit — `DashMap` already handles concurrent access via internal sharding.

New static:
```rust
static METRICS: Lazy<DashMap<BridgeOperation, OperationStats>> = Lazy::new(DashMap::new);
```

**Why not `parking_lot::Mutex`?** We're doing concurrent reads and writes from multiple Tokio tasks; `DashMap` is purpose-built for this.

### 3. Remove `From<core::X> for py::X` conversion impls

After the merge, `BridgeOperation`, `BridgeMetrics`, and `RuntimeInfo` are defined once inside `classic-pybridge-py/src/`. The PyO3 types and the internal types are the same types — no conversion needed.

### 4. `classic-pybridge-py` gains direct dependencies on workspace crates

Previously these were hidden behind `classic-pybridge-core`. After the merge, `Cargo.toml` for `classic-pybridge-py` explicitly depends on:
- `classic-shared-core` (for `get_runtime()`)
- `classic-perf-core` (for perf tracking)
- `parking_lot`, `dashmap`, `once_cell`, `num_cpus` (workspace deps)

This is the honest dependency graph — no hiding behind an intermediate crate.

### 5. `serial_test` dev-dep moves to `classic-pybridge-py`

Tests using `#[serial]` for the global `METRICS` state need `serial_test` in dev-deps. The crate currently lives only in `-core`; it moves to `-py`.

## Risks / Trade-offs

- **`rebuild_rust.ps1` references**: The script may enumerate binding crates. `classic-pybridge-py` already exists and is built; removing `-core` only removes a non-binding crate, so no script changes expected. Verify before closing.
- **Test migration**: The `#[cfg(test)]` block in `-core/src/lib.rs` must move to `-py` intact, or be converted to integration tests. Risk: low — tests are simple counter assertions.
- **Workspace compilation**: Removing a workspace member can surface implicit transitive deps. The only transitive consumer was `-py`, which we're updating explicitly.

## Migration Plan

1. Add `metrics.rs`, `runtime.rs` to `classic-pybridge-py/src/` (copied from `-core`, with nested lock fix)
2. Rewrite `classic-pybridge-py/src/lib.rs` to use local types directly (drop `From` impls, drop `classic_pybridge_core::` prefixes)
3. Update `classic-pybridge-py/Cargo.toml` (remove `-core` dep, add direct deps)
4. Remove `"business-logic/classic-pybridge-core"` from workspace `Cargo.toml`
5. Delete `ClassicLib-rs/business-logic/classic-pybridge-core/`
6. Update CLAUDE.md, AGENTS.md, GEMINI.md with architecture exception note
7. Build (`cargo build -p classic-pybridge-py`) and run tests

No Python-side changes. No rollback concern — this is a pure internal Rust restructuring.

## Open Questions

*(none — design is fully determined by the exploration session)*
