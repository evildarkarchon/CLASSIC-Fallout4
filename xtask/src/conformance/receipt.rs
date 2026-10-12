//! Central receipt validation for one prepared invocation.
//!
//! A participant's receipt is untrusted evidence. [`validate`] checks it
//! against the plan it answers, in stages that each stop at the first failing
//! stage, so a broken envelope never reaches comparison:
//!
//! 1. a receipt exists (`missing_execution_receipt`) and is strict JSON
//!    (`malformed_execution_receipt`);
//! 2. no item claims `skipped` or `unsupported` (`applicability_violation`):
//!    a required execution cannot opt out;
//! 3. the closed receipt shape (`malformed_execution_receipt`);
//! 4. the echoed identity (schema version, family, version, expectation
//!    digest, invocation) matches the plan (`stale_execution_receipt`);
//! 5. no unexpected evidence: the participant matches, IDs are unique and
//!    planned, and capability IDs match the plan
//!    (`malformed_execution_receipt`);
//! 6. per planned item: missing evidence (`missing_execution_receipt`), a
//!    participant-reported failure (`adapter_command_failure`), or exact
//!    comparison. Scenarios are compared after the family normalization
//!    before the declared one, the declared normalization, the family
//!    normalization after it, and the display-content carrier check (any of
//!    which fails as `normalization_failure`); every remaining difference is a
//!    `semantic_conformance_mismatch`. Consumer obligations compare exactly
//!    against the catalog's expectation.
//!
//! [`check_current`] separately proves the pack, its fixtures and the plan
//! bytes did not change between planning and validation.

use std::collections::{BTreeMap, BTreeSet};

use serde_json::{Map, Value, json};

use super::compare::{exact_differences, normalize, validate_display_content};
use super::families::{self, Stage};
use super::json::parse_strict;
use super::plan::PreparedPack;
use super::schema::{PlanParticipant, Receipt, ReceiptItem, RunPlan, is_stable_id};

/// Why an execution, invocation or family failed. Declaration order is the
/// report order.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub(crate) enum FailureKind {
    /// The toolchain or environment a participant needs was unavailable.
    LocalEnvironment,
    /// The participant command failed, timed out, or reported a failure.
    AdapterCommand,
    /// A required receipt, scenario or obligation produced no evidence.
    MissingReceipt,
    /// The receipt is not well-formed evidence for its plan.
    MalformedReceipt,
    /// The receipt or plan no longer matches the current tree.
    StaleReceipt,
    /// A required execution tried to opt out.
    Applicability,
    /// A consumer obligation lacks passing evidence from every required
    /// instance, or has no registration.
    CoverageMapping,
    /// A declared or family normalization could not be applied.
    Normalization,
    /// The normalized observation differs from the expectation.
    SemanticMismatch,
}

impl FailureKind {
    /// The protocol spelling.
    pub fn as_str(self) -> &'static str {
        match self {
            FailureKind::LocalEnvironment => "local_environment_failure",
            FailureKind::AdapterCommand => "adapter_command_failure",
            FailureKind::MissingReceipt => "missing_execution_receipt",
            FailureKind::MalformedReceipt => "malformed_execution_receipt",
            FailureKind::StaleReceipt => "stale_execution_receipt",
            FailureKind::Applicability => "applicability_violation",
            FailureKind::CoverageMapping => "coverage_mapping_gap",
            FailureKind::Normalization => "normalization_failure",
            FailureKind::SemanticMismatch => "semantic_conformance_mismatch",
        }
    }
}

/// One receipt-validation failure.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) struct ReceiptFailure {
    /// The failure kind.
    pub kind: FailureKind,
    /// The scenario or obligation it concerns, if any.
    pub item: Option<String>,
    /// The `$.`-style path it concerns, if any.
    pub path: Option<String>,
    /// Human-readable explanation.
    pub message: String,
}

impl ReceiptFailure {
    fn new(kind: FailureKind, message: impl Into<String>) -> Self {
        Self {
            kind,
            item: None,
            path: None,
            message: message.into(),
        }
    }

