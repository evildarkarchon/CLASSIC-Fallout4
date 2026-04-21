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
#[path = "lib_tests.rs"]
mod tests;
