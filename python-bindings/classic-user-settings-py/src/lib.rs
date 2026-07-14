//! Thin PyO3 adapter for typed User Settings inspection, update previews, and commits.

use classic_shared::without_gil;
use classic_user_settings_core::{
    AcceptedUserSettingsUpdate, CommitEligibility, CrashLogScanSettings, DocumentClassification,
    FrontendPreferences, FrontendState, GameSetupSettings, GuiWindow, GuiWindowGeometry,
    LegacyTuiStateImportOutcome, LegacyTuiStateImportReceipt, LegacyTuiStateImportRestoreOutcome,
    MigrationChange, MigrationChangeKind, MigrationDiagnostic, MigrationEndpoint,
    MigrationPlanningOutcome, PreferenceOrigin, Revision, SourceLocation, TuiRememberedState,
    UserSettings, UserSettingsCommitOutcome,
    UserSettingsFrontendTransitionOutcome as CoreUserSettingsFrontendTransitionOutcome,
    UserSettingsMigrationApplyOutcome, UserSettingsMigrationPlan, UserSettingsMigrationReceipt,
    UserSettingsMigrationRestoreOutcome, UserSettingsSchemaVersion, UserSettingsUpdate,
    UserSettingsUpdateField, UserSettingsUpdatePreview, WindowGeometry, import_legacy_tui_state,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
use std::collections::HashMap;

pyo3::create_exception!(
    classic_user_settings,
    UserSettingsCommitError,
    PyRuntimeError,
    "Operational failure while publishing an accepted User Settings Update."
);

pyo3::create_exception!(
    classic_user_settings,
    LegacyTuiStateImportError,
    PyRuntimeError,
    "Operational failure while importing retired TUI state into User Settings."
);

pyo3::create_exception!(
    classic_user_settings,
    UserSettingsMigrationError,
    PyRuntimeError,
    "Operational failure while applying or restoring a User Settings migration."
);

/// One structured diagnostic produced while opening User Settings.
#[pyclass(name = "UserSettingsDiagnostic", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyUserSettingsDiagnostic {
    /// Stable machine-readable diagnostic code.
    #[pyo3(get)]
    code: String,
    /// Human-readable diagnostic context.
    #[pyo3(get)]
    message: String,
}

/// Update-related User Settings consumed by update checks and compatibility adapters.
#[pyclass(name = "UpdatePreferences", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyUpdatePreferences {
    /// Whether first-party update checks are enabled after safe fallback policy.
    #[pyo3(get)]
    update_check: bool,
    /// Provenance token: `document`, `default`, or `degraded_fallback`.
    #[pyo3(get)]
    origin: String,
    /// Canonical compatibility source token: `GitHub` or `Both`.
    #[pyo3(get)]
    update_source: String,
    /// Provenance of the compatibility update-source selection.
    #[pyo3(get)]
    update_source_origin: String,
}

/// Typed Crash Log Scan settings projected from User Settings.
#[pyclass(name = "CrashLogScanSettings", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyCrashLogScanSettings {
    /// Whether FCX Mode is enabled.
    #[pyo3(get)]
    fcx_mode: bool,
    /// Provenance of the FCX Mode value.
    #[pyo3(get)]
    fcx_mode_origin: String,
    /// Whether Crash Logs should be simplified before analysis.
    #[pyo3(get)]
    simplify_logs: bool,
    /// Provenance of the Simplify Logs value.
    #[pyo3(get)]
    simplify_logs_origin: String,
    /// Whether scan statistics should be included in output.
    #[pyo3(get)]
    show_statistics: bool,
    /// Provenance of the Show Statistics value.
    #[pyo3(get)]
    show_statistics_origin: String,
    /// Whether FormID Value Lookup is enabled.
    #[pyo3(get)]
    formid_value_lookup: bool,
    /// Provenance of the FormID Value Lookup value.
    #[pyo3(get)]
    formid_value_lookup_origin: String,
    /// Additional FormID database paths keyed by managed game.
    #[pyo3(get)]
    formid_databases: HashMap<String, Vec<String>>,
    /// Provenance of the FormID Databases mapping.
    #[pyo3(get)]
    formid_databases_origin: String,
    /// Whether Standard Crash Log Scan Runs may move Unsolved Logs.
    #[pyo3(get)]
    move_unsolved_logs: bool,
    /// Provenance of the Move Unsolved Logs value.
    #[pyo3(get)]
    move_unsolved_logs_origin: String,
    /// Optional persisted Unsolved Logs Destination.
    #[pyo3(get)]
    unsolved_logs_destination: Option<String>,
    /// Provenance of the Unsolved Logs Destination value.
    #[pyo3(get)]
    unsolved_logs_destination_origin: String,
    /// Optional custom Crash Log Scan input.
    #[pyo3(get)]
    custom_scan_input: Option<String>,
    /// Provenance of the custom Crash Log Scan input.
    #[pyo3(get)]
    custom_scan_input_origin: String,
    /// Saved game-version selection token.
    #[pyo3(get)]
    game_version_selection: String,
    /// Provenance of the game-version selection.
    #[pyo3(get)]
    game_version_selection_origin: String,
    /// Requested scan concurrency, where zero selects the adaptive default.
    #[pyo3(get)]
    max_concurrent_scans: u32,
    /// Provenance of the requested scan concurrency.
    #[pyo3(get)]
    max_concurrent_scans_origin: String,
}

/// Typed Game Setup settings projected from User Settings.
#[pyclass(name = "GameSetupSettings", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyGameSetupSettings {
    /// Stable managed-game identifier.
    #[pyo3(get)]
    managed_game: String,
    /// Provenance of the managed-game identifier.
    #[pyo3(get)]
    managed_game_origin: String,
    /// Saved game-version selection token.
    #[pyo3(get)]
    game_version_selection: String,
    /// Provenance of the game-version selection.
    #[pyo3(get)]
    game_version_selection_origin: String,
    /// Optional persisted game installation root, preserving its spelling.
    #[pyo3(get)]
    game_root: Option<String>,
    /// Provenance of the game installation root.
    #[pyo3(get)]
    game_root_origin: String,
    /// Optional persisted game executable path, preserving its spelling.
    #[pyo3(get)]
    game_executable: Option<String>,
    /// Provenance of the game executable path.
    #[pyo3(get)]
    game_executable_origin: String,
    /// Optional persisted documents root, preserving its spelling.
    #[pyo3(get)]
    documents_root: Option<String>,
    /// Provenance of the documents root.
    #[pyo3(get)]
    documents_root_origin: String,
    /// Optional persisted INI-folder fallback, preserving its spelling.
    #[pyo3(get)]
    ini_folder: Option<String>,
    /// Provenance of the INI-folder fallback.
    #[pyo3(get)]
    ini_folder_origin: String,
    /// Optional persisted mods or staging root, preserving its spelling.
    #[pyo3(get)]
    mods_root: Option<String>,
    /// Provenance of the mods or staging root.
    #[pyo3(get)]
    mods_root_origin: String,
    /// Optional custom Crash Log Scan input, preserving its spelling.
    #[pyo3(get)]
    custom_scan_input: Option<String>,
    /// Provenance of the custom Crash Log Scan input.
    #[pyo3(get)]
    custom_scan_input_origin: String,
    /// Optional persisted Papyrus log path, preserving its spelling.
    #[pyo3(get)]
    papyrus_log: Option<String>,
    /// Provenance of the Papyrus log path.
    #[pyo3(get)]
    papyrus_log_origin: String,
}

/// Remembered presentation preferences shared by maintained frontends.
#[pyclass(name = "FrontendPreferences", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyFrontendPreferences {
    /// Whether successful scans should select the Results presentation.
    #[pyo3(get)]
    auto_switch_after_scan: bool,
    /// Provenance of the automatic result-switching preference.
    #[pyo3(get)]
    auto_switch_after_scan_origin: String,
    /// Remembered refresh interval in milliseconds.
    #[pyo3(get)]
    auto_refresh_interval_ms: u64,
    /// Provenance of the refresh interval.
    #[pyo3(get)]
    auto_refresh_interval_ms_origin: String,
}

/// Widget-independent remembered geometry for one GUI tab.
#[pyclass(name = "WindowGeometry", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyWindowGeometry {
    /// Whether the tab's window was maximized.
    #[pyo3(get)]
    maximized: bool,
    /// Provenance of the maximized state.
    #[pyo3(get)]
    maximized_origin: String,
    /// Remembered normal-state width in pixels.
    #[pyo3(get)]
    width: u32,
    /// Provenance of the remembered width.
    #[pyo3(get)]
    width_origin: String,
    /// Remembered normal-state height in pixels.
    #[pyo3(get)]
    height: u32,
    /// Provenance of the remembered height.
    #[pyo3(get)]
    height_origin: String,
}

