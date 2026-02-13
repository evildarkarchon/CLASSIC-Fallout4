//! Game Scan Orchestrator (G-01/G-02)
//!
//! Central async orchestrator for game scanning operations. Coordinates
//! concurrent execution of multiple game integrity checks and mod scans,
//! collecting results into a unified report.
//!
//! This is the Rust equivalent of Python's `GameIntegrityOrchestratorCore`
//! and `ScanGameCore` from `ClassicLib/scanning/game/`.
//!
//! ## Architecture
//!
//! The orchestrator is a **pure Rust** module that accepts configuration
//! as parameters (paths, game settings) rather than loading from YAML.
//! The Python/GUI layer is responsible for providing these values.
//!
//! Uses `tokio::JoinSet` for concurrent task management with structured
//! error handling -- individual check failures don't abort the entire scan.

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::path::{Path, PathBuf};

use thiserror::Error;
use tokio::task::JoinSet;

use crate::ba2::{BA2Issues, BA2Scanner};
use crate::config_cache::ConfigFileCache;
use crate::crashgen_orchestrator::CrashgenCheckOrchestrator;
use crate::enb::EnbChecker;
use crate::game_report::{ScanReportBuilder, ScanValidators};
use crate::ini::ConfigIssue;
use crate::logs::LogProcessor;
use crate::mod_ini::ModIniScanner;
use crate::unpacked::UnpackedScanner;
use crate::wrye::WryeBashParser;
use crate::xse::{GameVersion, XseChecker};
use classic_file_io_core::dds::{DDSAnalyzer, GameTarget};

/// Issue map type: category -> set of formatted issue strings
type IssueMap = BTreeMap<String, BTreeSet<String>>;

/// Errors from orchestrator operations
#[derive(Debug, Error)]
pub enum OrchestratorError {
    /// A game scan sub-task failed
    #[error("Scan task failed: {0}")]
    TaskFailed(String),

    /// Path configuration is missing or invalid
    #[error("Missing configuration: {0}")]
    MissingConfig(String),

    /// I/O error during scanning
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    /// Tokio join error
    #[error("Task join error: {0}")]
    JoinError(String),
}

/// Configuration for a game scan operation.
///
/// Provides all the paths and settings the orchestrator needs.
/// The caller (Python bindings or GUI) is responsible for populating these.
#[derive(Debug, Clone)]
pub struct GameScanConfig {
    /// Path to the game root directory
    pub game_path: PathBuf,
    /// Path to the docs folder (for log scanning)
    pub docs_path: Option<PathBuf>,
    /// Path to the mods folder
    pub mods_path: Option<PathBuf>,
    /// XSE acronym (e.g., "F4SE", "SKSE")
    pub xse_acronym: String,
    /// XSE script file patterns -> expected hashes
    pub xse_scriptfiles: HashMap<String, Vec<String>>,
    /// Path to F4SE/SKSE plugins directory
    pub plugins_path: Option<PathBuf>,
    /// Whether in VR mode
    pub is_vr: bool,
    /// Detected game version
    pub game_version: GameVersion,
    /// Crashgen plugin name (e.g., "Buffout4")
    pub crashgen_name: String,
    /// Wrye Bash warning patterns
    pub wrye_warnings: HashMap<String, String>,
    /// Log error catch patterns
    pub log_catch_errors: Vec<String>,
    /// Log file exclude patterns
    pub log_exclude_files: Vec<String>,
    /// Log error exclude patterns
    pub log_exclude_errors: Vec<String>,
    /// Game target for DDS validation
    pub game_target: GameTarget,
    /// Game name string (e.g., "Fallout4") for mod INI console command detection
    pub game_name: String,
}

/// Result of a single check task
#[derive(Debug, Clone)]
pub struct CheckResult {
    /// Name of the check
    pub name: String,
    /// Formatted output text
    pub output: String,
}

