#![allow(missing_docs)]
//! Criterion benchmarks for classic-scanlog-core operations.
//!
//! This module benchmarks crash log parsing, FormID extraction, pattern matching,
//! and plugin detection using real crash log fixtures from benches/fixtures/.
//!
//! # Running Benchmarks
//!
//! ```bash
//! # Quick mode (development)
//! BENCH_MODE=quick cargo bench --bench scanlog_benchmarks
//!
//! # Thorough mode (baseline establishment)
//! BENCH_MODE=thorough cargo bench --bench scanlog_benchmarks
//!
//! # Verify benchmark compiles
//! cargo bench --bench scanlog_benchmarks -- --test
//! ```

use criterion::{BenchmarkId, Criterion, Throughput, criterion_group, criterion_main};
use std::collections::HashSet;
use std::hint::black_box;
use std::sync::Arc;
use std::time::Duration;

// Import shared benchmark configuration from workspace benches/common/
#[path = "../../../benches/common/mod.rs"]
mod common;
#[path = "../../../benches/common/db_fixtures.rs"]
mod db_fixtures;

use classic_config_core::CoreModEntry;
use classic_database_core::DatabasePool;
use classic_scanlog_core::{
    FormIDAnalyzerCore, LogParser, PatternMatcher, PluginAnalyzer, RecordScanner, contains_plugin,
    contains_record, detect_plugins_batch, scan_records_batch,
};
use classic_shared_core::get_runtime;
use indexmap::IndexMap;

// =============================================================================
// Real Crash Log Fixtures (embedded at compile time)
// =============================================================================

/// Small crash log (~15 KB) - quick iteration
const SAMPLE_LOG_SMALL: &str = include_str!("fixtures/crash-0DB9300.log");

/// Medium crash log (~37 KB) - realistic workload
const SAMPLE_LOG_MEDIUM: &str = include_str!("fixtures/crash-12624.log");

/// Large crash log (~61 KB) - stress testing
const SAMPLE_LOG_LARGE: &str = include_str!("fixtures/crash-2022-06-05-12-58-02.log");

// =============================================================================
// Helper Functions
// =============================================================================

/// Splits crash log content into lines as Arc<str> for LogParser.
fn log_to_lines(content: &str) -> Vec<Arc<str>> {
    content.lines().map(Arc::from).collect()
}

/// Extracts callstack-like lines from log content.
fn extract_callstack_lines(content: &str) -> Vec<String> {
    content
        .lines()
        .filter(|line| line.contains("Form ID:") || line.contains("FormID") || line.contains("0x"))
        .map(|s| s.to_string())
        .take(200) // Limit for benchmark
        .collect()
}

/// Creates common error patterns for pattern matching benchmarks.
fn create_error_patterns() -> Vec<String> {
    vec![
        "ACCESS_VIOLATION".to_string(),
        "EXCEPTION_STACK_OVERFLOW".to_string(),
        "EXCEPTION_BREAKPOINT".to_string(),
        "NULL_POINTER".to_string(),
        "HEAP_CORRUPTION".to_string(),
        "Fallout4.exe".to_string(),
        "f4se".to_string(),
        "nvwgf2umx.dll".to_string(),
        "d3d11.dll".to_string(),
        "KERNEL32".to_string(),
        "ntdll".to_string(),
        "TESObjectREFR".to_string(),
        "PlayerCharacter".to_string(),
        "BSScript".to_string(),
        "Papyrus".to_string(),
    ]
}

/// Creates record types for record scanning benchmarks.
fn create_record_types() -> Vec<String> {
    vec![
        "NPC_".to_string(),
        "WEAP".to_string(),
        "ARMO".to_string(),
        "CELL".to_string(),
        "WRLD".to_string(),
        "ACHR".to_string(),
        "REFR".to_string(),
        "CONT".to_string(),
        "DOOR".to_string(),
        "MISC".to_string(),
    ]
}

