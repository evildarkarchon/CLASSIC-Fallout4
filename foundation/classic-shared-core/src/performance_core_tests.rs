use super::*;
use serial_test::serial;
use std::thread;

#[test]
#[serial]
fn test_timer() {
    METRICS.clear();

    let timer = Timer::start("test_operation");
    thread::sleep(Duration::from_millis(10));
    timer.finish().unwrap();

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
    timer.finish().unwrap();

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
    metrics
        .record_timing("op1", Duration::from_millis(10))
        .unwrap();
    metrics
        .record_timing("op1", Duration::from_millis(20))
        .unwrap();
    metrics
        .record_timing("op1", Duration::from_millis(5))
        .unwrap();

    let stats = metrics.get_stats("op1").unwrap();
    assert_eq!(stats.count, 3);
    assert_eq!(stats.min, Duration::from_millis(5));
    assert_eq!(stats.max, Duration::from_millis(20));
}

#[test]
fn test_record_bytes() {
    let metrics = PerformanceMetrics::new();
    metrics
        .record_timing("op", Duration::from_millis(1))
        .unwrap();
    metrics.record_bytes("op", 500).unwrap();
    metrics.record_bytes("op", 300).unwrap();

    let stats = metrics.get_stats("op").unwrap();
    assert_eq!(stats.bytes_processed, 800);
}

#[test]
fn test_get_stats_nonexistent() {
    let metrics = PerformanceMetrics::new();
    assert!(metrics.get_stats("nonexistent").is_none());
}

#[test]
fn test_bytes_only_operation_is_not_reported() {
    let metrics = PerformanceMetrics::new();
    metrics.record_bytes("bytes_only", 64).unwrap();
    assert!(metrics.get_stats("bytes_only").is_none());
    assert!(metrics.get_operations().is_empty());

    // The bytes recorded before the first sample still count.
    metrics.record_timing("bytes_only", Duration::ZERO).unwrap();
    assert_eq!(metrics.get_stats("bytes_only").unwrap().bytes_processed, 64);
}

#[test]
fn test_get_operations() {
    let metrics = PerformanceMetrics::new();
    metrics
        .record_timing("a", Duration::from_millis(1))
        .unwrap();
    metrics
        .record_timing("b", Duration::from_millis(1))
        .unwrap();

    let ops = metrics.get_operations();
    assert_eq!(ops.len(), 2);
    assert!(ops.contains(&"a".to_string()));
    assert!(ops.contains(&"b".to_string()));
}

#[test]
fn test_clear_metrics() {
    let metrics = PerformanceMetrics::new();
    metrics
        .record_timing("op", Duration::from_millis(1))
        .unwrap();
    metrics.record_bytes("op", 100).unwrap();
    metrics.clear();
    assert!(metrics.get_operations().is_empty());
    assert!(metrics.get_stats("op").is_none());

    // Clearing removes byte totals too, not just timing samples.
    metrics
        .record_timing("op", Duration::from_millis(1))
        .unwrap();
    assert_eq!(metrics.get_stats("op").unwrap().bytes_processed, 0);
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
    // A zero-length sample is valid and produces a zero average.
    metrics.record_timing("zero_avg", Duration::ZERO).unwrap();
    let stats = metrics.get_stats("zero_avg").unwrap();
    assert_eq!(stats.count, 1);
    assert_eq!(stats.average, Duration::ZERO);
}

// ---------------------------------------------------------------------------
// Sample conversion contract
// ---------------------------------------------------------------------------

#[test]
fn test_secs_conversion_rounds_once_to_nearest_nanosecond() {
    // 0.999e-9 is just below one nanosecond and rounds up to it.
    assert_eq!(duration_from_secs_f64(0.999e-9).unwrap().as_nanos(), 1);
    // 0.4e-9 rounds down to zero.
    assert_eq!(duration_from_secs_f64(0.4e-9).unwrap().as_nanos(), 0);
    assert_eq!(
        duration_from_secs_f64(0.125).unwrap(),
        Duration::from_millis(125)
    );
    assert_eq!(duration_from_secs_f64(1.0).unwrap(), Duration::from_secs(1));
}

