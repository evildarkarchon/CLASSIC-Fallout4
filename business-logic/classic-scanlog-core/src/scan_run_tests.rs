use super::*;
use crate::{AnalysisConfig, FormIdReadiness, SHORT_SCAN_CACHE_PROFILE};
use classic_shared_core::get_runtime;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use tempfile::tempdir;

const FIXTURE_LOG_SMALL: &str = include_str!("../benches/fixtures/crash-0DB9300.log");

fn make_ready_analysis() -> ScanReadyAnalysis {
    make_ready_analysis_with(None, None)
}

fn make_ready_analysis_with(
    paths: Option<crate::CrashLogScanIntakePaths>,
    unsolved_logs_destination: Option<std::path::PathBuf>,
) -> ScanReadyAnalysis {
    let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    config.crashgen_name = "Buffout 4".to_string();
    config.crashgen_latest = "1.26.2".to_string();
    config.game_version = "1.10.163".to_string();
    config.game_version_vr = "1.2.72".to_string();
    config.xse_acronym = "F4SE".to_string();

    ScanReadyAnalysis::new(
        config,
        FormIdReadiness {
            enabled: false,
            database_paths: Vec::new(),
        },
        SHORT_SCAN_CACHE_PROFILE,
        paths,
        unsolved_logs_destination,
    )
}

fn write_fixture_log(temp: &tempfile::TempDir, filename: &str) -> std::path::PathBuf {
    let log_path = temp.path().join(filename);
    std::fs::write(&log_path, FIXTURE_LOG_SMALL).expect("fixture log should be written");
    log_path
}

fn write_minimal_yaml_tree(root: &std::path::Path, data: &std::path::Path) {
    std::fs::create_dir_all(data.join("databases")).expect("database dir should be created");
    std::fs::write(
        data.join("databases").join("CLASSIC Main.yaml"),
        concat!(
            "CLASSIC_Info:\n",
            "  version: \"v9.1.0\"\n",
            "  version_date: \"2026-06-30\"\n",
            "CLASSIC_Interface:\n",
            "  autoscan_text_Fallout4: \"Autoscan Fallout 4\"\n",
            "catch_log_records:\n",
            "  - TESObjectREFR\n",
            "exclude_log_records:\n",
            "  - '(void*)'\n",
        ),
    )
    .expect("main YAML should be written");
    std::fs::write(
        data.join("databases").join("CLASSIC Fallout4.yaml"),
        concat!(
            "Game_Info:\n",
            "  XSE_Acronym: \"F4SE\"\n",
            "  GameVersion: \"1.10.163\"\n",
            "  CRASHGEN_LatestVer: \"1.28.6\"\n",
            "  CRASHGEN_LogName: \"Buffout 4\"\n",
            "  Main_Root_Name: \"Fallout4\"\n",
            "Crashlog_Plugins_Exclude: []\n",
            "Crashlog_Records_Exclude: []\n",
            "Crashgen_Registry:\n",
            "  default:\n",
            "    display_section: \"\"\n",
            "    ignore_keys: []\n",
            "    checks: []\n",
        ),
    )
    .expect("game YAML should be written");
    std::fs::write(
        root.join("CLASSIC Ignore.yaml"),
        "CLASSIC_Ignore_Fallout4:\n  - IgnoreThis.dll\n",
    )
    .expect("ignore YAML should be written");
}

fn service_request(
    root: &std::path::Path,
    source: CrashLogScanSource,
    options: CrashLogScanOptions,
) -> CrashLogScanRunServiceRequest {
    CrashLogScanRunServiceRequest {
        yaml_dir_root: root.to_path_buf(),
        yaml_dir_data: root.join("CLASSIC Data"),
        game: "Fallout4".to_string(),
        game_version: "auto".to_string(),
        options,
        source,
        setup_context: None,
        move_unsolved_logs: false,
        scan_facts: CrashLogScanFacts::default(),
        max_concurrent: Some(1),
        cancellation: None,
        preserve_order: true,
    }
}

