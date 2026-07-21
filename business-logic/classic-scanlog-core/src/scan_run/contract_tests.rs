use crate::CrashLogScanFacts;
use crate::scan_run::contract;
use crate::scan_run::test_support::{InfrastructureFault, LocalIgnoreResetGate, ScanRunTestHooks};
use crate::scan_run::test_support::{
    write_fixture_log, write_fixture_log_at, write_minimal_yaml_tree,
};
use crate::scan_run::{
    CrashLogScanDiscoverySource, CrashLogScanOutcome, CrashLogScanRunLogOutcome,
    CrashLogScanSetupContext, StandardCrashLogScanSource, StandardUnsolvedLogsIntent,
    TargetedCrashLogScanSource,
};
use classic_shared_core::GameId;
use classic_shared_core::get_runtime;
use serde::Deserialize;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Barrier};
use std::time::Duration;
use tempfile::tempdir;

const SHARED_SCAN_RUN_MANIFEST: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../tests/fixtures/crash_log_scan_run/manifest.json"
));

/// Shared structured-failure expectations consumed by every supported adapter.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SharedFailureFixtures {
    log_result: SharedLogFailureResult,
    infrastructure_errors: Vec<SharedInfrastructureFailure>,
}

/// One normalized failed log result with every durable failure stage.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SharedLogFailureResult {
    discovery_index: usize,
    crash_log: String,
    autoscan_report: Option<String>,
    disposition: String,
    failures: Vec<SharedLogFailure>,
    message: String,
    moved_to_unsolved_logs: bool,
    processing_time_us: u64,
    processing_time_ms: u64,
    formid_count: usize,
    plugin_count: usize,
    suspect_count: usize,
}

/// One ordered per-log failure expectation.
#[derive(Debug, Deserialize)]
struct SharedLogFailure {
    stage: String,
    message: String,
}

/// One normalized run-wide infrastructure failure expectation.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SharedInfrastructureFailure {
    stage: String,
    raw_message: String,
    message: String,
    path: Option<String>,
}

/// Shared reset outcome expectations exercised at the Rust-owned transaction boundary.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SharedResetOutcomes {
    replacement_failure_code: String,
    backup_must_equal_malformed_bytes: bool,
    pre_reset_cancellation_mutates: bool,
    post_critical_cancellation_status: String,
}

/// Loads the failure corpus used by core and binding mapping tests.
fn shared_failure_fixtures() -> SharedFailureFixtures {
    #[derive(Deserialize)]
    #[serde(rename_all = "camelCase")]
    struct Manifest {
        failure_fixtures: SharedFailureFixtures,
    }

    serde_json::from_str::<Manifest>(SHARED_SCAN_RUN_MANIFEST)
        .expect("shared scan-run manifest should deserialize")
        .failure_fixtures
}

/// Loads reset failure and cancellation expectations from the cross-binding fixture.
fn shared_reset_outcomes() -> SharedResetOutcomes {
    #[derive(Deserialize)]
    #[serde(rename_all = "camelCase")]
    struct Manifest {
        fixtures: Fixtures,
    }

    #[derive(Deserialize)]
    #[serde(rename_all = "camelCase")]
    struct Fixtures {
        installed_yaml_data: InstalledYamlDataFixture,
    }

    #[derive(Deserialize)]
    #[serde(rename_all = "camelCase")]
    struct InstalledYamlDataFixture {
        reset_outcomes: SharedResetOutcomes,
    }

    serde_json::from_str::<Manifest>(SHARED_SCAN_RUN_MANIFEST)
        .expect("shared scan-run manifest should deserialize")
        .fixtures
        .installed_yaml_data
        .reset_outcomes
}

fn final_run_configuration() -> contract::Configuration {
    contract::Configuration {
        installation_root: std::path::PathBuf::from("C:/CLASSIC"),
        game: GameId::Fallout4,
        game_version: "auto".to_string(),
        options: contract::Options::new(true, true),
        scan_facts: CrashLogScanFacts::default(),
        max_concurrent: Some(2),
    }
}

fn final_standard_source() -> StandardCrashLogScanSource {
    StandardCrashLogScanSource {
        base_directory: std::path::PathBuf::from("C:/CLASSIC"),
        custom_scan_directory: None,
        configured_documents_root: None,
    }
}

fn final_setup_context() -> CrashLogScanSetupContext {
    CrashLogScanSetupContext {
        game_root: Some(std::path::PathBuf::from("C:/Games/Fallout 4")),
        docs_root: Some(std::path::PathBuf::from(
            "C:/Users/Test/Documents/My Games/Fallout4",
        )),
        game_exe_path: None,
        xse_log_path: None,
    }
}

/// Builds an executable FCX request whose configuration issue contains a run-unique value.
fn executable_fcx_request(
    temp: &tempfile::TempDir,
    log_name: &str,
    max_particles: u32,
) -> (contract::Request, PathBuf) {
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);

    let game_root = root.join("Fallout4");
    let docs_root = root.join("Documents");
    std::fs::create_dir_all(&game_root).expect("game root should be created");
    std::fs::create_dir_all(&docs_root).expect("documents root should be created");
    let game_exe_path = game_root.join("Fallout4.exe");
    std::fs::write(&game_exe_path, b"not a real PE")
        .expect("game executable fixture should be written");
    std::fs::write(
        game_root.join("epo.ini"),
        format!("[Particles]\niMaxDesired = {max_particles}\n"),
    )
    .expect("FCX configuration fixture should be written");

    let log_path = write_fixture_log(temp, log_name);
    let request = contract::Request::targeted_with_fcx(
        contract::Configuration {
            installation_root: root.to_path_buf(),
            game: GameId::Fallout4,
            game_version: "Original".to_string(),
            options: contract::Options::new(false, false),
            scan_facts: CrashLogScanFacts::default(),
            max_concurrent: Some(1),
        },
        TargetedCrashLogScanSource {
            inputs: vec![log_path.clone()],
        },
        CrashLogScanSetupContext {
            game_root: Some(game_root),
            docs_root: Some(docs_root),
            game_exe_path: Some(game_exe_path),
            xse_log_path: None,
        },
    );
    (request, log_path)
}

/// Verifies one run's structured setup and persisted report exclude another run's marker.
fn assert_isolated_fcx_run(
    result: &contract::RunResult,
    log_path: &std::path::Path,
    expected_marker: &str,
    foreign_marker: &str,
) {
    assert!(
        result
            .setup
            .as_ref()
            .expect("setup result should be retained")
            .configuration_issues
            .iter()
            .any(|issue| issue.current_value == expected_marker)
    );
    let report = std::fs::read_to_string(crate::report::autoscan_report_path(log_path))
        .expect("Autoscan Report should be readable");
    assert!(report.contains(expected_marker));
    assert!(!report.contains(foreign_marker));
}

/// Stable terminal fields used to compare runs whose temporary paths and timings differ.
#[derive(Debug, Eq, PartialEq)]
struct RunSignature {
    status: contract::RunStatus,
    effective_concurrency: Option<usize>,
    succeeded: usize,
    failed: usize,
    cancelled: usize,
    logs: Vec<(usize, String, contract::LogDisposition, Option<String>)>,
}

/// Normalizes one terminal result to scheduling- and outcome-relevant fields.
fn run_signature(result: &contract::RunResult) -> RunSignature {
    RunSignature {
        status: result.status,
        effective_concurrency: result.effective_concurrency,
        succeeded: result.succeeded,
        failed: result.failed,
        cancelled: result.cancelled,
        logs: result
            .logs
            .iter()
            .map(|log| {
                (
                    log.discovery_index,
                    log.crash_log
                        .file_name()
                        .expect("fixture log should have a file name")
                        .to_string_lossy()
                        .into_owned(),
                    log.disposition,
                    log.autoscan_report.as_ref().map(|path| {
                        path.file_name()
                            .expect("Autoscan Report should have a file name")
                            .to_string_lossy()
                            .into_owned()
                    }),
                )
            })
            .collect(),
    }
}

/// Executes the same two-log request with no, recording, or deliberately slow observation.
fn observer_scenario(delay: Option<Duration>) -> (contract::RunResult, Vec<contract::Event>) {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let logs = vec![
        write_fixture_log(&temp, "crash-observer-first.log"),
        write_fixture_log(&temp, "crash-observer-second.log"),
    ];
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    configuration.max_concurrent = Some(2);
    let request =
        contract::Request::targeted(configuration, TargetedCrashLogScanSource { inputs: logs });
    let cancellation = contract::Cancellation::new();
    let mut events = Vec::new();
    let result = if let Some(delay) = delay {
        let mut observer = |event| {
            std::thread::sleep(delay);
            events.push(event);
        };
        get_runtime().block_on(contract::execute(
            request,
            &cancellation,
            Some(&mut observer),
        ))
    } else {
        get_runtime().block_on(contract::execute(request, &cancellation, None))
    }
    .expect("observer scenario should complete");

    (result, events)
}

/// Creates one malformed-Ignore targeted run paused at the public continuation seam.
fn paused_recovery_fixture(
    log_names: &[&str],
) -> (
    tempfile::TempDir,
    Vec<PathBuf>,
    PathBuf,
    Vec<u8>,
    contract::RunResult,
) {
    paused_recovery_fixture_with_hooks(log_names, ScanRunTestHooks::default())
}

/// Creates one malformed-Ignore targeted run paused with request-scoped deterministic hooks.
fn paused_recovery_fixture_with_hooks(
    log_names: &[&str],
    hooks: ScanRunTestHooks,
) -> (
    tempfile::TempDir,
    Vec<PathBuf>,
    PathBuf,
    Vec<u8>,
    contract::RunResult,
) {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let ignore_path = data.join("CLASSIC Ignore.yaml");
    let malformed_ignore = b"CLASSIC_Ignore_Fallout4: [unterminated".to_vec();
    std::fs::write(&ignore_path, &malformed_ignore)
        .expect("malformed Local Ignore fixture should be written");
    let logs = log_names
        .iter()
        .map(|name| write_fixture_log(&temp, name))
        .collect::<Vec<_>>();
    let request = contract::Request::targeted(
        contract::Configuration {
            installation_root: root.to_path_buf(),
            game: GameId::Fallout4,
            game_version: "Original".to_string(),
            options: contract::Options::new(false, false),
            scan_facts: CrashLogScanFacts::default(),
            max_concurrent: Some(logs.len().max(1)),
        },
        TargetedCrashLogScanSource {
            inputs: logs.clone(),
        },
    );
    let result = get_runtime()
        .block_on(contract::execute_with_test_hooks(
            request,
            &contract::Cancellation::new(),
            None,
            hooks.with_yaml_cache_root(root.join("isolated-cache")),
        ))
        .expect("malformed Local Ignore should pause with expected result data");
    assert_eq!(
        result.status,
        contract::RunStatus::LocalIgnoreRecoveryRequired
    );
    (temp, logs, ignore_path, malformed_ignore, result)
}

#[test]
fn sequential_fcx_runs_return_and_render_only_their_own_setup_facts() {
    let first_temp = tempdir().expect("first tempdir should succeed");
    let second_temp = tempdir().expect("second tempdir should succeed");
    let (first_request, first_log) =
        executable_fcx_request(&first_temp, "crash-first-fcx.log", 6001);
    let (second_request, second_log) =
        executable_fcx_request(&second_temp, "crash-second-fcx.log", 7001);

    let first = get_runtime()
        .block_on(contract::execute(
            first_request,
            &contract::Cancellation::new(),
            None,
        ))
        .expect("first FCX run should complete");
    let second = get_runtime()
        .block_on(contract::execute(
            second_request,
            &contract::Cancellation::new(),
            None,
        ))
        .expect("second FCX run should complete");

    assert_isolated_fcx_run(&first, &first_log, "6001", "7001");
    assert_isolated_fcx_run(&second, &second_log, "7001", "6001");
}

