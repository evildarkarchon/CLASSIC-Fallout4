//! Executable receipt runner for the public Crash Log Scan Run Rust seam.
//!
//! The central launcher supplies an input-only plan and a reserved output path. This test
//! materializes every scenario in a fresh temporary root, executes only the public scan-run
//! contract, renders only through the public presentation crate, and publishes a receipt whose
//! observations can be compared with the independently authored scenario pack.

use classic_config_core::{InspectedYamlDataFile, YamlDataContentIdentity};
use classic_scan_presentation::{
    DisplayLine, DisplaySegment, DisplaySeverity, RecoveryPrompt, render_event,
    render_local_ignore_recovery, render_resume_error, render_run_result,
};
use classic_scanlog_core::CrashLogScanFacts;
use classic_scanlog_core::scan_run::contract;
use classic_scanlog_core::scan_run::{
    StandardCrashLogScanSource, StandardUnsolvedLogsIntent, TargetedCrashLogScanSource,
};
use classic_shared_core::{GameId, get_runtime};
use classic_vocabulary::Vocabulary;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::BTreeMap;
use std::error::Error;
use std::ffi::OsString;
use std::fs::{self, File};
use std::io::{self, Write};
use std::path::{Component, Path, PathBuf};
use std::thread;
use std::time::{Duration, Instant};
use tempfile::{NamedTempFile, tempdir};

const RUN_PLAN_ENV: &str = "CLASSIC_CONFORMANCE_RUN_PLAN";
const OUTPUT_ENV: &str = "CLASSIC_CONFORMANCE_OUTPUT";
const RUNNER_ID: &str = "classic-rust-scan-run-conformance";

type RunnerResult<T> = Result<T, Box<dyn Error + Send + Sync>>;

/// Input-only plan materialized and authenticated by the central conformance launcher.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RunPlan {
    schema_version: u64,
    family_id: String,
    family_version: u64,
    expectation_digest: String,
    fixtures: BTreeMap<String, PathBuf>,
    participant: Participant,
    invocation: Invocation,
    scenarios: Vec<ScenarioPlan>,
}

/// Participant identity copied byte-for-byte from the authenticated run plan.
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct Participant {
    id: String,
    role: String,
    execution_instance_id: String,
}

/// Invocation identity copied byte-for-byte from the authenticated run plan.
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct Invocation {
    id: String,
    source_identity: String,
    run_plan_digest: String,
}

/// One scenario and the capabilities the resulting observation covers.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ScenarioPlan {
    id: String,
    capability_ids: Vec<String>,
    input: ScenarioInput,
}

/// Public scan-run request facts authored by the frozen base pack.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ScenarioInput {
    #[serde(default)]
    observation_profile: ObservationProfile,
    installation_data: Vec<FixturePlacement>,
    game: GameInput,
    game_version: String,
    show_formid_values: bool,
    simplify_logs: bool,
    formid_database_paths: Vec<String>,
    max_concurrent: usize,
    intent: ScanIntentInput,
    #[serde(default)]
    log_inputs: Vec<FixturePlacement>,
    #[serde(default)]
    targeted_inputs: Vec<TargetedInput>,
    #[serde(default)]
    directory_inputs: Vec<PathInput>,
    #[serde(default)]
    observed_paths: Vec<PathInput>,
    #[serde(default)]
    forbidden_effect_paths: Vec<String>,
    #[serde(default)]
    local_ignore_padding_bytes: usize,
    execution_flow: Option<ExecutionFlowInput>,
    continuation_flow: Option<ContinuationFlowInput>,
    standard_source: Option<StandardSourceInput>,
    unsolved_logs: Option<UnsolvedLogsInput>,
    unsolved_logs_path: Option<PathInput>,
}

/// Observation projection selected by the input-only plan.
#[derive(Clone, Copy, Debug, Default, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "kebab-case")]
enum ObservationProfile {
    #[default]
    Base,
    Failure,
    LocalIgnore,
    Lifecycle,
}

/// Input-only controls for one initial scan execution boundary.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ExecutionFlowInput {
    cancellation: ExecutionCancellationInput,
    observer_failure: Option<ObserverFailureInput>,
}

/// Public cancellation timing admitted by the current lifecycle slice.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "kebab-case")]
enum ExecutionCancellationInput {
    BeforeDiscovery,
    OnFirstLogQueued,
    OnFirstLogStarted,
    OnObserverFailure,
}

/// One deterministic downstream observer delivery failure requested by the plan.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ObserverFailureInput {
    event_kind: ObserverFailureEventInput,
    message: String,
}

/// Serialized event boundary at which the test adapter rejects delivery.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "snake_case")]
enum ObserverFailureEventInput {
    DiscoveryCompleted,
}

/// Game vocabulary admitted by the public base-scenario runner.
#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(rename_all = "lowercase")]
enum GameInput {
    Fallout4,
    Fallout4Vr,
}

/// Standard or Targeted request tag admitted by the frozen scenario family.
#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(rename_all = "lowercase")]
enum ScanIntentInput {
    Standard,
    Targeted,
}

/// Standard-only movement policy admitted by the base happy path.
#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(rename_all = "kebab-case")]
enum UnsolvedLogsInput {
    LeaveInPlace,
    MoveToCustom,
}

/// A declared fixture copied to one scenario-root-relative destination.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct FixturePlacement {
    fixture_ref: String,
    path: String,
}

/// One Targeted caller input, optionally backed by a declared fixture.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct TargetedInput {
    fixture_ref: Option<String>,
    path: String,
}

/// Input-only instructions for claiming and replaying one retained continuation.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ContinuationFlowInput {
    action: ContinuationActionInput,
    #[serde(default)]
    post_pause_data: Vec<FixturePlacement>,
    #[serde(default)]
    replays: Vec<ContinuationActionInput>,
    cancellation: Option<CancellationBoundaryInput>,
}

/// Public cancellation boundary exercised around one retained reset attempt.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "kebab-case")]
enum CancellationBoundaryInput {
    BeforeResume,
    AfterResetCriticalSection,
}

/// One public continuation operation and its decision when the operation is Resume.
#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ContinuationActionInput {
    operation: ContinuationOperationInput,
    decision: Option<RecoveryDecisionInput>,
}

/// Public operations admitted for a retained scan-run continuation.
#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(rename_all = "kebab-case")]
enum ContinuationOperationInput {
    Resume,
    Abandon,
}

/// Public Local Ignore recovery decisions admitted by the conformance pack.
#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(rename_all = "kebab-case")]
enum RecoveryDecisionInput {
    ProceedWithoutIgnore,
    ResetToDefault,
}

/// Standard discovery roots supplied to the public request constructor.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct StandardSourceInput {
    base_directory: PathInput,
    custom_scan_directory: Option<PathInput>,
    configured_documents_root: Option<PathInput>,
}

/// Canonical JSON path carrier used by scenario input.
#[derive(Debug, Deserialize)]
struct PathInput {
    path: String,
}

/// Publishes one receipt for the centrally materialized input-only run plan.
#[test]
fn writes_scan_run_conformance_receipt() {
    let Some((plan_path, output_path)) = read_runner_paths()
        .expect("the conformance launcher environment should be internally consistent")
    else {
        eprintln!("scan-run conformance launcher variables are absent; receipt run skipped");
        return;
    };
    let cache_root = tempdir().expect("an isolated YAML update cache should be created");
    let result = temp_env::with_vars(
        [
            ("LOCALAPPDATA", Some(cache_root.path())),
            ("XDG_CACHE_HOME", Some(cache_root.path())),
        ],
        || execute_and_publish(&plan_path, &output_path),
    );
    result.expect("the Rust public-seam conformance receipt should be published");
}

