//! Crash log scanning bridge for CXX FFI.
//!
//! Bridges `classic_scanlog_core::OrchestratorCore` for crash log analysis.
//! This is the PRIMARY FEATURE of the CLASSIC application.
//! Placeholder — will be implemented by Wave 2 agent.

use classic_config_core::YamlDataCore;
use classic_database_core::DatabasePool;
use classic_scanlog_core::papyrus::{PapyrusAnalyzer, PapyrusStats};
use classic_scanlog_core::{
    build_analysis_config_from_yaml, AnalysisConfig, AnalysisResult, OrchestratorCore,
};
use classic_shared_core::get_runtime;
use classic_yaml_core::YamlOperations;
use std::collections::HashSet;
use std::path::Path;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;

/// Opaque wrapper holding a fully-loaded AnalysisConfig (from YAML).
pub struct FullScanConfig {
    inner: AnalysisConfig,
    db_paths: Vec<PathBuf>,
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
    let db_paths = resolve_formid_db_paths(yaml_dir_root, yaml_dir_data, game);
    Ok(Box::new(FullScanConfig {
        inner: config,
        db_paths,
    }))
}

// ── Orchestrator ────────────────────────────────────────────────────

fn orchestrator_new(config: &FullScanConfig) -> Result<Box<Orchestrator>, String> {
    let mut orch = OrchestratorCore::new(config.inner.clone()).map_err(|e| format!("{e}"))?;

    // Match Python behavior: when FormID values are enabled, initialize DB pool
    // with Main + hardcoded + user-configured database paths.
    if config.inner.show_formid_values {
        let pool = Arc::new(DatabasePool::new(
            None,
            Duration::from_secs(300),
            config.inner.game.clone(),
        ));

        get_runtime()
            .block_on(pool.initialize(config.db_paths.clone()))
            .map_err(|e| format!("{e}"))?;

        orch.attach_database_pool(pool);
    }

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

// ── FormID database path resolution ─────────────────────────────────

fn hardcoded_formid_db_relpaths(game: &str) -> &'static [&'static str] {
    match game {
        "Fallout4" | "Fallout4VR" => &["databases/FOLON FormIDs.db"],
        _ => &[],
    }
}

fn normalize_path(path: PathBuf) -> PathBuf {
    path.components().collect()
}

fn dedupe_paths(paths: Vec<PathBuf>) -> Vec<PathBuf> {
    let mut seen = HashSet::new();
    let mut deduped = Vec::with_capacity(paths.len());
    for path in paths {
        let normalized = normalize_path(path);
        if seen.insert(normalized.clone()) {
            deduped.push(normalized);
        }
    }
    deduped
}

fn load_user_formid_db_paths(yaml_dir_root: &str, yaml_dir_data: &str, game: &str) -> Vec<PathBuf> {
    let settings = PathBuf::from(yaml_dir_root).join("CLASSIC Settings.yaml");
    let legacy_settings = PathBuf::from(yaml_dir_root).join("CLASSIC_Settings.yaml");

    let settings_path = if settings.exists() {
        settings
    } else if legacy_settings.exists() {
        legacy_settings
    } else {
        return Vec::new();
    };

    let ops = YamlOperations::new();
    let doc = match ops.load_yaml_file(Path::new(&settings_path)) {
        Ok(doc) => doc,
        Err(_) => return Vec::new(),
    };

    let key_path = format!("CLASSIC_Settings.FormID Databases.{game}");
    let raw_paths = ops.get_vec_value(&doc, &key_path);
    raw_paths
        .into_iter()
        .map(PathBuf::from)
        .map(|p| {
            if p.is_absolute() {
                normalize_path(p)
            } else {
                normalize_path(PathBuf::from(yaml_dir_data).join(p))
            }
        })
        .collect()
}

fn resolve_formid_db_paths(yaml_dir_root: &str, yaml_dir_data: &str, game: &str) -> Vec<PathBuf> {
    let data_dir = PathBuf::from(yaml_dir_data);
    let main_db = data_dir
        .join("databases")
        .join(format!("{game} FormIDs Main.db"));

    let hardcoded = hardcoded_formid_db_relpaths(game)
        .iter()
        .map(|rel| data_dir.join(rel))
        .collect::<Vec<_>>();

    let user_paths = load_user_formid_db_paths(yaml_dir_root, yaml_dir_data, game);

    let mut all_paths = Vec::with_capacity(1 + hardcoded.len() + user_paths.len());
    all_paths.push(main_db);
    all_paths.extend(hardcoded);
    all_paths.extend(user_paths);
    dedupe_paths(all_paths)
}

// ── Papyrus monitoring ────────────────────────────────────────────

/// Opaque wrapper around `PapyrusAnalyzer` for CXX FFI.
pub struct CxxPapyrusAnalyzer {
    inner: PapyrusAnalyzer,
}

