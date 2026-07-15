use crate::ScanLogError;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;

/// Request-scoped deterministic fault controls used by final-contract behavior tests.
///
/// Keeping these controls on one request avoids process-global test state while allowing
/// real discovery, intake, analysis orchestration, report persistence, and movement to run.
#[derive(Clone, Debug, Default)]
pub(crate) struct ScanRunTestHooks {
    analysis_delays: HashMap<usize, Duration>,
    analysis_failures: HashMap<usize, String>,
    infrastructure_failure: Option<InjectedInfrastructureFailure>,
    movement_failure: Option<InjectedMovementFailure>,
}

impl ScanRunTestHooks {
    /// Delays one admitted log before analysis so completion order can be forced reliably.
    #[must_use]
    pub(crate) fn with_analysis_delay(mut self, discovery_index: usize, delay: Duration) -> Self {
        self.analysis_delays.insert(discovery_index, delay);
        self
    }

    /// Replaces one admitted log's analysis with the supplied stable failure message.
    #[must_use]
    pub(crate) fn with_analysis_failure(
        mut self,
        discovery_index: usize,
        message: impl Into<String>,
    ) -> Self {
        self.analysis_failures
            .insert(discovery_index, message.into());
        self
    }

    /// Injects one lower-layer failure at its named lifecycle boundary.
    #[must_use]
    pub(crate) fn with_infrastructure_failure(
        mut self,
        fault: InfrastructureFault,
        message: impl Into<String>,
    ) -> Self {
        self.infrastructure_failure = Some(InjectedInfrastructureFailure {
            fault,
            message: message.into(),
        });
        self
    }

    /// Injects a movement failure after the requested number of artifacts moved successfully.
    #[must_use]
    pub(crate) fn with_movement_failure_after(
        mut self,
        successful_moves: usize,
        message: impl Into<String>,
    ) -> Self {
        self.movement_failure = Some(InjectedMovementFailure {
            successful_moves,
            observed_moves: Arc::new(AtomicUsize::new(0)),
            message: message.into(),
        });
        self
    }

    /// Returns the deterministic pre-analysis delay for one Crash Log.
    pub(crate) fn analysis_delay(&self, discovery_index: usize) -> Option<Duration> {
        self.analysis_delays.get(&discovery_index).copied()
    }

    /// Returns the deterministic analysis failure for one Crash Log.
    pub(crate) fn analysis_failure(&self, discovery_index: usize) -> Option<&str> {
        self.analysis_failures
            .get(&discovery_index)
            .map(String::as_str)
    }

    /// Constructs the raw lower-layer error when execution reaches the requested seam.
    pub(crate) fn infrastructure_failure(
        &self,
        fault: InfrastructureFault,
    ) -> Option<ScanLogError> {
        self.infrastructure_failure
            .as_ref()
            .filter(|failure| failure.fault == fault)
            .map(InjectedInfrastructureFailure::raw_error)
    }

    /// Returns a movement error once the configured successful-move boundary is reached.
    pub(crate) fn movement_failure(&self) -> Option<String> {
        self.movement_failure.as_ref().and_then(|failure| {
            (failure.observed_moves.load(Ordering::Acquire) >= failure.successful_moves)
                .then(|| failure.message.clone())
        })
    }

    /// Records one successfully moved artifact for movement fault sequencing.
    pub(crate) fn record_movement_success(&self) {
        if let Some(failure) = &self.movement_failure {
            failure.observed_moves.fetch_add(1, Ordering::AcqRel);
        }
    }
}

/// Internal lifecycle seams available to request-scoped infrastructure fault tests.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum InfrastructureFault {
    RequestValidation,
    Discovery,
    Intake,
    FormIdDatabaseAccess,
    Initialization,
    InternalInvariant,
}

/// Raw run-wide failure injected before production classification captures its context.
#[derive(Clone, Debug)]
struct InjectedInfrastructureFailure {
    fault: InfrastructureFault,
    message: String,
}

impl InjectedInfrastructureFailure {
    /// Builds the same error variant a lower layer can return at the selected seam.
    fn raw_error(&self) -> ScanLogError {
        match self.fault {
            InfrastructureFault::RequestValidation => {
                ScanLogError::ValidationError(self.message.clone())
            }
            InfrastructureFault::Discovery => {
                ScanLogError::IoError(std::io::Error::other(self.message.clone()))
            }
            InfrastructureFault::Intake => ScanLogError::ConfigError(self.message.clone()),
            InfrastructureFault::FormIdDatabaseAccess => {
                ScanLogError::DatabaseError(self.message.clone())
            }
            InfrastructureFault::Initialization => {
                ScanLogError::AnalysisError(self.message.clone())
            }
            InfrastructureFault::InternalInvariant => ScanLogError::Internal(self.message.clone()),
        }
    }
}

#[derive(Clone, Debug)]
struct InjectedMovementFailure {
    successful_moves: usize,
    observed_moves: Arc<AtomicUsize>,
    message: String,
}

pub(crate) const FIXTURE_LOG_SMALL: &str = include_str!("../benches/fixtures/crash-0DB9300.log");

pub(crate) fn write_fixture_log(temp: &tempfile::TempDir, filename: &str) -> PathBuf {
    let log_path = temp.path().join(filename);
    std::fs::write(&log_path, FIXTURE_LOG_SMALL).expect("fixture log should be written");
    log_path
}

/// Writes the small Crash Log fixture into an explicitly selected discovery directory.
pub(crate) fn write_fixture_log_at(directory: &Path, filename: &str) -> PathBuf {
    std::fs::create_dir_all(directory).expect("fixture directory should be created");
    let log_path = directory.join(filename);
    std::fs::write(&log_path, FIXTURE_LOG_SMALL).expect("fixture log should be written");
    log_path
}

pub(crate) fn write_minimal_yaml_tree(root: &Path, data: &Path) {
    std::fs::create_dir_all(data.join("databases")).expect("database dir should be created");
    std::fs::write(
        data.join("databases").join("CLASSIC Main.yaml"),
        concat!(
            "CLASSIC_Info:\n",
            "  version: \"v9.1.0\"\n",
            "  version_date: \"2026-06-30\"\n",
            "CLASSIC_Interface:\n",
            "  autoscan_text_Fallout4: \"Autoscan Fallout 4\"\n",
            "catch_log_records:\n",
            "  - TESObjectREFR\n",
            "exclude_log_records:\n",
            "  - '(void*)'\n",
        ),
    )
    .expect("main YAML should be written");
    std::fs::write(
        data.join("databases").join("CLASSIC Fallout4.yaml"),
        concat!(
            "Game_Info:\n",
            "  XSE_Acronym: \"F4SE\"\n",
            "  GameVersion: \"1.10.163\"\n",
            "  CRASHGEN_LatestVer: \"1.28.6\"\n",
            "  CRASHGEN_LogName: \"Buffout 4\"\n",
            "  Main_Root_Name: \"Fallout4\"\n",
            "Crashlog_Plugins_Exclude: []\n",
            "Crashlog_Records_Exclude: []\n",
            "Crashgen_Registry:\n",
            "  default:\n",
            "    display_section: \"\"\n",
            "    ignore_keys: []\n",
            "    checks: []\n",
        ),
    )
    .expect("game YAML should be written");
    std::fs::write(
        root.join("CLASSIC Ignore.yaml"),
        "CLASSIC_Ignore_Fallout4:\n  - IgnoreThis.dll\n",
    )
    .expect("ignore YAML should be written");
}