/// Remembered geometry for every maintained GUI tab.
#[pyclass(name = "GuiWindowGeometry", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyGuiWindowGeometry {
    /// Geometry for the Main Options tab.
    #[pyo3(get)]
    main_tab: PyWindowGeometry,
    /// Geometry for the File Backup tab.
    #[pyo3(get)]
    backups_tab: PyWindowGeometry,
    /// Geometry for the Articles tab.
    #[pyo3(get)]
    articles_tab: PyWindowGeometry,
    /// Geometry for the Results tab.
    #[pyo3(get)]
    results_tab: PyWindowGeometry,
}

/// Remembered TUI state represented under the canonical `UI.tui` namespace.
#[pyclass(name = "TuiRememberedState", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyTuiRememberedState {
    /// Stable zero-based tab ordinal remembered by the TUI.
    #[pyo3(get)]
    active_tab: u8,
    /// Provenance of the active-tab ordinal.
    #[pyo3(get)]
    active_tab_origin: String,
    /// Remembered Results list-panel width.
    #[pyo3(get)]
    results_panel_width: u16,
    /// Provenance of the Results list-panel width.
    #[pyo3(get)]
    results_panel_width_origin: String,
    /// Whether Results are remembered in ascending order.
    #[pyo3(get)]
    sort_ascending: bool,
    /// Provenance of the remembered sort direction.
    #[pyo3(get)]
    sort_ascending_origin: String,
}

/// Cohesive, widget-independent User Settings state remembered by frontends.
#[pyclass(name = "FrontendState", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyFrontendState {
    /// Remembered presentation preferences shared by frontends.
    #[pyo3(get)]
    preferences: PyFrontendPreferences,
    /// Remembered geometry for each maintained GUI tab.
    #[pyo3(get)]
    window_geometry: PyGuiWindowGeometry,
    /// Canonical namespace reserved for remembered TUI state.
    #[pyo3(get)]
    tui: PyTuiRememberedState,
}

/// A caller-authored request for a non-persisting User Settings Update preview.
#[pyclass(name = "UserSettingsUpdate", skip_from_py_object)]
#[derive(Clone, Default)]
pub struct PyUserSettingsUpdate {
    inner: UserSettingsUpdate,
}

#[pymethods]
impl PyUserSettingsUpdate {
    /// Creates an empty update request.
    #[new]
    fn new() -> Self {
        Self::default()
    }

    /// Requests a new Update Check preference.
    fn set_update_check(&mut self, value: bool) {
        self.inner = std::mem::take(&mut self.inner).with_update_check(value);
    }

    /// Requests a canonical or legacy-compatible Update Source selection.
    fn set_update_source(&mut self, value: String) {
        self.inner = std::mem::take(&mut self.inner).with_update_source(value);
    }

    /// Requests whether the GUI should switch to Results after a completed scan.
    fn set_auto_switch_after_scan(&mut self, value: bool) {
        self.inner = std::mem::take(&mut self.inner).with_auto_switch_after_scan(value);
    }

    /// Requests remembered geometry for one maintained GUI window token.
    ///
    /// Raises `ValueError` when `tab` is not one of the stable tokens exposed by
    /// the frontend-state contract; dimensions remain preview-validated with the full update.
    fn set_window_geometry(
        &mut self,
        tab: String,
        maximized: bool,
        width: i64,
        height: i64,
    ) -> PyResult<()> {
        let window = GuiWindow::parse(&tab).ok_or_else(|| {
            PyValueError::new_err(format!(
                "unknown GUI window '{tab}'; expected one of: main_tab, backups_tab, articles_tab, results_tab"
            ))
        })?;
        self.inner =
            std::mem::take(&mut self.inner).with_window_geometry(window, maximized, width, height);
        Ok(())
    }

    /// Requests one complete TUI remembered-state transition.
    ///
    /// The signed integer inputs remain preview-validated with the complete update so callers
    /// receive the stable field-specific diagnostics for out-of-range values.
    fn set_tui_remembered_state(
        &mut self,
        active_tab: i64,
        results_panel_width: i64,
        sort_ascending: bool,
    ) {
        self.inner = std::mem::take(&mut self.inner).with_tui_remembered_state(
            active_tab,
            results_panel_width,
            sort_ascending,
        );
    }

    /// Requests a managed-game identifier for validation with the complete preview.
    fn set_managed_game(&mut self, value: String) {
        self.inner = std::mem::take(&mut self.inner).with_managed_game(value);
    }

    /// Requests one canonical game-version selection token.
    fn set_game_version_selection(&mut self, value: String) {
        self.inner = std::mem::take(&mut self.inner).with_game_version_selection(value);
    }

    /// Requests an optional game installation root; `None` clears it.
    fn set_game_root(&mut self, value: Option<String>) {
        self.inner = std::mem::take(&mut self.inner).with_game_root(value);
    }

    /// Requests an optional game executable path; `None` clears it.
    fn set_game_executable(&mut self, value: Option<String>) {
        self.inner = std::mem::take(&mut self.inner).with_game_executable(value);
    }

    /// Requests an optional documents root; `None` clears it.
    fn set_documents_root(&mut self, value: Option<String>) {
        self.inner = std::mem::take(&mut self.inner).with_documents_root(value);
    }

    /// Requests an optional INI-folder compatibility fallback; `None` clears it.
    fn set_ini_folder(&mut self, value: Option<String>) {
        self.inner = std::mem::take(&mut self.inner).with_ini_folder(value);
    }

    /// Requests an optional mods or staging root; `None` clears it.
    fn set_mods_folder(&mut self, value: Option<String>) {
        self.inner = std::mem::take(&mut self.inner).with_mods_folder(value);
    }

    /// Requests a new FCX Mode preference.
    fn set_fcx_mode(&mut self, value: bool) {
        self.inner = std::mem::take(&mut self.inner).with_fcx_mode(value);
    }

    /// Requests a new Simplify Logs preference.
    fn set_simplify_logs(&mut self, value: bool) {
        self.inner = std::mem::take(&mut self.inner).with_simplify_logs(value);
    }

    /// Requests a new Show Statistics preference.
    fn set_show_statistics(&mut self, value: bool) {
        self.inner = std::mem::take(&mut self.inner).with_show_statistics(value);
    }

    /// Requests a new FormID Value Lookup preference.
    fn set_formid_value_lookup(&mut self, value: bool) {
        self.inner = std::mem::take(&mut self.inner).with_formid_value_lookup(value);
    }

    /// Requests replacement FormID database path lists keyed by managed game.
    fn set_formid_databases(&mut self, value: HashMap<String, Vec<String>>) {
        self.inner =
            std::mem::take(&mut self.inner).with_formid_databases(value.into_iter().collect());
    }

    /// Requests a new Move Unsolved Logs preference.
    fn set_move_unsolved_logs(&mut self, value: bool) {
        self.inner = std::mem::take(&mut self.inner).with_move_unsolved_logs(value);
    }

    /// Requests an optional Unsolved Logs Destination; `None` clears it.
    fn set_unsolved_logs_destination(&mut self, value: Option<String>) {
        self.inner = std::mem::take(&mut self.inner).with_unsolved_logs_destination(value);
    }

    /// Requests an optional custom Crash Log Scan input; `None` clears it.
    fn set_custom_scan_input(&mut self, value: Option<String>) {
        self.inner = std::mem::take(&mut self.inner).with_custom_scan_input(value);
    }

    /// Requests an optional Papyrus log path; `None` clears it.
    fn set_papyrus_log_path(&mut self, value: Option<String>) {
        self.inner = std::mem::take(&mut self.inner).with_papyrus_log_path(value);
    }

    /// Requests scan concurrency in the persisted `0..=32` range.
    fn set_max_concurrent_scans(&mut self, value: i64) {
        self.inner = std::mem::take(&mut self.inner).with_max_concurrent_scans(value);
    }
}

/// One field-specific diagnostic from a rejected User Settings Update preview.
#[pyclass(name = "UserSettingsUpdateDiagnostic", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyUserSettingsUpdateDiagnostic {
    /// Rejected canonical field path, absent for a preview-level failure.
    #[pyo3(get)]
    field_path: Option<String>,
    /// Stable machine-readable rejection code.
    #[pyo3(get)]
    code: String,
    /// Human-readable rejection context.
    #[pyo3(get)]
    message: String,
}

/// One canonical field explicitly requested in an accepted update preview.
#[pyclass(name = "UserSettingsUpdateField", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyUserSettingsUpdateField {
    /// Canonical RFC 6901-style field path.
    #[pyo3(get)]
    canonical_path: String,
    value: PyUserSettingsUpdateValue,
}

