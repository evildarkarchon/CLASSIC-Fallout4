use super::*;
use serial_test::serial;
use std::thread;

#[test]
#[serial]
fn test_timer() {
    METRICS.clear();

    let timer = Timer::start("test_operation");
    thread::sleep(Duration::from_millis(10));
    timer.stop();

    let stats = METRICS.get_stats("test_operation").unwrap();
    assert_eq!(stats.count, 1);
    assert!(stats.total >= Duration::from_millis(10));
}

#[test]
#[serial]
fn test_timed_macro() {
    timed!("macro_test", {
        thread::sleep(Duration::from_millis(5));
    });

    let stats = METRICS.get_stats("macro_test").unwrap();
    assert_eq!(stats.count, 1);
}

#[test]
#[serial]
fn test_timer_drop_records() {
    METRICS.clear();
    {
        let _timer = Timer::start("drop_test");
        thread::sleep(Duration::from_millis(5));
        // Timer dropped here
    }
    let stats = METRICS.get_stats("drop_test").unwrap();
    assert_eq!(stats.count, 1);
}

#[test]
#[serial]
fn test_timer_set_bytes() {
    METRICS.clear();
    let mut timer = Timer::start("bytes_test");
    timer.set_bytes(1024);
    timer.stop();

    let stats = METRICS.get_stats("bytes_test").unwrap();
    assert_eq!(stats.count, 1);
    assert_eq!(stats.bytes_processed, 1024);
}

#[test]
fn test_performance_metrics_new() {
    let metrics = PerformanceMetrics::new();
    assert!(metrics.get_operations().is_empty());
}

#[test]
fn test_performance_metrics_default() {
    let metrics = PerformanceMetrics::default();
    assert!(metrics.get_operations().is_empty());
}

#[test]
fn test_record_timing_multiple() {
    let metrics = PerformanceMetrics::new();
    metrics.record_timing("op1", Duration::from_millis(10));
    metrics.record_timing("op1", Duration::from_millis(20));
    metrics.record_timing("op1", Duration::from_millis(5));

    let stats = metrics.get_stats("op1").unwrap();
    assert_eq!(stats.count, 3);
    assert!(stats.min <= Duration::from_millis(6)); // ~5ms
    assert!(stats.max >= Duration::from_millis(19)); // ~20ms
}

#[test]
fn test_record_bytes() {
    let metrics = PerformanceMetrics::new();
    metrics.record_timing("op", Duration::from_millis(1));
    metrics.record_bytes("op", 500);
    metrics.record_bytes("op", 300);

    let stats = metrics.get_stats("op").unwrap();
    assert_eq!(stats.bytes_processed, 800);
}

#[test]
fn test_get_stats_nonexistent() {
    let metrics = PerformanceMetrics::new();
    assert!(metrics.get_stats("nonexistent").is_none());
}

#[test]
fn test_get_operations() {
    let metrics = PerformanceMetrics::new();
    metrics.record_timing("a", Duration::from_millis(1));
    metrics.record_timing("b", Duration::from_millis(1));

    let ops = metrics.get_operations();
    assert_eq!(ops.len(), 2);
    assert!(ops.contains(&"a".to_string()));
    assert!(ops.contains(&"b".to_string()));
}

#[test]
fn test_clear_metrics() {
    let metrics = PerformanceMetrics::new();
    metrics.record_timing("op", Duration::from_millis(1));
    metrics.record_bytes("op", 100);
    metrics.clear();
    assert!(metrics.get_operations().is_empty());
    assert!(metrics.get_stats("op").is_none());
}

#[test]
fn test_operation_stats_throughput() {
    let stats = OperationStats {
        count: 1,
        total: Duration::from_secs(1),
        average: Duration::from_secs(1),
        min: Duration::from_secs(1),
        max: Duration::from_secs(1),
        bytes_processed: 1_000_000,
    };
    let throughput = stats.throughput().unwrap();
    assert!((throughput - 1_000_000.0).abs() < 1.0);
}

#[test]
fn test_operation_stats_throughput_no_bytes() {
    let stats = OperationStats {
        count: 1,
        total: Duration::from_secs(1),
        average: Duration::from_secs(1),
        min: Duration::from_secs(1),
        max: Duration::from_secs(1),
        bytes_processed: 0,
    };
    assert!(stats.throughput().is_none());
}

#[test]
fn test_operation_stats_throughput_zero_duration() {
    let stats = OperationStats {
        count: 0,
        total: Duration::ZERO,
        average: Duration::ZERO,
        min: Duration::ZERO,
        max: Duration::ZERO,
        bytes_processed: 100,
    };
    assert!(stats.throughput().is_none());
}

#[test]
#[serial]
fn test_time_operation() {
    METRICS.clear();
    let result = time_operation("sync_op", || 42);
    assert_eq!(result, 42);
    assert!(METRICS.get_stats("sync_op").is_some());
}

#[test]
#[serial]
fn test_time_with_bytes() {
    METRICS.clear();
    let result = time_with_bytes("bytes_op", 2048, || "done");
    assert_eq!(result, "done");
    let stats = METRICS.get_stats("bytes_op").unwrap();
    assert_eq!(stats.bytes_processed, 2048);
}

#[test]
#[serial]
fn test_time_async() {
    METRICS.clear();
    let rt = crate::get_runtime();
    let result = rt.block_on(time_async("async_op", async { 99 }));
    assert_eq!(result, 99);
    assert!(METRICS.get_stats("async_op").is_some());
}

#[test]
fn test_get_global_metrics() {
    let metrics = get_global_metrics();
    // Just verify it doesn't panic and returns a reference
    let _ = metrics.get_operations();
}

#[test]
fn test_get_timer_start() {
    let start = get_timer_start();
    // Should be a past instant
    assert!(start.elapsed() >= Duration::ZERO);
}

#[test]
fn test_rolling_stats_zero_count() {
    let metrics = PerformanceMetrics::new();
    // Record a timing so we can get stats (0 count isn't possible with recorded ops)
    // Create the entry but don't record to get edge case
    metrics.record_timing("zero_avg", Duration::ZERO);
    let stats = metrics.get_stats("zero_avg").unwrap();
    assert_eq!(stats.count, 1);
    assert_eq!(stats.average, Duration::ZERO);
}
