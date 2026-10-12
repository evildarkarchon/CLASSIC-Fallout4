//! Scenario pack loading and validation.
//!
//! Every pack goes through the same steps, and every problem is collected:
//!
//! 1. strict JSON and the closed [`Pack`] shape;
//! 2. identities: stable IDs, no duplicates, known capabilities, and an
//!    `action` that is one of the scenario's own capabilities;
//! 3. fixtures: `fixtureRoot` and every fixture resolve to existing files
//!    beneath the repository and the root, and scenarios name only declared,
//!    distinct fixtures;
//! 4. normalization: exact JSON paths with rationales;
//! 5. the engine-wide input rule (below);
//! 6. the family's own input hook ([`families::validate_inputs`]);
//! 7. on a pack with no findings so far, the family's expectation compiler
//!    ([`families::compile_expectations`]), so an oracle reference that does
//!    not resolve, or an input that disagrees with its oracle, is a finding.
//!
//! **The input rule.** Inputs are fixture references only: a scenario's input
//! is exactly `{"fixtureRef": r}` with `fixtureRefs == [r]`. Families with
//! richer inputs ([`families::InputShape::Rich`]) are exempt from that shape
//! and check theirs in their hook, but the rest of the rule holds for every
//! family:
//!
//! - the fixture references an input names (`fixtureRef` and `*FixtureRef`
//!   members, at any depth) are exactly the scenario's `fixtureRefs`;
//! - a staged fixture's destination `path` is a canonical relative path, so
//!   staging stays inside the run directory, as the fixture itself stays
//!   under `fixtureRoot`;
//! - inputs carry no result data: no `expected` or `observation` member
//!   appears in the input or in a JSON fixture, and neither contains the
//!   scenario's expected observation.

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::path::{Path, PathBuf};

use anyhow::Result;
use serde_json::{Map, Value};

use super::families::{self, Fixture, InputContext, InputShape};
use super::json::{Document, parse_strict, pointer};
use super::schema::{
    Pack, is_canonical_relative_path, is_exact_json_path, is_fixture_ref, is_relative_file_path,
    is_stable_id,
};
use super::{Issue, load_document};
use crate::{Finding, RepoRoot};

/// Repo-relative directory the packs are discovered under (recursively).
pub(crate) const PACKS_DIR: &str = "tests/conformance/packs";

/// Members of an input or fixture that would hand a participant its answer.
const RESULT_KEYS: [&str; 2] = ["expected", "observation"];

/// A pack that deserialized into its closed shape. Its semantic findings, if
/// any, were reported while loading; applicability still reads it so one bad
/// scenario does not cascade into catalog findings.
#[derive(Debug)]
pub(crate) struct LoadedPack {
    /// Repo-relative pack path.
    pub file: String,
    /// The strict parse, for locating findings.
    pub document: Document,
    /// The typed pack.
    pub pack: Pack,
    /// The compiled expectations, when the pack had no findings.
    pub compiled: Option<families::Compiled>,
}

/// Every pack file, split into those that deserialized and those that did not.
#[derive(Debug, Default)]
pub(crate) struct Packs {
    /// Packs that deserialized, sorted by path.
    pub loaded: Vec<LoadedPack>,
    /// `familyId`s read from pack files that failed their closed shape.
    pub unloaded_families: BTreeSet<String>,
    /// Whether some pack file was not even strict JSON, so its family is
    /// unknown.
    pub unidentified: bool,
}

impl Packs {
    /// Whether a catalog entry for `family_id` may lack a loaded pack because
    /// that pack failed to load (its finding already fails the check). This
    /// keeps one broken pack from cascading into "untracked family" findings.
    pub fn excuses(&self, family_id: &str) -> bool {
        self.unidentified || self.unloaded_families.contains(family_id)
    }
}