#[pymethods]
impl PyUserSettingsUpdateField {
    /// Returns the requested typed value without stringifying or normalizing it.
    #[getter]
    fn value(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        match &self.value {
            PyUserSettingsUpdateValue::Boolean(value) => {
                Ok((*value).into_pyobject(py)?.to_owned().unbind().into())
            }
            PyUserSettingsUpdateValue::String(value) => {
                Ok(value.into_pyobject(py)?.unbind().into())
            }
            PyUserSettingsUpdateValue::OptionalString(Some(value)) => {
                Ok(value.into_pyobject(py)?.unbind().into())
            }
            PyUserSettingsUpdateValue::OptionalString(None) => Ok(py.None()),
            PyUserSettingsUpdateValue::StringLists(value) => {
                let result = PyDict::new(py);
                for (game, paths) in value {
                    result.set_item(game, paths)?;
                }
                Ok(result.unbind().into())
            }
            PyUserSettingsUpdateValue::UnsignedInteger(value) => {
                Ok((*value).into_pyobject(py)?.unbind().into())
            }
        }
    }
}

/// Python-owned representation of one typed accepted field value.
#[derive(Clone)]
enum PyUserSettingsUpdateValue {
    Boolean(bool),
    String(String),
    OptionalString(Option<String>),
    StringLists(HashMap<String, Vec<String>>),
    UnsignedInteger(u32),
}

/// All-or-nothing result of previewing a User Settings Update.
#[pyclass(name = "UserSettingsUpdatePreview", frozen, skip_from_py_object)]
pub struct PyUserSettingsUpdatePreview {
    /// Whether every requested field was accepted.
    #[pyo3(get)]
    accepted: bool,
    /// Source revision anchoring an accepted preview.
    #[pyo3(get)]
    base_revision: Option<String>,
    /// Only the canonical fields explicitly requested by an accepted preview.
    #[pyo3(get)]
    fields: Vec<PyUserSettingsUpdateField>,
    /// Field-specific or preview-level rejection diagnostics.
    #[pyo3(get)]
    diagnostics: Vec<PyUserSettingsUpdateDiagnostic>,
    /// Accepted core plan retained so commit uses the exact previewed revision and fields.
    accepted_update: Option<AcceptedUserSettingsUpdate>,
}

#[pymethods]
impl PyUserSettingsUpdatePreview {
    /// Commits this accepted preview against the latest canonical document.
    ///
    /// The core holds cross-process coordination while checking the content revision. A stale
    /// preview returns a structured conflict; operational publication failures raise
    /// `UserSettingsCommitError` and leave the newer document untouched.
    fn commit(
        &self,
        py: Python<'_>,
        classic_root: String,
    ) -> PyResult<PyUserSettingsCommitOutcome> {
        let accepted = self.accepted_update.clone().ok_or_else(|| {
            PyValueError::new_err("only an accepted User Settings Update preview can be committed")
        })?;
        let outcome = without_gil(py, move || accepted.commit(classic_root)).map_err(|error| {
            UserSettingsCommitError::new_err(format!("{}: {}", error.code(), error.message()))
        })?;
        Ok(commit_outcome_to_py(outcome))
    }
}

/// Structured result of committing a previously accepted User Settings Update.
#[pyclass(name = "UserSettingsCommitOutcome", frozen, skip_from_py_object)]
pub struct PyUserSettingsCommitOutcome {
    /// Result token: `committed` or `conflict`.
    #[pyo3(get)]
    status: String,
    /// Newly published revision, present only for `committed`.
    #[pyo3(get)]
    revision: Option<String>,
    /// Preview revision, present only for `conflict`.
    #[pyo3(get)]
    expected_revision: Option<String>,
    /// Latest on-disk revision, present only for `conflict`.
    #[pyo3(get)]
    actual_revision: Option<String>,
}

/// Structured result of one replay-safe frontend geometry transition.
#[pyclass(
    name = "UserSettingsFrontendTransitionOutcome",
    frozen,
    skip_from_py_object
)]
pub struct PyUserSettingsFrontendTransitionOutcome {
    /// Result token: `committed`, `conflict`, or `rejected`.
    #[pyo3(get)]
    status: String,
    /// Newly published revision, present only for `committed`.
    #[pyo3(get)]
    revision: Option<String>,
    /// Final retry revision, present only for `conflict`.
    #[pyo3(get)]
    expected_revision: Option<String>,
    /// Latest on-disk revision, present only for `conflict`.
    #[pyo3(get)]
    actual_revision: Option<String>,
    /// Structured validation diagnostics, populated only for `rejected`.
    #[pyo3(get)]
    diagnostics: Vec<PyUserSettingsUpdateDiagnostic>,
}

/// Tagged result of explicitly importing retired TUI state into User Settings.
#[pyclass(name = "LegacyTuiStateImportOutcome", frozen, skip_from_py_object)]
pub struct PyLegacyTuiStateImportOutcome {
    /// Outcome token identifying the no-op, applied, or conflict case.
    #[pyo3(get)]
    status: String,
    /// Settings classification for migration or trust-gated outcomes.
    #[pyo3(get)]
    classification: Option<String>,
    /// Settings revision for migration or trust-gated outcomes.
    #[pyo3(get)]
    revision: Option<String>,
    /// Concrete retired state path, present only when applied.
    #[pyo3(get)]
    source_path: Option<String>,
    /// Verified retained backup path, present only when applied.
    #[pyo3(get)]
    backup_path: Option<String>,
    /// Revision of exact parsed legacy bytes, present only when applied.
    #[pyo3(get)]
    source_revision: Option<String>,
    /// Independently verified backup revision, present only when applied.
    #[pyo3(get)]
    backup_revision: Option<String>,
    /// User Settings base revision selected for an applied import.
    #[pyo3(get)]
    base_settings_revision: Option<String>,
    /// User Settings revision published by an applied import.
    #[pyo3(get)]
    published_settings_revision: Option<String>,
    /// Selected revision for either conflict outcome.
    #[pyo3(get)]
    expected_revision: Option<String>,
    /// Revision found at the conflicting path.
    #[pyo3(get)]
    actual_revision: Option<String>,
    /// Opaque verified receipt, present only after an applied import.
    #[pyo3(get)]
    receipt: Option<PyLegacyTuiStateImportReceipt>,
}

/// Opaque verified receipt authorizing restoration of one legacy TUI state import.
#[pyclass(name = "LegacyTuiStateImportReceipt", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyLegacyTuiStateImportReceipt {
    inner: LegacyTuiStateImportReceipt,
}

#[pymethods]
impl PyLegacyTuiStateImportReceipt {
    /// Returns the concrete retired `state.json` path left unchanged by import.
    #[getter]
    fn source_path(&self) -> String {
        self.inner.source_path().display().to_string()
    }

    /// Returns the verified content-addressed backup of exact legacy bytes.
    #[getter]
    fn backup_path(&self) -> String {
        self.inner.backup_path().display().to_string()
    }

    /// Returns the canonical User Settings path modified by import.
    #[getter]
    fn settings_path(&self) -> String {
        self.inner.settings_path().display().to_string()
    }

    /// Returns the retained pre-import settings backup path when a document existed.
    #[getter]
    fn settings_backup_path(&self) -> Option<String> {
        self.inner
            .settings_backup_path()
            .map(|path| path.display().to_string())
    }

    /// Returns the revision of the exact parsed legacy bytes.
    #[getter]
    fn source_revision(&self) -> String {
        revision_token(self.inner.source_revision())
    }

    /// Returns the independently verified legacy backup revision.
    #[getter]
    fn backup_revision(&self) -> String {
        revision_token(self.inner.backup_revision())
    }

    /// Returns the User Settings base revision selected by import.
    #[getter]
    fn base_settings_revision(&self) -> String {
        revision_token(self.inner.base_settings_revision())
    }

    /// Returns the User Settings revision published by import.
    #[getter]
    fn published_settings_revision(&self) -> String {
        revision_token(self.inner.published_settings_revision())
    }

    /// Restores the pre-import User Settings state through this verified receipt.
    fn restore(
        &self,
        py: Python<'_>,
        classic_root: String,
    ) -> PyResult<PyLegacyTuiStateImportRestoreOutcome> {
        let receipt = self.inner.clone();
        let outcome = without_gil(py, move || receipt.restore(classic_root)).map_err(|error| {
            LegacyTuiStateImportError::new_err(format!("{}: {}", error.code(), error.message()))
        })?;
        Ok(legacy_tui_state_import_restore_outcome_to_py(outcome))
    }
}

