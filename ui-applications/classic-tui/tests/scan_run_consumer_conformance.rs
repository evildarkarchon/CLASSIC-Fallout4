//! Executable consumer receipt runner for the maintained TUI scan-run seam.
//!
//! The central launcher supplies an input-only consumer plan and a reserved output path. Ordinary
//! Cargo test runs have neither variable and report a visible skip. A receipt run materializes
//! shared fixtures under isolated roots, drives the public `App` event and key paths, and records
//! narrow layout observations without claiming semantic-adapter coverage.

use classic_scan_presentation::{DisplayLine, DisplaySegment, DisplaySeverity, render_run_result};
use classic_scanlog_core::scan_run::contract::{
    self, Cancellation, Configuration, Event, InfrastructureError, InfrastructureErrorStage,
    LocalIgnoreRecoveryDecision, Options, Request, RunResult,
};
use classic_scanlog_core::{
    CrashLogScanFacts, StandardCrashLogScanSource, StandardUnsolvedLogsIntent,
    TargetedCrashLogScanSource,
};
use classic_shared_core::{GameId, get_runtime};
use classic_tui::PresentedLine;
use classic_tui::app::{App, AsyncMessage, LastScanRun, Overlay};
use classic_vocabulary::Vocabulary;
use crossterm::event::{Event as TerminalEvent, KeyCode, KeyEvent, KeyModifiers};
use ratatui::Terminal;
use ratatui::backend::TestBackend;
use ratatui::buffer::Buffer;
use ratatui::style::Color;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fs::{self, File};
use std::io::{self, Write};
use std::panic::{AssertUnwindSafe, catch_unwind};
use std::path::{Component, Path, PathBuf};
use std::time::Duration;
use tempfile::{NamedTempFile, TempDir, tempdir};

const RUN_PLAN_ENV: &str = "CLASSIC_CONSUMER_CONFORMANCE_RUN_PLAN";
const OUTPUT_ENV: &str = "CLASSIC_CONSUMER_CONFORMANCE_OUTPUT";
const RUNNER_ID: &str = "classic-tui-scan-run-consumer";

const DISPLAY_SCENARIOS: &[&str] = &["standard-happy-path"];
const RECOVERY_SCENARIOS: &[&str] = &[
    "proceed-without-ignore-recovery",
    "reset-to-default-recovery",
    "abandon-local-ignore-recovery",
];
const CANCELLATION_SCENARIOS: &[&str] = &[
    "pre-discovery-cancelled",
    "post-discovery-queued-cancelled",
    "admitted-durable-cancelled",
];

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
    obligations: Vec<ObligationPlan>,
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

/// One named TUI obligation and the pack scenarios that make it applicable.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ObligationPlan {
    id: String,
    scenario_ids: Vec<String>,
}

/// A scenario materialized under an isolated root for one obligation observation.
struct MaterializedScenario {
    _temp: TempDir,
    root: PathBuf,
}

/// Lifecycle boundary at which the TUI requests cancellation.
#[derive(Clone, Copy, Eq, PartialEq)]
enum CancellationBoundary {
    BeforeDiscovery,
    OnFirstLogQueued,
    OnFirstLogStarted,
}