/// Loads and validates every pack under [`PACKS_DIR`], appending findings.
///
/// A missing or empty pack directory is a finding, as is a `familyId`
/// claimed by two packs.
///
/// # Errors
///
/// Fails when the pack tree or a pack file cannot be read.
pub(crate) fn load_all(root: &RepoRoot, findings: &mut Vec<Finding>) -> Result<Packs> {
    let discovery = |message: &str| Finding {
        path: PACKS_DIR.to_owned(),
        line: 1,
        rule: "pack-discovery",
        message: message.to_owned(),
    };
    if !root.join(PACKS_DIR).is_dir() {
        findings.push(discovery("the scenario pack directory is missing"));
        return Ok(Packs::default());
    }
    let mut result = Packs::default();
    let mut packs = Vec::new();
    for path in root.walk_files(PACKS_DIR, &["json"])? {
        let file = root.relative(&path);
        match load_document::<Pack>(root, &file, "pack-schema")? {
            Err(finding) => {
                findings.push(finding);
                let family = std::fs::read_to_string(&path)
                    .ok()
                    .and_then(|text| parse_strict(&text).ok())
                    .and_then(|document| document.value()["familyId"].as_str().map(str::to_owned));
                match family {
                    Some(family) => {
                        result.unloaded_families.insert(family);
                    }
                    None => result.unidentified = true,
                }
            }
            Ok(loaded) => {
                let (issues, compiled) = validate(root, &loaded.value);
                findings.extend(
                    issues
                        .into_iter()
                        .map(|issue| issue.locate(&loaded.file, &loaded.document)),
                );
                packs.push(LoadedPack {
                    file: loaded.file,
                    document: loaded.document,
                    pack: loaded.value,
                    compiled,
                });
            }
        }
    }
    if packs.is_empty() && !result.unidentified && result.unloaded_families.is_empty() {
        findings.push(discovery("no scenario packs were found"));
    }
    let mut owners: HashMap<&str, &str> = HashMap::new();
    for loaded in &packs {
        if let Some(first) = owners.insert(&loaded.pack.family_id, &loaded.file) {
            findings.push(Finding {
                path: loaded.file.clone(),
                line: loaded.document.line("/familyId"),
                rule: "pack-identity",
                message: format!(
                    "familyId {} is already declared by {first}",
                    loaded.pack.family_id
                ),
            });
        }
    }
    result.loaded = packs;
    Ok(result)
}

/// Loads and validates the single pack at the repo-relative `file`, for
/// re-checking that a pack did not change while a participant ran.
///
/// # Errors
///
/// Fails when the pack cannot be read, or has findings (listed).
pub(crate) fn load_one(root: &RepoRoot, file: &str) -> Result<LoadedPack> {
    let loaded = match load_document::<Pack>(root, file, "pack-schema")? {
        Ok(loaded) => loaded,
        Err(finding) => anyhow::bail!("{finding}"),
    };
    let (issues, compiled) = validate(root, &loaded.value);
    if !issues.is_empty() {
        let listed: Vec<String> = issues
            .into_iter()
            .map(|issue| issue.locate(&loaded.file, &loaded.document).to_string())
            .collect();
        anyhow::bail!("{}", listed.join("\n"));
    }
    Ok(LoadedPack {
        file: loaded.file,
        document: loaded.document,
        pack: loaded.value,
        compiled,
    })
}

/// Runs every semantic check on one deserialized pack; a pack with no
/// findings also returns its compiled expectations.
fn validate(root: &RepoRoot, pack: &Pack) -> (Vec<Issue>, Option<families::Compiled>) {
    let mut issues = identities(pack);
    let fixtures = fixtures(root, pack, &mut issues);
    normalization(pack, &mut issues);
    input_rule(pack, &fixtures, &mut issues);
    let context = InputContext {
        root,
        pack,
        fixtures: &fixtures,
    };
    issues.extend(families::validate_inputs(&context));
    // The expectation compiler reads fixtures and oracles the earlier steps
    // vouch for, so it runs only on an otherwise clean pack; on a broken one
    // its findings would only repeat theirs.
    if !issues.is_empty() {
        return (issues, None);
    }
    match families::compile_expectations(&context) {
        Ok(compiled) => (issues, Some(compiled)),
        Err(issue) => (vec![issue], None),
    }
}

/// Reports every element of `values` that occurs more than once.
fn duplicates<'a>(values: impl IntoIterator<Item = &'a str>) -> BTreeSet<&'a str> {
    let mut seen = BTreeSet::new();
    values
        .into_iter()
        .filter(|value| !seen.insert(*value))
        .collect()
}

