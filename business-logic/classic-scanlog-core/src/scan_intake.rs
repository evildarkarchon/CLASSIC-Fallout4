//! Crash Log Scan Intake preparation.
//!
//! This module owns the pre-analysis readiness decisions that convert selected
//! game/version input, YAML Data, scan flags, simplify-log rules, and FormID
//! database settings into a payload ready for `OrchestratorCore`.

use crate::error::{Result, ScanLogError};
use crate::{AnalysisConfig, build_analysis_config_from_yaml};
use classic_config_core::YamlDataCore;
use classic_database_core::{BATCH_CACHE_TTL_SECS, DatabasePool};
use classic_settings_core::YamlOperations;
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::time::Duration;

/// Cache profile used by short native CLI/GUI scan sessions.
pub const SHORT_SCAN_CACHE_PROFILE: ShortScanCacheProfile = ShortScanCacheProfile {
    cache_capacity: 30_000,
    cache_ttl_secs: BATCH_CACHE_TTL_SECS,
    cleanup_threshold: 4_096,
    cleanup_interval_secs: 300,
};

/// User-selected scan options that affect analysis readiness.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct CrashLogScanOptions {
    /// Whether FormID values should be looked up through the optional database pool.
    pub show_formid_values: bool,
    /// Whether FCX mode should include extra settings diagnostics.
    pub fcx_mode: bool,
    /// Whether simplify-log removal should be enabled during line preprocessing.
    pub simplify_logs: bool,
}

impl CrashLogScanOptions {
    /// Creates scan options from caller-facing flags.
    ///
    /// These flags map directly onto `AnalysisConfig` booleans; intake only adds
    /// the sidecar readiness data those flags imply.
    #[must_use]
    pub const fn new(show_formid_values: bool, fcx_mode: bool, simplify_logs: bool) -> Self {
        Self {
            show_formid_values,
            fcx_mode,
            simplify_logs,
        }
    }
}

/// Path roots used by path-backed YAML Data and scan sidecar settings.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CrashLogScanIntakePaths {
    /// Root directory containing user settings and ignore YAML.
    pub yaml_dir_root: PathBuf,
    /// `CLASSIC Data` directory containing shippable YAML databases.
    pub yaml_dir_data: PathBuf,
}

impl CrashLogScanIntakePaths {
    /// Creates intake path roots from the user/settings root and `CLASSIC Data` directory.
    #[must_use]
    pub fn new(
        yaml_dir_root: impl Into<PathBuf>,
        yaml_dir_data: impl Into<PathBuf>,
    ) -> CrashLogScanIntakePaths {
        Self {
            yaml_dir_root: yaml_dir_root.into(),
            yaml_dir_data: yaml_dir_data.into(),
        }
    }

    pub(crate) fn canonical_unsolved_logs_destination(&self) -> PathBuf {
        self.yaml_dir_root
            .join("CLASSIC Backup")
            .join("Unsolved Logs")
    }
}

/// FormID database readiness selected during intake.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FormIdReadiness {
    /// Whether callers requested DB-backed FormID values.
    pub enabled: bool,
    /// Ordered candidate database paths to initialize when `enabled` is true.
    pub database_paths: Vec<PathBuf>,
}

impl FormIdReadiness {
    /// Returns whether DB-backed FormID lookup was requested for this scan.
    #[must_use]
    pub const fn is_enabled(&self) -> bool {
        self.enabled
    }

    /// Returns the selected FormID database paths in initialization order.
    #[must_use]
    pub fn database_paths(&self) -> &[PathBuf] {
        &self.database_paths
    }
}

/// Cache knobs chosen by scan readiness for short native scan sessions.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ShortScanCacheProfile {
    /// Maximum number of cached FormID lookup entries.
    pub cache_capacity: usize,
    /// FormID lookup cache TTL in seconds.
    pub cache_ttl_secs: u64,
    /// Query count threshold that triggers proactive cache cleanup.
    pub cleanup_threshold: u64,
    /// Minimum proactive cleanup interval in seconds.
    pub cleanup_interval_secs: u64,
}

