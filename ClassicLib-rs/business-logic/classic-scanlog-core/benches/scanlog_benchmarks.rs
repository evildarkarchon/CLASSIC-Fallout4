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

use criterion::{BatchSize, BenchmarkId, Criterion, Throughput, criterion_group, criterion_main};
use std::collections::HashSet;
use std::hint::black_box;
use std::sync::Arc;
use std::time::Duration;

// Import shared benchmark configuration from workspace benches/common/
#[path = "../../../../benches/common/mod.rs"]
mod common;
#[path = "../../../../benches/common/db_fixtures.rs"]
mod db_fixtures;

use classic_config_core::CoreModEntry;
use classic_database_core::DatabasePool;
use classic_scanlog_core::{
    FormIDAnalyzerCore, LogParser, PatternMatcher, PluginAnalyzer, RecordScanner, contains_plugin,
    contains_record, detect_mods_batch, detect_mods_single, detect_plugins_batch,
    mod_detector::{
        build_important_matcher_for_bench, build_important_mod_haystack_for_bench,
        important_matcher_compile_count_for_bench, reset_important_matcher_cache_for_bench,
    },
    scan_records_batch,
};
use classic_shared_core::get_runtime;
use indexmap::IndexMap;
use regex::Regex;

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

fn create_phase5_cached_regex_yaml() -> IndexMap<String, String> {
    IndexMap::from([
        (
            "unofficial fallout 4 patch".to_string(),
            "Unofficial Fallout 4 Patch\nBaseline hotspot token.".to_string(),
        ),
        (
            "workshop framework".to_string(),
            "Workshop Framework\nSynthetic cached-regex benchmark token.".to_string(),
        ),
        (
            "sim settlements 2".to_string(),
            "Sim Settlements 2\nSynthetic cached-regex benchmark token.".to_string(),
        ),
        (
            "hudframework".to_string(),
            "HUDFramework\nSynthetic cached-regex benchmark token.".to_string(),
        ),
        (
            "looksmenu".to_string(),
            "LooksMenu\nSynthetic cached-regex benchmark token.".to_string(),
        ),
        (
            "fallui".to_string(),
            "FallUI\nSynthetic cached-regex benchmark token.".to_string(),
        ),
    ])
}

fn create_phase5_cached_regex_yaml_variant(seed: usize) -> IndexMap<String, String> {
    IndexMap::from([
        (
            format!("unofficial fallout 4 patch {seed}"),
            format!("Unofficial Fallout 4 Patch {seed}\nBaseline hotspot token."),
        ),
        (
            format!("workshop framework {seed}"),
            format!("Workshop Framework {seed}\nSynthetic cached-regex benchmark token."),
        ),
        (
            format!("sim settlements 2 {seed}"),
            format!("Sim Settlements 2 {seed}\nSynthetic cached-regex benchmark token."),
        ),
        (
            format!("hudframework {seed}"),
            format!("HUDFramework {seed}\nSynthetic cached-regex benchmark token."),
        ),
        (
            format!("looksmenu {seed}"),
            format!("LooksMenu {seed}\nSynthetic cached-regex benchmark token."),
        ),
        (
            format!("fallui {seed}"),
            format!("FallUI {seed}\nSynthetic cached-regex benchmark token."),
        ),
    ])
}

fn create_phase5_synthetic_plugins(count: usize) -> IndexMap<String, String> {
    let seed_plugins = [
        "Unofficial Fallout 4 Patch.esp",
        "Workshop Framework.esm",
        "Sim Settlements 2.esm",
        "HUDFramework.esm",
        "LooksMenu.esp",
        "FallUI.esp",
    ];

    let mut plugins = IndexMap::new();
    for index in 0..count {
        let id = format!("{:02X}", index % 0xFD);
        let plugin_name = if index < seed_plugins.len() {
            seed_plugins[index].to_string()
        } else {
            format!("SyntheticBenchmarkMod{:03}.esp", index)
        };
        plugins.insert(plugin_name, id);
    }
    plugins
}

