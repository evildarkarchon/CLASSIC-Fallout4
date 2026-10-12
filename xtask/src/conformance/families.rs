//! The per-family seam.
//!
//! Family behaviour is dispatched by a `match` on the family ID; there is no
//! trait or registry. Each operation defaults to identity (here: no extra
//! checks), so only the families that need one have an arm:
//!
//! - [`validate_inputs`]: input checks the engine-wide input rule cannot
//!   express (see `pack`).
//! - [`compile_expectations`]: turns a pack's authored `expected` members
//!   into exact observations, for the families whose expectations reference
//!   an independent oracle (user-settings, autoscan-report), and checks the
//!   vocabulary families' authored labels against their Rust tokens. It also
//!   names the oracle files the expectation digest must cover. `check` runs
//!   it so an oracle disagreement is a finding.
//! - [`normalize_observation`]: the family normalizations around a receipt's
//!   declared (pack) normalization, before exact comparison. Receipt
//!   validation calls it once per [`Stage`].
//! - [`input_shape`]: which families are exempt from the "fixture reference
//!   only" input shape because their inputs are richer.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

use super::Issue;
use super::schema::{Pack, Scenario};
use crate::RepoRoot;

mod autoscan_report;
mod aux_operations;
mod installation_paths;
mod scan_run;
mod settings_load;
mod update_services;
mod user_settings;
mod user_settings_migration;
mod user_settings_oracle;
mod vocabulary;
mod xse_folder;
mod yaml_nodes;

/// Rule identifier for every family-hook finding.
pub(crate) const RULE: &str = "family-input";

/// Rule identifier for every expectation-compiler finding.
pub(crate) const EXPECTATION_RULE: &str = "family-expectation";

/// A declared fixture that resolved beneath its pack's `fixtureRoot`.
#[derive(Debug, Clone)]
pub(crate) struct Fixture {
    /// The parsed content, for `.json` fixtures.
    pub json: Option<Value>,
}

/// What a family input hook can see: the pack, its resolved fixtures and the
/// repository (for hooks that read source files).
pub(crate) struct InputContext<'a> {
    /// The repository being checked.
    pub root: &'a RepoRoot,
    /// The pack under validation.
    pub pack: &'a Pack,
    /// Fixtures that resolved, by alias. A fixture missing here was already
    /// reported by the pack loader, so hooks skip scenarios that need it.
    pub fixtures: &'a BTreeMap<String, Fixture>,
}

impl InputContext<'_> {
    /// Each scenario with its index and its sole fixture's JSON content, for
    /// families whose input is one fixture reference. Scenarios whose fixture
    /// did not resolve or is not JSON are skipped (already reported).
    pub fn sole_json_fixtures(&self) -> Vec<(usize, &Scenario, &Value)> {
        self.pack
            .scenarios
            .iter()
            .enumerate()
            .filter_map(|(index, scenario)| {
                let [reference] = scenario.fixture_refs.as_slice() else {
                    return None;
                };
                let json = self.fixtures.get(reference)?.json.as_ref()?;
                Some((index, scenario, json))
            })
            .collect()
    }
}

impl InputContext<'_> {
    /// The pack's canonical `fixtureRoot`, for compilers that read oracle
    /// files beside the fixtures.
    ///
    /// # Errors
    ///
    /// Returns an issue when the root does not resolve (the pack loader has
    /// normally reported that already).
    pub fn fixture_root(&self) -> Result<PathBuf, Issue> {
        self.root
            .join(&self.pack.fixture_root)
            .canonicalize()
            .map_err(|error| {
                Issue::new(
                    "/fixtureRoot",
                    EXPECTATION_RULE,
                    format!(
                        "fixtureRoot {} does not resolve: {error}",
                        self.pack.fixture_root
                    ),
                )
            })
    }

    /// Canonical paths of every declared fixture that resolves, so a compiler
    /// can refuse an oracle that is also an adapter input.
    pub fn fixture_paths(&self, base: &Path) -> Vec<PathBuf> {
        self.pack
            .fixtures
            .values()
            .filter_map(|relative| super::pack::contained(base, relative))
            .collect()
    }
}

