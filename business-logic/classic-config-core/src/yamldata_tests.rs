use super::*;
use std::path::PathBuf;
use tempfile::tempdir;

// ============================================================
// Test Data Fixtures
// ============================================================

/// Minimal valid main YAML content for testing
fn minimal_main_yaml() -> &'static str {
    r#"
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-15"
catch_log_records:
  - "LAND"
  - "REFR"
  - "CELL"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan Fallout 4"
  autoscan_text_Skyrim: "Autoscan Skyrim"
"#
}

/// Minimal valid game YAML content for testing (Fallout4)
fn minimal_game_yaml() -> &'static str {
    r#"
Game_Info:
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
  GameVersionNEW: "1.10.984"
  CRASHGEN_LatestVer: "4.0.0"
  CRASHGEN_LogName: "crash-og"
  CRASHGEN_Ignore:
    - "OGIgnoreItem1"
    - "OGIgnoreItem2"
  Main_Root_Name: "Fallout4"
Game_Hints:
  - "Hint 1"
  - "Hint 2"
Warnings_CRASHGEN:
  Warn_NOPlugins: "No plugins found!"
  Warn_Outdated: "Your version is outdated."
Crashlog_Plugins_Exclude:
  - "Unofficial*.esp"
Crashlog_Records_Exclude:
  - "RecordType1"
Crashlog_Error_Check:
  - id: error_pattern_1
    name: Error Pattern 1
    severity: 4
    main_error_contains_any:
      - "Error description 1"
  - id: error_pattern_2
    name: Error Pattern 2
    severity: 2
    main_error_contains_any:
      - "Error description 2"
Crashlog_Stack_Check:
  - id: stack_pattern_1
    name: Stack Pattern 1
    severity: 3
    main_error_required_any:
      - "Main error required"
    main_error_optional_any:
      - "Main error optional"
    stack_contains_any:
      - "Stack pattern 1"
      - "Stack pattern 2"
    exclude_if_stack_contains_any:
      - "Excluded pattern"
    stack_contains_at_least:
      - substring: "Repeated pattern"
        count: 2
Mods_CONF:
  - mod_a: modA
    mod_b: modB
    name_a: Mod A
    name_b: Mod B
    description: "Config for ModA"
    fix: "Remove one."
Mods_CORE:
  - detect: ModB
    name: Core Mod B
    description: "Core mod B"
  - detect: GpuMod.dll
    name: GPU Mod
    description: "GPU-specific mod"
    gpu: nvidia
  - detect: ExcludedMod.esp
    name: Excluded Mod
    description: "Excluded mod"
    exclude_when:
      plugin_any: [SomeWorldspace.esm]
Mods_FREQ:
  - id: freq-mod
    criteria:
      any:
        - FreqMod
    name: Frequent Mod
    description: "Frequently used mod"
Mods_SOLU:
  - id: solu-mod
    criteria:
      any:
        - SoluMod
    name: Solution Mod
    description: "Solution mod"
"#
}

/// Production-shaped Fallout 4 YAML where Game_Info only has Main_Root_Name.
fn minimal_game_yaml_main_root_only() -> &'static str {
    r#"
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
"#
}

/// Production-shaped Fallout 4 YAML where Game_Info has compact Main_Root_Name.
fn minimal_game_yaml_main_root_only_compact() -> &'static str {
    r#"
Game_Info:
  Main_Root_Name: "Fallout4"
Crashgen_Registry:
  "Buffout 4":
    ignore_keys:
      - "BuffoutSpecificIgnore"
    checks: []
  default:
    ignore_keys:
      - "DefaultIgnore"
    checks: []
"#
}

/// Minimal valid ignore YAML content for testing
fn minimal_ignore_yaml() -> &'static str {
    r#"
CLASSIC_Ignore_Fallout4:
  - "IgnoreItem1"
  - "IgnoreItem2"
CLASSIC_Ignore_Skyrim:
  - "SkyrimIgnore1"
"#
}

// ============================================================
// YamlDataCore::from_yaml_content tests
// ============================================================

#[test]
fn test_from_yaml_content_creates_valid_instance() {
    let result = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    );

    assert!(result.is_ok(), "Should successfully parse valid YAML");
    let config = result.unwrap();
    assert_eq!(config.classic_version, "7.31.0");
}

