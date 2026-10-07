use super::*;

/// Overrides that supply nothing, so every saved value applies.
fn no_overrides() -> ffi::ScanRunLaunchOverridesDto {
    ffi::ScanRunLaunchOverridesDto {
        has_game: false,
        game: ffi::ScanRunGameId::Fallout4,
        has_game_version: false,
        game_version: String::new(),
        has_scan_path: false,
        scan_path: String::new(),
        no_scan_path: false,
        has_max_concurrent: false,
        max_concurrent: 0,
        show_formid_values: false,
        simplify_logs: false,
        fcx_mode: false,
    }
}

/// Creates an Installation Root holding a Fallout 4 VR User Settings document.
fn vr_root() -> tempfile::TempDir {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4 VR\n  \
         Game Version: VR\n  Max Concurrent Scans: 4\n  Move Unsolved Logs: true\n  \
         FormID Databases:\n    Fallout4:\n      - databases/Fallout4 FormIDs.db\n    \
         Fallout4VR:\n      - databases/Legacy VR FormIDs.db\n",
    )
    .unwrap();
    root
}

#[test]
fn standard_launch_view_carries_the_rust_built_request() {
    let root = vr_root();
    let root_text = root.path().to_string_lossy().into_owned();

    let launch = scan_run_launch_standard(&root_text, &no_overrides()).unwrap();

    assert!(!scan_run_launch_error(&launch).has_error);
    let view = scan_run_launch_view(&launch).unwrap();
    assert_eq!(view.intent, ffi::ScanRunLaunchIntent::Standard);
    assert_eq!(view.configuration.game, ffi::ScanRunGameId::Fallout4VR);
    assert_eq!(view.configuration.game_version, "VR");
    assert_eq!(
        view.configuration.formid_database_paths,
        ["databases/Fallout4 FormIDs.db", "databases/Legacy VR FormIDs.db"]
    );
    assert!(view.configuration.has_max_concurrent);
    assert_eq!(view.configuration.max_concurrent, 4);
    assert_eq!(view.standard_source.base_directory, root_text);
    assert_eq!(
        view.unsolved_logs,
        ffi::ScanRunLaunchUnsolvedLogs::MoveToConfiguredOrDefault
    );
    assert!(!view.fcx_enabled);
    assert!(view.diagnostics.is_empty());
    assert!(scan_run_launch_request(&launch).is_ok());
}

#[test]
fn zero_max_concurrent_override_requests_adaptive_concurrency() {
    let root = vr_root();
    let overrides = ffi::ScanRunLaunchOverridesDto {
        has_max_concurrent: true,
        max_concurrent: 0,
        has_game_version: true,
        game_version: "auto".to_string(),
        show_formid_values: true,
        ..no_overrides()
    };

    let launch =
        scan_run_launch_standard(&root.path().to_string_lossy(), &overrides).unwrap();

    let view = scan_run_launch_view(&launch).unwrap();
    assert!(!view.configuration.has_max_concurrent);
    assert_eq!(view.configuration.game_version, "auto");
    assert!(view.configuration.show_formid_values);
}

#[test]
fn targeted_launch_without_inputs_reports_the_typed_error() {
    let root = vr_root();

    let launch =
        scan_run_launch_targeted(&root.path().to_string_lossy(), &Vec::new(), &no_overrides())
            .unwrap();

    let error = scan_run_launch_error(&launch);
    assert!(error.has_error);
    assert_eq!(error.kind, ffi::ScanRunLaunchErrorKind::TargetedWithoutInputs);
    assert!(scan_run_launch_view(&launch).is_err());
    assert!(scan_run_launch_request(&launch).is_err());
}

#[test]
fn targeted_launch_view_lists_its_inputs() {
    let root = vr_root();
    let inputs = vec!["b.log".to_string(), "a.log".to_string()];

    let launch =
        scan_run_launch_targeted(&root.path().to_string_lossy(), &inputs, &no_overrides())
            .unwrap();

    let view = scan_run_launch_view(&launch).unwrap();
    assert_eq!(view.intent, ffi::ScanRunLaunchIntent::Targeted);
    assert_eq!(view.targeted_source.inputs, inputs);
}

/// Creates an Installation Root for Fallout 4 VR whose saved documents folder is `documents`.
fn vr_root_with_documents(documents: &str) -> tempfile::TempDir {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        format!(
            "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4 VR\n  \
             Game Version: VR\n  Documents Folder Path: {documents}\n"
        ),
    )
    .unwrap();
    root
}

