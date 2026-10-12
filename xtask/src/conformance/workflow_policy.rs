//! The CI workflow policy: every required conformance execution and every
//! surviving gate is a blocking, same-revision CI step, and the repository
//! verdict sees all of them.
//!
//! The workflows are parsed with `yaml-rust2` and walked structurally
//! (`jobs → steps`); no regular expression runs over the raw text. Line
//! numbers come from a second, event-level pass that records where each job
//! and step starts.
//!
//! What it enforces:
//!
//! - **Pinned jobs** ([`JOBS`]): every job that hosts a gate or a
//!   conformance step keeps its runner, its exact `timeout-minutes` and
//!   `needs`, `if: ${{ !cancelled() }}` exactly when it has `needs` (no
//!   condition otherwise), no `continue-on-error`, exactly one default
//!   `actions/checkout@v6` (no `ref`, `path` or `repository`), and for the
//!   native jobs the `compiler: [msvc, clang-cl]` matrix with
//!   `fail-fast: false` and no `exclude`/`include`.
//! - **Pinned steps**: each gate step appears exactly once, by name, with
//!   its exact `run` (or `uses`), `if`, `with`, `env` and step timeout and no
//!   other key (so no `continue-on-error`), in the pinned order. That covers
//!   `cxx-bridge-gate`, `xtask-linux`, clippy, the cargo-test steps,
//!   `user-settings-ownership`, `scan-run-contract`, `conformance check`,
//!   the native build-and-test steps, every `conformance run` and its upload,
//!   and the `full` job's download, participant guard, verdict and upload.
//! - **Denominator.** Every (participant, execution instance) the packs and
//!   catalogs require has its `conformance run` step, and every run step
//!   runs a participant something requires. One run covers every family of
//!   its participant, so a new family needs no new step; a new participant
//!   does. CXX, CLI and GUI run on the two-compiler matrix, so they must be
//!   required on exactly both instances.
//! - **Full aggregation** (`ci-binding-compliance.yml`): same-revision
//!   reusable `rust`/`native` jobs that cannot be skipped, and callees that
//!   declare `workflow_call`.
//! - **Corrosion:** one pinned, archived Corrosion source per run, verified
//!   before each native build.

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::io::ErrorKind;

use anyhow::{Context, Result};
use yaml_rust2::parser::{Event, MarkedEventReceiver, Parser};
use yaml_rust2::scanner::Marker;
use yaml_rust2::{Yaml, YamlLoader};

use super::ExecutionKey;
use super::applicability::CONSUMER_OBLIGATIONS;
use crate::{Finding, RepoRoot};

const RULE: &str = "workflow-policy";

const CI_RUST: &str = ".github/workflows/ci-rust.yml";
const CI_CPP: &str = ".github/workflows/ci-cpp.yml";
const CI_FULL: &str = ".github/workflows/ci-binding-compliance.yml";

/// The only accepted condition on conformance runs and on jobs with `needs`.
const NOT_CANCELLED: &str = "${{ !cancelled() }}";
/// The only accepted condition on diagnostics uploads.
const ALWAYS: &str = "always()";
/// The compiler matrix of every native participant job.
const COMPILERS: [&str; 2] = ["msvc", "clang-cl"];
/// The execution instances that matrix runs.
const MATRIX_INSTANCES: [&str; 2] = ["windows-clang-cl", "windows-msvc"];

/// The pinned Corrosion revision and its per-run artifact.
const CORROSION_REVISION: &str = "1499b14e4906a2890f5cee1547c8848db261753d";
const CORROSION_ARTIFACT: &str = "corrosion-source-v0.6.1";