fn create_phase5_synthetic_plugins_variant(seed: usize, count: usize) -> IndexMap<String, String> {
    let seed_plugins = [
        format!("Unofficial Fallout 4 Patch {seed}.esp"),
        format!("Workshop Framework {seed}.esm"),
        format!("Sim Settlements 2 {seed}.esm"),
        format!("HUDFramework {seed}.esm"),
        format!("LooksMenu {seed}.esp"),
        format!("FallUI {seed}.esp"),
    ];

    let mut plugins = IndexMap::new();
    for index in 0..count {
        let id = format!("{:02X}", index % 0xFD);
        let plugin_name = if index < seed_plugins.len() {
            seed_plugins[index].clone()
        } else {
            format!("SyntheticBenchmarkMod{seed:03}_{index:03}.esp")
        };
        plugins.insert(plugin_name, id);
    }
    plugins
}

fn create_phase5_batch_plugins(
    batch_size: usize,
    plugins_per_log: usize,
) -> Vec<IndexMap<String, String>> {
    (0..batch_size)
        .map(|batch_index| {
            let mut plugins = create_phase5_synthetic_plugins(plugins_per_log);
            plugins.insert(
                format!("BatchUnique{:02}.esp", batch_index),
                format!("{:02X}", (batch_index + plugins_per_log) % 0xFD),
            );
            plugins
        })
        .collect()
}

