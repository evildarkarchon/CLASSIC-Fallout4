//! Family reports and the repository-completeness verdict.
//!
//! A [`FamilyReport`] aggregates validated invocations ([`PreparedReport`]s)
//! against a denominator: one execution instance (what `conformance run`
//! reports per family) or every execution the family requires (what the
//! verdict reports). It fails on a missing execution, duplicate or
//! inconsistent evidence (more than one source revision, family version or
//! expectation digest), an invocation that failed receipt validation, an
//! invocation that does not report exactly its applicable scenarios or
//! obligations, and a consumer obligation without passing evidence from every
//! required instance (`coverage_mapping_gap`).
//!
//! The repository is complete when every pack's family report passes at
//! repository scope. There are no enforcement tiers: every family blocks.

use std::collections::{BTreeMap, BTreeSet};

use serde_json::{Value, json};

use super::applicability::{Execution, owned_obligations};
use super::json::canonical_bytes;
use super::plan::Role;
use super::receipt::{FailureKind, PreparedReport};
use super::schema::{Consumer, Pack};
use crate::{Finding, digest};

/// The family-level summary of an invocation that failed receipt validation.
const INVOCATION_FAILED: &str = "prepared invocation did not pass receipt validation";

/// What a family report claims to cover.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum Scope {
    /// One participant execution instance.
    Instance {
        /// The participant.
        participant: String,
        /// The execution instance.
        instance: String,
    },
    /// Every execution the family requires.
    Repository,
}

/// One family-level failure.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) struct ScopedFailure {
    /// The failure kind.
    pub kind: FailureKind,
    /// The participant it concerns, if any.
    pub participant: Option<String>,
    /// The execution instance it concerns, if any.
    pub instance: Option<String>,
    /// Human-readable explanation.
    pub message: String,
}

impl ScopedFailure {
    /// A failure about the execution `(participant, instance)`.
    pub fn at(
        kind: FailureKind,
        participant: &str,
        instance: &str,
        message: impl Into<String>,
    ) -> Self {
        Self {
            kind,
            participant: Some(participant.to_owned()),
            instance: Some(instance.to_owned()),
            message: message.into(),
        }
    }

    /// A failure of the whole family, not tied to one participant or instance.
    fn family(kind: FailureKind, message: impl Into<String>) -> Self {
        Self {
            kind,
            participant: None,
            instance: None,
            message: message.into(),
        }
    }
}

/// Consumer obligations covered by passing consumer invocations.
#[derive(Debug, Clone)]
pub(crate) struct ConsumerCoverage {
    /// The family.
    pub family_id: String,
    /// `(participant, instance)` executions whose evidence was used.
    pub executions: BTreeSet<(String, String)>,
    /// Digest of the selected invocations' report documents.
    pub evidence_digest: String,
    /// Covered obligations: `(obligation, participant, scenario IDs)`.
    pub covered: Vec<(String, String, Vec<String>)>,
    /// Uncovered obligations: `(obligation, message)`.
    pub gaps: Vec<(String, String)>,
}

impl ConsumerCoverage {
    /// Whether every obligation in scope is covered.
    pub fn passed(&self) -> bool {
        self.gaps.is_empty()
    }

    /// The coverage as a report document member: result, the executions whose
    /// evidence was used, the evidence digest, the covered obligations and a
    /// blocking `coverage_mapping_gap` failure per uncovered obligation.
    fn document(&self) -> Value {
        json!({
            "familyId": self.family_id,
            "result": if self.passed() { "pass" } else { "fail" },
            "executionEvidence": self
                .executions
                .iter()
                .map(|(participant, instance)| json!({"participantId": participant, "executionInstanceId": instance}))
                .collect::<Vec<_>>(),
            "preparedEvidenceDigest": self.evidence_digest,
            "obligations": self
                .covered
                .iter()
                .map(|(id, participant, evidence)| json!({"obligationId": id, "participantId": participant, "evidenceIds": evidence}))
                .collect::<Vec<_>>(),
            "failures": self
                .gaps
                .iter()
                .map(|(id, message)| json!({"kind": FailureKind::CoverageMapping.as_str(), "obligationId": id, "blocking": true, "message": message}))
                .collect::<Vec<_>>(),
        })
    }
}