/// Result of restoring User Settings through an applied legacy import receipt.
#[pyclass(
    name = "LegacyTuiStateImportRestoreOutcome",
    frozen,
    skip_from_py_object
)]
pub struct PyLegacyTuiStateImportRestoreOutcome {
    /// Outcome token: `restored` or `conflict`.
    #[pyo3(get)]
    status: String,
    /// Restored revision, present only when restored.
    #[pyo3(get)]
    revision: Option<String>,
    /// Imported revision that had to remain current for restore.
    #[pyo3(get)]
    expected_revision: Option<String>,
    /// Latest User Settings revision, present only when conflicted.
    #[pyo3(get)]
    actual_revision: Option<String>,
}

/// Explicit major/minor User Settings schema version proposed by a migration plan.
#[pyclass(name = "UserSettingsSchemaVersion", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyUserSettingsSchemaVersion {
    /// Breaking-change component.
    #[pyo3(get)]
    major: u32,
    /// Additive-change component.
    #[pyo3(get)]
    minor: u32,
}

/// One version/location endpoint in a proposed User Settings migration.
#[pyclass(name = "UserSettingsMigrationEndpoint", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyUserSettingsMigrationEndpoint {
    /// Root-relative source-location token.
    #[pyo3(get)]
    location: String,
    /// Explicit version, absent for a legacy unversioned form.
    #[pyo3(get)]
    schema_version: Option<PyUserSettingsSchemaVersion>,
}

/// One ordered, reviewable transition in a User Settings migration plan.
#[pyclass(name = "UserSettingsMigrationChange", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyUserSettingsMigrationChange {
    /// Stable change-kind token.
    #[pyo3(get)]
    kind: String,
    /// Source pointer or root-relative path, when applicable.
    #[pyo3(get)]
    source_path: Option<String>,
    /// Target pointer or root-relative path, when applicable.
    #[pyo3(get)]
    target_path: Option<String>,
    /// Deterministic value representation before the change, when applicable.
    #[pyo3(get)]
    before: Option<String>,
    /// Deterministic value representation after the change, when applicable.
    #[pyo3(get)]
    after: Option<String>,
}

/// Structured reason that a User Settings migration plan cannot be produced.
#[pyclass(name = "UserSettingsMigrationDiagnostic", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyUserSettingsMigrationDiagnostic {
    /// Stable machine-readable diagnostic code.
    #[pyo3(get)]
    code: String,
    /// Human-readable diagnostic context.
    #[pyo3(get)]
    message: String,
}

/// Immutable, revision-anchored proposal for an explicit User Settings migration.
#[pyclass(name = "UserSettingsMigrationPlan", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyUserSettingsMigrationPlan {
    /// Whether compatibility requires this plan before ordinary commits.
    #[pyo3(get)]
    required: bool,
    /// Exact content revision against which the plan was produced.
    #[pyo3(get)]
    base_revision: String,
    /// Current version/location endpoint.
    #[pyo3(get)]
    source: PyUserSettingsMigrationEndpoint,
    /// Proposed version/location endpoint.
    #[pyo3(get)]
    target: PyUserSettingsMigrationEndpoint,
    /// Ordered review rows describing the proposed transition.
    #[pyo3(get)]
    changes: Vec<PyUserSettingsMigrationChange>,
    /// Exact opened bytes retained for reversal and later backup verification.
    original_content: Vec<u8>,
    /// Deterministic proposed document bytes; planning does not publish them.
    proposed_content: Vec<u8>,
    /// Core plan retained so reversal preserves the exact domain contract.
    inner: UserSettingsMigrationPlan,
}

#[pymethods]
impl PyUserSettingsMigrationPlan {
    /// Returns the exact opened document bytes.
    #[getter]
    fn original_content<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        PyBytes::new(py, &self.original_content)
    }

    /// Returns the deterministic proposed document bytes.
    #[getter]
    fn proposed_content<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        PyBytes::new(py, &self.proposed_content)
    }

    /// Builds the exact inverse plan in memory without accessing the filesystem.
    fn reverse_in_memory(&self) -> Self {
        migration_plan_to_py(self.inner.reverse_in_memory())
    }

    /// Explicitly applies this caller-approved plan against the opened revision.
    ///
    /// Conflicts are returned as data; backup or publication failures raise
    /// `UserSettingsMigrationError` without flattening the core diagnostic code.
    fn apply(
        &self,
        py: Python<'_>,
        classic_root: String,
    ) -> PyResult<PyUserSettingsMigrationApplyOutcome> {
        let plan = self.inner.clone();
        let outcome = without_gil(py, move || plan.apply(classic_root)).map_err(|error| {
            UserSettingsMigrationError::new_err(format!("{}: {}", error.code(), error.message()))
        })?;
        Ok(migration_apply_outcome_to_py(outcome))
    }
}

/// Structured outcome from explicitly applying an approved migration plan.
#[pyclass(
    name = "UserSettingsMigrationApplyOutcome",
    frozen,
    skip_from_py_object
)]
pub struct PyUserSettingsMigrationApplyOutcome {
    /// Result token: `applied` or `conflict`.
    #[pyo3(get)]
    status: String,
    /// Verified migration receipt, present only when `status` is `applied`.
    #[pyo3(get)]
    receipt: Option<PyUserSettingsMigrationReceipt>,
    /// Approved plan revision, present only when `status` is `conflict`.
    #[pyo3(get)]
    expected_revision: Option<String>,
    /// Latest on-disk revision, present only when `status` is `conflict`.
    #[pyo3(get)]
    actual_revision: Option<String>,
}

/// Opaque verified record of one successfully applied User Settings migration.
#[pyclass(name = "UserSettingsMigrationReceipt", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyUserSettingsMigrationReceipt {
    /// Document path selected when the migration was approved and applied.
    #[pyo3(get)]
    source_path: String,
    /// Canonical path at which the migrated document was published.
    #[pyo3(get)]
    destination_path: String,
    /// Retained byte-exact backup verified before publication.
    #[pyo3(get)]
    backup_path: String,
    /// Source version/location endpoint recorded by the approved plan.
    #[pyo3(get)]
    source: PyUserSettingsMigrationEndpoint,
    /// Destination version/location endpoint recorded by the approved plan.
    #[pyo3(get)]
    target: PyUserSettingsMigrationEndpoint,
    /// Exact-byte revision attested by the retained backup.
    #[pyo3(get)]
    backup_revision: String,
    /// Exact-byte revision verified after migration publication.
    #[pyo3(get)]
    published_revision: String,
    /// Core receipt retained so restoration cannot be fabricated from public fields.
    inner: UserSettingsMigrationReceipt,
}

#[pymethods]
impl PyUserSettingsMigrationReceipt {
    /// Explicitly restores this receipt's verified backup under core coordination.
    ///
    /// Conflicts are returned as data; backup verification or publication failures raise
    /// `UserSettingsMigrationError` with the stable core diagnostic code.
    fn restore(
        &self,
        py: Python<'_>,
        classic_root: String,
    ) -> PyResult<PyUserSettingsMigrationRestoreOutcome> {
        let receipt = self.inner.clone();
        let outcome = without_gil(py, move || receipt.restore(classic_root)).map_err(|error| {
            UserSettingsMigrationError::new_err(format!("{}: {}", error.code(), error.message()))
        })?;
        Ok(migration_restore_outcome_to_py(outcome))
    }
}

/// Structured outcome from explicitly restoring a verified migration receipt.
#[pyclass(
    name = "UserSettingsMigrationRestoreOutcome",
    frozen,
    skip_from_py_object
)]
pub struct PyUserSettingsMigrationRestoreOutcome {
    /// Result token: `restored` or `conflict`.
    #[pyo3(get)]
    status: String,
    /// Restored byte-exact revision, present only when `status` is `restored`.
    #[pyo3(get)]
    revision: Option<String>,
    /// Published migration revision, present only when `status` is `conflict`.
    #[pyo3(get)]
    expected_revision: Option<String>,
    /// Latest on-disk revision, present only when `status` is `conflict`.
    #[pyo3(get)]
    actual_revision: Option<String>,
}

/// Result of planning an explicit User Settings migration.
#[pyclass(
    name = "UserSettingsMigrationPlanningOutcome",
    frozen,
    skip_from_py_object
)]
#[derive(Clone)]
pub struct PyUserSettingsMigrationPlanningOutcome {
    /// Result token: `not_required`, `planned`, or `unsupported`.
    #[pyo3(get)]
    status: String,
    /// Proposed migration, present only when `status` is `planned`.
    #[pyo3(get)]
    plan: Option<PyUserSettingsMigrationPlan>,
    /// Planning diagnostics, populated only when the source is unsupported.
    #[pyo3(get)]
    diagnostics: Vec<PyUserSettingsMigrationDiagnostic>,
}

