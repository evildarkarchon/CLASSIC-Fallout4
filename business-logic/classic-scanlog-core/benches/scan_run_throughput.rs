#![allow(missing_docs)]
//! Wall-clock throughput of whole Crash Log Scan Runs at several concurrency limits.
//!
//! This is the measurement behind audit card S5 ("scan concurrency gives no CPU
//! parallelism"). It drives the public `scan_run::contract::execute` entry point
//! exactly as the frontends do (one `block_on` on the shared runtime) over a
//! copy of the tracked `sample_logs/FO4` corpus and the shipped YAML Data, then
//! prints logs/second per `max_concurrent` value. If per-log work is truly
//! parallel, throughput should rise with the limit until it reaches the core
//! count. If every log is analysed on one thread, it plateaus early (around x2
//! when measured for S5), and only the overlap of file I/O between logs helps.
//!
//! It is a plain timing harness rather than a Criterion group because one sample
//! is a multi-second batch, and the interesting output is the ratio between
//! concurrency levels, not a statistically tight absolute time.
//!
//! ```bash
//! # Isolate the Installed YAML Data cache so a developer's updated YAML is not read.
//! LOCALAPPDATA=/tmp/classic-bench cargo bench -p classic-scanlog-core --bench scan_run_throughput
//!
//! # Knobs (all optional)
//! SCAN_RUN_BENCH_LOGS=400 SCAN_RUN_BENCH_CONCURRENCY=1,4,16 SCAN_RUN_BENCH_REPEATS=5 \
//!     cargo bench -p classic-scanlog-core --bench scan_run_throughput
//! ```

use classic_scanlog_core::CrashLogScanFacts;
use classic_scanlog_core::scan_run::TargetedCrashLogScanSource;
use classic_scanlog_core::scan_run::contract;
use classic_shared_core::{GameId, get_runtime};
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

const REPO_ROOT: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../..");

/// Reads a positive integer knob from the environment, falling back to `default`.
fn env_usize(name: &str, default: usize) -> usize {
    std::env::var(name)
        .ok()
        .and_then(|value| value.trim().parse::<usize>().ok())
        .filter(|value| *value > 0)
        .unwrap_or(default)
}

/// Returns the concurrency limits to measure, always including 1 as the baseline.
fn concurrency_levels() -> Vec<usize> {
    let cpus = std::thread::available_parallelism().map_or(4, |n| n.get());
    let mut levels = std::env::var("SCAN_RUN_BENCH_CONCURRENCY")
        .ok()
        .map(|raw| {
            raw.split(',')
                .filter_map(|part| part.trim().parse::<usize>().ok())
                .filter(|value| *value > 0)
                .collect::<Vec<_>>()
        })
        .filter(|levels| !levels.is_empty())
        .unwrap_or_else(|| vec![1, 2, 4, 8, cpus]);
    levels.push(1);
    levels.sort_unstable();
    levels.dedup();
    levels
}

/// Lists the first `count` tracked FO4 sample logs in a stable (sorted) order.
fn sample_logs(count: usize) -> Vec<PathBuf> {
    let corpus = Path::new(REPO_ROOT).join("sample_logs").join("FO4");
    let mut logs = std::fs::read_dir(&corpus)
        .unwrap_or_else(|error| panic!("{} should be readable: {error}", corpus.display()))
        .filter_map(|entry| entry.ok().map(|entry| entry.path()))
        .filter(|path| {
            path.file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name.starts_with("crash-") && name.ends_with(".log"))
        })
        .collect::<Vec<_>>();
    logs.sort();
    logs.truncate(count);
    assert!(
        !logs.is_empty(),
        "no crash-*.log files under {}",
        corpus.display()
    );
    logs
}