#[test]
fn test_from_yaml_content_extracts_main_yaml_values() {
    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    // Main YAML values
    assert_eq!(config.classic_version, "7.31.0");
    assert_eq!(config.classic_version_date, "2024-01-15");
    assert_eq!(config.classic_records_list, vec!["LAND", "REFR", "CELL"]);
    assert_eq!(config.autoscan_text, "Autoscan Fallout 4");
}

#[test]
fn test_from_yaml_content_extracts_game_yaml_values() {
    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    // Game YAML values
    assert_eq!(config.xse_acronym, "F4SE");
    assert_eq!(config.game_version, "1.10.163");
    assert_eq!(config.crashgen_latest_og, "4.0.0");
    assert_eq!(config.classic_game_hints, vec!["Hint 1", "Hint 2"]);
    assert_eq!(config.warn_noplugins, "No plugins found!");
    assert_eq!(config.warn_outdated, "Your version is outdated.");

    // Crashgen/game_root fields (from Game_Info)
    assert_eq!(config.crashgen_name, "crash-og");
    assert_eq!(
        config.crashgen_ignore,
        vec!["OGIgnoreItem1", "OGIgnoreItem2"]
    );
    assert_eq!(config.game_root_name, "Fallout4");
}

#[test]
fn test_from_yaml_content_extracts_ignore_list() {
    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    assert_eq!(config.ignore_list, vec!["IgnoreItem1", "IgnoreItem2"]);
}

#[test]
fn test_from_yaml_content_extracts_exclude_lists() {
    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    assert_eq!(config.game_ignore_plugins, vec!["Unofficial*.esp"]);
    assert_eq!(config.game_ignore_records, vec!["RecordType1"]);
}

#[test]
fn test_from_yaml_content_extracts_suspect_patterns() {
    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    assert_eq!(config.suspect_error_rules.len(), 2);
    assert_eq!(config.suspect_error_rules[0].id, "error_pattern_1");
    assert_eq!(config.suspect_error_rules[0].name, "Error Pattern 1");
    assert_eq!(config.suspect_error_rules[0].severity, 4);
    assert_eq!(
        config.suspect_error_rules[0].main_error_contains_any,
        vec!["Error description 1".to_string()]
    );

    assert_eq!(config.suspect_stack_rules.len(), 1);
    assert_eq!(config.suspect_stack_rules[0].id, "stack_pattern_1");
    assert_eq!(config.suspect_stack_rules[0].name, "Stack Pattern 1");
    assert_eq!(config.suspect_stack_rules[0].severity, 3);
    assert_eq!(
        config.suspect_stack_rules[0].main_error_required_any,
        vec!["Main error required".to_string()]
    );
    assert_eq!(
        config.suspect_stack_rules[0].main_error_optional_any,
        vec!["Main error optional".to_string()]
    );
    assert_eq!(
        config.suspect_stack_rules[0].stack_contains_any,
        vec!["Stack pattern 1".to_string(), "Stack pattern 2".to_string()]
    );
    assert_eq!(
        config.suspect_stack_rules[0].exclude_if_stack_contains_any,
        vec!["Excluded pattern".to_string()]
    );
    assert_eq!(
        config.suspect_stack_rules[0].stack_contains_at_least.len(),
        1
    );
    assert_eq!(
        config.suspect_stack_rules[0].stack_contains_at_least[0].substring,
        "Repeated pattern"
    );
    assert_eq!(
        config.suspect_stack_rules[0].stack_contains_at_least[0].count,
        2
    );
}

#[test]
fn test_from_yaml_content_preserves_quoted_hex_markers_in_stack_rules() {
    let game_yaml = minimal_game_yaml().replacen(
        "    main_error_optional_any:\n      - \"Main error optional\"",
        "    main_error_optional_any: [\"3A0000\", \"AD0000\", \"8E0000\", \"F4EE\"]",
        1,
    );

    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        &game_yaml,
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    assert_eq!(
        config.suspect_stack_rules[0].main_error_optional_any,
        vec![
            "3A0000".to_string(),
            "AD0000".to_string(),
            "8E0000".to_string(),
            "F4EE".to_string(),
        ]
    );
}