/// Read-only User Settings snapshot returned by `open_user_settings`.
#[pyclass(name = "UserSettingsSnapshot", frozen)]
pub struct PyUserSettingsSnapshot {
    /// Typed update preferences.
    #[pyo3(get)]
    update_preferences: PyUpdatePreferences,
    /// Typed Crash Log Scan settings.
    #[pyo3(get)]
    crash_log_scan_settings: PyCrashLogScanSettings,
    /// Typed Game Setup settings.
    #[pyo3(get)]
    game_setup_settings: PyGameSetupSettings,
    /// Typed, namespaced frontend state.
    #[pyo3(get)]
    frontend_state: PyFrontendState,
    /// Selected source token: `canonical`, `legacy`, or `missing`.
    #[pyo3(get)]
    source_location: String,
    /// Selected source path, absent when the document is missing.
    #[pyo3(get)]
    source_path: Option<String>,
    /// Document format/schema classification token.
    #[pyo3(get)]
    classification: String,
    /// Parsed schema major, absent for missing or unversioned documents.
    #[pyo3(get)]
    schema_major: Option<u32>,
    /// Parsed schema minor, absent for missing or unversioned documents.
    #[pyo3(get)]
    schema_minor: Option<u32>,
    /// Content-derived revision token (`sha256:…`, `missing`, or `unavailable`).
    #[pyo3(get)]
    revision: String,
    /// Commit policy token: `eligible`, `requires_migration`, or `blocked_untrusted`.
    #[pyo3(get)]
    commit_eligibility: String,
    /// Structured diagnostics in discovery and validation order.
    #[pyo3(get)]
    diagnostics: Vec<PyUserSettingsDiagnostic>,
    /// Exact source bytes retained for later semantic preservation.
    original_content: Option<Vec<u8>>,
    /// Core snapshot retained so previews stay anchored to this exact open.
    inner: UserSettings,
}

#[pymethods]
impl PyUserSettingsSnapshot {
    /// Returns the exact source bytes, or `None` when no bytes were available.
    #[getter]
    fn original_content<'py>(&self, py: Python<'py>) -> Option<Bound<'py, PyBytes>> {
        self.original_content
            .as_deref()
            .map(|content| PyBytes::new(py, content))
    }

    /// Validates every requested field as one unit without changing the snapshot or disk.
    fn preview_update(
        &self,
        update: PyRef<'_, PyUserSettingsUpdate>,
    ) -> PyUserSettingsUpdatePreview {
        update_preview_to_py(self.inner.preview_update(update.inner.clone()))
    }

    /// Validates an explicit missing-document bootstrap without writing to disk.
    ///
    /// This seam accepts only a trusted missing snapshot. The returned preview retains the
    /// bootstrap marker so `commit` publishes the complete Rust-owned default document before
    /// applying the requested fields.
    fn preview_bootstrap(
        &self,
        update: PyRef<'_, PyUserSettingsUpdate>,
    ) -> PyUserSettingsUpdatePreview {
        update_preview_to_py(self.inner.preview_bootstrap(update.inner.clone()))
    }

    /// Publishes one GUI geometry transition with at most one Rust-owned conflict replay.
    ///
    /// `tab` must be a stable maintained-window token. Validation rejection and a second
    /// concurrent edit return structured outcomes; operational persistence failures raise
    /// `UserSettingsCommitError` without partially writing the transition.
    fn commit_frontend_geometry_transition(
        &self,
        py: Python<'_>,
        classic_root: String,
        tab: String,
        maximized: bool,
        width: i64,
        height: i64,
    ) -> PyResult<PyUserSettingsFrontendTransitionOutcome> {
        let window = GuiWindow::parse(&tab).ok_or_else(|| {
            PyValueError::new_err(format!(
                "unknown GUI window '{tab}'; expected one of: main_tab, backups_tab, articles_tab, results_tab"
            ))
        })?;
        let expected_revision = self.inner.revision().clone();
        let outcome = without_gil(py, move || {
            UserSettings::commit_frontend_geometry_transition(
                classic_root,
                &expected_revision,
                window,
                maximized,
                width,
                height,
            )
        })
        .map_err(|error| {
            UserSettingsCommitError::new_err(format!("{}: {}", error.code(), error.message()))
        })?;
        Ok(frontend_transition_outcome_to_py(outcome))
    }

    /// Produces a deterministic, reversible plan without accessing the filesystem.
    fn plan_migration(&self) -> PyUserSettingsMigrationPlanningOutcome {
        migration_planning_outcome_to_py(self.inner.plan_migration())
    }
}

/// Opens User Settings relative to an explicit CLASSIC root without changing
/// either supported source document.
#[pyfunction]
pub fn open_user_settings(classic_root: String) -> PyUserSettingsSnapshot {
    user_settings_snapshot_to_py(UserSettings::open(classic_root))
}

/// Explicitly imports one retired TUI `state.json` into the canonical User Settings store.
///
/// Expected no-op and conflict cases return tagged data. Operational failures raise
/// `LegacyTuiStateImportError` with the stable core code prefixed in its message.
#[pyfunction]
pub fn import_legacy_tui_state_into_user_settings(
    py: Python<'_>,
    classic_root: String,
    legacy_state_path: String,
) -> PyResult<PyLegacyTuiStateImportOutcome> {
    let outcome = without_gil(py, move || {
        import_legacy_tui_state(classic_root, legacy_state_path)
    })
    .map_err(|error| {
        LegacyTuiStateImportError::new_err(format!("{}: {}", error.code(), error.message()))
    })?;
    Ok(legacy_tui_state_import_outcome_to_py(outcome))
}

/// Returns the Rust-owned published defaults without consulting the filesystem.
#[pyfunction]
pub fn user_settings_published_defaults() -> PyUserSettingsSnapshot {
    user_settings_snapshot_to_py(UserSettings::published_defaults())
}

/// Converts one core User Settings snapshot into the public Python-owned shape.
fn user_settings_snapshot_to_py(settings: UserSettings) -> PyUserSettingsSnapshot {
    let (schema_major, schema_minor) = settings
        .schema_version()
        .map_or((None, None), |(major, minor)| (Some(major), Some(minor)));

    PyUserSettingsSnapshot {
        update_preferences: PyUpdatePreferences {
            update_check: settings.update_preferences().update_check(),
            origin: preference_origin_token(settings.update_preferences().update_check_origin())
                .to_string(),
            update_source: settings
                .update_preferences()
                .update_source()
                .as_str()
                .to_string(),
            update_source_origin: preference_origin_token(
                settings.update_preferences().update_source_origin(),
            )
            .to_string(),
        },
        crash_log_scan_settings: crash_log_scan_settings_to_py(settings.crash_log_scan_settings()),
        game_setup_settings: game_setup_settings_to_py(settings.game_setup_settings()),
        frontend_state: frontend_state_to_py(settings.frontend_state()),
        source_location: source_location_token(settings.source().location()).to_string(),
        source_path: settings
            .source()
            .path()
            .map(|path| path.display().to_string()),
        classification: classification_token(settings.classification()).to_string(),
        schema_major,
        schema_minor,
        revision: revision_token(settings.revision()),
        commit_eligibility: commit_eligibility_token(settings.commit_eligibility()).to_string(),
        diagnostics: settings
            .diagnostics()
            .iter()
            .map(|diagnostic| PyUserSettingsDiagnostic {
                code: diagnostic.code().to_string(),
                message: diagnostic.message().to_string(),
            })
            .collect(),
        original_content: settings.original_bytes().map(<[u8]>::to_vec),
        inner: settings,
    }
}

/// Converts core frontend state into nested Python-owned values.
fn frontend_state_to_py(state: &FrontendState) -> PyFrontendState {
    PyFrontendState {
        preferences: frontend_preferences_to_py(state.preferences()),
        window_geometry: gui_window_geometry_to_py(state.window_geometry()),
        tui: tui_remembered_state_to_py(state.tui()),
    }
}

/// Converts shared frontend preferences into Python-owned values.
fn frontend_preferences_to_py(preferences: &FrontendPreferences) -> PyFrontendPreferences {
    PyFrontendPreferences {
        auto_switch_after_scan: preferences.auto_switch_after_scan(),
        auto_switch_after_scan_origin: preference_origin_token(
            preferences.auto_switch_after_scan_origin(),
        )
        .to_string(),
        auto_refresh_interval_ms: preferences.auto_refresh_interval_ms(),
        auto_refresh_interval_ms_origin: preference_origin_token(
            preferences.auto_refresh_interval_ms_origin(),
        )
        .to_string(),
    }
}