/// Reads the only two launcher-controlled environment values accepted by this runner.
fn read_runner_paths() -> RunnerResult<Option<(PathBuf, PathBuf)>> {
    let plan = std::env::var_os(RUN_PLAN_ENV);
    let output = std::env::var_os(OUTPUT_ENV);
    match (plan, output) {
        (None, None) => Ok(None),
        (Some(plan), Some(output)) => Ok(Some((PathBuf::from(plan), PathBuf::from(output)))),
        (Some(_), None) => Err(invalid_data(format!(
            "{OUTPUT_ENV} is required when {RUN_PLAN_ENV} is set"
        ))
        .into()),
        (None, Some(_)) => Err(invalid_data(format!(
            "{RUN_PLAN_ENV} is required when {OUTPUT_ENV} is set"
        ))
        .into()),
    }
}

/// Executes a validated plan and atomically publishes its copied identities and observations.
fn execute_and_publish(plan_path: &Path, output_path: &Path) -> RunnerResult<()> {
    let plan: RunPlan = serde_json::from_reader(File::open(plan_path)?)?;
    validate_plan_header(&plan)?;
    if output_path.exists() {
        return Err(invalid_data(format!(
            "reserved receipt path already exists: {}",
            output_path.display()
        ))
        .into());
    }

    let scenarios = plan
        .scenarios
        .iter()
        .map(|scenario| {
            let observation = execute_scenario(&plan.fixtures, scenario)?;
            Ok(json!({
                "id": scenario.id,
                "executionStatus": "completed",
                "capabilityIds": scenario.capability_ids,
                "observation": observation,
                "failure": null,
            }))
        })
        .collect::<RunnerResult<Vec<_>>>()?;
    let receipt = json!({
        "schemaVersion": 1,
        "familyId": plan.family_id,
        "familyVersion": plan.family_version,
        "expectationDigest": plan.expectation_digest,
        "invocation": plan.invocation,
        "participant": plan.participant,
        "runner": {
            "id": RUNNER_ID,
            "version": 1,
            "platform": std::env::consts::OS,
            "toolchain": "rust",
        },
        "scenarios": scenarios,
    });
    atomic_write_json(output_path, &receipt)
}

/// Rejects a plan intended for another schema, family, or adapter participant.
fn validate_plan_header(plan: &RunPlan) -> RunnerResult<()> {
    if plan.schema_version != 1
        || plan.family_id != "crash-log-scan-run"
        || plan.family_version != 1
        || plan.participant.id != "rust"
        || plan.participant.role != "semantic-adapter"
    {
        return Err(invalid_data("run plan is not the Rust Crash Log Scan Run v1 plan").into());
    }
    if plan.scenarios.is_empty() {
        return Err(invalid_data("run plan contains no scenarios").into());
    }
    Ok(())
}

/// Materializes and executes one scenario entirely beneath a fresh temporary root.
fn execute_scenario(
    fixtures: &BTreeMap<String, PathBuf>,
    scenario: &ScenarioPlan,
) -> RunnerResult<Value> {
    let scenario_root = tempdir()?;
    materialize_scenario(fixtures, &scenario.input, scenario_root.path())?;
    append_local_ignore_padding(&scenario.input, scenario_root.path())?;
    let request = build_request(&scenario.input, scenario_root.path())?;
    let cancellation = contract::Cancellation::new();
    if let Some(flow) = &scenario.input.execution_flow {
        if scenario.input.observation_profile != ObservationProfile::Lifecycle {
            return Err(invalid_data("executionFlow requires lifecycle observation").into());
        }
        if flow.cancellation == ExecutionCancellationInput::OnObserverFailure
            && flow.observer_failure.is_none()
        {
            return Err(
                invalid_data("on-observer-failure cancellation requires observerFailure").into(),
            );
        }
        if flow.cancellation != ExecutionCancellationInput::OnObserverFailure
            && flow.observer_failure.is_some()
        {
            return Err(
                invalid_data("observerFailure requires on-observer-failure cancellation").into(),
            );
        }
        if flow
            .observer_failure
            .as_ref()
            .is_some_and(|failure| failure.message.trim().is_empty())
        {
            return Err(invalid_data("observerFailure message is empty").into());
        }
        if flow.cancellation == ExecutionCancellationInput::BeforeDiscovery {
            cancellation.cancel();
        }
    } else if scenario.input.observation_profile == ObservationProfile::Lifecycle {
        return Err(invalid_data("lifecycle observation requires executionFlow").into());
    }
    let mut events = Vec::new();
    let mut observer_failure = None;
    let mut delivery_failed = false;
    let observer_cancellation = cancellation.clone();
    let cancel_on_first_queued = scenario
        .input
        .execution_flow
        .as_ref()
        .is_some_and(|flow| flow.cancellation == ExecutionCancellationInput::OnFirstLogQueued);
    let cancel_on_first_started = scenario
        .input
        .execution_flow
        .as_ref()
        .is_some_and(|flow| flow.cancellation == ExecutionCancellationInput::OnFirstLogStarted);
    let fail_on_discovery = scenario
        .input
        .execution_flow
        .as_ref()
        .and_then(|flow| flow.observer_failure.as_ref())
        .is_some_and(|failure| failure.event_kind == ObserverFailureEventInput::DiscoveryCompleted);
    let execution = {
        let mut observer = |event| {
            if delivery_failed {
                return;
            }
            if fail_on_discovery && matches!(&event, contract::Event::DiscoveryCompleted(_)) {
                events.push(event);
                // The Rust observer is infallible, so model a downstream sink refusal by
                // ending delivery and cancelling future work at the same public boundary.
                observer_failure = Some(json!({
                    "kind": "observer_delivery_failure",
                    "eventKind": "discovery_completed",
                    "messageNonEmpty": true,
                }));
                delivery_failed = true;
                observer_cancellation.cancel();
                return;
            }
            if cancel_on_first_queued && matches!(&event, contract::Event::LogQueued(_)) {
                observer_cancellation.cancel();
            }
            if cancel_on_first_started
                && matches!(
                    &event,
                    contract::Event::LogStarted(log) if log.discovery_index == 0
                )
            {
                observer_cancellation.cancel();
            }
            events.push(event);
        };
        get_runtime().block_on(contract::execute(
            request,
            &cancellation,
            Some(&mut observer),
        ))
    };
    let mut result = match execution {
        Ok(result) => result,
        Err(error) if scenario.input.observation_profile == ObservationProfile::Failure => {
            return project_failure_infrastructure_observation(
                scenario_root.path(),
                &scenario.input,
                &error,
            );
        }
        Err(error) => return Err(error.into()),
    };
    if let Some(flow) = &scenario.input.continuation_flow {
        return execute_continuation_flow(
            fixtures,
            &scenario.input,
            scenario_root.path(),
            &cancellation,
            &mut result,
            &events,
            flow,
        );
    }
    match scenario.input.observation_profile {
        ObservationProfile::Base => project_observation(scenario_root.path(), &result, &events),
        ObservationProfile::Failure => {
            project_failure_result_observation(scenario_root.path(), &scenario.input, &result)
        }
        ObservationProfile::LocalIgnore => project_local_ignore_observation(
            scenario_root.path(),
            &scenario.input,
            &result,
            &events,
        ),
        ObservationProfile::Lifecycle => project_lifecycle_observation(
            scenario_root.path(),
            &scenario.input,
            &result,
            &events,
            &cancellation,
            observer_failure,
        ),
    }
}

