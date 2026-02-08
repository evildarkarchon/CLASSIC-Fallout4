//! GIL Release Audit Benchmarks - YAML operations
//!
//! These benchmarks measure pure Rust compute time for YAML-related
//! operations to establish baselines for GIL release decisions.
//!
//! The benchmarks simulate the types of YAML content processed by CLASSIC
//! (configuration files, mod databases, etc.).
//!
//! # Running Benchmarks
//!
//! ```bash
//! # Quick mode (development)
//! BENCH_MODE=quick cargo bench --bench gil_benchmarks -p classic-yaml-py
//!
//! # Thorough mode (baseline establishment)
//! BENCH_MODE=thorough cargo bench --bench gil_benchmarks -p classic-yaml-py
//! ```

use criterion::{BenchmarkId, Criterion, criterion_group, criterion_main};
use std::collections::HashMap;
use std::hint::black_box;

// Import shared benchmark configuration from workspace benches/common/
#[path = "../../../benches/common/mod.rs"]
mod common;

/// Generate YAML-like content for benchmarking (string operations)
fn generate_yaml_content(lines: usize) -> String {
    let mut content = String::with_capacity(lines * 50);
    for i in 0..lines {
        if i % 10 == 0 {
            content.push_str(&format!("section_{}:\n", i / 10));
        } else {
            content.push_str(&format!("  key_{}: value_{}\n", i, i));
        }
    }
    content
}

/// Generate nested YAML-like structure
#[allow(dead_code)]
fn generate_nested_yaml(depth: usize, breadth: usize) -> String {
    fn generate_level(current_depth: usize, max_depth: usize, breadth: usize) -> String {
        if current_depth >= max_depth {
            return "value".to_string();
        }
        let indent = "  ".repeat(current_depth);
        let mut result = String::new();
        for i in 0..breadth {
            result.push_str(&format!("{}key_{}:\n", indent, i));
            result.push_str(&generate_level(current_depth + 1, max_depth, breadth));
        }
        result
    }
    generate_level(0, depth, breadth)
}

/// Benchmark YAML string parsing simulation
fn bench_yaml_parsing(c: &mut Criterion) {
    let mut group = c.benchmark_group("yaml_parsing");

    for line_count in [100, 1000, 5000] {
        let content = generate_yaml_content(line_count);

        group.bench_with_input(
            BenchmarkId::new("line_parsing", line_count),
            &content,
            |b, content| {
                b.iter(|| {
                    // Simulate YAML line parsing (key-value extraction)
                    let mut map = HashMap::new();
                    let mut current_section = String::new();
                    for line in content.lines() {
                        let trimmed = line.trim();
                        if trimmed.ends_with(':') && !trimmed.starts_with(' ') {
                            current_section = trimmed.trim_end_matches(':').to_string();
                        } else if let Some(idx) = trimmed.find(':') {
                            let key = format!("{}.{}", current_section, &trimmed[..idx].trim());
                            let value = trimmed[idx + 1..].trim().to_string();
                            map.insert(key, value);
                        }
                    }
                    black_box(map)
                })
            },
        );
    }

    group.finish();
}

/// Benchmark YAML serialization simulation
fn bench_yaml_serialization(c: &mut Criterion) {
    let mut group = c.benchmark_group("yaml_serialization");

    for size in [50, 200, 1000] {
        let data: HashMap<String, String> = (0..size)
            .map(|i| (format!("key_{}", i), format!("value_{}", i)))
            .collect();

        group.bench_with_input(BenchmarkId::new("serialize_map", size), &data, |b, data| {
            b.iter(|| {
                // Simulate YAML serialization
                let mut output = String::with_capacity(size * 30);
                for (key, value) in data {
                    output.push_str(key);
                    output.push_str(": ");
                    output.push_str(value);
                    output.push('\n');
                }
                black_box(output)
            })
        });
    }

    group.finish();
}

/// Benchmark nested structure traversal
fn bench_nested_traversal(c: &mut Criterion) {
    let mut group = c.benchmark_group("yaml_nested_traversal");

    // Benchmark dot-notation path traversal simulation
    let paths = vec![
        "level_3.level_2.level_1.key_0",
        "level_3.level_2.level_1.key_5",
        "level_3.level_2.key_3",
        "section.subsection.value",
        "game.mods.core.plugin_name",
    ];

    // Create a nested HashMap for path lookups
    let nested_data: HashMap<String, HashMap<String, String>> = {
        let mut outer = HashMap::new();
        for i in 0..10 {
            let mut inner = HashMap::new();
            for j in 0..20 {
                inner.insert(format!("key_{}", j), format!("value_{}_{}", i, j));
            }
            outer.insert(format!("section_{}", i), inner);
        }
        outer
    };

    group.bench_function("path_parsing", |b| {
        b.iter(|| {
            // Simulate dot notation path parsing
            for path in &paths {
                let parts: Vec<&str> = path.split('.').collect();
                black_box(parts);
            }
        })
    });

    group.bench_function("nested_lookup", |b| {
        b.iter(|| {
            // Simulate nested lookup
            let mut found = 0;
            for section in nested_data.values() {
                for _value in section.values() {
                    found += 1;
                }
            }
            black_box(found)
        })
    });

    group.finish();
}

/// Benchmark key lookup operations
fn bench_key_lookup(c: &mut Criterion) {
    let mut group = c.benchmark_group("yaml_key_lookup");

    for size in [100, 500, 2000] {
        let data: HashMap<String, String> = (0..size)
            .map(|i| (format!("key_{}", i), format!("value_{}", i)))
            .collect();

        let lookup_keys: Vec<String> = (0..100)
            .map(|i| format!("key_{}", i * (size / 100)))
            .collect();

        group.bench_with_input(
            BenchmarkId::new("lookup_100_keys", size),
            &(data, lookup_keys),
            |b, (data, keys)| {
                b.iter(|| {
                    let found: Vec<Option<&String>> = keys.iter().map(|k| data.get(k)).collect();
                    black_box(found)
                })
            },
        );
    }

    group.finish();
}

/// Benchmark string interning simulation (for repeated YAML values)
fn bench_string_interning(c: &mut Criterion) {
    let mut group = c.benchmark_group("yaml_string_interning");

    // Simulate repeated strings (common in YAML with mod descriptions)
    let repeated_strings: Vec<String> = (0..1000)
        .map(|i| {
            // Create strings with some repetition
            let base = i % 50;
            format!(
                "Common mod description text {} with some variation {}",
                base, i
            )
        })
        .collect();

    group.bench_function("intern_strings", |b| {
        b.iter(|| {
            // Simulate string interning with a simple dedup
            let mut seen: HashMap<&str, usize> = HashMap::new();
            for s in &repeated_strings {
                *seen.entry(s.as_str()).or_insert(0) += 1;
            }
            black_box(seen.len())
        })
    });

    group.finish();
}

criterion_group! {
    name = benches;
    config = common::config::configure_criterion();
    targets =
        bench_yaml_parsing,
        bench_yaml_serialization,
        bench_nested_traversal,
        bench_key_lookup,
        bench_string_interning
}
criterion_main!(benches);
