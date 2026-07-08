//! Path-backed scan sidecar settings for Crash Log Scan Intake.
//!
//! This module keeps YAML Data sidecar file names, legacy settings keys,
//! compatibility database paths, path normalization, and fail-soft loading local
//! to scan readiness instead of spreading those details through intake callers.

use crate::error::{Result, ScanLogError};
use crate::scan_intake::CrashLogScanIntakePaths;
use classic_settings_core::YamlOperations;
use std::collections::HashSet;
use std::path::{Path, PathBuf};

/// Typed sidecar settings resolved for a Crash Log Scan Intake.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub(crate) struct ScanSidecarSettings {
    /// Simplify-log removal strings read from YAML Data.
    pub(crate) remove_list: Vec<String>,
    /// Ordered FormID database paths selected for optional value lookup.
    pub(crate) formid_database_paths: Vec<PathBuf>,
    /// Persistent Unsolved Logs Destination, when configured.
    pub(crate) unsolved_logs_destination: Option<PathBuf>,
}

impl ScanSidecarSettings {
    /// Load all path-backed scan sidecar settings for the selected game.
    ///
    /// Missing or unreadable sidecar YAML preserves the existing fail-soft scan
    /// startup behavior: optional lists become empty instead of causing setup
    /// failure. A configured Unsolved Logs Destination is still validated because
    /// scan-run movement needs an absolute destination to be unambiguous.
    ///
    /// # Errors
    ///
    /// Returns `ScanLogError::InvalidInput` when `CLASSIC Settings.yaml`
    /// contains a non-empty relative Unsolved Logs Destination.
    pub(crate) fn load(paths: &CrashLogScanIntakePaths, game: &str) -> Result<Self> {
        Ok(Self {
            remove_list: load_simplify_remove_list(&paths.yaml_dir_data),
            formid_database_paths: resolve_formid_database_paths(
                &paths.yaml_dir_root,
                &paths.yaml_dir_data,
                game,
            ),
            unsolved_logs_destination: resolve_configured_unsolved_logs_destination(
                &paths.yaml_dir_root,
            )?,
        })
    }

    /// Return a sidecar-free settings set for in-memory YAML intake without paths.
    #[must_use]
    pub(crate) fn empty() -> Self {
        Self::default()
    }
}

/// Resolve the persistent Unsolved Logs Destination from `CLASSIC Settings.yaml`.
///
/// Missing or empty settings mean callers should use the canonical destination.
/// Non-empty values must be absolute and are not created during intake.
pub(crate) fn resolve_configured_unsolved_logs_destination(
    yaml_dir_root: impl AsRef<Path>,
) -> Result<Option<PathBuf>> {
    let settings_path = yaml_dir_root.as_ref().join("CLASSIC Settings.yaml");

    if !settings_path.exists() {
        return Ok(None);
    }

    let ops = YamlOperations::new();
    let doc = match ops.load_yaml_file(&settings_path) {
        Ok(doc) => doc,
        Err(_) => return Ok(None),
    };
    let raw = ops.get_string_value(&doc, "CLASSIC_Settings.Unsolved Logs Destination", "");
    let trimmed = raw.trim();

    if trimmed.is_empty() {
        return Ok(None);
    }

    let destination = PathBuf::from(trimmed);
    if !destination.is_absolute() {
        return Err(ScanLogError::InvalidInput(format!(
            "Unsolved Logs Destination must be an absolute path: {}",
            destination.display()
        )));
    }

    Ok(Some(normalize_path(destination)))
}

/// Resolve all FormID database paths needed for a scan.
///
/// The order preserves existing behavior: main game database, hardcoded
/// compatibility databases, then user-configured databases from settings.
#[must_use]
pub(crate) fn resolve_formid_database_paths(
    yaml_dir_root: impl AsRef<Path>,
    yaml_dir_data: impl AsRef<Path>,
    game: &str,
) -> Vec<PathBuf> {
    let data_dir = yaml_dir_data.as_ref();
    let main_db = data_dir
        .join("databases")
        .join(format!("{game} FormIDs Main.db"));

    let hardcoded = hardcoded_formid_database_relpaths(game)
        .iter()
        .map(|rel| data_dir.join(rel))
        .collect::<Vec<_>>();

    let user_paths = resolve_user_formid_database_paths(yaml_dir_root, yaml_dir_data, game);

    let mut all_paths = Vec::with_capacity(1 + hardcoded.len() + user_paths.len());
    all_paths.push(main_db);
    all_paths.extend(hardcoded);
    all_paths.extend(user_paths);
    dedupe_paths(all_paths)
}

/// Resolve user-configured FormID database paths from `CLASSIC Settings.yaml`.
///
/// Relative paths are interpreted under `yaml_dir_data`, matching the legacy
/// native bridge behavior.
#[must_use]
pub(crate) fn resolve_user_formid_database_paths(
    yaml_dir_root: impl AsRef<Path>,
    yaml_dir_data: impl AsRef<Path>,
    game: &str,
) -> Vec<PathBuf> {
    let settings_path = yaml_dir_root.as_ref().join("CLASSIC Settings.yaml");

    if !settings_path.exists() {
        return Vec::new();
    }

    let ops = YamlOperations::new();
    let doc = match ops.load_yaml_file(&settings_path) {
        Ok(doc) => doc,
        Err(_) => return Vec::new(),
    };

    let key_path = format!("CLASSIC_Settings.FormID Databases.{game}");
    ops.get_vec_value(&doc, &key_path)
        .into_iter()
        .map(PathBuf::from)
        .map(|path| {
            if path.is_absolute() {
                normalize_path(path)
            } else {
                normalize_path(yaml_dir_data.as_ref().join(path))
            }
        })
        .collect()
}

/// Load simplify-log removal rules from `CLASSIC Main.yaml`.
///
/// Missing or unreadable files return an empty list so intake preserves the
/// existing adapter fail-soft behavior.
#[must_use]
pub(crate) fn load_simplify_remove_list(yaml_dir_data: impl AsRef<Path>) -> Vec<String> {
    let main_yaml = yaml_dir_data
        .as_ref()
        .join("databases")
        .join("CLASSIC Main.yaml");

    if !main_yaml.exists() {
        return Vec::new();
    }

    let ops = YamlOperations::new();
    let doc = match ops.load_yaml_file(&main_yaml) {
        Ok(doc) => doc,
        Err(_) => return Vec::new(),
    };

    ops.get_vec_value(&doc, "exclude_log_records")
}

fn hardcoded_formid_database_relpaths(game: &str) -> &'static [&'static str] {
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

#[cfg(test)]
#[path = "scan_sidecar_settings_tests.rs"]
mod tests;
