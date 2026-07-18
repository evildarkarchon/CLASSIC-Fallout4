//! Deterministic explicit YAML Data loading for Node and Bun tooling callers.

use crate::config::YamlData;
use crate::shared::{JsGameId, core_to_js_game_id, js_to_core_game_id};
use classic_config_core::{
    ExplicitYamlDataLoadError, ExplicitYamlDataRequest, ExplicitYamlDataRole,
    ExplicitYamlDataSnapshot as CoreExplicitYamlDataSnapshot, GameDataRole,
    YamlDataContentIdentity, load_explicit_yaml_data as core_load_explicit_yaml_data,
};
use napi::bindgen_prelude::*;
use std::path::PathBuf;

/// Exact caller-selected paths for deterministic YAML Data loading.
#[napi(object)]
pub struct JsExplicitYamlDataPaths {
    /// Exact Main YAML Data file.
    pub main_path: String,
    /// Exact game YAML Data file.
    pub game_path: String,
    /// Exact Local Ignore YAML Data file.
    pub ignore_path: String,
}

/// Content identity derived from the exact bytes retained by a snapshot.
#[napi(object)]
pub struct JsYamlDataContentIdentity {
    /// Lowercase hexadecimal SHA-256 digest.
    pub sha256: String,
    /// Exact retained byte length.
    pub byte_len: i64,
}

/// Registered game-data role selected for an explicit snapshot.
#[napi(string_enum)]
pub enum JsExplicitYamlDataGameRole {
    /// Shared Fallout 4 data used for flat-screen and VR identities.
    Fallout4,
}

/// Immutable deterministic explicit YAML Data snapshot.
#[napi]
pub struct ExplicitYamlDataSnapshot {
    inner: CoreExplicitYamlDataSnapshot,
}

#[napi]
impl ExplicitYamlDataSnapshot {
    /// Returns the caller's typed game identity.
    #[napi(getter)]
    pub fn game(&self) -> JsGameId {
        core_to_js_game_id(&self.inner.game())
    }

    /// Returns the registered game-data role used for parsing and validation.
    #[napi(getter)]
    pub fn game_data_role(&self) -> JsExplicitYamlDataGameRole {
        match self.inner.game_data_role() {
            GameDataRole::Fallout4 => JsExplicitYamlDataGameRole::Fallout4,
        }
    }

    /// Returns a cloned immutable view of the parsed YAML Data.
    #[napi(getter)]
    pub fn yaml_data(&self) -> YamlData {
        YamlData::from_core(self.inner.yaml_data().clone())
    }

    /// Returns the exact retained Main-file identity.
    #[napi(getter)]
    pub fn main_identity(&self) -> JsYamlDataContentIdentity {
        content_identity_to_js(self.inner.main_identity())
    }

    /// Returns the exact retained game-file identity.
    #[napi(getter)]
    pub fn game_identity(&self) -> JsYamlDataContentIdentity {
        content_identity_to_js(self.inner.game_identity())
    }

    /// Returns the exact retained Local Ignore-file identity.
    #[napi(getter)]
    pub fn ignore_identity(&self) -> JsYamlDataContentIdentity {
        content_identity_to_js(self.inner.ignore_identity())
    }
}

/// Starts one deterministic explicit YAML Data load on the shared runtime.
///
/// The operation reads exactly the supplied files and never consults or mutates
/// installation, cache, generation, backup, or fallback state.
///
/// @param paths - Exact Main, game, and Local Ignore file paths.
/// @param game - Typed game identity; Fallout 4 VR selects the Fallout 4 role.
/// @param selectedGameVersion - Existing Version Registry selection mode.
/// @throws an error with stable `code` and optional `yamlRole` / `path` fields.
#[napi(ts_return_type = "Promise<ExplicitYamlDataSnapshot>")]
pub fn load_explicit_yaml_data(
    paths: JsExplicitYamlDataPaths,
    game: JsGameId,
    selected_game_version: String,
) -> AsyncTask<ExplicitYamlDataLoadTask> {
    AsyncTask::new(ExplicitYamlDataLoadTask {
        request: Some(ExplicitYamlDataRequest {
            main_path: PathBuf::from(paths.main_path),
            game_path: PathBuf::from(paths.game_path),
            ignore_path: PathBuf::from(paths.ignore_path),
            game: js_to_core_game_id(&game),
            selected_game_version,
        }),
    })
}

