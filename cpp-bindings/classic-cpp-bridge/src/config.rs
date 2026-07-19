//! YamlDataCore configuration bridge for CXX FFI.
//!
//! Bridges `classic_config_core::YamlDataCore` which loads all CLASSIC YAML
//! configuration files (main, game, ignore) into a structured Rust type.
//! Provides bulk YAML getters plus Local-YAML path persistence helpers.
//!
//! IndexMap fields are exposed as paired key/value vectors since CXX bridges
//! are isolated and can't share opaque types across modules.

use classic_config_core::{
    InspectedYamlDataFile as CoreInspectedYamlDataFile,
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
    LocalIgnoreYamlDataState as CoreLocalIgnoreYamlDataState, MainYamlVersionError,
    ModSolutionCriteria, SuspectErrorRule as CoreSuspectErrorRule,
    SuspectStackCountRule as CoreSuspectStackCountRule, SuspectStackRule as CoreSuspectStackRule,
    YamlDataCore,
    explicit_yaml_data::{
        ExplicitYamlDataLoadError as CoreExplicitYamlDataLoadError,
        ExplicitYamlDataRequest as CoreExplicitYamlDataRequest,
        ExplicitYamlDataRole as CoreExplicitYamlDataRole,
        ExplicitYamlDataSnapshot as CoreExplicitYamlDataSnapshot, GameDataRole as CoreGameDataRole,
        YamlDataContentIdentity, load_explicit_yaml_data as core_load_explicit_yaml_data,
    },
    inspect_installed_yaml_data as core_inspect_installed_yaml_data,
    load_installed_yaml_data as core_load_installed_yaml_data,
    load_main_yaml_version_with_bundled_dir as core_load_main_yaml_version_with_bundled_dir,
    persist_game_local_paths,
};
use classic_settings_core::{
    cache_stats as settings_core_cache_stats, clear_cache as clear_settings_cache,
    reset_cache_stats as reset_settings_core_cache_stats,
};
use classic_shared_core::GameId as CoreGameId;
use classic_shared_core::get_runtime;
use std::path::{Path, PathBuf};

/// Opaque wrapper around `YamlDataCore` for CXX FFI.
pub struct YamlData {
    pub(crate) inner: YamlDataCore,
}

/// Opaque result holder for one deterministic explicit YAML Data load.
pub struct ExplicitYamlDataLoad {
    result: Result<CoreExplicitYamlDataSnapshot, CoreExplicitYamlDataLoadError>,
}

/// Opaque immutable snapshot returned by deterministic explicit YAML Data loading.
pub struct ExplicitYamlDataSnapshot {
    inner: CoreExplicitYamlDataSnapshot,
}

/// Opaque result holder for one Installed YAML Data inspection operation.
pub struct InstalledYamlDataInspectionOperation {
    result: Result<CoreInstalledYamlDataInspection, CoreInstalledYamlDataInspectionError>,
}

/// Opaque immutable result returned by Installed YAML Data inspection.
pub struct InstalledYamlDataInspection {
    inner: CoreInstalledYamlDataInspection,
}

/// Opaque result holder for one Installed YAML Data load operation.
pub struct InstalledYamlDataLoadOperation {
    result: Result<CoreInstalledYamlDataLoadOutcome, CoreInstalledYamlDataLoadError>,
}

/// Opaque immutable snapshot returned by Installed YAML Data loading.
pub struct InstalledYamlDataSnapshot {
    inner: CoreInstalledYamlDataSnapshot,
}

/// Opaque immutable recovery proposal for malformed Local Ignore YAML Data.
pub struct LocalIgnoreRecoveryPlan {
    inner: CoreLocalIgnoreRecoveryPlan,
}

// ── Construction ────────────────────────────────────────────────────

fn yaml_data_load(
    yaml_dir_root: &str,
    yaml_dir_data: &str,
    game: &str,
    game_version: &str,
) -> Result<Box<YamlData>, String> {
    let dirs = vec![PathBuf::from(yaml_dir_root), PathBuf::from(yaml_dir_data)];
    let inner = get_runtime()
        .block_on(YamlDataCore::load_from_yaml_files(
            dirs,
            game.to_string(),
            game_version.to_string(),
        ))
        .map_err(|e| format!("{e}"))?;
    Ok(Box::new(YamlData { inner }))
}

/// Load exactly the three caller-selected YAML Data files without installation policy.
///
/// The returned handle always exists so C++ callers can inspect the stable typed
/// status before consuming a successful snapshot.
fn explicit_yaml_data_load(
    paths: ffi::ExplicitYamlDataPathsDto,
    game: ffi::ExplicitYamlDataGameId,
    selected_game_version: &str,
) -> Box<ExplicitYamlDataLoad> {
    let request = CoreExplicitYamlDataRequest {
        main_path: PathBuf::from(paths.main_path),
        game_path: PathBuf::from(paths.game_path),
        ignore_path: PathBuf::from(paths.ignore_path),
        game: explicit_game_id_to_core(game),
        selected_game_version: selected_game_version.to_string(),
    };
    Box::new(ExplicitYamlDataLoad {
        result: get_runtime().block_on(core_load_explicit_yaml_data(request)),
    })
}

/// Inspect update-eligible Installed YAML Data without reading Local Ignore.
///
/// The returned operation always exists so C++ callers can inspect typed
/// unsupported-game and no-usable-source failures before consuming success.
fn installed_yaml_data_inspect(
    installation_root: &str,
    game: ffi::ExplicitYamlDataGameId,
) -> Box<InstalledYamlDataInspectionOperation> {
    installed_yaml_data_inspection_operation_from_result(core_inspect_installed_yaml_data(
        CoreInstalledYamlDataInspectionRequest {
            installation_root: PathBuf::from(installation_root),
            game: explicit_game_id_to_core(game),
        },
    ))
}

/// Build an opaque inspection operation from the Rust-owned core result.
fn installed_yaml_data_inspection_operation_from_result(
    result: Result<CoreInstalledYamlDataInspection, CoreInstalledYamlDataInspectionError>,
) -> Box<InstalledYamlDataInspectionOperation> {
    Box::new(InstalledYamlDataInspectionOperation { result })
}

/// Return the success/error status captured by an Installed YAML Data inspection.
fn installed_yaml_data_inspection_status(
    operation: &InstalledYamlDataInspectionOperation,
) -> ffi::InstalledYamlDataInspectionStatusDto {
    match &operation.result {
        Ok(_) => ffi::InstalledYamlDataInspectionStatusDto {
            has_inspection: true,
            has_error: false,
            error: empty_installed_yaml_data_inspection_error(),
        },
        Err(error) => ffi::InstalledYamlDataInspectionStatusDto {
            has_inspection: false,
            has_error: true,
            error: installed_yaml_data_inspection_error_to_dto(error),
        },
    }
}

/// Consume a successful operation and return its immutable inspection result.
///
/// Callers inspect [`installed_yaml_data_inspection_status`] first. This
/// `Result` prevents a failed operation from being consumed as success.
// CXX requires Box here to consume the C++ UniquePtr and transfer ownership.
#[allow(clippy::boxed_local)]
fn installed_yaml_data_inspection_take(
    operation: Box<InstalledYamlDataInspectionOperation>,
) -> Result<Box<InstalledYamlDataInspection>, String> {
    match operation.result {
        Ok(inner) => Ok(Box::new(InstalledYamlDataInspection { inner })),
        Err(error) => Err(error.to_string()),
    }
}

/// Return the typed game identity retained by a successful inspection.
fn installed_yaml_data_inspection_game(
    inspection: &InstalledYamlDataInspection,
) -> ffi::ExplicitYamlDataGameId {
    explicit_game_id_to_ffi(inspection.inner.game())
}

/// Return the registered game-data role selected by a successful inspection.
fn installed_yaml_data_inspection_game_role(
    inspection: &InstalledYamlDataInspection,
) -> ffi::InstalledYamlDataGameRole {
    match inspection.inner.game_data_role() {
        CoreGameDataRole::Fallout4 => ffi::InstalledYamlDataGameRole::Fallout4,
    }
}

/// Return selected Main provenance, schema, and exact-byte content identity.
fn installed_yaml_data_inspection_main(
    inspection: &InstalledYamlDataInspection,
) -> ffi::InspectedYamlDataFileDto {
    inspected_yaml_data_file_to_dto(inspection.inner.main())
}

/// Return selected game provenance, schema, and exact-byte content identity.
fn installed_yaml_data_inspection_game_file(
    inspection: &InstalledYamlDataInspection,
) -> ffi::InspectedYamlDataFileDto {
    inspected_yaml_data_file_to_dto(inspection.inner.game_file())
}

/// Return every structured fallback or cache-resolution diagnostic.
fn installed_yaml_data_inspection_diagnostics(
    inspection: &InstalledYamlDataInspection,
) -> Vec<ffi::InstalledYamlDataDiagnosticDto> {
    inspection
        .inner
        .diagnostics()
        .iter()
        .map(installed_yaml_data_diagnostic_to_dto)
        .collect()
}

