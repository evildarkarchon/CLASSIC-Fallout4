//! Final Crash Log Scan Run contract adapter for Python.
//!
//! This module keeps request construction invariant-preserving while leaving
//! the complete scan lifecycle in `classic-scanlog-core`.

use crate::fcx_handler::PyConfigIssue;
use classic_config_core::{
    InspectedYamlDataFile, InstalledYamlDataProvenance, InstalledYamlDataRole,
    YamlDataContentIdentity,
};
use classic_scanlog_core::scan_run::contract;
use classic_scanlog_core::{
    CrashLogScanDiscoveryResult, CrashLogScanDiscoverySource, CrashLogScanFacts,
    CrashLogScanRunStatus, CrashLogScanSetupContext, CrashLogScanSetupResult, ScanProgressPhase,
    StandardCrashLogScanSource, StandardUnsolvedLogsIntent, TargetedCrashLogScanSource,
};
use classic_shared::without_gil_block_on;
use classic_shared_core::GameId;
use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyModule;
use std::path::PathBuf;

/// Explicit configuration shared by Standard and Targeted requests.
#[pyclass(name = "ScanRunConfiguration", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunConfiguration {
    installation_root: String,
    game: classic_shared_core::GameId,
    game_version: String,
    show_formid_values: bool,
    simplify_logs: bool,
    formid_database_paths: Vec<String>,
    unsolved_logs_destination: Option<String>,
    max_concurrent: Option<usize>,
}

#[pymethods]
impl PyScanRunConfiguration {
    /// Creates explicit scan facts without reopening User Settings.
    ///
    /// `game` must be one of the typed values exported by `classic_shared.GameId`.
    ///
    /// # Errors
    ///
    /// Returns `TypeError` for another Python type, `ValueError` for an unrecognized typed value,
    /// or the underlying import error when `classic_shared` is unavailable.
    #[new]
    #[pyo3(signature = (installation_root, game, game_version, show_formid_values, simplify_logs, formid_database_paths, unsolved_logs_destination=None, max_concurrent=None))]
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        installation_root: String,
        game: &Bound<'_, PyAny>,
        game_version: String,
        show_formid_values: bool,
        simplify_logs: bool,
        formid_database_paths: Vec<String>,
        unsolved_logs_destination: Option<String>,
        max_concurrent: Option<usize>,
    ) -> PyResult<Self> {
        Ok(Self {
            installation_root,
            game: typed_game_id_to_core(game)?,
            game_version,
            show_formid_values,
            simplify_logs,
            formid_database_paths,
            unsolved_logs_destination,
            max_concurrent,
        })
    }
}

/// Converts an authentic `classic_shared.GameId` without reparsing its display text.
fn typed_game_id_to_core(game: &Bound<'_, PyAny>) -> PyResult<GameId> {
    let shared = PyModule::import(game.py(), "classic_shared")?;
    let game_id_type = shared.getattr("GameId")?;
    if !game.is_instance(&game_id_type)? {
        return Err(PyTypeError::new_err(
            "game must be an instance of classic_shared.GameId",
        ));
    }

    for (attribute, core) in [
        ("Fallout4", GameId::Fallout4),
        ("Fallout4VR", GameId::Fallout4VR),
        ("Skyrim", GameId::Skyrim),
        ("Starfield", GameId::Starfield),
    ] {
        if game.eq(game_id_type.getattr(attribute)?)? {
            return Ok(core);
        }
    }

    Err(PyValueError::new_err(
        "game is not a recognized classic_shared.GameId value",
    ))
}

/// Standard discovery inputs for one scan run.
#[pyclass(name = "ScanRunStandardSource", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunStandardSource {
    base_directory: String,
    custom_scan_directory: Option<String>,
    configured_documents_root: Option<String>,
}

#[pymethods]
impl PyScanRunStandardSource {
    /// Creates explicit Standard discovery facts.
    #[new]
    #[pyo3(signature = (base_directory, custom_scan_directory=None, configured_documents_root=None))]
    pub fn new(
        base_directory: String,
        custom_scan_directory: Option<String>,
        configured_documents_root: Option<String>,
    ) -> Self {
        Self {
            base_directory,
            custom_scan_directory,
            configured_documents_root,
        }
    }
}

/// Targeted discovery inputs in caller-supplied order.
#[pyclass(name = "ScanRunTargetedSource", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunTargetedSource {
    inputs: Vec<String>,
}

#[pymethods]
impl PyScanRunTargetedSource {
    /// Creates explicit Targeted discovery facts.
    #[new]
    pub fn new(inputs: Vec<String>) -> Self {
        Self { inputs }
    }
}

/// Explicit run-scoped FCX setup facts.
#[pyclass(name = "ScanRunSetupContext", from_py_object)]
#[derive(Clone, Default)]
pub struct PyScanRunSetupContext {
    game_root: Option<String>,
    docs_root: Option<String>,
    game_exe_path: Option<String>,
    xse_log_path: Option<String>,
}

#[pymethods]
impl PyScanRunSetupContext {
    /// Creates explicit setup facts without consulting process-global state.
    #[new]
    #[pyo3(signature = (game_root=None, docs_root=None, game_exe_path=None, xse_log_path=None))]
    pub fn new(
        game_root: Option<String>,
        docs_root: Option<String>,
        game_exe_path: Option<String>,
        xse_log_path: Option<String>,
    ) -> Self {
        Self {
            game_root,
            docs_root,
            game_exe_path,
            xse_log_path,
        }
    }

    /// Returns the game installation root when supplied.
    #[getter]
    pub fn game_root(&self) -> Option<String> {
        self.game_root.clone()
    }

