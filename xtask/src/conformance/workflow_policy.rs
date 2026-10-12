//! The CI workflow policy: every required conformance execution is a
//! blocking, same-revision CI step, and the repository verdict sees all of
//! them.
//!
//! The workflows are parsed with `yaml-rust2` and walked structurally
//! (`jobs → steps`); no regular expression runs over the raw text. Line
//! numbers come from a second, event-level pass that records where each job
//! and step starts.
//!
//! What it enforces:
//!
//! - **Denominator.** For every required (family, participant, instance), the
//!   participant's job runs the family's launcher step, then uploads its
//!   diagnostics artifact. The step markers follow from the family and
//!   participant, so a newly applicable execution automatically needs a CI
//!   step. CXX, CLI and GUI run on the `compiler: [msvc, clang-cl]` matrix,
//!   which must cover exactly the two required instances.
//! - **Participant jobs.** `windows-latest`; `if: ${{ !cancelled() }}`
//!   exactly when the job has `needs`; no `continue-on-error`; the reserved
//!   `timeout-minutes` (`cli-tests` 360, `gui-tests` 180); exactly one
//!   default `actions/checkout@v6` with no `ref`, `path` or `repository`; and
//!   for matrix jobs `fail-fast: false` with no `exclude`.
//! - **Steps.** The legacy build/test step runs before the launcher, which
//!   runs before the upload. Launchers are blocking, use exactly
//!   `if: ${{ !cancelled() }}` and never claim `--profile full`. Uploads use
//!   exactly `if: always()` and `actions/upload-artifact@v6`; CXX uploads keep
//!   `**/run_plan.json`. GUI build and launcher steps use `-Preset
//!   ci-system-qt`.
//! - **Full aggregation** (`ci-binding-compliance.yml`): same-revision
//!   reusable `rust`/`native` jobs, `full` with `needs: [rust, native]`, the
//!   unmerged current-run artifact download, the upstream-result guard and the
//!   exact `--profile full` command.
//! - **Corrosion:** one pinned, archived Corrosion source per run, verified
//!   before each native build.
//! - **Crash Log Scan Run contract** preflight in ci-rust `test`: blocking,
//!   `if: ${{ !cancelled() }}`, before the Rust receipt run.

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::io::ErrorKind;

use anyhow::{Context, Result};
use yaml_rust2::parser::{Event, MarkedEventReceiver, Parser};
use yaml_rust2::scanner::Marker;
use yaml_rust2::{Yaml, YamlLoader};

use super::ExecutionKey;
use super::applicability::{CONSUMER_OBLIGATIONS, PARTICIPANTS};
use crate::{Finding, RepoRoot};

const RULE: &str = "workflow-policy";

const CI_RUST: &str = ".github/workflows/ci-rust.yml";
const CI_CPP: &str = ".github/workflows/ci-cpp.yml";
const CI_FULL: &str = ".github/workflows/ci-binding-compliance.yml";

/// The only accepted condition on launchers and jobs with `needs`.
const NOT_CANCELLED: &str = "${{ !cancelled() }}";
/// The only accepted condition on diagnostics uploads.
const ALWAYS: &str = "always()";
/// The compiler matrix of every native participant job.
const COMPILERS: [&str; 2] = ["msvc", "clang-cl"];

/// The Crash Log Scan Run contract preflight step, identified by its command.
const SCAN_RUN_CONTRACT_MARKER: &str = "scan_run_contract.py --repo-root .";
/// The Rust receipt run the preflight must precede.
const RUST_SCAN_RUN_LAUNCHER: &str = "run_scan_run_conformance.py --participant rust";

/// The `full` job's exact verdict command.
const FULL_COMMAND: &str = "python tools/binding_compliance/check_compliance.py --repo-root . --profile full --receipt-directory tools/binding_compliance/artifacts/downloaded --output-dir tools/binding_compliance/artifacts/full";

/// The pinned Corrosion revision and its per-run artifact.
const CORROSION_REVISION: &str = "1499b14e4906a2890f5cee1547c8848db261753d";
const CORROSION_ARTIFACT: &str = "corrosion-source-v0.6.1";