/// Load Installed YAML Data from one installation root without adapter-owned policy.
///
/// The returned operation always exists so C++ callers can inspect every typed
/// core failure before consuming a ready immutable snapshot.
fn installed_yaml_data_load(
    installation_root: &str,
    game: ffi::ExplicitYamlDataGameId,
    selected_game_version: &str,
) -> Box<InstalledYamlDataLoadOperation> {
    installed_yaml_data_load_operation_from_result(core_load_installed_yaml_data(
        CoreInstalledYamlDataLoadRequest {
            installation_root: PathBuf::from(installation_root),
            game: explicit_game_id_to_core(game),
            selected_game_version: selected_game_version.to_string(),
        },
    ))
}

/// Build an opaque load operation from the Rust-owned core outcome.
fn installed_yaml_data_load_operation_from_result(
    result: Result<CoreInstalledYamlDataLoadOutcome, CoreInstalledYamlDataLoadError>,
) -> Box<InstalledYamlDataLoadOperation> {
    Box::new(InstalledYamlDataLoadOperation { result })
}

/// Return the Ready/recovery-required/error status captured by an Installed YAML Data load.
fn installed_yaml_data_load_status(
    operation: &InstalledYamlDataLoadOperation,
) -> ffi::InstalledYamlDataLoadStatusDto {
    match &operation.result {
        Ok(CoreInstalledYamlDataLoadOutcome::Ready(_)) => ffi::InstalledYamlDataLoadStatusDto {
            has_snapshot: true,
            has_recovery_plan: false,
            has_error: false,
            error: empty_installed_yaml_data_load_error(),
        },
        Ok(CoreInstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(_)) => {
            ffi::InstalledYamlDataLoadStatusDto {
                has_snapshot: false,
                has_recovery_plan: true,
                has_error: false,
                error: empty_installed_yaml_data_load_error(),
            }
        }
        Err(error) => ffi::InstalledYamlDataLoadStatusDto {
            has_snapshot: false,
            has_recovery_plan: false,
            has_error: true,
            error: installed_yaml_data_load_error_to_dto(error),
        },
    }
}

/// Consume a Ready operation and return its immutable Installed YAML Data snapshot.
///
/// Callers inspect [`installed_yaml_data_load_status`] first. This `Result`
/// prevents a failed operation from being consumed as success.
// CXX requires Box here to consume the C++ UniquePtr and transfer ownership.
#[allow(clippy::boxed_local)]
fn installed_yaml_data_load_take_snapshot(
    operation: Box<InstalledYamlDataLoadOperation>,
) -> Result<Box<InstalledYamlDataSnapshot>, String> {
    match operation.result {
        Ok(CoreInstalledYamlDataLoadOutcome::Ready(inner)) => {
            Ok(Box::new(InstalledYamlDataSnapshot { inner }))
        }
        Ok(CoreInstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(_)) => {
            Err("Installed YAML Data load requires Local Ignore recovery".to_string())
        }
        Err(error) => Err(error.to_string()),
    }
}

/// Consume a recovery-required operation and return its immutable recovery plan.
///
/// Callers inspect [`installed_yaml_data_load_status`] first. This `Result`
/// prevents Ready or failed operations from being consumed as recovery plans.
// CXX requires Box here to consume the C++ UniquePtr and transfer ownership.
#[allow(clippy::boxed_local)]
fn installed_yaml_data_load_take_recovery_plan(
    operation: Box<InstalledYamlDataLoadOperation>,
) -> Result<Box<LocalIgnoreRecoveryPlan>, String> {
    match operation.result {
        Ok(CoreInstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(inner)) => {
            Ok(Box::new(LocalIgnoreRecoveryPlan { inner }))
        }
        Ok(CoreInstalledYamlDataLoadOutcome::Ready(_)) => {
            Err("Installed YAML Data load is already ready".to_string())
        }
        Err(error) => Err(error.to_string()),
    }
}

/// Return the typed game retained by a Local Ignore recovery plan.
fn local_ignore_recovery_plan_game(plan: &LocalIgnoreRecoveryPlan) -> ffi::ExplicitYamlDataGameId {
    explicit_game_id_to_ffi(plan.inner.game())
}

/// Return the registered game-data role retained by a Local Ignore recovery plan.
fn local_ignore_recovery_plan_game_role(
    plan: &LocalIgnoreRecoveryPlan,
) -> ffi::InstalledYamlDataGameRole {
    match plan.inner.game_data_role() {
        CoreGameDataRole::Fallout4 => ffi::InstalledYamlDataGameRole::Fallout4,
    }
}

/// Return retained Main provenance, schema, and exact-byte content identity.
fn local_ignore_recovery_plan_main(
    plan: &LocalIgnoreRecoveryPlan,
) -> ffi::InspectedYamlDataFileDto {
    inspected_yaml_data_file_to_dto(plan.inner.main())
}

/// Return retained game provenance, schema, and exact-byte content identity.
fn local_ignore_recovery_plan_game_file(
    plan: &LocalIgnoreRecoveryPlan,
) -> ffi::InspectedYamlDataFileDto {
    inspected_yaml_data_file_to_dto(plan.inner.game_file())
}

/// Return the canonical malformed Local Ignore path observed by the recovery plan.
fn local_ignore_recovery_plan_local_ignore_path(plan: &LocalIgnoreRecoveryPlan) -> String {
    plan.inner
        .local_ignore_path()
        .to_string_lossy()
        .into_owned()
}

/// Return the identity of the exact malformed Local Ignore bytes retained by the plan.
fn local_ignore_recovery_plan_malformed_local_ignore_identity(
    plan: &LocalIgnoreRecoveryPlan,
) -> ffi::YamlDataContentIdentityDto {
    content_identity_to_dto(plan.inner.malformed_local_ignore_identity())
}

/// Report whether validated selected-Main defaults were available when recovery began.
fn local_ignore_recovery_plan_has_default_local_ignore_identity(
    plan: &LocalIgnoreRecoveryPlan,
) -> bool {
    plan.inner.default_local_ignore_identity().is_some()
}

/// Return the identity of validated selected-Main defaults retained by the plan.
///
/// CXX does not bridge `Option<YamlDataContentIdentityDto>`, so callers inspect
/// [`local_ignore_recovery_plan_has_default_local_ignore_identity`] first. An unavailable
/// identity projects as an empty DTO rather than panicking or blocking recovery.
fn local_ignore_recovery_plan_default_local_ignore_identity(
    plan: &LocalIgnoreRecoveryPlan,
) -> ffi::YamlDataContentIdentityDto {
    plan.inner
        .default_local_ignore_identity()
        .map(content_identity_to_dto)
        .unwrap_or_else(|| ffi::YamlDataContentIdentityDto {
            sha256: String::new(),
            byte_len: 0,
        })
}

/// Return the retained Version Registry selection mode for the interrupted operation.
fn local_ignore_recovery_plan_selected_game_version(plan: &LocalIgnoreRecoveryPlan) -> String {
    plan.inner.selected_game_version().to_string()
}

/// Return retained selection and malformed Local Ignore diagnostics.
fn local_ignore_recovery_plan_diagnostics(
    plan: &LocalIgnoreRecoveryPlan,
) -> Vec<ffi::InstalledYamlDataDiagnosticDto> {
    plan.inner
        .diagnostics()
        .iter()
        .map(installed_yaml_data_diagnostic_to_dto)
        .collect()
}

/// Consume a recovery plan and complete the retained operation with no ignore entries.
///
/// The returned snapshot retains the plan's exact Main, game, and malformed Local Ignore
/// identities. This decision is operation-scoped and performs no filesystem writes.
// CXX requires Box here to consume the C++ UniquePtr and transfer ownership.
#[allow(clippy::boxed_local)]
fn local_ignore_recovery_plan_proceed_without_ignore(
    plan: Box<LocalIgnoreRecoveryPlan>,
) -> Box<InstalledYamlDataSnapshot> {
    Box::new(InstalledYamlDataSnapshot {
        inner: plan.inner.proceed_without_ignore(),
    })
}

/// Clone the parsed configuration view retained by an Installed YAML Data snapshot.
fn installed_yaml_data_snapshot_yaml_data(snapshot: &InstalledYamlDataSnapshot) -> Box<YamlData> {
    Box::new(YamlData {
        inner: snapshot.inner.yaml_data().clone(),
    })
}

/// Return the typed game identity retained by an Installed YAML Data snapshot.
fn installed_yaml_data_snapshot_game(
    snapshot: &InstalledYamlDataSnapshot,
) -> ffi::ExplicitYamlDataGameId {
    explicit_game_id_to_ffi(snapshot.inner.game())
}

/// Return the registered game-data role retained by a snapshot.
fn installed_yaml_data_snapshot_game_role(
    snapshot: &InstalledYamlDataSnapshot,
) -> ffi::InstalledYamlDataGameRole {
    match snapshot.inner.game_data_role() {
        CoreGameDataRole::Fallout4 => ffi::InstalledYamlDataGameRole::Fallout4,
    }
}

