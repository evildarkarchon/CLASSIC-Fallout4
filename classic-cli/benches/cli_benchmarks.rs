use classic_cli::{CliConfig, OutputFormatter, PathConfig, ScanStats};
use criterion::{black_box, criterion_group, criterion_main, Criterion};
use std::path::PathBuf;
use std::time::Duration;
use tempfile::tempdir;
use tokio::runtime::Runtime;

/// Benchmark config creation
fn bench_config_creation(c: &mut Criterion) {
    c.bench_function("config_default_creation", |b| {
        b.iter(|| {
            let config = black_box(CliConfig::default());
            config
        })
    });
}

/// Benchmark config save/load cycle
fn bench_config_save_load(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();

    c.bench_function("config_save_load_cycle", |b| {
        b.to_async(&rt).iter(|| async {
            let temp_dir = tempdir().unwrap();
            let config_path = temp_dir.path().join("bench_config.yaml");

            let config = CliConfig::default();
            config.save_to_yaml(&config_path).await.unwrap();

            let loaded = CliConfig::load_from_yaml(&config_path).await.unwrap();
            black_box(loaded)
        });
    });
}

/// Benchmark YAML serialization
fn bench_yaml_serialization(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();

    c.bench_function("config_yaml_serialization", |b| {
        b.to_async(&rt).iter(|| async {
            let temp_dir = tempdir().unwrap();
            let config_path = temp_dir.path().join("serialize.yaml");

            let config = CliConfig {
                fcx_mode: true,
                show_formid_values: true,
                stat_logging: true,
                move_unsolved_logs: true,
                simplify_logs: false,
                update_check: true,
                paths: PathConfig {
                    ini_folder: Some(PathBuf::from("C:\\Test\\INI")),
                    scan_custom: Some(PathBuf::from("C:\\Test\\Logs")),
                    mods_folder: Some(PathBuf::from("C:\\Test\\Mods")),
                    game_root: PathBuf::from("C:\\Test\\Game"),
                },
            };

            config.save_to_yaml(&config_path).await.unwrap();
            black_box(())
        });
    });
}

/// Benchmark output formatter operations
fn bench_output_formatter(c: &mut Criterion) {
    c.bench_function("output_formatter_creation", |b| {
        b.iter(|| {
            let formatter = black_box(OutputFormatter::new());
            formatter
        })
    });

    c.bench_function("output_formatter_stats_display", |b| {
        b.iter(|| {
            let stats = ScanStats {
                scanned_logs: 47,
                patterns_matched: 234,
                formids_resolved: 1842,
                suspects_identified: 12,
            };
            // Would format stats for display
            black_box(stats)
        })
    });
}

/// Benchmark argument parsing simulation
fn bench_arg_parsing(c: &mut Criterion) {
    c.bench_function("cli_args_clone", |b| {
        b.iter(|| {
            let args = classic_cli::CliArgs {
                fcx_mode: true,
                show_fid_values: true,
                stat_logging: false,
                move_unsolved: false,
                ini_path: Some(PathBuf::from("C:\\Test")),
                scan_path: None,
                mods_folder_path: None,
                simplify_logs: false,
            };
            black_box(args)
        })
    });
}

/// Benchmark config merge operations
fn bench_config_merge(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();

    c.bench_function("config_merge_cli_args", |b| {
        b.to_async(&rt).iter(|| async {
            let temp_dir = tempdir().unwrap();
            let config_path = temp_dir.path().join("merge.yaml");

            // Create base config
            let mut config = CliConfig::default();
            config.save_to_yaml(&config_path).await.unwrap();

            // Simulate CLI args override
            let args = classic_cli::CliArgs {
                fcx_mode: true,
                show_fid_values: true,
                stat_logging: false,
                move_unsolved: false,
                ini_path: None,
                scan_path: None,
                mods_folder_path: None,
                simplify_logs: false,
            };

            // Load and merge
            let result = classic_cli::load_or_create_config(&config_path, &args)
                .await
                .unwrap();
            black_box(result)
        });
    });
}

/// Benchmark path validation
fn bench_path_validation(c: &mut Criterion) {
    let temp_dir = tempdir().unwrap();
    let valid_path = temp_dir.path().to_path_buf();

    c.bench_function("path_exists_check_valid", |b| {
        b.iter(|| {
            let exists = black_box(valid_path.exists());
            exists
        })
    });

    c.bench_function("path_exists_check_invalid", |b| {
        let invalid = PathBuf::from("C:\\NonExistent\\Path\\12345");
        b.iter(|| {
            let exists = black_box(invalid.exists());
            exists
        })
    });
}

/// Benchmark memory allocation patterns
fn bench_memory_patterns(c: &mut Criterion) {
    c.bench_function("vec_allocation_small", |b| {
        b.iter(|| {
            let v: Vec<String> = black_box(Vec::with_capacity(10));
            v
        })
    });

    c.bench_function("vec_allocation_large", |b| {
        b.iter(|| {
            let v: Vec<String> = black_box(Vec::with_capacity(1000));
            v
        })
    });

    c.bench_function("pathbuf_creation", |b| {
        b.iter(|| {
            let path = black_box(PathBuf::from("C:\\Test\\Long\\Path\\To\\File.txt"));
            path
        })
    });
}

/// Startup simulation benchmark (most critical metric)
fn bench_startup_simulation(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();

    let mut group = c.benchmark_group("startup");
    group.measurement_time(Duration::from_secs(10));

    group.bench_function("cold_start_simulation", |b| {
        b.to_async(&rt).iter(|| async {
            let temp_dir = tempdir().unwrap();
            let config_path = temp_dir.path().join("startup.yaml");

            // Simulate full startup: load config, parse args, initialize
            let args = classic_cli::CliArgs {
                fcx_mode: false,
                show_fid_values: false,
                stat_logging: false,
                move_unsolved: false,
                ini_path: None,
                scan_path: None,
                mods_folder_path: None,
                simplify_logs: false,
            };

            let config = classic_cli::load_or_create_config(&config_path, &args)
                .await
                .unwrap();
            let _formatter = OutputFormatter::new();

            black_box(config)
        });
    });

    group.finish();
}

criterion_group!(
    benches,
    bench_config_creation,
    bench_config_save_load,
    bench_yaml_serialization,
    bench_output_formatter,
    bench_arg_parsing,
    bench_config_merge,
    bench_path_validation,
    bench_memory_patterns,
    bench_startup_simulation
);

criterion_main!(benches);