#[test]
fn overlapping_fcx_runs_return_and_render_only_their_own_setup_facts() {
    let first_temp = tempdir().expect("first tempdir should succeed");
    let second_temp = tempdir().expect("second tempdir should succeed");
    let (first_request, first_log) =
        executable_fcx_request(&first_temp, "crash-overlap-first.log", 8001);
    let (second_request, second_log) =
        executable_fcx_request(&second_temp, "crash-overlap-second.log", 9001);
    let admission_barrier = Arc::new(Barrier::new(2));
    let (first, second) = get_runtime().block_on(async move {
        let first_barrier = Arc::clone(&admission_barrier);
        let first_task = tokio::spawn(async move {
            let cancellation = contract::Cancellation::new();
            let mut observer = move |event| {
                if matches!(event, contract::Event::LogStarted(_)) {
                    first_barrier.wait();
                }
            };
            contract::execute(first_request, &cancellation, Some(&mut observer)).await
        });
        let second_barrier = Arc::clone(&admission_barrier);
        let second_task = tokio::spawn(async move {
            let cancellation = contract::Cancellation::new();
            let mut observer = move |event| {
                if matches!(event, contract::Event::LogStarted(_)) {
                    second_barrier.wait();
                }
            };
            contract::execute(second_request, &cancellation, Some(&mut observer)).await
        });
        tokio::join!(first_task, second_task)
    });
    let first = first
        .expect("first overlapping task should join")
        .expect("first overlapping FCX run should complete");
    let second = second
        .expect("second overlapping task should join")
        .expect("second overlapping FCX run should complete");

    assert_isolated_fcx_run(&first, &first_log, "8001", "9001");
    assert_isolated_fcx_run(&second, &second_log, "9001", "8001");
}

#[test]
fn fcx_disabled_run_has_no_setup_result_or_fcx_report_content() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let log_path = write_fixture_log(&temp, "crash-fcx-disabled.log");
    let request = contract::Request::targeted(
        contract::Configuration {
            installation_root: root.to_path_buf(),
            game: GameId::Fallout4,
            game_version: "Original".to_string(),
            options: contract::Options::new(false, false),
            scan_facts: CrashLogScanFacts::default(),
            max_concurrent: Some(1),
        },
        TargetedCrashLogScanSource {
            inputs: vec![log_path.clone()],
        },
    );

    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &contract::Cancellation::new(),
            None,
        ))
        .expect("FCX-disabled run should complete");

    assert!(result.setup.is_none());
    let report = std::fs::read_to_string(crate::report::autoscan_report_path(&log_path))
        .expect("FCX-disabled Autoscan Report should be readable");
    assert!(!report.contains("FCX LOCAL FILE CHECKS"));
    assert!(!report.contains("FCX SETUP VALIDATION"));
}

#[test]
fn targeted_run_uses_one_ready_installed_yaml_data_snapshot() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let log_path = write_fixture_log(&temp, "crash-installed-snapshot.log");
    let request = contract::Request::targeted(
        contract::Configuration {
            installation_root: root.to_path_buf(),
            game: GameId::Fallout4,
            game_version: "Original".to_string(),
            options: contract::Options::new(false, false),
            scan_facts: CrashLogScanFacts::default(),
            max_concurrent: Some(1),
        },
        TargetedCrashLogScanSource {
            inputs: vec![log_path.clone()],
        },
    );

    let result = get_runtime()
        .block_on(contract::execute_with_test_hooks(
            request,
            &contract::Cancellation::new(),
            None,
            ScanRunTestHooks::default().with_yaml_cache_root(root.join("isolated-cache")),
        ))
        .expect("a valid installed snapshot should complete the run");

    assert_eq!(result.status, contract::RunStatus::Completed);
    let installed = result
        .installed_yaml_data
        .as_ref()
        .expect("completed intake should expose selected Installed YAML Data");
    assert_eq!(
        installed.main.provenance(),
        classic_config_core::InstalledYamlDataProvenance::Bundled
    );
    assert_eq!(
        installed.game_file.provenance(),
        classic_config_core::InstalledYamlDataProvenance::Bundled
    );
    assert_eq!(
        installed.local_ignore_state,
        contract::LocalIgnoreRunState::Existing
    );
    assert!(installed.diagnostics.is_empty());
    assert!(crate::report::autoscan_report_path(&log_path).is_file());
}

#[test]
fn targeted_run_generates_missing_local_ignore_and_keeps_diagnostic_out_of_report() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let ignore_path = data.join("CLASSIC Ignore.yaml");
    std::fs::remove_file(&ignore_path).expect("Local Ignore should be absent before the run");
    let log_path = write_fixture_log(&temp, "crash-generated-ignore.log");
    let request = contract::Request::targeted(
        contract::Configuration {
            installation_root: root.to_path_buf(),
            game: GameId::Fallout4,
            game_version: "Original".to_string(),
            options: contract::Options::new(false, false),
            scan_facts: CrashLogScanFacts::default(),
            max_concurrent: Some(1),
        },
        TargetedCrashLogScanSource {
            inputs: vec![log_path.clone()],
        },
    );

    let result = get_runtime()
        .block_on(contract::execute_with_test_hooks(
            request,
            &contract::Cancellation::new(),
            None,
            ScanRunTestHooks::default().with_yaml_cache_root(root.join("isolated-cache")),
        ))
        .expect("generated Local Ignore should remain a successful Ready run");

    let installed = result
        .installed_yaml_data
        .as_ref()
        .expect("completed intake should expose selected Installed YAML Data");
    assert_eq!(
        installed.local_ignore_state,
        contract::LocalIgnoreRunState::Generated
    );
    let generated = installed
        .diagnostics
        .iter()
        .find(|diagnostic| {
            diagnostic.kind() == contract::InstalledYamlDataRunDiagnosticKind::LocalIgnoreGenerated
        })
        .expect("generation should be exposed as structured run-level data");
    assert_eq!(generated.path(), Some(ignore_path.as_path()));
    assert_eq!(
        std::fs::read_to_string(&ignore_path).expect("generated Local Ignore should be readable"),
        "CLASSIC_Ignore_Fallout4:\n  - IgnoreThis.dll\n"
    );
    let report = std::fs::read_to_string(crate::report::autoscan_report_path(&log_path))
        .expect("Autoscan Report should be readable");
    assert!(!report.contains(generated.message()));
    assert!(!report.contains("Local Ignore"));
}

/// Malformed Local Ignore pauses after prepared intake and resumes the retained run exactly once.
#[test]
fn targeted_run_resumes_without_ignore_from_retained_discovery_and_snapshot() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let malformed_ignore = b"CLASSIC_Ignore_Fallout4: [unterminated";
    let ignore_path = data.join("CLASSIC Ignore.yaml");
    std::fs::write(&ignore_path, malformed_ignore)
        .expect("malformed Local Ignore fixture should be written");
    let first_log = write_fixture_log(&temp, "crash-recovery-first.log");
    let second_log = write_fixture_log(&temp, "crash-recovery-second.log");
    let undiscovered_log = root.join("crash-recovery-undiscovered.log");
    let request = contract::Request::targeted(
        contract::Configuration {
            installation_root: root.to_path_buf(),
            game: GameId::Fallout4,
            game_version: "Original".to_string(),
            options: contract::Options::new(false, false),
            scan_facts: CrashLogScanFacts::default(),
            max_concurrent: Some(2),
        },
        TargetedCrashLogScanSource {
            inputs: vec![
                first_log.clone(),
                undiscovered_log.clone(),
                second_log.clone(),
            ],
        },
    );

    let mut initial = get_runtime()
        .block_on(contract::execute_with_test_hooks(
            request,
            &contract::Cancellation::new(),
            None,
            ScanRunTestHooks::default().with_yaml_cache_root(root.join("isolated-cache")),
        ))
        .expect("malformed Local Ignore should be expected run result data");

    assert_eq!(
        initial.status,
        contract::RunStatus::LocalIgnoreRecoveryRequired
    );
    let discovery = initial
        .discovery
        .as_ref()
        .expect("recovery-required result should retain completed discovery");
    assert_eq!(
        discovery.accepted_logs,
        [first_log.clone(), second_log.clone()]
    );
    assert!(
        discovery
            .rejected_inputs
            .iter()
            .any(|input| input.path == undiscovered_log)
    );
    let initial_installed = initial
        .installed_yaml_data
        .as_ref()
        .expect("recovery-required result should expose structured Installed YAML Data facts");
    assert_eq!(
        initial_installed.local_ignore_state,
        contract::LocalIgnoreRunState::RecoveryRequired
    );
    assert_eq!(
        initial_installed.local_ignore_identity.byte_len(),
        malformed_ignore.len() as u64
    );
    assert!(initial_installed.diagnostics.iter().any(|diagnostic| {
        diagnostic.kind() == contract::InstalledYamlDataRunDiagnosticKind::Parse
            && diagnostic.path() == Some(ignore_path.as_path())
    }));
    let selected_main = initial_installed.main.clone();
    let selected_game = initial_installed.game_file.clone();
    let continuation = initial
        .continuation
        .take()
        .expect("recovery-required result should carry an opaque continuation");

    std::fs::write(
        data.join("databases/CLASSIC Main.yaml"),
        b"schema_version: \"2.0\"\ninvalid: changed\n",
    )
    .expect("selected Main path should be replaced after recovery paused");
    std::fs::write(
        data.join("databases/CLASSIC Fallout4.yaml"),
        b"schema_version: \"1.0\"\ninvalid: changed\n",
    )
    .expect("selected game path should be replaced after recovery paused");
    let created_after_pause = write_fixture_log(&temp, "crash-recovery-undiscovered.log");
    assert_eq!(created_after_pause, undiscovered_log);

    let resumed = get_runtime()
        .block_on(continuation.resume(
            contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
            &contract::Cancellation::new(),
            None,
        ))
        .expect("Proceed Without Ignore should resume retained prepared intake");

    assert_eq!(resumed.status, contract::RunStatus::Completed);
    assert_eq!(
        resumed
            .discovery
            .as_ref()
            .expect("resumed result should retain the same discovery")
            .accepted_logs,
        [first_log.clone(), second_log.clone()]
    );
    assert_eq!(
        resumed
            .logs
            .iter()
            .map(|log| (log.discovery_index, log.crash_log.clone()))
            .collect::<Vec<_>>(),
        vec![(0, first_log.clone()), (1, second_log.clone())]
    );
    let resumed_installed = resumed
        .installed_yaml_data
        .as_ref()
        .expect("resumed result should expose the retained Installed YAML Data facts");
    assert_eq!(resumed_installed.main, selected_main);
    assert_eq!(resumed_installed.game_file, selected_game);
    assert_eq!(
        resumed_installed.local_ignore_state,
        contract::LocalIgnoreRunState::ProceedWithoutIgnore
    );
    assert_eq!(
        std::fs::read(&ignore_path).expect("malformed Local Ignore should remain readable"),
        malformed_ignore
    );
    assert!(crate::report::autoscan_report_path(&first_log).is_file());
    assert!(crate::report::autoscan_report_path(&second_log).is_file());
    assert!(!crate::report::autoscan_report_path(&undiscovered_log).exists());
}

