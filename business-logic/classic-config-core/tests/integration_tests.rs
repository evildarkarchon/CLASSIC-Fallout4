//! Integration tests for classic-config-core
//!
//! These tests verify cross-component workflows involving configuration loading,
//! YAML parsing, and the interaction between classic-yaml-core and classic-config-core.

use classic_config_core::{
    ConfigError, ExplicitYamlDataLoadError, ExplicitYamlDataRequest, ExplicitYamlDataRole,
    YamlDataCore, load_explicit_yaml_data,
};
use classic_shared_core::GameId;
use std::fs;
use tempfile::tempdir;

/// Main YAML accepted by the explicit loader's schema-2.0 and semantic gates.
///
/// The `minimal_*` fixtures below predate those gates and are used only with
/// `from_yaml_content`, which performs no schema validation.
fn explicit_main_yaml() -> &'static str {
    r#"schema_version: "2.0"
CLASSIC_Info:
  version: "9.1.0"
  version_date: "2026-07-17"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan Fallout 4"
catch_log_records: []
"#
}

/// Game YAML accepted by the explicit loader's Fallout 4 role validation.
fn explicit_game_yaml() -> &'static str {
    r#"schema_version: "1.0"
Game_Info:
  Main_Root_Name: "Fallout 4"
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
Crashlog_Error_Check: []
Crashlog_Stack_Check: []
Mods_FREQ: []
Mods_SOLU: []
"#
}

// ============================================================================
// Test Data Fixtures
// ============================================================================

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

// ============================================================================
// Complete Configuration Loading Workflow Tests
// ============================================================================

mod config_loading_workflows {
    use super::*;

    /// Every section of all three documents reaches its own `YamlDataCore` field.
    ///
    /// This previously drove the positional two-directory loader. That loader is
    /// gone — installed selection now belongs to `load_installed_yaml_data` and
    /// caller-selected files to `load_explicit_yaml_data`, both of which end in
    /// the same document-to-field assembly exercised here.
    #[test]
    fn test_complete_config_load_workflow() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .expect("Config assembly should succeed");

        // Verify all configuration sections loaded correctly
        // Main YAML
        assert_eq!(config.classic_version, "7.31.0");
        assert_eq!(config.classic_version_date, "2024-01-15");
        assert_eq!(config.classic_records_list, vec!["LAND", "REFR", "CELL"]);
        assert_eq!(config.autoscan_text, "Autoscan Fallout 4");

        // Game YAML
        assert_eq!(config.xse_acronym, "F4SE");
        assert_eq!(config.game_version, "1.10.163");
        assert_eq!(config.crashgen_latest_og, "4.0.0");
        assert_eq!(config.classic_game_hints, vec!["Hint 1", "Hint 2"]);
        assert_eq!(config.warn_noplugins, "No plugins found!");

        // Crashgen fields (from Game_Info)
        assert_eq!(config.crashgen_name, "crash-og");
        assert_eq!(config.game_root_name, "Fallout4");

        // Ignore YAML
        assert_eq!(config.ignore_list, vec!["IgnoreItem1", "IgnoreItem2"]);
    }

    /// Test selected game version mode does not override explicit Game_Info values
    #[test]
    fn test_selected_game_version_does_not_affect_loading_workflow() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "VR".to_string(),
        )
        .expect("VR config assembly should succeed");

        // Game_Info fields populated
        assert_eq!(config.crashgen_name, "crash-og");
        assert_eq!(config.crashgen_ignore, vec!["OGIgnoreItem1"]);
        assert_eq!(config.game_root_name, "Fallout4");
        assert_eq!(config.crashgen_latest_og, "4.0.0");

        // Accessors return Game_Info values
        assert_eq!(config.get_crashgen_name(), "crash-og");
        assert_eq!(config.get_game_root_name(), "Fallout4");
    }
}

// ============================================================================
// Multi-Game Configuration Tests
// ============================================================================

mod multi_game_config {
    use super::*;

    /// One shared Main document plus per-game game/Ignore data keys off the
    /// selected game, so two games assembled from the same Main and Ignore
    /// documents resolve different interface text and ignore entries.
    #[test]
    fn test_multi_game_configuration() {
        let skyrim_yaml = r#"
Game_Info:
  XSE_Acronym: "SKSE"
  GameVersion: "1.6.640"
Game_Hints:
  - "Skyrim Hint 1"
"#;

        let fallout_config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .expect("Fallout4 config should assemble");

        assert_eq!(fallout_config.xse_acronym, "F4SE");
        assert_eq!(fallout_config.autoscan_text, "Autoscan Fallout 4");
        assert_eq!(
            fallout_config.ignore_list,
            vec!["IgnoreItem1", "IgnoreItem2"]
        );

        let skyrim_config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            skyrim_yaml,
            minimal_ignore_yaml(),
            "Skyrim".to_string(),
            "auto".to_string(),
        )
        .expect("Skyrim config should assemble");