fn create_phase5_batch_plugins_variant(
    seed: usize,
    batch_size: usize,
    plugins_per_log: usize,
) -> Vec<IndexMap<String, String>> {
    (0..batch_size)
        .map(|batch_index| {
            let mut plugins =
                create_phase5_synthetic_plugins_variant(seed * 100 + batch_index, plugins_per_log);
            plugins.insert(
                format!("BatchUnique{seed:03}_{batch_index:02}.esp"),
                format!("{:02X}", (batch_index + plugins_per_log) % 0xFD),
            );
            plugins
        })
        .collect()
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

fn phase5_important_combined_text(
    plugins: &IndexMap<String, String>,
    xse_modules: &HashSet<String>,
) -> String {
    let plugin_text = plugins.keys().map(|name| name.to_lowercase());
    let xse_text = xse_modules.iter().map(|name| name.to_lowercase());
    plugin_text.chain(xse_text).collect::<Vec<_>>().join("\n")
}

fn detect_mods_important_legacy_regex_count(
    entries: &[CoreModEntry],
    plugins: &IndexMap<String, String>,
    xse_modules: &HashSet<String>,
) -> usize {
    let combined_text = phase5_important_combined_text(plugins, xse_modules);
    entries
        .iter()
        .filter(|entry| {
            let escaped = regex::escape(&entry.detect.to_lowercase());
            Regex::new(&escaped)
                .expect("legacy important-mod benchmark regex should compile")
                .is_match(&combined_text)
        })
        .count()
}

fn detect_mods_important_aho_count(
    entries: &[CoreModEntry],
    plugins: &IndexMap<String, String>,
    xse_modules: &HashSet<String>,
) -> usize {
    let combined_text = build_important_mod_haystack_for_bench(plugins, xse_modules);
    let matcher = build_important_matcher_for_bench(entries)
        .expect("important-mod aho benchmark matcher should build");

    matcher.find_iter(&combined_text).count()
}

fn detect_mods_important_aho_uncached_count(
    entries: &[CoreModEntry],
    plugins: &IndexMap<String, String>,
    xse_modules: &HashSet<String>,
) -> usize {
    reset_important_matcher_cache_for_bench();
    detect_mods_important_aho_count(entries, plugins, xse_modules)
}

fn detect_mods_important_aho_cached_haystack_count(
    entries: &[CoreModEntry],
    combined_text: &str,
) -> usize {
    let matcher = build_important_matcher_for_bench(entries)
        .expect("important-mod aho benchmark matcher should build");
    matcher.find_iter(combined_text).count()
}

fn detect_mods_important_aho_compile_only(entries: &[CoreModEntry]) -> usize {
    reset_important_matcher_cache_for_bench();
    let _before = important_matcher_compile_count_for_bench();
    let _matcher = build_important_matcher_for_bench(entries)
        .expect("important-mod aho benchmark matcher should build");
    important_matcher_compile_count_for_bench() as usize
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
                let analyzer = FormIDAnalyzerCore::new(
                    None,
                    false,
                    "Buffout 4".to_string(),
                    Vec::new(),
                    Vec::new(),
                    Vec::new(),
                )
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
        Vec::new(),
        Vec::new(),
        Vec::new(),
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
                let formid_analyzer = FormIDAnalyzerCore::new(
                    None,
                    false,
                    "Buffout 4".to_string(),
                    Vec::new(),
                    Vec::new(),
                    Vec::new(),
                )
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
            FormIDAnalyzerCore::new(
                None,
                false,
                "Buffout 4".to_string(),
                Vec::new(),
                Vec::new(),
                Vec::new(),
            )
            .expect("should succeed")
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
    let yaml_dict = create_phase5_cached_regex_yaml();
    let synthetic_plugins = create_phase5_synthetic_plugins(48);
    let batch_plugins = create_phase5_batch_plugins(16, 40);
    let important_entries = create_phase5_important_entries();
    let synthetic_xse_modules = create_phase5_important_xse_modules();
    let fixture_plugins = extract_fixture_plugins(SAMPLE_LOG_LARGE);
    let fixture_xse_modules: HashSet<String> = HashSet::new();

    let _ = detect_mods_single(yaml_dict.clone(), synthetic_plugins.clone())
        .expect("single matcher cache priming should succeed");
    let _ = detect_mods_batch(yaml_dict.clone(), batch_plugins.clone())
        .expect("batch matcher cache priming should succeed");

    let mut cached_regex_group = c.benchmark_group("phase5_cached_regex_paths");
    cached_regex_group.throughput(Throughput::Elements(synthetic_plugins.len() as u64));
    let mut single_uncached_seed = 0usize;
    cached_regex_group.bench_function("detect_mods_single_synthetic_uncached", |b| {
        b.iter_batched(
            || {
                let seed = single_uncached_seed;
                single_uncached_seed += 1;
                (
                    create_phase5_cached_regex_yaml_variant(seed),
                    create_phase5_synthetic_plugins_variant(seed, 48),
                )
            },
            |(yaml_dict, plugins)| {
                detect_mods_single(yaml_dict, plugins)
                    .expect("single uncached benchmark should succeed")
            },
            BatchSize::SmallInput,
        );
    });
    cached_regex_group.bench_function("detect_mods_single_synthetic_cached", |b| {
        b.iter_batched(
            || (yaml_dict.clone(), synthetic_plugins.clone()),
            |(yaml_dict, plugins)| {
                detect_mods_single(yaml_dict, plugins)
                    .expect("single cached benchmark should succeed")
            },
            BatchSize::SmallInput,
        );
    });
    let mut batch_uncached_seed = 0usize;
    cached_regex_group.bench_function("detect_mods_batch_synthetic_uncached", |b| {
        b.iter_batched(
            || {
                let seed = batch_uncached_seed;
                batch_uncached_seed += 1;
                (
                    create_phase5_cached_regex_yaml_variant(seed),
                    create_phase5_batch_plugins_variant(seed, 16, 40),
                )
            },
            |(yaml_dict, plugins)| {
                detect_mods_batch(yaml_dict, plugins)
                    .expect("batch uncached benchmark should succeed")
            },
            BatchSize::SmallInput,
        );
    });
    cached_regex_group.bench_function("detect_mods_batch_synthetic_cached", |b| {
        b.iter_batched(
            || (yaml_dict.clone(), batch_plugins.clone()),
            |(yaml_dict, plugins)| {
                detect_mods_batch(yaml_dict, plugins)
                    .expect("batch cached benchmark should succeed")
            },
            BatchSize::SmallInput,
        );
    });
    cached_regex_group.finish();

    let synthetic_important_haystack =
        build_important_mod_haystack_for_bench(&synthetic_plugins, &synthetic_xse_modules);
    let fixture_important_haystack =
        build_important_mod_haystack_for_bench(&fixture_plugins, &fixture_xse_modules);

    reset_important_matcher_cache_for_bench();
    let _ = build_important_matcher_for_bench(&important_entries)
        .expect("important-mod cached matcher should build");

    let mut important_group = c.benchmark_group("phase5_detect_mods_important");
    important_group.bench_function("legacy_regex_plugin_and_xse_surface", |b| {
        b.iter_batched(
            || {
                (
                    important_entries.clone(),
                    synthetic_plugins.clone(),
                    synthetic_xse_modules.clone(),
                )
            },
            |(entries, plugins, xse_modules)| {
                black_box(detect_mods_important_legacy_regex_count(
                    &entries,
                    &plugins,
                    &xse_modules,
                ))
            },
            BatchSize::SmallInput,
        );
    });
    important_group.bench_function("aho_compile_only_synthetic_literals", |b| {
        b.iter_batched(
            || important_entries.clone(),
            |entries| black_box(detect_mods_important_aho_compile_only(&entries)),
            BatchSize::SmallInput,
        );
    });
    important_group.bench_function("aho_build_haystack_only_plugin_and_xse_surface", |b| {
        b.iter_batched(
            || (synthetic_plugins.clone(), synthetic_xse_modules.clone()),
            |(plugins, xse_modules)| {
                black_box(build_important_mod_haystack_for_bench(
                    &plugins,
                    &xse_modules,
                ))
            },
            BatchSize::SmallInput,
        );
    });
    important_group.bench_function("aho_build_haystack_only_real_fixture_plugin_surface", |b| {
        b.iter_batched(
            || (fixture_plugins.clone(), fixture_xse_modules.clone()),
            |(plugins, xse_modules)| {
                black_box(build_important_mod_haystack_for_bench(
                    &plugins,
                    &xse_modules,
                ))
            },
            BatchSize::SmallInput,
        );
    });
    important_group.bench_function("aho_uncached_plugin_and_xse_surface", |b| {
        b.iter_batched(
            || {
                (
                    important_entries.clone(),
                    synthetic_plugins.clone(),
                    synthetic_xse_modules.clone(),
                )
            },
            |(entries, plugins, xse_modules)| {
                black_box(detect_mods_important_aho_uncached_count(
                    &entries,
                    &plugins,
                    &xse_modules,
                ))
            },
            BatchSize::SmallInput,
        );
    });
    important_group.bench_function("synthetic_plugin_and_xse_surface", |b| {
        b.iter_batched(
            || {
                (
                    important_entries.clone(),
                    synthetic_plugins.clone(),
                    synthetic_xse_modules.clone(),
                )
            },
            |(entries, plugins, xse_modules)| {
                black_box(detect_mods_important_aho_count(
                    &entries,
                    &plugins,
                    &xse_modules,
                ))
            },
            BatchSize::SmallInput,
        );
    });
    important_group.bench_function("aho_cached_match_only_plugin_and_xse_surface", |b| {
        b.iter_batched(
            || {
                (
                    important_entries.clone(),
                    synthetic_important_haystack.clone(),
                )
            },
            |(entries, combined_text)| {
                black_box(detect_mods_important_aho_cached_haystack_count(
                    &entries,
                    &combined_text,
                ))
            },
            BatchSize::SmallInput,
        );
    });
    important_group.bench_function("legacy_regex_real_fixture_plugin_surface", |b| {
        b.iter_batched(
            || {
                (
                    important_entries.clone(),
                    fixture_plugins.clone(),
                    fixture_xse_modules.clone(),
                )
            },
            |(entries, plugins, xse_modules)| {
                black_box(detect_mods_important_legacy_regex_count(
                    &entries,
                    &plugins,
                    &xse_modules,
                ))
            },
            BatchSize::SmallInput,
        );
    });
    important_group.bench_function("aho_uncached_real_fixture_plugin_surface", |b| {
        b.iter_batched(
            || {
                (
                    important_entries.clone(),
                    fixture_plugins.clone(),
                    fixture_xse_modules.clone(),
                )
            },
            |(entries, plugins, xse_modules)| {
                black_box(detect_mods_important_aho_uncached_count(
                    &entries,
                    &plugins,
                    &xse_modules,
                ))
            },
            BatchSize::SmallInput,
        );
    });
    important_group.bench_function("real_fixture_plugin_surface", |b| {
        b.iter_batched(
            || {
                (
                    important_entries.clone(),
                    fixture_plugins.clone(),
                    fixture_xse_modules.clone(),
                )
            },
            |(entries, plugins, xse_modules)| {
                black_box(detect_mods_important_aho_count(
                    &entries,
                    &plugins,
                    &xse_modules,
                ))
            },
            BatchSize::SmallInput,
        );
    });
    important_group.bench_function("aho_cached_match_only_real_fixture_plugin_surface", |b| {
        b.iter_batched(
            || {
                (
                    important_entries.clone(),
                    fixture_important_haystack.clone(),
                )
            },
            |(entries, combined_text)| {
                black_box(detect_mods_important_aho_cached_haystack_count(
                    &entries,
                    &combined_text,
                ))
            },
            BatchSize::SmallInput,
        );
    });
    important_group.finish();

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