/// Return selected Main provenance, schema, and exact-byte content identity.
fn installed_yaml_data_snapshot_main(
    snapshot: &InstalledYamlDataSnapshot,
) -> ffi::InspectedYamlDataFileDto {
    inspected_yaml_data_file_to_dto(snapshot.inner.main())
}

/// Return selected game provenance, schema, and exact-byte content identity.
fn installed_yaml_data_snapshot_game_file(
    snapshot: &InstalledYamlDataSnapshot,
) -> ffi::InspectedYamlDataFileDto {
    inspected_yaml_data_file_to_dto(snapshot.inner.game_file())
}

/// Return how Local Ignore YAML Data entered a ready snapshot.
fn installed_yaml_data_snapshot_local_ignore_state(
    snapshot: &InstalledYamlDataSnapshot,
) -> ffi::LocalIgnoreYamlDataState {
    match snapshot.inner.local_ignore_state() {
        CoreLocalIgnoreYamlDataState::Existing => ffi::LocalIgnoreYamlDataState::Existing,
        CoreLocalIgnoreYamlDataState::Generated => ffi::LocalIgnoreYamlDataState::Generated,
        CoreLocalIgnoreYamlDataState::ProceedWithoutIgnore => {
            ffi::LocalIgnoreYamlDataState::ProceedWithoutIgnore
        }
    }
}

/// Return the exact retained Local Ignore content identity.
fn installed_yaml_data_snapshot_local_ignore_identity(
    snapshot: &InstalledYamlDataSnapshot,
) -> ffi::YamlDataContentIdentityDto {
    content_identity_to_dto(snapshot.inner.local_ignore_identity())
}

/// Return every structured fallback, cache-resolution, or Local Ignore generation diagnostic.
fn installed_yaml_data_snapshot_diagnostics(
    snapshot: &InstalledYamlDataSnapshot,
) -> Vec<ffi::InstalledYamlDataDiagnosticDto> {
    snapshot
        .inner
        .diagnostics()
        .iter()
        .map(installed_yaml_data_diagnostic_to_dto)
        .collect()
}

/// Return the success/error status captured by an explicit YAML Data load.
fn explicit_yaml_data_load_status(
    load: &ExplicitYamlDataLoad,
) -> ffi::ExplicitYamlDataLoadStatusDto {
    match &load.result {
        Ok(_) => ffi::ExplicitYamlDataLoadStatusDto {
            has_snapshot: true,
            has_error: false,
            error: empty_explicit_yaml_data_error(),
        },
        Err(error) => ffi::ExplicitYamlDataLoadStatusDto {
            has_snapshot: false,
            has_error: true,
            error: explicit_yaml_data_error_to_dto(error),
        },
    }
}

/// Consume a successful load handle and return its immutable snapshot.
///
/// Callers inspect [`explicit_yaml_data_load_status`] first. This `Result`
/// protects against consuming a failed handle.
fn explicit_yaml_data_load_take_snapshot(
    load: Box<ExplicitYamlDataLoad>,
) -> Result<Box<ExplicitYamlDataSnapshot>, String> {
    match load.result {
        Ok(inner) => Ok(Box::new(ExplicitYamlDataSnapshot { inner })),
        Err(error) => Err(error.to_string()),
    }
}

/// Clone the parsed configuration view retained by an explicit snapshot.
fn explicit_yaml_data_snapshot_yaml_data(snapshot: &ExplicitYamlDataSnapshot) -> Box<YamlData> {
    Box::new(YamlData {
        inner: snapshot.inner.yaml_data().clone(),
    })
}

/// Return the registered game-data role used by the snapshot.
fn explicit_yaml_data_snapshot_game_role(
    snapshot: &ExplicitYamlDataSnapshot,
) -> ffi::ExplicitYamlDataGameRole {
    match snapshot.inner.game_data_role() {
        CoreGameDataRole::Fallout4 => ffi::ExplicitYamlDataGameRole::Fallout4,
    }
}

/// Return the caller's typed game identity retained by the snapshot.
fn explicit_yaml_data_snapshot_game(
    snapshot: &ExplicitYamlDataSnapshot,
) -> ffi::ExplicitYamlDataGameId {
    explicit_game_id_to_ffi(snapshot.inner.game())
}

/// Return the exact retained Main-file content identity.
fn explicit_yaml_data_snapshot_main_identity(
    snapshot: &ExplicitYamlDataSnapshot,
) -> ffi::YamlDataContentIdentityDto {
    content_identity_to_dto(snapshot.inner.main_identity())
}

/// Return the exact retained game-file content identity.
fn explicit_yaml_data_snapshot_game_identity(
    snapshot: &ExplicitYamlDataSnapshot,
) -> ffi::YamlDataContentIdentityDto {
    content_identity_to_dto(snapshot.inner.game_identity())
}

/// Return the exact retained Local Ignore-file content identity.
fn explicit_yaml_data_snapshot_ignore_identity(
    snapshot: &ExplicitYamlDataSnapshot,
) -> ffi::YamlDataContentIdentityDto {
    content_identity_to_dto(snapshot.inner.ignore_identity())
}

fn explicit_game_id_to_core(game: ffi::ExplicitYamlDataGameId) -> CoreGameId {
    match game {
        ffi::ExplicitYamlDataGameId::Fallout4 => CoreGameId::Fallout4,
        ffi::ExplicitYamlDataGameId::Fallout4VR => CoreGameId::Fallout4VR,
        ffi::ExplicitYamlDataGameId::Skyrim => CoreGameId::Skyrim,
        ffi::ExplicitYamlDataGameId::Starfield => CoreGameId::Starfield,
        // Unknown CXX enum values must fail as unsupported and must never
        // silently select Fallout 4 data.
        _ => CoreGameId::Starfield,
    }
}

fn explicit_game_id_to_ffi(game: CoreGameId) -> ffi::ExplicitYamlDataGameId {
    match game {
        CoreGameId::Fallout4 => ffi::ExplicitYamlDataGameId::Fallout4,
        CoreGameId::Fallout4VR => ffi::ExplicitYamlDataGameId::Fallout4VR,
        CoreGameId::Skyrim => ffi::ExplicitYamlDataGameId::Skyrim,
        CoreGameId::Starfield => ffi::ExplicitYamlDataGameId::Starfield,
    }
}

fn explicit_yaml_data_role_to_ffi(role: CoreExplicitYamlDataRole) -> ffi::ExplicitYamlDataRole {
    match role {
        CoreExplicitYamlDataRole::Main => ffi::ExplicitYamlDataRole::Main,
        CoreExplicitYamlDataRole::Game => ffi::ExplicitYamlDataRole::Game,
        CoreExplicitYamlDataRole::LocalIgnore => ffi::ExplicitYamlDataRole::LocalIgnore,
    }
}

fn explicit_yaml_data_error_to_dto(
    error: &CoreExplicitYamlDataLoadError,
) -> ffi::ExplicitYamlDataLoadErrorDto {
    let (kind, role, path) = match error {
        CoreExplicitYamlDataLoadError::UnsupportedGame { .. } => (
            ffi::ExplicitYamlDataLoadErrorKind::UnsupportedGame,
            None,
            None,
        ),
        CoreExplicitYamlDataLoadError::Read { role, path, .. } => (
            ffi::ExplicitYamlDataLoadErrorKind::Read,
            Some(*role),
            Some(path),
        ),
        CoreExplicitYamlDataLoadError::InvalidUtf8 { role, path, .. } => (
            ffi::ExplicitYamlDataLoadErrorKind::InvalidUtf8,
            Some(*role),
            Some(path),
        ),
        CoreExplicitYamlDataLoadError::Parse { role, path, .. } => (
            ffi::ExplicitYamlDataLoadErrorKind::Parse,
            Some(*role),
            Some(path),
        ),
        CoreExplicitYamlDataLoadError::InvalidRoleData { role, path, .. } => (
            ffi::ExplicitYamlDataLoadErrorKind::InvalidRoleData,
            Some(*role),
            Some(path),
        ),
    };
    ffi::ExplicitYamlDataLoadErrorDto {
        kind,
        has_role: role.is_some(),
        role: role
            .map(explicit_yaml_data_role_to_ffi)
            .unwrap_or(ffi::ExplicitYamlDataRole::Main),
        has_path: path.is_some(),
        path: path
            .map(|path| path.to_string_lossy().into_owned())
            .unwrap_or_default(),
        message: error.to_string(),
    }
}

fn empty_explicit_yaml_data_error() -> ffi::ExplicitYamlDataLoadErrorDto {
    // CXX shared structs cannot omit nested records; `has_error` is authoritative.
    ffi::ExplicitYamlDataLoadErrorDto {
        kind: ffi::ExplicitYamlDataLoadErrorKind::UnsupportedGame,
        has_role: false,
        role: ffi::ExplicitYamlDataRole::Main,
        has_path: false,
        path: String::new(),
        message: String::new(),
    }
}

