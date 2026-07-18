//! Deterministic explicit YAML Data loading for Python tooling callers.

use super::PyYamlData;
use classic_config_core::{
    ExplicitYamlDataLoadError as CoreExplicitYamlDataLoadError, ExplicitYamlDataRequest,
    ExplicitYamlDataRole as CoreExplicitYamlDataRole, ExplicitYamlDataSnapshot as CoreSnapshot,
    GameDataRole, YamlDataContentIdentity, load_explicit_yaml_data as core_load_explicit_yaml_data,
};
use classic_shared::without_gil_block_on;
use classic_shared_core::GameId;
use pyo3::create_exception;
use pyo3::exceptions::PyException;
use pyo3::prelude::*;
use std::path::PathBuf;

create_exception!(
    classic_config,
    ExplicitYamlDataLoadError,
    PyException,
    "Base class for deterministic explicit YAML Data load failures."
);
create_exception!(
    classic_config,
    ExplicitYamlDataUnsupportedGameError,
    ExplicitYamlDataLoadError,
    "Raised when a typed game has no registered YAML Data role."
);
create_exception!(
    classic_config,
    ExplicitYamlDataReadError,
    ExplicitYamlDataLoadError,
    "Raised when one exact caller-selected file cannot be read."
);
create_exception!(
    classic_config,
    ExplicitYamlDataInvalidUtf8Error,
    ExplicitYamlDataLoadError,
    "Raised when one exact caller-selected file is not UTF-8."
);
create_exception!(
    classic_config,
    ExplicitYamlDataParseError,
    ExplicitYamlDataLoadError,
    "Raised when one exact caller-selected file is malformed YAML."
);
create_exception!(
    classic_config,
    ExplicitYamlDataInvalidRoleDataError,
    ExplicitYamlDataLoadError,
    "Raised when parsed YAML does not satisfy its role contract."
);

/// Typed game identity accepted by deterministic explicit YAML Data loading.
#[pyclass(name = "ExplicitYamlDataGame", frozen, from_py_object)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct PyExplicitYamlDataGame {
    inner: GameId,
}

#[pymethods]
impl PyExplicitYamlDataGame {
    #[classattr]
    const FALLOUT4: Self = Self {
        inner: GameId::Fallout4,
    };

    #[classattr]
    const FALLOUT4_VR: Self = Self {
        inner: GameId::Fallout4VR,
    };

    #[classattr]
    const SKYRIM: Self = Self {
        inner: GameId::Skyrim,
    };

    #[classattr]
    const STARFIELD: Self = Self {
        inner: GameId::Starfield,
    };

    fn __str__(&self) -> &'static str {
        self.inner.as_str()
    }

    fn __repr__(&self) -> String {
        format!("ExplicitYamlDataGame.{}", self.constant_name())
    }

    fn __hash__(&self) -> u8 {
        match self.inner {
            GameId::Fallout4 => 0,
            GameId::Fallout4VR => 1,
            GameId::Skyrim => 2,
            GameId::Starfield => 3,
        }
    }

    fn __eq__(&self, other: &Self) -> bool {
        self.inner == other.inner
    }
}

impl PyExplicitYamlDataGame {
    /// Returns the shared core identity represented by this Python value.
    pub(crate) const fn into_core(self) -> GameId {
        self.inner
    }

    /// Wraps a shared core identity without accepting an untyped string.
    pub(crate) const fn from_core(inner: GameId) -> Self {
        Self { inner }
    }

    fn constant_name(&self) -> &'static str {
        match self.inner {
            GameId::Fallout4 => "FALLOUT4",
            GameId::Fallout4VR => "FALLOUT4_VR",
            GameId::Skyrim => "SKYRIM",
            GameId::Starfield => "STARFIELD",
        }
    }
}

/// Exact caller-selected paths for deterministic YAML Data loading.
#[pyclass(name = "ExplicitYamlDataPaths", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyExplicitYamlDataPaths {
    main_path: PathBuf,
    game_path: PathBuf,
    ignore_path: PathBuf,
}

#[pymethods]
impl PyExplicitYamlDataPaths {
    /// Owns the exact Main, game, and Local Ignore paths without resolving layout.
    #[new]
    fn new(main_path: PathBuf, game_path: PathBuf, ignore_path: PathBuf) -> Self {
        Self {
            main_path,
            game_path,
            ignore_path,
        }
    }

    #[getter]
    fn main_path(&self) -> PathBuf {
        self.main_path.clone()
    }

    #[getter]
    fn game_path(&self) -> PathBuf {
        self.game_path.clone()
    }

    #[getter]
    fn ignore_path(&self) -> PathBuf {
        self.ignore_path.clone()
    }
}

/// Read-only content identity derived from exact retained bytes.
#[pyclass(name = "YamlDataContentIdentity", frozen)]
pub struct PyYamlDataContentIdentity {
    sha256: String,
    byte_len: u64,
}

#[pymethods]
impl PyYamlDataContentIdentity {
    #[getter]
    fn sha256(&self) -> &str {
        &self.sha256
    }

    #[getter]
    const fn byte_len(&self) -> u64 {
        self.byte_len
    }
}

/// Immutable parsed YAML Data plus identities backed by retained file bytes.
#[pyclass(name = "ExplicitYamlDataSnapshot", frozen)]
pub struct PyExplicitYamlDataSnapshot {
    inner: CoreSnapshot,
}

#[pymethods]
impl PyExplicitYamlDataSnapshot {
    #[getter]
    fn game(&self) -> PyExplicitYamlDataGame {
        PyExplicitYamlDataGame::from_core(self.inner.game())
    }

