use super::*;
use classic_shared_core::performance_core::get_global_metrics;
use serial_test::serial;
use std::thread;
use std::time::Duration;

#[test]
#[serial]
fn test_timer_basic() {
    clear_metrics();

    let timer = start_timer("test_op");
    thread::sleep(Duration::from_millis(10));
    timer.finish().unwrap();

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
        timer.finish().unwrap();
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
    for seconds in [1.0, 2.0, 3.0, 4.0, 5.0] {
        record_timing("stats_test", seconds).unwrap();
    }

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

    record_timing("clear_test", 1.0).unwrap();
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
                    timer.finish().unwrap();
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

#[test]
#[serial]
fn test_facade_shares_the_shared_core_default_store() {
    clear_metrics();
    record_timing("facade", 0.5).unwrap();
    assert_eq!(get_global_metrics().get_stats("facade").unwrap().count, 1);

    // Clearing the shared-core store is visible through the facade.
    get_global_metrics().clear();
    assert!(get_summary().is_empty());
}

#[test]
#[serial]
fn test_invalid_samples_are_rejected_without_mutation() {
    clear_metrics();
    record_timing("kept", 0.25).unwrap();
    let before = get_summary();

    for value in [-0.001, f64::NAN, f64::INFINITY, f64::NEG_INFINITY, 1e300] {
        assert!(record_timing("kept", value).is_err(), "{value} accepted");
    }
    assert_eq!(get_summary(), before);
    clear_metrics();
}