/// Runs the consumer receipt only when both private launcher variables are present.
#[test]
#[ignore = "requires the private consumer conformance launcher environment"]
fn writes_tui_scan_run_consumer_receipt() {
    let Some((plan_path, output_path)) = read_runner_paths()
        .expect("the TUI consumer launcher environment should be internally consistent")
    else {
        eprintln!("TUI consumer conformance launcher variables are absent; receipt run skipped");
        return;
    };
    let cache_root = tempdir().expect("an isolated cache root should be created");
    temp_env::with_vars(
        [
            ("LOCALAPPDATA", Some(cache_root.path())),
            ("XDG_CACHE_HOME", Some(cache_root.path())),
        ],
        || execute_and_publish(&plan_path, &output_path),
    )
    .expect("the TUI scan-run consumer receipt should be published");
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

/// Executes every named obligation and atomically publishes even failed obligation evidence.
fn execute_and_publish(plan_path: &Path, output_path: &Path) -> RunnerResult<()> {
    let plan: RunPlan = serde_json::from_reader(File::open(plan_path)?)?;
    validate_plan(&plan)?;
    if output_path.exists() {
        return Err(invalid_data(format!(
            "reserved receipt path already exists: {}",
            output_path.display()
        ))
        .into());
    }

    let obligations = plan
        .obligations
        .iter()
        .map(|obligation| execute_obligation(&plan, obligation))
        .collect::<Vec<_>>();
    let all_completed = obligations
        .iter()
        .all(|entry| entry["executionStatus"] == "completed");
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
            "toolchain": "rust-cargo",
        },
        "obligations": obligations,
    });
    atomic_write_json(output_path, &receipt)?;
    if !all_completed {
        return Err(invalid_data("one or more TUI consumer obligations failed").into());
    }
    Ok(())
}

/// Rejects plans for another family, participant, or obligation inventory.
fn validate_plan(plan: &RunPlan) -> RunnerResult<()> {
    if plan.schema_version != 1
        || plan.family_id != "crash-log-scan-run"
        || plan.family_version != 1
        || plan.participant.id != "tui"
        || plan.participant.role != "consumer"
    {
        return Err(
            invalid_data("run plan is not the TUI Crash Log Scan Run v1 consumer plan").into(),
        );
    }
    if plan.obligations.is_empty() {
        return Err(invalid_data("TUI consumer run plan has no obligations").into());
    }
    let obligation_ids = plan
        .obligations
        .iter()
        .map(|obligation| obligation.id.as_str())
        .collect::<BTreeSet<_>>();
    if obligation_ids.len() != plan.obligations.len() {
        return Err(invalid_data("TUI consumer run plan repeats an obligation ID").into());
    }
    Ok(())
}

/// Executes one obligation while preserving a failure as receipt evidence.
fn execute_obligation(plan: &RunPlan, obligation: &ObligationPlan) -> Value {
    let result = catch_unwind(AssertUnwindSafe(|| {
        obligation_observation(plan, obligation)
    }));
    match result {
        Ok(Ok(observation)) => json!({
            "id": obligation.id,
            "executionStatus": "completed",
            "observation": observation,
            "failure": null,
        }),
        Ok(Err(error)) => failed_obligation(obligation, error.to_string()),
        Err(payload) => failed_obligation(obligation, panic_message(payload)),
    }
}

/// Dispatches one stable obligation ID to its actual TUI observation.
fn obligation_observation(plan: &RunPlan, obligation: &ObligationPlan) -> RunnerResult<Value> {
    match obligation.id.as_str() {
        "tui.display-content-delivery" => observe_display_delivery(plan, obligation),
        "tui.ordering" => observe_ordering(plan, obligation),
        "tui.styling-categories" => observe_styling_categories(plan, obligation),
        "tui.recovery-interaction" => observe_recovery_interactions(plan, obligation),
        "tui.cancellation" => observe_cancellation_interactions(plan, obligation),
        unknown => Err(invalid_data(format!("unknown TUI consumer obligation {unknown}")).into()),
    }
}

/// Observes complete line delivery and the typed path/count handoff before TUI layout.
fn observe_display_delivery(plan: &RunPlan, obligation: &ObligationPlan) -> RunnerResult<Value> {
    require_scenarios(obligation, DISPLAY_SCENARIOS)?;
    let (materialized, result) = execute_standard(plan)?;
    let source = render_run_result(&result);
    let mut app = App::new_for_testing();
    app.handle_async_message(AsyncMessage::ScanFinished(Box::new(Ok(result))));
    let delivered = app.scan_run_summary_lines();
    let delivered_indices = match_presented_lines(&source, &delivered)?;

    let mut typed_paths = Vec::new();
    let mut typed_counts = Vec::new();
    for (line_index, line) in source.iter().enumerate() {
        for (segment_index, segment) in line.segments.iter().enumerate() {
            match segment {
                DisplaySegment::Path(path) => typed_paths.push(json!({
                    "lineIndex": line_index,
                    "segmentIndex": segment_index,
                    "path": observed_path(&materialized.root, path),
                })),
                DisplaySegment::Count { value, noun } => typed_counts.push(json!({
                    "lineIndex": line_index,
                    "segmentIndex": segment_index,
                    "value": value,
                    "noun": noun,
                })),
                _ => {}
            }
        }
    }
    Ok(json!({
        "sourceLineCount": source.len(),
        "deliveredSourceLineIndices": delivered_indices,
        "typedPaths": typed_paths,
        "typedCounts": typed_counts,
    }))
}

