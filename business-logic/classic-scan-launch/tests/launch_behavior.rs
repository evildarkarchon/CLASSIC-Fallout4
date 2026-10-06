//! Behavioral checks for Crash Log Scan Launch through its public interface.
//!
//! Every case writes a User Settings document into a temporary Installation Root and
//! observes only the launch request, its diagnostics, its typed errors, and the bytes on
//! disk.

use classic_scan_launch::{
    CrashLogScanIntent, CrashLogScanLaunchDiagnosticKind, CrashLogScanLaunchError,
    CrashLogScanLaunchErrorKind, CrashLogScanLaunchOverrides, CrashLogScanLaunchRequest,
    GameVersionSelection, MaxConcurrency, prepare_launch,
};
use classic_scanlog_core::StandardUnsolvedLogsIntent;
use classic_scanlog_core::scan_run::contract::Request;
use classic_shared_core::GameId;
use std::num::NonZeroUsize;
use std::path::{Path, PathBuf};
use tempfile::TempDir;

/// Creates an Installation Root whose canonical User Settings document holds `yaml`.
fn root_with_settings(yaml: &str) -> TempDir {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(root.path().join("CLASSIC Settings.yaml"), yaml).unwrap();
    root
}

/// Quotes an absolute path as a single-quoted YAML scalar so backslashes stay literal.
fn yaml_path(path: &Path) -> String {
    format!("'{}'", path.display().to_string().replace('\'', "''"))
}

/// Launches a Standard scan with no overrides and unwraps the launch request.
fn standard(root: &Path) -> CrashLogScanLaunchRequest {
    prepare_launch(
        root,
        CrashLogScanIntent::Standard,
        &CrashLogScanLaunchOverrides::new(),
    )
    .expect("a Standard launch with no overrides is valid")
}

/// Returns the FormID database rows the request carries, as plain strings.
fn formid_rows(launch: &CrashLogScanLaunchRequest) -> Vec<String> {
    launch
        .request()
        .configuration()
        .scan_facts
        .formid_database_paths
        .iter()
        .map(|path| path.to_string_lossy().into_owned())
        .collect()
}

/// Returns the diagnostic codes the launch reports, in order.
fn diagnostic_codes(launch: &CrashLogScanLaunchRequest) -> Vec<&str> {
    launch
        .diagnostics()
        .iter()
        .map(|diagnostic| diagnostic.code())
        .collect()
}

const MANAGED_FALLOUT4: &str = r#"schema_version: "1.0"
CLASSIC_Settings:
  Managed Game: Fallout 4
  Game Version: NextGen
  FCX Mode: false
  Simplify Logs: true
  Show FormID Values: true
  Move Unsolved Logs: false
  Max Concurrent Scans: 3
  FormID Databases:
    Fallout4:
      - databases/Fallout4 FormIDs.db
"#;

#[test]
fn standard_launch_projects_saved_settings_for_the_managed_game() {
    let root = root_with_settings(MANAGED_FALLOUT4);

    let launch = standard(root.path());

    let configuration = launch.request().configuration();
    assert_eq!(configuration.installation_root, root.path());
    assert_eq!(configuration.game, GameId::Fallout4);
    assert_eq!(configuration.game_version, "NextGen");
    assert!(configuration.options.show_formid_values);
    assert!(configuration.options.simplify_logs);
    assert_eq!(configuration.max_concurrent, Some(3));
    assert_eq!(formid_rows(&launch), ["databases/Fallout4 FormIDs.db"]);
    assert_eq!(configuration.scan_facts.unsolved_logs_destination, None);
    let Request::Standard(request) = launch.request() else {
        panic!("a Standard intent must produce a Standard request");
    };
    assert_eq!(request.source().base_directory, root.path());
    assert_eq!(request.source().custom_scan_directory, None);
    assert_eq!(
        request.unsolved_logs(),
        &StandardUnsolvedLogsIntent::LeaveInPlace
    );
    assert!(!request.fcx_enabled());
    assert!(launch.setup_context().is_none());
    assert!(launch.diagnostics().is_empty());
}

