use super::*;
use std::io::Write;
use tempfile::NamedTempFile;
use tempfile::tempdir;

#[test]
fn test_yaml_data_load_invalid_dirs() {
    let result = yaml_data_load(
        "nonexistent_root_dir",
        "nonexistent_data_dir",
        "Fallout4",
        "auto",
    );
    assert!(result.is_err());
}

#[test]
fn test_yaml_data_load_from_real_dirs() {
    let root_dir = "J:\\CLASSIC-Fallout4";
    let data_dir = "J:\\CLASSIC-Fallout4\\ClassicLib";

    let result = yaml_data_load(root_dir, data_dir, "Fallout4", "auto");
    if let Ok(data) = result {
        assert!(!yaml_data_classic_version(&data).is_empty());
        assert!(!yaml_data_xse_acronym(&data).is_empty());
        assert!(!yaml_data_crashgen_name_field(&data).is_empty());
        assert!(!yaml_data_game_version(&data).is_empty());
        assert!(!yaml_data_mods_freq_entries(&data).is_empty());
        assert!(!yaml_data_mods_solu_entries(&data).is_empty());

        let name = yaml_data_get_crashgen_name(&data);
        assert!(!name.is_empty());

        // IndexMap key/value pairs should have matching lengths
        let err_keys = yaml_data_suspects_error_keys(&data);
        let err_vals = yaml_data_suspects_error_values(&data);
        assert_eq!(err_keys.len(), err_vals.len());
    }
}

#[test]
fn test_yaml_data_game_version_mode() {
    let root_dir = "J:\\CLASSIC-Fallout4";
    let data_dir = "J:\\CLASSIC-Fallout4\\ClassicLib";

    let result_og = yaml_data_load(root_dir, data_dir, "Fallout4", "auto");
    let result_vr = yaml_data_load(root_dir, data_dir, "Fallout4", "VR");

    if let (Ok(og), Ok(vr)) = (result_og, result_vr) {
        let og_root = yaml_data_get_game_root_name(&og);
        let vr_root = yaml_data_get_game_root_name(&vr);
        assert!(!og_root.is_empty());
        assert!(!vr_root.is_empty());
    }
}

#[test]
fn test_yaml_data_accessors_fallback_when_game_info_is_minimal() {
    let temp = tempdir().expect("failed to create temp dir");
    let data_dir = temp.path().join("CLASSIC Data");
    let db_dir = data_dir.join("databases");
    std::fs::create_dir_all(&db_dir).expect("failed to create db dir");

    let main_yaml = r#"
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-15"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan Fallout 4"
"#;
    let game_yaml = r#"
Game_Info:
  Main_Root_Name: "Fallout 4"
Crashgen_Registry:
  "Buffout 4":
    ignore_keys:
      - "BuffoutSpecificIgnore"
    checks: []
  default:
    ignore_keys:
      - "DefaultIgnore"
    checks: []
"#;
    let ignore_yaml = r#"
CLASSIC_Ignore_Fallout4: []
"#;

    std::fs::write(db_dir.join("CLASSIC Main.yaml"), main_yaml).expect("write main yaml");
    std::fs::write(db_dir.join("CLASSIC Fallout4.yaml"), game_yaml).expect("write game yaml");
    std::fs::write(temp.path().join("CLASSIC Ignore.yaml"), ignore_yaml)
        .expect("write ignore yaml");

    let root_dir = temp.path().to_string_lossy().to_string();
    let data_dir_str = data_dir.to_string_lossy().to_string();
    let data = yaml_data_load(&root_dir, &data_dir_str, "Fallout4", "auto")
        .expect("yaml_data_load should succeed");

    assert!(!yaml_data_get_crashgen_name(&data).is_empty());
    assert_eq!(
        yaml_data_get_crashgen_ignore(&data),
        vec!["BuffoutSpecificIgnore".to_string()]
    );
    assert!(!yaml_data_game_version(&data).is_empty());
}

