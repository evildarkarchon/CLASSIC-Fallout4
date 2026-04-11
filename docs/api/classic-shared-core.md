# `classic-shared-core` API Guide

Contributor-facing API documentation for [`ClassicLib-rs/foundation/classic-shared-core/`](../../ClassicLib-rs/foundation/classic-shared-core).

Crate metadata:

- Crate: `classic-shared-core`
- Description: `Pure Rust foundation utilities for CLASSIC - runtime, errors, and business logic`

This crate is the shared foundation layer under the active Rust business-logic crates, bindings, and some UI integration code. Its most important job is enforcing CLASSIC's shared Tokio runtime model, but it also exposes reusable error, path, performance, and string helpers.

Unlike the business-logic `*-core` crates, this crate is intentionally cross-cutting. A change here can affect async orchestration, bindings, and utility wrappers across the repo.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- run async Rust code through CLASSIC's single shared Tokio runtime
- return or convert into a common `ClassicError` / `ClassicResult` shape
- normalize or validate paths with reusable cached helpers
- collect lightweight process-wide timing and throughput metrics
- intern or normalize strings through reusable foundation utilities
- bridge async Tokio work back onto the Slint UI event loop when the optional GUI feature is enabled

Do not use this crate for:

- domain-specific YAML, config, scanlog, database, or file-I/O business logic
- creating a second Tokio runtime for a crate, binding layer, or UI surface
- assuming every helper here is re-exported from the crate root

Those higher-level concerns live in related crates such as [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core), [`classic-file-io-core`](../../ClassicLib-rs/business-logic/classic-file-io-core), [`classic-database-core`](../../ClassicLib-rs/business-logic/classic-database-core), and [`classic-scanlog-core`](../../ClassicLib-rs/business-logic/classic-scanlog-core).

---

## Module And API Map

This crate exposes both root-level items and public modules.

## Root-level API

- `get_runtime() -> &'static tokio::runtime::Runtime` - the shared runtime entry point used across CLASSIC
- `RuntimeConfig` - runtime builder configuration helper used internally and available for advanced callers building their own `tokio::runtime::Builder`
- `ClassicError`, `ClassicResult`, `IntoClassicError` - re-exported common error API from `errors`

## Public modules

### `errors`

- `ClassicError` - shared typed error enum
- `ClassicResult<T>` - alias for `Result<T, ClassicError>`
- `IntoClassicError<T>` - helper trait for converting `Result<T, E>` into `ClassicResult<T>`
- `classic_error!` - exported macro defined in this module

### `path_core`

- `PathHandler` - cached path normalization, validation, joining, splitting, and prefix helpers

### `performance_core`

- `PerformanceMetrics` - process-wide operation metrics store
- `OperationStats` - aggregate stats for one named operation
- `Timer` - RAII timing helper
- `time_async()`, `time_operation()`, `time_with_bytes()` - timing helpers
- `get_global_metrics()` and `get_timer_start()` - global metrics/time accessors
- `timed!` - exported timing macro

### `strings_core`

- `StringProcessor` - string interning, normalization, and batch processing helper
- `StringOperation` - `Upper`, `Lower`, `Trim`, or `Normalize`
- `ParseStringOperationError` - parse error for `StringOperation`

### `async_bridge` (`gui-bridge` feature only)

- `AsyncBridge` - async-to-UI coordination helper for Slint callers
- `BridgeError` - timeout/cancel/dispatch error enum
- `EventLoopDispatcher` - dispatcher trait for UI-thread invocation
- `SlintDispatcher` - default production dispatcher
- `set_dispatcher()` - one-time dispatcher injection hook for tests/custom startup

Important layout note: `path_core`, `performance_core`, and `strings_core` are public modules, but their types are not re-exported from `lib.rs`. Callers use module paths such as `classic_shared_core::path_core::PathHandler`.

---

## Public API Surface

## Shared runtime API

## `get_runtime()`

`get_runtime()` is the most important integration API in this crate.

- returns a reference to a lazily initialized global multi-threaded Tokio runtime
- is the supported path for `.block_on(...)`, `.spawn(...)`, or `.handle().clone()` in higher layers
- is the runtime used throughout bindings and async business-logic integration in this repo

Behavior visible in `src/lib.rs`:

- the runtime is created once through `LazyLock`
- initialization uses `RuntimeConfig::default()`
- the builder is `tokio::runtime::Builder::new_multi_thread()`
- I/O and time drivers are enabled by default
- worker thread count defaults to available parallelism, with `4` as fallback if detection fails