fn create_phase5_important_entries() -> Vec<CoreModEntry> {
    vec![
        CoreModEntry {
            detect: "Unofficial Fallout 4 Patch.esp".to_string(),
            name: "Unofficial Fallout 4 Patch".to_string(),
            description: "Install the unofficial patch for baseline stability coverage."
                .to_string(),
            gpu: None,
            gpu_mismatch_warning: None,
            exclude_when: None,
        },
        CoreModEntry {
            detect: "f4se_plugin_preloader".to_string(),
            name: "F4SE Plugin Preloader".to_string(),
            description: "Important XSE module path for hotspot matching.".to_string(),
            gpu: None,
            gpu_mismatch_warning: None,
            exclude_when: None,
        },
        CoreModEntry {
            detect: "bakascrapheap".to_string(),
            name: "Baka ScrapHeap".to_string(),
            description: "Synthetic important-mod literal benchmark token.".to_string(),
            gpu: None,
            gpu_mismatch_warning: None,
            exclude_when: None,
        },
        CoreModEntry {
            detect: "x-cell-fo4.dll".to_string(),
            name: "X-Cell".to_string(),
            description: "Synthetic XSE-module benchmark token.".to_string(),
            gpu: None,
            gpu_mismatch_warning: None,
            exclude_when: None,
        },
    ]
}

fn create_phase5_important_xse_modules() -> HashSet<String> {
    HashSet::from([
        "f4se_plugin_preloader.dll".to_string(),
        "x-cell-fo4.dll".to_string(),
    ])
}

fn extract_fixture_plugins(content: &str) -> IndexMap<String, String> {
    let parser = LogParser::new(None).expect("fixture parser should build");
    let fixture_lines: Vec<Arc<str>> = content.lines().map(Arc::<str>::from).collect();
    let sections = parser.parse_all_sections_arc(&fixture_lines);
    let plugin_lines: Vec<String> = sections
        .get(classic_scanlog_core::segment_key::PLUGINS)
        .expect("fixture should contain a plugins section")
        .iter()
        .map(|line| line.to_string())
        .collect();
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.2.72".to_string(),
    )
    .expect("fixture plugin analyzer should build");
    let (plugins, _limit_triggered, _limit_disabled) = analyzer
        .loadorder_scan_log(&plugin_lines, None, None)
        .expect("fixture plugins should parse");
    plugins
}

/// Rust-side replica of the C++ bridge `detect_crash_pattern` helper.
/// This benchmark remains in the core Criterion harness and intentionally is not an FFI benchmark.
fn bridge_style_detect_crash_pattern_with_parser(parser: &LogParser, lines: &[String]) -> String {
    match parser.parse_crash_header(lines) {
        Ok(header) => header.get("main_error").cloned().unwrap_or_default(),
        Err(_) => String::new(),
    }
}

fn bridge_style_detect_crash_pattern_uncached(lines: &[String]) -> String {
    let parser = LogParser::new(None).expect("default crash-pattern parser should build");
    bridge_style_detect_crash_pattern_with_parser(&parser, lines)
}

// =============================================================================
// Segment Parsing Benchmarks
// =============================================================================

fn segment_parsing_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("segment_parsing");

    // Test different log sizes
    let logs = [
        ("small_15kb", SAMPLE_LOG_SMALL),
        ("medium_37kb", SAMPLE_LOG_MEDIUM),
        ("large_61kb", SAMPLE_LOG_LARGE),
    ];

    for (name, content) in logs {
        let lines = log_to_lines(content);
        let bytes = content.len();

        group.throughput(Throughput::Bytes(bytes as u64));

        // Benchmark initial parse (no cache)
        group.bench_with_input(
            BenchmarkId::new("parse_segments", name),
            &lines,
            |b, lines| {
                let parser = LogParser::new(None).expect("parser creation should succeed");
                b.iter(|| {
                    parser.clear_caches();
                    parser.parse_all_sections_arc(lines)
                });
            },
        );

        // Benchmark cached parse
        group.bench_with_input(
            BenchmarkId::new("parse_segments_cached", name),
            &lines,
            |b, lines| {
                let parser = LogParser::new(None).expect("parser creation should succeed");
                // Prime the cache
                parser.parse_all_sections_arc(lines);
                b.iter(|| parser.parse_all_sections_arc(lines));
            },
        );
    }

    group.finish();
}