/// What a pinned step executes.
#[derive(Debug, Clone, Copy)]
enum Action {
    /// A shell command, compared exactly (trailing whitespace ignored).
    Run(&'static str),
    /// An action reference, compared exactly.
    Uses(&'static str),
}

/// One pinned step, matched by its `name`.
#[derive(Debug)]
struct StepPin {
    name: &'static str,
    action: Action,
    /// The exact `if`, or `None` for a step that must have no condition.
    condition: Option<&'static str>,
    /// The exact `with` mapping (empty: no `with`).
    with: &'static [(&'static str, &'static str)],
    /// The exact `env` mapping (empty: no `env`).
    env: &'static [(&'static str, &'static str)],
    /// The exact step `timeout-minutes`, if any.
    timeout: Option<i64>,
}

impl StepPin {
    /// A step running `command` with no condition.
    const fn run(name: &'static str, command: &'static str) -> Self {
        Self {
            name,
            action: Action::Run(command),
            condition: None,
            with: &[],
            env: &[],
            timeout: None,
        }
    }

    /// A step running `command` even after earlier failures (unless the
    /// workflow was cancelled).
    const fn run_unless_cancelled(name: &'static str, command: &'static str) -> Self {
        Self {
            condition: Some(NOT_CANCELLED),
            ..Self::run(name, command)
        }
    }

    /// An action step with no condition and no inputs yet.
    const fn uses(name: &'static str, action: &'static str) -> Self {
        Self {
            name,
            action: Action::Uses(action),
            condition: None,
            with: &[],
            env: &[],
            timeout: None,
        }
    }

    /// A diagnostics upload, which runs even on failure; its inputs are
    /// filled in by the caller (see [`upload!`]).
    const fn upload(name: &'static str) -> Self {
        Self {
            condition: Some(ALWAYS),
            ..Self::uses(name, "actions/upload-artifact@v6")
        }
    }
}

/// Builds an upload [`StepPin`] of `path` as artifact `artifact`. A missing
/// directory only warns: a run that wrote nothing is reported by the verdict
/// as a missing execution instead.
macro_rules! upload {
    ($name:expr, $artifact:expr, $path:expr) => {
        StepPin {
            with: &[
                ("name", $artifact),
                ("path", $path),
                ("if-no-files-found", "warn"),
                ("retention-days", "7"),
            ],
            ..StepPin::upload($name)
        }
    };
}

/// One pinned job and its pinned steps, in their required order.
#[derive(Debug)]
struct JobPin {
    workflow: &'static str,
    job: &'static str,
    runs_on: &'static str,
    timeout: i64,
    /// The exact `needs` (empty: none).
    needs: &'static [&'static str],
    /// Whether the job runs on the two-compiler matrix.
    matrix: bool,
    steps: &'static [StepPin],
}

/// Every pinned job. Changing a pinned value is a deliberate edit here, in
/// the same change as the workflow.
const JOBS: &[JobPin] = &[
    JobPin {
        workflow: CI_RUST,
        job: "lint",
        runs_on: "windows-latest",
        timeout: 60,
        needs: &[],
        matrix: false,
        steps: &[
            StepPin::run(
                "Check User Settings exclusive ownership",
                "cargo xtask user-settings-ownership",
            ),
            StepPin::run(
                "Check conformance packs, catalogs and workflow policy",
                "cargo xtask conformance check",
            ),
            StepPin::run(
                "Run clippy",
                "cargo clippy --workspace --all-targets --all-features -- -D warnings",
            ),
        ],
    },
    JobPin {
        workflow: CI_RUST,
        job: "test",
        runs_on: "windows-latest",
        timeout: 120,
        needs: &[],
        matrix: false,
        steps: &[
            StepPin::run(
                "Run phase-1 logging contract tests (Rust)",
                "cargo test -p classic-message-core -- --nocapture",
            ),
            StepPin::run(
                "Run Rust tests",
                "cargo test --workspace --release -- --nocapture",
            ),
            StepPin::run(
                "Run Rust tests with all features",
                "cargo test --workspace --release --all-features -- --nocapture",
            ),
            // The variant preflight runs before the Rust receipt run.
            StepPin::run_unless_cancelled(
                "Validate Crash Log Scan Run variant coverage",
                "cargo xtask scan-run-contract",
            ),
            StepPin::run_unless_cancelled(
                "Run Rust conformance",
                "cargo xtask conformance run --participant rust --artifact-root ${{ runner.temp }}/conformance",
            ),
            StepPin::run_unless_cancelled(
                "Run TUI consumer conformance",
                "cargo xtask conformance run --participant tui --artifact-root ${{ runner.temp }}/conformance",
            ),
            upload!(
                "Upload Rust conformance artifacts",
                "rust-conformance",
                "${{ runner.temp }}/conformance/rust/rust/"
            ),
            upload!(
                "Upload TUI consumer conformance artifacts",
                "tui-conformance",
                "${{ runner.temp }}/conformance/tui/tui/"
            ),
        ],
    },
    JobPin {
        workflow: CI_RUST,
        job: "xtask-linux",
        runs_on: "ubuntu-latest",
        timeout: 30,
        needs: &[],
        matrix: false,
        steps: &[
            StepPin::run("Build xtask", "cargo build -p xtask --locked"),
            StepPin::run(
                "Validate YAML Data",
                "cargo xtask yaml-data validate --databases-dir \"CLASSIC Data/databases\" --schema-ranges \"CLASSIC Data/databases/client-schema-ranges.yaml\"",
            ),
            StepPin::run(
                "Validate app-notification source",
                "cargo xtask app-notification validate --source \"CLASSIC Data/app-notification.yaml\"",
            ),
            StepPin::run(
                "Dry-run app-notification publish",
                "cargo xtask app-notification dry-run --workflow-tag app-notification-v0.0.0",
            ),
        ],
    },
    JobPin {
        workflow: CI_CPP,
        job: "cxx-bridge-gate",
        runs_on: "windows-latest",
        timeout: 20,
        needs: &[],
        matrix: false,
        steps: &[
            StepPin::run("Build xtask", "cargo build -p xtask --locked"),
            StepPin::run(
                "Check for orphan CXX bridge exports",
                "cargo xtask cxx-bridge-gate",
            ),
        ],
    },
    JobPin {
        workflow: CI_CPP,
        job: "cli-tests",
        runs_on: "windows-latest",
        timeout: 360,
        needs: &["corrosion-source"],
        matrix: true,
        steps: &[
            // The CTest-only conformance runs reuse this build.
            StepPin {
                timeout: Some(90),
                ..StepPin::run(
                    "Build and test CLI",
                    "pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -Compiler ${{ matrix.compiler }}",
                )
            },
            StepPin::run_unless_cancelled(
                "Run native CXX conformance",
                "cargo xtask conformance run --participant cxx --compiler ${{ matrix.compiler }} --artifact-root ${{ runner.temp }}/conformance",
            ),
            StepPin::run_unless_cancelled(
                "Run CLI consumer conformance",
                "cargo xtask conformance run --participant cli --compiler ${{ matrix.compiler }} --artifact-root ${{ runner.temp }}/conformance",
            ),
            upload!(
                "Upload native CXX conformance artifacts",
                "cxx-conformance-${{ matrix.compiler }}",
                "${{ runner.temp }}/conformance/cxx/windows-${{ matrix.compiler }}/"
            ),
            upload!(
                "Upload CLI consumer conformance artifacts",
                "cli-conformance-${{ matrix.compiler }}",
                "${{ runner.temp }}/conformance/cli/windows-${{ matrix.compiler }}/"
            ),
        ],
    },
    JobPin {
        workflow: CI_CPP,
        job: "gui-tests",
        runs_on: "windows-latest",
        timeout: 180,
        needs: &["corrosion-source"],
        matrix: true,
        steps: &[
            // The conformance run reuses this build, so both use ci-system-qt.
            StepPin::run(
                "Build and test GUI",
                "pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Preset ci-system-qt -Test -TestTimeoutSec 600 -Compiler ${{ matrix.compiler }}",
            ),
            StepPin::run_unless_cancelled(
                "Run GUI consumer conformance",
                "cargo xtask conformance run --participant gui --compiler ${{ matrix.compiler }} --preset ci-system-qt --artifact-root ${{ runner.temp }}/conformance",
            ),
            upload!(
                "Upload GUI consumer conformance artifacts",
                "gui-conformance-${{ matrix.compiler }}",
                "${{ runner.temp }}/conformance/gui/windows-${{ matrix.compiler }}/"
            ),
        ],
    },
    JobPin {
        workflow: CI_FULL,
        job: "full",
        runs_on: "windows-latest",
        timeout: 360,
        needs: &["rust", "native"],
        matrix: false,
        steps: &[
            // Every artifact of this run, unmerged, and no other run's.
            StepPin {
                with: &[
                    ("pattern", "*conformance*"),
                    ("path", "${{ runner.temp }}/conformance"),
                    ("merge-multiple", "false"),
                ],
                ..StepPin::uses(
                    "Download current-run conformance artifacts",
                    "actions/download-artifact@v8",
                )
            },
            // Exactly the two reusable participant workflows, each passed.
            StepPin {
                env: &[("PARTICIPANT_RESULTS", "${{ toJSON(needs) }}")],
                ..StepPin::run_unless_cancelled(
                    "Require every retained participant job to pass",
                    "$results = $env:PARTICIPANT_RESULTS | ConvertFrom-Json -AsHashtable\n\
                     if ($results.Count -ne 2 -or @($results.Values | Where-Object { $_.result -ne 'success' }).Count -ne 0) {\n  \
                     throw 'Every retained participant workflow must pass before repository conformance can pass.'\n\
                     }",
                )
            },
            StepPin::run_unless_cancelled(
                "Run full repository conformance verdict",
                "cargo xtask conformance verdict --receipts ${{ runner.temp }}/conformance --output ${{ runner.temp }}/conformance-verdict/verdict.json",
            ),
            StepPin {
                with: &[
                    ("name", "full-repository-verdict"),
                    ("path", "${{ runner.temp }}/conformance-verdict/"),
                    ("if-no-files-found", "warn"),
                    ("retention-days", "7"),
                    ("overwrite", "true"),
                ],
                ..StepPin::upload("Upload full repository conformance verdict")
            },
        ],
    },
];

/// The `conformance run` step of each participant: (participant, workflow,
/// job, step name, runs on the compiler matrix).
const RUN_STEPS: &[(&str, &str, &str, &str, bool)] = &[
    ("rust", CI_RUST, "test", "Run Rust conformance", false),
    (
        "tui",
        CI_RUST,
        "test",
        "Run TUI consumer conformance",
        false,
    ),
    (
        "cxx",
        CI_CPP,
        "cli-tests",
        "Run native CXX conformance",
        true,
    ),
    (
        "cli",
        CI_CPP,
        "cli-tests",
        "Run CLI consumer conformance",
        true,
    ),
    (
        "gui",
        CI_CPP,
        "gui-tests",
        "Run GUI consumer conformance",
        true,
    ),
];

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
    for pin in JOBS {
        let Some(workflow) = workflows.get(pin.workflow) else {
            continue;
        };
        let Some(job) = workflow.job(pin.job, &mut findings) else {
            continue;
        };
        pinned_job(workflow, &job, pin, &mut findings);
        pinned_steps(workflow, &job, pin, &mut findings);
    }
    denominator(&workflows, required, &mut findings);
    if let Some(workflow) = workflows.get(CI_FULL) {
        full_aggregation(root, workflow, &mut findings)?;
    }
    if let Some(workflow) = workflows.get(CI_CPP) {
        corrosion(workflow, &mut findings);
    }
    Ok(findings)
}

