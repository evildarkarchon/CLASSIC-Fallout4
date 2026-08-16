//! Executable receipt runner for the public Crash Log Scan Run Rust seam.
//!
//! The central launcher supplies an input-only plan and a reserved output path. This test
//! materializes every scenario in a fresh temporary root, executes only the public scan-run
//! contract, renders only through the public presentation crate, and publishes a receipt whose
//! observations can be compared with the independently authored scenario pack.

use classic_config_core::{InspectedYamlDataFile, YamlDataContentIdentity};
use classic_scan_presentation::{
    DisplayLine, DisplaySegment, DisplaySeverity, render_event, render_run_result,
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
    standard_source: Option<StandardSourceInput>,
    unsolved_logs: Option<UnsolvedLogsInput>,
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
    let request = build_request(&scenario.input, scenario_root.path())?;
    let cancellation = contract::Cancellation::new();
    let mut events = Vec::new();
    let result = get_runtime().block_on(contract::execute(
        request,
        &cancellation,
        Some(&mut |event| events.push(event)),
    ))?;
    project_observation(scenario_root.path(), &result, &events)
}

/// Copies every declared input fixture without exposing the pack's expected observations.
fn materialize_scenario(
    fixtures: &BTreeMap<String, PathBuf>,
    input: &ScenarioInput,
    root: &Path,
) -> RunnerResult<()> {
    for placement in &input.installation_data {
        copy_fixture(fixtures, &placement.fixture_ref, root, &placement.path)?;
    }
    for placement in &input.log_inputs {
        copy_fixture(fixtures, &placement.fixture_ref, root, &placement.path)?;
    }
    for targeted in &input.targeted_inputs {
        if let Some(fixture_ref) = &targeted.fixture_ref {
            copy_fixture(fixtures, fixture_ref, root, &targeted.path)?;
        }
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