fn standard_request(
    log_path: std::path::PathBuf,
    unsolved_logs: StandardUnsolvedLogsIntent,
) -> CrashLogScanRunRequest {
    CrashLogScanRunRequest {
        logs: vec![log_path],
        intent: CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent { unsolved_logs }),
        max_concurrent: Some(1),
        cancellation: None,
        preserve_order: true,
    }
}

#[test]
fn service_standard_discovery_no_logs_returns_status_and_discovery_data() {
    let temp = tempdir().expect("tempdir should succeed");
    let source = CrashLogScanSource::Standard(StandardCrashLogScanSource {
        base_directory: temp.path().to_path_buf(),
        custom_scan_directory: None,
        configured_documents_root: Some(temp.path().join("Docs")),
    });

    let result = get_runtime()
        .block_on(CrashLogScanRunService::execute(
            service_request(temp.path(), source, CrashLogScanOptions::default()),
            |_| {},
        ))
        .expect("no-log discovery should be an expected result");

    assert_eq!(result.status, CrashLogScanRunStatus::NoCrashLogsFound);
    let discovery = result.discovery.expect("discovery data should be present");
    assert_eq!(discovery.source, CrashLogScanDiscoverySource::Standard);
    assert!(discovery.accepted_logs.is_empty());
    assert!(discovery.rejected_inputs.is_empty());
    assert!(temp.path().join("Crash Logs").exists());
    assert!(temp.path().join("Crash Logs").join("Pastebin").exists());
}

#[test]
fn service_targeted_rejections_are_discovery_data() {
    let temp = tempdir().expect("tempdir should succeed");
    let missing = temp.path().join("missing.log");
    let source = CrashLogScanSource::Targeted(TargetedCrashLogScanSource {
        inputs: vec![missing.clone()],
    });

    let result = get_runtime()
        .block_on(CrashLogScanRunService::execute(
            service_request(temp.path(), source, CrashLogScanOptions::default()),
            |_| {},
        ))
        .expect("targeted rejection should not be an infrastructure error");

    assert_eq!(result.status, CrashLogScanRunStatus::NoCrashLogsFound);
    let discovery = result.discovery.expect("discovery data should be present");
    assert_eq!(discovery.source, CrashLogScanDiscoverySource::Targeted);
    assert!(discovery.accepted_logs.is_empty());
    assert_eq!(discovery.rejected_inputs.len(), 1);
    assert_eq!(discovery.rejected_inputs[0].path, missing);
    assert!(
        discovery.rejected_inputs[0]
            .reason
            .contains("does not exist")
    );
}

#[test]
fn service_fcx_mode_without_setup_context_returns_setup_failed_result() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "manual-selection.txt");
    let source = CrashLogScanSource::Targeted(TargetedCrashLogScanSource {
        inputs: vec![log_path.clone()],
    });

    let result = get_runtime()
        .block_on(CrashLogScanRunService::execute(
            service_request(
                temp.path(),
                source,
                CrashLogScanOptions::new(false, true, false),
            ),
            |_| {},
        ))
        .expect("missing setup facts should be result data");

    assert_eq!(result.status, CrashLogScanRunStatus::SetupFailed);
    assert_eq!(
        result
            .discovery
            .as_ref()
            .expect("discovery should be present")
            .accepted_logs,
        vec![log_path]
    );
    let setup = result.setup.expect("setup result should be present");
    assert_eq!(setup.status, "action_required");
    assert!(setup.actions.contains(&"provide_setup_context".to_string()));
    assert!(
        setup
            .message
            .as_deref()
            .is_some_and(|message| message.contains("Setup Context"))
    );
}

