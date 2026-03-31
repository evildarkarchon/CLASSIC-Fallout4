//! Setup coordination and initialization orchestration.
//!
//! This module provides the Rust-portable business logic for application setup,
//! including integrity checking, document validation, path configuration detection,
//! and settings migration. It orchestrates the various checking components from
//! `classic-scangame-core` and `classic-path-core` into a unified workflow.
//!
//! # Overview
//!
//! The Python `SetupCoordinator` class (in `ClassicLib/support/setup.py`) handles
//! both Python-specific concerns (logging, message handlers, asyncio, GlobalRegistry)
//! and portable business logic. This module extracts the portable parts:
//!
//! - **Combined check orchestration**: Running integrity, XSE, and document checks
//! - **Settings migration**: Converting legacy VR Mode to Game Version
//! - **Path configuration detection**: Determining if paths need auto-detection
//! - **Game version resolution**: Resolving effective game version from settings
//!
//! # Examples
//!
//! ```rust
//! use classic_scangame_core::setup::{
//!     SetupCheckConfig,
//!     run_combined_checks,
//!     migrate_game_version_setting,
//!     resolve_effective_game_version,
//! };
//!
//! // Migrate legacy VR Mode setting
//! let version = migrate_game_version_setting(None, Some(true));
//! assert_eq!(version, Some("VR".to_string()));
//!
//! // Resolve effective game version
//! let effective = resolve_effective_game_version(Some("VR"));
//! assert_eq!(effective, "VR");
//!
//! let effective = resolve_effective_game_version(Some("invalid"));
//! assert_eq!(effective, "auto");
//! ```

use std::path::Path;
use thiserror::Error;

use crate::integrity::{GameIntegrityChecker, IntegrityConfig, IntegrityError};

/// Errors from setup coordination.
#[derive(Debug, Error)]
pub enum SetupError {
    /// Integrity check error.
    #[error("Integrity check failed: {0}")]
    IntegrityError(#[from] IntegrityError),

    /// Document check error.
    #[error("Document check failed: {0}")]
    DocumentCheckError(String),

    /// Path validation error.
    #[error("Path validation failed: {0}")]
    PathError(String),
}

/// Result type for setup operations.
pub type SetupResult<T> = Result<T, SetupError>;

/// Configuration for running the combined setup checks.
///
/// This provides all the parameters needed by the various checking
/// components without requiring Python-specific infrastructure.
#[derive(Debug, Clone)]
pub struct SetupCheckConfig {
    /// Integrity checker configuration.
    pub integrity: IntegrityConfig,

    /// Game name for document checking (e.g., "Fallout4").
    pub game_name: String,

    /// Documents folder path (if known).
    pub docs_path: Option<String>,

    /// XSE checker configuration: list of (plugin_name, expected_hash) pairs.
    pub xse_hashes: Vec<(String, String)>,
}

/// Results from running all combined setup checks.
///
/// Collects output from integrity checks, XSE validation, and
/// document folder validation into a single results structure.
#[derive(Debug, Clone, Default)]
pub struct SetupCheckResults {
    /// Results from game integrity checks (executable version, installation location).
    pub integrity_results: Vec<String>,

    /// Results from XSE integrity and hash checks.
    pub xse_results: Vec<String>,

    /// Results from document folder checks (OneDrive, INI validation).
    pub docs_results: Vec<String>,

    /// Any errors encountered during checks (non-fatal).
    pub errors: Vec<String>,
}

impl SetupCheckResults {
    /// Combine all results into a single string (matches Python's `generate_combined_results`).
    ///
    /// # Returns
    ///
    /// A concatenated string of all check results.
    #[must_use]
    pub fn combined(&self) -> String {
        let mut parts = Vec::new();
        parts.extend(self.integrity_results.iter().cloned());
        parts.extend(self.xse_results.iter().cloned());
        parts.extend(self.docs_results.iter().cloned());
        parts.join("")
    }

    /// Check if any errors were encountered.
    #[must_use]
    pub fn has_errors(&self) -> bool {
        !self.errors.is_empty()
    }