/// Checks the workflows at `root` against the policy for `required`.
///
/// Returns every violation as a finding; a missing or unparseable workflow
/// is a finding too.
///
/// # Errors
///
/// Fails when a workflow exists but cannot be read.
pub fn check(root: &RepoRoot, required: &BTreeSet<ExecutionKey>) -> Result<Vec<Finding>> {
    let mut findings = Vec::new();
    let mut workflows = BTreeMap::new();
    for file in [CI_RUST, CI_CPP, CI_FULL] {
        match Workflow::load(root, file)? {
            Ok(workflow) => {
                workflows.insert(file, workflow);
            }
            Err(finding) => findings.push(finding),
        }
    }
    let policies = step_policies(required, &mut findings);

    let mut jobs_checked = BTreeSet::new();
    for policy in &policies {
        let Some(workflow) = workflows.get(policy.workflow) else { continue };
        let Some(job) = workflow.job(policy.job, &mut findings) else { continue };
        if jobs_checked.insert((policy.workflow, policy.job)) {
            participant_job(workflow, &job, policy, &mut findings);
        }
        policy_steps(workflow, &job, policy, &mut findings);
    }
    if let Some(workflow) = workflows.get(CI_FULL) {
        full_aggregation(root, workflow, &mut findings)?;
    }
    if let Some(workflow) = workflows.get(CI_CPP) {
        corrosion(workflow, &mut findings);
    }
    if let Some(workflow) = workflows.get(CI_RUST) {
        scan_run_contract_preflight(workflow, &mut findings);
    }
    Ok(findings)
}

/// One required (family, participant) step pair and where it must run.
#[derive(Debug)]
struct StepPolicy {
    family: String,
    participant: String,
    workflow: &'static str,
    job: &'static str,
    /// The build/test step that must precede the launcher.
    legacy: &'static str,
    /// A substring of the launcher step's `run`.
    launcher: String,
    /// The upload step's exact artifact `name`.
    artifact: String,
    matrix: bool,
    timeout: Option<i64>,
}

/// Turns the required executions into step policies, one per (family,
/// participant). A matrix participant must require exactly both compiler
/// instances, since one matrix step runs both.
fn step_policies(required: &BTreeSet<ExecutionKey>, findings: &mut Vec<Finding>) -> Vec<StepPolicy> {
    let mut grouped: BTreeMap<(&str, &str), BTreeSet<&str>> = BTreeMap::new();
    for key in required {
        grouped
            .entry((key.family_id.as_str(), key.participant_id.as_str()))
            .or_default()
            .insert(key.instance_id.as_str());
    }
    let mut policies = Vec::new();
    for ((family, participant), instances) in grouped {
        let Some(policy) = step_policy(family, participant) else {
            findings.push(Finding {
                path: CONSUMER_OBLIGATIONS.to_owned(),
                line: 1,
                rule: RULE,
                message: format!("participant {participant} of {family} has no CI workflow policy"),
            });
            continue;
        };
        let expected: BTreeSet<&str> = if policy.matrix {
            ["windows-clang-cl", "windows-msvc"].into()
        } else {
            [participant].into()
        };
        if instances != expected {
            let source = if participant == "cxx" { PARTICIPANTS } else { CONSUMER_OBLIGATIONS };
            findings.push(Finding {
                path: source.to_owned(),
                line: 1,
                rule: RULE,
                message: format!(
                    "{family} requires {participant} instances {instances:?}, but its CI step runs exactly {expected:?}"
                ),
            });
        }
        policies.push(policy);
    }
    policies
}