    fn item(mut self, item: &str) -> Self {
        self.item = Some(item.to_owned());
        self
    }

    fn at(mut self, path: &str) -> Self {
        self.path = Some(path.to_owned());
        self
    }

    /// The failure as a report document member.
    pub fn document(&self) -> Value {
        json!({
            "kind": self.kind.as_str(),
            "scenarioId": self.item,
            "path": self.path,
            "message": self.message,
        })
    }
}

/// The verdict for one planned scenario or obligation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct ItemResult {
    /// Scenario or obligation ID.
    pub id: String,
    /// `completed`, `failed` or `missing`.
    pub status: String,
    /// Whether it passed.
    pub passed: bool,
    /// The kinds of its failures, sorted and unique.
    pub kinds: Vec<FailureKind>,
}

impl ItemResult {
    fn new(id: &str, status: &str, failures: &[ReceiptFailure]) -> Self {
        let kinds: BTreeSet<FailureKind> = failures.iter().map(|failure| failure.kind).collect();
        Self {
            id: id.to_owned(),
            status: status.to_owned(),
            passed: kinds.is_empty(),
            kinds: kinds.into_iter().collect(),
        }
    }

    fn document(&self) -> Value {
        json!({
            "id": self.id,
            "executionStatus": self.status,
            "result": if self.passed { "pass" } else { "fail" },
            "failureKinds": self.kinds.iter().map(|kind| kind.as_str()).collect::<Vec<_>>(),
        })
    }
}

/// The validated outcome of one prepared invocation.
#[derive(Debug, Clone)]
pub(crate) struct PreparedReport {
    /// The plan's family.
    pub family_id: String,
    /// The plan's family version.
    pub family_version: u64,
    /// The plan's expectation digest.
    pub expectation_digest: String,
    /// The plan's invocation (`id`, `sourceIdentity`, `runPlanDigest`).
    pub invocation: Value,
    /// The plan's participant.
    pub participant: PlanParticipant,
    /// Per planned scenario (semantic adapters).
    pub scenarios: Vec<ItemResult>,
    /// Per planned obligation (consumers).
    pub obligations: Vec<ItemResult>,
    /// Every failure, sorted.
    pub failures: Vec<ReceiptFailure>,
}

impl PreparedReport {
    /// A report for `plan` carrying only `failures`.
    pub fn failed(plan: &RunPlan, failures: Vec<ReceiptFailure>) -> Self {
        Self::from_plan(plan, Vec::new(), Vec::new(), failures)
    }

    fn from_plan(
        plan: &RunPlan,
        scenarios: Vec<ItemResult>,
        obligations: Vec<ItemResult>,
        mut failures: Vec<ReceiptFailure>,
    ) -> Self {
        failures.sort();
        Self {
            family_id: plan.family_id.clone(),
            family_version: plan.family_version,
            expectation_digest: plan.expectation_digest.clone(),
            invocation: json!({
                "id": plan.invocation.id,
                "sourceIdentity": plan.invocation.source_identity,
                "runPlanDigest": plan.invocation.run_plan_digest,
            }),
            participant: plan.participant.clone(),
            scenarios,
            obligations,
            failures,
        }
    }

    /// Whether every planned item passed.
    pub fn passed(&self) -> bool {
        self.failures.is_empty()
    }

    /// The report as a JSON document.
    pub fn document(&self) -> Value {
        let mut document = json!({
            "schemaVersion": 1,
            "scope": "prepared-invocation",
            "familyId": self.family_id,
            "familyVersion": self.family_version,
            "expectationDigest": self.expectation_digest,
            "invocation": self.invocation,
            "participant": {
                "id": self.participant.id,
                "role": self.participant.role,
                "executionInstanceId": self.participant.execution_instance_id,
            },
            "result": if self.passed() { "pass" } else { "fail" },
            "scenarios": self.scenarios.iter().map(ItemResult::document).collect::<Vec<_>>(),
            "failures": self.failures.iter().map(ReceiptFailure::document).collect::<Vec<_>>(),
        });
        if !self.obligations.is_empty() {
            document["obligations"] = self.obligations.iter().map(ItemResult::document).collect();
        }
        document
    }
}

