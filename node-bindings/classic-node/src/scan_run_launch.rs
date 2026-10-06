//! Crash Log Scan Launch adapter for Node.js and Bun, beside the scan-run module.
//!
//! Every merge rule lives in `classic-scan-launch`. This module converts JavaScript
//! overrides into its builder and projects the launched request into the same shapes a
//! caller would otherwise build by hand for `ScanRunRequest`.

#[cfg(test)]
#[path = "scan_run_launch_tests.rs"]
mod tests;

use crate::scan_run::{
    JsScanRunConfiguration, JsScanRunDisplayLine, JsScanRunSetupContext, JsScanRunStandardSource,
    JsScanRunTargetedSource, ScanRunRequest, display_lines_to_js,
};
use crate::shared::{JsGameId, core_to_js_game_id, js_to_core_game_id};
use crate::vocabulary::js_token;
use classic_scan_launch::{
    CrashLogScanIntent, CrashLogScanLaunchDiagnostic, CrashLogScanLaunchError,
    CrashLogScanLaunchOverrides, CrashLogScanLaunchRequest, GameVersionSelection, MaxConcurrency,
    prepare_launch,
};
use classic_scan_presentation::render_launch_diagnostics;
use classic_scanlog_core::StandardUnsolvedLogsIntent;
use classic_scanlog_core::scan_run::contract::{Configuration, Request};
use classic_vocabulary::Vocabulary;
use napi::bindgen_prelude::{JsObjectValue, ToNapiValue};
use napi::{Env, JsError, JsValue, Status};
use std::path::{Path, PathBuf};

/// Optional per-run values that win over saved User Settings for one launch.
///
/// Every field is optional. `gameVersion` takes a User Settings game-version token
/// (`auto`, `Original`, `NextGen`, `AnniversaryEdition`, `VR`). `maxConcurrent` zero
/// explicitly requests adaptive concurrency, which overrides a saved limit.
/// `showFormidValues`, `simplifyLogs` and `fcxMode` are supplied-as-on: `true` turns the
/// option on for this run; `false` or absence keeps the saved value.
#[napi(object)]
#[derive(Default)]
pub struct JsScanRunLaunchOverrides {
    pub game: Option<JsGameId>,
    pub game_version: Option<String>,
    pub scan_path: Option<String>,
    pub max_concurrent: Option<u32>,
    pub show_formid_values: Option<bool>,
    pub simplify_logs: Option<bool>,
    pub fcx_mode: Option<bool>,
}

/// One non-fatal launch diagnostic; the launch still produced a scannable request.
#[napi(object)]
pub struct JsScanRunLaunchDiagnostic {
    /// Which launch rule produced it, as a camelCase Vocabulary Token.
    #[napi(
        ts_type = "'userSettings' | 'gameVersionNotApplied' | 'fcxModeNotApplied' | 'customScanFolderNotApplied' | 'setupFoldersNotApplied'"
    )]
    pub kind: String,
    /// Stable machine-readable code (the User Settings code for `userSettings`, the
    /// kind's snake_case token otherwise).
    pub code: String,
    /// Human-readable context. Prose; branch on `kind` and `code` instead.
    pub message: String,
}

/// The Crash Log Scan Run request a launch built, with its launch diagnostics.
///
/// The read-only getters show exactly what the launch decided; `request()` returns an
/// executable `ScanRunRequest` for `scanRunExecute`.
#[napi]
pub struct ScanRunLaunch {
    inner: CrashLogScanLaunchRequest,
}

#[napi]
impl ScanRunLaunch {
    /// Launches a Standard Crash Log Scan from saved User Settings and `overrides`.
    ///
    /// Opens User Settings under `installationRoot` read-only and never writes them; the
    /// Standard base folder is always `installationRoot`. Degraded User Settings still
    /// produce a launch, with their diagnostics. Throws `InvalidArg` for an unrepresentable
    /// input (a blank root or scan path, or an unknown game-version token). With FCX Mode
    /// on, `setupContext` carries the game folder, documents folder, game executable and
    /// XSE log; when the XSE log location cannot be inspected (not mere absence) it throws
    /// the typed launch error whose `code` and `kind` are `xse_log_inspect`.
    #[napi(factory)]
    pub fn standard(
        env: Env,
        installation_root: String,
        overrides: Option<JsScanRunLaunchOverrides>,
    ) -> napi::Result<Self> {
        launch(
            env,
            installation_root,
            CrashLogScanIntent::Standard,
            overrides,
        )
    }