    /// Returns the game documents root when supplied.
    #[getter]
    pub fn docs_root(&self) -> Option<String> {
        self.docs_root.clone()
    }

    /// Returns the game executable path when supplied.
    #[getter]
    pub fn game_exe_path(&self) -> Option<String> {
        self.game_exe_path.clone()
    }

    /// Returns the optional XSE log detection hint.
    #[getter]
    pub fn xse_log_path(&self) -> Option<String> {
        self.xse_log_path.clone()
    }
}

/// Opaque Standard-only Unsolved Logs policy.
#[pyclass(name = "ScanRunUnsolvedLogs")]
pub struct PyScanRunUnsolvedLogs {
    inner: StandardUnsolvedLogsIntent,
}

#[pymethods]
impl PyScanRunUnsolvedLogs {
    /// Creates a policy that leaves failed artifacts in place.
    #[staticmethod]
    pub fn leave_in_place() -> Self {
        Self {
            inner: StandardUnsolvedLogsIntent::LeaveInPlace,
        }
    }

    /// Creates a policy that uses the configured or Rust-default destination.
    #[staticmethod]
    pub fn move_to_configured_or_default() -> Self {
        Self {
            inner: StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
        }
    }

    /// Creates a policy that uses one caller-selected destination.
    #[staticmethod]
    pub fn move_to_custom(destination: String) -> PyResult<Self> {
        Ok(Self {
            inner: StandardUnsolvedLogsIntent::MoveToCustom(required_path(
                destination,
                "destination",
            )?),
        })
    }
}

/// Opaque invariant-preserving request for the final scan-run operation.
#[pyclass(name = "ScanRunRequest")]
pub struct PyScanRunRequest {
    pub(crate) inner: contract::Request,
}

#[pymethods]
impl PyScanRunRequest {
    /// Returns the stable tagged request intent.
    #[getter]
    pub fn intent(&self) -> &'static str {
        match self.inner {
            contract::Request::Standard(_) => "standard",
            contract::Request::Targeted(_) => "targeted",
        }
    }

    /// Constructs a non-FCX Standard request.
    #[staticmethod]
    pub fn standard(
        configuration: PyRef<'_, PyScanRunConfiguration>,
        source: PyRef<'_, PyScanRunStandardSource>,
        unsolved_logs: PyRef<'_, PyScanRunUnsolvedLogs>,
    ) -> PyResult<Self> {
        Ok(Self {
            inner: contract::Request::standard(
                configuration_to_core(&configuration)?,
                standard_source_to_core(&source)?,
                unsolved_logs.inner.clone(),
            ),
        })
    }

    /// Constructs an FCX-enabled Standard request with required setup facts.
    #[staticmethod]
    pub fn standard_with_fcx(
        configuration: PyRef<'_, PyScanRunConfiguration>,
        source: PyRef<'_, PyScanRunStandardSource>,
        unsolved_logs: PyRef<'_, PyScanRunUnsolvedLogs>,
        setup_context: PyRef<'_, PyScanRunSetupContext>,
    ) -> PyResult<Self> {
        Ok(Self {
            inner: contract::Request::standard_with_fcx(
                configuration_to_core(&configuration)?,
                standard_source_to_core(&source)?,
                unsolved_logs.inner.clone(),
                setup_context_to_core(&setup_context),
            ),
        })
    }

    /// Constructs a non-FCX Targeted request with no movement capability.
    #[staticmethod]
    pub fn targeted(
        configuration: PyRef<'_, PyScanRunConfiguration>,
        source: PyRef<'_, PyScanRunTargetedSource>,
    ) -> PyResult<Self> {
        Ok(Self {
            inner: contract::Request::targeted(
                configuration_to_core(&configuration)?,
                targeted_source_to_core(&source),
            ),
        })
    }

    /// Constructs an FCX-enabled Targeted request with no movement capability.
    #[staticmethod]
    pub fn targeted_with_fcx(
        configuration: PyRef<'_, PyScanRunConfiguration>,
        source: PyRef<'_, PyScanRunTargetedSource>,
        setup_context: PyRef<'_, PyScanRunSetupContext>,
    ) -> PyResult<Self> {
        Ok(Self {
            inner: contract::Request::targeted_with_fcx(
                configuration_to_core(&configuration)?,
                targeted_source_to_core(&source),
                setup_context_to_core(&setup_context),
            ),
        })
    }
}

/// Opaque monotonic cancellation control for one final-contract scan run.
#[pyclass(name = "ScanRunCancellation")]
pub struct PyScanRunCancellation {
    pub(crate) inner: contract::Cancellation,
}

#[pymethods]
impl PyScanRunCancellation {
    /// Creates an uncancelled control for one scan run.
    #[new]
    pub fn new() -> Self {
        Self {
            inner: contract::Cancellation::new(),
        }
    }

    /// Requests cancellation at the next Rust-owned safe seam.
    pub fn cancel(&self) {
        self.inner.cancel();
    }

    /// Returns whether cancellation has been requested.
    #[getter]
    pub fn is_cancelled(&self) -> bool {
        self.inner.is_cancelled()
    }
}

impl Default for PyScanRunCancellation {
    fn default() -> Self {
        Self::new()
    }
}

/// Python-compatible Targeted input rejection.
#[pyclass(name = "ScanRunRejectedInput", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunRejectedInput {
    path: String,
    reason: String,
}

#[pymethods]
impl PyScanRunRejectedInput {
    /// Returns the original rejected path.
    #[getter]
    pub fn path(&self) -> String {
        self.path.clone()
    }

