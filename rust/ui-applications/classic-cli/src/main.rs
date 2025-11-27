//! CLASSIC CLI - Command Line Interface for crash log analysis
//!
//! High-performance CLI tool for batch processing Fallout 4 and Skyrim crash logs
//! with Rust-accelerated analysis.

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

/// ```rust
/// Asynchronous entry point for the application that manages configuration,
/// loads game data, executes a crash log scan, and displays results.
///```
/// This function performs several key tasks:
/// 1. Parses command-line arguments using `CliArgs`.
/// 2. Loads or creates a configuration from a file, validates it, and saves updates.
/// 3. Finds and loads game data from YAML files for processing.
/// 4. Executes a crash log scan using the loaded configuration and game data.
/// 5. Displays a summary of scan results and output details.
///
/// # Workflow:
/// - Loads application configuration from the system or creates a new configuration if one does not exist.
/// - Validates configuration paths and handles warnings for missing or invalid paths.
/// - Identifies directories containing YAML game data and loads them for use in the scan.
/// - Executes a crash log scan using the processed configuration and game data.
/// - Outputs scan statistics, report locations, and provides interactive feedback to the user.
///
/// # Returns:
/// - `Ok(())`: If the application runs successfully to completion.
/// - `Err`: If any error occurs during the process, such as loading configuration, parsing YAML data,
///   or executing the scan.
///
/// # Errors:
/// This function may return errors in the following scenarios:
/// - Configuration file load or validation failures.
/// - Issues with saving the updated configuration to a file.
/// - Errors while finding or parsing YAML game data directories.
/// - Failures during the crash log scan process.
///
/// # Dependencies:
/// - This function leverages `classic-config-core` for YAML file management.
/// - Crash log scanning is handled via `ScanExecutor`.
///
/// # Examples:
/// ```
/// // Run the application:
/// if let Err(error) = run().await {
///     eprintln!("Application error: {}", error);
/// }
/// ```
///
/// # Notes:
/// - The function outputs information to the console using `OutputFormatter` for structured
///   and readable messages.
/// - YAML data loading currently assumes a non-VR mode with a possibility for future configuration options.
/// - At the end of the process, the user is prompted to press any key to exit.
///
/// # Panics:
/// This function does not explicitly panic but relies on helper functions that may contain
/// `expect` or `unwrap` in case of irrecoverable errors.
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
    let mut config = config::load_or_create_config(&config_path, &args)
        .await
        .context("Failed to load configuration")?;

    // Load paths from Local.yaml
    output.print_info("Loading local configuration paths...");
    config
        .load_local_yaml_paths("Fallout4")
        .await
        .context("Failed to load Local.yaml paths")?;

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

/// ```
/// Retrieves the configuration file path for the application.
///
/// The function determines the configuration file path by attempting to locate the directory
/// where the application is executed. It performs the following steps:
/// 1. Tries to determine the application's directory using the path of the current executable.
///    - If successful, it takes the parent directory of the executable.
///    - If this fails, it falls back to using the current working directory.
/// 2. Constructs the path to the configuration file by appending `"CLASSIC Settings.yaml"`
///    to the determined directory path (or defaults to the file name alone if no directory is found).
///```
/// # Returns
///
/// - `Ok(PathBuf)`: The path to the configuration file as a `PathBuf`.
/// - The return value ensures that there will always be some path, either relative or absolute.
///
/// # Errors
///
/// This function does not generate errors. However, the result is wrapped in `Result` to follow
/// common practices for potential extension.
///
/// # Example
///
/// ```
/// let config_path = get_config_path().unwrap();
/// println!("Configuration file path: {:?}", config_path);
/// ```
///
/// The output will resemble:
/// ```text
/// Configuration file path: "/path/to/CLASSIC Settings.yaml"
/// ```
///
/// Note that the actual path depends on the runtime environment.
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

/// ```rust
/// Finds directories containing YAML data based on the application's execution path
/// or the current working directory.
///```
/// ## Description
/// This function is designed to locate YAML data directories following a known structure
/// under `CLASSIC Data/databases` in the executable's directory or the current working
/// directory. If the proper folder structure is found, it returns three paths:
/// 1. A `databases` directory intended for "Main".
/// 2. A `databases` directory intended for "Game".
/// 3. The parent directory (execution directory or current working directory).
///
/// If no valid directory is found, the function returns an error.
///
/// ## Return Value
/// - `Ok(Vec<PathBuf>)`: A vector containing the following paths (in order):
///   1. The first `databases` directory found.
///   2. A duplicate of the first `databases` directory (for additional usage scenarios).
///   3. The parent directory (execution directory or current working directory).
/// - `Err`: An error if the `CLASSIC Data/databases` folder cannot be located.
///
/// ## Parameters
/// - `config: &CliConfig`: A configuration object for CLI interaction (though it is
///   currently unused in the function).
///
/// ## Errors
/// - Returns an error using `anyhow::bail!` if neither the executable's directory
///   nor the current directory contains a valid `CLASSIC Data/databases` folder.
///
/// ## Examples
/// ```rust
/// let config = CliConfig::new();
/// match find_yaml_directories(&config) {
///     Ok(paths) => {
///         for path in paths {
///             println!("Found path: {:?}", path);
///         }
///     }
///     Err(e) => {
///         eprintln!("Error: {}", e);
///     }
/// }
/// ```
fn find_yaml_directories(_config: &CliConfig) -> Result<Vec<PathBuf>> {
    // Try executable directory first
    if let Ok(exe_path) = std::env::current_exe()
        && let Some(exe_dir) = exe_path.parent()
    {
        let databases_dir = exe_dir.join("CLASSIC Data/databases");
        if databases_dir.exists() {
            // Return: [databases (Main), databases (Game), exe_dir (Ignore)]
            return Ok(vec![
                databases_dir.clone(),
                databases_dir,
                exe_dir.to_path_buf(),
            ]);
        }
    }

    // Try current directory
    if let Ok(current_dir) = std::env::current_dir() {
        let databases_dir = current_dir.join("CLASSIC Data/databases");
        if databases_dir.exists() {
            // Return: [databases (Main), databases (Game), current_dir (Ignore)]
            return Ok(vec![databases_dir.clone(), databases_dir, current_dir]);
        }
    }

    anyhow::bail!(
        "Could not find YAML data directories. Please ensure 'CLASSIC Data/databases' folder exists."
    )
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
