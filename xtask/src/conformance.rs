//! `cargo xtask conformance`: the Rust conformance engine.
//!
//! `check` validates the conformance inputs statically, without running any
//! participant:
//!
//! - every scenario pack under `tests/conformance/packs/` (closed shape,
//!   identities, fixtures, normalization, the engine-wide input rule, the
//!   family input hooks and the family expectation compilers);
//! - `tests/conformance/participants.json` (which families CXX runs);
//! - `tests/conformance/consumer-obligations.json` (the CLI, GUI and TUI
//!   consumers);
//! - the workflow policy: every applicable (family, participant, execution
//!   instance) has a blocking CI step, and the aggregation and Corrosion
//!   wiring the verdict depends on is intact.
//!
//! `run --participant <p>` runs every family that requires the participant,
//! one invocation per family: it writes an input-only run plan, launches the
//! participant's runner through the command table, validates the receipt
//! centrally, and writes an instance-scoped family report beside it. It keeps
//! going past failures and names every failed family at the end.
//!
//! `verdict` reads the run plans and receipts under a directory, authenticates
//! each plan against the current tree, validates each receipt, and decides
//! repository completeness: every pack's family must pass with every required
//! (participant, execution instance).
//!
//! Module layout (decision #301): [`json`] (strict parse, canonical bytes,
//! framed digest), [`schema`] (closed document shapes), `pack` (loading and the
//! generic input rule), `applicability` (who must run what), `plan` (run plans
//! and source identity), `launch` (the command table and process runner),
//! `receipt` (central receipt validation), `compare` (declared normalization
//! and exact comparison), `report` (family reports and the verdict),
//! `families` (the per-family seam, a `match` on the family ID),
//! `update_service` (the controlled update service fake) and
//! [`workflow_policy`].

use std::collections::{BTreeMap, BTreeSet};
use std::io::ErrorKind;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use serde::de::DeserializeOwned;
use serde_json::Value;

use crate::{Finding, Outcome, RepoRoot};

mod applicability;
mod compare;
mod families;
pub mod json;
mod launch;
mod pack;
mod plan;
mod receipt;
mod report;
pub mod schema;
mod update_service;
pub mod workflow_policy;

pub use applicability::ExecutionKey;
pub use launch::{Attempt, CommandTable, Launch, ParticipantCommand, spawn};

use applicability::{Applicability, Execution, owned_obligations};
use json::Document;
use pack::LoadedPack;
use plan::{Payload, PlanRequest, PreparedPack, Role};
use receipt::{ConsumerExpectations, FailureKind, PreparedReport};
use report::{Scope, ScopedFailure};
use schema::{PlanParticipant, RunPlan};

/// Default artifact root of `conformance run`, relative to the repository.
pub const DEFAULT_ARTIFACT_ROOT: &str = "target/conformance";

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
    /// Expectations that reference an independent oracle are compiled
    /// against it, so a disagreement with the oracle fails the check.
    Check(CheckArgs),
    /// Run every family that requires one participant, validate each receipt
    /// and report each family.
    ///
    /// Each family gets a fresh directory
    /// `<artifact-root>/<participant>/<instance>/<invocation id>/` holding
    /// `run_plan.json` (input only), the participant's `receipt.json`,
    /// `attempt.json` (command, exit code, output) and
    /// `conformance_report.json`. rust and tui run their `cargo test`
    /// runners; cxx, cli and gui run the build wrappers with
    /// `-Test -TestOnly`, so an earlier wrapper build must exist. Every family
    /// runs even after a failure; the failed families are named at the end.
    /// update-services and yaml-update-operations run against the in-process
    /// controlled update service.
    Run(RunArgs),
    /// Decide repository completeness from downloaded run artifacts.
    ///
    /// Reads every `run_plan.json` under --receipts, authenticates it against
    /// the current tree (pack, catalogs, digest and source identity),
    /// validates the `receipt.json` beside it, and requires every pack's family
    /// to pass with every applicable (participant, execution instance).
    Verdict(VerdictArgs),
}

