//! ```rust
//! # Performance Monitoring and Metrics Collection
//!
//! //

use dashmap::DashMap;
use once_cell::sync::Lazy;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

/// Global performance metrics collector
static METRICS: Lazy<Arc<PerformanceMetrics>> = Lazy::new(|| Arc::new(PerformanceMetrics::new()));

/// ```rust
/// A structure for collecting and aggregating performance metrics.
///
/// The `PerformanceMetrics` struct is designed to track various performance-related data
/// for operations. It facilitates the collection of timing data, operation execution counts,
/// and the amount of data processed by named operations. The metrics are stored using
/// concurrent data structures to allow safe usage in multi-threaded environments.
/// pub
pub struct PerformanceMetrics {
    /// Operation timings: name -> list of durations
    timings: DashMap<String, Vec<Duration>>,
    /// Operation counts
    counts: DashMap<String, AtomicUsize>,
    /// Total bytes processed by operation
    bytes_processed: DashMap<String, AtomicU64>,
}

impl PerformanceMetrics {
    /// ```rust
    /// Creates a new instance of the struct with the internal fields initialized.
    ///
    /// # Returns
    /// A new instance of the struct with empty `DashMap`s for `timings`, `counts`, and `bytes_processed`.
    ///
    /// # Example
    /// ```rust
    /// let instance = YourStruct::new();
    /// // The instance is now ready to use with empty DashMaps for tracking timings, counts, and bytes processed.
    /// ```
    ///
    /// This method is typically used to initialize the struct before performing any operations.
    /// ```
    pub fn new() -> Self {
        Self {
            timings: DashMap::new(),
            counts: DashMap::new(),
            bytes_processed: DashMap::new(),
        }
    }
    
    /// ```
    /// Records the execution time of an operation and tracks the number of times it has occurred.
    ///
    /// # Parameters
    /// - `operation`: A string slice that identifies the name of the operation being recorded.
    /// - `duration`: A `Duration` instance representing the time taken to complete the operation.
    ///
    /// # Behavior
    /// - Adds the provided `duration` to a vector associated with the `operation` in the `timings` map.
    ///   If the operation does not already exist in the map, it initializes a new vector.
    /// - Increments the count of executions for the `operation` in the `counts` map. If the operation
    ///   does not exist in the map, it initializes the count to zero before incrementing.
    ///
    /// # Thread Safety
    /// - The method relies on atomic operations (`fetch_add`) to ensure that updates to the
    ///   execution counts are thread-safe. However, the `timings` map is not inherently thread-safe,
    ///   so this method should only be used in a context where access to the `self` instance
    ///   is externally synchronized or where `self` uses appropriate synchronization primitives.
    /// ```
    /// # Usage
    /// ```rust
    /// use std::time::Duration;
    /// use std::sync::Arc;
    /// use std::sync::atomic::AtomicUsize;
    /// use std::collections::HashMap;
    ///
    /// // Example of setting up the necessary structure (pseudo-code):
    /// struct Recorder {
    ///     timings: HashMap<String, Vec<Duration>>,
    ///     counts: HashMap<String, AtomicUsize>,
    /// }
    ///
    /// impl Recorder {
    ///     pub fn record_timing(&self, operation: &str, duration: Duration) {
    ///         self.timings
    ///             .entry(operation.to_string())
    ///             .or_insert_with(Vec::new)
    ///             .push(duration);
    ///
    ///         self.counts
    ///             .entry(operation.to_string())
    ///             .or_insert_with(|| AtomicUsize::new(0))
    ///             .fetch_add(1, Ordering::Relaxed);
    ///     }
    /// }
    ///
    /// let recorder = Recorder {
    ///     timings: HashMap::new(),
    ///     counts: HashMap::new(),
    /// };
    ///
    /// // Example usage:
    /// recorder.record_timing("db_query", Duration::from_secs(2));
    /// ```
    pub fn record_timing(&self, operation: &str, duration: Duration) {
        self.timings
            .entry(operation.to_string())
            .or_insert_with(Vec::new)
            .push(duration);

        self.counts
            .entry(operation.to_string())
            .or_insert_with(|| AtomicUsize::new(0))
            .fetch_add(1, Ordering::Relaxed);
    }