/// One consumer obligation's catalog expectation, by obligation ID.
pub(crate) type ConsumerExpectations = BTreeMap<String, Map<String, Value>>;

/// Validates `receipt` (its bytes, or `None` when the participant wrote
/// none) against `plan`, comparing with `prepared`'s compiled expectations or,
/// for a consumer, with `consumer`'s catalog expectations.
pub(crate) fn validate(
    prepared: &PreparedPack,
    plan: &RunPlan,
    receipt: Option<&[u8]>,
    consumer: Option<&ConsumerExpectations>,
) -> PreparedReport {
    let fail = |failure: ReceiptFailure| PreparedReport::failed(plan, vec![failure]);
    let Some(bytes) = receipt else {
        return fail(ReceiptFailure::new(
            FailureKind::MissingReceipt,
            "the prepared invocation did not produce a receipt",
        ));
    };
    let text = match std::str::from_utf8(bytes) {
        Ok(text) => text,
        Err(_) => {
            return fail(ReceiptFailure::new(
                FailureKind::MalformedReceipt,
                "the receipt is not UTF-8",
            ));
        }
    };
    let value = match parse_strict(text) {
        Ok(document) => document.value().clone(),
        Err(error) => {
            return fail(ReceiptFailure::new(
                FailureKind::MalformedReceipt,
                format!("the receipt is not strict JSON: {error}"),
            ));
        }
    };
    let forbidden = forbidden_statuses(&value);
    if !forbidden.is_empty() {
        return PreparedReport::failed(plan, forbidden);
    }
    let receipt = match shape(&value) {
        Ok(receipt) => receipt,
        Err(message) => {
            return fail(ReceiptFailure::new(FailureKind::MalformedReceipt, message));
        }
    };
    let stale = stale_identity(&receipt, plan);
    if !stale.is_empty() {
        return PreparedReport::failed(plan, stale);
    }
    let unexpected = unexpected_evidence(&receipt, plan);
    if !unexpected.is_empty() {
        return PreparedReport::failed(plan, unexpected);
    }
    match (&plan.obligations, consumer) {
        (Some(planned), Some(expectations)) => {
            let items = receipt.obligations.unwrap_or_default();
            obligations(
                plan,
                planned.iter().map(|o| o.id.as_str()),
                &items,
                expectations,
            )
        }
        (Some(_), None) => fail(ReceiptFailure::new(
            FailureKind::Applicability,
            "consumer validation requires the repository obligation catalog",
        )),
        (None, _) => {
            let items = receipt.scenarios.unwrap_or_default();
            scenarios(prepared, plan, &items)
        }
    }
}

/// `skipped` or `unsupported` statuses, read before the shape check so they
/// classify as opting out rather than as malformed evidence.
fn forbidden_statuses(value: &Value) -> Vec<ReceiptFailure> {
    let items = value
        .get("scenarios")
        .or_else(|| value.get("obligations"))
        .and_then(Value::as_array);
    items
        .into_iter()
        .flatten()
        .filter(|item| {
            matches!(
                item.get("executionStatus").and_then(Value::as_str),
                Some("skipped" | "unsupported")
            )
        })
        .map(|item| {
            let failure = ReceiptFailure::new(
                FailureKind::Applicability,
                "a required execution cannot be skipped or reported as unsupported",
            )
            .at("$.executionStatus");
            match item.get("id").and_then(Value::as_str) {
                Some(id) => failure.item(id),
                None => failure,
            }
        })
        .collect()
}

