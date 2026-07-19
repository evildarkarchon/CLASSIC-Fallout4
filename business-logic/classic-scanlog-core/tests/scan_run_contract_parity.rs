//! Cross-interface parity tests for the language-neutral Crash Log Scan Run corpus.

use classic_scanlog_core::CrashLogScanFacts;
use classic_scanlog_core::scan_run::contract;
use classic_scanlog_core::scan_run::{
    CrashLogScanDiscoverySource, StandardCrashLogScanSource, StandardUnsolvedLogsIntent,
    TargetedCrashLogScanSource,
};
use classic_shared_core::{GameId, get_runtime};
use serde::Deserialize;
use std::path::{Path, PathBuf};
use tempfile::tempdir;

const FIXTURE_ROOT: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../tests/fixtures/crash_log_scan_run"
);
const MANIFEST_JSON: &str =
    include_str!("../../../tests/fixtures/crash_log_scan_run/manifest.json");

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Manifest {
    contract_variants: Vec<String>,
    fixtures: Fixtures,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Fixtures {
    standard: FixtureCase,
    targeted: FixtureCase,
    installed_yaml_data: InstalledYamlDataFixture,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct InstalledYamlDataFixture {
    log_template: String,
    input: String,
    malformed_local_ignore: String,
    expected_existing: InstalledYamlDataExpected,
    expected_generated: InstalledYamlDataExpected,
    expected_recovery_required: InstalledYamlDataExpected,
    expected_proceed_without_ignore: InstalledYamlDataExpected,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct InstalledYamlDataExpected {
    main_provenance: String,
    game_provenance: String,
    local_ignore_state: String,
    diagnostic_kinds: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct FixtureCase {
    log_template: String,
    #[serde(default)]
    logs: Vec<String>,
    #[serde(default)]
    inputs: Vec<String>,
    max_concurrent: usize,
    expected: FixtureExpected,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct FixtureExpected {
    source: String,
    accepted_logs: Vec<String>,
    rejected_inputs: Vec<String>,
    effective_concurrency: usize,
    discovery_order: Vec<usize>,
    dispositions: Vec<String>,
    artifact_suffix: String,
    #[serde(default)]
    unsolved_logs_artifacts: Vec<String>,
}

/// Loads the language-neutral expectations used by every supported adapter.
fn manifest() -> Manifest {
    serde_json::from_str(MANIFEST_JSON).expect("shared scan-run manifest should be valid")
}

/// Copies the immutable YAML tree needed by one real Crash Log Scan Run.
fn copy_yaml_tree(destination: &Path) {
    let fixture_root = Path::new(FIXTURE_ROOT);
    let database_destination = destination.join("CLASSIC Data").join("databases");
    std::fs::create_dir_all(&database_destination)
        .expect("shared fixture database directory should be created");
    for relative in [
        Path::new("CLASSIC Data/CLASSIC Ignore.yaml"),
        Path::new("CLASSIC Data/databases/CLASSIC Main.yaml"),
        Path::new("CLASSIC Data/databases/CLASSIC Fallout4.yaml"),
    ] {
        let target = destination.join(relative);
        if let Some(parent) = target.parent() {
            std::fs::create_dir_all(parent).expect("fixture parent should be created");
        }
        std::fs::copy(fixture_root.join(relative), target)
            .expect("shared YAML fixture should be copied");
    }
}

/// Materializes named Crash Logs from the shared valid-log template.
fn copy_logs(destination: &Path, template: &str, logs: &[String]) -> Vec<PathBuf> {
    let source = Path::new(FIXTURE_ROOT).join(template);
    logs.iter()
        .map(|relative| {
            let target = destination.join(relative);
            std::fs::create_dir_all(target.parent().expect("fixture log should have a parent"))
                .expect("fixture log directory should be created");
            std::fs::copy(&source, &target).expect("shared Crash Log fixture should be copied");
            target
        })
        .collect()
}

/// Builds the shared configuration while leaving intent-specific facts to the request.
fn configuration(root: &Path, max_concurrent: usize) -> contract::Configuration {
    contract::Configuration {
        installation_root: root.to_path_buf(),
        game: GameId::Fallout4,
        game_version: "auto".to_string(),
        options: contract::Options::new(false, false),
        scan_facts: CrashLogScanFacts::default(),
        max_concurrent: Some(max_concurrent),
    }
}

/// Converts one temp-root path to the forward-slash relative form in the manifest.
fn relative(root: &Path, path: &Path) -> String {
    path.strip_prefix(root)
        .expect("fixture output should stay beneath its temp root")
        .to_string_lossy()
        .replace('\\', "/")
}

/// Returns the stable identifier for one observed event without inspecting internals.
fn event_kind(event: &contract::Event) -> &'static str {
    match event {
        contract::Event::DiscoveryCompleted(_) => "event.discovery_completed",
        contract::Event::EffectiveConcurrencySelected { .. } => {
            "event.effective_concurrency_selected"
        }
        contract::Event::LogQueued(_) => "event.log_queued",
        contract::Event::LogStarted(_) => "event.log_started",
        contract::Event::LogPhase { .. } => "event.log_phase",
        contract::Event::LogFinished { .. } => "event.log_finished",
    }
}

/// Returns the manifest token for Installed YAML Data provenance.
fn provenance_token(provenance: classic_config_core::InstalledYamlDataProvenance) -> &'static str {
    match provenance {
        classic_config_core::InstalledYamlDataProvenance::Updated => "updated",
        classic_config_core::InstalledYamlDataProvenance::Previous => "previous",
        classic_config_core::InstalledYamlDataProvenance::Bundled => "bundled",
    }
}

/// Returns the manifest token for Local Ignore snapshot state.
fn local_ignore_state_token(state: contract::LocalIgnoreRunState) -> &'static str {
    match state {
        contract::LocalIgnoreRunState::Existing => "existing",
        contract::LocalIgnoreRunState::Generated => "generated",
        contract::LocalIgnoreRunState::RecoveryRequired => "recovery_required",
        contract::LocalIgnoreRunState::ProceedWithoutIgnore => "proceed_without_ignore",
    }
}

/// Returns the manifest token for one Installed YAML Data diagnostic kind.
fn diagnostic_kind_token(kind: contract::InstalledYamlDataRunDiagnosticKind) -> &'static str {
    use contract::InstalledYamlDataRunDiagnosticKind as Kind;
    match kind {
        Kind::CacheUnavailable => "cache_unavailable",
        Kind::Missing => "missing",
        Kind::Read => "read",
        Kind::InvalidUtf8 => "invalid_utf8",
        Kind::Parse => "parse",
        Kind::InvalidSchema => "invalid_schema",
        Kind::IncompatibleSchema => "incompatible_schema",
        Kind::InvalidRoleData => "invalid_role_data",
        Kind::LocalIgnoreGenerated => "local_ignore_generated",
    }
}

/// Compares stable Installed YAML Data metadata exposed by the final operation.
fn assert_installed_yaml_data(result: &contract::RunResult, expected: &InstalledYamlDataExpected) {
    let installed = result
        .installed_yaml_data
        .as_ref()
        .expect("completed intake should expose Installed YAML Data metadata");
    assert_eq!(
        provenance_token(installed.main.provenance()),
        expected.main_provenance
    );
    assert_eq!(
        provenance_token(installed.game_file.provenance()),
        expected.game_provenance
    );
    assert_eq!(
        local_ignore_state_token(installed.local_ignore_state),
        expected.local_ignore_state
    );
    assert_eq!(
        installed
            .diagnostics
            .iter()
            .map(|diagnostic| diagnostic_kind_token(diagnostic.kind()).to_string())
            .collect::<Vec<_>>(),
        expected.diagnostic_kinds
    );
}

/// Compares one public terminal result with the path-normalized shared expectations.
fn assert_result(root: &Path, result: &contract::RunResult, expected: &FixtureExpected) {
    let discovery = result
        .discovery
        .as_ref()
        .expect("shared fixture should complete discovery");
    assert_eq!(discovery.source.as_str(), expected.source);
    assert_eq!(
        discovery
            .accepted_logs
            .iter()
            .map(|path| relative(root, path))
            .collect::<Vec<_>>(),
        expected.accepted_logs
    );
    assert_eq!(
        discovery
            .rejected_inputs
            .iter()
            .map(|input| relative(root, &input.path))
            .collect::<Vec<_>>(),
        expected.rejected_inputs
    );
    assert_eq!(
        result.effective_concurrency,
        Some(expected.effective_concurrency)
    );
    assert_eq!(
        result
            .logs
            .iter()
            .map(|log| log.discovery_index)
            .collect::<Vec<_>>(),
        expected.discovery_order
    );
    assert_eq!(
        result
            .logs
            .iter()
            .map(|log| log.disposition.as_str())
            .collect::<Vec<_>>(),
        expected.dispositions
    );
    for log in &result.logs {
        let report = log
            .autoscan_report
            .as_ref()
            .expect("successful shared fixture log should retain its report path");
        assert!(
            report
                .to_string_lossy()
                .ends_with(&expected.artifact_suffix)
        );
        assert!(report.is_file(), "durable Autoscan Report should exist");
    }
}

#[test]
#[serial_test::serial]
fn shared_standard_and_targeted_fixtures_match_normalized_contract() {
    let cache_root = tempdir().expect("isolated cache root should be created");
    temp_env::with_vars(
        [
            ("LOCALAPPDATA", Some(cache_root.path())),
            ("XDG_CACHE_HOME", Some(cache_root.path())),
        ],
        shared_standard_and_targeted_fixtures_match_normalized_contract_with_isolated_cache,
    );
}

/// Executes the shared public contract after its process cache environment is isolated.
fn shared_standard_and_targeted_fixtures_match_normalized_contract_with_isolated_cache() {
    let manifest = manifest();
    let expected_event_variants = manifest
        .contract_variants
        .iter()
        .filter(|variant| variant.starts_with("event."))
        .cloned()
        .collect::<std::collections::BTreeSet<_>>();

    // shared Standard fixture: Rust owns discovery, scheduling, ordering, and artifacts.
    let standard_temp = tempdir().expect("standard tempdir should be created");
    copy_yaml_tree(standard_temp.path());
    copy_logs(
        standard_temp.path(),
        &manifest.fixtures.standard.log_template,
        &manifest.fixtures.standard.logs,
    );
    let standard_request = contract::Request::standard(
        configuration(
            standard_temp.path(),
            manifest.fixtures.standard.max_concurrent,
        ),
        StandardCrashLogScanSource {
            base_directory: standard_temp.path().to_path_buf(),
            custom_scan_directory: None,
            // Prevent the shared fixture from inheriting the developer's real
            // Documents tree through platform path discovery.
            configured_documents_root: Some(standard_temp.path().join("Documents")),
        },
        StandardUnsolvedLogsIntent::LeaveInPlace,
    );
    let mut standard_events = Vec::new();
    let standard_result = get_runtime()
        .block_on(contract::execute(
            standard_request,
            &contract::Cancellation::new(),
            Some(&mut |event| standard_events.push(event)),
        ))
        .expect("shared Standard fixture should complete");
    assert_result(
        standard_temp.path(),
        &standard_result,
        &manifest.fixtures.standard.expected,
    );
    assert_eq!(
        standard_events
            .iter()
            .map(event_kind)
            .map(str::to_string)
            .collect::<std::collections::BTreeSet<_>>(),
        expected_event_variants
    );

    // shared Targeted fixture: rejected inputs stay typed and movement stays impossible.
    let targeted_temp = tempdir().expect("targeted tempdir should be created");
    copy_yaml_tree(targeted_temp.path());
    let targeted = &manifest.fixtures.targeted;
    let accepted_relatives = targeted
        .inputs
        .iter()
        .filter(|path| path.ends_with(".log"))
        .cloned()
        .collect::<Vec<_>>();
    copy_logs(
        targeted_temp.path(),
        &targeted.log_template,
        &accepted_relatives,
    );
    let targeted_request = contract::Request::targeted(
        configuration(targeted_temp.path(), targeted.max_concurrent),
        TargetedCrashLogScanSource {
            inputs: targeted
                .inputs
                .iter()
                .map(|path| targeted_temp.path().join(path))
                .collect(),
        },
    );
    let targeted_result = get_runtime()
        .block_on(contract::execute(
            targeted_request,
            &contract::Cancellation::new(),
            None,
        ))
        .expect("shared Targeted fixture should complete");
    assert_eq!(
        targeted_result
            .discovery
            .as_ref()
            .expect("Targeted discovery should be retained")
            .source,
        CrashLogScanDiscoverySource::Targeted
    );
    assert_result(targeted_temp.path(), &targeted_result, &targeted.expected);
    assert_eq!(
        targeted.expected.unsolved_logs_artifacts,
        Vec::<String>::new()
    );
    assert!(!targeted_temp.path().join("Unsolved Logs").exists());
}

#[test]
#[serial_test::serial]
fn shared_installed_yaml_data_fixture_preserves_report_bytes_when_ignore_is_generated() {
    let cache_root = tempdir().expect("isolated cache root should be created");
    temp_env::with_vars(
        [
            ("LOCALAPPDATA", Some(cache_root.path())),
            ("XDG_CACHE_HOME", Some(cache_root.path())),
        ],
        shared_installed_yaml_data_fixture_preserves_report_bytes_with_isolated_cache,
    );
}

/// Executes equivalent existing/generated Ignore runs against the shared final-operation fixture.
fn shared_installed_yaml_data_fixture_preserves_report_bytes_with_isolated_cache() {
    let manifest = manifest();
    let fixture = &manifest.fixtures.installed_yaml_data;
    let temp = tempdir().expect("Installed YAML Data fixture tempdir should be created");
    copy_yaml_tree(temp.path());
    let log = copy_logs(
        temp.path(),
        &fixture.log_template,
        std::slice::from_ref(&fixture.input),
    )
    .pop()
    .expect("shared Installed YAML Data fixture should contain one log");
    let request = contract::Request::targeted(
        configuration(temp.path(), 1),
        TargetedCrashLogScanSource {
            inputs: vec![log.clone()],
        },
    );

    let existing = get_runtime()
        .block_on(contract::execute(
            request.clone(),
            &contract::Cancellation::new(),
            None,
        ))
        .expect("existing Local Ignore fixture should complete");
    assert_installed_yaml_data(&existing, &fixture.expected_existing);
    let report_path = existing.logs[0]
        .autoscan_report
        .as_ref()
        .expect("existing Local Ignore run should write an Autoscan Report");
    let existing_report = std::fs::read(report_path)
        .expect("existing Local Ignore Autoscan Report should be readable");

    std::fs::remove_file(temp.path().join("CLASSIC Data/CLASSIC Ignore.yaml"))
        .expect("Local Ignore should be removed before generation coverage");
    let generated = get_runtime()
        .block_on(contract::execute(
            request.clone(),
            &contract::Cancellation::new(),
            None,
        ))
        .expect("generated Local Ignore fixture should complete");
    assert_installed_yaml_data(&generated, &fixture.expected_generated);
    let generated_report = std::fs::read(
        generated.logs[0]
            .autoscan_report
            .as_ref()
            .expect("generated Local Ignore run should write an Autoscan Report"),
    )
    .expect("generated Local Ignore Autoscan Report should be readable");

    assert_eq!(
        generated_report, existing_report,
        "Installed YAML Data diagnostics must remain outside report text"
    );

    let ignore_path = temp.path().join("CLASSIC Data/CLASSIC Ignore.yaml");
    let malformed_ignore = fixture.malformed_local_ignore.as_bytes();
    std::fs::write(&ignore_path, malformed_ignore)
        .expect("malformed Local Ignore fixture should be written");
    let mut recovery = get_runtime()
        .block_on(contract::execute(
            request,
            &contract::Cancellation::new(),
            None,
        ))
        .expect("malformed Local Ignore should return expected recovery data");
    assert_eq!(
        recovery.status,
        contract::RunStatus::LocalIgnoreRecoveryRequired
    );
    assert_installed_yaml_data(&recovery, &fixture.expected_recovery_required);
    let continuation = recovery
        .continuation
        .take()
        .expect("recovery-required fixture should retain an opaque continuation");
    let proceeded = get_runtime()
        .block_on(continuation.resume(
            contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
            &contract::Cancellation::new(),
            None,
        ))
        .expect("Proceed Without Ignore should complete the retained shared run");
    assert_installed_yaml_data(&proceeded, &fixture.expected_proceed_without_ignore);
    let proceeded_report = std::fs::read(
        proceeded.logs[0]
            .autoscan_report
            .as_ref()
            .expect("Proceed Without Ignore should write an Autoscan Report"),
    )
    .expect("Proceed Without Ignore Autoscan Report should be readable");
    assert_eq!(
        proceeded_report, existing_report,
        "operation-scoped empty ignores must not change shared Autoscan Report bytes"
    );
    assert_eq!(
        std::fs::read(ignore_path).expect("malformed Local Ignore should remain readable"),
        malformed_ignore
    );
}