/// The CI step markers of one (family, participant).
fn step_policy(family: &str, participant: &str) -> Option<StepPolicy> {
    const COMPILER: &str = "${{ matrix.compiler }}";
    let (workflow, job, legacy, launcher, artifact, matrix, timeout) = match participant {
        "rust" => {
            let (launcher, artifact) = match family {
                "crash-log-scan-run" => (
                    "run_scan_run_conformance.py --participant rust".to_owned(),
                    "rust-scan-run-conformance".to_owned(),
                ),
                "user-settings" => (
                    "run_user_settings_conformance.py --participant rust".to_owned(),
                    "rust-user-settings-conformance".to_owned(),
                ),
                "autoscan-report" | "crash-log-scan-launch" => (
                    format!("run_scan_run_conformance.py --family {family} --participant rust"),
                    format!("rust-{family}-conformance"),
                ),
                _ => (
                    format!("run_semantic_conformance.py --family {family} --participant rust"),
                    format!("rust-{family}-conformance"),
                ),
            };
            (CI_RUST, "test", "Run Rust tests with all features", launcher, artifact, false, None)
        }
        "tui" => {
            let (launcher, artifact) = if family == "crash-log-scan-run" {
                (
                    "run_scan_run_consumer_conformance.py --participant tui".to_owned(),
                    "tui-consumer-conformance".to_owned(),
                )
            } else {
                (
                    format!("run_scan_run_consumer_conformance.py --family {family} --participant tui"),
                    format!("tui-{family}-consumer-conformance"),
                )
            };
            (CI_RUST, "test", "Run Rust tests with all features", launcher, artifact, false, None)
        }
        "cxx" | "cli" | "gui" => {
            let script = match participant {
                "cxx" => "run_cxx_conformance.ps1",
                "cli" => "run_cli_consumer_conformance.ps1",
                _ => "run_gui_consumer_conformance.ps1",
            };
            let suffix = if participant == "cxx" { "conformance" } else { "consumer-conformance" };
            let (launcher, artifact) = if family == "crash-log-scan-run" {
                (
                    format!("{script} -Compiler {COMPILER}"),
                    format!("{participant}-{suffix}-{COMPILER}"),
                )
            } else {
                (
                    format!("{script} -Family {family} -Compiler {COMPILER}"),
                    format!("{participant}-{family}-{suffix}-{COMPILER}"),
                )
            };
            let (job, legacy, timeout) = if participant == "gui" {
                ("gui-tests", "Build and test GUI", 180)
            } else {
                ("cli-tests", "Build and test CLI", 360)
            };
            (CI_CPP, job, legacy, launcher, artifact, true, Some(timeout))
        }
        _ => return None,
    };
    Some(StepPolicy {
        family: family.to_owned(),
        participant: participant.to_owned(),
        workflow,
        job,
        legacy,
        launcher,
        artifact,
        matrix,
        timeout,
    })
}

/// Job-level checks shared by every policy that runs in the job.
fn participant_job(workflow: &Workflow, job: &Job<'_>, policy: &StepPolicy, findings: &mut Vec<Finding>) {
    let mut fail = |message: String| findings.push(workflow.finding(&job.path, message));
    let label = format!("job {}", job.id);
    if text(&job.yaml["runs-on"]) != Some("windows-latest") {
        fail(format!("{label} must run on windows-latest to preserve the Windows receipt checkout layout"));
    }
    let has_needs = !job.yaml["needs"].is_badvalue();
    let condition = &job.yaml["if"];
    if has_needs && text(condition) != Some(NOT_CANCELLED) {
        fail(format!("{label} has needs, so it must use `if: {NOT_CANCELLED}` to run after upstream failures unless cancelled"));
    }
    if !has_needs && !condition.is_badvalue() {
        fail(format!("{label} is required and cannot be conditionally skipped"));
    }
    if !job.yaml["continue-on-error"].is_badvalue() {
        fail(format!("{label} is required and must be blocking (no continue-on-error)"));
    }
    if let Some(minutes) = policy.timeout
        && job.yaml["timeout-minutes"].as_i64() != Some(minutes)
    {
        fail(format!("{label} must reserve timeout-minutes: {minutes} for its retained and promoted gates"));
    }
    let checkouts: Vec<&Yaml> = job.steps().iter().filter(|step| text(&step["uses"]) == Some("actions/checkout@v6")).collect();
    if checkouts.len() != 1 {
        fail(format!("{label} must use exactly one default actions/checkout@v6"));
    }
    for checkout in checkouts {
        if !checkout["with"]["ref"].is_badvalue() {
            fail(format!("{label} checkout cannot replace the event source revision (ref)"));
        }
        if ["path", "repository"].iter().any(|key| !checkout["with"][*key].is_badvalue()) {
            fail(format!("{label} must preserve the default receipt checkout layout (no path or repository)"));
        }
    }
    if policy.matrix {
        let strategy = &job.yaml["strategy"];
        let compilers: Option<Vec<&str>> = strategy["matrix"]["compiler"]
            .as_vec()
            .and_then(|items| items.iter().map(text).collect());
        if compilers.as_deref() != Some(&COMPILERS[..]) {
            fail(format!("{label} is missing the exact required matrix compiler: [msvc, clang-cl]"));
        }
        if strategy["fail-fast"].as_bool() != Some(false) {
            fail(format!("{label} matrix must keep fail-fast: false"));
        }
        if !strategy["matrix"]["exclude"].is_badvalue() {
            fail(format!("{label} matrix cannot exclude required executions"));
        }
    }
}