// =============================================================================
// FormID Extraction Benchmarks
// =============================================================================

fn formid_extraction_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("formid_extraction");

    let logs = [
        ("small_15kb", SAMPLE_LOG_SMALL),
        ("medium_37kb", SAMPLE_LOG_MEDIUM),
        ("large_61kb", SAMPLE_LOG_LARGE),
    ];

    for (name, content) in logs {
        let callstack_lines = extract_callstack_lines(content);
        let bytes = callstack_lines.iter().map(|s| s.len()).sum::<usize>();

        group.throughput(Throughput::Bytes(bytes as u64));

        group.bench_with_input(
            BenchmarkId::new("extract_formids", name),
            &callstack_lines,
            |b, lines| {
                let analyzer = FormIDAnalyzerCore::new(None, false, "Buffout 4".to_string())
                    .expect("analyzer creation should succeed");

                b.iter(|| analyzer.extract_formids(lines.clone()));
            },
        );
    }

    // Benchmark FormID validation function
    group.bench_function("is_valid_formid", |b| {
        let test_ids = vec![
            "0x12345678",
            "0xABCDEF00",
            "12345678",
            "FF000000",
            "00000000",
        ];
        b.iter(|| {
            for id in &test_ids {
                let _ = classic_scanlog_core::is_valid_formid(id);
            }
        });
    });

    group.finish();
}

fn formid_resolution_db_benchmarks(c: &mut Criterion) {
    let runtime = get_runtime();
    let fixture = runtime
        .block_on(db_fixtures::DeterministicDbFixture::create(
            db_fixtures::FixtureConfig::default(),
        ))
        .expect("deterministic fixture generation should succeed");

    let mut group = c.benchmark_group("scanlog_formid_resolution");
    let pool = Arc::new(DatabasePool::new(
        Some(8),
        Duration::from_secs(900),
        fixture.table_name.clone(),
    ));
    runtime
        .block_on(pool.initialize(vec![fixture.db_paths[0].clone()]))
        .expect("database fixture initialization should succeed");

    let analyzer = FormIDAnalyzerCore::new(
        Some(pool.clone()),
        true, // show_formid_values=true to force DB-backed value resolution path
        "Buffout 4".to_string(),
    )
    .expect("analyzer creation should succeed");

    let crashlog_plugins: IndexMap<String, String> =
        fixture.plugin_prefix_pairs().into_iter().collect();

    for (scenario_id, formid_count) in [
        ("cold_small_32", 32usize),
        ("cold_medium_128", 128usize),
        ("cold_large_512", 512usize),
    ] {
        let callstack_lines = fixture.formid_callstack_lines(formid_count);
        group.throughput(Throughput::Elements(formid_count as u64));

        group.bench_with_input(
            BenchmarkId::new("resolve_with_db", scenario_id),
            &callstack_lines,
            |b, lines| {
                b.iter(|| {
                    pool.clear_cache(false);
                    let formids = analyzer.extract_formids(lines.clone());
                    let report_lines = runtime
                        .block_on(analyzer.formid_match(formids, &crashlog_plugins))
                        .expect("formid resolution should succeed");
                    black_box(report_lines.len())
                });
            },
        );
    }

    // Warm-cache run that exercises the same resolution path without cache clearing.
    let warm_lines = fixture.formid_callstack_lines(128);
    let warm_formids = analyzer.extract_formids(warm_lines.clone());
    runtime
        .block_on(analyzer.formid_match(warm_formids, &crashlog_plugins))
        .expect("warm cache priming should succeed");

    group.bench_with_input(
        BenchmarkId::new("resolve_with_db", "warm_medium_128"),
        &warm_lines,
        |b, lines| {
            b.iter(|| {
                let formids = analyzer.extract_formids(lines.clone());
                let report_lines = runtime
                    .block_on(analyzer.formid_match(formids, &crashlog_plugins))
                    .expect("formid resolution should succeed");
                black_box(report_lines.len())
            });
        },
    );

    group.finish();
    runtime
        .block_on(pool.close())
        .expect("database pool close should succeed");
}