    /// Returns the human-readable rejection reason.
    #[getter]
    pub fn reason(&self) -> String {
        self.reason.clone()
    }
}

/// Python-compatible complete discovery result.
#[pyclass(name = "ScanRunDiscoveryResult", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunDiscoveryResult {
    source: String,
    accepted_logs: Vec<String>,
    rejected_inputs: Vec<PyScanRunRejectedInput>,
    searched_locations: Vec<String>,
}

#[pymethods]
impl PyScanRunDiscoveryResult {
    /// Returns `standard` or `targeted`.
    #[getter]
    pub fn source(&self) -> String {
        self.source.clone()
    }

    /// Returns accepted Crash Logs in discovery order.
    #[getter]
    pub fn accepted_logs(&self) -> Vec<String> {
        self.accepted_logs.clone()
    }

    /// Returns all rejected Targeted inputs.
    #[getter]
    pub fn rejected_inputs(&self) -> Vec<PyScanRunRejectedInput> {
        self.rejected_inputs.clone()
    }

    /// Returns every location or input searched during discovery.
    #[getter]
    pub fn searched_locations(&self) -> Vec<String> {
        self.searched_locations.clone()
    }
}

/// Python-compatible typed FCX setup check.
#[pyclass(name = "ScanRunSetupCheck", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunSetupCheck {
    kind: String,
    state: String,
    message: String,
    details: Vec<String>,
}

#[pymethods]
impl PyScanRunSetupCheck {
    /// Returns the stable check kind.
    #[getter]
    pub fn kind(&self) -> String {
        self.kind.clone()
    }

    /// Returns the stable check state.
    #[getter]
    pub fn state(&self) -> String {
        self.state.clone()
    }

    /// Returns the short check summary.
    #[getter]
    pub fn message(&self) -> String {
        self.message.clone()
    }

    /// Returns the optional check detail lines.
    #[getter]
    pub fn details(&self) -> Vec<String> {
        self.details.clone()
    }
}

/// Python-compatible proposed setup path update.
#[pyclass(name = "ScanRunSetupPathUpdate", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunSetupPathUpdate {
    kind: String,
    path: String,
}

#[pymethods]
impl PyScanRunSetupPathUpdate {
    /// Returns the stable path kind.
    #[getter]
    pub fn kind(&self) -> String {
        self.kind.clone()
    }

    /// Returns the proposed path.
    #[getter]
    pub fn path(&self) -> String {
        self.path.clone()
    }
}

/// Python-compatible run-scoped FCX setup result.
#[pyclass(name = "ScanRunSetupResult", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunSetupResult {
    status: String,
    message: Option<String>,
    rendered_report: String,
    checks: Vec<PyScanRunSetupCheck>,
    path_updates: Vec<PyScanRunSetupPathUpdate>,
    configuration_issues: Vec<PyConfigIssue>,
    actions: Vec<String>,
    fatal_errors: Vec<String>,
}

#[pymethods]
impl PyScanRunSetupResult {
    /// Returns the adapter-facing setup status.
    #[getter]
    pub fn status(&self) -> String {
        self.status.clone()
    }

    /// Returns the optional concise setup message.
    #[getter]
    pub fn message(&self) -> Option<String> {
        self.message.clone()
    }

    /// Returns the canonical setup report.
    #[getter]
    pub fn rendered_report(&self) -> String {
        self.rendered_report.clone()
    }

    /// Returns typed setup checks.
    #[getter]
    pub fn checks(&self) -> Vec<PyScanRunSetupCheck> {
        self.checks.clone()
    }

    /// Returns proposed path updates.
    #[getter]
    pub fn path_updates(&self) -> Vec<PyScanRunSetupPathUpdate> {
        self.path_updates.clone()
    }

    /// Returns read-only FCX configuration issues.
    #[getter]
    pub fn configuration_issues(&self) -> Vec<PyConfigIssue> {
        self.configuration_issues.clone()
    }

    /// Returns required user actions.
    #[getter]
    pub fn actions(&self) -> Vec<String> {
        self.actions.clone()
    }

    /// Returns fatal setup errors.
    #[getter]
    pub fn fatal_errors(&self) -> Vec<String> {
        self.fatal_errors.clone()
    }
}

/// One structured per-log processing or finalization failure.
#[pyclass(name = "ScanRunLogFailure", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunLogFailure {
    stage: String,
    message: String,
}

#[pymethods]
impl PyScanRunLogFailure {
    /// Returns the stable failure stage.
    #[getter]
    pub fn stage(&self) -> String {
        self.stage.clone()
    }

    /// Returns the failure diagnostic.
    #[getter]
    pub fn message(&self) -> String {
        self.message.clone()
    }
}

/// Complete terminal result for one discovered Crash Log.
#[pyclass(name = "ScanRunLogResult", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunLogResult {
    discovery_index: usize,
    crash_log: String,
    autoscan_report: Option<String>,
    disposition: String,
    failures: Vec<PyScanRunLogFailure>,
    message: Option<String>,
    moved_to_unsolved_logs: bool,
    processing_time_us: u64,
    processing_time_ms: u64,
    formid_count: usize,
    plugin_count: usize,
    suspect_count: usize,
}

#[pymethods]
impl PyScanRunLogResult {
    /// Returns the stable discovery-order index.
    #[getter]
    pub fn discovery_index(&self) -> usize {
        self.discovery_index
    }

    /// Returns the Crash Log path.
    #[getter]
    pub fn crash_log(&self) -> String {
        self.crash_log.clone()
    }

