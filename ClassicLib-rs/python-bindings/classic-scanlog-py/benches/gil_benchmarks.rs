#![allow(missing_docs)]
//! GIL Release Audit Benchmarks - Phase 12
//!
//! These benchmarks measure pure Rust compute time to establish baselines
//! for GIL release decisions. FFI overhead is measured separately in Python tests.
//!
//! The benchmarks use the same data patterns and sizes as production workloads
//! to ensure timing measurements are representative.
//!
//! # Running Benchmarks
//!
//! ```bash
//! # Quick mode (development)
//! BENCH_MODE=quick cargo bench --bench gil_benchmarks -p classic-scanlog-py
//!
//! # Thorough mode (baseline establishment)
//! BENCH_MODE=thorough cargo bench --bench gil_benchmarks -p classic-scanlog-py
//! ```

use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion};
use std::collections::HashMap;
use std::hint::black_box;

// Import shared benchmark configuration from workspace benches/common/
#[path = "../../../../benches/common/mod.rs"]
mod common;

/// Generate realistic crash log lines for benchmarking
fn generate_test_log_lines(count: usize) -> Vec<String> {
    (0..count)
        .map(|i| {
            if i % 10 == 0 {
                format!("FORMS: Form ID: {:08X} (Plugin.esp)", i)
            } else if i % 5 == 0 {
                format!("[00] Plugin{}.esp", i)
            } else {
                format!("  0x{:08X} - Function+0x{:X}", 0x14000000 + i, i * 16)
            }
        })
        .collect()
}

/// Generate plugin dictionary for benchmarking
fn generate_plugins(count: usize) -> HashMap<String, String> {
    (0..count)
        .map(|i| (format!("Plugin{}.esp", i), format!("{:02X}", i % 256)))
        .collect()
}

/// Benchmark log line processing (simulates parse_segments)
fn bench_log_parsing(c: &mut Criterion) {
    let mut group = c.benchmark_group("scanlog_parsing");

    for size in [100, 1000, 10000] {
        let test_lines = generate_test_log_lines(size);

        group.bench_with_input(
            BenchmarkId::new("line_count", size),
            &test_lines,
            |b, lines| {
                b.iter(|| {
                    // Simulate segment boundary detection
                    let mut segment_count = 0;
                    let mut in_segment = false;
                    for line in lines.iter() {
                        if line.contains("FORMS:") {
                            in_segment = true;
                            segment_count += 1;
                        } else if line.is_empty() {
                            in_segment = false;
                        }
                        black_box(in_segment);
                    }
                    black_box(segment_count)
                })
            },
        );
    }

    group.finish();
}

/// Benchmark FormID extraction (regex-like pattern matching)
fn bench_formid_extraction(c: &mut Criterion) {
    let mut group = c.benchmark_group("formid_extraction");

    for size in [100, 1000, 5000] {
        let test_lines = generate_test_log_lines(size);

        group.bench_with_input(
            BenchmarkId::new("extract_formids", size),
            &test_lines,
            |b, lines| {
                b.iter(|| {
                    // Simulate FormID extraction pattern matching
                    let formids: Vec<&str> = lines
                        .iter()
                        .filter(|line| line.contains("Form ID:"))
                        .filter_map(|line| line.split("Form ID:").nth(1))
                        .map(|s| s.split_whitespace().next().unwrap_or(""))
                        .collect();
                    black_box(formids)
                })
            },
        );
    }

    group.finish();
}

/// Benchmark plugin matching
fn bench_plugin_matching(c: &mut Criterion) {
    let mut group = c.benchmark_group("plugin_matching");

    let test_lines = generate_test_log_lines(1000);
    let plugins_small = generate_plugins(50);
    let plugins_large = generate_plugins(500);

    group.bench_function("match_50_plugins", |b| {
        b.iter(|| {
            // Simulate plugin matching
            let matches: Vec<&String> = test_lines
                .iter()
                .filter(|line| {
                    plugins_small
                        .keys()
                        .any(|plugin| line.to_lowercase().contains(&plugin.to_lowercase()))
                })
                .collect();
            black_box(matches)
        })
    });

    group.bench_function("match_500_plugins", |b| {
        b.iter(|| {
            let matches: Vec<&String> = test_lines
                .iter()
                .filter(|line| {
                    plugins_large
                        .keys()
                        .any(|plugin| line.to_lowercase().contains(&plugin.to_lowercase()))
                })
                .collect();
            black_box(matches)
        })
    });

    group.finish();
}

/// Benchmark mod detection pattern matching
fn bench_mod_detection(c: &mut Criterion) {
    let mut group = c.benchmark_group("mod_detection");

    // Simulate YAML patterns
    let patterns: Vec<(String, String)> = (0..100)
        .map(|i| {
            (
                format!("pattern{}", i),
                format!("Description for pattern {}", i),
            )
        })
        .collect();

    let plugins = generate_plugins(200);

    group.bench_function("detect_100_patterns", |b| {
        b.iter(|| {
            // Simulate mod detection matching
            let mut matches = Vec::new();
            for (pattern, desc) in &patterns {
                for plugin in plugins.keys() {
                    if plugin.to_lowercase().contains(&pattern.to_lowercase()) {
                        matches.push((pattern.clone(), desc.clone()));
                        break;
                    }
                }
            }
            black_box(matches)
        })
    });

    group.finish();
}

/// Benchmark suspect pattern scanning
fn bench_suspect_scanning(c: &mut Criterion) {
    let mut group = c.benchmark_group("suspect_scanning");

    // Simulate suspect patterns
    let error_patterns: Vec<String> = (0..50)
        .map(|i| format!("Error pattern {} detected", i))
        .collect();

    let test_content = generate_test_log_lines(5000).join("\n");

    group.bench_function("scan_50_patterns", |b| {
        b.iter(|| {
            // Simulate suspect pattern scanning
            let mut found = Vec::new();
            let content_lower = test_content.to_lowercase();
            for pattern in &error_patterns {
                if content_lower.contains(&pattern.to_lowercase()) {
                    found.push(pattern.clone());
                }
            }
            black_box(found)
        })
    });

    group.finish();
}

criterion_group! {
    name = benches;
    config = common::config::configure_criterion();
    targets =
        bench_log_parsing,
        bench_formid_extraction,
        bench_plugin_matching,
        bench_mod_detection,
        bench_suspect_scanning
}
criterion_main!(benches);