    /// ```rust
    /// Records the number of bytes processed for a specific operation.
    ///
    /// This function updates a shared map (`bytes_processed`) that tracks the total
    /// number of bytes processed for different operations. It increments the count
    /// of bytes associated with the provided `operation` by the given `bytes` value.
    ///
    /// If the operation does not already exist in the map, it is initialized with
    /// an atomic counter set to 0 before the provided `bytes` value is added.
    ///
    /// # Parameters
    /// - `operation`: A string slice that specifies the name of the operation to track.
    /// - `bytes`: The number of bytes to add to the tracked value for the given operation.
    ///
    /// # Notes
    /// - The method uses an `AtomicU64` for each operation to ensure thread-safe updates.
    /// - The updates use `Ordering::Relaxed` as the memory ordering, which is suitable
    ///   when only atomic operations on the value are performed, and there are no
    ///   synchronization dependencies.
    ///```
    /// # Example
    /// ```
    /// use std::sync::Arc;
    /// use std::collections::HashMap;
    /// use std::sync::atomic::AtomicU64;
    ///
    /// // Assuming this method is part of a larger structure:
    /// struct OperationTracker {
    ///     bytes_processed: std::sync::Mutex<HashMap<String, AtomicU64>>,
    /// }
    ///
    /// impl OperationTracker {
    ///     pub fn new() -> Self {
    ///         Self {
    ///             bytes_processed: std::sync::Mutex::new(HashMap::new()),
    ///         }
    ///     }
    ///
    ///     pub fn record_bytes(&self, operation: &str, bytes: u64) {
    ///         let mut bytes_processed = self.bytes_processed.lock().unwrap();
    ///         bytes_processed
    ///             .entry(operation.to_string())
    ///             .or_insert_with(|| AtomicU64::new(0))
    ///             .fetch_add(bytes, Ordering::Relaxed);
    ///     }
    /// }
    ///
    /// let tracker = Arc::new(OperationTracker::new());
    /// tracker.record_bytes("read", 1024);
    /// tracker.record_bytes("write", 2048);
    /// ```
    pub fn record_bytes(&self, operation: &str, bytes: u64) {
        self.bytes_processed
            .entry(operation.to_string())
            .or_insert_with(|| AtomicU64::new(0))
            .fetch_add(bytes, Ordering::Relaxed);
    }

    /// ```rust
    /// Retrieves statistics for a specific operation, such as total, average, minimum, 
    /// and maximum durations of the operation execution, as well as the total number 
    /// of executions and bytes processed.
    ///```
    /// # Arguments
    ///
    /// * `operation` - A string slice that specifies the name of the operation for
    ///   which statistics are being retrieved.
    ///
    /// # Returns
    ///
    /// Returns an `Option<OperationStats>`:
    /// - `Some(OperationStats)` if statistics are available for the specified operation,
    ///   containing the count of executions, total execution duration, average execution duration,
    ///   minimum execution duration, maximum execution duration, and bytes processed.
    /// - `None` if no data is available for the specified operation.
    ///
    /// # Details
    ///
    /// - The method first retrieves the timing data (`timings`) for the provided operation.
    ///   If no such data exists, it immediately returns `None`.
    /// - It then retrieves the count of executions for the operation, performed with relaxed 
    ///   atomic ordering.
    /// - It also retrieves the total number of bytes processed during execution of the operation.
    ///   If no bytes have been recorded, it defaults to `0`.
    /// - If the `timings` data is empty, the method returns `None`.
    /// - The total, average, minimum, and maximum durations are subsequently calculated 
    ///   from the `timings` array.
    ///
    /// # Return Example
    ///
    /// If data is present for the operation, the output `OperationStats` will contain:
    /// - `count`: The number of times the operation has been executed.
    /// - `total`: The total duration of the operation executions.
    /// - `average`: The average duration of the operation.
    /// - `min`: The shortest recorded duration of the operation.
    /// - `max`: The longest recorded duration of the operation.
    /// - `bytes_processed`: Total number of bytes processed during the operation.
    ///
    /// If no data exists for the operation, `None` is returned.
    ///
    /// # Panics
    ///
    /// This method does not panic, but care should be taken when interpreting the optional results.
    ///
    /// # Example
    ///
    /// ```rust
    /// let stats = stats_collector.get_stats("read_operation");
    /// if let Some(stats) = stats {
    ///     println!("Operation executed {} times with an average duration of {:?}ms.",
    ///              stats.count, stats.average.as_millis());
    /// } else {
    ///     println!("No stats available for the operation.");
    /// }
    /// ```
    pub fn get_stats(&self, operation: &str) -> Option<OperationStats> {
        let timings = self.timings.get(operation)?;
        let count = self.counts.get(operation)?.load(Ordering::Relaxed);
        let bytes = self
            .bytes_processed
            .get(operation)
            .map(|b| b.load(Ordering::Relaxed))
            .unwrap_or(0);

        if timings.is_empty() {
            return None;
        }

        let total: Duration = timings.iter().sum();
        let avg = total / count as u32;
        let min = *timings.iter().min()?;
        let max = *timings.iter().max()?;

        Some(OperationStats {
            count,
            total,
            average: avg,
            min,
            max,
            bytes_processed: bytes,
        })
    }