    /// Returns the Autoscan Report path when persistence succeeded.
    #[getter]
    pub fn autoscan_report(&self) -> Option<String> {
        self.autoscan_report.clone()
    }

    /// Returns the terminal durable disposition.
    #[getter]
    pub fn disposition(&self) -> String {
        self.disposition.clone()
    }

    /// Returns all structured failures without collapsing their stages.
    #[getter]
    pub fn failures(&self) -> Vec<PyScanRunLogFailure> {
        self.failures.clone()
    }

    /// Returns the optional concise failure detail.
    #[getter]
    pub fn message(&self) -> Option<String> {
        self.message.clone()
    }

    /// Returns whether any artifact moved to Unsolved Logs.
    #[getter]
    pub fn moved_to_unsolved_logs(&self) -> bool {
        self.moved_to_unsolved_logs
    }

    /// Returns processing time in microseconds.
    #[getter]
    pub fn processing_time_us(&self) -> u64 {
        self.processing_time_us
    }

    /// Returns processing time in milliseconds.
    #[getter]
    pub fn processing_time_ms(&self) -> u64 {
        self.processing_time_ms
    }

    /// Returns the number of FormIDs found.
    #[getter]
    pub fn formid_count(&self) -> usize {
        self.formid_count
    }

    /// Returns the number of plugins detected.
    #[getter]
    pub fn plugin_count(&self) -> usize {
        self.plugin_count
    }

    /// Returns the number of suspect patterns matched.
    #[getter]
    pub fn suspect_count(&self) -> usize {
        self.suspect_count
    }
}

/// Exact-byte identity retained for one Installed YAML Data file in this scan run.
#[pyclass(name = "ScanRunYamlDataContentIdentity", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyScanRunYamlDataContentIdentity {
    /// Lowercase hexadecimal SHA-256 digest of the retained bytes.
    #[pyo3(get)]
    sha256: String,
    /// Number of retained bytes represented by this identity.
    #[pyo3(get)]
    byte_len: u64,
}

/// Selected metadata for one update-eligible Main or game YAML Data file.
#[pyclass(name = "ScanRunInspectedYamlDataFile", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyScanRunInspectedYamlDataFile {
    /// `main` or `game` role token.
    #[pyo3(get)]
    role: String,
    /// `updated`, `previous`, or `bundled` source token.
    #[pyo3(get)]
    provenance: String,
    /// Breaking-change component of the compatible schema version.
    #[pyo3(get)]
    schema_major: u32,
    /// Additive-change component of the compatible schema version.
    #[pyo3(get)]
    schema_minor: u32,
    /// Lowercase hexadecimal SHA-256 digest of the selected exact bytes.
    #[pyo3(get)]
    sha256: String,
    /// Length of the selected exact bytes.
    #[pyo3(get)]
    byte_length: u64,
}

/// One structured selection, fallback, validation, or generation diagnostic.
#[pyclass(
    name = "ScanRunInstalledYamlDataDiagnostic",
    frozen,
    skip_from_py_object
)]
#[derive(Clone)]
pub struct PyScanRunInstalledYamlDataDiagnostic {
    /// Affected update-eligible role token when applicable.
    #[pyo3(get)]
    role: Option<String>,
    /// Candidate provenance token when an installed candidate was involved.
    #[pyo3(get)]
    candidate: Option<String>,
    /// Affected path when the diagnostic is path-attributable.
    #[pyo3(get)]
    path: Option<PathBuf>,
    /// Stable snake-case diagnostic category.
    #[pyo3(get)]
    kind: String,
    /// Actionable human-readable explanation.
    #[pyo3(get)]
    message: String,
}

/// Installed YAML Data metadata retained from one immutable scan-run snapshot.
#[pyclass(name = "ScanRunInstalledYamlDataRunData", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyScanRunInstalledYamlDataRunData {
    /// Selected Main file schema, identity, and provenance.
    #[pyo3(get)]
    main: PyScanRunInspectedYamlDataFile,
    /// Selected game file schema, identity, and provenance.
    #[pyo3(get)]
    game_file: PyScanRunInspectedYamlDataFile,
    /// Stable token describing how Local Ignore entered the snapshot.
    #[pyo3(get)]
    local_ignore_state: String,
    /// Identity derived from the exact retained Local Ignore bytes.
    #[pyo3(get)]
    local_ignore_identity: PyScanRunYamlDataContentIdentity,
    /// Structured fallback, validation, and generation diagnostics.
    #[pyo3(get)]
    diagnostics: Vec<PyScanRunInstalledYamlDataDiagnostic>,
}

/// Complete terminal Crash Log Scan Run result.
#[pyclass(name = "ScanRunResult", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunResult {
    status: String,
    discovery: Option<PyScanRunDiscoveryResult>,
    setup: Option<PyScanRunSetupResult>,
    installed_yaml_data: Option<PyScanRunInstalledYamlDataRunData>,
    effective_concurrency: Option<usize>,
    message: Option<String>,
    total: usize,
    succeeded: usize,
    failed: usize,
    cancelled: usize,
    logs: Vec<PyScanRunLogResult>,
}

#[pymethods]
impl PyScanRunResult {
    /// Returns the stable lifecycle status.
    #[getter]
    pub fn status(&self) -> String {
        self.status.clone()
    }

    /// Returns completed discovery data when discovery committed.
    #[getter]
    pub fn discovery(&self) -> Option<PyScanRunDiscoveryResult> {
        self.discovery.clone()
    }

    /// Returns run-scoped setup data when FCX was enabled.
    #[getter]
    pub fn setup(&self) -> Option<PyScanRunSetupResult> {
        self.setup.clone()
    }