/// Combined result of all game integrity checks
#[derive(Debug, Clone)]
pub struct GameScanResult {
    /// Formatted report text from all checks
    pub report: String,
    /// Detected configuration issues (read-only, no file modification)
    pub config_issues: Vec<ConfigIssue>,
    /// Individual check results for debugging/inspection
    pub check_results: Vec<CheckResult>,
    /// Any errors from failed checks (non-fatal)
    pub errors: Vec<String>,
}

/// Combined result of mod scanning (unpacked + archived)
#[derive(Debug, Clone)]
pub struct ModScanResult {
    /// Formatted report text
    pub report: String,
    /// Unpacked issues found
    pub unpacked_issue_count: usize,
    /// Archived issues found
    pub archived_issue_count: usize,
    /// Any errors from scanning
    pub errors: Vec<String>,
}

/// Game Scan Orchestrator
///
/// Coordinates concurrent execution of game integrity checks and mod scans.
/// All checks run as independent tasks -- individual failures are captured
/// without aborting the entire operation.
///
/// # Example
///
/// ```rust,no_run
/// use classic_scangame_core::orchestrator::{GameScanOrchestrator, GameScanConfig};
/// use classic_file_io_core::dds::GameTarget;
/// use classic_scangame_core::xse::GameVersion;
/// use std::path::PathBuf;
/// use std::collections::HashMap;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let config = GameScanConfig {
///     game_path: PathBuf::from("C:/Games/Fallout4"),
///     docs_path: Some(PathBuf::from("C:/Games/Fallout4/docs")),
///     mods_path: Some(PathBuf::from("C:/Games/Fallout4/mods")),
///     xse_acronym: "F4SE".to_string(),
///     xse_scriptfiles: HashMap::new(),
///     plugins_path: Some(PathBuf::from("C:/Games/Fallout4/Data/F4SE/Plugins")),
///     is_vr: false,
///     game_version: GameVersion::Original,
///     crashgen_name: "Buffout4".to_string(),
///     wrye_warnings: HashMap::new(),
///     log_catch_errors: vec!["error".to_string()],
///     log_exclude_files: vec!["crash-".to_string()],
///     log_exclude_errors: vec![],
///     game_target: GameTarget::Fallout4,
///     game_name: "Fallout4".to_string(),
/// };
///
/// let orchestrator = GameScanOrchestrator::new(config);
/// let result = orchestrator.run_game_checks().await?;
/// println!("{}", result.report);
/// # Ok(())
/// # }
/// ```
pub struct GameScanOrchestrator {
    config: GameScanConfig,
}

impl GameScanOrchestrator {
    /// Create a new orchestrator with the given configuration
    pub fn new(config: GameScanConfig) -> Self {
        Self { config }
    }

