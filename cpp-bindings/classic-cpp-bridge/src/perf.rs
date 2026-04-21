//! Performance monitoring bridge for CXX FFI.
//!
//! Bridges `classic_perf_core` for recording timings and retrieving
//! summary statistics.

use classic_perf_core::{clear_metrics, get_summary, record_timing};

fn perf_record_timing(operation: &str, duration_secs: f64) {
    record_timing(operation, duration_secs);
}

fn perf_get_summary() -> Vec<String> {
    let summary = get_summary();
    summary
        .iter()
        .map(|(name, stats)| {
            format!(
                "{}: count={}, total={:.3}s, avg={:.3}s, min={:.3}s, max={:.3}s",
                name, stats.count, stats.total, stats.average, stats.min, stats.max
            )
        })
        .collect()
}

fn perf_clear_metrics() {
    clear_metrics();
}

fn perf_get_operation_count(operation: &str) -> u32 {
    let summary = get_summary();
    summary.get(operation).map(|s| s.count as u32).unwrap_or(0)
}

fn perf_get_operation_average(operation: &str) -> f64 {
    let summary = get_summary();
    summary.get(operation).map(|s| s.average).unwrap_or(0.0)
}

#[cxx::bridge(namespace = "classic::perf")]
mod ffi {
    extern "Rust" {
        fn perf_record_timing(operation: &str, duration_secs: f64);
        fn perf_get_summary() -> Vec<String>;
        fn perf_clear_metrics();
        fn perf_get_operation_count(operation: &str) -> u32;
        fn perf_get_operation_average(operation: &str) -> f64;
    }
}

#[cfg(test)]
#[path = "perf_tests.rs"]
mod tests;
