//! Installed YAML Data inspection and immutable loading for Node and Bun callers.

use crate::config::YamlData;
use crate::explicit_yaml_data::{JsYamlDataContentIdentity, content_identity_to_js};
use crate::shared::{JsGameId, core_to_js_game_id, js_to_core_game_id};
use classic_config_core::{
    GameDataRole, InspectedYamlDataFile as CoreInspectedYamlDataFile,
    InstalledYamlDataDiagnostic as CoreInstalledYamlDataDiagnostic,
    InstalledYamlDataDiagnosticKind as CoreInstalledYamlDataDiagnosticKind,
    InstalledYamlDataInspection as CoreInstalledYamlDataInspection,
    InstalledYamlDataInspectionError as CoreInstalledYamlDataInspectionError,
    InstalledYamlDataInspectionRequest as CoreInstalledYamlDataInspectionRequest,
    InstalledYamlDataLoadError as CoreInstalledYamlDataLoadError,
    InstalledYamlDataLoadOutcome as CoreInstalledYamlDataLoadOutcome,
    InstalledYamlDataLoadRequest as CoreInstalledYamlDataLoadRequest,
    InstalledYamlDataProvenance as CoreInstalledYamlDataProvenance,
    InstalledYamlDataRole as CoreInstalledYamlDataRole,
    InstalledYamlDataSnapshot as CoreInstalledYamlDataSnapshot,
    LocalIgnoreRecoveryPlan as CoreLocalIgnoreRecoveryPlan,
    LocalIgnoreResetConflict as CoreLocalIgnoreResetConflict,
    LocalIgnoreResetError as CoreLocalIgnoreResetError,
    LocalIgnoreResetOutcome as CoreLocalIgnoreResetOutcome,
    LocalIgnoreResetPublicationStage as CoreLocalIgnoreResetPublicationStage,
    LocalIgnoreResetResult as CoreLocalIgnoreResetResult,
    LocalIgnoreYamlDataState as CoreLocalIgnoreYamlDataState,
    inspect_installed_yaml_data as core_inspect_installed_yaml_data,
    load_installed_yaml_data as core_load_installed_yaml_data,
};
use napi::bindgen_prelude::*;
use std::path::PathBuf;

/// One installation root and typed game identity to inspect.
#[napi(object)]
pub struct JsInstalledYamlDataInspectionRequest {
    /// CLASSIC installation root containing `CLASSIC Data/databases`.
    pub installation_root: String,
    /// Typed game identity used to select the registered game data role.
    pub game: JsGameId,
}

/// One installation root, typed game, and Version Registry selection mode to load.
#[napi(object)]
pub struct JsInstalledYamlDataLoadRequest {
    /// CLASSIC installation root containing `CLASSIC Data`.
    pub installation_root: String,
    /// Typed game identity used to select the registered game data role.
    pub game: JsGameId,
    /// Existing game-version mode used for Version Registry metadata selection.
    pub selected_game_version: String,
}

/// Update-eligible Installed YAML Data role.
#[napi(string_enum)]
pub enum JsInstalledYamlDataRole {
    /// Global Main YAML Data.
    Main,
    /// Selected-game YAML Data.
    Game,
}

/// Candidate that supplied one selected Installed YAML Data file.
#[napi(string_enum)]
pub enum JsInstalledYamlDataProvenance {
    /// Canonical per-user updated candidate.
    Updated,
    /// Previous updated sibling selected because the canonical file was absent.
    Previous,
    /// Install-tree bundled candidate.
    Bundled,
}

/// Stable category for an Installed YAML Data diagnostic.
#[napi(string_enum)]
pub enum JsInstalledYamlDataDiagnosticKind {
    /// The per-user update cache could not be resolved.
    CacheUnavailable,
    /// A required final fallback candidate was absent.
    Missing,
    /// A present candidate could not be read.
    Read,
    /// Candidate bytes were not valid UTF-8.
    InvalidUtf8,
    /// Candidate text was not valid YAML Data.
    Parse,
    /// A candidate omitted or malformed its schema version.
    InvalidSchema,
    /// A candidate schema was outside the client-owned compatibility range.
    IncompatibleSchema,
    /// A candidate failed role-specific semantic validation.
    InvalidRoleData,
    /// Missing Local Ignore YAML Data was generated from selected Main defaults.
    LocalIgnoreGenerated,
    /// Malformed Local Ignore YAML Data was reset from retained selected-Main defaults.
    LocalIgnoreReset,
}

/// Registered game-data role selected for Installed YAML Data.
#[napi(string_enum)]
pub enum JsInstalledYamlDataGameRole {
    /// Shared Fallout 4 data used for flat-screen and VR identities.
    Fallout4,
}

/// Expected Installed YAML Data loading outcome.
#[napi(string_enum)]
pub enum JsInstalledYamlDataLoadStatus {
    /// Main, game, and valid Local Ignore data are ready for use.
    Ready,
    /// Existing Local Ignore data is malformed and requires an explicit caller decision.
    #[napi(value = "localIgnoreRecoveryRequired")]
    LocalIgnoreRecoveryRequired,
}