/// Reset To Default durably repairs Local Ignore and resumes the retained run exactly once.
#[test]
fn targeted_run_resets_local_ignore_and_resumes_retained_discovery_and_snapshot() {
    let (temp, logs, ignore_path, malformed_ignore, mut initial) = paused_recovery_fixture(&[
        "crash-reset-recovery-first.log",
        "crash-reset-recovery-second.log",
    ]);
    let initial_installed = initial
        .installed_yaml_data
        .as_ref()
        .expect("recovery-required result should expose selected Installed YAML Data");
    let selected_main = initial_installed.main.clone();
    let selected_game = initial_installed.game_file.clone();
    let continuation = initial
        .continuation
        .take()
        .expect("recovery-required result should carry an opaque continuation");
    let data = temp.path().join("CLASSIC Data");
    std::fs::write(
        data.join("databases/CLASSIC Main.yaml"),
        b"schema_version: \"2.0\"\ninvalid: changed\n",
    )
    .expect("selected Main path should be replaced after recovery paused");
    std::fs::write(
        data.join("databases/CLASSIC Fallout4.yaml"),
        b"schema_version: \"1.0\"\ninvalid: changed\n",
    )
    .expect("selected game path should be replaced after recovery paused");
    let mut events = Vec::new();
    let mut observer = |event| events.push(event);

    let resumed = get_runtime()
        .block_on(continuation.resume(
            contract::LocalIgnoreRecoveryDecision::ResetToDefault,
            &contract::Cancellation::new(),
            Some(&mut observer),
        ))
        .expect("Reset To Default should repair Local Ignore and resume retained preparation");

    assert_eq!(resumed.status, contract::RunStatus::Completed);
    assert_eq!(
        resumed
            .discovery
            .as_ref()
            .expect("resumed reset should retain completed discovery")
            .accepted_logs,
        logs
    );
    assert_eq!(resumed.logs.len(), 2);
    assert!(
        events
            .iter()
            .all(|event| !matches!(event, contract::Event::DiscoveryCompleted(_))),
        "resume must not emit a second discovery event"
    );
    assert_eq!(
        resumed
            .logs
            .iter()
            .map(|log| log.discovery_index)
            .collect::<Vec<_>>(),
        vec![0, 1]
    );
    let installed = resumed
        .installed_yaml_data
        .as_ref()
        .expect("successful reset should expose Installed YAML Data and reset metadata");
    assert_eq!(installed.main, selected_main);
    assert_eq!(installed.game_file, selected_game);
    assert_eq!(
        installed.local_ignore_state,
        contract::LocalIgnoreRunState::ResetToDefault
    );
    let reset = installed
        .local_ignore_reset
        .as_ref()
        .expect("successful reset should expose backup and replacement metadata");
    assert_eq!(reset.local_ignore_path, ignore_path);
    assert_eq!(
        std::fs::read(&reset.backup_path).expect("verified reset backup should be readable"),
        malformed_ignore
    );
    assert_eq!(reset.malformed_identity, reset.backup_identity);
    assert_eq!(reset.replacement_identity, installed.local_ignore_identity);
    assert!(installed.diagnostics.iter().any(|diagnostic| {
        diagnostic.kind() == contract::InstalledYamlDataRunDiagnosticKind::LocalIgnoreReset
            && diagnostic.path() == Some(ignore_path.as_path())
    }));
    assert_eq!(
        std::fs::read_to_string(&ignore_path).expect("reset Local Ignore should be readable"),
        "CLASSIC_Ignore_Fallout4:\n  - IgnoreThis.dll\n"
    );
    assert!(
        logs.iter()
            .all(|log| crate::report::autoscan_report_path(log).is_file())
    );
    let replay = get_runtime()
        .block_on(continuation.resume(
            contract::LocalIgnoreRecoveryDecision::ResetToDefault,
            &contract::Cancellation::new(),
            None,
        ))
        .expect_err("successful reset resume should consume the continuation");
    assert_eq!(replay, contract::ResumeError::ContinuationConsumed);
}

/// A changed canonical Local Ignore returns typed conflict data without backup or analysis.
#[test]
fn reset_to_default_returns_typed_conflict_without_overwriting_current_local_ignore() {
    let (_temp, logs, ignore_path, _malformed_ignore, mut initial) =
        paused_recovery_fixture(&["crash-reset-conflict.log"]);
    let continuation = initial
        .continuation
        .take()
        .expect("recovery-required result should carry an opaque continuation");
    let replacement = b"CLASSIC_Ignore_Fallout4:\n  - UserChanged.dll\n";
    std::fs::write(&ignore_path, replacement)
        .expect("conflicting Local Ignore bytes should be written");

    let error = get_runtime()
        .block_on(continuation.resume(
            contract::LocalIgnoreRecoveryDecision::ResetToDefault,
            &contract::Cancellation::new(),
            None,
        ))
        .expect_err("changed Local Ignore should reject reset as typed conflict data");

    let contract::ResumeError::LocalIgnoreResetConflict(conflict) = &error else {
        panic!("expected reset conflict, got {error:?}");
    };
    assert_eq!(
        error.kind(),
        contract::ResumeErrorKind::LocalIgnoreResetConflict
    );
    assert_eq!(error.kind().as_str(), "local_ignore_reset_conflict");
    assert_ne!(
        conflict.expected_identity,
        conflict.actual_identity.clone().unwrap()
    );
    assert!(conflict.backup_path.is_none());
    assert_eq!(
        std::fs::read(&ignore_path).expect("conflicting Local Ignore should remain readable"),
        replacement
    );
    assert!(
        logs.iter()
            .all(|log| !crate::report::autoscan_report_path(log).exists())
    );
    let replay = get_runtime()
        .block_on(continuation.resume(
            contract::LocalIgnoreRecoveryDecision::ResetToDefault,
            &contract::Cancellation::new(),
            None,
        ))
        .expect_err("conflicted reset resume should consume the continuation");
    assert_eq!(replay, contract::ResumeError::ContinuationConsumed);
}

/// Backup preparation failure is a stable reset outcome and never starts replacement or analysis.
#[test]
fn reset_to_default_returns_typed_backup_failure_without_mutation_or_analysis() {
    let (_temp, logs, ignore_path, malformed_ignore, mut initial) =
        paused_recovery_fixture(&["crash-reset-backup-failure.log"]);
    let continuation = initial
        .continuation
        .take()
        .expect("recovery-required result should carry an opaque continuation");
    let root = ignore_path
        .parent()
        .and_then(std::path::Path::parent)
        .expect("fixture Local Ignore should be below the installation root");
    let blocked_backup_root = root.join("CLASSIC Backup");
    std::fs::write(&blocked_backup_root, b"not a directory")
        .expect("backup root blocker should be written");

    let error = get_runtime()
        .block_on(continuation.resume(
            contract::LocalIgnoreRecoveryDecision::ResetToDefault,
            &contract::Cancellation::new(),
            None,
        ))
        .expect_err("backup preparation should fail with a stable reset outcome");

    let contract::ResumeError::LocalIgnoreResetBackupFailure(failure) = &error else {
        panic!("expected reset backup failure, got {error:?}");
    };
    assert_eq!(
        error.kind(),
        contract::ResumeErrorKind::LocalIgnoreResetBackupFailure
    );
    assert_eq!(error.kind().as_str(), "local_ignore_reset_backup_failure");
    assert!(failure.path.starts_with(&blocked_backup_root));
    assert!(failure.stage.is_none());
    assert!(!failure.message.is_empty());
    assert_eq!(
        std::fs::read(&ignore_path).expect("malformed Local Ignore should remain readable"),
        malformed_ignore
    );
    assert!(
        logs.iter()
            .all(|log| !crate::report::autoscan_report_path(log).exists())
    );
    let replay = get_runtime()
        .block_on(continuation.resume(
            contract::LocalIgnoreRecoveryDecision::ResetToDefault,
            &contract::Cancellation::new(),
            None,
        ))
        .expect_err("failed reset resume should consume the continuation");
    assert_eq!(replay, contract::ResumeError::ContinuationConsumed);
}

/// Replacement publication failures retain their stable kind, path, stage, and message.
#[test]
fn reset_replacement_publication_failure_projects_stable_typed_details() {
    let expected = shared_reset_outcomes();
    let path = PathBuf::from("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml");
    let error = contract::project_local_ignore_reset_error(
        classic_config_core::LocalIgnoreResetError::ReplacementPublication {
            path: path.clone(),
            stage: classic_config_core::LocalIgnoreResetPublicationStage::Publish,
            source: std::io::Error::other("injected replacement failure"),
        },
    );

    let contract::ResumeError::LocalIgnoreResetReplacementFailure(failure) = &error else {
        panic!("expected reset replacement failure, got {error:?}");
    };
    assert_eq!(
        error.kind(),
        contract::ResumeErrorKind::LocalIgnoreResetReplacementFailure
    );
    assert_eq!(error.kind().as_str(), expected.replacement_failure_code);
    assert_eq!(failure.path, path);
    assert_eq!(
        failure.stage,
        Some(contract::LocalIgnoreResetFailureStage::Publish)
    );
    assert_eq!(
        failure
            .stage
            .expect("replacement publication should retain its stage")
            .as_str(),
        "publish"
    );
    assert!(failure.message.contains("injected replacement failure"));
}

/// Cancellation observed before reset begins performs no backup, replacement, or analysis.
#[test]
fn cancellation_before_reset_to_default_performs_no_durable_or_analysis_work() {
    let expected = shared_reset_outcomes();
    let (_temp, logs, ignore_path, malformed_ignore, mut initial) =
        paused_recovery_fixture(&["crash-reset-pre-cancelled.log"]);
    let continuation = initial
        .continuation
        .take()
        .expect("recovery-required result should carry an opaque continuation");
    let cancellation = contract::Cancellation::new();
    cancellation.cancel();
    let mut events = Vec::new();
    let mut observer = |event| events.push(event);

    let cancelled = get_runtime()
        .block_on(continuation.resume(
            contract::LocalIgnoreRecoveryDecision::ResetToDefault,
            &cancellation,
            Some(&mut observer),
        ))
        .expect("pre-reset cancellation should remain normal result data");

    assert_eq!(cancelled.status, contract::RunStatus::Cancelled);
    assert_eq!(cancelled.cancelled, logs.len());
    assert!(cancelled.installed_yaml_data.is_none());
    assert!(cancelled.effective_concurrency.is_none());
    assert!(events.is_empty());
    let root = ignore_path
        .parent()
        .and_then(std::path::Path::parent)
        .expect("fixture Local Ignore should be below the installation root");
    let mutated = std::fs::read(&ignore_path)
        .expect("malformed Local Ignore should remain readable")
        != malformed_ignore
        || root.join("CLASSIC Backup").exists()
        || logs
            .iter()
            .any(|log| crate::report::autoscan_report_path(log).exists());
    assert_eq!(mutated, expected.pre_reset_cancellation_mutates);
}

/// Cancellation after reset enters its critical section waits for durability, then skips analysis.
#[test]
fn cancellation_racing_after_reset_begins_returns_cancelled_after_durable_reset() {
    let expected = shared_reset_outcomes();
    let gate = LocalIgnoreResetGate::new();
    let hooks = ScanRunTestHooks::default().with_local_ignore_reset_gate(gate.clone());
    let (_temp, logs, ignore_path, malformed_ignore, mut initial) =
        paused_recovery_fixture_with_hooks(&["crash-reset-racing-cancel.log"], hooks);
    let continuation = initial
        .continuation
        .take()
        .expect("recovery-required result should carry an opaque continuation");
    let cancellation = contract::Cancellation::new();
    let resume_cancellation = cancellation.clone();

    let handle = std::thread::spawn(move || {
        get_runtime().block_on(continuation.resume(
            contract::LocalIgnoreRecoveryDecision::ResetToDefault,
            &resume_cancellation,
            None,
        ))
    });
    gate.wait_until_entered();
    cancellation.cancel();
    gate.release();
    let cancelled = handle
        .join()
        .expect("racing reset resume thread should join")
        .expect("post-critical cancellation should remain normal result data");

    assert_eq!(
        cancelled.status.as_str(),
        expected.post_critical_cancellation_status
    );
    assert_eq!(cancelled.cancelled, logs.len());
    assert!(cancelled.installed_yaml_data.is_none());
    assert!(cancelled.effective_concurrency.is_none());
    assert_eq!(
        std::fs::read_to_string(&ignore_path).expect("reset Local Ignore should be readable"),
        "CLASSIC_Ignore_Fallout4:\n  - IgnoreThis.dll\n"
    );
    let root = ignore_path
        .parent()
        .and_then(std::path::Path::parent)
        .expect("fixture Local Ignore should be below the installation root");
    let backup_directory = root.join("CLASSIC Backup/YAML Data/Local Ignore");
    let backups = std::fs::read_dir(&backup_directory)
        .expect("durable reset should create its backup directory")
        .map(|entry| entry.expect("backup entry should be readable").path())
        .collect::<Vec<_>>();
    assert_eq!(backups.len(), 1);
    if expected.backup_must_equal_malformed_bytes {
        assert_eq!(
            std::fs::read(&backups[0]).expect("durable reset backup should be readable"),
            malformed_ignore
        );
    }
    assert!(
        logs.iter()
            .all(|log| !crate::report::autoscan_report_path(log).exists())
    );
}

