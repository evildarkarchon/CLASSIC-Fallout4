//! Thin PyO3 adapter for read-only User Settings and non-persisting update previews.

use classic_user_settings_core::{
    CommitEligibility, CrashLogScanSettings, DocumentClassification, PreferenceOrigin, Revision,
    SourceLocation, UserSettings, UserSettingsUpdate, UserSettingsUpdateField,
    UserSettingsUpdatePreview,
};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
use std::collections::HashMap;

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

/// Update-related User Settings consumed by update-check policy.
#[pyclass(name = "UpdatePreferences", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyUpdatePreferences {
    /// Whether first-party update checks are enabled after safe fallback policy.
    #[pyo3(get)]
    update_check: bool,
    /// Provenance token: `document`, `default`, or `degraded_fallback`.
    #[pyo3(get)]
    origin: String,
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

    /// Requests one canonical game-version selection token.
    fn set_game_version_selection(&mut self, value: String) {
        self.inner = std::mem::take(&mut self.inner).with_game_version_selection(value);
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
}

/// Opens User Settings relative to an explicit CLASSIC root without changing
/// either supported source document.
#[pyfunction]
pub fn open_user_settings(classic_root: String) -> PyUserSettingsSnapshot {
    let settings = UserSettings::open(classic_root);
    let (schema_major, schema_minor) = settings
        .schema_version()
        .map_or((None, None), |(major, minor)| (Some(major), Some(minor)));

    PyUserSettingsSnapshot {
        update_preferences: PyUpdatePreferences {
            update_check: settings.update_preferences().update_check(),
            origin: preference_origin_token(settings.update_preferences().update_check_origin())
                .to_string(),
        },
        crash_log_scan_settings: crash_log_scan_settings_to_py(settings.crash_log_scan_settings()),
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
        },
    }
}

/// Converts one accepted core field while preserving its typed requested value.
fn update_field_to_py(field: &UserSettingsUpdateField) -> PyUserSettingsUpdateField {
    let value = match field {
        UserSettingsUpdateField::UpdateCheck(value)
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
        UserSettingsUpdateField::FormIdDatabases(value) => PyUserSettingsUpdateValue::StringLists(
            value
                .iter()
                .map(|(game, paths)| (game.clone(), paths.clone()))
                .collect(),
        ),
        UserSettingsUpdateField::UnsolvedLogsDestination(value)
        | UserSettingsUpdateField::CustomScanInput(value) => {
            PyUserSettingsUpdateValue::OptionalString(value.clone())
        }
        UserSettingsUpdateField::MaxConcurrentScans(value) => {
            PyUserSettingsUpdateValue::UnsignedInteger(*value)
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

/// Python module for typed, read-only User Settings access.
#[pymodule]
fn classic_user_settings(module: &Bound<'_, PyModule>) -> PyResult<()> {
    classic_shared::configure_python_stdio(module.py());
    module.add("__version__", env!("CARGO_PKG_VERSION"))?;
    module.add_class::<PyUserSettingsDiagnostic>()?;
    module.add_class::<PyUpdatePreferences>()?;
    module.add_class::<PyCrashLogScanSettings>()?;
    module.add_class::<PyUserSettingsUpdate>()?;
    module.add_class::<PyUserSettingsUpdateDiagnostic>()?;
    module.add_class::<PyUserSettingsUpdateField>()?;
    module.add_class::<PyUserSettingsUpdatePreview>()?;
    module.add_class::<PyUserSettingsSnapshot>()?;
    module.add_function(wrap_pyfunction!(open_user_settings, module)?)?;
    Ok(())
}
