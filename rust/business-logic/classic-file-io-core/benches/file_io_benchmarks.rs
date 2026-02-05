//! Criterion benchmarks for classic-file-io-core operations.
//!
//! This module benchmarks encoding detection, path operations, and file I/O
//! using synthetic data for controlled measurements.
//!
//! # Running Benchmarks
//!
//! ```bash
//! # Quick mode (development)
//! BENCH_MODE=quick cargo bench --bench file_io_benchmarks
//!
//! # Thorough mode (baseline establishment)
//! BENCH_MODE=thorough cargo bench --bench file_io_benchmarks
//!
//! # Verify benchmark compiles
//! cargo bench --bench file_io_benchmarks -- --test
//! ```

use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use std::path::PathBuf;
use tempfile::TempDir;

// Import shared benchmark configuration from workspace benches/common/
#[path = "../../../benches/common/mod.rs"]
mod common;

use classic_file_io_core::{EncodingDetector, FileIOCore};

// =============================================================================
// Synthetic Data Generation
// =============================================================================

/// Generates UTF-8 content of specified size (bytes).
fn generate_utf8_content(size: usize) -> Vec<u8> {
    // Create UTF-8 content with realistic crash log patterns
    let line = "Fallout 4 v1.10.163 - Buffout 4 v1.26.2 - [RSP+50] 0x7FF123456789\n";
    let mut content = Vec::with_capacity(size);

    while content.len() < size {
        let remaining = size - content.len();
        if remaining >= line.len() {
            content.extend_from_slice(line.as_bytes());
        } else {
            content.extend_from_slice(&line.as_bytes()[..remaining]);
        }
    }

    content
}

/// Generates UTF-8 content with BOM of specified size.
fn generate_utf8_bom_content(size: usize) -> Vec<u8> {
    let mut content = vec![0xEF, 0xBB, 0xBF]; // UTF-8 BOM
    let text = generate_utf8_content(size.saturating_sub(3));
    content.extend_from_slice(&text);
    content
}

/// Generates Windows-1252 content with invalid UTF-8 sequences.
fn generate_windows_1252_content(size: usize) -> Vec<u8> {
    // Windows-1252 bytes that are invalid UTF-8
    // 0x80 = Euro sign, 0x93/0x94 = smart quotes, 0x99 = trademark
    let mut content = Vec::with_capacity(size);
    let patterns: Vec<u8> = vec![
        0x80, b'E', b'u', b'r', b'o', b' ', // Euro sign
        0x93, b'H', b'e', b'l', b'l', b'o', 0x94, b' ', // Smart quotes
        b'B', b'r', b'a', b'n', b'd', 0x99, b' ', // Trademark
    ];

    while content.len() < size {
        let remaining = size - content.len();
        let pattern_len = patterns.len().min(remaining);
        content.extend_from_slice(&patterns[..pattern_len]);
    }

    content
}

/// Generates a list of file paths for filtering benchmarks.
fn generate_path_list(count: usize) -> Vec<PathBuf> {
    let extensions = [".esp", ".esm", ".esl", ".dds", ".nif", ".txt", ".log", ".ini"];
    let prefixes = ["Data", "Mods", "Plugins", "Textures", "Meshes", "Scripts"];

    (0..count)
        .map(|i| {
            let prefix = prefixes[i % prefixes.len()];
            let ext = extensions[i % extensions.len()];
            PathBuf::from(format!("{}/file_{}{}", prefix, i, ext))
        })
        .collect()
}

// =============================================================================
// Encoding Detection Benchmarks
// =============================================================================