/// Sequential and concurrent replay both return the same typed consumed-continuation failure.
#[test]
fn proceed_without_ignore_continuation_rejects_every_replay() {
    let (_temp, _logs, _ignore_path, _malformed_ignore, mut initial) =
        paused_recovery_fixture(&["crash-continuation-replay.log"]);
    let continuation = initial
        .continuation
        .take()
        .expect("recovery-required result should carry a continuation");

    get_runtime().block_on(async {
        let first_cancellation = contract::Cancellation::new();
        let second_cancellation = contract::Cancellation::new();
        let (first, second) = tokio::join!(
            continuation.resume(
                contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
                &first_cancellation,
                None,
            ),
            continuation.resume(
                contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
                &second_cancellation,
                None,
            )
        );
        assert_eq!(usize::from(first.is_ok()) + usize::from(second.is_ok()), 1);
        let error = first
            .err()
            .or_else(|| second.err())
            .expect("one racing resume should fail");
        assert_eq!(error, contract::ResumeError::ContinuationConsumed);
        assert_eq!(error.kind().as_str(), "scan_run_continuation_consumed");

        let replay = continuation
            .resume(
                contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
                &contract::Cancellation::new(),
                None,
            )
            .await
            .expect_err("every later resume should reject replay");
        assert_eq!(replay, contract::ResumeError::ContinuationConsumed);
    });
}

/// Pre-resume cancellation consumes the continuation before recovery or analysis can begin.
#[test]
fn cancellation_before_recovery_resume_returns_normal_cancelled_after_discovery_result() {
    let (_temp, logs, ignore_path, malformed_ignore, mut initial) =
        paused_recovery_fixture(&["crash-continuation-cancelled.log"]);
    let continuation = initial
        .continuation
        .take()
        .expect("recovery-required result should carry a continuation");
    let cancellation = contract::Cancellation::new();
    cancellation.cancel();
    let mut events = Vec::new();
    let mut observer = |event| events.push(event);

    let cancelled = get_runtime()
        .block_on(continuation.resume(
            contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
            &cancellation,
            Some(&mut observer),
        ))
        .expect("pre-resume cancellation should remain expected result data");

    assert_eq!(cancelled.status, contract::RunStatus::Cancelled);
    assert_eq!(cancelled.cancelled, logs.len());
    assert_eq!(
        cancelled
            .discovery
            .as_ref()
            .expect("cancelled-after-discovery should retain discovery")
            .accepted_logs,
        logs
    );
    assert!(cancelled.installed_yaml_data.is_none());
    assert!(cancelled.effective_concurrency.is_none());
    assert!(events.is_empty());
    assert!(
        logs.iter()
            .all(|log| !crate::report::autoscan_report_path(log).exists())
    );
    assert_eq!(
        std::fs::read(ignore_path).expect("malformed Local Ignore should remain readable"),
        malformed_ignore
    );
    let replay = get_runtime()
        .block_on(continuation.resume(
            contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
            &contract::Cancellation::new(),
            None,
        ))
        .expect_err("cancelled resume should still consume the continuation");
    assert_eq!(replay, contract::ResumeError::ContinuationConsumed);
}

#[test]
fn targeted_run_keeps_the_accepted_updated_snapshot_when_installation_files_change() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let cache_root = root.join("isolated-cache");
    let cache = cache_root.join("CLASSIC").join("yaml-cache");
    std::fs::create_dir_all(&cache).expect("isolated cache should be created");
    let updated_game = cache.join("CLASSIC Fallout4.yaml");
    std::fs::write(
        &updated_game,
        concat!(
            "schema_version: \"1.0\"\n",
            "Game_Info:\n",
            "  XSE_Acronym: \"F4SE\"\n",
            "  GameVersion: \"1.10.163\"\n",
            "  CRASHGEN_LatestVer: \"1.28.6\"\n",
            "  CRASHGEN_LogName: \"Buffout 4\"\n",
            "  Main_Root_Name: \"Fallout4\"\n",
            "Crashlog_Plugins_Exclude: []\n",
            "Crashlog_Records_Exclude: []\n",
            "Crashlog_Error_Check:\n",
            "  - id: updated-snapshot-rule\n",
            "    name: Updated Snapshot Rule\n",
            "    severity: 5\n",
            "    main_error_contains_any: [EXCEPTION_ACCESS_VIOLATION]\n",
            "Crashlog_Stack_Check: []\n",
            "Mods_CONF: []\n",
            "Mods_CORE: []\n",
            "Mods_FREQ: []\n",
            "Mods_SOLU: []\n",
            "Crashgen_Registry:\n",
            "  default:\n",
            "    display_section: \"\"\n",
            "    ignore_keys: []\n",
            "    checks: []\n",
        ),
    )
    .expect("updated game YAML Data should be written");
    let log_path = write_fixture_log(&temp, "crash-updated-snapshot.log");
    let request = contract::Request::targeted(
        contract::Configuration {
            installation_root: root.to_path_buf(),
            game: GameId::Fallout4,
            game_version: "Original".to_string(),
            options: contract::Options::new(false, true),
            scan_facts: CrashLogScanFacts::default(),
            max_concurrent: Some(1),
        },
        TargetedCrashLogScanSource {
            inputs: vec![log_path.clone()],
        },
    );
    let bundled_main = data.join("databases").join("CLASSIC Main.yaml");
    let local_ignore = data.join("CLASSIC Ignore.yaml");
    let mut changed = false;
    let mut observer = |event| {
        if !changed && matches!(event, contract::Event::EffectiveConcurrencySelected { .. }) {
            changed = true;
            std::fs::write(
                &updated_game,
                b"schema_version: \"1.0\"\ninvalid: changed\n",
            )
            .expect("selected game path should be replaced after intake");
            std::fs::write(
                &bundled_main,
                b"schema_version: \"2.0\"\ninvalid: changed\n",
            )
            .expect("selected Main path should be replaced after intake");
            std::fs::write(&local_ignore, b"not: [valid")
                .expect("selected Local Ignore path should be replaced after intake");
        }
    };

    let result = get_runtime()
        .block_on(contract::execute_with_test_hooks(
            request,
            &contract::Cancellation::new(),
            Some(&mut observer),
            ScanRunTestHooks::default().with_yaml_cache_root(cache_root),
        ))
        .expect("the retained snapshot should complete after installation changes");

    assert!(
        changed,
        "the fixture should replace files only after intake"
    );
    let installed = result
        .installed_yaml_data
        .as_ref()
        .expect("completed intake should expose selected Installed YAML Data");
    assert_eq!(
        installed.main.provenance(),
        classic_config_core::InstalledYamlDataProvenance::Bundled
    );
    assert_eq!(
        installed.game_file.provenance(),
        classic_config_core::InstalledYamlDataProvenance::Updated
    );
    let report = std::fs::read_to_string(crate::report::autoscan_report_path(&log_path))
        .expect("Autoscan Report should be readable");
    assert!(report.contains("Updated Snapshot Rule"));
    assert!(!report.contains("invalid: changed"));
}

#[test]
fn targeted_run_exposes_independent_updated_candidate_fallback_diagnostics() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let cache_root = root.join("isolated-cache");
    let cache = cache_root.join("CLASSIC").join("yaml-cache");
    std::fs::create_dir_all(&cache).expect("isolated cache should be created");
    let bundled_main = std::fs::read_to_string(data.join("databases/CLASSIC Main.yaml"))
        .expect("bundled Main should be readable");
    let bundled_game = std::fs::read_to_string(data.join("databases/CLASSIC Fallout4.yaml"))
        .expect("bundled game should be readable");
    std::fs::write(
        cache.join("CLASSIC Main.yaml"),
        bundled_main.replace("schema_version: \"2.0\"", "schema_version: \"3.0\""),
    )
    .expect("incompatible updated Main should be written");
    std::fs::write(
        cache.join("CLASSIC Fallout4.yaml"),
        bundled_game.replace("Main_Root_Name: \"Fallout4\"", "Main_Root_Name: \"Skyrim\""),
    )
    .expect("semantically invalid updated game should be written");
    let log_path = write_fixture_log(&temp, "crash-fallback-diagnostics.log");
    let request = contract::Request::targeted(
        contract::Configuration {
            installation_root: root.to_path_buf(),
            game: GameId::Fallout4,
            game_version: "Original".to_string(),
            options: contract::Options::new(false, false),
            scan_facts: CrashLogScanFacts::default(),
            max_concurrent: Some(1),
        },
        TargetedCrashLogScanSource {
            inputs: vec![log_path],
        },
    );

    let result = get_runtime()
        .block_on(contract::execute_with_test_hooks(
            request,
            &contract::Cancellation::new(),
            None,
            ScanRunTestHooks::default().with_yaml_cache_root(cache_root),
        ))
        .expect("rejected update candidates should fall back independently");

    let installed = result
        .installed_yaml_data
        .as_ref()
        .expect("completed intake should expose Installed YAML Data metadata");
    assert_eq!(
        installed.main.provenance(),
        classic_config_core::InstalledYamlDataProvenance::Bundled
    );
    assert_eq!(
        installed.game_file.provenance(),
        classic_config_core::InstalledYamlDataProvenance::Bundled
    );
    assert!(installed.diagnostics.iter().any(|diagnostic| {
        diagnostic.role() == Some(classic_config_core::InstalledYamlDataRole::Main)
            && diagnostic.candidate()
                == Some(classic_config_core::InstalledYamlDataProvenance::Updated)
            && diagnostic.kind() == contract::InstalledYamlDataRunDiagnosticKind::IncompatibleSchema
    }));
    assert!(installed.diagnostics.iter().any(|diagnostic| {
        diagnostic.role() == Some(classic_config_core::InstalledYamlDataRole::Game)
            && diagnostic.candidate()
                == Some(classic_config_core::InstalledYamlDataProvenance::Updated)
            && diagnostic.kind() == contract::InstalledYamlDataRunDiagnosticKind::InvalidRoleData
    }));
}

#[test]
fn targeted_run_selects_missing_canonical_main_previous_sibling_read_only() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let cache_root = root.join("isolated-cache");
    let cache = cache_root.join("CLASSIC").join("yaml-cache");
    std::fs::create_dir_all(&cache).expect("isolated cache should be created");
    let previous = cache.join("CLASSIC Main.yaml.prev");
    std::fs::copy(data.join("databases/CLASSIC Main.yaml"), &previous)
        .expect("valid previous Main should be written");
    let log_path = write_fixture_log(&temp, "crash-previous-main.log");
    let request = contract::Request::targeted(
        contract::Configuration {
            installation_root: root.to_path_buf(),
            game: GameId::Fallout4,
            game_version: "Original".to_string(),
            options: contract::Options::new(false, false),
            scan_facts: CrashLogScanFacts::default(),
            max_concurrent: Some(1),
        },
        TargetedCrashLogScanSource {
            inputs: vec![log_path],
        },
    );

    let result = get_runtime()
        .block_on(contract::execute_with_test_hooks(
            request,
            &contract::Cancellation::new(),
            None,
            ScanRunTestHooks::default().with_yaml_cache_root(cache_root),
        ))
        .expect("a valid previous Main should complete the run");

    let installed = result
        .installed_yaml_data
        .as_ref()
        .expect("completed intake should expose Installed YAML Data metadata");
    assert_eq!(
        installed.main.provenance(),
        classic_config_core::InstalledYamlDataProvenance::Previous
    );
    assert!(
        previous.exists(),
        "the previous sibling must remain in place"
    );
    assert!(
        !cache.join("CLASSIC Main.yaml").exists(),
        "the run must not promote the previous sibling"
    );
}