/// Step-level checks for one (family, participant).
fn policy_steps(workflow: &Workflow, job: &Job<'_>, policy: &StepPolicy, findings: &mut Vec<Finding>) {
    let label = format!("job {}: {} {}", job.id, policy.participant, policy.family);
    let steps = job.steps();
    let legacy = steps.iter().position(|step| {
        text(&step["name"]).is_some_and(|name| name.contains(policy.legacy))
            || text(&step["run"]).is_some_and(|run| run.contains(policy.legacy))
    });
    let launchers = job.find(|step| text(&step["run"]).is_some_and(|run| run.contains(&policy.launcher)));
    let uploads = job.find(|step| text(&step["with"]["name"]) == Some(policy.artifact.as_str()));
    let (Some(legacy), [launcher], [upload]) = (legacy, launchers.as_slice(), uploads.as_slice()) else {
        findings.push(workflow.finding(
            &job.path,
            format!(
                "{label} is missing a required marker: the legacy step {:?}, exactly one launcher running {:?} and exactly one upload named {:?}",
                policy.legacy, policy.launcher, policy.artifact
            ),
        ));
        return;
    };
    let (launcher, upload) = (*launcher, *upload);
    let mut fail = |index: usize, message: String| findings.push(workflow.finding(&job.step_path(index), message));
    if !(legacy < launcher && launcher < upload) {
        fail(launcher, format!("{label} must run legacy, receipt, and upload steps in order"));
    }
    let launch = &steps[launcher];
    if !launch["continue-on-error"].is_badvalue() {
        fail(launcher, format!("{label} launcher must be blocking"));
    }
    if text(&launch["if"]) != Some(NOT_CANCELLED) {
        fail(launcher, format!("{label} launcher must run after earlier failures unless cancelled (`if: {NOT_CANCELLED}`)"));
    }
    if text(&launch["run"]).is_some_and(|run| run.contains("--profile full")) {
        fail(launcher, format!("{label} launcher cannot claim full-repository scope"));
    }
    if policy.participant == "gui" {
        for index in [legacy, launcher] {
            let presets = presets(text(&steps[index]["run"]).unwrap_or_default());
            if presets != ["ci-system-qt"] {
                fail(index, format!("{label} must reuse the preceding GUI build preset ci-system-qt"));
            }
        }
    }
    let artifact = &steps[upload];
    if text(&artifact["if"]) != Some(ALWAYS) {
        fail(upload, format!("{label} diagnostics must upload even on failure (`if: {ALWAYS}`)"));
    }
    if text(&artifact["uses"]) != Some("actions/upload-artifact@v6") {
        fail(upload, format!("{label} artifact marker is not an actions/upload-artifact@v6 step"));
    }
    if policy.participant == "cxx"
        && !text(&artifact["with"]["path"]).is_some_and(|path| path.contains("**/run_plan.json"))
    {
        fail(upload, format!("{label} upload must retain the authenticated run plan (**/run_plan.json)"));
    }
}

/// Every value following a `-Preset` token in a command line.
fn presets(command: &str) -> Vec<&str> {
    let tokens: Vec<&str> = command.split_whitespace().collect();
    tokens
        .windows(2)
        .filter(|pair| pair[0] == "-Preset")
        .map(|pair| pair[1])
        .collect()
}

