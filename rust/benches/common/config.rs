//! Criterion configuration with environment-controlled benchmark modes.
//!
//! This module provides a unified way to configure Criterion benchmarks with
//! two modes optimized for different use cases:
//!
//! - **Quick mode** (default): Fast iteration during development
//! - **Thorough mode**: Comprehensive measurement for baseline establishment
//!
//! # Environment Variable
//!
//! Set `BENCH_MODE` to control benchmark behavior:
//!
//! ```bash
//! # Quick mode (default) - fast feedback loop
//! BENCH_MODE=quick cargo bench
//!
//! # Thorough mode - for establishing baselines
//! BENCH_MODE=thorough cargo bench
//! ```
//!
//! # Mode Comparison
//!
//! | Setting           | Quick Mode | Thorough Mode |
//! |-------------------|------------|---------------|
//! | Sample size       | 50         | 200           |
//! | Measurement time  | 3 seconds  | 10 seconds    |
//! | Noise threshold   | 3%         | 1%            |
//! | Warm-up time      | 1 second   | 3 seconds     |
//!
//! # Usage
//!
//! ```ignore
//! use criterion::{criterion_group, criterion_main, Criterion};
//!
//! #[path = "../../benches/common/mod.rs"]
//! mod common;
//! use common::config::configure_criterion;
//!
//! fn my_benchmark(c: &mut Criterion) {
//!     c.bench_function("operation", |b| {
//!         b.iter(|| expensive_operation())
//!     });
//! }
//!
//! criterion_group! {
//!     name = benches;
//!     config = configure_criterion();
//!     targets = my_benchmark
//! }
//! criterion_main!(benches);
//! ```

use criterion::Criterion;
use std::env;
use std::time::Duration;

/// Benchmark mode controlling sample sizes and measurement duration.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BenchMode {
    /// Quick mode for development iteration.
    ///
    /// - 50 samples
    /// - 3 second measurement time
    /// - 3% noise threshold
    /// - 1 second warm-up
    Quick,

    /// Thorough mode for baseline establishment.
    ///
    /// - 200 samples
    /// - 10 second measurement time
    /// - 1% noise threshold
    /// - 3 second warm-up
    Thorough,
}

impl BenchMode {
    /// Reads the benchmark mode from the `BENCH_MODE` environment variable.
    ///
    /// Returns `Quick` mode if:
    /// - Environment variable is not set
    /// - Environment variable value is "quick" (case-insensitive)
    /// - Environment variable has any unrecognized value
    ///
    /// Returns `Thorough` mode if:
    /// - Environment variable value is "thorough" (case-insensitive)
    pub fn from_env() -> Self {
        match env::var("BENCH_MODE") {
            Ok(mode) => match mode.to_lowercase().as_str() {
                "thorough" => BenchMode::Thorough,
                "quick" | _ => BenchMode::Quick,
            },
            Err(_) => BenchMode::Quick,
        }
    }

    /// Returns the sample size for this mode.
    pub fn sample_size(&self) -> usize {
        match self {
            BenchMode::Quick => 50,
            BenchMode::Thorough => 200,
        }
    }

    /// Returns the measurement time for this mode.
    pub fn measurement_time(&self) -> Duration {
        match self {
            BenchMode::Quick => Duration::from_secs(3),
            BenchMode::Thorough => Duration::from_secs(10),
        }
    }

    /// Returns the warm-up time for this mode.
    pub fn warm_up_time(&self) -> Duration {
        match self {
            BenchMode::Quick => Duration::from_secs(1),
            BenchMode::Thorough => Duration::from_secs(3),
        }
    }

    /// Returns the noise threshold for this mode (as a fraction).
    pub fn noise_threshold(&self) -> f64 {
        match self {
            BenchMode::Quick => 0.03,
            BenchMode::Thorough => 0.01,
        }
    }
}

impl std::fmt::Display for BenchMode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            BenchMode::Quick => write!(f, "quick"),
            BenchMode::Thorough => write!(f, "thorough"),
        }
    }
}

/// Configures a Criterion instance based on the `BENCH_MODE` environment variable.
///
/// This function reads the `BENCH_MODE` environment variable and returns a
/// configured Criterion instance with appropriate settings for the selected mode.
///
/// # Returns
///
/// A configured `Criterion` instance ready for use in benchmark groups.
///
/// # Example
///
/// ```ignore
/// criterion_group! {
///     name = benches;
///     config = configure_criterion();
///     targets = my_benchmark
/// }
/// ```
///
/// # Environment
///
/// - `BENCH_MODE=quick` (default): Fast iteration for development
/// - `BENCH_MODE=thorough`: Comprehensive measurement for baselines
pub fn configure_criterion() -> Criterion {
    let mode = BenchMode::from_env();

    eprintln!(
        "[benchmark] Running in {} mode (sample_size={}, measurement_time={:?})",
        mode,
        mode.sample_size(),
        mode.measurement_time()
    );

    Criterion::default()
        .sample_size(mode.sample_size())
        .measurement_time(mode.measurement_time())
        .warm_up_time(mode.warm_up_time())
        .noise_threshold(mode.noise_threshold())
}

/// Returns the current benchmark mode from environment.
///
/// Useful for conditional logic in benchmarks based on mode.
pub fn get_bench_mode() -> BenchMode {
    BenchMode::from_env()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_quick_mode_defaults() {
        let mode = BenchMode::Quick;
        assert_eq!(mode.sample_size(), 50);
        assert_eq!(mode.measurement_time(), Duration::from_secs(3));
        assert_eq!(mode.warm_up_time(), Duration::from_secs(1));
        assert!((mode.noise_threshold() - 0.03).abs() < f64::EPSILON);
    }

    #[test]
    fn test_thorough_mode_values() {
        let mode = BenchMode::Thorough;
        assert_eq!(mode.sample_size(), 200);
        assert_eq!(mode.measurement_time(), Duration::from_secs(10));
        assert_eq!(mode.warm_up_time(), Duration::from_secs(3));
        assert!((mode.noise_threshold() - 0.01).abs() < f64::EPSILON);
    }

    #[test]
    fn test_display() {
        assert_eq!(format!("{}", BenchMode::Quick), "quick");
        assert_eq!(format!("{}", BenchMode::Thorough), "thorough");
    }
}