#[test]
fn fcx_configuration_scan_failure_is_a_typed_intake_error() {
    let temp = tempdir().expect("tempdir should succeed");
    let missing_game_root = temp.path().join("missing-game-root");
    // Exercise the post-intake seam directly so a real host registry installation cannot
    // replace the deliberately missing configured root and make this failure test machine-specific.
    let source = super::super::detect_setup_configuration_issues(
        None,
        Some(missing_game_root.as_path()),
        GameId::Fallout4.as_str(),
    )
    .expect_err("the missing fallback root should fail configuration scanning");
    let error = super::super::CrashLogScanRunServiceError::new(
        contract::InfrastructureErrorStage::Intake,
        Some(missing_game_root.clone()),
        source,
    );

    assert_eq!(error.stage, contract::InfrastructureErrorStage::Intake);
    assert_eq!(error.path, Some(missing_game_root));
    assert!(error.message.contains("configuration issues"));
}

#[test]
fn fcx_configuration_scan_uses_the_game_root_resolved_by_setup() {
    let configured_root = PathBuf::from("C:/stale-configured-root");
    let resolved_root = PathBuf::from("D:/resolved-game-root");

    assert_eq!(
        super::super::configuration_issue_scan_root(
            Some(resolved_root.as_path()),
            Some(configured_root.as_path()),
        ),
        Some(resolved_root.as_path())
    );
    assert_eq!(
        super::super::configuration_issue_scan_root(None, Some(configured_root.as_path())),
        Some(configured_root.as_path())
    );
}

#[test]
fn final_request_constructors_cover_every_valid_intent() {
    let standard_intents = [
        StandardUnsolvedLogsIntent::LeaveInPlace,
        StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
        StandardUnsolvedLogsIntent::MoveToCustom(std::path::PathBuf::from(
            "C:/CLASSIC/Unsolved Logs",
        )),
    ];

    for unsolved_logs in standard_intents {
        let request = contract::Request::standard(
            final_run_configuration(),
            final_standard_source(),
            unsolved_logs.clone(),
        );
        let contract::Request::Standard(request) = request else {
            panic!("standard constructor must preserve the tagged representation");
        };
        assert!(!request.fcx_enabled());
        assert_eq!(request.unsolved_logs(), &unsolved_logs);

        let request = contract::Request::standard_with_fcx(
            final_run_configuration(),
            final_standard_source(),
            unsolved_logs,
            final_setup_context(),
        );
        let contract::Request::Standard(request) = request else {
            panic!("FCX standard constructor must preserve the tagged representation");
        };
        assert!(request.fcx_enabled());
        assert!(request.setup_context().is_some());
    }

    let targeted_source = || TargetedCrashLogScanSource {
        inputs: vec![std::path::PathBuf::from("C:/Logs/crash.log")],
    };
    let request = contract::Request::targeted(final_run_configuration(), targeted_source());
    let contract::Request::Targeted(request) = request else {
        panic!("targeted constructor must preserve the tagged representation");
    };
    assert!(!request.fcx_enabled());

    let request = contract::Request::targeted_with_fcx(
        final_run_configuration(),
        targeted_source(),
        final_setup_context(),
    );
    let contract::Request::Targeted(request) = request else {
        panic!("FCX targeted constructor must preserve the tagged representation");
    };
    assert!(request.fcx_enabled());
    assert!(request.setup_context().is_some());
}

#[test]
fn cancellation_control_is_opaque_cloneable_and_separate_from_the_request() {
    let request = contract::Request::targeted(
        final_run_configuration(),
        TargetedCrashLogScanSource { inputs: Vec::new() },
    );
    let cancellation = contract::Cancellation::new();
    let adapter_control = cancellation.clone();

    assert!(matches!(request, contract::Request::Targeted(_)));
    assert!(!cancellation.is_cancelled());
    adapter_control.cancel();
    assert!(cancellation.is_cancelled());
}

#[test]
fn targeted_cancellation_before_discovery_has_no_discovery_result() {
    let temp = tempdir().expect("tempdir should succeed");
    let mut configuration = final_run_configuration();
    configuration.installation_root = temp.path().to_path_buf();
    let request = contract::Request::targeted(
        configuration,
        TargetedCrashLogScanSource {
            inputs: vec![temp.path().join("unobserved-target.log")],
        },
    );
    let cancellation = contract::Cancellation::new();
    cancellation.cancel();
    let mut events = Vec::new();
    let mut observer = |event| events.push(event);

    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &cancellation,
            Some(&mut observer),
        ))
        .expect("pre-discovery cancellation should be an expected terminal result");

    assert_eq!(result.status, contract::RunStatus::CancelledBeforeDiscovery);
    assert!(result.discovery.is_none());
    assert!(events.is_empty());
}

#[test]
fn standard_cancellation_before_discovery_has_no_discovery_result_or_side_effects() {
    let temp = tempdir().expect("tempdir should succeed");
    let mut configuration = final_run_configuration();
    configuration.installation_root = temp.path().to_path_buf();
    let request = contract::Request::standard(
        configuration,
        StandardCrashLogScanSource {
            base_directory: temp.path().to_path_buf(),
            custom_scan_directory: None,
            configured_documents_root: None,
        },
        StandardUnsolvedLogsIntent::LeaveInPlace,
    );
    let cancellation = contract::Cancellation::new();
    cancellation.cancel();
    let mut events = Vec::new();
    let mut observer = |event| events.push(event);

    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &cancellation,
            Some(&mut observer),
        ))
        .expect("pre-discovery cancellation should be an expected terminal result");

    assert_eq!(result.status, contract::RunStatus::CancelledBeforeDiscovery);
    assert!(result.discovery.is_none());
    assert!(events.is_empty());
    assert!(!temp.path().join("Crash Logs").exists());
}

#[test]
fn targeted_cancellation_during_discovery_discards_partial_results() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let directory = root.join("targeted-cancellation-tree");
    std::fs::create_dir_all(&directory).expect("targeted cancellation directory should be created");
    for index in 0..2_000 {
        std::fs::write(
            directory.join(format!("crash-targeted-discovery-cancel-{index:04}.log")),
            b"targeted discovery cancellation fixture",
        )
        .expect("targeted discovery fixture should be written");
    }
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    let request = contract::Request::targeted(
        configuration,
        TargetedCrashLogScanSource {
            inputs: vec![directory],
        },
    );
    let cancellation = contract::Cancellation::new();
    let cancellation_request = cancellation.clone();
    let mut events = Vec::new();
    let mut observer = |event| events.push(event);

    let result = get_runtime()
        .block_on(async {
            let canceller = tokio::spawn(async move {
                tokio::time::sleep(std::time::Duration::from_millis(1)).await;
                cancellation_request.cancel();
            });
            let result = contract::execute(request, &cancellation, Some(&mut observer)).await;
            canceller.await.expect("cancellation task should complete");
            result
        })
        .expect("discovery cancellation should be an expected terminal result");

    assert_eq!(result.status, contract::RunStatus::CancelledBeforeDiscovery);
    assert!(result.discovery.is_none());
    assert!(events.is_empty());
}

#[test]
fn standard_cancellation_during_discovery_discards_partial_results() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    for index in 0..256 {
        std::fs::write(
            root.join(format!("crash-standard-discovery-cancel-{index:04}.log")),
            b"discovery cancellation fixture",
        )
        .expect("standard discovery fixture should be written");
    }
    let first_moved_log = root
        .join("Crash Logs")
        .join("crash-standard-discovery-cancel-0000.log");
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    let request = contract::Request::standard(
        configuration,
        StandardCrashLogScanSource {
            base_directory: root.to_path_buf(),
            custom_scan_directory: None,
            configured_documents_root: Some(root.join("Documents")),
        },
        StandardUnsolvedLogsIntent::LeaveInPlace,
    );
    let cancellation = contract::Cancellation::new();
    let cancellation_request = cancellation.clone();
    let mut events = Vec::new();
    let mut observer = |event| events.push(event);

    let result = get_runtime()
        .block_on(async {
            let canceller = tokio::spawn(async move {
                tokio::time::timeout(std::time::Duration::from_secs(5), async {
                    while !first_moved_log.exists() {
                        tokio::task::yield_now().await;
                    }
                })
                .await
                .expect("standard discovery should move the first fixture");
                cancellation_request.cancel();
            });
            let result = contract::execute(request, &cancellation, Some(&mut observer)).await;
            canceller.await.expect("cancellation task should complete");
            result
        })
        .expect("discovery cancellation should be an expected terminal result");

    assert_eq!(result.status, contract::RunStatus::CancelledBeforeDiscovery);
    assert!(result.discovery.is_none());
    assert!(events.is_empty());
    let unmoved_logs = std::fs::read_dir(root)
        .expect("standard fixture root should remain readable")
        .filter_map(std::result::Result::ok)
        .filter(|entry| {
            entry
                .file_name()
                .to_string_lossy()
                .starts_with("crash-standard-discovery-cancel-")
        })
        .count();
    assert!(
        unmoved_logs > 0,
        "cancellation should stop within the Standard move phase"
    );
}

#[test]
fn targeted_cancellation_immediately_after_discovery_retains_the_complete_result() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let explicit = root.join("selected-input.txt");
    std::fs::write(&explicit, b"explicit targeted input")
        .expect("explicit targeted fixture should be written");
    let directory = root.join("selected-directory");
    let nested_directory = directory.join("nested");
    std::fs::create_dir_all(&nested_directory)
        .expect("nested targeted fixture directory should be created");
    let nested = nested_directory.join("crash-nested-target.log");
    std::fs::write(&nested, b"nested targeted input")
        .expect("nested targeted fixture should be written");
    let missing = root.join("missing-target.log");
    let inputs = vec![
        explicit.clone(),
        directory.clone(),
        nested.clone(),
        missing.clone(),
    ];
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    let request = contract::Request::targeted(
        configuration,
        TargetedCrashLogScanSource {
            inputs: inputs.clone(),
        },
    );
    let cancellation = contract::Cancellation::new();
    let observer_cancellation = cancellation.clone();
    let mut observed_discovery = None;
    let mut later_event_observed = false;
    let result = {
        let mut observer = |event| match event {
            contract::Event::DiscoveryCompleted(discovery) => {
                observed_discovery = Some(discovery);
                observer_cancellation.cancel();
            }
            _ => later_event_observed = true,
        };

        get_runtime()
            .block_on(contract::execute(
                request,
                &cancellation,
                Some(&mut observer),
            ))
            .expect("post-discovery cancellation should be an expected terminal result")
    };

    assert_eq!(result.status, contract::RunStatus::Cancelled);
    assert!(result.effective_concurrency.is_none());
    assert!(!later_event_observed);
    let retained = result
        .discovery
        .as_ref()
        .expect("completed discovery must be retained");
    let observed = observed_discovery
        .as_ref()
        .expect("completed discovery must be observable");
    assert_eq!(retained.source, CrashLogScanDiscoverySource::Targeted);
    assert_eq!(retained.accepted_logs, vec![explicit, nested]);
    assert_eq!(retained.searched_locations, inputs);
    assert_eq!(retained.rejected_inputs.len(), 1);
    assert_eq!(retained.rejected_inputs[0].path, missing);
    assert_eq!(observed.source, retained.source);
    assert_eq!(observed.accepted_logs, retained.accepted_logs);
    assert_eq!(observed.searched_locations, retained.searched_locations);
    assert_eq!(
        observed
            .rejected_inputs
            .iter()
            .map(|rejection| (&rejection.path, &rejection.reason))
            .collect::<Vec<_>>(),
        retained
            .rejected_inputs
            .iter()
            .map(|rejection| (&rejection.path, &rejection.reason))
            .collect::<Vec<_>>()
    );
    assert_eq!(result.total, 2);
    assert_eq!(result.cancelled, 2);
    assert!(
        result
            .logs
            .iter()
            .all(|log| { log.disposition == contract::LogDisposition::CancelledBeforeStart })
    );
}

