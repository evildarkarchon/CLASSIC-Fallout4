//! Rolling `Duration` timing metrics (Pure Rust)
//!
//! This module is the sole timing implementation for CLASSIC. Every binding
//! (CXX, Node, and both Python performance views) records into the
//! [`PerformanceMetrics`] collector defined here.
//!
//! # Default store
//!
//! There is one default observable store per linked library image, reached
//! through [`get_global_metrics`] and the seconds-based free functions
//! ([`record_timing`], [`get_summary`], [`clear_metrics`]) and [`Timer`]. All of
//! those entry points read and clear the same timing and byte state. A
//! [`PerformanceMetrics`] value constructed explicitly owns its own state and
//! never observes the default store.
//!
//! # Sample contract
//!
//! A timing sample is canonicalised to whole nanoseconds before it touches any
//! state:
//!
//! - Floating-point inputs must be finite and nonnegative. `-0.0` is treated as
//!   zero. A valid value is rounded exactly once, from its binary value, to the
//!   nearest nanosecond (ties to even), so a millisecond input is never
//!   rounded first to seconds and then again to nanoseconds.
//! - A single sample may not exceed [`MAX_SAMPLE_NANOS`].
//! - Per-operation sample counts, accumulated nanoseconds, and byte totals use
//!   checked arithmetic. A record that would wrap any of them is rejected.
//!
//! A rejected record returns a [`TimingError`] and leaves every counter for
//! every operation unchanged. Python bindings are the `classic_shared` and
//! `classic_perf` modules of the `classic-python-bindings` adapter crate.

use dashmap::DashMap;
use dashmap::mapref::entry::Entry;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fmt;
use std::sync::Arc;
use std::sync::LazyLock;
use std::time::{Duration, Instant};

/// Default metrics store for this linked library image.
static METRICS: LazyLock<Arc<PerformanceMetrics>> =
    LazyLock::new(|| Arc::new(PerformanceMetrics::new()));

/// Global reference instant for timer measurements
static TIMER_START: LazyLock<Instant> = LazyLock::new(Instant::now);

/// Largest single timing sample the collector accepts, in nanoseconds.
///
/// Samples are accumulated as `u64` nanoseconds, so one sample can never be
/// larger than the accumulator itself (roughly 584 years).
pub const MAX_SAMPLE_NANOS: u64 = u64::MAX;

const NANOS_PER_SECOND: u64 = 1_000_000_000;
const NANOS_PER_MILLISECOND: u64 = 1_000_000;

/// Counter that a rejected record would have overflowed.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MetricCounter {
    /// Number of timing samples recorded for an operation.
    SampleCount,
    /// Accumulated duration, in nanoseconds, for an operation.
    TotalDuration,
    /// Accumulated bytes processed by an operation.
    BytesProcessed,
}

impl fmt::Display for MetricCounter {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::SampleCount => "sample count",
            Self::TotalDuration => "total duration",
            Self::BytesProcessed => "bytes processed",
        })
    }
}

/// Reason a timing or byte record was rejected.
///
/// Every variant is raised before any metric state changes. Bindings project
/// all variants as their invalid-argument error (Python `ValueError`, Node
/// `InvalidArg`, CXX `rust::Error`).
#[derive(Clone, Debug, PartialEq, thiserror::Error)]
pub enum TimingError {
    /// The floating-point sample was NaN or infinite.
    #[error("timing sample must be a finite number, got {value}")]
    NonFinite {
        /// Rejected input in its caller-supplied unit.
        value: f64,
    },
    /// The floating-point sample was below zero.
    #[error("timing sample must not be negative, got {value}")]
    Negative {
        /// Rejected input in its caller-supplied unit.
        value: f64,
    },
    /// The sample is larger than [`MAX_SAMPLE_NANOS`] after rounding.
    #[error("timing sample exceeds the maximum of {MAX_SAMPLE_NANOS} nanoseconds")]
    SampleOutOfRange,
    /// Recording would wrap one of the operation's accumulated counters.
    #[error("recording '{operation}' would overflow its accumulated {counter}")]
    CounterOverflow {
        /// Operation whose counter is saturated.
        operation: String,
        /// The counter that would have wrapped.
        counter: MetricCounter,
    },
}

