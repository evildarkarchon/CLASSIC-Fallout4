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
mod tests {
    use serial_test::serial;

    use super::*;

    #[test]
    #[serial]
    fn test_record_and_summary() {
        perf_clear_metrics();
        perf_record_timing("cxx_rec_summary", 0.5);
        perf_record_timing("cxx_rec_summary", 1.0);

        let summary = perf_get_summary();
        assert!(!summary.is_empty());
        let test_line = summary.iter().find(|s| s.contains("cxx_rec_summary"));
        assert!(test_line.is_some());
    }

    #[test]
    #[serial]
    fn test_operation_count() {
        perf_clear_metrics();
        perf_record_timing("cxx_count_op", 0.1);
        perf_record_timing("cxx_count_op", 0.2);
        perf_record_timing("cxx_count_op", 0.3);
        assert_eq!(perf_get_operation_count("cxx_count_op"), 3);
    }

    #[test]
    #[serial]
    fn test_operation_average() {
        perf_clear_metrics();
        perf_record_timing("cxx_avg_op", 1.0);
        perf_record_timing("cxx_avg_op", 3.0);
        let avg = perf_get_operation_average("cxx_avg_op");
        assert!((avg - 2.0).abs() < f64::EPSILON);
    }

    #[test]
    #[serial]
    fn test_clear_metrics() {
        perf_record_timing("cxx_clear_op", 1.0);
        assert!(perf_get_operation_count("cxx_clear_op") >= 1);
        perf_clear_metrics();
        assert_eq!(perf_get_operation_count("cxx_clear_op"), 0);
    }

    #[test]
    #[serial]
    fn test_missing_operation() {
        perf_clear_metrics();
        assert_eq!(perf_get_operation_count("cxx_nonexistent_op"), 0);
        assert!((perf_get_operation_average("cxx_nonexistent_op")).abs() < f64::EPSILON);
    }
}
