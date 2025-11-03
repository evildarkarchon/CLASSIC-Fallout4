//! Benchmarks for string processing optimizations

#![allow(missing_docs)]

use classic_shared_core::strings_core::{StringOperation, StringProcessor};
use criterion::{BenchmarkId, Criterion, black_box, criterion_group, criterion_main};

fn bench_string_interning(c: &mut Criterion) {
    let mut group = c.benchmark_group("string_interning");
    let processor = StringProcessor::new();

    // Benchmark cache hits (after ThreadedRodeo optimization)
    group.bench_function("intern_cache_hit", |b| {
        processor.intern("test_string"); // Prime cache
        b.iter(|| {
            black_box(processor.intern("test_string"));
        });
    });

    // Benchmark cache misses
    group.bench_function("intern_cache_miss", |b| {
        let mut counter = 0;
        b.iter(|| {
            let s = format!("unique_string_{}", counter);
            counter += 1;
            black_box(processor.intern(&s));
        });
    });

    // Benchmark bulk interning
    let test_strings: Vec<String> = (0..1000).map(|i| format!("bulk_string_{}", i)).collect();
    group.bench_function("intern_bulk_1000", |b| {
        b.iter(|| {
            for s in &test_strings {
                black_box(processor.intern(s));
            }
        });
    });

    group.finish();
}

fn bench_common_prefix(c: &mut Criterion) {
    let mut group = c.benchmark_group("common_prefix");
    let processor = StringProcessor::new();

    // Short strings (O(n) optimization should shine)
    let short_strings: Vec<&str> = vec!["test_abc", "test_abd", "test_abe"];
    group.bench_function("short_strings", |b| {
        b.iter(|| {
            black_box(processor.common_prefix(&short_strings));
        });
    });

    // Long strings (O(n) vs O(n²) - huge difference)
    let long_strings: Vec<&str> = vec![
        "this_is_a_very_long_string_prefix_with_many_characters_abc",
        "this_is_a_very_long_string_prefix_with_many_characters_abd",
        "this_is_a_very_long_string_prefix_with_many_characters_abe",
    ];
    group.bench_function("long_strings", |b| {
        b.iter(|| {
            black_box(processor.common_prefix(&long_strings));
        });
    });

    // Very long strings (1000 chars - O(n²) would be 1M iterations!)
    let very_long_prefix = "x".repeat(900);
    let very_long_strings: Vec<String> = vec![
        format!("{}abc", very_long_prefix),
        format!("{}abd", very_long_prefix),
        format!("{}abe", very_long_prefix),
    ];
    let very_long_refs: Vec<&str> = very_long_strings.iter().map(|s| s.as_str()).collect();
    group.bench_function("very_long_strings_1000_chars", |b| {
        b.iter(|| {
            black_box(processor.common_prefix(&very_long_refs));
        });
    });

    group.finish();
}

fn bench_batch_operations(c: &mut Criterion) {
    let mut group = c.benchmark_group("batch_operations");
    let processor = StringProcessor::new();

    for size in [10, 100, 1000] {
        let batch: Vec<&str> = (0..size).map(|_| "  whitespace trimming test  ").collect();

        group.bench_with_input(
            BenchmarkId::new("process_batch_trim", size),
            &batch,
            |b, batch| {
                b.iter(|| {
                    black_box(processor.process_batch(batch, StringOperation::Trim));
                });
            },
        );

        group.bench_with_input(
            BenchmarkId::new("process_batch_upper", size),
            &batch,
            |b, batch| {
                b.iter(|| {
                    black_box(processor.process_batch(batch, StringOperation::Upper));
                });
            },
        );
    }

    group.finish();
}

fn bench_normalize(c: &mut Criterion) {
    let mut group = c.benchmark_group("normalize");
    let processor = StringProcessor::new();

    // Test normalize with various input patterns
    let short_text = "  Hello   World  ";
    group.bench_function("short_text", |b| {
        b.iter(|| {
            black_box(processor.normalize_string(short_text));
        });
    });

    let long_text = "  This   is   a   much   longer   text   with   many   spaces   and   words  ";
    group.bench_function("long_text", |b| {
        b.iter(|| {
            black_box(processor.normalize_string(long_text));
        });
    });

    group.finish();
}

fn bench_split_lines(c: &mut Criterion) {
    let mut group = c.benchmark_group("split_lines");
    let processor = StringProcessor::new();

    // Small text (10 lines)
    let small_text = (0..10)
        .map(|i| format!("Line {}", i))
        .collect::<Vec<_>>()
        .join("\n");

    group.bench_function("10_lines", |b| {
        b.iter(|| {
            black_box(processor.split_lines(&small_text));
        });
    });

    // Large text (1000 lines)
    let large_text = (0..1000)
        .map(|i| format!("Line {}", i))
        .collect::<Vec<_>>()
        .join("\n");

    group.bench_function("1000_lines", |b| {
        b.iter(|| {
            black_box(processor.split_lines(&large_text));
        });
    });

    group.finish();
}

criterion_group!(
    benches,
    bench_string_interning,
    bench_common_prefix,
    bench_batch_operations,
    bench_normalize,
    bench_split_lines
);
criterion_main!(benches);
