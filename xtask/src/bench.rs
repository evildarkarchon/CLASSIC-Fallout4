//! `cargo xtask bench percentiles | cleanup`: post-processing for Criterion
//! benchmark output under `target/criterion`.
//!
//! These replace the retired Python Criterion helpers (percentile extraction
//! and baseline cleanup). Running the benchmarks themselves stays with
//! `scripts/bench/run_benchmarks.ps1` and `compare_baselines.ps1`.
//!
//! - `percentiles` reads every `<bench-id>/new/raw.csv` and writes min, p50,
//!   p95, p99, max, mean and sample standard deviation of the per-iteration
//!   time to `percentiles.json`. `raw.csv` exists only when the benchmarking
//!   crate enables Criterion's `csv_output` feature, which no workspace crate
//!   does today; without it the subcommand fails with that precondition named.
//! - `cleanup` deletes all but the newest `--keep` baselines named
//!   `baseline-YYYY-MM-DD-HHMMSS` (the name `run_benchmarks.ps1 -SaveBaseline`
//!   generates when no name is given). Other baseline names are never touched.
//!
//! Two deliberate fixes over the Python helpers:
//!
//! - The unit column is kept as the string Criterion writes (`"ns"`). The
//!   Python helper called `float("ns")` and crashed on every valid `raw.csv`.
//! - Criterion saves a baseline per benchmark, as `<bench-id>/<baseline>/`,
//!   not as a top-level `target/criterion/<baseline>/`. `cleanup` therefore
//!   searches the whole tree and treats every directory sharing one baseline
//!   name as that baseline, so a baseline is kept or deleted as a unit across
//!   all benchmarks. The Python helper only looked at direct children of
//!   `target/criterion` and so never found a real baseline.
//!
//! Both subcommands return a one-line headline as the `Outcome::Pass` summary
//! and their human-readable report in its `report` field, since modules never
//! print; the binary prints the report on stdout after the `OK:` line.

use std::path::{Path, PathBuf};

use anyhow::{Context, Result};

use crate::{Outcome, RepoRoot};

mod cleanup;
mod percentiles;

/// Arguments for `bench`: which helper to run.
#[derive(Debug, Clone, clap::Args)]
pub struct Args {
    /// The bench helper to run.
    #[command(subcommand)]
    pub command: BenchCommand,
}

/// The `bench` helpers.
#[derive(Debug, Clone, clap::Subcommand)]
pub enum BenchCommand {
    /// Write p50/p95/p99 percentiles of each benchmark to a JSON file.
    ///
    /// Reads every `<bench-id>/new/raw.csv` under the Criterion directory and
    /// takes per-iteration time as `sample_measured_value / iteration_count`.
    ///
    /// Precondition: Criterion writes `raw.csv` only when the benchmarking
    /// crate enables Criterion's `csv_output` feature (no workspace crate does
    /// by default). Add it to that crate's `criterion` dev-dependency, run
    /// `cargo bench`, then run this command.
    Percentiles(PercentilesArgs),
    /// Delete old `baseline-YYYY-MM-DD-HHMMSS` Criterion baselines.
    ///
    /// Criterion stores each saved baseline inside every benchmark's
    /// directory (`<bench-id>/<baseline>/`); all directories with one baseline
    /// name are kept or deleted together. Other baseline names (for example
    /// `db-baseline-main`) are never touched. Dry run unless `--execute`.
    Cleanup(CleanupArgs),
}

/// Arguments for `bench percentiles`.
#[derive(Debug, Default, Clone, clap::Args)]
pub struct PercentilesArgs {
    /// Output JSON file [default: <criterion-dir>/percentiles.json].
    #[arg(long, short = 'o', value_name = "FILE")]
    pub output: Option<PathBuf>,

    /// Criterion results directory [default: <repo-root>/target/criterion].
    #[arg(long, value_name = "DIR")]
    pub criterion_dir: Option<PathBuf>,

    /// Print only the one-line summary, not the per-benchmark report.
    #[arg(long, short = 'q')]
    pub quiet: bool,
}

/// Arguments for `bench cleanup`.
#[derive(Debug, Clone, clap::Args)]
pub struct CleanupArgs {
    /// Actually delete old baselines (default: dry run).
    #[arg(long)]
    pub execute: bool,

    /// Number of most recent baselines to keep.
    #[arg(long, short = 'k', default_value_t = 10, value_name = "N")]
    pub keep: usize,

    /// Criterion results directory [default: <repo-root>/target/criterion].
    #[arg(long, value_name = "DIR")]
    pub criterion_dir: Option<PathBuf>,
}

impl Default for CleanupArgs {
    /// Matches the CLI defaults: dry run, keep 10.
    fn default() -> Self {
        Self {
            execute: false,
            keep: 10,
            criterion_dir: None,
        }
    }
}

/// Runs the selected bench helper over the repository at `root`.
///
/// Returns `Outcome::Pass` with a one-line headline and the helper's report
/// (no report for `percentiles --quiet`); neither helper produces findings.
///
/// # Errors
///
/// `percentiles` fails when the Criterion directory is missing, holds no
/// `new/raw.csv`, holds no usable sample, or the JSON cannot be written.
/// `cleanup` fails when the tree cannot be walked or a baseline directory
/// cannot be deleted (after attempting every deletion).
pub fn run(root: &RepoRoot, args: Args) -> Result<Outcome> {
    match args.command {
        BenchCommand::Percentiles(args) => percentiles::run(root, args),
        BenchCommand::Cleanup(args) => cleanup::run(root, args),
    }
}

/// Resolves the Criterion directory: `given` made absolute against the
/// current directory (as the Python helpers resolved it), or
/// `<repo-root>/target/criterion`.
fn criterion_dir(root: &RepoRoot, given: Option<&Path>) -> Result<PathBuf> {
    let dir = match given {
        Some(dir) => dir.to_path_buf(),
        // Joined per component so the path renders with native separators.
        None => root.path().join("target").join("criterion"),
    };
    absolute(&dir)
}

/// `std::path::absolute` with the path in the error message.
fn absolute(path: &Path) -> Result<PathBuf> {
    std::path::absolute(path).with_context(|| format!("resolving {}", path.display()))
}
