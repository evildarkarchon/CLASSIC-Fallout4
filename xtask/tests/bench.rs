//! Fixture-tree tests for `cargo xtask bench percentiles | cleanup`, driven
//! through `bench::run` (the subcommand seam), plus the binary's usage errors.
//!
//! Expected numbers and report text come from the retired Python helpers run
//! over the same trees (the percentile helper patched only to stop calling
//! `float("ns")`), not from re-deriving them here.

mod common;

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use common::FixtureRepo;
use xtask::Outcome;
use xtask::bench::{self, Args, BenchCommand, CleanupArgs, PercentilesArgs};

/// Header row Criterion's `csv_output` feature writes to every `raw.csv`.
const HEADER: &str = "group,function,value,throughput_num,throughput_type,sample_measured_value,unit,iteration_count";

/// The fixture's Criterion output directory, built component by component so
/// it renders with native separators on every platform.
fn criterion_dir(repo: &FixtureRepo) -> PathBuf {
    repo.path().join("target").join("criterion")
}

/// Writes a `raw.csv` with `rows` (after the header) under `bench_dir`.
fn raw_csv(repo: FixtureRepo, bench_dir: &str, rows: &[&str]) -> FixtureRepo {
    let mut text = format!("{HEADER}\n");
    for row in rows {
        text.push_str(row);
        text.push('\n');
    }
    repo.file(&format!("target/criterion/{bench_dir}/raw.csv"), &text)
}

/// A Criterion tree with a nested benchmark id, a flat one with a quoted
/// group name and malformed rows, a header-only one, and a saved `base`
/// sample that must be ignored.
fn percentile_tree() -> FixtureRepo {
    let repo = raw_csv(
        FixtureRepo::empty(),
        "grp/func/param/new",
        &[
            "grp,func,param,,,1000.0,ns,10",
            "grp,func,param,,,2200.0,ns,20",
            "grp,func,param,,,3600.0,ns,30",
            "grp,func,param,,,5200.0,ns,40",
            "grp,func,param,,,7000.0,ns,50",
        ],
    );
    let repo = raw_csv(
        repo,
        "flat_bench/new",
        &[
            "\"flat, bench\",,,,,1500000.0,ns,1000",
            "\"flat, bench\",,,,,abc,ns,1000",
            "\"flat, bench\",,,,,99.0,ns,0",
            "\"flat, bench\",,,,,3000000.0,ns,1000",
        ],
    );
    let repo = raw_csv(repo, "flat_bench/base", &["x,,,,,1.0,ns,1"]);
    raw_csv(repo, "empty_bench/new", &[])
}

fn percentiles(repo: &FixtureRepo, args: PercentilesArgs) -> anyhow::Result<Outcome> {
    bench::run(
        &repo.root(),
        Args {
            command: BenchCommand::Percentiles(args),
        },
    )
}

fn cleanup(repo: &FixtureRepo, args: CleanupArgs) -> anyhow::Result<Outcome> {
    bench::run(
        &repo.root(),
        Args {
            command: BenchCommand::Cleanup(args),
        },
    )
}

/// The `Pass` summary, failing the test on anything else.
fn pass_summary(outcome: anyhow::Result<Outcome>) -> String {
    match outcome.expect("bench runs") {
        Outcome::Pass { summary } => summary,
        other => panic!("expected a pass, got {other:?}"),
    }
}

/// The operational error's full message, failing the test on success.
fn error_text(outcome: anyhow::Result<Outcome>) -> String {
    format!("{:#}", outcome.expect_err("bench fails"))
}

/// Byte-exact `percentiles.json` the patched Python helper writes for
/// `percentile_tree` (it writes CRLF on Windows; xtask always writes LF).
const PERCENTILES_JSON: &str = r#"{
  "flat_bench": {
    "min": 1500.0,
    "p50": 2250.0,
    "p95": 2925.0,
    "p99": 2985.0,
    "max": 3000.0,
    "mean": 2250.0,
    "samples": 2,
    "stddev": 1060.6601717798212,
    "unit": "ns"
  },
  "grp/func/param": {
    "min": 100.0,
    "p50": 120.0,
    "p95": 138.0,
    "p99": 139.60000000000002,
    "max": 140.0,
    "mean": 120.0,
    "samples": 5,
    "stddev": 15.811388300841896,
    "unit": "ns"
  }
}"#;