#[test]
fn test_from_yaml_content_skips_zero_string_stack_count_rules() {
    let game_yaml = minimal_game_yaml().replacen("count: 2", "count: \"0\"", 1);

    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        &game_yaml,
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    assert!(
        config.suspect_stack_rules[0]
            .stack_contains_at_least
            .is_empty()
    );
}

#[test]
fn test_from_yaml_content_extracts_mod_databases() {
    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    assert_eq!(config.game_mods_conf.len(), 1);
    assert_eq!(config.game_mods_conf[0].mod_a, "modA");
    assert_eq!(config.game_mods_conf[0].description, "Config for ModA");

    assert_eq!(config.game_mods_core.len(), 3);
    assert_eq!(config.game_mods_core[0].detect, "ModB");
    assert_eq!(config.game_mods_core[0].name, "Core Mod B");
    assert_eq!(config.game_mods_core[0].description, "Core mod B");
    assert_eq!(config.game_mods_core[0].gpu, None);
    assert_eq!(config.game_mods_core[0].exclude_when, None);

    assert_eq!(config.game_mods_core[1].detect, "GpuMod.dll");
    assert_eq!(config.game_mods_core[1].gpu, Some("nvidia".to_string()));

    assert_eq!(config.game_mods_core[2].detect, "ExcludedMod.esp");
    assert_eq!(
        config.game_mods_core[2].exclude_when,
        Some(CoreModExclude::PluginAny(vec![
            "SomeWorldspace.esm".to_string()
        ]))
    );
    assert_eq!(config.game_mods_freq.len(), 1);
    assert_eq!(config.game_mods_freq[0].id, "freq-mod");
    assert_eq!(config.game_mods_freq[0].name, "Frequent Mod");
    assert_eq!(config.game_mods_freq[0].description, "Frequently used mod");
    assert_eq!(
        config.game_mods_freq[0].criteria,
        ModSolutionCriteria::Any(vec!["FreqMod".to_string()])
    );
    assert!(config.game_mods_freq[0].exceptions.is_empty());
    assert_eq!(config.game_mods_solu.len(), 1);
    assert_eq!(config.game_mods_solu[0].id, "solu-mod");
    assert_eq!(config.game_mods_solu[0].name, "Solution Mod");
    assert_eq!(config.game_mods_solu[0].description, "Solution mod");
    assert_eq!(
        config.game_mods_solu[0].criteria,
        ModSolutionCriteria::Any(vec!["SoluMod".to_string()])
    );
    assert!(config.game_mods_solu[0].exceptions.is_empty());
}

#[test]
fn test_from_yaml_content_parses_structured_mods_solu_entries() {
    let game_yaml = minimal_game_yaml().replacen(
        concat!(
            "Mods_SOLU:\n",
            "  - id: solu-mod\n",
            "    criteria:\n",
            "      any:\n",
            "        - SoluMod\n",
            "    name: Solution Mod\n",
            "    description: \"Solution mod\"\n"
        ),
        concat!(
            "Mods_SOLU:\n",
            "  - id: high-resolution-dlc\n",
            "    criteria:\n",
            "      any:\n",
            "        - DLCUltraHighResolution\n",
            "    exceptions:\n",
            "      - UHDTexturesFix.esp\n",
            "    name: High Resolution DLC\n",
            "    description: |\n",
            "      Disable the High Resolution Texture Pack.\n",
            "  - id: bodyslide-patch\n",
            "    criteria:\n",
            "      all:\n",
            "        - LooksMenu\n",
            "        - CBBE\n",
            "    name: BodySlide Patch\n",
            "    description: |\n",
            "      Install the compatibility patch.\n"
        ),
        1,
    );

    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        &game_yaml,
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .expect("from_yaml_content should parse structured Mods_SOLU entries");

    let debug_output = format!("{:?}", config.game_mods_solu);
    assert_eq!(config.game_mods_solu.len(), 2);
    assert!(debug_output.contains("high-resolution-dlc"));
    assert!(debug_output.contains("DLCUltraHighResolution"));
    assert!(debug_output.contains("UHDTexturesFix.esp"));
    assert!(debug_output.contains("BodySlide Patch"));

    let first = debug_output
        .find("high-resolution-dlc")
        .expect("first entry id should appear in debug output");
    let second = debug_output
        .find("bodyslide-patch")
        .expect("second entry id should appear in debug output");
    assert!(
        first < second,
        "Mods_SOLU entry order should follow YAML order"
    );
}

