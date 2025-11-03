//! Unit tests for rolling statistics optimizations

use classic_shared_core::performance_core::{Timer, get_global_metrics};
use std::thread;
use std::time::Duration;

#[test]
fn test_rolling_stats_basic() {
    let metrics = get_global_metrics();
    metrics.clear();

    // Record some timings
    metrics.record_timing("test_op", Duration::from_millis(10));
    metrics.record_timing("test_op", Duration::from_millis(20));
    metrics.record_timing("test_op", Duration::from_millis(30));

    let stats = metrics.get_stats("test_op").expect("Stats should exist");

    assert_eq!(stats.count, 3, "Should have 3 recorded timings");
    assert_eq!(
        stats.total,
        Duration::from_millis(60),
        "Total should be 60ms"
    );
    assert_eq!(stats.min, Duration::from_millis(10), "Min should be 10ms");
    assert_eq!(stats.max, Duration::from_millis(30), "Max should be 30ms");
    assert_eq!(
        stats.average,
        Duration::from_millis(20),
        "Average should be 20ms"
    );
}

#[test]
fn test_rolling_stats_constant_memory() {
    let metrics = get_global_metrics();
    metrics.clear();

    // Record many timings (old Vec<Duration> would use O(n) memory)
    for i in 0..10000 {
        let duration = Duration::from_micros(100 + (i % 100));
        metrics.record_timing("memory_test", duration);
    }

    let stats = metrics
        .get_stats("memory_test")
        .expect("Stats should exist");

    assert_eq!(stats.count, 10000, "Should have 10000 recorded timings");
    assert!(stats.total > Duration::ZERO, "Total should be positive");
    assert!(stats.min > Duration::ZERO, "Min should be positive");
    assert!(stats.max > Duration::ZERO, "Max should be positive");
    assert!(stats.average > Duration::ZERO, "Average should be positive");

    // Key test: Stats computation should be O(1), not O(n)
    // With old Vec<Duration>, this would iterate 10000 entries
    // With rolling stats, it's just atomic loads
    let start = std::time::Instant::now();
    for _ in 0..1000 {
        let _ = metrics.get_stats("memory_test");
    }
    let elapsed = start.elapsed();

    // Should complete very quickly (< 1ms for 1000 calls)
    assert!(
        elapsed < Duration::from_millis(10),
        "Stats retrieval should be O(1): {:?}",
        elapsed
    );
}

#[test]
fn test_rolling_stats_min_max() {
    let metrics = get_global_metrics();
    metrics.clear();

    // Test min/max tracking
    let timings = vec![100, 50, 200, 25, 150, 300];

    for &t in &timings {
        metrics.record_timing("minmax_test", Duration::from_micros(t));
    }

    let stats = metrics
        .get_stats("minmax_test")
        .expect("Stats should exist");

    assert_eq!(stats.min, Duration::from_micros(25), "Min should be 25µs");
    assert_eq!(stats.max, Duration::from_micros(300), "Max should be 300µs");
}

#[test]
fn test_rolling_stats_with_bytes() {
    let metrics = get_global_metrics();
    metrics.clear();

    // Record timing with bytes
    metrics.record_timing("file_op", Duration::from_millis(10));
    metrics.record_bytes("file_op", 1024 * 1024); // 1MB

    metrics.record_timing("file_op", Duration::from_millis(20));
    metrics.record_bytes("file_op", 2 * 1024 * 1024); // 2MB

    let stats = metrics.get_stats("file_op").expect("Stats should exist");

    assert_eq!(stats.count, 2, "Should have 2 timings");
    assert_eq!(stats.bytes_processed, 3 * 1024 * 1024, "Should have 3MB");

    let throughput = stats.throughput().expect("Should calculate throughput");
    assert!(throughput > 0.0, "Throughput should be positive");
}

#[test]
fn test_rolling_stats_multiple_operations() {
    let metrics = get_global_metrics();
    metrics.clear();

    // Record timings for multiple operations
    metrics.record_timing("op1", Duration::from_millis(10));
    metrics.record_timing("op2", Duration::from_millis(20));
    metrics.record_timing("op3", Duration::from_millis(30));

    let ops = metrics.get_operations();
    assert_eq!(ops.len(), 3, "Should have 3 operations");
    assert!(ops.contains(&"op1".to_string()));
    assert!(ops.contains(&"op2".to_string()));
    assert!(ops.contains(&"op3".to_string()));

    // Each operation should have its own stats
    let stats1 = metrics.get_stats("op1").expect("op1 stats should exist");
    let stats2 = metrics.get_stats("op2").expect("op2 stats should exist");
    let stats3 = metrics.get_stats("op3").expect("op3 stats should exist");

    assert_eq!(stats1.count, 1);
    assert_eq!(stats2.count, 1);
    assert_eq!(stats3.count, 1);
}

