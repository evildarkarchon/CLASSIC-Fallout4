use anyhow::Result;
use classic_config_core::ClassicConfig;
use std::path::Path;

use crate::args::CliArgs;

// Re-export types from classic-config-core for convenience
pub type CliConfig = ClassicConfig;
pub use classic_config_core::PathConfig;

/// Create configuration from CLI arguments (no saved config)
///
/// # Arguments
/// * `args` - Parsed CLI arguments
///
/// # Returns
/// New CliConfig with values from CLI arguments, falling back to defaults
pub fn config_from_cli_args(args: &CliArgs) -> CliConfig {
    let mut config = CliConfig::default();
    merge_cli_args(&mut config, args);
    config
}

/// Load configuration from file or create from CLI args
///
/// # Arguments
/// * `path` - Path to the YAML configuration file
/// * `args` - Parsed CLI arguments
///
/// # Returns
/// * Configuration loaded from file (if exists) merged with CLI args
/// * Configuration from CLI args only (if file doesn't exist)
pub async fn load_or_create_config(path: &Path, args: &CliArgs) -> Result<CliConfig> {
    if path.exists() {
        let mut config = CliConfig::load_from_yaml(path).await?;
        merge_cli_args(&mut config, args);
        Ok(config)
    } else {
        Ok(config_from_cli_args(args))
    }
}

/// Merge CLI arguments into configuration
///
/// CLI arguments take precedence over saved configuration.
/// Only arguments that are Some(...) will override the config.
///
/// # Arguments
/// * `config` - Configuration to update
/// * `args` - Parsed CLI arguments
pub fn merge_cli_args(config: &mut CliConfig, args: &CliArgs) {
    // Boolean flags from CLI always take precedence when set to true
    // (false is the default, so we only override when explicitly enabled)
    if args.fcx_mode {
        config.fcx_mode = true;
    }

    if args.show_fid_values {
        config.show_formid_values = true;
    }

    if args.stat_logging {
        config.stat_logging = true;
    }

    if args.move_unsolved {
        config.move_unsolved_logs = true;
    }

    if args.simplify_logs {
        config.simplify_logs = true;
    }

    // Path options override saved config when provided
    if let Some(ref ini_path) = args.ini_path {
        config.paths.ini_folder = Some(ini_path.clone());
    }

    if let Some(ref scan_path) = args.scan_path {
        config.paths.scan_custom = Some(scan_path.clone());
    }

    if let Some(ref mods_folder_path) = args.mods_folder_path {
        config.paths.mods_folder = Some(mods_folder_path.clone());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;
    use tempfile::tempdir;

    #[test]
    fn test_default_config() {
        let config = CliConfig::default();
        assert!(!config.fcx_mode);
        assert!(!config.show_formid_values);
        assert!(!config.stat_logging);
        assert!(!config.move_unsolved_logs);
        assert!(!config.simplify_logs);
        assert!(config.update_check);
    }

    #[test]
    fn test_merge_cli_args() {
        let mut config = CliConfig::default();
        let args = CliArgs {
            fcx_mode: true,
            show_fid_values: true,
            stat_logging: false,
            move_unsolved: false,
            ini_path: Some(PathBuf::from("C:\\Test\\Ini")),
            scan_path: None,
            mods_folder_path: None,
            simplify_logs: false,
        };

        merge_cli_args(&mut config, &args);

        assert!(config.fcx_mode);
        assert!(config.show_formid_values);
        assert!(!config.stat_logging); // Not changed (false flag)
        assert_eq!(
            config.paths.ini_folder,
            Some(PathBuf::from("C:\\Test\\Ini"))
        );
    }

    #[tokio::test]
    async fn test_save_and_load_yaml() {
        let temp_dir = tempdir().unwrap();
        let config_path = temp_dir.path().join("test_config.yaml");

        let mut config = CliConfig::default();
        config.fcx_mode = true;
        config.show_formid_values = true;
        config.paths.ini_folder = Some(PathBuf::from("C:\\Test"));

        // Save config
        config.save_to_yaml(&config_path).await.unwrap();
        assert!(config_path.exists());

        // Load config
        let loaded = CliConfig::load_from_yaml(&config_path).await.unwrap();
        assert_eq!(loaded.fcx_mode, config.fcx_mode);
        assert_eq!(loaded.show_formid_values, config.show_formid_values);
        assert_eq!(loaded.paths.ini_folder, config.paths.ini_folder);
    }

    #[tokio::test]
    async fn test_load_or_create_no_file() {
        let temp_dir = tempdir().unwrap();
        let config_path = temp_dir.path().join("nonexistent.yaml");

        let args = CliArgs {
            fcx_mode: true,
            show_fid_values: false,
            stat_logging: false,
            move_unsolved: false,
            ini_path: None,
            scan_path: None,
            mods_folder_path: None,
            simplify_logs: false,
        };

        let config = load_or_create_config(&config_path, &args).await.unwrap();
        assert!(config.fcx_mode); // From args
        assert!(!config.show_formid_values); // Default (false flag)
    }

    #[tokio::test]
    async fn test_load_or_create_with_existing_file() {
        let temp_dir = tempdir().unwrap();
        let config_path = temp_dir.path().join("existing_config.yaml");

        // Create a config and save it
        let mut saved_config = CliConfig::default();
        saved_config.fcx_mode = true;
        saved_config.stat_logging = true;
        saved_config.save_to_yaml(&config_path).await.unwrap();

        // Load with different CLI args
        let args = CliArgs {
            fcx_mode: false,       // Don't override (false is default)
            show_fid_values: true, // Enable via flag
            stat_logging: false,   // Don't override (false is default)
            move_unsolved: false,
            ini_path: None,
            scan_path: None,
            mods_folder_path: None,
            simplify_logs: false,
        };

        let loaded = load_or_create_config(&config_path, &args).await.unwrap();

        assert!(loaded.fcx_mode); // From saved config (not overridden by false flag)
        assert!(loaded.show_formid_values); // From args (enabled by flag)
        assert!(loaded.stat_logging); // From saved config (not overridden by false flag)
    }

    #[test]
    fn test_merge_cli_args_only_some_values() {
        let mut config = CliConfig {
            fcx_mode: true,
            show_formid_values: true,
            stat_logging: false,
            move_unsolved_logs: false,
            simplify_logs: false,
            update_check: true,
            paths: PathConfig::default(),
        };

        let args = CliArgs {
            fcx_mode: false,        // Don't override (false is default)
            show_fid_values: false, // Don't override (false is default)
            stat_logging: true,     // Enable via flag
            move_unsolved: false,
            ini_path: None,
            scan_path: None,
            mods_folder_path: None,
            simplify_logs: false,
        };

        merge_cli_args(&mut config, &args);

        assert!(config.fcx_mode); // Unchanged (false flag doesn't override)
        assert!(config.show_formid_values); // Unchanged (false flag doesn't override)
        assert!(config.stat_logging); // Changed to true (enabled by flag)
    }
}
