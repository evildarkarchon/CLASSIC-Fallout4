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
    InstalledYamlDataSnapshot as CoreSnapshot, LocalIgnoreRecoveryPlan as CoreRecoveryPlan,
    LocalIgnoreResetError as CoreResetError, LocalIgnoreResetOutcome as CoreResetOutcome,
    LocalIgnoreResetPublicationStage as CoreResetPublicationStage,
    LocalIgnoreYamlDataState as CoreLocalIgnoreState,
    YamlDataContentIdentity as CoreYamlDataContentIdentity,
    inspect_installed_yaml_data as core_inspect_installed_yaml_data,
    load_installed_yaml_data as core_load_installed_yaml_data,
};
use classic_shared::without_gil;
use pyo3::create_exception;
use pyo3::exceptions::{PyException, PyRuntimeError};
use pyo3::prelude::*;
use std::path::PathBuf;

const LOCAL_IGNORE_RECOVERY_PLAN_CONSUMED: &str =
    "Local Ignore recovery plan has already been consumed";

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
create_exception!(
    classic_config,
    LocalIgnoreResetError,
    PyException,
    "Base class for operational Local Ignore reset failures."
);
create_exception!(
    classic_config,
    LocalIgnoreResetDefaultsUnavailableError,
    LocalIgnoreResetError,
    "Raised when the recovery plan retained no usable selected-Main defaults."
);
create_exception!(
    classic_config,
    LocalIgnoreResetLockError,
    LocalIgnoreResetError,
    "Raised when the Local Ignore reset lock cannot be acquired."
);
create_exception!(
    classic_config,
    LocalIgnoreResetReadError,
    LocalIgnoreResetError,
    "Raised when authoritative Local Ignore bytes cannot be read during reset."
);
create_exception!(
    classic_config,
    LocalIgnoreResetBackupDirectoryError,
    LocalIgnoreResetError,
    "Raised when the config-owned Local Ignore backup directory cannot be prepared."
);
create_exception!(
    classic_config,
    LocalIgnoreResetBackupPublicationError,
    LocalIgnoreResetError,
    "Raised when the byte-exact Local Ignore backup cannot be durably published."
);
create_exception!(
    classic_config,
    LocalIgnoreResetBackupVerificationError,
    LocalIgnoreResetError,
    "Raised when the published Local Ignore backup cannot be verified byte-for-byte."
);
create_exception!(
    classic_config,
    LocalIgnoreResetReplacementPublicationError,
    LocalIgnoreResetError,
    "Raised when retained defaults cannot be atomically published as Local Ignore."
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

/// Opaque, consumable recovery plan retained by Rust core.
#[pyclass(name = "LocalIgnoreRecoveryPlan", skip_from_py_object)]
pub struct PyLocalIgnoreRecoveryPlan {
    inner: Option<CoreRecoveryPlan>,
}

/// Typed Ready outcome containing one immutable Installed YAML Data snapshot.
#[pyclass(name = "InstalledYamlDataLoadOutcome", frozen, skip_from_py_object)]
pub struct PyInstalledYamlDataLoadOutcome {
    snapshot: Py<PyInstalledYamlDataSnapshot>,
}

/// Typed recovery-required outcome containing one opaque Local Ignore plan.
#[pyclass(
    name = "InstalledYamlDataLocalIgnoreRecoveryRequiredOutcome",
    frozen,
    skip_from_py_object
)]
pub struct PyInstalledYamlDataLocalIgnoreRecoveryRequiredOutcome {
    recovery_plan: Py<PyLocalIgnoreRecoveryPlan>,
}

/// Typed successful reset outcome with durable publication metadata and retained snapshot.
#[pyclass(name = "LocalIgnoreResetOutcome", frozen, skip_from_py_object)]
pub struct PyLocalIgnoreResetOutcome {
    snapshot: Py<PyInstalledYamlDataSnapshot>,
    local_ignore_path: PathBuf,
    backup_path: PathBuf,
    malformed_local_ignore_identity: CoreYamlDataContentIdentity,
    backup_identity: CoreYamlDataContentIdentity,
    replacement_identity: CoreYamlDataContentIdentity,
    diagnostics: Vec<PyInstalledYamlDataDiagnostic>,
}