#[test]
fn standard_cancellation_immediately_after_discovery_retains_configured_sources() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let base_log = root.join("crash-standard-base.log");
    std::fs::write(&base_log, b"standard base input")
        .expect("standard base fixture should be written");
    let custom = root.join("Custom Logs");
    std::fs::create_dir_all(custom.join("nested"))
        .expect("custom fixture directories should be created");
    let custom_log = custom.join("crash-standard-custom.log");
    std::fs::write(&custom_log, b"standard custom input")
        .expect("standard custom fixture should be written");
    std::fs::write(
        custom.join("nested").join("crash-standard-nested.log"),
        b"nested custom input",
    )
    .expect("nested custom fixture should be written");
    let documents = root.join("Configured Documents");
    std::fs::create_dir_all(&documents).expect("configured documents fixture should be created");
    let moved_base_log = root.join("Crash Logs").join("crash-standard-base.log");
    let searched_locations = vec![
        root.to_path_buf(),
        root.join("Crash Logs"),
        custom.clone(),
        documents.clone(),
    ];
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    let request = contract::Request::standard(
        configuration,
        StandardCrashLogScanSource {
            base_directory: root.to_path_buf(),
            custom_scan_directory: Some(custom),
            configured_documents_root: Some(documents),
        },
        StandardUnsolvedLogsIntent::LeaveInPlace,
    );
    let cancellation = contract::Cancellation::new();
    let observer_cancellation = cancellation.clone();
    let mut observed_discovery = None;
    let mut later_event_observed = false;
    let result = {
        let mut observer = |event| match event {
            contract::Event::DiscoveryCompleted(discovery) => {
                observed_discovery = Some(discovery);
                observer_cancellation.cancel();
            }
            _ => later_event_observed = true,
        };

        get_runtime()
            .block_on(contract::execute(
                request,
                &cancellation,
                Some(&mut observer),
            ))
            .expect("post-discovery cancellation should be an expected terminal result")
    };

    assert_eq!(result.status, contract::RunStatus::Cancelled);
    assert!(result.effective_concurrency.is_none());
    assert!(!later_event_observed);
    let retained = result
        .discovery
        .as_ref()
        .expect("completed discovery must be retained");
    let observed = observed_discovery
        .as_ref()
        .expect("completed discovery must be observable");
    assert_eq!(retained.source, CrashLogScanDiscoverySource::Standard);
    assert_eq!(retained.accepted_logs, vec![moved_base_log, custom_log]);
    assert!(retained.rejected_inputs.is_empty());
    assert_eq!(retained.searched_locations, searched_locations);
    assert_eq!(observed.source, retained.source);
    assert_eq!(observed.accepted_logs, retained.accepted_logs);
    assert_eq!(observed.searched_locations, retained.searched_locations);
    assert_eq!(result.total, 2);
    assert_eq!(result.cancelled, 2);
    assert!(
        result
            .logs
            .iter()
            .all(|log| { log.disposition == contract::LogDisposition::CancelledBeforeStart })
    );
}

#[test]
fn final_contract_exposes_all_stable_variant_identifiers() {
    assert_eq!(
        contract::RunStatus::LocalIgnoreRecoveryRequired.as_str(),
        "local_ignore_recovery_required"
    );
    assert_eq!(
        contract::LocalIgnoreRunState::RecoveryRequired.as_str(),
        "recovery_required"
    );
    assert_eq!(
        contract::LocalIgnoreRunState::ProceedWithoutIgnore.as_str(),
        "proceed_without_ignore"
    );
    assert_eq!(
        contract::LocalIgnoreRunState::ResetToDefault.as_str(),
        "reset_to_default"
    );
    assert_eq!(
        contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore.as_str(),
        "proceed_without_ignore"
    );
    assert_eq!(
        contract::LocalIgnoreRecoveryDecision::ResetToDefault.as_str(),
        "reset_to_default"
    );
    assert_eq!(
        contract::ResumeErrorKind::ContinuationConsumed.as_str(),
        "scan_run_continuation_consumed"
    );
    assert_eq!(
        contract::ResumeErrorKind::LocalIgnoreResetConflict.as_str(),
        "local_ignore_reset_conflict"
    );
    assert_eq!(
        contract::ResumeErrorKind::LocalIgnoreResetBackupFailure.as_str(),
        "local_ignore_reset_backup_failure"
    );
    assert_eq!(
        contract::ResumeErrorKind::LocalIgnoreResetReplacementFailure.as_str(),
        "local_ignore_reset_replacement_failure"
    );

    assert_eq!(
        contract::InfrastructureErrorStage::RequestValidation.as_str(),
        "request_validation"
    );
    assert_eq!(
        contract::InfrastructureErrorStage::Discovery.as_str(),
        "discovery"
    );
    assert_eq!(
        contract::InfrastructureErrorStage::Intake.as_str(),
        "intake"
    );
    assert_eq!(
        contract::InfrastructureErrorStage::FormIdDatabaseAccess.as_str(),
        "formid_database_access"
    );
    assert_eq!(
        contract::InfrastructureErrorStage::Initialization.as_str(),
        "initialization"
    );
    assert_eq!(
        contract::InfrastructureErrorStage::InternalInvariant.as_str(),
        "internal_invariant"
    );

    assert_eq!(contract::LogDisposition::Succeeded.as_str(), "succeeded");
    assert_eq!(contract::LogDisposition::Failed.as_str(), "failed");
    assert_eq!(
        contract::LogDisposition::CancelledBeforeStart.as_str(),
        "cancelled_before_start"
    );
    assert_eq!(contract::LogFailureStage::Analysis.as_str(), "analysis");
    assert_eq!(
        contract::LogFailureStage::ReportWrite.as_str(),
        "report_write"
    );
    assert_eq!(
        contract::LogFailureStage::UnsolvedLogsFinalization.as_str(),
        "unsolved_logs_finalization"
    );
}

#[test]
fn final_operation_accepts_optional_observer_and_retains_completed_discovery() {
    let temp = tempdir().expect("tempdir should succeed");
    let mut configuration = final_run_configuration();
    configuration.installation_root = temp.path().to_path_buf();
    let request = contract::Request::targeted(
        configuration,
        TargetedCrashLogScanSource { inputs: Vec::new() },
    );
    let cancellation = contract::Cancellation::new();
    let mut events = Vec::new();
    let mut observer = |event| events.push(event);

    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &cancellation,
            Some(&mut observer),
        ))
        .expect("an empty targeted run should be an expected terminal result");

    assert_eq!(result.status, contract::RunStatus::NoCrashLogsFound);
    assert!(result.effective_concurrency.is_none());
    assert_eq!(result.logs.len(), 0);
    let discovery = result
        .discovery
        .as_ref()
        .expect("completed discovery must be retained");
    assert_eq!(discovery.source, CrashLogScanDiscoverySource::Targeted);
    assert!(matches!(
        events.as_slice(),
        [contract::Event::DiscoveryCompleted(event_discovery)]
            if event_discovery.source == CrashLogScanDiscoverySource::Targeted
    ));
}

#[test]
fn final_operation_rejects_zero_concurrency_with_typed_request_stage() {
    let mut configuration = final_run_configuration();
    configuration.max_concurrent = Some(0);
    let request = contract::Request::standard(
        configuration,
        final_standard_source(),
        StandardUnsolvedLogsIntent::LeaveInPlace,
    );

    let error = get_runtime()
        .block_on(contract::execute(
            request,
            &contract::Cancellation::new(),
            None,
        ))
        .expect_err("zero is not a valid explicit concurrency value");

    assert_eq!(
        error.stage,
        contract::InfrastructureErrorStage::RequestValidation
    );
    assert!(error.path.is_none());
    assert!(error.message.contains("max_concurrent"));
}

#[test]
fn final_log_result_preserves_multiple_structured_failure_stages() {
    let fixture = shared_failure_fixtures().log_result;
    let result = contract::LogResult::from(CrashLogScanRunLogOutcome {
        input_index: fixture.discovery_index,
        crash_log: std::path::PathBuf::from(&fixture.crash_log),
        autoscan_report: fixture.autoscan_report.as_ref().map(PathBuf::from),
        outcome: CrashLogScanOutcome::Failed,
        moved_to_unsolved_logs: fixture.moved_to_unsolved_logs,
        analysis_error: Some(fixture.failures[0].message.clone()),
        report_write_error: Some(fixture.failures[1].message.clone()),
        unsolved_logs_finalization_error: Some(fixture.failures[2].message.clone()),
        error: Some(fixture.message.clone()),
        processing_time_us: fixture.processing_time_us,
        processing_time_ms: fixture.processing_time_ms,
        formid_count: fixture.formid_count,
        plugin_count: fixture.plugin_count,
        suspect_count: fixture.suspect_count,
    });

    assert_eq!(result.discovery_index, fixture.discovery_index);
    assert_eq!(result.crash_log, PathBuf::from(fixture.crash_log));
    assert_eq!(
        result.autoscan_report,
        fixture.autoscan_report.map(PathBuf::from)
    );
    assert_eq!(result.disposition.as_str(), fixture.disposition);
    assert_eq!(
        result
            .failures
            .iter()
            .map(|failure| (failure.stage.as_str(), failure.message.as_str()))
            .collect::<Vec<_>>(),
        fixture
            .failures
            .iter()
            .map(|failure| (failure.stage.as_str(), failure.message.as_str()))
            .collect::<Vec<_>>()
    );
    assert_eq!(result.message.as_deref(), Some(fixture.message.as_str()));
    assert_eq!(
        result.moved_to_unsolved_logs,
        fixture.moved_to_unsolved_logs
    );
    assert_eq!(result.processing_time_us, fixture.processing_time_us);
    assert_eq!(result.processing_time_ms, fixture.processing_time_ms);
    assert_eq!(result.formid_count, fixture.formid_count);
    assert_eq!(result.plugin_count, fixture.plugin_count);
    assert_eq!(result.suspect_count, fixture.suspect_count);
}

#[test]
fn final_operation_reports_effective_concurrency_and_stable_log_events() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let log_path = write_fixture_log(&temp, "crash-final-contract.log");
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    configuration.max_concurrent = Some(4);
    let request = contract::Request::targeted(
        configuration,
        TargetedCrashLogScanSource {
            inputs: vec![log_path.clone()],
        },
    );
    let mut events = Vec::new();
    let mut observer = |event| events.push(event);

    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &contract::Cancellation::new(),
            Some(&mut observer),
        ))
        .expect("the final operation should route through the existing run internals");

    assert_eq!(result.status, contract::RunStatus::Completed);
    assert_eq!(result.effective_concurrency, Some(1));
    assert_eq!(result.logs.len(), 1);
    assert_eq!(result.logs[0].discovery_index, 0);
    assert_eq!(result.logs[0].crash_log, log_path);
    assert_eq!(
        result.logs[0].disposition,
        contract::LogDisposition::Succeeded
    );
    assert!(matches!(
        events.first(),
        Some(contract::Event::DiscoveryCompleted(_))
    ));
    assert!(matches!(
        events.get(1),
        Some(contract::Event::EffectiveConcurrencySelected {
            effective_concurrency: 1
        })
    ));
    assert!(
        events
            .iter()
            .any(|event| matches!(event, contract::Event::LogQueued(_)))
    );
    assert!(
        events
            .iter()
            .any(|event| matches!(event, contract::Event::LogStarted(_)))
    );
    assert!(
        events
            .iter()
            .any(|event| matches!(event, contract::Event::LogPhase { .. }))
    );
    assert!(events.iter().any(|event| matches!(
        event,
        contract::Event::LogFinished {
            disposition: contract::LogDisposition::Succeeded,
            ..
        }
    )));
}

