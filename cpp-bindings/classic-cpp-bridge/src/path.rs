//! Path detection and validation bridge for CXX FFI.
//!
//! Bridges `classic-path-core` helpers so the Qt GUI can reuse the same
//! automatic game/docs detection logic, path validation, INI checking,
//! and backup management as other implementations.
//!
//! # Architecture
//!
//! This module provides the `classic::path` C++ namespace.  All bridge
//! functions accept plain `&str` arguments (never `&Path`) because CXX
//! cannot share `std::path::Path` across the FFI boundary.  Each wrapper
//! converts to `Path::new(s)` only after the empty-string fast-path check
//! (Bridge String/Path Contract).
//!
//! # CXXS-08 surface
//!
//! - Validator helpers: `path_validate_exists`, `path_validate_is_directory`,
//!   `path_validate_is_file`, `path_validate_required_files`,
//!   `path_validate_custom_scan`
//! - Predicate helpers: `is_valid_path`, `is_restricted_path`
//! - Backward-compat aliases: `validate_path`, `check_restricted_path`
//! - INI checker (REAL surface): `docs_checker_validate_ini_file`,
//!   `docs_checker_run_all_checks`
//! - Backup helpers: `backup_create_timestamped`, `backup_list_existing`
//! - XSE log + game-path: `parse_xse_log`, `find_game_path`
//! - Fallout4-specific detection: `detect_fallout4_game_path`,
//!   `resolve_fallout4_exe_name`, `detect_fallout4_docs_path`

use classic_path_core::{
    BackupManager, DocsPathFinder, DocumentsChecker, GamePathFinder,
    IniCheckResult as CoreIniCheckResult, is_restricted_path as core_is_restricted_path,
    is_valid_path as core_is_valid_path, parse_xse_log as core_parse_xse_log,
    validate_custom_scan_path as core_validate_custom_scan_path,
    validate_is_directory as core_validate_is_directory, validate_is_file as core_validate_is_file,
    validate_path_exists as core_validate_path_exists,
    validate_required_files as core_validate_required_files,
};
use classic_version_registry_core::Fallout4Version;
use std::path::Path;

// ─────────────────────────────────────────────────────────────────────────────
// Fallout4-specific detection helpers (existing surface — preserved)
// ─────────────────────────────────────────────────────────────────────────────

fn resolve_fallout4_version_info(
    selected_game_version: &str,
) -> Option<classic_version_registry_core::VersionInfo> {
    classic_config_core::resolve_registry_version_info("Fallout4", selected_game_version)
}

fn resolve_fallout4_exe_name(selected_game_version: &str) -> String {
    resolve_fallout4_version_info(selected_game_version)
        .map(|info| format!("{}.exe", info.docs_name))
        .unwrap_or_else(|| "Fallout4.exe".to_string())
}

fn detect_fallout4_game_path(cached_path: &str, selected_game_version: &str) -> String {
    let version_info = resolve_fallout4_version_info(selected_game_version);
    let game_exe = version_info
        .as_ref()
        .map(|info| format!("{}.exe", info.docs_name))
        .unwrap_or_else(|| "Fallout4.exe".to_string());
    let finder = GamePathFinder::new(
        &game_exe,
        None::<&str>,
        "Fallout4",
        version_info.as_ref().is_some_and(|info| info.is_vr),
    );

    let cached = if cached_path.is_empty() {
        None
    } else {
        Some(Path::new(cached_path))
    };

    finder
        .find_game_path(cached, None)
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_default()
}

fn detect_fallout4_docs_path(cached_path: &str, selected_game_version: &str) -> String {
    let relative = resolve_fallout4_version_info(selected_game_version)
        .map(|info| fallout4_docs_relative_path(&info.docs_name))
        .unwrap_or_else(|| fallout4_docs_relative_path("Fallout4"));
    // Opt in to Fallout 4's Steam/Proton documents lookup on Linux.
    // The canonical 377160 literal now lives in classic_version_registry_core.
    let finder =
        DocsPathFinder::new(relative).with_steam_app_id(Fallout4Version::Original.steam_app_id());

    let cached = if cached_path.is_empty() {
        None
    } else {
        Some(cached_path)
    };

    finder
        .find_docs_path(cached)
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_default()
}