/// A scalar's text, whatever its YAML type (`7`, `false` and `"7"` all
/// compare as text against a pin).
fn scalar(value: &Yaml) -> Option<String> {
    match value {
        Yaml::String(text) | Yaml::Real(text) => Some(text.clone()),
        Yaml::Integer(number) => Some(number.to_string()),
        Yaml::Boolean(flag) => Some(flag.to_string()),
        _ => None,
    }
}

/// A list of strings, accepting the scalar shorthand (`needs: build`) and
/// treating an absent key as empty.
fn string_list(value: &Yaml) -> Option<Vec<&str>> {
    match value {
        Yaml::BadValue => Some(Vec::new()),
        Yaml::String(text) => Some(vec![text.as_str()]),
        Yaml::Array(items) => items.iter().map(text).collect(),
        _ => None,
    }
}

/// Whether the mapping `value` is exactly `expected` (an absent mapping
/// equals an empty one).
fn mapping_is(value: &Yaml, expected: &[(&str, &str)]) -> bool {
    let Some(actual) = (match value {
        Yaml::BadValue => Some(Vec::new()),
        Yaml::Hash(hash) => hash
            .iter()
            .map(|(key, value)| Some((text(key)?.to_owned(), scalar(value)?)))
            .collect::<Option<Vec<_>>>(),
        _ => None,
    }) else {
        return false;
    };
    let actual: BTreeMap<String, String> = actual.into_iter().collect();
    let expected: BTreeMap<String, String> = expected
        .iter()
        .map(|(key, value)| ((*key).to_owned(), (*value).to_owned()))
        .collect();
    actual.len() == expected.len() && actual == expected
}