/// Whether `value` is a lowercase canonical UUID v4.
fn is_uuid_v4(value: &str) -> bool {
    let bytes = value.as_bytes();
    bytes.len() == 36
        && bytes.iter().enumerate().all(|(index, byte)| match index {
            8 | 13 | 18 | 23 => *byte == b'-',
            14 => *byte == b'4',
            19 => matches!(byte, b'8' | b'9' | b'a' | b'b'),
            _ => matches!(byte, b'0'..=b'9' | b'a'..=b'f'),
        })
}

/// Whether `value` is `sha256:<64 lowercase hex>`.
pub(crate) fn is_sha256(value: &str) -> bool {
    value.strip_prefix("sha256:").is_some_and(|hex| {
        hex.len() == 64 && hex.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'))
    })
}

/// Whether `value` is `git:<40-64 hex>:sha256:<64 hex>`, all lowercase.
pub(crate) fn is_source_identity(value: &str) -> bool {
    let Some(rest) = value.strip_prefix("git:") else {
        return false;
    };
    let Some((revision, digest)) = rest.split_once(':') else {
        return false;
    };
    (40..=64).contains(&revision.len())
        && revision
            .bytes()
            .all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'))
        && is_sha256(digest)
}

/// Deserializes the closed receipt shape and checks what serde cannot.
fn shape(value: &Value) -> Result<Receipt, String> {
    let receipt: Receipt =
        serde_json::from_value(value.clone()).map_err(|error| format!("receipt shape: {error}"))?;
    let consumer = receipt.participant.role == "consumer";
    let checks: [(bool, &str); 11] = [
        (
            receipt.schema_version >= 1,
            "schemaVersion must be a positive integer",
        ),
        (
            receipt.family_version >= 1,
            "familyVersion must be a positive integer",
        ),
        (
            is_stable_id(&receipt.family_id),
            "familyId must be a stable identifier",
        ),
        (
            is_sha256(&receipt.expectation_digest),
            "expectationDigest must be sha256:<hex>",
        ),
        (
            is_uuid_v4(&receipt.invocation.id),
            "invocation.id must be a UUID v4",
        ),
        (
            is_source_identity(&receipt.invocation.source_identity),
            "invocation.sourceIdentity must be git:<revision>:sha256:<hex>",
        ),
        (
            is_sha256(&receipt.invocation.run_plan_digest),
            "invocation.runPlanDigest must be sha256:<hex>",
        ),
        (
            is_stable_id(&receipt.participant.id)
                && is_stable_id(&receipt.participant.execution_instance_id),
            "participant id and executionInstanceId must be stable identifiers",
        ),
        (
            matches!(
                receipt.participant.role.as_str(),
                "semantic-adapter" | "consumer"
            ),
            "participant.role must be semantic-adapter or consumer",
        ),
        (
            is_stable_id(&receipt.runner.id)
                && receipt.runner.version >= 1
                && is_stable_id(&receipt.runner.platform)
                && is_stable_id(&receipt.runner.toolchain),
            "runner id, platform and toolchain must be stable identifiers and version positive",
        ),
        (
            if consumer {
                receipt.obligations.is_some() && receipt.scenarios.is_none()
            } else {
                receipt.scenarios.is_some() && receipt.obligations.is_none()
            },
            "a semantic adapter reports scenarios and a consumer reports obligations",
        ),
    ];
    if let Some((_, message)) = checks.iter().find(|(ok, _)| !ok) {
        return Err(format!("receipt shape: {message}"));
    }
    let items = receipt
        .scenarios
        .as_ref()
        .or(receipt.obligations.as_ref())
        .into_iter()
        .flatten();
    for (index, item) in items.enumerate() {
        let at = if consumer {
            format!("obligations[{index}]")
        } else {
            format!("scenarios[{index}]")
        };
        item_shape(item, consumer).map_err(|message| format!("receipt shape: {at}: {message}"))?;
    }
    Ok(receipt)
}