    /// Returns Installed YAML Data metadata when intake selected a snapshot.
    #[getter]
    pub fn installed_yaml_data(&self) -> Option<PyScanRunInstalledYamlDataRunData> {
        self.installed_yaml_data.clone()
    }

    /// Returns Rust-selected concurrency once scheduling was reached.
    #[getter]
    pub fn effective_concurrency(&self) -> Option<usize> {
        self.effective_concurrency
    }

    /// Returns the optional concise run-level message.
    #[getter]
    pub fn message(&self) -> Option<String> {
        self.message.clone()
    }

    /// Returns the number of discovered Crash Logs.
    #[getter]
    pub fn total(&self) -> usize {
        self.total
    }

    /// Returns the number of successful Crash Logs.
    #[getter]
    pub fn succeeded(&self) -> usize {
        self.succeeded
    }

    /// Returns the number of failed Crash Logs.
    #[getter]
    pub fn failed(&self) -> usize {
        self.failed
    }

    /// Returns the number cancelled before start.
    #[getter]
    pub fn cancelled(&self) -> usize {
        self.cancelled
    }

    /// Returns per-log results in discovery order.
    #[getter]
    pub fn logs(&self) -> Vec<PyScanRunLogResult> {
        self.logs.clone()
    }
}

/// Typed run-wide infrastructure failure.
#[pyclass(name = "ScanRunInfrastructureError", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunInfrastructureError {
    stage: String,
    message: String,
    path: Option<String>,
}

#[pymethods]
impl PyScanRunInfrastructureError {
    /// Returns the stable infrastructure stage.
    #[getter]
    pub fn stage(&self) -> String {
        self.stage.clone()
    }

    /// Returns the failure diagnostic.
    #[getter]
    pub fn message(&self) -> String {
        self.message.clone()
    }

    /// Returns the relevant path when one was captured.
    #[getter]
    pub fn path(&self) -> Option<String> {
        self.path.clone()
    }
}

/// Common log-scoped event payload.
#[pyclass(name = "ScanRunLogEvent", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunLogEvent {
    discovery_index: usize,
    crash_log: String,
    completed: usize,
    total: usize,
}

#[pymethods]
impl PyScanRunLogEvent {
    /// Returns the stable discovery-order index.
    #[getter]
    pub fn discovery_index(&self) -> usize {
        self.discovery_index
    }

    /// Returns the event's Crash Log path.
    #[getter]
    pub fn crash_log(&self) -> String {
        self.crash_log.clone()
    }

    /// Returns the number of logs finished at observation time.
    #[getter]
    pub fn completed(&self) -> usize {
        self.completed
    }

    /// Returns the total accepted Crash Logs.
    #[getter]
    pub fn total(&self) -> usize {
        self.total
    }
}

/// One tagged serialized observer event.
#[pyclass(name = "ScanRunEvent", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunEvent {
    kind: String,
    discovery: Option<PyScanRunDiscoveryResult>,
    effective_concurrency: Option<usize>,
    log: Option<PyScanRunLogEvent>,
    phase: Option<String>,
    disposition: Option<String>,
}

#[pymethods]
impl PyScanRunEvent {
    /// Returns the stable event variant identifier.
    #[getter]
    pub fn kind(&self) -> String {
        self.kind.clone()
    }

    /// Returns discovery data for `discovery_completed`.
    #[getter]
    pub fn discovery(&self) -> Option<PyScanRunDiscoveryResult> {
        self.discovery.clone()
    }

    /// Returns the selected value for `effective_concurrency_selected`.
    #[getter]
    pub fn effective_concurrency(&self) -> Option<usize> {
        self.effective_concurrency
    }

    /// Returns common log facts for log-scoped variants.
    #[getter]
    pub fn log(&self) -> Option<PyScanRunLogEvent> {
        self.log.clone()
    }

    /// Returns the phase for `log_phase`.
    #[getter]
    pub fn phase(&self) -> Option<String> {
        self.phase.clone()
    }

    /// Returns the terminal disposition for `log_finished`.
    #[getter]
    pub fn disposition(&self) -> Option<String> {
        self.disposition.clone()
    }
}

/// Final operation envelope with independent adapter observation failure data.
#[pyclass(name = "ScanRunExecution", from_py_object)]
#[derive(Clone)]
pub struct PyScanRunExecution {
    result: Option<PyScanRunResult>,
    error: Option<PyScanRunInfrastructureError>,
    observer_error: Option<String>,
}

#[pymethods]
impl PyScanRunExecution {
    /// Returns a terminal result when core execution succeeded.
    #[getter]
    pub fn result(&self) -> Option<PyScanRunResult> {
        self.result.clone()
    }

    /// Returns a typed infrastructure failure when no result could be produced.
    #[getter]
    pub fn error(&self) -> Option<PyScanRunInfrastructureError> {
        self.error.clone()
    }

    /// Returns the first adapter-only observer delivery failure.
    #[getter]
    pub fn observer_error(&self) -> Option<String> {
        self.observer_error.clone()
    }
}

/// Converts explicit Python configuration into the final core contract.
fn configuration_to_core(value: &PyScanRunConfiguration) -> PyResult<contract::Configuration> {
    Ok(contract::Configuration {
        installation_root: required_path(value.installation_root.clone(), "installation_root")?,
        game: value.game,
        game_version: value.game_version.clone(),
        options: contract::Options::new(value.show_formid_values, value.simplify_logs),
        scan_facts: CrashLogScanFacts {
            formid_database_paths: value
                .formid_database_paths
                .iter()
                .map(PathBuf::from)
                .collect(),
            unsolved_logs_destination: optional_path(value.unsolved_logs_destination.as_deref()),
        },
        max_concurrent: value.max_concurrent,
    })
}