/// Observes the source-line positions in the exact order the TUI summary exposes them.
fn observe_ordering(plan: &RunPlan, obligation: &ObligationPlan) -> RunnerResult<Value> {
    require_scenarios(obligation, DISPLAY_SCENARIOS)?;
    let (_, result) = execute_standard(plan)?;
    let source = render_run_result(&result);
    let mut app = App::new_for_testing();
    app.handle_async_message(AsyncMessage::ScanFinished(Box::new(Ok(result))));
    Ok(json!({
        "sourceLineIndices": match_presented_lines(&source, &app.scan_run_summary_lines())?,
    }))
}

/// Observes the foreground colour actually rendered for every core severity category.
fn observe_styling_categories(plan: &RunPlan, obligation: &ObligationPlan) -> RunnerResult<Value> {
    require_scenarios(obligation, DISPLAY_SCENARIOS)?;

    let (_, standard_result) = execute_standard(plan)?;
    let mut standard_app = App::new_for_testing();
    standard_app.handle_async_message(AsyncMessage::ScanFinished(Box::new(Ok(standard_result))));
    let standard_lines = standard_app.scan_run_summary_lines();

    let (recovery, initial_log, late_log) =
        materialize_recovery(plan, "proceed-without-ignore-recovery")?;
    let cancellation = Cancellation::new();
    let paused = get_runtime().block_on(contract::execute(
        targeted_request(&recovery.root, vec![initial_log, late_log], 1),
        &cancellation,
        None,
    ))?;
    let mut recovery_app = App::new_for_testing();
    recovery_app.handle_async_message(AsyncMessage::ScanFinished(Box::new(Ok(paused))));
    let recovery_lines = recovery_app.local_ignore_recovery_lines();

    let mut failure_app = App::new_for_testing();
    failure_app.handle_async_message(AsyncMessage::ScanFinished(Box::new(Err(
        InfrastructureError {
            stage: InfrastructureErrorStage::Intake,
            message: "consumer style fixture".to_string(),
            path: None,
        },
    ))));
    let failure_lines = failure_app.scan_run_summary_lines();

    let categories = [
        rendered_category(
            &mut standard_app,
            Overlay::ScanSummary,
            &standard_lines,
            DisplaySeverity::Info,
        )?,
        rendered_category(
            &mut recovery_app,
            Overlay::LocalIgnoreRecovery,
            &recovery_lines,
            DisplaySeverity::Notice,
        )?,
        rendered_category(
            &mut recovery_app,
            Overlay::LocalIgnoreRecovery,
            &recovery_lines,
            DisplaySeverity::Warning,
        )?,
        rendered_category(
            &mut failure_app,
            Overlay::ScanSummary,
            &failure_lines,
            DisplaySeverity::Failure,
        )?,
        rendered_category(
            &mut standard_app,
            Overlay::ScanSummary,
            &standard_lines,
            DisplaySeverity::Success,
        )?,
    ];
    Ok(json!({ "categories": categories }))
}