fn content_identity_to_dto(identity: &YamlDataContentIdentity) -> ffi::YamlDataContentIdentityDto {
    ffi::YamlDataContentIdentityDto {
        sha256: identity.sha256_hex(),
        byte_len: identity.byte_len(),
    }
}

/// Convert a core Installed YAML Data role to its CXX projection.
fn installed_yaml_data_role_to_ffi(role: CoreInstalledYamlDataRole) -> ffi::InstalledYamlDataRole {
    match role {
        CoreInstalledYamlDataRole::Main => ffi::InstalledYamlDataRole::Main,
        CoreInstalledYamlDataRole::Game => ffi::InstalledYamlDataRole::Game,
    }
}

/// Convert a core selected-file role to the broader Installed YAML Data load role.
fn installed_yaml_data_load_role_to_ffi(
    role: CoreInstalledYamlDataRole,
) -> ffi::InstalledYamlDataLoadRole {
    match role {
        CoreInstalledYamlDataRole::Main => ffi::InstalledYamlDataLoadRole::Main,
        CoreInstalledYamlDataRole::Game => ffi::InstalledYamlDataLoadRole::Game,
    }
}

/// Convert core candidate provenance to its stable CXX projection.
fn installed_yaml_data_provenance_to_ffi(
    provenance: CoreInstalledYamlDataProvenance,
) -> ffi::InstalledYamlDataProvenance {
    match provenance {
        CoreInstalledYamlDataProvenance::Updated => ffi::InstalledYamlDataProvenance::Updated,
        CoreInstalledYamlDataProvenance::Previous => ffi::InstalledYamlDataProvenance::Previous,
        CoreInstalledYamlDataProvenance::Bundled => ffi::InstalledYamlDataProvenance::Bundled,
    }
}

/// Convert a core diagnostic kind to the stable CXX inventory.
fn installed_yaml_data_diagnostic_kind_to_ffi(
    kind: CoreInstalledYamlDataDiagnosticKind,
) -> ffi::InstalledYamlDataDiagnosticKind {
    match kind {
        CoreInstalledYamlDataDiagnosticKind::CacheUnavailable => {
            ffi::InstalledYamlDataDiagnosticKind::CacheUnavailable
        }
        CoreInstalledYamlDataDiagnosticKind::Missing => {
            ffi::InstalledYamlDataDiagnosticKind::Missing
        }
        CoreInstalledYamlDataDiagnosticKind::Read => ffi::InstalledYamlDataDiagnosticKind::Read,
        CoreInstalledYamlDataDiagnosticKind::InvalidUtf8 => {
            ffi::InstalledYamlDataDiagnosticKind::InvalidUtf8
        }
        CoreInstalledYamlDataDiagnosticKind::Parse => ffi::InstalledYamlDataDiagnosticKind::Parse,
        CoreInstalledYamlDataDiagnosticKind::InvalidSchema => {
            ffi::InstalledYamlDataDiagnosticKind::InvalidSchema
        }
        CoreInstalledYamlDataDiagnosticKind::IncompatibleSchema => {
            ffi::InstalledYamlDataDiagnosticKind::IncompatibleSchema
        }
        CoreInstalledYamlDataDiagnosticKind::InvalidRoleData => {
            ffi::InstalledYamlDataDiagnosticKind::InvalidRoleData
        }
        CoreInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated => {
            ffi::InstalledYamlDataDiagnosticKind::LocalIgnoreGenerated
        }
    }
}

/// Flatten one selected core file into its CXX metadata DTO.
fn inspected_yaml_data_file_to_dto(
    file: &CoreInspectedYamlDataFile,
) -> ffi::InspectedYamlDataFileDto {
    ffi::InspectedYamlDataFileDto {
        role: installed_yaml_data_role_to_ffi(file.role()),
        provenance: installed_yaml_data_provenance_to_ffi(file.provenance()),
        schema_version: file.schema_version().to_string(),
        sha256: file.identity().sha256_hex(),
        byte_len: file.identity().byte_len(),
    }
}

/// Flatten one structured core diagnostic into its CXX DTO.
fn installed_yaml_data_diagnostic_to_dto(
    diagnostic: &CoreInstalledYamlDataDiagnostic,
) -> ffi::InstalledYamlDataDiagnosticDto {
    let role = diagnostic.role();
    let candidate = diagnostic.candidate();
    let path = diagnostic.path();
    ffi::InstalledYamlDataDiagnosticDto {
        has_role: role.is_some(),
        role: role
            .map(installed_yaml_data_role_to_ffi)
            .unwrap_or(ffi::InstalledYamlDataRole::Main),
        has_candidate: candidate.is_some(),
        candidate: candidate
            .map(installed_yaml_data_provenance_to_ffi)
            .unwrap_or(ffi::InstalledYamlDataProvenance::Bundled),
        has_path: path.is_some(),
        path: path
            .map(|path| path.to_string_lossy().into_owned())
            .unwrap_or_default(),
        kind: installed_yaml_data_diagnostic_kind_to_ffi(diagnostic.kind()),
        message: diagnostic.message().to_string(),
    }
}

/// Convert one core inspection failure into its typed CXX error DTO.
fn installed_yaml_data_inspection_error_to_dto(
    error: &CoreInstalledYamlDataInspectionError,
) -> ffi::InstalledYamlDataInspectionErrorDto {
    match error {
        CoreInstalledYamlDataInspectionError::UnsupportedGame { .. } => {
            ffi::InstalledYamlDataInspectionErrorDto {
                kind: ffi::InstalledYamlDataInspectionErrorKind::UnsupportedGame,
                has_role: false,
                role: ffi::InstalledYamlDataRole::Main,
                diagnostics: Vec::new(),
                message: error.to_string(),
            }
        }
        CoreInstalledYamlDataInspectionError::NoUsableSource { role, diagnostics } => {
            ffi::InstalledYamlDataInspectionErrorDto {
                kind: ffi::InstalledYamlDataInspectionErrorKind::NoUsableSource,
                has_role: true,
                role: installed_yaml_data_role_to_ffi(*role),
                diagnostics: diagnostics
                    .iter()
                    .map(installed_yaml_data_diagnostic_to_dto)
                    .collect(),
                message: error.to_string(),
            }
        }
    }
}

/// Return the placeholder nested error used when `has_error` is false.
fn empty_installed_yaml_data_inspection_error() -> ffi::InstalledYamlDataInspectionErrorDto {
    ffi::InstalledYamlDataInspectionErrorDto {
        kind: ffi::InstalledYamlDataInspectionErrorKind::UnsupportedGame,
        has_role: false,
        role: ffi::InstalledYamlDataRole::Main,
        diagnostics: Vec::new(),
        message: String::new(),
    }
}

/// Convert one core Installed YAML Data load failure into its typed CXX error DTO.
fn installed_yaml_data_load_error_to_dto(
    error: &CoreInstalledYamlDataLoadError,
) -> ffi::InstalledYamlDataLoadErrorDto {
    let (kind, role, path, diagnostics) = match error {
        CoreInstalledYamlDataLoadError::UnsupportedGame { .. } => (
            ffi::InstalledYamlDataLoadErrorKind::UnsupportedGame,
            None,
            None,
            Vec::new(),
        ),
        CoreInstalledYamlDataLoadError::NoUsableSource { role, diagnostics } => (
            ffi::InstalledYamlDataLoadErrorKind::NoUsableSource,
            Some(installed_yaml_data_load_role_to_ffi(*role)),
            None,
            diagnostics
                .iter()
                .map(installed_yaml_data_diagnostic_to_dto)
                .collect(),
        ),
        CoreInstalledYamlDataLoadError::LocalIgnoreRead { path, .. } => (
            ffi::InstalledYamlDataLoadErrorKind::LocalIgnoreRead,
            Some(ffi::InstalledYamlDataLoadRole::LocalIgnore),
            Some(path),
            Vec::new(),
        ),
        CoreInstalledYamlDataLoadError::LocalIgnoreDefaultInvalid { path, .. } => (
            ffi::InstalledYamlDataLoadErrorKind::LocalIgnoreDefaultInvalid,
            Some(ffi::InstalledYamlDataLoadRole::LocalIgnore),
            Some(path),
            Vec::new(),
        ),
        CoreInstalledYamlDataLoadError::LocalIgnoreCreate { path, .. } => (
            ffi::InstalledYamlDataLoadErrorKind::LocalIgnoreCreate,
            Some(ffi::InstalledYamlDataLoadRole::LocalIgnore),
            Some(path),
            Vec::new(),
        ),
        CoreInstalledYamlDataLoadError::InvalidSelectedData { .. } => (
            ffi::InstalledYamlDataLoadErrorKind::InvalidSelectedData,
            None,
            None,
            Vec::new(),
        ),
    };
    ffi::InstalledYamlDataLoadErrorDto {
        kind,
        has_role: role.is_some(),
        role: role.unwrap_or(ffi::InstalledYamlDataLoadRole::Main),
        has_path: path.is_some(),
        path: path
            .map(|path| path.to_string_lossy().into_owned())
            .unwrap_or_default(),
        diagnostics,
        message: error.to_string(),
    }
}