Contributor rule: do not add another runtime to downstream crates when `get_runtime()` is available. The repo guidance explicitly treats this as a shared-runtime invariant.

## `RuntimeConfig`

`RuntimeConfig` is a public builder-helper struct, not a runtime replacement mechanism for the crate-global runtime.

Fields:

- `worker_threads: Option<usize>`
- `enable_io: bool`
- `enable_time: bool`
- `stack_size: Option<usize>`
- `thread_name: String`

Important constructors/helpers:

- `RuntimeConfig::default()`
- `RuntimeConfig::io_optimized()`
- `RuntimeConfig::cpu_optimized()`
- `RuntimeConfig::minimal()`
- `apply_to_builder(builder) -> tokio::runtime::Builder`

Contributor notes:

- `apply_to_builder()` is useful only when another crate needs to configure a builder using the same conventions; it does not mutate the existing global runtime
- the crate-global runtime is always built from `RuntimeConfig::default()` in current source
- there is no public API to replace or reconfigure the already-initialized global runtime

## Error API

## `ClassicError`

`ClassicError` is the crate's shared public error enum.

Variants:

- `Io { message, source }`
- `Path { message, path }`
- `Validation { message, field }`
- `Parse { message, position, context }`
- `Database { message, query }`
- `Cache { message }`
- `Encoding { message, encoding }`
- `Timeout { operation, duration_ms }`
- `Permission { message, resource }`
- `Configuration { message, key }`
- `Processing { message, stage }`
- `NotFound { resource }`
- `InvalidState { message, expected, actual }`
- `Generic { message, details }`

Public constructor helpers implemented on `ClassicError`:

- `ClassicError::io(...)`
- `ClassicError::path(...)`
- `ClassicError::validation(...)`
- `ClassicError::parse(...)`
- `ClassicError::database(...)`
- `ClassicError::encoding(...)`
- `ClassicError::timeout(...)`
- `ClassicError::permission(...)`
- `ClassicError::not_found(...)`
- `with_context(...)`

Source-observed note:

- `Cache`, `Configuration`, `Processing`, `InvalidState`, and `Generic` are public variants, but current source does not add dedicated constructor helpers for them

## `ClassicResult<T>` and `IntoClassicError<T>`

- `ClassicResult<T>` is just `Result<T, ClassicError>`
- `IntoClassicError<T>` adds `.into_classic(context)` to `Result<T, E>` where `E: Error + Send + Sync + 'static`

Behavior worth knowing:

- `.into_classic(context)` converts any source error into `ClassicError::Generic { message: context, details: Some(source.to_string()) }`
- `with_context()` preserves the `Generic` variant if the error is already `Generic`, but wraps any other variant into `ClassicError::Generic`

That means adding context through `with_context()` can trade away the original structured variant in exchange for a more general wrapped error message.

## Conversion behavior

Current `From` impls in `errors.rs`:

- `From<std::io::Error>` maps `NotFound`, `PermissionDenied`, and `TimedOut` into `NotFound`, `Permission`, and `Timeout` respectively
- other `std::io::ErrorKind` values become `ClassicError::Io`
- `From<std::str::Utf8Error>` becomes `ClassicError::Encoding(..., Some("UTF-8"))`

## `classic_error!`

The crate exports a `classic_error!` macro from `errors.rs`.

Contributor note:

- the macro is part of the public surface because it is `#[macro_export]`
- current in-repo source does not appear to use it anywhere outside the defining crate, so constructor methods on `ClassicError` are the better-documented integration path today

## `PathHandler`

`path_core::PathHandler` is the main path utility type.

Construction:

- `PathHandler::new(cache_ttl_seconds)`
- `PathHandler::new_with_limits(cache_ttl_seconds, max_cache_size)`
- `Default` -> `PathHandler::new(300)`

Important cache and validation methods:

- `normalize_path(path) -> ClassicResult<String>`
- `validate_paths_batch(paths) -> Vec<(String, bool, String)>`
- `cleanup_cache()`
- `clear_cache()`
- `cache_stats() -> (usize, usize)`
- `cache_metrics() -> (usize, usize, f64)`

Important path helpers:

- `join_paths(base, components) -> String`
- `split_path(path) -> Vec<String>`
- `get_filename(path) -> Option<String>`
- `get_extension(path) -> Option<String>`
- `get_parent(path) -> Option<String>`
- `is_absolute(path) -> bool`
- `to_absolute(path, base) -> ClassicResult<String>`
- `common_prefix(paths) -> Option<String>`

