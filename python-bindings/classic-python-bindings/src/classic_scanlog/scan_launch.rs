//! Crash Log Scan Launch adapter for the `classic_scanlog` facade.
//!
//! Every merge rule lives in `classic-scan-launch`. This module converts Python overrides
//! into its builder and exposes the launched request read-only, plus an executable
//! `ScanRunRequest` copy.

use crate::classic_scanlog::scan_run::{
    PyScanRunDisplayLine, PyScanRunRequest, PyScanRunSetupContext, display_lines_to_py,
    path_to_string, required_path, typed_game_id_to_core,
};
use classic_scan_launch::{
    CrashLogScanIntent, CrashLogScanLaunchDiagnostic, CrashLogScanLaunchError,
    CrashLogScanLaunchOverrides, CrashLogScanLaunchRequest, GameVersionSelection, MaxConcurrency,
    prepare_launch_in_scopes,
};
use classic_scan_presentation::render_launch_diagnostics;
use classic_scanlog_core::StandardUnsolvedLogsIntent;
use classic_scanlog_core::scan_run::contract::Request;
use classic_vocabulary::Vocabulary;
use pyo3::create_exception;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;
use std::path::PathBuf;

create_exception!(
    classic_scanlog,
    ScanRunLaunchError,
    PyValueError,
    "A Crash Log Scan Launch could not produce a request; each launch error kind is a subclass."
);
create_exception!(
    classic_scanlog,
    ScanRunLaunchTargetedWithoutInputsError,
    ScanRunLaunchError,
    "A Targeted Crash Log Scan Launch named no inputs."
);
create_exception!(
    classic_scanlog,
    ScanRunLaunchXseLogInspectError,
    ScanRunLaunchError,
    "FCX Mode is on and the XSE log location could not be inspected (not mere absence)."
);

/// Optional per-run values that win over saved User Settings for one launch.
///
/// `game` must be a `classic_shared.GameId`. `game_version` takes a User Settings
/// game-version token (`auto`, `Original`, `NextGen`, `AnniversaryEdition`, `VR`).
/// `max_concurrent=0` explicitly requests adaptive concurrency, which overrides a saved
/// limit. `show_formid_values`, `simplify_logs` and `fcx_mode` are supplied-as-on: `True`
/// turns the option on for this run; `False` keeps the saved value. `no_scan_path=True`
/// scans no custom scan folder for this run, withholding a saved one (a cleared custom scan
/// folder input); it cannot be combined with `scan_path`.
#[pyclass(name = "ScanRunLaunchOverrides", from_py_object)]
#[derive(Clone, Default)]
pub struct PyScanRunLaunchOverrides {
    inner: CrashLogScanLaunchOverrides,
}

#[pymethods]
impl PyScanRunLaunchOverrides {
    /// Creates overrides; every argument is optional and absent values keep the saved ones.
    ///
    /// # Errors
    ///
    /// Raises `TypeError`/`ValueError` for a `game` that is not a `classic_shared.GameId`,
    /// and `ValueError` for an unknown game-version token, a blank `scan_path`, or
    /// `scan_path` together with `no_scan_path=True`.
    #[new]
    #[pyo3(signature = (game=None, game_version=None, scan_path=None, max_concurrent=None, show_formid_values=false, simplify_logs=false, fcx_mode=false, no_scan_path=false))]
    // One parameter per override keeps the Python constructor keyword-compatible with every
    // other binding's override record.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        game: Option<&Bound<'_, PyAny>>,
        game_version: Option<String>,
        scan_path: Option<String>,
        max_concurrent: Option<usize>,
        show_formid_values: bool,
        simplify_logs: bool,
        fcx_mode: bool,
        no_scan_path: bool,
    ) -> PyResult<Self> {
        // The core builder lets the last scan path override win; keyword arguments have no
        // order, so a folder and "no folder" together are unrepresentable input.
        if scan_path.is_some() && no_scan_path {
            return Err(PyValueError::new_err(
                "scan_path and no_scan_path cannot both be supplied",
            ));
        }
        let mut inner = CrashLogScanLaunchOverrides::new();
        if let Some(game) = game {
            inner = inner.with_game(typed_game_id_to_core(game)?);
        }
        if let Some(game_version) = game_version {
            let selection = GameVersionSelection::parse(&game_version).ok_or_else(|| {
                PyValueError::new_err(format!("unsupported game_version override: {game_version}"))
            })?;
            inner = inner.with_game_version(selection);
        }
        if let Some(scan_path) = scan_path {
            inner = inner.with_scan_path(required_path(scan_path, "scan_path")?);
        }
        if no_scan_path {
            inner = inner.with_no_scan_path();
        }
        if let Some(max_concurrent) = max_concurrent {
            inner = inner.with_max_concurrency(MaxConcurrency::from_count(max_concurrent));
        }
        if show_formid_values {
            inner = inner.with_show_formid_values();
        }
        if simplify_logs {
            inner = inner.with_simplify_logs();
        }
        if fcx_mode {
            inner = inner.with_fcx_mode();
        }
        Ok(Self { inner })
    }
}

