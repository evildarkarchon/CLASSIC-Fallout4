//! Installed YAML Data inspection and immutable loading for Python callers.

use super::PyYamlData;
use super::explicit_yaml_data::{
    PyExplicitYamlDataGame, PyYamlDataContentIdentity, content_identity_to_py,
};
use classic_config_core::{
    InspectedYamlDataFile as CoreInspectedYamlDataFile,
    InstalledYamlDataDiagnostic as CoreInstalledYamlDataDiagnostic,
    InstalledYamlDataDiagnosticKind as CoreInstalledYamlDataDiagnosticKind,
    InstalledYamlDataInspectionError as CoreInstalledYamlDataInspectionError,
    InstalledYamlDataInspectionRequest, InstalledYamlDataLoadError as CoreLoadError,
    InstalledYamlDataLoadOutcome as CoreLoadOutcome, InstalledYamlDataLoadRequest,
    InstalledYamlDataProvenance as CoreProvenance, InstalledYamlDataRole as CoreRole,
    InstalledYamlDataSnapshot as CoreSnapshot, LocalIgnoreYamlDataState as CoreLocalIgnoreState,
    inspect_installed_yaml_data as core_inspect_installed_yaml_data,
    load_installed_yaml_data as core_load_installed_yaml_data,
};
use classic_shared::without_gil;
use pyo3::create_exception;
use pyo3::exceptions::PyException;
use pyo3::prelude::*;
use std::path::PathBuf;

create_exception!(
    classic_config,
    InstalledYamlDataInspectionError,
    PyException,
    "Base class for Installed YAML Data inspection failures."
);
create_exception!(
    classic_config,
    InstalledYamlDataUnsupportedGameError,
    InstalledYamlDataInspectionError,
    "Raised when a typed game has no registered Installed YAML Data role."
);
create_exception!(
    classic_config,
    InstalledYamlDataNoUsableSourceError,
    InstalledYamlDataInspectionError,
    "Raised when neither updated nor bundled data is usable for a required role."
);
create_exception!(
    classic_config,
    InstalledYamlDataLoadError,
    PyException,
    "Base class for fatal Installed YAML Data load failures."
);
create_exception!(
    classic_config,
    InstalledYamlDataLoadUnsupportedGameError,
    InstalledYamlDataLoadError,
    "Raised when a typed game has no registered Installed YAML Data role."
);
create_exception!(
    classic_config,
    InstalledYamlDataLoadNoUsableSourceError,
    InstalledYamlDataLoadError,
    "Raised when neither updated nor bundled data is usable for a required role."
);
create_exception!(
    classic_config,
    InstalledYamlDataLoadLocalIgnoreReadError,
    InstalledYamlDataLoadError,
    "Raised when authoritative Local Ignore YAML Data cannot be read."
);
create_exception!(
    classic_config,
    InstalledYamlDataLoadLocalIgnoreInvalidUtf8Error,
    InstalledYamlDataLoadError,
    "Raised when authoritative Local Ignore YAML Data is not UTF-8."
);
create_exception!(
    classic_config,
    InstalledYamlDataLoadLocalIgnoreParseError,
    InstalledYamlDataLoadError,
    "Raised when authoritative Local Ignore YAML Data is malformed YAML."
);
create_exception!(
    classic_config,
    InstalledYamlDataLoadLocalIgnoreInvalidRoleDataError,
    InstalledYamlDataLoadError,
    "Raised when authoritative Local Ignore YAML Data violates its role contract."
);
create_exception!(
    classic_config,
    InstalledYamlDataLoadLocalIgnoreDefaultInvalidError,
    InstalledYamlDataLoadError,
    "Raised when selected Main defaults cannot safely initialize Local Ignore YAML Data."
);
create_exception!(
    classic_config,
    InstalledYamlDataLoadLocalIgnoreCreateError,
    InstalledYamlDataLoadError,
    "Raised when missing Local Ignore YAML Data cannot be atomically created."
);
create_exception!(
    classic_config,
    InstalledYamlDataLoadInvalidSelectedDataError,
    InstalledYamlDataLoadError,
    "Raised when selected Installed YAML Data cannot form the parsed view."
);