/// Verifies adaptive selection is published once and retained for low-volume work.
#[test]
fn adaptive_low_volume_run_selects_and_retains_one_worker() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let log = write_fixture_log(&temp, "crash-adaptive-low-volume.log");
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    configuration.max_concurrent = None;
    let request = contract::Request::targeted(
        configuration,
        TargetedCrashLogScanSource { inputs: vec![log] },
    );
    let mut selected = Vec::new();
    let mut observer = |event| {
        if let contract::Event::EffectiveConcurrencySelected {
            effective_concurrency,
        } = event
        {
            selected.push(effective_concurrency);
        }
    };

    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &contract::Cancellation::new(),
            Some(&mut observer),
        ))
        .expect("adaptive low-volume run should complete");

    assert_eq!(selected, vec![1]);
    assert_eq!(result.effective_concurrency, Some(1));
}

/// Verifies observer presence and callback latency do not control scheduling or outcomes.
#[test]
fn observer_presence_and_latency_do_not_change_scheduling_or_terminal_results() {
    let (unobserved, unobserved_events) = observer_scenario(None);
    let (recorded, recorded_events) = observer_scenario(Some(Duration::ZERO));
    let (slow, slow_events) = observer_scenario(Some(Duration::from_millis(2)));

    assert!(unobserved_events.is_empty());
    assert_eq!(run_signature(&unobserved), run_signature(&recorded));
    assert_eq!(run_signature(&recorded), run_signature(&slow));

    let started_indices = |events: &[contract::Event]| {
        events
            .iter()
            .filter_map(|event| match event {
                contract::Event::LogStarted(log) => Some(log.discovery_index),
                _ => None,
            })
            .collect::<Vec<_>>()
    };
    assert_eq!(started_indices(&recorded_events), vec![0, 1]);
    assert_eq!(started_indices(&slow_events), vec![0, 1]);
}

/// Verifies serial admission remains occupied until the prior log is durably finished.
#[test]
fn serial_scheduler_finishes_one_log_before_starting_the_next() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let first = write_fixture_log(&temp, "crash-serial-first.log");
    let second = write_fixture_log(&temp, "crash-serial-second.log");
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    configuration.max_concurrent = Some(1);
    let request = contract::Request::targeted(
        configuration,
        TargetedCrashLogScanSource {
            inputs: vec![first, second],
        },
    );
    let mut events = Vec::new();
    let mut observer = |event| events.push(event);

    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &contract::Cancellation::new(),
            Some(&mut observer),
        ))
        .expect("serial final operation should complete");

    assert_eq!(result.effective_concurrency, Some(1));
    assert_eq!(result.succeeded, 2);
    let lifecycle = events
        .iter()
        .filter_map(|event| match event {
            contract::Event::LogStarted(log) => Some(("started", log.discovery_index)),
            contract::Event::LogFinished { log, .. } => Some(("finished", log.discovery_index)),
            _ => None,
        })
        .collect::<Vec<_>>();
    assert_eq!(
        lifecycle,
        vec![
            ("started", 0),
            ("finished", 0),
            ("started", 1),
            ("finished", 1),
        ]
    );
}

/// Verifies cancellation requested while logs are queued prevents every admission.
#[test]
fn cancellation_while_queued_never_emits_started() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let logs = vec![
        write_fixture_log(&temp, "crash-queued-first.log"),
        write_fixture_log(&temp, "crash-queued-second.log"),
    ];
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    configuration.max_concurrent = Some(1);
    let request = contract::Request::targeted(
        configuration,
        TargetedCrashLogScanSource {
            inputs: logs.clone(),
        },
    );
    let cancellation = contract::Cancellation::new();
    let observer_cancellation = cancellation.clone();
    let mut events = Vec::new();
    let mut observer = |event| {
        if matches!(event, contract::Event::LogQueued(_)) {
            observer_cancellation.cancel();
        }
        events.push(event);
    };

    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &cancellation,
            Some(&mut observer),
        ))
        .expect("queued cancellation should produce a terminal result");

    assert_eq!(result.status, contract::RunStatus::Cancelled);
    assert_eq!(result.cancelled, 2);
    assert!(
        result
            .logs
            .iter()
            .all(|log| log.disposition == contract::LogDisposition::CancelledBeforeStart)
    );
    assert!(
        events
            .iter()
            .all(|event| !matches!(event, contract::Event::LogStarted(_)))
    );
    assert!(
        logs.iter()
            .all(|log| { !crate::report::autoscan_report_path(log).exists() })
    );
}

/// Verifies admitted logs finish durably while later queued logs remain unstarted.
#[test]
fn cancellation_with_multiple_admitted_logs_preserves_their_durable_boundary() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let logs = (0..4)
        .map(|index| write_fixture_log(&temp, &format!("crash-admitted-{index}.log")))
        .collect::<Vec<_>>();
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    configuration.max_concurrent = Some(2);
    let request = contract::Request::targeted(
        configuration,
        TargetedCrashLogScanSource {
            inputs: logs.clone(),
        },
    );
    let cancellation = contract::Cancellation::new();
    let observer_cancellation = cancellation.clone();
    let mut started = Vec::new();
    let mut observer = |event| {
        if let contract::Event::LogStarted(log) = event {
            started.push(log.discovery_index);
            if log.discovery_index == 1 {
                observer_cancellation.cancel();
            }
        }
    };

    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &cancellation,
            Some(&mut observer),
        ))
        .expect("admitted cancellation should produce a terminal result");

    assert_eq!(started, vec![0, 1]);
    assert_eq!(result.status, contract::RunStatus::Cancelled);
    assert_eq!(result.succeeded, 2);
    assert_eq!(result.cancelled, 2);
    assert_eq!(
        result
            .logs
            .iter()
            .map(|log| log.disposition)
            .collect::<Vec<_>>(),
        vec![
            contract::LogDisposition::Succeeded,
            contract::LogDisposition::Succeeded,
            contract::LogDisposition::CancelledBeforeStart,
            contract::LogDisposition::CancelledBeforeStart,
        ]
    );
    assert!(
        logs[..2]
            .iter()
            .all(|log| crate::report::autoscan_report_path(log).is_file())
    );
    assert!(
        logs[2..]
            .iter()
            .all(|log| !crate::report::autoscan_report_path(log).exists())
    );
}

#[test]
fn observer_can_request_cancellation_before_discovered_logs_are_admitted() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let first = write_fixture_log(&temp, "crash-cancel-first.log");
    let second = write_fixture_log(&temp, "crash-cancel-second.log");
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    let request = contract::Request::targeted(
        configuration,
        TargetedCrashLogScanSource {
            inputs: vec![first, second],
        },
    );
    let cancellation = contract::Cancellation::new();
    let observer_cancellation = cancellation.clone();
    let started = Arc::new(AtomicBool::new(false));
    let observer_started = Arc::clone(&started);
    let mut observer = move |event| {
        if matches!(event, contract::Event::EffectiveConcurrencySelected { .. }) {
            observer_cancellation.cancel();
        }
        if matches!(event, contract::Event::LogStarted(_)) {
            observer_started.store(true, Ordering::SeqCst);
        }
    };

    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &cancellation,
            Some(&mut observer),
        ))
        .expect("observer-requested cancellation should be a terminal result");

    assert_eq!(result.status, contract::RunStatus::Cancelled);
    assert_eq!(result.cancelled, 2);
    assert!(
        result
            .logs
            .iter()
            .all(|log| { log.disposition == contract::LogDisposition::CancelledBeforeStart })
    );
    assert!(!started.load(Ordering::SeqCst));
}

/// Verifies live events retain completion order while terminal results retain discovery order.
#[test]
fn terminal_outcomes_remain_in_discovery_order_when_completion_is_out_of_order() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let first = write_fixture_log(&temp, "crash-slow-first.log");
    let second = write_fixture_log(&temp, "crash-fast-second.log");
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    configuration.max_concurrent = Some(2);
    let request = contract::Request::targeted(
        configuration,
        TargetedCrashLogScanSource {
            inputs: vec![first.clone(), second.clone()],
        },
    );
    let hooks = ScanRunTestHooks::default().with_analysis_delay(0, Duration::from_millis(100));
    let mut finished = Vec::new();
    let mut observer = |event| {
        if let contract::Event::LogFinished { log, .. } = event {
            finished.push(log.discovery_index);
        }
    };

    let result = get_runtime()
        .block_on(contract::execute_with_test_hooks(
            request,
            &contract::Cancellation::new(),
            Some(&mut observer),
            hooks,
        ))
        .expect("both admitted logs should complete");

    assert_eq!(finished, vec![1, 0]);
    assert_eq!(
        result
            .logs
            .iter()
            .map(|log| (log.discovery_index, log.crash_log.clone()))
            .collect::<Vec<_>>(),
        vec![(0, first), (1, second)]
    );
}

/// Verifies one admitted analysis failure does not suppress another admitted log's report.
#[test]
fn admitted_analysis_failure_does_not_abort_other_admitted_log() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let failed = write_fixture_log(&temp, "crash-failed-analysis.log");
    let succeeded = write_fixture_log(&temp, "crash-successful-analysis.log");
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    configuration.max_concurrent = Some(2);
    let request = contract::Request::targeted(
        configuration,
        TargetedCrashLogScanSource {
            inputs: vec![failed.clone(), succeeded.clone()],
        },
    );
    let hooks = ScanRunTestHooks::default().with_analysis_failure(0, "injected analysis failure");

    let result = get_runtime()
        .block_on(contract::execute_with_test_hooks(
            request,
            &contract::Cancellation::new(),
            None,
            hooks,
        ))
        .expect("a per-log analysis failure should not abort other admitted work");

    assert_eq!(result.status, contract::RunStatus::Completed);
    assert_eq!((result.total, result.succeeded, result.failed), (2, 1, 1));
    assert_eq!(result.cancelled, 0);

    let failed_result = &result.logs[0];
    assert_eq!(failed_result.crash_log, failed);
    assert_eq!(failed_result.disposition, contract::LogDisposition::Failed);
    assert!(failed_result.autoscan_report.is_none());
    assert!(!crate::report::autoscan_report_path(&failed_result.crash_log).exists());
    assert_eq!(
        failed_result
            .failures
            .iter()
            .map(|failure| (failure.stage, failure.message.as_str()))
            .collect::<Vec<_>>(),
        vec![(
            contract::LogFailureStage::Analysis,
            "injected analysis failure"
        )]
    );

    let succeeded_result = &result.logs[1];
    assert_eq!(succeeded_result.crash_log, succeeded);
    assert_eq!(
        succeeded_result.disposition,
        contract::LogDisposition::Succeeded
    );
    assert!(succeeded_result.failures.is_empty());
    let report = succeeded_result
        .autoscan_report
        .as_ref()
        .expect("the other admitted log should persist its Autoscan Report");
    assert!(report.is_file());
}

/// Verifies cancellation cannot publish Finished before Standard durable finalization resolves.
#[test]
fn admitted_standard_log_finishes_report_failure_and_movement_after_cancellation() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let _log = write_fixture_log_at(
        &root.join("Crash Logs"),
        "crash-cancelled-during-finalization.log",
    );
    let unsolved = root.join("Unsolved Logs");
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    configuration.max_concurrent = Some(1);
    let request = contract::Request::standard(
        configuration,
        StandardCrashLogScanSource {
            base_directory: root.to_path_buf(),
            custom_scan_directory: None,
            configured_documents_root: Some(root.join("Documents")),
        },
        StandardUnsolvedLogsIntent::MoveToCustom(unsolved.clone()),
    );
    let cancellation = contract::Cancellation::new();
    let observer_cancellation = cancellation.clone();
    let mut finished_saw_durable_state = false;
    let mut observer = |event| match event {
        contract::Event::DiscoveryCompleted(discovery) => {
            let accepted = discovery
                .accepted_logs
                .first()
                .expect("fixture should be discovered");
            std::fs::create_dir(crate::report::autoscan_report_path(accepted))
                .expect("a directory should force report persistence failure");
        }
        contract::Event::LogStarted(_) => observer_cancellation.cancel(),
        contract::Event::LogFinished {
            log: finished_log,
            disposition,
        } => {
            assert_eq!(disposition, contract::LogDisposition::Failed);
            let moved_log = unsolved.join(
                finished_log
                    .crash_log
                    .file_name()
                    .expect("discovered log should have a file name"),
            );
            finished_saw_durable_state = !finished_log.crash_log.exists() && moved_log.is_file();
        }
        _ => {}
    };

    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &cancellation,
            Some(&mut observer),
        ))
        .expect("admitted cancellation should resolve as terminal result data");

    assert!(finished_saw_durable_state);
    assert_eq!(result.logs.len(), 1);
    assert!(result.logs[0].moved_to_unsolved_logs);
    assert_eq!(
        result.logs[0]
            .failures
            .iter()
            .map(|failure| failure.stage)
            .collect::<Vec<_>>(),
        vec![contract::LogFailureStage::ReportWrite]
    );
}

