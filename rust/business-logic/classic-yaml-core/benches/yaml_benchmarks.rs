//! Criterion benchmarks for classic-yaml-core operations.
//!
//! This module benchmarks YAML parsing, serialization, traversal, and modification
//! operations using realistic workloads similar to CLASSIC's configuration files.
//!
//! # Running Benchmarks
//!
//! ```bash
//! # Quick mode (development)
//! BENCH_MODE=quick cargo bench --bench yaml_benchmarks
//!
//! # Thorough mode (baseline establishment)
//! BENCH_MODE=thorough cargo bench --bench yaml_benchmarks
//!
//! # Verify benchmark compiles
//! cargo bench --bench yaml_benchmarks -- --test
//! ```

use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use yaml_rust2::{Yaml, YamlLoader};

// Import shared benchmark configuration from workspace benches/common/
#[path = "../../../benches/common/mod.rs"]
mod common;

use classic_yaml_core::{YamlFormatConfig, YamlOperations};

// =============================================================================
// Test Data Generation
// =============================================================================

/// Generates realistic YAML content similar to CLASSIC configuration files.
///
/// Creates nested structures with game settings, mod configurations, and
/// metadata similar to the actual CLASSIC Data/databases/*.yaml files.
fn generate_yaml_content(lines: usize) -> String {
    let mut yaml = String::with_capacity(lines * 80);

    yaml.push_str("# CLASSIC Configuration File\n");
    yaml.push_str("version: 8.2.0\n");
    yaml.push_str("game: Fallout4\n");
    yaml.push_str("\n");

    // Settings section
    yaml.push_str("settings:\n");
    yaml.push_str("  fcx_mode: true\n");
    yaml.push_str("  show_formid_values: false\n");
    yaml.push_str("  auto_scan: true\n");
    yaml.push_str("  log_level: INFO\n");
    yaml.push_str("\n");

    // Generate mod entries
    let entries = (lines.saturating_sub(20)) / 8;
    yaml.push_str("mods:\n");

    for i in 0..entries {
        yaml.push_str(&format!("  mod_{}:\n", i));
        yaml.push_str(&format!("    name: \"Test Mod {}\"\n", i));
        yaml.push_str(&format!("    plugin: \"TestMod{}.esp\"\n", i));
        yaml.push_str(&format!("    priority: {}\n", i % 255));
        yaml.push_str(&format!("    enabled: {}\n", i % 2 == 0));
        yaml.push_str("    tags:\n");
        yaml.push_str(&format!("      - category_{}\n", i % 10));
        yaml.push_str(&format!("      - type_{}\n", i % 5));
    }

    yaml
}

/// Generates multi-document YAML content.
fn generate_multi_document_yaml(docs: usize, entries_per_doc: usize) -> String {
    let mut yaml = String::with_capacity(docs * entries_per_doc * 100);

    for doc_idx in 0..docs {
        if doc_idx > 0 {
            yaml.push_str("---\n");
        }
        yaml.push_str(&format!("document: {}\n", doc_idx));
        yaml.push_str("entries:\n");

        for i in 0..entries_per_doc {
            yaml.push_str(&format!("  entry_{}:\n", i));
            yaml.push_str(&format!("    value: {}\n", i * doc_idx));
            yaml.push_str(&format!("    enabled: {}\n", i % 2 == 0));
        }
    }

    yaml
}

/// Generates deeply nested YAML for traversal benchmarks.
fn generate_nested_yaml(depth: usize) -> String {
    let mut yaml = String::with_capacity(depth * 50);

    yaml.push_str("root:\n");
    for i in 0..depth {
        let indent = "  ".repeat(i + 1);
        yaml.push_str(&format!("{}level_{}:\n", indent, i));
    }

    // Add a final value at the deepest level
    let final_indent = "  ".repeat(depth + 1);
    yaml.push_str(&format!("{}value: deep_nested_value\n", final_indent));

    yaml
}

// =============================================================================
// Parsing Benchmarks
// =============================================================================

fn yaml_parsing_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("yaml_parsing");

    // Test different YAML sizes
    let sizes = [(100, "100_lines"), (1000, "1000_lines"), (5000, "5000_lines")];

    for (lines, name) in sizes {
        let content = generate_yaml_content(lines);
        let bytes = content.len();

        group.throughput(Throughput::Bytes(bytes as u64));

        group.bench_with_input(BenchmarkId::new("parse", name), &content, |b, content| {
            let ops = YamlOperations::new();
            b.iter(|| {
                ops.parse_yaml(content).expect("parse should succeed")
            });
        });
    }

    // Benchmark multi-document parsing
    let multi_doc = generate_multi_document_yaml(5, 100);
    group.throughput(Throughput::Bytes(multi_doc.len() as u64));
    group.bench_with_input(
        BenchmarkId::new("parse", "multi_document_5x100"),
        &multi_doc,
        |b, content| {
            b.iter(|| {
                YamlLoader::load_from_str(content).expect("parse should succeed")
            });
        },
    );

    group.finish();
}

// =============================================================================
// Serialization Benchmarks
// =============================================================================

