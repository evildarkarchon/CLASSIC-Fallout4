# `classic-perf-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-perf-core/`](../../business-logic/classic-perf-core).

Crate metadata:

- Crate: `classic-perf-core`
- Description: `Seconds-based timing facade over classic-shared-core for CLASSIC`

This crate owns no timing state or logic. Its crate root re-exports the seconds view of [`classic_shared_core::performance_core`](classic-shared-core.md#performancemetrics-timer-and-helpers), which is the sole rolling `Duration` timing implementation. Recording through this facade, through `classic_shared_core::performance_core::get_global_metrics()`, or through a `Timer` therefore reads and clears **one default metrics store per linked library image**.

The crate identity is scheduled for retirement (issue #256) once its remaining callers (the C++ bridge, Node, and `classic-perf-py`) import `classic_shared_core::performance_core` directly. Until then its re-exported paths stay valid.

Parity ownership: the CXX, Node, and Python parity contracts name `classic-shared-core` as the owning Rust crate for every binding-mapped timing row, because the behavior lives there. Do not restore `classic-perf-core` as the owner during a baseline refresh. The only rows that still name `classic-perf-core` are the Node contract's Rust-only `reexport` rows (`perf.Timer@rust`, `perf.start_timer@rust`), which record this facade's own re-export surface.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Root-Level Public API

Everything below is a `pub use` of the same-named item in `classic_shared_core::performance_core`:

- `MetricsSummary` - seconds-based `count` / `total` / `average` / `min` / `max` for one operation
- `record_timing(name, duration_secs) -> Result<(), TimingError>` - record one sample, in seconds, into the default store
- `record_timing_millis(name, duration_ms) -> Result<(), TimingError>` - record one sample, in milliseconds, into the default store
- `get_summary() -> HashMap<String, MetricsSummary>` - snapshot every operation in the default store
- `clear_metrics()` - clear all timing **and byte** state in the default store
- `Timer` / `start_timer(name)` - RAII timer (`start`, `set_bytes`, `elapsed() -> Duration`, `finish() -> Result<(), TimingError>`) that records at most once, on `finish()` or on drop
- `TimingError` / `MetricCounter` - typed rejection reasons

See the shared-core guide for the storage model and full semantics.

---

## Sample Contract

- A floating-point sample must be finite and nonnegative. `-0.0` is treated as zero.
- A valid sample is rounded **once**, from its exact binary value, to the nearest nanosecond (ties to even). `record_timing_millis` scales milliseconds in the same single step instead of dividing into seconds first.
- One sample may not exceed `u64::MAX` nanoseconds (about 584 years).
- Per-operation sample counts, accumulated nanoseconds, and byte totals use checked arithmetic. A record that would wrap any of them is rejected.
- Every rejection happens before any state changes: no operation is created, and existing counters are untouched.
- Summaries come from whole-nanosecond rolling statistics. The average is the total divided by the count, truncated to whole nanoseconds. Values may differ from the retired `f64` sample-vector implementation at nanosecond precision.

## Error Handling Model

`TimingError` variants and their stable `code()` tokens:

| Variant | `code()` | Raised when |
|---|---|---|
| `NonFinite { value }` | `timing_sample_not_finite` | NaN or ±infinity |
| `Negative { value }` | `timing_sample_negative` | below zero (not `-0.0`) |
| `SampleOutOfRange` | `timing_sample_out_of_range` | more than `u64::MAX` ns after rounding |
| `CounterOverflow { operation, counter }` | `timing_counter_overflow` | the operation's sample count, total duration, or byte total would wrap |

`Timer::finish` returns `CounterOverflow` when its record would wrap. Dropping an unfinished timer cannot report an error, so an overflowing drop record is logged and skipped rather than wrapped. Bindings project every variant as their invalid-argument error; see [`error-contract.md`](error-contract.md#timing-sample-errors).

---

## Binding Projections

| Binding | Entry points | Units | Invalid input |
|---|---|---|---|
| [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge/src/perf.rs) (`classic::perf`) | `perf_record_timing -> Result<()>`, `perf_get_summary`, `perf_clear_metrics`, `perf_get_operation_count`, `perf_get_operation_average` | seconds | `rust::Error`, message begins with the stable token |
| [`classic-node`](../../node-bindings/classic-node/src/shared.rs) | `recordTimingMetric`, `getMetricsSummary`, `clearAllMetrics` | milliseconds | `Error` with `code === "InvalidArg"`, message begins with the stable token |
| [`classic-perf-py`](../../python-bindings/classic-perf-py/src/lib.rs) (`classic_perf`) | `record_timing`, `get_summary`, `clear_metrics`, `reset_metrics`, `Timer`, `start_timer`, `MetricsSummary` | seconds | `ValueError`, message begins with the stable token |

Missing operations keep their existing projections: absent from summary maps, and `0` / `0.0` from the CXX numeric accessors.

Each linked library image has its own default store. Within one image, every view shares it. In the current Python packaging, `classic_perf` and `classic_shared` are separate extension images, so each has its own store. They will share one store once the single-wheel adapter lands (issue #259).

---

## Usage Example

```rust
use classic_perf_core::{clear_metrics, get_summary, record_timing, start_timer};
use std::thread;
use std::time::Duration;

clear_metrics();

for _ in 0..3 {
    let timer = start_timer("load_config");
    thread::sleep(Duration::from_millis(10));
    timer.finish().expect("a short sample cannot overflow");
}

let summary = get_summary();
let stats = summary.get("load_config").unwrap();
assert_eq!(stats.count, 3);
assert!(stats.average >= 0.010);

// Invalid samples are rejected before any state changes.
assert!(record_timing("load_config", f64::NAN).is_err());
assert_eq!(get_summary()["load_config"].count, 3);
```

---

## Contributor Notes

- Do not add state or logic here; change `classic_shared_core::performance_core` instead.
- New Rust callers should import `classic_shared_core::performance_core` directly. This facade exists only until issue #256 retires it.
- `clear_metrics()` clears the whole default store for the linked image, including state recorded through shared-core APIs and byte totals.