/// Renders one maintained overlay and records the colour on a delivered line of the requested kind.
fn rendered_category(
    app: &mut App,
    overlay: Overlay,
    lines: &[PresentedLine],
    severity: DisplaySeverity,
) -> RunnerResult<Value> {
    let (line_index, line) = lines
        .iter()
        .enumerate()
        .find(|(_, line)| line.severity == severity)
        .ok_or_else(|| {
            invalid_data(format!(
                "fixture omitted {} severity",
                severity_token(severity)
            ))
        })?;
    match &overlay {
        Overlay::ScanSummary => app.scan_summary_scroll = line_index as u16,
        Overlay::LocalIgnoreRecovery => app.local_ignore_recovery_scroll = line_index as u16,
        _ => {
            return Err(invalid_data("style observation requires a severity-aware overlay").into());
        }
    }
    app.active_overlay = Some(overlay);

    let backend = TestBackend::new(160, 60);
    let mut terminal = Terminal::new(backend)?;
    terminal.draw(|frame| app.render(frame))?;
    let color = find_rendered_line_color(terminal.backend().buffer(), &line.text)?;
    Ok(json!({
        "severity": severity_token(severity),
        "color": color_token(color),
    }))
}

/// Finds the foreground colour on an exact line of text in a rendered terminal buffer.
fn find_rendered_line_color(buffer: &Buffer, text: &str) -> RunnerResult<Color> {
    // Scan-run overlays wrap at 86 cells. A substantial prefix is enough to identify the delivered
    // line while still observing the style applied by the real paragraph renderer.
    let symbols = text
        .chars()
        .take(72)
        .map(|value| value.to_string())
        .collect::<Vec<_>>();
    let area = buffer.area;
    if symbols.is_empty() || symbols.len() > usize::from(area.width) {
        return Err(invalid_data("rendered style fixture line has an unsupported width").into());
    }
    let last_x = area.width - symbols.len() as u16;
    for y in area.y..area.y + area.height {
        for relative_x in 0..=last_x {
            let x = area.x + relative_x;
            if symbols
                .iter()
                .enumerate()
                .all(|(offset, symbol)| buffer[(x + offset as u16, y)].symbol() == symbol)
            {
                return Ok(buffer[(x, y)].fg);
            }
        }
    }
    Err(invalid_data(format!("rendered overlay omitted expected line {text:?}")).into())
}

/// Drives Proceed, Reset, and explicit abandonment through the ordinary TUI key path.
fn observe_recovery_interactions(
    plan: &RunPlan,
    obligation: &ObligationPlan,
) -> RunnerResult<Value> {
    require_scenarios(obligation, RECOVERY_SCENARIOS)?;
    let interactions = obligation
        .scenario_ids
        .iter()
        .map(|scenario_id| observe_recovery_interaction(plan, scenario_id))
        .collect::<RunnerResult<Vec<_>>>()?;
    Ok(json!({ "interactions": interactions }))
}

/// Drives one planned recovery action and records the state reached through the App seam.
fn observe_recovery_interaction(plan: &RunPlan, scenario_id: &str) -> RunnerResult<Value> {
    let (scenario, initial_log, late_log) = materialize_recovery(plan, scenario_id)?;
    let cancellation = Cancellation::new();
    let request = targeted_request(&scenario.root, vec![initial_log, late_log.clone()], 1);
    let paused = get_runtime().block_on(contract::execute(request, &cancellation, None))?;
    copy_fixture(
        &plan.fixtures,
        "malformedLocalIgnoreYaml",
        &scenario.root,
        "CLASSIC Data/databases/CLASSIC Main.yaml",
    )?;
    copy_fixture(
        &plan.fixtures,
        "malformedLocalIgnoreYaml",
        &scenario.root,
        "CLASSIC Data/databases/CLASSIC Fallout4.yaml",
    )?;
    copy_fixture_at(&plan.fixtures, "validCrashLog", &late_log)?;

    let mut app = App::new_for_testing();
    app.scan_cancellation = Some(cancellation);
    app.handle_async_message(AsyncMessage::ScanFinished(Box::new(Ok(paused))));
    let offered_decisions = [
        (
            LocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
            "proceed-without-ignore",
        ),
        (
            LocalIgnoreRecoveryDecision::ResetToDefault,
            "reset-to-default",
        ),
    ]
    .into_iter()
    .filter_map(|(decision, token)| {
        app.local_ignore_decision_available(decision)
            .then_some(token)
    })
    .collect::<Vec<_>>();
    let (key, key_token) = recovery_key(scenario_id)?;
    press(&mut app, key);
    pump_until_resume_finished(&mut app)?;
    let terminal_status = terminal_result(&app)?.status.as_str();
    let overlay = match app.active_overlay {
        None => "none",
        Some(Overlay::LocalIgnoreRecovery) => "local-ignore-recovery",
        Some(_) => "other",
    };
    Ok(json!({
        "scenarioId": scenario_id,
        "key": key_token,
        "offeredDecisions": offered_decisions,
        "terminalStatus": terminal_status,
        "overlayAfterSelection": overlay,
        "remainingContinuationCount": usize::from(app.pending_local_ignore_recovery.is_some()),
    }))
}