#[test]
fn test_from_yaml_content_rejects_legacy_mods_freq_map_format() {
    let legacy_game_yaml = minimal_game_yaml().replacen(
        r#"Mods_FREQ:
  - id: freq-mod
    criteria:
      any:
        - FreqMod
    name: Frequent Mod
    description: "Frequently used mod"
"#,
        r#"Mods_FREQ:
  FreqMod: "Frequently used mod"
"#,
        1,
    );

    let result = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        &legacy_game_yaml,
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    );

    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(matches!(err, ConfigError::ParseError { .. }));
    match err {
        ConfigError::ParseError { context, message } => {
            assert!(context.to_lowercase().contains("game yaml"));
            assert!(message.contains("Mods_FREQ"));
            assert!(message.to_lowercase().contains("legacy map format"));
        }
        _ => panic!("Expected ParseError"),
    }
}

#[test]
fn test_from_yaml_content_auto_game_version_uses_game_info_values() {
    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    // Game_Info fields populated
    assert_eq!(config.crashgen_name, "crash-og");
    assert_eq!(
        config.crashgen_ignore,
        vec!["OGIgnoreItem1", "OGIgnoreItem2"]
    );
    assert_eq!(config.game_root_name, "Fallout4");
}

#[test]
fn test_accessor_methods() {
    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    // Accessors return Game_Info values
    assert_eq!(config.get_crashgen_name(), "crash-og");
    assert_eq!(
        config.get_crashgen_ignore(),
        &["OGIgnoreItem1", "OGIgnoreItem2"]
    );
    assert_eq!(config.get_game_root_name(), "Fallout4");
}

#[test]
fn test_selected_game_version_parameter_does_not_affect_explicit_game_info_values() {
    // This fixture explicitly defines Game_Info values, so mode selection
    // should not change extracted crashgen metadata.
    let config_og = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    let config_vr = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "VR".to_string(),
    )
    .unwrap();

    assert_eq!(config_og.crashgen_name, config_vr.crashgen_name);
    assert_eq!(config_og.crashgen_ignore, config_vr.crashgen_ignore);
    assert_eq!(config_og.game_root_name, config_vr.game_root_name);
}

#[test]
fn test_from_yaml_content_skyrim_game() {
    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Skyrim".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    // Should use Skyrim-specific autoscan text
    assert_eq!(config.autoscan_text, "Autoscan Skyrim");
    // Should use Skyrim ignore list
    assert_eq!(config.ignore_list, vec!["SkyrimIgnore1"]);
}

#[test]
fn test_from_yaml_content_different_games_use_correct_ignore_lists() {
    let fallout_config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    let skyrim_config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Skyrim".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    assert_ne!(fallout_config.ignore_list, skyrim_config.ignore_list);
    assert_eq!(fallout_config.ignore_list.len(), 2);
    assert_eq!(skyrim_config.ignore_list.len(), 1);
}

// ============================================================
// Error Handling Tests
// ============================================================

#[test]
fn test_from_yaml_content_invalid_main_yaml() {
    let invalid_yaml = "{ invalid: yaml: content: }}}";

    let result = YamlDataCore::from_yaml_content(
        invalid_yaml,
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    );

    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(matches!(err, ConfigError::ParseError { .. }));
    match err {
        ConfigError::ParseError { context, .. } => {
            assert!(context.to_lowercase().contains("main yaml"));
        }
        _ => panic!("Expected ParseError"),
    }
}

#[test]
fn test_from_yaml_content_invalid_game_yaml() {
    let invalid_yaml = "invalid: [unclosed";

    let result = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        invalid_yaml,
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    );

    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(matches!(err, ConfigError::ParseError { .. }));
    match err {
        ConfigError::ParseError { context, .. } => {
            assert!(context.to_lowercase().contains("game yaml"));
        }
        _ => panic!("Expected ParseError"),
    }
}

