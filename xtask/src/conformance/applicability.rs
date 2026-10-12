//! Who must run which scenarios: `participants.json` plus the consumer
//! obligation catalog, applied to the packs.
//!
//! - **Rust** runs every scenario of every pack (instance `rust`).
//! - **CXX** runs a family only when `participants.json` enrols it, and then
//!   exactly the scenarios whose `action` is an enrolled capability (extra
//!   `capabilityIds` do not exclude a scenario). It runs on both compilers:
//!   `windows-clang-cl` and `windows-msvc`.
//! - **Consumers** (`cli`, `gui`, `tui`) run the obligations a pack declares,
//!   on the execution instances `consumer-obligations.json` registers.
//!
//! Packs never choose their participants. Both catalogs are validated here,
//! including against the packs: an enrolment or registration for a family
//! without a pack, an unknown capability or scenario, an enrolment that
//! selects nothing, and an obligation a pack declares but nobody registers
//! (or the reverse) are all findings.

use std::collections::{BTreeMap, BTreeSet};

use anyhow::Result;

use super::json::Document;
use super::pack::{LoadedPack, Packs};
use super::schema::{ConsumerObligations, Participants, is_canonical_relative_path, is_stable_id};
use super::{Issue, load_document};
use crate::{Finding, RepoRoot};

/// Repo-relative path of the semantic participant catalog.
pub(crate) const PARTICIPANTS: &str = "tests/conformance/participants.json";
/// Repo-relative path of the consumer obligation catalog.
pub(crate) const CONSUMER_OBLIGATIONS: &str = "tests/conformance/consumer-obligations.json";

/// The CXX participant's execution instances: one per compiler.
const CXX_INSTANCES: [&str; 2] = ["windows-clang-cl", "windows-msvc"];
/// The consumers the obligation catalog may register.
const CONSUMERS: [&str; 3] = ["cli", "gui", "tui"];

/// One required execution: a participant instance must produce a receipt for
/// a family.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ExecutionKey {
    /// The pack's family.
    pub family_id: String,
    /// `rust`, `cxx`, `cli`, `gui` or `tui`.
    pub participant_id: String,
    /// The execution instance, e.g. `rust`, `tui` or `windows-msvc`.
    pub instance_id: String,
}

impl ExecutionKey {
    /// Builds a key from its three parts.
    pub fn new(family_id: &str, participant_id: &str, instance_id: &str) -> Self {
        Self {
            family_id: family_id.to_owned(),
            participant_id: participant_id.to_owned(),
            instance_id: instance_id.to_owned(),
        }
    }
}

/// The derived requirement plus counts for the `check` summary.
#[derive(Debug, Default)]
pub(crate) struct Applicability {
    /// Every required (family, participant, instance).
    pub required: BTreeSet<ExecutionKey>,
    /// Families CXX is enrolled in.
    pub cxx_families: usize,
    /// Scenarios CXX runs, across families.
    pub cxx_scenarios: usize,
    /// Registered consumer obligations.
    pub consumer_obligations: usize,
}

/// Loads both catalogs, validates them against `packs`, appends findings and
/// derives the required executions.
///
/// A catalog that cannot be loaded contributes nothing to the requirement;
/// its finding already fails the check.
///
/// # Errors
///
/// Fails when a catalog exists but cannot be read.
pub(crate) fn derive(
    root: &RepoRoot,
    packs: &Packs,
    findings: &mut Vec<Finding>,
) -> Result<Applicability> {
    let mut applicability = Applicability::default();
    let by_family: BTreeMap<&str, &LoadedPack> = packs
        .loaded
        .iter()
        .map(|loaded| (loaded.pack.family_id.as_str(), loaded))
        .collect();
    for loaded in &packs.loaded {
        applicability
            .required
            .insert(ExecutionKey::new(&loaded.pack.family_id, "rust", "rust"));
    }

    match load_document::<Participants>(root, PARTICIPANTS, "participants")? {
        Err(finding) => findings.push(finding),
        Ok(catalog) => {
            let issues = participants(&catalog.value, &by_family, packs, &mut applicability);
            locate(findings, &catalog.file, &catalog.document, issues);
        }
    }

    let mut registered: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    match load_document::<ConsumerObligations>(root, CONSUMER_OBLIGATIONS, "consumer-obligations")?
    {
        Err(finding) => findings.push(finding),
        Ok(catalog) => {
            let issues = consumers(
                root,
                &catalog.value,
                &by_family,
                packs,
                &mut applicability,
                &mut registered,
            );
            locate(findings, &catalog.file, &catalog.document, issues);
        }
    }
    // A pack obligation nobody registers would never run.
    for loaded in &packs.loaded {
        let owned = registered.get(loaded.pack.family_id.as_str());
        for (index, obligation) in loaded.pack.consumer_obligations.iter().enumerate() {
            if !owned.is_some_and(|ids| ids.contains(&obligation.id)) {
                findings.push(
                    Issue::new(
                        format!("/consumerObligations/{index}"),
                        "consumer-obligations",
                        format!(
                            "consumer obligation {} has no registration in {CONSUMER_OBLIGATIONS}",
                            obligation.id
                        ),
                    )
                    .locate(&loaded.file, &loaded.document),
                );
            }
        }
    }
    Ok(applicability)
}