/// Convert `PapyrusStats` to the CXX-shared DTO.
fn papyrus_stats_to_dto(stats: &PapyrusStats) -> ffi::PapyrusStatsDto {
    ffi::PapyrusStatsDto {
        dumps: stats.dumps as u32,
        stacks: stats.stacks as u32,
        warnings: stats.warnings as u32,
        errors: stats.errors as u32,
        lines_processed: stats.lines_processed as u32,
        dumps_stacks_ratio: stats.dumps_to_stacks_ratio(),
    }
}

fn papyrus_analyzer_new(log_path: &str) -> Box<CxxPapyrusAnalyzer> {
    Box::new(CxxPapyrusAnalyzer {
        inner: PapyrusAnalyzer::new(PathBuf::from(log_path)),
    })
}

fn papyrus_start_monitoring(analyzer: &mut CxxPapyrusAnalyzer) -> Result<(), String> {
    analyzer
        .inner
        .start_monitoring()
        .map_err(|e| format!("{e}"))
}

fn papyrus_check_updates(analyzer: &mut CxxPapyrusAnalyzer) -> ffi::PapyrusStatsDto {
    // Poll for new data; if there are updates they're folded into internal stats.
    // Errors are silently ignored -- C++ gets the last-known stats either way.
    let _ = analyzer.inner.check_for_updates();
    papyrus_stats_to_dto(analyzer.inner.stats())
}

fn papyrus_analyze_full(analyzer: &mut CxxPapyrusAnalyzer) -> Result<ffi::PapyrusStatsDto, String> {
    let stats = analyzer.inner.analyze_full().map_err(|e| format!("{e}"))?;
    Ok(papyrus_stats_to_dto(&stats))
}

fn papyrus_log_exists(analyzer: &CxxPapyrusAnalyzer) -> bool {
    analyzer.inner.log_exists()
}