    /// ```
    /// Clears all recorded data within the instance.
    ///
    /// This function resets the internal collections `timings`, `counts`, and
    /// `bytes_processed` by removing all their elements. After calling this method, 
    /// the instance will be in its initial state, as though no data had been added.
    /// ```
    /// # Example
    ///
    /// ```rust
    /// let mut stats = Stats::new();
    /// stats.record_timing(100);
    /// stats.record_count(5);
    /// stats.record_bytes(1024);
    ///
    /// stats.clear();
    ///
    /// assert!(stats.timings.is_empty());
    /// assert!(stats.counts.is_empty());
    /// assert!(stats.bytes_processed.is_empty());
    /// ```
    pub fn clear(&self) {
        self.timings.clear();
        self.counts.clear();
        self.bytes_processed.clear();
    }
}

/// ```
/// A structure representing statistics of an operation, typically used to measure performance
/// or throughput over a period of time.
///
/// # Fields
/// - `count`:
///     The total number of operations performed.
/// - `total`:
///     The cumulative duration of all the operations combined.
/// - `average`:
///     The average duration per operation. Typically calculated as `total / count`.
/// - `min`:
///     The shortest duration recorded for a single operation.
/// - `max`:
///     The longest duration recorded for a single operation.
/// - `bytes_processed`:
///     The total number of bytes processed across all operations.
///
/// This structure can be cloned and debugged, making it suitable for use in performance
/// logging, profiling, or benchmarking scenarios.
/// ```
#[derive(Clone, Debug)]
pub struct OperationStats {
    pub count: usize,
    pub total: Duration,
    pub average: Duration,
    pub min: Duration,
    pub max: Duration,
    pub bytes_processed: u64,
}

/// ```rust
/// A structure to measure the duration of an operation, optionally tracking the number of bytes processed.
///
/// The `Timer` struct is designed to record the time taken for an operation to complete and can include
/// additional contextual information such as the number of bytes involved.
/// ```
/// # Fields
///
/// - `operation`:
///   An optional `String` representing the name or description of the operation being timed. 
///   If `None`, no specific operation name is tracked.
///
/// - `start`:
///   An `Instant` instance marking the start time of the operation. This is used for measuring
///   the elapsed duration of the operation.
///
/// - `bytes`:
///   An optional `u64` value representing the number of bytes associated with the operation 
///   (e.g., bytes processed, downloaded, or transferred). Defaults to `None` if not specified.
///
/// # Examples
///
/// ```rust
/// use std::time::Instant;
/// use your_crate::Timer;
///
/// let timer = Timer {
///     operation: Some(String::from("Download")),
///     start: Instant::now(),
///     bytes: Some(1024),
/// };
///
/// // Perform some operation...
///
/// println!("Operation: {:?}", timer.operation);
/// println!("Bytes processed: {:?}", timer.bytes);
/// ```
pub struct Timer {
    operation: Option<String>,
    start: Instant,
    bytes: Option<u64>,
}

impl Timer {
    /// Start a new timer
    pub fn start(operation: impl Into<String>) -> Self {
        Self {
            operation: Some(operation.into()),
            start: Instant::now(),
            bytes: None,
        }
    }

    /// ```
    /// Sets the `bytes` field of the instance to the provided value.
    /// ```
    /// # Parameters
    /// - `bytes` (`u64`): The value to set for the `bytes` field.
    ///
    /// # Behavior
    /// This method assigns the given `bytes` value to the `bytes` field of the
    /// instance, encapsulating it in a `Some` variant of the `Option<u64>` type.
    ///
    /// # Examples
    /// ```
    /// let mut instance = YourStruct::new();
    /// instance.set_bytes(1024);
    /// assert_eq!(instance.bytes, Some(1024));
    /// ```
    pub fn set_bytes(&mut self, bytes: u64) {
        self.bytes = Some(bytes);
    }


    /// ```
    /// Stops the ongoing operation, records its duration, and optionally records the associated byte count.
    ///
    /// The function takes ownership of the `self` object, which is expected to have an ongoing operation.
    /// It performs the following steps:
    /// - Checks if there is a current operation (`self.operation`) and takes ownership of it, leaving `None` in its place.
    /// - If an operation exists:
    ///   - Calculates the elapsed time since the operation started (`self.start.elapsed()`).
    ///   - Records the timing metric for the operation using `METRICS.record_timing`.
    ///   - If the `self.bytes` field has a value, it also records the byte metric for the operation using `METRICS.record_bytes`.
    ///```
    /// # Parameters
    /// - `self`: The structure instance containing the operation state. It is consumed by this method.
    ///
    /// # Behavior
    /// - If `self.operation` is `None`, no operation metrics are recorded, and the method does nothing.
    /// - If `self.bytes` is `Some`, the byte count associated with the operation is recorded; otherwise, only the timing is recorded.
    ///
    /// # Example
    /// ```
    /// let handler = OperationHandler::new();
    /// // Start and perform some operations...
    /// handler.stop();  // Stops the operation and logs metrics.
    /// ```
    ///
    /// # Notes
    /// - This is a consuming method, meaning the `self` instance can no longer be used after calling `stop`.
    /// - Ensure that `operation`, if any, is collected and processed before calling this method.
    /// ```
    pub fn stop(mut self) {
        if let Some(operation) = self.operation.take() {
            let duration = self.start.elapsed();
            METRICS.record_timing(&operation, duration);

            if let Some(bytes) = self.bytes {
                METRICS.record_bytes(&operation, bytes);
            }
        }
    }
}

