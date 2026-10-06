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
        has_max_concurrent: false,
        max_concurrent: 0,
        show_formid_values: false,
        simplify_logs: false,
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
}
