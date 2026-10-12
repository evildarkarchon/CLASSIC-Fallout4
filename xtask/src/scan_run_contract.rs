//! `cargo xtask scan-run-contract`: the Crash Log Scan Run contract manifest
//! (`tests/fixtures/crash_log_scan_run/manifest.json`) must agree with the
//! Rust contract, its fixtures, the variant-evidence policy and the
//! never-exposed boundary.
//!
//! Every check runs and every finding is collected; nothing stops at the first
//! problem. The checks are:
//!
//! - **Manifest shape:** `schemaVersion` is 1 and `contractVariants` is a
//!   non-empty list of unique strings.
//! - **Rust enums:** each `rustEnums` entry names an enum, found with `syn` in
//!   its source file. Each variant maps to `<category>.<snake_case>` (or its
//!   `renames` entry), and that set must equal the manifest's variants with the
//!   same `<category>.` prefix, in both directions.
//! - **Variant evidence:** the [`variant_policy`] rows must cover exactly the
//!   manifest's variants, and every runtime row's scenario must be a
//!   `scenarios[].id` in the crash-log-scan-run conformance pack.
//! - **Fixtures:** every `fixtureFiles` entry exists; `fixtureRoot` is a
//!   directory inside the repository; the Reset To Default fixture
//!   (`fixtures.installedYamlData`) keeps its stable codes and semantics; and
//!   the shared failure fixtures cover every `log_failure_stage.*` and
//!   `infrastructure_error_stage.*` variant exactly.
//! - **Never-exposed boundary:** `forbiddenExports` has one entry per
//!   `supportedAdapters` owner, and no listed symbol appears in its listed
//!   source file. Identifier-shaped symbols match on identifier boundaries
//!   (so `scan_run_execute` does not match `scan_run_contract_execute`); any
//!   other symbol is a raw substring. A missing file fails unless the entry is
//!   `optional`.
//!
//! An unreadable or unparseable manifest is an operational error. Everything
//! the manifest points at is a finding. Findings about manifest content point
//! at the first manifest line that names the offending key or value.

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Component, Path, PathBuf};

use anyhow::{Context, Result, bail};
use serde_json::{Map, Value, json};

use crate::{Finding, Outcome, RepoRoot, rust_source};

pub mod variant_policy;

use variant_policy::{Evidence, POLICY_PATH, TARGETS};

/// Repo-relative path of the contract manifest.
pub const MANIFEST_PATH: &str = "tests/fixtures/crash_log_scan_run/manifest.json";
/// Repo-relative path of the crash-log-scan-run conformance pack.
pub const PACK_PATH: &str = "tests/conformance/packs/crash_log_scan_run/v1.json";

const MANIFEST_SHAPE: &str = "manifest-shape";
const RUST_ENUM_MISMATCH: &str = "rust-enum-mismatch";
const VARIANT_EVIDENCE: &str = "variant-evidence";
const FIXTURE_FILES: &str = "fixture-files";
const RESET_FIXTURE: &str = "reset-fixture";
const FAILURE_FIXTURE: &str = "failure-fixture";
const FORBIDDEN_EXPORT: &str = "forbidden-export";

/// Prefix of every Reset To Default fixture message.
const INSTALLED: &str = "fixtures.installedYamlData";

/// Arguments for `scan-run-contract` (none today).
#[derive(Debug, Default, Clone, clap::Args)]
pub struct Args {}

