//! The one Crash Log Scan Launch operation and the request it returns.

use crate::diagnostic::CrashLogScanLaunchDiagnostic;
use crate::error::CrashLogScanLaunchError;
use crate::overrides::{CrashLogScanLaunchOverrides, MaxConcurrency};
use classic_scanlog_core::scan_run::contract::{Configuration, Options, Request};
use classic_scanlog_core::{
    CrashLogScanFacts, CrashLogScanSetupContext, StandardCrashLogScanSource,
    StandardUnsolvedLogsIntent, TargetedCrashLogScanSource,
};
use classic_user_settings_core::{CrashLogScanSettings, GameSetupSettings, UserSettings};
use std::path::{Path, PathBuf};

/// Which Crash Logs a launch scans.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CrashLogScanIntent {
    /// Scan CLASSIC's normal locations under the Installation Root, plus the custom scan
    /// folder when one is saved or overridden.
    Standard,
    /// Scan exactly these user-selected files or folders, in this order.
    ///
    /// An empty list is rejected with [`CrashLogScanLaunchError::TargetedWithoutInputs`].
    Targeted(Vec<PathBuf>),
}

/// The Crash Log Scan Run request a launch produced, with the diagnostics to show beside it.
///
/// The request is ready to execute. When FCX Mode is enabled it already carries its Crash
/// Log Scan Setup Context, which [`Self::setup_context`] exposes without unpacking the
/// request.
#[derive(Debug, Clone)]
pub struct CrashLogScanLaunchRequest {
    request: Request,
    diagnostics: Vec<CrashLogScanLaunchDiagnostic>,
}

impl CrashLogScanLaunchRequest {
    /// Returns the Crash Log Scan Run request.
    #[must_use]
    pub const fn request(&self) -> &Request {
        &self.request
    }

    /// Returns the Crash Log Scan Setup Context when FCX Mode is enabled, otherwise `None`.
    #[must_use]
    pub const fn setup_context(&self) -> Option<&CrashLogScanSetupContext> {
        match &self.request {
            Request::Standard(request) => request.setup_context(),
            Request::Targeted(request) => request.setup_context(),
        }
    }

    /// Returns the launch diagnostics, in the order they were produced.
    #[must_use]
    pub fn diagnostics(&self) -> &[CrashLogScanLaunchDiagnostic] {
        &self.diagnostics
    }

    /// Consumes the launch and returns the request alone, for execution.
    #[must_use]
    pub fn into_request(self) -> Request {
        self.request
    }

    /// Consumes the launch and returns the request and its diagnostics.
    #[must_use]
    pub fn into_parts(self) -> (Request, Vec<CrashLogScanLaunchDiagnostic>) {
        (self.request, self.diagnostics)
    }
}