// =============================================================================
// Pattern Matching Benchmarks
// =============================================================================

fn pattern_matching_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("pattern_matching");

    let patterns = create_error_patterns();

    let logs = [
        ("small_15kb", SAMPLE_LOG_SMALL),
        ("medium_37kb", SAMPLE_LOG_MEDIUM),
        ("large_61kb", SAMPLE_LOG_LARGE),
    ];

    for (name, content) in logs {
        let bytes = content.len();
        group.throughput(Throughput::Bytes(bytes as u64));

        // Benchmark Aho-Corasick pattern matching
        group.bench_with_input(
            BenchmarkId::new("aho_corasick_find_all", name),
            content,
            |b, content| {
                let matcher =
                    PatternMatcher::new(patterns.clone()).expect("matcher creation should succeed");
                b.iter(|| matcher.find_all(content));
            },
        );

        // Benchmark has_match (fast early exit)
        group.bench_with_input(
            BenchmarkId::new("aho_corasick_has_match", name),
            content,
            |b, content| {
                let matcher =
                    PatternMatcher::new(patterns.clone()).expect("matcher creation should succeed");
                b.iter(|| matcher.has_match(content));
            },
        );
    }

    // Benchmark pattern matcher creation (compile time)
    group.bench_function("pattern_matcher_creation_15_patterns", |b| {
        b.iter(|| PatternMatcher::new(patterns.clone()).expect("should succeed"));
    });

    group.finish();
}

// =============================================================================
// Plugin Detection Benchmarks
// =============================================================================

fn plugin_detection_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("plugin_detection");

    let logs = [
        ("small_15kb", SAMPLE_LOG_SMALL),
        ("medium_37kb", SAMPLE_LOG_MEDIUM),
        ("large_61kb", SAMPLE_LOG_LARGE),
    ];

    for (name, content) in logs {
        let bytes = content.len();
        group.throughput(Throughput::Bytes(bytes as u64));

        // Benchmark line-by-line plugin detection
        group.bench_with_input(
            BenchmarkId::new("contains_plugin_per_line", name),
            content,
            |b, content| {
                b.iter(|| {
                    for line in content.lines() {
                        let _ = contains_plugin(line);
                    }
                });
            },
        );

        // Benchmark full log plugin detection (using detect_plugins_batch for single log)
        group.bench_with_input(
            BenchmarkId::new("detect_plugins_single_log", name),
            content,
            |b, content| {
                b.iter(|| detect_plugins_batch(vec![content.to_string()]));
            },
        );
    }

    // Benchmark batch plugin detection
    let logs_batch: Vec<String> = vec![SAMPLE_LOG_SMALL.to_string(), SAMPLE_LOG_MEDIUM.to_string()];
    group.bench_function("detect_plugins_batch_2_logs", |b| {
        b.iter(|| detect_plugins_batch(logs_batch.clone()));
    });

    group.finish();
}

// =============================================================================
// Record Scanning Benchmarks
// =============================================================================