/// Validates schema versions, stable identities and identity references.
fn identities(pack: &Pack) -> Vec<Issue> {
    const RULE: &str = "pack-identity";
    let mut issues = Vec::new();
    let mut stable = |pointer: String, value: &str, label: &str| {
        if !is_stable_id(value) {
            issues.push(Issue::new(
                pointer,
                RULE,
                format!("{label} {value:?} must be a stable machine identifier (lowercase letters and digits joined by `.` or `-`)"),
            ));
        }
    };
    stable("/familyId".into(), &pack.family_id, "familyId");
    stable(
        "/domainOwner/rustCrate".into(),
        &pack.domain_owner.rust_crate,
        "domainOwner.rustCrate",
    );
    for (index, capability) in pack.capabilities.iter().enumerate() {
        let at = format!("/capabilities/{index}");
        stable(format!("{at}/id"), &capability.id, "capability id");
        if let Some(crate_name) = &capability.rust_crate {
            stable(
                format!("{at}/rustCrate"),
                crate_name,
                "capability rustCrate",
            );
        }
        for (position, family) in capability.observation_families.iter().enumerate() {
            stable(
                format!("{at}/observationFamilies/{position}"),
                family,
                "observation family",
            );
        }
    }
    for (index, scenario) in pack.scenarios.iter().enumerate() {
        let at = format!("/scenarios/{index}");
        stable(format!("{at}/id"), &scenario.id, "scenario id");
        stable(format!("{at}/action"), &scenario.action, "action");
        for (position, capability) in scenario.capability_ids.iter().enumerate() {
            stable(
                format!("{at}/capabilityIds/{position}"),
                capability,
                "capability id",
            );
        }
    }
    for (index, obligation) in pack.consumer_obligations.iter().enumerate() {
        stable(
            format!("/consumerObligations/{index}/id"),
            &obligation.id,
            "consumer obligation id",
        );
    }

    if pack.schema_version != 1 {
        issues.push(Issue::new(
            "/schemaVersion",
            RULE,
            "schemaVersion must be 1",
        ));
    }
    if pack.family_version == 0 {
        issues.push(Issue::new(
            "/familyVersion",
            RULE,
            "familyVersion must be positive",
        ));
    }
    if pack.capabilities.is_empty() {
        issues.push(Issue::new(
            "/capabilities",
            RULE,
            "a pack declares at least one capability",
        ));
    }
    if pack.scenarios.is_empty() {
        issues.push(Issue::new(
            "/scenarios",
            RULE,
            "a pack declares at least one scenario",
        ));
    }
    for (index, capability) in pack.capabilities.iter().enumerate() {
        let at = format!("/capabilities/{index}");
        for (field, values) in [
            ("rustSymbols", &capability.rust_symbols),
            ("observationFamilies", &capability.observation_families),
        ] {
            if values.is_empty() || values.iter().any(String::is_empty) {
                issues.push(Issue::new(
                    format!("{at}/{field}"),
                    RULE,
                    format!("{field} must be a non-empty list of non-empty strings"),
                ));
            }
            for duplicate in duplicates(values.iter().map(String::as_str)) {
                issues.push(Issue::new(
                    format!("{at}/{field}"),
                    RULE,
                    format!("{field} lists {duplicate:?} more than once"),
                ));
            }
        }
    }
    let capability_ids: BTreeSet<&str> = pack.capabilities.iter().map(|c| c.id.as_str()).collect();
    for duplicate in duplicates(pack.capabilities.iter().map(|c| c.id.as_str())) {
        issues.push(Issue::new(
            "/capabilities",
            RULE,
            format!("duplicate capability {duplicate}"),
        ));
    }
    for (index, scenario) in pack.scenarios.iter().enumerate() {
        let at = format!("/scenarios/{index}");
        if scenario.capability_ids.is_empty() {
            issues.push(Issue::new(
                format!("{at}/capabilityIds"),
                RULE,
                "a scenario names at least one capability",
            ));
        }
        for duplicate in duplicates(scenario.capability_ids.iter().map(String::as_str)) {
            issues.push(Issue::new(
                format!("{at}/capabilityIds"),
                RULE,
                format!(
                    "scenario {} names capability {duplicate} twice",
                    scenario.id
                ),
            ));
        }
        for capability in &scenario.capability_ids {
            if !capability_ids.contains(capability.as_str()) {
                issues.push(Issue::new(
                    format!("{at}/capabilityIds"),
                    RULE,
                    format!(
                        "scenario {} references unknown capability {capability}",
                        scenario.id
                    ),
                ));
            }
        }
        if !scenario.capability_ids.contains(&scenario.action) {
            issues.push(Issue::new(
                format!("{at}/action"),
                RULE,
                format!(
                    "scenario {} action {} must be one of its capabilityIds",
                    scenario.id, scenario.action
                ),
            ));
        }
    }
    for duplicate in duplicates(pack.scenarios.iter().map(|s| s.id.as_str())) {
        issues.push(Issue::new(
            "/scenarios",
            RULE,
            format!("duplicate scenario {duplicate}"),
        ));
    }
    for duplicate in duplicates(pack.consumer_obligations.iter().map(|o| o.id.as_str())) {
        issues.push(Issue::new(
            "/consumerObligations",
            RULE,
            format!("duplicate consumer obligation {duplicate}"),
        ));
    }
    issues
}