impl ShortScanCacheProfile {
    /// Applies this profile to a database pool without taking ownership of the pool.
    ///
    /// Intake chooses the profile; `classic-database-core` still owns the pool
    /// implementation, bounds, and cache mechanics behind these setters.
    pub fn apply_to_pool(&self, pool: &DatabasePool) {
        pool.set_cache_ttl(Duration::from_secs(self.cache_ttl_secs));
        pool.set_cache_capacity(self.cache_capacity);
        pool.set_cache_cleanup_threshold(self.cleanup_threshold);
        pool.set_cache_cleanup_interval(Duration::from_secs(self.cleanup_interval_secs));
    }
}

/// Result of preparing a Crash Log scan for analysis.
#[derive(Clone)]
pub struct ScanReadyAnalysis {
    /// Fully populated analysis payload for `OrchestratorCore`.
    pub(crate) analysis_config: AnalysisConfig,
    /// FormID database readiness selected for this scan.
    pub(crate) formid_readiness: FormIdReadiness,
    /// Short-scan database cache profile selected for native callers.
    pub(crate) cache_profile: ShortScanCacheProfile,
    /// Path roots available to path-backed intake.
    pub(crate) paths: Option<CrashLogScanIntakePaths>,
    /// Persistent Unsolved Logs Destination, when configured.
    pub(crate) unsolved_logs_destination: Option<PathBuf>,
}

impl ScanReadyAnalysis {
    pub(crate) fn new(
        analysis_config: AnalysisConfig,
        formid_readiness: FormIdReadiness,
        cache_profile: ShortScanCacheProfile,
        paths: Option<CrashLogScanIntakePaths>,
        unsolved_logs_destination: Option<PathBuf>,
    ) -> Self {
        Self {
            analysis_config,
            formid_readiness,
            cache_profile,
            paths,
            unsolved_logs_destination,
        }
    }

    /// Returns the prepared analysis configuration.
    #[must_use]
    pub fn analysis_config(&self) -> &AnalysisConfig {
        &self.analysis_config
    }

    /// Returns FormID database readiness selected during intake.
    #[must_use]
    pub fn formid_readiness(&self) -> &FormIdReadiness {
        &self.formid_readiness
    }

    /// Returns the short-scan database cache profile.
    #[must_use]
    pub const fn cache_profile(&self) -> ShortScanCacheProfile {
        self.cache_profile
    }

    /// Returns the path roots for path-backed intake, when available.
    #[must_use]
    pub fn paths(&self) -> Option<&CrashLogScanIntakePaths> {
        self.paths.as_ref()
    }

    /// Returns the configured Unsolved Logs Destination, when the setting is non-empty.
    #[must_use]
    pub fn unsolved_logs_destination(&self) -> Option<&Path> {
        self.unsolved_logs_destination.as_deref()
    }

    /// Returns whether this prepared scan should initialize FormID databases.
    ///
    /// In-memory intake can be used without filesystem sidecar paths; in that
    /// shape the scan still records that FormID lookup was requested, but there
    /// is no database path set to initialize.
    #[must_use]
    pub fn should_initialize_formid_database(&self) -> bool {
        self.formid_readiness.is_enabled() && !self.formid_readiness.database_paths().is_empty()
    }
}

enum YamlDataSource<'a> {
    PathBacked,
    InMemory(&'a YamlDataCore),
}

/// Prepares an existing Crash Log scan for analysis.
pub struct CrashLogScanIntake<'a> {
    game: String,
    selected_game_version: String,
    options: CrashLogScanOptions,
    paths: Option<CrashLogScanIntakePaths>,
    yaml_source: YamlDataSource<'a>,
}

impl<'a> CrashLogScanIntake<'a> {
    /// Creates intake for YAML Data loaded from the standard path-backed layout.
    ///
    /// The returned intake loads `YamlDataCore` from `yaml_dir_root` and
    /// `yaml_dir_data`, then resolves simplify-log and FormID sidecar settings
    /// from the same roots.
    #[must_use]
    pub fn from_yaml_paths(
        yaml_dir_root: impl Into<PathBuf>,
        yaml_dir_data: impl Into<PathBuf>,
        game: impl Into<String>,
        selected_game_version: impl Into<String>,
        options: CrashLogScanOptions,
    ) -> Self {
        Self {
            game: game.into(),
            selected_game_version: selected_game_version.into(),
            options,
            paths: Some(CrashLogScanIntakePaths::new(yaml_dir_root, yaml_dir_data)),
            yaml_source: YamlDataSource::PathBacked,
        }
    }