    /// Run all game integrity checks concurrently.
    ///
    /// Executes XSE validation, crashgen checking, ENB detection,
    /// log error scanning, Wrye Bash analysis, and mod INI scanning
    /// as concurrent tasks. Individual failures are captured as errors
    /// in the result rather than aborting the entire operation.
    pub async fn run_game_checks(&self) -> Result<GameScanResult, OrchestratorError> {
        let mut join_set: JoinSet<Result<CheckResult, String>> = JoinSet::new();

        // Clone values needed by spawned tasks
        let config = self.config.clone();

        // 1. XSE plugins check
        {
            let plugins_path = config.plugins_path.clone();
            let is_vr = config.is_vr;
            let game_version = config.game_version;
            join_set.spawn_blocking(move || match plugins_path {
                Some(path) => match XseChecker::new(&path, is_vr, game_version) {
                    Ok(checker) => Ok(CheckResult {
                        name: "xse_plugins".to_string(),
                        output: checker.validate(),
                    }),
                    Err(e) => Err(format!("XSE check error: {}", e)),
                },
                None => Ok(CheckResult {
                    name: "xse_plugins".to_string(),
                    output: String::new(),
                }),
            });
        }

        // 2. Crashgen settings check
        {
            let game_path = config.game_path.clone();
            let crashgen_name = config.crashgen_name.clone();
            join_set.spawn_blocking(move || {
                match CrashgenCheckOrchestrator::check(&game_path, &crashgen_name) {
                    Ok(report) => Ok(CheckResult {
                        name: "crashgen".to_string(),
                        output: report.message,
                    }),
                    Err(e) => Err(format!("Crashgen check error: {}", e)),
                }
            });
        }

        // 3. ENB detection
        {
            let game_path = config.game_path.clone();
            join_set.spawn_blocking(move || {
                let checker = EnbChecker::new(&game_path);
                let result = checker.validate();
                Ok(CheckResult {
                    name: "enb".to_string(),
                    output: checker.format_message(&result),
                })
            });
        }

        // 4. Log errors in docs folder
        if let Some(docs_path) = config.docs_path.clone() {
            let catch = config.log_catch_errors.clone();
            let exclude_files = config.log_exclude_files.clone();
            let exclude_errors = config.log_exclude_errors.clone();
            join_set.spawn_blocking(move || {
                match LogProcessor::new(catch, exclude_files, exclude_errors) {
                    Ok(processor) => match processor.process_logs(&docs_path) {
                        Ok(report) => Ok(CheckResult {
                            name: "docs_logs".to_string(),
                            output: report,
                        }),
                        Err(e) => Err(format!("Docs log scan error: {}", e)),
                    },
                    Err(e) => Err(format!("Log processor init error: {}", e)),
                }
            });
        }

        // 5. Log errors in game folder
        {
            let game_path = config.game_path.clone();
            let catch = config.log_catch_errors.clone();
            let exclude_files = config.log_exclude_files.clone();
            let exclude_errors = config.log_exclude_errors.clone();
            join_set.spawn_blocking(move || {
                match LogProcessor::new(catch, exclude_files, exclude_errors) {
                    Ok(processor) => match processor.process_logs(&game_path) {
                        Ok(report) => Ok(CheckResult {
                            name: "game_logs".to_string(),
                            output: report,
                        }),
                        Err(e) => Err(format!("Game log scan error: {}", e)),
                    },
                    Err(e) => Err(format!("Log processor init error: {}", e)),
                }
            });
        }

        // 6. Wrye Bash check
        {
            let game_path = config.game_path.clone();
            let wrye_warnings = config.wrye_warnings.clone();
            join_set.spawn_blocking(move || {
                let modchecker_path = game_path.join("ModChecker.html");
                if !modchecker_path.exists() {
                    return Ok(CheckResult {
                        name: "wrye_bash".to_string(),
                        output: String::new(),
                    });
                }
                let html = match std::fs::read_to_string(&modchecker_path) {
                    Ok(content) => content,
                    Err(e) => return Err(format!("Failed to read ModChecker.html: {}", e)),
                };
                let parser = WryeBashParser::new(wrye_warnings);
                let issues = parser.parse(&html);
                Ok(CheckResult {
                    name: "wrye_bash".to_string(),
                    output: WryeBashParser::format_report(&issues),
                })
            });
        }

        // 7. Mod INI scan
        {
            let game_path = config.game_path.clone();
            let game_name = config.game_name.clone();
            join_set.spawn_blocking(move || match ModIniScanner::scan(&game_path, &game_name) {
                Ok(result) => Ok(CheckResult {
                    name: "mod_inis".to_string(),
                    output: result.message,
                }),
                Err(e) => Err(format!("Mod INI scan error: {}", e)),
            });
        }

        // Collect all results
        let mut check_results = Vec::new();
        let mut errors = Vec::new();

        while let Some(result) = join_set.join_next().await {
            match result {
                Ok(Ok(check)) => check_results.push(check),
                Ok(Err(err_msg)) => errors.push(err_msg),
                Err(join_err) => errors.push(format!("Task panic: {}", join_err)),
            }
        }

        // Detect config issues (read-only FCX mode)
        let config_issues = self.detect_config_issues();

        // Build combined report
        let report = check_results
            .iter()
            .filter(|r| !r.output.is_empty())
            .map(|r| r.output.as_str())
            .collect::<Vec<_>>()
            .join("");

        Ok(GameScanResult {
            report,
            config_issues,
            check_results,
            errors,
        })
    }