/// Converts Standard discovery inputs without adding movement policy.
fn standard_source_to_core(
    value: &PyScanRunStandardSource,
) -> PyResult<StandardCrashLogScanSource> {
    Ok(StandardCrashLogScanSource {
        base_directory: required_path(value.base_directory.clone(), "base_directory")?,
        custom_scan_directory: value.custom_scan_directory.as_ref().map(PathBuf::from),
        configured_documents_root: value.configured_documents_root.as_ref().map(PathBuf::from),
    })
}

/// Converts Targeted discovery inputs while preserving caller order.
fn targeted_source_to_core(value: &PyScanRunTargetedSource) -> TargetedCrashLogScanSource {
    TargetedCrashLogScanSource {
        inputs: value.inputs.iter().map(PathBuf::from).collect(),
    }
}

/// Converts explicit FCX setup facts without consulting global state.
fn setup_context_to_core(value: &PyScanRunSetupContext) -> CrashLogScanSetupContext {
    CrashLogScanSetupContext {
        game_root: value.game_root().map(PathBuf::from),
        docs_root: value.docs_root().map(PathBuf::from),
        game_exe_path: value.game_exe_path().map(PathBuf::from),
        xse_log_path: value.xse_log_path().map(PathBuf::from),
    }
}

/// Validates required path text at the adapter boundary.
fn required_path(value: String, label: &str) -> PyResult<PathBuf> {
    if value.trim().is_empty() {
        return Err(PyValueError::new_err(format!("{label} must not be blank")));
    }
    Ok(PathBuf::from(value))
}

/// Converts optional path text while treating blank binding sentinels as absent.
fn optional_path(value: Option<&str>) -> Option<PathBuf> {
    value
        .filter(|path| !path.trim().is_empty())
        .map(PathBuf::from)
}

fn path_to_string(path: PathBuf) -> String {
    path.to_string_lossy().into_owned()
}

/// Maps discovery while preserving all accepted, rejected, and searched paths.
fn discovery_to_py(value: CrashLogScanDiscoveryResult) -> PyScanRunDiscoveryResult {
    let source = match value.source {
        CrashLogScanDiscoverySource::Standard => "standard",
        CrashLogScanDiscoverySource::Targeted => "targeted",
    };
    PyScanRunDiscoveryResult {
        source: source.to_string(),
        accepted_logs: value
            .accepted_logs
            .into_iter()
            .map(path_to_string)
            .collect(),
        rejected_inputs: value
            .rejected_inputs
            .into_iter()
            .map(|rejected| PyScanRunRejectedInput {
                path: path_to_string(rejected.path),
                reason: rejected.reason,
            })
            .collect(),
        searched_locations: value
            .searched_locations
            .into_iter()
            .map(path_to_string)
            .collect(),
    }
}

/// Maps run-scoped setup data with every optional field intact.
fn setup_to_py(value: CrashLogScanSetupResult) -> PyScanRunSetupResult {
    PyScanRunSetupResult {
        status: value.status,
        message: value.message,
        rendered_report: value.rendered_report,
        checks: value
            .checks
            .into_iter()
            .map(|check| PyScanRunSetupCheck {
                kind: check.kind,
                state: check.state,
                message: check.message,
                details: check.details,
            })
            .collect(),
        path_updates: value
            .path_updates
            .into_iter()
            .map(|update| PyScanRunSetupPathUpdate {
                kind: update.kind,
                path: path_to_string(update.path),
            })
            .collect(),
        configuration_issues: value
            .configuration_issues
            .into_iter()
            .map(PyConfigIssue::from)
            .collect(),
        actions: value.actions,
        fatal_errors: value.fatal_errors,
    }
}

fn disposition_to_string(value: contract::LogDisposition) -> String {
    match value {
        contract::LogDisposition::Succeeded => "succeeded",
        contract::LogDisposition::Failed => "failed",
        contract::LogDisposition::CancelledBeforeStart => "cancelled_before_start",
    }
    .to_string()
}

fn log_failure_stage_to_string(value: contract::LogFailureStage) -> String {
    match value {
        contract::LogFailureStage::Analysis => "analysis",
        contract::LogFailureStage::ReportWrite => "report_write",
        contract::LogFailureStage::UnsolvedLogsFinalization => "unsolved_logs_finalization",
    }
    .to_string()
}

/// Maps one complete terminal log result without collapsing structured failures.
fn log_result_to_py(value: contract::LogResult) -> PyScanRunLogResult {
    PyScanRunLogResult {
        discovery_index: value.discovery_index,
        crash_log: path_to_string(value.crash_log),
        autoscan_report: value.autoscan_report.map(path_to_string),
        disposition: disposition_to_string(value.disposition),
        failures: value
            .failures
            .into_iter()
            .map(|failure| PyScanRunLogFailure {
                stage: log_failure_stage_to_string(failure.stage),
                message: failure.message,
            })
            .collect(),
        message: value.message,
        moved_to_unsolved_logs: value.moved_to_unsolved_logs,
        processing_time_us: value.processing_time_us,
        processing_time_ms: value.processing_time_ms,
        formid_count: value.formid_count,
        plugin_count: value.plugin_count,
        suspect_count: value.suspect_count,
    }
}

