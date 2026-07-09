//! Game file scanning bridge for CXX FFI.
//!
//! Bridges `classic_scangame_core` for Game Setup Intake, path detection,
//! and the BA2 / INI / ENB / TOML / Wrye / Integrity / Setup / Crashgen sub-domain checkers.

use classic_scangame_core::integrity::IntegrityConfig;
use classic_scangame_core::{
    GameSetupCheck, GameSetupIntake, GameSetupIntakeResult,
    game_setup_needs_path_detection as core_game_setup_needs_path_detection,
};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::str::FromStr;

use classic_scangame_core::crashgen_orchestrator::{
    CrashgenCheckOrchestrator, CrashgenReport as CoreCrashgenReport,
};
use classic_scangame_core::enb::EnbValidationResult as CoreEnbValidationResult;
use classic_scangame_core::ini::ConfigIssue as CoreIniConfigIssue;
use classic_scangame_core::integrity::{
    CheckType as CoreCheckType, GameIntegrityChecker,
    IntegrityCheckResult as CoreIntegrityCheckResult,
};
use classic_scangame_core::toml::{
    CrashgenChecker, TomlConfigIssue as CoreTomlConfigIssue,
    TomlIssueSeverity as CoreTomlIssueSeverity,
};
use classic_scangame_core::wrye::{
    WryeBashParser, WryeIssue as CoreWryeIssue, WryeSeverity as CoreWryeSeverity,
};
use classic_scangame_core::{
    BA2Scanner, EnbChecker, EnbConfigResult as CoreEnbConfigResult, EnbResult as CoreEnbResult,
    IniValidator, IssueSeverity as CoreIniIssueSeverity,
};
use classic_shared_core::GameId;

// ─────────────────────────────────────────────────────────────────────────────
// Game Setup Intake entry points
// ─────────────────────────────────────────────────────────────────────────────

fn run_game_setup_intake(
    game_id: &str,
    game_version: &str,
    game_root: &str,
    docs_path: &str,
    xse_log_path: &str,
) -> ffi::GameSetupIntakeDto {
    match execute_game_setup_intake(game_id, game_version, game_root, docs_path, xse_log_path) {
        Ok(result) => game_setup_result_to_dto(result),
        Err(message) => ffi::GameSetupIntakeDto {
            rendered_report: format!("Game Setup Intake failed: {message}\n"),
            status: "fatal_error".to_string(),
            has_errors: true,
            total_checks: 0,
            failed_checks: 0,
            action_count: 0,
            path_update_count: 0,
            game_root: String::new(),
            docs_root: String::new(),
        },
    }
}

fn game_setup_intake_checks(
    game_id: &str,
    game_version: &str,
    game_root: &str,
    docs_path: &str,
    xse_log_path: &str,
) -> Result<Vec<ffi::GameSetupCheckDto>, String> {
    execute_game_setup_intake(game_id, game_version, game_root, docs_path, xse_log_path).map(
        |result| {
            result
                .checks
                .into_iter()
                .map(game_setup_check_to_dto)
                .collect()
        },
    )
}

fn game_setup_needs_path_detection(
    game_path: &str,
    docs_path: &str,
) -> ffi::GameSetupPathDetectionNeeds {
    let gp = if game_path.is_empty() {
        None
    } else {
        Some(game_path)
    };
    let dp = if docs_path.is_empty() {
        None
    } else {
        Some(docs_path)
    };
    let (need_game, need_docs) = core_game_setup_needs_path_detection(gp, dp);
    ffi::GameSetupPathDetectionNeeds {
        needs_game_path: need_game,
        needs_docs_path: need_docs,
    }
}