/// Drives each lifecycle boundary through the TUI cancellation control.
fn observe_cancellation_interactions(
    plan: &RunPlan,
    obligation: &ObligationPlan,
) -> RunnerResult<Value> {
    require_scenarios(obligation, CANCELLATION_SCENARIOS)?;
    let interactions = obligation
        .scenario_ids
        .iter()
        .map(|scenario_id| observe_cancellation_interaction(plan, scenario_id))
        .collect::<RunnerResult<Vec<_>>>()?;
    Ok(json!({ "interactions": interactions }))
}

/// Executes one planned boundary while events and cancellation cross the public App seam.
fn observe_cancellation_interaction(plan: &RunPlan, scenario_id: &str) -> RunnerResult<Value> {
    let (scenario, logs, boundary) = materialize_cancellation(plan, scenario_id)?;
    let request = targeted_request(&scenario.root, logs, 1);
    let cancellation = Cancellation::new();
    let mut app = App::new_for_testing();
    app.scan_in_progress = true;
    app.scan_cancellation = Some(cancellation.clone());
    let mut triggered = false;
    if boundary == CancellationBoundary::BeforeDiscovery {
        app.start_or_cancel_crash_scan();
        triggered = true;
    }
    let result = {
        let mut observer = |event: Event| {
            let trigger_now = !triggered
                && match boundary {
                    CancellationBoundary::BeforeDiscovery => false,
                    CancellationBoundary::OnFirstLogQueued => matches!(event, Event::LogQueued(_)),
                    CancellationBoundary::OnFirstLogStarted => {
                        matches!(event, Event::LogStarted(_))
                    }
                };
            app.handle_async_message(AsyncMessage::ScanEvent(event));
            if trigger_now {
                app.start_or_cancel_crash_scan();
                triggered = true;
            }
        };
        get_runtime().block_on(contract::execute(
            request,
            &cancellation,
            Some(&mut observer),
        ))?
    };
    app.handle_async_message(AsyncMessage::ScanFinished(Box::new(Ok(result))));
    let retained = terminal_result(&app)?;
    let observation = json!({
        "scenarioId": scenario_id,
        "trigger": cancellation_token(boundary),
        "terminalStatus": retained.status.as_str(),
        "succeeded": retained.succeeded,
        "failed": retained.failed,
        "cancelled": retained.cancelled,
        "logDispositions": retained
            .logs
            .iter()
            .map(|log| Vocabulary::as_str(log.disposition))
            .collect::<Vec<_>>(),
    });
    Ok(observation)
}

/// Executes the real Standard happy path used by all Display Content obligations.
fn execute_standard(plan: &RunPlan) -> RunnerResult<(MaterializedScenario, RunResult)> {
    let scenario = materialize_common(plan, "localIgnoreYaml")?;
    for name in [
        "crash-shared-standard-01.log",
        "crash-shared-standard-02.log",
    ] {
        copy_fixture(
            &plan.fixtures,
            "validCrashLog",
            &scenario.root,
            &format!("Standard/Crash Logs/{name}"),
        )?;
    }
    let request = Request::standard(
        configuration(&scenario.root, 4),
        StandardCrashLogScanSource {
            base_directory: scenario.root.join("Standard"),
            custom_scan_directory: None,
            configured_documents_root: Some(scenario.root.join("Documents")),
        },
        StandardUnsolvedLogsIntent::LeaveInPlace,
    );
    let cancellation = Cancellation::new();
    let result = get_runtime().block_on(contract::execute(request, &cancellation, None))?;
    Ok((scenario, result))
}