/// Return the placeholder nested load error used when `has_error` is false.
fn empty_installed_yaml_data_load_error() -> ffi::InstalledYamlDataLoadErrorDto {
    // CXX shared structs cannot omit nested records; `has_error` is authoritative.
    ffi::InstalledYamlDataLoadErrorDto {
        kind: ffi::InstalledYamlDataLoadErrorKind::UnsupportedGame,
        has_role: false,
        role: ffi::InstalledYamlDataLoadRole::Main,
        has_path: false,
        path: String::new(),
        diagnostics: Vec::new(),
        message: String::new(),
    }
}

/// Persist optional game and documents paths through the standalone Game Local writer.
///
/// Empty path strings mean "leave this key unchanged". Failures are returned as
/// strings for the existing CXX `Result` contract.
fn save_local_yaml_paths(
    local_yaml_path: &str,
    game_root: &str,
    docs_root: &str,
) -> Result<(), String> {
    // CXX strings cannot express optional borrowed paths, so empty values retain
    // the established adapter meaning of "do not update this field".
    let game_root = (!game_root.is_empty()).then(|| Path::new(game_root));
    let docs_root = (!docs_root.is_empty()).then(|| Path::new(docs_root));

    get_runtime()
        .block_on(persist_game_local_paths(
            Path::new(local_yaml_path),
            game_root,
            docs_root,
        ))
        .map_err(|e| format!("{e}"))
}

// ── Main YAML version (schema-gated) ────────────────────────────────
//
// Unlike `yaml_data_load`, this helper is scoped to exactly one field
// (`CLASSIC_Info.version`) and is intentionally schema-gated by
// `client_schemas::MAIN_YAML`. Native frontends call it on startup to
// populate `QApplication::applicationVersion()` (GUI) or the
// binary-release update-check input (CLI) without ever trusting a
// partially-updated or legacy `schema_version: 1.x` file that would
// otherwise degrade downstream notification classification to `unknown`.
//
// Error shape follows the app-notification precedent in `update.rs`:
// empty-string sentinels on success, a structured `error_kind` plus
// human-readable `error_message` on failure. This lets Qt callers map
// each kind to an actionable dialog ("upgrade client", "fix version
// field", etc.) without parsing free-form strings.

/// Load `CLASSIC Main.yaml` with `client_schemas::MAIN_YAML` schema gating
/// and return the trimmed `CLASSIC_Info.version`.
///
/// `bundled_yaml_dir` empty string keeps the default relative path
/// (`CLASSIC Data/databases/CLASSIC Main.yaml`, resolved against process
/// CWD — correct for the CLI/GUI launched next to `CLASSIC Data/`). A
/// non-empty value is the explicit install-tree directory holding the
/// shippable YAML files (pass this from contexts where `current_exe()`
/// would yield the wrong parent).
fn load_main_yaml_version(bundled_yaml_dir: &str) -> ffi::MainYamlVersionDto {
    let bundled = if bundled_yaml_dir.is_empty() {
        None
    } else {
        Some(Path::new(bundled_yaml_dir))
    };
    match get_runtime().block_on(core_load_main_yaml_version_with_bundled_dir(bundled)) {
        Ok(version) => ffi::MainYamlVersionDto {
            version,
            error_kind: String::new(),
            error_message: String::new(),
        },
        Err(err) => ffi::MainYamlVersionDto {
            version: String::new(),
            error_kind: main_yaml_version_error_kind(&err).to_string(),
            error_message: format!("{err}"),
        },
    }
}

/// Stable `error_kind` discriminator values for
/// [`ffi::MainYamlVersionDto`]. Kept as a dedicated function so the
/// string constants stay adjacent to the match and any future variants
/// (the core error is `#[non_exhaustive]`) show up here as a compile
/// error that forces the bridge to acknowledge them.
fn main_yaml_version_error_kind(err: &MainYamlVersionError) -> &'static str {
    match err {
        MainYamlVersionError::Load(_) => "load",
        MainYamlVersionError::VersionKeyMissing { .. } => "version_key_missing",
        MainYamlVersionError::VersionEmpty { .. } => "version_empty",
        MainYamlVersionError::VersionNotString { .. } => "version_not_string",
        MainYamlVersionError::VersionInvalid { .. } => "version_invalid",
        // `MainYamlVersionError` is `#[non_exhaustive]`; when a new
        // variant is added in the core crate this arm forces the bridge
        // to pick a new `error_kind` string instead of silently folding
        // into a catch-all.
        _ => "unknown",
    }
}

// ── String getters ──────────────────────────────────────────────────

fn yaml_data_classic_version(data: &YamlData) -> &str {
    &data.inner.classic_version
}

fn yaml_data_classic_version_date(data: &YamlData) -> &str {
    &data.inner.classic_version_date
}

fn yaml_data_crashgen_name_field(data: &YamlData) -> &str {
    &data.inner.crashgen_name
}

fn yaml_data_crashgen_latest_og(data: &YamlData) -> &str {
    &data.inner.crashgen_latest_og
}

fn yaml_data_warn_noplugins(data: &YamlData) -> &str {
    &data.inner.warn_noplugins
}

fn yaml_data_warn_outdated(data: &YamlData) -> &str {
    &data.inner.warn_outdated
}

fn yaml_data_xse_acronym(data: &YamlData) -> &str {
    &data.inner.xse_acronym
}

fn yaml_data_autoscan_text(data: &YamlData) -> &str {
    &data.inner.autoscan_text
}

fn yaml_data_game_version(data: &YamlData) -> &str {
    &data.inner.game_version
}

fn yaml_data_game_root_name_field(data: &YamlData) -> &str {
    &data.inner.game_root_name
}

// ── Accessors ───────────────────────────────────────────────────────

fn yaml_data_get_crashgen_name(data: &YamlData) -> String {
    data.inner.get_crashgen_name().to_string()
}

fn yaml_data_get_game_root_name(data: &YamlData) -> String {
    data.inner.get_game_root_name().to_string()
}

fn yaml_data_get_crashgen_ignore(data: &YamlData) -> Vec<String> {
    data.inner.get_crashgen_ignore().to_vec()
}

// ── Vec<String> getters ─────────────────────────────────────────────

fn yaml_data_classic_game_hints(data: &YamlData) -> Vec<String> {
    data.inner.classic_game_hints.clone()
}

fn yaml_data_classic_records_list(data: &YamlData) -> Vec<String> {
    data.inner.classic_records_list.clone()
}

fn yaml_data_crashgen_ignore_og(data: &YamlData) -> Vec<String> {
    data.inner.crashgen_ignore.clone()
}

fn yaml_data_game_ignore_plugins(data: &YamlData) -> Vec<String> {
    data.inner.game_ignore_plugins.clone()
}

fn yaml_data_game_ignore_records(data: &YamlData) -> Vec<String> {
    data.inner.game_ignore_records.clone()
}

fn yaml_data_ignore_list(data: &YamlData) -> Vec<String> {
    data.inner.ignore_list.clone()
}

// ── IndexMap getters as key/value pair vectors ──────────────────────
// CXX bridges are isolated, so we return flattened data instead of
// opaque StringMap/StringVecMap types from the types module.

fn yaml_data_suspects_error_keys(data: &YamlData) -> Vec<String> {
    data.inner
        .suspect_error_rules
        .iter()
        .map(|rule| rule.id.clone())
        .collect()
}

fn yaml_data_suspects_error_values(data: &YamlData) -> Vec<String> {
    data.inner
        .suspect_error_rules
        .iter()
        .map(|rule| rule.name.clone())
        .collect()
}

fn yaml_data_suspects_stack_keys(data: &YamlData) -> Vec<String> {
    data.inner
        .suspect_stack_rules
        .iter()
        .map(|rule| rule.id.clone())
        .collect()
}

fn yaml_data_mods_core_keys(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_core
        .iter()
        .map(|e| e.detect.clone())
        .collect()
}

fn yaml_data_mods_core_values(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_core
        .iter()
        .map(|e| e.description.clone())
        .collect()
}

fn yaml_data_mods_core_names(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_core
        .iter()
        .map(|e| e.name.clone())
        .collect()
}

fn yaml_data_mods_core_gpus(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_core
        .iter()
        .map(|e| e.gpu.clone().unwrap_or_default())
        .collect()
}

fn yaml_data_mods_core_count(data: &YamlData) -> usize {
    data.inner.game_mods_core.len()
}

