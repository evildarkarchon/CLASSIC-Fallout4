//! Seconds-based timing facade for CLASSIC.
//!
//! This crate no longer owns any timing state. Every item is re-exported from
//! [`classic_shared_core::performance_core`], the sole rolling `Duration`
//! implementation, so recording through this facade, through
//! `classic_shared_core::performance_core::get_global_metrics()`, or through a
//! [`Timer`] reads and clears the same default store for the linked library
//! image.
//!
//! The crate identity is scheduled for retirement once its remaining callers
//! import `classic_shared_core::performance_core` directly.
//!
//! # Sample contract
//!
//! [`record_timing`] accepts finite, nonnegative seconds, treats `-0.0` as
//! zero, and rounds once to the nearest nanosecond. Invalid or overflowing
//! samples return a [`TimingError`] and leave all metrics unchanged.
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
//! timer.finish().expect("a short sample cannot overflow");
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

pub use classic_shared_core::performance_core::{
    MetricCounter, MetricsSummary, Timer, TimingError, clear_metrics, get_summary, record_timing,
    record_timing_millis, start_timer,
};

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