/// One non-fatal launch diagnostic; the launch still produced a scannable request.
#[pyclass(name = "ScanRunLaunchDiagnostic", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyScanRunLaunchDiagnostic {
    /// Which launch rule produced it, as a frozen Vocabulary Token: `user_settings`,
    /// `game_version_not_applied`, `fcx_mode_not_applied`,
    /// `custom_scan_folder_not_applied`, or `setup_folders_not_applied`.
    #[pyo3(get)]
    kind: &'static str,
    /// Stable machine-readable code (the User Settings code for `user_settings`, the
    /// kind's token otherwise).
    #[pyo3(get)]
    code: String,
    /// Human-readable context. Prose; branch on `kind` and `code` instead.
    #[pyo3(get)]
    message: String,
}

/// The Crash Log Scan Run request a launch built, with its launch diagnostics.
///
/// The read-only properties show exactly what the launch decided; `request()` returns an
/// executable `ScanRunRequest` for `scan_run_execute`.
#[pyclass(name = "ScanRunLaunch", frozen, skip_from_py_object)]
pub struct PyScanRunLaunch {
    inner: CrashLogScanLaunchRequest,
}

#[pymethods]
impl PyScanRunLaunch {
    /// Launches a Standard Crash Log Scan from saved User Settings and `overrides`.
    ///
    /// Opens User Settings under `installation_root` read-only and never writes them; the
    /// Standard base folder is always `installation_root`. Degraded User Settings still
    /// produce a launch, with their diagnostics.
    ///
    /// # Errors
    ///
    /// Raises `ValueError` for a blank `installation_root`, and
    /// `ScanRunLaunchXseLogInspectError` (a `ScanRunLaunchError`) when FCX Mode is on and the
    /// XSE log location cannot be inspected for a reason other than absence.
    #[staticmethod]
    #[pyo3(signature = (installation_root, overrides=None))]
    pub fn standard(
        installation_root: String,
        overrides: Option<PyRef<'_, PyScanRunLaunchOverrides>>,
    ) -> PyResult<Self> {
        launch(installation_root, CrashLogScanIntent::Standard, overrides)
    }

    /// Launches a Targeted Crash Log Scan of exactly `inputs`, in order.
    ///
    /// # Errors
    ///
    /// Raises `ScanRunLaunchTargetedWithoutInputsError` (a `ScanRunLaunchError`) for an
    /// empty `inputs` list, `ScanRunLaunchXseLogInspectError` as for `standard`, and
    /// `ValueError` for a blank `installation_root`.
    #[staticmethod]
    #[pyo3(signature = (installation_root, inputs, overrides=None))]
    pub fn targeted(
        installation_root: String,
        inputs: Vec<String>,
        overrides: Option<PyRef<'_, PyScanRunLaunchOverrides>>,
    ) -> PyResult<Self> {
        launch(
            installation_root,
            CrashLogScanIntent::Targeted(inputs.into_iter().map(PathBuf::from).collect()),
            overrides,
        )
    }