/// Job-level checks: runner, timeout, `needs`, condition, blocking,
/// checkout layout and the compiler matrix.
fn pinned_job(workflow: &Workflow, job: &Job<'_>, pin: &JobPin, findings: &mut Vec<Finding>) {
    let mut fail = |message: String| findings.push(workflow.finding(&job.path, message));
    let label = format!("job {}", job.id);
    if text(&job.yaml["runs-on"]) != Some(pin.runs_on) {
        fail(format!(
            "{label} must run on {} (the receipt checkout layout and toolchain it was proven on)",
            pin.runs_on
        ));
    }
    if job.yaml["timeout-minutes"].as_i64() != Some(pin.timeout) {
        fail(format!(
            "{label} must reserve exactly timeout-minutes: {}",
            pin.timeout
        ));
    }
    if string_list(&job.yaml["needs"]).as_deref() != Some(pin.needs) {
        fail(format!("{label} must have exactly needs: {:?}", pin.needs));
    }
    let condition = &job.yaml["if"];
    if pin.needs.is_empty() {
        if !condition.is_badvalue() {
            fail(format!(
                "{label} is required and cannot be conditionally skipped"
            ));
        }
    } else if text(condition) != Some(NOT_CANCELLED) {
        fail(format!(
            "{label} has needs, so it must use `if: {NOT_CANCELLED}` to run after upstream failures unless cancelled"
        ));
    }
    if !job.yaml["continue-on-error"].is_badvalue() {
        fail(format!(
            "{label} is required and must be blocking (no continue-on-error)"
        ));
    }
    let checkouts: Vec<&Yaml> = job
        .steps()
        .iter()
        .filter(|step| text(&step["uses"]) == Some("actions/checkout@v6"))
        .collect();
    if checkouts.len() != 1 {
        fail(format!(
            "{label} must use exactly one default actions/checkout@v6"
        ));
    }
    for checkout in checkouts {
        if !checkout["with"]["ref"].is_badvalue() {
            fail(format!(
                "{label} checkout cannot replace the event source revision (ref)"
            ));
        }
        if ["path", "repository"]
            .iter()
            .any(|key| !checkout["with"][*key].is_badvalue())
        {
            fail(format!(
                "{label} must preserve the default receipt checkout layout (no path or repository)"
            ));
        }
    }
    let strategy = &job.yaml["strategy"];
    if pin.matrix {
        let compilers: Option<Vec<&str>> = strategy["matrix"]["compiler"]
            .as_vec()
            .and_then(|items| items.iter().map(text).collect());
        if compilers.as_deref() != Some(&COMPILERS[..]) {
            fail(format!(
                "{label} is missing the exact required matrix compiler: [msvc, clang-cl]"
            ));
        }
        if strategy["fail-fast"].as_bool() != Some(false) {
            fail(format!("{label} matrix must keep fail-fast: false"));
        }
        if !strategy["matrix"]["exclude"].is_badvalue()
            || !strategy["matrix"]["include"].is_badvalue()
        {
            fail(format!(
                "{label} matrix cannot exclude or add executions (no exclude or include)"
            ));
        }
    } else if !strategy.is_badvalue() {
        fail(format!("{label} cannot run on a matrix"));
    }
}