/// How Local Ignore YAML Data entered an installed snapshot.
#[napi(string_enum)]
pub enum JsLocalIgnoreYamlDataState {
    /// A valid user-owned Local Ignore file already existed.
    Existing,
    /// Missing Local Ignore YAML Data was generated from selected Main defaults.
    Generated,
    /// The current operation explicitly proceeded with no Local Ignore entries.
    ProceedWithoutIgnore,
    /// Malformed Local Ignore YAML Data was reset from retained selected-Main defaults.
    ResetToDefault,
}

/// Expected outcome of resetting malformed Local Ignore YAML Data.
#[napi(string_enum)]
pub enum JsLocalIgnoreResetStatus {
    /// The retained malformed bytes were backed up and defaults became authoritative.
    Reset,
    /// The canonical file changed after the recovery plan was created.
    Conflict,
}

/// Durable publication boundary attributed by a Local Ignore reset failure.
#[napi(string_enum)]
pub enum JsLocalIgnoreResetPublicationStage {
    /// A same-directory staging file could not be created.
    Create,
    /// Complete bytes could not be written to the staging file.
    Write,
    /// Buffered staging bytes could not be flushed.
    Flush,
    /// Staging bytes could not be synchronized to durable storage.
    Sync,
    /// The fully synchronized staging file could not be atomically published.
    Publish,
}

/// Identity mismatch that prevented a Local Ignore reset from overwriting newer state.
#[napi(object, object_from_js = false)]
pub struct JsLocalIgnoreResetConflict {
    /// Malformed-file identity against which the caller approved reset.
    pub expected_identity: JsYamlDataContentIdentity,
    /// Current canonical identity, absent when the file was removed.
    pub actual_identity: Option<JsYamlDataContentIdentity>,
    /// Verified backup retained before a late conflict, when one was published.
    pub backup_path: Option<String>,
}

/// Successful durable Local Ignore reset and its retained Installed YAML Data snapshot.
#[napi(object, object_from_js = false)]
pub struct JsLocalIgnoreResetResult {
    /// Reset-ready snapshot built from the retained Main, game, and default bytes.
    pub snapshot: InstalledYamlDataSnapshot,
    /// Canonical Local Ignore path that was reset.
    pub local_ignore_path: String,
    /// Durable byte-exact backup path verified before replacement.
    pub backup_path: String,
    /// Identity observed when the recovery plan retained the malformed bytes.
    pub malformed_local_ignore_identity: JsYamlDataContentIdentity,
    /// Identity independently verified from the durable backup bytes.
    pub backup_identity: JsYamlDataContentIdentity,
    /// Identity of retained selected-Main defaults published as the replacement.
    pub replacement_identity: JsYamlDataContentIdentity,
    /// Selection, malformed-file, and successful-reset diagnostics.
    pub diagnostics: Vec<JsInstalledYamlDataDiagnostic>,
}

/// Typed Local Ignore reset outcome with exactly one status-selected payload.
#[napi(object, object_from_js = false)]
pub struct JsLocalIgnoreResetOutcome {
    /// Stable expected-outcome discriminator.
    pub status: JsLocalIgnoreResetStatus,
    /// Successful reset metadata and snapshot, populated only for `reset`.
    pub reset: Option<JsLocalIgnoreResetResult>,
    /// Conflict identities, populated only for `conflict`.
    pub conflict: Option<JsLocalIgnoreResetConflict>,
}

/// Structured attribution for one selection, rejection, or local generation event.
#[napi(object)]
pub struct JsInstalledYamlDataDiagnostic {
    /// Affected update-eligible role, absent for installation-wide or Local Ignore events.
    pub role: Option<JsInstalledYamlDataRole>,
    /// Rejected candidate provenance, absent when no update-eligible candidate applies.
    pub candidate: Option<JsInstalledYamlDataProvenance>,
    /// Affected path when the diagnostic is path-attributable.
    pub path: Option<String>,
    /// Stable machine-readable diagnostic category.
    pub kind: JsInstalledYamlDataDiagnosticKind,
    /// Actionable human-readable explanation.
    pub message: String,
}

/// Selected facts for one update-eligible Installed YAML Data file.
#[napi(object)]
pub struct JsInspectedYamlDataFile {
    /// Whether this is Main or selected-game YAML Data.
    pub role: JsInstalledYamlDataRole,
    /// Candidate that supplied the selected exact bytes.
    pub provenance: JsInstalledYamlDataProvenance,
    /// Breaking-change component of the selected schema version.
    pub schema_major: u32,
    /// Additive-change component of the selected schema version.
    pub schema_minor: u32,
    /// Lowercase hexadecimal SHA-256 digest of the selected exact bytes.
    pub sha256: String,
    /// Length of the selected exact bytes.
    pub byte_length: i64,
}

/// Selected Main/game Installed YAML Data facts and fallback diagnostics.
#[napi(object)]
pub struct JsInstalledYamlDataInspection {
    /// Typed game identity requested by the caller.
    pub game: JsGameId,
    /// Registered data role used for the selected game file.
    pub game_data_role: JsInstalledYamlDataGameRole,
    /// Independently selected Main YAML Data facts.
    pub main: JsInspectedYamlDataFile,
    /// Independently selected game YAML Data facts.
    pub game_file: JsInspectedYamlDataFile,
    /// Structured fallback and cache-resolution diagnostics.
    pub diagnostics: Vec<JsInstalledYamlDataDiagnostic>,
}