    /// Launches a Targeted Crash Log Scan of exactly `inputs`, in order.
    ///
    /// An empty `inputs` list throws the typed launch error whose `code` and `kind` are
    /// `targeted_without_inputs`. Otherwise behaves like `standard`.
    #[napi(factory)]
    pub fn targeted(
        env: Env,
        installation_root: String,
        inputs: Vec<String>,
        overrides: Option<JsScanRunLaunchOverrides>,
    ) -> napi::Result<Self> {
        launch(
            env,
            installation_root,
            CrashLogScanIntent::Targeted(inputs.into_iter().map(PathBuf::from).collect()),
            overrides,
        )
    }

    /// Returns which Crash Logs the request scans.
    #[napi(getter, ts_return_type = "'standard' | 'targeted'")]
    pub fn intent(&self) -> &'static str {
        match self.inner.request() {
            Request::Standard(_) => "standard",
            Request::Targeted(_) => "targeted",
        }
    }

    /// Returns the run configuration the launch built.
    #[napi(getter)]
    pub fn configuration(&self) -> JsScanRunConfiguration {
        configuration_to_js(self.inner.request().configuration())
    }

    /// Returns the Standard discovery source, or `null` for a Targeted request.
    #[napi(getter)]
    pub fn standard_source(&self) -> Option<JsScanRunStandardSource> {
        match self.inner.request() {
            Request::Standard(request) => {
                let source = request.source();
                Some(JsScanRunStandardSource {
                    base_directory: path_text(&source.base_directory),
                    custom_scan_directory: source.custom_scan_directory.as_deref().map(path_text),
                    configured_documents_root: source
                        .configured_documents_root
                        .as_deref()
                        .map(path_text),
                })
            }
            Request::Targeted(_) => None,
        }
    }

    /// Returns the Standard Unsolved Logs intent, or `null` for a Targeted request.
    #[napi(
        getter,
        ts_return_type = "'leaveInPlace' | 'moveToConfiguredOrDefault' | 'moveToCustom' | null"
    )]
    pub fn unsolved_logs(&self) -> Option<&'static str> {
        match self.inner.request() {
            Request::Standard(request) => Some(match request.unsolved_logs() {
                StandardUnsolvedLogsIntent::LeaveInPlace => "leaveInPlace",
                StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault => {
                    "moveToConfiguredOrDefault"
                }
                StandardUnsolvedLogsIntent::MoveToCustom(_) => "moveToCustom",
            }),
            Request::Targeted(_) => None,
        }
    }

    /// Returns the Targeted discovery source, or `null` for a Standard request.
    #[napi(getter)]
    pub fn targeted_source(&self) -> Option<JsScanRunTargetedSource> {
        match self.inner.request() {
            Request::Standard(_) => None,
            Request::Targeted(request) => Some(JsScanRunTargetedSource {
                inputs: request
                    .source()
                    .inputs
                    .iter()
                    .map(|path| path_text(path))
                    .collect(),
            }),
        }
    }

    /// Returns whether the request enables FCX Mode.
    #[napi(getter)]
    pub fn fcx_enabled(&self) -> bool {
        self.inner.setup_context().is_some()
    }

    /// Returns the Crash Log Scan Setup Context when FCX Mode is enabled, otherwise `null`.
    #[napi(getter)]
    pub fn setup_context(&self) -> Option<JsScanRunSetupContext> {
        self.inner
            .setup_context()
            .map(|context| JsScanRunSetupContext {
                game_root: context.game_root.as_deref().map(path_text),
                docs_root: context.docs_root.as_deref().map(path_text),
                game_exe_path: context.game_exe_path.as_deref().map(path_text),
                xse_log_path: context.xse_log_path.as_deref().map(path_text),
            })
    }

    /// Returns the launch diagnostics, in the order they were produced.
    #[napi(getter)]
    pub fn diagnostics(&self) -> Vec<JsScanRunLaunchDiagnostic> {
        self.inner
            .diagnostics()
            .iter()
            .map(diagnostic_to_js)
            .collect()
    }

    /// Returns the launch diagnostics rendered as Display Content, one line per
    /// diagnostic in the same order. Show these rather than phrasing `diagnostics` in
    /// JavaScript.
    #[napi(getter)]
    pub fn display_lines(&self) -> Vec<JsScanRunDisplayLine> {
        display_lines_to_js(&render_launch_diagnostics(self.inner.diagnostics()))
    }

    /// Returns an executable copy of the launched request.
    #[napi]
    pub fn request(&self) -> ScanRunRequest {
        ScanRunRequest::from_core(self.inner.request().clone())
    }
}