#[test]
fn fcx_mode_override_carries_the_setup_context_with_the_vr_xse_log() {
    let documents = tempfile::tempdir().unwrap();
    let xse_folder = documents.path().join("F4SE");
    std::fs::create_dir_all(&xse_folder).unwrap();
    std::fs::write(xse_folder.join("f4se.log"), b"").unwrap();
    std::fs::write(xse_folder.join("f4sevr.log"), b"").unwrap();
    let root = vr_root_with_documents(&format!("'{}'", documents.path().display()));
    let overrides = ffi::ScanRunLaunchOverridesDto {
        fcx_mode: true,
        ..no_overrides()
    };

    let launch = scan_run_launch_standard(&root.path().to_string_lossy(), &overrides).unwrap();

    let view = scan_run_launch_view(&launch).unwrap();
    assert!(view.fcx_enabled);
    assert!(view.setup_context.has_docs_root);
    assert!(view.setup_context.has_xse_log_path);
    assert_eq!(
        view.setup_context.xse_log_path,
        xse_folder.join("f4sevr.log").to_string_lossy()
    );
}

#[test]
fn uninspectable_xse_log_is_the_typed_launch_error() {
    // The YAML `\0` escape saves a documents folder no platform can inspect.
    let root = vr_root_with_documents("\"/bad\\0docs\"");
    let overrides = ffi::ScanRunLaunchOverridesDto {
        fcx_mode: true,
        ..no_overrides()
    };

    let launch = scan_run_launch_standard(&root.path().to_string_lossy(), &overrides).unwrap();

    let error = scan_run_launch_error(&launch);
    assert!(error.has_error);
    assert_eq!(error.kind, ffi::ScanRunLaunchErrorKind::XseLogInspect);
    assert!(scan_run_launch_view(&launch).is_err());
}

#[test]
fn non_managed_game_reports_withheld_values_with_display_lines() {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4\n  \
         Game Version: NextGen\n  FCX Mode: true\n  Game Folder Path: 'C:/Games/Fallout 4'\n",
    )
    .unwrap();
    let overrides = ffi::ScanRunLaunchOverridesDto {
        has_game: true,
        game: ffi::ScanRunGameId::Fallout4VR,
        ..no_overrides()
    };

    let launch = scan_run_launch_standard(&root.path().to_string_lossy(), &overrides).unwrap();

    let view = scan_run_launch_view(&launch).unwrap();
    assert_eq!(view.configuration.game_version, "auto");
    assert!(!view.fcx_enabled);
    let kinds: Vec<_> = view.diagnostics.iter().map(|diagnostic| diagnostic.kind).collect();
    assert_eq!(
        kinds,
        [
            ffi::ScanRunLaunchDiagnosticKind::GameVersionNotApplied,
            ffi::ScanRunLaunchDiagnosticKind::FcxModeNotApplied,
            ffi::ScanRunLaunchDiagnosticKind::SetupFoldersNotApplied,
        ]
    );
    assert_eq!(view.diagnostics[0].code, "game_version_not_applied");
    // One Rust-rendered display line per diagnostic, in the same order.
    assert_eq!(view.display_lines.len(), view.diagnostics.len());
    let first = &view.display_lines[0];
    assert_eq!(first.severity, ffi::ScanRunDisplaySeverity::Notice);
    assert_eq!(first.segments[0].kind, ffi::ScanRunDisplaySegmentKind::Label);
    assert_eq!(first.segments[0].text, "saved game version not applied");
    assert_eq!(first.segments[2].kind, ffi::ScanRunDisplaySegmentKind::Name);
    assert_eq!(first.segments[2].text, "Fallout 4 VR");
}

#[test]
fn unrepresentable_overrides_are_rejected_before_launching() {
    let root = vr_root();
    let root_text = root.path().to_string_lossy().into_owned();

    let bad_version = ffi::ScanRunLaunchOverridesDto {
        has_game_version: true,
        game_version: "Nonsense".to_string(),
        ..no_overrides()
    };
    assert!(scan_run_launch_standard(&root_text, &bad_version).is_err());
    assert!(scan_run_launch_standard("  ", &no_overrides()).is_err());

    // A folder and "no custom scan folder" at once cannot both win.
    let both_scan_paths = ffi::ScanRunLaunchOverridesDto {
        has_scan_path: true,
        scan_path: root_text.clone(),
        no_scan_path: true,
        ..no_overrides()
    };
    assert!(scan_run_launch_standard(&root_text, &both_scan_paths).is_err());
}

#[test]
fn no_scan_path_override_withholds_the_saved_custom_scan_folder() {
    let root = tempfile::tempdir().unwrap();
    let saved = root.path().join("Saved Custom Logs");
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        format!(
            "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4\n  \
             SCAN Custom Path: '{}'\n",
            saved.display()
        ),
    )
    .unwrap();
    let root_text = root.path().to_string_lossy().into_owned();
    let overrides = ffi::ScanRunLaunchOverridesDto {
        no_scan_path: true,
        ..no_overrides()
    };

    let saved_view =
        scan_run_launch_view(&scan_run_launch_standard(&root_text, &no_overrides()).unwrap())
            .unwrap();
    let cleared_view =
        scan_run_launch_view(&scan_run_launch_standard(&root_text, &overrides).unwrap()).unwrap();

    assert!(saved_view.standard_source.has_custom_scan_directory);
    assert!(!cleared_view.standard_source.has_custom_scan_directory);
    assert_eq!(cleared_view.standard_source.base_directory, root_text);
}