#[test]
fn percentiles_keep_criterions_string_unit_instead_of_crashing() {
    // Regression test for the retired helper's `float("ns")` crash: every
    // valid raw.csv carries the string unit "ns".
    let repo = percentile_tree();

    pass_summary(percentiles(&repo, PercentilesArgs::default()));

    let written = fs::read_to_string(criterion_dir(&repo).join("percentiles.json")).unwrap();
    assert_eq!(written, PERCENTILES_JSON);
}

#[test]
fn percentiles_report_matches_the_python_summary() {
    let repo = percentile_tree();
    let output = criterion_dir(&repo).join("percentiles.json");

    let summary = pass_summary(percentiles(&repo, PercentilesArgs::default()));

    let rule = "=".repeat(70);
    let expected = format!(
        "bench percentiles: wrote 2 benchmark(s) to {out} (1 skipped)\n\
         Found 3 benchmark(s) to process...\n\
         \x20 Skipped (empty/invalid): empty_bench\n\
         \x20 Processed: flat_bench\n\
         \x20 Processed: grp/func/param\n\
         \n{rule}\nBenchmark Percentile Summary\n{rule}\n\
         \nflat_bench:\n\
         \x20 Samples:  2\n\
         \x20 Min:      1.50 us\n\
         \x20 P50:      2.25 us\n\
         \x20 P95:      2.92 us\n\
         \x20 P99:      2.98 us\n\
         \x20 Max:      3.00 us\n\
         \x20 Mean:     2.25 us\n\
         \x20 Stddev:   1.06 us\n\
         \ngrp/func/param:\n\
         \x20 Samples:  5\n\
         \x20 Min:      100.00 ns\n\
         \x20 P50:      120.00 ns\n\
         \x20 P95:      138.00 ns\n\
         \x20 P99:      139.60 ns\n\
         \x20 Max:      140.00 ns\n\
         \x20 Mean:     120.00 ns\n\
         \x20 Stddev:   15.81 ns\n\
         \n{rule}\n\
         \nResults written to: {out}",
        out = output.display()
    );
    assert_eq!(summary, expected);
}

#[test]
fn percentiles_quiet_keeps_only_the_headline_and_honours_output() {
    let repo = percentile_tree();
    let output = repo.path().join("out.json");

    let summary = pass_summary(percentiles(
        &repo,
        PercentilesArgs {
            output: Some(output.clone()),
            quiet: true,
            ..PercentilesArgs::default()
        },
    ));

    assert_eq!(
        summary,
        format!(
            "bench percentiles: wrote 2 benchmark(s) to {} (1 skipped)",
            output.display()
        )
    );
    assert_eq!(fs::read_to_string(&output).unwrap(), PERCENTILES_JSON);
    assert!(!criterion_dir(&repo).join("percentiles.json").exists());
}

#[test]
fn percentiles_read_an_explicit_criterion_dir() {
    let repo = raw_csv(
        FixtureRepo::empty(),
        "elsewhere/one/new",
        &["one,,,,,5.0,ns,1"],
    );
    // Not the default `target/criterion`, so the benchmark name is `one`.
    let dir = criterion_dir(&repo).join("elsewhere");

    let summary = pass_summary(percentiles(
        &repo,
        PercentilesArgs {
            criterion_dir: Some(dir.clone()),
            quiet: true,
            ..PercentilesArgs::default()
        },
    ));

    let output = dir.join("percentiles.json");
    assert_eq!(
        summary,
        format!(
            "bench percentiles: wrote 1 benchmark(s) to {}",
            output.display()
        )
    );
    let written = fs::read_to_string(output).unwrap();
    assert!(
        written.starts_with("{\n  \"one\": {\n    \"min\": 5.0,"),
        "{written}"
    );
    assert!(
        written.contains("\"stddev\": 0.0,\n    \"unit\": \"ns\""),
        "{written}"
    );
}

