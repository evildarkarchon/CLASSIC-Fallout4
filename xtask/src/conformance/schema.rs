//! Closed shapes of the conformance documents.
//!
//! Each document is a `#[serde(deny_unknown_fields)]` struct, so an unknown or
//! missing member, or a value of the wrong JSON type, fails deserialization.
//! What serde cannot express runs as a strict pass: [`super::json::parse_strict`]
//! rejects duplicate keys and floats before serde sees the text, and the
//! pattern helpers below check stable identities, fixture aliases, JSON paths
//! and relative paths.
//!
//! These structs replace the unenforced JSON Schema files that used to sit in
//! `tests/conformance/schemas/`. Run plans and receipts are read back through
//! [`RunPlan`] and [`Receipt`]; the attempt and report documents are only
//! ever written by xtask itself, so they have no reader struct.

use std::collections::BTreeMap;

use serde::Deserialize;
use serde_json::{Map, Value};

/// A scenario pack: `tests/conformance/packs/<dir>/v1.json`.
///
/// Pack authoring rules:
/// - `familyId`, capability, scenario and obligation IDs are stable machine
///   identifiers ([`is_stable_id`]); fixture aliases match [`is_fixture_ref`].
/// - `fixtureRoot` and every fixture path are canonical relative POSIX paths
///   that resolve to existing files beneath the repository and the root.
/// - A scenario's `action` is one of its own `capabilityIds`, and every
///   capability it names is declared by the pack.
/// - Inputs name fixtures only (see the pack module's input rule); results
///   live in `expected`, never in `input` or a fixture.
/// - No JSON number in a pack may be floating-point.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct Pack {
    /// Always `1`.
    pub schema_version: u64,
    /// Stable family identity.
    pub family_id: String,
    /// Positive family version.
    pub family_version: u64,
    /// The Rust crate that owns the family's behaviour.
    pub domain_owner: DomainOwner,
    /// Repo-relative directory every fixture lives under.
    pub fixture_root: String,
    /// Fixture alias to `fixtureRoot`-relative path.
    pub fixtures: BTreeMap<String, String>,
    /// Declared capabilities (non-empty).
    pub capabilities: Vec<Capability>,
    /// Scenarios (non-empty).
    pub scenarios: Vec<Scenario>,
    /// Consumer obligations the family declares; registered centrally in
    /// `consumer-obligations.json`.
    pub consumer_obligations: Vec<ObligationRef>,
}

/// The owning Rust crate of a pack.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct DomainOwner {
    /// Stable crate identity, e.g. `classic-scanlog-core`.
    pub rust_crate: String,
}

/// One capability a family exercises.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct Capability {
    /// Stable capability identity.
    pub id: String,
    /// Public Rust symbols behind the capability (non-empty, unique).
    pub rust_symbols: Vec<String>,
    /// Observation families the capability produces (non-empty, unique).
    pub observation_families: Vec<String>,
    /// A crate other than the pack's domain owner, when one owns this
    /// capability.
    #[serde(default)]
    pub rust_crate: Option<String>,
}

/// One scenario: inputs plus the exact expected observation.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct Scenario {
    /// Stable scenario identity.
    pub id: String,
    /// The capability this scenario executes; one of `capability_ids`.
    pub action: String,
    /// Capabilities the scenario touches (non-empty, unique).
    pub capability_ids: Vec<String>,
    /// Fixture aliases the scenario stages (unique).
    pub fixture_refs: Vec<String>,
    /// Input-only parameters handed to the participant.
    pub input: Map<String, Value>,
    /// The exact observation the participant must report.
    pub expected: Map<String, Value>,
    /// Narrow, rationale-bearing comparison rules.
    pub normalization: Normalization,
}

/// Per-scenario comparison rules.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct Normalization {
    /// Rewrite actual-side absolute `path` fields to fixture-root-relative.
    pub root_relative_paths: bool,
    /// Exact JSON paths whose arrays compare as multisets.
    pub unordered_paths: Vec<String>,
    /// Exact JSON paths removed from both sides, each with a rationale.
    pub excluded_paths: Vec<Exclusion>,
    /// Empty files a participant may or may not leave behind.
    #[serde(default)]
    pub optional_empty_files: Option<Vec<OptionalEmptyFile>>,
}

/// One excluded JSON path.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct Exclusion {
    /// Exact JSON path ([`is_exact_json_path`]).
    pub path: String,
    /// Why the path cannot be compared (non-blank).
    pub rationale: String,
}

/// One optional empty file selector.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct OptionalEmptyFile {
    /// Exact JSON path of the file list.
    pub path: String,
    /// File path relative to the fixture root ([`is_relative_file_path`]).
    pub relative_path: String,
    /// Why the file may be absent (non-blank).
    pub rationale: String,
}

/// A pack's declaration of one consumer obligation.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct ObligationRef {
    /// Stable obligation identity.
    pub id: String,
}