Behavior worth knowing from the source:

- `normalize_path()` first checks the cache by the exact input `String` key
- on cache miss it tries `PathBuf::canonicalize()` and falls back to an internal `clean_path()` helper if canonicalization fails
- `validate_paths_batch()` runs in parallel with Rayon and caches validation results by `PathBuf`
- `to_absolute()` joins a relative path onto the caller-provided base or the current working directory, but does not canonicalize the result
- `common_prefix()` compares `PathBuf` components, not raw strings

Source-observed limitation:

- comments describe the bounded cache as LRU, but the current eviction logic removes the bottom 20% of entries by `hit_count`, not by recency timestamp

## `PerformanceMetrics`, `Timer`, and helpers

`performance_core` provides a process-wide, constant-memory timing system.

## `PerformanceMetrics`

Important methods:

- `PerformanceMetrics::new()`
- `record_timing(operation, duration)`
- `record_bytes(operation, bytes)`
- `get_stats(operation) -> Option<OperationStats>`
- `get_operations() -> Vec<String>`
- `clear()`

Behavior worth knowing:

- operation names are `String` keys in a global `DashMap`
- timings are aggregated into rolling stats instead of storing every sample
- byte counts are tracked separately and combined into `OperationStats` at read time

## `OperationStats`

Fields:

- `count`
- `total`
- `average`
- `min`
- `max`
- `bytes_processed`

Helper:

- `throughput() -> Option<f64>` returns bytes per second only when `bytes_processed > 0` and total duration is non-zero

## `Timer`

Important methods:

- `Timer::start(operation)`
- `set_bytes(bytes)`
- `stop()`

Contributor notes:

- `Timer` records on explicit `stop()`
- if a `Timer` is dropped without `stop()`, `Drop` records the timing automatically
- `stop(self)` consumes the timer so the later drop does not double-record

## Free functions and macro

- `time_async(operation, future)`
- `time_operation(operation, f)`
- `time_with_bytes(operation, bytes, f)`
- `get_global_metrics() -> &'static Arc<PerformanceMetrics>`
- `get_timer_start() -> Instant`
- `timed!(name, { ... })`

Contributor note:

- the metrics collector is process-global and shared by the whole runtime process; `clear()` wipes all recorded operations, not just one crate's metrics

## `StringProcessor`

`strings_core::StringProcessor` is the crate's reusable string helper.

Construction:

- `StringProcessor::new()`
- `Default`

Important interning methods:

- `intern(s) -> String`
- `intern_spur(s) -> lasso::Spur`
- `resolve(&spur) -> String`
- `pool_stats() -> usize`

Important processing methods:

- `process_batch(strings, operation) -> Vec<String>`
- `normalize_string(s) -> String`
- `common_prefix(strings) -> String`
- `split_lines(text) -> Vec<String>`
- `join_lines(lines, separator) -> String`
- `clear_pool()`

Behavior worth knowing from the source:

- the interner is a shared `Arc<ThreadedRodeo>` inside the processor instance
- `intern()` returns a newly owned `String`, not a borrowed handle
- `intern_spur()` is the lower-allocation path for Rust callers that can keep `Spur` values around
- `process_batch()` parallelizes work with Rayon
- `normalize_string()` trims outer whitespace, collapses internal whitespace runs to single spaces, and lowercases with `to_ascii_lowercase()`
- `common_prefix()` compares bytes, then backs up to a UTF-8 character boundary before slicing

Source-observed limitation:

- `clear_pool()` does not clear the interner; it only prints a warning to stderr because `ThreadedRodeo` is append-only in the current design

## `StringOperation` and `ParseStringOperationError`

- `StringOperation` variants: `Upper`, `Lower`, `Trim`, `Normalize`
- `FromStr` accepts only exact lowercase strings: `"upper"`, `"lower"`, `"trim"`, `"normalize"`
- invalid parse input returns `ParseStringOperationError`

## `AsyncBridge` and GUI-only API

The `async_bridge` module exists only with the `gui-bridge` feature.

## `BridgeError`

Variants:

- `Timeout(Duration)`
- `Cancelled`
- `DispatchFailed(String)`

## `EventLoopDispatcher` and `set_dispatcher()`