fn item_shape(item: &ReceiptItem, consumer: bool) -> Result<(), String> {
    if !is_stable_id(&item.id) {
        return Err("id must be a stable identifier".into());
    }
    match (&item.capability_ids, consumer) {
        (Some(_), true) => return Err("obligation evidence has no capabilityIds".into()),
        (None, false) => return Err("scenario evidence needs capabilityIds".into()),
        (Some(ids), false) => {
            let unique = ids.iter().collect::<BTreeSet<_>>().len() == ids.len();
            if ids.is_empty() || !unique || !ids.iter().all(|id| is_stable_id(id)) {
                return Err(
                    "capabilityIds must be a non-empty list of unique stable identifiers".into(),
                );
            }
        }
        (None, true) => {}
    }
    if !item.observation.is_object() {
        return Err("observation must be an object".into());
    }
    match (item.execution_status.as_str(), &item.failure) {
        ("completed", None) => Ok(()),
        ("completed", Some(_)) => Err("failure must be null when completed".into()),
        ("failed", Some(failure))
            if is_stable_id(&failure.kind) && !failure.message.trim().is_empty() =>
        {
            Ok(())
        }
        ("failed", _) => Err("a failed execution needs failure {kind, message}".into()),
        _ => Err("executionStatus must be completed or failed".into()),
    }
}

/// Echoed identity that differs from the plan.
fn stale_identity(receipt: &Receipt, plan: &RunPlan) -> Vec<ReceiptFailure> {
    let stale = |label: &str| {
        ReceiptFailure::new(
            FailureKind::StaleReceipt,
            format!("receipt {label} does not match the prepared invocation"),
        )
        .at(&format!("$.{label}"))
    };
    let mut failures = Vec::new();
    if receipt.schema_version != plan.schema_version {
        failures.push(stale("schemaVersion"));
    }
    if receipt.family_id != plan.family_id {
        failures.push(stale("familyId"));
    }
    if receipt.family_version != plan.family_version {
        failures.push(stale("familyVersion"));
    }
    if receipt.expectation_digest != plan.expectation_digest {
        failures.push(stale("expectationDigest"));
    }
    for (label, actual, expected) in [
        ("invocation.id", &receipt.invocation.id, &plan.invocation.id),
        (
            "invocation.runPlanDigest",
            &receipt.invocation.run_plan_digest,
            &plan.invocation.run_plan_digest,
        ),
        (
            "invocation.sourceIdentity",
            &receipt.invocation.source_identity,
            &plan.invocation.source_identity,
        ),
    ] {
        if actual != expected {
            failures.push(stale(label));
        }
    }
    failures
}

/// Evidence the plan did not ask for.
fn unexpected_evidence(receipt: &Receipt, plan: &RunPlan) -> Vec<ReceiptFailure> {
    let mut failures = Vec::new();
    for (label, actual, expected) in [
        ("id", &receipt.participant.id, &plan.participant.id),
        ("role", &receipt.participant.role, &plan.participant.role),
        (
            "executionInstanceId",
            &receipt.participant.execution_instance_id,
            &plan.participant.execution_instance_id,
        ),
    ] {
        if actual != expected {
            failures.push(
                ReceiptFailure::new(
                    FailureKind::MalformedReceipt,
                    format!("receipt participant {label} is unexpected for this prepared run"),
                )
                .at(&format!("$.participant.{label}")),
            );
        }
    }
    let planned: BTreeMap<&str, Option<&Vec<String>>> = match (&plan.scenarios, &plan.obligations) {
        (Some(scenarios), _) => scenarios
            .iter()
            .map(|s| (s.id.as_str(), Some(&s.capability_ids)))
            .collect(),
        (None, Some(obligations)) => obligations.iter().map(|o| (o.id.as_str(), None)).collect(),
        (None, None) => BTreeMap::new(),
    };
    let items = receipt.scenarios.as_ref().or(receipt.obligations.as_ref());
    let mut seen = BTreeSet::new();
    let mut duplicates = BTreeSet::new();
    for item in items.into_iter().flatten() {
        if !seen.insert(item.id.as_str()) {
            duplicates.insert(item.id.as_str());
        }
        match planned.get(item.id.as_str()) {
            None => failures.push(
                ReceiptFailure::new(
                    FailureKind::MalformedReceipt,
                    "receipt contains an unexpected scenario identity",
                )
                .item(&item.id),
            ),
            Some(Some(capabilities)) if item.capability_ids.as_ref() != Some(*capabilities) => {
                failures.push(
                    ReceiptFailure::new(
                        FailureKind::MalformedReceipt,
                        "receipt capability identities differ from the run plan",
                    )
                    .item(&item.id)
                    .at("$.capabilityIds"),
                );
            }
            Some(_) => {}
        }
    }
    for id in duplicates {
        failures.push(
            ReceiptFailure::new(
                FailureKind::MalformedReceipt,
                "receipt contains duplicate scenario execution evidence",
            )
            .item(id),
        );
    }
    failures
}