#[test]
fn percentiles_fail_operationally_without_usable_input() {
    let missing = FixtureRepo::empty();
    let text = error_text(percentiles(&missing, PercentilesArgs::default()));
    assert!(text.contains("Criterion directory not found"), "{text}");
    assert!(text.contains("cargo bench"), "{text}");

    // Without Criterion's `csv_output` feature there is never a raw.csv; the
    // error names the precondition instead of a bare "not found".
    let no_csv = FixtureRepo::empty().file("target/criterion/b/new/estimates.json", "{}");
    let text = error_text(percentiles(&no_csv, PercentilesArgs::default()));
    assert!(text.contains("No raw.csv files found"), "{text}");
    assert!(text.contains("csv_output"), "{text}");

    let invalid = raw_csv(FixtureRepo::empty(), "b/new", &["b,,,,,abc,ns,1"]);
    let text = error_text(percentiles(&invalid, PercentilesArgs::default()));
    assert!(text.contains("No valid benchmark data found"), "{text}");
}

/// Writes a three-byte `estimates.json` into each Criterion directory in `dirs`.
fn baseline_tree(dirs: &[&str]) -> FixtureRepo {
    dirs.iter().fold(FixtureRepo::empty(), |repo, dir| {
        repo.file(&format!("target/criterion/{dir}/estimates.json"), "abc")
    })
}

/// Criterion's real layout: each saved baseline is a directory inside every
/// benchmark's own directory, next to `new` and `base`.
fn per_benchmark_tree() -> FixtureRepo {
    baseline_tree(&[
        "grp/func/param/new",
        "grp/func/param/base",
        "grp/func/param/baseline-2026-01-01-000000",
        "grp/func/param/baseline-2026-02-01-000000",
        "grp/func/param/baseline-2026-03-01-120000",
        "grp/func/param/db-baseline-main",
        "grp/func/param/baseline-2026-13-01-000000",
        "flat_bench/new",
        "flat_bench/baseline-2026-01-01-000000",
        "flat_bench/baseline-2026-03-01-120000",
        "report",
    ])
}

fn exists(repo: &FixtureRepo, dir: &str) -> bool {
    criterion_dir(repo).join(Path::new(dir)).is_dir()
}

#[test]
fn cleanup_finds_baselines_inside_each_benchmark_directory() {
    // The retired helper only scanned direct children of target/criterion and
    // reported "No baselines found" for this tree.
    let repo = per_benchmark_tree();

    let summary = pass_summary(cleanup(
        &repo,
        CleanupArgs {
            keep: 1,
            ..CleanupArgs::default()
        },
    ));

    assert_eq!(
        summary,
        format!(
            "bench cleanup: dry run, would delete 2 of 3 baseline(s)\n\
             Found 3 baseline(s) in {dir}\n\
             Keeping the 1 most recent\n\
             \n\
             Baselines to KEEP:\n\
             \x20 [KEEP]   baseline-2026-03-01-120000  (2026-03-01 12:00:00, 6.0 B)\n\
             \n\
             Baselines to DELETE:\n\
             \x20 [WOULD DELETE] baseline-2026-01-01-000000  (2026-01-01 00:00:00, 6.0 B)\n\
             \x20 [WOULD DELETE] baseline-2026-02-01-000000  (2026-02-01 00:00:00, 3.0 B)\n\
             \n\
             Would delete 2 baseline(s) (9.0 B total)\n\
             \n\
             Run with --execute to actually delete these baselines.",
            dir = criterion_dir(&repo).display()
        )
    );
    // A dry run deletes nothing.
    assert!(exists(&repo, "grp/func/param/baseline-2026-01-01-000000"));
    assert!(exists(&repo, "flat_bench/baseline-2026-01-01-000000"));
}

