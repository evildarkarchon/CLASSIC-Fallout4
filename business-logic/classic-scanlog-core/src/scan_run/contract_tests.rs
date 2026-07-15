use crate::CrashLogScanFacts;
use crate::scan_run::contract;
use crate::scan_run::test_support::{write_fixture_log, write_minimal_yaml_tree};
use crate::scan_run::{
    CrashLogScanDiscoverySource, CrashLogScanOutcome, CrashLogScanRunLogOutcome,
    CrashLogScanSetupContext, StandardCrashLogScanSource, StandardUnsolvedLogsIntent,
    TargetedCrashLogScanSource,
};
use classic_shared_core::GameId;
use classic_shared_core::get_runtime;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use tempfile::tempdir;

fn final_run_configuration() -> contract::Configuration {
    contract::Configuration {
        yaml_dir_root: std::path::PathBuf::from("C:/CLASSIC"),
        yaml_dir_data: std::path::PathBuf::from("C:/CLASSIC/CLASSIC Data"),
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
    configuration.yaml_dir_root = temp.path().to_path_buf();
    configuration.yaml_dir_data = temp.path().join("CLASSIC Data");
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
    configuration.yaml_dir_root = temp.path().to_path_buf();
    configuration.yaml_dir_data = temp.path().join("CLASSIC Data");
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
    configuration.yaml_dir_root = root.to_path_buf();
    configuration.yaml_dir_data = data;
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
    configuration.yaml_dir_root = root.to_path_buf();
    configuration.yaml_dir_data = data;
    let request = contract::Request::standard(
        configuration,
        StandardCrashLogScanSource {
            base_directory: root.to_path_buf(),
            custom_scan_directory: None,
            configured_documents_root: None,
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
    configuration.yaml_dir_root = root.to_path_buf();
    configuration.yaml_dir_data = data;
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
    configuration.yaml_dir_root = root.to_path_buf();
    configuration.yaml_dir_data = data;
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
    configuration.yaml_dir_root = temp.path().to_path_buf();
    configuration.yaml_dir_data = temp.path().join("CLASSIC Data");
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
    let result = contract::LogResult::from(CrashLogScanRunLogOutcome {
        input_index: 0,
        crash_log: std::path::PathBuf::from("crash.log"),
        autoscan_report: None,
        outcome: CrashLogScanOutcome::Failed,
        report_write_failed: true,
        moved_to_unsolved_logs: false,
        unsolved_logs_finalization_failed: true,
        analysis_error: None,
        report_write_error: Some("report failed".to_string()),
        unsolved_logs_finalization_error: Some("move failed".to_string()),
        error: Some("report failed; move failed".to_string()),
        processing_time_us: 0,
        processing_time_ms: 0,
        formid_count: 0,
        plugin_count: 0,
        suspect_count: 0,
    });

    assert_eq!(result.disposition, contract::LogDisposition::Failed);
    assert_eq!(
        result
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

#[test]
fn final_operation_reports_effective_concurrency_and_stable_log_events() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let log_path = write_fixture_log(&temp, "crash-final-contract.log");
    let mut configuration = final_run_configuration();
    configuration.yaml_dir_root = root.to_path_buf();
    configuration.yaml_dir_data = data;
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

#[test]
fn observer_can_request_cancellation_before_discovered_logs_are_admitted() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let first = write_fixture_log(&temp, "crash-cancel-first.log");
    let second = write_fixture_log(&temp, "crash-cancel-second.log");
    let mut configuration = final_run_configuration();
    configuration.yaml_dir_root = root.to_path_buf();
    configuration.yaml_dir_data = data;
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