#[test]
fn fcx_config_checks_use_game_root_resolved_from_configured_executable() {
    let temp = tempdir().expect("tempdir should succeed");
    let game_root = temp.path().join("Fallout4");
    let docs_root = temp.path().join("Docs");
    std::fs::create_dir_all(&game_root).expect("game root should be created");
    std::fs::create_dir_all(&docs_root).expect("docs root should be created");
    let game_exe_path = game_root.join("Fallout4.exe");
    std::fs::write(&game_exe_path, b"not a real PE").expect("game executable should be written");
    std::fs::write(
        game_root.join("epo.ini"),
        "[Particles]\niMaxDesired = 6001\n",
    )
    .expect("problematic config should be written");
    let source = CrashLogScanSource::Targeted(TargetedCrashLogScanSource { inputs: Vec::new() });
    let mut request = service_request(
        temp.path(),
        source,
        CrashLogScanOptions::new(false, true, false),
    );
    request.game_version = "Original".to_string();
    request.setup_context = Some(CrashLogScanSetupContext {
        game_root: None,
        docs_root: Some(docs_root),
        game_exe_path: Some(game_exe_path),
        xse_log_path: None,
    });

    let (setup, _) = evaluate_setup_for_scan(&request);

    let setup = setup.expect("FCX setup result should be present");
    assert!(
        setup
            .configuration_issues
            .iter()
            .any(|issue| { issue.setting == "iMaxDesired" && issue.current_value == "6001" })
    );
}

#[test]
fn service_standard_discovery_runs_analysis_and_attaches_discovery() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let source_log = root.join("crash-service-success.log");
    std::fs::write(&source_log, FIXTURE_LOG_SMALL).expect("source log should be written");
    let source = CrashLogScanSource::Standard(StandardCrashLogScanSource {
        base_directory: root.to_path_buf(),
        custom_scan_directory: None,
        configured_documents_root: Some(root.join("Docs")),
    });
    let mut events = Vec::new();

    let result = get_runtime()
        .block_on(CrashLogScanRunService::execute(
            service_request(root, source, CrashLogScanOptions::default()),
            |event| events.push(event),
        ))
        .expect("standard service run should succeed");

    let accepted_log = root.join("Crash Logs").join("crash-service-success.log");
    assert_eq!(result.status, CrashLogScanRunStatus::Completed);
    assert_eq!(result.total, 1);
    assert_eq!(result.succeeded, 1);
    assert!(!source_log.exists());
    assert_eq!(
        result
            .discovery
            .as_ref()
            .expect("discovery should be present")
            .accepted_logs,
        vec![accepted_log.clone()]
    );
    assert_eq!(result.logs[0].crash_log, accepted_log);
    assert!(
        events
            .iter()
            .any(|event| event.kind == CrashLogScanRunEventKind::Started)
    );
}

#[test]
fn standard_scan_run_writes_autoscan_report() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-success.log");
    let run = CrashLogScanRun::new(make_ready_analysis());
    let mut events = Vec::new();

    let result = get_runtime()
        .block_on(run.run(
            standard_request(log_path.clone(), StandardUnsolvedLogsIntent::LeaveInPlace),
            |event| {
                events.push(event);
            },
        ))
        .expect("scan run should succeed");

    let autoscan_path = temp.path().join("crash-success-AUTOSCAN.md");
    assert_eq!(result.total, 1);
    assert_eq!(result.succeeded, 1);
    assert_eq!(result.failed, 0);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Succeeded);
    assert!(!result.logs[0].report_write_failed);
    assert_eq!(result.logs[0].autoscan_report, Some(autoscan_path.clone()));
    assert!(autoscan_path.exists());
    assert!(
        events
            .iter()
            .any(|event| event.kind == CrashLogScanRunEventKind::Completed)
    );
}

#[test]
fn standard_scan_run_leave_in_place_does_not_move_failed_log() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-leave-fail.log");
    let autoscan_path = temp.path().join("crash-leave-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let result = get_runtime()
        .block_on(run.run(
            standard_request(log_path.clone(), StandardUnsolvedLogsIntent::LeaveInPlace),
            |_| {},
        ))
        .expect("scan run should return per-log failure");

    assert_eq!(result.succeeded, 0);
    assert_eq!(result.failed, 1);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Failed);
    assert!(result.logs[0].report_write_failed);
    assert!(!result.logs[0].moved_to_unsolved_logs);
    assert!(log_path.exists());
}

