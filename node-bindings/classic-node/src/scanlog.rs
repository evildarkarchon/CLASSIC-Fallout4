//! Scanlog bindings for classic-scanlog-core
//!
//! Exposes crash log analysis configuration and result types to JavaScript/TypeScript.
//! Full orchestration (process_log) is exposed as an async function that returns a Promise.
//!
//! ## Async Pattern
//! All async functions respect the ONE RUNTIME RULE by spawning work on the shared
//! Tokio runtime via `classic_shared_core::get_runtime()`.
//!
//! ## Sync Utilities
//! Parsing utilities (`parseLogSegments`, `extractFormIds`, `extractPluginList`,
//! `detectCrashPattern`) are synchronous and operate on string content directly.

use classic_config_core::{ClassicConfig, YamlDataCore};
use classic_scangame_core::integrity::IntegrityConfig;
use classic_scangame_core::{SetupCheckConfig, detect_config_issues, run_combined_checks};
use classic_scanlog_core::crashgen_registry::{CrashgenEntry, CrashgenRegistry};
use classic_scanlog_core::orchestrator;
use classic_scanlog_core::parser::LogParser;
use classic_scanlog_core::segment_key;
use classic_scanlog_core::{ConfigIssue, FcxModeHandler, FcxResetError, GLOBAL_FCX_HANDLER};
use classic_scanlog_core::{
    CrashLogScanIntake, CrashLogScanOptions, CrashLogScanOutcome, CrashLogScanRun,
    CrashLogScanRunLogOutcome, CrashLogScanRunMode, CrashLogScanRunRequest, OrchestratorCore,
    StandardCrashLogScanRunOptions, UnsolvedLogsPolicy,
};
use classic_shared_core::GameId;
use std::collections::{HashMap, HashSet};
use std::path::PathBuf;

use crate::crashgen_rules::{JsCrashgenRegistryEntry, core_rules_to_js, js_rules_to_core};

/// Convert any Display error to a napi::Error.
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

fn normalize_max_concurrent(max_concurrent: Option<u32>) -> Option<usize> {
    match max_concurrent {
        Some(0) | None => None,
        Some(value) => Some(value as usize),
    }
}

async fn load_classic_config() -> napi::Result<ClassicConfig> {
    ClassicConfig::load_or_default()
        .await
        .map_err(|error| to_napi_err(format!("failed to load CLASSIC config: {error}")))
}

fn infer_game_id(config: &ClassicConfig) -> Option<GameId> {
    let game_root = &config.paths.game_root;
    if !game_root.as_os_str().is_empty() {
        if let Some(game_id) = GameId::all()
            .into_iter()
            .find(|game_id| game_root.join(game_id.exe_name()).exists())
        {
            return Some(game_id);
        }

        if let Some(name) = game_root.file_name().and_then(|name| name.to_str())
            && let Ok(game_id) = name.parse::<GameId>()
        {
            return Some(game_id);
        }
    }

    None
}

fn build_setup_check_config(config: &ClassicConfig, game_id: GameId) -> Option<SetupCheckConfig> {
    if config.paths.game_root.as_os_str().is_empty() {
        return None;
    }

    Some(SetupCheckConfig {
        integrity: IntegrityConfig::new(
            config.paths.game_root.join(game_id.exe_name()),
            Vec::new(),
            game_id.as_str().to_string(),
        ),
        game_name: game_id.as_str().to_string(),
        docs_path: config
            .paths
            .docs_root
            .as_ref()
            .or(config.paths.ini_folder.as_ref())
            .map(|path| path.to_string_lossy().into_owned()),
        xse_hashes: Vec::new(),
    })
}

fn to_scanlog_issue(issue: classic_scangame_core::ConfigIssue) -> ConfigIssue {
    ConfigIssue::new(
        issue.file_path.display().to_string(),
        Some(issue.section),
        issue.setting,
        issue.current_value,
        issue.recommended_value,
        issue.description,
        match issue.severity {
            classic_scangame_core::IssueSeverity::Error => "error",
            classic_scangame_core::IssueSeverity::Warning => "warning",
            classic_scangame_core::IssueSeverity::Info => "info",
        }
        .to_string(),
    )
}

fn format_detected_issues(issues: &[ConfigIssue]) -> String {
    issues.iter().map(ConfigIssue::format_report).collect()
}