impl Drop for Timer {
    /// ```rust
    /// The `drop` method is called when the object is dropped, automatically executing
    /// cleanup logic and recording metrics if required.
    ///
    /// This method performs the following actions:
    /// 1. Checks if the `operation` field of the instance is set (`Some` value).
    ///    - If set, it records the elapsed duration since the operation started using the `METRICS.record_timing` method.
    /// 2. If the `bytes` field is also set (`Some` value), it records the number of bytes associated 
    ///    with the operation using `METRICS.record_bytes`.
    ///
    /// This ensures that metrics like execution duration and any associated byte counts
    /// are logged before the object is deallocated or goes out of scope.
    ///```
    /// ### Notes
    /// - This method relies on the `self.operation` and `self.bytes` fields being `Option` types.
    /// - The `METRICS` system is assumed to handle recording and persistence of timing
    ///   and byte-related metrics.
    ///
    /// ### Safety
    /// - Ensure `self.start.elapsed()` does not panic and can handle edge cases like time overflow.
    ///
    /// ### Example
    /// Automatically recording metrics when the object goes out of scope:
    /// ```rust
    /// {
    ///     let mut operation_tracker = OperationTracker::new("example_operation");
    ///     // Perform some work here
    ///     operation_tracker.add_bytes(1024);
    ///     // On exiting the scope, `drop` will be called automatically.
    /// }
    /// ```
    fn drop(&mut self) {
        // Auto-stop if not explicitly stopped
        if let Some(ref operation) = self.operation {
            let duration = self.start.elapsed();
            METRICS.record_timing(operation, duration);

            if let Some(bytes) = self.bytes {
                METRICS.record_bytes(operation, bytes);
            }
        }
    }
}

/// ```rust
/// The `timed!` macro is used to measure and log the execution duration of a given block of code.
///
/// # Parameters
/// - `$name`: An expression of type `&str` that acts as a name or label for the timed block.
/// - `$block`: A block of code `{}` whose execution time will be measured.
///
/// # Usage
/// The macro wraps the provided code block in a timer, ensuring the start and end time of the block's
/// execution is recorded. It uses the `Timer::start` function from `$crate::utils::performance`
/// to begin timing, and the elapsed time will be automatically handled once the block finishes execution.
///
/// The macro does not return the elapsed time directly but may log it or use it internally, depending
/// on the `Timer` implementation.
///
/// # Example
/// ```rust
/// use my_crate::timed;
///
/// fn main() {
///     timed!("example_block", {
///         // Code to be measured
///         for i in 0..1000 {
///             println!("{}", i);
///         }
///     });
/// }
/// ```
///
/// In this example, the `timed!` macro will measure how long the `for` loop takes to execute
/// and may log or handle the elapsed time accordingly.
///
/// # Notes
/// - This macro requires the existence of a `Timer` struct or implementation in `$crate::utils::performance`.
/// - Ensure that the `$name` string provided uniquely identifies the block for easier debugging or tracking.
///
/// # Macro Expansion
/// The macro expands into:
/// ```rust
/// let _timer = $crate::utils::performance::Timer::start($name);
/// $block
/// ```
/// This ensures the timer begins before the block executes and the block is timed properly.
/// ```
#[macro_export]
macro_rules! timed {
    ($name:expr, $block:block) => {{
        let _timer = $crate::utils::performance::Timer::start($name);
        $block
    }};
}

/// Python-exposed performance monitor
#[pyclass]
pub struct RustPerformanceMonitor;

#[pymethods]
impl RustPerformanceMonitor {
    #[new]
    pub fn new() -> Self {
        Self
    }