fn run_status_to_string(value: CrashLogScanRunStatus) -> String {
    match value {
        CrashLogScanRunStatus::Completed => "completed",
        CrashLogScanRunStatus::NoCrashLogsFound => "no_crash_logs_found",
        CrashLogScanRunStatus::SetupFailed => "setup_failed",
        CrashLogScanRunStatus::CancelledBeforeDiscovery => "cancelled_before_discovery",
        CrashLogScanRunStatus::Cancelled => "cancelled",
    }
    .to_string()
}

/// Returns the stable Python token for one selected Installed YAML Data role.
const fn installed_yaml_data_role_to_string(value: InstalledYamlDataRole) -> &'static str {
    match value {
        InstalledYamlDataRole::Main => "main",
        InstalledYamlDataRole::Game => "game",
    }
}

/// Returns the stable Python token for one selected candidate provenance.
const fn installed_yaml_data_provenance_to_string(
    value: InstalledYamlDataProvenance,
) -> &'static str {
    match value {
        InstalledYamlDataProvenance::Updated => "updated",
        InstalledYamlDataProvenance::Previous => "previous",
        InstalledYamlDataProvenance::Bundled => "bundled",
    }
}

/// Returns the stable Python token for every valid-or-generated diagnostic kind.
const fn installed_yaml_data_diagnostic_kind_to_string(
    value: contract::InstalledYamlDataRunDiagnosticKind,
) -> &'static str {
    use contract::InstalledYamlDataRunDiagnosticKind as Kind;
    match value {
        Kind::CacheUnavailable => "cache_unavailable",
        Kind::Missing => "missing",
        Kind::Read => "read",
        Kind::InvalidUtf8 => "invalid_utf8",
        Kind::Parse => "parse",
        Kind::InvalidSchema => "invalid_schema",
        Kind::IncompatibleSchema => "incompatible_schema",
        Kind::InvalidRoleData => "invalid_role_data",
        Kind::LocalIgnoreGenerated => "local_ignore_generated",
    }
}

/// Returns the stable Python token for every valid-or-generated Local Ignore state.
const fn local_ignore_state_to_string(value: contract::LocalIgnoreRunState) -> &'static str {
    match value {
        contract::LocalIgnoreRunState::Existing => "existing",
        contract::LocalIgnoreRunState::Generated => "generated",
    }
}

/// Projects selected file metadata with the same shape as `classic_config`.
fn installed_yaml_data_file_to_py(value: InspectedYamlDataFile) -> PyScanRunInspectedYamlDataFile {
    let schema = value.schema_version();
    PyScanRunInspectedYamlDataFile {
        role: installed_yaml_data_role_to_string(value.role()).to_string(),
        provenance: installed_yaml_data_provenance_to_string(value.provenance()).to_string(),
        schema_major: schema.major,
        schema_minor: schema.minor,
        sha256: value.identity().sha256_hex(),
        byte_length: value.identity().byte_len(),
    }
}

/// Projects an exact-byte identity with the same shape as `classic_config`.
fn installed_yaml_data_identity_to_py(
    value: YamlDataContentIdentity,
) -> PyScanRunYamlDataContentIdentity {
    PyScanRunYamlDataContentIdentity {
        sha256: value.sha256_hex(),
        byte_len: value.byte_len(),
    }
}

/// Projects one diagnostic without collapsing optional attribution fields.
fn installed_yaml_data_diagnostic_to_py(
    value: contract::InstalledYamlDataRunDiagnostic,
) -> PyScanRunInstalledYamlDataDiagnostic {
    PyScanRunInstalledYamlDataDiagnostic {
        role: value
            .role()
            .map(installed_yaml_data_role_to_string)
            .map(str::to_string),
        candidate: value
            .candidate()
            .map(installed_yaml_data_provenance_to_string)
            .map(str::to_string),
        path: value.path().map(PathBuf::from),
        kind: installed_yaml_data_diagnostic_kind_to_string(value.kind()).to_string(),
        message: value.message().to_string(),
    }
}

/// Projects run-scoped Installed YAML Data metadata exhaustively.
fn installed_yaml_data_to_py(
    value: contract::InstalledYamlDataRunData,
) -> PyScanRunInstalledYamlDataRunData {
    PyScanRunInstalledYamlDataRunData {
        main: installed_yaml_data_file_to_py(value.main),
        game_file: installed_yaml_data_file_to_py(value.game_file),
        local_ignore_state: local_ignore_state_to_string(value.local_ignore_state).to_string(),
        local_ignore_identity: installed_yaml_data_identity_to_py(value.local_ignore_identity),
        diagnostics: value
            .diagnostics
            .into_iter()
            .map(installed_yaml_data_diagnostic_to_py)
            .collect(),
    }
}

/// Maps the complete terminal result including selected Installed YAML Data.
fn run_result_to_py(value: contract::RunResult) -> PyScanRunResult {
    PyScanRunResult {
        status: run_status_to_string(value.status),
        discovery: value.discovery.map(discovery_to_py),
        setup: value.setup.map(setup_to_py),
        installed_yaml_data: value.installed_yaml_data.map(installed_yaml_data_to_py),
        effective_concurrency: value.effective_concurrency,
        message: value.message,
        total: value.total,
        succeeded: value.succeeded,
        failed: value.failed,
        cancelled: value.cancelled,
        logs: value.logs.into_iter().map(log_result_to_py).collect(),
    }
}

/// Maps every typed run-wide error field, including its optional path.
fn infrastructure_error_to_py(
    value: contract::InfrastructureError,
) -> PyScanRunInfrastructureError {
    let stage = match value.stage {
        contract::InfrastructureErrorStage::RequestValidation => "request_validation",
        contract::InfrastructureErrorStage::Discovery => "discovery",
        contract::InfrastructureErrorStage::Intake => "intake",
        contract::InfrastructureErrorStage::FormIdDatabaseAccess => "formid_database_access",
        contract::InfrastructureErrorStage::Initialization => "initialization",
        contract::InfrastructureErrorStage::InternalInvariant => "internal_invariant",
    };
    PyScanRunInfrastructureError {
        stage: stage.to_string(),
        message: value.message,
        path: value.path.map(path_to_string),
    }
}