/// Typed conflict outcome returned when the approved malformed file changed or disappeared.
#[pyclass(name = "LocalIgnoreResetConflictOutcome", frozen, skip_from_py_object)]
pub struct PyLocalIgnoreResetConflictOutcome {
    expected_identity: CoreYamlDataContentIdentity,
    actual_identity: Option<CoreYamlDataContentIdentity>,
    backup_path: Option<PathBuf>,
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
impl PyInstalledYamlDataLocalIgnoreRecoveryRequiredOutcome {
    /// Return the stable expected-outcome discriminator.
    #[getter]
    fn status(&self) -> &'static str {
        "local_ignore_recovery_required"
    }

    /// Return the opaque recovery plan owned by this outcome.
    #[getter]
    fn recovery_plan(&self, py: Python<'_>) -> Py<PyLocalIgnoreRecoveryPlan> {
        self.recovery_plan.clone_ref(py)
    }
}

#[pymethods]
impl PyLocalIgnoreResetOutcome {
    /// Return the stable successful-reset discriminator.
    #[getter]
    fn status(&self) -> &'static str {
        "reset"
    }

    /// Return the immutable reset-ready snapshot retained from the recovery plan.
    #[getter]
    fn snapshot(&self, py: Python<'_>) -> Py<PyInstalledYamlDataSnapshot> {
        self.snapshot.clone_ref(py)
    }

    /// Return the canonical Local Ignore path that became authoritative.
    #[getter]
    fn local_ignore_path(&self) -> PathBuf {
        self.local_ignore_path.clone()
    }

    /// Return the durable byte-exact backup path verified before replacement.
    #[getter]
    fn backup_path(&self) -> PathBuf {
        self.backup_path.clone()
    }

    /// Return the malformed-file identity retained when recovery became necessary.
    #[getter]
    fn malformed_local_ignore_identity(&self) -> PyYamlDataContentIdentity {
        content_identity_to_py(&self.malformed_local_ignore_identity)
    }

    /// Return the identity independently verified from the durable backup bytes.
    #[getter]
    fn backup_identity(&self) -> PyYamlDataContentIdentity {
        content_identity_to_py(&self.backup_identity)
    }

    /// Return the identity of retained defaults published as the replacement.
    #[getter]
    fn replacement_identity(&self) -> PyYamlDataContentIdentity {
        content_identity_to_py(&self.replacement_identity)
    }

    /// Return retained selection, malformed-file, and successful-reset diagnostics.
    #[getter]
    fn diagnostics(&self) -> Vec<PyInstalledYamlDataDiagnostic> {
        self.diagnostics.clone()
    }
}

#[pymethods]
impl PyLocalIgnoreResetConflictOutcome {
    /// Return the stable conflict discriminator.
    #[getter]
    fn status(&self) -> &'static str {
        "conflict"
    }

    /// Return the malformed-file identity against which reset was approved.
    #[getter]
    fn expected_identity(&self) -> PyYamlDataContentIdentity {
        content_identity_to_py(&self.expected_identity)
    }

    /// Return the current canonical identity, or `None` when the file disappeared.
    #[getter]
    fn actual_identity(&self) -> Option<PyYamlDataContentIdentity> {
        self.actual_identity.as_ref().map(content_identity_to_py)
    }

    /// Return the verified backup retained before a late conflict, when one was published.
    #[getter]
    fn backup_path(&self) -> Option<PathBuf> {
        self.backup_path.clone()
    }
}

impl PyLocalIgnoreRecoveryPlan {
    /// Borrows the Rust-owned plan or reports that its one decision was already consumed.
    fn retained(&self) -> PyResult<&CoreRecoveryPlan> {
        self.inner
            .as_ref()
            .ok_or_else(|| PyRuntimeError::new_err(LOCAL_IGNORE_RECOVERY_PLAN_CONSUMED))
    }
}

#[pymethods]
impl PyLocalIgnoreRecoveryPlan {
    /// Return the typed game retained by the already selected snapshot.
    ///
    /// # Errors
    ///
    /// Raises `RuntimeError` when this plan was already consumed.
    #[getter]
    fn game(&self) -> PyResult<PyExplicitYamlDataGame> {
        Ok(PyExplicitYamlDataGame::from_core(self.retained()?.game()))
    }