/// Claims one paused continuation, applies after-pause mutations, then proves one-shot replay.
fn execute_continuation_flow(
    fixtures: &BTreeMap<String, PathBuf>,
    input: &ScenarioInput,
    root: &Path,
    cancellation: &contract::Cancellation,
    initial_result: &mut contract::RunResult,
    initial_events: &[contract::Event],
    flow: &ContinuationFlowInput,
) -> RunnerResult<Value> {
    if input.observation_profile != ObservationProfile::LocalIgnore {
        return Err(
            invalid_data("continuationFlow requires the local-ignore observation profile").into(),
        );
    }
    validate_continuation_action(flow.action)?;
    for replay in &flow.replays {
        validate_continuation_action(*replay)?;
    }
    let prompt = render_local_ignore_recovery(initial_result.installed_yaml_data.as_ref());
    let initial =
        project_local_ignore_phase(root, initial_result, initial_events, true, Some(&prompt))?;
    let continuation = initial_result
        .continuation
        .take()
        .ok_or_else(|| invalid_data("continuationFlow initial result has no continuation"))?;
    materialize_placements(fixtures, &flow.post_pause_data, root)?;

    if flow.cancellation == Some(CancellationBoundaryInput::BeforeResume) {
        cancellation.cancel();
    }
    let cancellation_worker =
        if flow.cancellation == Some(CancellationBoundaryInput::AfterResetCriticalSection) {
            Some(cancel_after_reset_entry(root, cancellation.clone()))
        } else {
            None
        };
    let cancelled_before_terminal = cancellation.is_cancelled();
    let mut terminal_events = Vec::new();
    let terminal_outcome = get_runtime().block_on(run_continuation_action(
        &continuation,
        flow.action,
        cancellation,
        Some(&mut |event| terminal_events.push(event)),
    ));
    if let Some(worker) = cancellation_worker {
        let observed = worker
            .join()
            .map_err(|_| invalid_data("reset-entry cancellation worker panicked"))?;
        if !observed {
            return Err(invalid_data(
                "reset-entry cancellation boundary was not observed within five seconds",
            )
            .into());
        }
    }
    let cancelled_after_terminal = cancellation.is_cancelled();
    let (terminal_result, terminal, terminal_error) = match terminal_outcome {
        Ok(result) => {
            let terminal =
                project_local_ignore_phase(root, &result, &terminal_events, false, None)?;
            (Some(result), Some(terminal), None)
        }
        Err(error) => (
            None,
            None,
            Some(project_terminal_error(root, &error, &terminal_events)?),
        ),
    };

    let replays = flow
        .replays
        .iter()
        .copied()
        .map(|action| {
            match get_runtime().block_on(run_continuation_action(
                &continuation,
                action,
                cancellation,
                None,
            )) {
                Ok(_) => Err(
                    invalid_data("a replayed continuation action unexpectedly succeeded").into(),
                ),
                Err(error) => Ok(project_replay_error(action, &error)),
            }
        })
        .collect::<RunnerResult<Vec<_>>>()?;

    Ok(json!({
        "initial": initial,
        "terminal": terminal,
        "terminalError": terminal_error,
        "replays": replays,
        "cancellation": {
            "beforeTerminal": cancelled_before_terminal,
            "afterTerminal": cancelled_after_terminal,
            "afterReplays": cancellation.is_cancelled(),
        },
        "durableEffects": project_local_ignore_effects(root, input, terminal_result.as_ref())?,
    }))
}

/// Requests cancellation only after the public reset lock proves critical-section entry.
fn cancel_after_reset_entry(
    root: &Path,
    cancellation: contract::Cancellation,
) -> thread::JoinHandle<bool> {
    let reset_lock = root.join(".classic-local-ignore-reset.lock");
    thread::spawn(move || {
        let deadline = Instant::now() + Duration::from_secs(5);
        while !reset_lock.exists() && Instant::now() < deadline {
            thread::sleep(Duration::from_millis(1));
        }
        if !reset_lock.exists() {
            return false;
        }
        cancellation.cancel();
        true
    })
}

/// Rejects structurally invalid operation/decision pairs before spending a continuation.
fn validate_continuation_action(action: ContinuationActionInput) -> RunnerResult<()> {
    match (action.operation, action.decision) {
        (ContinuationOperationInput::Resume, Some(_))
        | (ContinuationOperationInput::Abandon, None) => Ok(()),
        (ContinuationOperationInput::Resume, None) => {
            Err(invalid_data("Resume continuation action has no recovery decision").into())
        }
        (ContinuationOperationInput::Abandon, Some(_)) => Err(invalid_data(
            "Abandon continuation action must not have a recovery decision",
        )
        .into()),
    }
}

/// Invokes one public continuation action without inferring intent from a scenario identifier.
async fn run_continuation_action(
    continuation: &contract::CrashLogScanRunContinuation,
    action: ContinuationActionInput,
    cancellation: &contract::Cancellation,
    observer: Option<&mut dyn contract::Observer>,
) -> Result<contract::RunResult, contract::ResumeError> {
    match action.operation {
        ContinuationOperationInput::Resume => {
            let decision = action
                .decision
                .expect("continuation action was validated before execution");
            continuation
                .resume(decision.into(), cancellation, observer)
                .await
        }
        ContinuationOperationInput::Abandon => {
            debug_assert!(action.decision.is_none());
            continuation.abandon(cancellation, observer).await
        }
    }
}

impl From<RecoveryDecisionInput> for contract::LocalIgnoreRecoveryDecision {
    fn from(value: RecoveryDecisionInput) -> Self {
        match value {
            RecoveryDecisionInput::ProceedWithoutIgnore => Self::ProceedWithoutIgnore,
            RecoveryDecisionInput::ResetToDefault => Self::ResetToDefault,
        }
    }
}

/// Copies every declared input fixture without exposing the pack's expected observations.
fn materialize_scenario(
    fixtures: &BTreeMap<String, PathBuf>,
    input: &ScenarioInput,
    root: &Path,
) -> RunnerResult<()> {
    materialize_placements(fixtures, &input.installation_data, root)?;
    materialize_placements(fixtures, &input.log_inputs, root)?;
    for targeted in &input.targeted_inputs {
        if let Some(fixture_ref) = &targeted.fixture_ref {
            copy_fixture(fixtures, fixture_ref, root, &targeted.path)?;
        }
    }
    materialize_directories(&input.directory_inputs, root)?;
    Ok(())
}

/// Creates every declared directory input beneath the isolated scenario root.
fn materialize_directories(directories: &[PathInput], root: &Path) -> RunnerResult<()> {
    for directory in directories {
        fs::create_dir_all(join_relative(root, &directory.path)?)?;
    }
    Ok(())
}