async fn run_fcx_scan_state_checks() -> napi::Result<()> {
    let config = load_classic_config().await?;
    let game_id = infer_game_id(&config).ok_or_else(|| {
        to_napi_err("failed to infer game id from configured game root; run path detection first")
    })?;

    let main_result = build_setup_check_config(&config, game_id)
        .map(|setup_config| run_combined_checks(&setup_config).combined())
        .unwrap_or_default();

    let rust_issues: Vec<ConfigIssue> = if config.paths.game_root.as_os_str().is_empty() {
        Vec::new()
    } else {
        detect_config_issues(&config.paths.game_root, game_id.as_str())
            .into_iter()
            .map(to_scanlog_issue)
            .collect()
    };
    let game_result = format_detected_issues(&rust_issues);

    let mut global_handler = GLOBAL_FCX_HANDLER.lock();
    global_handler.checks_run = true;
    global_handler.fcx_mode = true;
    global_handler.set_main_files_result(main_result);
    global_handler.set_game_files_result(game_result);
    global_handler.set_detected_issues(rust_issues);

    Ok(())
}

async fn prepare_fcx_state_for_scan(fcx_mode: bool) -> napi::Result<()> {
    match FcxModeHandler::reset_global_state() {
        Ok(()) | Err(FcxResetError::Unnecessary) => {}
        Err(error) => {
            return Err(to_napi_err(format!(
                "failed to reset FCX global state before scan: {error}"
            )));
        }
    }

    if fcx_mode {
        run_fcx_scan_state_checks().await?;
    }

    Ok(())
}

/// Detect crashgen settings section markers within parser `settings` lines.
///
/// The parser's `settings` segment now includes all pre-`SYSTEM SPECS:` lines.
/// For Node's `header` field we preserve legacy behavior by only exposing lines
/// after known crashgen settings markers.
fn is_settings_header_marker(line: &str) -> bool {
    let trimmed = line.trim();
    trimmed.eq_ignore_ascii_case("[Compatibility]") || trimmed.eq_ignore_ascii_case("[Patches]")
}

/// JavaScript-compatible analysis configuration.
///
/// This is a simplified view of `classic_scanlog_core::AnalysisConfig` exposing
/// the most commonly needed fields. Additional fields can be set via setter methods.
#[napi(object)]
pub struct JsAnalysisConfig {
    /// Game name (e.g., "Fallout4")
    pub game: String,
    /// Selected game-version mode
    /// ("auto", "Original", "NextGen", "AnniversaryEdition"/"AE", "VR")
    pub game_version: String,
    /// Crashgen name (e.g., "Buffout 4")
    pub crashgen_name: String,
    /// XSE acronym (e.g., "F4SE")
    pub xse_acronym: String,
    /// CLASSIC version string
    pub classic_version: String,
    /// Whether FCX mode is enabled
    pub fcx_mode: bool,
    /// Whether to simplify logs
    pub simplify_logs: bool,
    /// Per-crashgen registry entries with optional settings rules.
    pub crashgen_registry: Option<HashMap<String, JsCrashgenRegistryEntry>>,
}

/// Optional settings used when building analysis config from YAML content.
#[napi(object)]
#[derive(Clone)]
pub struct JsAnalysisBuildOptions {
    /// Whether to include FormID value lookups in reports.
    pub show_formid_values: Option<bool>,
    /// Whether FCX mode is enabled.
    pub fcx_mode: Option<bool>,
    /// Whether to simplify logs by removing configured strings.
    pub simplify_logs: Option<bool>,
    /// Strings to remove when simplify logs is enabled.
    pub remove_list: Option<Vec<String>>,
}

/// JavaScript-compatible analysis result.
///
/// Contains the report and statistics from analyzing a single crash log.
#[napi(object)]
pub struct JsAnalysisResult {
    /// Path to the log file that was analyzed
    pub log_path: String,
    /// Generated report lines
    pub report_lines: Vec<String>,
    /// Whether analysis succeeded
    pub success: bool,
    /// Error message if analysis failed
    pub error: Option<String>,
    /// Processing time in milliseconds
    pub processing_time_ms: u32,
    /// Number of FormIDs found
    pub formid_count: u32,
    /// Number of plugins detected
    pub plugin_count: u32,
    /// Number of suspect patterns matched
    pub suspect_count: u32,
}

/// Options for a full Crash Log Scan Run.
#[napi(object)]
pub struct JsScanRunOptions {
    /// Root directory that contains CLASSIC Data and CLASSIC Ignore.yaml.
    pub yaml_dir_root: String,
    /// CLASSIC Data directory.
    pub yaml_dir_data: String,
    /// Game identifier, e.g. Fallout4.
    pub game: String,
    /// Selected game-version mode.
    pub game_version: String,
    /// Whether to include FormID value lookups in reports.
    pub show_formid_values: Option<bool>,
    /// Whether FCX mode is enabled.
    pub fcx_mode: Option<bool>,
    /// Whether to simplify logs by removing configured strings.
    pub simplify_logs: Option<bool>,
    /// Whether failed Standard runs move logs and reports to Unsolved Logs.
    pub move_unsolved_logs: Option<bool>,
    /// Whether this is a Targeted Crash Log Scan Run.
    pub targeted_mode: Option<bool>,
    /// Optional maximum number of concurrent scans. Zero and undefined use core defaults.
    pub max_concurrent: Option<u32>,
    /// Whether results should preserve input order instead of completion order.
    pub preserve_order: Option<bool>,
}