impl TimingError {
    /// Stable lowercase token for this failure.
    ///
    /// Bindings prefix their error message with this token (`"<code>: ..."`)
    /// so callers can branch without parsing prose.
    pub fn code(&self) -> &'static str {
        match self {
            Self::NonFinite { .. } => "timing_sample_not_finite",
            Self::Negative { .. } => "timing_sample_negative",
            Self::SampleOutOfRange => "timing_sample_out_of_range",
            Self::CounterOverflow { .. } => "timing_counter_overflow",
        }
    }

    /// Binding wire format: `"<code>: <message>"`.
    ///
    /// Every adapter (CXX `rust::Error`, Node `InvalidArg`, Python
    /// `ValueError`) uses this exact text so callers can split on the first
    /// `": "` to recover [`TimingError::code`].
    pub fn coded_message(&self) -> String {
        format!("{}: {self}", self.code())
    }
}

/// Convert floating-point seconds to a canonical [`Duration`].
///
/// # Errors
///
/// Returns [`TimingError::NonFinite`], [`TimingError::Negative`], or
/// [`TimingError::SampleOutOfRange`] when `secs` is not an acceptable sample.
pub fn duration_from_secs_f64(secs: f64) -> Result<Duration, TimingError> {
    round_to_nanos(secs, NANOS_PER_SECOND).map(Duration::from_nanos)
}

/// Convert floating-point milliseconds to a canonical [`Duration`].
///
/// The value is scaled and rounded in one exact step, so it is not first
/// rounded to seconds.
///
/// # Errors
///
/// Same as [`duration_from_secs_f64`].
pub fn duration_from_millis_f64(millis: f64) -> Result<Duration, TimingError> {
    round_to_nanos(millis, NANOS_PER_MILLISECOND).map(Duration::from_nanos)
}

/// Convert integral milliseconds to a canonical [`Duration`].
///
/// # Errors
///
/// Returns [`TimingError::SampleOutOfRange`] when the value in nanoseconds
/// would exceed [`MAX_SAMPLE_NANOS`].
pub fn duration_from_millis_u64(millis: u64) -> Result<Duration, TimingError> {
    millis
        .checked_mul(NANOS_PER_MILLISECOND)
        .map(Duration::from_nanos)
        .ok_or(TimingError::SampleOutOfRange)
}

/// Convert signed integral milliseconds to a canonical [`Duration`].
///
/// Accepts the wide signed integers some bindings receive (for example a
/// Python `int`) so the sign and range checks stay in core.
///
/// # Errors
///
/// Returns [`TimingError::Negative`] for values below zero and
/// [`TimingError::SampleOutOfRange`] when the value in nanoseconds would
/// exceed [`MAX_SAMPLE_NANOS`].
pub fn duration_from_millis_i128(millis: i128) -> Result<Duration, TimingError> {
    if millis < 0 {
        return Err(TimingError::Negative {
            value: millis as f64,
        });
    }
    u64::try_from(millis)
        .map_err(|_| TimingError::SampleOutOfRange)
        .and_then(duration_from_millis_u64)
}