#[test]
fn test_timer_integration() {
    let metrics = get_global_metrics();
    metrics.clear();

    {
        let timer = Timer::start("timer_test");
        thread::sleep(Duration::from_millis(10));
        timer.stop();
    }

    let stats = metrics.get_stats("timer_test").expect("Stats should exist");
    assert_eq!(stats.count, 1, "Should have 1 timing");
    assert!(
        stats.total >= Duration::from_millis(10),
        "Duration should be at least 10ms"
    );
}

#[test]
fn test_timer_auto_drop() {
    let metrics = get_global_metrics();
    metrics.clear();

    {
        let _timer = Timer::start("auto_drop_test");
        thread::sleep(Duration::from_millis(5));
        // Timer drops here and auto-records
    }

    let stats = metrics
        .get_stats("auto_drop_test")
        .expect("Stats should exist");
    assert_eq!(stats.count, 1, "Should have 1 timing from auto-drop");
    assert!(
        stats.total >= Duration::from_millis(5),
        "Duration should be at least 5ms"
    );
}

#[test]
fn test_timer_with_bytes() {
    let metrics = get_global_metrics();
    metrics.clear();

    {
        let mut timer = Timer::start("bytes_test");
        timer.set_bytes(1024);
        thread::sleep(Duration::from_millis(10));
        timer.stop();
    }

    let stats = metrics.get_stats("bytes_test").expect("Stats should exist");
    assert_eq!(stats.count, 1, "Should have 1 timing");
    assert_eq!(stats.bytes_processed, 1024, "Should have recorded bytes");
}

#[test]
fn test_concurrent_recording() {
    let metrics = get_global_metrics();
    metrics.clear();

    // Spawn multiple threads recording concurrently
    let handles: Vec<_> = (0..10)
        .map(|thread_id| {
            let metrics = metrics.clone();
            thread::spawn(move || {
                for i in 0..100 {
                    let duration = Duration::from_micros(100 + (i % 100));
                    metrics.record_timing(&format!("thread_{}", thread_id), duration);
                }
            })
        })
        .collect();

    for handle in handles {
        handle.join().expect("Thread should complete");
    }

    // Verify all threads recorded their data
    for thread_id in 0..10 {
        let stats = metrics
            .get_stats(&format!("thread_{}", thread_id))
            .expect("Thread stats should exist");
        assert_eq!(
            stats.count, 100,
            "Thread {} should have 100 timings",
            thread_id
        );
    }
}

#[test]
fn test_clear_metrics() {
    let metrics = get_global_metrics();

    // Record some data
    metrics.record_timing("clear_test", Duration::from_millis(10));
    assert!(
        metrics.get_stats("clear_test").is_some(),
        "Stats should exist before clear"
    );

    // Clear all metrics
    metrics.clear();

    assert!(
        metrics.get_stats("clear_test").is_none(),
        "Stats should not exist after clear"
    );
    assert_eq!(
        metrics.get_operations().len(),
        0,
        "Should have no operations after clear"
    );
}

#[test]
fn test_rolling_stats_accuracy() {
    let metrics = get_global_metrics();
    metrics.clear();

    // Known sequence of timings
    let timings = vec![5, 10, 15, 20, 25, 30, 35, 40, 45, 50];
    let expected_sum: u64 = timings.iter().sum();
    let expected_count = timings.len();
    let expected_avg = expected_sum / expected_count as u64;
    let expected_min = *timings.iter().min().unwrap();
    let expected_max = *timings.iter().max().unwrap();

    for &t in &timings {
        metrics.record_timing("accuracy_test", Duration::from_millis(t));
    }

    let stats = metrics
        .get_stats("accuracy_test")
        .expect("Stats should exist");

    assert_eq!(stats.count, expected_count, "Count should match");
    assert_eq!(
        stats.total,
        Duration::from_millis(expected_sum),
        "Total should match"
    );
    assert_eq!(
        stats.average,
        Duration::from_millis(expected_avg),
        "Average should match"
    );
    assert_eq!(
        stats.min,
        Duration::from_millis(expected_min),
        "Min should match"
    );
    assert_eq!(
        stats.max,
        Duration::from_millis(expected_max),
        "Max should match"
    );
}
