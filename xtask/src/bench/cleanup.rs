//! `bench cleanup`: delete all but the newest timestamped Criterion baselines.
//!
//! Report text matches the retired Python baseline-cleanup helper, with these
//! deliberate differences:
//!
//! - Baselines are found anywhere in the tree (Criterion's real
//!   `<bench-id>/<baseline>/` layout), grouped by name; see the `bench` module
//!   docs.
//! - Deleted baselines report the size they freed; Python measured them after
//!   deletion and always printed `0.0 B`.
//! - A failed deletion is an operational failure (exit 1) once every deletion
//!   has been attempted; Python printed it and exited 0.
//! - A negative `--keep` is a usage error (exit 2) from argument parsing.

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use walkdir::WalkDir;

use super::{CleanupArgs, criterion_dir};
use crate::{Outcome, RepoRoot};

/// Headline for every run that finds nothing to consider.
const NOTHING: &str = "bench cleanup: no baselines to clean up";

/// One baseline name and every benchmark directory saved under it.
struct Baseline {
    timestamp: Timestamp,
    dirs: Vec<PathBuf>,
}

/// The UTC time encoded in a `baseline-YYYY-MM-DD-HHMMSS` name.
#[derive(Debug, Clone, Copy)]
struct Timestamp {
    year: u32,
    month: u32,
    day: u32,
    hour: u32,
    minute: u32,
    second: u32,
}

/// Runs `bench cleanup`; see the module docs.
pub(super) fn run(root: &RepoRoot, args: CleanupArgs) -> Result<Outcome> {
    let dir = criterion_dir(root, args.criterion_dir.as_deref())?;
    if !dir.exists() {
        return Ok(Outcome::Pass {
            summary: format!(
                "{NOTHING}\nCriterion directory not found: {}\nNo baselines to clean up.",
                dir.display()
            ),
        });
    }

    let baselines = find_baselines(&dir)?;
    if baselines.is_empty() {
        return Ok(Outcome::Pass {
            summary: format!(
                "{NOTHING}\nNo baselines found matching pattern: baseline-YYYY-MM-DD-HHMMSS"
            ),
        });
    }

    // `find_baselines` returns a map keyed by name, and the fixed-width,
    // zero-padded name sorts exactly like its timestamp: oldest first.
    let total = baselines.len();
    let delete_count = total.saturating_sub(args.keep);
    let mut entries: Vec<(String, Baseline)> = baselines.into_iter().collect();
    let to_keep = entries.split_off(delete_count);
    let to_delete = entries;

    let mut report = format!(
        "Found {total} baseline(s) in {}\nKeeping the {} most recent\n\n",
        dir.display(),
        args.keep
    );
    if !to_keep.is_empty() {
        report.push_str("Baselines to KEEP:\n");
        for (name, baseline) in &to_keep {
            let _ = writeln!(
                report,
                "  [KEEP]   {name}  ({}, {})",
                baseline.timestamp,
                format_size(size_of(&baseline.dirs))
            );
        }
        report.push('\n');
    }

    if to_delete.is_empty() {
        report.push_str("No baselines need to be deleted.");
    } else {
        let action = if args.execute {
            "DELETED"
        } else {
            "WOULD DELETE"
        };
        report.push_str("Baselines to DELETE:\n");
        let mut freed = 0u64;
        let mut failures = Vec::new();
        for (name, baseline) in &to_delete {
            // Measured before deleting, so the report shows what was freed.
            let size = size_of(&baseline.dirs);
            freed += size;
            if args.execute {
                for dir in &baseline.dirs {
                    if let Err(error) = fs::remove_dir_all(dir) {
                        failures.push(format!("{}: {error}", dir.display()));
                    }
                }
            }
            let _ = writeln!(
                report,
                "  [{action}] {name}  ({}, {})",
                baseline.timestamp,
                format_size(size)
            );
        }
        if !failures.is_empty() {
            bail!(
                "failed to delete {} baseline director(ies):\n  {}",
                failures.len(),
                failures.join("\n  ")
            );
        }
        report.push('\n');
        if args.execute {
            let _ = write!(report, "Deleted {} baseline(s)", to_delete.len());
        } else {
            let _ = write!(
                report,
                "Would delete {} baseline(s) ({} total)\n\n\
                 Run with --execute to actually delete these baselines.",
                to_delete.len(),
                format_size(freed)
            );
        }
    }

    let headline = if args.execute {
        format!("bench cleanup: deleted {delete_count} of {total} baseline(s)")
    } else {
        format!("bench cleanup: dry run, would delete {delete_count} of {total} baseline(s)")
    };
    Ok(Outcome::Pass {
        summary: format!("{headline}\n{report}"),
    })
}