fn record_scanning_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("record_scanning");

    let record_types = create_record_types();
    let ignore_records: Vec<String> = vec![];

    let logs = [
        ("small_15kb", SAMPLE_LOG_SMALL),
        ("medium_37kb", SAMPLE_LOG_MEDIUM),
        ("large_61kb", SAMPLE_LOG_LARGE),
    ];

    for (name, content) in logs {
        let bytes = content.len();
        group.throughput(Throughput::Bytes(bytes as u64));

        // Benchmark line-by-line record detection
        group.bench_with_input(
            BenchmarkId::new("contains_record_per_line", name),
            content,
            |b, content| {
                b.iter(|| {
                    for line in content.lines() {
                        let _ = contains_record(line, &record_types, &ignore_records);
                    }
                });
            },
        );

        // Benchmark record scanner with full config
        group.bench_with_input(
            BenchmarkId::new("record_scanner_scan", name),
            content,
            |b, content| {
                let scanner =
                    RecordScanner::new(record_types.clone(), vec![], "Buffout 4".to_string());

                let lines: Vec<String> = content.lines().map(|s| s.to_string()).collect();
                b.iter(|| scanner.scan_named_records(&lines));
            },
        );
    }

    // Benchmark batch record scanning
    let segments: Vec<Vec<String>> = vec![
        SAMPLE_LOG_SMALL.lines().map(|s| s.to_string()).collect(),
        SAMPLE_LOG_MEDIUM.lines().map(|s| s.to_string()).collect(),
    ];
    group.bench_function("scan_records_batch_2_segments", |b| {
        b.iter(|| {
            scan_records_batch(
                segments.clone(),
                record_types.clone(),
                ignore_records.clone(),
            )
        });
    });

    group.finish();
}

// =============================================================================
// Full Pipeline Benchmarks
// =============================================================================

fn full_pipeline_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("full_pipeline");

    let logs = [
        ("small_15kb", SAMPLE_LOG_SMALL),
        ("medium_37kb", SAMPLE_LOG_MEDIUM),
        ("large_61kb", SAMPLE_LOG_LARGE),
    ];

    for (name, content) in logs {
        let bytes = content.len();
        group.throughput(Throughput::Bytes(bytes as u64));

        // Full analysis pipeline: parse + extract FormIDs + pattern match + plugin detect
        group.bench_with_input(
            BenchmarkId::new("complete_analysis", name),
            content,
            |b, content| {
                let parser = LogParser::new(None).expect("parser creation should succeed");
                let patterns = create_error_patterns();
                let pattern_matcher =
                    PatternMatcher::new(patterns).expect("matcher creation should succeed");
                let formid_analyzer = FormIDAnalyzerCore::new(None, false, "Buffout 4".to_string())
                    .expect("analyzer creation should succeed");

                b.iter(|| {
                    let lines = log_to_lines(content);

                    // Parse segments
                    let _segments = parser.parse_all_sections_arc(&lines);

                    // Pattern matching
                    let _matches = pattern_matcher.find_all(content);

                    // Plugin detection (using batch API for single log)
                    let _plugins = detect_plugins_batch(vec![content.to_string()]);

                    // FormID extraction
                    let callstack_lines = extract_callstack_lines(content);
                    let _formids = formid_analyzer.extract_formids(callstack_lines);
                });
            },
        );
    }

    group.finish();
}

// =============================================================================
// Log Parser Creation Benchmarks
// =============================================================================

fn parser_creation_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("parser_creation");

    // Default parser creation
    group.bench_function("log_parser_default", |b| {
        b.iter(|| LogParser::new(None).expect("should succeed"));
    });

    // Custom boundaries parser creation
    let custom_boundaries = vec![
        ("START".to_string(), "MIDDLE".to_string()),
        ("MIDDLE".to_string(), "END".to_string()),
        ("END".to_string(), "EOF".to_string()),
    ];

    group.bench_function("log_parser_custom_3_boundaries", |b| {
        b.iter(|| LogParser::new(Some(custom_boundaries.clone())).expect("should succeed"));
    });

    // FormID analyzer creation
    group.bench_function("formid_analyzer_creation", |b| {
        b.iter(|| {
            FormIDAnalyzerCore::new(None, false, "Buffout 4".to_string()).expect("should succeed")
        });
    });

    // Record scanner creation
    group.bench_function("record_scanner_creation", |b| {
        let record_types = create_record_types();
        b.iter(|| RecordScanner::new(record_types.clone(), vec![], "Buffout 4".to_string()));
    });

    // Pattern matcher creation with 15 patterns
    group.bench_function("pattern_matcher_creation", |b| {
        let patterns = create_error_patterns();
        b.iter(|| PatternMatcher::new(patterns.clone()).expect("should succeed"));
    });

    group.finish();
}