    /// Returns `standard` or `targeted`.
    #[getter]
    pub fn intent(&self) -> &'static str {
        match self.inner.request() {
            Request::Standard(_) => "standard",
            Request::Targeted(_) => "targeted",
        }
    }

    /// Returns the scanned game as a `classic_shared.GameId`.
    #[getter]
    pub fn game<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let game = self.inner.request().configuration().game;
        PyModule::import(py, "classic_shared")?
            .getattr("GameId")?
            .getattr(game.as_str())
    }

    /// Returns the selected game-version token.
    #[getter]
    pub fn game_version(&self) -> String {
        self.inner.request().configuration().game_version.clone()
    }

    /// Returns whether FormID values are looked up during the run.
    #[getter]
    pub fn show_formid_values(&self) -> bool {
        self.inner
            .request()
            .configuration()
            .options
            .show_formid_values
    }

    /// Returns whether Crash Logs are simplified during the run.
    #[getter]
    pub fn simplify_logs(&self) -> bool {
        self.inner.request().configuration().options.simplify_logs
    }

    /// Returns the FormID database rows that apply to the scanned game, as persisted.
    #[getter]
    pub fn formid_database_paths(&self) -> Vec<String> {
        self.inner
            .request()
            .configuration()
            .scan_facts
            .formid_database_paths
            .iter()
            .map(|path| path_to_string(path))
            .collect()
    }

    /// Returns the saved Unsolved Logs Destination, if any.
    #[getter]
    pub fn unsolved_logs_destination(&self) -> Option<String> {
        self.inner
            .request()
            .configuration()
            .scan_facts
            .unsolved_logs_destination
            .as_deref()
            .map(path_to_string)
    }

    /// Returns the explicit concurrency limit, or `None` for adaptive concurrency.
    #[getter]
    pub fn max_concurrent(&self) -> Option<usize> {
        self.inner.request().configuration().max_concurrent
    }

    /// Returns the Standard base folder (always the Installation Root), or `None` when Targeted.
    #[getter]
    pub fn base_directory(&self) -> Option<String> {
        self.standard_source(|source| Some(path_to_string(&source.base_directory)))
    }

    /// Returns the Standard custom scan folder, if any.
    #[getter]
    pub fn custom_scan_directory(&self) -> Option<String> {
        self.standard_source(|source| source.custom_scan_directory.as_deref().map(path_to_string))
    }

    /// Returns the Standard configured documents root, if any.
    #[getter]
    pub fn configured_documents_root(&self) -> Option<String> {
        self.standard_source(|source| {
            source
                .configured_documents_root
                .as_deref()
                .map(path_to_string)
        })
    }

    /// Returns the Standard Unsolved Logs intent token, or `None` when Targeted.
    ///
    /// One of `leave_in_place`, `move_to_configured_or_default` or `move_to_custom`.
    #[getter]
    pub fn unsolved_logs(&self) -> Option<&'static str> {
        match self.inner.request() {
            Request::Standard(request) => Some(match request.unsolved_logs() {
                StandardUnsolvedLogsIntent::LeaveInPlace => "leave_in_place",
                StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault => {
                    "move_to_configured_or_default"
                }
                StandardUnsolvedLogsIntent::MoveToCustom(_) => "move_to_custom",
            }),
            Request::Targeted(_) => None,
        }
    }

    /// Returns the Targeted inputs in order, or `None` for a Standard request.
    #[getter]
    pub fn targeted_inputs(&self) -> Option<Vec<String>> {
        match self.inner.request() {
            Request::Standard(_) => None,
            Request::Targeted(request) => Some(
                request
                    .source()
                    .inputs
                    .iter()
                    .map(|path| path_to_string(path))
                    .collect(),
            ),
        }
    }

    /// Returns whether the request enables FCX Mode.
    #[getter]
    pub fn fcx_enabled(&self) -> bool {
        self.inner.setup_context().is_some()
    }

    /// Returns the Crash Log Scan Setup Context when FCX Mode is enabled, otherwise `None`.
    #[getter]
    pub fn setup_context(&self) -> Option<PyScanRunSetupContext> {
        self.inner.setup_context().map(|context| {
            PyScanRunSetupContext::new(
                context.game_root.as_deref().map(path_to_string),
                context.docs_root.as_deref().map(path_to_string),
                context.game_exe_path.as_deref().map(path_to_string),
                context.xse_log_path.as_deref().map(path_to_string),
            )
        })
    }

    /// Returns the launch diagnostics, in the order they were produced.
    #[getter]
    pub fn diagnostics(&self) -> Vec<PyScanRunLaunchDiagnostic> {
        self.inner
            .diagnostics()
            .iter()
            .map(diagnostic_to_py)
            .collect()
    }

    /// Returns the launch diagnostics rendered as Display Content, one line per
    /// diagnostic in the same order. Show these rather than phrasing `diagnostics` in
    /// Python.
    #[getter]
    pub fn display_lines(&self) -> Vec<PyScanRunDisplayLine> {
        display_lines_to_py(&render_launch_diagnostics(self.inner.diagnostics()))
    }

    /// Returns an executable copy of the launched request.
    pub fn request(&self) -> PyScanRunRequest {
        PyScanRunRequest {
            inner: self.inner.request().clone(),
        }
    }
}

