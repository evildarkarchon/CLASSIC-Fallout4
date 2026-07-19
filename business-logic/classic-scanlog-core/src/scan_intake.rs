//! Crash Log Scan Intake preparation.
//!
//! This module owns the pre-analysis readiness decisions that convert selected
//! game/version input, YAML Data, scan flags, simplify-log rules, and FormID
//! database settings into a payload ready for `OrchestratorCore`.

use crate::AnalysisConfig;
use crate::error::{Result, ScanLogError};
use crate::orchestrator::build_analysis_config_from_yaml;
use crate::scan_sidecar_settings::{self, ScanSidecarSettings};
use classic_config_core::{InstalledYamlDataSnapshot, YamlDataCore};
use classic_database_core::{BATCH_CACHE_TTL_SECS, DatabasePool};
use std::path::{Path, PathBuf};
use std::sync::Arc;
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
    /// Root directory containing ignore YAML and the canonical backup layout.
    pub yaml_dir_root: PathBuf,
    /// `CLASSIC Data` directory containing shippable YAML databases.
    pub yaml_dir_data: PathBuf,
}

/// Typed User Settings facts supplied by a Crash Log Scan adapter.
///
/// Crash Log Scan Intake consumes these values but never opens or persists User
/// Settings. Callers retain ownership of settings discovery, diagnostics, and
/// accepted updates.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct CrashLogScanFacts {
    /// Additional FormID database paths configured for the selected game.
    ///
    /// Relative paths are resolved under `yaml_dir_data` before intake appends
    /// them after the main and compatibility databases and removes duplicates.
    pub formid_database_paths: Vec<PathBuf>,
    /// Configured absolute Unsolved Logs Destination, when present.
    pub unsolved_logs_destination: Option<PathBuf>,
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
    /// Retained installed bytes whose parsed data backs this run's analysis configuration.
    pub(crate) _installed_yaml_data_snapshot: Option<Arc<InstalledYamlDataSnapshot>>,
}