    /// Creates intake from already-loaded in-memory YAML Data.
    ///
    /// Supplying `paths` lets in-memory tests or adapters resolve the same
    /// simplify-log and FormID sidecar settings as path-backed production input.
    #[must_use]
    pub fn from_yaml_data(
        yaml: &'a YamlDataCore,
        paths: Option<CrashLogScanIntakePaths>,
        game: impl Into<String>,
        selected_game_version: impl Into<String>,
        options: CrashLogScanOptions,
    ) -> Self {
        Self {
            game: game.into(),
            selected_game_version: selected_game_version.into(),
            options,
            paths,
            yaml_source: YamlDataSource::InMemory(yaml),
        }
    }

    /// Builds a scan-ready payload without starting analysis.
    ///
    /// This centralizes current readiness behavior and intentionally preserves
    /// fail-soft sidecar loading: missing simplify-log settings or FormID user
    /// settings produce empty sidecar lists rather than new hard failures.
    ///
    /// # Errors
    ///
    /// Returns `ScanLogError::ConfigError` when path-backed YAML Data fails to
    /// load or parse through `classic-config-core`.
    pub async fn prepare(&self) -> Result<ScanReadyAnalysis> {
        let loaded_yaml = match self.yaml_source {
            YamlDataSource::PathBacked => {
                let paths = self.paths.as_ref().ok_or_else(|| {
                    ScanLogError::Internal(
                        "path-backed Crash Log Scan Intake missing path roots".to_string(),
                    )
                })?;
                let yaml_dirs = vec![paths.yaml_dir_root.clone(), paths.yaml_dir_data.clone()];
                Some(
                    YamlDataCore::load_from_yaml_files(
                        yaml_dirs,
                        self.game.clone(),
                        self.selected_game_version.clone(),
                    )
                    .await
                    .map_err(|error| ScanLogError::ConfigError(error.to_string()))?,
                )
            }
            YamlDataSource::InMemory(_) => None,
        };

        let yaml = match self.yaml_source {
            YamlDataSource::PathBacked => loaded_yaml.as_ref().ok_or_else(|| {
                ScanLogError::Internal("path-backed YAML Data was not loaded".to_string())
            })?,
            YamlDataSource::InMemory(yaml) => yaml,
        };

        let remove_list = self
            .paths
            .as_ref()
            .map(|paths| load_simplify_remove_list(&paths.yaml_dir_data))
            .unwrap_or_default();
        let analysis_config = build_analysis_config_from_yaml(
            yaml,
            &self.game,
            &self.selected_game_version,
            self.options.show_formid_values,
            self.options.fcx_mode,
            self.options.simplify_logs,
            remove_list,
        );
        let database_paths = self
            .paths
            .as_ref()
            .map(|paths| {
                resolve_formid_database_paths(
                    &paths.yaml_dir_root,
                    &paths.yaml_dir_data,
                    &self.game,
                )
            })
            .unwrap_or_default();
        let unsolved_logs_destination = match self.paths.as_ref() {
            Some(paths) => resolve_configured_unsolved_logs_destination(&paths.yaml_dir_root)?,
            None => None,
        };
        let show_formid_values = analysis_config.show_formid_values;

        Ok(ScanReadyAnalysis::new(
            analysis_config,
            FormIdReadiness {
                enabled: show_formid_values,
                database_paths,
            },
            SHORT_SCAN_CACHE_PROFILE,
            self.paths.clone(),
            unsolved_logs_destination,
        ))
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
pub fn resolve_formid_database_paths(
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
pub fn resolve_user_formid_database_paths(
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
pub fn load_simplify_remove_list(yaml_dir_data: impl AsRef<Path>) -> Vec<String> {
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
#[path = "scan_intake_tests.rs"]
mod tests;
