use super::*;

#[test]
fn launch_exposes_the_rust_built_request_and_diagnostics() {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        "CLASSIC_Settings:\n  Managed Game: Fallout 4\n  Move Unsolved Logs: false\n  \
         FormID Databases:\n    Fallout4:\n      - databases/Fallout4 FormIDs.db\n",
    )
    .unwrap();

    let launched = launch(
        root.path().to_string_lossy().into_owned(),
        CrashLogScanIntent::Standard,
        None,
    )
    .unwrap();

    assert_eq!(launched.intent(), "standard");
    assert_eq!(
        launched.base_directory().as_deref(),
        Some(root.path().to_string_lossy().as_ref())
    );
    assert_eq!(
        launched.formid_database_paths(),
        ["databases/Fallout4 FormIDs.db"]
    );
    assert_eq!(launched.unsolved_logs(), Some("leave_in_place"));
    assert_eq!(launched.targeted_inputs(), None);
    let diagnostics = launched.diagnostics();
    assert_eq!(diagnostics.len(), 1);
    assert_eq!(diagnostics[0].kind, "user_settings");
    assert_eq!(diagnostics[0].code, "migration_required_unversioned_document");
}

#[test]
fn non_managed_game_exposes_withheld_values_and_their_display_lines() {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4\n  \
         FCX Mode: true\n",
    )
    .unwrap();
    let launched = PyScanRunLaunch {
        inner: prepare_launch(
            root.path(),
            CrashLogScanIntent::Standard,
            &CrashLogScanLaunchOverrides::new()
                .with_game(classic_shared_core::GameId::Fallout4VR),
        )
        .unwrap(),
    };

    let diagnostics = launched.diagnostics();
    assert_eq!(diagnostics.len(), 1);
    assert_eq!(diagnostics[0].kind, "fcx_mode_not_applied");
    assert_eq!(diagnostics[0].code, "fcx_mode_not_applied");
    let lines = launched.display_lines();
    assert_eq!(lines.len(), 1);
    assert_eq!(lines[0].severity, "notice");
    assert_eq!(lines[0].segments[0].text, "saved FCX Mode not applied");
}

#[test]
fn blank_installation_root_is_rejected_before_launching() {
    assert!(launch("  ".to_string(), CrashLogScanIntent::Standard, None).is_err());
}