- `EventLoopDispatcher::dispatch(Box<dyn FnOnce() + Send + 'static>) -> Result<(), BridgeError>`
- `SlintDispatcher` is the default production implementation over `slint::invoke_from_event_loop`
- `set_dispatcher(dispatcher)` stores a global dispatcher in a `OnceLock`

Contributor notes:

- `set_dispatcher()` panics if called more than once in a process
- tests in this crate use mock/failing dispatchers instead of a real Slint event loop

## `AsyncBridge`

Important methods:

- `run_with_ui_update(operation, on_complete)`
- `spawn_background(operation)`
- `run_with_timeout(timeout, operation, on_complete)`
- `run_cancellable(cancel_token, operation, on_complete)`
- `invoke_on_ui_thread(f)`

Behavior worth knowing from the source:

- all async work is spawned onto `crate::get_runtime()`
- UI callbacks are dispatched through the global `EventLoopDispatcher`
- dispatch failures are logged with `log::error!` and then dropped; they are not returned to the caller synchronously
- `spawn_background()` is fire-and-forget and does not return a `JoinHandle`
- `run_with_timeout()` passes `Result<R, BridgeError>` to the completion callback
- `run_cancellable()` passes `Option<R>` to the completion callback instead of `Result<R, BridgeError>`

Source-observed limitation:

- `BridgeError::Cancelled` is public, but `run_cancellable()` currently reports cancellation as `None` rather than surfacing `BridgeError::Cancelled`

---

## Shared Runtime And Async Flow

This crate is the foundation for the repo's shared-runtime rule.

The source-visible flow is:

1. A caller reaches `classic_shared_core::get_runtime()`.
2. The global `LazyLock<Runtime>` initializes on first use.
3. The runtime uses `RuntimeConfig::default()` and a multi-threaded Tokio builder.
4. Higher-level crates do one of three things with that runtime:
   - `block_on(...)` from sync binding/front-end entry points
   - `spawn(...)` from already-running Rust/UI code
   - `handle().clone()` for N-API or other task handoff patterns
5. Async business-logic crates such as config, file I/O, database, and scanlog run on that shared runtime instead of creating their own.

In-repo examples of this collaboration:

- [`ClassicLib-rs/business-logic/classic-config-core/src/lib.rs`](../../ClassicLib-rs/business-logic/classic-config-core/src/lib.rs) re-exports `get_runtime`
- [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs) documents `get_runtime().block_on(...)` as the C++ bridge pattern
- [`ClassicLib-rs/node-bindings/classic-node/src/fileio.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/fileio.rs) and sibling modules clone the shared runtime handle for Node task execution
- [`ClassicLib-rs/ui-applications/classic-tui/src/app.rs`](../../ClassicLib-rs/ui-applications/classic-tui/src/app.rs) uses `get_runtime().spawn(...)`

Contributor rule: if you add new async foundation or business-logic APIs, keep them compatible with the shared runtime model rather than introducing per-crate runtime ownership.

---

## Error Handling Model

This crate establishes a mixed error model for downstream code.

## Structured shared errors

Use `ClassicError` / `ClassicResult<T>` when you want:

- consistent error categories at crate boundaries
- human-readable formatting through `thiserror`
- context attachment via `with_context()` or `.into_classic(...)`

## Lossy context wrapping

Two parts of the current API intentionally trade strict structure for convenience:

- `IntoClassicError::into_classic(...)` always produces `ClassicError::Generic`
- `ClassicError::with_context(...)` converts non-`Generic` errors into `Generic`

That is useful for contributor ergonomics, but callers that need to preserve exact variant identity should add context before conversion or carry a crate-specific error type instead.

## Module-local errors still exist elsewhere

This crate does not replace the more specific error enums in higher layers such as:

- `YamlError` in [`classic-settings-core`](../../docs/api/classic-settings-core.md) (absorbed from the former ``yaml-core`` in v9.1.0 Phase 1)
- `ConfigError` in [`classic-config-core`](../../docs/api/classic-config-core.md)
- `FileIOError` in [`classic-file-io-core`](../../docs/api/classic-file-io-core.md)
- `DatabaseError` in [`classic-database-core`](../../docs/api/classic-database-core.md)
- `ScanLogError` in [`classic-scanlog-core`](../../docs/api/classic-scanlog-core.md)

In practice, `classic-shared-core` gives the repo a common foundation error vocabulary, but higher-level crates still define richer domain-specific errors where needed.

---

## Feature Flags

Contributor-relevant feature flags from `Cargo.toml`:

- default features: none
- `gui-bridge` - enables `async_bridge`, pulling in optional `slint` and `tokio-util`

What `gui-bridge` changes:

- adds the `async_bridge` module at compile time
- adds the root-level re-exports `AsyncBridge`, `BridgeError`, `EventLoopDispatcher`, `SlintDispatcher`, and `set_dispatcher`
- enables `run_cancellable()` support through `tokio_util::sync::CancellationToken`

Contributor note:

- outside `gui-bridge`, the crate still provides the shared runtime and foundation helpers, but none of the Slint bridge API exists
- `gui-bridge` now builds directly from the workspace `slint` dependency set; `classic-shared-core` no longer carries a crate-local `zerovec` workaround for this feature path

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `tokio` and `futures` - shared runtime and async foundation
- `thiserror` and `anyhow` - error ergonomics
- `dashmap` and `parking_lot` - concurrent/shared helper state
- `rayon` - parallel batch work in path/string helpers
- `lasso` and `smartstring` - string interning and compact string operations
- `rustc-hash` and `xxhash-rust` - present as foundation dependencies, though the current public source in this crate does not visibly expose hashing APIs
- `log` - logging for path canonicalization and async bridge dispatch failures

Related CLASSIC crates and consumers:

- [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core) - re-exports `get_runtime` and depends on the shared-runtime rule
- [`classic-file-io-core`](../../ClassicLib-rs/business-logic/classic-file-io-core), [`classic-database-core`](../../ClassicLib-rs/business-logic/classic-database-core), and [`classic-scanlog-core`](../../ClassicLib-rs/business-logic/classic-scanlog-core) - async business-logic crates expected to run on the shared runtime
- [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge) and [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node) - binding layers that call into async Rust using the shared runtime
- [`classic-shared-py`](../../ClassicLib-rs/foundation/classic-shared-py) - PyO3 wrapper over this crate's runtime/error/path/performance/string helpers
- [`classic-gui`](../../classic-gui) and Rust UI crates such as [`ClassicLib-rs/ui-applications/classic-tui`](../../ClassicLib-rs/ui-applications/classic-tui) - UI surfaces that depend on the same runtime policy; Slint-style bridging is feature-gated here

Source-observed note:

- `Cargo.toml` lists several utility dependencies that are not visibly part of the current public API surface yet. Keep docs aligned with exported behavior, not dependency presence alone.

---

## Usage Examples

### Run async work on the shared runtime

This is the main contributor-facing pattern used across bindings and higher layers.

```rust
use classic_shared_core::get_runtime;

let contents = get_runtime().block_on(async {
    tokio::fs::read_to_string("CLASSIC Settings.yaml").await
})?;

println!("Loaded {} bytes", contents.len());
# Ok::<(), std::io::Error>(())
```

### Use a foundation helper from a public module

```rust
use classic_shared_core::strings_core::{StringOperation, StringProcessor};

let strings = StringProcessor::new();

let normalized = strings.process_batch(
    &["  Buffout  4  ", "  Fallout4.esm  "],
    StringOperation::Normalize,
);

assert_eq!(normalized, vec!["buffout 4", "fallout4.esm"]);
```

If you are writing sync wrapper code around async business logic, `get_runtime()` is the primary API to reach for first.

---

## Contributor Notes And Known Limits

- `get_runtime()` is the supported public runtime entry point; `RUNTIME` itself is crate-private.
- `RuntimeConfig` is public, but current crate code does not let callers swap the config used by the global runtime.
- `path_core`, `performance_core`, and `strings_core` are public modules, not root-level re-exports.
- `PathHandler`'s bounded cache eviction is hit-count based, even though comments describe it as LRU.
- `StringProcessor::clear_pool()` does not clear anything; it warns and expects callers to create a new instance instead.
- `ClassicError::with_context()` can erase the original variant by wrapping it into `Generic`.
- `BridgeError::Cancelled` is public, but current `run_cancellable()` uses `Option<R>` rather than that variant.
- `classic_error!` is exported, but current repo code does not appear to rely on it.
- several dependencies in `Cargo.toml` are foundation-oriented but do not currently correspond to visible public APIs in `src/`

If you extend this crate, update this document when you change:

- root-level exports in `src/lib.rs`
- the shared runtime contract or initialization behavior
- `ClassicError` variants, conversion rules, or context-wrapping behavior
- public module types in `path_core`, `performance_core`, `strings_core`, or `async_bridge`
- feature-gated GUI bridge behavior or dispatcher assumptions