/// Runs every scan-run contract check over the repository at `root`.
///
/// # Errors
///
/// Fails when the manifest cannot be read, is not JSON, or is not a JSON
/// object. Every other problem is a finding in the returned `Outcome::Fail`.
pub fn run(root: &RepoRoot, _args: Args) -> Result<Outcome> {
    let text = std::fs::read_to_string(root.join(MANIFEST_PATH))
        .with_context(|| format!("reading {MANIFEST_PATH}"))?;
    let manifest: Value =
        serde_json::from_str(&text).with_context(|| format!("parsing {MANIFEST_PATH}"))?;
    let Value::Object(manifest) = manifest else {
        bail!("{MANIFEST_PATH} must contain a JSON object");
    };

    let mut check = Check {
        root,
        text: &text,
        findings: Vec::new(),
    };
    if manifest.get("schemaVersion").and_then(Value::as_u64) != Some(1) {
        check.at_key(
            "schemaVersion",
            MANIFEST_SHAPE,
            "schemaVersion must be 1".into(),
        );
    }
    let variants = check
        .string_list(
            manifest.get("contractVariants"),
            "contractVariants",
            "contractVariants",
            MANIFEST_SHAPE,
        )
        .map(|list| list.into_iter().collect::<BTreeSet<_>>());
    let variants = match variants {
        Some(set) if set.is_empty() => {
            check.at_key(
                "contractVariants",
                MANIFEST_SHAPE,
                "contractVariants must not be empty".into(),
            );
            None
        }
        other => other,
    };

    // Every variant-dependent check is skipped when the variant list itself is
    // unusable; comparing against an empty set would only bury that finding.
    if let Some(variants) = &variants {
        check.rust_inventory(&manifest, variants);
        check.variant_evidence(variants);
        check.failure_fixtures(&manifest, variants);
    }
    let supported = check.string_list(
        manifest.get("supportedAdapters"),
        "supportedAdapters",
        "supportedAdapters",
        MANIFEST_SHAPE,
    );
    check.fixture_files(&manifest);
    check.reset_fixture(&manifest);
    check.forbidden_exports(&manifest, supported.as_deref());

    let variant_count = variants.as_ref().map_or(0, BTreeSet::len);
    let enum_count = manifest
        .get("rustEnums")
        .and_then(Value::as_array)
        .map_or(0, Vec::len);
    let finding_count = check.findings.len();
    Ok(Outcome::from_findings(
        check.findings,
        format!(
            "scan-run-contract: Crash Log Scan Run contract manifest is complete \
             ({variant_count} variants, {enum_count} Rust enums)"
        ),
        format!("scan-run-contract: {finding_count} finding(s) in the Crash Log Scan Run contract"),
    ))
}

/// Accumulates findings for one run.
struct Check<'a> {
    root: &'a RepoRoot,
    /// Manifest text, searched to give manifest findings a line number.
    text: &'a str,
    findings: Vec<Finding>,
}