/// One structured selection, candidate-rejection, or Local Ignore generation diagnostic.
#[pyclass(name = "InstalledYamlDataDiagnostic", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyInstalledYamlDataDiagnostic {
    /// Affected role token, or `None` when no update-eligible Main/game role applies.
    #[pyo3(get)]
    role: Option<String>,
    /// Candidate token, or `None` when no installed candidate was involved.
    #[pyo3(get)]
    candidate: Option<String>,
    /// Affected path when the diagnostic is path-attributable.
    #[pyo3(get)]
    path: Option<PathBuf>,
    /// Stable diagnostic category.
    #[pyo3(get)]
    kind: String,
    /// Actionable human-readable explanation.
    #[pyo3(get)]
    message: String,
}

/// Selected facts for one update-eligible Main or game file.
#[pyclass(name = "InspectedYamlDataFile", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyInspectedYamlDataFile {
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

/// Immutable selected Main/game facts and retained fallback diagnostics.
#[pyclass(name = "InstalledYamlDataInspection", frozen, skip_from_py_object)]
pub struct PyInstalledYamlDataInspection {
    /// Typed game identity requested by the caller.
    #[pyo3(get)]
    game: PyExplicitYamlDataGame,
    /// Registered data role used by the selected game file.
    #[pyo3(get)]
    game_data_role: String,
    /// Independently selected Main file facts.
    #[pyo3(get)]
    main: PyInspectedYamlDataFile,
    /// Independently selected game file facts.
    #[pyo3(get)]
    game_file: PyInspectedYamlDataFile,
    /// Structured cache-resolution and candidate-rejection diagnostics.
    #[pyo3(get)]
    diagnostics: Vec<PyInstalledYamlDataDiagnostic>,
}

/// Immutable Ready snapshot for one explicit installation root and game-version mode.
#[pyclass(name = "InstalledYamlDataSnapshot", frozen, skip_from_py_object)]
pub struct PyInstalledYamlDataSnapshot {
    inner: CoreSnapshot,
}

/// Typed Ready outcome containing one immutable Installed YAML Data snapshot.
#[pyclass(name = "InstalledYamlDataLoadOutcome", frozen, skip_from_py_object)]
pub struct PyInstalledYamlDataLoadOutcome {
    snapshot: Py<PyInstalledYamlDataSnapshot>,
}

#[pymethods]
impl PyInstalledYamlDataLoadOutcome {
    /// Return the stable expected-outcome discriminator.
    #[getter]
    fn status(&self) -> &'static str {
        "ready"
    }

    /// Return the immutable snapshot owned by this Ready outcome.
    #[getter]
    fn snapshot(&self, py: Python<'_>) -> Py<PyInstalledYamlDataSnapshot> {
        self.snapshot.clone_ref(py)
    }
}

#[pymethods]
impl PyInstalledYamlDataSnapshot {
    /// Return the typed game identity retained by Rust core.
    #[getter]
    fn game(&self) -> PyExplicitYamlDataGame {
        PyExplicitYamlDataGame::from_core(self.inner.game())
    }

    /// Return the registered data role used by the selected game file.
    #[getter]
    fn game_data_role(&self) -> &'static str {
        match self.inner.game_data_role() {
            classic_config_core::GameDataRole::Fallout4 => "Fallout4",
        }
    }

    /// Clone the parsed view derived from the snapshot's exact retained bytes.
    #[getter]
    fn yaml_data(&self) -> PyYamlData {
        PyYamlData::_from_core(self.inner.yaml_data().clone())
    }

    /// Return selected Main provenance, schema, and exact-byte identity.
    #[getter]
    fn main(&self) -> PyInspectedYamlDataFile {
        inspected_file_to_py(self.inner.main())
    }

    /// Return selected game provenance, schema, and exact-byte identity.
    #[getter]
    fn game_file(&self) -> PyInspectedYamlDataFile {
        inspected_file_to_py(self.inner.game_file())
    }

    /// Return how Local Ignore YAML Data entered this Ready snapshot.
    #[getter]
    fn local_ignore_state(&self) -> &'static str {
        match self.inner.local_ignore_state() {
            CoreLocalIgnoreState::Existing => "existing",
            CoreLocalIgnoreState::Generated => "generated",
        }
    }

    /// Return the identity of the exact retained Local Ignore bytes.
    #[getter]
    fn local_ignore_identity(&self) -> PyYamlDataContentIdentity {
        content_identity_to_py(self.inner.local_ignore_identity())
    }

    /// Return every structured fallback, cache-resolution, or generation diagnostic.
    #[getter]
    fn diagnostics(&self) -> Vec<PyInstalledYamlDataDiagnostic> {
        self.inner
            .diagnostics()
            .iter()
            .map(diagnostic_to_py)
            .collect()
    }
}

