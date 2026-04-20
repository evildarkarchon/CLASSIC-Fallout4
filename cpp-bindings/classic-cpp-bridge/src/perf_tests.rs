use serial_test::serial;

use super::*;

#[test]
#[serial]
fn test_record_and_summary() {
    perf_clear_metrics();
    perf_record_timing("cxx_rec_summary", 0.5);
    perf_record_timing("cxx_rec_summary", 1.0);

    let summary = perf_get_summary();
    assert!(!summary.is_empty());
    let test_line = summary.iter().find(|s| s.contains("cxx_rec_summary"));
    assert!(test_line.is_some());
}

#[test]
#[serial]
fn test_operation_count() {
    perf_clear_metrics();
    perf_record_timing("cxx_count_op", 0.1);
    perf_record_timing("cxx_count_op", 0.2);
    perf_record_timing("cxx_count_op", 0.3);
    assert_eq!(perf_get_operation_count("cxx_count_op"), 3);
}

#[test]
#[serial]
fn test_operation_average() {
    perf_clear_metrics();
    perf_record_timing("cxx_avg_op", 1.0);
    perf_record_timing("cxx_avg_op", 3.0);
    let avg = perf_get_operation_average("cxx_avg_op");
    assert!((avg - 2.0).abs() < f64::EPSILON);
}

#[test]
#[serial]
fn test_clear_metrics() {
    perf_record_timing("cxx_clear_op", 1.0);
    assert!(perf_get_operation_count("cxx_clear_op") >= 1);
    perf_clear_metrics();
    assert_eq!(perf_get_operation_count("cxx_clear_op"), 0);
}

#[test]
#[serial]
fn test_missing_operation() {
    perf_clear_metrics();
    assert_eq!(perf_get_operation_count("cxx_nonexistent_op"), 0);
    assert!((perf_get_operation_average("cxx_nonexistent_op")).abs() < f64::EPSILON);
}
