# `classic-shared-core` API Guide

Contributor-facing API documentation for [`foundation/classic-shared-core/`](../../foundation/classic-shared-core).

Crate metadata:

- Crate: `classic-shared-core`
- Description: `Pure Rust foundation utilities for CLASSIC - runtime, errors, generic YAML, loose version/PE helpers, and business logic`

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
- parse, load, merge, validate, or schema-check generic YAML, or cache parsed YAML under logical keys (`yaml`)
- parse, compare, extract, or format loose version strings, or read a Windows PE file's version resource (`version`)
- bridge async Tokio work back onto the Slint UI event loop when the optional GUI feature is enabled

Do not use this crate for:

- domain-specific YAML, config, scanlog, database, or file-I/O business logic
- deciding whether a version is a *known* game or script-extender version; that is Version Registry policy (`is_known_fallout4_version()` / `is_known_f4se_version()` in [`classic-version-registry-core`](classic-version-registry-core.md#known-version-queries))
- creating a second Tokio runtime for a crate, binding layer, or UI surface
- assuming every helper here is re-exported from the crate root

Those higher-level concerns live in related crates such as [`classic-config-core`](../../business-logic/classic-config-core), [`classic-file-io-core`](../../business-logic/classic-file-io-core), [`classic-database-core`](../../business-logic/classic-database-core), and [`classic-scanlog-core`](../../business-logic/classic-scanlog-core).

---

## Module And API Map

This crate exposes both root-level items and public modules.

## Root-level API

- `get_runtime() -> &'static tokio::runtime::Runtime` - the shared runtime entry point used across CLASSIC
- `RuntimeConfig` - runtime builder configuration helper used internally and available for advanced callers building their own `tokio::runtime::Builder`
- `ClassicError`, `ClassicResult`, `IntoClassicError` - re-exported common error API from `errors`
- `GameId` - shared supported-game enum used across setup, web, registry-state, and binding-facing flows

## Public modules

### `errors`

- `ClassicError` - shared typed error enum
- `ClassicResult<T>` - alias for `Result<T, ClassicError>`
- `IntoClassicError<T>` - helper trait for converting `Result<T, E>` into `ClassicResult<T>`
- `classic_error!` - exported macro defined in this module

### `path_core`

- `PathHandler` - cached path normalization, validation, joining, splitting, and prefix helpers
- generic path primitives (#245): `is_valid_path`, `validate_path_exists`, `validate_is_directory`, `validate_is_file`, `is_executable_file_path`, `check_drive_exists`, `check_read_permissions`, `check_write_permissions`, `validate_path_with_permissions`, `drive_exists`, `has_read_permission`, `has_write_permission`, `remove_readonly_attribute`, Windows-only `remove_readonly`, and `PathError` / `PathResult<T>`
- OS cache root: `user_cache_root()`, `user_cache_root_with_env()`, `CacheRootUnavailable`, `non_empty_env_var()`

See [Generic path primitives](#generic-path-primitives-path_core).

### `performance_core`

The sole rolling `Duration` timing implementation for every binding.

- `PerformanceMetrics` - operation metrics store (the default store or an explicitly owned one)
- `OperationStats` - aggregate stats for one named operation
- `MetricsSummary` - seconds-based projection of `OperationStats`
- `TimingError`, `MetricCounter` - typed sample and counter rejections
- `Timer`, `start_timer()` - RAII timing helper that records at most once
- `record_timing()`, `record_timing_millis()`, `get_summary()`, `clear_metrics()` - seconds/milliseconds view of the default store
- `duration_from_secs_f64()`, `duration_from_millis_f64()`, `duration_from_millis_u64()`, `duration_from_millis_i128()` - validating sample conversions
- `MAX_SAMPLE_NANOS` - largest accepted single sample
- `time_async()`, `time_operation()`, `time_with_bytes()` - timing helpers
- `get_global_metrics()` and `get_timer_start()` - default store and timer epoch accessors
- `timed!` - exported timing macro

### `strings_core`

- `StringProcessor` - string interning, normalization, and batch processing helper
- `StringOperation` - `Upper`, `Lower`, `Trim`, or `Normalize`
- `ParseStringOperationError` - parse error for `StringOperation`

### `version`

The sole owner of the domain-neutral loose version and PE helpers. See [Loose versions and PE helpers](#loose-versions-and-pe-helpers-version).

- `parse_version()`, `try_parse_version()`, `compare_versions()`, `format_version()`
- `extract_version_from_filename()`, `extract_version_from_log()`, `extract_all_versions()`
- `VersionError`, `VersionResult<T>`
- public submodule `version::pe_version`: `is_valid_executable_path()`, `extract_pe_version()`, `PeVersionError`, `PeVersionResult<T>` (also re-exported at the `version` root)

### `yaml`

The sole owner of domain-neutral YAML rules. See [Generic YAML](#generic-yaml-yaml).

- parsing and sync/async loaders, multi-document and merge-key (`<<`) merging
- the bounded logical-key cache (`load_settings_*`, `get_cached`, `cache_stats`, ...)
- `YamlOperations` and its path/mtime-aware YAML-file cache (`yaml_cache_stats`, `clear_global_yaml_cache`, ...)
- opaque cache scope handles for both caches (`LogicalKeyCacheScope`, `YamlFileCacheScope`)
- scalar `validators` and `schema_version` compatibility checks
- `SettingsError`, `SettingsSource`, `YamlError`, `YamlSchemaError`

### `async_bridge` (`gui-bridge` feature only)

- `AsyncBridge` - async-to-UI coordination helper for Slint callers
- `BridgeError` - timeout/cancel/dispatch error enum
- `EventLoopDispatcher` - dispatcher trait for UI-thread invocation
- `SlintDispatcher` - default production dispatcher
- `set_dispatcher()` - one-time dispatcher injection hook for tests/custom startup

Important layout note: `path_core`, `performance_core`, `strings_core`, `version`, and `yaml` are public modules, but their types are not re-exported from `lib.rs`. Callers use module paths such as `classic_shared_core::path_core::PathHandler`.

---

## Public API Surface

## Shared runtime API

## `GameId`

`GameId` is the shared game-identity enum used across the workspace.

Variants:

- `Fallout4`
- `Fallout4VR`
- `Skyrim`
- `Starfield`

Important methods and traits:

- `as_str() -> &'static str`
- `exe_name() -> &'static str`
- `is_vr() -> bool`
- `all() -> [GameId; 4]`
- `display_name() -> &'static str` - Rust-owned user-facing names: `Fallout 4`, `Fallout 4 VR`, `Skyrim`, and `Starfield`
- `Display`, `FromStr`, `Serialize`, `Deserialize`, `Clone`, `Copy`, `Hash`

Behavior worth knowing:

- `exe_name()` hardcodes the expected executable per supported game
- Node `getGameName`, Python `GameId.display_name`, and CXX `game_id_display_name` delegate to the same display-name method. Stable serialization tokens continue to come from `as_str()`.
- `is_vr()` is only true for `Fallout4VR`
- `FromStr` is exact and case-sensitive; it accepts only the variant names shown above

Contributor note:

- `GameId` moved into the foundation layer during Phase 3 so setup, path, web, XSE, bridge, and binding layers can share game identity without depending on a retired constants crate

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

## Generic path primitives (`path_core`)

`path_core` is the domain-neutral owner of CLASSIC's generic path checks. They moved unchanged from `classic-path-core` in #245 so callers that only need a neutral check depend on shared core alone; `classic-path-core` keeps game/documents discovery, custom-scan and settings-path policy, required-file checks, and the per-user cache directories, and no longer re-exports these items.

Existence and kind:

- `is_valid_path(path) -> bool` - `Path::exists()`
- `validate_path_exists(path)`, `validate_is_directory(path)`, `validate_is_file(path) -> PathResult<()>` - a missing path is always `NotFound` before any kind check
- `is_executable_file_path(path) -> bool` - an existing file whose extension is `.exe`, `.app`, or absent. This was `classic_path_core::is_valid_executable_path`; it is renamed because `version::pe_version::is_valid_executable_path` (an existing `.exe`/`.dll` whose PE version can be read) answers a different question, and the parity tooling keys Rust symbols by crate and bare name.

Permission and drive:

- `check_drive_exists(path)` - checks the Windows drive prefix; always `Ok(())` elsewhere
- `check_read_permissions(path)` - lists a directory or opens a file; anything else is `InvalidPath("Path is neither a file nor directory: ..")`
- `check_write_permissions(path)` - creates and removes `.classic_test_write` in the directory (or the file's parent)
- `validate_path_with_permissions(path, check_read, check_write)` - drive, existence, then the requested permission checks
- `drive_exists`, `has_read_permission`, `has_write_permission` - boolean wrappers over the checks above

Read-only:

- `remove_readonly_attribute(path)` - clears the read-only flag on Windows; a no-op elsewhere
- `remove_readonly(path)` (Windows only) - same flag change, but also writes a warning to stderr when clearing fails; kept distinct because the Node and Python `remove_readonly` exports rely on that behavior

`PathError` variants and messages are unchanged and are observed by the CXX, Node, and Python path adapters:

- `NotFound(PathBuf)` - `Path does not exist: ..`
- `NotADirectory(PathBuf)` - `Path is not a directory: ..`
- `NotAFile(PathBuf)` - `Path is not a file: ..`
- `IoError { path, source }` - `I/O error for path ..: ..`
- `PermissionDenied(String)` - `Permission denied: ..`
- `InvalidPath(String)` - `Invalid path: ..`

OS cache root:

- `user_cache_root_with_env(env) -> Result<PathBuf, CacheRootUnavailable>` - `%LOCALAPPDATA%`, then `%APPDATA%` on Windows; `$XDG_CACHE_HOME`, then `$HOME/.cache` elsewhere. Pure resolution; nothing is created.
- `user_cache_root()` - the same, reading the process environment through `non_empty_env_var()`
- `non_empty_env_var(name)` - treats unset *and* empty variables as absent so an empty `%LOCALAPPDATA%` falls through to the next candidate
- `CacheRootUnavailable` displays as `neither LOCALAPPDATA nor APPDATA is set` (or the Unix pair). Cache owners append their own context, which is how `classic-path-core`'s YAML and app-notification cache errors keep their exact pre-move messages.

The root holds no `CLASSIC/...` subdirectory policy; each cache owner joins its own.

## `PerformanceMetrics`, `Timer`, and helpers

`performance_core` is the single, constant-memory timing implementation. C++, Node, and both Python performance views (`classic_perf` through `classic-perf-py`, and `classic_shared.RustPerformanceMonitor`) all record into it.

The former `classic-perf-core` crate, a seconds-view re-export facade over this module, was retired in issue #256. Its `classic_perf_core::*` import paths end with no forwarding shim; Rust callers import `classic_shared_core::performance_core` directly. The CXX, Node, and Python parity contracts name `classic-shared-core` as the owning Rust crate for every timing row; do not restore `classic-perf-core` as an owner during a baseline refresh.

### Default store

There is **one default observable store per linked library image**: `get_global_metrics()`, the seconds/milliseconds free functions, and `Timer` all read and clear the same timing and byte state. A `PerformanceMetrics::new()` value owns independent state that the default store never sees. The C++ bridge and Node addon each link their own image and therefore their own default. Today `classic_perf` and `classic_shared` are separate Python extension images with separate stores; the single-wheel adapter (issue #259) puts them in one image.

### Sample contract

- Floating-point samples must be finite and nonnegative; `-0.0` is zero.
- A valid sample is rounded **once**, from its exact binary value, to the nearest nanosecond (ties to even). Millisecond input is scaled in that same step, not divided into seconds first.
- One sample may not exceed `MAX_SAMPLE_NANOS` (`u64::MAX`, about 584 years). `Duration` inputs above it are rejected too.
- Sample counts, accumulated nanoseconds, and byte totals use checked arithmetic; a record that would wrap any of them is rejected.
- Rejections happen before any mutation: no entry is created and no counter changes.

`TimingError` variants carry a stable `code()` token: `timing_sample_not_finite`, `timing_sample_negative`, `timing_sample_out_of_range`, and `timing_counter_overflow`. Every binding uses `coded_message()` (`"<code>: <message>"`) as its error text ([error contract](error-contract.md#timing-sample-errors)).

### Binding projections

| Binding | Entry points | Units | Invalid input |
|---|---|---|---|
| [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge/src/perf.rs) (`classic::perf`) | `perf_record_timing -> Result<()>`, `perf_get_summary`, `perf_clear_metrics`, `perf_get_operation_count`, `perf_get_operation_average` | seconds | `rust::Error`, message begins with the stable token |
| [`classic-node`](../../node-bindings/classic-node/src/shared.rs) | `recordTimingMetric`, `getMetricsSummary`, `clearAllMetrics` | milliseconds | `Error` with `code === "InvalidArg"`, message begins with the stable token |
| [`classic-perf-py`](../../python-bindings/classic-perf-py/src/lib.rs) (`classic_perf`) | `record_timing`, `get_summary`, `clear_metrics`, `reset_metrics`, `Timer`, `start_timer`, `MetricsSummary` | seconds | `ValueError`, message begins with the stable token |

Missing operations keep their existing projections: absent from summary maps, and `0` / `0.0` from the CXX numeric accessors.

### Seconds-view example

```rust
use classic_shared_core::performance_core::{
    clear_metrics, get_summary, record_timing, start_timer,
};
use std::thread;
use std::time::Duration;

clear_metrics();

for _ in 0..3 {
    let timer = start_timer("load_config");
    thread::sleep(Duration::from_millis(10));
    timer.finish().expect("a short sample cannot overflow");
}

let summary = get_summary();
assert_eq!(summary["load_config"].count, 3);
assert!(summary["load_config"].average >= 0.010);

// Invalid samples are rejected before any state changes.
assert!(record_timing("load_config", f64::NAN).is_err());
assert_eq!(get_summary()["load_config"].count, 3);
```

## `PerformanceMetrics`

Important methods:

- `PerformanceMetrics::new()`
- `record_timing(operation, duration) -> Result<(), TimingError>`
- `record_timing_secs(operation, f64)` / `record_timing_millis(operation, f64)`
- `record_bytes(operation, bytes) -> Result<(), TimingError>`
- `record_timing_with_bytes(operation, duration, Option<bytes>)` - both counters change or neither does
- `get_stats(operation) -> Option<OperationStats>`
- `get_operations() -> Vec<String>` and `all_stats() -> HashMap<String, OperationStats>`
- `clear()` - removes timing **and** byte state

Behavior worth knowing:

- each operation name owns one `DashMap` entry holding its rolling stats (count, sum, min, max as whole nanoseconds) and its byte total
- a record validates every counter under the entry's shard lock before committing, which is what makes rejection mutation-free
- an operation with bytes but no timing sample is not reported by `get_stats`, `get_operations`, or `all_stats`

## `OperationStats`

Fields:

- `count`
- `total`
- `average` (total ÷ count, truncated to whole nanoseconds)
- `min`
- `max`
- `bytes_processed`

Helper:

- `throughput() -> Option<f64>` returns bytes per second only when `bytes_processed > 0` and total duration is non-zero

## `Timer`

Important methods:

- `Timer::start(operation)` / `start_timer(operation)`
- `set_bytes(bytes)`
- `elapsed() -> Duration`
- `finish() -> Result<(), TimingError>`
- `stop() -> Result<(), TimingError>` - alias of `finish()` kept for existing callers; it now returns the overflow error instead of `()`

Contributor notes:

- `finish(self)` consumes the timer and records elapsed time plus any bytes in one atomic update
- an unfinished `Timer` records on drop; it never records twice
- drop cannot return an error, so an overflowing drop record is logged and skipped instead of wrapping

## Free functions and macro

- `record_timing(name, secs)`, `record_timing_millis(name, ms)`, `get_summary()`, `clear_metrics()` - default-store seconds view
- `time_async(operation, future)`
- `time_operation(operation, f)`
- `time_with_bytes(operation, bytes, f)`
- `get_global_metrics() -> &'static Arc<PerformanceMetrics>`
- `get_timer_start() -> Instant`
- `timed!(name, { ... })`

Contributor note:

- the default store is shared by every caller in the linked image; `clear()` / `clear_metrics()` wipe all recorded operations, not just one crate's metrics
- `time_async`, `time_operation`, and `time_with_bytes` cannot surface errors, so an overflowing record is logged and skipped

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

## Generic YAML (`yaml`)

`classic_shared_core::yaml` is the single owner of CLASSIC's domain-neutral YAML rules. The generic rules and logical-key cache moved here from `classic-settings-core` in issue #239, and `YamlOperations` with its path/mtime-aware YAML-file cache followed in issue #240. `classic-settings-core` now only re-exports these items until its retirement (issue #257), so loading through either path reads and clears the **same** default-scope caches.

Everything is reached through the module path, for example `classic_shared_core::yaml::load_yaml_sync` or `classic_shared_core::yaml::validators::SettingType`. Nothing from `yaml` is re-exported at the crate root, which keeps `yaml::Result` from colliding with other crate-root names.

CLASSIC-specific file identity (`YamlFile`) is deliberately **not** here; it stays in [`classic-settings-core`](classic-settings-core.md) until config takes file policy (issue #246).

### Module map

- `SettingsError`, `Result<T>` - loader/merge/cache error type and alias
- `SettingsSource` - distinguishes path-backed and label-backed parse sources
- `Yaml` - re-export of `yaml_rust2::Yaml`
- loaders: `parse_yaml_content`, `load_yaml_sync`, `load_yaml_async`, `load_yaml_merged_sync`, `load_yaml_merged_async`, `load_yaml_batch_sync`, `load_yaml_batch_async`
- merging: `merge_yaml_documents`, `merge_keys`
- logical-key cache: `load_settings_sync`, `load_settings_async`, `load_batch_sync`, `load_batch_async`, `get_cached`, `is_cached`, `invalidate`, `clear_cache`, `cache_size`, `cache_keys`, `cache_stats`, `reset_cache_stats`, `CacheStats`, and the scope handle `LogicalKeyCacheScope`
- YAML-file operations and cache: `YamlOperations`, `YamlCacheStats`, `yaml_cache_stats`, `reset_yaml_cache_stats`, `clear_global_yaml_cache`, and the scope handle `YamlFileCacheScope`
- schema compatibility: `SchemaVersion`, `SchemaParseError`, `SchemaCompat`, `Compatibility`, `schema_compat_check`, `extract_schema_version`, `YamlSchemaError`, `SCHEMA_VERSION_KEY`
- `YamlError` - error type for merge-key resolution and every `YamlOperations` method
- public submodule `validators`: `SettingType`, `CoercedValue`, `validate_setting_value`, `coerce_setting_value`

`accessors`, `error`, `file_cache`, `loader`, `logical_key_cache`, `merge`, `operation_error`, `operations`, and `schema_version` are private submodules; their items are reachable only through the `yaml` re-exports.

### `SettingsSource`

Variants:

- `Path(PathBuf)` - filesystem-backed source used by path-based loaders
- `Label(String)` - logical source name for in-memory content

Helpers and conversions:

- `path() -> Option<&PathBuf>` returns the path only for `Path`
- `label() -> Option<&str>` returns the label only for `Label`
- `From<PathBuf>`, `From<&Path>`, `From<String>`, and `From<&str>` are implemented
- `Display` prints the filesystem path or label text used in error messages

### `SettingsError`

Variants:

- `IoError { path, source }` - disk read failure for a path-backed load
- `YamlParseError { source, message }` - YAML syntax failure tagged with `SettingsSource`
- `EmptyDocument { source }` - empty YAML stream or stream where every document is `BadValue`
- `KeyNotFound(String)` - cache lookup miss for APIs that treat a missing key as an error
- `InvalidYamlStructure { source, index, found }` - merge-time failure when any document is not a mapping
- `TaskJoinError { path, source }` - async batch task failed to join

Behavior worth knowing:

- `IoError` and `YamlParseError` are used by raw load helpers; `EmptyDocument` and `InvalidYamlStructure` by merge helpers; `TaskJoinError` by async batch loading when a spawned task fails to join
- `KeyNotFound` remains part of the public error surface for cache-oriented APIs even though no current call path in this module returns it
- only `IoError` and `TaskJoinError` expose an underlying `source()` error through `std::error::Error`
- parse and merge helpers use `SettingsSource::Label(...)` for in-memory content and `SettingsSource::Path(...)` for file-backed content

### Loaders

These functions read or normalize YAML without touching the cache.

- `parse_yaml_content(source, content)` parses YAML from an in-memory string, preserves the caller-supplied logical source label in parse errors, and returns `Vec<Yaml>`
- `load_yaml_sync(path)` reads with `std::fs::read_to_string`, parses every document with `yaml_rust2::YamlLoader::load_from_str`, and returns `Vec<Yaml>`; failures are `IoError` or `YamlParseError`
- `load_yaml_async(path)` reads with `tokio::fs::read_to_string` and uses the same parse path and error variants
- `load_yaml_merged_sync(path)` / `load_yaml_merged_async(path)` are `load_yaml_*` plus `merge_yaml_documents`, returning one merged `Yaml::Hash`; they are the preferred entry points for crates such as [`classic-config-core`](classic-config-core.md) that consume multi-document files as one mapping
- `load_yaml_batch_sync(paths)` loads sequentially; `load_yaml_batch_async(paths)` spawns one Tokio task per path, then collects results in input order. Both return `Vec<(String, Vec<Yaml>)>` keyed by `path.display().to_string()` and stop at the first failing file. Async join failures surface as `TaskJoinError`, not as parse failures.

The raw loaders never reduce input to the first document; multi-document YAML stays a `Vec<Yaml>` until a caller explicitly merges it.

### Merging

`merge_yaml_documents(source, docs)`:

- reduces a `Vec<Yaml>` into one merged mapping
- requires every document to be a mapping
- merges nested mappings recursively
- replaces sequences, scalars, and type-conflict values with the later document's value
- returns `SettingsError::EmptyDocument` for an empty stream and `SettingsError::InvalidYamlStructure` (zero-based `index`) when any document is not a mapping

`merge_keys(yaml)` resolves YAML merge-key (`<<`) usage after parsing:

- the `<<` value may be a single mapping or a sequence of mappings
- resolution is recursive, including nested merged mappings and arrays containing merged mappings
- explicitly present keys in the current mapping win over merged keys
- when merging a sequence of mappings, earlier mappings win because later inserts do not overwrite existing keys
- the `<<` key is removed from the result
- a `<<` value that is not a mapping or a sequence of mappings returns `YamlError::InvalidValue`

No loader applies merge-key resolution automatically; it is opt-in.

### Logical-key cache

The cache stores parsed YAML documents in a bounded concurrent store per [cache scope](#cache-scopes). The free functions below use the process default scope, of which there is one per linked library image:

- key type: caller-chosen `String`
- value type: `Arc<Vec<Yaml>>`, so callers can cheaply clone values and compare `Arc` identity across reads
- backing store: one `quick_cache::sync::Cache<String, Arc<Vec<Yaml>>>` plus hit/miss counters per scope; the default scope is created lazily on first use
- configured capacity: `64` per scope; `quick_cache` uses bounded eviction, so tests should check that the cache stays within capacity rather than asserting an exact victim order

Population:

- `load_settings_sync(key, path)` / `load_settings_async(key, path)` load through `load_yaml_*`, wrap the documents in `Arc`, insert them under `key`, and return the inserted `Arc`. Re-loading an existing key replaces its value.
- `load_batch_sync(paths)` / `load_batch_async(paths)` load every file, then insert each result under `path.display().to_string()`. On success they return `paths.len()`, not a separately computed insert count.

Freshness: the cache never consults file mtimes, content hashes, or other freshness signals. A key changes only when the caller loads it again or evicts it.

Access and management:

- `get_cached(key) -> Option<Arc<Vec<Yaml>>>` returns a cloned `Arc` if present
- `is_cached(key) -> bool` checks existence without touching hit/miss counters
- `invalidate(key) -> bool` removes one entry and reports whether it existed
- `clear_cache()` removes all entries but leaves counters unchanged
- `cache_size() -> usize` returns the entry count
- `cache_keys() -> Vec<String>` returns all keys in no stable order

`CacheStats`, `cache_stats()`, and `reset_cache_stats()`:

- `CacheStats` fields: `hits`, `misses`, `hit_rate`, `size`, `capacity` (`Serialize`)
- hit/miss counters are per-scope `AtomicU64` values updated **only** by `get_cached()`; loading does not count as a hit or miss
- `capacity` reports the configured bound, `64`
- `reset_cache_stats()` resets counters only; it does not clear entries

`LogicalKeyCacheScope` exposes the same operations as methods (`load_settings_sync`, `load_settings_async`, `load_batch_sync`, `load_batch_async`, `get_cached`, `is_cached`, `invalidate`, `clear_cache`, `cache_size`, `cache_keys`, `cache_stats`, `reset_cache_stats`); each free function is exactly the method of the same name on `LogicalKeyCacheScope::default_scope()`.

This cache is distinct from the path-keyed, mtime-aware [YAML-file cache](#yaml-file-cache) (capacity `128`, `yaml_cache_stats()`); the two never share entries or counters, and their scope handles are separate types.

### Cache scopes

Both caches keep their state behind an opaque, cheaply cloneable scope handle: `LogicalKeyCacheScope` for the logical-key cache and `YamlFileCacheScope` for the YAML-file cache.

- `default_scope()` returns the process default scope. Every unscoped free function (`load_settings_sync`, `get_cached`, `yaml_cache_stats`, `clear_global_yaml_cache`, ...) and every `YamlOperations::new()` object uses it, so Rust, CXX, and Node callers observe one cache per linked library image, exactly as before scopes existed.
- `new_isolated()` creates an empty scope with the same capacity, freshness, counter, and clear rules that shares no entries or counters with any other scope.
- Clones of a handle name the same store; `==` compares store identity (not contents). `Debug` reports only whether the handle is the default scope and its entry count.
- Scopes are never selected from thread-local or task-local state. A caller passes the handle explicitly (or moves a clone into an `async` block), so async work keeps its scope regardless of which runtime thread resumes it.

Why scopes exist: today each of the 18 Python extension modules links its own copy of this crate, so each facade's caches are implicitly separate. When those facades merge into one native extension, the Python adapter preserves that separation by selecting a scope per former facade:

- `classic_settings` uses its own isolated `LogicalKeyCacheScope` and `YamlFileCacheScope`. Its cache functions, every `classic_settings.YamlOperations` object, and its `clear_global_yaml_cache` / `reset_yaml_cache_stats` / `yaml_cache_stats` helpers affect only those stores.
- `classic_config.clear_yaml_cache()` clears the default `YamlFileCacheScope`, which is the store config-core's own `YamlOperations::new()` loaders fill. It never evicts `classic_settings` entries.
- `classic_xse`, `classic_version_registry`, `classic_user_settings`, and `classic_scanlog` only fill the YAML-file cache indirectly, through config-core, Version Registry, and scanlog loaders that call `YamlOperations::new()`. After the merge they share the default scope with `classic_config`. This deliberately narrows #233's per-image rule: none of those facades exposes YAML-file cache stats or controls, entries are mtime-validated, and the Version Registry snapshot is loaded once, so the only effect of a `classic_config.clear_yaml_cache()` on their entries is an extra re-read. Threading a scope through those loaders would change their public Rust signatures for no observable gain.

Parity: the scope handles and `YamlOperations::with_cache_scope` / `cache_scope` are deliberately Rust-only. Bindings never hand a scope to their callers; the CXX and Node adapters keep the unscoped default paths, and the Python adapter selects handles internally. They therefore appear in the Rust API surface baselines without a binding mapping row.

### `YamlOperations`

`YamlOperations` is the integration type for parsing, serializing, saving, and reading dot-path values from single YAML documents, with an optional path/mtime-aware file cache. It moved here from `classic-settings-core` (issue #240), which still re-exports it.

Construction and cache control:

- `YamlOperations::new()` - caching enabled, default `YamlFileCacheScope`
- `YamlOperations::with_cache_scope(scope)` - caching enabled, the given scope
- `cache_scope() -> &YamlFileCacheScope`
- `set_cache_enabled(enabled)` / `is_cache_enabled() -> bool`
- `clear_cache()` - evicts every entry in the object's scope, including entries other objects loaded into it; counters are kept
- `get_cache_stats() -> HashMap<String, usize>` - `cached_files`, `capacity`, and `total_bytes` (raw YAML text retained) for the object's scope

Parsing and file I/O:

- `parse_yaml(content) -> Result<Yaml, YamlError>`
- `dump_yaml(yaml) -> Result<String, YamlError>`
- `load_yaml_file(path) -> Result<Yaml, YamlError>`
- `save_yaml_file(path, yaml) -> Result<(), YamlError>`
- `load_yaml_files_batch(paths) -> HashMap<String, Yaml>` - loads in parallel with Rayon and silently skips files that fail

Generic nested access helpers:

- `get_setting(yaml, key_path) -> Option<Yaml>`
- `set_setting(yaml, key_path, value) -> Result<Yaml, YamlError>`
- `get_settings_batch(yaml, key_paths) -> HashMap<String, Yaml>`
- `set_settings_batch(yaml, settings) -> Result<Yaml, YamlError>`

Typed extraction helpers:

- `get_string_value(data, key_path, default) -> String`
- `get_vec_value(data, key_path) -> Vec<String>`
- `get_hashmap_value(data, key_path) -> HashMap<String, String>`
- `get_indexmap_value(data, key_path) -> IndexMap<String, String>`
- `get_hashmap_vec_value(data, key_path) -> HashMap<String, Vec<String>>`
- `get_indexmap_vec_value(data, key_path) -> IndexMap<String, Vec<String>>`

Behavior worth knowing:

- `parse_yaml()` and `load_yaml_file()` always return only the first YAML document from multi-document input (unlike the `load_yaml_*` loaders, which preserve all documents).
- `parse_yaml()` does not apply merge-key resolution; call `merge_keys()` explicitly.
- Dot-path traversal only walks `Yaml::Hash` nodes. Array indexing is not supported.
- `get_setting()` clones and returns the final `Yaml` value.
- `set_setting()` creates missing intermediate hashes and will replace a non-hash intermediate node with a new hash to complete the requested path. Empty or whitespace-only paths return `YamlError::InvalidKeyPath`.
- Typed extraction helpers are intentionally lossy: they silently drop non-string items and type mismatches instead of raising errors.

The Node `yamlGetIndexmapValue` adapter preserves the core map's insertion order
for ordinary string keys by inserting them directly into its returned JavaScript
object. JavaScript enumerates integer-index keys numerically, so that language
rule still applies to numeric-looking YAML keys.

### YAML-file cache

`load_yaml_file(path)` flow:

1. If the object's caching is enabled, look up the exact `PathBuf` in the object's scope (path spelling is **not** canonicalized).
2. If an entry exists and the file's current modification time is not newer than the cached one, count a hit and return a clone.
3. Otherwise remove any stale entry, count a miss, read with `std::fs::read_to_string`, parse with `YamlLoader`, keep the first document, and (if caching is enabled) insert it with its mtime and raw text.

A load with caching disabled always counts a miss and never inserts.

`save_yaml_file(path, yaml)` serializes with `dump_yaml()`, writes `path.with_extension("yaml.tmp")`, renames it onto the target, and, if caching is enabled, removes the target path from the object's scope only.

Observability, all on the default scope unless called through a `YamlFileCacheScope` handle:

- `YamlCacheStats` - `hits`, `misses`, `hit_rate`, `size`, `capacity` (`Serialize`, exactly these five fields)
- `yaml_cache_stats()` / `YamlFileCacheScope::stats()` - counters plus current size and capacity (`128`)
- `reset_yaml_cache_stats()` / `YamlFileCacheScope::reset_stats()` - reset hit/miss counters only; entries stay
- `clear_global_yaml_cache()` / `YamlFileCacheScope::clear()` - remove all entries; counters stay

The `yaml_cache_stats` / `YamlCacheStats` names deliberately differ from the logical-key cache's `cache_stats` / `CacheStats` so the two caches are never confused.

### C++ bridge surface

The C++ bridge module `classic::settings` exposes this surface through `yaml_ops_*` functions (parse, dump, load, save, get/set setting, typed getters, `yaml_ops_cache_stats`, `yaml_ops_cache_size`, `yaml_ops_clear_cache`) on an opaque `YamlOps` handle, plus `YamlCacheStatsDto`. They always use the default scopes. See [`classic-cpp-bridge-data-entrypoints.md`](classic-cpp-bridge-data-entrypoints.md) for the full entry-point list.

### Validators (`yaml::validators`)

`SettingType` variants: `Int`, `Bool`, `Float`, `Path`, `String`.

`CoercedValue` variants: `Int(i64)`, `Bool(bool)`, `Float(f64)`, `Path(String)`, `String(String)`, with accessors `as_i64()`, `as_bool()`, `as_f64()`, and `as_str()` (for `String` and `Path`).

`validate_setting_value(value, expected_type) -> bool`:

- `Int` uses `parse::<i64>()`
- `Bool` accepts `true/false`, `yes/no`, `1/0`, and `on/off`, case-insensitive
- `Float` uses `parse::<f64>()`, so integer strings also validate as float
- `Path` accepts any non-empty string
- `String` always validates

`coerce_setting_value(value, target_type) -> Result<CoercedValue, String>` follows the same rules; `Path` rejects only the empty string and `String` always succeeds. Coercion failures are plain `String` messages, not typed errors.

### Schema compatibility

- `SchemaVersion { major, minor }` parses from a strict `"MAJOR.MINOR"` string (`FromStr`) and displays the same way; ordering is major-then-minor
- `SchemaParseError`: `MissingSeparator`, `TooManyComponents`, `EmptyComponent`, `NonDigitComponent`, `ComponentOverflow`
- `extract_schema_version(doc)` reads the root `schema_version` key (`SCHEMA_VERSION_KEY`). A missing or null key is `YamlSchemaError::Missing`; an unquoted number, an integer, or another non-string value is `YamlSchemaError::Malformed`. `YamlSchemaError::with_file(label)` attaches a file label to `Malformed` and leaves `Missing` unchanged.
- `SchemaCompat::new(accepted_major, minimum_minor)` describes what a client accepts; `schema_compat_check(&version, &compat)` returns `Compatible`, `IncompatibleMajor { file_major, client_accepted_major }`, or `IncompatibleMinor { file_minor, client_minimum_minor }`

Per-file schema ranges (which CLASSIC file accepts which range) are domain policy and stay with the file-policy owner, not here.

### `YamlError`

Variants: `ParseError(String)`, `SerializeError(String)`, `IoError(std::io::Error)`, `EmptyDocument`, `InvalidValue(String)`, `UnresolvedAlias`, `InvalidKeyPath(String)`, `TypeConversionError(String)`.

`merge_keys()` returns it (`InvalidValue`), and `YamlOperations` uses it for its parse (`ParseError`, `EmptyDocument`), serialize (`SerializeError`), I/O (`IoError`), and key-path (`InvalidKeyPath`) errors.

### Runtime

Sync loaders use `std::fs`; async loaders use `tokio::fs` and run on whatever runtime polls them, and async batch loading uses `tokio::spawn` on that runtime. The module never creates a runtime; CLASSIC callers drive it through `get_runtime()`.

### Example

```rust
use classic_shared_core::yaml::{get_cached, load_settings_sync};
use std::path::Path;

let docs = load_settings_sync("ignore", Path::new("CLASSIC Ignore.yaml"))?;

let cached = get_cached("ignore").expect("document should be cached after load");
assert!(std::sync::Arc::ptr_eq(&docs, &cached));

# Ok::<(), classic_shared_core::yaml::SettingsError>(())
```

Use a non-User-Settings document; first-party production code must use [`classic-user-settings-core`](classic-user-settings-core.md) for `CLASSIC Settings.yaml`.

## Loose versions and PE helpers (`version`)

`classic_shared_core::version` is the domain-neutral owner of CLASSIC's lenient version-string helpers and Windows PE file-version extraction (issue #243). It knows nothing about which game or XSE versions exist: known-version queries are Version Registry policy and stay outside shared core.

The former `classic_version_core` root and `classic_version_core::pe_version` paths re-export these exact items until that crate retires (issue #258). Values, `VersionError` / `PeVersionError` variants, and their messages are unchanged by the move. New callers import `classic_shared_core::version` directly. `classic-xse-core` no longer re-exports `parse_version()`, `try_parse_version()`, or `compare_versions()`.

Parity ownership: CXX, Node, and Python rows for these helpers name `classic-shared-core` while keeping their row IDs and exported operation identities. Rust-only `@rust` proxy rows for items `classic-version-core` still re-exports name that facade. Do not restore `classic-version-core` as the owner of the binding rows during a baseline refresh. The `version-operations`, `version-extraction`, `version-pe`, and `version-pe-path` conformance packs name `classic-shared-core` as their `domainOwner`; `version-f4se` names the known-version policy owner, `classic-version-registry-core`.

### `VersionError` and `VersionResult<T>`

Variants:

- `ParseError(String)` - a numeric component failed to parse (`Invalid version string: Invalid major version: x`)
- `EmptyVersion` - the input was exactly empty (`Version string is empty`)
- `NotFound(String)` - public, but no current helper constructs it
- `InvalidFormat(String)` - fewer than two dot-separated components (`Invalid version format: Version must have at least major.minor: 1`)

Whitespace-only input becomes `InvalidFormat` after trimming, not `EmptyVersion`.

### `parse_version()` and `try_parse_version()`

`parse_version(version_str) -> VersionResult<semver::Version>` normalizes loose shapes such as `1.10.163`, `1.10.163.0`, `v1.10.163`, `V1.10.163`, and `1.10`:

- trims surrounding whitespace and strips a leading `v` or `V`
- requires at least `major.minor`; defaults `patch = 0` when only two components are present
- ignores any component after the third, including the game build number; extra components are not rejected
- does not support pre-release or build-metadata syntax such as `1.2.3-alpha` (use `semver::Version::parse` for strict semver, as the update channels do)

`try_parse_version()` is `parse_version().ok()`.

### `compare_versions()` and `format_version()`

- `compare_versions(v1, v2) -> Ordering` is `semver::Version::cmp()`; no registry data is involved.
- `format_version(version, prefix) -> String` returns `version.to_string()`, or `format!("{prefix}{version}")` when a prefix is supplied. It neither validates nor reparses.

### Text extraction helpers

All three return `Option`/`Vec` rather than a typed error, and all drop a fourth numeric component.

- `extract_version_from_filename(filename) -> Option<Version>` tries `v?major.minor.patch.build`, then `v?major.minor.patch`, then `v?major.minor`, returning the first match of the first pattern that matches.
- `extract_version_from_log(log_content) -> Option<Version>` first looks for `(?i)version[:\s]+v?major.minor.patch(.build)?` and falls back to `extract_version_from_filename(log_content)`. The first match wins, so an XSE `version` line can precede a later game-version line.
- `extract_all_versions(content) -> Vec<Version>` collects every `v?major.minor.patch(.build)?` match in regex order, keeping duplicates.

### `pe_version`

- `is_valid_executable_path(path) -> bool` checks that the path exists, is a file, and has a case-insensitive `.exe` or `.dll` extension. It does not verify the bytes are a PE image.
- `extract_pe_version(path) -> PeVersionResult<(u16, u16, u16, u16)>` validates the path, reads the whole file into memory, parses it with `pelite`, and returns the `VS_FIXEDFILEINFO` `(Major, Minor, Patch, Build)` file version. It is not a streaming API, and it is the only helper that keeps all four components.

`PeVersionError` variants:

- `InvalidPath(PathBuf)` - nonexistent path or wrong extension (both fail `is_valid_executable_path()` first)
- `IoError { path, source }` - the file passed validation but could not be read
- `InvalidPe(String)` - `pelite` could not parse a usable PE image or resources block
- `NoVersionInfo(PathBuf)` - the PE parsed but has no readable version resource

The string helpers are cross-platform. The PE helpers read the Portable Executable format, but they run on any platform when pointed at a real PE file. Nothing here reads ELF or Mach-O metadata.

### Example

```rust,no_run
use classic_shared_core::version::{compare_versions, extract_pe_version, parse_version};
use std::path::Path;

let installed = parse_version("1.10.163.0")?;
let required = parse_version("v1.10.984")?;
assert!(compare_versions(&installed, &required).is_lt());

let (major, minor, patch, build) =
    extract_pe_version(Path::new("C:/Games/Fallout4/Fallout4.exe"))?;
println!("PE file version: {major}.{minor}.{patch}.{build}");

# Ok::<(), Box<dyn std::error::Error>>(())
```

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

- [`business-logic/classic-config-core/src/lib.rs`](../../business-logic/classic-config-core/src/lib.rs) re-exports `get_runtime`
- [`cpp-bindings/classic-cpp-bridge/src/lib.rs`](../../cpp-bindings/classic-cpp-bridge/src/lib.rs) documents `get_runtime().block_on(...)` as the C++ bridge pattern
- [`node-bindings/classic-node/src/fileio.rs`](../../node-bindings/classic-node/src/fileio.rs) and sibling modules clone the shared runtime handle for Node task execution
- [`ui-applications/classic-tui/src/app.rs`](../../ui-applications/classic-tui/src/app.rs) uses `get_runtime().spawn(...)`

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

- `SettingsError` and `YamlError` in this crate's own [`yaml`](#generic-yaml-yaml) module, which `classic-settings-core` re-exports
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
- `yaml-rust2` - YAML parsing and the exposed `yaml::Yaml` type
- `quick_cache` - bounded logical-key and YAML-file cache stores
- `indexmap` - insertion-ordered `YamlOperations` extraction helpers
- `tracing` - logical-key and YAML-file cache hit/miss trace events
- `semver` and `regex` - the `version` module's normalized 3-part versions and text extraction
- `pelite` - PE resource parsing for `version::pe_version::extract_pe_version()`

Related CLASSIC crates and consumers:

- [`classic-config-core`](../../business-logic/classic-config-core) - re-exports `get_runtime` and depends on the shared-runtime rule
- [`classic-file-io-core`](../../business-logic/classic-file-io-core), [`classic-database-core`](../../business-logic/classic-database-core), and [`classic-scanlog-core`](../../business-logic/classic-scanlog-core) - async business-logic crates expected to run on the shared runtime
- [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge) and [`classic-node`](../../node-bindings/classic-node) - binding layers that call into async Rust using the shared runtime
- [`classic-shared-py`](../../foundation/classic-shared-py) - PyO3 wrapper over this crate's runtime/error/path/performance/string helpers
- [`classic-gui`](../../classic-gui) and Rust UI crates such as [`ui-applications/classic-tui`](../../ui-applications/classic-tui) - UI surfaces that depend on the same runtime policy; Slint-style bridging is feature-gated here

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
- `path_core`, `performance_core`, `strings_core`, `version`, and `yaml` are public modules, not root-level re-exports.
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
- public module types in `path_core`, `performance_core`, `strings_core`, `version`, `yaml`, or `async_bridge`
- loose version acceptance rules, extraction regexes or precedence, or PE validation and extraction behavior
- logical-key or YAML-file cache capacity, freshness, counter, clear, or scope behavior
- the `YamlOperations` surface, typed extraction semantics, or merge-key handling
- feature-gated GUI bridge behavior or dispatcher assumptions