/// Inspects installed Main and game YAML Data without reading or modifying Local Ignore.
///
/// The operation releases the GIL while config core resolves updated and bundled
/// candidates. It does not create the cache or promote, rewrite, repair, or delete files.
/// Returns independently selected Main/game metadata plus every non-terminal diagnostic.
///
/// # Errors
///
/// Raises `InstalledYamlDataUnsupportedGameError` when `game` has no registered data role.
/// Raises `InstalledYamlDataNoUsableSourceError` when updated and bundled candidates are
/// exhausted for either required role; its `diagnostics` attribute retains the rejection trail.
#[pyfunction]
fn inspect_installed_yaml_data(
    py: Python<'_>,
    installation_root: PathBuf,
    game: PyExplicitYamlDataGame,
) -> PyResult<PyInstalledYamlDataInspection> {
    let request = InstalledYamlDataInspectionRequest {
        installation_root,
        game: game.into_core(),
    };
    let inspection = without_gil(py, || core_inspect_installed_yaml_data(request))
        .map_err(installed_yaml_data_error_to_py)?;

    Ok(PyInstalledYamlDataInspection {
        game: PyExplicitYamlDataGame::from_core(inspection.game()),
        game_data_role: match inspection.game_data_role() {
            classic_config_core::GameDataRole::Fallout4 => "Fallout4".to_string(),
        },
        main: inspected_file_to_py(inspection.main()),
        game_file: inspected_file_to_py(inspection.game_file()),
        diagnostics: inspection
            .diagnostics()
            .iter()
            .map(diagnostic_to_py)
            .collect(),
    })
}

/// Load one immutable Ready Installed YAML Data snapshot.
///
/// The operation releases the GIL while Rust core independently selects Main and game,
/// preserves existing Local Ignore or atomically generates it when missing, and builds the
/// parsed view. Existing Local Ignore is never replaced during ordinary loading.
///
/// # Errors
///
/// Raises a typed `InstalledYamlDataLoadError` subclass for every fatal core result.
#[pyfunction]
fn load_installed_yaml_data(
    py: Python<'_>,
    installation_root: PathBuf,
    game: PyExplicitYamlDataGame,
    selected_game_version: String,
) -> PyResult<PyInstalledYamlDataLoadOutcome> {
    let request = InstalledYamlDataLoadRequest {
        installation_root,
        game: game.into_core(),
        selected_game_version,
    };
    let outcome = without_gil(py, || core_load_installed_yaml_data(request))
        .map_err(installed_yaml_data_load_error_to_py)?;
    let CoreLoadOutcome::Ready(inner) = outcome;
    let snapshot = Py::new(py, PyInstalledYamlDataSnapshot { inner })?;
    Ok(PyInstalledYamlDataLoadOutcome { snapshot })
}

/// Projects one selected file without retaining an independent path or byte cache.
fn inspected_file_to_py(file: &CoreInspectedYamlDataFile) -> PyInspectedYamlDataFile {
    let schema = file.schema_version();
    PyInspectedYamlDataFile {
        role: role_token(file.role()).to_string(),
        provenance: provenance_token(file.provenance()).to_string(),
        schema_major: schema.major,
        schema_minor: schema.minor,
        sha256: file.identity().sha256_hex(),
        byte_length: file.identity().byte_len(),
    }
}

/// Projects one structured diagnostic using stable snake-case tokens.
fn diagnostic_to_py(diagnostic: &CoreInstalledYamlDataDiagnostic) -> PyInstalledYamlDataDiagnostic {
    PyInstalledYamlDataDiagnostic {
        role: diagnostic.role().map(role_token).map(str::to_string),
        candidate: diagnostic
            .candidate()
            .map(provenance_token)
            .map(str::to_string),
        path: diagnostic.path().map(PathBuf::from),
        kind: diagnostic_kind_token(diagnostic.kind()).to_string(),
        message: diagnostic.message().to_string(),
    }
}