/// Resolves the authored oracle file `relative` beneath the canonical fixture
/// root `base`, rejecting traversal, absolute paths and anything that escapes
/// the root or is not a regular file.
pub(crate) fn oracle_file(base: &Path, relative: &str) -> Result<PathBuf, String> {
    if !super::schema::is_canonical_relative_path(relative) {
        return Err(format!(
            "oracle file {relative:?} must be a contained relative path"
        ));
    }
    match super::pack::contained(base, relative) {
        Some(path) if path.is_file() => Ok(path),
        _ => Err(format!(
            "oracle file {relative} must be an existing regular file beneath fixtureRoot"
        )),
    }
}

/// Reads the oracle file `relative` beneath `base` (see [`oracle_file`]).
pub(crate) fn read_oracle(base: &Path, relative: &str) -> Result<Vec<u8>, String> {
    let path = oracle_file(base, relative)?;
    std::fs::read(&path).map_err(|error| format!("cannot read oracle file {relative}: {error}"))
}

/// A pack's compiled expectations.
///
/// `check` needs only the compiler's verdict; the run-plan digest and receipt
/// validation (Engine A3) read the compiled values.
#[derive(Debug, Clone, PartialEq)]
pub(crate) struct Compiled {
    /// Each scenario's exact expected observation, by scenario index.
    pub expected: Vec<Map<String, Value>>,
    /// Repo-relative oracle files the expectation digest covers, in digest
    /// order. They are authored dependencies, never adapter inputs.
    pub oracles: Vec<String>,
}

impl Compiled {
    /// The pack's authored expectations, unchanged, with no oracle files.
    fn identity(pack: &Pack) -> Self {
        Self {
            expected: pack
                .scenarios
                .iter()
                .map(|scenario| scenario.expected.clone())
                .collect(),
            oracles: Vec::new(),
        }
    }
}

/// Compiles the pack's expectations; families without an arm use their
/// authored `expected` members as they are.
///
/// # Errors
///
/// Returns the first problem as an issue: an oracle reference that does not
/// resolve, an oracle that is also an input fixture, or a scenario whose
/// input or authored expectation disagrees with its oracle.
pub(crate) fn compile_expectations(context: &InputContext<'_>) -> Result<Compiled, Issue> {
    match context.pack.family_id.as_str() {
        "user-settings" => user_settings_oracle::compile(context),
        "autoscan-report" => autoscan_report::compile(context),
        "config-vocabulary" | "scan-run-vocabulary" => vocabulary::compile(context),
        _ => Ok(Compiled::identity(context.pack)),
    }
}

/// Builds an expectation-compiler issue about scenario `index`'s expectation.
pub(crate) fn expectation_issue(index: usize, message: impl Into<String>) -> Issue {
    Issue::new(
        format!("/scenarios/{index}/expected"),
        EXPECTATION_RULE,
        message,
    )
}

/// When a family normalization runs relative to the pack's declared
/// normalization (root-relative paths, optional empty files, exclusions,
/// unordered arrays).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Stage {
    /// Before the declared normalization: expected-side expansions that need
    /// the raw observation (autoscan-report's FCX path tokens).
    BeforeDeclared,
    /// After the declared normalization: actual-side normalizations that
    /// read root-relative trees (user-settings' published YAML bytes).
    AfterDeclared,
}

/// A receipt observation that cannot be normalized; reported as a
/// `normalization_failure`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct NormalizationError {
    /// Human-readable reason.
    pub message: String,
    /// The `$.`-style path of the offending observation member.
    pub path: String,
}

impl NormalizationError {
    /// Builds an error at `path`.
    pub fn new(message: impl Into<String>, path: &str) -> Self {
        Self {
            message: message.into(),
            path: path.to_owned(),
        }
    }
}

/// One scenario observation: a compiled `expected` member or a receipt's
/// `observation`.
pub(crate) type Observation = Map<String, Value>;

/// Applies the family's normalization for `stage` to one scenario's compiled
/// `expected` observation and the participant's `actual` observation, and
/// returns the pair to compare exactly. Families and stages without an arm
/// return both unchanged.
///
/// - autoscan-report, before: expands the FCX path tokens in the expected
///   report bytes using the observation's `executionRoot`.
/// - user-settings, after, every action but `user-settings.open`:
///   authenticates committed or migrated revisions against the observed raw
///   bytes and replaces published bytes with YAML nodes.
///
/// # Errors
///
/// Returns a [`NormalizationError`] when the observation lacks the raw
/// evidence the normalization authenticates, or the evidence disagrees.
pub(crate) fn normalize_observation(
    family_id: &str,
    action: &str,
    stage: Stage,
    expected: Observation,
    actual: Observation,
) -> Result<(Observation, Observation), NormalizationError> {
    match (family_id, stage) {
        ("autoscan-report", Stage::BeforeDeclared) => {
            let expected = autoscan_report::expand(&expected, &actual)?;
            Ok((expected, actual))
        }
        ("user-settings", Stage::AfterDeclared) if action != "user-settings.open" => {
            let actual = user_settings_oracle::normalize(&expected, &actual)?;
            Ok((expected, actual))
        }
        _ => Ok((expected, actual)),
    }
}