/// Converts all maintained GUI tab geometry into Python-owned values.
fn gui_window_geometry_to_py(geometry: &GuiWindowGeometry) -> PyGuiWindowGeometry {
    PyGuiWindowGeometry {
        main_tab: window_geometry_to_py(geometry.main_tab()),
        backups_tab: window_geometry_to_py(geometry.backups_tab()),
        articles_tab: window_geometry_to_py(geometry.articles_tab()),
        results_tab: window_geometry_to_py(geometry.results_tab()),
    }
}

/// Converts one core GUI geometry value into a Python-owned value.
fn window_geometry_to_py(geometry: &WindowGeometry) -> PyWindowGeometry {
    PyWindowGeometry {
        maximized: geometry.maximized(),
        maximized_origin: preference_origin_token(geometry.maximized_origin()).to_string(),
        width: geometry.width(),
        width_origin: preference_origin_token(geometry.width_origin()).to_string(),
        height: geometry.height(),
        height_origin: preference_origin_token(geometry.height_origin()).to_string(),
    }
}

/// Converts canonical TUI remembered state into a Python-owned value.
fn tui_remembered_state_to_py(state: &TuiRememberedState) -> PyTuiRememberedState {
    PyTuiRememberedState {
        active_tab: state.active_tab(),
        active_tab_origin: preference_origin_token(state.active_tab_origin()).to_string(),
        results_panel_width: state.results_panel_width(),
        results_panel_width_origin: preference_origin_token(state.results_panel_width_origin())
            .to_string(),
        sort_ascending: state.sort_ascending(),
        sort_ascending_origin: preference_origin_token(state.sort_ascending_origin()).to_string(),
    }
}

/// Converts core Game Setup settings into Python-owned values without normalizing paths.
fn game_setup_settings_to_py(settings: &GameSetupSettings) -> PyGameSetupSettings {
    PyGameSetupSettings {
        managed_game: settings.managed_game().as_str().to_string(),
        managed_game_origin: preference_origin_token(settings.managed_game_origin()).to_string(),
        game_version_selection: settings.game_version_selection().as_str().to_string(),
        game_version_selection_origin: preference_origin_token(
            settings.game_version_selection_origin(),
        )
        .to_string(),
        game_root: settings.game_root().map(str::to_string),
        game_root_origin: preference_origin_token(settings.game_root_origin()).to_string(),
        game_executable: settings.game_executable().map(str::to_string),
        game_executable_origin: preference_origin_token(settings.game_executable_origin())
            .to_string(),
        documents_root: settings.documents_root().map(str::to_string),
        documents_root_origin: preference_origin_token(settings.documents_root_origin())
            .to_string(),
        ini_folder: settings.ini_folder().map(str::to_string),
        ini_folder_origin: preference_origin_token(settings.ini_folder_origin()).to_string(),
        mods_root: settings.mods_root().map(str::to_string),
        mods_root_origin: preference_origin_token(settings.mods_root_origin()).to_string(),
        custom_scan_input: settings.custom_scan_input().map(str::to_string),
        custom_scan_input_origin: preference_origin_token(settings.custom_scan_input_origin())
            .to_string(),
        papyrus_log: settings.papyrus_log().map(str::to_string),
        papyrus_log_origin: preference_origin_token(settings.papyrus_log_origin()).to_string(),
    }
}

/// Converts core Crash Log Scan settings into Python-owned values.
fn crash_log_scan_settings_to_py(settings: &CrashLogScanSettings) -> PyCrashLogScanSettings {
    PyCrashLogScanSettings {
        fcx_mode: settings.fcx_mode(),
        fcx_mode_origin: preference_origin_token(settings.fcx_mode_origin()).to_string(),
        simplify_logs: settings.simplify_logs(),
        simplify_logs_origin: preference_origin_token(settings.simplify_logs_origin()).to_string(),
        show_statistics: settings.show_statistics(),
        show_statistics_origin: preference_origin_token(settings.show_statistics_origin())
            .to_string(),
        formid_value_lookup: settings.formid_value_lookup(),
        formid_value_lookup_origin: preference_origin_token(settings.formid_value_lookup_origin())
            .to_string(),
        formid_databases: settings
            .formid_databases()
            .iter()
            .map(|(game, paths)| (game.clone(), paths.clone()))
            .collect(),
        formid_databases_origin: preference_origin_token(settings.formid_databases_origin())
            .to_string(),
        move_unsolved_logs: settings.move_unsolved_logs(),
        move_unsolved_logs_origin: preference_origin_token(settings.move_unsolved_logs_origin())
            .to_string(),
        unsolved_logs_destination: settings.unsolved_logs_destination().map(str::to_string),
        unsolved_logs_destination_origin: preference_origin_token(
            settings.unsolved_logs_destination_origin(),
        )
        .to_string(),
        custom_scan_input: settings.custom_scan_input().map(str::to_string),
        custom_scan_input_origin: preference_origin_token(settings.custom_scan_input_origin())
            .to_string(),
        game_version_selection: settings.game_version_selection().as_str().to_string(),
        game_version_selection_origin: preference_origin_token(
            settings.game_version_selection_origin(),
        )
        .to_string(),
        max_concurrent_scans: settings.max_concurrent_scans(),
        max_concurrent_scans_origin: preference_origin_token(
            settings.max_concurrent_scans_origin(),
        )
        .to_string(),
    }
}

/// Converts an all-or-nothing core preview into one stable Python result shape.
fn update_preview_to_py(preview: UserSettingsUpdatePreview) -> PyUserSettingsUpdatePreview {
    match preview {
        UserSettingsUpdatePreview::Accepted(accepted) => PyUserSettingsUpdatePreview {
            accepted: true,
            base_revision: Some(revision_token(accepted.base_revision())),
            fields: accepted.fields().iter().map(update_field_to_py).collect(),
            diagnostics: Vec::new(),
            accepted_update: Some(accepted),
        },
        UserSettingsUpdatePreview::Rejected(diagnostics) => PyUserSettingsUpdatePreview {
            accepted: false,
            base_revision: None,
            fields: Vec::new(),
            diagnostics: diagnostics
                .iter()
                .map(|diagnostic| PyUserSettingsUpdateDiagnostic {
                    field_path: diagnostic.field_path().map(str::to_string),
                    code: diagnostic.code().to_string(),
                    message: diagnostic.message().to_string(),
                })
                .collect(),
            accepted_update: None,
        },
    }
}

/// Converts the core commit result without flattening a stale revision into an exception.
fn commit_outcome_to_py(outcome: UserSettingsCommitOutcome) -> PyUserSettingsCommitOutcome {
    match outcome {
        UserSettingsCommitOutcome::Committed { revision } => PyUserSettingsCommitOutcome {
            status: "committed".to_string(),
            revision: Some(revision_token(&revision)),
            expected_revision: None,
            actual_revision: None,
        },
        UserSettingsCommitOutcome::Conflict {
            expected_revision,
            actual_revision,
        } => PyUserSettingsCommitOutcome {
            status: "conflict".to_string(),
            revision: None,
            expected_revision: Some(revision_token(&expected_revision)),
            actual_revision: Some(revision_token(&actual_revision)),
        },
    }
}

/// Converts the replay-safe geometry transition outcome without flattening diagnostics.
fn frontend_transition_outcome_to_py(
    outcome: CoreUserSettingsFrontendTransitionOutcome,
) -> PyUserSettingsFrontendTransitionOutcome {
    match outcome {
        CoreUserSettingsFrontendTransitionOutcome::Committed { revision } => {
            PyUserSettingsFrontendTransitionOutcome {
                status: "committed".to_string(),
                revision: Some(revision_token(&revision)),
                expected_revision: None,
                actual_revision: None,
                diagnostics: Vec::new(),
            }
        }
        CoreUserSettingsFrontendTransitionOutcome::Rejected { diagnostics } => {
            PyUserSettingsFrontendTransitionOutcome {
                status: "rejected".to_string(),
                revision: None,
                expected_revision: None,
                actual_revision: None,
                diagnostics: diagnostics
                    .into_iter()
                    .map(|diagnostic| PyUserSettingsUpdateDiagnostic {
                        field_path: diagnostic.field_path().map(ToOwned::to_owned),
                        code: diagnostic.code().to_string(),
                        message: diagnostic.message().to_string(),
                    })
                    .collect(),
            }
        }
        CoreUserSettingsFrontendTransitionOutcome::Conflict {
            expected_revision,
            actual_revision,
        } => PyUserSettingsFrontendTransitionOutcome {
            status: "conflict".to_string(),
            revision: None,
            expected_revision: Some(revision_token(&expected_revision)),
            actual_revision: Some(revision_token(&actual_revision)),
            diagnostics: Vec::new(),
        },
    }
}