fn locate(findings: &mut Vec<Finding>, file: &str, document: &Document, issues: Vec<Issue>) {
    findings.extend(issues.into_iter().map(|issue| issue.locate(file, document)));
}

/// Validates `participants.json` and adds the CXX requirement.
fn participants(
    catalog: &Participants,
    packs: &BTreeMap<&str, &LoadedPack>,
    all_packs: &Packs,
    applicability: &mut Applicability,
) -> Vec<Issue> {
    const RULE: &str = "participants";
    let mut issues = Vec::new();
    if catalog.schema_version != 1 {
        issues.push(Issue::new(
            "/schemaVersion",
            RULE,
            "schemaVersion must be 1",
        ));
    }
    let ids: Vec<&str> = catalog
        .families
        .iter()
        .map(|family| family.family_id.as_str())
        .collect();
    let canonical: Vec<&str> = ids
        .iter()
        .copied()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    if ids != canonical {
        issues.push(Issue::new(
            "/families",
            RULE,
            "families must be sorted and unique by familyId",
        ));
    }
    for (index, family) in catalog.families.iter().enumerate() {
        let at = format!("/families/{index}");
        let id = &family.family_id;
        if !is_stable_id(id) {
            issues.push(Issue::new(
                format!("{at}/familyId"),
                RULE,
                format!("{id:?} is not a stable family identity"),
            ));
        }
        let Some(enrolment) = &family.cxx else {
            issues.push(Issue::new(
                at,
                RULE,
                format!("{id} must enrol at least one participant; omit Rust-only families"),
            ));
            continue;
        };
        let capabilities = &enrolment.capability_ids;
        let at = format!("{at}/cxx/capabilityIds");
        let sorted_unique = capabilities.windows(2).all(|pair| pair[0] < pair[1]);
        if capabilities.is_empty()
            || !sorted_unique
            || !capabilities.iter().all(|c| is_stable_id(c))
        {
            issues.push(Issue::new(
                at.clone(),
                RULE,
                format!("{id} cxx capabilityIds must be a non-empty, sorted, unique list of capability IDs"),
            ));
        }
        let Some(loaded) = packs.get(id.as_str()) else {
            if all_packs.excuses(id) {
                continue;
            }
            issues.push(Issue::new(
                format!("/families/{index}/familyId"),
                RULE,
                format!("participants.json enrols untracked family {id} (no pack declares it)"),
            ));
            continue;
        };
        let declared: BTreeSet<&str> = loaded
            .pack
            .capabilities
            .iter()
            .map(|c| c.id.as_str())
            .collect();
        for capability in capabilities {
            if !declared.contains(capability.as_str()) {
                issues.push(Issue::new(
                    at.clone(),
                    RULE,
                    format!("{id} enrols cxx in unknown capability {capability}"),
                ));
            }
        }
        // The action rule: a scenario applies to CXX when its action is
        // enrolled; other capabilities it names do not exclude it.
        let selected = loaded
            .pack
            .scenarios
            .iter()
            .filter(|scenario| capabilities.contains(&scenario.action))
            .count();
        if selected == 0 {
            issues.push(Issue::new(
                at,
                RULE,
                format!("the cxx enrolment of {id} selects no scenario"),
            ));
            continue;
        }
        applicability.cxx_families += 1;
        applicability.cxx_scenarios += selected;
        for instance in CXX_INSTANCES {
            applicability
                .required
                .insert(ExecutionKey::new(id, "cxx", instance));
        }
    }
    issues
}