#[test]
fn test_millis_conversion_rounds_once_to_nearest_nanosecond() {
    assert_eq!(
        duration_from_millis_f64(125.0).unwrap(),
        Duration::from_millis(125)
    );
    // 1.5 µs expressed in milliseconds is exact in nanoseconds.
    assert_eq!(duration_from_millis_f64(0.0015).unwrap().as_nanos(), 1_500);
    // 1/128 ms and 3/128 ms are exact binary values whose nanosecond products
    // (7812.5 and 23437.5) are exact ties; ties round to the even neighbour.
    assert_eq!(
        duration_from_millis_f64(1.0 / 128.0).unwrap().as_nanos(),
        7_812
    );
    assert_eq!(
        duration_from_millis_f64(3.0 / 128.0).unwrap().as_nanos(),
        23_438
    );
}

#[test]
fn test_secs_conversion_matches_std_single_rounding() {
    // std's `try_from_secs_f64` rounds exactly once from the binary value.
    // Cross-check a deterministic spread of magnitudes inside our range.
    let mut state: u64 = 0x9E37_79B9_7F4A_7C15;
    for _ in 0..20_000 {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        let mantissa = (state >> 11) as f64 / (1u64 << 53) as f64;
        let exponent = (state % 60) as i32 - 40;
        let value = mantissa * 2f64.powi(exponent);
        let ours = duration_from_secs_f64(value).unwrap();
        let std_value = Duration::try_from_secs_f64(value).unwrap();
        assert_eq!(ours, std_value, "mismatch for {value:e}");
    }
}

#[test]
fn test_negative_zero_is_zero() {
    assert_eq!(duration_from_secs_f64(-0.0).unwrap(), Duration::ZERO);
    assert_eq!(duration_from_millis_f64(-0.0).unwrap(), Duration::ZERO);
}

#[test]
fn test_subnormal_rounds_to_zero() {
    assert_eq!(
        duration_from_secs_f64(f64::from_bits(1)).unwrap(),
        Duration::ZERO
    );
}

#[test]
fn test_invalid_float_samples_are_rejected() {
    assert_eq!(
        duration_from_secs_f64(-1e-12),
        Err(TimingError::Negative { value: -1e-12 })
    );
    assert!(matches!(
        duration_from_secs_f64(f64::NAN),
        Err(TimingError::NonFinite { .. })
    ));
    assert_eq!(
        duration_from_millis_f64(f64::INFINITY),
        Err(TimingError::NonFinite {
            value: f64::INFINITY
        })
    );
    assert_eq!(
        duration_from_millis_f64(f64::NEG_INFINITY),
        Err(TimingError::NonFinite {
            value: f64::NEG_INFINITY
        })
    );
}

#[test]
fn test_representable_sample_limits() {
    // u64::MAX ns ≈ 18_446_744_073.709_551_615 s; the largest f64 below that
    // bound converts, the next one up does not.
    let max_secs = u64::MAX as f64 / 1e9;
    let below = f64::from_bits(max_secs.to_bits() - 1);
    assert!(duration_from_secs_f64(below).is_ok());
    assert_eq!(
        duration_from_secs_f64(max_secs * 2.0),
        Err(TimingError::SampleOutOfRange)
    );
    assert_eq!(
        duration_from_secs_f64(f64::MAX),
        Err(TimingError::SampleOutOfRange)
    );
    assert_eq!(
        duration_from_millis_u64(u64::MAX / NANOS_PER_MILLISECOND).unwrap(),
        Duration::from_millis(u64::MAX / NANOS_PER_MILLISECOND)
    );
    assert_eq!(
        duration_from_millis_u64(u64::MAX / NANOS_PER_MILLISECOND + 1),
        Err(TimingError::SampleOutOfRange)
    );
}

// ---------------------------------------------------------------------------
// No-mutation and counter-limit contract
// ---------------------------------------------------------------------------

#[test]
fn test_invalid_samples_leave_state_unchanged() {
    let metrics = PerformanceMetrics::new();
    metrics.record_timing_secs("op", 0.5).unwrap();
    let before = metrics.all_stats();

    for value in [-1.0, f64::NAN, f64::INFINITY, f64::MAX] {
        assert!(metrics.record_timing_secs("op", value).is_err());
        assert!(metrics.record_timing_millis("fresh", value).is_err());
    }
    assert!(
        metrics
            .record_timing("fresh", Duration::from_secs(u64::MAX))
            .is_err()
    );

    // No new operation was created and the existing one is untouched.
    assert_eq!(metrics.all_stats(), before);
}

