//! `bench percentiles`: tail percentiles from Criterion's `raw.csv` samples.
//!
//! Output matches the retired Python percentile helper (with its `float("ns")`
//! crash fixed) in key order, number formatting and report text, with these
//! deliberate differences:
//!
//! - Benchmarks are processed and written in sorted order, not filesystem
//!   order, so output is deterministic.
//! - The benchmark name is the path between the Criterion directory and
//!   `new/`. Python searched the absolute path for a part named `criterion`
//!   (falling back to the parent directory's name), which misnamed results
//!   when `--criterion-dir` was not called `criterion`.
//! - The JSON is written UTF-8 with LF line endings on every platform. Python
//!   escaped non-ASCII names and wrote CRLF on Windows.
//! - `mean` and `stddev` use compensated `f64` sums; Python's `statistics`
//!   module computes them through exact fractions, so a result can differ in
//!   the last unit of precision.
//! - An unreadable `raw.csv` is listed as skipped in the report (with the
//!   error) instead of a stderr warning, since modules never print.

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use serde::Serialize;
use walkdir::WalkDir;

use super::{PercentilesArgs, absolute, criterion_dir};
use crate::{Outcome, RepoRoot};

/// Hint appended to every "nothing to read" error.
const RUN_FIRST: &str = "Run benchmarks first: cargo bench";

/// Statistics for one benchmark, serialized in the Python helper's key order.
#[derive(Debug, Serialize)]
struct Stats {
    min: f64,
    p50: f64,
    p95: f64,
    p99: f64,
    max: f64,
    mean: f64,
    samples: usize,
    stddev: f64,
    /// Criterion's unit string, normally `"ns"`. Kept as a string: converting
    /// it to a number is the crash this port fixes.
    unit: String,
}

/// What became of one `raw.csv`.
enum Processed {
    Stats(Stats),
    /// No header, no rows, or no row with a usable sample.
    Empty,
    /// The file could not be read.
    Unreadable(String),
}

/// Runs `bench percentiles`; see the module docs.
pub(super) fn run(root: &RepoRoot, args: PercentilesArgs) -> Result<Outcome> {
    let dir = criterion_dir(root, args.criterion_dir.as_deref())?;
    if !dir.exists() {
        bail!(
            "Criterion directory not found: {}\n{RUN_FIRST}",
            dir.display()
        );
    }

    let csv_files = find_raw_csvs(&dir)?;
    if csv_files.is_empty() {
        bail!(
            "No raw.csv files found in {}\n{RUN_FIRST}, with Criterion's `csv_output` \
             feature enabled on the benchmarking crate's `criterion` dependency \
             (Criterion writes raw.csv only with that feature)",
            dir.display()
        );
    }

    let mut report = format!("Found {} benchmark(s) to process...\n", csv_files.len());
    let mut results = BTreeMap::new();
    let mut skipped = 0usize;
    for path in &csv_files {
        let name = benchmark_name(&dir, path);
        match process_raw_csv(path) {
            Processed::Stats(stats) => {
                let _ = writeln!(report, "  Processed: {name}");
                results.insert(name, stats);
            }
            Processed::Empty => {
                skipped += 1;
                let _ = writeln!(report, "  Skipped (empty/invalid): {name}");
            }
            Processed::Unreadable(error) => {
                skipped += 1;
                let _ = writeln!(report, "  Skipped (unreadable: {error}): {name}");
            }
        }
    }
    if results.is_empty() {
        bail!("No valid benchmark data found.\n{}", report.trim_end());
    }

    let output = match &args.output {
        Some(output) => absolute(output)?,
        None => dir.join("percentiles.json"),
    };
    // `to_string_pretty` matches Python's `json.dump(indent=2)` layout,
    // including the missing trailing newline.
    let json = serde_json::to_string_pretty(&results).context("serializing percentiles")?;
    fs::write(&output, json).with_context(|| format!("writing {}", output.display()))?;

    let mut headline = format!(
        "bench percentiles: wrote {} benchmark(s) to {}",
        results.len(),
        output.display()
    );
    if skipped > 0 {
        let _ = write!(headline, " ({skipped} skipped)");
    }
    if args.quiet {
        return Ok(Outcome::Pass {
            summary: headline,
            report: None,
        });
    }

    let rule = "=".repeat(70);
    let _ = write!(report, "\n{rule}\nBenchmark Percentile Summary\n{rule}\n");
    for (name, stats) in &results {
        let _ = write!(
            report,
            "\n{name}:\n  Samples:  {}\n  Min:      {}\n  P50:      {}\n  P95:      {}\n  \
             P99:      {}\n  Max:      {}\n  Mean:     {}\n  Stddev:   {}\n",
            stats.samples,
            format_time(stats.min),
            format_time(stats.p50),
            format_time(stats.p95),
            format_time(stats.p99),
            format_time(stats.max),
            format_time(stats.mean),
            format_time(stats.stddev),
        );
    }
    let _ = write!(
        report,
        "\n{rule}\n\nResults written to: {}",
        output.display()
    );
    Ok(Outcome::Pass {
        summary: headline,
        report: Some(report),
    })
}