/// Resolves `relative` under `base` and proves it stays there.
///
/// Both sides are canonicalized, so a symlink cannot smuggle a path outside.
pub(super) fn contained(base: &Path, relative: &str) -> Option<PathBuf> {
    let resolved = base.join(relative).canonicalize().ok()?;
    resolved.starts_with(base).then_some(resolved)
}

/// Validates `fixtureRoot`, every fixture declaration and every scenario's
/// fixture references; returns the fixtures that resolved.
fn fixtures(root: &RepoRoot, pack: &Pack, issues: &mut Vec<Issue>) -> BTreeMap<String, Fixture> {
    const RULE: &str = "pack-fixture";
    let mut resolved = BTreeMap::new();
    let fixture_root = if !is_canonical_relative_path(&pack.fixture_root) {
        issues.push(Issue::new(
            "/fixtureRoot",
            RULE,
            "fixtureRoot must be a canonical relative path without traversal",
        ));
        None
    } else {
        let repository = root.path().canonicalize().ok();
        match repository.and_then(|repository| contained(&repository, &pack.fixture_root)) {
            Some(path) if path.is_dir() => Some(path),
            _ => {
                issues.push(Issue::new(
                    "/fixtureRoot",
                    RULE,
                    format!(
                        "fixtureRoot {} must be an existing repository directory",
                        pack.fixture_root
                    ),
                ));
                None
            }
        }
    };

    let mut seen_paths = BTreeSet::new();
    for (reference, relative) in &pack.fixtures {
        let at = pointer("/fixtures", reference);
        if !is_fixture_ref(reference) {
            issues.push(Issue::new(
                at.clone(),
                RULE,
                format!("fixture alias {reference:?} must start with a letter and use only letters, digits, `_` or `-`"),
            ));
        }
        if !is_canonical_relative_path(relative) {
            issues.push(Issue::new(
                at,
                RULE,
                format!("fixture {reference} path {relative:?} must be a canonical relative path without traversal"),
            ));
            continue;
        }
        if !seen_paths.insert(relative.as_str()) {
            issues.push(Issue::new(
                at.clone(),
                RULE,
                format!("fixture path {relative} is declared more than once"),
            ));
        }
        let Some(base) = &fixture_root else { continue };
        match contained(base, relative) {
            Some(path) if path.is_file() => {
                let json = if relative.ends_with(".json") {
                    match std::fs::read(&path).map(|bytes| serde_json::from_slice::<Value>(&bytes))
                    {
                        Ok(Ok(value)) => Some(value),
                        Ok(Err(error)) => {
                            issues.push(Issue::new(
                                at,
                                RULE,
                                format!(
                                    "fixture {reference} ({relative}) is not valid JSON: {error}"
                                ),
                            ));
                            None
                        }
                        Err(error) => {
                            issues.push(Issue::new(
                                at,
                                RULE,
                                format!("fixture {reference} ({relative}) cannot be read: {error}"),
                            ));
                            None
                        }
                    }
                } else {
                    None
                };
                resolved.insert(reference.clone(), Fixture { json });
            }
            _ => issues.push(Issue::new(
                at,
                RULE,
                format!(
                    "fixture {reference} ({relative}) must be an existing file beneath fixtureRoot"
                ),
            )),
        }
    }

    for (index, scenario) in pack.scenarios.iter().enumerate() {
        let at = format!("/scenarios/{index}/fixtureRefs");
        for duplicate in duplicates(scenario.fixture_refs.iter().map(String::as_str)) {
            issues.push(Issue::new(
                at.clone(),
                RULE,
                format!("scenario {} names fixture {duplicate} twice", scenario.id),
            ));
        }
        for reference in &scenario.fixture_refs {
            if !pack.fixtures.contains_key(reference) {
                issues.push(Issue::new(
                    at.clone(),
                    RULE,
                    format!(
                        "scenario {} references undeclared fixture {reference}",
                        scenario.id
                    ),
                ));
            }
        }
    }
    resolved
}