impl Check<'_> {
    /// 1-based line of the first occurrence of `needle` in the manifest, or 1.
    fn manifest_line(&self, needle: &str) -> usize {
        self.text
            .find(needle)
            .map_or(1, |offset| line_at(self.text, offset))
    }

    /// Records a manifest finding at the line of the JSON string `"literal"`
    /// (a key or a string value).
    fn at_key(&mut self, literal: &str, rule: &'static str, message: String) {
        let line = self.manifest_line(&format!("\"{literal}\""));
        self.findings.push(Finding {
            path: MANIFEST_PATH.to_owned(),
            line,
            rule,
            message,
        });
    }

    fn at(&mut self, path: &str, line: usize, rule: &'static str, message: String) {
        self.findings.push(Finding {
            path: path.to_owned(),
            line,
            rule,
            message,
        });
    }

    /// Reads `value` as a list of strings. Records `<label> must be a list of
    /// strings` (and returns `None`) when it is not, and `<label> contains
    /// duplicates` (still returning the list) when an entry repeats.
    fn string_list(
        &mut self,
        value: Option<&Value>,
        label: &str,
        line_key: &str,
        rule: &'static str,
    ) -> Option<Vec<String>> {
        let list: Option<Vec<String>> = value.and_then(Value::as_array).and_then(|items| {
            items
                .iter()
                .map(|item| item.as_str().map(str::to_owned))
                .collect()
        });
        let Some(list) = list else {
            self.at_key(line_key, rule, format!("{label} must be a list of strings"));
            return None;
        };
        if list.iter().collect::<BTreeSet<_>>().len() != list.len() {
            self.at_key(line_key, rule, format!("{label} contains duplicates"));
        }
        Some(list)
    }

    /// Compares every `rustEnums` entry's parsed variants with the manifest.
    fn rust_inventory(&mut self, manifest: &Map<String, Value>, variants: &BTreeSet<String>) {
        let Some(specs) = manifest.get("rustEnums").and_then(Value::as_array) else {
            self.at_key(
                "rustEnums",
                RUST_ENUM_MISMATCH,
                "rustEnums must be a list".into(),
            );
            return;
        };
        for spec in specs {
            let field = |name: &str| spec.get(name).and_then(Value::as_str);
            let (Some(category), Some(path), Some(name)) =
                (field("category"), field("path"), field("name"))
            else {
                self.at_key(
                    "rustEnums",
                    RUST_ENUM_MISMATCH,
                    "Rust enum category, path, and name must be strings".into(),
                );
                continue;
            };
            let renames: Option<BTreeMap<&str, &str>> = match spec.get("renames") {
                None => Some(BTreeMap::new()),
                Some(Value::Object(map)) => map
                    .iter()
                    .map(|(from, to)| to.as_str().map(|to| (from.as_str(), to)))
                    .collect(),
                Some(_) => None,
            };
            let Some(renames) = renames else {
                self.at_key(
                    name,
                    RUST_ENUM_MISMATCH,
                    format!("Rust enum {name} renames must be strings"),
                );
                continue;
            };
            let source = match std::fs::read_to_string(self.root.join(path)) {
                Ok(source) => source,
                Err(error) => {
                    self.at_key(
                        name,
                        RUST_ENUM_MISMATCH,
                        format!("Cannot read Rust enum source {path}: {error}"),
                    );
                    continue;
                }
            };
            let file = match rust_source::parse_file(path, &source) {
                Ok(file) => file,
                Err(error) => {
                    self.at_key(
                        name,
                        RUST_ENUM_MISMATCH,
                        format!("Rust enum {name}: {error:#}"),
                    );
                    continue;
                }
            };
            let Some(item) = rust_source::find_enum(&file, name) else {
                self.at_key(
                    name,
                    RUST_ENUM_MISMATCH,
                    format!("Rust enum {name} was not found in {path}"),
                );
                continue;
            };
            if item.variants.is_empty() {
                let line = item.ident.span().start().line;
                self.at(
                    path,
                    line,
                    RUST_ENUM_MISMATCH,
                    format!("Rust enum {name} has no variants"),
                );
                continue;
            }

            let parsed: BTreeSet<String> = item
                .variants
                .iter()
                .map(|variant| variant.ident.to_string())
                .collect();
            let stale_renames: Vec<&str> = renames
                .keys()
                .copied()
                .filter(|from| !parsed.contains(*from))
                .collect();
            if !stale_renames.is_empty() {
                self.at_key(
                    stale_renames[0],
                    RUST_ENUM_MISMATCH,
                    format!(
                        "Rust enum {name} has stale renames: {}",
                        stale_renames.join(", ")
                    ),
                );
            }

            // Variant id -> line of the variant in the Rust source.
            let observed: BTreeMap<String, usize> = item
                .variants
                .iter()
                .map(|variant| {
                    let ident = variant.ident.to_string();
                    let mapped = renames
                        .get(ident.as_str())
                        .map_or_else(|| snake_case(&ident), |to| (*to).to_owned());
                    (
                        format!("{category}.{mapped}"),
                        variant.ident.span().start().line,
                    )
                })
                .collect();
            let prefix = format!("{category}.");
            for (variant, line) in &observed {
                if !variants.contains(variant) {
                    self.at(
                        path,
                        *line,
                        RUST_ENUM_MISMATCH,
                        format!(
                            "Rust enum {name} does not match the manifest: unregistered {variant}"
                        ),
                    );
                }
            }
            for variant in variants
                .iter()
                .filter(|variant| variant.starts_with(&prefix))
            {
                if !observed.contains_key(variant) {
                    self.at_key(
                        variant,
                        RUST_ENUM_MISMATCH,
                        format!("Rust enum {name} does not match the manifest: stale {variant}"),
                    );
                }
            }
        }
    }

    /// Checks the compiled policy against the manifest variants and the pack.
    fn variant_evidence(&mut self, variants: &BTreeSet<String>) {
        let policy: BTreeSet<&str> = TARGETS.iter().map(|target| target.variant).collect();
        for variant in variants {
            if !policy.contains(variant.as_str()) {
                self.at_key(
                    variant,
                    VARIANT_EVIDENCE,
                    format!("variant evidence policy differs: missing {variant} (add it to {POLICY_PATH})"),
                );
            }
        }
        for target in TARGETS {
            if !variants.contains(target.variant) {
                self.at(
                    POLICY_PATH,
                    target.line as usize,
                    VARIANT_EVIDENCE,
                    format!("variant evidence policy differs: stale {}", target.variant),
                );
            }
        }

        let Some(scenarios) = self.pack_scenarios() else {
            return;
        };
        for target in TARGETS {
            if let Evidence::Runtime { scenario_id } = target.evidence
                && !scenarios.contains(scenario_id)
            {
                self.at(
                    POLICY_PATH,
                    target.line as usize,
                    VARIANT_EVIDENCE,
                    format!(
                        "variant {} references scenario '{scenario_id}', which is not a scenario in {PACK_PATH}",
                        target.variant
                    ),
                );
            }
        }
    }

    /// The pack's `scenarios[].id` set, or `None` after recording why it could
    /// not be read.
    fn pack_scenarios(&mut self) -> Option<BTreeSet<String>> {
        let pack = std::fs::read_to_string(self.root.join(PACK_PATH))
            .map_err(|error| format!("Cannot read {PACK_PATH}: {error}"))
            .and_then(|text| {
                serde_json::from_str::<Value>(&text)
                    .map_err(|error| format!("{PACK_PATH} is not valid JSON: {error}"))
            });
        let ids: Result<BTreeSet<String>, String> = pack.and_then(|pack| {
            pack.get("scenarios")
                .and_then(Value::as_array)
                .and_then(|scenarios| {
                    scenarios
                        .iter()
                        .map(|scenario| {
                            scenario
                                .get("id")
                                .and_then(Value::as_str)
                                .map(str::to_owned)
                        })
                        .collect()
                })
                .ok_or_else(|| {
                    format!("{PACK_PATH} scenarios must be a list of objects with string ids")
                })
        });
        match ids {
            Ok(ids) => Some(ids),
            Err(message) => {
                self.at(PACK_PATH, 1, VARIANT_EVIDENCE, message);
                None
            }
        }
    }

    /// Every `fixtureFiles` entry must be an existing file.
    fn fixture_files(&mut self, manifest: &Map<String, Value>) {
        let Some(files) = self.string_list(
            manifest.get("fixtureFiles"),
            "fixtureFiles",
            "fixtureFiles",
            FIXTURE_FILES,
        ) else {
            return;
        };
        for file in files {
            if !self.root.join(&file).is_file() {
                self.at_key(
                    &file,
                    FIXTURE_FILES,
                    format!("Shared fixture file is missing: {file}"),
                );
            }
        }
    }

    /// The Reset To Default fixture corpus stays repository-owned and keeps its
    /// stable codes, durable outcomes and expected state.
    fn reset_fixture(&mut self, manifest: &Map<String, Value>) {
        match manifest
            .get("fixtureRoot")
            .and_then(Value::as_str)
            .filter(|root| !root.is_empty())
        {
            None => self.at_key(
                "fixtureRoot",
                RESET_FIXTURE,
                "fixtureRoot must be a non-empty string".into(),
            ),
            Some(relative) => match contained(self.root, relative) {
                None => self.at_key(
                    "fixtureRoot",
                    RESET_FIXTURE,
                    "fixtureRoot must remain within the repository".into(),
                ),
                Some(path) if !path.is_dir() => self.at_key(
                    "fixtureRoot",
                    RESET_FIXTURE,
                    format!("fixtureRoot directory is missing: {relative}"),
                ),
                Some(_) => {}
            },
        }

        let Some(fixtures) = manifest.get("fixtures").and_then(Value::as_object) else {
            self.at_key(
                "fixtures",
                RESET_FIXTURE,
                "fixtures must be an object".into(),
            );
            return;
        };
        let Some(installed) = fixtures.get("installedYamlData").and_then(Value::as_object) else {
            self.at_key(
                "fixtures",
                RESET_FIXTURE,
                format!("{INSTALLED} must be an object"),
            );
            return;
        };

        match installed.get("resetOutcomes").and_then(Value::as_object) {
            None => self.at_key(
                "installedYamlData",
                RESET_FIXTURE,
                format!("{INSTALLED}.resetOutcomes must be an object"),
            ),
            Some(outcomes) => {
                let expected = [
                    ("conflictCode", json!("local_ignore_reset_conflict")),
                    (
                        "backupFailureCode",
                        json!("local_ignore_reset_backup_failure"),
                    ),
                    (
                        "replacementFailureCode",
                        json!("local_ignore_reset_replacement_failure"),
                    ),
                    (
                        "durabilityUnknownCode",
                        json!("local_ignore_reset_durability_unknown"),
                    ),
                    ("consumedCode", json!("scan_run_continuation_consumed")),
                    ("backupMustEqualMalformedBytes", json!(true)),
                    ("reportMustEqualExistingBytes", json!(true)),
                    ("preResetCancellationMutates", json!(false)),
                    ("postCriticalCancellationStatus", json!("cancelled")),
                ];
                for (field, value) in expected {
                    if outcomes.get(field) != Some(&value) {
                        let line_key = if outcomes.contains_key(field) {
                            field
                        } else {
                            "resetOutcomes"
                        };
                        self.at_key(
                            line_key,
                            RESET_FIXTURE,
                            format!("{INSTALLED}.resetOutcomes.{field} must be {value}"),
                        );
                    }
                }
            }
        }

        let Some(reset) = installed
            .get("expectedResetToDefault")
            .and_then(Value::as_object)
        else {
            self.at_key(
                "installedYamlData",
                RESET_FIXTURE,
                format!("{INSTALLED}.expectedResetToDefault must be an object"),
            );
            return;
        };
        const RESET: &str = "expectedResetToDefault";
        if reset.get("localIgnoreState").and_then(Value::as_str) != Some("reset_to_default") {
            self.at_key(
                RESET,
                RESET_FIXTURE,
                format!("{INSTALLED}.{RESET}.localIgnoreState must be \"reset_to_default\""),
            );
        }
        let kinds = self.string_list(
            reset.get("diagnosticKinds"),
            &format!("{INSTALLED}.{RESET}.diagnosticKinds"),
            RESET,
            RESET_FIXTURE,
        );
        if let Some(kinds) = kinds {
            let kinds: BTreeSet<&str> = kinds.iter().map(String::as_str).collect();
            if kinds != BTreeSet::from(["local_ignore_reset", "parse"]) {
                self.at_key(
                    RESET,
                    RESET_FIXTURE,
                    format!(
                        "{INSTALLED}.{RESET}.diagnosticKinds must be [\"local_ignore_reset\", \"parse\"] (in any order)"
                    ),
                );
            }
        }
        let Some(recovery) = installed
            .get("expectedRecoveryRequired")
            .and_then(Value::as_object)
        else {
            self.at_key(
                "installedYamlData",
                RESET_FIXTURE,
                format!("{INSTALLED}.expectedRecoveryRequired must be an object"),
            );
            return;
        };
        for field in ["mainProvenance", "gameProvenance"] {
            let retained = recovery.get(field).and_then(Value::as_str);
            if retained.is_none() || reset.get(field).and_then(Value::as_str) != retained {
                self.at_key(
                    RESET,
                    RESET_FIXTURE,
                    format!(
                        "{INSTALLED}.{RESET}.{field} must retain expectedRecoveryRequired.{field}"
                    ),
                );
            }
        }
    }

    /// The shared per-log and infrastructure failure fixtures must cover every
    /// stage variant exactly.
    fn failure_fixtures(&mut self, manifest: &Map<String, Value>, variants: &BTreeSet<String>) {
        let Some(fixtures) = manifest.get("failureFixtures").and_then(Value::as_object) else {
            self.at_key(
                "failureFixtures",
                FAILURE_FIXTURE,
                "failureFixtures must be an object".into(),
            );
            return;
        };

        let log_failures = fixtures
            .get("logResult")
            .and_then(Value::as_object)
            .and_then(|log| log.get("failures"))
            .and_then(Value::as_array)
            .filter(|failures| !failures.is_empty());
        match log_failures {
            None => self.at_key(
                "logResult",
                FAILURE_FIXTURE,
                "failureFixtures.logResult.failures must be a non-empty list of objects".into(),
            ),
            Some(failures) => {
                let mut observed = BTreeSet::new();
                for failure in failures {
                    let stage = failure.get("stage").and_then(Value::as_str);
                    let message = failure.get("message").and_then(Value::as_str);
                    match (stage, message) {
                        (Some(stage), Some(message)) if !message.is_empty() => {
                            observed.insert(format!("log_failure_stage.{stage}"));
                        }
                        _ => self.at_key(
                            "logResult",
                            FAILURE_FIXTURE,
                            "log failure fixtures require string stage and non-empty message"
                                .into(),
                        ),
                    }
                }
                self.stage_diff(
                    "logResult",
                    "shared log failure stages",
                    "log_failure_stage.",
                    &observed,
                    variants,
                );
            }
        }

        let infrastructure = fixtures
            .get("infrastructureErrors")
            .and_then(Value::as_array)
            .filter(|errors| !errors.is_empty());
        match infrastructure {
            None => self.at_key(
                "infrastructureErrors",
                FAILURE_FIXTURE,
                "failureFixtures.infrastructureErrors must be a non-empty list of objects".into(),
            ),
            Some(errors) => {
                let mut observed = BTreeSet::new();
                for error in errors {
                    let text = |name: &str| {
                        error
                            .get(name)
                            .and_then(Value::as_str)
                            .filter(|v| !v.is_empty())
                    };
                    match (text("stage"), text("rawMessage"), text("message")) {
                        (Some(stage), Some(_), Some(_)) => {
                            observed.insert(format!("infrastructure_error_stage.{stage}"));
                        }
                        _ => self.at_key(
                            "infrastructureErrors",
                            FAILURE_FIXTURE,
                            "infrastructure failure fixtures require stage, rawMessage, and message".into(),
                        ),
                    }
                    if !matches!(
                        error.get("path"),
                        None | Some(Value::Null | Value::String(_))
                    ) {
                        self.at_key(
                            "infrastructureErrors",
                            FAILURE_FIXTURE,
                            "infrastructure failure fixture path must be a string or null".into(),
                        );
                    }
                }
                self.stage_diff(
                    "infrastructureErrors",
                    "shared infrastructure failure stages",
                    "infrastructure_error_stage.",
                    &observed,
                    variants,
                );
            }
        }
    }

    /// Reports each stage variant the fixtures miss and each fixture stage that
    /// is not a variant.
    fn stage_diff(
        &mut self,
        line_key: &str,
        what: &str,
        prefix: &str,
        observed: &BTreeSet<String>,
        variants: &BTreeSet<String>,
    ) {
        let expected: BTreeSet<&String> =
            variants.iter().filter(|v| v.starts_with(prefix)).collect();
        for missing in expected.iter().filter(|v| !observed.contains(**v)) {
            self.at_key(
                line_key,
                FAILURE_FIXTURE,
                format!("{what} differ: missing {missing}"),
            );
        }
        for stale in observed.iter().filter(|v| !expected.contains(v)) {
            self.at_key(
                line_key,
                FAILURE_FIXTURE,
                format!("{what} differ: stale {stale}"),
            );
        }
    }

    /// `forbiddenExports` covers exactly the supported adapters, and no listed
    /// symbol appears in its listed source file.
    fn forbidden_exports(&mut self, manifest: &Map<String, Value>, supported: Option<&[String]>) {
        const KEY: &str = "forbiddenExports";
        let Some(owners) = manifest
            .get(KEY)
            .and_then(Value::as_object)
            .filter(|owners| !owners.is_empty())
        else {
            self.at_key(
                KEY,
                FORBIDDEN_EXPORT,
                "forbiddenExports must be a non-empty object".into(),
            );
            return;
        };
        if let Some(supported) = supported {
            let supported: BTreeSet<&str> = supported.iter().map(String::as_str).collect();
            let declared: BTreeSet<&str> = owners.keys().map(String::as_str).collect();
            let mut details = Vec::new();
            let missing: Vec<&str> = supported.difference(&declared).copied().collect();
            if !missing.is_empty() {
                details.push(format!("missing {}", missing.join(", ")));
            }
            let unexpected: Vec<&str> = declared.difference(&supported).copied().collect();
            if !unexpected.is_empty() {
                details.push(format!("unexpected {}", unexpected.join(", ")));
            }
            if !details.is_empty() {
                self.at_key(
                    KEY,
                    FORBIDDEN_EXPORT,
                    format!(
                        "forbiddenExports must exactly match supportedAdapters ({})",
                        details.join("; ")
                    ),
                );
            }
        }

        for (owner, entries) in owners {
            let Some(entries) = entries.as_array().filter(|entries| !entries.is_empty()) else {
                self.at_key(
                    owner,
                    FORBIDDEN_EXPORT,
                    format!("forbiddenExports.{owner} must be a non-empty list"),
                );
                continue;
            };
            for entry in entries {
                let Some(path) = entry
                    .get("path")
                    .and_then(Value::as_str)
                    .filter(|path| !path.is_empty())
                else {
                    self.at_key(
                        owner,
                        FORBIDDEN_EXPORT,
                        format!("forbiddenExports.{owner} path must be a string"),
                    );
                    continue;
                };
                let label = format!("forbiddenExports.{owner}.{path}.symbols");
                let Some(symbols) =
                    self.string_list(entry.get("symbols"), &label, path, FORBIDDEN_EXPORT)
                else {
                    continue;
                };
                if symbols.is_empty() {
                    self.at_key(path, FORBIDDEN_EXPORT, format!("{label} must not be empty"));
                    continue;
                }
                let optional = match entry.get("optional") {
                    None => false,
                    Some(Value::Bool(optional)) => *optional,
                    Some(_) => {
                        self.at_key(
                            path,
                            FORBIDDEN_EXPORT,
                            format!("forbiddenExports.{owner}.{path}.optional must be boolean"),
                        );
                        continue;
                    }
                };
                let Some(full) = contained(self.root, path) else {
                    self.at_key(
                        path,
                        FORBIDDEN_EXPORT,
                        format!("forbiddenExports.{owner} path escapes the repository: {path}"),
                    );
                    continue;
                };
                if !full.is_file() {
                    if !optional {
                        self.at_key(
                            path,
                            FORBIDDEN_EXPORT,
                            format!("Cannot read {owner} forbidden-export surface {path}"),
                        );
                    }
                    continue;
                }
                let source = match std::fs::read_to_string(&full) {
                    Ok(source) => source,
                    Err(error) => {
                        self.at_key(
                            path,
                            FORBIDDEN_EXPORT,
                            format!("Cannot read {owner} forbidden-export surface {path}: {error}"),
                        );
                        continue;
                    }
                };
                for symbol in &symbols {
                    if let Some(offset) = find_symbol(&source, symbol) {
                        self.at(
                            path,
                            line_at(&source, offset),
                            FORBIDDEN_EXPORT,
                            format!("{owner} {path} still contains `{symbol}`"),
                        );
                    }
                }
            }
        }
    }
}

