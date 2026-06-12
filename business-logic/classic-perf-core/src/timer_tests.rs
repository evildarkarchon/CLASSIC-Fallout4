use super::*;
use crate::{clear_metrics, get_summary};
use serial_test::serial;
use std::thread;
use std::time::Duration;

#[test]
#[serial]
fn test_timer_finish() {
    clear_metrics();

    let timer = start_timer("finish_test");
    thread::sleep(Duration::from_millis(10));
    timer.finish();

    let summary = get_summary();
    assert!(summary.contains_key("finish_test"));
    let stats = summary.get("finish_test").unwrap();
    assert_eq!(stats.count, 1);
    assert!(stats.total >= 0.010);
}

#[test]
#[serial]
fn test_timer_drop() {
    clear_metrics();

    {
        let _timer = start_timer("drop_test");
        thread::sleep(Duration::from_millis(10));
        // Drops here
    }

    let summary = get_summary();
    assert!(summary.contains_key("drop_test"));
}

#[test]
#[serial]
fn test_timer_elapsed() {
    clear_metrics();

    let timer = start_timer("elapsed_test");
    thread::sleep(Duration::from_millis(50));
    let elapsed = timer.elapsed();
    assert!(elapsed >= 0.05);
    timer.finish();
}

#[test]
#[serial]
fn test_multiple_timers() {
    clear_metrics();

    for _i in 0..5 {
        let timer = start_timer("multi_test");
        thread::sleep(Duration::from_millis(10));
        timer.finish();
    }

    let summary = get_summary();
    let stats = summary.get("multi_test").unwrap();
    assert_eq!(stats.count, 5);
}