        assert_eq!(skyrim_config.xse_acronym, "SKSE");
        assert_eq!(skyrim_config.autoscan_text, "Autoscan Skyrim");
        assert_eq!(skyrim_config.ignore_list, vec!["SkyrimIgnore1"]);
    }
}

// ============================================================================
// from_yaml_content Workflow Tests
// ============================================================================

mod from_content_workflows {
    use super::*;

    /// Test creating config from content strings
    #[test]
    fn test_from_content_workflow() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .expect("from_yaml_content should succeed");

        // All sections should be populated
        assert!(!config.classic_version.is_empty());
        assert!(!config.xse_acronym.is_empty());
        assert!(!config.ignore_list.is_empty());
    }

    #[test]
    fn test_from_yaml_content_merges_multiple_documents_per_input() {
        let main = concat!(
            "CLASSIC_Info:\n",
            "  version: \"7.31.0\"\n",
            "---\n",
            "CLASSIC_Interface:\n",
            "  autoscan_text_Fallout4: \"Merged Autoscan\"\n",
        );
        let game = concat!(
            "Game_Info:\n",
            "  XSE_Acronym: \"F4SE\"\n",
            "---\n",
            "Warnings_CRASHGEN:\n",
            "  Warn_NOPlugins: \"Merged warning\"\n",
        );
        let ignore = concat!(
            "CLASSIC_Ignore_Fallout4:\n",
            "  - \"IgnoreA\"\n",
            "---\n",
            "CLASSIC_Ignore_Skyrim:\n",
            "  - \"IgnoreB\"\n",
        );

        let config = YamlDataCore::from_yaml_content(
            main,
            game,
            ignore,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .expect("from_yaml_content should merge multiple documents per input");

        assert_eq!(config.classic_version, "7.31.0");
        assert_eq!(config.autoscan_text, "Merged Autoscan");
        assert_eq!(config.xse_acronym, "F4SE");
        assert_eq!(config.warn_noplugins, "Merged warning");
        assert_eq!(config.ignore_list, vec!["IgnoreA"]);
    }

    /// Test from_content produces identical results across selected game modes
    #[test]
    fn test_from_content_selected_game_version_ignored_for_explicit_game_info() {
        let vr_config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "VR".to_string(),
        )
        .expect("VR from_yaml_content should succeed");

        let og_config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .expect("OG from_yaml_content should succeed");

        // Both configs should have identical fields for this fixture.
        assert_eq!(vr_config.crashgen_name, og_config.crashgen_name);
        assert_eq!(vr_config.crashgen_name, "crash-og");

        // Accessors return Game_Info values
        assert_eq!(vr_config.get_crashgen_name(), "crash-og");
        assert_eq!(og_config.get_crashgen_name(), "crash-og");
    }

    /// Test from_content extracts all mod databases
    #[test]
    fn test_from_content_mod_databases() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .expect("from_yaml_content should succeed");

        // All mod databases should be populated
        assert_eq!(config.game_mods_conf.len(), 1);
        assert_eq!(config.game_mods_conf[0].mod_a, "modA");
        assert_eq!(config.game_mods_conf[0].description, "Config for ModA");
        assert_eq!(config.game_mods_core.len(), 1);
        assert_eq!(config.game_mods_core[0].detect, "ModB");
        assert_eq!(config.game_mods_core[0].name, "Core Mod B");
        assert_eq!(config.game_mods_core[0].description, "Core mod B");
        assert_eq!(config.game_mods_freq.len(), 1);
        assert_eq!(config.game_mods_freq[0].id, "freq-mod");
        assert_eq!(config.game_mods_freq[0].name, "Frequent Mod");
        assert_eq!(config.game_mods_freq[0].description, "Frequently used mod");
        assert_eq!(config.game_mods_solu.len(), 1);
        assert_eq!(config.game_mods_solu[0].id, "solu-mod");
        assert_eq!(config.game_mods_solu[0].name, "Solution Mod");
        assert_eq!(config.game_mods_solu[0].description, "Solution mod");
    }
}

// ============================================================================
// Error Handling Workflow Tests
// ============================================================================

mod error_handling_workflows {
    use super::*;