/// Immutable Installed YAML Data snapshot backed by exact core-owned bytes.
#[napi]
pub struct InstalledYamlDataSnapshot {
    inner: CoreInstalledYamlDataSnapshot,
}

#[napi]
impl InstalledYamlDataSnapshot {
    /// Returns the typed game identity requested by the caller.
    #[napi(getter)]
    pub fn game(&self) -> JsGameId {
        core_to_js_game_id(&self.inner.game())
    }

    /// Returns the registered game-data role used by the snapshot.
    #[napi(getter)]
    pub fn game_data_role(&self) -> JsInstalledYamlDataGameRole {
        game_role_to_js(self.inner.game_data_role())
    }

    /// Returns a cloned immutable view of the parsed YAML Data.
    #[napi(getter)]
    pub fn yaml_data(&self) -> YamlData {
        YamlData::from_core(self.inner.yaml_data().clone())
    }

    /// Returns the Main-derived simplify removal list retained by this immutable snapshot.
    #[napi(getter)]
    pub fn simplify_remove_list(&self) -> Vec<String> {
        self.inner.simplify_remove_list().to_vec()
    }

    /// Returns metadata for the independently selected Main YAML Data.
    #[napi(getter)]
    pub fn main(&self) -> JsInspectedYamlDataFile {
        inspected_file_to_js(self.inner.main())
    }

    /// Returns metadata for the independently selected game YAML Data.
    #[napi(getter)]
    pub fn game_file(&self) -> JsInspectedYamlDataFile {
        inspected_file_to_js(self.inner.game_file())
    }

    /// Returns how Local Ignore YAML Data entered this snapshot.
    #[napi(getter)]
    pub fn local_ignore_state(&self) -> JsLocalIgnoreYamlDataState {
        local_ignore_state_to_js(self.inner.local_ignore_state())
    }

    /// Returns the SHA-256 identity and byte length of exact Local Ignore bytes.
    #[napi(getter)]
    pub fn local_ignore_identity(&self) -> JsYamlDataContentIdentity {
        content_identity_to_js(self.inner.local_ignore_identity())
    }

    /// Returns structured fallback, cache-resolution, and generation diagnostics.
    #[napi(getter)]
    pub fn diagnostics(&self) -> Vec<JsInstalledYamlDataDiagnostic> {
        self.inner
            .diagnostics()
            .iter()
            .map(diagnostic_to_js)
            .collect()
    }
}

/// Opaque single-use recovery proposal for malformed existing Local Ignore YAML Data.
#[napi]
pub struct LocalIgnoreRecoveryPlan {
    inner: Option<CoreLocalIgnoreRecoveryPlan>,
}

#[napi]
impl LocalIgnoreRecoveryPlan {
    /// Returns the typed game retained by the already selected snapshot.
    #[napi(getter)]
    pub fn game(&self) -> Result<JsGameId> {
        Ok(core_to_js_game_id(&self.inner()?.game()))
    }

    /// Returns the registered game-data role retained by the already selected snapshot.
    #[napi(getter)]
    pub fn game_data_role(&self) -> Result<JsInstalledYamlDataGameRole> {
        Ok(game_role_to_js(self.inner()?.game_data_role()))
    }

    /// Returns metadata for the retained independently selected Main YAML Data.
    #[napi(getter)]
    pub fn main(&self) -> Result<JsInspectedYamlDataFile> {
        Ok(inspected_file_to_js(self.inner()?.main()))
    }

    /// Returns metadata for the retained independently selected game YAML Data.
    #[napi(getter)]
    pub fn game_file(&self) -> Result<JsInspectedYamlDataFile> {
        Ok(inspected_file_to_js(self.inner()?.game_file()))
    }

    /// Returns the canonical malformed Local Ignore path observed by this plan.
    #[napi(getter)]
    pub fn local_ignore_path(&self) -> Result<String> {
        Ok(self
            .inner()?
            .local_ignore_path()
            .to_string_lossy()
            .into_owned())
    }

    /// Returns the identity of the exact malformed Local Ignore bytes observed by this plan.
    #[napi(getter)]
    pub fn malformed_local_ignore_identity(&self) -> Result<JsYamlDataContentIdentity> {
        Ok(content_identity_to_js(
            self.inner()?.malformed_local_ignore_identity(),
        ))
    }

    /// Returns the identity of validated selected-Main defaults, or `null` when unavailable.
    ///
    /// Missing or invalid defaults do not block `proceedWithoutIgnore`; `resetToDefault` instead
    /// rejects with `defaults_unavailable` because replacement requires validated defaults.
    #[napi(getter)]
    pub fn default_local_ignore_identity(&self) -> Result<Option<JsYamlDataContentIdentity>> {
        Ok(self
            .inner()?
            .default_local_ignore_identity()
            .map(content_identity_to_js))
    }

    /// Returns the Version Registry selection mode retained for the interrupted operation.
    #[napi(getter)]
    pub fn selected_game_version(&self) -> Result<String> {
        Ok(self.inner()?.selected_game_version().to_string())
    }