/// Step-level checks: each pinned step exactly once, exactly as pinned, in
/// the pinned order.
fn pinned_steps(workflow: &Workflow, job: &Job<'_>, pin: &JobPin, findings: &mut Vec<Finding>) {
    let steps = job.steps();
    let mut previous: Option<(usize, &str)> = None;
    for step_pin in pin.steps {
        let label = format!("job {}: step {:?}", job.id, step_pin.name);
        let matches = job.find(|step| text(&step["name"]) == Some(step_pin.name));
        let [index] = matches.as_slice() else {
            findings.push(workflow.finding(
                &job.path,
                format!(
                    "{label} must appear exactly once (found {}); it is a pinned gate step",
                    matches.len()
                ),
            ));
            continue;
        };
        let index = *index;
        let step = &steps[index];
        let mut fail =
            |message: String| findings.push(workflow.finding(&job.step_path(index), message));
        match step_pin.action {
            Action::Run(command) => {
                let actual = text(&step["run"]).map(|run| run.replace("\r\n", "\n"));
                if actual.as_deref().map(str::trim_end) != Some(command) {
                    fail(format!("{label} must run exactly `{command}`"));
                }
            }
            Action::Uses(action) => {
                if text(&step["uses"]) != Some(action) {
                    fail(format!("{label} must use exactly {action}"));
                }
            }
        }
        if text(&step["if"]) != step_pin.condition {
            fail(match step_pin.condition {
                Some(condition) => format!("{label} must use exactly `if: {condition}`"),
                None => format!("{label} is required and cannot be conditionally skipped"),
            });
        }
        if !mapping_is(&step["with"], step_pin.with) {
            fail(format!(
                "{label} must have exactly with: {:?}",
                step_pin.with
            ));
        }
        if !mapping_is(&step["env"], step_pin.env) {
            fail(format!("{label} must have exactly env: {:?}", step_pin.env));
        }
        if step["timeout-minutes"].as_i64() != step_pin.timeout {
            fail(format!(
                "{label} must have timeout-minutes: {:?}",
                step_pin.timeout
            ));
        }
        let allowed = [
            "name",
            "run",
            "uses",
            "if",
            "with",
            "env",
            "timeout-minutes",
        ];
        if let Some(hash) = step.as_hash() {
            for key in hash.keys() {
                let key = text(key).unwrap_or("?");
                if !allowed.contains(&key) {
                    fail(format!(
                        "{label} cannot set `{key}` (it must stay blocking and exactly as pinned)"
                    ));
                }
            }
        }
        if let Some((before, name)) = previous
            && index < before
        {
            fail(format!("{label} must come after step {name:?}"));
        }
        previous = Some((index, step_pin.name));
    }
}