/// Appends deterministic malformed bytes used to hold reset inside its critical section.
fn append_local_ignore_padding(input: &ScenarioInput, root: &Path) -> RunnerResult<()> {
    if input.local_ignore_padding_bytes == 0 {
        return Ok(());
    }
    let path = root.join("CLASSIC Data/CLASSIC Ignore.yaml");
    let mut file = File::options().append(true).open(&path)?;
    let chunk = [b'x'; 64 * 1024];
    let mut remaining = input.local_ignore_padding_bytes;
    while remaining > 0 {
        let count = remaining.min(chunk.len());
        file.write_all(&chunk[..count])?;
        remaining -= count;
    }
    Ok(())
}

/// Copies an ordered set of declared fixtures beneath one isolated scenario root.
fn materialize_placements(
    fixtures: &BTreeMap<String, PathBuf>,
    placements: &[FixturePlacement],
    root: &Path,
) -> RunnerResult<()> {
    for placement in placements {
        copy_fixture(fixtures, &placement.fixture_ref, root, &placement.path)?;
    }
    Ok(())
}

/// Copies one repository-owned fixture to a validated relative destination.
fn copy_fixture(
    fixtures: &BTreeMap<String, PathBuf>,
    fixture_ref: &str,
    root: &Path,
    relative: &str,
) -> RunnerResult<()> {
    let source = fixtures
        .get(fixture_ref)
        .ok_or_else(|| invalid_data(format!("unknown fixture reference {fixture_ref}")))?;
    if !source.is_file() {
        return Err(invalid_data(format!("fixture is not a file: {}", source.display())).into());
    }
    let destination = join_relative(root, relative)?;
    let parent = destination
        .parent()
        .ok_or_else(|| invalid_data("fixture destination has no parent"))?;
    fs::create_dir_all(parent)?;
    fs::copy(source, destination)?;
    Ok(())
}

/// Builds the public Standard or Targeted request without using test hooks.
fn build_request(input: &ScenarioInput, root: &Path) -> RunnerResult<contract::Request> {
    let game = match input.game {
        GameInput::Fallout4 => GameId::Fallout4,
        GameInput::Fallout4Vr => GameId::Fallout4VR,
    };
    let scan_facts = CrashLogScanFacts {
        formid_database_paths: input
            .formid_database_paths
            .iter()
            .map(PathBuf::from)
            .collect(),
        unsolved_logs_destination: None,
    };
    let configuration = contract::Configuration {
        installation_root: root.to_path_buf(),
        game,
        game_version: input.game_version.clone(),
        options: contract::Options::new(input.show_formid_values, input.simplify_logs),
        scan_facts,
        max_concurrent: Some(input.max_concurrent),
    };
    match input.intent {
        ScanIntentInput::Standard => {
            let source = input
                .standard_source
                .as_ref()
                .ok_or_else(|| invalid_data("Standard scenario has no standardSource"))?;
            let unsolved_logs = match input.unsolved_logs {
                Some(UnsolvedLogsInput::LeaveInPlace) => StandardUnsolvedLogsIntent::LeaveInPlace,
                Some(UnsolvedLogsInput::MoveToCustom) => {
                    let destination = input.unsolved_logs_path.as_ref().ok_or_else(|| {
                        invalid_data("move-to-custom requires an unsolvedLogsPath")
                    })?;
                    StandardUnsolvedLogsIntent::MoveToCustom(join_relative(
                        root,
                        &destination.path,
                    )?)
                }
                None => {
                    return Err(invalid_data("Standard scenario has no unsolvedLogs intent").into());
                }
            };
            Ok(contract::Request::standard(
                configuration,
                StandardCrashLogScanSource {
                    base_directory: join_relative(root, &source.base_directory.path)?,
                    custom_scan_directory: optional_path(
                        root,
                        source.custom_scan_directory.as_ref(),
                    )?,
                    configured_documents_root: optional_path(
                        root,
                        source.configured_documents_root.as_ref(),
                    )?,
                },
                unsolved_logs,
            ))
        }
        ScanIntentInput::Targeted => Ok(contract::Request::targeted(
            configuration,
            TargetedCrashLogScanSource {
                inputs: input
                    .targeted_inputs
                    .iter()
                    .map(|targeted| join_relative(root, &targeted.path))
                    .collect::<RunnerResult<Vec<_>>>()?,
            },
        )),
    }
}

/// Resolves an optional scenario path beneath its fresh root.
fn optional_path(root: &Path, value: Option<&PathInput>) -> RunnerResult<Option<PathBuf>> {
    value
        .map(|carrier| join_relative(root, &carrier.path))
        .transpose()
}

/// Joins a portable plan path while rejecting absolute paths and traversal.
fn join_relative(root: &Path, relative: &str) -> RunnerResult<PathBuf> {
    if relative.is_empty() {
        return Err(invalid_data("scenario path is empty").into());
    }
    let mut destination = root.to_path_buf();
    for component in Path::new(relative).components() {
        match component {
            Component::Normal(part) => destination.push(part),
            _ => {
                return Err(invalid_data(format!(
                    "scenario path is not a clean relative path: {relative}"
                ))
                .into());
            }
        }
    }
    Ok(destination)
}

/// Projects a public infrastructure failure as a completed semantic observation.
fn project_failure_infrastructure_observation(
    root: &Path,
    input: &ScenarioInput,
    error: &contract::InfrastructureError,
) -> RunnerResult<Value> {
    Ok(json!({
        "infrastructureError": {
            "stage": error.stage.as_str(),
            "messageNonEmpty": !error.message.is_empty(),
            "path": error.path.as_ref().map(|path| path_carrier(root, path)).transpose()?,
        },
        "durableEffects": project_observed_effects(root, &input.observed_paths)?,
    }))
}

/// Projects a completed run whose stable evidence is its per-log structured failures.
fn project_failure_result_observation(
    root: &Path,
    input: &ScenarioInput,
    result: &contract::RunResult,
) -> RunnerResult<Value> {
    let logs = result
        .logs
        .iter()
        .map(|log| project_failure_log(root, log))
        .collect::<RunnerResult<Vec<_>>>()?;
    Ok(json!({
        "status": result.status.as_str(),
        "logs": logs,
        "durableEffects": project_observed_effects(root, &input.observed_paths)?,
    }))
}

/// Projects one failed log without retaining unstable diagnostic prose.
fn project_failure_log(root: &Path, log: &contract::LogResult) -> RunnerResult<Value> {
    let failures = log
        .failures
        .iter()
        .map(|failure| {
            json!({
                "stage": failure.stage.as_str(),
                "messageNonEmpty": !failure.message.is_empty(),
            })
        })
        .collect::<Vec<_>>();
    Ok(json!({
        "discoveryIndex": log.discovery_index,
        "crashLog": path_carrier(root, &log.crash_log)?,
        "autoscanReport": log.autoscan_report.as_ref().map(|path| path_carrier(root, path)).transpose()?,
        "disposition": log.disposition.as_str(),
        "failures": failures,
        "messageNonEmpty": log.message.as_ref().is_some_and(|message| !message.is_empty()),
        "movedToUnsolvedLogs": log.moved_to_unsolved_logs,
    }))
}

/// Classifies every declared durable-effect path in plan order.
fn project_observed_effects(root: &Path, paths: &[PathInput]) -> RunnerResult<Vec<Value>> {
    paths
        .iter()
        .map(|path| project_observed_effect(root, path))
        .collect()
}