#[test]
fn test_from_yaml_content_invalid_ignore_yaml() {
    let invalid_yaml = "not: valid: yaml: {{";

    let result = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        invalid_yaml,
        "Fallout4".to_string(),
        "auto".to_string(),
    );

    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(matches!(err, ConfigError::ParseError { .. }));
    match err {
        ConfigError::ParseError { context, .. } => {
            assert!(context.to_lowercase().contains("ignore yaml"));
        }
        _ => panic!("Expected ParseError"),
    }
}

#[test]
fn test_from_yaml_content_rejects_legacy_suspect_error_map_format() {
    let legacy_game_yaml = minimal_game_yaml().replacen(
        r#"Crashlog_Error_Check:
  - id: error_pattern_1
    name: Error Pattern 1
    severity: 4
    main_error_contains_any:
      - "Error description 1"
  - id: error_pattern_2
    name: Error Pattern 2
    severity: 2
    main_error_contains_any:
      - "Error description 2"
"#,
        r#"Crashlog_Error_Check:
  ErrorPattern1: "Error description 1"
  ErrorPattern2: "Error description 2"
"#,
        1,
    );

    let result = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        &legacy_game_yaml,
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    );

    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(matches!(err, ConfigError::ParseError { .. }));
    match err {
        ConfigError::ParseError { context, message } => {
            assert!(context.to_lowercase().contains("game yaml"));
            assert!(message.contains("Crashlog_Error_Check"));
            assert!(message.to_lowercase().contains("legacy map format"));
        }
        _ => panic!("Expected ParseError"),
    }
}

#[test]
fn test_from_yaml_content_rejects_legacy_suspect_stack_map_format() {
    let legacy_game_yaml = minimal_game_yaml().replacen(
        r#"Crashlog_Stack_Check:
  - id: stack_pattern_1
    name: Stack Pattern 1
    severity: 3
    main_error_required_any:
      - "Main error required"
    main_error_optional_any:
      - "Main error optional"
    stack_contains_any:
      - "Stack pattern 1"
      - "Stack pattern 2"
    exclude_if_stack_contains_any:
      - "Excluded pattern"
    stack_contains_at_least:
      - substring: "Repeated pattern"
        count: 2
"#,
        r#"Crashlog_Stack_Check:
  StackPattern1: "Stack description 1"
"#,
        1,
    );

    let result = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        &legacy_game_yaml,
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    );

    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(matches!(err, ConfigError::ParseError { .. }));
    match err {
        ConfigError::ParseError { context, message } => {
            assert!(context.to_lowercase().contains("game yaml"));
            assert!(message.contains("Crashlog_Stack_Check"));
            assert!(message.to_lowercase().contains("legacy map format"));
        }
        _ => panic!("Expected ParseError"),
    }
}

#[test]
fn test_from_yaml_content_empty_main_document() {
    let empty_yaml = "";

    let result = YamlDataCore::from_yaml_content(
        empty_yaml,
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    );

    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(matches!(err, ConfigError::EmptyDocument(_)));
    match err {
        ConfigError::EmptyDocument(msg) => {
            assert!(msg.contains("Main"));
        }
        _ => panic!("Expected EmptyDocument error"),
    }
}

#[test]
fn test_from_yaml_content_empty_game_document() {
    let empty_yaml = "";

    let result = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        empty_yaml,
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    );

    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(matches!(err, ConfigError::EmptyDocument(_)));
}

#[test]
fn test_from_yaml_content_empty_ignore_document() {
    let empty_yaml = "";

    let result = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        empty_yaml,
        "Fallout4".to_string(),
        "auto".to_string(),
    );

    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(matches!(err, ConfigError::EmptyDocument(_)));
}

#[test]
fn test_from_yaml_content_missing_keys_use_defaults() {
    // YAML with no matching keys - should use default empty values
    let sparse_main = r#"
other_key: value
"#;
    let sparse_game = r#"
unrelated: data
"#;
    let sparse_ignore = r#"
different_game: []
"#;

    let result = YamlDataCore::from_yaml_content(
        sparse_main,
        sparse_game,
        sparse_ignore,
        "Fallout4".to_string(),
        "auto".to_string(),
    );

    assert!(result.is_ok());
    let config = result.unwrap();
    // Missing values should be empty strings/vecs
    assert_eq!(config.classic_version, "");
    assert!(config.classic_records_list.is_empty());
    assert!(config.ignore_list.is_empty());
}

