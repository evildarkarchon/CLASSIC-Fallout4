//! Public behavior coverage for typed Crash Log Scan Intake facts.

use classic_config_core::YamlDataCore;
use classic_scanlog_core::{CrashLogScanFacts, CrashLogScanIntake, CrashLogScanOptions};
use std::path::Path;
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

#[test]
fn intake_consumes_typed_scan_facts_without_opening_user_settings() {
    let temp = tempdir().expect("tempdir should be created");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    let configured_absolute = root.join("configured-absolute.db");
    let configured_destination = root.join("configured-unsolved");
    write_minimal_yaml_tree(root, &data);

    // This document would fail the old raw-path intake because its destination is relative.
    std::fs::write(
        root.join("CLASSIC Settings.yaml"),
        concat!(
            "CLASSIC_Settings:\n",
            "  Unsolved Logs Destination: must-not-be-read\n",
            "  FormID Databases:\n",
            "    Fallout4:\n",
            "      - databases/must-not-be-read.db\n",
        ),
    )
    .expect("sentinel User Settings should be written");

    let ready = classic_shared_core::get_runtime()
        .block_on(
            CrashLogScanIntake::from_yaml_paths(
                root,
                &data,
                "Fallout4",
                "auto",
                CrashLogScanOptions::new(true, false, true),
            )
            .with_scan_facts(CrashLogScanFacts {
                formid_database_paths: vec![
                    "databases/FOLON FormIDs.db".into(),
                    "databases/configured-relative.db".into(),
                    configured_absolute.clone(),
                    "databases/configured-relative.db".into(),
                ],
                unsolved_logs_destination: Some(configured_destination.clone()),
            })
            .prepare(),
        )
        .expect("typed facts should prepare without interpreting User Settings");

    assert_eq!(
        ready.formid_readiness().database_paths(),
        [
            data.join("databases").join("Fallout4 FormIDs Main.db"),
            data.join("databases").join("FOLON FormIDs.db"),
            data.join("databases").join("configured-relative.db"),
            configured_absolute,
        ]
    );
    assert_eq!(
        ready.unsolved_logs_destination(),
        Some(configured_destination.as_path())
    );
    assert_eq!(
        ready.analysis_config().remove_list,
        vec!["(void*)".to_string()]
    );
}

#[test]
fn pathless_intake_rejects_relative_configured_formid_paths() {
    let temp = tempdir().expect("tempdir should be created");
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    write_minimal_yaml_tree(root, &data);
    let yaml = classic_shared_core::get_runtime()
        .block_on(YamlDataCore::load_from_yaml_files(
            vec![root.to_path_buf(), data],
            "Fallout4".to_string(),
            "auto".to_string(),
        ))
        .expect("fixture YAML should load");

    let result = classic_shared_core::get_runtime().block_on(
        CrashLogScanIntake::from_yaml_data(
            &yaml,
            None,
            "Fallout4",
            "auto",
            CrashLogScanOptions::new(true, false, false),
        )
        .with_scan_facts(CrashLogScanFacts {
            formid_database_paths: vec!["databases/configured-relative.db".into()],
            unsolved_logs_destination: None,
        })
        .prepare(),
    );

    let error = match result {
        Ok(_) => panic!("relative configured FormID path should require yaml_dir_data"),
        Err(error) => error,
    };
    assert!(error.to_string().contains("yaml_dir_data"));
}