/// Materializes one malformed-Ignore recovery case and returns its accepted and late inputs.
fn materialize_recovery(
    plan: &RunPlan,
    scenario_id: &str,
) -> RunnerResult<(MaterializedScenario, PathBuf, PathBuf)> {
    let stem = match scenario_id {
        "proceed-without-ignore-recovery" => "proceed",
        "reset-to-default-recovery" => "reset",
        "abandon-local-ignore-recovery" => "abandon",
        _ => return Err(invalid_data(format!("unknown recovery scenario {scenario_id}")).into()),
    };
    let scenario = materialize_common(plan, "malformedLocalIgnoreYaml")?;
    let initial = scenario.root.join(format!("Recovery/{stem}.log"));
    let late = scenario.root.join(format!("Recovery/{stem}-late.log"));
    copy_fixture_at(&plan.fixtures, "validCrashLog", &initial)?;
    Ok((scenario, initial, late))
}

/// Materializes one cancellation case and returns its inputs and trigger boundary.
fn materialize_cancellation(
    plan: &RunPlan,
    scenario_id: &str,
) -> RunnerResult<(MaterializedScenario, Vec<PathBuf>, CancellationBoundary)> {
    let (stem, boundary) = match scenario_id {
        "pre-discovery-cancelled" => ("pre-discovery", CancellationBoundary::BeforeDiscovery),
        "post-discovery-queued-cancelled" => ("queued", CancellationBoundary::OnFirstLogQueued),
        "admitted-durable-cancelled" => ("admitted", CancellationBoundary::OnFirstLogStarted),
        _ => {
            return Err(
                invalid_data(format!("unknown cancellation scenario {scenario_id}")).into(),
            );
        }
    };
    let scenario = materialize_common(plan, "localIgnoreYaml")?;
    let logs = [1, 2]
        .into_iter()
        .map(|ordinal| {
            let path = scenario
                .root
                .join(format!("Lifecycle/crash-{stem}-{ordinal:02}.log"));
            copy_fixture_at(&plan.fixtures, "validCrashLog", &path)?;
            Ok(path)
        })
        .collect::<RunnerResult<Vec<_>>>()?;
    Ok((scenario, logs, boundary))
}

/// Creates one isolated installation with the selected canonical Local Ignore fixture.
fn materialize_common(
    plan: &RunPlan,
    local_ignore_fixture: &str,
) -> RunnerResult<MaterializedScenario> {
    let temp = tempdir()?;
    let root = temp.path().to_path_buf();
    for (fixture, relative) in [
        ("mainYaml", "CLASSIC Data/databases/CLASSIC Main.yaml"),
        ("gameYaml", "CLASSIC Data/databases/CLASSIC Fallout4.yaml"),
        (local_ignore_fixture, "CLASSIC Data/CLASSIC Ignore.yaml"),
    ] {
        copy_fixture(&plan.fixtures, fixture, &root, relative)?;
    }
    Ok(MaterializedScenario { _temp: temp, root })
}

/// Builds the shared public scan-run configuration beneath one isolated root.
fn configuration(root: &Path, max_concurrent: usize) -> Configuration {
    Configuration {
        installation_root: root.to_path_buf(),
        game: GameId::Fallout4,
        game_version: "auto".to_string(),
        options: Options::new(false, false),
        scan_facts: CrashLogScanFacts::default(),
        max_concurrent: Some(max_concurrent),
    }
}

/// Builds one public Targeted request over caller-selected fixture paths.
fn targeted_request(root: &Path, inputs: Vec<PathBuf>, max_concurrent: usize) -> Request {
    Request::targeted(
        configuration(root, max_concurrent),
        TargetedCrashLogScanSource { inputs },
    )
}