/// Background task that delegates explicit loading to the shared Rust runtime.
pub struct ExplicitYamlDataLoadTask {
    request: Option<ExplicitYamlDataRequest>,
}

/// Core result retained until JavaScript-thread resolution.
pub enum ExplicitYamlDataTaskOutput {
    /// Successfully loaded immutable snapshot.
    Success(Box<CoreExplicitYamlDataSnapshot>),
    /// Typed core failure awaiting JavaScript error projection.
    Failure(ExplicitYamlDataLoadError),
}

impl Task for ExplicitYamlDataLoadTask {
    type Output = ExplicitYamlDataTaskOutput;
    type JsValue = ExplicitYamlDataSnapshot;

    /// Executes the core future on CLASSIC's process-wide Tokio runtime.
    fn compute(&mut self) -> Result<Self::Output> {
        let request = self
            .request
            .take()
            .ok_or_else(|| napi::Error::from_reason("explicit YAML Data task already ran"))?;
        Ok(
            match classic_shared_core::get_runtime().block_on(core_load_explicit_yaml_data(request))
            {
                Ok(snapshot) => ExplicitYamlDataTaskOutput::Success(Box::new(snapshot)),
                Err(error) => ExplicitYamlDataTaskOutput::Failure(error),
            },
        )
    }

    /// Resolves a snapshot or rejects with stable typed error metadata.
    fn resolve(&mut self, env: Env, output: Self::Output) -> Result<Self::JsValue> {
        match output {
            ExplicitYamlDataTaskOutput::Success(inner) => {
                Ok(ExplicitYamlDataSnapshot { inner: *inner })
            }
            ExplicitYamlDataTaskOutput::Failure(error) => {
                Err(explicit_yaml_data_error_to_napi(env, error))
            }
        }
    }
}

fn content_identity_to_js(identity: &YamlDataContentIdentity) -> JsYamlDataContentIdentity {
    JsYamlDataContentIdentity {
        sha256: identity.sha256_hex(),
        byte_len: identity.byte_len() as i64,
    }
}

fn explicit_yaml_data_role_name(role: ExplicitYamlDataRole) -> &'static str {
    match role {
        ExplicitYamlDataRole::Main => "main",
        ExplicitYamlDataRole::Game => "game",
        ExplicitYamlDataRole::LocalIgnore => "local_ignore",
    }
}

fn explicit_yaml_data_error_to_napi(env: Env, error: ExplicitYamlDataLoadError) -> napi::Error {
    let (code, role, path) = match &error {
        ExplicitYamlDataLoadError::UnsupportedGame { .. } => ("unsupported_game", None, None),
        ExplicitYamlDataLoadError::Read { role, path, .. } => {
            ("read", Some(*role), Some(path.clone()))
        }
        ExplicitYamlDataLoadError::InvalidUtf8 { role, path, .. } => {
            ("invalid_utf8", Some(*role), Some(path.clone()))
        }
        ExplicitYamlDataLoadError::Parse { role, path, .. } => {
            ("parse", Some(*role), Some(path.clone()))
        }
        ExplicitYamlDataLoadError::InvalidRoleData { role, path, .. } => {
            ("invalid_role_data", Some(*role), Some(path.clone()))
        }
    };
    let message = error.to_string();
    let raw_error = JsError::from(napi::Error::new(code, message.clone())).into_unknown(env);
    let Ok(mut object) = raw_error.coerce_to_object() else {
        return base_explicit_yaml_data_error(env, code, message);
    };
    if let Some(role) = role
        && object
            .set_named_property("yamlRole", explicit_yaml_data_role_name(role))
            .is_err()
    {
        return base_explicit_yaml_data_error(env, code, message);
    }
    if let Some(path) = path
        && object
            .set_named_property("path", path.to_string_lossy().into_owned())
            .is_err()
    {
        return base_explicit_yaml_data_error(env, code, message);
    }
    object
        .into_unknown(&env)
        .map(napi::Error::from)
        .unwrap_or_else(|_| base_explicit_yaml_data_error(env, code, message))
}

fn base_explicit_yaml_data_error(env: Env, code: &str, message: String) -> napi::Error {
    napi::Error::from(JsError::from(napi::Error::new(code, message)).into_unknown(env))
}
