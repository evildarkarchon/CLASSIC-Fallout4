//! Metrics storage and summary statistics.

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Global metrics storage.
///
/// Uses `DashMap` for lock-free concurrent access. Each operation name
/// maps to a vector of timing samples (in seconds).
static METRICS: once_cell::sync::Lazy<DashMap<String, Vec<f64>>> =
    once_cell::sync::Lazy::new(DashMap::new);

/// Summary statistics for a single operation.
///
/// All timing values are in seconds as f64.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsSummary {
    /// Number of timing samples recorded
    pub count: usize,

    /// Total time across all samples (seconds)
    pub total: f64,

    /// Average time per sample (seconds)
    pub average: f64,

    /// Minimum sample time (seconds)
    pub min: f64,

    /// Maximum sample time (seconds)
    pub max: f64,
}

impl MetricsSummary {
    /// Create summary statistics from a list of timing samples.
    ///
    /// # Arguments
    ///
    /// * `timings` - Slice of timing values in seconds
    ///
    /// # Panics
    ///
    /// Panics if timings slice is empty.
    fn from_timings(timings: &[f64]) -> Self {
        assert!(
            !timings.is_empty(),
            "Cannot create summary from empty timings"
        );

        let count = timings.len();
        let total: f64 = timings.iter().sum();
        let average = total / count as f64;
        let min = timings.iter().fold(f64::INFINITY, |a, &b| a.min(b));
        let max = timings.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));

        Self {
            count,
            total,
            average,
            min,
            max,
        }
    }
}

/// Record a timing measurement for an operation.
///
/// # Arguments
///
/// * `name` - Operation name/identifier
/// * `duration_secs` - Duration in seconds
///
/// # Examples
///
/// ```rust
/// use classic_perf_core::record_timing;
///
/// record_timing("database_query", 0.123);
/// record_timing("file_load", 0.045);
/// ```
pub fn record_timing(name: &str, duration_secs: f64) {
    METRICS
        .entry(name.to_string())
        .and_modify(|v| v.push(duration_secs))
        .or_insert_with(|| vec![duration_secs]);
}

/// Get summary statistics for all recorded operations.
///
/// Returns a HashMap where keys are operation names and values are
/// their corresponding summary statistics.
///
/// # Returns
///
/// HashMap of operation names to their summary statistics.
///
/// # Examples
///
/// ```rust
/// use classic_perf_core::{record_timing, get_summary};
///
/// record_timing("test_op", 1.0);
/// record_timing("test_op", 2.0);
///
/// let summary = get_summary();
/// if let Some(stats) = summary.get("test_op") {
///     println!("Average: {:.3}s", stats.average);
///     println!("Count: {}", stats.count);
/// }
/// ```
pub fn get_summary() -> HashMap<String, MetricsSummary> {
    let mut result = HashMap::new();

    for entry in METRICS.iter() {
        let name = entry.key().clone();
        let timings = entry.value();

        if !timings.is_empty() {
            result.insert(name, MetricsSummary::from_timings(timings));
        }
    }

    result
}

/// Clear all recorded metrics.
///
/// This is primarily useful for testing to ensure clean state between tests.
///
/// # Examples
///
/// ```rust
/// use classic_perf_core::{record_timing, get_summary, clear_metrics};
///
/// record_timing("test", 1.0);
/// assert!(get_summary().contains_key("test"));
///
/// clear_metrics();
/// assert!(get_summary().is_empty());
/// ```
pub fn clear_metrics() {
    METRICS.clear();
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;

    #[test]
    fn test_metrics_store_uses_std_lazy_lock() {
        assert!(std::any::type_name_of_val(&METRICS).contains("LazyLock"));
    }

    #[test]
    #[serial]
    fn test_record_and_retrieve() {
        clear_metrics();

        record_timing("op1", 1.5);
        record_timing("op1", 2.5);
        record_timing("op2", 3.0);

        let summary = get_summary();
        assert_eq!(summary.len(), 2);
        assert!(summary.contains_key("op1"));
        assert!(summary.contains_key("op2"));
    }

    #[test]
    #[serial]
    fn test_summary_calculation() {
        clear_metrics();

        record_timing("calc_test", 1.0);
        record_timing("calc_test", 2.0);
        record_timing("calc_test", 3.0);
        record_timing("calc_test", 4.0);
        record_timing("calc_test", 5.0);

        let summary = get_summary();
        let stats = summary.get("calc_test").unwrap();

        assert_eq!(stats.count, 5);
        assert_eq!(stats.total, 15.0);
        assert_eq!(stats.average, 3.0);
        assert_eq!(stats.min, 1.0);
        assert_eq!(stats.max, 5.0);
    }

    #[test]
    #[serial]
    fn test_single_sample() {
        clear_metrics();

        record_timing("single", 42.0);

        let summary = get_summary();
        let stats = summary.get("single").unwrap();

        assert_eq!(stats.count, 1);
        assert_eq!(stats.total, 42.0);
        assert_eq!(stats.average, 42.0);
        assert_eq!(stats.min, 42.0);
        assert_eq!(stats.max, 42.0);
    }

    #[test]
    #[serial]
    fn test_clear() {
        clear_metrics();

        record_timing("clear1", 1.0);
        record_timing("clear2", 2.0);
        assert_eq!(get_summary().len(), 2);

        clear_metrics();
        assert_eq!(get_summary().len(), 0);
    }

    #[test]
    #[serial]
    fn test_concurrent_access() {
        use std::thread;

        clear_metrics();

        let handles: Vec<_> = (0..100)
            .map(|i| {
                thread::spawn(move || {
                    record_timing("concurrent", i as f64);
                })
            })
            .collect();

        for handle in handles {
            handle.join().unwrap();
        }

        let summary = get_summary();
        let stats = summary.get("concurrent").unwrap();
        assert_eq!(stats.count, 100);
    }
}