    /// Returns retained selection and malformed Local Ignore diagnostics.
    #[napi(getter)]
    pub fn diagnostics(&self) -> Result<Vec<JsInstalledYamlDataDiagnostic>> {
        Ok(self
            .inner()?
            .diagnostics()
            .iter()
            .map(diagnostic_to_js)
            .collect())
    }

    /// Completes the retained operation with no Local Ignore entries and no filesystem writes.
    ///
    /// This decision consumes the plan. Reusing the same JavaScript plan rejects with the stable
    /// `local_ignore_recovery_plan_consumed` error code instead of re-running the operation.
    #[napi]
    pub fn proceed_without_ignore(&mut self, env: Env) -> Result<InstalledYamlDataSnapshot> {
        let plan = self.inner.take().ok_or_else(|| {
            base_inspection_error(
                env,
                "local_ignore_recovery_plan_consumed",
                "Local Ignore recovery plan has already been consumed".to_string(),
            )
        })?;
        Ok(InstalledYamlDataSnapshot {
            inner: plan.proceed_without_ignore(),
        })
    }

    /// Durably backs up malformed bytes and resets Local Ignore from retained defaults.
    ///
    /// This decision consumes the plan before scheduling work. Blocking core reset runs on the
    /// N-API worker pool as one non-interruptible atomic critical section; typed conflicts resolve
    /// as data, while operational failures reject with stable `code`, `yamlRole`, `path`, optional
    /// `stage`, and human-readable `reason` metadata.
    ///
    /// Reusing the JavaScript plan throws `local_ignore_recovery_plan_consumed` without scheduling
    /// another reset.
    #[napi(ts_return_type = "Promise<JsLocalIgnoreResetOutcome>")]
    pub fn reset_to_default(&mut self, env: Env) -> Result<AsyncTask<LocalIgnoreResetTask>> {
        let plan = self.inner.take().ok_or_else(|| {
            base_inspection_error(
                env,
                "local_ignore_recovery_plan_consumed",
                "Local Ignore recovery plan has already been consumed".to_string(),
            )
        })?;
        Ok(AsyncTask::new(LocalIgnoreResetTask { plan: Some(plan) }))
    }
}

impl LocalIgnoreRecoveryPlan {
    /// Returns the retained core plan or a stable error after the plan has been consumed.
    fn inner(&self) -> Result<&CoreLocalIgnoreRecoveryPlan> {
        self.inner.as_ref().ok_or_else(|| {
            napi::Error::new(
                Status::GenericFailure,
                "Local Ignore recovery plan has already been consumed",
            )
        })
    }
}

/// Background task that keeps the synchronous Local Ignore reset off the JavaScript thread.
pub struct LocalIgnoreResetTask {
    plan: Option<CoreLocalIgnoreRecoveryPlan>,
}

/// Core reset outcome retained until JavaScript-thread resolution.
pub enum LocalIgnoreResetTaskOutput {
    /// Typed reset or conflict outcome from config core.
    Success(Box<CoreLocalIgnoreResetOutcome>),
    /// Stage-attributed operational failure awaiting JavaScript error projection.
    Failure(CoreLocalIgnoreResetError),
}

impl Task for LocalIgnoreResetTask {
    type Output = LocalIgnoreResetTaskOutput;
    type JsValue = JsLocalIgnoreResetOutcome;

    /// Executes the consuming synchronous core reset on N-API's worker pool.
    fn compute(&mut self) -> Result<Self::Output> {
        let plan = self
            .plan
            .take()
            .ok_or_else(|| napi::Error::from_reason("Local Ignore reset task already ran"))?;
        Ok(match plan.reset_to_default() {
            Ok(outcome) => LocalIgnoreResetTaskOutput::Success(Box::new(outcome)),
            Err(error) => LocalIgnoreResetTaskOutput::Failure(error),
        })
    }

    /// Resolves expected outcomes as tagged data and rejects operational failures with metadata.
    fn resolve(&mut self, env: Env, output: Self::Output) -> Result<Self::JsValue> {
        match output {
            LocalIgnoreResetTaskOutput::Success(outcome) => {
                Ok(local_ignore_reset_outcome_to_js(*outcome))
            }
            LocalIgnoreResetTaskOutput::Failure(error) => {
                Err(local_ignore_reset_error_to_napi(env, error))
            }
        }
    }
}

/// Typed Installed YAML Data loading outcome with one status-selected payload.
#[napi(object, object_from_js = false)]
pub struct JsInstalledYamlDataLoadOutcome {
    /// Stable expected-outcome discriminator.
    pub status: JsInstalledYamlDataLoadStatus,
    /// Immutable snapshot populated only for the Ready outcome.
    pub snapshot: Option<InstalledYamlDataSnapshot>,
    /// Opaque plan populated only when Local Ignore recovery is required.
    pub recovery_plan: Option<LocalIgnoreRecoveryPlan>,
}