/// SHA-256 over the canonical array of `reports`' documents, ordered by
/// participant, instance and invocation, binding coverage to its evidence.
fn evidence_digest(reports: &[&PreparedReport]) -> String {
    let mut sorted: Vec<&&PreparedReport> = reports.iter().collect();
    sorted.sort_by_key(|report| {
        (
            report.participant.id.clone(),
            report.participant.execution_instance_id.clone(),
            report.invocation["id"]
                .as_str()
                .unwrap_or_default()
                .to_owned(),
        )
    });
    let documents: Vec<Value> = sorted.iter().map(|report| report.document()).collect();
    let hex = digest::sha256_hex(&canonical_bytes(&Value::Array(documents)));
    format!("sha256:{hex}")
}

/// Derives consumer coverage from the consumer invocations in `reports`.
///
/// An obligation is covered when every in-scope instance of its owning
/// consumer has a passing invocation that passed the obligation.
/// `scope` limits the consumers and instances considered; obligations other
/// consumers own are still known registrations.
pub(crate) fn consumer_coverage(
    pack: &Pack,
    consumers: &[&Consumer],
    reports: &[&PreparedReport],
    scope: &Scope,
) -> ConsumerCoverage {
    let mut passed: BTreeMap<(String, String), BTreeSet<String>> = BTreeMap::new();
    for report in reports
        .iter()
        .filter(|report| report.participant.role == Role::Consumer.as_str())
    {
        let key = (
            report.participant.id.clone(),
            report.participant.execution_instance_id.clone(),
        );
        let ids = if report.passed() {
            report
                .obligations
                .iter()
                .filter(|item| item.passed)
                .map(|item| item.id.clone())
                .collect()
        } else {
            BTreeSet::new()
        };
        passed.entry(key).or_insert(ids);
    }
    let mut covered = Vec::new();
    let mut gaps = Vec::new();
    let mut selected = BTreeSet::new();
    for consumer in consumers {
        let instances: Vec<&String> = consumer
            .execution_instance_ids
            .iter()
            .filter(|instance| match scope {
                Scope::Repository => true,
                Scope::Instance {
                    participant,
                    instance: wanted,
                } => participant == &consumer.id && wanted == *instance,
            })
            .collect();
        if instances.is_empty() {
            continue;
        }
        let keys: Vec<(String, String)> = instances
            .iter()
            .map(|instance| (consumer.id.clone(), (*instance).clone()))
            .collect();
        selected.extend(keys.iter().filter(|key| passed.contains_key(*key)).cloned());
        for obligation in owned_obligations(pack, consumer) {
            let everywhere = keys.iter().all(|key| {
                passed
                    .get(key)
                    .is_some_and(|ids| ids.contains(&obligation.id))
            });
            if everywhere {
                covered.push((
                    obligation.id.clone(),
                    consumer.id.clone(),
                    obligation.scenario_ids.clone(),
                ));
            } else {
                gaps.push((
                    obligation.id.clone(),
                    "consumer obligation lacks passing evidence from every required execution instance"
                        .to_owned(),
                ));
            }
        }
    }
    let registered: BTreeSet<&str> = consumers
        .iter()
        .flat_map(|consumer| &consumer.obligations)
        .map(|obligation| obligation.id.as_str())
        .collect();
    for declared in &pack.consumer_obligations {
        if !registered.contains(declared.id.as_str()) {
            gaps.push((
                declared.id.clone(),
                "pack consumer obligation has no registration in the consumer catalog".to_owned(),
            ));
        }
    }
    covered.sort();
    gaps.sort();
    let evidence: Vec<&PreparedReport> = reports
        .iter()
        .copied()
        .filter(|report| {
            selected.contains(&(
                report.participant.id.clone(),
                report.participant.execution_instance_id.clone(),
            ))
        })
        .collect();
    ConsumerCoverage {
        family_id: pack.family_id.clone(),
        executions: selected,
        evidence_digest: evidence_digest(&evidence),
        covered,
        gaps,
    }
}