/// `ci-binding-compliance.yml`: the repository verdict's inputs.
fn full_aggregation(root: &RepoRoot, workflow: &Workflow, findings: &mut Vec<Finding>) -> Result<()> {
    for (job_id, callee) in [("rust", CI_RUST), ("native", CI_CPP)] {
        let Some(job) = workflow.job(job_id, findings) else { continue };
        let mut fail = |message: String| findings.push(workflow.finding(&job.path, format!("full aggregation: {message}")));
        if text(&job.yaml["uses"]) != Some(&format!("./{callee}")) {
            fail(format!("job {job_id} must be the same-revision reusable workflow ./{callee}"));
        }
        if ["if", "continue-on-error", "needs"].iter().any(|key| !job.yaml[*key].is_badvalue()) {
            fail(format!("job {job_id} cannot skip a required reusable job (no if, continue-on-error or needs)"));
        }
        let callee_text = match std::fs::read_to_string(root.join(callee)) {
            Ok(text) => Some(text),
            Err(error) if error.kind() == ErrorKind::NotFound => None,
            Err(error) => return Err(error).with_context(|| format!("reading {callee}")),
        };
        let callable = callee_text
            .and_then(|text| YamlLoader::load_from_str(&text).ok())
            .and_then(|docs| docs.into_iter().next())
            .is_some_and(|doc| doc["on"].as_hash().is_some_and(|on| on.contains_key(&Yaml::String("workflow_call".into()))));
        if !callable {
            fail(format!("{callee} must declare `on: workflow_call` to be a full aggregation participant"));
        }
    }

    let Some(full) = workflow.job("full", findings) else { return Ok(()) };
    let mut fail = |path: &str, message: &str| findings.push(workflow.finding(path, format!("full aggregation: {message}")));
    let needs: Option<Vec<&str>> = full.yaml["needs"].as_vec().and_then(|items| items.iter().map(text).collect());
    if needs.as_deref() != Some(&["rust", "native"][..])
        || text(&full.yaml["if"]) != Some(NOT_CANCELLED)
        || text(&full.yaml["runs-on"]) != Some("windows-latest")
    {
        fail(&full.path, "job full must await every Windows participant: needs: [rust, native], if: ${{ !cancelled() }}, runs-on: windows-latest");
    }
    if !full.yaml["continue-on-error"].is_badvalue() {
        fail(&full.path, "job full must be blocking");
    }

    let checkouts = full.find(|step| text(&step["uses"]) == Some("actions/checkout@v6"));
    match checkouts.as_slice() {
        [index] if ["ref", "path", "repository"].iter().all(|key| full.steps()[*index]["with"][*key].is_badvalue()) => {}
        [index] => fail(&full.step_path(*index), "the checkout must preserve the event checkout identity"),
        _ => fail(&full.path, "job full must check out the repository exactly once"),
    }

    let download = full.find(|step| text(&step["name"]) == Some("Download current-run conformance artifacts"));
    match download.as_slice() {
        [index] => {
            let step = &full.steps()[*index];
            let with = &step["with"];
            let exact = text(&step["uses"]) == Some("actions/download-artifact@v8")
                && text(&with["pattern"]) == Some("*conformance*")
                && text(&with["path"]) == Some("tools/binding_compliance/artifacts/downloaded")
                && with["merge-multiple"].as_bool() == Some(false);
            if !exact {
                fail(&full.step_path(*index), "the download must take every unmerged receipt artifact (download-artifact@v8, pattern '*conformance*', merge-multiple: false)");
            }
            if ["run-id", "repository", "github-token", "name", "artifact-ids"].iter().any(|key| !with[*key].is_badvalue()) {
                fail(&full.step_path(*index), "artifacts must come from the current workflow run");
            }
        }
        _ => fail(&full.path, "job full must have one \"Download current-run conformance artifacts\" step"),
    }

    let guard = full.find(|step| text(&step["name"]) == Some("Require every retained participant job to pass"));
    match guard.as_slice() {
        [index] => {
            let step = &full.steps()[*index];
            let ok = text(&step["env"]["PARTICIPANT_RESULTS"]) == Some("${{ toJSON(needs) }}")
                && step["continue-on-error"].is_badvalue()
                && text(&step["if"]) == Some(NOT_CANCELLED);
            if !ok {
                fail(&full.step_path(*index), "the upstream guard must require actual upstream job results (PARTICIPANT_RESULTS: ${{ toJSON(needs) }}, blocking, if: ${{ !cancelled() }})");
            }
        }
        _ => fail(&full.path, "job full must have one \"Require every retained participant job to pass\" step"),
    }

    let launchers = full.find(|step| {
        text(&step["run"]).is_some_and(|run| run.contains("tools/binding_compliance/check_compliance.py"))
    });
    match launchers.as_slice() {
        [index] => {
            let step = &full.steps()[*index];
            if text(&step["run"]).map(str::trim_end) != Some(FULL_COMMAND) || !step["continue-on-error"].is_badvalue() {
                fail(&full.step_path(*index), "the verdict step must execute the complete full profile command");
            }
            if text(&step["if"]) != Some(NOT_CANCELLED) {
                fail(&full.step_path(*index), "the verdict step must report upstream failures (if: ${{ !cancelled() }})");
            }
        }
        _ => fail(&full.path, "job full must run check_compliance.py exactly once"),
    }
    Ok(())
}