/// Inspect update-eligible Main and game YAML Data for one CLASSIC installation.
///
/// Inspection reads candidate files without creating the cache, promoting
/// `.prev`, or reading, creating, or repairing Local Ignore YAML Data.
///
/// @param request - Explicit installation root and typed game identity.
/// @throws an error with stable `code`, optional `yamlRole`, and structured
/// `diagnostics` metadata when both required roles cannot be selected.
#[napi(ts_return_type = "Promise<JsInstalledYamlDataInspection>")]
pub fn inspect_installed_yaml_data(
    request: JsInstalledYamlDataInspectionRequest,
) -> AsyncTask<InstalledYamlDataInspectionTask> {
    AsyncTask::new(InstalledYamlDataInspectionTask {
        request: Some(CoreInstalledYamlDataInspectionRequest {
            installation_root: PathBuf::from(request.installation_root),
            game: js_to_core_game_id(&request.game),
        }),
    })
}

/// Load one immutable Installed YAML Data outcome with Ready or recovery-required content.
///
/// Config core owns selection, compatibility, parsing, and filesystem policy. This adapter
/// performs only request/result projection and runs blocking file I/O on N-API's worker pool.
/// Malformed existing Local Ignore data resolves a recovery plan instead of rejecting.
///
/// @param request - Installation root, typed game identity, and game-version mode.
/// @throws an error with stable `code` plus role, path, or diagnostics metadata when applicable.
#[napi(ts_return_type = "Promise<JsInstalledYamlDataLoadOutcome>")]
pub fn load_installed_yaml_data(
    request: JsInstalledYamlDataLoadRequest,
) -> AsyncTask<InstalledYamlDataLoadTask> {
    AsyncTask::new(InstalledYamlDataLoadTask {
        request: Some(CoreInstalledYamlDataLoadRequest {
            installation_root: PathBuf::from(request.installation_root),
            game: js_to_core_game_id(&request.game),
            selected_game_version: request.selected_game_version,
        }),
    })
}

/// Background task that keeps installed snapshot loading off the JavaScript thread.
pub struct InstalledYamlDataLoadTask {
    request: Option<CoreInstalledYamlDataLoadRequest>,
}

/// Core load result retained until JavaScript-thread resolution.
pub enum InstalledYamlDataLoadTaskOutput {
    /// Successfully loaded a typed core outcome.
    Success(Box<CoreInstalledYamlDataLoadOutcome>),
    /// Typed core failure awaiting JavaScript error projection.
    Failure(CoreInstalledYamlDataLoadError),
}

impl Task for InstalledYamlDataLoadTask {
    type Output = InstalledYamlDataLoadTaskOutput;
    type JsValue = JsInstalledYamlDataLoadOutcome;

    /// Executes synchronous core loading on N-API's worker pool.
    fn compute(&mut self) -> Result<Self::Output> {
        let request = self
            .request
            .take()
            .ok_or_else(|| napi::Error::from_reason("Installed YAML Data load task already ran"))?;
        Ok(match core_load_installed_yaml_data(request) {
            Ok(outcome) => InstalledYamlDataLoadTaskOutput::Success(Box::new(outcome)),
            Err(error) => InstalledYamlDataLoadTaskOutput::Failure(error),
        })
    }

    /// Resolves a status-discriminated snapshot or recovery plan, or rejects a fatal error.
    fn resolve(&mut self, env: Env, output: Self::Output) -> Result<Self::JsValue> {
        match output {
            InstalledYamlDataLoadTaskOutput::Success(outcome) => match *outcome {
                CoreInstalledYamlDataLoadOutcome::Ready(snapshot) => {
                    Ok(JsInstalledYamlDataLoadOutcome {
                        status: JsInstalledYamlDataLoadStatus::Ready,
                        snapshot: Some(InstalledYamlDataSnapshot { inner: snapshot }),
                        recovery_plan: None,
                    })
                }
                CoreInstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(plan) => {
                    Ok(JsInstalledYamlDataLoadOutcome {
                        status: JsInstalledYamlDataLoadStatus::LocalIgnoreRecoveryRequired,
                        snapshot: None,
                        recovery_plan: Some(LocalIgnoreRecoveryPlan { inner: Some(plan) }),
                    })
                }
            },
            InstalledYamlDataLoadTaskOutput::Failure(error) => Err(load_error_to_napi(env, error)),
        }
    }
}

/// Background task that keeps installed-file I/O off the JavaScript thread.
pub struct InstalledYamlDataInspectionTask {
    request: Option<CoreInstalledYamlDataInspectionRequest>,
}

/// Core result retained until JavaScript-thread resolution.
pub enum InstalledYamlDataInspectionTaskOutput {
    /// Successfully inspected both required roles.
    Success(Box<CoreInstalledYamlDataInspection>),
    /// Typed core failure awaiting JavaScript error projection.
    Failure(CoreInstalledYamlDataInspectionError),
}

impl Task for InstalledYamlDataInspectionTask {
    type Output = InstalledYamlDataInspectionTaskOutput;
    type JsValue = JsInstalledYamlDataInspection;

    /// Executes synchronous filesystem inspection on N-API's worker pool.
    fn compute(&mut self) -> Result<Self::Output> {
        let request = self.request.take().ok_or_else(|| {
            napi::Error::from_reason("Installed YAML Data inspection task already ran")
        })?;
        Ok(match core_inspect_installed_yaml_data(request) {
            Ok(inspection) => InstalledYamlDataInspectionTaskOutput::Success(Box::new(inspection)),
            Err(error) => InstalledYamlDataInspectionTaskOutput::Failure(error),
        })
    }