    /// A caller-selected file that does not exist fails with a typed role and path.
    ///
    /// The positional loader this replaced reported one untyped `IOError` no
    /// matter which of the three files was absent. The retained explicit seam
    /// names the role, which is what a tooling caller needs to fix its input.
    #[tokio::test]
    async fn test_missing_file_error() {
        let temp_dir = tempdir().expect("Failed to create temp dir");
        let main_path = temp_dir.path().join("main.yaml");
        fs::write(&main_path, explicit_main_yaml()).expect("Failed to write main YAML");

        // Game and Local Ignore are deliberately absent.
        let missing_game = temp_dir.path().join("absent-game.yaml");

        let result = load_explicit_yaml_data(ExplicitYamlDataRequest {
            main_path,
            game_path: missing_game.clone(),
            ignore_path: temp_dir.path().join("absent-ignore.yaml"),
            game: GameId::Fallout4,
            selected_game_version: "auto".to_string(),
        })
        .await;

        match result {
            Err(ExplicitYamlDataLoadError::Read { role, path, .. }) => {
                assert_eq!(role, ExplicitYamlDataRole::Game);
                assert_eq!(path, missing_game);
            }
            Err(e) => panic!("Expected a typed Read failure, got {e:?}"),
            Ok(_) => panic!("Should fail with missing files"),
        }
    }

    /// Test invalid YAML error handling
    #[test]
    fn test_invalid_yaml_error() {
        let invalid_yaml = "{ invalid: yaml: content: }}}";

        let result = YamlDataCore::from_yaml_content(
            invalid_yaml,
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        );

        assert!(result.is_err());
        match result {
            Err(ConfigError::ParseError { context, .. }) => {
                assert!(context.contains("main"), "Should mention main YAML");
            }
            Err(e) => panic!("Expected ParseError, got {:?}", e),
            Ok(_) => panic!("Should fail with invalid YAML"),
        }
    }

    #[test]
    fn test_from_yaml_content_non_mapping_later_document_returns_parse_like_error() {
        let invalid_game_yaml = concat!(
            "Game_Info:\n",
            "  XSE_Acronym: \"F4SE\"\n",
            "---\n",
            "- invalid\n",
        );

        let result = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            invalid_game_yaml,
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        );

        assert!(result.is_err());
        match result {
            Err(ConfigError::ParseError { context, .. }) => {
                assert!(context.contains("game") || context.contains("Game"));
            }
            Err(e) => panic!("Expected ParseError, got {:?}", e),
            Ok(_) => panic!("Should fail when a later YAML document is not a mapping"),
        }
    }

    /// Test empty document error handling
    #[test]
    fn test_empty_document_error() {
        let result = YamlDataCore::from_yaml_content(
            "",
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        );

        assert!(result.is_err());
        match result {
            Err(ConfigError::EmptyDocument(msg)) => {
                assert!(msg.contains("Main"), "Should mention Main YAML");
            }
            Err(e) => panic!("Expected EmptyDocument, got {:?}", e),
            Ok(_) => panic!("Should fail with empty document"),
        }
    }
}

// ============================================================================
// Explicit-File Loading Tests
//
// The removed positional loader read its three files with `tokio::join!`, so
// these cases used to be framed as "parallel loading". The retained
// deterministic seam is `load_explicit_yaml_data`; what still matters is that
// concurrent loads stay independent and that multi-document files merge.
// ============================================================================

mod explicit_file_loading {
    use super::*;