/// Every required (participant, instance) has its run step, and every run
/// step runs a required participant.
fn denominator(
    workflows: &BTreeMap<&str, Workflow>,
    required: &BTreeSet<ExecutionKey>,
    findings: &mut Vec<Finding>,
) {
    let mut instances: BTreeMap<&str, BTreeSet<&str>> = BTreeMap::new();
    for key in required {
        instances
            .entry(key.participant_id.as_str())
            .or_default()
            .insert(key.instance_id.as_str());
    }
    for (participant, required_instances) in &instances {
        if !RUN_STEPS.iter().any(|(id, ..)| id == participant) {
            findings.push(Finding {
                path: CONSUMER_OBLIGATIONS.to_owned(),
                line: 1,
                rule: RULE,
                message: format!(
                    "participant {participant} is required on {required_instances:?} but has no CI `conformance run` step"
                ),
            });
        }
    }
    for (participant, file, job_id, name, matrix) in RUN_STEPS {
        let Some(workflow) = workflows.get(file) else {
            continue;
        };
        let Some(job) = workflow.yaml["jobs"][*job_id].as_hash().map(|_| Job {
            id: job_id,
            path: format!("/jobs/{job_id}"),
            yaml: &workflow.yaml["jobs"][*job_id],
        }) else {
            continue;
        };
        // A missing step is already reported by the pinned-step check.
        let path = match job
            .find(|step| text(&step["name"]) == Some(*name))
            .as_slice()
        {
            [index] => job.step_path(*index),
            _ => job.path.clone(),
        };
        let runs: BTreeSet<&str> = if *matrix {
            MATRIX_INSTANCES.into()
        } else {
            [*participant].into()
        };
        match instances.get(participant) {
            None => findings.push(workflow.finding(
                &path,
                format!(
                    "step {name:?} runs participant {participant}, but no family requires {participant}, so `conformance run` would fail"
                ),
            )),
            Some(required_instances) if *required_instances != runs => {
                findings.push(workflow.finding(
                    &path,
                    format!(
                        "{participant} is required on instances {required_instances:?}, but step {name:?} runs exactly {runs:?}; the catalogs must require it on both compilers"
                    ),
                ));
            }
            Some(_) => {}
        }
    }
}