fn phase5_hotspot_benchmarks(c: &mut Criterion) {
    let important_entries = create_phase5_important_entries();
    let input = classic_scanlog_core::ModGuidanceAnalysisInput {
        plugins: extract_fixture_plugins(SAMPLE_LOG_LARGE),
        user_gpu: Some("amd".to_string()),
        xse_modules: create_phase5_important_xse_modules(),
    };
    let analyzer = classic_scanlog_core::ModGuidanceAnalyzer::new(
        Vec::new(),
        Vec::new(),
        Vec::new(),
        important_entries.clone(),
    )
    .expect("semantic Mod Guidance analyzer should build");

    let mut guidance_group = c.benchmark_group("phase5_mod_guidance_analyzer");
    guidance_group.bench_function("construction", |b| {
        b.iter(|| {
            classic_scanlog_core::ModGuidanceAnalyzer::new(
                Vec::new(),
                Vec::new(),
                Vec::new(),
                important_entries.clone(),
            )
            .expect("semantic Mod Guidance analyzer should build")
        });
    });
    guidance_group.bench_function("aggregate_analysis", |b| {
        b.iter(|| {
            analyzer
                .analyze(black_box(input.clone()))
                .expect("semantic Mod Guidance analysis should succeed")
        });
    });
    guidance_group.finish();
    let bridge_fixture_lines: Vec<String> = SAMPLE_LOG_LARGE.lines().map(str::to_string).collect();
    let bridge_header_excerpt: Vec<String> = SAMPLE_LOG_LARGE
        .lines()
        .take(24)
        .map(str::to_string)
        .collect();
    let cached_bridge_parser =
        LogParser::new(None).expect("cached crash-pattern parser should build");

    let mut bridge_group = c.benchmark_group("phase5_bridge_crash_pattern_replica");
    bridge_group.bench_function("parser_per_call_real_fixture", |b| {
        b.iter(|| bridge_style_detect_crash_pattern_uncached(black_box(&bridge_fixture_lines)));
    });
    bridge_group.bench_function("cached_parser_real_fixture", |b| {
        b.iter(|| {
            bridge_style_detect_crash_pattern_with_parser(
                black_box(&cached_bridge_parser),
                black_box(&bridge_fixture_lines),
            )
        });
    });
    bridge_group.bench_function("parser_per_call_header_excerpt", |b| {
        b.iter(|| bridge_style_detect_crash_pattern_uncached(black_box(&bridge_header_excerpt)));
    });
    bridge_group.bench_function("cached_parser_header_excerpt", |b| {
        b.iter(|| {
            bridge_style_detect_crash_pattern_with_parser(
                black_box(&cached_bridge_parser),
                black_box(&bridge_header_excerpt),
            )
        });
    });
    bridge_group.finish();
}

// =============================================================================
// Criterion Group Configuration
// =============================================================================

criterion_group! {
    name = benches;
    config = common::config::configure_criterion();
    targets =
        segment_parsing_benchmarks,
        formid_extraction_benchmarks,
        formid_resolution_db_benchmarks,
        pattern_matching_benchmarks,
        plugin_detection_benchmarks,
        record_scanning_benchmarks,
        full_pipeline_benchmarks,
        parser_creation_benchmarks,
        phase5_hotspot_benchmarks
}

criterion_main!(benches);