/// Compares each planned consumer obligation with its catalog expectation.
fn obligations<'a>(
    plan: &RunPlan,
    planned: impl Iterator<Item = &'a str>,
    items: &[ReceiptItem],
    expectations: &ConsumerExpectations,
) -> PreparedReport {
    let by_id: BTreeMap<&str, &ReceiptItem> =
        items.iter().map(|item| (item.id.as_str(), item)).collect();
    let mut results = Vec::new();
    let mut failures = Vec::new();
    for id in planned {
        let (status, own) = match (by_id.get(id), expectations.get(id)) {
            (Some(actual), Some(expected)) if actual.execution_status == "completed" => {
                let own: Vec<ReceiptFailure> =
                    exact_differences(&Value::Object(expected.clone()), &actual.observation)
                        .into_iter()
                        .map(|difference| {
                            ReceiptFailure::new(
                                FailureKind::SemanticMismatch,
                                format!(
                                    "consumer obligation observation differs: {}",
                                    difference.kind
                                ),
                            )
                            .item(id)
                            .at(&difference.path)
                        })
                        .collect();
                ("completed", own)
            }
            (Some(_), Some(_)) => (
                "failed",
                vec![
                    ReceiptFailure::new(
                        FailureKind::AdapterCommand,
                        "consumer execution failed before producing a completed observation",
                    )
                    .item(id),
                ],
            ),
            _ => (
                "missing",
                vec![
                    ReceiptFailure::new(
                        FailureKind::MissingReceipt,
                        "the required consumer obligation did not produce execution evidence",
                    )
                    .item(id),
                ],
            ),
        };
        results.push(ItemResult::new(id, status, &own));
        failures.extend(own);
    }
    PreparedReport::from_plan(plan, Vec::new(), results, failures)
}

/// Normalizes and compares each planned scenario.
fn scenarios(prepared: &PreparedPack, plan: &RunPlan, items: &[ReceiptItem]) -> PreparedReport {
    let by_id: BTreeMap<&str, &ReceiptItem> =
        items.iter().map(|item| (item.id.as_str(), item)).collect();
    let planned: BTreeSet<&str> = plan
        .scenarios
        .iter()
        .flatten()
        .map(|scenario| scenario.id.as_str())
        .collect();
    let display: BTreeSet<&str> = prepared
        .pack
        .capabilities
        .iter()
        .filter(|capability| {
            capability
                .observation_families
                .iter()
                .any(|f| f == "display-content")
        })
        .map(|capability| capability.id.as_str())
        .collect();
    let mut results = Vec::new();
    let mut failures = Vec::new();
    for (index, scenario) in prepared.pack.scenarios.iter().enumerate() {
        let id = scenario.id.as_str();
        if !planned.contains(id) {
            continue;
        }
        let (status, own) = match by_id.get(id) {
            None => (
                "missing",
                vec![
                    ReceiptFailure::new(
                        FailureKind::MissingReceipt,
                        "the required scenario did not produce execution evidence",
                    )
                    .item(id),
                ],
            ),
            Some(actual) if actual.execution_status == "failed" => {
                let reported = actual
                    .failure
                    .as_ref()
                    .map(|failure| format!(": {}: {}", failure.kind, failure.message))
                    .unwrap_or_default();
                (
                    "failed",
                    vec![
                        ReceiptFailure::new(
                            FailureKind::AdapterCommand,
                            format!("adapter execution failed before producing a completed observation{reported}"),
                        )
                        .item(id),
                    ],
                )
            }
            Some(actual) => {
                let observation = actual.observation.as_object().cloned().unwrap_or_default();
                let checks_display = scenario
                    .capability_ids
                    .iter()
                    .any(|capability| display.contains(capability.as_str()));
                let own = compare_scenario(prepared, plan, index, observation, checks_display);
                ("completed", own)
            }
        };
        results.push(ItemResult::new(id, status, &own));
        failures.extend(own);
    }
    PreparedReport::from_plan(plan, results, Vec::new(), failures)
}