    /// Get the total number of check results.
    #[must_use]
    pub fn total_checks(&self) -> usize {
        self.integrity_results.len() + self.xse_results.len() + self.docs_results.len()
    }
}

/// Run combined integrity, XSE, and document checks.
///
/// This is the Rust equivalent of the Python `SetupCoordinator.generate_combined_results()`.
/// It runs all checks and collects results into a single structure.
///
/// # Arguments
///
/// * `config` - Configuration for all check components
///
/// # Returns
///
/// A `SetupCheckResults` with all check outputs collected.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_scangame_core::setup::{SetupCheckConfig, run_combined_checks};
/// use classic_scangame_core::integrity::IntegrityConfig;
/// use std::path::PathBuf;
///
/// let config = SetupCheckConfig {
///     integrity: IntegrityConfig::new(
///         PathBuf::from("C:\\Games\\Fallout4\\Fallout4.exe"),
///         vec!["abc123".into()],
///         "Fallout 4".into(),
///     ),
///     game_name: "Fallout4".into(),
///     docs_path: Some("C:\\Users\\Name\\Documents\\My Games\\Fallout4".into()),
///     xse_hashes: vec![],
/// };
///
/// let results = run_combined_checks(&config);
/// println!("{}", results.combined());
/// ```
pub fn run_combined_checks(config: &SetupCheckConfig) -> SetupCheckResults {
    let mut results = SetupCheckResults::default();

    // 1. Run game integrity checks
    let checker = GameIntegrityChecker::new(config.integrity.clone());
    match checker.run_full_check() {
        Ok(output) => {
            if !output.is_empty() {
                results.integrity_results.push(output);
            }
        }
        Err(e) => {
            results.errors.push(format!("Integrity check error: {}", e));
        }
    }

    // 2. Run document checks (if docs path is known)
    if let Some(docs_path) = &config.docs_path {
        let docs_checker = classic_path_core::DocumentsChecker::new(config.game_name.clone());
        match docs_checker.run_all_checks(Path::new(docs_path)) {
            Ok(messages) => {
                results.docs_results.extend(messages);
            }
            Err(e) => {
                results.errors.push(format!("Document check error: {}", e));
            }
        }
    }

    results
}

/// Migrate the legacy VR Mode setting to the new Game Version format.
///
/// In CLASSIC v8.0+, the "VR Mode" boolean setting was replaced with a
/// Canonicalize user-facing game version inputs.
///
/// Accepts aliases and case variations and maps them to the canonical mode names.
#[must_use]
fn canonical_game_version(value: &str) -> Option<&'static str> {
    let normalized: String = value
        .chars()
        .filter(|ch| ch.is_ascii_alphanumeric())
        .map(|ch| ch.to_ascii_lowercase())
        .collect();
    match normalized.as_str() {
        "auto" => Some("auto"),
        "original" | "og" => Some("Original"),
        "nextgen" | "ng" => Some("NextGen"),
        "anniversaryedition" | "anniversary" | "ae" => Some("AnniversaryEdition"),
        "vr" => Some("VR"),
        _ => None,
    }
}

/// Migrate legacy game-version settings into canonical game version mode values.
///
/// Supports "Original", "NextGen", "AnniversaryEdition"/"AE", "VR", and "auto".
/// Explicit non-"auto" game version values take precedence over legacy VR mode.
#[must_use]
pub fn migrate_game_version_setting(
    game_version: Option<&str>,
    legacy_vr_mode: Option<bool>,
) -> Option<String> {
    // If new setting is explicitly set to a known value, use it
    if let Some(version) = game_version.and_then(canonical_game_version)
        && version != "auto"
    {
        return Some(version.to_string());
    }

    // If new setting is unset or "auto", check legacy VR mode
    if legacy_vr_mode == Some(true) {
        return Some("VR".to_string());
    }

    // If game_version is "auto" but no legacy VR, keep as-is
    if let Some(v) = game_version {
        if let Some(version) = canonical_game_version(v) {
            return Some(version.to_string());
        }
        if !v.trim().is_empty() {
            return Some(v.trim().to_string());
        }
    }

    None
}

/// Resolve the effective game version from a raw setting value.
///
/// Maps the raw Game Version setting to one of the known values,
/// defaulting to "auto" for unknown or missing values.
///
/// # Arguments
///
/// * `game_version` - The raw Game Version setting value
///
/// # Returns
///
/// One of: "Original", "NextGen", "AnniversaryEdition", "VR", or "auto".
///
/// # Examples
///
/// ```rust
/// use classic_scangame_core::setup::resolve_effective_game_version;
///
/// assert_eq!(resolve_effective_game_version(Some("VR")), "VR");
/// assert_eq!(resolve_effective_game_version(Some("Original")), "Original");
/// assert_eq!(resolve_effective_game_version(Some("NextGen")), "NextGen");
/// assert_eq!(resolve_effective_game_version(Some("auto")), "auto");
/// assert_eq!(resolve_effective_game_version(Some("invalid")), "auto");
/// assert_eq!(resolve_effective_game_version(None), "auto");
/// ```
#[must_use]
pub fn resolve_effective_game_version(game_version: Option<&str>) -> &'static str {
    game_version
        .and_then(canonical_game_version)
        .unwrap_or("auto")
}

/// Check if game and documents paths need auto-detection.
///
/// Returns a tuple of `(needs_game_path, needs_docs_path)` indicating
/// which paths are missing and need to be detected.
///
/// # Arguments
///
/// * `game_path` - Current game path setting (empty or None means not configured)
/// * `docs_path` - Current documents path setting (empty or None means not configured)
///
/// # Returns
///
/// A tuple `(needs_game_path, needs_docs_path)`.
///
/// # Examples
///
/// ```rust
/// use classic_scangame_core::setup::needs_path_detection;
///
/// // Both missing
/// assert_eq!(needs_path_detection(None, None), (true, true));
///
/// // Only game path set
/// assert_eq!(needs_path_detection(Some("C:\\Games\\Fallout4"), None), (false, true));
///
/// // Both set
/// assert_eq!(needs_path_detection(Some("C:\\Games"), Some("C:\\Docs")), (false, false));
///
/// // Empty strings treated as missing
/// assert_eq!(needs_path_detection(Some(""), Some("")), (true, true));
/// ```
#[must_use]
pub fn needs_path_detection(game_path: Option<&str>, docs_path: Option<&str>) -> (bool, bool) {
    let needs_game = game_path.is_none_or(|p| p.is_empty());
    let needs_docs = docs_path.is_none_or(|p| p.is_empty());
    (needs_game, needs_docs)
}