/// 1-based line of byte `offset` in `text`.
fn line_at(text: &str, offset: usize) -> usize {
    text[..offset].matches('\n').count() + 1
}

/// Resolves the repo-relative `relative` lexically under `root`, or `None` when
/// it is absolute or climbs above the root with `..`. Symlinks are not
/// followed; the manifest names tracked files, which are never symlinks here.
fn contained(root: &RepoRoot, relative: &str) -> Option<PathBuf> {
    let mut parts = Vec::new();
    for component in Path::new(relative).components() {
        match component {
            Component::Normal(part) => parts.push(part),
            Component::CurDir => {}
            Component::ParentDir => {
                parts.pop()?;
            }
            Component::RootDir | Component::Prefix(_) => return None,
        }
    }
    let mut path = root.path().to_path_buf();
    path.extend(parts);
    Some(path)
}

/// Byte offset of the first occurrence of `symbol` in `source`.
///
/// An identifier-shaped symbol (`[A-Za-z_][A-Za-z0-9_]*`) only matches where
/// neither neighbour is an ASCII identifier character, so a forbidden name
/// does not match a longer surviving name that contains it. Any other symbol
/// (for example `pub fn continuation`) is a raw substring.
fn find_symbol(source: &str, symbol: &str) -> Option<usize> {
    let identifier = symbol
        .chars()
        .next()
        .is_some_and(|first| first.is_ascii_alphabetic() || first == '_')
        && symbol.chars().all(is_identifier_char);
    if !identifier {
        return source.find(symbol);
    }
    let mut start = 0;
    while let Some(relative) = source[start..].find(symbol) {
        let offset = start + relative;
        let before = source[..offset].chars().next_back();
        let after = source[offset + symbol.len()..].chars().next();
        if !before.is_some_and(is_identifier_char) && !after.is_some_and(is_identifier_char) {
            return Some(offset);
        }
        // Identifier symbols are ASCII, so the next char boundary is one byte on.
        start = offset + 1;
    }
    None
}