impl PyScanRunLaunch {
    /// Reads one Standard source field, or `None` for a Targeted request.
    fn standard_source(
        &self,
        read: impl FnOnce(&classic_scanlog_core::StandardCrashLogScanSource) -> Option<String>,
    ) -> Option<String> {
        match self.inner.request() {
            Request::Standard(request) => read(request.source()),
            Request::Targeted(_) => None,
        }
    }
}

/// Converts Python inputs and runs the one Rust launch operation.
fn launch(
    installation_root: String,
    intent: CrashLogScanIntent,
    overrides: Option<PyRef<'_, PyScanRunLaunchOverrides>>,
) -> PyResult<PyScanRunLaunch> {
    let installation_root = required_path(installation_root, "installation_root")?;
    let overrides = overrides
        .map(|overrides| overrides.inner.clone())
        .unwrap_or_default();
    // The facade's own scopes, the same ones `scan_run_execute` runs in, so the FCX setup
    // facts this launch gathers come from the snapshot its run will read.
    prepare_launch_in_scopes(
        installation_root,
        intent,
        &overrides,
        &crate::classic_scanlog::SCANLOG_VERSION_REGISTRY_SCOPE,
        &crate::classic_scanlog::SCANLOG_YAML_FILE_SCOPE,
    )
    .map(|inner| PyScanRunLaunch { inner })
    .map_err(launch_error_to_py)
}

/// Raises the typed exception subclass for one launch error.
fn launch_error_to_py(error: CrashLogScanLaunchError) -> PyErr {
    let message = error.to_string();
    match error {
        CrashLogScanLaunchError::TargetedWithoutInputs => {
            ScanRunLaunchTargetedWithoutInputsError::new_err(message)
        }
        CrashLogScanLaunchError::XseLogInspect { .. } => {
            ScanRunLaunchXseLogInspectError::new_err(message)
        }
    }
}

/// Projects one launch diagnostic.
fn diagnostic_to_py(diagnostic: &CrashLogScanLaunchDiagnostic) -> PyScanRunLaunchDiagnostic {
    PyScanRunLaunchDiagnostic {
        kind: diagnostic.kind().as_str(),
        code: diagnostic.code().to_string(),
        message: diagnostic.message().to_string(),
    }
}

/// Registers the launch classes and exceptions on the `classic_scanlog` facade.
pub(crate) fn register_scan_launch_exports(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyScanRunLaunchOverrides>()?;
    m.add_class::<PyScanRunLaunchDiagnostic>()?;
    m.add_class::<PyScanRunLaunch>()?;
    m.add(
        "ScanRunLaunchError",
        m.py().get_type::<ScanRunLaunchError>(),
    )?;
    m.add(
        "ScanRunLaunchTargetedWithoutInputsError",
        m.py().get_type::<ScanRunLaunchTargetedWithoutInputsError>(),
    )?;
    m.add(
        "ScanRunLaunchXseLogInspectError",
        m.py().get_type::<ScanRunLaunchXseLogInspectError>(),
    )?;
    Ok(())
}

// Keep the repository's required sibling-test declaration intact under rustfmt.
#[rustfmt::skip]
#[cfg(test)] #[path = "scan_launch_tests.rs"] mod tests;