/// Builds a family-hook issue about scenario `index`'s input.
pub(crate) fn issue(index: usize, message: impl Into<String>) -> Issue {
    Issue::new(format!("/scenarios/{index}/input"), RULE, message)
}

/// Whether a family's scenario inputs must be exactly one fixture reference.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum InputShape {
    /// `input == {"fixtureRef": r}` and `fixtureRefs == [r]`.
    FixtureRefOnly,
    /// Inputs carry more than fixture references; the family's
    /// [`validate_inputs`] arm checks their shape.
    Rich,
}

/// The input shape of `family_id`.
pub(crate) fn input_shape(family_id: &str) -> InputShape {
    match family_id {
        "user-settings"
        | "crash-log-scan-run"
        | "crash-log-scan-launch"
        | "autoscan-report"
        | "config-vocabulary"
        | "scan-run-vocabulary" => InputShape::Rich,
        _ => InputShape::FixtureRefOnly,
    }
}

/// Runs the family's bespoke input checks; families without an arm have none.
pub(crate) fn validate_inputs(context: &InputContext<'_>) -> Vec<Issue> {
    match context.pack.family_id.as_str() {
        "web-operations"
        | "resource-operations"
        | "version-operations"
        | "version-extraction"
        | "version-f4se"
        | "version-pe"
        | "version-pe-path" => aux_operations::validate(context),
        "xse-folder" => xse_folder::validate(context),
        "installation-paths" => installation_paths::validate(context),
        "update-services" => update_services::validate(context),
        "settings-load" => settings_load::validate_load(context),
        "settings-yaml" => settings_load::validate_yaml(context),
        "settings-yaml-batch" => settings_load::validate_yaml_batch(context),
        "user-settings" => user_settings::validate(context),
        "crash-log-scan-run" | "autoscan-report" => scan_run::validate_run(context),
        "crash-log-scan-launch" => scan_run::validate_launch(context),
        "config-vocabulary" | "scan-run-vocabulary" => vocabulary::validate(context),
        _ => Vec::new(),
    }
}

/// Whether `value` is an object whose member names are exactly `keys`.
pub(crate) fn has_exact_keys(value: &Value, keys: &[&str]) -> bool {
    value
        .as_object()
        .is_some_and(|map| map.len() == keys.len() && keys.iter().all(|key| map.contains_key(*key)))
}

/// Whether `value` is an array of strings.
pub(crate) fn is_string_list(value: &Value) -> bool {
    value
        .as_array()
        .is_some_and(|items| items.iter().all(Value::is_string))
}

/// Lowercase hexadecimal of `bytes`.
pub(crate) fn encode_hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

/// Decodes canonical (lowercase, even-length) hexadecimal; `None` for any
/// other text, so a receipt cannot pass bytes in a second spelling.
pub(crate) fn decode_hex(text: &str) -> Option<Vec<u8>> {
    if !text.len().is_multiple_of(2)
        || !text
            .bytes()
            .all(|byte| matches!(byte, b'0'..=b'9' | b'a'..=b'f'))
    {
        return None;
    }
    (0..text.len())
        .step_by(2)
        .map(|index| u8::from_str_radix(&text[index..index + 2], 16).ok())
        .collect()
}

/// `"sha256:<hex>"` for `content`, or `"missing"` for an absent document: the
/// public content revision token of a settings document.
pub(crate) fn revision(content: Option<&[u8]>) -> String {
    content.map_or_else(
        || "missing".to_owned(),
        |bytes| format!("sha256:{}", sha256_hex(bytes)),
    )
}

/// Lowercase hex SHA-256 of `bytes`, for pinning controlled fixture content.
pub(crate) fn sha256_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

#[cfg(test)]
#[path = "families_tests.rs"]
mod tests;
