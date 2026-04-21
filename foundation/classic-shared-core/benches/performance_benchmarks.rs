//! Benchmarks for performance metrics optimizations

#![allow(missing_docs)]

use classic_shared_core::performance_core::{Timer, get_global_metrics};
use criterion::{BenchmarkId, Criterion, criterion_group, criterion_main};
use std::hint::black_box;
use std::time::Duration;

fn bench_record_timing(c: &mut Criterion) {
    let mut group = c.benchmark_group("record_timing");
    let metrics = get_global_metrics();

    // Clear metrics before benchmarking
    metrics.clear();

    // Benchmark recording timing (now with rolling stats - O(1) memory)
    group.bench_function("record_single", |b| {
        b.iter(|| {
            metrics.record_timing("test_op", Duration::from_micros(100));
            black_box(());
        });
    });

    // Benchmark recording many timings (tests memory efficiency)
    for count in [100, 1000, 10000] {
        group.bench_with_input(
            BenchmarkId::new("record_many", count),
            &count,
            |b, &count| {
                metrics.clear();
                b.iter(|| {
                    for i in 0..count {
                        let duration = Duration::from_micros(100 + (i as u64 % 100));
                        metrics.record_timing("bulk_op", duration);
                        black_box(());
                    }
                });
            },
        );
    }

    group.finish();
}

fn bench_get_stats(c: &mut Criterion) {
    let mut group = c.benchmark_group("get_stats");
    let metrics = get_global_metrics();

    // Record different amounts of data
    for count in [100, 1000, 10000] {
        metrics.clear();

        // Record timings
        for i in 0..count {
            let duration = Duration::from_micros(100 + (i as u64 % 100));
            metrics.record_timing("test_op", duration);
        }

        group.bench_with_input(
            BenchmarkId::new("get_stats_after_n_records", count),
            &count,
            |b, _| {
                b.iter(|| {
                    black_box(metrics.get_stats("test_op"));
                });
            },
        );
    }

    group.finish();
}

fn bench_timer(c: &mut Criterion) {
    let mut group = c.benchmark_group("timer");
    let metrics = get_global_metrics();

    metrics.clear();

    // Benchmark timer creation and stopping
    group.bench_function("timer_start_stop", |b| {
        b.iter(|| {
            let timer = Timer::start("benchmark_op");
            // Simulate some work
            std::thread::sleep(Duration::from_micros(1));
            timer.stop();
        });
    });

    // Benchmark timer with automatic drop
    group.bench_function("timer_auto_drop", |b| {
        b.iter(|| {
            let _timer = Timer::start("benchmark_op_drop");
            // Simulate some work
            std::thread::sleep(Duration::from_micros(1));
            // Timer automatically records on drop
        });
    });

    // Benchmark timer with bytes
    group.bench_function("timer_with_bytes", |b| {
        b.iter(|| {
            let mut timer = Timer::start("benchmark_op_bytes");
            timer.set_bytes(1024);
            std::thread::sleep(Duration::from_micros(1));
            timer.stop();
        });
    });

    group.finish();
}

fn bench_record_bytes(c: &mut Criterion) {
    let mut group = c.benchmark_group("record_bytes");
    let metrics = get_global_metrics();

    metrics.clear();

    // Benchmark bytes recording
    group.bench_function("record_bytes", |b| {
        b.iter(|| {
            metrics.record_bytes("file_op", 1024 * 1024);
            black_box(());
        });
    });

    // Benchmark with timing and bytes
    group.bench_function("record_timing_and_bytes", |b| {
        b.iter(|| {
            metrics.record_timing("file_op", Duration::from_millis(10));
            black_box(());
            metrics.record_bytes("file_op", 1024 * 1024);
            black_box(());
        });
    });

    group.finish();
}

fn bench_get_operations(c: &mut Criterion) {
    let mut group = c.benchmark_group("get_operations");
    let metrics = get_global_metrics();

    // Create operations with different counts
    for op_count in [10, 100, 1000] {
        metrics.clear();

        // Create operations
        for i in 0..op_count {
            let op_name = format!("operation_{}", i);
            metrics.record_timing(&op_name, Duration::from_micros(100));
        }

        group.bench_with_input(
            BenchmarkId::new("get_all_operations", op_count),
            &op_count,
            |b, _| {
                b.iter(|| {
                    black_box(metrics.get_operations());
                });
            },
        );
    }

    group.finish();
}

fn bench_throughput_calculation(c: &mut Criterion) {
    let mut group = c.benchmark_group("throughput");
    let metrics = get_global_metrics();

    metrics.clear();

    // Record some operations with bytes
    for i in 0..100 {
        metrics.record_timing("throughput_op", Duration::from_millis(10));
        metrics.record_bytes("throughput_op", (i + 1) * 1024 * 1024);
    }

    group.bench_function("calculate_throughput", |b| {
        b.iter(|| {
            if let Some(stats) = metrics.get_stats("throughput_op") {
                black_box(stats.throughput());
            }
        });
    });

    group.finish();
}

fn bench_concurrent_recording(c: &mut Criterion) {
    let mut group = c.benchmark_group("concurrent");
    let metrics = get_global_metrics();

    metrics.clear();

    // Benchmark concurrent access (tests atomic operations)
    group.bench_function("concurrent_record_10_threads", |b| {
        b.iter(|| {
            let handles: Vec<_> = (0..10)
                .map(|thread_id| {
                    let metrics = metrics.clone();
                    std::thread::spawn(move || {
                        for i in 0..100 {
                            let duration = Duration::from_micros(100 + (i % 100));
                            metrics.record_timing(&format!("thread_{}_op", thread_id), duration);
                        }
                    })
                })
                .collect();

            for handle in handles {
                handle.join().unwrap();
            }
        });
    });

    group.finish();
}

fn bench_memory_efficiency(c: &mut Criterion) {
    let mut group = c.benchmark_group("memory_efficiency");
    let metrics = get_global_metrics();

    // This benchmark validates O(1) memory usage
    // With rolling stats, memory should remain constant regardless of record count

    for record_count in [1000, 10000, 100000] {
        metrics.clear();

        group.bench_with_input(
            BenchmarkId::new("constant_memory", record_count),
            &record_count,
            |b, &count| {
                b.iter(|| {
                    for i in 0..count {
                        let duration = Duration::from_micros(100 + (i as u64 % 100));
                        metrics.record_timing("memory_test", duration);
                        black_box(());
                    }
                    // Stats should be instant (O(1)) regardless of record count
                    black_box(metrics.get_stats("memory_test"));
                });
            },
        );
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_record_timing,
    bench_get_stats,
    bench_timer,
    bench_record_bytes,
    bench_get_operations,
    bench_throughput_calculation,
    bench_concurrent_recording,
    bench_memory_efficiency
);
criterion_main!(benches);