fn yaml_data_mod_entry(
    entry: &classic_config_core::ModSolutionEntry,
) -> ffi::YamlDataModSolutionEntry {
    let criteria = match &entry.criteria {
        ModSolutionCriteria::Any(values) => ffi::YamlDataModSolutionCriteria {
            any: values.clone(),
            all: Vec::new(),
        },
        ModSolutionCriteria::All(values) => ffi::YamlDataModSolutionCriteria {
            any: Vec::new(),
            all: values.clone(),
        },
    };

    ffi::YamlDataModSolutionEntry {
        id: entry.id.clone(),
        criteria,
        exceptions: entry.exceptions.clone(),
        name: entry.name.clone(),
        description: entry.description.clone(),
    }
}

fn yaml_data_mods_freq_entries(data: &YamlData) -> Vec<ffi::YamlDataModSolutionEntry> {
    data.inner
        .game_mods_freq
        .iter()
        .map(yaml_data_mod_entry)
        .collect()
}

fn yaml_data_mods_conf_mod_a(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_conf
        .iter()
        .map(|e| e.mod_a.clone())
        .collect()
}

fn yaml_data_mods_conf_mod_b(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_conf
        .iter()
        .map(|e| e.mod_b.clone())
        .collect()
}

fn yaml_data_mods_conf_name_a(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_conf
        .iter()
        .map(|e| e.name_a.clone())
        .collect()
}

fn yaml_data_mods_conf_name_b(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_conf
        .iter()
        .map(|e| e.name_b.clone())
        .collect()
}

fn yaml_data_mods_conf_descriptions(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_conf
        .iter()
        .map(|e| e.description.clone())
        .collect()
}

fn yaml_data_mods_conf_fixes(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_conf
        .iter()
        .map(|e| e.fix.clone())
        .collect()
}

fn yaml_data_mods_conf_links(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_conf
        .iter()
        .map(|e| e.link.clone().unwrap_or_default())
        .collect()
}

fn yaml_data_mods_conf_count(data: &YamlData) -> usize {
    data.inner.game_mods_conf.len()
}

fn yaml_data_mods_solu_entries(data: &YamlData) -> Vec<ffi::YamlDataModSolutionEntry> {
    data.inner
        .game_mods_solu
        .iter()
        .map(yaml_data_mod_entry)
        .collect()
}

fn settings_cache_clear() {
    clear_settings_cache();
}

fn settings_cache_size() -> usize {
    settings_cache_stats().size
}

fn settings_cache_stats() -> ffi::CacheStats {
    let stats = settings_core_cache_stats();
    ffi::CacheStats {
        hits: stats.hits,
        misses: stats.misses,
        hit_rate: stats.hit_rate,
        size: stats.size,
        capacity: stats.capacity,
    }
}

fn reset_settings_cache_stats() {
    reset_settings_core_cache_stats();
}

// ── Suspect rule typed accessors (CXXS-07) ─────────────────────────
// Additive per D-08 — existing yaml_data_suspects_error_keys/values and
// yaml_data_suspects_stack_keys fns above remain unchanged.

/// Returns the full set of error-type suspect rules as typed DTOs.
///
/// Each `SuspectErrorRuleDto` carries the rule's stable `id`, display `name`,
/// `severity`, and the `main_error_contains_any` pattern list.
///
/// Bridge contract: this is the typed complement to the existing
/// `yaml_data_suspects_error_keys` / `yaml_data_suspects_error_values` pair.
/// Both coexist per D-08 (additive, not replacing).
fn yaml_data_suspects_error_rules(data: &YamlData) -> Vec<ffi::SuspectErrorRuleDto> {
    data.inner
        .suspect_error_rules
        .iter()
        .map(|r: &CoreSuspectErrorRule| ffi::SuspectErrorRuleDto {
            id: r.id.clone(),
            name: r.name.clone(),
            severity: r.severity,
            main_error_contains_any: r.main_error_contains_any.clone(),
        })
        .collect()
}

/// Returns the flattened metadata for all stack-type suspect rules.
///
/// Each `SuspectStackRuleMetadataDto` carries the rule's `id`, `name`,
/// `severity`, and the four `Vec<String>` pattern fields — but does NOT
/// include the nested `stack_contains_at_least` count rules. Those are
/// exposed separately via `yaml_data_suspects_stack_count_rules_for_id`.
///
/// Pitfall 6 fix (Codex HIGH correction): a previous design returned
/// `Vec<SuspectStackRuleDto>` where the inner DTO contained a
/// `Vec<SuspectStackCountRuleDto>` field. That is a `Vec<StructWithVec>`
/// shape that CXX cannot safely bridge. The flattened metadata DTO +
/// separate per-rule count getter eliminates this constraint entirely.
fn yaml_data_suspects_stack_rules_metadata(
    data: &YamlData,
) -> Vec<ffi::SuspectStackRuleMetadataDto> {
    data.inner
        .suspect_stack_rules
        .iter()
        .map(
            |r: &CoreSuspectStackRule| ffi::SuspectStackRuleMetadataDto {
                id: r.id.clone(),
                name: r.name.clone(),
                severity: r.severity,
                main_error_required_any: r.main_error_required_any.clone(),
                main_error_optional_any: r.main_error_optional_any.clone(),
                stack_contains_any: r.stack_contains_any.clone(),
                exclude_if_stack_contains_any: r.exclude_if_stack_contains_any.clone(),
                // Note: stack_contains_at_least is NOT included here — use
                // yaml_data_suspects_stack_count_rules_for_id to retrieve count rules.
            },
        )
        .collect()
}

/// Returns the count rules for a single stack-type suspect rule, keyed by rule id.
///
/// C++ callers iterate the metadata list first via
/// `yaml_data_suspects_stack_rules_metadata`, then call this getter for each
/// rule that needs its count rules. Returns an empty Vec when the id is not
/// found (unknown id, no count rules configured).
///
/// Each `SuspectStackCountRuleDto` has a `substring` (the stack pattern) and
/// a `count` (minimum required occurrences, cast from `usize` to `u32`).
fn yaml_data_suspects_stack_count_rules_for_id(
    data: &YamlData,
    rule_id: &str,
) -> Vec<ffi::SuspectStackCountRuleDto> {
    data.inner
        .suspect_stack_rules
        .iter()
        .find(|r| r.id == rule_id)
        .map(|r| {
            r.stack_contains_at_least
                .iter()
                .map(
                    |c: &CoreSuspectStackCountRule| ffi::SuspectStackCountRuleDto {
                        substring: c.substring.clone(),
                        count: c.count as u32,
                    },
                )
                .collect()
        })
        .unwrap_or_default()
}