/// One family's aggregated verdict over a scope.
#[derive(Debug, Clone)]
pub(crate) struct FamilyReport {
    /// The family.
    pub family_id: String,
    /// What the report covers.
    pub scope: Scope,
    /// The denominator: `(participant, instance)`, sorted.
    pub required: Vec<(String, String)>,
    /// Executions with evidence, sorted.
    pub received: BTreeSet<(String, String)>,
    /// Family-level failures, sorted.
    pub failures: Vec<ScopedFailure>,
    /// Consumer coverage, when consumers are in scope.
    pub coverage: Option<ConsumerCoverage>,
    /// The validated invocations the report used.
    pub invocations: Vec<PreparedReport>,
}

impl FamilyReport {
    /// Executions in the denominator without evidence.
    pub fn missing(&self) -> Vec<&(String, String)> {
        self.required
            .iter()
            .filter(|key| !self.received.contains(*key))
            .collect()
    }

    /// Whether the report passes: a non-empty denominator, nothing missing,
    /// no failure, and covered consumer obligations.
    pub fn passed(&self) -> bool {
        !self.required.is_empty()
            && self.missing().is_empty()
            && self.failures.is_empty()
            && self.coverage.as_ref().is_none_or(ConsumerCoverage::passed)
    }

    /// The report as a JSON document.
    pub fn document(&self) -> Value {
        let execution = |(participant, instance): &(String, String)| json!({"participantId": participant, "executionInstanceId": instance});
        let (kind, participant, instance) = match &self.scope {
            Scope::Instance {
                participant,
                instance,
            } => ("execution-instance", json!(participant), json!(instance)),
            Scope::Repository => ("full-repository", Value::Null, Value::Null),
        };
        json!({
            "schemaVersion": 1,
            "familyId": self.family_id,
            "scope": {"kind": kind, "participantId": participant, "executionInstanceId": instance},
            "result": if self.passed() { "pass" } else { "fail" },
            "repositoryComplete": self.scope == Scope::Repository && self.passed(),
            "requiredExecutions": self.required.iter().map(execution).collect::<Vec<_>>(),
            "receivedExecutions": self.received.iter().map(execution).collect::<Vec<_>>(),
            "missingExecutions": self.missing().into_iter().map(execution).collect::<Vec<_>>(),
            "failures": self
                .failures
                .iter()
                .map(|failure| json!({
                    "kind": failure.kind.as_str(),
                    "participantId": failure.participant,
                    "executionInstanceId": failure.instance,
                    "message": failure.message,
                }))
                .collect::<Vec<_>>(),
            "consumerCoverage": self.coverage.as_ref().map(ConsumerCoverage::document),
            "invocations": self.invocations.iter().map(PreparedReport::document).collect::<Vec<_>>(),
        })
    }