/// Validates each scenario's normalization rules.
fn normalization(pack: &Pack, issues: &mut Vec<Issue>) {
    const RULE: &str = "pack-normalization";
    for (index, scenario) in pack.scenarios.iter().enumerate() {
        let at = format!("/scenarios/{index}/normalization");
        let rules = &scenario.normalization;
        let mut path_issue = |pointer: String, path: &str| {
            if !is_exact_json_path(path) {
                issues.push(Issue::new(
                    pointer,
                    RULE,
                    format!("{path:?} must be one exact JSON path without wildcards, recursive descent or root-wide selection"),
                ));
            }
        };
        for (position, path) in rules.unordered_paths.iter().enumerate() {
            path_issue(format!("{at}/unorderedPaths/{position}"), path);
        }
        for (position, exclusion) in rules.excluded_paths.iter().enumerate() {
            path_issue(
                format!("{at}/excludedPaths/{position}/path"),
                &exclusion.path,
            );
        }
        for (position, optional) in rules.optional_empty_files.iter().flatten().enumerate() {
            path_issue(
                format!("{at}/optionalEmptyFiles/{position}/path"),
                &optional.path,
            );
        }
        for (position, exclusion) in rules.excluded_paths.iter().enumerate() {
            if exclusion.rationale.trim().is_empty() {
                issues.push(Issue::new(
                    format!("{at}/excludedPaths/{position}/rationale"),
                    RULE,
                    format!(
                        "excluded path {} needs a non-empty rationale",
                        exclusion.path
                    ),
                ));
            }
        }
        for (position, optional) in rules.optional_empty_files.iter().flatten().enumerate() {
            let entry = format!("{at}/optionalEmptyFiles/{position}");
            if !is_relative_file_path(&optional.relative_path) {
                issues.push(Issue::new(
                    format!("{entry}/relativePath"),
                    RULE,
                    format!(
                        "{:?} must be a canonical relative file path",
                        optional.relative_path
                    ),
                ));
            }
            if optional.rationale.trim().is_empty() {
                issues.push(Issue::new(
                    format!("{entry}/rationale"),
                    RULE,
                    "an optional empty file needs a non-empty rationale",
                ));
            }
        }
        for duplicate in duplicates(rules.unordered_paths.iter().map(String::as_str)) {
            issues.push(Issue::new(
                at.clone(),
                RULE,
                format!("duplicate unordered path {duplicate}"),
            ));
        }
        for duplicate in duplicates(rules.excluded_paths.iter().map(|e| e.path.as_str())) {
            issues.push(Issue::new(
                at.clone(),
                RULE,
                format!("duplicate excluded path {duplicate}"),
            ));
        }
        let selectors: Vec<String> = rules
            .optional_empty_files
            .iter()
            .flatten()
            .map(|optional| format!("{} {}", optional.path, optional.relative_path))
            .collect();
        for duplicate in duplicates(selectors.iter().map(String::as_str)) {
            issues.push(Issue::new(
                at.clone(),
                RULE,
                format!("duplicate optional empty file selector {duplicate}"),
            ));
        }
        let excluded: BTreeSet<&str> = rules
            .excluded_paths
            .iter()
            .map(|e| e.path.as_str())
            .collect();
        for path in &rules.unordered_paths {
            if excluded.contains(path.as_str()) {
                issues.push(Issue::new(
                    at.clone(),
                    RULE,
                    format!("{path} cannot be both unordered and excluded"),
                ));
            }
        }
    }
}