/// Converts JavaScript inputs and runs the one Rust launch operation.
fn launch(
    env: Env,
    installation_root: String,
    intent: CrashLogScanIntent,
    overrides: Option<JsScanRunLaunchOverrides>,
) -> napi::Result<ScanRunLaunch> {
    let installation_root = required_path(installation_root, "installationRoot")?;
    let overrides = overrides_to_core(overrides.unwrap_or_default())?;
    prepare_launch(installation_root, intent, &overrides)
        .map(|inner| ScanRunLaunch { inner })
        .map_err(|error| launch_error_to_napi(env, &error))
}

/// Converts optional JavaScript overrides into the core override builder.
fn overrides_to_core(value: JsScanRunLaunchOverrides) -> napi::Result<CrashLogScanLaunchOverrides> {
    let mut overrides = CrashLogScanLaunchOverrides::new();
    if let Some(game) = value.game {
        overrides = overrides.with_game(js_to_core_game_id(&game));
    }
    if let Some(game_version) = value.game_version {
        let selection = GameVersionSelection::parse(&game_version).ok_or_else(|| {
            napi::Error::new(
                Status::InvalidArg,
                format!("unsupported gameVersion override: {game_version}"),
            )
        })?;
        overrides = overrides.with_game_version(selection);
    }
    if let Some(scan_path) = value.scan_path {
        overrides = overrides.with_scan_path(required_path(scan_path, "scanPath")?);
    }
    if let Some(max_concurrent) = value.max_concurrent {
        overrides = overrides.with_max_concurrency(MaxConcurrency::from_count(
            usize::try_from(max_concurrent).unwrap_or(usize::MAX),
        ));
    }
    if value.show_formid_values == Some(true) {
        overrides = overrides.with_show_formid_values();
    }
    if value.simplify_logs == Some(true) {
        overrides = overrides.with_simplify_logs();
    }
    if value.fcx_mode == Some(true) {
        overrides = overrides.with_fcx_mode();
    }
    Ok(overrides)
}

/// Builds a JavaScript error whose `code` and `kind` are the frozen launch error token.
fn launch_error_to_napi(env: Env, error: &CrashLogScanLaunchError) -> napi::Error {
    let code = error.kind().as_str();
    let message = error.to_string();
    let raw_error = JsError::from(napi::Error::new(code, message.clone())).into_unknown(env);
    let Ok(mut object) = raw_error.coerce_to_object() else {
        return napi::Error::new(Status::GenericFailure, message);
    };
    // `kind` mirrors the resume errors' shape, so one consumer check covers both.
    if object.set_named_property("kind", code).is_err() {
        return napi::Error::new(Status::GenericFailure, message);
    }
    object
        .into_unknown(&env)
        .map(napi::Error::from)
        .unwrap_or_else(|_| napi::Error::new(Status::GenericFailure, message))
}

/// Projects the core run configuration into the request-construction object.
fn configuration_to_js(configuration: &Configuration) -> JsScanRunConfiguration {
    JsScanRunConfiguration {
        installation_root: path_text(&configuration.installation_root),
        game: core_to_js_game_id(&configuration.game),
        game_version: configuration.game_version.clone(),
        show_formid_values: configuration.options.show_formid_values,
        simplify_logs: configuration.options.simplify_logs,
        formid_database_paths: configuration
            .scan_facts
            .formid_database_paths
            .iter()
            .map(|path| path_text(path))
            .collect(),
        unsolved_logs_destination: configuration
            .scan_facts
            .unsolved_logs_destination
            .as_deref()
            .map(path_text),
        // The launch never produces a limit above u32 in practice; saturate rather than wrap.
        max_concurrent: configuration
            .max_concurrent
            .map(|limit| u32::try_from(limit).unwrap_or(u32::MAX)),
    }
}

/// Projects one launch diagnostic.
fn diagnostic_to_js(diagnostic: &CrashLogScanLaunchDiagnostic) -> JsScanRunLaunchDiagnostic {
    JsScanRunLaunchDiagnostic {
        kind: js_token(diagnostic.kind().as_str()),
        code: diagnostic.code().to_string(),
        message: diagnostic.message().to_string(),
    }
}

/// Rejects blank path text, which cannot name a folder.
fn required_path(value: String, label: &str) -> napi::Result<PathBuf> {
    if value.trim().is_empty() {
        return Err(napi::Error::new(
            Status::InvalidArg,
            format!("{label} must not be blank"),
        ));
    }
    Ok(PathBuf::from(value))
}

/// Renders a path for JavaScript without failing on non-UTF-8 components.
fn path_text(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}
