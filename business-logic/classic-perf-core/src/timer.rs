//! RAII timer for automatic timing measurements.

use crate::metrics::record_timing;
use std::time::Instant;

/// RAII timer that automatically records elapsed time on drop.
///
/// The timer starts when created and records its elapsed time when
/// `finish()` is called or when it's dropped (goes out of scope).
///
/// # Examples
///
/// ```rust
/// use classic_perf_core::start_timer;
/// use std::thread;
/// use std::time::Duration;
///
/// {
///     let timer = start_timer("my_operation");
///     thread::sleep(Duration::from_millis(100));
///     // Timer automatically records when dropped
/// }
///
/// // Or explicitly finish
/// let timer = start_timer("explicit");
/// thread::sleep(Duration::from_millis(50));
/// timer.finish(); // Records immediately
/// ```
pub struct Timer {
    name: String,
    start: Instant,
    finished: bool,
}

impl Timer {
    /// Create a new timer with the given operation name.
    ///
    /// # Arguments
    ///
    /// * `name` - Operation name for metrics tracking
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_perf_core::Timer;
    ///
    /// let timer = Timer::new("database_query");
    /// // ... perform operation ...
    /// timer.finish();
    /// ```
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            start: Instant::now(),
            finished: false,
        }
    }

    /// Finish timing and record the measurement.
    ///
    /// This consumes the timer and records the elapsed time.
    /// If the timer is dropped without calling `finish()`, it will
    /// automatically record on drop.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_perf_core::start_timer;
    /// use std::thread;
    /// use std::time::Duration;
    ///
    /// let timer = start_timer("operation");
    /// thread::sleep(Duration::from_millis(100));
    /// timer.finish(); // Records ~0.1 seconds
    /// ```
    pub fn finish(mut self) {
        if !self.finished {
            let elapsed = self.start.elapsed().as_secs_f64();
            record_timing(&self.name, elapsed);
            self.finished = true;
        }
    }

    /// Get the current elapsed time without finishing the timer.
    ///
    /// # Returns
    ///
    /// Elapsed time in seconds since the timer started.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_perf_core::start_timer;
    /// use std::thread;
    /// use std::time::Duration;
    ///
    /// let timer = start_timer("check_elapsed");
    /// thread::sleep(Duration::from_millis(50));
    /// let elapsed = timer.elapsed();
    /// assert!(elapsed >= 0.05);
    /// timer.finish();
    /// ```
    pub fn elapsed(&self) -> f64 {
        self.start.elapsed().as_secs_f64()
    }
}

impl Drop for Timer {
    /// Automatically record timing if `finish()` wasn't called.
    fn drop(&mut self) {
        if !self.finished {
            let elapsed = self.start.elapsed().as_secs_f64();
            record_timing(&self.name, elapsed);
            self.finished = true;
        }
    }
}

/// Create and start a new timer.
///
/// Convenience function that creates a `Timer` and starts timing immediately.
///
/// # Arguments
///
/// * `name` - Operation name for metrics tracking
///
/// # Returns
///
/// A new `Timer` instance that's already running.
///
/// # Examples
///
/// ```rust
/// use classic_perf_core::start_timer;
/// use std::thread;
/// use std::time::Duration;
///
/// let timer = start_timer("my_operation");
/// thread::sleep(Duration::from_millis(100));
/// timer.finish();
/// ```
pub fn start_timer(name: impl Into<String>) -> Timer {
    Timer::new(name)
}

#[cfg(test)]
#[path = "timer_tests.rs"]
mod tests;