/// Applies the engine-wide input rule (see the module docs) to every scenario.
fn input_rule(pack: &Pack, fixtures: &BTreeMap<String, Fixture>, issues: &mut Vec<Issue>) {
    const RULE: &str = "pack-input";
    let shape = families::input_shape(&pack.family_id);
    for (index, scenario) in pack.scenarios.iter().enumerate() {
        let at = format!("/scenarios/{index}/input");
        let id = &scenario.id;

        if shape == InputShape::FixtureRefOnly {
            let sole = match (
                scenario.input.get("fixtureRef"),
                scenario.fixture_refs.as_slice(),
            ) {
                (Some(Value::String(reference)), [only]) => {
                    scenario.input.len() == 1 && reference == only
                }
                _ => false,
            };
            if !sole {
                issues.push(Issue::new(
                    at.clone(),
                    RULE,
                    format!("scenario {id} input must be exactly {{\"fixtureRef\": <ref>}} naming its sole fixtureRefs entry"),
                ));
            }
        }

        let mut named = BTreeSet::new();
        let mut walk_issues = Vec::new();
        walk_input(&scenario.input, &at, &mut named, &mut walk_issues);
        issues.extend(walk_issues);
        let declared: BTreeSet<&str> = scenario.fixture_refs.iter().map(String::as_str).collect();
        let named: BTreeSet<&str> = named.iter().map(String::as_str).collect();
        if named != declared {
            issues.push(Issue::new(
                at.clone(),
                RULE,
                format!(
                    "scenario {id} input names fixtures {named:?} but fixtureRefs lists {declared:?}"
                ),
            ));
        }

        let expected = Value::Object(scenario.expected.clone());
        let input = Value::Object(scenario.input.clone());
        let mut sources = vec![("input".to_owned(), &input)];
        for reference in &scenario.fixture_refs {
            if let Some(Fixture {
                json: Some(json), ..
            }) = fixtures.get(reference)
            {
                sources.push((format!("fixture {reference}"), json));
            }
        }
        for (label, value) in sources {
            if let Some(key) = result_key(value) {
                issues.push(Issue::new(
                    at.clone(),
                    RULE,
                    format!("scenario {id} {label} carries result data: member {key:?}"),
                ));
            }
            if !scenario.expected.is_empty() && contains_subtree(value, &expected) {
                issues.push(Issue::new(
                    at.clone(),
                    RULE,
                    format!("scenario {id} {label} contains the scenario's expected observation"),
                ));
            }
        }
    }
}

/// Collects fixture references named by `input` and checks staged paths.
fn walk_input(
    input: &Map<String, Value>,
    at: &str,
    named: &mut BTreeSet<String>,
    issues: &mut Vec<Issue>,
) {
    for (key, value) in input {
        let here = pointer(at, key);
        if key == "fixtureRef" || key.ends_with("FixtureRef") {
            match value {
                Value::String(reference) => {
                    named.insert(reference.clone());
                }
                _ => issues.push(Issue::new(
                    here.clone(),
                    "pack-input",
                    format!("{key} must be a fixture alias string"),
                )),
            }
        }
        if key == "path" && input.contains_key("fixtureRef") {
            let canonical = value.as_str().is_some_and(is_canonical_relative_path);
            if !canonical {
                issues.push(Issue::new(
                    here.clone(),
                    "pack-input",
                    "a staged fixture path must be a canonical relative path without traversal",
                ));
            }
        }
        walk_value(value, &here, named, issues);
    }
}

fn walk_value(value: &Value, at: &str, named: &mut BTreeSet<String>, issues: &mut Vec<Issue>) {
    match value {
        Value::Object(map) => walk_input(map, at, named, issues),
        Value::Array(items) => {
            for (index, item) in items.iter().enumerate() {
                walk_value(item, &pointer(at, index), named, issues);
            }
        }
        _ => {}
    }
}

/// The first result-data member name found anywhere in `value`.
fn result_key(value: &Value) -> Option<&'static str> {
    match value {
        Value::Object(map) => RESULT_KEYS
            .into_iter()
            .find(|key| map.contains_key(*key))
            .or_else(|| map.values().find_map(result_key)),
        Value::Array(items) => items.iter().find_map(result_key),
        _ => None,
    }
}

/// Whether `needle` equals `value` or any value nested inside it.
fn contains_subtree(value: &Value, needle: &Value) -> bool {
    value == needle
        || match value {
            Value::Object(map) => map.values().any(|child| contains_subtree(child, needle)),
            Value::Array(items) => items.iter().any(|child| contains_subtree(child, needle)),
            _ => false,
        }
}