fn encoding_detection_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("encoding_detection");

    let sizes = [
        (1024, "1kb"),
        (10 * 1024, "10kb"),
        (100 * 1024, "100kb"),
    ];

    // Benchmark UTF-8 detection (most common case)
    for (size, name) in sizes {
        let content = generate_utf8_content(size);
        group.throughput(Throughput::Bytes(content.len() as u64));

        group.bench_with_input(
            BenchmarkId::new("detect_utf8", name),
            &content,
            |b, content| {
                let detector = EncodingDetector::new();
                b.iter(|| detector.detect(content));
            },
        );
    }

    // Benchmark UTF-8 with BOM detection
    for (size, name) in sizes {
        let content = generate_utf8_bom_content(size);
        group.throughput(Throughput::Bytes(content.len() as u64));

        group.bench_with_input(
            BenchmarkId::new("detect_utf8_bom", name),
            &content,
            |b, content| {
                let detector = EncodingDetector::new();
                b.iter(|| detector.detect(content));
            },
        );
    }

    // Benchmark Windows-1252 detection (fallback case)
    for (size, name) in sizes {
        let content = generate_windows_1252_content(size);
        group.throughput(Throughput::Bytes(content.len() as u64));

        group.bench_with_input(
            BenchmarkId::new("detect_windows1252", name),
            &content,
            |b, content| {
                let detector = EncodingDetector::new();
                b.iter(|| detector.detect(content));
            },
        );
    }

    // Benchmark detect_name (returns String)
    let medium_content = generate_utf8_content(10 * 1024);
    group.bench_function("detect_name_utf8_10kb", |b| {
        let detector = EncodingDetector::new();
        b.iter(|| detector.detect_name(&medium_content));
    });

    group.finish();
}

// =============================================================================
// Path Filtering Benchmarks
// =============================================================================

fn path_filtering_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("path_filtering");

    let sizes = [(100, "100_paths"), (1000, "1000_paths"), (10000, "10000_paths")];

    for (count, name) in sizes {
        let paths = generate_path_list(count);

        // Filter by extension
        group.bench_with_input(
            BenchmarkId::new("filter_by_esp_extension", name),
            &paths,
            |b, paths| {
                b.iter(|| {
                    paths
                        .iter()
                        .filter(|p| {
                            p.extension()
                                .map(|ext| ext == "esp" || ext == "esm" || ext == "esl")
                                .unwrap_or(false)
                        })
                        .count()
                });
            },
        );

        // Filter by prefix/directory
        group.bench_with_input(
            BenchmarkId::new("filter_by_data_prefix", name),
            &paths,
            |b, paths| {
                b.iter(|| {
                    paths
                        .iter()
                        .filter(|p| p.starts_with("Data"))
                        .count()
                });
            },
        );

        // Count unique extensions
        group.bench_with_input(
            BenchmarkId::new("count_unique_extensions", name),
            &paths,
            |b, paths| {
                b.iter(|| {
                    let mut extensions: Vec<_> = paths
                        .iter()
                        .filter_map(|p| p.extension())
                        .collect();
                    extensions.sort();
                    extensions.dedup();
                    extensions.len()
                });
            },
        );
    }

    group.finish();
}

// =============================================================================
// FileIOCore Creation and Cache Benchmarks
// =============================================================================

fn file_io_core_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("file_io_core");

    // Benchmark FileIOCore creation
    group.bench_function("creation_default", |b| {
        b.iter(|| FileIOCore::default());
    });

    group.bench_function("creation_custom_cache", |b| {
        b.iter(|| FileIOCore::new("utf-8", "ignore", 256, 16));
    });

    // Benchmark cache operations with temp files
    let temp_dir = TempDir::new().expect("create temp dir");

    // Create test files of different sizes
    let small_content = generate_utf8_content(1024);
    let medium_content = generate_utf8_content(10 * 1024);

    let small_path = temp_dir.path().join("small.txt");
    let medium_path = temp_dir.path().join("medium.txt");

    std::fs::write(&small_path, &small_content).expect("write small file");
    std::fs::write(&medium_path, &medium_content).expect("write medium file");

    // Benchmark read file (async - uses tokio runtime)
    group.bench_function("read_file_1kb_cached", |b| {
        let file_io = FileIOCore::default();
        let rt = tokio::runtime::Runtime::new().unwrap();

        // Prime the cache
        rt.block_on(async {
            let _ = file_io.read_file(&small_path).await;
        });

        b.iter(|| {
            rt.block_on(async { file_io.read_file(&small_path).await.ok() })
        });
    });

    group.bench_function("read_file_10kb_cached", |b| {
        let file_io = FileIOCore::default();
        let rt = tokio::runtime::Runtime::new().unwrap();

        // Prime the cache
        rt.block_on(async {
            let _ = file_io.read_file(&medium_path).await;
        });

        b.iter(|| {
            rt.block_on(async { file_io.read_file(&medium_path).await.ok() })
        });
    });

    group.finish();
}