#[test]
fn test_from_yaml_content_falls_back_to_registry_metadata_when_game_info_is_minimal() {
    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml_main_root_only(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    // Main root name is still sourced from YAML.
    assert_eq!(config.game_root_name, "Fallout 4");

    // These fields should be backfilled from version registry metadata.
    assert!(!config.crashgen_name.is_empty());
    assert!(!config.crashgen_latest_og.is_empty());
    assert!(!config.xse_acronym.is_empty());
    assert!(!config.game_version.is_empty());

    // Legacy ignore fallback comes from Crashgen_Registry when Game_Info.CRASHGEN_Ignore is absent.
    assert_eq!(config.crashgen_ignore, vec!["BuffoutSpecificIgnore"]);
}

#[test]
fn test_from_yaml_content_registry_fallback_matches_for_spaced_and_compact_main_root_names() {
    let spaced_config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml_main_root_only(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();
    let compact_config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml_main_root_only_compact(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    assert_eq!(spaced_config.crashgen_name, compact_config.crashgen_name);
    assert_eq!(
        spaced_config.crashgen_latest_og,
        compact_config.crashgen_latest_og
    );
    assert_eq!(spaced_config.xse_acronym, compact_config.xse_acronym);
    assert_eq!(spaced_config.game_version, compact_config.game_version);
    assert_eq!(
        spaced_config.crashgen_ignore,
        compact_config.crashgen_ignore
    );
}

#[test]
fn test_from_yaml_content_registry_selected_mode_resolves_expected_versions() {
    let original = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml_main_root_only(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "Original".to_string(),
    )
    .unwrap();
    let next_gen = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml_main_root_only(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "NextGen".to_string(),
    )
    .unwrap();
    let anniversary = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml_main_root_only(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "AnniversaryEdition".to_string(),
    )
    .unwrap();
    let anniversary_alias = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml_main_root_only(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "AE".to_string(),
    )
    .unwrap();
    let vr = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml_main_root_only(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "VR".to_string(),
    )
    .unwrap();

    assert_eq!(original.game_version, "1.10.163");
    assert_eq!(next_gen.game_version, "1.10.984");
    assert_eq!(anniversary.game_version, "1.11.221");
    assert_eq!(anniversary_alias.game_version, anniversary.game_version);
    assert_eq!(vr.game_version, "1.2.72");
}

#[test]
fn test_from_yaml_content_respects_explicit_empty_crashgen_ignore() {
    let game_yaml = r#"
Game_Info:
  Main_Root_Name: "Fallout 4"
  CRASHGEN_LogName: "Buffout 4"
  CRASHGEN_Ignore: []
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

    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        game_yaml,
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    assert!(
        config.crashgen_ignore.is_empty(),
        "explicit empty CRASHGEN_Ignore must not be replaced by registry fallback"
    );
}

// ============================================================
// Async File Loading Tests
// ============================================================

#[tokio::test]
async fn test_load_from_yaml_files_success() {
    let temp_dir = tempdir().unwrap();

    // Create directory structure
    let databases_dir = temp_dir.path().join("databases");
    std::fs::create_dir_all(&databases_dir).unwrap();

    // Write test files
    let main_path = databases_dir.join("CLASSIC Main.yaml");
    let game_path = databases_dir.join("CLASSIC Fallout4.yaml");
    let ignore_path = temp_dir.path().join("CLASSIC Ignore.yaml");

    std::fs::write(&main_path, minimal_main_yaml()).unwrap();
    std::fs::write(&game_path, minimal_game_yaml()).unwrap();
    std::fs::write(&ignore_path, minimal_ignore_yaml()).unwrap();

    // Use the 2-element API (root_dir, data_dir)
    let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

    let result =
        YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), "auto".to_string())
            .await;

    assert!(result.is_ok(), "Load failed: {:?}", result.err());
    let config = result.unwrap();
    assert_eq!(config.classic_version, "7.31.0");
    assert_eq!(config.xse_acronym, "F4SE");
}

#[tokio::test]
async fn test_load_from_yaml_files_with_three_dirs() {
    let temp_dir = tempdir().unwrap();

    // Create separate directories for each YAML file
    let main_dir = temp_dir.path().join("main");
    let game_dir = temp_dir.path().join("game");
    let ignore_dir = temp_dir.path().join("ignore");

    std::fs::create_dir_all(&main_dir).unwrap();
    std::fs::create_dir_all(&game_dir).unwrap();
    std::fs::create_dir_all(&ignore_dir).unwrap();

    // Write test files
    std::fs::write(main_dir.join("CLASSIC Main.yaml"), minimal_main_yaml()).unwrap();
    std::fs::write(game_dir.join("CLASSIC Fallout4.yaml"), minimal_game_yaml()).unwrap();
    std::fs::write(
        ignore_dir.join("CLASSIC Ignore.yaml"),
        minimal_ignore_yaml(),
    )
    .unwrap();

    // Use the 3-element API
    let yaml_dirs = vec![main_dir, game_dir, ignore_dir];

    let result =
        YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), "auto".to_string())
            .await;

    assert!(result.is_ok(), "Load failed: {:?}", result.err());
    let config = result.unwrap();
    assert_eq!(config.classic_version, "7.31.0");
}