/// `ci-cpp.yml`: one pinned Corrosion source per run, verified before each
/// native build.
fn corrosion(workflow: &Workflow, findings: &mut Vec<Finding>) {
    let archive_markers = [
        "git clone --depth 1 --branch v0.6.1",
        CORROSION_REVISION,
        "git -C $sourceDir archive --format=zip",
        "Get-FileHash -LiteralPath $archivePath -Algorithm SHA256",
    ];
    if let Some(fetch) = workflow.job("corrosion-source", findings) {
        let mut fail = |path: &str, message: &str| findings.push(workflow.finding(path, format!("Corrosion source: {message}")));
        match fetch.find(|step| text(&step["name"]) == Some("Archive verified Corrosion v0.6.1 source")).as_slice() {
            [index] => {
                let run = text(&fetch.steps()[*index]["run"]).unwrap_or_default();
                if !archive_markers.iter().all(|marker| run.contains(marker)) {
                    fail(&fetch.step_path(*index), "the source must be pinned to its revision and archived once");
                }
            }
            _ => fail(&fetch.path, "job corrosion-source must archive the verified source once"),
        }
        match fetch.find(|step| text(&step["name"]) == Some("Upload pinned Corrosion source")).as_slice() {
            [index] => {
                let step = &fetch.steps()[*index];
                let ok = text(&step["uses"]) == Some("actions/upload-artifact@v6")
                    && text(&step["with"]["name"]) == Some(CORROSION_ARTIFACT)
                    && text(&step["with"]["path"]) == Some("${{ runner.temp }}/classic-corrosion-artifact/")
                    && text(&step["with"]["if-no-files-found"]) == Some("error");
                if !ok {
                    fail(&fetch.step_path(*index), "the archive must be uploaded as corrosion-source-v0.6.1 with if-no-files-found: error");
                }
            }
            _ => fail(&fetch.path, "the archive must be uploaded once"),
        }
        if !fetch.yaml["continue-on-error"].is_badvalue() || !fetch.yaml["strategy"].is_badvalue() {
            fail(&fetch.path, "the fetch must be one blocking job (no matrix, no continue-on-error)");
        }
    }

    let verify_markers = [
        CORROSION_REVISION,
        "Get-FileHash -LiteralPath $archivePath -Algorithm SHA256",
        "Expand-Archive -LiteralPath $archivePath",
        "CLASSIC_CORROSION_SOURCE_DIR=$sourceDir",
    ];
    for (job_id, build) in [("cli-tests", "Build and test CLI"), ("gui-tests", "Build and test GUI")] {
        let Some(job) = workflow.job(job_id, findings) else { continue };
        let mut fail = |path: &str, message: &str| findings.push(workflow.finding(path, format!("Corrosion source: {message}")));
        let needs: Option<Vec<&str>> = job.yaml["needs"].as_vec().and_then(|items| items.iter().map(text).collect());
        if needs.as_deref() != Some(&["corrosion-source"][..]) {
            fail(&job.path, "the corrosion-source job must gate each native build (needs: [corrosion-source])");
        }
        match job.find(|step| text(&step["name"]) == Some("Download pinned Corrosion source")).as_slice() {
            [index] => {
                let step = &job.steps()[*index];
                let with = &step["with"];
                let ok = text(&step["uses"]) == Some("actions/download-artifact@v8")
                    && text(&with["name"]) == Some(CORROSION_ARTIFACT)
                    && text(&with["path"]) == Some("${{ runner.temp }}/classic-corrosion-artifact")
                    && ["run-id", "repository", "github-token", "artifact-ids"].iter().all(|key| with[*key].is_badvalue());
                if !ok {
                    fail(&job.step_path(*index), "the source must come from this run's corrosion-source-v0.6.1 artifact");
                }
            }
            _ => fail(&job.path, "the source must be downloaded once from this run"),
        }
        let verify = job.find(|step| text(&step["name"]) == Some("Verify and extract pinned Corrosion source"));
        let build_index = job.steps().iter().position(|step| text(&step["name"]) == Some(build));
        match verify.as_slice() {
            [index] => {
                let run = text(&job.steps()[*index]["run"]).unwrap_or_default();
                if !verify_markers.iter().all(|marker| run.contains(marker)) {
                    fail(&job.step_path(*index), "the verification was weakened (revision, hash, Expand-Archive, CLASSIC_CORROSION_SOURCE_DIR)");
                }
                if build_index.is_none_or(|build_index| *index > build_index) {
                    fail(&job.step_path(*index), "the source must be verified before the build");
                }
            }
            _ => fail(&job.path, "the source must be verified and extracted once"),
        }
    }
}