    /// Resolves typed inspection data or rejects with stable error metadata.
    fn resolve(&mut self, env: Env, output: Self::Output) -> Result<Self::JsValue> {
        match output {
            InstalledYamlDataInspectionTaskOutput::Success(inspection) => {
                Ok(inspection_to_js(&inspection))
            }
            InstalledYamlDataInspectionTaskOutput::Failure(error) => {
                Err(inspection_error_to_napi(env, error))
            }
        }
    }
}

fn inspection_to_js(inspection: &CoreInstalledYamlDataInspection) -> JsInstalledYamlDataInspection {
    JsInstalledYamlDataInspection {
        game: core_to_js_game_id(&inspection.game()),
        game_data_role: game_role_to_js(inspection.game_data_role()),
        main: inspected_file_to_js(inspection.main()),
        game_file: inspected_file_to_js(inspection.game_file()),
        diagnostics: inspection
            .diagnostics()
            .iter()
            .map(diagnostic_to_js)
            .collect(),
    }
}

/// Project selected file metadata without exposing the snapshot's retained bytes.
pub(crate) fn inspected_file_to_js(file: &CoreInspectedYamlDataFile) -> JsInspectedYamlDataFile {
    let schema = file.schema_version();
    JsInspectedYamlDataFile {
        role: role_to_js(file.role()),
        provenance: provenance_to_js(file.provenance()),
        schema_major: schema.major,
        schema_minor: schema.minor,
        sha256: file.identity().sha256_hex(),
        byte_length: file.identity().byte_len() as i64,
    }
}

/// Project one structured diagnostic without parsing its human-readable message.
pub(crate) fn diagnostic_to_js(
    diagnostic: &CoreInstalledYamlDataDiagnostic,
) -> JsInstalledYamlDataDiagnostic {
    JsInstalledYamlDataDiagnostic {
        role: diagnostic.role().map(role_to_js),
        candidate: diagnostic.candidate().map(provenance_to_js),
        path: diagnostic
            .path()
            .map(|path| path.to_string_lossy().into_owned()),
        kind: diagnostic_kind_to_js(diagnostic.kind()),
        message: diagnostic.message().to_string(),
    }
}

/// Project the core's reset and conflict variants into one stable tagged JavaScript shape.
fn local_ignore_reset_outcome_to_js(
    outcome: CoreLocalIgnoreResetOutcome,
) -> JsLocalIgnoreResetOutcome {
    match outcome {
        CoreLocalIgnoreResetOutcome::Reset(result) => JsLocalIgnoreResetOutcome {
            status: JsLocalIgnoreResetStatus::Reset,
            reset: Some(local_ignore_reset_result_to_js(result)),
            conflict: None,
        },
        CoreLocalIgnoreResetOutcome::Conflict(conflict) => JsLocalIgnoreResetOutcome {
            status: JsLocalIgnoreResetStatus::Conflict,
            reset: None,
            conflict: Some(local_ignore_reset_conflict_to_js(&conflict)),
        },
    }
}

/// Project a successful reset without exposing or rereading any private retained core bytes.
fn local_ignore_reset_result_to_js(result: CoreLocalIgnoreResetResult) -> JsLocalIgnoreResetResult {
    let local_ignore_path = result.local_ignore_path().to_string_lossy().into_owned();
    let backup_path = result.backup_path().to_string_lossy().into_owned();
    let malformed_local_ignore_identity =
        content_identity_to_js(result.malformed_local_ignore_identity());
    let backup_identity = content_identity_to_js(result.backup_identity());
    let replacement_identity = content_identity_to_js(result.replacement_identity());
    let diagnostics = result.diagnostics().iter().map(diagnostic_to_js).collect();
    JsLocalIgnoreResetResult {
        snapshot: InstalledYamlDataSnapshot {
            inner: result.into_snapshot(),
        },
        local_ignore_path,
        backup_path,
        malformed_local_ignore_identity,
        backup_identity,
        replacement_identity,
        diagnostics,
    }
}

/// Project conflict identities and the optional already-verified late-conflict backup path.
fn local_ignore_reset_conflict_to_js(
    conflict: &CoreLocalIgnoreResetConflict,
) -> JsLocalIgnoreResetConflict {
    JsLocalIgnoreResetConflict {
        expected_identity: content_identity_to_js(conflict.expected_identity()),
        actual_identity: conflict.actual_identity().map(content_identity_to_js),
        backup_path: conflict
            .backup_path()
            .map(|path| path.to_string_lossy().into_owned()),
    }
}

const fn role_to_js(role: CoreInstalledYamlDataRole) -> JsInstalledYamlDataRole {
    match role {
        CoreInstalledYamlDataRole::Main => JsInstalledYamlDataRole::Main,
        CoreInstalledYamlDataRole::Game => JsInstalledYamlDataRole::Game,
    }
}

const fn provenance_to_js(
    provenance: CoreInstalledYamlDataProvenance,
) -> JsInstalledYamlDataProvenance {
    match provenance {
        CoreInstalledYamlDataProvenance::Updated => JsInstalledYamlDataProvenance::Updated,
        CoreInstalledYamlDataProvenance::Previous => JsInstalledYamlDataProvenance::Previous,
        CoreInstalledYamlDataProvenance::Bundled => JsInstalledYamlDataProvenance::Bundled,
    }
}