#[test]
fn test_save_local_yaml_paths_creates_file() {
    let temp = tempdir().expect("failed to create temp dir");
    let local_yaml_path = temp
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Fallout4 Local.yaml");

    save_local_yaml_paths(
        &local_yaml_path.to_string_lossy(),
        "C:/Games/Fallout4",
        "C:/Users/Test/Documents/My Games/Fallout4",
    )
    .expect("save_local_yaml_paths should succeed");

    let yaml = classic_settings_core::YamlOperations::new()
        .load_yaml_file(&local_yaml_path)
        .expect("load local yaml");
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Game"].as_str(),
        Some("C:/Games/Fallout4")
    );
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Docs"].as_str(),
        Some("C:/Users/Test/Documents/My Games/Fallout4")
    );
}

// ── CXXS-07 typed suspect-rule tests ───────────────────────────────

/// Builds a minimal YamlData with suspect error rules for testing.
fn make_yaml_data_with_suspect_rules() -> Option<Box<YamlData>> {
    let temp = tempdir().expect("failed to create temp dir");
    let data_dir = temp.path().join("CLASSIC Data");
    let db_dir = data_dir.join("databases");
    std::fs::create_dir_all(&db_dir).expect("failed to create db dir");

    let main_yaml = r#"
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-15"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan Fallout 4"
"#;

    let game_yaml = r#"
Game_Info:
  Main_Root_Name: "Fallout 4"
Crashgen_Registry:
  "Buffout 4":
    ignore_keys: []
    checks: []
  default:
    ignore_keys: []
    checks: []
Crashlog_Error_Check:
  - id: "err_test_rule"
    name: "Test Error Rule"
    severity: 3
    main_error_contains_any:
      - "AccessViolation"
      - "NullPointer"
Crashlog_Stack_Check:
  - id: "stack_test_rule"
    name: "Test Stack Rule"
    severity: 2
    main_error_required_any:
      - "RequiredPattern"
    main_error_optional_any:
      - "OptionalPattern"
    stack_contains_any:
      - "StackPattern1"
      - "StackPattern2"
    exclude_if_stack_contains_any:
      - "ExcludePattern"
    stack_contains_at_least:
      - substring: "RepeatedFunc"
        count: 2
"#;

    let ignore_yaml = r#"
CLASSIC_Ignore_Fallout4: []
"#;

    std::fs::write(db_dir.join("CLASSIC Main.yaml"), main_yaml).ok()?;
    std::fs::write(db_dir.join("CLASSIC Fallout4.yaml"), game_yaml).ok()?;
    std::fs::write(temp.path().join("CLASSIC Ignore.yaml"), ignore_yaml).ok()?;

    let root_dir = temp.path().to_string_lossy().to_string();
    let data_dir_str = data_dir.to_string_lossy().to_string();

    // Keep temp alive by leaking — test fixture only
    std::mem::forget(temp);

    yaml_data_load(&root_dir, &data_dir_str, "Fallout4", "auto").ok()
}

#[test]
fn test_yaml_data_suspects_error_rules_empty() {
    let temp = tempdir().expect("failed to create temp dir");
    let data_dir = temp.path().join("CLASSIC Data");
    let db_dir = data_dir.join("databases");
    std::fs::create_dir_all(&db_dir).expect("failed to create db dir");

    let main_yaml = "CLASSIC_Info:\n  version: \"7.0.0\"\n  version_date: \"2024-01-01\"\nCLASSIC_Interface:\n  autoscan_text_Fallout4: \"Autoscan\"\n";
    let game_yaml = "Game_Info:\n  Main_Root_Name: \"Fallout 4\"\nCrashgen_Registry:\n  default:\n    ignore_keys: []\n    checks: []\n";
    let ignore_yaml = "CLASSIC_Ignore_Fallout4: []\n";

    std::fs::write(db_dir.join("CLASSIC Main.yaml"), main_yaml).expect("write main yaml");
    std::fs::write(db_dir.join("CLASSIC Fallout4.yaml"), game_yaml).expect("write game yaml");
    std::fs::write(temp.path().join("CLASSIC Ignore.yaml"), ignore_yaml)
        .expect("write ignore yaml");

    let root_dir = temp.path().to_string_lossy().to_string();
    let data_dir_str = data_dir.to_string_lossy().to_string();

    if let Ok(data) = yaml_data_load(&root_dir, &data_dir_str, "Fallout4", "auto") {
        assert!(yaml_data_suspects_error_rules(&data).is_empty());
    }
}