    /// Renders the report's problems as findings: family-level failures
    /// against `pack_file`, and each invocation's receipt failures against
    /// the location `locations` gives its `(participant, instance)`.
    pub fn findings(
        &self,
        pack_file: &str,
        locations: &BTreeMap<(String, String), String>,
    ) -> Vec<Finding> {
        let family = &self.family_id;
        let mut findings = Vec::new();
        // An invocation's own receipt failures are rendered below in detail,
        // so its one-line family summary would only repeat them.
        for failure in self
            .failures
            .iter()
            .filter(|failure| failure.message != INVOCATION_FAILED)
        {
            let who = match (&failure.participant, &failure.instance) {
                (Some(participant), Some(instance)) => format!(" {participant}/{instance}"),
                _ => String::new(),
            };
            findings.push(Finding::file(
                pack_file,
                failure.kind.as_str(),
                format!("{family}{who}: {}", failure.message),
            ));
        }
        for key in self.missing() {
            findings.push(Finding::file(
                pack_file,
                FailureKind::MissingReceipt.as_str(),
                format!(
                    "{family} {}/{}: required execution produced no validated invocation",
                    key.0, key.1
                ),
            ));
        }
        if let Some(coverage) = &self.coverage {
            for (obligation, message) in &coverage.gaps {
                findings.push(Finding::file(
                    pack_file,
                    FailureKind::CoverageMapping.as_str(),
                    format!("{family} obligation {obligation}: {message}"),
                ));
            }
        }
        for report in &self.invocations {
            let key = (
                report.participant.id.clone(),
                report.participant.execution_instance_id.clone(),
            );
            let path = locations
                .get(&key)
                .cloned()
                .unwrap_or_else(|| pack_file.to_owned());
            for failure in &report.failures {
                let item = failure
                    .item
                    .as_ref()
                    .map(|item| format!(" scenario {item}"))
                    .unwrap_or_default();
                let at = failure
                    .path
                    .as_ref()
                    .map(|path| format!(" at {path}"))
                    .unwrap_or_default();
                findings.push(Finding::file(
                    path.clone(),
                    failure.kind.as_str(),
                    format!(
                        "{family} {}/{}{item}{at}: {}",
                        key.0, key.1, failure.message
                    ),
                ));
            }
        }
        findings
    }
}

/// Aggregates `invocations` for `pack` over `scope`.
///
/// `executions` is the family's full requirement; the scope selects from it.
/// `extra` carries failures found before aggregation (a plan that no longer
/// authenticates, a failed participant command). Consumer coverage is derived
/// when consumers are in scope.
pub(crate) fn family_report(
    pack: &Pack,
    scope: Scope,
    executions: &[Execution],
    consumers: &[&Consumer],
    invocations: Vec<PreparedReport>,
    extra: Vec<ScopedFailure>,
) -> FamilyReport {
    let in_scope: Vec<&Execution> = executions
        .iter()
        .filter(|execution| match &scope {
            Scope::Repository => true,
            Scope::Instance {
                participant,
                instance,
            } => &execution.participant == participant && &execution.instance == instance,
        })
        .collect();
    let by_key: BTreeMap<(String, String), &Execution> = in_scope
        .iter()
        .map(|execution| {
            (
                (execution.participant.clone(), execution.instance.clone()),
                *execution,
            )
        })
        .collect();
    let mut failures = extra;
    if in_scope.is_empty()
        && let Scope::Instance {
            participant,
            instance,
        } = &scope
    {
        failures.push(ScopedFailure::at(
            FailureKind::Applicability,
            participant,
            instance,
            format!(
                "{participant}/{instance} is not applicable to family {}",
                pack.family_id
            ),
        ));
    }
    let mut received = BTreeSet::new();
    let mut selected = Vec::new();
    let mut revisions = BTreeSet::new();
    let mut identities = BTreeSet::new();
    for report in invocations {
        let key = (
            report.participant.id.clone(),
            report.participant.execution_instance_id.clone(),
        );
        let Some(execution) = by_key.get(&key) else {
            continue;
        };
        let (participant, instance) = (&key.0, &key.1);
        if !received.insert(key.clone()) {
            failures.push(ScopedFailure::at(
                FailureKind::MalformedReceipt,
                participant,
                instance,
                "duplicate prepared invocation evidence for one required execution",
            ));
            continue;
        }
        if report.participant.role != execution.role.as_str() {
            failures.push(ScopedFailure::at(
                FailureKind::Applicability,
                participant,
                instance,
                "prepared report role does not match the family's applicability",
            ));
        }
        if report.family_id != pack.family_id {
            failures.push(ScopedFailure::at(
                FailureKind::StaleReceipt,
                participant,
                instance,
                "prepared report family does not match the scoped family",
            ));
        }
        identities.insert((report.family_version, report.expectation_digest.clone()));
        match report.invocation["sourceIdentity"]
            .as_str()
            .filter(|identity| super::receipt::is_source_identity(identity))
            .and_then(|identity| identity.split(':').nth(1))
        {
            Some(revision) => {
                revisions.insert(revision.to_owned());
            }
            None => failures.push(ScopedFailure::at(
                FailureKind::StaleReceipt,
                participant,
                instance,
                "prepared invocation has no valid source identity",
            )),
        }
        if !report.passed() {
            failures.push(ScopedFailure::at(
                FailureKind::SemanticMismatch,
                participant,
                instance,
                INVOCATION_FAILED,
            ));
        }
        let reported: Vec<&String> = if execution.role == Role::Consumer {
            report.obligations.iter().map(|item| &item.id).collect()
        } else {
            report.scenarios.iter().map(|item| &item.id).collect()
        };
        let unique: BTreeSet<&String> = reported.iter().copied().collect();
        let expected: BTreeSet<&String> = execution.evidence.iter().collect();
        if unique.len() != reported.len() || unique != expected {
            let label = if execution.role == Role::Consumer {
                "consumer obligation"
            } else {
                "scenario"
            };
            failures.push(ScopedFailure::at(
                FailureKind::MissingReceipt,
                participant,
                instance,
                format!("prepared invocation does not contain the exact applicable {label} set"),
            ));
        }
        selected.push(report);
    }
    if revisions.len() > 1 {
        failures.push(ScopedFailure::family(
            FailureKind::StaleReceipt,
            "the family's invocations must describe one common git revision",
        ));
    }
    if identities.len() > 1 {
        failures.push(ScopedFailure::family(
            FailureKind::StaleReceipt,
            "the family's invocations must describe one family version and expectation digest",
        ));
    }
    let consumers_in_scope = in_scope
        .iter()
        .any(|execution| execution.role == Role::Consumer);
    let coverage = consumers_in_scope.then(|| {
        let refs: Vec<&PreparedReport> = selected.iter().collect();
        consumer_coverage(pack, consumers, &refs, &scope)
    });
    failures.sort();
    failures.dedup();
    let mut required: Vec<(String, String)> = by_key.keys().cloned().collect();
    required.sort();
    FamilyReport {
        family_id: pack.family_id.clone(),
        scope,
        required,
        received,
        failures,
        coverage,
        invocations: selected,
    }
}

