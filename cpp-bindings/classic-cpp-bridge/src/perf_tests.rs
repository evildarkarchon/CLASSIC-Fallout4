use serial_test::serial;

use super::*;

#[test]
#[serial]
fn test_record_and_summary() {
    perf_clear_metrics();
    perf_record_timing("cxx_rec_summary", 0.5).unwrap();
    perf_record_timing("cxx_rec_summary", 1.0).unwrap();

    let summary = perf_get_summary();
    assert!(!summary.is_empty());
    let test_line = summary.iter().find(|s| s.contains("cxx_rec_summary"));
    assert!(test_line.is_some());
}

#[test]
#[serial]
fn test_operation_count() {
    perf_clear_metrics();
    perf_record_timing("cxx_count_op", 0.1).unwrap();
    perf_record_timing("cxx_count_op", 0.2).unwrap();
    perf_record_timing("cxx_count_op", 0.3).unwrap();
    assert_eq!(perf_get_operation_count("cxx_count_op"), 3);
}

#[test]
#[serial]
fn test_operation_average() {
    perf_clear_metrics();
    perf_record_timing("cxx_avg_op", 1.0).unwrap();
    perf_record_timing("cxx_avg_op", 3.0).unwrap();
    let avg = perf_get_operation_average("cxx_avg_op");
    assert!((avg - 2.0).abs() < f64::EPSILON);
}

#[test]
#[serial]
fn test_clear_metrics() {
    perf_record_timing("cxx_clear_op", 1.0).unwrap();
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

#[test]
#[serial]
fn test_invalid_samples_raise_coded_errors_without_mutation() {
    perf_clear_metrics();
    perf_record_timing("cxx_invalid_op", 0.25).unwrap();
    let before = perf_get_summary();

    for (value, code) in [
        (-0.5, "timing_sample_negative"),
        (f64::NAN, "timing_sample_not_finite"),
        (f64::INFINITY, "timing_sample_not_finite"),
        (1e300, "timing_sample_out_of_range"),
    ] {
        let error = perf_record_timing("cxx_invalid_op", value).unwrap_err();
        assert!(error.starts_with(&format!("{code}: ")), "{error}");
    }
    assert!(perf_record_timing("cxx_never_created", f64::NAN).is_err());

    assert_eq!(perf_get_summary(), before);
    assert_eq!(perf_get_operation_count("cxx_never_created"), 0);
    perf_clear_metrics();
}

#[test]
#[serial]
fn test_accumulated_overflow_is_rejected() {
    perf_clear_metrics();
    // 18e9 s fits below u64::MAX nanoseconds; a second one would not.
    perf_record_timing("cxx_full_op", 18e9).unwrap();
    let error = perf_record_timing("cxx_full_op", 1e9).unwrap_err();
    assert!(error.starts_with("timing_counter_overflow: "), "{error}");
    assert_eq!(perf_get_operation_count("cxx_full_op"), 1);
    perf_clear_metrics();
}

#[test]
#[serial]
fn test_negative_zero_and_nanosecond_rounding() {
    perf_clear_metrics();
    perf_record_timing("cxx_zero_op", -0.0).unwrap();
    assert_eq!(perf_get_operation_count("cxx_zero_op"), 1);
    assert_eq!(perf_get_operation_average("cxx_zero_op"), 0.0);

    // 1/1024 s is exactly 976_562.5 ns; ties round to the even neighbour.
    perf_record_timing("cxx_tie_op", 1.0 / 1024.0).unwrap();
    assert_eq!(perf_get_operation_average("cxx_tie_op"), 976_562e-9);
    perf_clear_metrics();
}