const fn diagnostic_kind_to_js(
    kind: CoreInstalledYamlDataDiagnosticKind,
) -> JsInstalledYamlDataDiagnosticKind {
    match kind {
        CoreInstalledYamlDataDiagnosticKind::CacheUnavailable => {
            JsInstalledYamlDataDiagnosticKind::CacheUnavailable
        }
        CoreInstalledYamlDataDiagnosticKind::Missing => JsInstalledYamlDataDiagnosticKind::Missing,
        CoreInstalledYamlDataDiagnosticKind::Read => JsInstalledYamlDataDiagnosticKind::Read,
        CoreInstalledYamlDataDiagnosticKind::InvalidUtf8 => {
            JsInstalledYamlDataDiagnosticKind::InvalidUtf8
        }
        CoreInstalledYamlDataDiagnosticKind::Parse => JsInstalledYamlDataDiagnosticKind::Parse,
        CoreInstalledYamlDataDiagnosticKind::InvalidSchema => {
            JsInstalledYamlDataDiagnosticKind::InvalidSchema
        }
        CoreInstalledYamlDataDiagnosticKind::IncompatibleSchema => {
            JsInstalledYamlDataDiagnosticKind::IncompatibleSchema
        }
        CoreInstalledYamlDataDiagnosticKind::InvalidRoleData => {
            JsInstalledYamlDataDiagnosticKind::InvalidRoleData
        }
        CoreInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated => {
            JsInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated
        }
        CoreInstalledYamlDataDiagnosticKind::LocalIgnoreReset => {
            JsInstalledYamlDataDiagnosticKind::LocalIgnoreReset
        }
    }
}

/// Project the core Local Ignore origin without recreating recovery policy.
pub(crate) const fn local_ignore_state_to_js(
    state: CoreLocalIgnoreYamlDataState,
) -> JsLocalIgnoreYamlDataState {
    match state {
        CoreLocalIgnoreYamlDataState::Existing => JsLocalIgnoreYamlDataState::Existing,
        CoreLocalIgnoreYamlDataState::Generated => JsLocalIgnoreYamlDataState::Generated,
        CoreLocalIgnoreYamlDataState::ProceedWithoutIgnore => {
            JsLocalIgnoreYamlDataState::ProceedWithoutIgnore
        }
        CoreLocalIgnoreYamlDataState::ResetToDefault => JsLocalIgnoreYamlDataState::ResetToDefault,
    }
}

const fn reset_publication_stage_to_js(
    stage: CoreLocalIgnoreResetPublicationStage,
) -> JsLocalIgnoreResetPublicationStage {
    match stage {
        CoreLocalIgnoreResetPublicationStage::Create => JsLocalIgnoreResetPublicationStage::Create,
        CoreLocalIgnoreResetPublicationStage::Write => JsLocalIgnoreResetPublicationStage::Write,
        CoreLocalIgnoreResetPublicationStage::Flush => JsLocalIgnoreResetPublicationStage::Flush,
        CoreLocalIgnoreResetPublicationStage::Sync => JsLocalIgnoreResetPublicationStage::Sync,
        CoreLocalIgnoreResetPublicationStage::Publish => {
            JsLocalIgnoreResetPublicationStage::Publish
        }
    }
}

const fn game_role_to_js(role: GameDataRole) -> JsInstalledYamlDataGameRole {
    match role {
        GameDataRole::Fallout4 => JsInstalledYamlDataGameRole::Fallout4,
    }
}

/// Project a typed core terminal failure into a JavaScript `Error` with contract metadata.
///
/// Unsupported games carry only `code`; exhausted selection also carries `yamlRole` and
/// structured diagnostics so callers never need to parse the human-readable message.
fn inspection_error_to_napi(env: Env, error: CoreInstalledYamlDataInspectionError) -> napi::Error {
    let (code, role, diagnostics) = match &error {
        CoreInstalledYamlDataInspectionError::UnsupportedGame { .. } => {
            ("unsupported_game", None, Vec::new())
        }
        CoreInstalledYamlDataInspectionError::NoUsableSource { role, diagnostics } => (
            "no_usable_source",
            Some(*role),
            diagnostics.iter().map(diagnostic_to_js).collect(),
        ),
    };
    installed_yaml_data_error(
        env,
        code,
        error.to_string(),
        InstalledYamlDataErrorMetadata {
            role: role.map(role_name),
            diagnostics,
            ..InstalledYamlDataErrorMetadata::default()
        },
    )
}

