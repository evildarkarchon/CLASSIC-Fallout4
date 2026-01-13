//! Benchmarks for path handling optimizations

#![allow(missing_docs)]

use classic_shared_core::path_core::PathHandler;
use criterion::{BenchmarkId, Criterion, criterion_group, criterion_main};
use std::env;
use std::hint::black_box;

fn bench_normalize_path(c: &mut Criterion) {
    let mut group = c.benchmark_group("normalize_path");

    // Get current directory for realistic path
    let current_dir = env::current_dir().expect("Failed to get current directory");
    let test_path = current_dir
        .join("test_file.txt")
        .to_string_lossy()
        .to_string();

    // Unbounded cache (original behavior)
    let handler_unbounded = PathHandler::new(300);
    group.bench_function("cache_miss_unbounded", |b| {
        b.iter(|| {
            black_box(handler_unbounded.normalize_path(&test_path).ok());
        });
    });

    group.bench_function("cache_hit_unbounded", |b| {
        // Prime cache
        handler_unbounded.normalize_path(&test_path).ok();
        b.iter(|| {
            black_box(handler_unbounded.normalize_path(&test_path).ok());
        });
    });

    // Bounded cache with LRU eviction
    let handler_bounded = PathHandler::new_with_limits(300, 1000);
    group.bench_function("cache_miss_bounded", |b| {
        b.iter(|| {
            black_box(handler_bounded.normalize_path(&test_path).ok());
        });
    });

    group.bench_function("cache_hit_bounded", |b| {
        // Prime cache
        handler_bounded.normalize_path(&test_path).ok();
        b.iter(|| {
            black_box(handler_bounded.normalize_path(&test_path).ok());
        });
    });

    group.finish();
}

fn bench_cache_eviction(c: &mut Criterion) {
    let mut group = c.benchmark_group("cache_eviction");

    // Benchmark LRU eviction overhead
    for cache_size in [100, 1000, 10000] {
        let handler = PathHandler::new_with_limits(300, cache_size);

        group.bench_with_input(
            BenchmarkId::new("fill_cache", cache_size),
            &cache_size,
            |b, &size| {
                b.iter(|| {
                    for i in 0..size {
                        let path = format!("test_path_{}.txt", i);
                        black_box(handler.normalize_path(&path).ok());
                    }
                });
            },
        );

        // Fill cache to capacity
        for i in 0..cache_size {
            let path = format!("test_path_{}.txt", i);
            handler.normalize_path(&path).ok();
        }

        group.bench_with_input(
            BenchmarkId::new("eviction_trigger", cache_size),
            &cache_size,
            |b, _| {
                let mut counter = cache_size;
                b.iter(|| {
                    let path = format!("new_path_{}.txt", counter);
                    counter += 1;
                    black_box(handler.normalize_path(&path).ok());
                });
            },
        );
    }

    group.finish();
}

fn bench_validate_paths_batch(c: &mut Criterion) {
    let mut group = c.benchmark_group("validate_paths_batch");
    let handler = PathHandler::new(300);

    let current_dir = env::current_dir().expect("Failed to get current directory");

    for size in [10, 100, 1000] {
        let paths: Vec<String> = (0..size)
            .map(|i| {
                current_dir
                    .join(format!("test_file_{}.txt", i))
                    .to_string_lossy()
                    .to_string()
            })
            .collect();

        group.bench_with_input(
            BenchmarkId::new("validate_batch", size),
            &paths,
            |b, paths| {
                b.iter(|| {
                    black_box(handler.validate_paths_batch(paths));
                });
            },
        );
    }

    group.finish();
}

fn bench_cache_metrics(c: &mut Criterion) {
    let mut group = c.benchmark_group("cache_metrics");
    let handler = PathHandler::new_with_limits(300, 1000);

    // Fill cache with some entries
    for i in 0..500 {
        let path = format!("test_path_{}.txt", i);
        handler.normalize_path(&path).ok();
    }

    // Access some entries to generate hits
    for i in 0..250 {
        let path = format!("test_path_{}.txt", i);
        handler.normalize_path(&path).ok();
    }

    group.bench_function("get_metrics", |b| {
        b.iter(|| {
            black_box(handler.cache_metrics());
        });
    });

    group.bench_function("get_stats", |b| {
        b.iter(|| {
            black_box(handler.cache_stats());
        });
    });

    group.finish();
}

fn bench_path_operations(c: &mut Criterion) {
    let mut group = c.benchmark_group("path_operations");
    let handler = PathHandler::new(300);

    let test_path = if cfg!(windows) {
        "C:\\Users\\test\\Documents\\project\\src\\main.rs"
    } else {
        "/home/test/Documents/project/src/main.rs"
    };

    group.bench_function("split_path", |b| {
        b.iter(|| {
            black_box(handler.split_path(test_path));
        });
    });

    group.bench_function("get_filename", |b| {
        b.iter(|| {
            black_box(handler.get_filename(test_path));
        });
    });

    group.bench_function("get_extension", |b| {
        b.iter(|| {
            black_box(handler.get_extension(test_path));
        });
    });

    group.bench_function("get_parent", |b| {
        b.iter(|| {
            black_box(handler.get_parent(test_path));
        });
    });

    group.bench_function("is_absolute", |b| {
        b.iter(|| {
            black_box(handler.is_absolute(test_path));
        });
    });

    // Benchmark common prefix
    let paths = vec![
        test_path.to_string(),
        if cfg!(windows) {
            "C:\\Users\\test\\Documents\\project\\src\\lib.rs".to_string()
        } else {
            "/home/test/Documents/project/src/lib.rs".to_string()
        },
        if cfg!(windows) {
            "C:\\Users\\test\\Documents\\project\\src\\utils.rs".to_string()
        } else {
            "/home/test/Documents/project/src/utils.rs".to_string()
        },
    ];

    group.bench_function("common_prefix", |b| {
        b.iter(|| {
            black_box(handler.common_prefix(&paths));
        });
    });

    group.finish();
}

criterion_group!(
    benches,
    bench_normalize_path,
    bench_cache_eviction,
    bench_validate_paths_batch,
    bench_cache_metrics,
    bench_path_operations
);
criterion_main!(benches);