/// Every `raw.csv` whose parent directory is `new` (Criterion's latest
/// sample), sorted by path. Saved baselines also hold a `raw.csv`; those are
/// not the current run and are skipped.
fn find_raw_csvs(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut files = Vec::new();
    for entry in WalkDir::new(dir).sort_by_file_name() {
        let entry = entry.with_context(|| format!("walking {}", dir.display()))?;
        let path = entry.path();
        let in_new = path
            .parent()
            .and_then(Path::file_name)
            .is_some_and(|parent| parent == "new");
        if entry.file_type().is_file() && entry.file_name() == "raw.csv" && in_new {
            files.push(entry.into_path());
        }
    }
    Ok(files)
}

/// The benchmark id: the path components between `dir` and `new/raw.csv`,
/// joined with `/` (for example `group/function/value`).
fn benchmark_name(dir: &Path, csv: &Path) -> String {
    let bench_dir = csv.parent().and_then(Path::parent).unwrap_or(csv);
    bench_dir
        .strip_prefix(dir)
        .unwrap_or(bench_dir)
        .components()
        .map(|component| component.as_os_str().to_string_lossy())
        .collect::<Vec<_>>()
        .join("/")
}

/// Reads one `raw.csv` the way Python's `csv.DictReader` did: the first record
/// is the header, rows are matched to it by position, and a row missing a
/// column or holding an unparseable number is skipped.
fn process_raw_csv(path: &Path) -> Processed {
    let bytes = match fs::read(path) {
        Ok(bytes) => bytes,
        Err(error) => return Processed::Unreadable(error.to_string()),
    };
    let text = String::from_utf8_lossy(&bytes);
    let mut records = parse_csv(&text).into_iter();
    let Some(header) = records.next() else {
        return Processed::Empty;
    };
    // A duplicated header name maps to its last column, as in a Python dict.
    let column = |name: &str| header.iter().rposition(|field| field == name);
    let value_col = column("sample_measured_value");
    let count_col = column("iteration_count");
    let unit_col = column("unit");

    let mut times = Vec::new();
    // Criterion's wall-time unit; used when no row carries a `unit` column.
    let mut unit = String::from("ns");
    for row in records {
        let field = |col: Option<usize>| col.and_then(|col| row.get(col));
        let Some(value) = field(value_col).and_then(|v| parse_float(v)) else {
            continue;
        };
        let Some(count) = field(count_col).and_then(|c| parse_int(c)) else {
            continue;
        };
        if count > 0 {
            times.push(value / count as f64);
        }
        if let Some(row_unit) = field(unit_col) {
            unit.clone_from(row_unit);
        }
    }
    if times.is_empty() {
        return Processed::Empty;
    }
    Processed::Stats(calculate(times, unit))
}

