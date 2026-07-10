//! Behavioral coverage for the public, read-only frontend-state User Settings group.

use classic_user_settings_core::{PreferenceOrigin, UserSettings};
use std::{fs, path::PathBuf};

/// Returns one fixture from the repository-level User Settings compatibility corpus.
fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../tests/fixtures/user_settings_compatibility")
        .join(name)
}

/// Projects canonical frontend preferences and GUI geometry without changing the source.
#[test]
fn canonical_frontend_state_is_typed_and_read_only() {
    let root = tempfile::tempdir().expect("create temporary CLASSIC root");
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let source = fs::read(fixture_path("gui_geometry.yaml")).expect("read geometry fixture");
    fs::write(&settings_path, &source).expect("write User Settings fixture");

    let settings = UserSettings::open(root.path());
    let frontend = settings.frontend_state();

    assert!(frontend.preferences().auto_switch_after_scan());
    assert_eq!(
        frontend.preferences().auto_switch_after_scan_origin(),
        PreferenceOrigin::Document
    );
    assert_eq!(frontend.preferences().auto_refresh_interval_ms(), 5_000);
    assert_eq!(
        frontend.preferences().auto_refresh_interval_ms_origin(),
        PreferenceOrigin::Document
    );

    let main = frontend.window_geometry().main_tab();
    assert_eq!(
        (main.width(), main.height(), main.maximized()),
        (705, 641, false)
    );
    assert_eq!(main.width_origin(), PreferenceOrigin::Document);
    assert_eq!(main.height_origin(), PreferenceOrigin::Document);
    assert_eq!(main.maximized_origin(), PreferenceOrigin::Document);

    let backups = frontend.window_geometry().backups_tab();
    assert_eq!(
        (backups.width(), backups.height(), backups.maximized()),
        (750, 580, false)
    );
    let articles = frontend.window_geometry().articles_tab();
    assert_eq!(
        (articles.width(), articles.height(), articles.maximized()),
        (550, 350, false)
    );
    let results = frontend.window_geometry().results_tab();
    assert_eq!(
        (results.width(), results.height(), results.maximized()),
        (750, 450, true)
    );

    assert_eq!(frontend.tui().active_tab(), 0);
    assert_eq!(frontend.tui().results_panel_width(), 30);
    assert!(!frontend.tui().sort_ascending());
    assert_eq!(
        frontend.tui().active_tab_origin(),
        PreferenceOrigin::Default
    );
    assert_eq!(settings.original_bytes(), Some(source.as_slice()));
    assert_eq!(
        fs::read(settings_path).expect("reread User Settings"),
        source
    );
}

/// Falls back per invalid presentation leaf while retaining source bytes and valid siblings.
#[test]
fn invalid_frontend_values_report_diagnostics_without_rewriting() {
    let root = tempfile::tempdir().expect("create temporary CLASSIC root");
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let source =
        fs::read(fixture_path("invalid_known_values.yaml")).expect("read invalid-values fixture");
    fs::write(&settings_path, &source).expect("write User Settings fixture");

    let settings = UserSettings::open(root.path());
    let main = settings.frontend_state().window_geometry().main_tab();

    assert_eq!(
        (main.width(), main.height(), main.maximized()),
        (640, 500, false)
    );
    assert_eq!(main.width_origin(), PreferenceOrigin::DegradedFallback);
    assert_eq!(main.height_origin(), PreferenceOrigin::Document);
    assert_eq!(main.maximized_origin(), PreferenceOrigin::DegradedFallback);
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec![
            "invalid_type_update_check",
            "invalid_enum_game_version",
            "invalid_type_move_unsolved_logs",
            "invalid_path_unsolved_logs_destination",
            "invalid_path_custom_scan_input",
            "invalid_range_max_concurrent_scans",
            "invalid_value_formid_databases",
            "invalid_type_gui_geometry_width",
            "invalid_type_gui_geometry_maximized",
        ]
    );
    assert_eq!(settings.original_bytes(), Some(source.as_slice()));
    assert_eq!(
        fs::read(settings_path).expect("reread User Settings"),
        source
    );
}

/// Reads the canonical TUI namespace while preserving unknown frontend namespaces and leaves.
#[test]
fn tui_state_and_unknown_frontend_content_survive_read_only_open() {
    let root = tempfile::tempdir().expect("create temporary CLASSIC root");
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let source = br#"schema_version: "1.0"
UI:
  preferences:
    auto_switch_after_scan: false
    auto_refresh_interval_ms: 2500
    future_presentation: compact
  tui:
    active_tab: 2
    results_panel_width: 42
    sort_ascending: true
    future_flag: retained
  community_frontend:
    theme: amber
"#;
    fs::write(&settings_path, source).expect("write User Settings fixture");

    let settings = UserSettings::open(root.path());
    let frontend = settings.frontend_state();

    assert!(!frontend.preferences().auto_switch_after_scan());
    assert_eq!(frontend.preferences().auto_refresh_interval_ms(), 2_500);
    assert_eq!(frontend.tui().active_tab(), 2);
    assert_eq!(frontend.tui().results_panel_width(), 42);
    assert!(frontend.tui().sort_ascending());
    assert_eq!(
        frontend.tui().results_panel_width_origin(),
        PreferenceOrigin::Document
    );
    assert!(settings.diagnostics().is_empty());
    assert_eq!(settings.original_bytes(), Some(source.as_slice()));
    assert_eq!(
        fs::read(settings_path).expect("reread User Settings"),
        source
    );
}