    /// ```rust
    /// Start a timer for a given operation and return a Python dictionary containing the operation name 
    /// and the start time.
    ///
    /// This method creates a timer for the specified `operation` by initializing a Python dictionary 
    /// with the operation name and the elapsed time since an arbitrary system start point in seconds. 
    /// The elapsed time is recorded as a floating-point number in seconds to provide high-resolution timing.
    /// ```
    /// # Parameters:
    /// - `py`: A reference to the Python interpreter, allowing interaction with Python objects.
    /// - `operation`: A `String` representing the name or description of the operation to be timed.
    ///
    /// # Returns:
    /// - `PyResult<Py<PyAny>>`: Returns a Python dictionary containing:
    ///   - `"operation"`: The name of the operation (string).
    ///   - `"start"`: The elapsed time in seconds as a floating-point number.
    ///
    /// # Errors:
    /// This function returns an error if the Python dictionary cannot be created or updated with 
    /// the specified keys and values.
    ///
    /// # Example:
    /// ```python
    /// # Assuming `start_timer` is bound to a Python object in the Rust binding:
    /// timer = some_object.start_timer("example_operation")
    /// print(timer)  # Example output: {'operation': 'example_operation', 'start': 0.234567}
    /// ```
    ///
    /// # Notes:
    /// - The `start` key in the dictionary is derived from `Instant::now().elapsed().as_secs_f64()`, 
    ///   which may not reflect absolute system time but is suitable for measuring relative durations.
    /// ```
    #[pyo3(signature = (operation))]
    pub fn start_timer(&self, py: Python, operation: String) -> PyResult<Py<PyAny>> {
        let timer_dict = PyDict::new(py);
        timer_dict.set_item("operation", operation.clone())?;
        timer_dict.set_item("start", Instant::now().elapsed().as_secs_f64())?;

        Ok(timer_dict.unbind().into())
    }