fn execute_game_setup_intake(
    game_id: &str,
    game_version: &str,
    game_root: &str,
    docs_path: &str,
    xse_log_path: &str,
) -> Result<GameSetupIntakeResult, String> {
    let game_id = GameId::from_str(game_id).map_err(|error| error.to_string())?;
    let mut intake = GameSetupIntake::new(game_id, game_version);
    if !game_root.trim().is_empty() {
        intake = intake.with_game_root(PathBuf::from(game_root));
    }
    if !docs_path.trim().is_empty() {
        intake = intake.with_docs_root(PathBuf::from(docs_path));
    }
    if !xse_log_path.trim().is_empty() {
        intake = intake.with_xse_log_path(PathBuf::from(xse_log_path));
    }
    Ok(intake.run())
}

fn game_setup_result_to_dto(result: GameSetupIntakeResult) -> ffi::GameSetupIntakeDto {
    let has_errors = result.has_errors();
    let total_checks = result.total_checks() as u32;
    let failed_checks = result.failed_checks() as u32;
    ffi::GameSetupIntakeDto {
        rendered_report: result.rendered_report,
        status: result.status.as_str().to_string(),
        has_errors,
        total_checks,
        failed_checks,
        action_count: result.actions.len() as u32,
        path_update_count: result.path_updates.len() as u32,
        game_root: result
            .paths
            .game_root
            .map(|path| path.to_string_lossy().into_owned())
            .unwrap_or_default(),
        docs_root: result
            .paths
            .docs_root
            .map(|path| path.to_string_lossy().into_owned())
            .unwrap_or_default(),
    }
}