/// Projects one observed path as a regular file, directory, other entry, or absence.
fn project_observed_effect(root: &Path, input: &PathInput) -> RunnerResult<Value> {
    let path = join_relative(root, &input.path)?;
    let kind = match fs::metadata(&path) {
        Ok(metadata) if metadata.is_file() => "file",
        Ok(metadata) if metadata.is_dir() => "directory",
        Ok(_) => "other",
        Err(error) if error.kind() == io::ErrorKind::NotFound => "missing",
        Err(error) => return Err(error.into()),
    };
    Ok(json!({
        "path": relative_path(root, &path)?,
        "kind": kind,
    }))
}

/// Projects the complete terminal result, deterministic traces, rendering, and durable effects.
fn project_observation(
    root: &Path,
    result: &contract::RunResult,
    events: &[contract::Event],
) -> RunnerResult<Value> {
    if result.setup.is_some() {
        return Err(invalid_data("non-FCX base scenario unexpectedly returned setup data").into());
    }
    let discovery = result
        .discovery
        .as_ref()
        .map(|value| project_discovery(root, value))
        .transpose()?;
    let installed_yaml_data = result
        .installed_yaml_data
        .as_ref()
        .map(|value| project_installed_yaml_data(root, value))
        .transpose()?;
    let logs = result
        .logs
        .iter()
        .map(|log| project_log(root, log))
        .collect::<RunnerResult<Vec<_>>>()?;
    let event_observation = project_events(root, result, events)?;
    let display_content = project_display(root, &render_run_result(result))?;
    let reports = result
        .logs
        .iter()
        .filter_map(|log| log.autoscan_report.as_ref())
        .map(|path| project_report_effect(root, path))
        .collect::<RunnerResult<Vec<_>>>()?;
    let unsolved_logs = root.join("Unsolved Logs");

    Ok(json!({
        "run": {
            "status": result.status.as_str(),
            "message": result.message,
            "total": result.total,
            "succeeded": result.succeeded,
            "failed": result.failed,
            "cancelled": result.cancelled,
            "setup": null,
            "effectiveConcurrency": result.effective_concurrency,
        },
        "discovery": discovery,
        "installedYamlData": installed_yaml_data,
        "logs": logs,
        "events": event_observation,
        "displayContent": display_content,
        "durableEffects": {
            "reports": reports,
            "unsolvedLogs": {
                "path": "Unsolved Logs",
                "exists": unsolved_logs.exists(),
            },
        },
    }))
}

/// Projects cancellation lifecycle facts without duplicating happy-path presentation data.
fn project_lifecycle_observation(
    root: &Path,
    input: &ScenarioInput,
    result: &contract::RunResult,
    events: &[contract::Event],
    cancellation: &contract::Cancellation,
    observer_failure: Option<Value>,
) -> RunnerResult<Value> {
    if result.setup.is_some() {
        return Err(invalid_data("lifecycle scenario unexpectedly returned setup data").into());
    }
    let discovery = result
        .discovery
        .as_ref()
        .map(|value| project_discovery(root, value))
        .transpose()?;
    let logs = result
        .logs
        .iter()
        .map(|log| project_log(root, log))
        .collect::<RunnerResult<Vec<_>>>()?;
    Ok(json!({
        "run": {
            "status": result.status.as_str(),
            "message": result.message,
            "total": result.total,
            "succeeded": result.succeeded,
            "failed": result.failed,
            "cancelled": result.cancelled,
            "effectiveConcurrency": result.effective_concurrency,
        },
        "discovery": discovery,
        "logs": logs,
        "events": project_compact_events(result, events)?,
        "observerFailure": observer_failure,
        "cancellation": {
            "requested": cancellation.is_cancelled(),
        },
        "durableEffects": project_lifecycle_effects(root, input, result)?,
    }))
}

/// Observes reports plus every explicitly forbidden lifecycle artifact path.
fn project_lifecycle_effects(
    root: &Path,
    input: &ScenarioInput,
    result: &contract::RunResult,
) -> RunnerResult<Value> {
    let reports = result
        .logs
        .iter()
        .filter_map(|log| log.autoscan_report.as_ref())
        .map(|path| project_report_effect(root, path))
        .collect::<RunnerResult<Vec<_>>>()?;
    let forbidden = input
        .forbidden_effect_paths
        .iter()
        .map(|relative| {
            let path = join_relative(root, relative)?;
            Ok(json!({
                "path": relative_path(root, &path)?,
                "exists": path.exists(),
            }))
        })
        .collect::<RunnerResult<Vec<_>>>()?;
    Ok(json!({"reports": reports, "forbidden": forbidden}))
}

/// Projects the stable Local Ignore facts without path-bearing diagnostic prose.
///
/// Generated and recovery diagnostics embed the temporary root, while reset diagnostics also
/// embed a process-unique backup name. The conformance oracle therefore compares their typed
/// attribution and durable identities instead of nondeterministic prose.
fn project_local_ignore_observation(
    root: &Path,
    input: &ScenarioInput,
    result: &contract::RunResult,
    events: &[contract::Event],
) -> RunnerResult<Value> {
    let mut observation =
        project_local_ignore_phase(root, result, events, result.continuation.is_some(), None)?;
    observation
        .as_object_mut()
        .ok_or_else(|| invalid_data("Local Ignore phase projection is not an object"))?
        .insert(
            "durableEffects".to_string(),
            project_local_ignore_effects(root, input, Some(result))?,
        );
    Ok(observation)
}

/// Projects one initial or terminal Local Ignore result without reading filesystem effects.
fn project_local_ignore_phase(
    root: &Path,
    result: &contract::RunResult,
    events: &[contract::Event],
    continuation_available: bool,
    recovery_prompt: Option<&RecoveryPrompt>,
) -> RunnerResult<Value> {
    if result.setup.is_some() {
        return Err(invalid_data("Local Ignore scenario unexpectedly returned setup data").into());
    }
    let discovery = result
        .discovery
        .as_ref()
        .map(|value| project_discovery(root, value))
        .transpose()?;
    let installed_yaml_data = result
        .installed_yaml_data
        .as_ref()
        .map(|value| project_local_ignore_installed_yaml_data(root, value))
        .transpose()?;
    let logs = result
        .logs
        .iter()
        .map(|log| project_log(root, log))
        .collect::<RunnerResult<Vec<_>>>()?;

    Ok(json!({
        "run": {
            "status": result.status.as_str(),
            "message": result.message,
            "total": result.total,
            "succeeded": result.succeeded,
            "failed": result.failed,
            "cancelled": result.cancelled,
            "effectiveConcurrency": result.effective_concurrency,
        },
        "discovery": discovery,
        "installedYamlData": installed_yaml_data,
        "logs": logs,
        "events": project_compact_events(result, events)?,
        "continuationAvailable": continuation_available,
        "recoveryPrompt": recovery_prompt.map(project_recovery_prompt),
    }))
}

/// Projects the public recovery prompt, including decision labels and availability.
fn project_recovery_prompt(prompt: &RecoveryPrompt) -> Value {
    let decisions = prompt
        .decisions
        .iter()
        .map(|decision| {
            json!({
                "decision": decision.decision.as_str(),
                "label": decision.label,
                "available": decision.available,
            })
        })
        .collect::<Vec<_>>();
    let display_severities = display_severities(&prompt.lines);
    json!({
        "displaySeverities": display_severities,
        "decisions": decisions,
    })
}

