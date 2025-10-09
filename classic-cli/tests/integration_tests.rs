use classic_cli::{CliArgs, CliConfig, PathConfig, OutputFormatter, ScanStats};
use std::path::PathBuf;
use tempfile::tempdir;
use tokio::fs;

// Note: These are integration tests that test multiple components together
// They use the internal API, not the CLI binary itself

mod config_integration {
    use super::*;

    #[tokio::test]
    async fn test_config_persistence_workflow() {
        let temp_dir = tempdir().unwrap();
        let config_path = temp_dir.path().join("CLASSIC Settings.yaml");

        // Simulate first run: no config exists
        assert!(!config_path.exists());

        // Create default config and save
        let config = CliConfig::default();
        config.save_to_yaml(&config_path).await.unwrap();

        // Verify file was created
        assert!(config_path.exists());

        // Load config and verify it matches
        let loaded = CliConfig::load_from_yaml(&config_path).await.unwrap();

        assert_eq!(loaded.fcx_mode, config.fcx_mode);
        assert_eq!(loaded.update_check, config.update_check);
    }

    #[tokio::test]
    async fn test_config_cli_args_override_workflow() {
        let temp_dir = tempdir().unwrap();
        let config_path = temp_dir.path().join("CLASSIC Settings.yaml");

        // Save initial config with fcx_mode = false
        let mut initial_config = CliConfig::default();
        initial_config.fcx_mode = false;
        initial_config.save_to_yaml(&config_path).await.unwrap();

        // Simulate CLI run with --fcx-mode flag
        let args = CliArgs {
            fcx_mode: true,         // Override via CLI flag
            show_fid_values: false,
            stat_logging: false,
            move_unsolved: false,
            ini_path: None,
            scan_path: None,
            mods_folder_path: None,
            simplify_logs: false,
        };

        // Load config with CLI args
        let loaded = CliConfig::load_or_create(&config_path, &args)
            .await
            .unwrap();

        // Verify CLI arg took precedence
        assert!(loaded.fcx_mode);
    }

    #[tokio::test]
    async fn test_config_multiple_saves() {
        let temp_dir = tempdir().unwrap();
        let config_path = temp_dir.path().join("CLASSIC Settings.yaml");

        // First save
        let mut config1 = CliConfig::default();
        config1.fcx_mode = true;
        config1.save_to_yaml(&config_path).await.unwrap();

        // Second save (overwrite)
        let mut config2 = CliConfig::default();
        config2.fcx_mode = false;
        config2.stat_logging = true;
        config2.save_to_yaml(&config_path).await.unwrap();

        // Load and verify second save took effect
        let loaded = CliConfig::load_from_yaml(&config_path).await.unwrap();

        assert!(!loaded.fcx_mode);
        assert!(loaded.stat_logging);
    }
}

mod error_handling_integration {
    use super::*;

    #[tokio::test]
    async fn test_config_missing_file_error() {
        let temp_dir = tempdir().unwrap();
        let nonexistent = temp_dir.path().join("nonexistent.yaml");

        let result = CliConfig::load_from_yaml(&nonexistent).await;
        assert!(result.is_err());

        let error = result.unwrap_err();
        assert!(error.to_string().contains("Failed to read config file"));
    }

    #[tokio::test]
    async fn test_config_invalid_yaml_error() {
        let temp_dir = tempdir().unwrap();
        let invalid_yaml = temp_dir.path().join("invalid.yaml");

        // Write invalid YAML
        fs::write(&invalid_yaml, "invalid: yaml: content:\n  - broken")
            .await
            .unwrap();

        let result = CliConfig::load_from_yaml(&invalid_yaml).await;
        assert!(result.is_err());
    }
}

mod yaml_round_trip_integration {
    use super::*;

    #[tokio::test]
    async fn test_config_yaml_special_characters() {
        let temp_dir = tempdir().unwrap();
        let config_path = temp_dir.path().join("special_chars.yaml");

        // Config with paths containing special characters
        let config = CliConfig {
            fcx_mode: true,
            show_formid_values: false,
            stat_logging: true,
            move_unsolved_logs: false,
            simplify_logs: false,
            update_check: true,
            paths: classic_cli::PathConfig {
                ini_folder: Some(PathBuf::from("C:\\Users\\Test & User\\Documents")),
                scan_custom: Some(PathBuf::from("D:\\Logs (2024)")),
                mods_folder: Some(PathBuf::from("C:\\Mods - Collection #1")),
                game_root: PathBuf::from("C:\\Game"),
            },
        };

        // Save and load
        config.save_to_yaml(&config_path).await.unwrap();
        let loaded = CliConfig::load_from_yaml(&config_path).await.unwrap();

        // Verify all paths preserved correctly
        assert_eq!(loaded.paths.ini_folder, config.paths.ini_folder);
        assert_eq!(loaded.paths.scan_custom, config.paths.scan_custom);
        assert_eq!(loaded.paths.mods_folder, config.paths.mods_folder);
    }

