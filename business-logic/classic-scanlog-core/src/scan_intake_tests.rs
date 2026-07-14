use super::*;
use tempfile::tempdir;

fn write_minimal_yaml_tree(root: &Path, data: &Path) {
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
            "  - 'Basic Render Driver'\n",
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
            "Crashlog_Plugins_Exclude:\n",
            "  - Fallout4.esm\n",
            "Crashlog_Records_Exclude:\n",
            "  - IgnoreMe\n",
            "Crashgen_Registry:\n",
            "  default:\n",
            "    display_section: \"\"\n",
            "    ignore_keys: []\n",
            "    checks: []\n",
            "  Buffout 4:\n",
            "    display_section: \"[Compatibility]\"\n",
            "    ignore_keys: []\n",
            "    checks:\n",
            "      - achievements\n",
        ),
    )
    .expect("game YAML should be written");
    std::fs::write(
        root.join("CLASSIC Ignore.yaml"),
        "CLASSIC_Ignore_Fallout4:\n  - IgnoreThis.dll\n",
    )
    .expect("ignore YAML should be written");
}

fn prepare_path_backed(root: &Path, data: &Path) -> Result<ScanReadyAnalysis> {
    classic_shared_core::get_runtime().block_on(
        CrashLogScanIntake::from_yaml_paths(
            root,
            data,
            "Fallout4",
            "auto",
            CrashLogScanOptions::default(),
        )
        .prepare(),
    )
}

#[test]
fn path_backed_and_in_memory_yaml_prepare_equivalent_scan_ready_payloads() {
    let temp = tempdir().expect("tempdir should be created");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let options = CrashLogScanOptions::new(true, true, true);
    let scan_facts = CrashLogScanFacts {
        formid_database_paths: vec![PathBuf::from("databases/custom.db")],
        unsolved_logs_destination: None,
    };

    let path_ready = classic_shared_core::get_runtime()
        .block_on(
            CrashLogScanIntake::from_yaml_paths(root, &data, "Fallout4", "auto", options)
                .with_scan_facts(scan_facts.clone())
                .prepare(),
        )
        .expect("path-backed intake should prepare");
    let yaml = classic_shared_core::get_runtime()
        .block_on(YamlDataCore::load_from_yaml_files(
            vec![root.to_path_buf(), data.clone()],
            "Fallout4".to_string(),
            "auto".to_string(),
        ))
        .expect("fixture YAML should load");
    let in_memory_ready = classic_shared_core::get_runtime()
        .block_on(
            CrashLogScanIntake::from_yaml_data(
                &yaml,
                Some(CrashLogScanIntakePaths::new(root, &data)),
                "Fallout4",
                "auto",
                options,
            )
            .with_scan_facts(scan_facts)
            .prepare(),
        )
        .expect("in-memory intake should prepare");

    assert_eq!(
        path_ready.analysis_config().classic_version,
        in_memory_ready.analysis_config().classic_version
    );
    assert_eq!(
        path_ready.analysis_config().crashgen_name,
        in_memory_ready.analysis_config().crashgen_name
    );
    assert_eq!(
        path_ready.analysis_config().game_version,
        in_memory_ready.analysis_config().game_version
    );
    assert_eq!(path_ready.analysis_config().xse_acronym, "F4SE");
    assert_eq!(path_ready.analysis_config().crashgen_name, "Buffout 4");
    assert!(
        !path_ready.analysis_config().crashgen_latest.is_empty(),
        "intake should resolve Crashgen metadata through registry or YAML fallback"
    );
    assert!(path_ready.analysis_config().show_formid_values);
    assert!(path_ready.analysis_config().fcx_mode);
    assert!(path_ready.analysis_config().simplify_logs);
    assert_eq!(
        path_ready.analysis_config().remove_list,
        vec!["(void*)".to_string(), "Basic Render Driver".to_string()]
    );
    assert_eq!(
        path_ready.analysis_config().remove_list,
        in_memory_ready.analysis_config().remove_list
    );
    assert_eq!(
        path_ready.formid_readiness(),
        in_memory_ready.formid_readiness()
    );
    assert!(path_ready.should_initialize_formid_database());
    assert_eq!(
        path_ready.paths(),
        Some(&CrashLogScanIntakePaths::new(root, &data))
    );
    assert!(path_ready.unsolved_logs_destination().is_none());
}

#[test]
fn selected_game_version_resolution_flows_through_intake() {
    let temp = tempdir().expect("tempdir should be created");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let options = CrashLogScanOptions::default();

    let original_ready = classic_shared_core::get_runtime()
        .block_on(
            CrashLogScanIntake::from_yaml_paths(root, &data, "Fallout4", "Original", options)
                .prepare(),
        )
        .expect("Original intake should prepare");
    let vr_ready = classic_shared_core::get_runtime()
        .block_on(
            CrashLogScanIntake::from_yaml_paths(root, &data, "Fallout4", "VR", options).prepare(),
        )
        .expect("VR intake should prepare");

    assert_eq!(original_ready.analysis_config().game_version, "1.10.163");
    assert_eq!(vr_ready.analysis_config().game_version, "1.2.72");
    assert_eq!(vr_ready.analysis_config().game_version_vr, "1.2.72");
}

