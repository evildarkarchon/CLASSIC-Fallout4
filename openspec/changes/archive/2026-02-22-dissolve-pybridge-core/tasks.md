## 1. Add logic sub-modules to classic-pybridge-py

- [x] 1.1 Copy `classic-pybridge-core/src/metrics.rs` to `classic-pybridge-py/src/metrics.rs`; fix the nested lock: replace `Lazy<Arc<RwLock<ThreadMetrics>>>` with `Lazy<DashMap<BridgeOperation, OperationStats>>` and remove `ThreadMetrics` struct
- [x] 1.2 Copy `classic-pybridge-core/src/runtime.rs` to `classic-pybridge-py/src/runtime.rs` unchanged
- [x] 1.3 Add `mod metrics; mod runtime;` declarations to `classic-pybridge-py/src/lib.rs`

## 2. Rewrite classic-pybridge-py/src/lib.rs

- [x] 2.1 Remove all `From<classic_pybridge_core::X> for X` conversion impls (`BridgeOperationType`, `BridgeMetrics`, `RuntimeInfo`)
- [x] 2.2 Update `record_operation` to call local `metrics::record_bridge_operation()` directly (no `classic_pybridge_core::` prefix)
- [x] 2.3 Update `get_metrics` to call local `metrics::get_bridge_metrics()` and map from the local `BridgeMetrics` type directly
- [x] 2.4 Update `clear_metrics` to call local `metrics::clear_bridge_metrics()`
- [x] 2.5 Update `is_runtime_available` and `get_runtime_info` to use local `runtime::` functions
- [x] 2.6 Remove the `use classic_pybridge_core::*` / `classic_pybridge_core::` references entirely

## 3. Update Cargo.toml files

- [x] 3.1 In `classic-pybridge-py/Cargo.toml`: remove `classic-pybridge-core` dependency; add `classic-shared-core`, `classic-perf-core`, `parking_lot`, `dashmap`, `once_cell`, `num_cpus` as direct dependencies
- [x] 3.2 In `classic-pybridge-py/Cargo.toml`: add `serial_test` to `[dev-dependencies]`
- [x] 3.3 In `ClassicLib-rs/Cargo.toml`: remove `"business-logic/classic-pybridge-core"` from workspace `members`

## 4. Migrate tests

- [x] 4.1 Copy the `#[cfg(test)]` block from `classic-pybridge-core/src/lib.rs` into `classic-pybridge-py/src/lib.rs` (or a new `src/tests.rs`); update any `classic_pybridge_core::` references to use local paths

## 5. Delete classic-pybridge-core

- [x] 5.1 Delete the `ClassicLib-rs/business-logic/classic-pybridge-core/` directory entirely

## 6. Build and test

- [x] 6.1 Run `cargo build -p classic-pybridge-py --manifest-path ClassicLib-rs/Cargo.toml` and confirm it compiles clean
- [x] 6.2 Run `cargo test -p classic-pybridge-py --manifest-path ClassicLib-rs/Cargo.toml` and confirm all tests pass
- [x] 6.3 Run `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` to confirm no other crate regresses

## 7. Update agent instruction files

- [x] 7.1 In `CLAUDE.md` (line ~153), add exception note after "Each `*-py` crate wraps its corresponding `*-core` crate as a `cdylib`": `**Exception**: \`classic-pybridge-py\` has no \`-core\` counterpart — its bridge metrics and runtime helpers live directly in the binding crate, since the functionality is exclusively Python-facing and doesn't warrant a separate intermediate crate.`
- [x] 7.2 Apply the same note to `AGENTS.md` at the equivalent location
- [x] 7.3 Apply the same note to `GEMINI.md` at the equivalent location