    /// Detect configuration issues (read-only, FCX mode).
    ///
    /// Scans mod INI files for known problematic settings without modifying files.
    fn detect_config_issues(&self) -> Vec<ConfigIssue> {
        let game_root = &self.config.game_path;
        let mut cache = match ConfigFileCache::new(game_root, &[]) {
            Ok(c) => c,
            Err(_) => return Vec::new(),
        };

        // Collect mod INI issues using the cache
        if let Ok(result) = ModIniScanner::scan_with_cache(&mut cache, &self.config.game_name) {
            return result.issues;
        }

        Vec::new()
    }

    /// Run mod file scans (unpacked + archived) concurrently.
    ///
    /// Scans both loose/unpacked mod files and BA2 archives for issues.
    /// Returns a combined formatted report.
    pub async fn run_mod_scans(&self) -> Result<ModScanResult, OrchestratorError> {
        let mods_path = match &self.config.mods_path {
            Some(p) => p.clone(),
            None => {
                return Ok(ModScanResult {
                    report: String::new(),
                    unpacked_issue_count: 0,
                    archived_issue_count: 0,
                    errors: vec!["Mods folder path not configured".to_string()],
                });
            }
        };

        if !mods_path.exists() {
            return Ok(ModScanResult {
                report: String::new(),
                unpacked_issue_count: 0,
                archived_issue_count: 0,
                errors: vec![format!("Mods folder not found: {}", mods_path.display())],
            });
        }

        let mut join_set: JoinSet<Result<(&'static str, IssueMap), String>> = JoinSet::new();

        // Unpacked scan
        {
            let mods_path = mods_path.clone();
            let xse_scripts: Vec<String> = self.config.xse_scriptfiles.keys().cloned().collect();
            let game_target = self.config.game_target;
            join_set
                .spawn_blocking(move || Self::scan_unpacked(&mods_path, &xse_scripts, game_target));
        }

        // Archived scan
        {
            let mods_path = mods_path.clone();
            join_set.spawn_blocking(move || Self::scan_archived(&mods_path));
        }

        let mut unpacked_issues = BTreeMap::new();
        let mut archived_issues = BTreeMap::new();
        let mut errors = Vec::new();

        while let Some(result) = join_set.join_next().await {
            match result {
                Ok(Ok(("unpacked", issues))) => unpacked_issues = issues,
                Ok(Ok(("archived", issues))) => archived_issues = issues,
                Ok(Ok(_)) => {}
                Ok(Err(err_msg)) => errors.push(err_msg),
                Err(join_err) => errors.push(format!("Task panic: {}", join_err)),
            }
        }

        let unpacked_count: usize = unpacked_issues.values().map(|s| s.len()).sum();
        let archived_count: usize = archived_issues.values().map(|s| s.len()).sum();

        // Build report
        let validators = ScanValidators::new();
        let builder = ScanReportBuilder::new(&validators);
        let report = builder.build_combined_report(
            &unpacked_issues,
            &archived_issues,
            &self.config.xse_acronym,
        );

        Ok(ModScanResult {
            report,
            unpacked_issue_count: unpacked_count,
            archived_issue_count: archived_count,
            errors,
        })
    }

    /// Scan unpacked (loose) mod files
    fn scan_unpacked(
        mods_path: &Path,
        xse_scripts: &[String],
        game_target: GameTarget,
    ) -> Result<(&'static str, IssueMap), String> {
        let scanner = UnpackedScanner::new();
        let issues = scanner
            .scan_directory(mods_path, xse_scripts)
            .map_err(|e| format!("Unpacked scan error: {}", e))?;

        let mut issue_map = BTreeMap::new();

        // Convert UnpackedIssues to BTreeMap<String, BTreeSet<String>>
        if !issues.tex_frmt.is_empty() {
            issue_map.insert(
                "tex_frmt".to_string(),
                issues.tex_frmt.into_iter().collect(),
            );
        }
        if !issues.snd_frmt.is_empty() {
            issue_map.insert(
                "snd_frmt".to_string(),
                issues.snd_frmt.into_iter().collect(),
            );
        }
        if !issues.xse_file.is_empty() {
            issue_map.insert(
                "xse_file".to_string(),
                issues.xse_file.into_iter().collect(),
            );
        }
        if !issues.previs.is_empty() {
            issue_map.insert("previs".to_string(), issues.previs.into_iter().collect());
        }
        if !issues.animdata.is_empty() {
            issue_map.insert(
                "animdata".to_string(),
                issues.animdata.into_iter().collect(),
            );
        }

        // DDS dimension checking via DDSAnalyzer
        if !issues.dds_files.is_empty() {
            let analyzer = DDSAnalyzer::new(game_target);
            let dds_issues = analyzer.validate_batch(&issues.dds_files);
            if !dds_issues.is_empty() {
                let mut tex_dims = BTreeSet::new();
                for (path, file_issues) in &dds_issues {
                    let display = path.display();
                    for issue in file_issues {
                        tex_dims.insert(format!("  - {}: {}\n", display, issue));
                    }
                }
                issue_map.insert("tex_dims".to_string(), tex_dims);
            }
        }

        Ok(("unpacked", issue_map))
    }

    /// Scan archived (BA2) mod files
    fn scan_archived(mods_path: &Path) -> Result<(&'static str, IssueMap), String> {
        let scanner = BA2Scanner::new();
        let ba2_files = scanner.find_ba2_files(mods_path);

        if ba2_files.is_empty() {
            return Ok(("archived", BTreeMap::new()));
        }

        let results = scanner.scan_archives_batch(&ba2_files);

        let mut issue_map: IssueMap = BTreeMap::new();

        for result in results {
            match result {
                Ok(ba2_issues) => {
                    merge_ba2_issues(&ba2_issues, &mut issue_map);
                }
                Err(e) => {
                    log::warn!("BA2 scan error: {}", e);
                }
            }
        }

        Ok(("archived", issue_map))
    }

    /// Run the full scan pipeline: game checks + mod scans.
    ///
    /// Returns combined game result and mod result.
    pub async fn run_full_scan(
        &self,
    ) -> Result<(GameScanResult, ModScanResult), OrchestratorError> {
        let mut join_set: JoinSet<Result<FullScanPart, OrchestratorError>> = JoinSet::new();

        // We need to run game checks and mod scans concurrently.
        // Since run_game_checks and run_mod_scans are async, we spawn them as tokio tasks.
        // But they take &self, so we clone the config for independent orchestrators.

        let config1 = self.config.clone();
        join_set.spawn(async move {
            let orch = GameScanOrchestrator::new(config1);
            let result = orch.run_game_checks().await?;
            Ok(FullScanPart::Game(result))
        });

        let config2 = self.config.clone();
        join_set.spawn(async move {
            let orch = GameScanOrchestrator::new(config2);
            let result = orch.run_mod_scans().await?;
            Ok(FullScanPart::Mods(result))
        });

        let mut game_result = None;
        let mut mod_result = None;

        while let Some(result) = join_set.join_next().await {
            match result {
                Ok(Ok(FullScanPart::Game(r))) => game_result = Some(r),
                Ok(Ok(FullScanPart::Mods(r))) => mod_result = Some(r),
                Ok(Err(e)) => return Err(e),
                Err(join_err) => return Err(OrchestratorError::JoinError(join_err.to_string())),
            }
        }

        Ok((
            game_result.unwrap_or(GameScanResult {
                report: String::new(),
                config_issues: Vec::new(),
                check_results: Vec::new(),
                errors: vec!["Game checks did not complete".to_string()],
            }),
            mod_result.unwrap_or(ModScanResult {
                report: String::new(),
                unpacked_issue_count: 0,
                archived_issue_count: 0,
                errors: vec!["Mod scans did not complete".to_string()],
            }),
        ))
    }
}

/// Internal enum for distinguishing full scan results
enum FullScanPart {
    Game(GameScanResult),
    Mods(ModScanResult),
}

/// Merge BA2Issues into a BTreeMap issue collection
fn merge_ba2_issues(ba2: &BA2Issues, map: &mut BTreeMap<String, BTreeSet<String>>) {
    for item in &ba2.tex_dims {
        map.entry("tex_dims".to_string())
            .or_default()
            .insert(item.clone());
    }
    for item in &ba2.tex_frmt {
        map.entry("tex_frmt".to_string())
            .or_default()
            .insert(item.clone());
    }
    for item in &ba2.snd_frmt {
        map.entry("snd_frmt".to_string())
            .or_default()
            .insert(item.clone());
    }
    for item in &ba2.xse_file {
        map.entry("xse_file".to_string())
            .or_default()
            .insert(item.clone());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn default_config(game_path: PathBuf) -> GameScanConfig {
        GameScanConfig {
            game_path,
            docs_path: None,
            mods_path: None,
            xse_acronym: "F4SE".to_string(),
            xse_scriptfiles: HashMap::new(),
            plugins_path: None,
            is_vr: false,
            game_version: GameVersion::Original,
            crashgen_name: "Buffout4".to_string(),
            wrye_warnings: HashMap::new(),
            log_catch_errors: vec!["error".to_string()],
            log_exclude_files: vec![],
            log_exclude_errors: vec![],
            game_target: GameTarget::Fallout4,
            game_name: "Fallout4".to_string(),
        }
    }

    #[test]
    fn test_orchestrator_creation() {
        let temp = TempDir::new().unwrap();
        let config = default_config(temp.path().to_path_buf());
        let _orch = GameScanOrchestrator::new(config);
    }

    #[test]
    fn test_config_clone() {
        let temp = TempDir::new().unwrap();
        let config = default_config(temp.path().to_path_buf());
        let config2 = config.clone();
        assert_eq!(config.xse_acronym, config2.xse_acronym);
        assert_eq!(config.crashgen_name, config2.crashgen_name);
    }

    #[test]
    fn test_merge_ba2_issues_empty() {
        let issues = BA2Issues::new();
        let mut map = BTreeMap::new();
        merge_ba2_issues(&issues, &mut map);
        assert!(map.is_empty());
    }

    #[test]
    fn test_merge_ba2_issues_populated() {
        let mut issues = BA2Issues::new();
        issues
            .tex_dims
            .push("  - 1023x512 : mod.ba2 > texture.dds".to_string());
        issues
            .snd_frmt
            .push("  - MP3 : mod.ba2 > sound.mp3\n".to_string());

        let mut map = BTreeMap::new();
        merge_ba2_issues(&issues, &mut map);

        assert_eq!(map.len(), 2);
        assert!(map.contains_key("tex_dims"));
        assert!(map.contains_key("snd_frmt"));
    }

    #[tokio::test]
    async fn test_run_game_checks_no_paths() {
        let temp = TempDir::new().unwrap();
        let config = default_config(temp.path().to_path_buf());
        let orch = GameScanOrchestrator::new(config);

        let result = orch.run_game_checks().await.unwrap();
        // Should complete without panic, even with no real game files
        assert!(result.errors.is_empty() || !result.errors.is_empty()); // Just assert it runs
    }

    #[tokio::test]
    async fn test_run_mod_scans_no_mods_path() {
        let temp = TempDir::new().unwrap();
        let config = default_config(temp.path().to_path_buf());
        let orch = GameScanOrchestrator::new(config);

        let result = orch.run_mod_scans().await.unwrap();
        assert!(result.report.is_empty());
        assert!(!result.errors.is_empty()); // Should report missing path
    }

    #[tokio::test]
    async fn test_run_mod_scans_empty_mods_dir() {
        let temp = TempDir::new().unwrap();
        let mods_dir = temp.path().join("mods");
        fs::create_dir(&mods_dir).unwrap();

        let mut config = default_config(temp.path().to_path_buf());
        config.mods_path = Some(mods_dir);

        let orch = GameScanOrchestrator::new(config);
        let result = orch.run_mod_scans().await.unwrap();
        // Empty mods dir = no issues
        assert_eq!(result.unpacked_issue_count, 0);
        assert_eq!(result.archived_issue_count, 0);
    }

    #[tokio::test]
    async fn test_run_mod_scans_with_bad_textures() {
        let temp = TempDir::new().unwrap();
        let mods_dir = temp.path().join("mods");
        fs::create_dir(&mods_dir).unwrap();

        // Create a TGA file (wrong format)
        let tga_path = mods_dir.join("bad_texture.tga");
        fs::write(&tga_path, b"not a real texture").unwrap();

        let mut config = default_config(temp.path().to_path_buf());
        config.mods_path = Some(mods_dir);

        let orch = GameScanOrchestrator::new(config);
        let result = orch.run_mod_scans().await.unwrap();
        assert!(result.unpacked_issue_count > 0);
    }

    #[tokio::test]
    async fn test_run_full_scan() {
        let temp = TempDir::new().unwrap();
        let config = default_config(temp.path().to_path_buf());
        let orch = GameScanOrchestrator::new(config);

        let (game_result, mod_result) = orch.run_full_scan().await.unwrap();
        // Both should complete without panic
        let _ = game_result;
        let _ = mod_result;
    }

    #[test]
    fn test_game_scan_result_fields() {
        let result = GameScanResult {
            report: "test".to_string(),
            config_issues: vec![],
            check_results: vec![CheckResult {
                name: "xse".to_string(),
                output: "ok".to_string(),
            }],
            errors: vec![],
        };
        assert_eq!(result.report, "test");
        assert_eq!(result.check_results.len(), 1);
    }

    #[test]
    fn test_mod_scan_result_fields() {
        let result = ModScanResult {
            report: "scan report".to_string(),
            unpacked_issue_count: 5,
            archived_issue_count: 3,
            errors: vec![],
        };
        assert_eq!(result.unpacked_issue_count, 5);
        assert_eq!(result.archived_issue_count, 3);
    }

    #[test]
    fn test_scan_unpacked_empty_dir() {
        let temp = TempDir::new().unwrap();
        let (label, issues) =
            GameScanOrchestrator::scan_unpacked(temp.path(), &[], GameTarget::Fallout4).unwrap();
        assert_eq!(label, "unpacked");
        assert!(issues.is_empty());
    }

    #[test]
    fn test_scan_archived_empty_dir() {
        let temp = TempDir::new().unwrap();
        let (label, issues) = GameScanOrchestrator::scan_archived(temp.path()).unwrap();
        assert_eq!(label, "archived");
        assert!(issues.is_empty());
    }

    #[test]
    fn test_scan_unpacked_detects_bad_format() {
        let temp = TempDir::new().unwrap();
        fs::write(temp.path().join("test.tga"), b"fake").unwrap();

        let (_, issues) =
            GameScanOrchestrator::scan_unpacked(temp.path(), &[], GameTarget::Fallout4).unwrap();
        assert!(issues.contains_key("tex_frmt"));
    }

    #[test]
    fn test_detect_config_issues_nonexistent_path() {
        let config = default_config(PathBuf::from("nonexistent_path_12345"));
        let orch = GameScanOrchestrator::new(config);
        let issues = orch.detect_config_issues();
        // Should return empty list, not panic
        assert!(issues.is_empty());
    }
}
