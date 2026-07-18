//! Installed YAML Data inspection for Node and Bun callers.

use crate::shared::{JsGameId, core_to_js_game_id, js_to_core_game_id};
use classic_config_core::{
    GameDataRole, InspectedYamlDataFile as CoreInspectedYamlDataFile,
    InstalledYamlDataDiagnostic as CoreInstalledYamlDataDiagnostic,
    InstalledYamlDataDiagnosticKind as CoreInstalledYamlDataDiagnosticKind,
    InstalledYamlDataInspection as CoreInstalledYamlDataInspection,
    InstalledYamlDataInspectionError as CoreInstalledYamlDataInspectionError,
    InstalledYamlDataInspectionRequest as CoreInstalledYamlDataInspectionRequest,
    InstalledYamlDataProvenance as CoreInstalledYamlDataProvenance,
    InstalledYamlDataRole as CoreInstalledYamlDataRole,
    inspect_installed_yaml_data as core_inspect_installed_yaml_data,
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
}

/// Registered game-data role selected for Installed YAML Data.
#[napi(string_enum)]
pub enum JsInstalledYamlDataGameRole {
    /// Shared Fallout 4 data used for flat-screen and VR identities.
    Fallout4,
}

/// Structured attribution for one cache-resolution or candidate-rejection event.
#[napi(object)]
pub struct JsInstalledYamlDataDiagnostic {
    /// Affected file role, absent for installation-wide diagnostics.
    pub role: Option<JsInstalledYamlDataRole>,
    /// Rejected candidate provenance, absent when no candidate was resolved.
    pub candidate: Option<JsInstalledYamlDataProvenance>,
    /// Candidate path when the diagnostic is path-attributable.
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

fn inspected_file_to_js(file: &CoreInspectedYamlDataFile) -> JsInspectedYamlDataFile {
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

fn diagnostic_to_js(diagnostic: &CoreInstalledYamlDataDiagnostic) -> JsInstalledYamlDataDiagnostic {
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
    let message = error.to_string();
    let raw_error = JsError::from(napi::Error::new(code, message.clone())).into_unknown(env);
    let Ok(mut object) = raw_error.coerce_to_object() else {
        return base_inspection_error(env, code, message);
    };
    if let Some(role) = role
        && object
            .set_named_property("yamlRole", role_name(role))
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
