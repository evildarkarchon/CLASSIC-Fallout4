//! Game file scanning bridge for CXX FFI.
//!
//! Bridges `classic_scangame_core` for setup checks, path detection,
//! and the BA2 / INI / ENB sub-domain checkers.

use classic_scangame_core::integrity::IntegrityConfig;
use classic_scangame_core::setup::{
    SetupCheckConfig, needs_path_detection as core_needs_path_detection, run_combined_checks,
};
use std::collections::HashMap;
use std::path::{Path, PathBuf};

use classic_scangame_core::{
    BA2Scanner,
    EnbChecker,
    EnbResult as CoreEnbResult,
    EnbConfigResult as CoreEnbConfigResult,
    IniValidator,
    IssueSeverity as CoreIniIssueSeverity,
};
use classic_scangame_core::ini::ConfigIssue as CoreIniConfigIssue;
use classic_scangame_core::enb::EnbValidationResult as CoreEnbValidationResult;

// ─────────────────────────────────────────────────────────────────────────────
// EXISTING entry points (D-08 — UNCHANGED)
// ─────────────────────────────────────────────────────────────────────────────

fn run_setup_checks(
    game_exe_path: &str,
    _game_root: &str,
    docs_path: &str,
    game_name: &str,
) -> ffi::SetupCheckResult {
    let integrity = IntegrityConfig::new(
        PathBuf::from(game_exe_path),
        Vec::new(),
        game_name.to_string(),
    );
    let config = SetupCheckConfig {
        integrity,
        game_name: game_name.to_string(),
        docs_path: if docs_path.is_empty() {
            None
        } else {
            Some(docs_path.to_string())
        },
        xse_hashes: Vec::new(),
    };
    let results = run_combined_checks(&config);
    ffi::SetupCheckResult {
        combined_output: results.combined(),
        has_errors: results.has_errors(),
        total_checks: results.total_checks() as u32,
    }
}