#[test]
fn standard_scan_run_configured_or_default_uses_canonical_destination_from_intake_paths() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-canonical-fail.log");
    let autoscan_path = temp.path().join("crash-canonical-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let unsolved_dir = temp.path().join("CLASSIC Backup").join("Unsolved Logs");
    let paths = crate::CrashLogScanIntakePaths::new(temp.path(), temp.path().join("CLASSIC Data"));
    let run = CrashLogScanRun::new(make_ready_analysis_with(Some(paths), None));

    let result = get_runtime()
        .block_on(run.run(
            standard_request(
                log_path.clone(),
                StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
            ),
            |_| {},
        ))
        .expect("scan run should return per-log failure");

    assert_eq!(result.succeeded, 0);
    assert_eq!(result.failed, 1);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Failed);
    assert!(result.logs[0].moved_to_unsolved_logs);
    assert!(!log_path.exists());
    assert!(unsolved_dir.join("crash-canonical-fail.log").exists());
}

#[test]
fn standard_scan_run_configured_or_default_uses_configured_destination() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-configured-fail.log");
    let autoscan_path = temp.path().join("crash-configured-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let configured_dir = temp.path().join("user-selected-unsolved");
    let paths = crate::CrashLogScanIntakePaths::new(temp.path(), temp.path().join("CLASSIC Data"));
    let run = CrashLogScanRun::new(make_ready_analysis_with(
        Some(paths),
        Some(configured_dir.clone()),
    ));

    let result = get_runtime()
        .block_on(run.run(
            standard_request(
                log_path.clone(),
                StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
            ),
            |_| {},
        ))
        .expect("scan run should return per-log failure");

    assert_eq!(result.failed, 1);
    assert!(result.logs[0].moved_to_unsolved_logs);
    assert!(!log_path.exists());
    assert!(configured_dir.join("crash-configured-fail.log").exists());
}

#[test]
fn standard_scan_run_configured_or_default_without_destination_source_fails_setup() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-no-destination-source.log");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let error = match get_runtime().block_on(run.run(
        standard_request(
            log_path.clone(),
            StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
        ),
        |_| {},
    )) {
        Ok(_) => panic!("missing destination source should fail setup"),
        Err(error) => error,
    };

    assert!(matches!(error, ScanLogError::InvalidInput(_)));
    assert!(log_path.exists());
}

#[test]
fn standard_scan_run_relative_custom_destination_fails_setup() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-relative-destination.log");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let error = match get_runtime().block_on(run.run(
        standard_request(
            log_path.clone(),
            StandardUnsolvedLogsIntent::MoveToCustom(std::path::PathBuf::from("relative")),
        ),
        |_| {},
    )) {
        Ok(_) => panic!("relative custom destination should fail setup"),
        Err(error) => error,
    };

    assert!(matches!(error, ScanLogError::InvalidInput(_)));
    assert!(log_path.exists());
}

#[test]
fn standard_scan_run_custom_destination_moves_failed_log_to_unsolved_logs() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-write-fail.log");
    let autoscan_path = temp.path().join("crash-write-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let unsolved_dir = temp.path().join("custom-unsolved");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let result = get_runtime()
        .block_on(run.run(
            standard_request(
                log_path.clone(),
                StandardUnsolvedLogsIntent::MoveToCustom(unsolved_dir.clone()),
            ),
            |_| {},
        ))
        .expect("scan run should return per-log failure");

    assert_eq!(result.succeeded, 0);
    assert_eq!(result.failed, 1);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Failed);
    assert!(result.logs[0].moved_to_unsolved_logs);
    assert!(!log_path.exists());
    assert!(unsolved_dir.join("crash-write-fail.log").exists());
}

#[test]
fn standard_scan_run_unwritable_custom_destination_remains_per_log_failure() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-unwritable-fail.log");
    let autoscan_path = temp.path().join("crash-unwritable-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let blocked_destination = temp.path().join("blocked-destination");
    std::fs::write(&blocked_destination, "not a directory")
        .expect("destination blocker should be written");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let result = get_runtime()
        .block_on(run.run(
            standard_request(
                log_path.clone(),
                StandardUnsolvedLogsIntent::MoveToCustom(blocked_destination.clone()),
            ),
            |_| {},
        ))
        .expect("unwritable destination should be a per-log failure");

    assert_eq!(result.failed, 1);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Failed);
    assert!(!result.logs[0].moved_to_unsolved_logs);
    assert!(result.logs[0].error.is_some());
    assert!(log_path.exists());
    assert!(blocked_destination.is_file());
}