    /// ```rust
    /// Stops a timer for a specified operation and records metrics associated with its duration and optional data processed.
    ///
    /// This method is designed to be called from Python code and works with Python dictionary objects (`PyDict`) to obtain necessary timer information. 
    /// It records the duration of the operation and optionally updates metrics for the number of bytes processed, if provided.
    ///```
    /// # Arguments
    ///
    /// * `timer_info` - A reference to a Python dictionary (`&Bound<'_, PyDict>`) containing the timer-related information:
    ///     - `"operation"`: A string identifying the operation being timed. This key is required.
    ///     - `"start"`: A floating-point value representing the start time of the timer, in seconds since the epoch. This key is required.
    /// * `bytes_processed` - An optional `u64` value indicating the number of bytes processed during the operation. If provided, this value will be recorded.
    ///
    /// # Returns
    ///
    /// * `PyResult<()>` - Returns `Ok(())` if the operation completes successfully, or an error (`PyErr`) if a required key is missing or if any other issue arises.
    ///
    /// # Errors
    ///
    /// The function will return an error in the following cases:
    /// * If the `"operation"` key is missing in `timer_info`, a `PyKeyError` will be raised.
    /// * If the `"start"` key is missing in `timer_info`, a `PyKeyError` will be raised.
    ///
    /// # Panics
    ///
    /// This function will not panic under normal circumstances; errors are propagated as `PyResult` values.
    ///
    /// # Examples
    ///
    /// ```python
    /// # Example usage in Python:
    ///
    /// timer_info = {"operation": "data_processing", "start": 1697483943.15}
    /// bytes_processed = 1024
    /// my_module.stop_timer(timer_info, bytes_processed=bytes_processed)
    /// ```
    ///
    /// This would record the timing for the `"data_processing"` operation and track the 1024 bytes processed.
    #[pyo3(signature = (timer_info, bytes_processed=None))]
    pub fn stop_timer(
        &self,
        timer_info: &Bound<'_, PyDict>,
        bytes_processed: Option<u64>,
    ) -> PyResult<()> {
        let operation: String = timer_info
            .get_item("operation")?
            .ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing 'operation' key")
            })?
            .extract()?;

        let start: f64 = timer_info
            .get_item("start")?
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing 'start' key"))?
            .extract()?;

        let duration = Duration::from_secs_f64(Instant::now().elapsed().as_secs_f64() - start);

        METRICS.record_timing(&operation, duration);

        if let Some(bytes) = bytes_processed {
            METRICS.record_bytes(&operation, bytes);
        }

        Ok(())
    }

    /// ```
    /// Retrieves all statistics for tracked operations and returns them as a Python dictionary.
    ///
    /// This method collects metrics data from the global `METRICS` object
    /// and organizes it as a dictionary of dictionaries accessible in Python.
    /// Each key in the outer dictionary corresponds to an operation name, and its value
    /// is another dictionary containing various statistics about the operation.
    /// ```
    /// ### Statistics Included
    /// For each tracked operation, the following metrics are included:
    /// - **count**: Total number of times the operation was executed.
    /// - **total_ms**: Total execution time of the operation in milliseconds.
    /// - **avg_ms**: Average execution time of the operation in milliseconds.
    /// - **min_ms**: Minimum execution time of the operation in milliseconds.
    /// - **max_ms**: Maximum execution time of the operation in milliseconds.
    /// - **bytes_processed**: Total number of bytes processed during the operation (if applicable).
    /// - **throughput_bytes_per_sec**: Throughput in bytes per second, calculated if `bytes_processed` > 0 and `total_ms` > 0.
    ///
    /// ### Parameters
    /// - `py`: A `Python` token representing the Python interpreter, required for constructing Python objects within Rust.
    ///
    /// ### Returns
    /// - `PyResult<Py<PyDict>>`: A Python dictionary where keys are operation names (strings),
    ///   and values are dictionaries containing the corresponding statistics for each operation.
    ///
    /// ### Errors
    /// Returns a Python exception if there is a failure while setting up the dictionary or accessing the `METRICS` object.
    ///
    /// ### Example
    /// ```python
    /// # Assuming this function is called in Python:
    /// stats = my_rust_extension.get_all_stats()
    /// for operation, metrics in stats.items():
    ///     print(f"Operation: {operation}")
    ///     print(f"  Count: {metrics['count']}")
    ///     print(f"  Total Time (ms): {metrics['total_ms']}")
    ///     print(f"  Average Time (ms): {metrics['avg_ms']}")
    ///     print(f"  Min Time (ms): {metrics['min_ms']}")
    ///     print(f"  Max Time (ms): {metrics['max_ms']}")
    ///     print(f"  Bytes Processed: {metrics['bytes_processed']}")
    ///     if 'throughput_bytes_per_sec' in metrics:
    ///         print(f"  Throughput (bytes/sec): {metrics['throughput_bytes_per_sec']}")
    /// ```
    pub fn get_all_stats(&self, py: Python) -> PyResult<Py<PyDict>> {
        let stats_dict = PyDict::new(py);

        for entry in METRICS.timings.iter() {
            let operation = entry.key();
            if let Some(stats) = METRICS.get_stats(operation) {
                let op_dict = PyDict::new(py);
                op_dict.set_item("count", stats.count)?;
                op_dict.set_item("total_ms", stats.total.as_millis() as u64)?;
                op_dict.set_item("avg_ms", stats.average.as_millis() as u64)?;
                op_dict.set_item("min_ms", stats.min.as_millis() as u64)?;
                op_dict.set_item("max_ms", stats.max.as_millis() as u64)?;
                op_dict.set_item("bytes_processed", stats.bytes_processed)?;

                // Calculate throughput if bytes were processed
                if stats.bytes_processed > 0 && stats.total.as_secs() > 0 {
                    let throughput = stats.bytes_processed as f64 / stats.total.as_secs_f64();
                    op_dict.set_item("throughput_bytes_per_sec", throughput)?;
                }

                stats_dict.set_item(operation.clone(), op_dict)?;
            }
        }

        Ok(stats_dict.unbind())
    }

    /// ```rust
    /// Retrieves statistics for a specific operation and returns them as a Python dictionary.
    ///
    /// This function fetches metrics (such as execution count, total time, average time,
    /// minimum time, maximum time, and bytes processed) for a given `operation` from
    /// the `METRICS` global store. These metrics are then converted into a Python
    /// dictionary (`PyDict`) and returned to the caller. If metrics are unavailable
    /// for the specified operation, `None` is returned.
    /// ```
    /// # Parameters
    /// - `self`: Reference to the current instance of the containing object.
    /// - `py`: The Python interpreter instance, required for constructing the Python objects.
    /// - `operation`: A string representing the name of the operation whose metrics are being retrieved.
    ///
    /// # Returns
    /// - `PyResult<Option<Py<PyDict>>>`: On success, this returns:
    ///   - `Some(Py<PyDict>)`: A Python dictionary containing the following keys:
    ///       - `"count"`: Number of times the operation was executed.
    ///       - `"total_ms"`: Total execution time in milliseconds.
    ///       - `"avg_ms"`: Average execution time in milliseconds.
    ///       - `"min_ms"`: Minimum execution time in milliseconds.
    ///       - `"max_ms"`: Maximum execution time in milliseconds.
    ///       - `"bytes_processed"`: Total bytes processed during the operation.
    ///       - `"throughput_bytes_per_sec"` (optional): Calculated throughput in bytes per second
    ///         if `bytes_processed` is greater than `0` and total duration is greater than `0` seconds.
    ///   - `None`: Indicates that no metrics are available for the specified operation.
    ///
    /// # Errors
    /// - Returns a `PyErr` if there is an error setting any key-value pair in the Python dictionary.
    ///
    /// # Example
    /// ```rust
    /// let operation_name = "example_operation";
    /// match my_object.get_operation_stats(py, operation_name.to_string()) {
    ///     Ok(Some(stats_dict)) => {
    ///         println!("Operation stats: {:?}", stats_dict);
    ///     }
    ///     Ok(None) => {
    ///         println!("No metrics available for the operation '{}'", operation_name);
    ///     }
    ///     Err(err) => {
    ///         eprintln!("Failed to fetch operation stats: {}", err);
    ///     }
    /// }
    /// ```
    ///
    /// # Notes
    /// - This function assumes that `METRICS.get_stats(&operation)` provides an `Option<Stats>`
    ///   where `Stats` is a structure containing details like `count`, `total`, `average`, `min`,
    ///   `max`, and `bytes_processed`.
    /// - The time-related metrics (`total`, `average`, `min`, `max`) are expected to be returned
    ///   as `Duration` types, and they are converted to milliseconds in the resulting dictionary.
    /// ```
    pub fn get_operation_stats(
        &self,
        py: Python,
        operation: String,
    ) -> PyResult<Option<Py<PyDict>>> {
        match METRICS.get_stats(&operation) {
            Some(stats) => {
                let op_dict = PyDict::new(py);
                op_dict.set_item("count", stats.count)?;
                op_dict.set_item("total_ms", stats.total.as_millis() as u64)?;
                op_dict.set_item("avg_ms", stats.average.as_millis() as u64)?;
                op_dict.set_item("min_ms", stats.min.as_millis() as u64)?;
                op_dict.set_item("max_ms", stats.max.as_millis() as u64)?;
                op_dict.set_item("bytes_processed", stats.bytes_processed)?;

                if stats.bytes_processed > 0 && stats.total.as_secs() > 0 {
                    let throughput = stats.bytes_processed as f64 / stats.total.as_secs_f64();
                    op_dict.set_item("throughput_bytes_per_sec", throughput)?;
                }

                Ok(Some(op_dict.unbind()))
            }
            None => Ok(None),
        }
    }

    /// Clear all performance metrics
    pub fn clear_metrics(&self) {
        METRICS.clear();
    }

    /// ```rust
    /// Records a custom metric for a specific operation, including its duration and, optionally,
    /// the number of bytes processed during the operation.
    ///```
    /// # Arguments
    /// - `operation` (`String`): The name of the operation for which the metric is being recorded.
    /// - `duration_ms` (`u64`): The duration of the operation in milliseconds.
    /// - `bytes_processed` (`Option<u64>`): An optional parameter representing the number of bytes processed
    ///   during the operation. If provided, it will be recorded alongside the operation metric.
    ///
    /// # Behavior
    /// - The function records the timing data for the operation by converting the provided `duration_ms`
    ///   into a `Duration` and passing it to the `METRICS.record_timing` method.
    /// - If the `bytes_processed` argument is provided (i.e., is `Some`), the number of bytes is logged
    ///   using the `METRICS.record_bytes` method.
    ///
    /// # Examples
    /// ```rust
    /// use your_module::YourStruct;
    ///
    /// let instance = YourStruct::new();
    ///
    /// // Record a metric for an operation with a duration of 1500 milliseconds (1.5 seconds)
    /// instance.record_metric("file_download".to_string(), 1500, None);
    ///
    /// // Record a metric for an operation with a duration of 500 milliseconds
    /// // and 200 bytes processed
    /// instance.record_metric("data_upload".to_string(), 500, Some(200));
    /// ```
    #[pyo3(signature = (operation, duration_ms, bytes_processed=None))]
    pub fn record_metric(&self, operation: String, duration_ms: u64, bytes_processed: Option<u64>) {
        let duration = Duration::from_millis(duration_ms);
        METRICS.record_timing(&operation, duration);

        if let Some(bytes) = bytes_processed {
            METRICS.record_bytes(&operation, bytes);
        }
    }
}