#[cfg(test)]
mod tests {
    use super::*;

    // ========================================================================
    // Settings Migration Tests
    // ========================================================================

    #[test]
    fn test_migrate_game_version_setting_new_takes_precedence() {
        assert_eq!(
            migrate_game_version_setting(Some("Original"), Some(true)),
            Some("Original".to_string())
        );
        assert_eq!(
            migrate_game_version_setting(Some("NextGen"), Some(false)),
            Some("NextGen".to_string())
        );
        assert_eq!(
            migrate_game_version_setting(Some("AnniversaryEdition"), Some(false)),
            Some("AnniversaryEdition".to_string())
        );
        assert_eq!(
            migrate_game_version_setting(Some("AE"), Some(false)),
            Some("AnniversaryEdition".to_string())
        );
        assert_eq!(
            migrate_game_version_setting(Some("VR"), None),
            Some("VR".to_string())
        );
    }

    #[test]
    fn test_migrate_game_version_setting_legacy_migration() {
        assert_eq!(
            migrate_game_version_setting(None, Some(true)),
            Some("VR".to_string())
        );
        assert_eq!(
            migrate_game_version_setting(Some("auto"), Some(true)),
            Some("VR".to_string())
        );
    }

    #[test]
    fn test_migrate_game_version_setting_no_migration_needed() {
        assert_eq!(
            migrate_game_version_setting(Some("auto"), Some(false)),
            Some("auto".to_string())
        );
        assert_eq!(
            migrate_game_version_setting(Some("auto"), None),
            Some("auto".to_string())
        );
    }

    #[test]
    fn test_migrate_game_version_setting_nothing_set() {
        assert_eq!(migrate_game_version_setting(None, None), None);
        assert_eq!(migrate_game_version_setting(None, Some(false)), None);
    }

    // ========================================================================
    // Game Version Resolution Tests
    // ========================================================================

    #[test]
    fn test_resolve_known_versions() {
        assert_eq!(resolve_effective_game_version(Some("Original")), "Original");
        assert_eq!(resolve_effective_game_version(Some("NextGen")), "NextGen");
        assert_eq!(
            resolve_effective_game_version(Some("AnniversaryEdition")),
            "AnniversaryEdition"
        );
        assert_eq!(
            resolve_effective_game_version(Some("AE")),
            "AnniversaryEdition"
        );
        assert_eq!(resolve_effective_game_version(Some("VR")), "VR");
        assert_eq!(resolve_effective_game_version(Some("auto")), "auto");
    }

    #[test]
    fn test_resolve_unknown_defaults_to_auto() {
        assert_eq!(resolve_effective_game_version(Some("invalid")), "auto");
        assert_eq!(resolve_effective_game_version(Some("")), "auto");
        assert_eq!(resolve_effective_game_version(None), "auto");
    }

    // ========================================================================
    // Path Detection Tests
    // ========================================================================

    #[test]
    fn test_needs_path_detection_both_missing() {
        assert_eq!(needs_path_detection(None, None), (true, true));
    }

    #[test]
    fn test_needs_path_detection_both_set() {
        assert_eq!(
            needs_path_detection(Some("C:\\Games"), Some("C:\\Docs")),
            (false, false)
        );
    }

    #[test]
    fn test_needs_path_detection_partial() {
        assert_eq!(needs_path_detection(Some("C:\\Games"), None), (false, true));
        assert_eq!(needs_path_detection(None, Some("C:\\Docs")), (true, false));
    }

    #[test]
    fn test_needs_path_detection_empty_strings() {
        assert_eq!(needs_path_detection(Some(""), Some("")), (true, true));
    }

    // ========================================================================
    // SetupCheckResults Tests
    // ========================================================================

    #[test]
    fn test_results_default_empty() {
        let results = SetupCheckResults::default();
        assert!(!results.has_errors());
        assert_eq!(results.total_checks(), 0);
        assert!(results.combined().is_empty());
    }

    #[test]
    fn test_results_combined() {
        let results = SetupCheckResults {
            integrity_results: vec!["check1".into()],
            xse_results: vec!["check2".into()],
            docs_results: vec!["check3".into()],
            errors: vec![],
        };
        assert_eq!(results.combined(), "check1check2check3");
        assert_eq!(results.total_checks(), 3);
        assert!(!results.has_errors());
    }

    #[test]
    fn test_results_with_errors() {
        let results = SetupCheckResults {
            integrity_results: vec![],
            xse_results: vec![],
            docs_results: vec![],
            errors: vec!["something failed".into()],
        };
        assert!(results.has_errors());
    }
}