/// Converts every core legacy import outcome into one stable Python object shape.
fn legacy_tui_state_import_outcome_to_py(
    outcome: LegacyTuiStateImportOutcome,
) -> PyLegacyTuiStateImportOutcome {
    let mut result = PyLegacyTuiStateImportOutcome {
        status: String::new(),
        classification: None,
        revision: None,
        source_path: None,
        backup_path: None,
        source_revision: None,
        backup_revision: None,
        base_settings_revision: None,
        published_settings_revision: None,
        expected_revision: None,
        actual_revision: None,
        receipt: None,
    };
    match outcome {
        LegacyTuiStateImportOutcome::NoLegacySource => {
            result.status = "no_legacy_source".to_string();
        }
        LegacyTuiStateImportOutcome::RequiresSettingsMigration {
            classification,
            revision,
        } => {
            result.status = "requires_settings_migration".to_string();
            result.classification = Some(classification_token(classification).to_string());
            result.revision = Some(revision_token(&revision));
        }
        LegacyTuiStateImportOutcome::UntrustedSettingsBase {
            classification,
            revision,
        } => {
            result.status = "untrusted_settings_base".to_string();
            result.classification = Some(classification_token(classification).to_string());
            result.revision = Some(revision_token(&revision));
        }
        LegacyTuiStateImportOutcome::Applied(receipt) => {
            result.status = "applied".to_string();
            result.source_path = Some(receipt.source_path().display().to_string());
            result.backup_path = Some(receipt.backup_path().display().to_string());
            result.source_revision = Some(revision_token(receipt.source_revision()));
            result.backup_revision = Some(revision_token(receipt.backup_revision()));
            result.base_settings_revision = Some(revision_token(receipt.base_settings_revision()));
            result.published_settings_revision =
                Some(revision_token(receipt.published_settings_revision()));
            result.receipt = Some(PyLegacyTuiStateImportReceipt { inner: receipt });
        }
        LegacyTuiStateImportOutcome::SettingsConflict {
            expected_revision,
            actual_revision,
        } => {
            result.status = "settings_conflict".to_string();
            result.expected_revision = Some(revision_token(&expected_revision));
            result.actual_revision = Some(revision_token(&actual_revision));
        }
        LegacyTuiStateImportOutcome::LegacySourceConflict {
            expected_revision,
            actual_revision,
        } => {
            result.status = "legacy_source_conflict".to_string();
            result.expected_revision = Some(revision_token(&expected_revision));
            result.actual_revision = Some(revision_token(&actual_revision));
        }
    }
    result
}

/// Converts a core restore outcome while retaining conflict revision evidence.
fn legacy_tui_state_import_restore_outcome_to_py(
    outcome: LegacyTuiStateImportRestoreOutcome,
) -> PyLegacyTuiStateImportRestoreOutcome {
    match outcome {
        LegacyTuiStateImportRestoreOutcome::Restored { revision } => {
            PyLegacyTuiStateImportRestoreOutcome {
                status: "restored".to_string(),
                revision: Some(revision_token(&revision)),
                expected_revision: None,
                actual_revision: None,
            }
        }
        LegacyTuiStateImportRestoreOutcome::Conflict {
            expected_revision,
            actual_revision,
        } => PyLegacyTuiStateImportRestoreOutcome {
            status: "conflict".to_string(),
            revision: None,
            expected_revision: Some(revision_token(&expected_revision)),
            actual_revision: Some(revision_token(&actual_revision)),
        },
    }
}

/// Converts the core planning result into one stable Python outcome shape.
fn migration_planning_outcome_to_py(
    outcome: MigrationPlanningOutcome,
) -> PyUserSettingsMigrationPlanningOutcome {
    match outcome {
        MigrationPlanningOutcome::NotRequired => PyUserSettingsMigrationPlanningOutcome {
            status: "not_required".to_string(),
            plan: None,
            diagnostics: Vec::new(),
        },
        MigrationPlanningOutcome::Planned(plan) => PyUserSettingsMigrationPlanningOutcome {
            status: "planned".to_string(),
            plan: Some(migration_plan_to_py(plan)),
            diagnostics: Vec::new(),
        },
        MigrationPlanningOutcome::Unsupported(diagnostics) => {
            PyUserSettingsMigrationPlanningOutcome {
                status: "unsupported".to_string(),
                plan: None,
                diagnostics: diagnostics.iter().map(migration_diagnostic_to_py).collect(),
            }
        }
    }
}

/// Converts an immutable core migration plan while retaining it for exact reversal.
fn migration_plan_to_py(plan: UserSettingsMigrationPlan) -> PyUserSettingsMigrationPlan {
    PyUserSettingsMigrationPlan {
        required: plan.required(),
        base_revision: revision_token(plan.base_revision()),
        source: migration_endpoint_to_py(plan.source()),
        target: migration_endpoint_to_py(plan.target()),
        changes: plan.changes().iter().map(migration_change_to_py).collect(),
        original_content: plan.original_bytes().to_vec(),
        proposed_content: plan.proposed_bytes().to_vec(),
        inner: plan,
    }
}

/// Converts core apply success and conflict variants without turning expected conflicts into errors.
fn migration_apply_outcome_to_py(
    outcome: UserSettingsMigrationApplyOutcome,
) -> PyUserSettingsMigrationApplyOutcome {
    match outcome {
        UserSettingsMigrationApplyOutcome::Applied(receipt) => {
            PyUserSettingsMigrationApplyOutcome {
                status: "applied".to_string(),
                receipt: Some(migration_receipt_to_py(receipt)),
                expected_revision: None,
                actual_revision: None,
            }
        }
        UserSettingsMigrationApplyOutcome::Conflict {
            expected_revision,
            actual_revision,
        } => PyUserSettingsMigrationApplyOutcome {
            status: "conflict".to_string(),
            receipt: None,
            expected_revision: Some(revision_token(&expected_revision)),
            actual_revision: Some(revision_token(&actual_revision)),
        },
    }
}

/// Converts a verified core receipt while retaining its opaque restoration authority.
fn migration_receipt_to_py(
    receipt: UserSettingsMigrationReceipt,
) -> PyUserSettingsMigrationReceipt {
    PyUserSettingsMigrationReceipt {
        source_path: receipt.source_path().display().to_string(),
        destination_path: receipt.destination_path().display().to_string(),
        backup_path: receipt.backup_path().display().to_string(),
        source: migration_endpoint_to_py(receipt.source()),
        target: migration_endpoint_to_py(receipt.target()),
        backup_revision: revision_token(receipt.backup_revision()),
        published_revision: revision_token(receipt.published_revision()),
        inner: receipt,
    }
}

/// Converts core restore success and conflict variants without hiding revision evidence.
fn migration_restore_outcome_to_py(
    outcome: UserSettingsMigrationRestoreOutcome,
) -> PyUserSettingsMigrationRestoreOutcome {
    match outcome {
        UserSettingsMigrationRestoreOutcome::Restored { revision } => {
            PyUserSettingsMigrationRestoreOutcome {
                status: "restored".to_string(),
                revision: Some(revision_token(&revision)),
                expected_revision: None,
                actual_revision: None,
            }
        }
        UserSettingsMigrationRestoreOutcome::Conflict {
            expected_revision,
            actual_revision,
        } => PyUserSettingsMigrationRestoreOutcome {
            status: "conflict".to_string(),
            revision: None,
            expected_revision: Some(revision_token(&expected_revision)),
            actual_revision: Some(revision_token(&actual_revision)),
        },
    }
}

/// Converts one core migration endpoint into Python-owned location and version values.
fn migration_endpoint_to_py(endpoint: &MigrationEndpoint) -> PyUserSettingsMigrationEndpoint {
    PyUserSettingsMigrationEndpoint {
        location: source_location_token(endpoint.location()).to_string(),
        schema_version: endpoint
            .schema_version()
            .map(user_settings_schema_version_to_py),
    }
}

/// Converts one explicit core User Settings schema version.
fn user_settings_schema_version_to_py(
    version: UserSettingsSchemaVersion,
) -> PyUserSettingsSchemaVersion {
    PyUserSettingsSchemaVersion {
        major: version.major(),
        minor: version.minor(),
    }
}

/// Converts one ordered core migration change into a reviewable Python row.
fn migration_change_to_py(change: &MigrationChange) -> PyUserSettingsMigrationChange {
    PyUserSettingsMigrationChange {
        kind: migration_change_kind_token(change.kind()).to_string(),
        source_path: change.source_path().map(str::to_string),
        target_path: change.target_path().map(str::to_string),
        before: change.before().map(str::to_string),
        after: change.after().map(str::to_string),
    }
}