fn fallout4_docs_relative_path(docs_name: &str) -> String {
    // DocsPathFinder joins this string on Unix/Proton too, where backslash is a literal.
    format!("My Games/{docs_name}")
}

// ─────────────────────────────────────────────────────────────────────────────
// Validation helpers — Result<(), String>
// (Bridge String/Path Contract: empty strings fall through to the underlying
//  validator, which returns Err with a clear message.)
// ─────────────────────────────────────────────────────────────────────────────

fn path_validate_exists(path: &str) -> Result<(), String> {
    core_validate_path_exists(Path::new(path)).map_err(|e| e.to_string())
}

fn path_validate_is_directory(path: &str) -> Result<(), String> {
    core_validate_is_directory(Path::new(path)).map_err(|e| e.to_string())
}

fn path_validate_is_file(path: &str) -> Result<(), String> {
    core_validate_is_file(Path::new(path)).map_err(|e| e.to_string())
}

fn path_validate_required_files(dir: &str, required: &[String]) -> Result<(), String> {
    core_validate_required_files(Path::new(dir), required).map_err(|e| e.to_string())
}

fn path_validate_custom_scan(path: &str) -> Result<(), String> {
    core_validate_custom_scan_path(Path::new(path)).map_err(|e| e.to_string())
}

// ─────────────────────────────────────────────────────────────────────────────
// Predicate helpers — fail-soft bool
// ─────────────────────────────────────────────────────────────────────────────

fn is_valid_path(path: &str) -> bool {
    core_is_valid_path(Path::new(path))
}

fn is_restricted_path(path: &str) -> bool {
    core_is_restricted_path(Path::new(path))
}

/// Backward-compatible alias for `is_valid_path` (D-11 / D-08 shim).
fn validate_path(path: &str) -> bool {
    core_is_valid_path(Path::new(path))
}

/// Backward-compatible alias for `is_restricted_path` (D-11 / D-08 shim).
fn check_restricted_path(path: &str) -> bool {
    core_is_restricted_path(Path::new(path))
}

// ─────────────────────────────────────────────────────────────────────────────
// INI checker — REAL surface (corrected per Codex HIGH review)
// Mirrors DocumentsChecker::validate_ini_file and run_all_checks.
// There is NO check_ini_files free fn — all entry points go through
// DocumentsChecker::new(game_name).
// ─────────────────────────────────────────────────────────────────────────────

fn docs_checker_validate_ini_file(
    docs_path: &str,
    game_name: &str,
    ini_name: &str,
) -> ffi::IniCheckResultDto {
    // Bridge String/Path Contract: empty docs_path returns a fail-soft "missing" result.
    if docs_path.is_empty() {
        return ffi::IniCheckResultDto {
            ini_name: ini_name.to_string(),
            exists: false,
            is_valid: false,
            message: String::new(),
            issue_or_empty: "missing".to_string(),
            has_issue: true,
        };
    }
    let checker = DocumentsChecker::new(game_name);
    match checker.validate_ini_file(Path::new(docs_path), ini_name) {
        Ok(result) => map_ini_check_result(result),
        Err(_e) => ffi::IniCheckResultDto {
            ini_name: ini_name.to_string(),
            exists: false,
            is_valid: false,
            message: String::new(),
            issue_or_empty: "io_error".to_string(),
            has_issue: true,
        },
    }
}

fn docs_checker_run_all_checks(docs_path: &str, game_name: &str) -> Vec<String> {
    if docs_path.is_empty() {
        return Vec::new();
    }
    let checker = DocumentsChecker::new(game_name);
    checker
        .run_all_checks(Path::new(docs_path))
        .unwrap_or_default()
}