/// Converts a core terminal failure into the typed Python hierarchy and metadata contract.
fn installed_yaml_data_error_to_py(error: CoreInstalledYamlDataInspectionError) -> PyErr {
    let message = error.to_string();
    let (code, yaml_role, diagnostics, py_error) = match error {
        CoreInstalledYamlDataInspectionError::UnsupportedGame { .. } => (
            "unsupported_game",
            None,
            Vec::new(),
            InstalledYamlDataUnsupportedGameError::new_err(message),
        ),
        CoreInstalledYamlDataInspectionError::NoUsableSource { role, diagnostics } => (
            "no_usable_source",
            Some(role_token(role)),
            diagnostics.iter().map(diagnostic_to_py).collect(),
            InstalledYamlDataNoUsableSourceError::new_err(message),
        ),
    };
    Python::attach(|py| {
        let value = py_error.value(py);
        value.setattr("code", code)?;
        value.setattr("yaml_role", yaml_role)?;
        value.setattr("diagnostics", diagnostics)?;
        Ok::<(), PyErr>(())
    })
    .expect("CLASSIC Installed YAML Data exceptions must accept contract attributes");
    py_error
}

/// Convert every fatal core load result into a stable typed Python exception.
fn installed_yaml_data_load_error_to_py(error: CoreLoadError) -> PyErr {
    let message = error.to_string();
    let (code, yaml_role, path, diagnostics, py_error) = match error {
        CoreLoadError::UnsupportedGame { .. } => (
            "unsupported_game",
            None,
            None,
            Vec::new(),
            InstalledYamlDataLoadUnsupportedGameError::new_err(message),
        ),
        CoreLoadError::NoUsableSource { role, diagnostics } => (
            "no_usable_source",
            Some(role_token(role)),
            None,
            diagnostics.iter().map(diagnostic_to_py).collect(),
            InstalledYamlDataLoadNoUsableSourceError::new_err(message),
        ),
        CoreLoadError::LocalIgnoreRead { path, .. } => (
            "local_ignore_read",
            Some("local_ignore"),
            Some(path.to_string_lossy().into_owned()),
            Vec::new(),
            InstalledYamlDataLoadLocalIgnoreReadError::new_err(message),
        ),
        CoreLoadError::LocalIgnoreInvalidUtf8 { path, .. } => (
            "local_ignore_invalid_utf8",
            Some("local_ignore"),
            Some(path.to_string_lossy().into_owned()),
            Vec::new(),
            InstalledYamlDataLoadLocalIgnoreInvalidUtf8Error::new_err(message),
        ),
        CoreLoadError::LocalIgnoreParse { path, .. } => (
            "local_ignore_parse",
            Some("local_ignore"),
            Some(path.to_string_lossy().into_owned()),
            Vec::new(),
            InstalledYamlDataLoadLocalIgnoreParseError::new_err(message),
        ),
        CoreLoadError::LocalIgnoreInvalidRoleData { path, .. } => (
            "local_ignore_invalid_role_data",
            Some("local_ignore"),
            Some(path.to_string_lossy().into_owned()),
            Vec::new(),
            InstalledYamlDataLoadLocalIgnoreInvalidRoleDataError::new_err(message),
        ),
        CoreLoadError::LocalIgnoreDefaultInvalid { path, .. } => (
            "local_ignore_default_invalid",
            Some("local_ignore"),
            Some(path.to_string_lossy().into_owned()),
            Vec::new(),
            InstalledYamlDataLoadLocalIgnoreDefaultInvalidError::new_err(message),
        ),
        CoreLoadError::LocalIgnoreCreate { path, .. } => (
            "local_ignore_create",
            Some("local_ignore"),
            Some(path.to_string_lossy().into_owned()),
            Vec::new(),
            InstalledYamlDataLoadLocalIgnoreCreateError::new_err(message),
        ),
        CoreLoadError::InvalidSelectedData { .. } => (
            "invalid_selected_data",
            None,
            None,
            Vec::new(),
            InstalledYamlDataLoadInvalidSelectedDataError::new_err(message),
        ),
    };
    Python::attach(|py| {
        let value = py_error.value(py);
        value.setattr("code", code)?;
        value.setattr("yaml_role", yaml_role)?;
        value.setattr("path", path)?;
        value.setattr("diagnostics", diagnostics)?;
        Ok::<(), PyErr>(())
    })
    .expect("CLASSIC Installed YAML Data load exceptions must accept contract attributes");
    py_error
}

/// Returns the stable Python role token.
const fn role_token(role: CoreRole) -> &'static str {
    match role {
        CoreRole::Main => "main",
        CoreRole::Game => "game",
    }
}

