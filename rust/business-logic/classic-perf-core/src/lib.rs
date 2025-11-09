//! Performance monitoring and timing utilities for CLASSIC.
//!
//! This crate provides high-precision timing, metrics collection, and
//! performance analysis tools for both Rust and Python (via PyO3 bindings).
//!
//! # Features
//!
//! - **High-precision timing** using `std::time::Instant`
//! - **Thread-safe metrics storage** with lock-free concurrent access
//! - **Summary statistics** (count, total, average, min, max)
//! - **Zero-allocation timing** for hot paths
//! - **Context-based timing** with RAII guards
//!
//! # Architecture
//!
//! Metrics are stored in a global `DashMap` for lock-free concurrent access.
//! Each operation stores individual timing samples, enabling detailed analysis.
//!
//! # Examples
//!
//! ```rust
//! use classic_perf_core::{start_timer, get_summary, clear_metrics};
//! use std::thread;
//! use std::time::Duration;
//!
//! // Time an operation
//! let timer = start_timer("my_operation");
//! thread::sleep(Duration::from_millis(100));
//! timer.finish(); // Automatically records timing
//!
//! // Get summary statistics
//! let summary = get_summary();
//! if let Some(stats) = summary.get("my_operation") {
//!     println!("Average: {:.3}ms", stats.average * 1000.0);
//! }
//!
//! // Clear metrics
//! clear_metrics();
//! ```

mod metrics;
mod timer;

pub use metrics::{MetricsSummary, clear_metrics, get_summary, record_timing};
pub use timer::{Timer, start_timer};

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;
    use std::thread;
    use std::time::Duration;

    #[test]
    #[serial]
    fn test_timer_basic() {
        clear_metrics();

        let timer = start_timer("test_op");
        thread::sleep(Duration::from_millis(10));
        timer.finish();

        let summary = get_summary();
        assert!(summary.contains_key("test_op"));
        let stats = summary.get("test_op").unwrap();
        assert_eq!(stats.count, 1);
        assert!(stats.total >= 0.010); // At least 10ms
    }

    #[test]
    #[serial]
    fn test_multiple_timings() {
        clear_metrics();

        for _i in 0..5 {
            let timer = start_timer("batch_op");
            thread::sleep(Duration::from_millis(10));
            timer.finish();
        }

        let summary = get_summary();
        let stats = summary.get("batch_op").unwrap();
        assert_eq!(stats.count, 5);
        assert!(stats.average >= 0.010);
    }

    #[test]
    #[serial]
    fn test_summary_statistics() {
        clear_metrics();

        // Record timings with known values
        record_timing("stats_test", 1.0);
        record_timing("stats_test", 2.0);
        record_timing("stats_test", 3.0);
        record_timing("stats_test", 4.0);
        record_timing("stats_test", 5.0);

        let summary = get_summary();
        let stats = summary.get("stats_test").unwrap();

        assert_eq!(stats.count, 5);
        assert_eq!(stats.total, 15.0);
        assert_eq!(stats.average, 3.0);
        assert_eq!(stats.min, 1.0);
        assert_eq!(stats.max, 5.0);
    }

    #[test]
    #[serial]
    fn test_clear_metrics() {
        clear_metrics();

        record_timing("clear_test", 1.0);
        assert!(get_summary().contains_key("clear_test"));

        clear_metrics();
        assert!(!get_summary().contains_key("clear_test"));
    }

    #[test]
    #[serial]
    fn test_thread_safety() {
        clear_metrics();

        let handles: Vec<_> = (0..10)
            .map(|i| {
                thread::spawn(move || {
                    for _ in 0..10 {
                        let timer = start_timer(format!("thread_{}", i));
                        thread::sleep(Duration::from_micros(100));
                        timer.finish();
                    }
                })
            })
            .collect();

        for handle in handles {
            handle.join().unwrap();
        }

        let summary = get_summary();
        // Should have 10 different operations (one per thread)
        assert_eq!(summary.len(), 10);

        // Each should have 10 samples
        for i in 0..10 {
            let key = format!("thread_{}", i);
            let stats = summary.get(&key).unwrap();
            assert_eq!(stats.count, 10);
        }
    }

    #[test]
    #[serial]
    fn test_timer_drop_records() {
        clear_metrics();

        {
            let _timer = start_timer("drop_test");
            thread::sleep(Duration::from_millis(10));
            // Timer drops here and automatically records
        }

        let summary = get_summary();
        assert!(summary.contains_key("drop_test"));
    }
}