/// `tests/conformance/participants.json`: semantic participants other than
/// Rust, enrolled per family.
///
/// Every family is Rust-only by default. A listed family enrols `cxx` with
/// the capability IDs CXX covers; CXX then runs exactly the scenarios whose
/// `action` is one of them. Families are sorted and unique; capability IDs are
/// non-empty, sorted and unique.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct Participants {
    /// Always `1`.
    pub schema_version: u64,
    /// Enrolments, sorted by `familyId`.
    pub families: Vec<ParticipantFamily>,
}

/// One family's non-Rust enrolments.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct ParticipantFamily {
    /// The enrolled family.
    pub family_id: String,
    /// The CXX enrolment; the only enrollable participant.
    #[serde(default)]
    pub cxx: Option<Enrolment>,
}

/// The capabilities one participant covers in a family.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct Enrolment {
    /// Sorted, unique, non-empty capability IDs.
    pub capability_ids: Vec<String>,
}

/// `tests/conformance/consumer-obligations.json`: the CLI, GUI and TUI
/// consumer registry.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct ConsumerObligations {
    /// Always `1`.
    pub schema_version: u64,
    /// Per-family consumer registrations.
    pub families: Vec<ConsumerFamily>,
}

/// The consumers registered for one family.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct ConsumerFamily {
    /// The family the obligations belong to.
    pub family_id: String,
    /// Registered consumers (non-empty).
    pub consumers: Vec<Consumer>,
}

/// One consumer and the obligations it owns in a family.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct Consumer {
    /// `cli`, `gui` or `tui`.
    pub id: String,
    /// Execution instances that must each produce a receipt.
    pub execution_instance_ids: Vec<String>,
    /// Repo-relative sources whose bytes identify the consumer run.
    pub source_paths: Vec<String>,
    /// Owned obligations (non-empty).
    pub obligations: Vec<ConsumerObligation>,
}

/// One consumer obligation and its exact expected observation.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct ConsumerObligation {
    /// Stable obligation identity; declared by the family's pack.
    pub id: String,
    /// Pack scenarios the obligation exercises (non-empty, unique).
    pub scenario_ids: Vec<String>,
    /// The exact observation the consumer must report.
    pub expected: Map<String, Value>,
}

/// An input-only run plan, written by `conformance run` beside the reserved
/// receipt path and handed to one participant invocation.
///
/// Exactly one of `scenarios` (semantic adapters) or `obligations`
/// (consumers) is present, matching `participant.role`. A plan carries no
/// `expected` member: participants never see the answer.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct RunPlan {
    /// Always `1`.
    pub schema_version: u64,
    /// The pack's family.
    pub family_id: String,
    /// The pack's family version.
    pub family_version: u64,
    /// Framed digest of the compiled pack, its oracles and its fixtures.
    pub expectation_digest: String,
    /// Absolute, OS-native fixture root.
    pub fixture_root: String,
    /// Fixture alias to absolute, OS-native path.
    pub fixtures: BTreeMap<String, String>,
    /// Sorted repo-relative paths whose bytes form `sourceIdentity`.
    pub source_paths: Vec<String>,
    /// Who runs the plan.
    pub participant: PlanParticipant,
    /// This invocation's identity.
    pub invocation: PlanInvocation,
    /// Semantic-adapter payload: the applicable scenarios, input only.
    #[serde(default)]
    pub scenarios: Option<Vec<PlanScenario>>,
    /// Consumer payload: the owned obligations.
    #[serde(default)]
    pub obligations: Option<Vec<PlanObligation>>,
}

/// The participant a plan or receipt belongs to.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct PlanParticipant {
    /// `rust`, `cxx`, `cli`, `gui` or `tui`.
    pub id: String,
    /// `semantic-adapter` or `consumer`.
    pub role: String,
    /// The execution instance, e.g. `rust` or `windows-msvc`.
    pub execution_instance_id: String,
}

/// One invocation's identity, echoed by its receipt.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct PlanInvocation {
    /// UUID v4.
    pub id: String,
    /// `git:<HEAD>:sha256:<hex>` over the declared source paths.
    pub source_identity: String,
    /// Framed digest of the plan without this member.
    pub run_plan_digest: String,
}

/// One scenario as a participant sees it: everything but `expected`.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct PlanScenario {
    /// Scenario identity.
    pub id: String,
    /// The capability to execute.
    pub action: String,
    /// Capabilities the scenario touches.
    pub capability_ids: Vec<String>,
    /// Fixtures the scenario stages.
    pub fixture_refs: Vec<String>,
    /// Input-only parameters.
    pub input: Map<String, Value>,
    /// The declared comparison rules.
    pub normalization: Normalization,
}

/// One consumer obligation as a consumer sees it.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct PlanObligation {
    /// Obligation identity.
    pub id: String,
    /// Pack scenarios the obligation exercises.
    pub scenario_ids: Vec<String>,
}

