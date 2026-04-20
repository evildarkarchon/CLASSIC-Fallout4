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
