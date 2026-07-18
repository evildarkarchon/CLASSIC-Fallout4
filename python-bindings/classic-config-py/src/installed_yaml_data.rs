//! Side-effect-limited Installed YAML Data inspection for Python callers.

use super::explicit_yaml_data::PyExplicitYamlDataGame;
use classic_config_core::{
    InspectedYamlDataFile as CoreInspectedYamlDataFile,
    InstalledYamlDataDiagnostic as CoreInstalledYamlDataDiagnostic,
    InstalledYamlDataDiagnosticKind as CoreInstalledYamlDataDiagnosticKind,
    InstalledYamlDataInspectionError as CoreInstalledYamlDataInspectionError,
    InstalledYamlDataInspectionRequest, InstalledYamlDataProvenance as CoreProvenance,
    InstalledYamlDataRole as CoreRole,
    inspect_installed_yaml_data as core_inspect_installed_yaml_data,
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

/// One structured cache-resolution or candidate-rejection diagnostic.
#[pyclass(name = "InstalledYamlDataDiagnostic", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyInstalledYamlDataDiagnostic {
    /// Affected role token, or `None` for an installation-wide diagnostic.
    #[pyo3(get)]
    role: Option<String>,
    /// Candidate token, or `None` when no candidate path was available.
    #[pyo3(get)]
    candidate: Option<String>,
    /// Candidate path when the diagnostic is path-attributable.
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
    }
}

/// Registers Installed YAML Data DTOs, inspection operation, and exception hierarchy.
pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyInstalledYamlDataDiagnostic>()?;
    module.add_class::<PyInspectedYamlDataFile>()?;
    module.add_class::<PyInstalledYamlDataInspection>()?;
    module.add_function(wrap_pyfunction!(inspect_installed_yaml_data, module)?)?;
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
    Ok(())
}