/// A participant's receipt: its observations for one run plan.
///
/// The envelope echoes the plan's identity. `scenarios` belong to semantic
/// adapters and `obligations` to consumers. There is no `not_applicable`
/// status and no `policyExceptionId`: a required execution either completes
/// or fails.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct Receipt {
    /// Positive; anything but `1` is a stale receipt.
    pub schema_version: u64,
    /// Echoed from the plan.
    pub family_id: String,
    /// Echoed from the plan.
    pub family_version: u64,
    /// Echoed from the plan.
    pub expectation_digest: String,
    /// Echoed from the plan.
    pub invocation: PlanInvocation,
    /// Echoed from the plan.
    pub participant: PlanParticipant,
    /// The runner that produced the receipt.
    pub runner: Runner,
    /// Semantic-adapter evidence.
    #[serde(default)]
    pub scenarios: Option<Vec<ReceiptItem>>,
    /// Consumer evidence.
    #[serde(default)]
    pub obligations: Option<Vec<ReceiptItem>>,
}

/// The runner that wrote a receipt.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct Runner {
    /// Stable runner identity.
    pub id: String,
    /// Positive runner version.
    pub version: u64,
    /// Stable platform identity, e.g. `windows`.
    pub platform: String,
    /// Stable toolchain identity, e.g. `rust`.
    pub toolchain: String,
}

/// One scenario's or obligation's execution evidence.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct ReceiptItem {
    /// Scenario or obligation identity.
    pub id: String,
    /// `completed` or `failed`.
    pub execution_status: String,
    /// Scenario evidence only: the plan's capability IDs, echoed.
    #[serde(default)]
    pub capability_ids: Option<Vec<String>>,
    /// The observation (an object).
    pub observation: Value,
    /// `null` when completed; `{kind, message}` when failed.
    pub failure: Option<ItemFailure>,
}

/// Why a participant could not complete one scenario or obligation.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct ItemFailure {
    /// Stable failure identity.
    pub kind: String,
    /// Non-empty explanation.
    pub message: String,
}

/// Whether `value` is a stable machine identity: lowercase ASCII words of
/// letters and digits, starting with a letter, joined by single `.` or `-`.
pub fn is_stable_id(value: &str) -> bool {
    let mut segments = value.split(['.', '-']);
    let Some(first) = segments.next() else {
        return false;
    };
    let word = |segment: &str| {
        !segment.is_empty()
            && segment
                .bytes()
                .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit())
    };
    first.starts_with(|c: char| c.is_ascii_lowercase()) && word(first) && segments.all(word)
}

/// Whether `value` is a fixture alias: an ASCII letter, then letters, digits,
/// `_` or `-`.
pub fn is_fixture_ref(value: &str) -> bool {
    let mut bytes = value.bytes();
    bytes
        .next()
        .is_some_and(|first| first.is_ascii_alphabetic())
        && bytes.all(|byte| byte.is_ascii_alphanumeric() || byte == b'_' || byte == b'-')
}

/// Whether `value` is one exact, non-root JSON path such as `$.a[0].b`: no
/// wildcards, recursive descent or root-wide selection.
pub fn is_exact_json_path(value: &str) -> bool {
    let Some(mut rest) = value.strip_prefix('$') else {
        return false;
    };
    if rest.is_empty() {
        return false;
    }
    while !rest.is_empty() {
        if let Some(after) = rest.strip_prefix('.') {
            let end = after
                .find(|c: char| !(c.is_ascii_alphanumeric() || c == '_' || c == '-'))
                .unwrap_or(after.len());
            let name = &after[..end];
            if !name.starts_with(|c: char| c.is_ascii_alphabetic() || c == '_') {
                return false;
            }
            rest = &after[end..];
        } else if let Some(after) = rest.strip_prefix('[') {
            let Some(close) = after.find(']') else {
                return false;
            };
            let index = &after[..close];
            let canonical = index == "0"
                || (!index.is_empty()
                    && !index.starts_with('0')
                    && index.bytes().all(|byte| byte.is_ascii_digit()));
            if !canonical {
                return false;
            }
            rest = &after[close + 1..];
        } else {
            return false;
        }
    }
    true
}

/// Whether `value` is a canonical relative POSIX path: non-empty, no `\`, not
/// absolute (POSIX or Windows drive), no empty, `.` or `..` segment.
pub fn is_canonical_relative_path(value: &str) -> bool {
    let bytes = value.as_bytes();
    let drive = bytes.len() >= 2 && bytes[0].is_ascii_alphabetic() && bytes[1] == b':';
    !value.is_empty()
        && !value.contains('\\')
        && !value.starts_with('/')
        && !drive
        && value
            .split('/')
            .all(|segment| !segment.is_empty() && segment != "." && segment != "..")
}

/// Whether `value` is an optional-empty-file path: a canonical relative path
/// whose segments also carry no `:` or NUL.
pub fn is_relative_file_path(value: &str) -> bool {
    is_canonical_relative_path(value) && !value.contains([':', '\0'])
}

#[cfg(test)]
#[path = "schema_tests.rs"]
mod tests;