fn map_ini_check_result(r: CoreIniCheckResult) -> ffi::IniCheckResultDto {
    let has_issue = r.issue.is_some();
    ffi::IniCheckResultDto {
        ini_name: r.ini_name,
        exists: r.exists,
        is_valid: r.is_valid,
        message: r.message,
        issue_or_empty: r.issue.unwrap_or_default(),
        has_issue,
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Backup helpers
// BackupManager uses instance-based new(backup_root) API; the bridge wraps
// it as static-style helpers by deriving the backup root from the source path.
// ─────────────────────────────────────────────────────────────────────────────

fn backup_create_timestamped(source_path: &str, game_name: &str) -> Result<String, String> {
    if source_path.is_empty() {
        return Err("backup_create_timestamped: source_path is empty".to_string());
    }
    let source = Path::new(source_path);
    let backup_root = source
        .parent()
        .ok_or_else(|| "backup_create_timestamped: source path has no parent".to_string())?
        .join("CLASSIC Backups")
        .join(game_name);
    let manager = BackupManager::new(&backup_root);

    // Extract version from source file's sibling XSE log if available.
    // Fall back to a simple timestamped copy when no XSE log is present.
    let timestamp = {
        use std::time::{SystemTime, UNIX_EPOCH};
        let secs = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);
        secs.to_string()
    };

    let xse_version = classic_path_core::XseVersion::new(timestamp);
    manager
        .create_backup(source, &xse_version)
        .map(|p| p.to_string_lossy().to_string())
        .map_err(|e| e.to_string())
}

fn backup_list_existing(source_path: &str, game_name: &str) -> Vec<String> {
    if source_path.is_empty() {
        return Vec::new();
    }
    let source = Path::new(source_path);
    let backup_root = match source.parent() {
        Some(p) => p.join("CLASSIC Backups").join(game_name),
        None => return Vec::new(),
    };
    if !backup_root.exists() {
        return Vec::new();
    }
    let manager = BackupManager::new(&backup_root);
    manager.list_versions().unwrap_or_default()
}

// ─────────────────────────────────────────────────────────────────────────────
// XSE log + game-path discovery
// ─────────────────────────────────────────────────────────────────────────────

fn parse_xse_log(log_path: &str) -> Result<String, String> {
    if log_path.is_empty() {
        return Err("parse_xse_log: log_path is empty".to_string());
    }
    core_parse_xse_log(Path::new(log_path))
        .map(|p| p.to_string_lossy().to_string())
        .map_err(|e| e.to_string())
}

fn find_game_path(
    game_exe: &str,
    xse_loader: &str,
    game_name: &str,
    is_vr: bool,
    cached_path: &str,
    xse_log_path: &str,
) -> String {
    if game_exe.is_empty() {
        return String::new();
    }
    let xse_loader_opt = if xse_loader.is_empty() {
        None::<&str>
    } else {
        Some(xse_loader)
    };
    let cached = if cached_path.is_empty() {
        None
    } else {
        Some(Path::new(cached_path))
    };
    let xse_log = if xse_log_path.is_empty() {
        None
    } else {
        Some(Path::new(xse_log_path))
    };
    let finder = GamePathFinder::new(game_exe, xse_loader_opt, game_name, is_vr);
    finder
        .find_game_path(cached, xse_log)
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_default()
}

// ─────────────────────────────────────────────────────────────────────────────
// CXX bridge declaration — namespace = "classic::path"
// ─────────────────────────────────────────────────────────────────────────────

#[cxx::bridge(namespace = "classic::path")]
mod ffi {
    /// Flat shared struct mirroring `classic_path_core::checker::IniCheckResult`.
    ///
    /// `issue: Option<String>` is flattened to `issue_or_empty: String` plus
    /// `has_issue: bool` per the Bridge String/Path Contract (CXX cannot share
    /// `Option<T>` across the FFI boundary).
    struct IniCheckResultDto {
        /// Name of the INI file checked (e.g., "Fallout4.ini").
        ini_name: String,
        /// Whether the INI file exists on disk.
        exists: bool,
        /// Whether the INI file is valid and parseable.
        is_valid: bool,
        /// Human-readable message describing the check result.
        message: String,
        /// Flattened `issue` field: empty string when `has_issue` is false.
        issue_or_empty: String,
        /// True when `issue` is `Some(_)` (mirrors `IniCheckResult::has_issue()`).
        has_issue: bool,
    }

    extern "Rust" {
        // ── Existing detection helpers (preserved) ──────────────────────
        /// Detect Fallout 4 game root path.
        ///
        /// Returns empty string if detection fails.
        fn detect_fallout4_game_path(cached_path: &str, selected_game_version: &str) -> String;

        /// Resolve the expected Fallout 4 executable name for a selected version.
        fn resolve_fallout4_exe_name(selected_game_version: &str) -> String;

        /// Detect Fallout 4 docs path (e.g. My Games/Fallout4).
        ///
        /// Returns empty string if detection fails.
        fn detect_fallout4_docs_path(cached_path: &str, selected_game_version: &str) -> String;

        // ── Validation Result helpers (CXXS-08) ─────────────────────────
        /// Check that `path` exists on disk. Throws on the C++ side if invalid.
        fn path_validate_exists(path: &str) -> Result<()>;
        /// Check that `path` exists and is a directory.
        fn path_validate_is_directory(path: &str) -> Result<()>;
        /// Check that `path` exists and is a file.
        fn path_validate_is_file(path: &str) -> Result<()>;
        /// Check that all `required` filenames exist under `dir`.
        fn path_validate_required_files(dir: &str, required: &[String]) -> Result<()>;
        /// Check that `path` is a valid, non-restricted directory for custom scans.
        fn path_validate_custom_scan(path: &str) -> Result<()>;

        // ── Predicate helpers ────────────────────────────────────────────
        /// Returns `true` if `path` exists on disk.
        fn is_valid_path(path: &str) -> bool;
        /// Returns `true` if `path` is a restricted Windows system directory.
        fn is_restricted_path(path: &str) -> bool;

        // ── Backward-compatible bool aliases (D-11 / D-08) ──────────────
        /// Alias for `is_valid_path` — retained for consumer compatibility.
        fn validate_path(path: &str) -> bool;
        /// Alias for `is_restricted_path` — retained for consumer compatibility.
        fn check_restricted_path(path: &str) -> bool;

        // ── INI checker (REAL surface, corrected per Codex HIGH review) ──
        /// Validate a single INI file via `DocumentsChecker::validate_ini_file`.
        fn docs_checker_validate_ini_file(
            docs_path: &str,
            game_name: &str,
            ini_name: &str,
        ) -> IniCheckResultDto;
        /// Run all document checks via `DocumentsChecker::run_all_checks`.
        fn docs_checker_run_all_checks(docs_path: &str, game_name: &str) -> Vec<String>;

        // ── Backup helpers ───────────────────────────────────────────────
        /// Create a timestamped backup of `source_path`. Throws on error.
        fn backup_create_timestamped(source_path: &str, game_name: &str) -> Result<String>;
        /// List existing backups for `source_path`. Returns empty on failure.
        fn backup_list_existing(source_path: &str, game_name: &str) -> Vec<String>;

        // ── XSE log + find_game_path ─────────────────────────────────────
        /// Parse an XSE log file and return the discovered game directory path.
        ///
        /// Throws on the C++ side if the log cannot be parsed.
        fn parse_xse_log(log_path: &str) -> Result<String>;

        /// Find game installation path using multiple strategies.
        ///
        /// Returns empty string on failure (fail-soft).
        fn find_game_path(
            game_exe: &str,
            xse_loader: &str,
            game_name: &str,
            is_vr: bool,
            cached_path: &str,
            xse_log_path: &str,
        ) -> String;
    }
}

#[cfg(test)]
#[path = "path_tests.rs"]
mod tests;
