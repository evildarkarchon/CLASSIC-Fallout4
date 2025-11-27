use clap::Parser;
use std::path::PathBuf;

/// CLASSIC - Crash Log Auto Scanner & Setup Integrity Checker
/// Command-Line Interface
#[derive(Parser, Debug)]
#[command(name = "classic")]
#[command(author = "CLASSIC Team")]
#[command(version = env!("CARGO_PKG_VERSION"))]
#[command(about = "Crash Log Auto Scanner & Setup Integrity Checker", long_about = None)]
pub struct CliArgs {
    /// Enable FCX mode for enhanced FormID analysis
    #[arg(long, action = clap::ArgAction::SetTrue)]
    pub fcx_mode: bool,

    /// Show FormID values in output
    #[arg(long, action = clap::ArgAction::SetTrue)]
    pub show_fid_values: bool,

    /// Enable statistical logging
    #[arg(long, action = clap::ArgAction::SetTrue)]
    pub stat_logging: bool,

    /// Move unsolved logs to subfolder
    #[arg(long, action = clap::ArgAction::SetTrue)]
    pub move_unsolved: bool,

    /// Path to INI folder
    #[arg(long, value_name = "PATH")]
    pub ini_path: Option<PathBuf>,

    /// Path to custom scan folder
    #[arg(long, value_name = "PATH")]
    pub scan_path: Option<PathBuf>,

    /// Path to mods folder
    #[arg(long, value_name = "PATH")]
    pub mods_folder_path: Option<PathBuf>,

    /// Simplify logs (may remove important info)
    #[arg(long, action = clap::ArgAction::SetTrue)]
    pub simplify_logs: bool,
}

impl CliArgs {
    /// Parse command-line arguments
    pub fn parse_args() -> Self {
        Self::parse()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cli_args_parsing() {
        let args = CliArgs::parse_from([
            "classic-cli",
            "--fcx-mode",
            "--show-fid-values",
            "--scan-path",
            "C:\\Test",
        ]);

        assert!(args.fcx_mode);
        assert!(args.show_fid_values);
        assert_eq!(args.scan_path.unwrap(), PathBuf::from("C:\\Test"));
    }

    #[test]
    fn test_cli_args_all_options() {
        let args = CliArgs::parse_from([
            "classic-cli",
            "--fcx-mode",
            "--show-fid-values",
            "--stat-logging",
            "--move-unsolved",
            "--ini-path",
            "C:\\Ini",
            "--scan-path",
            "D:\\Logs",
            "--mods-folder-path",
            "C:\\MO2\\mods",
            "--simplify-logs",
        ]);

        assert!(args.fcx_mode);
        assert!(args.show_fid_values);
        assert!(args.stat_logging);
        assert!(args.move_unsolved);
        assert_eq!(args.ini_path.unwrap(), PathBuf::from("C:\\Ini"));
        assert_eq!(args.scan_path.unwrap(), PathBuf::from("D:\\Logs"));
        assert_eq!(
            args.mods_folder_path.unwrap(),
            PathBuf::from("C:\\MO2\\mods")
        );
        assert!(args.simplify_logs);
    }

    #[test]
    fn test_cli_args_no_options() {
        let args = CliArgs::parse_from(["classic-cli"]);

        assert!(!args.fcx_mode);
        assert!(!args.show_fid_values);
        assert!(!args.stat_logging);
        assert!(!args.move_unsolved);
        assert_eq!(args.ini_path, None);
        assert_eq!(args.scan_path, None);
        assert_eq!(args.mods_folder_path, None);
        assert!(!args.simplify_logs);
    }

    #[test]
    fn test_cli_args_boolean_flags() {
        let args = CliArgs::parse_from([
            "classic-cli",
            "--fcx-mode",
            "--show-fid-values",
            "--stat-logging",
        ]);

        assert!(args.fcx_mode);
        assert!(args.show_fid_values);
        assert!(args.stat_logging);
        assert!(!args.move_unsolved);
        assert!(!args.simplify_logs);
    }

    #[test]
    fn test_cli_args_path_options() {
        let args = CliArgs::parse_from([
            "classic-cli",
            "--ini-path",
            "C:\\Test\\Ini",
            "--scan-path",
            "D:\\Logs",
            "--mods-folder-path",
            "C:\\Mods",
        ]);

        assert_eq!(args.ini_path, Some(PathBuf::from("C:\\Test\\Ini")));
        assert_eq!(args.scan_path, Some(PathBuf::from("D:\\Logs")));
        assert_eq!(args.mods_folder_path, Some(PathBuf::from("C:\\Mods")));
    }

    #[test]
    fn test_cli_args_windows_paths_with_spaces() {
        let args = CliArgs::parse_from([
            "classic-cli",
            "--ini-path",
            "C:\\Program Files\\Test Folder",
        ]);

        assert_eq!(
            args.ini_path,
            Some(PathBuf::from("C:\\Program Files\\Test Folder"))
        );
    }

    #[test]
    fn test_cli_args_mixed_options() {
        let args = CliArgs::parse_from([
            "classic-cli",
            "--fcx-mode",
            "--scan-path",
            "D:\\Logs",
            "--simplify-logs",
        ]);

        assert!(args.fcx_mode);
        assert_eq!(args.scan_path, Some(PathBuf::from("D:\\Logs")));
        assert!(args.simplify_logs);
        assert!(!args.show_fid_values);
    }
}