#[test]
fn explicit_value_overrides_win_over_saved_values() {
    let root = root_with_settings(MANAGED_FALLOUT4);
    let scan_folder = root.path().join("one-off scan");
    let overrides = CrashLogScanLaunchOverrides::new()
        .with_game(GameId::Fallout4)
        .with_game_version(GameVersionSelection::AnniversaryEdition)
        .with_scan_path(&scan_folder)
        .with_max_concurrency(MaxConcurrency::Limit(NonZeroUsize::new(7).unwrap()));

    let launch = prepare_launch(root.path(), CrashLogScanIntent::Standard, &overrides).unwrap();

    let configuration = launch.request().configuration();
    assert_eq!(configuration.game, GameId::Fallout4);
    assert_eq!(configuration.game_version, "AnniversaryEdition");
    assert_eq!(configuration.max_concurrent, Some(7));
    let Request::Standard(request) = launch.request() else {
        panic!("a Standard intent must produce a Standard request");
    };
    assert_eq!(
        request.source().custom_scan_directory.as_deref(),
        Some(scan_folder.as_path())
    );
}

#[test]
fn game_override_selects_the_scanned_games_formid_rows() {
    let root = root_with_settings(MANAGED_FALLOUT4);

    let launch = prepare_launch(
        root.path(),
        CrashLogScanIntent::Standard,
        &CrashLogScanLaunchOverrides::new().with_game(GameId::Skyrim),
    )
    .unwrap();

    assert_eq!(launch.request().configuration().game, GameId::Skyrim);
    assert!(formid_rows(&launch).is_empty());
}

#[test]
fn supplied_as_on_overrides_turn_options_on_and_absence_keeps_the_saved_value() {
    let saved_off = root_with_settings(
        r#"schema_version: "1.0"
CLASSIC_Settings:
  Managed Game: Fallout 4
  Simplify Logs: false
  Show FormID Values: false
"#,
    );
    let switched_on = prepare_launch(
        saved_off.path(),
        CrashLogScanIntent::Standard,
        &CrashLogScanLaunchOverrides::new()
            .with_show_formid_values()
            .with_simplify_logs(),
    )
    .unwrap();
    assert!(
        switched_on
            .request()
            .configuration()
            .options
            .show_formid_values
    );
    assert!(switched_on.request().configuration().options.simplify_logs);

    let kept_off = standard(saved_off.path());
    assert!(
        !kept_off
            .request()
            .configuration()
            .options
            .show_formid_values
    );
    assert!(!kept_off.request().configuration().options.simplify_logs);

    // Not supplying the override never turns a saved option off.
    let saved_on = root_with_settings(MANAGED_FALLOUT4);
    let kept_on = standard(saved_on.path());
    assert!(kept_on.request().configuration().options.show_formid_values);
    assert!(kept_on.request().configuration().options.simplify_logs);
}

#[test]
fn adaptive_concurrency_override_beats_a_saved_limit() {
    let root = root_with_settings(MANAGED_FALLOUT4);

    let launch = prepare_launch(
        root.path(),
        CrashLogScanIntent::Standard,
        &CrashLogScanLaunchOverrides::new().with_max_concurrency(MaxConcurrency::Adaptive),
    )
    .unwrap();

    assert_eq!(launch.request().configuration().max_concurrent, None);
}

#[test]
fn saved_zero_concurrency_selects_adaptively() {
    let root = root_with_settings(
        r#"schema_version: "1.0"
CLASSIC_Settings:
  Managed Game: Fallout 4
  Max Concurrent Scans: 0
"#,
    );

    assert_eq!(
        standard(root.path())
            .request()
            .configuration()
            .max_concurrent,
        None
    );
}

#[test]
fn standard_base_folder_is_the_installation_root_and_the_saved_custom_scan_folder_applies() {
    let root = tempfile::tempdir().unwrap();
    let custom = root.path().join("Saved Custom Logs");
    let destination = root.path().join("Unsolved Elsewhere");
    let documents = root.path().join("Documents");
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        format!(
            "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4\n  \
             Move Unsolved Logs: true\n  SCAN Custom Path: {}\n  \
             Unsolved Logs Destination: {}\n  Documents Folder Path: {}\n",
            yaml_path(&custom),
            yaml_path(&destination),
            yaml_path(&documents)
        ),
    )
    .unwrap();

    let launch = standard(root.path());

    let Request::Standard(request) = launch.request() else {
        panic!("a Standard intent must produce a Standard request");
    };
    assert_eq!(request.source().base_directory, root.path());
    assert_eq!(
        request.source().custom_scan_directory.as_deref(),
        Some(custom.as_path())
    );
    assert_eq!(
        request.source().configured_documents_root.as_deref(),
        Some(documents.as_path())
    );
    assert_eq!(
        request.unsolved_logs(),
        &StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault
    );
    assert_eq!(
        launch
            .request()
            .configuration()
            .scan_facts
            .unsolved_logs_destination
            .as_deref(),
        Some(destination.as_path())
    );
    assert!(
        launch.diagnostics().is_empty(),
        "{:?}",
        launch.diagnostics()
    );
}