/// Converts one structured planning diagnostic.
fn migration_diagnostic_to_py(
    diagnostic: &MigrationDiagnostic,
) -> PyUserSettingsMigrationDiagnostic {
    PyUserSettingsMigrationDiagnostic {
        code: diagnostic.code().to_string(),
        message: diagnostic.message().to_string(),
    }
}

/// Returns the Python token for one stable migration change category.
fn migration_change_kind_token(kind: MigrationChangeKind) -> &'static str {
    match kind {
        MigrationChangeKind::LocationTransition => "location_transition",
        MigrationChangeKind::SchemaVersionTransition => "schema_version_transition",
        MigrationChangeKind::FieldTransition => "field_transition",
        MigrationChangeKind::AliasCanonicalization => "alias_canonicalization",
        MigrationChangeKind::KnownValueCanonicalization => "known_value_canonicalization",
    }
}

/// Converts one accepted core field while preserving its typed requested value.
fn update_field_to_py(field: &UserSettingsUpdateField) -> PyUserSettingsUpdateField {
    let value = match field {
        UserSettingsUpdateField::UpdateCheck(value)
        | UserSettingsUpdateField::AutoSwitchAfterScan(value)
        | UserSettingsUpdateField::WindowMaximized(_, value)
        | UserSettingsUpdateField::TuiSortAscending(value)
        | UserSettingsUpdateField::FcxMode(value)
        | UserSettingsUpdateField::SimplifyLogs(value)
        | UserSettingsUpdateField::ShowStatistics(value)
        | UserSettingsUpdateField::FormIdValueLookup(value)
        | UserSettingsUpdateField::MoveUnsolvedLogs(value) => {
            PyUserSettingsUpdateValue::Boolean(*value)
        }
        UserSettingsUpdateField::GameVersionSelection(value) => {
            PyUserSettingsUpdateValue::String(value.as_str().to_string())
        }
        UserSettingsUpdateField::UpdateSource(value) => {
            PyUserSettingsUpdateValue::String(value.as_str().to_string())
        }
        UserSettingsUpdateField::ManagedGame(value) => {
            PyUserSettingsUpdateValue::String(value.as_str().to_string())
        }
        UserSettingsUpdateField::FormIdDatabases(value) => PyUserSettingsUpdateValue::StringLists(
            value
                .iter()
                .map(|(game, paths)| (game.clone(), paths.clone()))
                .collect(),
        ),
        UserSettingsUpdateField::GameRoot(value)
        | UserSettingsUpdateField::GameExecutable(value)
        | UserSettingsUpdateField::DocumentsRoot(value)
        | UserSettingsUpdateField::IniFolder(value)
        | UserSettingsUpdateField::ModsFolder(value)
        | UserSettingsUpdateField::PapyrusLogPath(value)
        | UserSettingsUpdateField::UnsolvedLogsDestination(value)
        | UserSettingsUpdateField::CustomScanInput(value) => {
            PyUserSettingsUpdateValue::OptionalString(value.clone())
        }
        UserSettingsUpdateField::MaxConcurrentScans(value) => {
            PyUserSettingsUpdateValue::UnsignedInteger(*value)
        }
        UserSettingsUpdateField::WindowWidth(_, value)
        | UserSettingsUpdateField::WindowHeight(_, value) => {
            PyUserSettingsUpdateValue::UnsignedInteger(*value)
        }
        UserSettingsUpdateField::TuiActiveTab(value) => {
            PyUserSettingsUpdateValue::UnsignedInteger(u32::from(*value))
        }
        UserSettingsUpdateField::TuiResultsPanelWidth(value) => {
            PyUserSettingsUpdateValue::UnsignedInteger(u32::from(*value))
        }
    };

    PyUserSettingsUpdateField {
        canonical_path: field.canonical_path().to_string(),
        value,
    }
}

/// Returns the Python token for preference provenance.
fn preference_origin_token(origin: PreferenceOrigin) -> &'static str {
    match origin {
        PreferenceOrigin::Document => "document",
        PreferenceOrigin::Default => "default",
        PreferenceOrigin::DegradedFallback => "degraded_fallback",
    }
}

/// Returns the Python token for source location.
fn source_location_token(location: SourceLocation) -> &'static str {
    match location {
        SourceLocation::Canonical => "canonical",
        SourceLocation::Legacy => "legacy",
        SourceLocation::Missing => "missing",
    }
}

/// Returns the Python token for document classification.
fn classification_token(classification: DocumentClassification) -> &'static str {
    match classification {
        DocumentClassification::Current => "current",
        DocumentClassification::Unversioned => "unversioned",
        DocumentClassification::Older => "older",
        DocumentClassification::NewerCompatible => "newer_compatible",
        DocumentClassification::FutureMajor => "future_major",
        DocumentClassification::LegacyFlat => "legacy_flat",
        DocumentClassification::Malformed => "malformed",
        DocumentClassification::Missing => "missing",
    }
}

/// Returns the Python token for commit eligibility.
fn commit_eligibility_token(eligibility: CommitEligibility) -> &'static str {
    match eligibility {
        CommitEligibility::Eligible => "eligible",
        CommitEligibility::RequiresMigration => "requires_migration",
        CommitEligibility::BlockedUntrusted => "blocked_untrusted",
    }
}

/// Formats the content revision for Python consumers.
fn revision_token(revision: &Revision) -> String {
    match revision {
        Revision::Missing => "missing".to_string(),
        Revision::Unavailable => "unavailable".to_string(),
        Revision::ContentSha256(digest) => {
            let mut token = String::with_capacity("sha256:".len() + digest.len() * 2);
            token.push_str("sha256:");
            for byte in digest {
                use std::fmt::Write as _;
                write!(&mut token, "{byte:02x}").expect("writing to a String cannot fail");
            }
            token
        }
    }
}

/// Python module for typed User Settings access and explicit conflict-safe updates.
#[pymodule]
fn classic_user_settings(module: &Bound<'_, PyModule>) -> PyResult<()> {
    classic_shared::configure_python_stdio(module.py());
    module.add("__version__", env!("CARGO_PKG_VERSION"))?;
    module.add_class::<PyUserSettingsDiagnostic>()?;
    module.add_class::<PyUpdatePreferences>()?;
    module.add_class::<PyCrashLogScanSettings>()?;
    module.add_class::<PyGameSetupSettings>()?;
    module.add_class::<PyFrontendPreferences>()?;
    module.add_class::<PyWindowGeometry>()?;
    module.add_class::<PyGuiWindowGeometry>()?;
    module.add_class::<PyTuiRememberedState>()?;
    module.add_class::<PyFrontendState>()?;
    module.add_class::<PyUserSettingsUpdate>()?;
    module.add_class::<PyUserSettingsUpdateDiagnostic>()?;
    module.add_class::<PyUserSettingsUpdateField>()?;
    module.add_class::<PyUserSettingsUpdatePreview>()?;
    module.add_class::<PyUserSettingsCommitOutcome>()?;
    module.add_class::<PyUserSettingsFrontendTransitionOutcome>()?;
    module.add_class::<PyLegacyTuiStateImportOutcome>()?;
    module.add_class::<PyLegacyTuiStateImportReceipt>()?;
    module.add_class::<PyLegacyTuiStateImportRestoreOutcome>()?;
    module.add_class::<PyUserSettingsSchemaVersion>()?;
    module.add_class::<PyUserSettingsMigrationEndpoint>()?;
    module.add_class::<PyUserSettingsMigrationChange>()?;
    module.add_class::<PyUserSettingsMigrationDiagnostic>()?;
    module.add_class::<PyUserSettingsMigrationPlan>()?;
    module.add_class::<PyUserSettingsMigrationApplyOutcome>()?;
    module.add_class::<PyUserSettingsMigrationReceipt>()?;
    module.add_class::<PyUserSettingsMigrationRestoreOutcome>()?;
    module.add_class::<PyUserSettingsMigrationPlanningOutcome>()?;
    module.add_class::<PyUserSettingsSnapshot>()?;
    module.add(
        "UserSettingsCommitError",
        module.py().get_type::<UserSettingsCommitError>(),
    )?;
    module.add(
        "UserSettingsMigrationError",
        module.py().get_type::<UserSettingsMigrationError>(),
    )?;
    module.add(
        "LegacyTuiStateImportError",
        module.py().get_type::<LegacyTuiStateImportError>(),
    )?;
    module.add_function(wrap_pyfunction!(open_user_settings, module)?)?;
    module.add_function(wrap_pyfunction!(
        import_legacy_tui_state_into_user_settings,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(user_settings_published_defaults, module)?)?;
    Ok(())
}