/// Validates `consumer-obligations.json`, records each family's registered
/// obligation IDs, and adds the consumer requirement.
fn consumers(
    root: &RepoRoot,
    catalog: &ConsumerObligations,
    packs: &BTreeMap<&str, &LoadedPack>,
    all_packs: &Packs,
    applicability: &mut Applicability,
    registered: &mut BTreeMap<String, BTreeSet<String>>,
) -> Vec<Issue> {
    const RULE: &str = "consumer-obligations";
    let mut issues = Vec::new();
    if catalog.schema_version != 1 {
        issues.push(Issue::new(
            "/schemaVersion",
            RULE,
            "schemaVersion must be 1",
        ));
    }
    let mut family_ids = BTreeSet::new();
    for (family_index, family) in catalog.families.iter().enumerate() {
        let at = format!("/families/{family_index}");
        let id = family.family_id.as_str();
        if !is_stable_id(id) || !family_ids.insert(id) {
            issues.push(Issue::new(
                format!("{at}/familyId"),
                RULE,
                format!("{id:?} must be a unique, stable family identity"),
            ));
        }
        if family.consumers.is_empty() {
            issues.push(Issue::new(
                format!("{at}/consumers"),
                RULE,
                format!("{id} registers no consumer"),
            ));
        }
        let loaded = packs.get(id);
        if loaded.is_none() && !all_packs.excuses(id) {
            issues.push(Issue::new(
                format!("{at}/familyId"),
                RULE,
                format!("consumer obligations name untracked family {id} (no pack declares it)"),
            ));
        }
        let declared: BTreeSet<&str> = loaded
            .map(|loaded| {
                loaded
                    .pack
                    .consumer_obligations
                    .iter()
                    .map(|o| o.id.as_str())
                    .collect()
            })
            .unwrap_or_default();
        let scenarios: BTreeSet<&str> = loaded
            .map(|loaded| {
                loaded
                    .pack
                    .scenarios
                    .iter()
                    .map(|s| s.id.as_str())
                    .collect()
            })
            .unwrap_or_default();
        let mut consumer_ids = BTreeSet::new();
        let owned = registered.entry(id.to_owned()).or_default();
        for (consumer_index, consumer) in family.consumers.iter().enumerate() {
            let at = format!("{at}/consumers/{consumer_index}");
            if !CONSUMERS.contains(&consumer.id.as_str())
                || !consumer_ids.insert(consumer.id.as_str())
            {
                issues.push(Issue::new(
                    format!("{at}/id"),
                    RULE,
                    format!(
                        "consumer {:?} must be one of {CONSUMERS:?}, once per family",
                        consumer.id
                    ),
                ));
            }
            let instances = &consumer.execution_instance_ids;
            let unique_instances =
                instances.iter().collect::<BTreeSet<_>>().len() == instances.len();
            if instances.is_empty()
                || !unique_instances
                || !instances.iter().all(|i| is_stable_id(i))
            {
                issues.push(Issue::new(
                    format!("{at}/executionInstanceIds"),
                    RULE,
                    "executionInstanceIds must be a non-empty list of unique, stable instance IDs",
                ));
            }
            let paths = &consumer.source_paths;
            if paths.is_empty() || paths.iter().collect::<BTreeSet<_>>().len() != paths.len() {
                issues.push(Issue::new(
                    format!("{at}/sourcePaths"),
                    RULE,
                    "sourcePaths must be a non-empty list of unique paths",
                ));
            }
            for (path_index, path) in paths.iter().enumerate() {
                let exists = is_canonical_relative_path(path) && root.join(path).exists();
                if !exists {
                    issues.push(Issue::new(
                        format!("{at}/sourcePaths/{path_index}"),
                        RULE,
                        format!("source path {path:?} must name an existing repository path in canonical relative form"),
                    ));
                }
            }
            if consumer.obligations.is_empty() {
                issues.push(Issue::new(
                    format!("{at}/obligations"),
                    RULE,
                    "a consumer owns at least one obligation",
                ));
            }
            let mut selected = false;
            for (obligation_index, obligation) in consumer.obligations.iter().enumerate() {
                let at = format!("{at}/obligations/{obligation_index}");
                applicability.consumer_obligations += 1;
                if !is_stable_id(&obligation.id) || !owned.insert(obligation.id.clone()) {
                    issues.push(Issue::new(
                        format!("{at}/id"),
                        RULE,
                        format!("obligation {:?} must be a stable ID with exactly one consumer owner in {id}", obligation.id),
                    ));
                }
                if loaded.is_some() && !declared.contains(obligation.id.as_str()) {
                    issues.push(Issue::new(
                        format!("{at}/id"),
                        RULE,
                        format!(
                            "obligation {} is not declared by the {id} pack",
                            obligation.id
                        ),
                    ));
                } else {
                    selected = true;
                }
                let ids = &obligation.scenario_ids;
                let unique = ids.iter().collect::<BTreeSet<_>>().len() == ids.len();
                if ids.is_empty() || !unique || !ids.iter().all(|s| is_stable_id(s)) {
                    issues.push(Issue::new(
                        format!("{at}/scenarioIds"),
                        RULE,
                        "scenarioIds must be a non-empty list of unique scenario IDs",
                    ));
                }
                for scenario in ids {
                    if loaded.is_some() && !scenarios.contains(scenario.as_str()) {
                        issues.push(Issue::new(
                            format!("{at}/scenarioIds"),
                            RULE,
                            format!(
                                "obligation {} references unknown {id} scenario {scenario}",
                                obligation.id
                            ),
                        ));
                    }
                }
            }
            if selected && loaded.is_some() {
                for instance in instances {
                    applicability
                        .required
                        .insert(ExecutionKey::new(id, &consumer.id, instance));
                }
            }
        }
    }
    issues
}
