use super::*;

#[test]
fn zero_max_concurrent_override_requests_adaptive_concurrency() {
    let overrides = overrides_to_core(JsScanRunLaunchOverrides {
        max_concurrent: Some(0),
        ..JsScanRunLaunchOverrides::default()
    })
    .unwrap();

    assert_eq!(overrides.max_concurrency(), Some(MaxConcurrency::Adaptive));
}

#[test]
fn false_supplied_as_on_overrides_keep_the_saved_value() {
    let overrides = overrides_to_core(JsScanRunLaunchOverrides {
        show_formid_values: Some(false),
        simplify_logs: Some(true),
        ..JsScanRunLaunchOverrides::default()
    })
    .unwrap();

    assert!(!overrides.show_formid_values());
    assert!(overrides.simplify_logs());
}

#[test]
fn fcx_mode_override_is_supplied_as_on() {
    let on = overrides_to_core(JsScanRunLaunchOverrides {
        fcx_mode: Some(true),
        ..JsScanRunLaunchOverrides::default()
    })
    .unwrap();
    let off = overrides_to_core(JsScanRunLaunchOverrides {
        fcx_mode: Some(false),
        ..JsScanRunLaunchOverrides::default()
    })
    .unwrap();

    assert!(on.fcx_mode());
    assert!(!off.fcx_mode());
}

#[test]
fn unknown_game_version_override_is_an_invalid_argument() {
    let error = overrides_to_core(JsScanRunLaunchOverrides {
        game_version: Some("Nonsense".to_string()),
        ..JsScanRunLaunchOverrides::default()
    })
    .expect_err("an unknown game-version token cannot be represented");

    assert_eq!(error.status, Status::InvalidArg);
}

#[test]
fn launch_projects_the_rust_built_configuration_and_diagnostics() {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        "CLASSIC_Settings:\n  Managed Game: Fallout 4 VR\n  FormID Databases:\n    \
         Fallout4VR:\n      - databases/Legacy VR FormIDs.db\n",
    )
    .unwrap();
    let launched = ScanRunLaunch {
        inner: prepare_launch(
            root.path(),
            CrashLogScanIntent::Standard,
            &CrashLogScanLaunchOverrides::new(),
        )
        .unwrap(),
    };

    let configuration = launched.configuration();
    assert!(matches!(configuration.game, JsGameId::Fallout4Vr));
    assert_eq!(
        configuration.formid_database_paths,
        ["databases/Legacy VR FormIDs.db"]
    );
    assert_eq!(launched.intent(), "standard");
    assert_eq!(launched.unsolved_logs(), Some("moveToConfiguredOrDefault"));
    let diagnostics = launched.diagnostics();
    assert_eq!(diagnostics.len(), 1);
    assert_eq!(diagnostics[0].kind, "userSettings");
    assert_eq!(
        diagnostics[0].code,
        "migration_required_unversioned_document"
    );
}
