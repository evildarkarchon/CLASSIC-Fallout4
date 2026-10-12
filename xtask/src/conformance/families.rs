//! The per-family seam.
//!
//! Family behaviour is dispatched by a `match` on the family ID; there is no
//! trait or registry. Each operation defaults to identity (here: no extra
//! checks), so only the families that need one have an arm:
//!
//! - [`validate_inputs`]: input checks the engine-wide input rule cannot
//!   express (see `pack`). This is the only operation `check` needs; the
//!   expectation compilers (`compile_expectations`) and receipt normalizers
//!   (`normalize_observation`) join this module, with the same `match` shape,
//!   when the engine runs participants.
//! - [`input_shape`]: which families are exempt from the "fixture reference
//!   only" input shape because their inputs are richer.

use std::collections::BTreeMap;

use serde_json::Value;
use sha2::{Digest, Sha256};

use super::Issue;
use super::schema::{Pack, Scenario};
use crate::RepoRoot;

mod aux_operations;
mod installation_paths;
mod scan_run;
mod settings_load;
mod user_settings;
mod vocabulary;
mod xse_folder;

/// Rule identifier for every family-hook finding.
pub(crate) const RULE: &str = "family-input";

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