#[test]
fn test_accumulated_duration_cannot_wrap() {
    let metrics = PerformanceMetrics::new();
    let max = Duration::from_nanos(MAX_SAMPLE_NANOS);
    metrics.record_timing("op", max).unwrap();
    let before = metrics.get_stats("op").unwrap();

    assert_eq!(
        metrics.record_timing("op", Duration::from_nanos(1)),
        Err(TimingError::CounterOverflow {
            operation: "op".into(),
            counter: MetricCounter::TotalDuration,
        })
    );
    assert_eq!(metrics.get_stats("op").unwrap(), before);

    // A zero sample still fits and updates count and minimum.
    metrics.record_timing("op", Duration::ZERO).unwrap();
    let after = metrics.get_stats("op").unwrap();
    assert_eq!(after.count, 2);
    assert_eq!(after.min, Duration::ZERO);
    assert_eq!(after.total, max);
}

#[test]
fn test_accumulated_bytes_cannot_wrap() {
    let metrics = PerformanceMetrics::new();
    metrics.record_timing("op", Duration::ZERO).unwrap();
    metrics.record_bytes("op", u64::MAX).unwrap();

    assert_eq!(
        metrics.record_bytes("op", 1),
        Err(TimingError::CounterOverflow {
            operation: "op".into(),
            counter: MetricCounter::BytesProcessed,
        })
    );
    assert_eq!(metrics.get_stats("op").unwrap().bytes_processed, u64::MAX);
}

#[test]
fn test_combined_record_is_all_or_nothing() {
    let metrics = PerformanceMetrics::new();
    metrics
        .record_timing("op", Duration::from_millis(1))
        .unwrap();
    metrics.record_bytes("op", u64::MAX).unwrap();
    let before = metrics.get_stats("op").unwrap();

    // The byte overflow must also discard the timing half of the record.
    assert!(
        metrics
            .record_timing_with_bytes("op", Duration::from_millis(1), Some(1))
            .is_err()
    );
    assert_eq!(metrics.get_stats("op").unwrap(), before);
}

#[test]
fn test_error_codes_are_stable_tokens() {
    assert_eq!(
        TimingError::NonFinite { value: f64::NAN }.code(),
        "timing_sample_not_finite"
    );
    assert_eq!(
        TimingError::Negative { value: -1.0 }.code(),
        "timing_sample_negative"
    );
    assert_eq!(
        TimingError::SampleOutOfRange.code(),
        "timing_sample_out_of_range"
    );
    assert_eq!(
        TimingError::CounterOverflow {
            operation: String::new(),
            counter: MetricCounter::SampleCount,
        }
        .code(),
        "timing_counter_overflow"
    );
}

#[test]
#[serial]
fn test_millis_free_function_records_into_default_store() {
    clear_metrics();
    record_timing_millis("ms", 3.0 / 128.0).unwrap();
    assert_eq!(
        get_global_metrics().get_stats("ms").unwrap().total,
        Duration::from_nanos(23_438)
    );
    assert!(record_timing_millis("ms", -1.0).is_err());
    assert_eq!(get_global_metrics().get_stats("ms").unwrap().count, 1);
    clear_metrics();
}

#[test]
fn test_coded_message_prefixes_stable_token() {
    let error = TimingError::Negative { value: -2.0 };
    assert_eq!(
        error.coded_message(),
        "timing_sample_negative: timing sample must not be negative, got -2"
    );
}

#[test]
fn test_signed_millis_conversion() {
    assert_eq!(
        duration_from_millis_i128(250).unwrap(),
        Duration::from_millis(250)
    );
    assert_eq!(
        duration_from_millis_i128(-1),
        Err(TimingError::Negative { value: -1.0 })
    );
    assert_eq!(
        duration_from_millis_i128(i128::MAX),
        Err(TimingError::SampleOutOfRange)
    );
}

#[test]
#[serial]
fn test_stop_is_an_at_most_once_alias_of_finish() {
    clear_metrics();
    let timer = Timer::start("stopped");
    timer.stop().unwrap();
    assert_eq!(get_summary()["stopped"].count, 1);
    clear_metrics();
}