/// Copies one declared fixture to a traversal-safe relative destination.
fn copy_fixture(
    fixtures: &BTreeMap<String, PathBuf>,
    fixture_ref: &str,
    root: &Path,
    relative: &str,
) -> RunnerResult<()> {
    let destination = join_relative(root, relative)?;
    copy_fixture_at(fixtures, fixture_ref, &destination)
}

/// Copies one declared fixture to an already isolated absolute destination.
fn copy_fixture_at(
    fixtures: &BTreeMap<String, PathBuf>,
    fixture_ref: &str,
    destination: &Path,
) -> RunnerResult<()> {
    let source = fixtures
        .get(fixture_ref)
        .ok_or_else(|| invalid_data(format!("unknown fixture reference {fixture_ref}")))?;
    fs::create_dir_all(
        destination
            .parent()
            .ok_or_else(|| invalid_data("fixture destination has no parent"))?,
    )?;
    fs::copy(source, destination)?;
    Ok(())
}

/// Joins one portable path while rejecting absolute and traversal components.
fn join_relative(root: &Path, relative: &str) -> RunnerResult<PathBuf> {
    let candidate = Path::new(relative);
    if relative.is_empty()
        || candidate.is_absolute()
        || candidate
            .components()
            .any(|component| !matches!(component, Component::Normal(_)))
    {
        return Err(invalid_data(format!("invalid relative fixture path {relative:?}")).into());
    }
    Ok(root.join(candidate))
}

/// Matches TUI-presented lines back to their core source positions without recording prose.
fn match_presented_lines(
    source: &[DisplayLine],
    presented: &[classic_tui::PresentedLine],
) -> RunnerResult<Vec<usize>> {
    let source_lines = source
        .iter()
        .map(|line| (line.severity, flatten_line(line)))
        .collect::<Vec<_>>();
    let mut cursor = 0;
    let mut indices = Vec::with_capacity(presented.len());
    for line in presented {
        let relative = source_lines[cursor..]
            .iter()
            .position(|candidate| candidate == &(line.severity, line.text.clone()))
            .ok_or_else(|| {
                invalid_data("TUI delivered a line not present in core display content")
            })?;
        let index = cursor + relative;
        indices.push(index);
        cursor = index + 1;
    }
    Ok(indices)
}

/// Flattens one source line using the TUI's documented full-path layout rule.
fn flatten_line(line: &DisplayLine) -> String {
    line.segments
        .iter()
        .map(|segment| match segment {
            DisplaySegment::Text(text) | DisplaySegment::Label(text) => (*text).to_string(),
            DisplaySegment::Count { value, noun } => format!("{value} {noun}"),
            DisplaySegment::Path(path) => path.display().to_string(),
            DisplaySegment::Name(name) | DisplaySegment::Emphasis(name) => name.clone(),
        })
        .collect::<Vec<_>>()
        .join(" ")
}

/// Returns a portable root-relative path observation where the scenario owns the path.
fn observed_path(root: &Path, path: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .components()
        .map(|component| component.as_os_str().to_string_lossy())
        .collect::<Vec<_>>()
        .join("/")
}

/// Returns the stable obligation token for one core severity category.
const fn severity_token(severity: DisplaySeverity) -> &'static str {
    match severity {
        DisplaySeverity::Info => "info",
        DisplaySeverity::Notice => "notice",
        DisplaySeverity::Warning => "warning",
        DisplaySeverity::Failure => "failure",
        DisplaySeverity::Success => "success",
    }
}

/// Returns a stable token for the real Ratatui color selected by the TUI theme.
fn color_token(color: ratatui::style::Color) -> String {
    match color {
        ratatui::style::Color::Rgb(red, green, blue) => format!("rgb:{red},{green},{blue}"),
        other => format!("{other:?}").to_ascii_lowercase(),
    }
}

/// Resolves a recovery scenario to its ordinary terminal key.
fn recovery_key(scenario_id: &str) -> RunnerResult<(KeyCode, &'static str)> {
    match scenario_id {
        "proceed-without-ignore-recovery" => Ok((KeyCode::Char('p'), "p")),
        "reset-to-default-recovery" => Ok((KeyCode::Char('r'), "r")),
        "abandon-local-ignore-recovery" => Ok((KeyCode::Esc, "escape")),
        _ => Err(invalid_data(format!("unknown recovery scenario {scenario_id}")).into()),
    }
}