/// `ci-binding-compliance.yml`: the reusable participant workflows the
/// verdict aggregates.
fn full_aggregation(
    root: &RepoRoot,
    workflow: &Workflow,
    findings: &mut Vec<Finding>,
) -> Result<()> {
    for (job_id, callee) in [("rust", CI_RUST), ("native", CI_CPP)] {
        let Some(job) = workflow.job(job_id, findings) else {
            continue;
        };
        let mut fail = |message: String| {
            findings.push(workflow.finding(&job.path, format!("full aggregation: {message}")))
        };
        if text(&job.yaml["uses"]) != Some(&format!("./{callee}")) {
            fail(format!(
                "job {job_id} must be the same-revision reusable workflow ./{callee}"
            ));
        }
        if ["if", "continue-on-error", "needs"]
            .iter()
            .any(|key| !job.yaml[*key].is_badvalue())
        {
            fail(format!(
                "job {job_id} cannot skip a required reusable job (no if, continue-on-error or needs)"
            ));
        }
        let callee_text = match std::fs::read_to_string(root.join(callee)) {
            Ok(text) => Some(text),
            Err(error) if error.kind() == ErrorKind::NotFound => None,
            Err(error) => return Err(error).with_context(|| format!("reading {callee}")),
        };
        let callable = callee_text
            .and_then(|text| YamlLoader::load_from_str(&text).ok())
            .and_then(|docs| docs.into_iter().next())
            .is_some_and(|doc| {
                doc["on"]
                    .as_hash()
                    .is_some_and(|on| on.contains_key(&Yaml::String("workflow_call".into())))
            });
        if !callable {
            fail(format!(
                "{callee} must declare `on: workflow_call` to be a full aggregation participant"
            ));
        }
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
        let mut fail = |path: &str, message: &str| {
            findings.push(workflow.finding(path, format!("Corrosion source: {message}")))
        };
        match fetch
            .find(|step| text(&step["name"]) == Some("Archive verified Corrosion v0.6.1 source"))
            .as_slice()
        {
            [index] => {
                let run = text(&fetch.steps()[*index]["run"]).unwrap_or_default();
                if !archive_markers.iter().all(|marker| run.contains(marker)) {
                    fail(
                        &fetch.step_path(*index),
                        "the source must be pinned to its revision and archived once",
                    );
                }
            }
            _ => fail(
                &fetch.path,
                "job corrosion-source must archive the verified source once",
            ),
        }
        match fetch
            .find(|step| text(&step["name"]) == Some("Upload pinned Corrosion source"))
            .as_slice()
        {
            [index] => {
                let step = &fetch.steps()[*index];
                let ok = text(&step["uses"]) == Some("actions/upload-artifact@v6")
                    && text(&step["with"]["name"]) == Some(CORROSION_ARTIFACT)
                    && text(&step["with"]["path"])
                        == Some("${{ runner.temp }}/classic-corrosion-artifact/")
                    && text(&step["with"]["if-no-files-found"]) == Some("error");
                if !ok {
                    fail(
                        &fetch.step_path(*index),
                        "the archive must be uploaded as corrosion-source-v0.6.1 with if-no-files-found: error",
                    );
                }
            }
            _ => fail(&fetch.path, "the archive must be uploaded once"),
        }
        if !fetch.yaml["continue-on-error"].is_badvalue() || !fetch.yaml["strategy"].is_badvalue() {
            fail(
                &fetch.path,
                "the fetch must be one blocking job (no matrix, no continue-on-error)",
            );
        }
    }

    let verify_markers = [
        CORROSION_REVISION,
        "Get-FileHash -LiteralPath $archivePath -Algorithm SHA256",
        "Expand-Archive -LiteralPath $archivePath",
        "CLASSIC_CORROSION_SOURCE_DIR=$sourceDir",
    ];
    for (job_id, build) in [
        ("cli-tests", "Build and test CLI"),
        ("gui-tests", "Build and test GUI"),
    ] {
        let Some(job) = workflow.job(job_id, findings) else {
            continue;
        };
        let mut fail = |path: &str, message: &str| {
            findings.push(workflow.finding(path, format!("Corrosion source: {message}")))
        };
        let needs: Option<Vec<&str>> = job.yaml["needs"]
            .as_vec()
            .and_then(|items| items.iter().map(text).collect());
        if needs.as_deref() != Some(&["corrosion-source"][..]) {
            fail(
                &job.path,
                "the corrosion-source job must gate each native build (needs: [corrosion-source])",
            );
        }
        match job
            .find(|step| text(&step["name"]) == Some("Download pinned Corrosion source"))
            .as_slice()
        {
            [index] => {
                let step = &job.steps()[*index];
                let with = &step["with"];
                let ok = text(&step["uses"]) == Some("actions/download-artifact@v8")
                    && text(&with["name"]) == Some(CORROSION_ARTIFACT)
                    && text(&with["path"]) == Some("${{ runner.temp }}/classic-corrosion-artifact")
                    && ["run-id", "repository", "github-token", "artifact-ids"]
                        .iter()
                        .all(|key| with[*key].is_badvalue());
                if !ok {
                    fail(
                        &job.step_path(*index),
                        "the source must come from this run's corrosion-source-v0.6.1 artifact",
                    );
                }
            }
            _ => fail(
                &job.path,
                "the source must be downloaded once from this run",
            ),
        }
        let verify = job
            .find(|step| text(&step["name"]) == Some("Verify and extract pinned Corrosion source"));
        let build_index = job
            .steps()
            .iter()
            .position(|step| text(&step["name"]) == Some(build));
        match verify.as_slice() {
            [index] => {
                let run = text(&job.steps()[*index]["run"]).unwrap_or_default();
                if !verify_markers.iter().all(|marker| run.contains(marker)) {
                    fail(
                        &job.step_path(*index),
                        "the verification was weakened (revision, hash, Expand-Archive, CLASSIC_CORROSION_SOURCE_DIR)",
                    );
                }
                if build_index.is_none_or(|build_index| *index > build_index) {
                    fail(
                        &job.step_path(*index),
                        "the source must be verified before the build",
                    );
                }
            }
            _ => fail(&job.path, "the source must be verified and extracted once"),
        }
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
            Ok(_) => {
                return Ok(Err(finding(
                    1,
                    "a workflow must be exactly one YAML document".into(),
                )));
            }
            Err(error) => {
                return Ok(Err(finding(
                    error.marker().line().max(1),
                    format!("invalid YAML: {}", error.info()),
                )));
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