    #[getter]
    fn game_data_role(&self) -> &'static str {
        match self.inner.game_data_role() {
            GameDataRole::Fallout4 => "Fallout4",
        }
    }

    #[getter]
    fn yaml_data(&self) -> PyYamlData {
        PyYamlData::_from_core(self.inner.yaml_data().clone())
    }

    #[getter]
    fn main_identity(&self) -> PyYamlDataContentIdentity {
        content_identity_to_py(self.inner.main_identity())
    }

    #[getter]
    fn game_identity(&self) -> PyYamlDataContentIdentity {
        content_identity_to_py(self.inner.game_identity())
    }

    #[getter]
    fn ignore_identity(&self) -> PyYamlDataContentIdentity {
        content_identity_to_py(self.inner.ignore_identity())
    }
}

/// Load exactly the caller-selected Main, game, and Local Ignore files.
///
/// The operation releases the GIL while waiting on CLASSIC's shared runtime and
/// never consults or mutates installation, cache, generation, backup, or fallback state.
#[pyfunction]
fn load_explicit_yaml_data(
    py: Python<'_>,
    paths: PyExplicitYamlDataPaths,
    game: PyExplicitYamlDataGame,
    selected_game_version: String,
) -> PyResult<PyExplicitYamlDataSnapshot> {
    let request = ExplicitYamlDataRequest {
        main_path: paths.main_path,
        game_path: paths.game_path,
        ignore_path: paths.ignore_path,
        game: game.inner,
        selected_game_version,
    };
    let inner = without_gil_block_on(py, || core_load_explicit_yaml_data(request))
        .map_err(explicit_yaml_data_error_to_py)?;
    Ok(PyExplicitYamlDataSnapshot { inner })
}

fn content_identity_to_py(identity: &YamlDataContentIdentity) -> PyYamlDataContentIdentity {
    PyYamlDataContentIdentity {
        sha256: identity.sha256_hex(),
        byte_len: identity.byte_len(),
    }
}

fn explicit_yaml_data_error_to_py(error: CoreExplicitYamlDataLoadError) -> PyErr {
    let (code, role, path) = match &error {
        CoreExplicitYamlDataLoadError::UnsupportedGame { .. } => ("unsupported_game", None, None),
        CoreExplicitYamlDataLoadError::Read { role, path, .. } => (
            "read",
            Some(*role),
            Some(path.to_string_lossy().into_owned()),
        ),
        CoreExplicitYamlDataLoadError::InvalidUtf8 { role, path, .. } => (
            "invalid_utf8",
            Some(*role),
            Some(path.to_string_lossy().into_owned()),
        ),
        CoreExplicitYamlDataLoadError::Parse { role, path, .. } => (
            "parse",
            Some(*role),
            Some(path.to_string_lossy().into_owned()),
        ),
        CoreExplicitYamlDataLoadError::InvalidRoleData { role, path, .. } => (
            "invalid_role_data",
            Some(*role),
            Some(path.to_string_lossy().into_owned()),
        ),
    };
    let message = error.to_string();
    let py_error = match error {
        CoreExplicitYamlDataLoadError::UnsupportedGame { .. } => {
            ExplicitYamlDataUnsupportedGameError::new_err(message)
        }
        CoreExplicitYamlDataLoadError::Read { .. } => ExplicitYamlDataReadError::new_err(message),
        CoreExplicitYamlDataLoadError::InvalidUtf8 { .. } => {
            ExplicitYamlDataInvalidUtf8Error::new_err(message)
        }
        CoreExplicitYamlDataLoadError::Parse { .. } => ExplicitYamlDataParseError::new_err(message),
        CoreExplicitYamlDataLoadError::InvalidRoleData { .. } => {
            ExplicitYamlDataInvalidRoleDataError::new_err(message)
        }
    };
    Python::attach(|py| {
        let value = py_error.value(py);
        value.setattr("code", code)?;
        value.setattr("yaml_role", role.map(explicit_yaml_data_role_name))?;
        value.setattr("path", path)?;
        Ok::<(), PyErr>(())
    })
    .expect("CLASSIC explicit YAML Data exceptions must accept contract attributes");
    py_error
}

fn explicit_yaml_data_role_name(role: CoreExplicitYamlDataRole) -> &'static str {
    match role {
        CoreExplicitYamlDataRole::Main => "main",
        CoreExplicitYamlDataRole::Game => "game",
        CoreExplicitYamlDataRole::LocalIgnore => "local_ignore",
    }
}

/// Registers the explicit loader types, operation, and exception hierarchy.
pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyExplicitYamlDataGame>()?;
    module.add_class::<PyExplicitYamlDataPaths>()?;
    module.add_class::<PyYamlDataContentIdentity>()?;
    module.add_class::<PyExplicitYamlDataSnapshot>()?;
    module.add_function(wrap_pyfunction!(load_explicit_yaml_data, module)?)?;
    let py = module.py();
    module.add(
        "ExplicitYamlDataLoadError",
        py.get_type::<ExplicitYamlDataLoadError>(),
    )?;
    module.add(
        "ExplicitYamlDataUnsupportedGameError",
        py.get_type::<ExplicitYamlDataUnsupportedGameError>(),
    )?;
    module.add(
        "ExplicitYamlDataReadError",
        py.get_type::<ExplicitYamlDataReadError>(),
    )?;
    module.add(
        "ExplicitYamlDataInvalidUtf8Error",
        py.get_type::<ExplicitYamlDataInvalidUtf8Error>(),
    )?;
    module.add(
        "ExplicitYamlDataParseError",
        py.get_type::<ExplicitYamlDataParseError>(),
    )?;
    module.add(
        "ExplicitYamlDataInvalidRoleDataError",
        py.get_type::<ExplicitYamlDataInvalidRoleDataError>(),
    )?;
    Ok(())
}