#[test]
fn cleanup_execute_deletes_old_baselines_from_every_benchmark() {
    let repo = per_benchmark_tree();

    let summary = pass_summary(cleanup(
        &repo,
        CleanupArgs {
            keep: 1,
            execute: true,
            ..CleanupArgs::default()
        },
    ));

    assert!(
        summary.starts_with("bench cleanup: deleted 2 of 3 baseline(s)\n"),
        "{summary}"
    );
    // Sizes are measured before deletion, so the report shows what was freed.
    assert!(
        summary.contains(
            "\x20 [DELETED] baseline-2026-01-01-000000  (2026-01-01 00:00:00, 6.0 B)\n\
             \x20 [DELETED] baseline-2026-02-01-000000  (2026-02-01 00:00:00, 3.0 B)\n\
             \nDeleted 2 baseline(s)"
        ),
        "{summary}"
    );
    for gone in [
        "grp/func/param/baseline-2026-01-01-000000",
        "grp/func/param/baseline-2026-02-01-000000",
        "flat_bench/baseline-2026-01-01-000000",
    ] {
        assert!(!exists(&repo, gone), "{gone} should be deleted");
    }
    for kept in [
        "grp/func/param/new",
        "grp/func/param/base",
        "grp/func/param/baseline-2026-03-01-120000",
        "grp/func/param/db-baseline-main",
        "grp/func/param/baseline-2026-13-01-000000",
        "flat_bench/new",
        "flat_bench/baseline-2026-03-01-120000",
        "report",
    ] {
        assert!(exists(&repo, kept), "{kept} should be kept");
    }
}

#[test]
fn cleanup_still_handles_top_level_baselines_and_invalid_dates() {
    // The layout the retired helper assumed; output matches it line for line.
    let repo = baseline_tree(&[
        "baseline-2026-01-01-000000",
        "baseline-2026-02-01-000000",
        "baseline-2026-03-01-120000",
        "baseline-2026-02-30-000000",
        "base",
    ]);

    let summary = pass_summary(cleanup(
        &repo,
        CleanupArgs {
            keep: 1,
            ..CleanupArgs::default()
        },
    ));

    assert_eq!(
        summary,
        format!(
            "bench cleanup: dry run, would delete 2 of 3 baseline(s)\n\
             Found 3 baseline(s) in {dir}\n\
             Keeping the 1 most recent\n\
             \n\
             Baselines to KEEP:\n\
             \x20 [KEEP]   baseline-2026-03-01-120000  (2026-03-01 12:00:00, 3.0 B)\n\
             \n\
             Baselines to DELETE:\n\
             \x20 [WOULD DELETE] baseline-2026-01-01-000000  (2026-01-01 00:00:00, 3.0 B)\n\
             \x20 [WOULD DELETE] baseline-2026-02-01-000000  (2026-02-01 00:00:00, 3.0 B)\n\
             \n\
             Would delete 2 baseline(s) (6.0 B total)\n\
             \n\
             Run with --execute to actually delete these baselines.",
            dir = criterion_dir(&repo).display()
        )
    );
}

#[test]
fn cleanup_passes_when_there_is_nothing_to_delete() {
    let missing = FixtureRepo::empty();
    assert_eq!(
        pass_summary(cleanup(&missing, CleanupArgs::default())),
        format!(
            "bench cleanup: no baselines to clean up\n\
             Criterion directory not found: {}\n\
             No baselines to clean up.",
            criterion_dir(&missing).display()
        )
    );

    let none = baseline_tree(&["b/new", "b/db-baseline-main"]);
    assert_eq!(
        pass_summary(cleanup(&none, CleanupArgs::default())),
        "bench cleanup: no baselines to clean up\n\
         No baselines found matching pattern: baseline-YYYY-MM-DD-HHMMSS"
    );

    // The default keeps 10, so two baselines are both kept.
    let few = baseline_tree(&[
        "b/baseline-2026-01-01-000000",
        "b/baseline-2026-01-02-000000",
    ]);
    let summary = pass_summary(cleanup(&few, CleanupArgs::default()));
    assert!(
        summary.starts_with("bench cleanup: dry run, would delete 0 of 2 baseline(s)\n"),
        "{summary}"
    );
    assert!(
        summary.ends_with("\nNo baselines need to be deleted."),
        "{summary}"
    );
}

fn xtask(args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_xtask"))
        .args(args)
        .output()
        .expect("run the xtask binary")
}

#[test]
fn bench_usage_errors_exit_with_2_and_help_names_the_csv_precondition() {
    assert_eq!(xtask(&["bench"]).status.code(), Some(2));
    assert_eq!(
        xtask(&["bench", "cleanup", "--keep", "-1"]).status.code(),
        Some(2)
    );

    let help = xtask(&["bench", "percentiles", "--help"]);
    assert_eq!(help.status.code(), Some(0));
    let text = String::from_utf8_lossy(&help.stdout);
    assert!(text.contains("csv_output"), "{text}");
}