#[test]
fn in_memory_yaml_without_paths_preserves_config_and_avoids_sidecar_paths() {
    let yaml = YamlDataCore {
        classic_game_hints: Vec::new(),
        classic_records_list: Vec::new(),
        classic_version: "v9.1.0".to_string(),
        classic_version_date: String::new(),
        crashgen_name: "Buffout 4".to_string(),
        crashgen_latest_og: "1.28.6".to_string(),
        crashgen_ignore: Vec::new(),
        warn_noplugins: String::new(),
        warn_outdated: String::new(),
        xse_acronym: "F4SE".to_string(),
        game_ignore_plugins: Vec::new(),
        game_ignore_records: Vec::new(),
        ignore_list: Vec::new(),
        suspect_error_rules: Vec::new(),
        suspect_stack_rules: Vec::new(),
        game_mods_conf: Vec::new(),
        game_mods_core: Vec::new(),
        game_mods_freq: Vec::new(),
        game_mods_solu: Vec::new(),
        autoscan_text: String::new(),
        game_version: "1.10.163".to_string(),
        game_root_name: "Fallout4".to_string(),
        crashgen_registry: std::collections::HashMap::new(),
    };

    let ready = classic_shared_core::get_runtime()
        .block_on(
            CrashLogScanIntake::from_yaml_data(
                &yaml,
                None,
                "Fallout4",
                "auto",
                CrashLogScanOptions::new(true, false, true),
            )
            .prepare(),
        )
        .expect("in-memory intake should prepare without paths");

    assert_eq!(ready.analysis_config().classic_version, "v9.1.0");
    assert!(ready.analysis_config().show_formid_values);
    assert!(ready.analysis_config().simplify_logs);
    assert!(ready.analysis_config().remove_list.is_empty());
    assert!(ready.formid_readiness().is_enabled());
    assert!(ready.formid_readiness().database_paths().is_empty());
    assert!(ready.paths().is_none());
    assert!(ready.unsolved_logs_destination().is_none());
    assert!(!ready.should_initialize_formid_database());
}

#[test]
fn missing_unsolved_logs_destination_produces_no_configured_destination() {
    let temp = tempdir().expect("tempdir should be created");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);

    let ready = prepare_path_backed(root, &data).expect("intake should prepare");

    assert!(ready.unsolved_logs_destination().is_none());
}

#[test]
fn typed_none_unsolved_logs_destination_produces_no_configured_destination() {
    let temp = tempdir().expect("tempdir should be created");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let ready = prepare_path_backed(root, &data).expect("intake should prepare");

    assert!(ready.unsolved_logs_destination().is_none());
}

#[test]
fn malformed_user_settings_is_not_opened_during_intake() {
    let temp = tempdir().expect("tempdir should be created");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    std::fs::write(root.join("CLASSIC Settings.yaml"), "CLASSIC_Settings: [\n")
        .expect("settings YAML should be written");

    let ready = prepare_path_backed(root, &data).expect("intake should prepare fail-soft");

    assert!(ready.unsolved_logs_destination().is_none());
}

#[test]
fn typed_absolute_unsolved_logs_destination_is_stored_without_existing() {
    let temp = tempdir().expect("tempdir should be created");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    let destination = root.join("custom unsolved logs");
    write_minimal_yaml_tree(root, &data);
    let ready = classic_shared_core::get_runtime()
        .block_on(
            CrashLogScanIntake::from_yaml_paths(
                root,
                &data,
                "Fallout4",
                "auto",
                CrashLogScanOptions::default(),
            )
            .with_scan_facts(CrashLogScanFacts {
                formid_database_paths: Vec::new(),
                unsolved_logs_destination: Some(destination.clone()),
            })
            .prepare(),
        )
        .expect("intake should prepare");

    assert_eq!(
        ready.unsolved_logs_destination(),
        Some(destination.as_path())
    );
    assert!(!destination.exists());
}

#[test]
fn typed_relative_unsolved_logs_destination_fails_setup() {
    let temp = tempdir().expect("tempdir should be created");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let result = classic_shared_core::get_runtime().block_on(
        CrashLogScanIntake::from_yaml_paths(
            root,
            &data,
            "Fallout4",
            "auto",
            CrashLogScanOptions::default(),
        )
        .with_scan_facts(CrashLogScanFacts {
            formid_database_paths: Vec::new(),
            unsolved_logs_destination: Some(PathBuf::from("relative/path")),
        })
        .prepare(),
    );
    let error = match result {
        Ok(_) => panic!("relative destination should fail"),
        Err(error) => error,
    };

    assert!(matches!(error, ScanLogError::InvalidInput(_)));
}

#[test]
fn resolve_formid_database_paths_preserves_existing_order_and_dedupes() {
    let temp = tempdir().expect("tempdir should be created");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    std::fs::create_dir_all(data.join("databases")).expect("database dir should be created");
    let custom = data.join("databases").join("custom.db");

    let paths = resolve_formid_database_paths(
        &data,
        "Fallout4",
        &[
            PathBuf::from("databases/FOLON FormIDs.db"),
            PathBuf::from("databases/custom.db"),
        ],
    );
    let main = data.join("databases").join("Fallout4 FormIDs Main.db");
    let folon = data.join("databases").join("FOLON FormIDs.db");

    assert_eq!(paths, vec![main, folon, custom]);
}

#[test]
fn short_scan_cache_profile_applies_database_pool_knobs() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "Fallout4".to_string());

    SHORT_SCAN_CACHE_PROFILE.apply_to_pool(&pool);

    assert_eq!(
        pool.get_cache_capacity(),
        SHORT_SCAN_CACHE_PROFILE.cache_capacity
    );
    assert_eq!(
        pool.get_cache_ttl(),
        Duration::from_secs(SHORT_SCAN_CACHE_PROFILE.cache_ttl_secs)
    );
    assert_eq!(
        pool.get_cache_cleanup_threshold(),
        SHORT_SCAN_CACHE_PROFILE.cleanup_threshold
    );
    assert_eq!(
        pool.get_cache_cleanup_interval(),
        Duration::from_secs(SHORT_SCAN_CACHE_PROFILE.cleanup_interval_secs)
    );
}