/// JavaScript-compatible full scan-run per-log result.
#[napi(object)]
pub struct JsScanRunLogResult {
    /// Stable index from the input log path list.
    pub input_index: u32,
    /// Crash Log path selected for this entry.
    pub log_path: String,
    /// Autoscan Report path when one was written successfully.
    pub autoscan_report_path: Option<String>,
    /// Whether analysis and run-owned side effects succeeded.
    pub success: bool,
    /// Whether this entry was cancelled before analysis started.
    pub cancelled: bool,
    /// Whether the Crash Log or Autoscan Report moved to Unsolved Logs.
    pub moved_to_unsolved_logs: bool,
    /// Error message for failed or cancelled outcomes.
    pub error: Option<String>,
    /// Processing time in milliseconds.
    pub processing_time_ms: u32,
    /// Number of FormIDs found.
    pub formid_count: u32,
    /// Number of plugins detected.
    pub plugin_count: u32,
    /// Number of suspect patterns matched.
    pub suspect_count: u32,
}

#[napi(object)]
pub struct JsFcxConfigIssue {
    pub file_path: String,
    pub section: Option<String>,
    pub setting: String,
    pub current_value: String,
    pub recommended_value: String,
    pub description: String,
    pub severity: String,
}

impl From<&ConfigIssue> for JsFcxConfigIssue {
    fn from(issue: &ConfigIssue) -> Self {
        Self {
            file_path: issue.file_path.clone(),
            section: issue.section.clone(),
            setting: issue.setting.clone(),
            current_value: issue.current_value.clone(),
            recommended_value: issue.recommended_value.clone(),
            description: issue.description.clone(),
            severity: issue.severity.clone(),
        }
    }
}

/// JavaScript-compatible parsed log segments.
///
/// Contains the various sections extracted from a crash log.
#[napi(object)]
pub struct JsLogSegments {
    /// Header/compatibility section lines
    pub header: Vec<String>,
    /// System specs section lines
    pub system: Vec<String>,
    /// Probable call stack section lines
    pub stack: Vec<String>,
    /// Modules section lines
    pub modules: Vec<String>,
    /// Plugins section lines
    pub plugins: Vec<String>,
    /// Number of segments found
    pub segment_count: u32,
}

/// Create a new analysis configuration with defaults.
///
/// Returns a JavaScript object with the configuration fields.
/// Modify the returned object's properties before passing to analysis functions.
#[napi]
pub fn create_analysis_config(game: String, game_version: String) -> JsAnalysisConfig {
    JsAnalysisConfig {
        game,
        game_version,
        crashgen_name: String::new(),
        xse_acronym: String::new(),
        classic_version: "CLASSIC".to_string(),
        fcx_mode: false,
        simplify_logs: false,
        crashgen_registry: Some(HashMap::new()),
    }
}

#[napi]
pub fn reset_fcx_global_state() -> napi::Result<()> {
    match FcxModeHandler::reset_global_state() {
        Ok(()) | Err(FcxResetError::Unnecessary) => Ok(()),
        Err(error) => Err(to_napi_err(format!(
            "failed to reset FCX global state: {error}"
        ))),
    }
}

#[napi]
pub fn get_fcx_config_issues() -> Vec<JsFcxConfigIssue> {
    let handler = GLOBAL_FCX_HANDLER.lock();
    handler
        .get_detected_issues()
        .iter()
        .map(JsFcxConfigIssue::from)
        .collect()
}

fn resolve_build_options(
    options: Option<JsAnalysisBuildOptions>,
) -> (bool, bool, bool, Vec<String>) {
    let Some(options) = options else {
        return (false, false, false, Vec::new());
    };

    (
        options.show_formid_values.unwrap_or(false),
        options.fcx_mode.unwrap_or(false),
        options.simplify_logs.unwrap_or(false),
        options.remove_list.unwrap_or_default(),
    )
}

fn build_core_config_from_yaml_content(
    main_content: String,
    game_content: String,
    ignore_content: String,
    game: String,
    selected_game_version: String,
    options: Option<JsAnalysisBuildOptions>,
) -> napi::Result<(orchestrator::AnalysisConfig, YamlDataCore)> {
    let (show_formid_values, fcx_mode, simplify_logs, remove_list) = resolve_build_options(options);
    let yaml = YamlDataCore::from_yaml_content(
        &main_content,
        &game_content,
        &ignore_content,
        game.clone(),
        selected_game_version.clone(),
    )
    .map_err(to_napi_err)?;

    let config = orchestrator::build_analysis_config_from_yaml(
        &yaml,
        &game,
        &selected_game_version,
        show_formid_values,
        fcx_mode,
        simplify_logs,
        remove_list,
    );

    Ok((config, yaml))
}