/// Round `value * nanos_per_unit` to the nearest integer, ties to even.
///
/// The product is computed exactly from the float's mantissa and exponent so
/// that the only rounding step is the final one. `nanos_per_unit` must be at
/// most 1e9, which keeps `mantissa * nanos_per_unit` below 2^83.
fn round_to_nanos(value: f64, nanos_per_unit: u64) -> Result<u64, TimingError> {
    if !value.is_finite() {
        return Err(TimingError::NonFinite { value });
    }
    // `-0.0 == 0.0`, so negative zero is accepted here as zero.
    if value == 0.0 {
        return Ok(0);
    }
    if value < 0.0 {
        return Err(TimingError::Negative { value });
    }

    // Decompose the positive finite value as `mantissa * 2^exponent`.
    let bits = value.to_bits();
    let biased_exponent = ((bits >> 52) & 0x7ff) as i32;
    let fraction = bits & ((1u64 << 52) - 1);
    let (mantissa, exponent) = if biased_exponent == 0 {
        // Subnormal: no implicit leading bit.
        (fraction, -1074)
    } else {
        (fraction | (1u64 << 52), biased_exponent - 1075)
    };

    let scaled = u128::from(mantissa) * u128::from(nanos_per_unit);
    let nanos = if exponent >= 0 {
        // Any shift past 64 bits already exceeds u64 nanoseconds.
        if exponent > 64 {
            return Err(TimingError::SampleOutOfRange);
        }
        scaled
            .checked_mul(1u128 << exponent)
            .ok_or(TimingError::SampleOutOfRange)?
    } else {
        let shift = exponent.unsigned_abs();
        if shift >= 128 {
            // `scaled < 2^83`, so the quotient is below one half.
            0
        } else {
            let quotient = scaled >> shift;
            let remainder = scaled & ((1u128 << shift) - 1);
            let half = 1u128 << (shift - 1);
            if remainder > half || (remainder == half && quotient & 1 == 1) {
                quotient + 1
            } else {
                quotient
            }
        }
    };

    u64::try_from(nanos).map_err(|_| TimingError::SampleOutOfRange)
}

/// Validate that a `Duration` fits in one accumulated sample.
fn sample_nanos(duration: Duration) -> Result<u64, TimingError> {
    u64::try_from(duration.as_nanos()).map_err(|_| TimingError::SampleOutOfRange)
}

/// Rolling statistics for one operation's timing samples.
///
/// Constant memory per operation: only the count, sum, minimum, and maximum
/// are retained, never the individual samples. Fields are plain integers
/// because every mutation happens under the owning `DashMap` shard lock, which
/// lets a record validate all counters before committing any of them.
#[derive(Clone, Copy, Debug)]
struct RollingStats {
    count: usize,
    sum_nanos: u64,
    min_nanos: u64,
    max_nanos: u64,
}

impl RollingStats {
    /// Statistics for an operation's first sample.
    fn first(nanos: u64) -> Self {
        Self {
            count: 1,
            sum_nanos: nanos,
            min_nanos: nanos,
            max_nanos: nanos,
        }
    }

    /// Statistics after adding `nanos`, or the counter that would wrap.
    fn with_sample(self, nanos: u64) -> Result<Self, MetricCounter> {
        Ok(Self {
            count: self
                .count
                .checked_add(1)
                .ok_or(MetricCounter::SampleCount)?,
            sum_nanos: self
                .sum_nanos
                .checked_add(nanos)
                .ok_or(MetricCounter::TotalDuration)?,
            min_nanos: self.min_nanos.min(nanos),
            max_nanos: self.max_nanos.max(nanos),
        })
    }

    /// Project the rolling statistics into public [`OperationStats`].
    fn to_stats(self, bytes_processed: u64) -> OperationStats {
        // `count` is never zero: an entry exists only after its first sample.
        let average = self.sum_nanos / self.count.max(1) as u64;
        OperationStats {
            count: self.count,
            total: Duration::from_nanos(self.sum_nanos),
            average: Duration::from_nanos(average),
            min: Duration::from_nanos(self.min_nanos),
            max: Duration::from_nanos(self.max_nanos),
            bytes_processed,
        }
    }
}

/// All metric state for one operation name.
///
/// Timing and byte counters share one map entry so a combined timer record is
/// validated and committed under a single lock.
#[derive(Clone, Copy, Debug, Default)]
struct OperationState {
    /// `None` until the first timing sample; byte-only operations are not
    /// reported by [`PerformanceMetrics::get_stats`].
    timing: Option<RollingStats>,
    bytes_processed: u64,
}