/// Arguments for `conformance check` (none today).
#[derive(Debug, Default, Clone, clap::Args)]
pub struct CheckArgs {}

/// A conformance participant.
#[derive(Debug, Clone, Copy, PartialEq, Eq, clap::ValueEnum)]
pub enum Participant {
    /// The Rust semantic adapter (every family).
    Rust,
    /// The native C++ semantic adapter (families participants.json enrols).
    Cxx,
    /// The CLI consumer.
    Cli,
    /// The GUI consumer.
    Gui,
    /// The TUI consumer.
    Tui,
}

impl Participant {
    /// The protocol spelling.
    pub fn id(self) -> &'static str {
        match self {
            Participant::Rust => "rust",
            Participant::Cxx => "cxx",
            Participant::Cli => "cli",
            Participant::Gui => "gui",
            Participant::Tui => "tui",
        }
    }
}

/// The native compiler a CXX, CLI or GUI run uses.
#[derive(Debug, Clone, Copy, PartialEq, Eq, clap::ValueEnum)]
pub enum Compiler {
    /// MSVC (`windows-msvc`).
    Msvc,
    /// clang-cl (`windows-clang-cl`).
    ClangCl,
}

impl Compiler {
    /// The wrapper's `-Compiler` spelling.
    pub fn name(self) -> &'static str {
        match self {
            Compiler::Msvc => "msvc",
            Compiler::ClangCl => "clang-cl",
        }
    }
}

/// Arguments for `conformance run`.
#[derive(Debug, Clone, clap::Args)]
pub struct RunArgs {
    /// The participant to run.
    #[arg(long, value_enum)]
    pub participant: Participant,
    /// The compiler of a cxx, cli or gui run (instance `windows-<compiler>`).
    #[arg(
        long,
        value_enum,
        required_if_eq_any = [("participant", "cxx"), ("participant", "cli"), ("participant", "gui")]
    )]
    pub compiler: Option<Compiler>,
    /// The GUI build wrapper's -Preset (CI uses ci-system-qt).
    #[arg(long, default_value = "default")]
    pub preset: String,
    /// Run only this family (repeatable); it must require the participant.
    #[arg(long = "family", value_name = "FAMILY")]
    pub families: Vec<String>,
    /// Where invocation directories are created (relative paths are taken
    /// from the repository root).
    #[arg(long, value_name = "DIR", default_value = DEFAULT_ARTIFACT_ROOT)]
    pub artifact_root: PathBuf,
}

/// Arguments for `conformance verdict`.
#[derive(Debug, Clone, clap::Args)]
pub struct VerdictArgs {
    /// Directory holding run artifacts (searched recursively for
    /// `run_plan.json`; relative paths are taken from the repository root).
    #[arg(long, value_name = "DIR")]
    pub receipts: PathBuf,
    /// Also write the verdict document here as JSON.
    #[arg(long, value_name = "FILE")]
    pub output: Option<PathBuf>,
}

/// Runs one conformance operation over the repository at `root`.
///
/// # Errors
///
/// Fails on an operational problem (an unreadable directory or file); every
/// problem with the conformance inputs or the participants is a finding
/// instead.
pub fn run(root: &RepoRoot, args: Args) -> Result<Outcome> {
    run_with_progress(root, args, &mut |_| {})
}