fn phase_to_string(value: ScanProgressPhase) -> String {
    match value {
        ScanProgressPhase::Setup => "setup",
        ScanProgressPhase::Parse => "parse",
        ScanProgressPhase::Analyze => "analyze",
        ScanProgressPhase::Finalize => "finalize",
    }
    .to_string()
}

fn log_event_to_py(value: contract::LogEvent) -> PyScanRunLogEvent {
    PyScanRunLogEvent {
        discovery_index: value.discovery_index,
        crash_log: path_to_string(value.crash_log),
        completed: value.completed,
        total: value.total,
    }
}

/// Maps every event variant into one stable tagged Python shape.
fn event_to_py(value: contract::Event) -> PyScanRunEvent {
    match value {
        contract::Event::DiscoveryCompleted(discovery) => PyScanRunEvent {
            kind: "discovery_completed".to_string(),
            discovery: Some(discovery_to_py(discovery)),
            effective_concurrency: None,
            log: None,
            phase: None,
            disposition: None,
        },
        contract::Event::EffectiveConcurrencySelected {
            effective_concurrency,
        } => PyScanRunEvent {
            kind: "effective_concurrency_selected".to_string(),
            discovery: None,
            effective_concurrency: Some(effective_concurrency),
            log: None,
            phase: None,
            disposition: None,
        },
        contract::Event::LogQueued(log) => PyScanRunEvent {
            kind: "log_queued".to_string(),
            discovery: None,
            effective_concurrency: None,
            log: Some(log_event_to_py(log)),
            phase: None,
            disposition: None,
        },
        contract::Event::LogStarted(log) => PyScanRunEvent {
            kind: "log_started".to_string(),
            discovery: None,
            effective_concurrency: None,
            log: Some(log_event_to_py(log)),
            phase: None,
            disposition: None,
        },
        contract::Event::LogPhase { log, phase } => PyScanRunEvent {
            kind: "log_phase".to_string(),
            discovery: None,
            effective_concurrency: None,
            log: Some(log_event_to_py(log)),
            phase: Some(phase_to_string(phase)),
            disposition: None,
        },
        contract::Event::LogFinished { log, disposition } => PyScanRunEvent {
            kind: "log_finished".to_string(),
            discovery: None,
            effective_concurrency: None,
            log: Some(log_event_to_py(log)),
            phase: None,
            disposition: Some(disposition_to_string(disposition)),
        },
    }
}

struct PyObserverAdapter {
    callback: Py<PyAny>,
    cancellation: contract::Cancellation,
    cancel_on_error: bool,
    delivery_error: Option<String>,
    delivery_failed: bool,
}

impl PyObserverAdapter {
    /// Records only the first adapter delivery failure and optionally requests cancellation.
    fn record_failure(&mut self, message: String) {
        self.delivery_failed = true;
        if self.delivery_error.is_none() {
            self.delivery_error = Some(message);
        }
        if self.cancel_on_error {
            self.cancellation.cancel();
        }
    }
}

impl contract::Observer for PyObserverAdapter {
    /// Reacquires the GIL for exactly one serialized callback delivery.
    fn on_event(&mut self, event: contract::Event) {
        if self.delivery_failed {
            return;
        }

        let result = Python::attach(|py| self.callback.call1(py, (event_to_py(event),)));
        if let Err(error) = result {
            self.record_failure(error.to_string());
        }
    }
}

/// Executes one final-contract request with optional serialized observation.
///
/// Observer exceptions are adapter-only data. Delivery stops after the first
/// exception, while `cancel_on_observer_error` determines whether the adapter
/// also requests safe stopping through the separate cancellation control.
#[pyfunction]
#[pyo3(signature = (request, cancellation, observer=None, cancel_on_observer_error=false))]
pub fn scan_run_execute(
    py: Python<'_>,
    request: PyRef<'_, PyScanRunRequest>,
    cancellation: PyRef<'_, PyScanRunCancellation>,
    observer: Option<Py<PyAny>>,
    cancel_on_observer_error: bool,
) -> PyResult<PyScanRunExecution> {
    let request = request.inner.clone();
    let cancellation = cancellation.inner.clone();
    let result = without_gil_block_on(py, || async move {
        let mut observer = observer.map(|callback| PyObserverAdapter {
            callback,
            cancellation: cancellation.clone(),
            cancel_on_error: cancel_on_observer_error,
            delivery_error: None,
            delivery_failed: false,
        });
        let result = contract::execute(
            request,
            &cancellation,
            observer
                .as_mut()
                .map(|adapter| adapter as &mut dyn contract::Observer),
        )
        .await;
        let observer_error = observer.and_then(|adapter| adapter.delivery_error);
        (result, observer_error)
    });

    let (result, observer_error) = result;
    Ok(match result {
        Ok(result) => PyScanRunExecution {
            result: Some(run_result_to_py(result)),
            error: None,
            observer_error,
        },
        Err(error) => PyScanRunExecution {
            result: None,
            error: Some(infrastructure_error_to_py(error)),
            observer_error,
        },
    })
}

// Keep the repository's required sibling-test declaration intact under rustfmt.
#[rustfmt::skip]
#[cfg(test)] #[path = "scan_run_tests.rs"] mod tests;