/// Runs the normalization pipeline and exact comparison for one completed
/// scenario.
fn compare_scenario(
    prepared: &PreparedPack,
    plan: &RunPlan,
    index: usize,
    observation: Map<String, Value>,
    checks_display: bool,
) -> Vec<ReceiptFailure> {
    let scenario = &prepared.pack.scenarios[index];
    let family = prepared.family_id.as_str();
    let action = scenario.action.as_str();
    let normalized = families::normalize_observation(
        family,
        action,
        Stage::BeforeDeclared,
        prepared.expected[index].clone(),
        observation,
    )
    .and_then(|(expected, actual)| {
        normalize(
            expected,
            actual,
            &scenario.normalization,
            &plan.fixture_root,
        )
    })
    .and_then(|(expected, actual)| {
        families::normalize_observation(family, action, Stage::AfterDeclared, expected, actual)
    })
    .and_then(|(expected, actual)| {
        let (expected, actual) = (Value::Object(expected), Value::Object(actual));
        if checks_display {
            validate_display_content(&expected, &actual)?;
        }
        Ok((expected, actual))
    });
    match normalized {
        Err(error) => vec![
            ReceiptFailure::new(FailureKind::Normalization, error.message)
                .item(&scenario.id)
                .at(&error.path),
        ],
        Ok((expected, actual)) => exact_differences(&expected, &actual)
            .into_iter()
            .map(|difference| {
                ReceiptFailure::new(
                    FailureKind::SemanticMismatch,
                    format!("exact observation differs: {}", difference.kind),
                )
                .item(&scenario.id)
                .at(&difference.path)
            })
            .collect(),
    }
}

/// Proves the pack and its fixtures (`current`, freshly prepared) and the
/// plan bytes on disk are unchanged since `prepared` was planned.
pub(crate) fn check_current(
    prepared: &PreparedPack,
    current: anyhow::Result<PreparedPack>,
    run_plan: &std::path::Path,
    planned_bytes: &[u8],
) -> Vec<ReceiptFailure> {
    let mut failures = Vec::new();
    match current {
        Err(error) => failures.push(ReceiptFailure::new(
            FailureKind::StaleReceipt,
            format!("the tracked pack or a fixture is no longer valid: {error:#}"),
        )),
        Ok(current) => {
            if current.canonical != prepared.canonical
                || current.expectation_digest != prepared.expectation_digest
            {
                failures.push(ReceiptFailure::new(
                    FailureKind::StaleReceipt,
                    "the tracked pack or a fixture changed after the run was planned",
                ));
            }
        }
    }
    match std::fs::read(run_plan) {
        Err(error) => failures.push(ReceiptFailure::new(
            FailureKind::StaleReceipt,
            format!("the run plan is no longer readable: {error}"),
        )),
        Ok(bytes) if bytes != planned_bytes => failures.push(ReceiptFailure::new(
            FailureKind::StaleReceipt,
            "the run plan changed after it was written",
        )),
        Ok(_) => {}
    }
    failures
}

#[cfg(test)]
#[path = "receipt_tests.rs"]
mod tests;