#[test]
fn test_counter_overflow_message_names_operation_and_counter() {
    let error = TimingError::CounterOverflow {
        operation: "scan".into(),
        counter: MetricCounter::TotalDuration,
    };
    assert_eq!(
        error.to_string(),
        "recording 'scan' would overflow its accumulated total duration"
    );
}

// ---------------------------------------------------------------------------
// Default store and seconds view
// ---------------------------------------------------------------------------

#[test]
#[serial]
fn test_seconds_view_and_default_store_share_state() {
    clear_metrics();
    record_timing("shared", 0.25).unwrap();
    METRICS
        .record_timing_with_bytes("shared", Duration::from_millis(750), Some(10))
        .unwrap();

    let summary = get_summary();
    let shared = &summary["shared"];
    assert_eq!(shared.count, 2);
    assert_eq!(shared.total, 1.0);
    assert_eq!(shared.average, 0.5);
    assert_eq!(shared.min, 0.25);
    assert_eq!(shared.max, 0.75);
    assert_eq!(get_global_metrics().get_stats("shared").unwrap().count, 2);

    // Clearing through either view clears timing and bytes for both.
    get_global_metrics().clear();
    assert!(get_summary().is_empty());
    record_timing("shared", 0.0).unwrap();
    assert_eq!(
        get_global_metrics()
            .get_stats("shared")
            .unwrap()
            .bytes_processed,
        0
    );
    clear_metrics();
    assert!(get_global_metrics().get_operations().is_empty());
}

#[test]
#[serial]
fn test_explicit_metrics_are_independent_of_default_store() {
    clear_metrics();
    let owned = PerformanceMetrics::new();
    owned
        .record_timing("owned", Duration::from_millis(1))
        .unwrap();
    record_timing("global", 0.001).unwrap();

    assert!(!get_summary().contains_key("owned"));
    assert!(owned.get_stats("global").is_none());

    clear_metrics();
    assert_eq!(owned.get_stats("owned").unwrap().count, 1);
}

#[test]
#[serial]
fn test_seconds_record_rejects_without_mutation() {
    clear_metrics();
    record_timing("kept", 0.5).unwrap();
    let before = get_summary();
    assert!(record_timing("kept", -0.5).is_err());
    assert!(record_timing("new", f64::NAN).is_err());
    assert_eq!(get_summary(), before);
    clear_metrics();
}

#[test]
#[serial]
fn test_timer_records_at_most_once() {
    clear_metrics();
    let timer = start_timer("once");
    assert!(timer.elapsed() >= Duration::ZERO);
    // `finish` consumes the timer; its later drop must not record again.
    timer.finish().unwrap();
    assert_eq!(get_summary()["once"].count, 1);

    {
        let _dropped = start_timer("dropped");
    }
    assert_eq!(get_summary()["dropped"].count, 1);
    clear_metrics();
}

/// Concurrent timers on distinct names all land in the default store.
///
/// Carried over from the retired `classic-perf-core` facade suite so the
/// seconds view keeps a multi-threaded recording check after #256.
#[test]
#[serial]
fn test_concurrent_timers_record_into_default_store() {
    clear_metrics();

    let handles: Vec<_> = (0..10)
        .map(|i| {
            thread::spawn(move || {
                for _ in 0..10 {
                    let timer = start_timer(format!("thread_{i}"));
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
    assert_eq!(summary.len(), 10);
    for i in 0..10 {
        assert_eq!(summary[&format!("thread_{i}")].count, 10);
    }
    clear_metrics();
}

#[test]
#[serial]
fn test_timer_overflow_is_rejected_on_finish_and_skipped_on_drop() {
    clear_metrics();
    METRICS
        .record_timing("full", Duration::from_nanos(MAX_SAMPLE_NANOS))
        .unwrap();
    let before = METRICS.get_stats("full").unwrap();

    thread::sleep(Duration::from_millis(1));
    let finished = Timer::start("full");
    thread::sleep(Duration::from_millis(1));
    assert!(matches!(
        finished.finish(),
        Err(TimingError::CounterOverflow { .. })
    ));
    {
        let _dropped = Timer::start("full");
        thread::sleep(Duration::from_millis(1));
    }

    assert_eq!(METRICS.get_stats("full").unwrap(), before);
    clear_metrics();
}