/// Every directory under `dir` named `baseline-YYYY-MM-DD-HHMMSS` with a real
/// calendar date, grouped by name. A matching directory's contents are not
/// searched further.
fn find_baselines(dir: &Path) -> Result<BTreeMap<String, Baseline>> {
    let mut baselines: BTreeMap<String, Baseline> = BTreeMap::new();
    let mut walk = WalkDir::new(dir)
        .min_depth(1)
        .sort_by_file_name()
        .into_iter();
    while let Some(entry) = walk.next() {
        let entry = entry.with_context(|| format!("walking {}", dir.display()))?;
        // Symlinks are not followed, so a linked directory is never deleted.
        if !entry.file_type().is_dir() {
            continue;
        }
        let Some(name) = entry.file_name().to_str() else {
            continue;
        };
        let Some(timestamp) = parse_baseline_name(name) else {
            continue;
        };
        let name = name.to_owned();
        walk.skip_current_dir();
        baselines
            .entry(name)
            .or_insert_with(|| Baseline {
                timestamp,
                dirs: Vec::new(),
            })
            .dirs
            .push(entry.into_path());
    }
    Ok(baselines)
}

/// Parses `baseline-YYYY-MM-DD-HHMMSS` (ASCII digits) into a valid UTC time;
/// impossible dates such as month 13 or February 30 are not baselines.
fn parse_baseline_name(name: &str) -> Option<Timestamp> {
    let rest = name.strip_prefix("baseline-")?.as_bytes();
    let separators_ok = rest.len() == 17 && rest[4] == b'-' && rest[7] == b'-' && rest[10] == b'-';
    if !separators_ok {
        return None;
    }
    let number = |range: std::ops::Range<usize>| -> Option<u32> {
        let digits = &rest[range];
        if !digits.iter().all(u8::is_ascii_digit) {
            return None;
        }
        Some(
            digits
                .iter()
                .fold(0, |acc, d| acc * 10 + u32::from(d - b'0')),
        )
    };
    let timestamp = Timestamp {
        year: number(0..4)?,
        month: number(5..7)?,
        day: number(8..10)?,
        hour: number(11..13)?,
        minute: number(13..15)?,
        second: number(15..17)?,
    };
    timestamp.is_valid().then_some(timestamp)
}

impl Timestamp {
    /// The range Python's `datetime` accepts (year 1 or later).
    fn is_valid(&self) -> bool {
        let leap = (self.year.is_multiple_of(4) && !self.year.is_multiple_of(100))
            || self.year.is_multiple_of(400);
        let days_in_month = match self.month {
            1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
            4 | 6 | 9 | 11 => 30,
            2 if leap => 29,
            2 => 28,
            _ => return false,
        };
        self.year >= 1
            && (1..=days_in_month).contains(&self.day)
            && self.hour < 24
            && self.minute < 60
            && self.second < 60
    }
}

impl std::fmt::Display for Timestamp {
    /// `YYYY-MM-DD HH:MM:SS`, as the Python report printed it.
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{:04}-{:02}-{:02} {:02}:{:02}:{:02}",
            self.year, self.month, self.day, self.hour, self.minute, self.second
        )
    }
}

/// Total bytes of the files under `dirs`. Unreadable entries count as zero:
/// the size is informational and must not block a cleanup.
fn size_of(dirs: &[PathBuf]) -> u64 {
    dirs.iter()
        .flat_map(WalkDir::new)
        .filter_map(Result::ok)
        .filter(|entry| entry.file_type().is_file())
        .filter_map(|entry| entry.metadata().ok())
        .map(|metadata| metadata.len())
        .sum()
}

/// Bytes as `B`, `KB`, `MB`, `GB` or `TB` (powers of 1024) with one decimal.
fn format_size(bytes: u64) -> String {
    let mut size = bytes as f64;
    for unit in ["B", "KB", "MB", "GB"] {
        if size < 1024.0 {
            return format!("{size:.1} {unit}");
        }
        size /= 1024.0;
    }
    format!("{size:.1} TB")
}