/// Build an analysis config from raw YAML content (high-level config path).
#[napi]
pub fn create_analysis_config_from_yaml_content(
    main_content: String,
    game_content: String,
    ignore_content: String,
    game: String,
    game_version: String,
    options: Option<JsAnalysisBuildOptions>,
) -> napi::Result<JsAnalysisConfig> {
    let (core_config, yaml) = build_core_config_from_yaml_content(
        main_content,
        game_content,
        ignore_content,
        game,
        game_version.clone(),
        options,
    )?;

    Ok(JsAnalysisConfig {
        game: core_config.game,
        game_version,
        crashgen_name: core_config.crashgen_name,
        xse_acronym: core_config.xse_acronym,
        classic_version: core_config.classic_version,
        fcx_mode: core_config.fcx_mode,
        simplify_logs: core_config.simplify_logs,
        crashgen_registry: Some(
            yaml.crashgen_registry
                .iter()
                .map(|(name, entry)| {
                    (
                        name.clone(),
                        JsCrashgenRegistryEntry {
                            display_section: entry.display_section.clone(),
                            ignore_keys: entry.ignore_keys.clone(),
                            checks: entry.checks.clone(),
                            settings_rules_version: entry.settings_rules_version,
                            settings_rules: core_rules_to_js(entry.settings_rules.as_ref()),
                        },
                    )
                })
                .collect(),
        ),
    })
}

/// Process a single crash log using configuration built directly from YAML content.
#[napi]
pub async fn process_log_with_yaml_content(
    log_path: String,
    main_content: String,
    game_content: String,
    ignore_content: String,
    game: String,
    game_version: String,
    options: Option<JsAnalysisBuildOptions>,
) -> napi::Result<JsAnalysisResult> {
    let (_, fcx_mode, _, _) = resolve_build_options(options.clone());
    prepare_fcx_state_for_scan(fcx_mode).await?;
    let (core_config, _) = build_core_config_from_yaml_content(
        main_content,
        game_content,
        ignore_content,
        game,
        game_version,
        options,
    )?;
    let handle = classic_shared_core::get_runtime().handle().clone();

    let result = handle
        .spawn(async move {
            let orchestrator = OrchestratorCore::new(core_config)
                .map_err(|e| format!("Failed to create orchestrator: {e}"))?;
            orchestrator
                .process_log(log_path)
                .await
                .map_err(|e| format!("Analysis error: {e}"))
        })
        .await
        .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
        .map_err(to_napi_err)?;

    Ok(_core_result_to_js(&result))
}

/// Process multiple crash logs using configuration built directly from YAML content.
#[allow(clippy::too_many_arguments)]
#[napi]
pub async fn process_logs_batch_with_yaml_content(
    log_paths: Vec<String>,
    main_content: String,
    game_content: String,
    ignore_content: String,
    game: String,
    game_version: String,
    options: Option<JsAnalysisBuildOptions>,
    max_concurrent: Option<u32>,
) -> napi::Result<Vec<JsAnalysisResult>> {
    let (_, fcx_mode, _, _) = resolve_build_options(options.clone());
    prepare_fcx_state_for_scan(fcx_mode).await?;
    let (core_config, _) = build_core_config_from_yaml_content(
        main_content,
        game_content,
        ignore_content,
        game,
        game_version,
        options,
    )?;
    let handle = classic_shared_core::get_runtime().handle().clone();
    let max_concurrent = normalize_max_concurrent(max_concurrent);

    let results = handle
        .spawn(async move {
            let orchestrator = OrchestratorCore::new(core_config)
                .map_err(|e| format!("Failed to create orchestrator: {e}"))?;
            Ok::<_, String>(
                orchestrator
                    .process_logs_batch(log_paths, max_concurrent)
                    .await,
            )
        })
        .await
        .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
        .map_err(to_napi_err)?;

    Ok(results.iter().map(_core_result_to_js).collect())
}

