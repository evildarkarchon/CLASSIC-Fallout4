# `classic-perf-core` API Guide

Contributor-facing API documentation for [`ClassicLib-rs/business-logic/classic-perf-core/`](../../ClassicLib-rs/business-logic/classic-perf-core).

Crate metadata:

- Crate: `classic-perf-core`
- Description: `Performance monitoring and timing utilities for CLASSIC`

This crate is a small, process-wide timing helper used to record named duration samples and derive summary statistics on demand. It is intentionally narrower than most business-logic crates: it does not own async runtime behavior, domain-specific metrics, or reporting pipelines. It just stores timing samples behind global state and exposes simple APIs for recording, timing, clearing, and summarizing them.

In current repo usage, this crate mainly serves shared and binding layers that want a lightweight metrics bucket without pulling in heavier domain logic. Node, Python, and the C++ bridge all adapt this crate's data into their own ABI-friendly shapes.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- record a named timing sample as seconds
- wrap a block of work in an RAII timer and record automatically on drop
- retrieve aggregate `count` / `total` / `average` / `min` / `max` statistics per operation name
- clear all collected metrics in the current process, especially in tests or isolated measurement sessions
- share one simple timing store across Rust code and binding adapters

Do not use this crate for:

- runtime orchestration or async scheduling
- typed domain metrics with labels, tags, histograms, percentiles, or counters
- long-running production telemetry retention
- per-request or per-subsystem isolation
- structured error reporting

This is a low-level helper crate. Higher-level interpretation of what an operation name means belongs to the caller.

---

## Module And API Map

This crate has two internal modules, but its public API is exposed from the crate root.

## Internal modules

- `metrics` - global metrics store plus summary generation
- `timer` - RAII timer type and convenience constructor

## Root-level public API

- `MetricsSummary` - summary struct for one operation's recorded samples
- `record_timing(name, duration_secs)` - append one duration sample
- `get_summary() -> HashMap<String, MetricsSummary>` - compute summaries for all operations
- `clear_metrics()` - clear the entire global metrics store
- `Timer` - running timer that records on `finish()` or `Drop`
- `start_timer(name) -> Timer` - convenience constructor for `Timer`

Contributor note:

- unlike some other CLASSIC crates, there are no public submodules to import from; callers use root paths such as `classic_perf_core::start_timer`

---

## Public API Surface

## `MetricsSummary`

`MetricsSummary` is the only public data model in this crate.

Fields:

- `count: usize`
- `total: f64`
- `average: f64`
- `min: f64`
- `max: f64`

All values are measured in seconds.

Behavior visible in `src/metrics.rs`:

- summaries are computed from the currently stored raw sample list for one operation
- `MetricsSummary` derives `Clone`, `Debug`, `Serialize`, and `Deserialize`
- summary construction is internal; callers cannot build one through a public constructor in this crate

## `record_timing(name, duration_secs)`

`record_timing` is the lowest-level write API.

Behavior visible in source:

- stores metrics under a `String` key derived from `name`
- appends `duration_secs` to that operation's sample vector
- creates the vector on first write for a name
- returns `()` and does not report validation errors

Important contributor note:

- the function accepts any `f64` value; current source does not reject negative, NaN, or infinite durations before storing them

## `get_summary() -> HashMap<String, MetricsSummary>`

`get_summary` is the main read API.

Behavior visible in source:

- iterates every operation currently present in the global metrics store
- skips empty vectors if any exist internally
- computes `count`, `total`, `average`, `min`, and `max` for each operation
- returns a fresh `HashMap`, not a live view into the underlying storage

Contributor implications:

- summary computation happens at read time, not write time
- the crate stores individual samples, so memory use grows with the number of recorded timings
- the returned map has no documented ordering guarantees

## `clear_metrics()`

- clears the entire process-wide metrics store
- is heavily used in this crate's tests to isolate assertions
- affects all users of `classic-perf-core` in the current process, not just the current caller or subsystem

## `Timer`

`Timer` is the RAII timing helper.

Construction and methods:

- `Timer::new(name)` - start timing immediately
- `finish(self)` - consume the timer and record elapsed time once
- `elapsed(&self) -> f64` - inspect elapsed time without recording yet

Behavior visible in `src/timer.rs`:

- the timer stores `name`, `Instant::now()` at creation, and a private `finished` flag
- `finish(self)` records elapsed seconds through `record_timing`
- `Drop` also records elapsed seconds when `finish()` was not called
- `finish(self)` consumes the timer, which prevents later accidental reuse

Contributor note:

- explicit `finish()` and implicit drop both write into the same global store; the type is designed to avoid double-recording for a single timer instance

## `start_timer(name) -> Timer`

- thin convenience wrapper over `Timer::new(name)`
- this is the most common entry point used in examples and tests

---

## Timing And Summary Flow

The source-visible flow is straightforward and fully global:

1. A caller either calls `record_timing(...)` directly or creates a `Timer` with `start_timer(...)` or `Timer::new(...)`.
2. A `Timer` captures `Instant::now()` at construction.
3. The caller either calls `finish()` or lets the timer drop.
4. The timer converts elapsed time to seconds with `as_secs_f64()` and forwards it to `record_timing(...)`.
5. `record_timing(...)` appends the sample into the global `DashMap<String, Vec<f64>>`.
6. Later, `get_summary()` walks the whole map and computes aggregate statistics per operation name.
7. `clear_metrics()` discards all accumulated samples when the caller needs a fresh measurement session.

This means the crate separates write-time sample capture from read-time aggregation. There is no rolling summary cache in the current implementation.

---

## Error Handling Model

This crate does not currently expose a crate-specific error type or `Result` alias.

Public behavior is intentionally fail-soft and minimal:

- `record_timing(...)` is infallible at the API level
- `get_summary()` always returns a map, including an empty map when nothing has been recorded
- `clear_metrics()` is infallible
- `Timer::finish()` and `Timer::elapsed()` are infallible

Contributor implications:

- callers do not get validation errors for suspicious duration values
- there is no typed distinction between "no samples recorded" and "metrics were cleared"; both produce an empty summary map
- if you need richer validation or telemetry contracts, add them in a higher-level crate instead of assuming this crate already has them

Source-backed note:

- `Cargo.toml` depends on `thiserror`, but the current public source under `src/` does not define or export an error enum

---

## Concurrency And Global State Notes

This crate is explicitly process-global.

Implementation details visible in `src/metrics.rs`:

- storage is one `static` `std::sync::LazyLock<DashMap<String, Vec<f64>>>`
- initialization happens on first access
- operation names are shared across the whole process namespace
- each operation stores every recorded sample in a `Vec<f64>`

Contributor cautions:

- metrics recorded by unrelated subsystems share the same namespace and storage
- `clear_metrics()` can interfere with parallel tests or concurrent consumers if called carelessly
- operation names should be chosen deliberately to avoid accidental collisions across bindings or subsystems
- unlike a fixed-size rolling aggregator, this implementation keeps raw samples, so hot paths with many recordings can grow memory usage over time

The crate's own tests use `serial_test` because the metrics store is global mutable state.

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `dashmap` - concurrent process-wide metrics storage
- `std::sync::LazyLock` - standard-library lazy initialization of the global store
- `serde` - serialization support on `MetricsSummary`

Related CLASSIC crates and wrappers:

- [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/perf.rs) - exposes `record`, `clear`, and stringified summary helpers for C++ callers
- [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node/src/shared.rs) - converts the Rust summary into JavaScript-friendly timing objects, using milliseconds at the API edge
- [`classic-perf-py`](../../ClassicLib-rs/python-bindings/classic-perf-py/src/lib.rs) - exposes structured metric summaries plus a Python wrapper over `Timer`
- [`binding-parity-overview.md`](binding-parity-overview.md) - compares how C++, Node, and Python currently narrow or preserve this crate's surface
- [`classic-shared-core`](classic-shared-core.md) - has its own separate `performance_core` helper module; do not assume the two crates expose the same API or storage model

That last point matters for contributors: `classic-perf-core` is its own crate with its own global state. It is not a re-export of `classic_shared_core::performance_core`.

---

## Usage Example

This example stays close to the crate's real `examples/basic_timing.rs` and root API.

```rust
use classic_perf_core::{clear_metrics, get_summary, start_timer};
use std::thread;
use std::time::Duration;

clear_metrics();

for _ in 0..3 {
    let timer = start_timer("load_config");
    thread::sleep(Duration::from_millis(10));
    timer.finish();
}

let summary = get_summary();
let stats = summary.get("load_config").unwrap();

assert_eq!(stats.count, 3);
assert!(stats.average >= 0.010);
```

You can also rely on drop-based recording when that matches the call site better:

```rust
use classic_perf_core::{clear_metrics, get_summary, start_timer};
use std::thread;
use std::time::Duration;

clear_metrics();

{
    let _timer = start_timer("parse_yaml");
    thread::sleep(Duration::from_millis(5));
}

assert!(get_summary().contains_key("parse_yaml"));
```

---

## Contributor Notes And Known Limits

- the public API is only the crate-root re-exports from `src/lib.rs`
- this crate stores raw timing samples and computes summaries later; it does not keep a constant-memory rolling aggregate today
- `record_timing(...)` does not validate numeric inputs before storing them
- all durations and summaries are in seconds inside the Rust API; some bindings convert to milliseconds at their boundary
- the metrics store is process-global and shared across Rust, C++, Node, and Python consumers in the same process
- `clear_metrics()` is convenient for tests but risky in shared integration flows
- `Cargo.toml` lists `serde_json` and `thiserror`, but the current public source does not expose JSON-specific or error-typed APIs

If you extend this crate, update this document when you change:

- root-level exports in `src/lib.rs`
- the storage model in `src/metrics.rs`
- the summary fields or units in `MetricsSummary`
- `Timer` finish/drop behavior
- binding-facing assumptions about units or summary shape
