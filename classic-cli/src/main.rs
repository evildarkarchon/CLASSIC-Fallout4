mod args;
mod config;
mod error;
mod executor;
mod output;

use anyhow::{Context, Result};
use classic_config_core::YamlDataCore;
use std::path::PathBuf;
use std::process;

use args::CliArgs;
use config::CliConfig;
use executor::ScanExecutor;
use output::OutputFormatter;

/// Main entry point for CLASSIC CLI
#[tokio::main]
async fn main() {
    // Run the application and exit with appropriate code
    if let Err(e) = run().await {
        let output = OutputFormatter::new();
        output.print_error(&format!("{:?}", e));
        process::exit(1);
    }
}

/// Main application logic
async fn run() -> Result<()> {
    // Parse command-line arguments
    let args = CliArgs::parse_args();

    // Create output formatter
    let output = OutputFormatter::new();

    // Print header
    output.print_header(env!("CARGO_PKG_VERSION"));

    // Determine config file location
    let config_path = get_config_path()?;

    // Load or create configuration
    output.print_info("Loading configuration...");
    let config = config::load_or_create_config(&config_path, &args)
        .await
        .context("Failed to load configuration")?;

    // Validate configuration paths
    if let Err(e) = config.validate_paths() {
        output.print_warning(&format!("Path validation warning: {}", e));
        output.print_info("Some paths may not exist - continuing with available paths...");
    }

    output.print_success("Configuration loaded successfully");

    // Save updated configuration
    config
        .save_to_yaml(&config_path)
        .await
        .context("Failed to save configuration")?;

    // Determine YAML data directories
    let yaml_dirs = find_yaml_directories(&config)?;
    output.print_info(&format!(
        "Loading game data from {} directories...",
        yaml_dirs.len()
    ));

    // Load YAML game data using classic-config-core
    let yaml_data = YamlDataCore::load_from_yaml_files(
        yaml_dirs,
        "Fallout4".to_string(),
        false, // VR mode - TODO: detect from config
    )
    .await
    .context("Failed to load YAML game data")?;

    output.print_success(&format!(
        "Game data loaded: CLASSIC v{} ({})",
        yaml_data.classic_version, yaml_data.classic_version_date
    ));

    // Create scan executor
    let executor = ScanExecutor::new(config.clone(), yaml_data);

    // Execute the scan
    output.print_info("Starting crash log scan...");
    println!();

    let (stats, crash_log_dir) = executor
        .execute_scan(&output)
        .await
        .context("Scan execution failed")?;

    // Display results summary
    output.print_scan_summary(&stats);

    // Print footer with report location
    let report_path = crash_log_dir.join("Reports").to_string_lossy().to_string();
    output.print_footer(&report_path);

    // Wait for user input (like Python's os.system("pause"))
    output.wait_for_input()?;

    Ok(())
}

/// Get the standardized configuration file path
///
/// Uses "CLASSIC Settings.yaml" for consistency with Python version
fn get_config_path() -> Result<PathBuf> {
    // Try to find the application directory
    let app_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.to_path_buf()))
        .or_else(|| std::env::current_dir().ok());

    let config_path = app_dir
        .map(|d| d.join("CLASSIC Settings.yaml"))
        .unwrap_or_else(|| PathBuf::from("CLASSIC Settings.yaml"));

    Ok(config_path)
}

/// Find YAML data directories
fn find_yaml_directories(config: &CliConfig) -> Result<Vec<PathBuf>> {
    // Try to find YAML directories relative to executable or current directory
    let mut yaml_dirs = Vec::new();

    // Try executable directory first
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            let yaml_dir = exe_dir.join("YAML");
            if yaml_dir.exists() {
                yaml_dirs.push(yaml_dir.join("Main"));
                yaml_dirs.push(yaml_dir.join("Games"));
                yaml_dirs.push(yaml_dir.join("Ignore"));
                return Ok(yaml_dirs);
            }
        }
    }

    // Try current directory
    if let Ok(current_dir) = std::env::current_dir() {
        let yaml_dir = current_dir.join("YAML");
        if yaml_dir.exists() {
            yaml_dirs.push(yaml_dir.join("Main"));
            yaml_dirs.push(yaml_dir.join("Games"));
            yaml_dirs.push(yaml_dir.join("Ignore"));
            return Ok(yaml_dirs);
        }
    }

    // Try game root directory
    let yaml_dir = config.paths.game_root.join("CLASSIC").join("YAML");
    if yaml_dir.exists() {
        yaml_dirs.push(yaml_dir.join("Main"));
        yaml_dirs.push(yaml_dir.join("Games"));
        yaml_dirs.push(yaml_dir.join("Ignore"));
        return Ok(yaml_dirs);
    }

    anyhow::bail!("Could not find YAML data directories. Please ensure YAML/ folder exists.")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_config_path() {
        let path = get_config_path().unwrap();
        assert!(path.to_string_lossy().contains("CLASSIC Settings.yaml"));
    }

    #[test]
    fn test_find_yaml_directories_nonexistent() {
        let config = CliConfig::default();
        // This should fail since test environment won't have YAML dirs
        assert!(find_yaml_directories(&config).is_err());
    }
}