// =============================================================================
// Log Collection Pattern Benchmarks
// =============================================================================

fn log_pattern_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("log_patterns");

    // Test log filename matching patterns
    let log_filenames = vec![
        "crash-2024-01-15-10-30-00.log".to_string(),
        "crash-1234567890.log".to_string(),
        "crash-autoscan.log".to_string(),
        "Fallout4.log".to_string(),
        "f4se.log".to_string(),
        "random_file.txt".to_string(),
        "crash-2024-01-15.log".to_string(),
        "crash_log.txt".to_string(),
    ];

    // Benchmark crash log pattern matching
    group.bench_function("match_crash_log_pattern", |b| {
        let pattern = regex::Regex::new(r"crash-.*\.log$").unwrap();
        b.iter(|| {
            log_filenames
                .iter()
                .filter(|f| pattern.is_match(f))
                .count()
        });
    });

    // Benchmark autoscan pattern matching
    group.bench_function("match_autoscan_pattern", |b| {
        let pattern = regex::Regex::new(r"crash-autoscan\.log$").unwrap();
        b.iter(|| {
            log_filenames
                .iter()
                .filter(|f| pattern.is_match(f))
                .count()
        });
    });

    // Benchmark simple string matching (for comparison)
    group.bench_function("match_simple_contains", |b| {
        b.iter(|| {
            log_filenames
                .iter()
                .filter(|f| f.starts_with("crash-") && f.ends_with(".log"))
                .count()
        });
    });

    group.finish();
}

// =============================================================================
// DDS Header Parsing Benchmarks
// =============================================================================

fn dds_parsing_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("dds_parsing");

    // Create a minimal valid DDS header (128 bytes minimum)
    // DDS magic: 0x20534444 ("DDS ")
    let mut dds_header = vec![0u8; 128];
    dds_header[0..4].copy_from_slice(&[0x44, 0x44, 0x53, 0x20]); // "DDS "
    dds_header[4..8].copy_from_slice(&[124, 0, 0, 0]); // Header size = 124
    dds_header[8..12].copy_from_slice(&[0x0F, 0x10, 0x00, 0x00]); // Flags
    dds_header[12..16].copy_from_slice(&[0x00, 0x04, 0x00, 0x00]); // Height = 1024
    dds_header[16..20].copy_from_slice(&[0x00, 0x04, 0x00, 0x00]); // Width = 1024

    group.throughput(Throughput::Bytes(dds_header.len() as u64));

    // Benchmark DDS magic number validation
    group.bench_function("validate_dds_magic", |b| {
        b.iter(|| {
            dds_header.len() >= 4
                && dds_header[0] == 0x44
                && dds_header[1] == 0x44
                && dds_header[2] == 0x53
                && dds_header[3] == 0x20
        });
    });

    // Benchmark DDS dimension extraction
    group.bench_function("extract_dds_dimensions", |b| {
        b.iter(|| {
            if dds_header.len() >= 20 {
                let height = u32::from_le_bytes([
                    dds_header[12],
                    dds_header[13],
                    dds_header[14],
                    dds_header[15],
                ]);
                let width = u32::from_le_bytes([
                    dds_header[16],
                    dds_header[17],
                    dds_header[18],
                    dds_header[19],
                ]);
                (width, height)
            } else {
                (0, 0)
            }
        });
    });

    group.finish();
}

// =============================================================================
// Criterion Group Configuration
// =============================================================================

criterion_group! {
    name = benches;
    config = common::config::configure_criterion();
    targets =
        encoding_detection_benchmarks,
        path_filtering_benchmarks,
        file_io_core_benchmarks,
        log_pattern_benchmarks,
        dds_parsing_benchmarks
}

criterion_main!(benches);