/// Presses one unmodified key through the ordinary terminal event path.
fn press(app: &mut App, code: KeyCode) {
    app.handle_event(TerminalEvent::Key(KeyEvent::new(code, KeyModifiers::NONE)));
}

/// Drains background messages until a resumed or abandoned continuation finishes.
fn pump_until_resume_finished(app: &mut App) -> RunnerResult<()> {
    loop {
        let message = get_runtime()
            .block_on(async {
                tokio::time::timeout(Duration::from_secs(30), app.async_rx.recv()).await
            })
            .map_err(|_| invalid_data("TUI recovery worker did not finish within 30 seconds"))?
            .ok_or_else(|| invalid_data("TUI async channel closed before recovery finished"))?;
        let finished = matches!(message, AsyncMessage::ScanResumeFinished(_));
        app.handle_async_message(message);
        if finished {
            return Ok(());
        }
    }
}

/// Returns the retained terminal result after the TUI applies a completion message.
fn terminal_result(app: &App) -> RunnerResult<&RunResult> {
    match app.last_scan_run.as_ref() {
        Some(LastScanRun::Run(result)) => Ok(result),
        Some(LastScanRun::Failed(error)) => {
            Err(invalid_data(format!("unexpected infrastructure failure: {error:?}")).into())
        }
        Some(LastScanRun::RecoveryFailed(error)) => {
            Err(invalid_data(format!("unexpected recovery failure: {error:?}")).into())
        }
        None => Err(invalid_data("TUI retained no terminal scan result").into()),
    }
}

/// Returns the stable plan token for one cancellation boundary.
const fn cancellation_token(boundary: CancellationBoundary) -> &'static str {
    match boundary {
        CancellationBoundary::BeforeDiscovery => "before-discovery",
        CancellationBoundary::OnFirstLogQueued => "on-first-log-queued",
        CancellationBoundary::OnFirstLogStarted => "on-first-log-started",
    }
}

/// Requires one obligation's scenario identity and order to match its owned profile.
fn require_scenarios(obligation: &ObligationPlan, expected: &[&str]) -> RunnerResult<()> {
    if obligation.scenario_ids != expected {
        return Err(invalid_data(format!(
            "obligation {} scenario IDs differ from its TUI profile",
            obligation.id
        ))
        .into());
    }
    Ok(())
}

/// Builds one failed obligation entry with non-empty receipt-safe diagnostic text.
fn failed_obligation(obligation: &ObligationPlan, message: String) -> Value {
    json!({
        "id": obligation.id,
        "executionStatus": "failed",
        "observation": {},
        "failure": {
            "kind": "consumer-execution-failure",
            "message": if message.trim().is_empty() { "unknown TUI consumer failure" } else { &message },
        },
    })
}

/// Converts a caught panic payload into non-empty receipt-safe diagnostic text.
fn panic_message(payload: Box<dyn std::any::Any + Send>) -> String {
    payload
        .downcast_ref::<String>()
        .cloned()
        .or_else(|| {
            payload
                .downcast_ref::<&str>()
                .map(|message| (*message).to_string())
        })
        .unwrap_or_else(|| "TUI consumer obligation panicked".to_string())
}

/// Publishes compact canonical JSON without exposing partial receipt bytes.
fn atomic_write_json(path: &Path, document: &Value) -> RunnerResult<()> {
    let parent = path
        .parent()
        .ok_or_else(|| invalid_data("receipt path has no parent directory"))?;
    fs::create_dir_all(parent)?;
    let mut temporary = NamedTempFile::new_in(parent)?;
    serde_json::to_writer(&mut temporary, document)?;
    temporary.write_all(b"\n")?;
    temporary.as_file_mut().sync_all()?;
    temporary.persist_noclobber(path)?;
    Ok(())
}

/// Creates one invalid-data error with a receipt-safe message.
fn invalid_data(message: impl Into<String>) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message.into())
}