#[tokio::test]
async fn test_load_from_yaml_files_invalid_dir_count() {
    // Provide only 1 directory (invalid)
    let yaml_dirs = vec![PathBuf::from("/some/path")];

    let result =
        YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), "auto".to_string())
            .await;

    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(matches!(err, ConfigError::InvalidInput(_)));
}

#[tokio::test]
async fn test_load_from_yaml_files_invalid_four_dirs() {
    // Provide 4 directories (also invalid)
    let yaml_dirs = vec![
        PathBuf::from("/a"),
        PathBuf::from("/b"),
        PathBuf::from("/c"),
        PathBuf::from("/d"),
    ];

    let result =
        YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), "auto".to_string())
            .await;

    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(matches!(err, ConfigError::InvalidInput(_)));
}

#[tokio::test]
async fn test_load_from_yaml_files_missing_main_file() {
    let temp_dir = tempdir().unwrap();
    let databases_dir = temp_dir.path().join("databases");
    std::fs::create_dir_all(&databases_dir).unwrap();

    // Only write game and ignore files, not main
    std::fs::write(
        databases_dir.join("CLASSIC Fallout4.yaml"),
        minimal_game_yaml(),
    )
    .unwrap();
    std::fs::write(
        temp_dir.path().join("CLASSIC Ignore.yaml"),
        minimal_ignore_yaml(),
    )
    .unwrap();

    let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

    let result =
        YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), "auto".to_string())
            .await;

    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(matches!(err, ConfigError::IOError { .. }));
}

#[tokio::test]
async fn test_load_from_yaml_files_missing_game_file() {
    let temp_dir = tempdir().unwrap();
    let databases_dir = temp_dir.path().join("databases");
    std::fs::create_dir_all(&databases_dir).unwrap();

    // Write main and ignore, but not game
    std::fs::write(databases_dir.join("CLASSIC Main.yaml"), minimal_main_yaml()).unwrap();
    std::fs::write(
        temp_dir.path().join("CLASSIC Ignore.yaml"),
        minimal_ignore_yaml(),
    )
    .unwrap();

    let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

    let result =
        YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), "auto".to_string())
            .await;

    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(matches!(err, ConfigError::IOError { .. }));
}

#[tokio::test]
async fn test_load_from_yaml_files_missing_ignore_file() {
    let temp_dir = tempdir().unwrap();
    let databases_dir = temp_dir.path().join("databases");
    std::fs::create_dir_all(&databases_dir).unwrap();

    // Write main and game, but not ignore
    std::fs::write(databases_dir.join("CLASSIC Main.yaml"), minimal_main_yaml()).unwrap();
    std::fs::write(
        databases_dir.join("CLASSIC Fallout4.yaml"),
        minimal_game_yaml(),
    )
    .unwrap();

    let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

    let result =
        YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), "auto".to_string())
            .await;

    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(matches!(err, ConfigError::IOError { .. }));
}