/// ```
/// Times the execution duration of an asynchronous operation and records the timing for metrics.
///
/// This function takes an operation name and a `Future`, measures how long it takes to `.await` the future,
/// and logs the duration to a metrics system. It then returns the result of the future.
///```
/// # Type Parameters
/// - `F`: The type of the asynchronous operation, which implements the `Future` trait.
/// - `T`: The output type of the future being awaited.
///
/// # Arguments
/// - `operation`: A string-like type representing the name or description of the operation being measured.
///   This is used to label the recorded timing in the metrics system.
/// - `future`: The asynchronous operation (i.e., a `Future`) to be executed.
///
/// # Returns
/// This function returns the result of the asynchronous operation of type `T`.
///
/// # Metrics
/// The function records the elapsed time of the operation using the global `METRICS` system.
/// The timing is associated with the provided `operation` string.
///
/// # Example
/// ```rust
/// use std::time::Duration;
/// use tokio::time::sleep;
///
/// #[tokio::main]
/// async fn main() {
///     // Simulate an async task
///     let result = time_async("example_task", async {
///         sleep(Duration::from_secs(2)).await;
///         42 // Example result
///     }).await;
///
///     println!("Result: {}", result); // Output: Result: 42
/// }
/// ```
///
/// # Notes
/// - The `METRICS` object must have a function `record_timing` that accepts the operation name and a duration.
/// - Ensure that the operation string is unique and descriptive to make the metrics data meaningful.
///
/// # Errors
/// This function does not explicitly handle errors. Any errors that occur within the provided future will propagate normally.
/// ```
pub async fn time_async<F, T>(operation: impl Into<String>, future: F) -> T
where
    F: std::future::Future<Output = T>,
{
    let operation = operation.into();
    let start = Instant::now();

    let result = future.await;

    let duration = start.elapsed();
    METRICS.record_timing(&operation, duration);

    result
}