/// Project every fatal Installed YAML Data load error into stable JavaScript metadata.
fn load_error_to_napi(env: Env, error: CoreInstalledYamlDataLoadError) -> napi::Error {
    let (code, role, path, diagnostics) = match &error {
        CoreInstalledYamlDataLoadError::UnsupportedGame { .. } => {
            ("unsupported_game", None, None, Vec::new())
        }
        CoreInstalledYamlDataLoadError::NoUsableSource { role, diagnostics } => (
            "no_usable_source",
            Some(role_name(*role)),
            None,
            diagnostics.iter().map(diagnostic_to_js).collect(),
        ),
        CoreInstalledYamlDataLoadError::LocalIgnoreRead { path, .. } => (
            "local_ignore_read",
            Some("local_ignore"),
            Some(path.clone()),
            Vec::new(),
        ),
        CoreInstalledYamlDataLoadError::LocalIgnoreDefaultInvalid { path, .. } => (
            "local_ignore_default_invalid",
            Some("local_ignore"),
            Some(path.clone()),
            Vec::new(),
        ),
        CoreInstalledYamlDataLoadError::LocalIgnoreCreate { path, .. } => (
            "local_ignore_create",
            Some("local_ignore"),
            Some(path.clone()),
            Vec::new(),
        ),
        CoreInstalledYamlDataLoadError::InvalidSelectedData { .. } => {
            ("invalid_selected_data", None, None, Vec::new())
        }
    };
    installed_yaml_data_error(
        env,
        code,
        error.to_string(),
        InstalledYamlDataErrorMetadata {
            role,
            path,
            diagnostics,
            ..InstalledYamlDataErrorMetadata::default()
        },
    )
}

/// Project every Local Ignore reset failure into stable JavaScript operation metadata.
fn local_ignore_reset_error_to_napi(env: Env, error: CoreLocalIgnoreResetError) -> napi::Error {
    let (code, path, stage, reason) = match &error {
        CoreLocalIgnoreResetError::DefaultsUnavailable { path, reason } => {
            ("defaults_unavailable", path.clone(), None, reason.clone())
        }
        CoreLocalIgnoreResetError::Lock { path, source } => {
            ("lock", path.clone(), None, source.to_string())
        }
        CoreLocalIgnoreResetError::Read { path, source } => {
            ("read", path.clone(), None, source.to_string())
        }
        CoreLocalIgnoreResetError::BackupDirectory { path, source } => {
            ("backup_directory", path.clone(), None, source.to_string())
        }
        CoreLocalIgnoreResetError::BackupPublication {
            path,
            stage,
            source,
        } => (
            "backup_publication",
            path.clone(),
            Some(*stage),
            source.to_string(),
        ),
        CoreLocalIgnoreResetError::BackupVerification { path, reason } => {
            ("backup_verification", path.clone(), None, reason.clone())
        }
        CoreLocalIgnoreResetError::ReplacementPublication {
            path,
            stage,
            source,
        } => (
            "replacement_publication",
            path.clone(),
            Some(*stage),
            source.to_string(),
        ),
    };
    installed_yaml_data_error(
        env,
        code,
        error.to_string(),
        InstalledYamlDataErrorMetadata {
            role: Some("local_ignore"),
            path: Some(path),
            stage,
            reason: Some(reason),
            ..InstalledYamlDataErrorMetadata::default()
        },
    )
}

/// Optional JavaScript metadata shared by Installed YAML Data operation failures.
#[derive(Default)]
struct InstalledYamlDataErrorMetadata {
    role: Option<&'static str>,
    path: Option<PathBuf>,
    diagnostics: Vec<JsInstalledYamlDataDiagnostic>,
    stage: Option<CoreLocalIgnoreResetPublicationStage>,
    reason: Option<String>,
}

/// Build one JavaScript `Error` with only the metadata applicable to its core variant.
fn installed_yaml_data_error(
    env: Env,
    code: &str,
    message: String,
    metadata: InstalledYamlDataErrorMetadata,
) -> napi::Error {
    let InstalledYamlDataErrorMetadata {
        role,
        path,
        diagnostics,
        stage,
        reason,
    } = metadata;
    let raw_error = JsError::from(napi::Error::new(code, message.clone())).into_unknown(env);
    let Ok(mut object) = raw_error.coerce_to_object() else {
        return base_inspection_error(env, code, message);
    };
    if let Some(role) = role
        && object.set_named_property("yamlRole", role).is_err()
    {
        return base_inspection_error(env, code, message);
    }
    if let Some(path) = path
        && object
            .set_named_property("path", path.to_string_lossy().into_owned())
            .is_err()
    {
        return base_inspection_error(env, code, message);
    }
    if !diagnostics.is_empty()
        && object
            .set_named_property("diagnostics", diagnostics)
            .is_err()
    {
        return base_inspection_error(env, code, message);
    }
    if let Some(stage) = stage
        && object
            .set_named_property("stage", reset_publication_stage_to_js(stage))
            .is_err()
    {
        return base_inspection_error(env, code, message);
    }
    if let Some(reason) = reason
        && object.set_named_property("reason", reason).is_err()
    {
        return base_inspection_error(env, code, message);
    }
    object
        .into_unknown(&env)
        .map(napi::Error::from)
        .unwrap_or_else(|_| base_inspection_error(env, code, message))
}

const fn role_name(role: CoreInstalledYamlDataRole) -> &'static str {
    match role {
        CoreInstalledYamlDataRole::Main => "main",
        CoreInstalledYamlDataRole::Game => "game",
    }
}

fn base_inspection_error(env: Env, code: &str, message: String) -> napi::Error {
    napi::Error::from(JsError::from(napi::Error::new(code, message)).into_unknown(env))
}