/// Percentiles by linear interpolation between closest ranks, plus mean and
/// sample standard deviation (0 for a single sample), as the Python helper
/// computed them.
fn calculate(mut values: Vec<f64>, unit: String) -> Stats {
    values.sort_by(f64::total_cmp);
    let n = values.len();
    let percentile = |p: f64| {
        if n == 1 {
            return values[0];
        }
        let rank = (p / 100.0) * (n - 1) as f64;
        // Truncation, like Python's `int(rank)` on a non-negative float.
        let lower = rank as usize;
        let upper = (lower + 1).min(n - 1);
        let weight = rank - lower as f64;
        values[lower] * (1.0 - weight) + values[upper] * weight
    };
    let mean = compensated_sum(values.iter().copied()) / n as f64;
    let stddev = if n >= 2 {
        let squares = compensated_sum(values.iter().map(|value| (value - mean).powi(2)));
        (squares / (n - 1) as f64).sqrt()
    } else {
        0.0
    };
    Stats {
        min: values[0],
        p50: percentile(50.0),
        p95: percentile(95.0),
        p99: percentile(99.0),
        max: values[n - 1],
        mean,
        samples: n,
        stddev,
        unit,
    }
}

/// Neumaier-compensated sum, close to Python's exact `statistics` sums.
fn compensated_sum(values: impl Iterator<Item = f64>) -> f64 {
    let mut sum = 0.0_f64;
    let mut compensation = 0.0_f64;
    for value in values {
        let total = sum + value;
        if sum.abs() >= value.abs() {
            compensation += (sum - total) + value;
        } else {
            compensation += (value - total) + sum;
        }
        sum = total;
    }
    sum + compensation
}

/// Python `float(text)` for the forms Criterion can write: surrounding
/// whitespace is ignored.
fn parse_float(text: &str) -> Option<f64> {
    text.trim().parse().ok()
}

/// Python `int(text)` for the forms Criterion can write: surrounding
/// whitespace is ignored.
fn parse_int(text: &str) -> Option<i64> {
    text.trim().parse().ok()
}

/// Splits `text` into records with Python's default `csv` dialect: comma
/// delimiter, `"` quoting with `""` as an escaped quote, quoted fields may hold
/// commas and newlines, and blank lines are skipped.
fn parse_csv(text: &str) -> Vec<Vec<String>> {
    let mut records = Vec::new();
    let mut record: Vec<String> = Vec::new();
    let mut field = String::new();
    // True once the current line has any content, so a blank line is skipped
    // rather than read as a record with one empty field.
    let mut started = false;
    let mut in_quotes = false;
    let mut chars = text.chars().peekable();
    while let Some(ch) = chars.next() {
        if in_quotes {
            if ch == '"' {
                if chars.peek() == Some(&'"') {
                    chars.next();
                    field.push('"');
                } else {
                    in_quotes = false;
                }
            } else {
                field.push(ch);
            }
            continue;
        }
        match ch {
            '"' if field.is_empty() => {
                in_quotes = true;
                started = true;
            }
            ',' => {
                record.push(std::mem::take(&mut field));
                started = true;
            }
            '\r' | '\n' => {
                if ch == '\r' && chars.peek() == Some(&'\n') {
                    chars.next();
                }
                if started {
                    record.push(std::mem::take(&mut field));
                    records.push(std::mem::take(&mut record));
                }
                started = false;
            }
            _ => {
                field.push(ch);
                started = true;
            }
        }
    }
    if started {
        record.push(field);
        records.push(record);
    }
    records
}

/// Nanoseconds as `ns`, `us`, `ms` or `s` with two decimals, as the Python
/// report printed them.
fn format_time(ns: f64) -> String {
    if ns < 1_000.0 {
        format!("{ns:.2} ns")
    } else if ns < 1_000_000.0 {
        format!("{:.2} us", ns / 1_000.0)
    } else if ns < 1_000_000_000.0 {
        format!("{:.2} ms", ns / 1_000_000.0)
    } else {
        format!("{:.2} s", ns / 1_000_000_000.0)
    }
}