#[test]
fn standard_scan_run_preserves_existing_unsolved_log() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-overwrite-fail.log");
    let autoscan_path = temp.path().join("crash-overwrite-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let unsolved_dir = temp.path().join("custom-unsolved");
    std::fs::create_dir_all(&unsolved_dir).expect("unsolved directory should be created");
    let unsolved_log_path = unsolved_dir.join("crash-overwrite-fail.log");
    std::fs::write(&unsolved_log_path, "stale unsolved log")
        .expect("stale unsolved log should be written");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let result = get_runtime()
        .block_on(run.run(
            standard_request(
                log_path.clone(),
                StandardUnsolvedLogsIntent::MoveToCustom(unsolved_dir.clone()),
            ),
            |_| {},
        ))
        .expect("scan run should return per-log failure");

    assert_eq!(result.succeeded, 0);
    assert_eq!(result.failed, 1);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Failed);
    assert!(result.logs[0].moved_to_unsolved_logs);
    assert!(!log_path.exists());
    assert_eq!(
        std::fs::read_to_string(&unsolved_log_path).expect("stale log should be readable"),
        "stale unsolved log"
    );
    assert_eq!(
        std::fs::read_to_string(unsolved_dir.join("crash-overwrite-fail-1.log"))
            .expect("moved log should be readable"),
        FIXTURE_LOG_SMALL
    );
}

#[test]
fn move_unsolved_artifacts_preserves_existing_log_and_report_destinations() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = temp.path().join("crash-overwrite-artifacts.log");
    let report_path = temp.path().join("crash-overwrite-artifacts-AUTOSCAN.md");
    let unsolved_dir = temp.path().join("custom-unsolved");
    std::fs::create_dir_all(&unsolved_dir).expect("unsolved directory should be created");
    let unsolved_log_path = unsolved_dir.join("crash-overwrite-artifacts.log");
    let unsolved_report_path = unsolved_dir.join("crash-overwrite-artifacts-AUTOSCAN.md");
    std::fs::write(&log_path, "new log contents").expect("source log should be written");
    std::fs::write(&report_path, "new report contents").expect("source report should be written");
    std::fs::write(&unsolved_log_path, "stale log contents").expect("stale log should be written");
    std::fs::write(&unsolved_report_path, "stale report contents")
        .expect("stale report should be written");

    let moved = get_runtime()
        .block_on(move_unsolved_artifacts(&log_path, &unsolved_dir))
        .expect("artifacts should move to unique destinations");

    assert!(moved);
    assert!(!log_path.exists());
    assert!(!report_path.exists());
    assert_eq!(
        std::fs::read_to_string(&unsolved_log_path).expect("stale log should be readable"),
        "stale log contents"
    );
    assert_eq!(
        std::fs::read_to_string(&unsolved_report_path).expect("stale report should be readable"),
        "stale report contents"
    );
    assert_eq!(
        std::fs::read_to_string(unsolved_dir.join("crash-overwrite-artifacts-1.log"))
            .expect("moved log should be readable"),
        "new log contents"
    );
    assert_eq!(
        std::fs::read_to_string(unsolved_dir.join("crash-overwrite-artifacts-AUTOSCAN-1.md"))
            .expect("moved report should be readable"),
        "new report contents"
    );
}

#[test]
fn targeted_scan_run_does_not_move_failed_log_to_unsolved_logs() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-targeted-fail.log");
    let autoscan_path = temp.path().join("crash-targeted-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let unsolved_dir = temp.path().join("CLASSIC Backup").join("Unsolved Logs");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let result = get_runtime()
        .block_on(run.run(
            CrashLogScanRunRequest {
                logs: vec![log_path.clone()],
                intent: CrashLogScanRunIntent::Targeted,
                max_concurrent: Some(1),
                cancellation: None,
                preserve_order: true,
            },
            |_| {},
        ))
        .expect("scan run should return per-log failure");

    assert_eq!(result.failed, 1);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Failed);
    assert!(!result.logs[0].moved_to_unsolved_logs);
    assert!(log_path.exists());
    assert!(!unsolved_dir.exists());
}