#[test]
fn scan_path_override_replaces_the_saved_custom_scan_folder() {
    let root = tempfile::tempdir().unwrap();
    let saved = root.path().join("Saved Custom Logs");
    let one_off = root.path().join("One-off Logs");
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        format!(
            "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4\n  \
             SCAN Custom Path: {}\n",
            yaml_path(&saved)
        ),
    )
    .unwrap();

    let launch = prepare_launch(
        root.path(),
        CrashLogScanIntent::Standard,
        &CrashLogScanLaunchOverrides::new().with_scan_path(&one_off),
    )
    .unwrap();

    let Request::Standard(request) = launch.request() else {
        panic!("a Standard intent must produce a Standard request");
    };
    assert_eq!(request.source().base_directory, root.path());
    assert_eq!(
        request.source().custom_scan_directory.as_deref(),
        Some(one_off.as_path())
    );
}

/// Builds a Fallout 4 VR managed-game document with the given FormID Databases body.
fn managed_vr(formid_databases: &str) -> String {
    format!(
        "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4 VR\n  \
         Game Version: VR\n  FormID Databases:\n{formid_databases}"
    )
}

#[test]
fn fallout4_vr_scan_reads_the_shared_fallout4_rows() {
    let root = root_with_settings(&managed_vr(
        "    Fallout4:\n      - databases/Fallout4 FormIDs.db\n",
    ));

    let launch = standard(root.path());

    assert_eq!(launch.request().configuration().game, GameId::Fallout4VR);
    assert_eq!(launch.request().configuration().game_version, "VR");
    assert_eq!(formid_rows(&launch), ["databases/Fallout4 FormIDs.db"]);
}

#[test]
fn fallout4_vr_scan_still_reads_legacy_fallout4vr_rows() {
    let root = root_with_settings(&managed_vr(
        "    Fallout4VR:\n      - databases/Legacy VR FormIDs.db\n",
    ));

    assert_eq!(
        formid_rows(&standard(root.path())),
        ["databases/Legacy VR FormIDs.db"]
    );
}

#[test]
fn fallout4_vr_scan_reads_shared_rows_before_legacy_rows() {
    let root = root_with_settings(&managed_vr(
        "    Fallout4:\n      - databases/Fallout4 FormIDs.db\n    \
         Fallout4VR:\n      - databases/Legacy VR FormIDs.db\n",
    ));

    assert_eq!(
        formid_rows(&standard(root.path())),
        [
            "databases/Fallout4 FormIDs.db",
            "databases/Legacy VR FormIDs.db"
        ]
    );
}

#[test]
fn fallout4_vr_scan_reads_a_row_saved_under_both_keys_once() {
    let root = root_with_settings(&managed_vr(
        "    Fallout4:\n      - databases/Fallout4 FormIDs.db\n      \
         - databases/Shared Extra FormIDs.db\n    \
         Fallout4VR:\n      - databases/Fallout4 FormIDs.db\n      \
         - databases/Legacy VR FormIDs.db\n",
    ));

    assert_eq!(
        formid_rows(&standard(root.path())),
        [
            "databases/Fallout4 FormIDs.db",
            "databases/Shared Extra FormIDs.db",
            "databases/Legacy VR FormIDs.db"
        ]
    );
}

#[test]
fn malformed_user_settings_produce_a_request_with_their_diagnostics() {
    let root = root_with_settings(
        "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Broken Sequence: [one, two\n",
    );

    let launch = standard(root.path());

    assert_eq!(launch.request().configuration().game, GameId::Fallout4);
    assert!(formid_rows(&launch).is_empty());
    assert!(!matches!(launch.request(), Request::Standard(request) if request.fcx_enabled()));
    assert_eq!(
        diagnostic_codes(&launch),
        ["malformed_document", "commit_blocked_untrusted_document"]
    );
    assert!(
        launch
            .diagnostics()
            .iter()
            .all(|diagnostic| diagnostic.kind() == CrashLogScanLaunchDiagnosticKind::UserSettings)
    );
}

