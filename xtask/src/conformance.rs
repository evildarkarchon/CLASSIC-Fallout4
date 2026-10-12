//! `cargo xtask conformance`: the Rust conformance engine.
//!
//! `check` validates the conformance inputs statically, without running any
//! participant:
//!
//! - every scenario pack under `tests/conformance/packs/` (closed shape,
//!   identities, fixtures, normalization, the engine-wide input rule and the
//!   family input hooks);
//! - `tests/conformance/participants.json` (which families CXX runs);
//! - `tests/conformance/consumer-obligations.json` (the CLI, GUI and TUI
//!   consumers);
//! - the workflow policy: every applicable (family, participant, execution
//!   instance) has a blocking CI step, and the aggregation and Corrosion
//!   wiring the verdict depends on is intact.
//!
//! Module layout (decision #301): [`json`] (strict parse, canonical bytes,
//! framed digest), [`schema`] (closed document shapes), `pack` (loading and the
//! generic input rule), `applicability` (who must run what), `families` (the
//! per-family seam, a `match` on the family ID), and [`workflow_policy`].
//! The plan, launch, receipt, compare and report modules arrive with the
//! `run` and `verdict` commands.

use std::collections::BTreeSet;
use std::io::ErrorKind;

use anyhow::{Context, Result, bail};
use serde::de::DeserializeOwned;

use crate::{Finding, Outcome, RepoRoot};

mod applicability;
mod families;
pub mod json;
mod pack;
pub mod schema;
pub mod workflow_policy;

pub use applicability::ExecutionKey;

use json::Document;

/// Arguments for `conformance`.
#[derive(Debug, clap::Args)]
pub struct Args {
    /// The conformance operation to perform.
    #[command(subcommand)]
    pub command: Command,
}

/// `conformance` operations.
#[derive(Debug, Clone, clap::Subcommand)]
pub enum Command {
    /// Validate every pack, participants.json, consumer-obligations.json and
    /// the CI workflow policy, without running any participant.
    ///
    /// Pack inputs may name fixtures only (`{"fixtureRef": ...}`), fixtures
    /// must stay under the pack's fixtureRoot, and neither inputs nor fixtures
    /// may carry result data. Families whose inputs are richer than one
    /// fixture reference validate them through their own input hook.
    Check(CheckArgs),
}

/// Arguments for `conformance check` (none today).
#[derive(Debug, Default, Clone, clap::Args)]
pub struct CheckArgs {}

/// Runs one conformance operation over the repository at `root`.
///
/// # Errors
///
/// Fails on an operational problem (an unreadable directory or file); every
/// problem with the conformance inputs themselves is a finding instead.
pub fn run(root: &RepoRoot, args: Args) -> Result<Outcome> {
    match args.command {
        Command::Check(_) => check(root),
    }
}

/// `conformance check`: packs, catalogs and the workflow policy.
fn check(root: &RepoRoot) -> Result<Outcome> {
    let mut findings = Vec::new();
    let packs = pack::load_all(root, &mut findings)?;
    let applicability = applicability::derive(root, &packs, &mut findings)?;
    let required = &applicability.required;
    findings.extend(workflow_policy::check(root, required)?);

    let scenarios: usize = packs
        .loaded
        .iter()
        .map(|loaded| loaded.pack.scenarios.len())
        .sum();
    let summary = format!(
        "conformance check: {} packs ({scenarios} scenarios), {} CXX scenarios in {} enrolled \
         families, {} consumer obligations, {} required CI executions",
        packs.loaded.len(),
        applicability.cxx_scenarios,
        applicability.cxx_families,
        applicability.consumer_obligations,
        required.len(),
    );
    let count = findings.len();
    Ok(Outcome::from_findings(
        findings,
        summary,
        format!("conformance check failed: {count} findings"),
    ))
}

/// Every (family, participant, execution instance) the packs and catalogs at
/// `root` require CI to run, the denominator of the workflow policy.
///
/// # Errors
///
/// Fails when a pack or catalog has findings (they are listed in the error),
/// or on an operational problem reading them.
pub fn required_executions(root: &RepoRoot) -> Result<BTreeSet<ExecutionKey>> {
    let mut findings = Vec::new();
    let packs = pack::load_all(root, &mut findings)?;
    let applicability = applicability::derive(root, &packs, &mut findings)?;
    if !findings.is_empty() {
        let listed: Vec<String> = findings.iter().map(ToString::to_string).collect();
        bail!("conformance inputs have findings:\n{}", listed.join("\n"));
    }
    Ok(applicability.required)
}

/// One problem inside a JSON document, located by JSON pointer until it is
/// rendered as a [`Finding`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Issue {
    /// RFC 6901 pointer of the offending value.
    pub pointer: String,
    /// Stable kebab-case rule identifier.
    pub rule: &'static str,
    /// Human-readable explanation.
    pub message: String,
}

impl Issue {
    /// Builds an issue at `pointer`.
    pub fn new(pointer: impl Into<String>, rule: &'static str, message: impl Into<String>) -> Self {
        Self {
            pointer: pointer.into(),
            rule,
            message: message.into(),
        }
    }

    /// Renders the issue as a finding in `file`, at the line `document`
    /// recorded for the issue's pointer.
    pub fn locate(self, file: &str, document: &Document) -> Finding {
        Finding {
            path: file.to_owned(),
            line: document.line(&self.pointer),
            rule: self.rule,
            message: self.message,
        }
    }
}

/// A JSON document that parsed strictly and deserialized into its closed shape.
#[derive(Debug, Clone)]
pub(crate) struct Loaded<T> {
    /// Repo-relative path with forward slashes.
    pub file: String,
    /// The strict parse, for locating later findings.
    pub document: Document,
    /// The typed document.
    pub value: T,
}

/// Loads the repo-relative JSON document `relative` as a `T`.
///
/// A missing file, invalid strict JSON (`invalid-json`) or a shape violation
/// (`schema_rule`) is returned as `Ok(Err(finding))`, so `check` reports it
/// alongside everything else.
///
/// # Errors
///
/// Fails when the file exists but cannot be read.
pub(crate) fn load_document<T: DeserializeOwned>(
    root: &RepoRoot,
    relative: &str,
    schema_rule: &'static str,
) -> Result<std::result::Result<Loaded<T>, Finding>> {
    let finding = |line: usize, rule: &'static str, message: String| Finding {
        path: relative.to_owned(),
        line,
        rule,
        message,
    };
    let text = match std::fs::read_to_string(root.join(relative)) {
        Ok(text) => text,
        Err(error) if error.kind() == ErrorKind::NotFound => {
            return Ok(Err(finding(
                1,
                schema_rule,
                "required file is missing".into(),
            )));
        }
        Err(error) if error.kind() == ErrorKind::InvalidData => {
            return Ok(Err(finding(1, "invalid-json", "file is not UTF-8".into())));
        }
        Err(error) => return Err(error).with_context(|| format!("reading {relative}")),
    };
    let document = match json::parse_strict(&text) {
        Ok(document) => document,
        Err(error) => return Ok(Err(finding(error.line, "invalid-json", error.message))),
    };
    match serde_json::from_str::<T>(&text) {
        Ok(value) => Ok(Ok(Loaded {
            file: relative.to_owned(),
            document,
            value,
        })),
        Err(error) => {
            // serde_json appends " at line L column C"; the line goes into the
            // finding prefix instead.
            let message = error.to_string();
            let message = message
                .rsplit_once(" at line ")
                .map_or(message.as_str(), |(head, _)| head)
                .to_owned();
            Ok(Err(finding(error.line().max(1), schema_rule, message)))
        }
    }
}