/// Execute a full Crash Log Scan Run for selected logs.
///
/// This is the adapter-facing scan-run seam: Rust writes Autoscan Reports and
/// owns Standard versus Targeted Unsolved Logs behavior before returning each
/// per-log outcome. Use the lower-level process* functions only when callers
/// explicitly need analysis results with report lines.
#[napi]
pub async fn scan_run_execute(
    log_paths: Vec<String>,
    options: JsScanRunOptions,
) -> napi::Result<Vec<JsScanRunLogResult>> {
    let handle = classic_shared_core::get_runtime().handle().clone();
    let max_concurrent = normalize_max_concurrent(options.max_concurrent);
    let show_formid_values = options.show_formid_values.unwrap_or(false);
    let fcx_mode = options.fcx_mode.unwrap_or(false);
    let simplify_logs = options.simplify_logs.unwrap_or(false);
    let targeted_mode = options.targeted_mode.unwrap_or(false);
    let move_unsolved_logs = options.move_unsolved_logs.unwrap_or(false);
    let preserve_order = options.preserve_order.unwrap_or(false);
    let yaml_dir_root = PathBuf::from(&options.yaml_dir_root);
    let yaml_dir_data = PathBuf::from(&options.yaml_dir_data);

    let results = handle
        .spawn(async move {
            let prepared = CrashLogScanIntake::from_yaml_paths(
                yaml_dir_root.clone(),
                yaml_dir_data,
                options.game,
                options.game_version,
                CrashLogScanOptions::new(show_formid_values, fcx_mode, simplify_logs),
            )
            .prepare()
            .await
            .map_err(|error| format!("Failed to prepare scan run: {error}"))?;

            let mode = if targeted_mode {
                CrashLogScanRunMode::Targeted
            } else {
                CrashLogScanRunMode::Standard(StandardCrashLogScanRunOptions {
                    unsolved_logs: if move_unsolved_logs {
                        UnsolvedLogsPolicy::MoveTo {
                            directory: yaml_dir_root.join("CLASSIC Backup").join("Unsolved Logs"),
                        }
                    } else {
                        UnsolvedLogsPolicy::LeaveInPlace
                    },
                })
            };

            let run = CrashLogScanRun::new(prepared);
            let result = run
                .run(
                    CrashLogScanRunRequest {
                        logs: log_paths.into_iter().map(PathBuf::from).collect(),
                        mode,
                        max_concurrent,
                        cancellation: None,
                        preserve_order,
                    },
                    |_| {},
                )
                .await
                .map_err(|error| format!("Failed to execute scan run: {error}"))?;

            Ok::<_, String>(
                result
                    .logs
                    .into_iter()
                    .map(scan_run_outcome_to_js)
                    .collect(),
            )
        })
        .await
        .map_err(|error| to_napi_err(format!("Runtime error: {error}")))?
        .map_err(to_napi_err)?;

    Ok(results)
}

// ============================================================================
// Async Analysis Functions
// ============================================================================

/// Process a single crash log file and return the analysis result.
///
/// Reads the crash log at `logPath`, runs the full analysis pipeline, and
/// returns a Promise that resolves to a `JsAnalysisResult`.
///
/// Respects the ONE RUNTIME RULE: spawns work on the shared Tokio runtime.
#[napi]
pub async fn process_log(
    log_path: String,
    config: JsAnalysisConfig,
) -> napi::Result<JsAnalysisResult> {
    prepare_fcx_state_for_scan(config.fcx_mode).await?;
    let core_config = _js_config_to_core(&config);
    let handle = classic_shared_core::get_runtime().handle().clone();

    let result = handle
        .spawn(async move {
            let orchestrator = OrchestratorCore::new(core_config)
                .map_err(|e| format!("Failed to create orchestrator: {e}"))?;
            orchestrator
                .process_log(log_path)
                .await
                .map_err(|e| format!("Analysis error: {e}"))
        })
        .await
        .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
        .map_err(to_napi_err)?;

    Ok(_core_result_to_js(&result))
}

/// Process multiple crash log files concurrently and return all results.
///
/// Each log is analyzed independently; failures do not stop processing of
/// remaining logs. Failed analyses appear in the result array with
/// `success: false` and an error message.
///
/// Respects the ONE RUNTIME RULE: spawns work on the shared Tokio runtime.
#[napi]
pub async fn process_logs_batch(
    log_paths: Vec<String>,
    config: JsAnalysisConfig,
    max_concurrent: Option<u32>,
) -> napi::Result<Vec<JsAnalysisResult>> {
    prepare_fcx_state_for_scan(config.fcx_mode).await?;
    let core_config = _js_config_to_core(&config);
    let handle = classic_shared_core::get_runtime().handle().clone();
    let max_concurrent = normalize_max_concurrent(max_concurrent);

    let results = handle
        .spawn(async move {
            let orchestrator = OrchestratorCore::new(core_config)
                .map_err(|e| format!("Failed to create orchestrator: {e}"))?;
            Ok::<_, String>(
                orchestrator
                    .process_logs_batch(log_paths, max_concurrent)
                    .await,
            )
        })
        .await
        .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
        .map_err(to_napi_err)?;

    Ok(results.iter().map(_core_result_to_js).collect())
}

// ============================================================================
// Synchronous Parsing Utilities
// ============================================================================