    #[tokio::test]
    async fn test_config_yaml_boolean_values() {
        let temp_dir = tempdir().unwrap();
        let config_path = temp_dir.path().join("booleans.yaml");

        // Test all boolean combinations
        let configs_to_test = vec![
            (true, true, true, true, true, true),
            (false, false, false, false, false, false),
            (true, false, true, false, true, false),
            (false, true, false, true, false, true),
        ];

        for (fcx, show_fid, stat, move_unsolved, simplify, update) in configs_to_test {
            let config = CliConfig {
                fcx_mode: fcx,
                show_formid_values: show_fid,
                stat_logging: stat,
                move_unsolved_logs: move_unsolved,
                simplify_logs: simplify,
                update_check: update,
                paths: PathConfig::default(),
            };

            config.save_to_yaml(&config_path).await.unwrap();
            let loaded = CliConfig::load_from_yaml(&config_path)
                .await
                .unwrap();

            assert_eq!(loaded.fcx_mode, fcx);
            assert_eq!(loaded.show_formid_values, show_fid);
            assert_eq!(loaded.stat_logging, stat);
            assert_eq!(loaded.move_unsolved_logs, move_unsolved);
            assert_eq!(loaded.simplify_logs, simplify);
            assert_eq!(loaded.update_check, update);
        }
    }

    #[tokio::test]
    async fn test_config_yaml_none_paths() {
        let temp_dir = tempdir().unwrap();
        let config_path = temp_dir.path().join("none_paths.yaml");

        // Config with all optional paths as None
        let config = CliConfig {
            fcx_mode: true,
            show_formid_values: true,
            stat_logging: false,
            move_unsolved_logs: false,
            simplify_logs: false,
            update_check: true,
            paths: PathConfig {
                ini_folder: None,
                scan_custom: None,
                mods_folder: None,
                game_root: PathBuf::from("C:\\Game"),
            },
        };

        config.save_to_yaml(&config_path).await.unwrap();
        let loaded = CliConfig::load_from_yaml(&config_path)
            .await
            .unwrap();

        assert!(loaded.paths.ini_folder.is_none());
        assert!(loaded.paths.scan_custom.is_none());
        assert!(loaded.paths.mods_folder.is_none());
        assert_eq!(loaded.paths.game_root, PathBuf::from("C:\\Game"));
    }
}

// Executor tests would require mock crash logs
// These are commented out but show the structure:
/*
mod executor_integration {
    use super::*;

    #[tokio::test]
    async fn test_executor_find_crash_logs() {
        let temp_dir = tempdir().unwrap();
        let logs_dir = temp_dir.path().join("Crash Logs");
        fs::create_dir_all(&logs_dir).await.unwrap();

        // Create mock crash log files
        fs::write(logs_dir.join("crash-2024-01-01-12-00-00.log"), "test log content")
            .await
            .unwrap();
        fs::write(logs_dir.join("crash-2024-01-02-13-00-00.log"), "test log content")
            .await
            .unwrap();
        fs::write(logs_dir.join("other-file.txt"), "not a crash log")
            .await
            .unwrap();

        // Test executor can find crash logs
        // Would need to mock FileIOCore or use actual implementation
    }
}
*/

// Output formatter tests
mod output_integration {
    use super::*;

    #[test]
    fn test_output_formatter_creation() {
        let formatter = OutputFormatter::new();
        // Just verify it can be created without panicking
        assert!(true);
    }

    #[test]
    fn test_scan_stats_default() {
        let stats = ScanStats::default();
        assert_eq!(stats.scanned_logs, 0);
        assert_eq!(stats.patterns_matched, 0);
        assert_eq!(stats.formids_resolved, 0);
        assert_eq!(stats.suspects_identified, 0);
    }

    #[test]
    fn test_scan_stats_with_values() {
        let stats = ScanStats {
            scanned_logs: 47,
            patterns_matched: 234,
            formids_resolved: 1842,
            suspects_identified: 12,
        };

        assert_eq!(stats.scanned_logs, 47);
        assert_eq!(stats.patterns_matched, 234);
        assert_eq!(stats.formids_resolved, 1842);
        assert_eq!(stats.suspects_identified, 12);
    }
}

// Integration tests use the classic_cli library crate
// All modules are available via use classic_cli::*;