/// ci-rust `test`: the Crash Log Scan Run contract preflight.
fn scan_run_contract_preflight(workflow: &Workflow, findings: &mut Vec<Finding>) {
    let Some(job) = workflow.job("test", findings) else { return };
    let preflight = job.find(|step| text(&step["run"]).is_some_and(|run| run.contains(SCAN_RUN_CONTRACT_MARKER)));
    let [index] = preflight.as_slice() else {
        findings.push(workflow.finding(&job.path, format!("job test must run the variant preflight ({SCAN_RUN_CONTRACT_MARKER}) exactly once")));
        return;
    };
    let step = &job.steps()[*index];
    let mut fail = |message: &str| findings.push(workflow.finding(&job.step_path(*index), message.to_owned()));
    if !step["continue-on-error"].is_badvalue() {
        fail("the ci-rust variant preflight must be blocking");
    }
    if text(&step["if"]) != Some(NOT_CANCELLED) {
        fail("the ci-rust variant preflight must run after earlier failures unless cancelled");
    }
    let rust = job.steps().iter().position(|step| text(&step["run"]).is_some_and(|run| run.contains(RUST_SCAN_RUN_LAUNCHER)));
    if rust.is_some_and(|rust| *index > rust) {
        fail("the ci-rust variant preflight must run before Rust receipt execution");
    }
}

/// A string scalar's text.
fn text(value: &Yaml) -> Option<&str> {
    value.as_str()
}

/// One parsed workflow plus the line where each node starts.
struct Workflow {
    file: &'static str,
    yaml: Yaml,
    lines: HashMap<String, usize>,
}

/// A job inside a workflow.
struct Job<'a> {
    id: &'a str,
    path: String,
    yaml: &'a Yaml,
}

impl Job<'_> {
    fn steps(&self) -> &[Yaml] {
        self.yaml["steps"].as_vec().map_or(&[], Vec::as_slice)
    }

    /// Indices of the steps matching `predicate`.
    fn find(&self, predicate: impl Fn(&Yaml) -> bool) -> Vec<usize> {
        self.steps()
            .iter()
            .enumerate()
            .filter(|(_, step)| predicate(step))
            .map(|(index, _)| index)
            .collect()
    }

    fn step_path(&self, index: usize) -> String {
        format!("{}/steps/{index}", self.path)
    }
}

