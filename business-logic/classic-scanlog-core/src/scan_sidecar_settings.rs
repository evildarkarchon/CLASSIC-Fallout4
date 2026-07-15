//! Path-backed scan sidecar settings for Crash Log Scan Intake.
//!
//! This module keeps YAML Data sidecar file names, compatibility database paths,
//! path normalization, and fail-soft loading local to scan readiness instead of
//! spreading those details through intake callers.

use crate::error::{Result, ScanLogError};
use crate::scan_intake::{CrashLogScanFacts, CrashLogScanIntakePaths};
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
    /// Load YAML Data sidecars and combine them with caller-provided scan facts.
    ///
    /// Missing or unreadable YAML Data preserves the existing fail-soft scan
    /// startup behavior. A configured Unsolved Logs Destination is still
    /// validated because scan-run movement needs an absolute destination.
    ///
    /// # Errors
    ///
    /// Returns `ScanLogError::InvalidInput` when the typed facts contain a
    /// relative Unsolved Logs Destination.
    pub(crate) fn load(
        paths: &CrashLogScanIntakePaths,
        game: &str,
        scan_facts: &CrashLogScanFacts,
    ) -> Result<Self> {
        let unsolved_logs_destination =
            validate_unsolved_logs_destination(scan_facts.unsolved_logs_destination.clone())?;
        Ok(Self {
            remove_list: load_simplify_remove_list(&paths.yaml_dir_data),
            formid_database_paths: resolve_formid_database_paths(
                &paths.yaml_dir_data,
                game,
                &scan_facts.formid_database_paths,
            ),
            unsolved_logs_destination,
        })
    }

    /// Preserve typed facts for in-memory YAML intake that has no path roots.
    ///
    /// Without `yaml_dir_data`, configured relative FormID paths cannot be
    /// rebased. Callers that supply them must also supply
    /// [`CrashLogScanIntakePaths`].
    ///
    /// # Errors
    ///
    /// Returns `ScanLogError::InvalidInput` when the typed facts contain a
    /// relative Unsolved Logs Destination or a configured relative FormID path
    /// that cannot be resolved without `yaml_dir_data`.
    pub(crate) fn from_scan_facts(scan_facts: &CrashLogScanFacts) -> Result<Self> {
        if let Some(path) = scan_facts
            .formid_database_paths
            .iter()
            .find(|path| path.is_relative())
        {
            return Err(ScanLogError::InvalidInput(format!(
                "configured FormID database path requires yaml_dir_data: {}",
                path.display()
            )));
        }

        Ok(Self {
            remove_list: Vec::new(),
            formid_database_paths: dedupe_paths(scan_facts.formid_database_paths.clone()),
            unsolved_logs_destination: validate_unsolved_logs_destination(
                scan_facts.unsolved_logs_destination.clone(),
            )?,
        })
    }
}

/// Validates and normalizes an optional typed Unsolved Logs Destination.
///
/// Empty input remains absent. Absolute paths are normalized without touching the
/// filesystem; relative paths return [`ScanLogError::InvalidInput`].
fn validate_unsolved_logs_destination(destination: Option<PathBuf>) -> Result<Option<PathBuf>> {
    let Some(destination) = destination else {
        return Ok(None);
    };
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
/// compatibility databases, then caller-provided configured databases.
#[must_use]
pub(crate) fn resolve_formid_database_paths(
    yaml_dir_data: impl AsRef<Path>,
    game: &str,
    configured_paths: &[PathBuf],
) -> Vec<PathBuf> {
    let data_dir = yaml_dir_data.as_ref();
    let main_database_game = main_formid_database_game(game);
    let main_db = data_dir
        .join("databases")
        .join(format!("{main_database_game} FormIDs Main.db"));

    let hardcoded = hardcoded_formid_database_relpaths(game)
        .iter()
        .map(|rel| data_dir.join(rel))
        .collect::<Vec<_>>();

    let configured_paths = configured_paths.iter().cloned().map(|path| {
        if path.is_absolute() {
            normalize_path(path)
        } else {
            normalize_path(data_dir.join(path))
        }
    });

    let mut all_paths = Vec::with_capacity(1 + hardcoded.len() + configured_paths.len());
    all_paths.push(main_db);
    all_paths.extend(hardcoded);
    all_paths.extend(configured_paths);
    dedupe_paths(all_paths)
}

/// Returns the shared game identity used by the built-in main FormID database.
///
/// Fallout 4 VR retains its own runtime identity but reads Fallout 4's shared
/// analysis data, matching the `CLASSIC Fallout4.yaml` ownership contract.
fn main_formid_database_game(game: &str) -> &str {
    match game {
        "Fallout4VR" => "Fallout4",
        _ => game,
    }
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