/// Builds the Crash Log Scan Run request for one launch.
///
/// Opens User Settings read-only under `installation_root` and merges them with
/// `overrides`, where a supplied override always wins over the saved value. It never
/// writes User Settings and never runs the scan.
///
/// - A Standard scan's base folder is always `installation_root`; the scan path override
///   and the saved custom scan folder are the explicit way to scan elsewhere.
/// - FormID database rows come from User Settings' game-aware read for the scanned game,
///   so a Fallout 4 VR scan reads the shared Fallout 4 rows.
/// - Degraded User Settings (malformed, newer, needing migration) are not an error: the
///   request is built from the values User Settings projected for that document, and its
///   diagnostics are reported as [`CrashLogScanLaunchDiagnostic::UserSettings`].
///
/// # Errors
///
/// Returns [`CrashLogScanLaunchError::TargetedWithoutInputs`] for a Targeted intent with
/// no inputs. User Settings are not opened in that case.
pub fn prepare_launch(
    installation_root: impl AsRef<Path>,
    intent: CrashLogScanIntent,
    overrides: &CrashLogScanLaunchOverrides,
) -> Result<CrashLogScanLaunchRequest, CrashLogScanLaunchError> {
    if matches!(&intent, CrashLogScanIntent::Targeted(inputs) if inputs.is_empty()) {
        return Err(CrashLogScanLaunchError::TargetedWithoutInputs);
    }
    let installation_root = installation_root.as_ref();
    let settings = UserSettings::open(installation_root);
    let scan = settings.crash_log_scan_settings();
    let setup = settings.game_setup_settings();

    let configuration = configuration(installation_root, scan, setup, overrides);
    let setup_context = scan.fcx_mode().then(|| setup_context(setup));
    let request = match intent {
        CrashLogScanIntent::Standard => {
            let source = StandardCrashLogScanSource {
                base_directory: installation_root.to_path_buf(),
                custom_scan_directory: overrides
                    .scan_path()
                    .map(Path::to_path_buf)
                    .or_else(|| scan.custom_scan_input().map(PathBuf::from)),
                configured_documents_root: setup.documents_root().map(PathBuf::from),
            };
            let unsolved_logs = if scan.move_unsolved_logs() {
                StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault
            } else {
                StandardUnsolvedLogsIntent::LeaveInPlace
            };
            match setup_context {
                Some(context) => {
                    Request::standard_with_fcx(configuration, source, unsolved_logs, context)
                }
                None => Request::standard(configuration, source, unsolved_logs),
            }
        }
        CrashLogScanIntent::Targeted(inputs) => {
            let source = TargetedCrashLogScanSource { inputs };
            match setup_context {
                Some(context) => Request::targeted_with_fcx(configuration, source, context),
                None => Request::targeted(configuration, source),
            }
        }
    };

    let diagnostics = settings
        .diagnostics()
        .iter()
        .cloned()
        .map(CrashLogScanLaunchDiagnostic::UserSettings)
        .collect();
    Ok(CrashLogScanLaunchRequest {
        request,
        diagnostics,
    })
}

/// Merges saved scan settings with the overrides into the shared run configuration.
fn configuration(
    installation_root: &Path,
    scan: &CrashLogScanSettings,
    setup: &GameSetupSettings,
    overrides: &CrashLogScanLaunchOverrides,
) -> Configuration {
    let game = overrides.game().unwrap_or_else(|| setup.managed_game());
    let game_version = overrides
        .game_version()
        .unwrap_or_else(|| scan.game_version_selection());
    let max_concurrency = overrides.max_concurrency().unwrap_or_else(|| {
        // Saved Max Concurrent Scans uses the same zero-means-adaptive convention.
        MaxConcurrency::from_count(usize::try_from(scan.max_concurrent_scans()).unwrap_or(0))
    });
    Configuration {
        installation_root: installation_root.to_path_buf(),
        game,
        game_version: game_version.as_str().to_string(),
        options: Options::new(
            scan.formid_value_lookup() || overrides.show_formid_values(),
            scan.simplify_logs() || overrides.simplify_logs(),
        ),
        scan_facts: CrashLogScanFacts {
            formid_database_paths: scan
                .formid_databases_for_game(game)
                .into_iter()
                .map(PathBuf::from)
                .collect(),
            unsolved_logs_destination: scan.unsolved_logs_destination().map(PathBuf::from),
        },
        max_concurrent: max_concurrency.limit(),
    }
}

/// Projects the saved setup folders into the run-scoped FCX setup facts.
///
/// Missing folders stay `None`: FCX setup validation reports them in the Crash Log Scan
/// Setup Result rather than the launch refusing to start. The XSE log is not resolved here
/// yet, so it is left for setup validation to discover.
fn setup_context(setup: &GameSetupSettings) -> CrashLogScanSetupContext {
    CrashLogScanSetupContext {
        game_root: setup.game_root().map(PathBuf::from),
        docs_root: setup.documents_root().map(PathBuf::from),
        game_exe_path: setup.game_executable().map(PathBuf::from),
        xse_log_path: None,
    }
}
