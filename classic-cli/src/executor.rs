use anyhow::{Context, Result};
use classic_config_core::YamlDataCore;
use classic_file_io_core::FileIOCore;
use classic_scanlog_core::{OrchestratorCore, AnalysisConfig, AnalysisResult};
use std::path::{Path, PathBuf};

use crate::config::CliConfig;
use crate::output::{OutputFormatter, ScanStats};

/// Scan executor for CLI
///
/// Thin wrapper that handles CLI-specific concerns:
/// - Finding crash log directories
/// - Building configuration from YAML data
/// - Calling the orchestrator
pub struct ScanExecutor {
    config: CliConfig,
    yaml_data: YamlDataCore,
    file_io: FileIOCore,
}

impl ScanExecutor {
    /// Create a new scan executor
    pub fn new(config: CliConfig, yaml_data: YamlDataCore) -> Self {
        Self {
            config,
            yaml_data,
            file_io: FileIOCore::new("utf-8", "ignore", 100, 50),
        }
    }

    /// Execute the crash log scan
    pub async fn execute_scan(&self, output: &OutputFormatter) -> Result<(ScanStats, PathBuf)> {
        output.print_info("Initializing scan...");

        // Find crash log directory
        let crash_log_dir = self.find_crash_log_directory()?;
        output.print_success(&format!("Found crash log directory: {}", crash_log_dir.display()));

        // Find all crash log files using FileIOCore
        let log_files = self.file_io.walk_directory(
            &crash_log_dir,
            Some(r"^crash-.*\.(log|txt)$"),
            Some(1) // Only search in current directory, not subdirectories
        ).context("Failed to search for crash logs")?;

        output.print_success(&format!("Found {} crash logs in scan directory", log_files.len()));

        if log_files.is_empty() {
            output.print_warning("No crash logs found to analyze");
            return Ok((ScanStats::default(), crash_log_dir));
        }

        // Build analysis configuration from YAML data
        let analysis_config = self.build_analysis_config();

        // Create orchestrator - uses core business logic directly
        let orchestrator = OrchestratorCore::new(analysis_config)
            .context("Failed to create orchestrator")?;

        // Create progress bar
        let progress = output.create_progress_bar(log_files.len() as u64, "Scanning crash logs...");

        // Process all log files using orchestrator
        let log_paths: Vec<String> = log_files
            .iter()
            .map(|p| p.to_string_lossy().to_string())
            .collect();

        // Process logs individually to provide progress updates
        let mut results = Vec::new();
        for (idx, log_path) in log_paths.iter().enumerate() {
            let log_name = Path::new(log_path)
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("unknown");

            output.update_progress(&progress, idx as u64, &format!("Processing {}...", log_name));

            match orchestrator.process_log(log_path.clone()).await {
                Ok(result) => results.push(result),
                Err(e) => {
                    output.print_warning(&format!("Failed to process {}: {}", log_name, e));
                }
            }
        }

        progress.finish_with_message("Scan complete!");

        // Collect statistics from results
        let stats = self.collect_statistics(&results);

        // Generate reports if needed (orchestrator handles this in full implementation)
        if !self.config.simplify_logs {
            self.write_reports(&results, &crash_log_dir).await?;
        }

        Ok((stats, crash_log_dir))
    }

    /// Find the crash log directory based on configuration
    fn find_crash_log_directory(&self) -> Result<PathBuf> {
        // Check for custom scan path first
        if let Some(ref custom_path) = self.config.paths.scan_custom {
            if custom_path.exists() {
                return Ok(custom_path.clone());
            }
        }

        // Try to find default crash log directory in game documents
        if let Some(ref ini_folder) = self.config.paths.ini_folder {
            let crash_logs = ini_folder.parent()
                .and_then(|p| Some(p.join("Fallout 4").join("Crash Logs")))
                .filter(|p| p.exists());

            if let Some(logs_dir) = crash_logs {
                return Ok(logs_dir);
            }
        }

        // Fallback to common location
        let default_path = dirs::document_dir()
            .map(|d| d.join("My Games").join("Fallout4").join("Crash Logs"))
            .filter(|p| p.exists());

        default_path.ok_or_else(|| anyhow::anyhow!("Could not find crash log directory"))
    }

    /// Build AnalysisConfig from YamlDataCore
    fn build_analysis_config(&self) -> AnalysisConfig {
        AnalysisConfig {
            game: "Fallout4".to_string(),
            vr_mode: false, // TODO: Detect VR mode from config
            crashgen_name: self.yaml_data.crashgen_name.clone(),
            crashgen_latest: self.yaml_data.crashgen_latest_og.clone(),
            game_version: self.yaml_data.game_version.clone(),
            xse_acronym: self.yaml_data.xse_acronym.clone(),
            ignore_plugins: self.yaml_data.game_ignore_plugins.clone(),
            ignore_records: self.yaml_data.game_ignore_records.clone(),
            ignore_list: self.yaml_data.ignore_list.clone(),
            suspects_error: self.yaml_data.suspects_error_list.clone(),
            suspects_stack: self.yaml_data.suspects_stack_list.clone(),
            mods_core: self.yaml_data.game_mods_core.clone(),
            mods_freq: self.yaml_data.game_mods_freq.clone(),
            mods_conf: self.yaml_data.game_mods_conf.clone(),
            mods_solu: self.yaml_data.game_mods_solu.clone(),
        }
    }

