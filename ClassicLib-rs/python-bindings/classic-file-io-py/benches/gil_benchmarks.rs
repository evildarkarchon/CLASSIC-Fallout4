#![allow(missing_docs)]
//! GIL Release Audit Benchmarks - File I/O operations
//!
//! These benchmarks measure pure Rust compute time for file I/O related
//! operations to establish baselines for GIL release decisions.
//!
//! Note: Actual file I/O timing is highly variable and depends on disk speed,
//! caching, etc. These benchmarks focus on the compute-bound portions.
//!
//! # Running Benchmarks
//!
//! ```bash
//! # Quick mode (development)
//! BENCH_MODE=quick cargo bench --bench gil_benchmarks -p classic-file-io-py
//!
//! # Thorough mode (baseline establishment)
//! BENCH_MODE=thorough cargo bench --bench gil_benchmarks -p classic-file-io-py
//! ```

use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion};
use std::hint::black_box;
use std::path::PathBuf;

// Import shared benchmark configuration from workspace benches/common/
#[path = "../../../../benches/common/mod.rs"]
mod common;

/// Generate test file paths for benchmarking
fn generate_test_paths(count: usize) -> Vec<PathBuf> {
    (0..count)
        .map(|i| PathBuf::from(format!("path/to/file_{}.txt", i)))
        .collect()
}

/// Benchmark path filtering operations (simulates walk_directory filtering)
fn bench_path_filtering(c: &mut Criterion) {
    let mut group = c.benchmark_group("file_io_path_filtering");

    for size in [100, 1000, 10000] {
        // Generate diverse file paths
        let paths: Vec<PathBuf> = (0..size)
            .map(|i| {
                let ext = match i % 5 {
                    0 => "txt",
                    1 => "dds",
                    2 => "nif",
                    3 => "esp",
                    _ => "ba2",
                };
                PathBuf::from(format!("data/textures/file_{}.{}", i, ext))
            })
            .collect();

        group.bench_with_input(
            BenchmarkId::new("filter_by_extension", size),
            &paths,
            |b, paths| {
                b.iter(|| {
                    let dds_files: Vec<&PathBuf> = paths
                        .iter()
                        .filter(|p| {
                            p.extension()
                                .is_some_and(|ext| ext.eq_ignore_ascii_case("dds"))
                        })
                        .collect();
                    black_box(dds_files)
                })
            },
        );

        group.bench_with_input(
            BenchmarkId::new("filter_by_pattern", size),
            &paths,
            |b, paths| {
                b.iter(|| {
                    let matching: Vec<&PathBuf> = paths
                        .iter()
                        .filter(|p| p.to_string_lossy().to_lowercase().contains("textures"))
                        .collect();
                    black_box(matching)
                })
            },
        );
    }

    group.finish();
}

/// Benchmark path processing (normalization, joining, etc.)
fn bench_path_processing(c: &mut Criterion) {
    let mut group = c.benchmark_group("file_io_path_processing");

    let base_paths = generate_test_paths(1000);

    group.bench_function("normalize_paths", |b| {
        b.iter(|| {
            let normalized: Vec<String> = base_paths
                .iter()
                .map(|p| p.to_string_lossy().replace('\\', "/").to_lowercase())
                .collect();
            black_box(normalized)
        })
    });

    group.bench_function("extract_filenames", |b| {
        b.iter(|| {
            let filenames: Vec<String> = base_paths
                .iter()
                .filter_map(|p| p.file_name())
                .map(|n| n.to_string_lossy().to_string())
                .collect();
            black_box(filenames)
        })
    });

    group.finish();
}

/// Benchmark DDS header parsing simulation
fn bench_dds_header_parsing(c: &mut Criterion) {
    let mut group = c.benchmark_group("file_io_dds_parsing");

    // Simulate DDS header bytes (128 bytes is typical DDS header size)
    let header_bytes: Vec<u8> = {
        let mut bytes = vec![0u8; 128];
        // DDS magic number
        bytes[0..4].copy_from_slice(b"DDS ");
        // Size field (124 for standard DDS)
        bytes[4..8].copy_from_slice(&124u32.to_le_bytes());
        // Flags
        bytes[8..12].copy_from_slice(&0x1007u32.to_le_bytes());
        // Height (1024)
        bytes[12..16].copy_from_slice(&1024u32.to_le_bytes());
        // Width (2048)
        bytes[16..20].copy_from_slice(&2048u32.to_le_bytes());
        bytes
    };

    for count in [10, 100, 1000] {
        let headers: Vec<Vec<u8>> = (0..count).map(|_| header_bytes.clone()).collect();

        group.bench_with_input(
            BenchmarkId::new("parse_headers", count),
            &headers,
            |b, headers| {
                b.iter(|| {
                    let dimensions: Vec<(u32, u32)> = headers
                        .iter()
                        .filter_map(|h| {
                            if h.len() >= 20 && &h[0..4] == b"DDS " {
                                let height = u32::from_le_bytes([h[12], h[13], h[14], h[15]]);
                                let width = u32::from_le_bytes([h[16], h[17], h[18], h[19]]);
                                Some((width, height))
                            } else {
                                None
                            }
                        })
                        .collect();
                    black_box(dimensions)
                })
            },
        );
    }

    group.finish();
}

/// Benchmark batch result aggregation
fn bench_batch_aggregation(c: &mut Criterion) {
    let mut group = c.benchmark_group("file_io_batch_aggregation");

    // Simulate batch read results
    let results: Vec<(PathBuf, Result<String, String>)> = (0..1000)
        .map(|i| {
            let path = PathBuf::from(format!("file_{}.txt", i));
            let result = if i % 10 == 0 {
                Err(format!("Error reading file {}", i))
            } else {
                Ok(format!("Content of file {}", i))
            };
            (path, result)
        })
        .collect();

    group.bench_function("aggregate_results", |b| {
        b.iter(|| {
            let mut successes = Vec::new();
            let mut failures = Vec::new();
            for (path, result) in &results {
                match result {
                    Ok(content) => successes.push((path.clone(), content.clone())),
                    Err(err) => failures.push((path.clone(), err.clone())),
                }
            }
            black_box((successes.len(), failures.len()))
        })
    });

    group.finish();
}

criterion_group! {
    name = benches;
    config = common::config::configure_criterion();
    targets =
        bench_path_filtering,
        bench_path_processing,
        bench_dds_header_parsing,
        bench_batch_aggregation
}
criterion_main!(benches);