fn needs_path_detection(game_path: &str, docs_path: &str) -> ffi::PathDetectionNeeds {
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
    let (need_game, need_docs) = core_needs_path_detection(gp, dp);
    ffi::PathDetectionNeeds {
        needs_game_path: need_game,
        needs_docs_path: need_docs,
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
    let path_arg = if game_path.is_empty() {
        "."
    } else {
        game_path
    };
    let checker = EnbChecker::new(path_arg);
    let result: CoreEnbValidationResult = checker.validate();
    // REAL field set: binaries + config (NO errors Vec — Codex HIGH correction)
    ffi::EnbValidationResultDto {
        binaries: map_enb_result(result.binaries),
        config: map_enb_config_result(result.config),
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// CXX bridge — namespace classic::scangame
// ─────────────────────────────────────────────────────────────────────────────

#[cxx::bridge(namespace = "classic::scangame")]
mod ffi {
    // ── Existing shared structs (D-08 — KEEP UNCHANGED) ─────────────────────
    struct SetupCheckResult {
        combined_output: String,
        has_errors: bool,
        total_checks: u32,
    }

    struct PathDetectionNeeds {
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

    extern "Rust" {
        // ── Existing fns (D-08 — UNCHANGED) ─────────────────────────────────
        fn run_setup_checks(
            game_exe_path: &str,
            game_root: &str,
            docs_path: &str,
            game_name: &str,
        ) -> SetupCheckResult;

        fn needs_path_detection(game_path: &str, docs_path: &str) -> PathDetectionNeeds;

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
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    // ── Existing tests (D-08 — PRESERVE) ─────────────────────────────────────

    #[test]
    fn test_run_setup_checks_nonexistent() {
        let result = run_setup_checks("nonexistent_exe.exe", "nonexistent_root", "", "Fallout4");
        // Should complete without panic
        let _ = result.combined_output;
    }

    #[test]
    fn test_needs_path_detection_empty() {
        let result = needs_path_detection("", "");
        assert!(result.needs_game_path);
        assert!(result.needs_docs_path);
    }

    #[test]
    fn test_needs_path_detection_with_paths() {
        let result = needs_path_detection("C:\\Games\\Fallout4", "C:\\Users\\Docs");
        assert!(!result.needs_game_path);
        assert!(!result.needs_docs_path);
    }

    // ── BA2 sub-domain tests ──────────────────────────────────────────────────

    #[test]
    fn test_ba2_scan_archive_summary_nonexistent_returns_no_issues() {
        let r = ba2_scan_archive_summary("nonexistent.ba2");
        assert!(!r.has_issues);
        assert_eq!(r.total, 0);
        assert_eq!(r.tex_dim_count, 0);
        assert_eq!(r.tex_fmt_count, 0);
        assert_eq!(r.snd_fmt_count, 0);
        assert_eq!(r.xse_file_count, 0);
    }

    #[test]
    fn test_ba2_get_categories_empty_for_nonexistent() {
        assert!(ba2_get_tex_dims_for_archive("nonexistent.ba2").is_empty());
        assert!(ba2_get_tex_frmt_for_archive("nonexistent.ba2").is_empty());
        assert!(ba2_get_snd_frmt_for_archive("nonexistent.ba2").is_empty());
        assert!(ba2_get_xse_files_for_archive("nonexistent.ba2").is_empty());
    }

    // ── INI sub-domain tests ──────────────────────────────────────────────────

    #[test]
    fn test_ini_validator_validate_inis_empty_root_errors() {
        assert!(ini_validator_validate_inis("Fallout4", "").is_err());
    }

    #[test]
    fn test_ini_validator_detect_all_issues_empty_root_returns_empty() {
        assert!(ini_validator_detect_all_issues_for_root("Fallout4", "").is_empty());
    }

    #[test]
    fn test_ini_validator_validate_inis_nonexistent_dir() {
        // Real IniValidator::scan_config_files on a missing dir returns Err or empty map;
        // either way the bridge must not panic.
        let result = ini_validator_validate_inis("Fallout4", "nonexistent\\dir");
        // Accept Ok (empty report) or Err (scan failure) — both are valid
        match result {
            Ok(report) => {
                // report may be empty or contain file-not-found notices
                let _ = report;
            }
            Err(msg) => {
                assert!(!msg.is_empty());
            }
        }
    }

    #[test]
    fn test_ini_validator_detect_all_issues_nonexistent_dir_returns_empty() {
        // scan_config_files returns Err on missing dir → bridge returns empty Vec
        let issues = ini_validator_detect_all_issues_for_root("Fallout4", "nonexistent\\dir");
        assert!(issues.is_empty());
    }

    // ── ENB sub-domain tests (REAL variant names — Codex HIGH correction) ────

    #[test]
    fn test_enb_checker_validate_empty_dir_real_variants() {
        // Empty temp dir — no ENB files at all
        let temp_dir = TempDir::new().unwrap();
        let r = enb_checker_validate(&temp_dir.path().to_string_lossy());
        // REAL variants: NotInstalled, NotFound (Codex HIGH correction)
        assert!(
            matches!(r.binaries, ffi::EnbResult::NotInstalled),
            "expected NotInstalled variant"
        );
        assert!(
            matches!(r.config, ffi::EnbConfigResult::NotFound),
            "expected NotFound variant"
        );
    }

    #[test]
    fn test_enb_checker_validate_present_real_variants() {
        // Mirrors classic-scangame-core/src/enb.rs::test_enb_present
        let temp_dir = TempDir::new().unwrap();
        fs::write(temp_dir.path().join("d3d11.dll"), b"x").unwrap();
        fs::write(temp_dir.path().join("d3dcompiler_46e.dll"), b"x").unwrap();
        fs::write(temp_dir.path().join("enbseries.ini"), b"[ENB]\n").unwrap();
        let r = enb_checker_validate(&temp_dir.path().to_string_lossy());
        // REAL variants: Present, Valid (Codex HIGH correction)
        assert!(
            matches!(r.binaries, ffi::EnbResult::Present),
            "expected Present variant"
        );
        assert!(
            matches!(r.config, ffi::EnbConfigResult::Valid),
            "expected Valid variant"
        );
    }

    #[test]
    fn test_enb_checker_validate_partial_real_variant() {
        // Only d3d11.dll — missing d3dcompiler → Partial
        let temp_dir = TempDir::new().unwrap();
        fs::write(temp_dir.path().join("d3d11.dll"), b"x").unwrap();
        let r = enb_checker_validate(&temp_dir.path().to_string_lossy());
        // REAL variant: Partial (Codex HIGH correction)
        assert!(
            matches!(r.binaries, ffi::EnbResult::Partial),
            "expected Partial variant"
        );
    }

    #[test]
    fn test_enb_checker_validate_present_no_config() {
        // Both binaries present, no enbseries.ini
        let temp_dir = TempDir::new().unwrap();
        fs::write(temp_dir.path().join("d3d11.dll"), b"x").unwrap();
        fs::write(temp_dir.path().join("d3dcompiler_46e.dll"), b"x").unwrap();
        let r = enb_checker_validate(&temp_dir.path().to_string_lossy());
        assert!(matches!(r.binaries, ffi::EnbResult::Present));
        assert!(matches!(r.config, ffi::EnbConfigResult::NotFound));
    }
}