impl OperationState {
    /// State after applying an optional timing sample and optional byte count.
    fn with_record(
        self,
        operation: &str,
        nanos: Option<u64>,
        bytes: Option<u64>,
    ) -> Result<Self, TimingError> {
        let overflow = |counter| TimingError::CounterOverflow {
            operation: operation.to_owned(),
            counter,
        };
        let timing = match (self.timing, nanos) {
            (Some(stats), Some(nanos)) => Some(stats.with_sample(nanos).map_err(overflow)?),
            (None, Some(nanos)) => Some(RollingStats::first(nanos)),
            (timing, None) => timing,
        };
        let bytes_processed = match bytes {
            Some(bytes) => self
                .bytes_processed
                .checked_add(bytes)
                .ok_or_else(|| overflow(MetricCounter::BytesProcessed))?,
            None => self.bytes_processed,
        };
        Ok(Self {
            timing,
            bytes_processed,
        })
    }
}

/// Performance metrics storage
///
/// Thread-safe storage for tracking operation timings, counts, and bytes
/// processed. Each operation keeps constant-size rolling statistics.
///
/// The process-wide default store is returned by [`get_global_metrics`];
/// values created with [`PerformanceMetrics::new`] own independent state.
#[derive(Debug, Default)]
pub struct PerformanceMetrics {
    operations: DashMap<String, OperationState>,
}

impl PerformanceMetrics {
    /// Creates a new `PerformanceMetrics` instance with empty metrics.
    pub fn new() -> Self {
        Self {
            operations: DashMap::new(),
        }
    }

    /// Apply a validated record atomically for one operation.
    ///
    /// The candidate state is computed first and stored only if every counter
    /// stays in range, so a rejected record never creates or mutates an entry.
    fn apply(
        &self,
        operation: &str,
        nanos: Option<u64>,
        bytes: Option<u64>,
    ) -> Result<(), TimingError> {
        // `entry` holds the shard write lock until the match arm finishes.
        match self.operations.entry(operation.to_owned()) {
            Entry::Occupied(mut entry) => {
                let next = entry.get().with_record(operation, nanos, bytes)?;
                *entry.get_mut() = next;
            }
            Entry::Vacant(entry) => {
                let next = OperationState::default().with_record(operation, nanos, bytes)?;
                entry.insert(next);
            }
        }
        Ok(())
    }

    /// Record a timing sample for an operation.
    ///
    /// # Errors
    ///
    /// Returns [`TimingError::SampleOutOfRange`] for a sample above
    /// [`MAX_SAMPLE_NANOS`] and [`TimingError::CounterOverflow`] when the
    /// operation's count or total would wrap. State is unchanged on error.
    pub fn record_timing(&self, operation: &str, duration: Duration) -> Result<(), TimingError> {
        let nanos = sample_nanos(duration)?;
        self.apply(operation, Some(nanos), None)
    }

    /// Record a timing sample given in floating-point seconds.
    ///
    /// # Errors
    ///
    /// Any conversion error from [`duration_from_secs_f64`], or the errors of
    /// [`PerformanceMetrics::record_timing`].
    pub fn record_timing_secs(&self, operation: &str, secs: f64) -> Result<(), TimingError> {
        self.record_timing(operation, duration_from_secs_f64(secs)?)
    }

    /// Record a timing sample given in floating-point milliseconds.
    ///
    /// # Errors
    ///
    /// Any conversion error from [`duration_from_millis_f64`], or the errors
    /// of [`PerformanceMetrics::record_timing`].
    pub fn record_timing_millis(&self, operation: &str, millis: f64) -> Result<(), TimingError> {
        self.record_timing(operation, duration_from_millis_f64(millis)?)
    }

    /// Record bytes processed by an operation.
    ///
    /// # Errors
    ///
    /// Returns [`TimingError::CounterOverflow`] when the operation's byte
    /// total would wrap. State is unchanged on error.
    pub fn record_bytes(&self, operation: &str, bytes: u64) -> Result<(), TimingError> {
        self.apply(operation, None, Some(bytes))
    }