fn yaml_serialization_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("yaml_serialization");

    let sizes = [(100, "100_lines"), (1000, "1000_lines"), (5000, "5000_lines")];

    for (lines, name) in sizes {
        let content = generate_yaml_content(lines);
        let ops = YamlOperations::new();
        let parsed = ops.parse_yaml(&content).expect("parse should succeed");

        // Estimate serialized size based on input
        group.throughput(Throughput::Bytes(content.len() as u64));

        group.bench_with_input(BenchmarkId::new("dump", name), &parsed, |b, yaml| {
            b.iter(|| {
                ops.dump_yaml(yaml).expect("dump should succeed")
            });
        });
    }

    group.finish();
}

// =============================================================================
// Traversal Benchmarks
// =============================================================================

fn yaml_traversal_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("yaml_traversal");

    // Setup test data
    let content = generate_yaml_content(1000);
    let ops = YamlOperations::new();
    let parsed = ops.parse_yaml(&content).expect("parse should succeed");

    // Benchmark shallow key access
    group.bench_function("get_setting_shallow", |b| {
        b.iter(|| {
            ops.get_setting(&parsed, "version")
        });
    });

    // Benchmark nested key access
    group.bench_function("get_setting_nested", |b| {
        b.iter(|| {
            ops.get_setting(&parsed, "settings.fcx_mode")
        });
    });

    // Benchmark deep nested access
    let deep_content = generate_nested_yaml(10);
    let deep_parsed = ops.parse_yaml(&deep_content).expect("parse should succeed");
    let deep_path = (0..10).map(|i| format!("level_{}", i)).collect::<Vec<_>>().join(".");
    let full_path = format!("root.{}.value", deep_path);

    group.bench_function("get_setting_deep_10_levels", |b| {
        b.iter(|| {
            ops.get_setting(&deep_parsed, &full_path)
        });
    });

    // Benchmark iteration over hash keys
    group.bench_function("iterate_mods_section", |b| {
        b.iter(|| {
            if let Some(mods) = ops.get_setting(&parsed, "mods") {
                if let Yaml::Hash(hash) = mods {
                    let count: usize = hash.iter().count();
                    count
                } else {
                    0
                }
            } else {
                0
            }
        });
    });

    group.finish();
}

// =============================================================================
// Modification Benchmarks
// =============================================================================

fn yaml_modification_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("yaml_modification");

    let content = generate_yaml_content(500);
    let ops = YamlOperations::new();
    let parsed = ops.parse_yaml(&content).expect("parse should succeed");

    // Benchmark updating existing value
    group.bench_function("set_setting_existing", |b| {
        b.iter(|| {
            ops.set_setting(&parsed, "settings.fcx_mode", Yaml::Boolean(false))
                .expect("set should succeed")
        });
    });

    // Benchmark creating new path
    group.bench_function("set_setting_new_path", |b| {
        b.iter(|| {
            ops.set_setting(
                &parsed,
                "new_section.subsection.value",
                Yaml::String("test".to_string()),
            )
            .expect("set should succeed")
        });
    });

    // Benchmark adding to nested structure
    group.bench_function("set_setting_deep_nested", |b| {
        b.iter(|| {
            ops.set_setting(
                &parsed,
                "mods.mod_0.extra.nested.deep.value",
                Yaml::Integer(42),
            )
            .expect("set should succeed")
        });
    });

    // Benchmark batch modifications (simulated)
    let paths = vec![
        ("settings.fcx_mode", Yaml::Boolean(true)),
        ("settings.show_formid_values", Yaml::Boolean(true)),
        ("settings.auto_scan", Yaml::Boolean(false)),
        ("settings.log_level", Yaml::String("DEBUG".to_string())),
        ("version", Yaml::String("9.0.0".to_string())),
    ];

    group.bench_function("batch_modifications_5_settings", |b| {
        b.iter(|| {
            let mut current = parsed.clone();
            for (path, value) in &paths {
                current = ops
                    .set_setting(&current, path, value.clone())
                    .expect("set should succeed");
            }
            current
        });
    });

    group.finish();
}

// =============================================================================
// Configuration Variants Benchmarks
// =============================================================================

fn yaml_config_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("yaml_config_variants");

    let content = generate_yaml_content(1000);

    // Default config
    let default_ops = YamlOperations::new();

    // Custom config with different formatting
    let custom_config = YamlFormatConfig {
        preserve_quotes: false,
        width: 80,
        indent_mapping: 4,
        indent_sequence: 4,
        indent_offset: 0,
    };
    let custom_ops = YamlOperations::with_config(custom_config);

    group.throughput(Throughput::Bytes(content.len() as u64));

    group.bench_function("parse_with_default_config", |b| {
        b.iter(|| {
            default_ops.parse_yaml(&content).expect("parse should succeed")
        });
    });

    group.bench_function("parse_with_custom_config", |b| {
        b.iter(|| {
            custom_ops.parse_yaml(&content).expect("parse should succeed")
        });
    });

    // Serialization with different configs
    let parsed = default_ops.parse_yaml(&content).expect("parse should succeed");

    group.bench_function("dump_with_default_config", |b| {
        b.iter(|| {
            default_ops.dump_yaml(&parsed).expect("dump should succeed")
        });
    });

    group.bench_function("dump_with_custom_config", |b| {
        b.iter(|| {
            custom_ops.dump_yaml(&parsed).expect("dump should succeed")
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
        yaml_parsing_benchmarks,
        yaml_serialization_benchmarks,
        yaml_traversal_benchmarks,
        yaml_modification_benchmarks,
        yaml_config_benchmarks
}

criterion_main!(benches);