/// The repository verdict over every pack's repository-scope report.
#[derive(Debug, Clone)]
pub(crate) struct Verdict {
    /// Every pack's family, sorted.
    pub required: Vec<String>,
    /// Families with no receipt at all.
    pub missing: Vec<String>,
    /// The family reports for families with receipts, sorted by family.
    pub families: Vec<FamilyReport>,
}

impl Verdict {
    /// Whether the repository is complete: no family missing and every
    /// family report passing at repository scope.
    pub fn complete(&self) -> bool {
        !self.required.is_empty()
            && self.missing.is_empty()
            && self.families.iter().all(FamilyReport::passed)
    }

    /// The verdict as a JSON document.
    pub fn document(&self) -> Value {
        json!({
            "schemaVersion": 1,
            "scope": {"kind": "full-repository"},
            "result": if self.complete() { "pass" } else { "fail" },
            "repositoryComplete": self.complete(),
            "requiredFamilies": self.required,
            "missingFamilies": self.missing,
            "families": self.families.iter().map(FamilyReport::document).collect::<Vec<_>>(),
        })
    }
}

/// `value` as indented JSON with object members sorted and a trailing
/// newline, the form report files are written in.
pub(crate) fn pretty(value: &Value) -> String {
    // Re-parsing the canonical bytes sorts every object regardless of whether
    // `serde_json/preserve_order` is on in this build.
    let sorted: Value =
        serde_json::from_slice(&canonical_bytes(value)).expect("canonical JSON parses");
    let mut text = serde_json::to_string_pretty(&sorted).expect("JSON serializes");
    text.push('\n');
    text
}

#[cfg(test)]
#[path = "report_tests.rs"]
mod tests;