/// Returns the stable Python candidate-provenance token.
const fn provenance_token(provenance: CoreProvenance) -> &'static str {
    match provenance {
        CoreProvenance::Updated => "updated",
        CoreProvenance::Previous => "previous",
        CoreProvenance::Bundled => "bundled",
    }
}

/// Returns the stable Python diagnostic-kind token.
const fn diagnostic_kind_token(kind: CoreInstalledYamlDataDiagnosticKind) -> &'static str {
    match kind {
        CoreInstalledYamlDataDiagnosticKind::CacheUnavailable => "cache_unavailable",
        CoreInstalledYamlDataDiagnosticKind::Missing => "missing",
        CoreInstalledYamlDataDiagnosticKind::Read => "read",
        CoreInstalledYamlDataDiagnosticKind::InvalidUtf8 => "invalid_utf8",
        CoreInstalledYamlDataDiagnosticKind::Parse => "parse",
        CoreInstalledYamlDataDiagnosticKind::InvalidSchema => "invalid_schema",
        CoreInstalledYamlDataDiagnosticKind::IncompatibleSchema => "incompatible_schema",
        CoreInstalledYamlDataDiagnosticKind::InvalidRoleData => "invalid_role_data",
        CoreInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated => "local_ignore_generated",
    }
}

/// Registers Installed YAML Data DTOs, inspection operation, and exception hierarchy.
pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyInstalledYamlDataDiagnostic>()?;
    module.add_class::<PyInspectedYamlDataFile>()?;
    module.add_class::<PyInstalledYamlDataInspection>()?;
    module.add_class::<PyInstalledYamlDataSnapshot>()?;
    module.add_class::<PyInstalledYamlDataLoadOutcome>()?;
    module.add_function(wrap_pyfunction!(inspect_installed_yaml_data, module)?)?;
    module.add_function(wrap_pyfunction!(load_installed_yaml_data, module)?)?;
    let py = module.py();
    module.add(
        "InstalledYamlDataInspectionError",
        py.get_type::<InstalledYamlDataInspectionError>(),
    )?;
    module.add(
        "InstalledYamlDataUnsupportedGameError",
        py.get_type::<InstalledYamlDataUnsupportedGameError>(),
    )?;
    module.add(
        "InstalledYamlDataNoUsableSourceError",
        py.get_type::<InstalledYamlDataNoUsableSourceError>(),
    )?;
    module.add(
        "InstalledYamlDataLoadError",
        py.get_type::<InstalledYamlDataLoadError>(),
    )?;
    module.add(
        "InstalledYamlDataLoadUnsupportedGameError",
        py.get_type::<InstalledYamlDataLoadUnsupportedGameError>(),
    )?;
    module.add(
        "InstalledYamlDataLoadNoUsableSourceError",
        py.get_type::<InstalledYamlDataLoadNoUsableSourceError>(),
    )?;
    module.add(
        "InstalledYamlDataLoadLocalIgnoreReadError",
        py.get_type::<InstalledYamlDataLoadLocalIgnoreReadError>(),
    )?;
    module.add(
        "InstalledYamlDataLoadLocalIgnoreInvalidUtf8Error",
        py.get_type::<InstalledYamlDataLoadLocalIgnoreInvalidUtf8Error>(),
    )?;
    module.add(
        "InstalledYamlDataLoadLocalIgnoreParseError",
        py.get_type::<InstalledYamlDataLoadLocalIgnoreParseError>(),
    )?;
    module.add(
        "InstalledYamlDataLoadLocalIgnoreInvalidRoleDataError",
        py.get_type::<InstalledYamlDataLoadLocalIgnoreInvalidRoleDataError>(),
    )?;
    module.add(
        "InstalledYamlDataLoadLocalIgnoreDefaultInvalidError",
        py.get_type::<InstalledYamlDataLoadLocalIgnoreDefaultInvalidError>(),
    )?;
    module.add(
        "InstalledYamlDataLoadLocalIgnoreCreateError",
        py.get_type::<InstalledYamlDataLoadLocalIgnoreCreateError>(),
    )?;
    module.add(
        "InstalledYamlDataLoadInvalidSelectedDataError",
        py.get_type::<InstalledYamlDataLoadInvalidSelectedDataError>(),
    )?;
    Ok(())
}