    /// Record a timing sample and, optionally, bytes as one atomic update.
    ///
    /// Either both counters change or neither does.
    ///
    /// # Errors
    ///
    /// The union of [`PerformanceMetrics::record_timing`] and
    /// [`PerformanceMetrics::record_bytes`] errors.
    pub fn record_timing_with_bytes(
        &self,
        operation: &str,
        duration: Duration,
        bytes: Option<u64>,
    ) -> Result<(), TimingError> {
        let nanos = sample_nanos(duration)?;
        self.apply(operation, Some(nanos), bytes)
    }

    /// Get statistics for an operation, or `None` if it has no timing samples.
    pub fn get_stats(&self, operation: &str) -> Option<OperationStats> {
        let state = self.operations.get(operation)?;
        state
            .timing
            .map(|timing| timing.to_stats(state.bytes_processed))
    }

    /// Get all operation names with recorded timing samples.
    pub fn get_operations(&self) -> Vec<String> {
        self.operations
            .iter()
            .filter(|entry| entry.timing.is_some())
            .map(|entry| entry.key().clone())
            .collect()
    }

    /// Snapshot statistics for every operation with timing samples.
    pub fn all_stats(&self) -> HashMap<String, OperationStats> {
        self.operations
            .iter()
            .filter_map(|entry| {
                entry
                    .timing
                    .map(|timing| (entry.key().clone(), timing.to_stats(entry.bytes_processed)))
            })
            .collect()
    }

    /// Clear all timing and byte metrics.
    pub fn clear(&self) {
        self.operations.clear();
    }
}

/// Statistics for a single operation type
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OperationStats {
    /// Number of times this operation was executed
    pub count: usize,
    /// Total time spent on this operation
    pub total: Duration,
    /// Average time per operation, truncated to whole nanoseconds
    pub average: Duration,
    /// Minimum time for a single operation
    pub min: Duration,
    /// Maximum time for a single operation
    pub max: Duration,
    /// Total bytes processed by this operation
    pub bytes_processed: u64,
}

impl OperationStats {
    /// Calculate throughput in bytes per second
    pub fn throughput(&self) -> Option<f64> {
        if self.bytes_processed > 0 && !self.total.is_zero() {
            Some(self.bytes_processed as f64 / self.total.as_secs_f64())
        } else {
            None
        }
    }
}

/// Seconds-based summary of one operation in the default store.
///
/// This is the projection used by the `classic_perf` Python module and the
/// CXX `classic::perf` bridge. Values are computed from whole-nanosecond
/// rolling statistics.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
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

impl From<&OperationStats> for MetricsSummary {
    fn from(stats: &OperationStats) -> Self {
        Self {
            count: stats.count,
            total: stats.total.as_secs_f64(),
            average: stats.average.as_secs_f64(),
            min: stats.min.as_secs_f64(),
            max: stats.max.as_secs_f64(),
        }
    }
}

/// Record a timing sample, in seconds, into the default store.
///
/// # Errors
///
/// See [`PerformanceMetrics::record_timing_secs`]. State is unchanged on
/// error.
pub fn record_timing(name: &str, duration_secs: f64) -> Result<(), TimingError> {
    METRICS.record_timing_secs(name, duration_secs)
}

/// Record a timing sample, in milliseconds, into the default store.
///
/// The millisecond value is rounded to nanoseconds in one step rather than
/// being divided into seconds first.
///
/// # Errors
///
/// See [`PerformanceMetrics::record_timing_millis`]. State is unchanged on
/// error.
pub fn record_timing_millis(name: &str, duration_ms: f64) -> Result<(), TimingError> {
    METRICS.record_timing_millis(name, duration_ms)
}

/// Seconds-based summaries for every operation in the default store.
pub fn get_summary() -> HashMap<String, MetricsSummary> {
    METRICS
        .all_stats()
        .iter()
        .map(|(name, stats)| (name.clone(), MetricsSummary::from(stats)))
        .collect()
}

/// Clear all timing and byte state in the default store.
pub fn clear_metrics() {
    METRICS.clear();
}

