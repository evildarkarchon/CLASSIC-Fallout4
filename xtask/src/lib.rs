//! CLASSIC repository tooling behind `cargo xtask <command>`.
//!
//! The crate is a library with one module per subcommand, fronted by a thin
//! `clap` binary (`src/main.rs`). Every subcommand module exposes
//! `run(&RepoRoot, args) -> anyhow::Result<Outcome>`:
//!
//! - `Ok(Outcome::Pass { .. })`: the check passed.
//! - `Ok(Outcome::Fail { .. })`: the check ran and found violations.
//! - `Err(..)`: an operational failure (unreadable tree, unparseable input).
//!
//! Modules never print. The binary renders the [`Outcome`] and picks the exit
//! code: 0 on pass, 1 on a failed check or operational failure, 2 on a usage
//! error. Findings go to stderr as `path:line: rule: message`, then a summary;
//! a pass prints `OK: <summary>` on stdout.
//!
//! There is no gate trait or registry: the `match` in `main` is the whole
//! dispatch table. Shared helper modules exist only once they have two real
//! callers.

use std::fmt;

pub mod bench;
pub mod cxx_bridge_gate;
mod repo;

pub use repo::RepoRoot;

/// One violation reported by a subcommand.
///
/// Rendered as `path:line: rule: message`, where `path` is repo-relative with
/// forward slashes.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Finding {
    /// Repo-relative path with forward slashes.
    pub path: String,
    /// 1-based line number the finding points at.
    pub line: usize,
    /// Stable kebab-case rule identifier, e.g. `orphan-export`.
    pub rule: &'static str,
    /// Human-readable explanation.
    pub message: String,
}

impl fmt::Display for Finding {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}:{}: {}: {}",
            self.path, self.line, self.rule, self.message
        )
    }
}

/// The plain-data result of one subcommand run.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Outcome {
    /// The check passed; `summary` is printed after `OK: `.
    Pass {
        /// One-line description of what was checked.
        summary: String,
    },
    /// The check found violations. Findings are complete (all collected, not
    /// first-only) and sorted by path, then line.
    Fail {
        /// Every violation found.
        findings: Vec<Finding>,
        /// One-line summary printed after the findings.
        summary: String,
    },
}

impl Outcome {
    /// Builds a `Fail` from `findings` (sorted here), or a `Pass` when there are
    /// none. Each summary is only used for its matching variant.
    pub fn from_findings(
        mut findings: Vec<Finding>,
        pass_summary: String,
        fail_summary: String,
    ) -> Self {
        if findings.is_empty() {
            Outcome::Pass {
                summary: pass_summary,
            }
        } else {
            findings.sort();
            Outcome::Fail {
                findings,
                summary: fail_summary,
            }
        }
    }
}

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