    /// Each of the three files may carry several `---` documents, which merge
    /// within that file before the roles are assembled.
    #[tokio::test]
    async fn test_explicit_load_merges_multiple_documents_per_file() {
        let temp_dir = tempdir().expect("Failed to create temp dir");
        let main_path = temp_dir.path().join("main.yaml");
        let game_path = temp_dir.path().join("game.yaml");
        let ignore_path = temp_dir.path().join("ignore.yaml");

        fs::write(
            &main_path,
            concat!(
                "schema_version: \"2.0\"\n",
                "CLASSIC_Info:\n",
                "  version: \"9.1.0\"\n",
                "  version_date: \"2026-07-17\"\n",
                "catch_log_records: []\n",
                "---\n",
                "CLASSIC_Interface:\n",
                "  autoscan_text_Fallout4: \"Merged Autoscan\"\n",
            ),
        )
        .expect("Failed to write main YAML");
        fs::write(
            &game_path,
            concat!(
                "schema_version: \"1.0\"\n",
                "Game_Info:\n",
                "  Main_Root_Name: \"Fallout 4\"\n",
                "  XSE_Acronym: \"F4SE\"\n",
                "  GameVersion: \"1.10.163\"\n",
                "Crashlog_Error_Check: []\n",
                "Crashlog_Stack_Check: []\n",
                "Mods_FREQ: []\n",
                "Mods_SOLU: []\n",
                "---\n",
                "Warnings_CRASHGEN:\n",
                "  Warn_NOPlugins: \"Merged warning\"\n",
            ),
        )
        .expect("Failed to write game YAML");
        fs::write(
            &ignore_path,
            concat!(
                "CLASSIC_Ignore_Fallout4:\n",
                "  - \"IgnoreA\"\n",
                "---\n",
                "CLASSIC_Ignore_Skyrim:\n",
                "  - \"IgnoreB\"\n",
            ),
        )
        .expect("Failed to write ignore YAML");

        let snapshot = load_explicit_yaml_data(ExplicitYamlDataRequest {
            main_path,
            game_path,
            ignore_path,
            game: GameId::Fallout4,
            selected_game_version: "auto".to_string(),
        })
        .await
        .expect("explicit loading should merge multiple documents per file");

        let config = snapshot.yaml_data();
        assert_eq!(config.classic_version, "9.1.0");
        assert_eq!(config.autoscan_text, "Merged Autoscan");
        assert_eq!(config.xse_acronym, "F4SE");
        assert_eq!(config.warn_noplugins, "Merged warning");
        // Only the selected game's Ignore key is read.
        assert_eq!(config.ignore_list, vec!["IgnoreA"]);
    }

    /// Concurrent explicit loads of the same files each produce an independent
    /// snapshot; nothing is shared or cached across them.
    #[tokio::test]
    async fn test_concurrent_explicit_loading() {
        let temp_dir = tempdir().expect("Failed to create temp dir");
        let main_path = temp_dir.path().join("main.yaml");
        let game_path = temp_dir.path().join("game.yaml");
        let ignore_path = temp_dir.path().join("ignore.yaml");

        fs::write(&main_path, explicit_main_yaml()).expect("Failed to write main YAML");
        fs::write(&game_path, explicit_game_yaml()).expect("Failed to write game YAML");
        fs::write(&ignore_path, "CLASSIC_Ignore_Fallout4: []\n")
            .expect("Failed to write ignore YAML");

        let mut handles = Vec::new();
        for _ in 0..4 {
            let request = ExplicitYamlDataRequest {
                main_path: main_path.clone(),
                game_path: game_path.clone(),
                ignore_path: ignore_path.clone(),
                game: GameId::Fallout4,
                selected_game_version: "auto".to_string(),
            };
            handles.push(tokio::spawn(async move {
                load_explicit_yaml_data(request).await
            }));
        }

        for handle in handles {
            let snapshot = handle
                .await
                .expect("Task should complete")
                .expect("explicit load should succeed");
            assert_eq!(snapshot.yaml_data().classic_version, "9.1.0");
            assert_eq!(snapshot.yaml_data().xse_acronym, "F4SE");
        }
    }
}

// ============================================================================
// Clone and Debug Tests
// ============================================================================

mod clone_debug {
    use super::*;

    /// Test config cloning preserves all data
    #[test]
    fn test_config_clone() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .expect("from_yaml_content should succeed");

        let cloned = config.clone();

        // All fields should match
        assert_eq!(cloned.classic_version, config.classic_version);
        assert_eq!(cloned.xse_acronym, config.xse_acronym);
        assert_eq!(cloned.ignore_list, config.ignore_list);
        assert_eq!(cloned.game_mods_conf, config.game_mods_conf);
        assert_eq!(cloned.suspect_error_rules, config.suspect_error_rules);
    }

    /// Test debug format
    #[test]
    fn test_config_debug_format() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .expect("from_yaml_content should succeed");

        let debug_str = format!("{:?}", config);

        // Debug output should contain struct name and key fields
        assert!(debug_str.contains("YamlDataCore"));
        assert!(debug_str.contains("classic_version"));
    }
}

// ============================================================================
// Missing Key Handling Tests
// ============================================================================

mod missing_keys {
    use super::*;

    /// Test that missing keys use empty defaults
    #[test]
    fn test_missing_keys_use_defaults() {
        // Sparse YAML with no matching keys
        let sparse_main = "other_key: value\n";
        let sparse_game = "unrelated: data\n";
        let sparse_ignore = "different_game: []\n";

        let config = YamlDataCore::from_yaml_content(
            sparse_main,
            sparse_game,
            sparse_ignore,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .expect("from_yaml_content should succeed");

        // Missing values should be empty
        assert_eq!(config.classic_version, "");
        assert!(config.classic_records_list.is_empty());
        assert!(config.ignore_list.is_empty());
        assert!(config.game_mods_conf.is_empty());
    }
}