/// Projects one typed consumed-continuation replay through the public presentation seam.
fn project_replay_error(action: ContinuationActionInput, error: &contract::ResumeError) -> Value {
    json!({
        "operation": match action.operation {
            ContinuationOperationInput::Resume => "resume",
            ContinuationOperationInput::Abandon => "abandon",
        },
        "decision": action.decision.map(|decision| contract::LocalIgnoreRecoveryDecision::from(decision).as_str()),
        "error": {
            "kind": error.kind().as_str(),
            "message": error.to_string(),
            "displaySeverities": display_severities(&render_resume_error(error)),
        },
    })
}

/// Projects one typed terminal resume rejection without retaining OS-dependent prose.
fn project_terminal_error(
    root: &Path,
    error: &contract::ResumeError,
    events: &[contract::Event],
) -> RunnerResult<Value> {
    if !events.is_empty() {
        return Err(
            invalid_data("terminal resume error unexpectedly emitted observer events").into(),
        );
    }
    let mut path = None;
    let mut stage = None;
    let mut expected_identity = None;
    let mut actual_identity = None;
    let mut backup_path = None;
    let mut malformed_identity = None;
    let mut backup_identity = None;
    let mut replacement_identity = None;
    match error {
        contract::ResumeError::LocalIgnoreResetConflict(conflict) => {
            expected_identity = Some(project_identity(&conflict.expected_identity));
            actual_identity = conflict.actual_identity.as_ref().map(project_identity);
            backup_path = conflict
                .backup_path
                .as_ref()
                .map(|value| path_carrier(root, value))
                .transpose()?;
        }
        contract::ResumeError::LocalIgnoreResetBackupFailure(failure)
        | contract::ResumeError::LocalIgnoreResetReplacementFailure(failure) => {
            path = Some(path_carrier(root, &failure.path)?);
            stage = failure.stage.map(Vocabulary::as_str);
        }
        contract::ResumeError::LocalIgnoreResetDurabilityUnknown(receipt) => {
            path = Some(path_carrier(root, &receipt.path)?);
            backup_path = Some(path_carrier(root, &receipt.backup_path)?);
            malformed_identity = Some(project_identity(&receipt.malformed_identity));
            backup_identity = Some(project_identity(&receipt.backup_identity));
            replacement_identity = Some(project_identity(&receipt.replacement_identity));
        }
        contract::ResumeError::ContinuationConsumed | contract::ResumeError::Infrastructure(_) => {}
    }
    let code = error.kind().as_str();
    Ok(json!({
        "kind": code,
        "code": code,
        "messageNonEmpty": !error.to_string().is_empty(),
        "path": path,
        "stage": stage,
        "expectedIdentity": expected_identity,
        "actualIdentity": actual_identity,
        "backupPath": backup_path,
        "malformedIdentity": malformed_identity,
        "backupIdentity": backup_identity,
        "replacementIdentity": replacement_identity,
        "displaySeverities": display_severities(&render_resume_error(error)),
        "events": [],
    }))
}

/// Preserves the ordered severity contract while omitting prose already covered by render tests.
fn display_severities(lines: &[DisplayLine]) -> Vec<&'static str> {
    lines
        .iter()
        .map(|line| severity_token(line.severity))
        .collect()
}

/// Projects Installed YAML Data fields whose values are stable across every adapter.
fn project_local_ignore_installed_yaml_data(
    root: &Path,
    installed: &contract::InstalledYamlDataRunData,
) -> RunnerResult<Value> {
    let diagnostics = installed
        .diagnostics
        .iter()
        .map(|diagnostic| {
            Ok(json!({
                "role": diagnostic.role().map(Vocabulary::as_str),
                "candidate": diagnostic.candidate().map(Vocabulary::as_str),
                "path": diagnostic.path().map(|path| path_carrier(root, path)).transpose()?,
                "kind": diagnostic.kind().as_str(),
            }))
        })
        .collect::<RunnerResult<Vec<_>>>()?;
    let reset = installed
        .local_ignore_reset
        .as_ref()
        .map(|reset| -> RunnerResult<Value> {
            let backup_parent = reset
                .backup_path
                .parent()
                .ok_or_else(|| invalid_data("Local Ignore reset backup has no parent directory"))?;
            let backup_bytes = read_optional_file(&reset.backup_path)?;
            Ok(json!({
                "localIgnorePath": path_carrier(root, &reset.local_ignore_path)?,
                "backup": {
                    "parentPath": relative_path(root, backup_parent)?,
                    "exists": backup_bytes.is_some(),
                    "identityMatchesReceipt": backup_bytes.as_deref().map(YamlDataContentIdentity::from_bytes).as_ref() == Some(&reset.backup_identity),
                },
                "malformedIdentity": project_identity(&reset.malformed_identity),
                "backupIdentity": project_identity(&reset.backup_identity),
                "replacementIdentity": project_identity(&reset.replacement_identity),
            }))
        })
        .transpose()?;

    Ok(json!({
        "mainIdentity": project_identity(installed.main.identity()),
        "gameIdentity": project_identity(installed.game_file.identity()),
        "localIgnoreState": installed.local_ignore_state.as_str(),
        "localIgnoreIdentity": project_identity(&installed.local_ignore_identity),
        "diagnostics": diagnostics,
        "localIgnoreResetAvailable": installed.local_ignore_reset_available,
        "localIgnoreReset": reset,
    }))
}

/// Projects only stable event tokens while preserving run/log ordering.
fn project_compact_events(
    result: &contract::RunResult,
    events: &[contract::Event],
) -> RunnerResult<Value> {
    let mut run_events = Vec::new();
    let mut traces = vec![Vec::new(); result.logs.len()];
    for event in events {
        match event {
            contract::Event::DiscoveryCompleted(_) => {
                run_events.push("discovery_completed".to_string());
            }
            contract::Event::EffectiveConcurrencySelected { .. } => {
                run_events.push("effective_concurrency_selected".to_string());
            }
            contract::Event::LogQueued(log) => {
                append_compact_log_event(result, &mut traces, log, "log_queued")?;
            }
            contract::Event::LogStarted(log) => {
                append_compact_log_event(result, &mut traces, log, "log_started")?;
            }
            contract::Event::LogPhase { log, phase } => append_compact_log_event(
                result,
                &mut traces,
                log,
                &format!("log_phase:{}", phase.as_str()),
            )?,
            contract::Event::LogFinished { log, disposition } => append_compact_log_event(
                result,
                &mut traces,
                log,
                &format!("log_finished:{}", disposition.as_str()),
            )?,
        }
    }
    let logs = result
        .logs
        .iter()
        .zip(traces)
        .map(|(log, trace)| json!({"discoveryIndex": log.discovery_index, "trace": trace}))
        .collect::<Vec<_>>();
    Ok(json!({"run": run_events, "logs": logs}))
}

/// Appends one compact event after checking its discovery identity.
fn append_compact_log_event(
    result: &contract::RunResult,
    traces: &mut [Vec<String>],
    event: &contract::LogEvent,
    token: &str,
) -> RunnerResult<()> {
    let position = result
        .logs
        .iter()
        .position(|log| log.discovery_index == event.discovery_index)
        .ok_or_else(|| invalid_data("compact event references an unknown discovery index"))?;
    if result.logs[position].crash_log != event.crash_log {
        return Err(invalid_data("compact event references a different Crash Log").into());
    }
    traces[position].push(token.to_string());
    Ok(())
}