#[cxx::bridge(namespace = "classic::config")]
mod ffi {
    /// Typed game identity for deterministic explicit YAML Data loading.
    ///
    /// CXX bridge modules cannot share enum definitions, so this mirrors
    /// `classic_shared_core::GameId` in the config namespace.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ExplicitYamlDataGameId {
        Fallout4 = 0,
        Fallout4VR = 1,
        Skyrim = 2,
        Starfield = 3,
    }

    /// Registered game-data role selected for an explicit snapshot.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ExplicitYamlDataGameRole {
        Fallout4 = 0,
    }

    /// Role of one exact file in an explicit YAML Data request.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ExplicitYamlDataRole {
        Main = 0,
        Game = 1,
        LocalIgnore = 2,
    }

    /// Stable typed category of one explicit YAML Data load failure.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ExplicitYamlDataLoadErrorKind {
        UnsupportedGame = 0,
        Read = 1,
        InvalidUtf8 = 2,
        Parse = 3,
        InvalidRoleData = 4,
    }

    /// Registered game-data role selected by Installed YAML Data inspection.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum InstalledYamlDataGameRole {
        Fallout4 = 0,
    }

    /// Update-eligible YAML Data role attributed by inspection.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum InstalledYamlDataRole {
        Main = 0,
        Game = 1,
    }

    /// Candidate provenance for one selected or rejected installed file.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum InstalledYamlDataProvenance {
        Updated = 0,
        Previous = 1,
        Bundled = 2,
    }

    /// Stable category for an Installed YAML Data selection or generation diagnostic.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum InstalledYamlDataDiagnosticKind {
        CacheUnavailable = 0,
        Missing = 1,
        Read = 2,
        InvalidUtf8 = 3,
        Parse = 4,
        InvalidSchema = 5,
        IncompatibleSchema = 6,
        InvalidRoleData = 7,
        /// Missing Local Ignore YAML Data was generated from selected Main defaults.
        LocalIgnoreGenerated = 8,
    }

    /// Stable typed category of an Installed YAML Data inspection failure.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum InstalledYamlDataInspectionErrorKind {
        UnsupportedGame = 0,
        NoUsableSource = 1,
    }

    /// Stable typed category of an Installed YAML Data load failure.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum InstalledYamlDataLoadErrorKind {
        UnsupportedGame = 0,
        NoUsableSource = 1,
        LocalIgnoreRead = 2,
        InvalidSelectedData = 6,
        /// Selected Main defaults could not safely initialize Local Ignore YAML Data.
        LocalIgnoreDefaultInvalid = 7,
        /// Local Ignore YAML Data could not be atomically created.
        LocalIgnoreCreate = 8,
    }

    /// File role attributed by an Installed YAML Data load failure.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum InstalledYamlDataLoadRole {
        Main = 0,
        Game = 1,
        LocalIgnore = 2,
    }

    /// How Local Ignore YAML Data entered a ready installed snapshot.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum LocalIgnoreYamlDataState {
        Existing = 0,
        /// Missing Local Ignore YAML Data was generated from selected Main defaults.
        Generated = 1,
        /// Malformed Local Ignore bytes were ignored for this operation without changing them.
        ProceedWithoutIgnore = 2,
    }

    /// Exact caller-selected paths for deterministic YAML Data loading.
    struct ExplicitYamlDataPathsDto {
        main_path: String,
        game_path: String,
        ignore_path: String,
    }

    /// Content identity derived from the exact retained file bytes.
    struct YamlDataContentIdentityDto {
        sha256: String,
        byte_len: u64,
    }

    /// Typed explicit-load failure with optional role and path context.
    struct ExplicitYamlDataLoadErrorDto {
        kind: ExplicitYamlDataLoadErrorKind,
        has_role: bool,
        role: ExplicitYamlDataRole,
        has_path: bool,
        path: String,
        message: String,
    }

    /// Exactly one of `has_snapshot` and `has_error` is true.
    struct ExplicitYamlDataLoadStatusDto {
        has_snapshot: bool,
        has_error: bool,
        error: ExplicitYamlDataLoadErrorDto,
    }

    /// Selected-file metadata derived from the exact inspected bytes.
    struct InspectedYamlDataFileDto {
        role: InstalledYamlDataRole,
        provenance: InstalledYamlDataProvenance,
        schema_version: String,
        sha256: String,
        byte_len: u64,
    }

    /// Structured attribution for one fallback, cache-resolution, or Local Ignore generation event.
    struct InstalledYamlDataDiagnosticDto {
        has_role: bool,
        role: InstalledYamlDataRole,
        has_candidate: bool,
        candidate: InstalledYamlDataProvenance,
        has_path: bool,
        path: String,
        kind: InstalledYamlDataDiagnosticKind,
        message: String,
    }

    /// Typed inspection failure with optional role and structured diagnostics.
    struct InstalledYamlDataInspectionErrorDto {
        kind: InstalledYamlDataInspectionErrorKind,
        has_role: bool,
        role: InstalledYamlDataRole,
        diagnostics: Vec<InstalledYamlDataDiagnosticDto>,
        message: String,
    }

    /// Exactly one of `has_inspection` and `has_error` is true.
    struct InstalledYamlDataInspectionStatusDto {
        has_inspection: bool,
        has_error: bool,
        error: InstalledYamlDataInspectionErrorDto,
    }

    /// Typed Installed YAML Data load failure with optional role/path context.
    struct InstalledYamlDataLoadErrorDto {
        kind: InstalledYamlDataLoadErrorKind,
        has_role: bool,
        role: InstalledYamlDataLoadRole,
        has_path: bool,
        path: String,
        diagnostics: Vec<InstalledYamlDataDiagnosticDto>,
        message: String,
    }

    /// Exactly one of `has_snapshot`, `has_recovery_plan`, and `has_error` is true.
    struct InstalledYamlDataLoadStatusDto {
        has_snapshot: bool,
        has_recovery_plan: bool,
        has_error: bool,
        error: InstalledYamlDataLoadErrorDto,
    }

    struct CacheStats {
        hits: u64,
        misses: u64,
        hit_rate: f64,
        size: usize,
        capacity: usize,
    }

    struct YamlDataModSolutionCriteria {
        any: Vec<String>,
        all: Vec<String>,
    }

    struct YamlDataModSolutionEntry {
        id: String,
        criteria: YamlDataModSolutionCriteria,
        exceptions: Vec<String>,
        name: String,
        description: String,
    }

    // CXXS-07: Typed suspect-rule DTOs (additive per D-08)

    /// Typed DTO for a single error-type suspect rule (Crashlog_Error_Check).
    struct SuspectErrorRuleDto {
        id: String,
        name: String,
        severity: i32,
        main_error_contains_any: Vec<String>,
    }

    /// Flattened metadata DTO for a single stack-type suspect rule (Crashlog_Stack_Check).
    ///
    /// Does NOT contain the nested count rules — use
    /// `yaml_data_suspects_stack_count_rules_for_id` to retrieve those separately.
    /// This flattening satisfies Pitfall 6 (no Vec<StructWithVec>).
    struct SuspectStackRuleMetadataDto {
        id: String,
        name: String,
        severity: i32,
        main_error_required_any: Vec<String>,
        main_error_optional_any: Vec<String>,
        stack_contains_any: Vec<String>,
        exclude_if_stack_contains_any: Vec<String>,
    }

    /// DTO for a single count-based stack-match requirement within a stack rule.
    /// Returned by `yaml_data_suspects_stack_count_rules_for_id` keyed by rule id.
    struct SuspectStackCountRuleDto {
        substring: String,
        count: u32,
    }

    /// Result of [`load_main_yaml_version`].
    ///
    /// Empty-string sentinel contract per `docs/api/error-contract.md`:
    ///
    /// - On success: `version` is the trimmed `CLASSIC_Info.version`
    ///   (never empty); `error_kind` and `error_message` are `""`.
    /// - On failure: `version` is `""`; `error_kind` carries one of
    ///   `"load"`, `"version_key_missing"`, `"version_empty"`,
    ///   `"version_not_string"`, or `"unknown"` (reserved for future
    ///   `MainYamlVersionError` variants); `error_message` carries the
    ///   `Display` rendering of the underlying error, suitable for a
    ///   Qt message box.
    ///
    /// C++ callers check `error_kind.empty()` first; a non-empty
    /// `error_kind` MUST be surfaced (do not fall back to
    /// `QApplication::applicationVersion()` — that would reintroduce
    /// the silent-degradation behavior this bridge exists to prevent).
    struct MainYamlVersionDto {
        version: String,
        error_kind: String,
        error_message: String,
    }

    extern "Rust" {
        type YamlData;
        type ExplicitYamlDataLoad;
        type ExplicitYamlDataSnapshot;
        type InstalledYamlDataInspectionOperation;
        type InstalledYamlDataInspection;
        type InstalledYamlDataLoadOperation;
        type InstalledYamlDataSnapshot;
        type LocalIgnoreRecoveryPlan;

        // Construction (async, block_on)
        fn yaml_data_load(
            yaml_dir_root: &str,
            yaml_dir_data: &str,
            game: &str,
            game_version: &str,
        ) -> Result<Box<YamlData>>;

        /// Begin a deterministic load of exactly the supplied Main, game, and
        /// Local Ignore files. This operation never consults installation state.
        fn explicit_yaml_data_load(
            paths: ExplicitYamlDataPathsDto,
            game: ExplicitYamlDataGameId,
            selected_game_version: &str,
        ) -> Box<ExplicitYamlDataLoad>;
        /// Inspect the stable typed result before consuming a successful snapshot.
        fn explicit_yaml_data_load_status(
            load: &ExplicitYamlDataLoad,
        ) -> ExplicitYamlDataLoadStatusDto;
        /// Consume a ready load and return its immutable snapshot.
        fn explicit_yaml_data_load_take_snapshot(
            load: Box<ExplicitYamlDataLoad>,
        ) -> Result<Box<ExplicitYamlDataSnapshot>>;
        /// Clone the parsed configuration view retained by a snapshot.
        fn explicit_yaml_data_snapshot_yaml_data(
            snapshot: &ExplicitYamlDataSnapshot,
        ) -> Box<YamlData>;
        fn explicit_yaml_data_snapshot_game_role(
            snapshot: &ExplicitYamlDataSnapshot,
        ) -> ExplicitYamlDataGameRole;
        fn explicit_yaml_data_snapshot_game(
            snapshot: &ExplicitYamlDataSnapshot,
        ) -> ExplicitYamlDataGameId;
        fn explicit_yaml_data_snapshot_main_identity(
            snapshot: &ExplicitYamlDataSnapshot,
        ) -> YamlDataContentIdentityDto;
        fn explicit_yaml_data_snapshot_game_identity(
            snapshot: &ExplicitYamlDataSnapshot,
        ) -> YamlDataContentIdentityDto;
        fn explicit_yaml_data_snapshot_ignore_identity(
            snapshot: &ExplicitYamlDataSnapshot,
        ) -> YamlDataContentIdentityDto;

        /// Inspect selected Main and game YAML Data under one installation root.
        /// Local Ignore is neither read nor modified by this operation.
        fn installed_yaml_data_inspect(
            installation_root: &str,
            game: ExplicitYamlDataGameId,
        ) -> Box<InstalledYamlDataInspectionOperation>;
        /// Inspect typed success or failure before consuming the operation.
        fn installed_yaml_data_inspection_status(
            operation: &InstalledYamlDataInspectionOperation,
        ) -> InstalledYamlDataInspectionStatusDto;
        /// Consume a successful operation and return its immutable inspection.
        fn installed_yaml_data_inspection_take(
            operation: Box<InstalledYamlDataInspectionOperation>,
        ) -> Result<Box<InstalledYamlDataInspection>>;
        fn installed_yaml_data_inspection_game(
            inspection: &InstalledYamlDataInspection,
        ) -> ExplicitYamlDataGameId;
        fn installed_yaml_data_inspection_game_role(
            inspection: &InstalledYamlDataInspection,
        ) -> InstalledYamlDataGameRole;
        fn installed_yaml_data_inspection_main(
            inspection: &InstalledYamlDataInspection,
        ) -> InspectedYamlDataFileDto;
        fn installed_yaml_data_inspection_game_file(
            inspection: &InstalledYamlDataInspection,
        ) -> InspectedYamlDataFileDto;
        fn installed_yaml_data_inspection_diagnostics(
            inspection: &InstalledYamlDataInspection,
        ) -> Vec<InstalledYamlDataDiagnosticDto>;

        /// Load Main, game, and valid existing-or-generated Local Ignore YAML Data
        /// through the config-owned Installed YAML Data policy.
        fn installed_yaml_data_load(
            installation_root: &str,
            game: ExplicitYamlDataGameId,
            selected_game_version: &str,
        ) -> Box<InstalledYamlDataLoadOperation>;
        /// Inspect typed Ready, recovery-required, or error state before consuming the operation.
        fn installed_yaml_data_load_status(
            operation: &InstalledYamlDataLoadOperation,
        ) -> InstalledYamlDataLoadStatusDto;
        /// Consume a Ready operation and return its immutable snapshot.
        fn installed_yaml_data_load_take_snapshot(
            operation: Box<InstalledYamlDataLoadOperation>,
        ) -> Result<Box<InstalledYamlDataSnapshot>>;
        /// Consume a recovery-required operation and return its immutable recovery plan.
        fn installed_yaml_data_load_take_recovery_plan(
            operation: Box<InstalledYamlDataLoadOperation>,
        ) -> Result<Box<LocalIgnoreRecoveryPlan>>;
        fn local_ignore_recovery_plan_game(
            plan: &LocalIgnoreRecoveryPlan,
        ) -> ExplicitYamlDataGameId;
        fn local_ignore_recovery_plan_game_role(
            plan: &LocalIgnoreRecoveryPlan,
        ) -> InstalledYamlDataGameRole;
        fn local_ignore_recovery_plan_main(
            plan: &LocalIgnoreRecoveryPlan,
        ) -> InspectedYamlDataFileDto;
        fn local_ignore_recovery_plan_game_file(
            plan: &LocalIgnoreRecoveryPlan,
        ) -> InspectedYamlDataFileDto;
        fn local_ignore_recovery_plan_local_ignore_path(plan: &LocalIgnoreRecoveryPlan) -> String;
        fn local_ignore_recovery_plan_malformed_local_ignore_identity(
            plan: &LocalIgnoreRecoveryPlan,
        ) -> YamlDataContentIdentityDto;
        fn local_ignore_recovery_plan_has_default_local_ignore_identity(
            plan: &LocalIgnoreRecoveryPlan,
        ) -> bool;
        fn local_ignore_recovery_plan_default_local_ignore_identity(
            plan: &LocalIgnoreRecoveryPlan,
        ) -> YamlDataContentIdentityDto;
        fn local_ignore_recovery_plan_selected_game_version(
            plan: &LocalIgnoreRecoveryPlan,
        ) -> String;
        fn local_ignore_recovery_plan_diagnostics(
            plan: &LocalIgnoreRecoveryPlan,
        ) -> Vec<InstalledYamlDataDiagnosticDto>;
        /// Complete the retained operation with no ignore entries and no filesystem writes.
        fn local_ignore_recovery_plan_proceed_without_ignore(
            plan: Box<LocalIgnoreRecoveryPlan>,
        ) -> Box<InstalledYamlDataSnapshot>;
        /// Clone the parsed configuration view retained by the snapshot.
        fn installed_yaml_data_snapshot_yaml_data(
            snapshot: &InstalledYamlDataSnapshot,
        ) -> Box<YamlData>;
        fn installed_yaml_data_snapshot_game(
            snapshot: &InstalledYamlDataSnapshot,
        ) -> ExplicitYamlDataGameId;
        fn installed_yaml_data_snapshot_game_role(
            snapshot: &InstalledYamlDataSnapshot,
        ) -> InstalledYamlDataGameRole;
        fn installed_yaml_data_snapshot_main(
            snapshot: &InstalledYamlDataSnapshot,
        ) -> InspectedYamlDataFileDto;
        fn installed_yaml_data_snapshot_game_file(
            snapshot: &InstalledYamlDataSnapshot,
        ) -> InspectedYamlDataFileDto;
        fn installed_yaml_data_snapshot_local_ignore_state(
            snapshot: &InstalledYamlDataSnapshot,
        ) -> LocalIgnoreYamlDataState;
        fn installed_yaml_data_snapshot_local_ignore_identity(
            snapshot: &InstalledYamlDataSnapshot,
        ) -> YamlDataContentIdentityDto;
        fn installed_yaml_data_snapshot_diagnostics(
            snapshot: &InstalledYamlDataSnapshot,
        ) -> Vec<InstalledYamlDataDiagnosticDto>;

        fn save_local_yaml_paths(
            local_yaml_path: &str,
            game_root: &str,
            docs_root: &str,
        ) -> Result<()>;

        /// Schema-gated `CLASSIC_Info.version` reader for native startup
        /// paths. See [`MainYamlVersionDto`] for the success/failure
        /// contract.
        ///
        /// `bundled_yaml_dir` empty → default relative path resolved
        /// against process CWD (correct when launched next to
        /// `CLASSIC Data/`). Non-empty → explicit install-tree
        /// `CLASSIC Data/databases` directory.
        fn load_main_yaml_version(bundled_yaml_dir: &str) -> MainYamlVersionDto;

        // String getters
        fn yaml_data_classic_version(data: &YamlData) -> &str;
        fn yaml_data_classic_version_date(data: &YamlData) -> &str;
        fn yaml_data_crashgen_name_field(data: &YamlData) -> &str;
        fn yaml_data_crashgen_latest_og(data: &YamlData) -> &str;
        fn yaml_data_warn_noplugins(data: &YamlData) -> &str;
        fn yaml_data_warn_outdated(data: &YamlData) -> &str;
        fn yaml_data_xse_acronym(data: &YamlData) -> &str;
        fn yaml_data_autoscan_text(data: &YamlData) -> &str;
        fn yaml_data_game_version(data: &YamlData) -> &str;
        fn yaml_data_game_root_name_field(data: &YamlData) -> &str;

        // Accessors
        fn yaml_data_get_crashgen_name(data: &YamlData) -> String;
        fn yaml_data_get_game_root_name(data: &YamlData) -> String;
        fn yaml_data_get_crashgen_ignore(data: &YamlData) -> Vec<String>;

        // Vec<String> getters
        fn yaml_data_classic_game_hints(data: &YamlData) -> Vec<String>;
        fn yaml_data_classic_records_list(data: &YamlData) -> Vec<String>;
        fn yaml_data_crashgen_ignore_og(data: &YamlData) -> Vec<String>;
        fn yaml_data_game_ignore_plugins(data: &YamlData) -> Vec<String>;
        fn yaml_data_game_ignore_records(data: &YamlData) -> Vec<String>;
        fn yaml_data_ignore_list(data: &YamlData) -> Vec<String>;

        // IndexMap getters as paired key/value vectors
        fn yaml_data_suspects_error_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_suspects_error_values(data: &YamlData) -> Vec<String>;
        fn yaml_data_suspects_stack_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_core_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_core_values(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_core_names(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_core_gpus(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_core_count(data: &YamlData) -> usize;
        fn yaml_data_mods_freq_entries(data: &YamlData) -> Vec<YamlDataModSolutionEntry>;
        fn yaml_data_mods_conf_mod_a(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_mod_b(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_name_a(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_name_b(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_descriptions(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_fixes(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_links(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_count(data: &YamlData) -> usize;
        fn yaml_data_mods_solu_entries(data: &YamlData) -> Vec<YamlDataModSolutionEntry>;

        fn settings_cache_clear();
        fn settings_cache_size() -> usize;
        fn settings_cache_stats() -> CacheStats;
        fn reset_settings_cache_stats();

        // CXXS-07: Typed suspect-rule accessors (additive per D-08)
        fn yaml_data_suspects_error_rules(data: &YamlData) -> Vec<SuspectErrorRuleDto>;
        fn yaml_data_suspects_stack_rules_metadata(
            data: &YamlData,
        ) -> Vec<SuspectStackRuleMetadataDto>;
        fn yaml_data_suspects_stack_count_rules_for_id(
            data: &YamlData,
            rule_id: &str,
        ) -> Vec<SuspectStackCountRuleDto>;
    }
}

#[cfg(test)]
#[path = "config_tests.rs"]
mod tests;