#[test]
fn newer_user_settings_produce_a_request_with_their_diagnostics() {
    let root = root_with_settings(
        "schema_version: \"99.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4 VR\n  \
         FCX Mode: true\n  Max Concurrent Scans: 9\n",
    );

    let launch = standard(root.path());

    // A newer major cannot be trusted, so none of its values apply.
    assert_eq!(launch.request().configuration().game, GameId::Fallout4);
    assert_eq!(launch.request().configuration().max_concurrent, None);
    assert!(launch.setup_context().is_none());
    assert_eq!(
        diagnostic_codes(&launch),
        [
            "unsupported_future_major_schema",
            "commit_blocked_untrusted_document"
        ]
    );
}

#[test]
fn user_settings_needing_migration_still_produce_a_request_with_their_diagnostics() {
    let root = root_with_settings(
        "CLASSIC_Settings:\n  Managed Game: Fallout 4\n  Game Version: Original\n  \
         Max Concurrent Scans: 2\n",
    );

    let launch = standard(root.path());

    assert_eq!(launch.request().configuration().game_version, "Original");
    assert_eq!(launch.request().configuration().max_concurrent, Some(2));
    assert_eq!(
        diagnostic_codes(&launch),
        ["migration_required_unversioned_document"]
    );
}

#[test]
fn targeted_launch_scans_exactly_its_inputs_in_order() {
    let root = root_with_settings(MANAGED_FALLOUT4);
    let inputs = vec![root.path().join("b.log"), root.path().join("a folder")];

    let launch = prepare_launch(
        root.path(),
        CrashLogScanIntent::Targeted(inputs.clone()),
        &CrashLogScanLaunchOverrides::new(),
    )
    .unwrap();

    let Request::Targeted(request) = launch.request() else {
        panic!("a Targeted intent must produce a Targeted request");
    };
    assert_eq!(request.source().inputs, inputs);
    assert_eq!(launch.request().configuration().game, GameId::Fallout4);
}

#[test]
fn targeted_launch_without_inputs_is_a_typed_error() {
    let root = root_with_settings(MANAGED_FALLOUT4);

    let error = prepare_launch(
        root.path(),
        CrashLogScanIntent::Targeted(Vec::new()),
        &CrashLogScanLaunchOverrides::new(),
    )
    .unwrap_err();

    assert_eq!(error, CrashLogScanLaunchError::TargetedWithoutInputs);
    assert_eq!(
        error.kind(),
        CrashLogScanLaunchErrorKind::TargetedWithoutInputs
    );
}

#[test]
fn launch_leaves_the_user_settings_document_byte_identical() {
    let root = root_with_settings(MANAGED_FALLOUT4);
    let path = root.path().join("CLASSIC Settings.yaml");
    let before = std::fs::read(&path).unwrap();
    let modified_before = std::fs::metadata(&path).unwrap().modified().unwrap();

    let _ = standard(root.path());
    let _ = prepare_launch(
        root.path(),
        CrashLogScanIntent::Targeted(vec![root.path().join("a.log")]),
        &CrashLogScanLaunchOverrides::new()
            .with_show_formid_values()
            .with_max_concurrency(MaxConcurrency::Adaptive),
    )
    .unwrap();

    assert_eq!(std::fs::read(&path).unwrap(), before);
    assert_eq!(
        std::fs::metadata(&path).unwrap().modified().unwrap(),
        modified_before
    );
    // Nothing else appeared beside it either: no backup, lock, or migrated copy.
    let entries: Vec<PathBuf> = std::fs::read_dir(root.path())
        .unwrap()
        .map(|entry| entry.unwrap().path())
        .collect();
    assert_eq!(entries, [path]);
}

#[test]
fn saved_fcx_mode_carries_the_saved_setup_folders_without_refusing_missing_ones() {
    let root = tempfile::tempdir().unwrap();
    let game = root.path().join("Fallout 4");
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        format!(
            "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4\n  \
             FCX Mode: true\n  Game Folder Path: {}\n",
            yaml_path(&game)
        ),
    )
    .unwrap();

    let launch = standard(root.path());

    let context = launch
        .setup_context()
        .expect("FCX Mode carries a setup context");
    // The saved folder does not exist; FCX setup validation, not the launch, reports that.
    assert_eq!(context.game_root.as_deref(), Some(game.as_path()));
    assert_eq!(context.docs_root, None);
    assert!(matches!(launch.request(), Request::Standard(request) if request.fcx_enabled()));
}

#[test]
fn launch_without_a_user_settings_document_uses_published_defaults_and_creates_nothing() {
    let root = tempfile::tempdir().unwrap();

    let launch = standard(root.path());

    assert_eq!(launch.request().configuration().game, GameId::Fallout4);
    assert!(std::fs::read_dir(root.path()).unwrap().next().is_none());
}