/// Projects Local Ignore, backup, report, and explicitly forbidden filesystem effects.
fn project_local_ignore_effects(
    root: &Path,
    input: &ScenarioInput,
    result: Option<&contract::RunResult>,
) -> RunnerResult<Value> {
    let local_ignore = root.join("CLASSIC Data/CLASSIC Ignore.yaml");
    let backup_directory = root.join("CLASSIC Backup/YAML Data/Local Ignore");
    let mut backups = if backup_directory.is_dir() {
        fs::read_dir(&backup_directory)?
            .map(|entry| entry.map(|value| value.path()))
            .collect::<Result<Vec<_>, _>>()?
    } else {
        Vec::new()
    };
    backups.sort();
    let backups = backups
        .iter()
        .filter(|path| path.is_file())
        .map(|path| project_backup_effect(root, path))
        .collect::<RunnerResult<Vec<_>>>()?;
    let reports = result
        .into_iter()
        .flat_map(|value| value.logs.iter())
        .filter_map(|log| log.autoscan_report.as_ref())
        .map(|path| project_exact_report_effect(root, path))
        .collect::<RunnerResult<Vec<_>>>()?;
    let forbidden = input
        .forbidden_effect_paths
        .iter()
        .map(|relative| {
            let path = join_relative(root, relative)?;
            project_file_effect(root, &path)
        })
        .collect::<RunnerResult<Vec<_>>>()?;

    Ok(json!({
        "localIgnore": project_file_effect(root, &local_ignore)?,
        "backups": backups,
        "reports": reports,
        "forbidden": forbidden,
    }))
}

/// Projects a backup through a stable parent path while retaining its exact byte identity.
fn project_backup_effect(root: &Path, path: &Path) -> RunnerResult<Value> {
    let parent = path
        .parent()
        .ok_or_else(|| invalid_data("Local Ignore backup has no parent directory"))?;
    let bytes = read_optional_file(path)?
        .ok_or_else(|| invalid_data("enumerated Local Ignore backup is not a readable file"))?;
    let identity = YamlDataContentIdentity::from_bytes(&bytes);
    Ok(json!({
        "parentPath": relative_path(root, parent)?,
        "identity": project_identity(&identity),
    }))
}

/// Projects one report's exact durable identity in addition to existence facts.
fn project_exact_report_effect(root: &Path, path: &Path) -> RunnerResult<Value> {
    let bytes = read_optional_file(path)?;
    let identity = bytes
        .as_deref()
        .map(YamlDataContentIdentity::from_bytes)
        .map(|value| project_identity(&value));
    Ok(json!({
        "path": relative_path(root, path)?,
        "exists": bytes.is_some(),
        "nonEmpty": bytes.as_ref().is_some_and(|value| !value.is_empty()),
        "identity": identity,
    }))
}

/// Projects one file's exact identity when it exists.
fn project_file_effect(root: &Path, path: &Path) -> RunnerResult<Value> {
    let metadata = match fs::metadata(path) {
        Ok(metadata) => Some(metadata),
        Err(error) if error.kind() == io::ErrorKind::NotFound => None,
        Err(error) => return Err(error.into()),
    };
    let identity = if metadata.as_ref().is_some_and(fs::Metadata::is_file) {
        Some(project_identity(&YamlDataContentIdentity::from_bytes(
            &fs::read(path)?,
        )))
    } else {
        None
    };
    Ok(json!({
        "path": relative_path(root, path)?,
        "exists": metadata.is_some(),
        "identity": identity,
    }))
}

/// Reads an optional file while distinguishing absence from every other I/O failure.
fn read_optional_file(path: &Path) -> RunnerResult<Option<Vec<u8>>> {
    match fs::read(path) {
        Ok(bytes) => Ok(Some(bytes)),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(error.into()),
    }
}

/// Projects ordered discovery facts with paths relative to the scenario root.
fn project_discovery(
    root: &Path,
    discovery: &classic_scanlog_core::CrashLogScanDiscoveryResult,
) -> RunnerResult<Value> {
    let accepted = discovery
        .accepted_logs
        .iter()
        .map(|path| path_carrier(root, path))
        .collect::<RunnerResult<Vec<_>>>()?;
    let rejected = discovery
        .rejected_inputs
        .iter()
        .map(|input| {
            Ok(json!({
                "path": relative_path(root, &input.path)?,
                "reason": input.reason,
            }))
        })
        .collect::<RunnerResult<Vec<_>>>()?;
    let searched = discovery
        .searched_locations
        .iter()
        .map(|path| path_carrier(root, path))
        .collect::<RunnerResult<Vec<_>>>()?;
    Ok(json!({
        "source": discovery.source.as_str(),
        "acceptedLogs": accepted,
        "rejectedInputs": rejected,
        "searchedLocations": searched,
    }))
}

/// Projects Installed YAML Data roles, schema versions, identities, and diagnostics.
fn project_installed_yaml_data(
    root: &Path,
    installed: &contract::InstalledYamlDataRunData,
) -> RunnerResult<Value> {
    let diagnostics = installed
        .diagnostics
        .iter()
        .map(|diagnostic| {
            Ok(json!({
                "role": diagnostic.role().map(Vocabulary::as_str),
                "candidate": diagnostic.candidate().map(Vocabulary::as_str),
                "path": diagnostic.path().map(|path| path_carrier(root, path)).transpose()?,
                "kind": diagnostic.kind().as_str(),
                "message": diagnostic.message(),
            }))
        })
        .collect::<RunnerResult<Vec<_>>>()?;
    Ok(json!({
        "main": project_yaml_file(&installed.main),
        "gameFile": project_yaml_file(&installed.game_file),
        "localIgnoreState": installed.local_ignore_state.as_str(),
        "localIgnoreIdentity": project_identity(&installed.local_ignore_identity),
        "diagnostics": diagnostics,
        "localIgnoreResetAvailable": installed.local_ignore_reset_available,
    }))
}

/// Projects one selected YAML file without reopening its mutable source path.
fn project_yaml_file(file: &InspectedYamlDataFile) -> Value {
    let schema = file.schema_version();
    json!({
        "role": file.role().as_str(),
        "provenance": file.provenance().as_str(),
        "schemaMajor": schema.major,
        "schemaMinor": schema.minor,
        "identity": project_identity(file.identity()),
    })
}

/// Projects a retained SHA-256 and byte-length identity.
fn project_identity(identity: &YamlDataContentIdentity) -> Value {
    json!({
        "sha256": identity.sha256_hex(),
        "byteLength": identity.byte_len(),
    })
}

/// Projects one per-log terminal outcome while intentionally excluding volatile timings.
fn project_log(root: &Path, log: &contract::LogResult) -> RunnerResult<Value> {
    let failures = log
        .failures
        .iter()
        .map(|failure| {
            json!({
                "stage": failure.stage.as_str(),
                "message": failure.message,
            })
        })
        .collect::<Vec<_>>();
    Ok(json!({
        "discoveryIndex": log.discovery_index,
        "crashLog": path_carrier(root, &log.crash_log)?,
        "autoscanReport": log.autoscan_report.as_ref().map(|path| path_carrier(root, path)).transpose()?,
        "disposition": log.disposition.as_str(),
        "failures": failures,
        "message": log.message,
        "movedToUnsolvedLogs": log.moved_to_unsolved_logs,
    }))
}