/// Builds one isolated installation root holding the shipped YAML Data and copies of `logs`.
///
/// Returns the temp dir (kept alive by the caller) and the copied log paths. The
/// copies matter: a Targeted run writes an Autoscan Report beside every input, and
/// the tracked corpus must not be touched.
fn materialize(logs: &[PathBuf]) -> (tempfile::TempDir, Vec<PathBuf>) {
    let root = tempfile::tempdir().expect("bench tempdir should be created");
    let databases = root.path().join("CLASSIC Data").join("databases");
    std::fs::create_dir_all(&databases).expect("bench database dir should be created");
    for name in ["CLASSIC Main.yaml", "CLASSIC Fallout4.yaml"] {
        std::fs::copy(
            Path::new(REPO_ROOT)
                .join("CLASSIC Data/databases")
                .join(name),
            databases.join(name),
        )
        .expect("shipped YAML Data should be copied");
    }
    // The shipped tree has no Ignore file; reuse the scan-run fixture's so the run
    // reads an existing Local Ignore instead of generating one inside the timing.
    std::fs::copy(
        Path::new(REPO_ROOT)
            .join("tests/fixtures/crash_log_scan_run/CLASSIC Data/CLASSIC Ignore.yaml"),
        root.path().join("CLASSIC Data").join("CLASSIC Ignore.yaml"),
    )
    .expect("fixture Ignore should be copied");

    let input_dir = root.path().join("input");
    std::fs::create_dir_all(&input_dir).expect("bench input dir should be created");
    let copies = logs
        .iter()
        .map(|source| {
            let target = input_dir.join(source.file_name().expect("log should have a name"));
            std::fs::copy(source, &target).expect("sample log should be copied");
            target
        })
        .collect();
    (root, copies)
}

/// Runs one Targeted scan over fresh copies and returns its wall time and success count.
fn run_once(logs: &[PathBuf], max_concurrent: usize) -> (Duration, usize, usize) {
    let (root, inputs) = materialize(logs);
    let request = contract::Request::targeted(
        contract::Configuration {
            installation_root: root.path().to_path_buf(),
            game: GameId::Fallout4,
            game_version: "auto".to_string(),
            options: contract::Options::new(false, false),
            scan_facts: CrashLogScanFacts::default(),
            max_concurrent: Some(max_concurrent),
        },
        TargetedCrashLogScanSource { inputs },
    );
    let started = Instant::now();
    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &contract::Cancellation::new(),
            None,
            contract::ObserverFailurePolicy::ContinueRun,
        ))
        .expect("bench scan run should complete");
    let elapsed = started.elapsed();
    assert_eq!(
        result.effective_concurrency,
        Some(max_concurrent),
        "an explicit limit should be used as the effective concurrency"
    );
    (elapsed, result.succeeded, result.failed)
}

fn main() {
    // `cargo bench` passes `--bench`; `cargo test --benches` passes nothing, and
    // `cargo bench -- --test` adds `--test`. Only a real bench invocation should pay
    // for multi-second scan batches, so the other two just prove the target builds.
    let args = std::env::args().collect::<Vec<_>>();
    if !args.iter().any(|arg| arg == "--bench") || args.iter().any(|arg| arg == "--test") {
        println!("scan_run_throughput: skipped outside a `cargo bench` run");
        return;
    }

    let log_count = env_usize("SCAN_RUN_BENCH_LOGS", 200);
    let repeats = env_usize("SCAN_RUN_BENCH_REPEATS", 3);
    let logs = sample_logs(log_count);
    let levels = concurrency_levels();
    println!(
        "scan_run_throughput: {} logs, {} repeats, runtime workers = available parallelism ({})",
        logs.len(),
        repeats,
        std::thread::available_parallelism().map_or(0, |n| n.get())
    );

    // Warm-up: first run pays YAML parsing, regex compilation, and page-cache misses.
    let _ = run_once(&logs, 1);

    let mut baseline = None;
    for level in levels {
        let mut samples = (0..repeats)
            .map(|_| run_once(&logs, level))
            .collect::<Vec<_>>();
        samples.sort_by_key(|(elapsed, _, _)| *elapsed);
        let (best, succeeded, failed) = samples[0];
        let median = samples[samples.len() / 2].0;
        let rate = logs.len() as f64 / best.as_secs_f64();
        let speedup = *baseline.get_or_insert(rate);
        println!(
            "max_concurrent={level:>3}  best={:>8.1} ms  median={:>8.1} ms  {:>7.1} logs/s  x{:.2} vs 1  (ok={succeeded}, failed={failed})",
            best.as_secs_f64() * 1e3,
            median.as_secs_f64() * 1e3,
            rate,
            rate / speedup,
        );
    }
}
