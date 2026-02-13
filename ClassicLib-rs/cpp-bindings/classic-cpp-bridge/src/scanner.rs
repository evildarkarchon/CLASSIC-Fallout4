//! Crash log scanning bridge for CXX FFI.
//!
//! Bridges `classic_scanlog_core::OrchestratorCore` for crash log analysis.
//! This is the PRIMARY FEATURE of the CLASSIC application.
//! Placeholder — will be implemented by Wave 2 agent.

use classic_config_core::YamlDataCore;
use classic_scanlog_core::{
    AnalysisConfig, AnalysisResult, OrchestratorCore, build_analysis_config_from_yaml,
};
use classic_shared_core::get_runtime;
use std::path::PathBuf;

/// Opaque wrapper holding a fully-loaded AnalysisConfig (from YAML).
pub struct FullScanConfig {
    inner: AnalysisConfig,
}

/// Opaque wrapper around OrchestratorCore.
pub struct Orchestrator {
    inner: OrchestratorCore,
}

// ── Config construction ─────────────────────────────────────────────

fn build_full_scan_config(
    yaml_dir_root: &str,
    yaml_dir_data: &str,
    game: &str,
    vr_mode: bool,
    show_formid_values: bool,
    fcx_mode: bool,
    simplify_logs: bool,
) -> Result<Box<FullScanConfig>, String> {
    let dirs = vec![PathBuf::from(yaml_dir_root), PathBuf::from(yaml_dir_data)];
    let yaml = get_runtime()
        .block_on(YamlDataCore::load_from_yaml_files(
            dirs,
            game.to_string(),
            vr_mode,
        ))
        .map_err(|e| format!("{e}"))?;

    let config = build_analysis_config_from_yaml(
        &yaml,
        game,
        vr_mode,
        show_formid_values,
        fcx_mode,
        simplify_logs,
        Vec::new(),
    );
    Ok(Box::new(FullScanConfig { inner: config }))
}

// ── Orchestrator ────────────────────────────────────────────────────

fn orchestrator_new(config: &FullScanConfig) -> Result<Box<Orchestrator>, String> {
    let orch = OrchestratorCore::new(config.inner.clone()).map_err(|e| format!("{e}"))?;
    Ok(Box::new(Orchestrator { inner: orch }))
}

fn orchestrator_new_minimal(
    game: &str,
    vr_mode: bool,
    crashgen_name: &str,
    xse_acronym: &str,
) -> Result<Box<Orchestrator>, String> {
    let mut config = AnalysisConfig::new(game.to_string(), vr_mode);
    config.crashgen_name = crashgen_name.to_string();
    config.xse_acronym = xse_acronym.to_string();
    let orch = OrchestratorCore::new(config).map_err(|e| format!("{e}"))?;
    Ok(Box::new(Orchestrator { inner: orch }))
}

fn orchestrator_process_log(
    orch: &Orchestrator,
    log_path: &str,
) -> Result<ffi::ScanResult, String> {
    let result = get_runtime()
        .block_on(orch.inner.process_log(log_path.to_string()))
        .map_err(|e| format!("{e}"))?;
    Ok(analysis_result_to_dto(result))
}

fn orchestrator_process_logs_batch(
    orch: &Orchestrator,
    log_paths: &[String],
) -> Vec<ffi::ScanResult> {
    let paths: Vec<String> = log_paths.to_vec();
    let results = get_runtime().block_on(orch.inner.process_logs_batch(paths, None));
    results.into_iter().map(analysis_result_to_dto).collect()
}

fn analysis_result_to_dto(r: AnalysisResult) -> ffi::ScanResult {
    ffi::ScanResult {
        log_path: r.log_path,
        success: r.success,
        report_lines: r.report_lines,
        error_message: r.error.unwrap_or_default(),
        processing_time_ms: r.processing_time_ms,
        formid_count: r.formid_count as u32,
        plugin_count: r.plugin_count as u32,
        suspect_count: r.suspect_count as u32,
    }
}

// ── Utility functions ───────────────────────────────────────────────

fn detect_vr_log(content: &str) -> bool {
    // VR logs contain "Fallout4VR.esm" or "SkyrimVR.esm" in plugin list
    content.contains("Fallout4VR.esm") || content.contains("SkyrimVR.esm")
}

fn detect_crash_pattern(content: &str) -> String {
    // Parse the crash header to extract the main error/crash module
    let parser = classic_scanlog_core::LogParser::new(None).unwrap();
    let lines: Vec<String> = content.lines().map(|l| l.to_string()).collect();
    match parser.parse_crash_header(&lines) {
        Ok(header) => header.get("main_error").cloned().unwrap_or_default(),
        Err(_) => String::new(),
    }
}

#[cxx::bridge(namespace = "classic::scanner")]
mod ffi {
    /// Result of scanning a single crash log.
    struct ScanResult {
        log_path: String,
        success: bool,
        report_lines: Vec<String>,
        error_message: String,
        processing_time_ms: u64,
        formid_count: u32,
        plugin_count: u32,
        suspect_count: u32,
    }

    extern "Rust" {
        type FullScanConfig;
        type Orchestrator;

        // Config construction
        fn build_full_scan_config(
            yaml_dir_root: &str,
            yaml_dir_data: &str,
            game: &str,
            vr_mode: bool,
            show_formid_values: bool,
            fcx_mode: bool,
            simplify_logs: bool,
        ) -> Result<Box<FullScanConfig>>;

        // Orchestrator
        fn orchestrator_new(config: &FullScanConfig) -> Result<Box<Orchestrator>>;
        fn orchestrator_new_minimal(
            game: &str,
            vr_mode: bool,
            crashgen_name: &str,
            xse_acronym: &str,
        ) -> Result<Box<Orchestrator>>;
        fn orchestrator_process_log(orch: &Orchestrator, log_path: &str) -> Result<ScanResult>;
        fn orchestrator_process_logs_batch(
            orch: &Orchestrator,
            log_paths: &[String],
        ) -> Vec<ScanResult>;

        // Utilities
        fn detect_vr_log(content: &str) -> bool;
        fn detect_crash_pattern(content: &str) -> String;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_orchestrator_new_minimal() {
        let result = orchestrator_new_minimal("Fallout4", false, "Buffout 4", "F4SE");
        assert!(result.is_ok());
    }

    #[test]
    fn test_detect_vr_log_positive() {
        assert!(detect_vr_log("some content\nFallout4VR.esm\nmore content"));
        assert!(detect_vr_log("SkyrimVR.esm"));
    }

    #[test]
    fn test_detect_vr_log_negative() {
        assert!(!detect_vr_log("Fallout4.esm\nregular content"));
        assert!(!detect_vr_log(""));
    }

    #[test]
    fn test_detect_crash_pattern_empty() {
        let result = detect_crash_pattern("");
        // Empty content should not match any crash pattern
        assert!(result.is_empty());
    }

    #[test]
    fn test_build_full_scan_config_invalid_dirs() {
        let result = build_full_scan_config(
            "nonexistent_root",
            "nonexistent_data",
            "Fallout4",
            false,
            false,
            false,
            false,
        );
        assert!(result.is_err());
    }

    #[test]
    fn test_scan_result_dto() {
        let ar = AnalysisResult::success("test.log".to_string(), vec!["line1".to_string()], 1000);
        let dto = analysis_result_to_dto(ar);
        assert_eq!(dto.log_path, "test.log");
        assert!(dto.success);
        assert_eq!(dto.report_lines, vec!["line1"]);
        assert!(dto.error_message.is_empty());
    }
}