    /// Return the registered data role retained by the selected game file.
    ///
    /// # Errors
    ///
    /// Raises `RuntimeError` when this plan was already consumed.
    #[getter]
    fn game_data_role(&self) -> PyResult<&'static str> {
        Ok(match self.retained()?.game_data_role() {
            classic_config_core::GameDataRole::Fallout4 => "Fallout4",
        })
    }

    /// Return retained selected Main provenance, schema, and exact-byte identity.
    ///
    /// # Errors
    ///
    /// Raises `RuntimeError` when this plan was already consumed.
    #[getter]
    fn main(&self) -> PyResult<PyInspectedYamlDataFile> {
        Ok(inspected_file_to_py(self.retained()?.main()))
    }

    /// Return retained selected game provenance, schema, and exact-byte identity.
    ///
    /// # Errors
    ///
    /// Raises `RuntimeError` when this plan was already consumed.
    #[getter]
    fn game_file(&self) -> PyResult<PyInspectedYamlDataFile> {
        Ok(inspected_file_to_py(self.retained()?.game_file()))
    }

    /// Return the canonical malformed Local Ignore path observed by this plan.
    ///
    /// # Errors
    ///
    /// Raises `RuntimeError` when this plan was already consumed.
    #[getter]
    fn local_ignore_path(&self) -> PyResult<PathBuf> {
        Ok(self.retained()?.local_ignore_path().to_path_buf())
    }

    /// Return the identity of the exact malformed Local Ignore bytes.
    ///
    /// # Errors
    ///
    /// Raises `RuntimeError` when this plan was already consumed.
    #[getter]
    fn malformed_local_ignore_identity(&self) -> PyResult<PyYamlDataContentIdentity> {
        Ok(content_identity_to_py(
            self.retained()?.malformed_local_ignore_identity(),
        ))
    }

    /// Return the identity of validated selected-Main defaults, or `None` when unavailable.
    ///
    /// Missing or invalid defaults do not block proceeding because malformed installed Local
    /// Ignore bytes are never replaced during this recovery operation.
    ///
    /// # Errors
    ///
    /// Raises `RuntimeError` when this plan was already consumed.
    #[getter]
    fn default_local_ignore_identity(&self) -> PyResult<Option<PyYamlDataContentIdentity>> {
        Ok(self
            .retained()?
            .default_local_ignore_identity()
            .map(content_identity_to_py))
    }

    /// Return the retained game-version mode for the interrupted operation.
    ///
    /// # Errors
    ///
    /// Raises `RuntimeError` when this plan was already consumed.
    #[getter]
    fn selected_game_version(&self) -> PyResult<String> {
        Ok(self.retained()?.selected_game_version().to_string())
    }

    /// Return retained selection and malformed Local Ignore diagnostics.
    ///
    /// # Errors
    ///
    /// Raises `RuntimeError` when this plan was already consumed.
    #[getter]
    fn diagnostics(&self) -> PyResult<Vec<PyInstalledYamlDataDiagnostic>> {
        Ok(self
            .retained()?
            .diagnostics()
            .iter()
            .map(diagnostic_to_py)
            .collect())
    }

    /// Complete this retained operation with an empty, operation-scoped ignore list.
    ///
    /// The plan can be consumed only once. Proceeding performs no filesystem access or writes;
    /// a later installed load encounters the unchanged malformed file again.
    ///
    /// # Errors
    ///
    /// Raises `RuntimeError` when this plan was already consumed.
    fn proceed_without_ignore(&mut self) -> PyResult<PyInstalledYamlDataSnapshot> {
        let plan = self
            .inner
            .take()
            .ok_or_else(|| PyRuntimeError::new_err(LOCAL_IGNORE_RECOVERY_PLAN_CONSUMED))?;
        Ok(PyInstalledYamlDataSnapshot {
            inner: plan.proceed_without_ignore(),
        })
    }

    /// Consume this plan to durably back up malformed bytes and publish retained defaults.
    ///
    /// The synchronous core reset runs without the GIL and is non-interruptible after entry.
    /// It returns a typed successful-reset or conflict outcome and never reselects Main, game,
    /// or default bytes. Any attempt, including an operational failure, consumes the plan.
    ///
    /// # Errors
    ///
    /// Raises `RuntimeError` when this plan was already consumed. Raises a typed
    /// `LocalIgnoreResetError` subclass when the accepted reset cannot complete safely.
    fn reset_to_default(&mut self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let plan = self
            .inner
            .take()
            .ok_or_else(|| PyRuntimeError::new_err(LOCAL_IGNORE_RECOVERY_PLAN_CONSUMED))?;
        let outcome = without_gil(py, move || plan.reset_to_default())
            .map_err(local_ignore_reset_error_to_py)?;

        match outcome {
            CoreResetOutcome::Reset(result) => {
                let local_ignore_path = result.local_ignore_path().to_path_buf();
                let backup_path = result.backup_path().to_path_buf();
                let malformed_local_ignore_identity =
                    result.malformed_local_ignore_identity().clone();
                let backup_identity = result.backup_identity().clone();
                let replacement_identity = result.replacement_identity().clone();
                let diagnostics = result.diagnostics().iter().map(diagnostic_to_py).collect();
                let snapshot = Py::new(
                    py,
                    PyInstalledYamlDataSnapshot {
                        inner: result.into_snapshot(),
                    },
                )?;
                Ok(Py::new(
                    py,
                    PyLocalIgnoreResetOutcome {
                        snapshot,
                        local_ignore_path,
                        backup_path,
                        malformed_local_ignore_identity,
                        backup_identity,
                        replacement_identity,
                        diagnostics,
                    },
                )?
                .into_any())
            }
            CoreResetOutcome::Conflict(conflict) => Ok(Py::new(
                py,
                PyLocalIgnoreResetConflictOutcome {
                    expected_identity: conflict.expected_identity().clone(),
                    actual_identity: conflict.actual_identity().cloned(),
                    backup_path: conflict.backup_path().map(PathBuf::from),
                },
            )?
            .into_any()),
        }
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

    /// Return the validated simplify-log removal list retained from selected Main bytes.
    #[getter]
    fn simplify_remove_list(&self) -> Vec<String> {
        self.inner.simplify_remove_list().to_vec()
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
            CoreLocalIgnoreState::ProceedWithoutIgnore => "proceed_without_ignore",
            CoreLocalIgnoreState::ResetToDefault => "reset_to_default",
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

/// Load one immutable Installed YAML Data snapshot or retained recovery proposal.
///
/// The operation releases the GIL while Rust core independently selects Main and game,
/// preserves existing Local Ignore or atomically generates it when missing, and builds the
/// parsed view. Malformed existing Local Ignore returns an expected recovery-required outcome;
/// it is never replaced during ordinary loading.
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
) -> PyResult<Py<PyAny>> {
    let request = InstalledYamlDataLoadRequest {
        installation_root,
        game: game.into_core(),
        selected_game_version,
    };
    let outcome = without_gil(py, || core_load_installed_yaml_data(request))
        .map_err(installed_yaml_data_load_error_to_py)?;
    match outcome {
        CoreLoadOutcome::Ready(inner) => {
            let snapshot = Py::new(py, PyInstalledYamlDataSnapshot { inner })?;
            Ok(Py::new(py, PyInstalledYamlDataLoadOutcome { snapshot })?.into_any())
        }
        CoreLoadOutcome::LocalIgnoreRecoveryRequired(inner) => {
            let recovery_plan = Py::new(py, PyLocalIgnoreRecoveryPlan { inner: Some(inner) })?;
            Ok(Py::new(
                py,
                PyInstalledYamlDataLocalIgnoreRecoveryRequiredOutcome { recovery_plan },
            )?
            .into_any())
        }
    }
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

/// Convert every operational reset failure into its typed Python subclass and metadata.
fn local_ignore_reset_error_to_py(error: CoreResetError) -> PyErr {
    let message = error.to_string();
    let (code, path, stage, reason, py_error) = match error {
        CoreResetError::DefaultsUnavailable { path, reason } => (
            "defaults_unavailable",
            path,
            None,
            reason,
            LocalIgnoreResetDefaultsUnavailableError::new_err(message),
        ),
        CoreResetError::Lock { path, source } => (
            "lock",
            path,
            None,
            source.to_string(),
            LocalIgnoreResetLockError::new_err(message),
        ),
        CoreResetError::Read { path, source } => (
            "read",
            path,
            None,
            source.to_string(),
            LocalIgnoreResetReadError::new_err(message),
        ),
        CoreResetError::BackupDirectory { path, source } => (
            "backup_directory",
            path,
            None,
            source.to_string(),
            LocalIgnoreResetBackupDirectoryError::new_err(message),
        ),
        CoreResetError::BackupPublication {
            path,
            stage,
            source,
        } => (
            "backup_publication",
            path,
            Some(reset_publication_stage_token(stage)),
            source.to_string(),
            LocalIgnoreResetBackupPublicationError::new_err(message),
        ),
        CoreResetError::BackupVerification { path, reason } => (
            "backup_verification",
            path,
            None,
            reason,
            LocalIgnoreResetBackupVerificationError::new_err(message),
        ),
        CoreResetError::ReplacementPublication {
            path,
            stage,
            source,
        } => (
            "replacement_publication",
            path,
            Some(reset_publication_stage_token(stage)),
            source.to_string(),
            LocalIgnoreResetReplacementPublicationError::new_err(message),
        ),
    };
    Python::attach(|py| {
        let value = py_error.value(py);
        value.setattr("code", code)?;
        value.setattr("path", path.to_string_lossy().into_owned())?;
        value.setattr("stage", stage)?;
        value.setattr("reason", reason)?;
        Ok::<(), PyErr>(())
    })
    .expect("CLASSIC Local Ignore reset exceptions must accept contract attributes");
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

/// Returns the stable Python token for one durable reset publication boundary.
const fn reset_publication_stage_token(stage: CoreResetPublicationStage) -> &'static str {
    match stage {
        CoreResetPublicationStage::Create => "create",
        CoreResetPublicationStage::Write => "write",
        CoreResetPublicationStage::Flush => "flush",
        CoreResetPublicationStage::Sync => "sync",
        CoreResetPublicationStage::Publish => "publish",
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
        CoreInstalledYamlDataDiagnosticKind::LocalIgnoreReset => "local_ignore_reset",
    }
}

/// Registers Installed YAML Data DTOs, inspection operation, and exception hierarchy.
pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyInstalledYamlDataDiagnostic>()?;
    module.add_class::<PyInspectedYamlDataFile>()?;
    module.add_class::<PyInstalledYamlDataInspection>()?;
    module.add_class::<PyInstalledYamlDataSnapshot>()?;
    module.add_class::<PyLocalIgnoreRecoveryPlan>()?;
    module.add_class::<PyInstalledYamlDataLoadOutcome>()?;
    module.add_class::<PyInstalledYamlDataLocalIgnoreRecoveryRequiredOutcome>()?;
    module.add_class::<PyLocalIgnoreResetOutcome>()?;
    module.add_class::<PyLocalIgnoreResetConflictOutcome>()?;
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
    module.add(
        "LocalIgnoreResetError",
        py.get_type::<LocalIgnoreResetError>(),
    )?;
    module.add(
        "LocalIgnoreResetDefaultsUnavailableError",
        py.get_type::<LocalIgnoreResetDefaultsUnavailableError>(),
    )?;
    module.add(
        "LocalIgnoreResetLockError",
        py.get_type::<LocalIgnoreResetLockError>(),
    )?;
    module.add(
        "LocalIgnoreResetReadError",
        py.get_type::<LocalIgnoreResetReadError>(),
    )?;
    module.add(
        "LocalIgnoreResetBackupDirectoryError",
        py.get_type::<LocalIgnoreResetBackupDirectoryError>(),
    )?;
    module.add(
        "LocalIgnoreResetBackupPublicationError",
        py.get_type::<LocalIgnoreResetBackupPublicationError>(),
    )?;
    module.add(
        "LocalIgnoreResetBackupVerificationError",
        py.get_type::<LocalIgnoreResetBackupVerificationError>(),
    )?;
    module.add(
        "LocalIgnoreResetReplacementPublicationError",
        py.get_type::<LocalIgnoreResetReplacementPublicationError>(),
    )?;
    Ok(())
}