/// Parse crash log content into structured segments.
///
/// Splits the log content into sections (header, system, stack, modules, plugins)
/// using the SIMD-optimized parser. This is a synchronous operation.
///
/// @param content - The full crash log file content as a string.
/// @returns A `JsLogSegments` object with the extracted sections.
#[napi]
pub fn parse_log_segments(content: String) -> napi::Result<JsLogSegments> {
    let parser = LogParser::new(None).map_err(to_napi_err)?;

    let lines: Vec<String> = content.lines().map(String::from).collect();

    let all_sections = parser.parse_all_sections(&lines);
    let header = all_sections
        .get(segment_key::SETTINGS)
        .and_then(|settings| {
            settings
                .iter()
                .position(|line| is_settings_header_marker(line))
                .map(|idx| settings[idx + 1..].to_vec())
        })
        .unwrap_or_default();
    let system = all_sections
        .get(segment_key::SYSTEM)
        .cloned()
        .unwrap_or_default();
    let stack = all_sections
        .get(segment_key::CALLSTACK)
        .cloned()
        .unwrap_or_default();
    let modules = all_sections
        .get(segment_key::MODULES)
        .cloned()
        .unwrap_or_default();
    let plugins = all_sections
        .get(segment_key::PLUGINS)
        .cloned()
        .unwrap_or_default();
    let segment_count = [
        header.as_slice(),
        system.as_slice(),
        stack.as_slice(),
        modules.as_slice(),
        plugins.as_slice(),
    ]
    .iter()
    .filter(|section| !section.is_empty())
    .count() as u32;

    Ok(JsLogSegments {
        header,
        system,
        stack,
        modules,
        plugins,
        segment_count,
    })
}

/// Extract FormID hex strings from crash log content.
///
/// Searches for Bethesda game FormIDs (8-character hex identifiers) in the
/// provided text. Uses SIMD-optimized regex matching.
///
/// @param content - The crash log content (or a section of it) to search.
/// @returns An array of FormID strings (hex values without "0x" prefix).
#[napi]
pub fn extract_form_ids(content: String) -> napi::Result<Vec<String>> {
    let parser = LogParser::new(None).map_err(to_napi_err)?;
    let lines: Vec<String> = content.lines().map(String::from).collect();
    Ok(parser.extract_formids(&lines))
}

/// Extract plugin names from crash log content.
///
/// Searches for Bethesda game plugin entries (e.g., `[00] Fallout4.esm`)
/// and returns just the plugin filenames.
///
/// @param content - The crash log content (or plugin section) to search.
/// @returns An array of plugin filename strings (e.g., "Fallout4.esm").
#[napi]
pub fn extract_plugin_list(content: String) -> napi::Result<Vec<String>> {
    let parser = LogParser::new(None).map_err(to_napi_err)?;
    let lines: Vec<String> = content.lines().map(String::from).collect();
    let plugins = parser.extract_plugins(&lines);
    // Return just the plugin names (first element of each tuple)
    Ok(plugins.into_iter().map(|(name, _index)| name).collect())
}

/// Detect the crash pattern from crash log content.
///
/// Analyzes the log header for known crash patterns (e.g., "ACCESS_VIOLATION",
/// "STACK_OVERFLOW", "STACK_BUFFER_OVERRUN"). Returns the pattern name if
/// detected, or `undefined` if no known pattern is found.
///
/// @param content - The crash log content to analyze.
/// @returns The crash pattern name, or `undefined` if none detected.
#[napi]
pub fn detect_crash_pattern(content: String) -> Option<String> {
    // Known crash patterns to detect in the main error line
    let known_patterns: &[(&str, &str)] = &[
        ("EXCEPTION_ACCESS_VIOLATION", "ACCESS_VIOLATION"),
        ("EXCEPTION_STACK_OVERFLOW", "STACK_OVERFLOW"),
        ("EXCEPTION_INT_DIVIDE_BY_ZERO", "INT_DIVIDE_BY_ZERO"),
        ("EXCEPTION_BREAKPOINT", "BREAKPOINT"),
        ("EXCEPTION_ILLEGAL_INSTRUCTION", "ILLEGAL_INSTRUCTION"),
        ("EXCEPTION_STACK_BUFFER_OVERRUN", "STACK_BUFFER_OVERRUN"),
        ("STATUS_HEAP_CORRUPTION", "HEAP_CORRUPTION"),
        ("0xC0000005", "ACCESS_VIOLATION"),
        ("0xC00000FD", "STACK_OVERFLOW"),
        ("0xC0000094", "INT_DIVIDE_BY_ZERO"),
        ("0x80000003", "BREAKPOINT"),
        ("0xC000001D", "ILLEGAL_INSTRUCTION"),
        ("0xC0000409", "STACK_BUFFER_OVERRUN"),
    ];

    // Search the first 30 lines for the main error / unhandled exception
    let upper = content.to_uppercase();
    for line in upper.lines().take(30) {
        if line.contains("UNHANDLED EXCEPTION")
            || line.contains("EXCEPTION_")
            || line.contains("0XC000")
        {
            for (pattern, name) in known_patterns {
                if line.contains(pattern) {
                    return Some(name.to_string());
                }
            }
        }
    }

    None
}