/// [`run`], reporting each family `conformance run` starts and finishes to
/// `progress` (the binary prints these lines to stderr).
///
/// # Errors
///
/// As for [`run`].
pub fn run_with_progress(
    root: &RepoRoot,
    args: Args,
    progress: &mut dyn FnMut(&str),
) -> Result<Outcome> {
    match args.command {
        Command::Check(_) => check(root),
        Command::Run(args) => {
            let compiler = args.compiler.map_or("msvc", Compiler::name);
            let table = CommandTable::repository(compiler, &args.preset);
            run_participant(root, &args, &table, &mut spawn, progress)
        }
        Command::Verdict(args) => verdict(root, &args),
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

/// Loads every pack and both catalogs; any finding makes running or judging
/// impossible, so it is returned as the failing outcome instead.
fn load_inputs(
    root: &RepoRoot,
) -> Result<std::result::Result<(pack::Packs, Applicability), Outcome>> {
    let mut findings = Vec::new();
    let packs = pack::load_all(root, &mut findings)?;
    let applicability = applicability::derive(root, &packs, &mut findings)?;
    if findings.is_empty() {
        return Ok(Ok((packs, applicability)));
    }
    let count = findings.len();
    Ok(Err(Outcome::from_findings(
        findings,
        String::new(),
        format!(
            "the conformance inputs have {count} findings; fix them first (`cargo xtask conformance check`)"
        ),
    )))
}

/// Resolves a command-line directory: relative paths are taken from `root`.
fn from_root(root: &RepoRoot, path: &Path) -> PathBuf {
    if path.is_absolute() {
        path.to_path_buf()
    } else {
        root.path().join(path)
    }
}

/// The repo-relative source paths of a consumer run: the obligation catalog
/// itself plus the consumer's registered sources.
fn consumer_source_paths(consumer: &schema::Consumer) -> Vec<String> {
    let mut paths = vec![applicability::CONSUMER_OBLIGATIONS.to_owned()];
    paths.extend(consumer.source_paths.iter().cloned());
    paths
}

/// A plan's payload, plus for a consumer its catalog-owned source paths and
/// obligation expectations.
type PlanInputs = (Payload, Option<Vec<String>>, Option<ConsumerExpectations>);

/// What a plan for `execution` hands its participant, and for a consumer
/// its catalog-owned source paths and obligation expectations.
fn payload_for(
    loaded: &LoadedPack,
    execution: &Execution,
    applicability: &Applicability,
) -> std::result::Result<PlanInputs, String> {
    match execution.role {
        Role::SemanticAdapter => Ok((Payload::Scenarios(execution.evidence.clone()), None, None)),
        Role::Consumer => {
            let consumer = applicability
                .consumer(&loaded.pack.family_id, &execution.participant)
                .ok_or_else(|| format!("{} is not a registered consumer", execution.participant))?;
            let owned = owned_obligations(&loaded.pack, consumer);
            let payload = Payload::Obligations(
                owned
                    .iter()
                    .map(|obligation| (obligation.id.clone(), obligation.scenario_ids.clone()))
                    .collect(),
            );
            let expectations = owned
                .iter()
                .map(|obligation| (obligation.id.clone(), obligation.expected.clone()))
                .collect();
            Ok((
                payload,
                Some(consumer_source_paths(consumer)),
                Some(expectations),
            ))
        }
    }
}

/// `conformance run`, with the command table and the runner injected.
///
/// `runner` executes one [`Launch`]; the real one is [`spawn`]. Every family
/// that requires the participant's instance runs, failures do not stop the
/// run, and the outcome names every failed family.
///
/// # Errors
///
/// Fails on a usage problem (a missing `--compiler`, an unknown or
/// inapplicable `--family`, a participant nothing requires) or when the
/// inputs cannot be read.
pub fn run_participant(
    root: &RepoRoot,
    args: &RunArgs,
    table: &CommandTable,
    runner: &mut dyn FnMut(&Launch) -> Attempt,
    progress: &mut dyn FnMut(&str),
) -> Result<Outcome> {
    let participant = args.participant.id();
    let instance = match (args.participant, args.compiler) {
        (Participant::Rust | Participant::Tui, None) => participant.to_owned(),
        (Participant::Rust | Participant::Tui, Some(_)) => {
            bail!("--compiler applies only to cxx, cli and gui")
        }
        (_, Some(compiler)) => format!("windows-{}", compiler.name()),
        (_, None) => bail!("--compiler is required for {participant}"),
    };
    let (packs, applicability) = match load_inputs(root)? {
        Ok(inputs) => inputs,
        Err(outcome) => return Ok(outcome),
    };
    let mut work: Vec<(&LoadedPack, Execution)> = Vec::new();
    for loaded in &packs.loaded {
        for execution in applicability.executions(&loaded.pack) {
            if execution.participant == participant && execution.instance == instance {
                work.push((loaded, execution));
            }
        }
    }
    for family in &args.families {
        if !work
            .iter()
            .any(|(loaded, _)| &loaded.pack.family_id == family)
        {
            bail!("family {family} does not require {participant}/{instance}");
        }
    }
    if !args.families.is_empty() {
        work.retain(|(loaded, _)| args.families.contains(&loaded.pack.family_id));
    }
    if work.is_empty() {
        bail!("no family requires {participant}/{instance}");
    }
    let artifact_root = from_root(root, &args.artifact_root);
    let total = work.len();
    let mut findings = Vec::new();
    let mut failed = Vec::new();
    for (index, (loaded, execution)) in work.iter().enumerate() {
        let family = &loaded.pack.family_id;
        progress(&format!(
            "[{}/{total}] {family}: running {participant}/{instance}",
            index + 1
        ));
        let (passed, family_findings, location) = match run_family(
            root,
            loaded,
            execution,
            &applicability,
            table,
            runner,
            &artifact_root,
        ) {
            Ok(run) => (run.passed, run.findings, run.location),
            Err(error) => (
                false,
                vec![Finding {
                    path: loaded.file.clone(),
                    line: 1,
                    rule: "conformance-run",
                    message: format!("{family} {participant}/{instance}: {error:#}"),
                }],
                None,
            ),
        };
        let verdict = if passed { "pass" } else { "FAIL" };
        let location = location
            .map(|location| format!(" ({location})"))
            .unwrap_or_default();
        progress(&format!(
            "[{}/{total}] {family}: {verdict}{location}",
            index + 1
        ));
        if !passed {
            failed.push(family.clone());
            findings.extend(family_findings);
        }
    }
    let summary = format!("conformance run {participant}/{instance}: {total} families passed");
    let failure = format!(
        "conformance run {participant}/{instance} failed: {} of {total} families failed: {}",
        failed.len(),
        failed.join(", ")
    );
    if failed.is_empty() {
        return Ok(Outcome::Pass { summary });
    }
    // A failed family always carries at least one finding; keep the outcome a
    // failure even if a report somehow rendered none.
    if findings.is_empty() {
        findings.push(Finding {
            path: String::from("."),
            line: 1,
            rule: "conformance-run",
            message: failure.clone(),
        });
    }
    Ok(Outcome::from_findings(findings, summary, failure))
}

/// One family's `run` result.
struct FamilyRun {
    passed: bool,
    findings: Vec<Finding>,
    /// The report's location, for progress lines.
    location: Option<String>,
}

/// Plans, launches, validates and reports one family for one execution.
fn run_family(
    root: &RepoRoot,
    loaded: &LoadedPack,
    execution: &Execution,
    applicability: &Applicability,
    table: &CommandTable,
    runner: &mut dyn FnMut(&Launch) -> Attempt,
    artifact_root: &Path,
) -> Result<FamilyRun> {
    let family = loaded.pack.family_id.as_str();
    let (participant, instance) = (execution.participant.as_str(), execution.instance.as_str());
    let prepared = plan::prepare(root, loaded)?;
    let command = table
        .command(participant, family)
        .with_context(|| format!("no {participant} command is registered for {family}"))?;
    let (payload, consumer_paths, expectations) =
        payload_for(loaded, execution, applicability).map_err(anyhow::Error::msg)?;
    let request = PlanRequest {
        participant: participant.to_owned(),
        role: execution.role,
        instance: instance.to_owned(),
        source_paths: consumer_paths.unwrap_or_else(|| command.source_paths.clone()),
        payload,
    };
    let plan_document = plan::build(root, &prepared, &request)?;
    let materialized = plan::write(artifact_root, &plan_document)?;

    let (plan_env, output_env) = match execution.role {
        Role::SemanticAdapter => launch::SEMANTIC_ENV,
        Role::Consumer => launch::CONSUMER_ENV,
    };
    let mut env = BTreeMap::new();
    env.insert(plan_env.to_owned(), plan::native(&materialized.run_plan));
    env.insert(output_env.to_owned(), plan::native(&materialized.receipt));
    let service =
        if execution.role == Role::SemanticAdapter && update_service::FAMILIES.contains(&family) {
            let service = update_service::ControlledUpdateService::start(
                update_service::scripts_from_plan(&plan_document)?,
            )?;
            env.insert(
                update_service::SERVICE_ENV.to_owned(),
                service.url().to_owned(),
            );
            // Ambient proxy settings must not divert loopback requests.
            env.insert("NO_PROXY".to_owned(), "127.0.0.1,localhost".to_owned());
            Some(service)
        } else {
            None
        };
    let launch = Launch {
        family_id: family.to_owned(),
        participant: participant.to_owned(),
        instance: instance.to_owned(),
        command,
        working_dir: root.path().to_path_buf(),
        env,
        run_plan: materialized.run_plan.clone(),
        receipt: materialized.receipt.clone(),
    };
    let attempt = runner(&launch);
    let service_result = service.map(update_service::ControlledUpdateService::finish);

    let mut attempt_document = attempt.document(&launch);
    if let Some(result) = &service_result {
        attempt_document["controlledUpdateService"] = match result {
            Ok(()) => Value::String("complete".into()),
            Err(problems) => Value::String(problems.clone()),
        };
    }
    write_text(
        &materialized.dir.join("attempt.json"),
        &report::pretty(&attempt_document),
    )?;

    let mut extra = attempt.failures(&launch);
    if let Some(Err(problems)) = &service_result {
        extra.push(ScopedFailure::at(
            FailureKind::AdapterCommand,
            participant,
            instance,
            format!("the controlled update service was not used as scripted: {problems}"),
        ));
    }
    let plan_value: RunPlan =
        serde_json::from_value(plan_document.clone()).context("re-reading the run plan")?;
    let current =
        pack::load_one(root, &loaded.file).and_then(|current| plan::prepare(root, &current));
    let stale = receipt::check_current(
        &prepared,
        current,
        &materialized.run_plan,
        &materialized.bytes,
    );
    let invocation = if stale.is_empty() {
        let bytes = std::fs::read(&materialized.receipt).ok();
        receipt::validate(
            &prepared,
            &plan_value,
            bytes.as_deref(),
            expectations.as_ref(),
        )
    } else {
        PreparedReport::failed(&plan_value, stale)
    };
    let family_report = report::family_report(
        &loaded.pack,
        Scope::Instance {
            participant: participant.to_owned(),
            instance: instance.to_owned(),
        },
        &applicability.executions(&loaded.pack),
        &applicability.consumers_of(family),
        vec![invocation],
        extra,
    );
    let report_path = materialized.dir.join("conformance_report.json");
    write_text(&report_path, &report::pretty(&family_report.document()))?;
    let location = launch::display(root.path(), &report_path);
    let mut locations = BTreeMap::new();
    locations.insert(
        (participant.to_owned(), instance.to_owned()),
        location.clone(),
    );
    Ok(FamilyRun {
        passed: family_report.passed(),
        findings: family_report.findings(&loaded.file, &locations),
        location: Some(location),
    })
}

/// Writes `text` to `path`.
fn write_text(path: &Path, text: &str) -> Result<()> {
    std::fs::write(path, text).with_context(|| format!("writing {}", path.display()))
}

/// Every `run_plan.json` beneath `directory`, sorted.
fn discover_plans(directory: &Path) -> Result<Vec<PathBuf>> {
    if !directory.is_dir() {
        bail!("receipt directory {} does not exist", directory.display());
    }
    let mut plans = Vec::new();
    for entry in walkdir::WalkDir::new(directory).sort_by_file_name() {
        let entry = entry.with_context(|| format!("walking {}", directory.display()))?;
        if entry.file_type().is_file() && entry.file_name() == "run_plan.json" {
            plans.push(entry.into_path());
        }
    }
    if plans.is_empty() {
        bail!(
            "receipt directory {} contains no run plans",
            directory.display()
        );
    }
    Ok(plans)
}

/// The participant a plan names, read without trusting anything else in it.
fn plan_participant(path: &Path) -> std::result::Result<(String, PlanParticipant), String> {
    let text = std::fs::read_to_string(path)
        .map_err(|error| format!("cannot read the run plan: {error}"))?;
    let document = json::parse_strict(&text)
        .map_err(|error| format!("the run plan is not strict JSON: {error}"))?;
    let value = document.value();
    let family = value["familyId"]
        .as_str()
        .ok_or("the run plan names no familyId")?
        .to_owned();
    let participant: PlanParticipant = serde_json::from_value(value["participant"].clone())
        .map_err(|error| format!("the run plan's participant is malformed: {error}"))?;
    Ok((family, participant))
}

/// `conformance verdict`: repository completeness from run artifacts.
fn verdict(root: &RepoRoot, args: &VerdictArgs) -> Result<Outcome> {
    let (packs, applicability) = match load_inputs(root)? {
        Ok(inputs) => inputs,
        Err(outcome) => return Ok(outcome),
    };
    let by_family: BTreeMap<&str, &LoadedPack> = packs
        .loaded
        .iter()
        .map(|loaded| (loaded.pack.family_id.as_str(), loaded))
        .collect();
    let mut findings = Vec::new();
    let mut grouped: BTreeMap<String, Vec<(PathBuf, PlanParticipant)>> = BTreeMap::new();
    for path in discover_plans(&from_root(root, &args.receipts))? {
        let location = launch::display(root.path(), &path);
        match plan_participant(&path) {
            Ok((family, participant)) if by_family.contains_key(family.as_str()) => {
                grouped.entry(family).or_default().push((path, participant));
            }
            Ok((family, _)) => findings.push(Finding {
                path: location,
                line: 1,
                rule: FailureKind::StaleReceipt.as_str(),
                message: format!("the run plan names untracked family {family}"),
            }),
            Err(message) => findings.push(Finding {
                path: location,
                line: 1,
                rule: FailureKind::MalformedReceipt.as_str(),
                message,
            }),
        }
    }

    let mut families = Vec::new();
    for (family, plans) in &grouped {
        let loaded = by_family[family.as_str()];
        let prepared = plan::prepare(root, loaded)?;
        let executions = applicability.executions(&loaded.pack);
        let mut invocations = Vec::new();
        let mut extra = Vec::new();
        let mut locations = BTreeMap::new();
        for (path, participant) in plans {
            let key = (
                participant.id.clone(),
                participant.execution_instance_id.clone(),
            );
            let receipt_path = path.with_file_name("receipt.json");
            locations.insert(key.clone(), launch::display(root.path(), &receipt_path));
            match judge_plan(
                root,
                &prepared,
                loaded,
                &executions,
                &applicability,
                path,
                &receipt_path,
            ) {
                Ok(invocation) => invocations.push(invocation),
                Err(message) => extra.push(ScopedFailure::at(
                    FailureKind::StaleReceipt,
                    &key.0,
                    &key.1,
                    format!("{}: {message}", launch::display(root.path(), path)),
                )),
            }
        }
        let family_report = report::family_report(
            &loaded.pack,
            Scope::Repository,
            &executions,
            &applicability.consumers_of(family),
            invocations,
            extra,
        );
        findings.extend(family_report.findings(&loaded.file, &locations));
        families.push(family_report);
    }
    let required: Vec<String> = by_family
        .keys()
        .map(|family| (*family).to_owned())
        .collect();
    let missing: Vec<String> = required
        .iter()
        .filter(|family| !grouped.contains_key(*family))
        .cloned()
        .collect();
    for family in &missing {
        findings.push(Finding {
            path: by_family[family.as_str()].file.clone(),
            line: 1,
            rule: FailureKind::MissingReceipt.as_str(),
            message: format!("{family}: no run artifacts for this family"),
        });
    }
    let verdict = report::Verdict {
        required,
        missing,
        families,
    };
    if let Some(output) = &args.output {
        let output = from_root(root, output);
        if let Some(parent) = output.parent() {
            std::fs::create_dir_all(parent)
                .with_context(|| format!("creating {}", parent.display()))?;
        }
        write_text(&output, &report::pretty(&verdict.document()))?;
    }
    let executions: usize = verdict
        .families
        .iter()
        .map(|family| family.received.len())
        .sum();
    let summary = format!(
        "conformance verdict: repository complete: {} families, {executions} executions",
        verdict.required.len()
    );
    let failed: Vec<&str> = verdict
        .families
        .iter()
        .filter(|family| !family.passed())
        .map(|family| family.family_id.as_str())
        .chain(verdict.missing.iter().map(String::as_str))
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    let failure = format!(
        "conformance verdict: repository incomplete: {} of {} families failed: {}",
        failed.len(),
        verdict.required.len(),
        failed.join(", ")
    );
    if verdict.complete() && findings.is_empty() {
        return Ok(Outcome::Pass { summary });
    }
    if findings.is_empty() {
        findings.push(Finding {
            path: String::from("."),
            line: 1,
            rule: "conformance-verdict",
            message: failure.clone(),
        });
    }
    Ok(Outcome::from_findings(findings, summary, failure))
}

/// Authenticates one downloaded plan and validates its receipt.
fn judge_plan(
    root: &RepoRoot,
    prepared: &PreparedPack,
    loaded: &LoadedPack,
    executions: &[Execution],
    applicability: &Applicability,
    path: &Path,
    receipt_path: &Path,
) -> std::result::Result<PreparedReport, String> {
    let mut expectations = None;
    let materialized = plan::reload(root, prepared, path, |participant| {
        let execution = executions
            .iter()
            .find(|execution| {
                execution.participant == participant.id
                    && execution.instance == participant.execution_instance_id
                    && execution.role.as_str() == participant.role
            })
            .ok_or_else(|| {
                format!(
                    "{}/{} is not applicable to {}",
                    participant.id, participant.execution_instance_id, prepared.family_id
                )
            })?;
        let (payload, paths, _) = payload_for(loaded, execution, applicability)?;
        Ok((payload, paths))
    })?;
    let plan_value: RunPlan =
        serde_json::from_value(materialized.plan.clone()).map_err(|error| error.to_string())?;
    if plan_value.participant.role == Role::Consumer.as_str() {
        let execution = executions
            .iter()
            .find(|execution| {
                execution.participant == plan_value.participant.id
                    && execution.instance == plan_value.participant.execution_instance_id
            })
            .ok_or("the consumer is not applicable")?;
        expectations = payload_for(loaded, execution, applicability)?.2;
    }
    let bytes = std::fs::read(receipt_path).ok();
    Ok(receipt::validate(
        prepared,
        &plan_value,
        bytes.as_deref(),
        expectations.as_ref(),
    ))
}

/// Every scenario's compiled expectation, by family and scenario ID: what a
/// correct participant's observation must equal after normalization.
///
/// # Errors
///
/// Fails when a pack or catalog has findings, or cannot be read.
pub fn expectations(root: &RepoRoot) -> Result<BTreeMap<String, BTreeMap<String, Value>>> {
    let (packs, _) = match load_inputs(root)? {
        Ok(inputs) => inputs,
        Err(Outcome::Fail { findings, .. }) => {
            let listed: Vec<String> = findings.iter().map(ToString::to_string).collect();
            bail!("conformance inputs have findings:\n{}", listed.join("\n"));
        }
        Err(Outcome::Pass { .. }) => unreachable!("load_inputs only returns failing outcomes"),
    };
    let mut all = BTreeMap::new();
    for loaded in &packs.loaded {
        let compiled = loaded
            .compiled
            .as_ref()
            .context("a clean pack has compiled expectations")?;
        let scenarios = loaded
            .pack
            .scenarios
            .iter()
            .zip(&compiled.expected)
            .map(|(scenario, expected)| (scenario.id.clone(), Value::Object(expected.clone())))
            .collect();
        all.insert(loaded.pack.family_id.clone(), scenarios);
    }
    Ok(all)
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

#[cfg(test)]
#[path = "conformance_tests.rs"]
mod tests;