fn papyrus_reset(analyzer: &mut CxxPapyrusAnalyzer) {
    analyzer.inner.reset();
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

    /// Papyrus log statistics transferred across the FFI boundary.
    struct PapyrusStatsDto {
        dumps: u32,
        stacks: u32,
        warnings: u32,
        errors: u32,
        lines_processed: u32,
        dumps_stacks_ratio: f64,
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

        // Papyrus monitoring
        type CxxPapyrusAnalyzer;
        fn papyrus_analyzer_new(log_path: &str) -> Box<CxxPapyrusAnalyzer>;
        fn papyrus_start_monitoring(analyzer: &mut CxxPapyrusAnalyzer) -> Result<()>;
        fn papyrus_check_updates(analyzer: &mut CxxPapyrusAnalyzer) -> PapyrusStatsDto;
        fn papyrus_analyze_full(analyzer: &mut CxxPapyrusAnalyzer) -> Result<PapyrusStatsDto>;
        fn papyrus_log_exists(analyzer: &CxxPapyrusAnalyzer) -> bool;
        fn papyrus_reset(analyzer: &mut CxxPapyrusAnalyzer);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::tempdir;
    use tempfile::NamedTempFile;

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
    fn test_resolve_formid_db_paths_includes_main_and_hardcoded_folon() {
        let temp = tempdir().unwrap();
        let root = temp.path();
        let data = root.join("CLASSIC Data");
        std::fs::create_dir_all(data.join("databases")).unwrap();

        // Explicit empty user list should still include hardcoded FOLON path.
        std::fs::write(
            root.join("CLASSIC Settings.yaml"),
            "CLASSIC_Settings:\n  FormID Databases:\n    Fallout4: []\n",
        )
        .unwrap();

        let paths =
            resolve_formid_db_paths(&root.to_string_lossy(), &data.to_string_lossy(), "Fallout4");
        let main = data.join("databases").join("Fallout4 FormIDs Main.db");
        let folon = data.join("databases").join("FOLON FormIDs.db");

        assert_eq!(paths, vec![main, folon]);
    }

    #[test]
    fn test_resolve_formid_db_paths_deduplicates_hardcoded_and_user_paths() {
        let temp = tempdir().unwrap();
        let root = temp.path();
        let data = root.join("CLASSIC Data");
        std::fs::create_dir_all(data.join("databases")).unwrap();
        let custom = data.join("databases").join("custom.db");

        let settings_yaml =
        "CLASSIC_Settings:\n  FormID Databases:\n    Fallout4:\n      - databases/FOLON FormIDs.db\n      - databases/custom.db\n";
        std::fs::write(root.join("CLASSIC Settings.yaml"), settings_yaml).unwrap();

        let paths =
            resolve_formid_db_paths(&root.to_string_lossy(), &data.to_string_lossy(), "Fallout4");
        let main = data.join("databases").join("Fallout4 FormIDs Main.db");
        let folon = data.join("databases").join("FOLON FormIDs.db");

        assert_eq!(paths, vec![main, folon, custom]);
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

    // ── Papyrus bridge tests ──────────────────────────────────────

    #[test]
    fn test_papyrus_analyzer_new() {
        let analyzer = papyrus_analyzer_new("/some/path/Papyrus.0.log");
        // Should not panic; analyzer wraps the path without file access
        assert!(!papyrus_log_exists(&analyzer));
    }

    #[test]
    fn test_papyrus_log_exists_with_real_file() {
        let temp = NamedTempFile::new().unwrap();
        let path = temp.path().to_str().unwrap();
        let analyzer = papyrus_analyzer_new(path);
        assert!(papyrus_log_exists(&analyzer));
    }

    #[test]
    fn test_papyrus_analyze_full() {
        let mut temp = NamedTempFile::new().unwrap();
        writeln!(temp, "Dumping Stacks for thread 0x1234").unwrap();
        writeln!(temp, "Dumping Stack for function foo").unwrap();
        writeln!(temp, "[2024/01/01] warning: Variable not initialized").unwrap();
        writeln!(temp, "[2024/01/01] error: Null reference").unwrap();
        temp.flush().unwrap();

        let path = temp.path().to_str().unwrap();
        let mut analyzer = papyrus_analyzer_new(path);
        let dto = papyrus_analyze_full(&mut analyzer).unwrap();

        assert_eq!(dto.dumps, 1);
        assert_eq!(dto.stacks, 1);
        assert_eq!(dto.warnings, 1);
        assert_eq!(dto.errors, 1);
        assert_eq!(dto.lines_processed, 4);
        assert!(dto.dumps_stacks_ratio > 0.0);
    }

    #[test]
    fn test_papyrus_analyze_full_nonexistent() {
        let mut analyzer = papyrus_analyzer_new("/nonexistent/Papyrus.0.log");
        let result = papyrus_analyze_full(&mut analyzer);
        assert!(result.is_err());
    }

    #[test]
    fn test_papyrus_start_monitoring_nonexistent() {
        let mut analyzer = papyrus_analyzer_new("/nonexistent/Papyrus.0.log");
        let result = papyrus_start_monitoring(&mut analyzer);
        assert!(result.is_err());
    }

    #[test]
    fn test_papyrus_start_monitoring_and_check_updates() {
        let mut temp = NamedTempFile::new().unwrap();
        writeln!(temp, "Initial line").unwrap();
        temp.flush().unwrap();

        let path = temp.path().to_str().unwrap();
        let mut analyzer = papyrus_analyzer_new(path);

        // Start monitoring positions at end of file
        papyrus_start_monitoring(&mut analyzer).unwrap();

        // No new data yet -- stats should be empty
        let dto = papyrus_check_updates(&mut analyzer);
        assert_eq!(dto.dumps, 0);
        assert_eq!(dto.lines_processed, 0);

        // Append new data
        writeln!(temp, "Dumping Stacks for thread 0xABC").unwrap();
        writeln!(temp, "[2024/01/01] error: Something bad").unwrap();
        temp.flush().unwrap();

        // Now check_updates should pick up the new lines
        let dto = papyrus_check_updates(&mut analyzer);
        assert_eq!(dto.dumps, 1);
        assert_eq!(dto.errors, 1);
        assert_eq!(dto.lines_processed, 2);
    }

    #[test]
    fn test_papyrus_reset() {
        let mut temp = NamedTempFile::new().unwrap();
        writeln!(temp, "Dumping Stacks").unwrap();
        writeln!(temp, "[2024/01/01] error: Null ref").unwrap();
        temp.flush().unwrap();

        let path = temp.path().to_str().unwrap();
        let mut analyzer = papyrus_analyzer_new(path);

        // Analyze to populate stats
        papyrus_analyze_full(&mut analyzer).unwrap();

        // Reset clears everything
        papyrus_reset(&mut analyzer);

        // check_updates after reset should re-read from beginning
        let dto = papyrus_check_updates(&mut analyzer);
        assert_eq!(dto.dumps, 1);
        assert_eq!(dto.errors, 1);
        assert_eq!(dto.lines_processed, 2);
    }

    #[test]
    fn test_papyrus_stats_dto_no_activity() {
        let stats = PapyrusStats {
            dumps: 0,
            stacks: 0,
            warnings: 10,
            errors: 0,
            last_modified: None,
            lines_processed: 100,
        };
        let dto = papyrus_stats_to_dto(&stats);
        assert_eq!(dto.dumps_stacks_ratio, 0.0);
        assert_eq!(dto.warnings, 10);
        assert_eq!(dto.lines_processed, 100);
    }

    #[test]
    fn test_papyrus_stats_dto_with_activity() {
        let stats = PapyrusStats {
            dumps: 5,
            stacks: 2,
            warnings: 0,
            errors: 10,
            last_modified: None,
            lines_processed: 50,
        };
        let dto = papyrus_stats_to_dto(&stats);
        assert_eq!(dto.dumps, 5);
        assert_eq!(dto.stacks, 2);
        assert_eq!(dto.errors, 10);
        assert_eq!(dto.dumps_stacks_ratio, 2.5);
    }
}
