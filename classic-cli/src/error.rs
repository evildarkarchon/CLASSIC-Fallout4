use std::fmt;

/// CLI-specific error types with user-friendly messages
#[derive(Debug)]
#[allow(dead_code)]
pub enum CliError {
    /// Configuration file error
    ConfigError(String),

    /// YAML data loading error
    YamlError(String),

    /// Crash log directory not found
    DirectoryNotFound(String),

    /// No crash logs found
    NoCrashLogs,

    /// Scan execution error
    ScanError(String),

    /// I/O error
    IoError(String),
}

impl fmt::Display for CliError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CliError::ConfigError(msg) => {
                write!(f, "Configuration Error: {}\n\nTip: Check that CLASSIC Settings.yaml exists and is properly formatted.", msg)
            }
            CliError::YamlError(msg) => {
                write!(f, "YAML Data Error: {}\n\nTip: Ensure YAML/ directory exists with Main, Games, and Ignore subdirectories.", msg)
            }
            CliError::DirectoryNotFound(path) => {
                write!(f, "Directory Not Found: {}\n\nTip: Specify a custom scan path with --scan-path or ensure crash logs are in the default location.", path)
            }
            CliError::NoCrashLogs => {
                write!(f, "No Crash Logs Found\n\nTip: Crash log files must start with 'crash-' prefix and have .log or .txt extension.")
            }
            CliError::ScanError(msg) => {
                write!(f, "Scan Error: {}\n\nTip: Check that crash logs are accessible and not corrupted.", msg)
            }
            CliError::IoError(msg) => {
                write!(
                    f,
                    "I/O Error: {}\n\nTip: Check file permissions and disk space.",
                    msg
                )
            }
        }
    }
}

impl std::error::Error for CliError {}

impl From<std::io::Error> for CliError {
    fn from(err: std::io::Error) -> Self {
        CliError::IoError(err.to_string())
    }
}

impl From<anyhow::Error> for CliError {
    fn from(err: anyhow::Error) -> Self {
        // Try to extract context for better error messages
        let error_str = err.to_string();

        if error_str.contains("YAML") || error_str.contains("yaml") {
            CliError::YamlError(error_str)
        } else if error_str.contains("config") || error_str.contains("Config") {
            CliError::ConfigError(error_str)
        } else if error_str.contains("directory") || error_str.contains("Directory") {
            CliError::DirectoryNotFound(error_str)
        } else if error_str.contains("scan") || error_str.contains("Scan") {
            CliError::ScanError(error_str)
        } else {
            CliError::IoError(error_str)
        }
    }
}

/// Helper function to print detailed error with context
#[allow(dead_code)]
pub fn print_error_detail(error: &CliError) {
    use console::Style;

    let error_style = Style::new().red().bold();
    let tip_style = Style::new().yellow();

    eprintln!("\n{}", error_style.apply_to("ERROR:"));
    eprintln!("{}", error);

    // Additional troubleshooting suggestions
    match error {
        CliError::ConfigError(_) => {
            eprintln!("\n{}", tip_style.apply_to("Troubleshooting:"));
            eprintln!("  1. Verify CLASSIC Settings.yaml syntax");
            eprintln!("  2. Check file encoding (should be UTF-8)");
            eprintln!("  3. Run with default settings (delete config file to regenerate)");
        }
        CliError::YamlError(_) => {
            eprintln!("\n{}", tip_style.apply_to("Troubleshooting:"));
            eprintln!("  1. Ensure YAML directory structure:");
            eprintln!("     - YAML/Main/CLASSIC Main.yaml");
            eprintln!("     - YAML/Games/CLASSIC Fallout4.yaml");
            eprintln!("     - YAML/Ignore/CLASSIC Ignore.yaml");
            eprintln!("  2. Verify all YAML files are present");
            eprintln!("  3. Check YAML file syntax");
        }
        CliError::DirectoryNotFound(_) => {
            eprintln!("\n{}", tip_style.apply_to("Troubleshooting:"));
            eprintln!("  1. Use --scan-path to specify custom crash log directory");
            eprintln!("  2. Check Documents/My Games/Fallout4/Crash Logs exists");
            eprintln!("  3. Ensure you have run the game at least once");
        }
        CliError::NoCrashLogs => {
            eprintln!("\n{}", tip_style.apply_to("Troubleshooting:"));
            eprintln!("  1. Verify crash logs exist in the scan directory");
            eprintln!("  2. Check that files start with 'crash-' prefix");
            eprintln!("  3. Ensure files have .log or .txt extension");
        }
        _ => {}
    }
    eprintln!();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_display() {
        let err = CliError::ConfigError("Invalid syntax".to_string());
        let msg = format!("{}", err);
        assert!(msg.contains("Configuration Error"));
        assert!(msg.contains("Tip:"));
    }

    #[test]
    fn test_io_error_conversion() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file not found");
        let cli_err: CliError = io_err.into();
        assert!(matches!(cli_err, CliError::IoError(_)));
    }

    #[test]
    fn test_no_crash_logs_error() {
        let err = CliError::NoCrashLogs;
        let msg = format!("{}", err);
        assert!(msg.contains("No Crash Logs Found"));
        assert!(msg.contains("crash-"));
    }
}