#[test]
fn cancellation_before_start_is_counted_separately() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-cancelled.log");
    let cancellation = Arc::new(AtomicBool::new(true));
    let run = CrashLogScanRun::new(make_ready_analysis());

    let result = get_runtime()
        .block_on(run.run(
            CrashLogScanRunRequest {
                logs: vec![log_path],
                intent: CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent {
                    unsolved_logs: StandardUnsolvedLogsIntent::LeaveInPlace,
                }),
                max_concurrent: Some(1),
                cancellation: Some(Arc::clone(&cancellation)),
                preserve_order: true,
            },
            |_| {},
        ))
        .expect("scan run should complete with cancellation outcome");

    assert!(cancellation.load(Ordering::Relaxed));
    assert_eq!(result.succeeded, 0);
    assert_eq!(result.failed, 0);
    assert_eq!(result.cancelled, 1);
    assert_eq!(
        result.logs[0].outcome,
        CrashLogScanOutcome::CancelledBeforeStart
    );
}

#[test]
fn from_adapter_flags_targeted_wins_over_move_and_destination() {
    let intent = CrashLogScanRunIntent::from_adapter_flags(true, true, Some("C:/custom/unsolved"));

    assert!(matches!(intent, CrashLogScanRunIntent::Targeted));
}

#[test]
fn from_adapter_flags_move_disabled_leaves_in_place_and_ignores_destination() {
    let intent =
        CrashLogScanRunIntent::from_adapter_flags(false, false, Some("C:/custom/unsolved"));

    assert!(matches!(
        intent,
        CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent {
            unsolved_logs: StandardUnsolvedLogsIntent::LeaveInPlace,
        })
    ));
}

#[test]
fn from_adapter_flags_move_with_destination_trims_to_custom() {
    let intent =
        CrashLogScanRunIntent::from_adapter_flags(false, true, Some("  C:/custom/unsolved  "));

    match intent {
        CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent {
            unsolved_logs: StandardUnsolvedLogsIntent::MoveToCustom(destination),
        }) => assert_eq!(destination, std::path::PathBuf::from("C:/custom/unsolved")),
        _ => panic!("expected standard custom destination intent"),
    }
}

#[test]
fn from_adapter_flags_move_with_whitespace_destination_uses_configured_or_default() {
    let intent = CrashLogScanRunIntent::from_adapter_flags(false, true, Some("   "));

    assert!(matches!(
        intent,
        CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent {
            unsolved_logs: StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
        })
    ));
}

#[test]
fn from_adapter_flags_move_without_destination_uses_configured_or_default() {
    let intent = CrashLogScanRunIntent::from_adapter_flags(false, true, None);

    assert!(matches!(
        intent,
        CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent {
            unsolved_logs: StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
        })
    ));
}

#[test]
fn from_configured_flags_move_with_path_uses_custom_destination() {
    let destination = std::path::PathBuf::from("C:/custom/unsolved");

    let intent =
        CrashLogScanRunIntent::from_configured_flags(false, true, Some(destination.clone()));

    match intent {
        CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent {
            unsolved_logs: StandardUnsolvedLogsIntent::MoveToCustom(custom),
        }) => assert_eq!(custom, destination),
        _ => panic!("expected standard custom destination intent"),
    }
}

#[test]
fn normalize_scan_run_concurrency_folds_zero_to_adaptive() {
    assert_eq!(normalize_scan_run_concurrency(None), None);
    assert_eq!(normalize_scan_run_concurrency(Some(0)), None);
    assert_eq!(normalize_scan_run_concurrency(Some(1)), Some(1));
    assert_eq!(normalize_scan_run_concurrency(Some(8)), Some(8));
}

#[test]
fn scan_run_treats_zero_max_concurrent_as_adaptive_default() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-zero-concurrency.log");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let result = get_runtime()
        .block_on(run.run(
            CrashLogScanRunRequest {
                logs: vec![log_path.clone()],
                intent: CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent {
                    unsolved_logs: StandardUnsolvedLogsIntent::LeaveInPlace,
                }),
                max_concurrent: Some(0),
                cancellation: None,
                preserve_order: true,
            },
            |_| {},
        ))
        .expect("scan run should succeed with adaptive concurrency");

    assert_eq!(result.total, 1);
    assert_eq!(result.succeeded, 1);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Succeeded);
}