/// ```
/// Measures the execution time of a given operation and logs its duration.
///
/// This function takes an operation name and a closure (`f`) that represents the
/// operation to be timed. It starts a timer, executes the closure, stops the
/// timer, and returns the result of the closure. The timing information can be
/// used for performance monitoring or debugging purposes.
///```
/// # Type Parameters
/// - `F`: A type that implements the `FnOnce` trait, representing the operation
///   to be measured.
/// - `T`: The return type of the closure `f`.
///
/// # Parameters
/// - `operation`: A string or type that can be converted into a `String`, which
///   represents the name of the operation being timed. This is used for
///   logging purposes.
/// - `f`: A closure containing the operation whose execution time you want to measure.
///
/// # Returns
/// - This function returns the result of the closure `f`.
///
/// # Example
/// ```
/// use my_crate::time_operation;
///
/// let result = time_operation("Expensive Operation", || {
///     // Simulate some expensive computation
///     let sum: u32 = (1..=1000).sum();
///     sum
/// });
///
/// println!("Result of the operation: {}", result);
/// ```
///
/// # Notes
/// - The function assumes the existence of a `Timer` struct with `start` and
///   `stop` methods, as shown in the implementation.
/// - Ensure the `Timer` is appropriately set up to perform logging or
///   measurement as expected.
///
/// # Panics
/// This function does not explicitly handle any panics that might occur during
/// the execution of the provided closure `f`. If `f` panics, the timing operation
/// will not complete.
/// ```
pub fn time_operation<F, T>(operation: impl Into<String>, f: F) -> T
where
    F: FnOnce() -> T,
{
    let timer = Timer::start(operation);
    let result = f();
    timer.stop();
    result
}

/// ```
/// Measures the execution time of a given operation and associates it with a specific byte size.
///
/// This function is used to time a closure `f` in the context of an `operation`
/// (represented as a string) while also associating the execution with a specific
/// number of `bytes`. The timing measurement starts just before `f` is executed
/// and stops after `f` completes. It uses a `Timer` to handle the measurement
/// and associates the given `bytes` to the operation for logging or monitoring purposes.
///```
/// # Type Parameters
/// - `F`: A callable (closure or function) that takes no arguments and returns a value of type `T`.
/// - `T`: The return type of the function or closure `f`.
///
/// # Parameters
/// - `operation`: A string-like value (`impl Into<String>`) that represents the name or description
///   of the operation being timed.
/// - `bytes`: A `u64` value that indicates the number of bytes associated with the operation.
///   This could represent the size of the data being processed, for instance.
/// - `f`: A closure or function that encapsulates the operation whose execution time is to be measured.
///   The closure is executed once (`FnOnce`).
///
/// # Returns
/// The value returned by the provided closure `f` of type `T`.
///
/// # Example
/// ```
/// let result = time_with_bytes("process_data", 1024, || {
///     // Your operation here, e.g., processing some data.
///     process_large_data()
/// });
/// println!("Operation result: {:?}", result);
/// ```
///
/// In this example, the function times the execution of `process_large_data()`
/// and associates the operation with the byte size of `1024`.
///
/// # Notes
/// - The function assumes that the `Timer` object has methods `start()`, `set_bytes()`, and `stop()`.
/// - The provided `f` closure is executed within the time measurement, and all timing
///   operations are performed synchronously.
///
/// # Panics
/// This function does not handle potential panics from the closure `f`. If `f` panics,
/// the timer might not be stopped properly, leading to incomplete timing data.
/// Ensure that `f` is safe and unlikely to panic when used within this function.
///
/// # Dependencies
/// Requires the `Timer` type to be available and properly implemented in the module or scope.
/// ```
pub fn time_with_bytes<F, T>(operation: impl Into<String>, bytes: u64, f: F) -> T
where
    F: FnOnce() -> T,
{
    let mut timer = Timer::start(operation);
    timer.set_bytes(bytes);
    let result = f();
    timer.stop();
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;

    #[test]
    fn test_timer() {
        // Clear any previous metrics for this test
        METRICS.clear();

        let timer = Timer::start("test_operation");
        thread::sleep(Duration::from_millis(10));
        timer.stop();

        // Now the timer.stop() takes ownership and prevents Drop from recording again
        let stats = METRICS.get_stats("test_operation").unwrap();
        assert_eq!(stats.count, 1); // Exactly 1 recording
        assert!(stats.total >= Duration::from_millis(10));
    }

    #[test]
    fn test_timed_macro() {
        timed!("macro_test", {
            thread::sleep(Duration::from_millis(5));
        });

        let stats = METRICS.get_stats("macro_test").unwrap();
        assert_eq!(stats.count, 1);
    }
}