impl ScanReadyAnalysis {
    pub(crate) fn new(
        analysis_config: AnalysisConfig,
        formid_readiness: FormIdReadiness,
        cache_profile: ShortScanCacheProfile,
        paths: Option<CrashLogScanIntakePaths>,
        unsolved_logs_destination: Option<PathBuf>,
        installed_yaml_data_snapshot: Option<Arc<InstalledYamlDataSnapshot>>,
    ) -> Self {
        Self {
            analysis_config,
            formid_readiness,
            cache_profile,
            paths,
            unsolved_logs_destination,
            _installed_yaml_data_snapshot: installed_yaml_data_snapshot,
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
    InstalledSnapshot(Arc<InstalledYamlDataSnapshot>),
}

/// Prepares an existing Crash Log scan for analysis.
pub struct CrashLogScanIntake<'a> {
    game: String,
    selected_game_version: String,
    options: CrashLogScanOptions,
    paths: Option<CrashLogScanIntakePaths>,
    scan_facts: CrashLogScanFacts,
    yaml_source: YamlDataSource<'a>,
}

impl<'a> CrashLogScanIntake<'a> {
    /// Creates intake for YAML Data loaded from the standard path-backed layout.
    ///
    /// The returned intake loads `YamlDataCore` from `yaml_dir_root` and
    /// `yaml_dir_data`, then loads simplify-log rules from YAML Data. FormID and
    /// Unsolved Logs settings must be supplied through [`Self::with_scan_facts`].
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
            scan_facts: CrashLogScanFacts::default(),
            yaml_source: YamlDataSource::PathBacked,
        }
    }

    /// Creates intake from already-loaded in-memory YAML Data.
    ///
    /// Supplying `paths` lets in-memory tests or adapters load the same
    /// simplify-log rules and resolve the same typed FormID paths as path-backed
    /// production input.
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
            scan_facts: CrashLogScanFacts::default(),
            yaml_source: YamlDataSource::InMemory(yaml),
        }
    }

    /// Creates intake from one immutable Installed YAML Data Snapshot.
    ///
    /// The snapshot remains owned by the prepared run so selected bytes cannot be replaced by
    /// concurrent installation changes. Only non-YAML sidecar paths are derived from the one
    /// installation root.
    #[must_use]
    pub fn from_installed_yaml_data(
        snapshot: Arc<InstalledYamlDataSnapshot>,
        installation_root: impl Into<PathBuf>,
        selected_game_version: impl Into<String>,
        options: CrashLogScanOptions,
    ) -> Self {
        let installation_root = installation_root.into();
        let game = snapshot.game().as_str().to_string();
        Self {
            game,
            selected_game_version: selected_game_version.into(),
            options,
            paths: Some(CrashLogScanIntakePaths::new(
                installation_root.clone(),
                installation_root.join("CLASSIC Data"),
            )),
            scan_facts: CrashLogScanFacts::default(),
            yaml_source: YamlDataSource::InstalledSnapshot(snapshot),
        }
    }

    /// Supplies typed scan facts already projected by the caller's User Settings adapter.
    ///
    /// These values replace all scan-intake interpretation of User Settings files.
    #[must_use]
    pub fn with_scan_facts(mut self, scan_facts: CrashLogScanFacts) -> Self {
        self.scan_facts = scan_facts;
        self
    }

    /// Builds a scan-ready payload without starting analysis.
    ///
    /// This centralizes current readiness behavior and intentionally preserves
    /// fail-soft YAML Data sidecar loading: missing simplify-log rules produce an
    /// empty removal list rather than a new hard failure.
    ///
    /// # Errors
    ///
    /// Returns `ScanLogError::ConfigError` when path-backed YAML Data fails to
    /// load or parse through `classic-config-core`, or
    /// `ScanLogError::InvalidInput` when the typed Unsolved Logs Destination is
    /// relative.
    pub async fn prepare(&self) -> Result<ScanReadyAnalysis> {
        let loaded_yaml = match &self.yaml_source {
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
            YamlDataSource::InMemory(_) | YamlDataSource::InstalledSnapshot(_) => None,
        };

        let yaml = match &self.yaml_source {
            YamlDataSource::PathBacked => loaded_yaml.as_ref().ok_or_else(|| {
                ScanLogError::Internal("path-backed YAML Data was not loaded".to_string())
            })?,
            YamlDataSource::InMemory(yaml) => *yaml,
            YamlDataSource::InstalledSnapshot(snapshot) => snapshot.yaml_data(),
        };

        let sidecar_settings = match (&self.yaml_source, self.paths.as_ref()) {
            (YamlDataSource::InstalledSnapshot(snapshot), Some(paths)) => {
                ScanSidecarSettings::from_installed_snapshot(
                    paths,
                    &self.game,
                    &self.scan_facts,
                    snapshot.simplify_remove_list(),
                )?
            }
            (_, Some(paths)) => ScanSidecarSettings::load(paths, &self.game, &self.scan_facts)?,
            (_, None) => ScanSidecarSettings::from_scan_facts(&self.scan_facts)?,
        };
        let ScanSidecarSettings {
            remove_list,
            formid_database_paths,
            unsolved_logs_destination,
        } = sidecar_settings;

        let analysis_config = build_analysis_config_from_yaml(
            yaml,
            &self.game,
            &self.selected_game_version,
            self.options.show_formid_values,
            self.options.fcx_mode,
            self.options.simplify_logs,
            remove_list,
        );
        let show_formid_values = analysis_config.show_formid_values;

        Ok(ScanReadyAnalysis::new(
            analysis_config,
            FormIdReadiness {
                enabled: show_formid_values,
                database_paths: formid_database_paths,
            },
            SHORT_SCAN_CACHE_PROFILE,
            self.paths.clone(),
            unsolved_logs_destination,
            match &self.yaml_source {
                YamlDataSource::InstalledSnapshot(snapshot) => Some(Arc::clone(snapshot)),
                YamlDataSource::PathBacked | YamlDataSource::InMemory(_) => None,
            },
        ))
    }
}

/// Resolve all FormID database paths needed for a scan.
///
/// The order preserves existing behavior: main game database, hardcoded
/// compatibility databases, then caller-provided configured databases. Relative
/// configured paths are resolved under `yaml_dir_data` before deduplication.
#[must_use]
pub fn resolve_formid_database_paths(
    yaml_dir_data: impl AsRef<Path>,
    game: &str,
    configured_paths: &[PathBuf],
) -> Vec<PathBuf> {
    scan_sidecar_settings::resolve_formid_database_paths(yaml_dir_data, game, configured_paths)
}

/// Load simplify-log removal rules from `CLASSIC Main.yaml`.
///
/// Missing or unreadable files return an empty list so intake preserves the
/// existing adapter fail-soft behavior. This compatibility helper delegates to
/// the typed sidecar settings module that owns the YAML path/key implementation
/// details.
#[must_use]
pub fn load_simplify_remove_list(yaml_dir_data: impl AsRef<Path>) -> Vec<String> {
    scan_sidecar_settings::load_simplify_remove_list(yaml_dir_data)
}

#[cfg(test)]
#[path = "scan_intake_tests.rs"]
mod tests;