/// Partitions serialized observer events into stable run and per-log traces.
fn project_events(
    root: &Path,
    result: &contract::RunResult,
    events: &[contract::Event],
) -> RunnerResult<Value> {
    let mut run_events = Vec::new();
    let mut traces = vec![Vec::new(); result.logs.len()];
    for event in events {
        let display_content = project_display(root, &render_event(event))?;
        match event {
            contract::Event::DiscoveryCompleted(_) => run_events.push(json!({
                "kind": "discovery_completed",
                "displayContent": display_content,
            })),
            contract::Event::EffectiveConcurrencySelected {
                effective_concurrency,
            } => run_events.push(json!({
                "kind": "effective_concurrency_selected",
                "effectiveConcurrency": effective_concurrency,
                "displayContent": display_content,
            })),
            contract::Event::LogQueued(log) => append_log_event(
                result,
                &mut traces,
                log,
                json!({"kind": "log_queued", "displayContent": display_content}),
            )?,
            contract::Event::LogStarted(log) => append_log_event(
                result,
                &mut traces,
                log,
                json!({"kind": "log_started", "displayContent": display_content}),
            )?,
            contract::Event::LogPhase { log, phase } => append_log_event(
                result,
                &mut traces,
                log,
                json!({
                    "kind": "log_phase",
                    "phase": phase.as_str(),
                    "displayContent": display_content,
                }),
            )?,
            contract::Event::LogFinished { log, disposition } => append_log_event(
                result,
                &mut traces,
                log,
                json!({
                    "kind": "log_finished",
                    "disposition": disposition.as_str(),
                    "displayContent": display_content,
                }),
            )?,
        }
    }
    let log_events = result
        .logs
        .iter()
        .zip(traces)
        .map(|(log, trace)| {
            Ok(json!({
                "discoveryIndex": log.discovery_index,
                "crashLog": path_carrier(root, &log.crash_log)?,
                "trace": trace,
            }))
        })
        .collect::<RunnerResult<Vec<_>>>()?;
    Ok(json!({"run": run_events, "logs": log_events}))
}

/// Adds one live event to its discovery-indexed trace and validates its Crash Log identity.
fn append_log_event(
    result: &contract::RunResult,
    traces: &mut [Vec<Value>],
    event: &contract::LogEvent,
    projected: Value,
) -> RunnerResult<()> {
    let position = result
        .logs
        .iter()
        .position(|log| log.discovery_index == event.discovery_index)
        .ok_or_else(|| {
            invalid_data(format!(
                "event references unknown discovery index {}",
                event.discovery_index
            ))
        })?;
    if result.logs[position].crash_log != event.crash_log {
        return Err(invalid_data(format!(
            "event Crash Log differs at discovery index {}",
            event.discovery_index
        ))
        .into());
    }
    traces[position].push(projected);
    Ok(())
}

/// Projects typed Display Content into the closed binding carrier shape.
fn project_display(root: &Path, lines: &[DisplayLine]) -> RunnerResult<Value> {
    let lines = lines
        .iter()
        .map(|line| {
            let segments = line
                .segments
                .iter()
                .map(|segment| project_segment(root, segment))
                .collect::<RunnerResult<Vec<_>>>()?;
            Ok(json!({
                "severity": severity_token(line.severity),
                "segments": segments,
            }))
        })
        .collect::<RunnerResult<Vec<_>>>()?;
    Ok(Value::Array(lines))
}

/// Projects every Display Segment variant exhaustively without interpolating its payload.
fn project_segment(root: &Path, segment: &DisplaySegment) -> RunnerResult<Value> {
    let (kind, text, path, count) = match segment {
        DisplaySegment::Text(value) => ("text", (*value).to_string(), String::new(), 0),
        DisplaySegment::Label(value) => ("label", (*value).to_string(), String::new(), 0),
        DisplaySegment::Count { value, noun } => {
            ("count", (*noun).to_string(), String::new(), *value)
        }
        DisplaySegment::Path(value) => ("path", String::new(), relative_path(root, value)?, 0),
        DisplaySegment::Name(value) => ("name", value.clone(), String::new(), 0),
        DisplaySegment::Emphasis(value) => ("emphasis", value.clone(), String::new(), 0),
    };
    Ok(json!({"kind": kind, "text": text, "path": path, "count": count}))
}

/// Returns the frozen lowercase carrier token for one display severity.
const fn severity_token(severity: DisplaySeverity) -> &'static str {
    match severity {
        DisplaySeverity::Info => "info",
        DisplaySeverity::Notice => "notice",
        DisplaySeverity::Warning => "warning",
        DisplaySeverity::Failure => "failure",
        DisplaySeverity::Success => "success",
    }
}

/// Reopens one report only to record the durable existence and non-empty facts in the pack.
fn project_report_effect(root: &Path, path: &Path) -> RunnerResult<Value> {
    let metadata = fs::metadata(path).ok();
    Ok(json!({
        "path": relative_path(root, path)?,
        "exists": metadata.as_ref().is_some_and(fs::Metadata::is_file),
        "nonEmpty": metadata.is_some_and(|value| value.is_file() && value.len() > 0),
    }))
}

/// Wraps one normalized path in the carrier used by structured scan-run facts.
fn path_carrier(root: &Path, path: &Path) -> RunnerResult<Value> {
    Ok(json!({"path": relative_path(root, path)?}))
}

/// Converts a scenario-root path to portable forward-slash receipt form.
fn relative_path(root: &Path, path: &Path) -> RunnerResult<String> {
    let relative = path.strip_prefix(root).map_err(|_| {
        invalid_data(format!(
            "observed path escapes scenario root: {}",
            path.display()
        ))
    })?;
    let mut parts = Vec::<OsString>::new();
    for component in relative.components() {
        match component {
            Component::Normal(part) => parts.push(part.to_os_string()),
            _ => {
                return Err(invalid_data(format!(
                    "observed path is not normalized: {}",
                    path.display()
                ))
                .into());
            }
        }
    }
    if parts.is_empty() {
        return Ok(".".to_string());
    }
    parts
        .iter()
        .map(|part| {
            part.to_str()
                .map(str::to_owned)
                .ok_or_else(|| invalid_data("observed path is not valid UTF-8"))
        })
        .collect::<Result<Vec<_>, _>>()
        .map(|parts| parts.join("/"))
        .map_err(Into::into)
}

/// Publishes a complete JSON receipt without ever exposing partial bytes at its final path.
fn atomic_write_json(output_path: &Path, receipt: &Value) -> RunnerResult<()> {
    let parent = output_path
        .parent()
        .ok_or_else(|| invalid_data("receipt output path has no parent"))?;
    let mut temporary = NamedTempFile::new_in(parent)?;
    serde_json::to_writer_pretty(temporary.as_file_mut(), receipt)?;
    temporary.as_file_mut().write_all(b"\n")?;
    temporary.as_file_mut().sync_all()?;
    // The central materializer reserves an absent destination, which lets same-directory
    // persistence provide one atomic visibility boundary on every supported platform.
    temporary
        .persist(output_path)
        .map_err(|error| error.error)?;
    Ok(())
}

/// Builds a stable invalid-input error without adding a runner-only error dependency.
fn invalid_data(message: impl Into<String>) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message.into())
}