impl Workflow {
    /// Loads `file`; a missing or unparseable workflow is a finding.
    fn load(root: &RepoRoot, file: &'static str) -> Result<std::result::Result<Self, Finding>> {
        let finding = |line: usize, message: String| Finding {
            path: file.to_owned(),
            line,
            rule: RULE,
            message,
        };
        let source = match std::fs::read_to_string(root.join(file)) {
            Ok(source) => source,
            Err(error) if error.kind() == ErrorKind::NotFound => {
                return Ok(Err(finding(1, "required workflow is missing".into())));
            }
            Err(error) => return Err(error).with_context(|| format!("reading {file}")),
        };
        let yaml = match YamlLoader::load_from_str(&source) {
            Ok(mut documents) if documents.len() == 1 => documents.remove(0),
            Ok(_) => return Ok(Err(finding(1, "a workflow must be exactly one YAML document".into()))),
            Err(error) => {
                return Ok(Err(finding(error.marker().line().max(1), format!("invalid YAML: {}", error.info()))));
            }
        };
        let mut tracker = LineTracker::default();
        // The loader above already accepted the text, so this event pass
        // cannot fail; a failure would only cost line precision.
        let _ = Parser::new_from_str(&source).load(&mut tracker, true);
        Ok(Ok(Self {
            file,
            yaml,
            lines: tracker.lines,
        }))
    }

    /// The job `id`, or a finding when the workflow has no such job.
    fn job<'a>(&'a self, id: &'a str, findings: &mut Vec<Finding>) -> Option<Job<'a>> {
        let yaml = &self.yaml["jobs"][id];
        if yaml.as_hash().is_none() {
            findings.push(self.finding("/jobs", format!("missing required workflow job {id}")));
            return None;
        }
        Some(Job {
            id,
            path: format!("/jobs/{id}"),
            yaml,
        })
    }

    /// A finding at the node `path` (`/jobs/<id>[/steps/<n>]`).
    fn finding(&self, path: &str, message: String) -> Finding {
        let mut current = path;
        let line = loop {
            if let Some(line) = self.lines.get(current) {
                break *line;
            }
            match current.rfind('/') {
                Some(index) => current = &current[..index],
                None => break 1,
            }
        };
        Finding {
            path: self.file.to_owned(),
            line,
            rule: RULE,
            message,
        }
    }
}

/// Records the line where each mapping entry and sequence item starts, keyed
/// by its slash path (`/jobs/test/steps/3`).
#[derive(Default)]
struct LineTracker {
    stack: Vec<Frame>,
    lines: HashMap<String, usize>,
}

enum Frame {
    Mapping { path: String, key: Option<String> },
    Sequence { path: String, next: usize },
}

impl LineTracker {
    /// Advances the parent for a new node and returns the node's path, or
    /// `None` when the node is a mapping key (its line is recorded for the
    /// entry it names).
    fn enter(&mut self, scalar: Option<&str>, line: usize) -> Option<String> {
        match self.stack.last_mut() {
            None => Some(String::new()),
            Some(Frame::Sequence { path, next }) => {
                let child = format!("{path}/{next}");
                *next += 1;
                self.lines.entry(child.clone()).or_insert(line);
                Some(child)
            }
            Some(Frame::Mapping { path, key }) => match key.take() {
                None => {
                    let name = scalar.unwrap_or("?").to_owned();
                    self.lines.entry(format!("{path}/{name}")).or_insert(line);
                    *key = Some(name);
                    None
                }
                Some(name) => Some(format!("{path}/{name}")),
            },
        }
    }
}

impl MarkedEventReceiver for LineTracker {
    fn on_event(&mut self, event: Event, mark: Marker) {
        match event {
            Event::Scalar(value, ..) => {
                self.enter(Some(&value), mark.line());
            }
            Event::Alias(_) => {
                self.enter(None, mark.line());
            }
            Event::SequenceStart(..) => {
                let path = self.enter(None, mark.line()).unwrap_or_else(|| "/?".into());
                self.stack.push(Frame::Sequence { path, next: 0 });
            }
            Event::MappingStart(..) => {
                let path = self.enter(None, mark.line()).unwrap_or_else(|| "/?".into());
                self.stack.push(Frame::Mapping { path, key: None });
            }
            Event::SequenceEnd | Event::MappingEnd => {
                self.stack.pop();
            }
            _ => {}
        }
    }
}

#[cfg(test)]
#[path = "workflow_policy_tests.rs"]
mod tests;