    /// Collect statistics from analysis results
    fn collect_statistics(&self, results: &[AnalysisResult]) -> ScanStats {
        let scanned_logs = results.len();
        let patterns_matched = 0; // TODO: Track patterns in AnalysisResult
        let mut formids_resolved = 0;
        let mut suspects_identified = 0;

        for result in results {
            if !result.success {
                continue;
            }

            formids_resolved += result.formid_count;
            suspects_identified += result.suspect_count;
        }

        ScanStats {
            scanned_logs,
            patterns_matched,
            formids_resolved,
            suspects_identified,
        }
    }

    /// Write report files using FileIOCore
    async fn write_reports(&self, results: &[AnalysisResult], crash_log_dir: &Path) -> Result<()> {
        let reports_dir = crash_log_dir.join("Reports");
        tokio::fs::create_dir_all(&reports_dir)
            .await
            .context("Failed to create Reports directory")?;

        // Prepare all reports to write in parallel
        let reports_to_write: Vec<(PathBuf, String)> = results
            .iter()
            .filter(|r| r.success && !r.report_lines.is_empty())
            .map(|result| {
                let log_name = Path::new(&result.log_path)
                    .file_stem()
                    .and_then(|n| n.to_str())
                    .unwrap_or("unknown");

                let report_path = reports_dir.join(format!("{}_REPORT.txt", log_name));
                let report_content = result.report_lines.join("\n");

                (report_path, report_content)
            })
            .collect();

        // Write all reports in parallel using FileIOCore
        let write_results = self.file_io.write_multiple_files(reports_to_write).await;

        // Check for errors
        let errors: Vec<_> = write_results
            .into_iter()
            .filter_map(|(path, result)| result.err().map(|e| (path, e)))
            .collect();

        if !errors.is_empty() {
            // Note: We can't access OutputFormatter here since it's not passed to this method
            // For now, keep eprintln! for report write errors (non-critical warnings)
            eprintln!("Warning: Failed to write {} reports:", errors.len());
            for (path, err) in errors {
                eprintln!("  {}: {}", path.display(), err);
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    fn create_test_yaml_data() -> YamlDataCore {
        YamlDataCore {
            classic_game_hints: vec!["Hint1".to_string()],
            classic_records_list: vec!["Record1".to_string()],
            classic_version: "8.0.0".to_string(),
            classic_version_date: "2025-10-09".to_string(),
            crashgen_name: "Buffout 4".to_string(),
            crashgen_latest_og: "1.40.0".to_string(),
            crashgen_latest_vr: "1.0.0".to_string(),
            crashgen_ignore: vec![],
            warn_noplugins: "No plugins found".to_string(),
            warn_outdated: "Outdated version".to_string(),
            xse_acronym: "F4SE".to_string(),
            game_ignore_plugins: vec![],
            game_ignore_records: vec![],
            ignore_list: vec![],
            suspects_error_list: HashMap::new(),
            suspects_stack_list: HashMap::new(),
            game_mods_conf: HashMap::new(),
            game_mods_core: HashMap::new(),
            game_mods_core_folon: HashMap::new(),
            game_mods_freq: HashMap::new(),
            game_mods_opc2: HashMap::new(),
            game_mods_solu: HashMap::new(),
            autoscan_text: "Autoscan".to_string(),
            game_version: "1.10.163".to_string(),
            game_version_new: "1.10.163".to_string(),
            game_version_vr: "1.2.72".to_string(),
        }
    }

    #[test]
    fn test_executor_creation() {
        let config = CliConfig::default();
        let yaml_data = create_test_yaml_data();
        let executor = ScanExecutor::new(config, yaml_data);
        assert!(true); // Just verify creation works
    }

    #[test]
    fn test_build_analysis_config() {
        let config = CliConfig::default();
        let yaml_data = create_test_yaml_data();
        let executor = ScanExecutor::new(config, yaml_data);

        let analysis_config = executor.build_analysis_config();
        assert_eq!(analysis_config.game, "Fallout4");
        assert_eq!(analysis_config.crashgen_name, "Buffout 4");
        assert_eq!(analysis_config.xse_acronym, "F4SE");
    }

    #[test]
    fn test_collect_statistics_empty() {
        let config = CliConfig::default();
        let yaml_data = create_test_yaml_data();
        let executor = ScanExecutor::new(config, yaml_data);

        let results = vec![];
        let stats = executor.collect_statistics(&results);
        assert_eq!(stats.scanned_logs, 0);
        assert_eq!(stats.formids_resolved, 0);
    }

    #[test]
    fn test_collect_statistics_with_results() {
        let config = CliConfig::default();
        let yaml_data = create_test_yaml_data();
        let executor = ScanExecutor::new(config, yaml_data);

        let mut result1 = AnalysisResult::success(
            "test1.log".to_string(),
            vec!["Line 1".to_string()],
            100,
        );
        result1.formid_count = 10;
        result1.suspect_count = 2;

        let mut result2 = AnalysisResult::success(
            "test2.log".to_string(),
            vec!["Line 2".to_string()],
            150,
        );
        result2.formid_count = 20;
        result2.suspect_count = 3;

        let results = vec![result1, result2];
        let stats = executor.collect_statistics(&results);

        assert_eq!(stats.scanned_logs, 2);
        assert_eq!(stats.formids_resolved, 30);
        assert_eq!(stats.suspects_identified, 5);
    }
}