/// Projects legacy frontend preferences and gives the canonical nested value precedence.
#[test]
fn frontend_preference_compatibility_sources_have_stable_precedence() {
    let flat_root = tempfile::tempdir().expect("create flat CLASSIC root");
    let flat_source =
        fs::read(fixture_path("flat_classic_config.yaml")).expect("read flat fixture");
    fs::write(flat_root.path().join("CLASSIC Settings.yaml"), &flat_source)
        .expect("write flat User Settings fixture");

    let flat = UserSettings::open(flat_root.path());
    let flat_preferences = flat.frontend_state().preferences();
    assert!(!flat_preferences.auto_switch_after_scan());
    assert_eq!(flat_preferences.auto_refresh_interval_ms(), 2_500);
    assert_eq!(
        flat_preferences.auto_switch_after_scan_origin(),
        PreferenceOrigin::Document
    );
    assert_eq!(
        flat.frontend_state()
            .window_geometry()
            .main_tab()
            .width_origin(),
        PreferenceOrigin::Default
    );

    let nested_root = tempfile::tempdir().expect("create nested CLASSIC root");
    let nested_source = br#"schema_version: "1.0"
CLASSIC_Settings:
  Auto Switch After Scan: true
UI:
  preferences:
    auto_switch_after_scan: false
"#;
    fs::write(
        nested_root.path().join("CLASSIC Settings.yaml"),
        nested_source,
    )
    .expect("write nested User Settings fixture");

    let nested = UserSettings::open(nested_root.path());
    assert!(
        !nested
            .frontend_state()
            .preferences()
            .auto_switch_after_scan()
    );
    assert_eq!(
        nested
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec!["canonical_alias_conflict_auto_switch_after_scan"]
    );
    assert_eq!(nested.original_bytes(), Some(nested_source.as_slice()));
}

/// Diagnoses a malformed live-GUI alias even when the canonical value can be used.
#[test]
fn canonical_frontend_preference_reports_invalid_compatibility_alias() {
    let root = tempfile::tempdir().expect("create nested CLASSIC root");
    let source = br#"schema_version: "1.0"
CLASSIC_Settings:
  Auto Switch After Scan: sometimes
UI:
  preferences:
    auto_switch_after_scan: false
"#;
    fs::write(root.path().join("CLASSIC Settings.yaml"), source)
        .expect("write nested User Settings fixture");

    let settings = UserSettings::open(root.path());

    assert!(
        !settings
            .frontend_state()
            .preferences()
            .auto_switch_after_scan()
    );
    assert_eq!(
        settings
            .frontend_state()
            .preferences()
            .auto_switch_after_scan_origin(),
        PreferenceOrigin::Document
    );
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec!["invalid_type_frontend_auto_switch_after_scan"]
    );
    assert_eq!(settings.original_bytes(), Some(source.as_slice()));
}

/// Distinguishes published frontend defaults from fallbacks for an untrusted document.
#[test]
fn missing_and_untrusted_documents_expose_distinct_frontend_origins() {
    let missing_root = tempfile::tempdir().expect("create missing CLASSIC root");
    let missing = UserSettings::open(missing_root.path());
    assert!(
        missing
            .frontend_state()
            .preferences()
            .auto_switch_after_scan()
    );
    assert_eq!(
        missing
            .frontend_state()
            .preferences()
            .auto_switch_after_scan_origin(),
        PreferenceOrigin::Default
    );
    assert_eq!(
        missing
            .frontend_state()
            .window_geometry()
            .main_tab()
            .width_origin(),
        PreferenceOrigin::Default
    );

    let malformed_root = tempfile::tempdir().expect("create malformed CLASSIC root");
    let malformed_source =
        fs::read(fixture_path("malformed.yaml")).expect("read malformed fixture");
    fs::write(
        malformed_root.path().join("CLASSIC Settings.yaml"),
        &malformed_source,
    )
    .expect("write malformed User Settings fixture");

    let malformed = UserSettings::open(malformed_root.path());
    assert_eq!(
        malformed
            .frontend_state()
            .preferences()
            .auto_switch_after_scan_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(
        malformed
            .frontend_state()
            .window_geometry()
            .main_tab()
            .width_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(
        malformed.frontend_state().tui().active_tab_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(
        malformed.original_bytes(),
        Some(malformed_source.as_slice())
    );
}

/// Diagnoses invalid known namespaces and TUI values without degrading unrelated namespaces.
#[test]
fn invalid_frontend_namespaces_and_tui_values_fall_back_independently() {
    let root = tempfile::tempdir().expect("create temporary CLASSIC root");
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let source = br#"schema_version: "1.0"
UI:
  preferences: compact
  window_geometry:
    main_tab: wide
  tui:
    active_tab: 9
    results_panel_width: -1
    sort_ascending: yes
  future_frontend:
    retained: true
"#;
    fs::write(&settings_path, source).expect("write User Settings fixture");

    let settings = UserSettings::open(root.path());
    let frontend = settings.frontend_state();

    assert_eq!(
        frontend.preferences().auto_refresh_interval_ms_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(
        frontend.window_geometry().main_tab().width_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(
        frontend.window_geometry().backups_tab().width_origin(),
        PreferenceOrigin::Default
    );
    assert_eq!(frontend.tui().active_tab(), 0);
    assert_eq!(frontend.tui().results_panel_width(), 30);
    assert!(!frontend.tui().sort_ascending());
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec![
            "invalid_type_frontend_preferences",
            "invalid_type_gui_geometry_tab",
            "invalid_range_tui_active_tab",
            "invalid_range_tui_results_panel_width",
            "invalid_type_tui_sort_ascending",
        ]
    );
    assert_eq!(settings.original_bytes(), Some(source.as_slice()));
    assert_eq!(
        fs::read(settings_path).expect("reread User Settings"),
        source
    );
}