#[test]
fn test_yaml_data_suspects_error_rules_populated() {
    if let Some(data) = make_yaml_data_with_suspect_rules() {
        let rules = yaml_data_suspects_error_rules(&data);
        assert!(!rules.is_empty(), "expected at least one error rule");
        let rule = &rules[0];
        assert_eq!(rule.id, "err_test_rule");
        assert_eq!(rule.name, "Test Error Rule");
        assert_eq!(rule.severity, 3);
        assert!(
            rule.main_error_contains_any
                .contains(&"AccessViolation".to_string()),
            "expected AccessViolation in main_error_contains_any"
        );
    }
}

#[test]
fn test_yaml_data_suspects_stack_rules_metadata_no_count_rules_field() {
    if let Some(data) = make_yaml_data_with_suspect_rules() {
        let metadata = yaml_data_suspects_stack_rules_metadata(&data);
        assert!(!metadata.is_empty(), "expected at least one stack rule");
        let rule = &metadata[0];
        assert_eq!(rule.id, "stack_test_rule");
        assert_eq!(rule.name, "Test Stack Rule");
        assert_eq!(rule.severity, 2);
        // Verify all flat Vec<String> fields are accessible (no nested Vec<Struct>)
        assert!(
            rule.main_error_required_any
                .contains(&"RequiredPattern".to_string())
        );
        assert!(
            rule.main_error_optional_any
                .contains(&"OptionalPattern".to_string())
        );
        assert!(
            rule.stack_contains_any
                .contains(&"StackPattern1".to_string())
        );
        assert!(
            rule.exclude_if_stack_contains_any
                .contains(&"ExcludePattern".to_string())
        );
        // Pitfall 6 compile-time proof: no stack_contains_at_least field on the DTO
    }
}

#[test]
fn test_yaml_data_suspects_stack_count_rules_unknown_id_returns_empty() {
    if let Some(data) = make_yaml_data_with_suspect_rules() {
        let count_rules =
            yaml_data_suspects_stack_count_rules_for_id(&data, "definitely_not_a_real_id_xyz");
        assert!(count_rules.is_empty());
    }
}

#[test]
fn test_yaml_data_suspects_stack_count_rules_known_id_returns_populated() {
    if let Some(data) = make_yaml_data_with_suspect_rules() {
        let count_rules = yaml_data_suspects_stack_count_rules_for_id(&data, "stack_test_rule");
        assert!(
            !count_rules.is_empty(),
            "expected count rules for stack_test_rule"
        );
        assert_eq!(count_rules[0].substring, "RepeatedFunc");
        assert_eq!(count_rules[0].count, 2);
    }
}

#[test]
fn test_yaml_data_suspects_error_keys_still_works_d08_regression() {
    // D-08 regression: existing fn must remain unchanged
    if let Some(data) = make_yaml_data_with_suspect_rules() {
        let keys = yaml_data_suspects_error_keys(&data);
        assert!(
            !keys.is_empty(),
            "yaml_data_suspects_error_keys must still work (D-08)"
        );
    }
}

#[test]
fn test_yaml_data_suspects_stack_keys_still_works_d08_regression() {
    // D-08 regression: existing fn must remain unchanged
    if let Some(data) = make_yaml_data_with_suspect_rules() {
        let keys = yaml_data_suspects_stack_keys(&data);
        assert!(
            !keys.is_empty(),
            "yaml_data_suspects_stack_keys must still work (D-08)"
        );
    }
}

#[test]
fn test_settings_cache_stats_helpers_forward_core_surface() {
    settings_cache_clear();
    reset_settings_cache_stats();

    assert_eq!(settings_cache_size(), 0);
    let initial = settings_cache_stats();
    assert_eq!(initial.hits, 0);
    assert_eq!(initial.misses, 0);
    assert_eq!(initial.size, 0);
    assert_eq!(initial.capacity, 64);

    let mut file = NamedTempFile::new().expect("create temp yaml");
    file.write_all(b"key: value\n").expect("write temp yaml");
    file.flush().expect("flush temp yaml");

    classic_settings_core::load_settings_sync("bridge-settings", file.path())
        .expect("load settings into cache");

    let populated = settings_cache_stats();
    assert_eq!(settings_cache_size(), 1);
    assert_eq!(populated.size, 1);
}