// ============================================================================
// Internal Helpers
// ============================================================================

/// Convert a JsAnalysisConfig to the core AnalysisConfig type.
///
/// This is an internal helper used when passing config to the orchestrator.
/// Not exported to JavaScript.
pub(crate) fn _js_config_to_core(config: &JsAnalysisConfig) -> orchestrator::AnalysisConfig {
    let mut core_config =
        orchestrator::AnalysisConfig::new(config.game.clone(), config.game_version.clone());
    core_config.crashgen_name = config.crashgen_name.clone();
    core_config.xse_acronym = config.xse_acronym.clone();
    core_config.classic_version = config.classic_version.clone();
    core_config.fcx_mode = config.fcx_mode;
    core_config.simplify_logs = config.simplify_logs;

    let mut entries: HashMap<String, CrashgenEntry> = HashMap::new();
    let mut default_entry = CrashgenEntry::default_entry();
    if let Some(registry) = &config.crashgen_registry {
        for (name, entry) in registry {
            let mapped = CrashgenEntry {
                display_section: entry.display_section.clone(),
                ignore_keys: entry.ignore_keys.iter().cloned().collect::<HashSet<_>>(),
                settings_rules: js_rules_to_core(entry.settings_rules.clone()),
            };

            if name == "default" {
                default_entry = mapped;
            } else {
                entries.insert(name.clone(), mapped);
            }
        }
    }
    core_config.crashgen_registry = CrashgenRegistry::new(entries, default_entry);
    core_config
}

/// Convert a core AnalysisResult to the JS-compatible type.
pub(crate) fn _core_result_to_js(result: &orchestrator::AnalysisResult) -> JsAnalysisResult {
    JsAnalysisResult {
        log_path: result.log_path.clone(),
        report_lines: result.report_lines.clone(),
        success: result.success,
        error: result.error.clone(),
        processing_time_ms: result.processing_time_ms as u32,
        formid_count: result.formid_count as u32,
        plugin_count: result.plugin_count as u32,
        suspect_count: result.suspect_count as u32,
    }
}

fn scan_run_outcome_to_js(outcome: CrashLogScanRunLogOutcome) -> JsScanRunLogResult {
    JsScanRunLogResult {
        input_index: outcome.input_index as u32,
        log_path: outcome.crash_log.to_string_lossy().to_string(),
        autoscan_report_path: outcome
            .autoscan_report
            .map(|path| path.to_string_lossy().to_string()),
        success: outcome.outcome == CrashLogScanOutcome::Succeeded,
        cancelled: outcome.outcome == CrashLogScanOutcome::CancelledBeforeStart,
        moved_to_unsolved_logs: outcome.moved_to_unsolved_logs,
        error: outcome.error,
        processing_time_ms: outcome.processing_time_ms as u32,
        formid_count: outcome.formid_count as u32,
        plugin_count: outcome.plugin_count as u32,
        suspect_count: outcome.suspect_count as u32,
    }
}

// ============================================================================
// VR Log Detection
// ============================================================================

/// Detect if crash log content is from a VR game.
///
/// Checks for VR-specific markers (e.g. "Fallout4VR.exe", "Fallout4VR.esm")
/// in the log content, case-insensitively.
///
/// @param content - The crash log content to check.
/// @returns `true` if VR markers are found, `false` otherwise.
#[napi]
pub fn detect_vr_log(content: String) -> bool {
    classic_scanlog_core::detect_vr_log(&content)
}

// ============================================================================
// GPU Detection
// ============================================================================

/// GPU information detected from system specs.
#[napi(object)]
pub struct JsGpuInfo {
    /// Primary GPU name (e.g. "Nvidia AD104 [GeForce RTX 4070]")
    pub primary: String,
    /// Secondary GPU name, if present
    pub secondary: Option<String>,
    /// GPU manufacturer (e.g. "AMD", "Nvidia", "Intel", "Unknown")
    pub manufacturer: String,
    /// Rival GPU manufacturer for compatibility checks
    pub rival: Option<String>,
}