/// Verifies a partial artifact move remains structured instead of being erased by a later failure.
#[test]
fn partial_unsolved_logs_movement_retains_moved_state_and_failure() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let _log = write_fixture_log_at(&root.join("Crash Logs"), "crash-partial-movement.log");
    let unsolved = root.join("Unsolved Logs");
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    configuration.max_concurrent = Some(1);
    let request = contract::Request::standard(
        configuration,
        StandardCrashLogScanSource {
            base_directory: root.to_path_buf(),
            custom_scan_directory: None,
            configured_documents_root: None,
        },
        StandardUnsolvedLogsIntent::MoveToCustom(unsolved.clone()),
    );
    let hooks = ScanRunTestHooks::default()
        .with_analysis_failure(0, "injected analysis failure")
        .with_movement_failure_after(1, "injected report movement failure");
    let mut observer = |event| {
        if let contract::Event::DiscoveryCompleted(discovery) = event {
            let accepted = discovery
                .accepted_logs
                .first()
                .expect("fixture should be discovered");
            std::fs::write(
                crate::report::autoscan_report_path(accepted),
                "existing report",
            )
            .expect("report fixture should be written");
        }
    };

    let result = get_runtime()
        .block_on(contract::execute_with_test_hooks(
            request,
            &contract::Cancellation::new(),
            Some(&mut observer),
            hooks,
        ))
        .expect("per-log failures should not become a run-wide error");

    assert_eq!(result.logs[0].disposition, contract::LogDisposition::Failed);
    assert!(result.logs[0].moved_to_unsolved_logs);
    let moved_log = unsolved.join(
        result.logs[0]
            .crash_log
            .file_name()
            .expect("discovered log should have a file name"),
    );
    let report = crate::report::autoscan_report_path(&result.logs[0].crash_log);
    assert!(moved_log.is_file());
    assert!(report.is_file());
    assert_eq!(
        result.logs[0]
            .failures
            .iter()
            .map(|failure| (failure.stage, failure.message.as_str()))
            .collect::<Vec<_>>(),
        vec![
            (
                contract::LogFailureStage::Analysis,
                "injected analysis failure"
            ),
            (
                contract::LogFailureStage::UnsolvedLogsFinalization,
                "injected report movement failure"
            ),
        ]
    );
}

/// Verifies the final Targeted request cannot relocate a log even when finalization fails.
#[test]
fn targeted_report_failure_cannot_trigger_unsolved_logs_movement() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let log = write_fixture_log(&temp, "crash-targeted-no-movement.log");
    std::fs::create_dir(crate::report::autoscan_report_path(&log))
        .expect("a directory should force report persistence failure");
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    configuration.max_concurrent = Some(1);
    let request = contract::Request::targeted(
        configuration,
        TargetedCrashLogScanSource {
            inputs: vec![log.clone()],
        },
    );

    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &contract::Cancellation::new(),
            None,
        ))
        .expect("report failure should remain per-log result data");

    assert!(log.is_file());
    assert!(!result.logs[0].moved_to_unsolved_logs);
    assert_eq!(
        result.logs[0]
            .failures
            .iter()
            .map(|failure| failure.stage)
            .collect::<Vec<_>>(),
        vec![contract::LogFailureStage::ReportWrite]
    );
}

/// Verifies Standard collision handling preserves the existing artifact and picks a suffix.
#[test]
fn standard_unsolved_logs_collision_preserves_existing_destination() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let _log = write_fixture_log_at(&root.join("Crash Logs"), "crash-collision.log");
    let unsolved = root.join("Unsolved Logs");
    std::fs::create_dir_all(&unsolved).expect("destination should be created");
    let existing = unsolved.join("crash-collision.log");
    std::fs::write(&existing, "existing").expect("existing destination should be written");
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    configuration.max_concurrent = Some(1);
    let request = contract::Request::standard(
        configuration,
        StandardCrashLogScanSource {
            base_directory: root.to_path_buf(),
            custom_scan_directory: None,
            configured_documents_root: Some(root.join("Documents")),
        },
        StandardUnsolvedLogsIntent::MoveToCustom(unsolved.clone()),
    );
    let mut observer = |event| {
        if let contract::Event::DiscoveryCompleted(discovery) = event {
            let accepted = discovery
                .accepted_logs
                .first()
                .expect("fixture should be discovered");
            std::fs::create_dir(crate::report::autoscan_report_path(accepted))
                .expect("a directory should force report persistence failure");
        }
    };

    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &contract::Cancellation::new(),
            Some(&mut observer),
        ))
        .expect("collision should be an ordinary per-log finalization outcome");

    assert!(result.logs[0].moved_to_unsolved_logs);
    assert_eq!(
        std::fs::read_to_string(&existing).expect("existing destination should remain readable"),
        "existing"
    );
    assert!(unsolved.join("crash-collision-1.log").is_file());
}

/// Verifies overlapping Standard runs atomically claim distinct collision destinations.
#[test]
fn overlapping_standard_runs_never_clobber_same_name_unsolved_logs() {
    let temp = tempdir().expect("tempdir should succeed");
    let destination = temp.path().join("Unsolved Logs");
    let build_run = |name: &str, contents: &str| {
        let root = temp.path().join(name);
        let data = root.join("CLASSIC Data");
        write_minimal_yaml_tree(&root, &data);
        let log = root.join("Crash Logs").join("crash-concurrent.log");
        std::fs::create_dir_all(log.parent().expect("log should have a parent"))
            .expect("Crash Logs directory should be created");
        std::fs::write(&log, contents).expect("run-unique Crash Log should be written");
        let request = contract::Request::standard(
            contract::Configuration {
                installation_root: root.clone(),
                game: GameId::Fallout4,
                game_version: "auto".to_string(),
                options: contract::Options::new(false, false),
                scan_facts: CrashLogScanFacts::default(),
                max_concurrent: Some(1),
            },
            StandardCrashLogScanSource {
                base_directory: root.clone(),
                custom_scan_directory: None,
                configured_documents_root: Some(root.join("Documents")),
            },
            StandardUnsolvedLogsIntent::MoveToCustom(destination.clone()),
        );
        let hooks = ScanRunTestHooks::default().with_analysis_failure(0, "injected failure");
        (request, hooks)
    };
    let (first_request, first_hooks) = build_run("first", "first run");
    let (second_request, second_hooks) = build_run("second", "second run");

    let (first, second) = get_runtime().block_on(async {
        let first_cancellation = contract::Cancellation::new();
        let second_cancellation = contract::Cancellation::new();
        tokio::join!(
            contract::execute_with_test_hooks(
                first_request,
                &first_cancellation,
                None,
                first_hooks,
            ),
            contract::execute_with_test_hooks(
                second_request,
                &second_cancellation,
                None,
                second_hooks,
            )
        )
    });

    assert!(first.expect("first run should complete").logs[0].moved_to_unsolved_logs);
    assert!(second.expect("second run should complete").logs[0].moved_to_unsolved_logs);
    let mut contents = [
        std::fs::read_to_string(destination.join("crash-concurrent.log"))
            .expect("first destination should exist"),
        std::fs::read_to_string(destination.join("crash-concurrent-1.log"))
            .expect("collision destination should exist"),
    ];
    contents.sort();
    assert_eq!(contents, ["first run", "second run"]);
}

/// Verifies a real destination filesystem error is preserved beside report failure.
#[test]
fn standard_unsolved_logs_filesystem_failure_is_structured() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let _log = write_fixture_log_at(&root.join("Crash Logs"), "crash-movement-error.log");
    let blocked_destination = root.join("blocked-destination");
    std::fs::write(&blocked_destination, "not a directory")
        .expect("blocking destination file should be written");
    let mut configuration = final_run_configuration();
    configuration.installation_root = root.to_path_buf();
    configuration.max_concurrent = Some(1);
    let request = contract::Request::standard(
        configuration,
        StandardCrashLogScanSource {
            base_directory: root.to_path_buf(),
            custom_scan_directory: None,
            configured_documents_root: Some(root.join("Documents")),
        },
        StandardUnsolvedLogsIntent::MoveToCustom(blocked_destination),
    );
    let mut observer = |event| {
        if let contract::Event::DiscoveryCompleted(discovery) = event {
            let accepted = discovery
                .accepted_logs
                .first()
                .expect("fixture should be discovered");
            std::fs::create_dir(crate::report::autoscan_report_path(accepted))
                .expect("a directory should force report persistence failure");
        }
    };

    let result = get_runtime()
        .block_on(contract::execute(
            request,
            &contract::Cancellation::new(),
            Some(&mut observer),
        ))
        .expect("filesystem failure should remain per-log result data");

    assert!(!result.logs[0].moved_to_unsolved_logs);
    assert_eq!(
        result.logs[0]
            .failures
            .iter()
            .map(|failure| failure.stage)
            .collect::<Vec<_>>(),
        vec![
            contract::LogFailureStage::ReportWrite,
            contract::LogFailureStage::UnsolvedLogsFinalization,
        ]
    );
}

/// Verifies every stable infrastructure stage preserves its message and optional path.
#[test]
fn injected_infrastructure_failures_preserve_every_stable_contract_field() {
    let fixtures = shared_failure_fixtures().infrastructure_errors;
    let cases = [
        (
            InfrastructureFault::RequestValidation,
            contract::InfrastructureErrorStage::RequestValidation,
        ),
        (
            InfrastructureFault::Discovery,
            contract::InfrastructureErrorStage::Discovery,
        ),
        (
            InfrastructureFault::Intake,
            contract::InfrastructureErrorStage::Intake,
        ),
        (
            InfrastructureFault::FormIdDatabaseAccess,
            contract::InfrastructureErrorStage::FormIdDatabaseAccess,
        ),
        (
            InfrastructureFault::Initialization,
            contract::InfrastructureErrorStage::Initialization,
        ),
        (
            InfrastructureFault::InternalInvariant,
            contract::InfrastructureErrorStage::InternalInvariant,
        ),
    ];

    assert_eq!(fixtures.len(), cases.len());
    for ((fault, stage), fixture) in cases.into_iter().zip(fixtures) {
        assert_eq!(fixture.stage, stage.as_str());
        let temp = tempdir().expect("tempdir should succeed");
        let root = temp.path();
        let data = root.join("CLASSIC Data");
        write_minimal_yaml_tree(root, &data);
        let log = write_fixture_log(&temp, "crash-shared-infrastructure.log");
        let mut configuration = final_run_configuration();
        configuration.installation_root = root.to_path_buf();
        configuration.max_concurrent = Some(1);
        let request = contract::Request::targeted(
            configuration,
            TargetedCrashLogScanSource {
                inputs: vec![log.clone()],
            },
        );
        let expected_path = fixture.path.as_ref().map(|path| root.join(path));
        if fault == InfrastructureFault::Discovery {
            assert_eq!(expected_path.as_ref(), Some(&log));
        }
        let hooks =
            ScanRunTestHooks::default().with_infrastructure_failure(fault, fixture.raw_message);

        let error = get_runtime()
            .block_on(contract::execute_with_test_hooks(
                request,
                &contract::Cancellation::new(),
                None,
                hooks,
            ))
            .expect_err("injected infrastructure failure should stop the run");

        assert_eq!(error.stage, stage);
        assert_eq!(error.message, fixture.message);
        assert_eq!(error.path, expected_path);
    }
}
