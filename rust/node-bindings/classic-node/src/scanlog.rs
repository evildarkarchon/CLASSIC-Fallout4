//! Scanlog bindings for classic-scanlog-core
//!
//! Exposes crash log analysis configuration and result types to JavaScript/TypeScript.
//! Full orchestration (process_log) is exposed as an async function that returns a Promise.

use classic_scanlog_core::orchestrator;

/// JavaScript-compatible analysis configuration.
///
/// This is a simplified view of `classic_scanlog_core::AnalysisConfig` exposing
/// the most commonly needed fields. Additional fields can be set via setter methods.
#[napi(object)]
pub struct JsAnalysisConfig {
    /// Game name (e.g., "Fallout4")
    pub game: String,
    /// VR mode enabled
    pub vr_mode: bool,
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

/// Create a new analysis configuration with defaults.
///
/// Returns a JavaScript object with the configuration fields.
/// Modify the returned object's properties before passing to analysis functions.
#[napi]
pub fn create_analysis_config(game: String, vr_mode: bool) -> JsAnalysisConfig {
    JsAnalysisConfig {
        game,
        vr_mode,
        crashgen_name: String::new(),
        xse_acronym: String::new(),
        classic_version: "CLASSIC".to_string(),
        fcx_mode: false,
        simplify_logs: false,
    }
}

/// Convert a JsAnalysisConfig to the core AnalysisConfig type.
///
/// This is an internal helper used when passing config to the orchestrator.
/// Not exported to JavaScript.
pub(crate) fn _js_config_to_core(config: &JsAnalysisConfig) -> orchestrator::AnalysisConfig {
    let mut core_config = orchestrator::AnalysisConfig::new(config.game.clone(), config.vr_mode);
    core_config.crashgen_name = config.crashgen_name.clone();
    core_config.xse_acronym = config.xse_acronym.clone();
    core_config.classic_version = config.classic_version.clone();
    core_config.fcx_mode = config.fcx_mode;
    core_config.simplify_logs = config.simplify_logs;
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