/// Detect GPU information from system specification lines.
///
/// Parses lines from the SYSTEM SPECS section of a crash log to identify
/// the primary and secondary GPUs, manufacturer, and rival vendor.
///
/// @param systemLines - Array of system specification lines from the crash log.
/// @returns A `JsGpuInfo` object with the detected GPU information.
#[napi]
pub fn detect_gpu_info(system_lines: Vec<String>) -> JsGpuInfo {
    let info = classic_scanlog_core::gpu_detector::GpuDetector::get_gpu_info(&system_lines);
    JsGpuInfo {
        primary: info.primary,
        secondary: info.secondary,
        manufacturer: info.manufacturer,
        rival: info.rival,
    }
}

// ============================================================================
// Crashgen Version Checking
// ============================================================================

/// Parsed crash generator version components.
#[napi(object)]
pub struct JsCrashgenVersionInfo {
    /// Major version number (e.g. 1 in "1.28.0")
    pub major: u32,
    /// Minor version number (e.g. 28 in "1.28.0")
    pub minor: u32,
    /// Patch version number (e.g. 0 in "1.28.0")
    pub patch: u32,
}

/// Crashgen version validation status returned to JavaScript.
#[napi(string_enum)]
pub enum JsCrashgenVersionStatus {
    /// Detected version matches one of the supported versions.
    Valid,
    /// Detected version is older than the supported range.
    Outdated,
    /// Detected version is newer than any known supported version.
    NewerThanKnown,
    /// No supported versions were provided or version parsing failed.
    NoSupportedVersion,
}

/// Parse a crash generator version string into components.
///
/// Accepts various formats: "1.28.0", "v1.28.0", "Buffout 4 v1.28.0".
/// Returns `undefined` if parsing fails.
///
/// @param versionStr - The version string to parse.
/// @returns Parsed version components, or `undefined` on failure.
#[napi]
pub fn parse_crashgen_version(version_str: String) -> Option<JsCrashgenVersionInfo> {
    classic_scanlog_core::version::CrashgenVersion::parse(&version_str).map(|v| {
        JsCrashgenVersionInfo {
            major: v.major as u32,
            minor: v.minor as u32,
            patch: v.patch as u32,
        }
    })
}

/// Check a crash generator version against a list of valid versions.
///
/// Returns one of: "Valid", "Outdated", "NewerThanKnown", "NoSupportedVersion".
///
/// @param detected - The detected version string (e.g. "1.28.6" or "Buffout 4 v1.28.6").
/// @param validVersions - Array of valid version strings to check against.
/// @returns A status string indicating the validation result.
#[napi]
pub fn check_crashgen_version_status(
    detected: String,
    valid_versions: Vec<String>,
) -> JsCrashgenVersionStatus {
    let valid_refs: Vec<&str> = valid_versions.iter().map(|s| s.as_str()).collect();
    let status =
        classic_scanlog_core::version::check_crashgen_version_status(&detected, &valid_refs);
    match status {
        classic_scanlog_core::version::CrashgenVersionStatus::Valid => {
            JsCrashgenVersionStatus::Valid
        }
        classic_scanlog_core::version::CrashgenVersionStatus::Outdated => {
            JsCrashgenVersionStatus::Outdated
        }
        classic_scanlog_core::version::CrashgenVersionStatus::NewerThanKnown => {
            JsCrashgenVersionStatus::NewerThanKnown
        }
        classic_scanlog_core::version::CrashgenVersionStatus::NoSupportedVersion => {
            JsCrashgenVersionStatus::NoSupportedVersion
        }
    }
}

// ============================================================================
// Papyrus Analysis
// ============================================================================

/// Papyrus log analysis statistics.
#[napi(object)]
pub struct JsPapyrusStats {
    /// Number of "Dumping Stacks" entries (plural)
    pub dumps: u32,
    /// Number of "Dumping Stack" entries (singular)
    pub stacks: u32,
    /// Number of warning messages
    pub warnings: u32,
    /// Number of error messages
    pub errors: u32,
    /// Total lines processed from the log file
    pub lines_processed: u32,
}

/// Analyze a Papyrus log file and return statistics.
///
/// Reads the Papyrus log at the given path and collects statistics about
/// dumps, stacks, warnings, and errors.
///
/// @param logPath - Absolute path to the Papyrus log file.
/// @returns A `JsPapyrusStats` object with the analysis results.
#[napi]
pub fn analyze_papyrus_log(log_path: String) -> napi::Result<JsPapyrusStats> {
    let mut analyzer =
        classic_scanlog_core::papyrus::PapyrusAnalyzer::new(std::path::PathBuf::from(&log_path));
    let stats = analyzer.analyze_full().map_err(to_napi_err)?;
    Ok(JsPapyrusStats {
        dumps: stats.dumps as u32,
        stacks: stats.stacks as u32,
        warnings: stats.warnings as u32,
        errors: stats.errors as u32,
        lines_processed: stats.lines_processed as u32,
    })
}