/// Performance timer for measuring operation duration
///
/// Records into the default store when [`Timer::finish`] is called or, if it
/// never was, when the timer is dropped. A timer records at most once.
#[must_use = "Timer should be stored and finished or dropped to record metrics"]
pub struct Timer {
    /// Operation name; `None` once the timer has recorded.
    operation: Option<String>,
    /// Start time of the operation
    start: Instant,
    /// Optional bytes processed during operation
    bytes: Option<u64>,
}

impl Timer {
    /// Start a new timer for the given operation
    pub fn start(operation: impl Into<String>) -> Self {
        Self {
            operation: Some(operation.into()),
            start: Instant::now(),
            bytes: None,
        }
    }

    /// Set the number of bytes processed during this operation
    pub fn set_bytes(&mut self, bytes: u64) {
        self.bytes = Some(bytes);
    }

    /// Time elapsed since the timer started.
    pub fn elapsed(&self) -> Duration {
        self.start.elapsed()
    }

    /// Stop the timer and record its elapsed time (and bytes, if set).
    ///
    /// # Errors
    ///
    /// Returns [`TimingError`] if the record would overflow the operation's
    /// counters. The timer is consumed either way and never records again.
    pub fn finish(mut self) -> Result<(), TimingError> {
        self.record()
    }

    /// Alias of [`Timer::finish`], kept for existing shared-core callers.
    ///
    /// # Errors
    ///
    /// Same as [`Timer::finish`].
    pub fn stop(self) -> Result<(), TimingError> {
        self.finish()
    }

    /// Record once; later calls (including from `Drop`) are no-ops.
    fn record(&mut self) -> Result<(), TimingError> {
        match self.operation.take() {
            Some(operation) => {
                METRICS.record_timing_with_bytes(&operation, self.start.elapsed(), self.bytes)
            }
            None => Ok(()),
        }
    }
}

impl Drop for Timer {
    fn drop(&mut self) {
        // Drop cannot report failure; an overflowing record is skipped rather
        // than wrapped so existing totals stay valid.
        if let Err(error) = self.record() {
            log::warn!("dropped timer did not record: {error}");
        }
    }
}

/// Create and start a [`Timer`] for `name`.
pub fn start_timer(name: impl Into<String>) -> Timer {
    Timer::start(name)
}

/// Macro for timing a block of code
#[macro_export]
macro_rules! timed {
    ($name:expr, $block:block) => {{
        let _timer = $crate::performance_core::Timer::start($name);
        $block
    }};
}

/// Helper function to time async operations
///
/// A record that would overflow is logged and skipped; the future's output is
/// always returned.
pub async fn time_async<F, T>(operation: impl Into<String>, future: F) -> T
where
    F: std::future::Future<Output = T>,
{
    let operation = operation.into();
    let start = Instant::now();

    let result = future.await;

    if let Err(error) = METRICS.record_timing(&operation, start.elapsed()) {
        log::warn!("async timing was not recorded: {error}");
    }

    result
}

/// Helper function to time sync operations with result
///
/// A record that would overflow is logged and skipped.
pub fn time_operation<F, T>(operation: impl Into<String>, f: F) -> T
where
    F: FnOnce() -> T,
{
    let timer = Timer::start(operation);
    let result = f();
    if let Err(error) = timer.finish() {
        log::warn!("operation timing was not recorded: {error}");
    }
    result
}

/// Helper function to time operations that process bytes
///
/// A record that would overflow is logged and skipped.
pub fn time_with_bytes<F, T>(operation: impl Into<String>, bytes: u64, f: F) -> T
where
    F: FnOnce() -> T,
{
    let mut timer = Timer::start(operation);
    timer.set_bytes(bytes);
    let result = f();
    if let Err(error) = timer.finish() {
        log::warn!("operation timing was not recorded: {error}");
    }
    result
}

/// Get a reference to the default metrics store for this library image.
pub fn get_global_metrics() -> &'static Arc<PerformanceMetrics> {
    &METRICS
}

/// Get the global timer start instant
pub fn get_timer_start() -> Instant {
    *TIMER_START
}

#[cfg(test)]
#[path = "performance_core_tests.rs"]
mod tests;