#[tokio::test]
async fn test_load_from_yaml_files_parallel_preserves_order() {
    // This test verifies that tokio::join! preserves order
    // (unlike JoinSet which returns in completion order)
    let temp_dir = tempdir().unwrap();
    let databases_dir = temp_dir.path().join("databases");
    std::fs::create_dir_all(&databases_dir).unwrap();

    // Create files with distinct content
    let main_yaml = r#"
CLASSIC_Info:
  version: "MAIN_VERSION"
"#;
    let game_yaml = r#"
Game_Info:
  XSE_Acronym: "GAME_XSE"
"#;
    let ignore_yaml = r#"
CLASSIC_Ignore_TestGame:
  - "IGNORE_ITEM"
"#;

    std::fs::write(databases_dir.join("CLASSIC Main.yaml"), main_yaml).unwrap();
    std::fs::write(databases_dir.join("CLASSIC TestGame.yaml"), game_yaml).unwrap();
    std::fs::write(temp_dir.path().join("CLASSIC Ignore.yaml"), ignore_yaml).unwrap();

    let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

    let result =
        YamlDataCore::load_from_yaml_files(yaml_dirs, "TestGame".to_string(), "auto".to_string())
            .await;

    assert!(result.is_ok());
    let config = result.unwrap();

    // Verify that values from each file are correctly assigned
    assert_eq!(config.classic_version, "MAIN_VERSION");
    assert_eq!(config.xse_acronym, "GAME_XSE");
    assert_eq!(config.ignore_list, vec!["IGNORE_ITEM"]);
}

#[tokio::test]
async fn test_load_from_yaml_files_game_info_loading() {
    let temp_dir = tempdir().unwrap();
    let databases_dir = temp_dir.path().join("databases");
    std::fs::create_dir_all(&databases_dir).unwrap();

    std::fs::write(databases_dir.join("CLASSIC Main.yaml"), minimal_main_yaml()).unwrap();
    std::fs::write(
        databases_dir.join("CLASSIC Fallout4.yaml"),
        minimal_game_yaml(),
    )
    .unwrap();
    std::fs::write(
        temp_dir.path().join("CLASSIC Ignore.yaml"),
        minimal_ignore_yaml(),
    )
    .unwrap();

    let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

    let result =
        YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), "auto".to_string())
            .await;

    assert!(result.is_ok());
    let config = result.unwrap();
    // Game_Info fields should be populated
    assert_eq!(config.crashgen_name, "crash-og");
    assert_eq!(config.game_root_name, "Fallout4");
}

// ============================================================
// Clone and Debug Tests
// ============================================================

#[test]
fn test_yamldata_clone() {
    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    let cloned = config.clone();

    assert_eq!(config.classic_version, cloned.classic_version);
    assert_eq!(config.xse_acronym, cloned.xse_acronym);
    assert_eq!(config.ignore_list, cloned.ignore_list);
}

#[test]
fn test_yamldata_debug_format() {
    let config = YamlDataCore::from_yaml_content(
        minimal_main_yaml(),
        minimal_game_yaml(),
        minimal_ignore_yaml(),
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .unwrap();

    let debug_str = format!("{:?}", config);
    assert!(debug_str.contains("YamlDataCore"));
    assert!(debug_str.contains("classic_version"));
}

// ============================================================
// ConfigError Tests
// ============================================================

#[test]
fn test_config_error_invalid_input_display() {
    let err = ConfigError::InvalidInput("test message".to_string());
    let display = format!("{}", err);
    assert!(display.contains("Invalid input"));
    assert!(display.contains("test message"));
}

#[test]
fn test_config_error_empty_document_display() {
    let err = ConfigError::EmptyDocument("Main YAML".to_string());
    let display = format!("{}", err);
    assert!(display.contains("Empty YAML document"));
    assert!(display.contains("Main YAML"));
}

#[test]
fn test_config_error_parse_error_display() {
    let err = ConfigError::ParseError {
        context: "Failed to parse game YAML".to_string(),
        message: "document 1 must be a mapping".to_string(),
    };
    let display = format!("{}", err);
    assert!(display.contains("Failed to parse game YAML"));
    assert!(display.contains("document 1 must be a mapping"));
}

#[test]
fn test_config_error_io_error_display() {
    let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file not found");
    let err = ConfigError::IOError {
        context: "Failed to read config".to_string(),
        source: io_err,
    };
    let display = format!("{}", err);
    assert!(display.contains("Failed to read config"));
}