fn is_identifier_char(c: char) -> bool {
    c.is_ascii_alphanumeric() || c == '_'
}

/// Converts a Rust `PascalCase` variant name to its manifest `snake_case` id,
/// exactly as the retired Python tool did with two regex passes:
/// `(.)([A-Z][a-z]+)` -> `\1_\2`, then `([a-z0-9])([A-Z])` -> `\1_\2`, then
/// lowercase. So `FormIdDatabaseAccess` becomes `form_id_database_access`.
pub(crate) fn snake_case(name: &str) -> String {
    let chars: Vec<char> = name.chars().collect();

    // Pass 1: an underscore before each capitalised word that follows any
    // character. Matches are non-overlapping, scanning left to right.
    let mut first = Vec::with_capacity(chars.len() * 2);
    let mut i = 0;
    while i < chars.len() {
        if i + 2 < chars.len()
            && chars[i + 1].is_ascii_uppercase()
            && chars[i + 2].is_ascii_lowercase()
        {
            let mut end = i + 3;
            while end < chars.len() && chars[end].is_ascii_lowercase() {
                end += 1;
            }
            first.push(chars[i]);
            first.push('_');
            first.extend_from_slice(&chars[i + 1..end]);
            i = end;
        } else {
            first.push(chars[i]);
            i += 1;
        }
    }

    // Pass 2: an underscore between a lowercase letter or digit and a capital.
    let mut second = String::with_capacity(first.len() * 2);
    let mut i = 0;
    while i < first.len() {
        let c = first[i];
        if i + 1 < first.len()
            && (c.is_ascii_lowercase() || c.is_ascii_digit())
            && first[i + 1].is_ascii_uppercase()
        {
            second.push(c);
            second.push('_');
            second.push(first[i + 1]);
            i += 2;
        } else {
            second.push(c);
            i += 1;
        }
    }
    second.to_lowercase()
}

#[cfg(test)]
#[path = "scan_run_contract_tests.rs"]
mod tests;
