//! Integration tests for classic-config-core
//!
//! These tests verify cross-component workflows involving configuration loading,
//! YAML parsing, and the interaction between classic-yaml-core and classic-config-core.

use classic_config_core::{ConfigError, YamlDataCore};
use std::fs;
use std::path::PathBuf;
use tempfile::tempdir;

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
  ErrorPattern1: "Error description 1"
  ErrorPattern2: "Error description 2"
Crashlog_Stack_Check:
  StackPattern1: "Stack description 1"
Mods_CONF:
  ModA: "Config for ModA"
Mods_CORE:
  ModB: "Core mod B"
Mods_CORE_FOLON:
  FolonMod: "Folon specific mod"
Mods_FREQ:
  FreqMod: "Frequently used mod"
Mods_OPC2:
  OpcMod: "OPC2 mod"
Mods_SOLU:
  SoluMod: "Solution mod"
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

    /// Test complete configuration loading from files
    #[tokio::test]
    async fn test_complete_config_load_workflow() {
        let temp_dir = tempdir().expect("Failed to create temp dir");

        // Create directory structure matching CLASSIC layout
        let databases_dir = temp_dir.path().join("databases");
        fs::create_dir_all(&databases_dir).expect("Failed to create databases dir");

        // Write config files
        fs::write(databases_dir.join("CLASSIC Main.yaml"), minimal_main_yaml())
            .expect("Failed to write main YAML");
        fs::write(
            databases_dir.join("CLASSIC Fallout4.yaml"),
            minimal_game_yaml(),
        )
        .expect("Failed to write game YAML");
        fs::write(
            temp_dir.path().join("CLASSIC Ignore.yaml"),
            minimal_ignore_yaml(),
        )
        .expect("Failed to write ignore YAML");

        // Load configuration using 2-element API (root_dir, data_dir)
        let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

        let config = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await
        .expect("Config load should succeed");

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

    /// Test loading with 3-directory API (legacy)
    #[tokio::test]
    async fn test_three_directory_api_workflow() {
        let temp_dir = tempdir().expect("Failed to create temp dir");

        // Create separate directories for each config type
        let main_dir = temp_dir.path().join("main");
        let game_dir = temp_dir.path().join("game");
        let ignore_dir = temp_dir.path().join("ignore");

        fs::create_dir_all(&main_dir).expect("Failed to create main dir");
        fs::create_dir_all(&game_dir).expect("Failed to create game dir");
        fs::create_dir_all(&ignore_dir).expect("Failed to create ignore dir");

        // Write files in their respective directories
        fs::write(main_dir.join("CLASSIC Main.yaml"), minimal_main_yaml())
            .expect("Failed to write main YAML");
        fs::write(game_dir.join("CLASSIC Fallout4.yaml"), minimal_game_yaml())
            .expect("Failed to write game YAML");
        fs::write(
            ignore_dir.join("CLASSIC Ignore.yaml"),
            minimal_ignore_yaml(),
        )
        .expect("Failed to write ignore YAML");

        // Load using 3-element API
        let yaml_dirs = vec![main_dir, game_dir, ignore_dir];

        let config = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await
        .expect("Config load should succeed");

        assert_eq!(config.classic_version, "7.31.0");
        assert_eq!(config.xse_acronym, "F4SE");
    }

    /// Test selected game version mode does not override explicit Game_Info values
    #[tokio::test]
    async fn test_selected_game_version_does_not_affect_loading_workflow() {
        let temp_dir = tempdir().expect("Failed to create temp dir");
        let databases_dir = temp_dir.path().join("databases");
        fs::create_dir_all(&databases_dir).expect("Failed to create databases dir");

        fs::write(databases_dir.join("CLASSIC Main.yaml"), minimal_main_yaml())
            .expect("Failed to write main YAML");
        fs::write(
            databases_dir.join("CLASSIC Fallout4.yaml"),
            minimal_game_yaml(),
        )
        .expect("Failed to write game YAML");
        fs::write(
            temp_dir.path().join("CLASSIC Ignore.yaml"),
            minimal_ignore_yaml(),
        )
        .expect("Failed to write ignore YAML");

        let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

        let config =
            YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), "VR".to_string())
                .await
                .expect("VR config load should succeed");

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

    /// Test loading configuration for different games
    #[tokio::test]
    async fn test_multi_game_configuration() {
        let temp_dir = tempdir().expect("Failed to create temp dir");
        let databases_dir = temp_dir.path().join("databases");
        fs::create_dir_all(&databases_dir).expect("Failed to create databases dir");

        // Write main YAML (shared)
        fs::write(databases_dir.join("CLASSIC Main.yaml"), minimal_main_yaml())
            .expect("Failed to write main YAML");

        // Write game-specific YAMLs
        fs::write(
            databases_dir.join("CLASSIC Fallout4.yaml"),
            minimal_game_yaml(),
        )
        .expect("Failed to write Fallout4 YAML");

        let skyrim_yaml = r#"
Game_Info:
  XSE_Acronym: "SKSE"
  GameVersion: "1.6.640"
Game_Hints:
  - "Skyrim Hint 1"
"#;
        fs::write(databases_dir.join("CLASSIC Skyrim.yaml"), skyrim_yaml)
            .expect("Failed to write Skyrim YAML");

        // Write ignore YAML with both games
        fs::write(
            temp_dir.path().join("CLASSIC Ignore.yaml"),
            minimal_ignore_yaml(),
        )
        .expect("Failed to write ignore YAML");

        let base_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

        // Load Fallout4 config
        let fallout_config = YamlDataCore::load_from_yaml_files(
            base_dirs.clone(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await
        .expect("Fallout4 config should load");

        assert_eq!(fallout_config.xse_acronym, "F4SE");
        assert_eq!(fallout_config.autoscan_text, "Autoscan Fallout 4");
        assert_eq!(
            fallout_config.ignore_list,
            vec!["IgnoreItem1", "IgnoreItem2"]
        );

        // Load Skyrim config
        let skyrim_config =
            YamlDataCore::load_from_yaml_files(base_dirs, "Skyrim".to_string(), "auto".to_string())
                .await
                .expect("Skyrim config should load");

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
        assert_eq!(
            config.game_mods_conf.get("ModA"),
            Some(&"Config for ModA".to_string())
        );
        assert_eq!(
            config.game_mods_core.get("ModB"),
            Some(&"Core mod B".to_string())
        );
        assert_eq!(
            config.game_mods_core_folon.get("FolonMod"),
            Some(&"Folon specific mod".to_string())
        );
        assert_eq!(
            config.game_mods_freq.get("FreqMod"),
            Some(&"Frequently used mod".to_string())
        );
        assert_eq!(
            config.game_mods_opc2.get("OpcMod"),
            Some(&"OPC2 mod".to_string())
        );
        assert_eq!(
            config.game_mods_solu.get("SoluMod"),
            Some(&"Solution mod".to_string())
        );
    }
}

// ============================================================================
// Error Handling Workflow Tests
// ============================================================================

mod error_handling_workflows {
    use super::*;

    /// Test missing file error handling
    #[tokio::test]
    async fn test_missing_file_error() {
        let temp_dir = tempdir().expect("Failed to create temp dir");
        let databases_dir = temp_dir.path().join("databases");
        fs::create_dir_all(&databases_dir).expect("Failed to create databases dir");

        // Only create main YAML, missing game and ignore
        fs::write(databases_dir.join("CLASSIC Main.yaml"), minimal_main_yaml())
            .expect("Failed to write main YAML");

        let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

        let result = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await;

        assert!(result.is_err());
        match result {
            Err(ConfigError::IOError { context, .. }) => {
                assert!(
                    context.contains("not found") || context.contains("YAML file"),
                    "Should mention file not found"
                );
            }
            Err(e) => panic!("Expected IOError, got {:?}", e),
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

    /// Test invalid directory count error
    #[tokio::test]
    async fn test_invalid_directory_count() {
        // 1 directory (invalid)
        let result = YamlDataCore::load_from_yaml_files(
            vec![PathBuf::from("/some/path")],
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await;

        assert!(result.is_err());
        match result {
            Err(ConfigError::InvalidInput(msg)) => {
                assert!(
                    msg.contains("2") || msg.contains("3"),
                    "Should mention required directory count"
                );
            }
            Err(e) => panic!("Expected InvalidInput, got {:?}", e),
            Ok(_) => panic!("Should fail with invalid directory count"),
        }

        // 4 directories (also invalid)
        let result = YamlDataCore::load_from_yaml_files(
            vec![
                PathBuf::from("/a"),
                PathBuf::from("/b"),
                PathBuf::from("/c"),
                PathBuf::from("/d"),
            ],
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await;

        assert!(result.is_err());
        match result {
            Err(ConfigError::InvalidInput(_)) => (),
            Err(e) => panic!("Expected InvalidInput, got {:?}", e),
            Ok(_) => panic!("Should fail with invalid directory count"),
        }
    }
}

// ============================================================================
// Parallel Loading Tests
// ============================================================================

mod parallel_loading {
    use super::*;

    #[tokio::test]
    async fn test_load_from_yaml_files_merges_multiple_documents() {
        let temp_dir = tempdir().expect("Failed to create temp dir");
        let databases_dir = temp_dir.path().join("databases");
        fs::create_dir_all(&databases_dir).expect("Failed to create databases dir");

        fs::write(
            databases_dir.join("CLASSIC Main.yaml"),
            concat!(
                "CLASSIC_Info:\n",
                "  version: \"7.31.0\"\n",
                "---\n",
                "CLASSIC_Interface:\n",
                "  autoscan_text_Fallout4: \"Merged Autoscan\"\n",
            ),
        )
        .expect("Failed to write main YAML");
        fs::write(
            databases_dir.join("CLASSIC Fallout4.yaml"),
            concat!(
                "Game_Info:\n",
                "  XSE_Acronym: \"F4SE\"\n",
                "---\n",
                "Warnings_CRASHGEN:\n",
                "  Warn_NOPlugins: \"Merged warning\"\n",
            ),
        )
        .expect("Failed to write game YAML");
        fs::write(
            temp_dir.path().join("CLASSIC Ignore.yaml"),
            concat!(
                "CLASSIC_Ignore_Fallout4:\n",
                "  - \"IgnoreA\"\n",
                "---\n",
                "CLASSIC_Ignore_Skyrim:\n",
                "  - \"IgnoreB\"\n",
            ),
        )
        .expect("Failed to write ignore YAML");

        let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

        let config = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await
        .expect("load_from_yaml_files should merge multiple documents");

        assert_eq!(config.classic_version, "7.31.0");
        assert_eq!(config.autoscan_text, "Merged Autoscan");
        assert_eq!(config.xse_acronym, "F4SE");
        assert_eq!(config.warn_noplugins, "Merged warning");
        assert_eq!(config.ignore_list, vec!["IgnoreA"]);
    }

    /// Test that parallel loading preserves file order
    #[tokio::test]
    async fn test_parallel_loading_order_preserved() {
        let temp_dir = tempdir().expect("Failed to create temp dir");
        let databases_dir = temp_dir.path().join("databases");
        fs::create_dir_all(&databases_dir).expect("Failed to create databases dir");

        // Create files with unique identifiers
        let main_yaml = r#"
CLASSIC_Info:
  version: "MAIN_UNIQUE_VERSION"
"#;
        let game_yaml = r#"
Game_Info:
  XSE_Acronym: "GAME_UNIQUE_XSE"
"#;
        let ignore_yaml = r#"
CLASSIC_Ignore_TestGame:
  - "IGNORE_UNIQUE_ITEM"
"#;

        fs::write(databases_dir.join("CLASSIC Main.yaml"), main_yaml)
            .expect("Failed to write main YAML");
        fs::write(databases_dir.join("CLASSIC TestGame.yaml"), game_yaml)
            .expect("Failed to write game YAML");
        fs::write(temp_dir.path().join("CLASSIC Ignore.yaml"), ignore_yaml)
            .expect("Failed to write ignore YAML");

        let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

        let config = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "TestGame".to_string(),
            "auto".to_string(),
        )
        .await
        .expect("Config load should succeed");

        // Verify values from each file are correctly assigned
        assert_eq!(
            config.classic_version, "MAIN_UNIQUE_VERSION",
            "Version should come from main YAML"
        );
        assert_eq!(
            config.xse_acronym, "GAME_UNIQUE_XSE",
            "XSE should come from game YAML"
        );
        assert_eq!(
            config.ignore_list,
            vec!["IGNORE_UNIQUE_ITEM"],
            "Ignore list should come from ignore YAML"
        );
    }

    /// Test concurrent configuration loading
    #[tokio::test]
    async fn test_concurrent_config_loading() {
        let temp_dir = tempdir().expect("Failed to create temp dir");
        let databases_dir = temp_dir.path().join("databases");
        fs::create_dir_all(&databases_dir).expect("Failed to create databases dir");

        fs::write(databases_dir.join("CLASSIC Main.yaml"), minimal_main_yaml())
            .expect("Failed to write main YAML");
        fs::write(
            databases_dir.join("CLASSIC Fallout4.yaml"),
            minimal_game_yaml(),
        )
        .expect("Failed to write game YAML");
        fs::write(
            temp_dir.path().join("CLASSIC Ignore.yaml"),
            minimal_ignore_yaml(),
        )
        .expect("Failed to write ignore YAML");

        let base_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

        // Spawn multiple concurrent loads
        let mut handles = Vec::new();
        for _ in 0..4 {
            let dirs = base_dirs.clone();
            handles.push(tokio::spawn(async move {
                YamlDataCore::load_from_yaml_files(dirs, "Fallout4".to_string(), "auto".to_string())
                    .await
            }));
        }

        // All loads should succeed
        for handle in handles {
            let result = handle.await.expect("Task should complete");
            let config = result.expect("Config load should succeed");
            assert_eq!(config.classic_version, "7.31.0");
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
        assert_eq!(cloned.suspects_error_list, config.suspects_error_list);
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