fn game_setup_check_to_dto(check: GameSetupCheck) -> ffi::GameSetupCheckDto {
    ffi::GameSetupCheckDto {
        kind: check.kind.as_str().to_string(),
        state: check.state.as_str().to_string(),
        message: check.message,
        details: check.details.join("\n"),
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// BA2 sub-domain — REAL BA2Scanner API (Codex HIGH correction)
// ─────────────────────────────────────────────────────────────────────────────

/// Construct a BA2Scanner and run scan_archive; returns None on any error
/// (file not found, unsupported platform, parse error).
fn run_ba2_scan(path_str: &str) -> Option<classic_scangame_core::ba2::BA2Issues> {
    if path_str.is_empty() {
        return None;
    }
    let scanner = BA2Scanner::new();
    scanner.scan_archive(Path::new(path_str)).ok()
}

/// Scan a single BA2 archive and return a flat summary DTO (counts only).
///
/// Returns all-zero / has_issues=false on missing archive or scan error
/// (fail-soft — C++ callers do not need to handle Rust Results).
fn ba2_scan_archive_summary(archive_path: &str) -> ffi::Ba2IssuesSummaryDto {
    let issues = match run_ba2_scan(archive_path) {
        Some(i) => i,
        None => {
            return ffi::Ba2IssuesSummaryDto {
                tex_dim_count: 0,
                tex_fmt_count: 0,
                snd_fmt_count: 0,
                xse_file_count: 0,
                total: 0,
                has_issues: false,
            };
        }
    };
    let tex = issues.tex_dims.len() as u32;
    let fmt = issues.tex_frmt.len() as u32;
    let snd = issues.snd_frmt.len() as u32;
    let xse = issues.xse_file.len() as u32;
    let total = tex + fmt + snd + xse;
    ffi::Ba2IssuesSummaryDto {
        tex_dim_count: tex,
        tex_fmt_count: fmt,
        snd_fmt_count: snd,
        xse_file_count: xse,
        total,
        has_issues: total > 0,
    }
}

/// Return per-archive texture-dimension issue strings (empty Vec on error).
fn ba2_get_tex_dims_for_archive(archive_path: &str) -> Vec<String> {
    run_ba2_scan(archive_path)
        .map(|i| i.tex_dims)
        .unwrap_or_default()
}

/// Return per-archive texture-format issue strings (empty Vec on error).
fn ba2_get_tex_frmt_for_archive(archive_path: &str) -> Vec<String> {
    run_ba2_scan(archive_path)
        .map(|i| i.tex_frmt)
        .unwrap_or_default()
}

/// Return per-archive sound-format issue strings (empty Vec on error).
fn ba2_get_snd_frmt_for_archive(archive_path: &str) -> Vec<String> {
    run_ba2_scan(archive_path)
        .map(|i| i.snd_frmt)
        .unwrap_or_default()
}

/// Return per-archive XSE-file issue strings (empty Vec on error).
fn ba2_get_xse_files_for_archive(archive_path: &str) -> Vec<String> {
    run_ba2_scan(archive_path)
        .map(|i| i.xse_file)
        .unwrap_or_default()
}

// ─────────────────────────────────────────────────────────────────────────────
// INI sub-domain — REAL IniValidator API + REAL ConfigIssue field set
// (Codex HIGH correction)
// ─────────────────────────────────────────────────────────────────────────────

fn map_ini_severity(s: CoreIniIssueSeverity) -> ffi::IssueSeverity {
    match s {
        CoreIniIssueSeverity::Error => ffi::IssueSeverity::Error,
        CoreIniIssueSeverity::Warning => ffi::IssueSeverity::Warning,
        CoreIniIssueSeverity::Info => ffi::IssueSeverity::Info,
    }
}

/// Convert a REAL ConfigIssue (classic-scangame-core/src/ini.rs:55-78) to the
/// bridge DTO, mapping PathBuf → String at the bridge boundary.
fn convert_ini_issue(issue: CoreIniConfigIssue) -> ffi::IniConfigIssueDto {
    ffi::IniConfigIssueDto {
        file_path: issue.file_path.to_string_lossy().into_owned(),
        section: issue.section,
        setting: issue.setting,
        current_value: issue.current_value,
        recommended_value: issue.recommended_value,
        description: issue.description,
        severity: map_ini_severity(issue.severity),
    }
}

/// Run the full INI validation for a game root directory and return the
/// formatted report text (same text the Rust CLI would show).
///
/// Returns Err if game_root is empty or the validator fails to scan config files.
fn ini_validator_validate_inis(game_name: &str, game_root: &str) -> Result<String, String> {
    if game_root.is_empty() {
        return Err("ini_validator_validate_inis: empty game_root".to_string());
    }
    let mut validator = IniValidator::new(game_name);
    validator
        .validate_inis(Path::new(game_root))
        .map_err(|e| e.to_string())
}

/// Scan a game root for INI config files and return all structured issues.
///
/// Returns empty Vec on empty game_root or if no config files are found.
fn ini_validator_detect_all_issues_for_root(
    game_name: &str,
    game_root: &str,
) -> Vec<ffi::IniConfigIssueDto> {
    if game_root.is_empty() {
        return Vec::new();
    }
    let validator = IniValidator::new(game_name);
    let config_files: HashMap<String, PathBuf> =
        match validator.scan_config_files(Path::new(game_root)) {
            Ok(map) => map,
            Err(_) => return Vec::new(),
        };
    validator
        .detect_all_issues(&config_files)
        .into_iter()
        .map(convert_ini_issue)
        .collect()
}

// ─────────────────────────────────────────────────────────────────────────────
// ENB sub-domain — REAL EnbChecker API (Codex HIGH correction)
// ─────────────────────────────────────────────────────────────────────────────

fn map_enb_result(r: CoreEnbResult) -> ffi::EnbResult {
    // REAL variants: Present, Partial, NotInstalled
    match r {
        CoreEnbResult::Present => ffi::EnbResult::Present,
        CoreEnbResult::Partial => ffi::EnbResult::Partial,
        CoreEnbResult::NotInstalled => ffi::EnbResult::NotInstalled,
    }
}

fn map_enb_config_result(r: CoreEnbConfigResult) -> ffi::EnbConfigResult {
    // REAL variants: Valid, NotFound, Unreadable
    match r {
        CoreEnbConfigResult::Valid => ffi::EnbConfigResult::Valid,
        CoreEnbConfigResult::NotFound => ffi::EnbConfigResult::NotFound,
        CoreEnbConfigResult::Unreadable => ffi::EnbConfigResult::Unreadable,
    }
}

/// Run ENB validation for a game directory, returning a flat DTO with the
/// REAL field set (binaries + config; no fictional errors Vec).
///
/// Falls back to "." if game_path is empty (checker treats it as cwd).
fn enb_checker_validate(game_path: &str) -> ffi::EnbValidationResultDto {
    let path_arg = if game_path.is_empty() { "." } else { game_path };
    let checker = EnbChecker::new(path_arg);
    let result: CoreEnbValidationResult = checker.validate();
    // REAL field set: binaries + config (NO errors Vec — Codex HIGH correction)
    ffi::EnbValidationResultDto {
        binaries: map_enb_result(result.binaries),
        config: map_enb_config_result(result.config),
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// TOML sub-domain — REAL CrashgenChecker API (Codex HIGH correction)
// ─────────────────────────────────────────────────────────────────────────────

fn map_toml_severity(s: CoreTomlIssueSeverity) -> ffi::TomlIssueSeverity {
    match s {
        CoreTomlIssueSeverity::Info => ffi::TomlIssueSeverity::Info,
        CoreTomlIssueSeverity::Warning => ffi::TomlIssueSeverity::Warning,
        CoreTomlIssueSeverity::Error => ffi::TomlIssueSeverity::Error,
    }
}

fn convert_toml_issue(i: CoreTomlConfigIssue) -> ffi::TomlConfigIssueDto {
    // REAL field set per classic-scangame-core/src/toml.rs:61-82
    ffi::TomlConfigIssueDto {
        file_path: i.file_path.to_string_lossy().into_owned(),
        section: i.section,
        setting: i.setting,
        current_value: i.current_value,
        recommended_value: i.recommended_value,
        description: i.description,
        severity: map_toml_severity(i.severity),
    }
}

fn run_crashgen_checker(
    plugins_path: &str,
    crashgen_name: &str,
) -> Option<(String, Vec<CoreTomlConfigIssue>)> {
    if plugins_path.is_empty() {
        return None;
    }
    let mut checker = CrashgenChecker::new(Path::new(plugins_path), crashgen_name);
    checker.check().ok()
}

/// Run CrashgenChecker and return a summary DTO (report_text + issue_count).
///
/// Returns empty DTO on empty plugins_path or check error (fail-soft).
fn crashgen_checker_check(plugins_path: &str, crashgen_name: &str) -> ffi::CrashgenCheckResultDto {
    match run_crashgen_checker(plugins_path, crashgen_name) {
        Some((text, issues)) => ffi::CrashgenCheckResultDto {
            report_text: text,
            issue_count: issues.len() as u32,
        },
        None => ffi::CrashgenCheckResultDto {
            report_text: String::new(),
            issue_count: 0,
        },
    }
}

/// Return structured TOML issues from CrashgenChecker (empty Vec on error).
fn crashgen_checker_get_issues(
    plugins_path: &str,
    crashgen_name: &str,
) -> Vec<ffi::TomlConfigIssueDto> {
    run_crashgen_checker(plugins_path, crashgen_name)
        .map(|(_, issues)| issues.into_iter().map(convert_toml_issue).collect())
        .unwrap_or_default()
}

// ─────────────────────────────────────────────────────────────────────────────
// Wrye sub-domain — REAL WryeBashParser API + ROW-oriented flattening
// (Codex HIGH correction + Pitfall 6 Vec<StructWithVec> elimination)
// REAL WryeSeverity has 3 variants: Info, Warning, Error (no Note)
// ─────────────────────────────────────────────────────────────────────────────

fn map_wrye_severity(s: CoreWryeSeverity) -> ffi::WryeSeverity {
    // REAL variants per classic-scangame-core/src/wrye.rs:42-49
    match s {
        CoreWryeSeverity::Error => ffi::WryeSeverity::Error,
        CoreWryeSeverity::Warning => ffi::WryeSeverity::Warning,
        CoreWryeSeverity::Info => ffi::WryeSeverity::Info,
    }
}

/// Parse a Wrye Bash ModChecker HTML report and return ROW-oriented results.
///
/// Each `(WryeIssue, plugin)` pair becomes one `WryeIssueRowDto` row.
/// This flattens the embedded `plugins: Vec<String>` field (Pitfall 6 fix).
/// Issues with zero plugins emit a single row with an empty plugin string.
///
/// # Arguments
/// * `html_content` — raw HTML string from ModChecker.html
/// * `warnings_keys` / `warnings_values` — parallel slices forming the wrye_warnings map
///   (must be same length; returns empty Vec on mismatch)
fn wrye_parse_html_rows(
    html_content: &str,
    warnings_keys: &[String],
    warnings_values: &[String],
) -> Vec<ffi::WryeIssueRowDto> {
    // Build the HashMap input from parallel string slices.
    if warnings_keys.len() != warnings_values.len() {
        return Vec::new();
    }
    let warnings: HashMap<String, String> = warnings_keys
        .iter()
        .cloned()
        .zip(warnings_values.iter().cloned())
        .collect();

    let parser = WryeBashParser::new(warnings);
    let issues: Vec<CoreWryeIssue> = parser.parse(html_content);

    // Pitfall 6 elimination: flatten each (issue, plugin) into a row.
    // The row carries a stable issue_index so C++ callers can group rows
    // back into issues if needed.
    let mut rows = Vec::new();
    for (issue_index, issue) in issues.into_iter().enumerate() {
        let row_index_u32 = issue_index as u32;
        let warning_text = issue.warning_message.clone().unwrap_or_default();
        let has_warning = issue.warning_message.is_some();
        let severity = map_wrye_severity(issue.severity);
        if issue.plugins.is_empty() {
            // Issue with no plugins — emit a single row with empty plugin string
            rows.push(ffi::WryeIssueRowDto {
                issue_index: row_index_u32,
                section_title: issue.section_title.clone(),
                plugin: String::new(),
                warning_message_or_empty: warning_text,
                has_warning_message: has_warning,
                severity,
            });
        } else {
            for plugin in &issue.plugins {
                rows.push(ffi::WryeIssueRowDto {
                    issue_index: row_index_u32,
                    section_title: issue.section_title.clone(),
                    plugin: plugin.clone(),
                    warning_message_or_empty: warning_text.clone(),
                    has_warning_message: has_warning,
                    severity,
                });
            }
        }
    }
    rows
}

// ─────────────────────────────────────────────────────────────────────────────
// Integrity sub-domain — REAL GameIntegrityChecker API + REAL CheckType
// (Codex HIGH correction: is_valid NOT passed; 2 variants not 5)
// ─────────────────────────────────────────────────────────────────────────────

fn map_check_type(c: CoreCheckType) -> ffi::CheckType {
    // REAL: only 2 variants (Codex HIGH correction)
    match c {
        CoreCheckType::ExecutableVersion => ffi::CheckType::ExecutableVersion,
        CoreCheckType::InstallationLocation => ffi::CheckType::InstallationLocation,
    }
}

/// Run all integrity checks and return a flat Vec of result DTOs.
///
/// Constructs IntegrityConfig internally with no steam_ini_path or root_warn.
/// Returns empty Vec on empty game_exe_path or root_name.
fn integrity_run_all_checks(
    game_exe_path: &str,
    valid_hashes: &[String],
    root_name: &str,
) -> Vec<ffi::IntegrityCheckResultDto> {
    if game_exe_path.is_empty() || root_name.is_empty() {
        return Vec::new();
    }
    let config = IntegrityConfig::new(
        PathBuf::from(game_exe_path),
        valid_hashes.to_vec(),
        root_name.to_string(),
    );
    let checker = GameIntegrityChecker::new(config);
    checker
        .run_all_checks()
        .unwrap_or_default()
        .into_iter()
        .map(|r: CoreIntegrityCheckResult| ffi::IntegrityCheckResultDto {
            is_valid: r.is_valid, // REAL field name (NOT `passed`) — Codex HIGH correction
            message: r.message,
            check_type: map_check_type(r.check_type),
        })
        .collect()
}

// ─────────────────────────────────────────────────────────────────────────────
// Setup orchestration now flows through Game Setup Intake above.
// ─────────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
// CrashgenOrchestrator — REAL CrashgenCheckOrchestrator + REAL CrashgenReport
// Two Vec fields (issues, installed_plugins) exposed via separate getters
// (Pitfall 6 — no nested Vec in the summary DTO)
// ─────────────────────────────────────────────────────────────────────────────

fn run_crashgen_orchestrator(
    plugins_path: &str,
    crashgen_name: &str,
) -> Option<CoreCrashgenReport> {
    if plugins_path.is_empty() {
        return None;
    }
    CrashgenCheckOrchestrator::check(Path::new(plugins_path), crashgen_name).ok()
}

/// Run the CrashgenCheckOrchestrator and return a flat summary DTO.
///
/// The two Vec fields (issues, installed_plugins) are accessible via separate
/// getter fns to avoid Pitfall 6 (nested Vec in CXX struct).
fn crashgen_orchestrator_check_summary(
    plugins_path: &str,
    crashgen_name: &str,
) -> ffi::CrashgenReportSummaryDto {
    match run_crashgen_orchestrator(plugins_path, crashgen_name) {
        Some(report) => {
            let config_path_str = report
                .config_path
                .as_ref()
                .map(|p| p.to_string_lossy().into_owned())
                .unwrap_or_default();
            let has_config_path = report.config_path.is_some();
            ffi::CrashgenReportSummaryDto {
                message: report.message,
                crashgen_name: report.crashgen_name,
                config_path_or_empty: config_path_str,
                has_config_path,
                issue_count: report.issues.len() as u32,
                installed_plugin_count: report.installed_plugins.len() as u32,
            }
        }
        None => ffi::CrashgenReportSummaryDto {
            message: String::new(),
            crashgen_name: crashgen_name.to_string(),
            config_path_or_empty: String::new(),
            has_config_path: false,
            issue_count: 0,
            installed_plugin_count: 0,
        },
    }
}

/// Return structured TOML issues from the CrashgenCheckOrchestrator (empty Vec on error).
fn crashgen_orchestrator_get_issues(
    plugins_path: &str,
    crashgen_name: &str,
) -> Vec<ffi::TomlConfigIssueDto> {
    run_crashgen_orchestrator(plugins_path, crashgen_name)
        .map(|r| r.issues.into_iter().map(convert_toml_issue).collect())
        .unwrap_or_default()
}

/// Return installed plugin names from the CrashgenCheckOrchestrator (empty Vec on error).
fn crashgen_orchestrator_get_installed_plugins(
    plugins_path: &str,
    crashgen_name: &str,
) -> Vec<String> {
    run_crashgen_orchestrator(plugins_path, crashgen_name)
        .map(|r| r.installed_plugins)
        .unwrap_or_default()
}

// ─────────────────────────────────────────────────────────────────────────────
// CXX bridge — namespace classic::scangame
// ─────────────────────────────────────────────────────────────────────────────

#[cxx::bridge(namespace = "classic::scangame")]
mod ffi {
    // ── Game Setup Intake DTOs ───────────────────────────────────────────────
    struct GameSetupIntakeDto {
        rendered_report: String,
        status: String,
        has_errors: bool,
        total_checks: u32,
        failed_checks: u32,
        action_count: u32,
        path_update_count: u32,
        game_root: String,
        docs_root: String,
    }

    struct GameSetupCheckDto {
        kind: String,
        state: String,
        message: String,
        details: String,
    }

    struct GameSetupPathDetectionNeeds {
        needs_game_path: bool,
        needs_docs_path: bool,
    }

    // ── New shared enums (D-04/D-07 — repr(u8), REAL variants) ─────────────

    /// INI configuration issue severity (mirrors classic_scangame_core::ini::IssueSeverity).
    #[repr(u8)]
    enum IssueSeverity {
        Error = 0,
        Warning = 1,
        Info = 2,
    }

    /// ENB binary presence (mirrors classic_scangame_core::enb::EnbResult).
    /// REAL variants: Present / Partial / NotInstalled (Codex HIGH correction).
    #[repr(u8)]
    enum EnbResult {
        Present = 0,
        Partial = 1,
        NotInstalled = 2,
    }

    /// ENB config file status (mirrors classic_scangame_core::enb::EnbConfigResult).
    /// REAL variants: Valid / NotFound / Unreadable (Codex HIGH correction).
    #[repr(u8)]
    enum EnbConfigResult {
        Valid = 0,
        NotFound = 1,
        Unreadable = 2,
    }

    // ── New flat DTOs (all Pitfall 6 CLEAR — no Vec<StructWithVec>) ─────────

    /// BA2 scan summary: per-category issue counts (flat — no nested Vec).
    struct Ba2IssuesSummaryDto {
        tex_dim_count: u32,
        tex_fmt_count: u32,
        snd_fmt_count: u32,
        xse_file_count: u32,
        total: u32,
        has_issues: bool,
    }

    /// INI configuration issue with REAL ConfigIssue field set
    /// (file_path, section, setting, current_value, recommended_value,
    ///  description, severity — Codex HIGH correction).
    struct IniConfigIssueDto {
        file_path: String,
        section: String,
        setting: String,
        current_value: String,
        recommended_value: String,
        description: String,
        severity: IssueSeverity,
    }

    /// ENB validation result with REAL field set: binaries + config.
    /// NO errors Vec (Codex HIGH correction).
    struct EnbValidationResultDto {
        binaries: EnbResult,
        config: EnbConfigResult,
    }

    // ── New shared enums for plan 02-06 (D-04/D-07 — repr(u8)) ─────────────

    /// TOML configuration issue severity (mirrors classic_scangame_core::toml::TomlIssueSeverity).
    #[repr(u8)]
    enum TomlIssueSeverity {
        Info = 0,
        Warning = 1,
        Error = 2,
    }

    /// Wrye Bash issue severity (mirrors classic_scangame_core::wrye::WryeSeverity).
    /// REAL: 3 variants only — Info, Warning, Error (no Note).
    #[repr(u8)]
    enum WryeSeverity {
        Info = 0,
        Warning = 1,
        Error = 2,
    }

    /// Game integrity check type (mirrors classic_scangame_core::integrity::CheckType).
    /// REAL: only 2 variants — ExecutableVersion + InstallationLocation (Codex HIGH correction).
    #[repr(u8)]
    enum CheckType {
        ExecutableVersion = 0,
        InstallationLocation = 1,
    }

    // ── New flat DTOs for plan 02-06 (all Pitfall 6 CLEAR — no Vec<StructWithVec>) ──

    /// TOML config issue with REAL TomlConfigIssue field set
    /// (file_path, section, setting, current_value, recommended_value, description, severity —
    ///  Codex HIGH correction).
    struct TomlConfigIssueDto {
        file_path: String,
        section: String,
        setting: String,
        current_value: String,
        recommended_value: String,
        description: String,
        severity: TomlIssueSeverity,
    }

    /// Wrye Bash row-oriented DTO (Pitfall 6 fix — flattens plugins: Vec<String>).
    /// Each (issue, plugin) pair becomes one row; issue_index lets C++ callers
    /// group rows back into issues if needed.
    struct WryeIssueRowDto {
        issue_index: u32,
        section_title: String,
        plugin: String,
        warning_message_or_empty: String,
        has_warning_message: bool,
        severity: WryeSeverity,
    }

    /// Integrity check result with REAL field set (Codex HIGH correction).
    /// NOTE: `is_valid: bool` (NOT `passed: bool`).
    struct IntegrityCheckResultDto {
        is_valid: bool,
        message: String,
        check_type: CheckType,
    }

    /// CrashgenChecker.check() summary — (report_text, issue_count).
    /// Full issue list accessible via crashgen_checker_get_issues (Pitfall 6 separation).
    struct CrashgenCheckResultDto {
        report_text: String,
        issue_count: u32,
    }

    /// CrashgenReport summary DTO — REAL CrashgenReport field set.
    /// The two Vec fields (issues, installed_plugins) are exposed via separate getters
    /// to avoid Pitfall 6 (no nested Vec in this struct).
    struct CrashgenReportSummaryDto {
        message: String,
        crashgen_name: String,
        config_path_or_empty: String,
        has_config_path: bool,
        issue_count: u32,
        installed_plugin_count: u32,
    }

    extern "Rust" {
        // ── Game Setup Intake ───────────────────────────────────────────────
        fn run_game_setup_intake(
            game_id: &str,
            game_version: &str,
            game_root: &str,
            docs_path: &str,
            xse_log_path: &str,
        ) -> GameSetupIntakeDto;

        fn game_setup_intake_checks(
            game_id: &str,
            game_version: &str,
            game_root: &str,
            docs_path: &str,
            xse_log_path: &str,
        ) -> Result<Vec<GameSetupCheckDto>>;

        fn game_setup_needs_path_detection(
            game_path: &str,
            docs_path: &str,
        ) -> GameSetupPathDetectionNeeds;

        // ── BA2 sub-domain (REAL BA2Scanner behind the scenes) ───────────────
        fn ba2_scan_archive_summary(archive_path: &str) -> Ba2IssuesSummaryDto;
        fn ba2_get_tex_dims_for_archive(archive_path: &str) -> Vec<String>;
        fn ba2_get_tex_frmt_for_archive(archive_path: &str) -> Vec<String>;
        fn ba2_get_snd_frmt_for_archive(archive_path: &str) -> Vec<String>;
        fn ba2_get_xse_files_for_archive(archive_path: &str) -> Vec<String>;

        // ── INI sub-domain (REAL IniValidator behind the scenes) ─────────────
        fn ini_validator_validate_inis(game_name: &str, game_root: &str) -> Result<String>;
        fn ini_validator_detect_all_issues_for_root(
            game_name: &str,
            game_root: &str,
        ) -> Vec<IniConfigIssueDto>;

        // ── ENB sub-domain (REAL EnbChecker behind the scenes) ───────────────
        fn enb_checker_validate(game_path: &str) -> EnbValidationResultDto;

        // ── TOML sub-domain (REAL CrashgenChecker — Codex HIGH correction) ───
        fn crashgen_checker_check(
            plugins_path: &str,
            crashgen_name: &str,
        ) -> CrashgenCheckResultDto;
        fn crashgen_checker_get_issues(
            plugins_path: &str,
            crashgen_name: &str,
        ) -> Vec<TomlConfigIssueDto>;

        // ── Wrye sub-domain (REAL WryeBashParser — row-oriented Pitfall 6 fix) ─
        fn wrye_parse_html_rows(
            html_content: &str,
            warnings_keys: &[String],
            warnings_values: &[String],
        ) -> Vec<WryeIssueRowDto>;

        // ── Integrity sub-domain (REAL GameIntegrityChecker) ─────────────────
        fn integrity_run_all_checks(
            game_exe_path: &str,
            valid_hashes: &[String],
            root_name: &str,
        ) -> Vec<IntegrityCheckResultDto>;

        // ── CrashgenOrchestrator (REAL CrashgenCheckOrchestrator) ─────────────
        fn crashgen_orchestrator_check_summary(
            plugins_path: &str,
            crashgen_name: &str,
        ) -> CrashgenReportSummaryDto;
        fn crashgen_orchestrator_get_issues(
            plugins_path: &str,
            crashgen_name: &str,
        ) -> Vec<TomlConfigIssueDto>;
        fn crashgen_orchestrator_get_installed_plugins(
            plugins_path: &str,
            crashgen_name: &str,
        ) -> Vec<String>;
    }
}

#[cfg(test)]
#[path = "scangame_tests.rs"]
mod tests;
