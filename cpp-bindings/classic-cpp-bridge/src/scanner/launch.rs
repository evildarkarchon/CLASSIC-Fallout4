//! Crash Log Scan Launch adapter for the CXX scanner bridge.
//!
//! Every merge rule lives in `classic-scan-launch`; this module only converts bridge
//! primitives into its overrides and projects the launched request into the same DTOs a
//! caller would otherwise have built by hand.

use super::contract::{ScanRunRequest, required_path, scan_run_game_id_to_core};
use super::ffi;
use classic_scan_launch::{
    CrashLogScanIntent, CrashLogScanLaunchDiagnostic, CrashLogScanLaunchDiagnosticKind,
    CrashLogScanLaunchError, CrashLogScanLaunchErrorKind, CrashLogScanLaunchOverrides,
    CrashLogScanLaunchRequest, GameVersionSelection, MaxConcurrency, prepare_launch,
};
use classic_scanlog_core::scan_run::contract::{Configuration, Request};
use classic_scanlog_core::{
    CrashLogScanSetupContext, StandardCrashLogScanSource, StandardUnsolvedLogsIntent,
};
use classic_shared_core::GameId;
use classic_vocabulary::Vocabulary;
use std::path::{Path, PathBuf};

/// Opaque outcome of one Crash Log Scan Launch: the launched request or its typed error.
pub(crate) struct ScanRunLaunch {
    outcome: Result<CrashLogScanLaunchRequest, CrashLogScanLaunchError>,
}

/// Launches a Standard Crash Log Scan.
///
/// Returns an error string only when a bridge input cannot be represented; typed launch
/// errors stay inside the returned handle.
pub(crate) fn scan_run_launch_standard(
    installation_root: &str,
    overrides: &ffi::ScanRunLaunchOverridesDto,
) -> Result<Box<ScanRunLaunch>, String> {
    launch(installation_root, CrashLogScanIntent::Standard, overrides)
}

/// Launches a Targeted Crash Log Scan of exactly `inputs`.
///
/// An empty list is passed through so Rust reports the typed `TargetedWithoutInputs` error.
// The bridge signature is `&Vec<String>` because cxx exposes `rust::Vec` by that type; the
// `ptr_arg` suggestion of `&[String]` cannot cross the bridge.
#[allow(clippy::ptr_arg)]
pub(crate) fn scan_run_launch_targeted(
    installation_root: &str,
    inputs: &Vec<String>,
    overrides: &ffi::ScanRunLaunchOverridesDto,
) -> Result<Box<ScanRunLaunch>, String> {
    launch(
        installation_root,
        CrashLogScanIntent::Targeted(inputs.iter().map(PathBuf::from).collect()),
        overrides,
    )
}

/// Returns the typed launch error, or a `has_error == false` placeholder.
pub(crate) fn scan_run_launch_error(launch: &ScanRunLaunch) -> ffi::ScanRunLaunchErrorDto {
    match &launch.outcome {
        Ok(_) => ffi::ScanRunLaunchErrorDto {
            has_error: false,
            // CXX shared structs cannot omit nested records; `has_error` is authoritative.
            kind: ffi::ScanRunLaunchErrorKind::TargetedWithoutInputs,
            message: String::new(),
        },
        Err(error) => ffi::ScanRunLaunchErrorDto {
            has_error: true,
            kind: map_error_kind(error.kind()),
            message: error.to_string(),
        },
    }
}

/// Projects the launched request and diagnostics; fails when the launch itself failed.
pub(crate) fn scan_run_launch_view(
    launch: &ScanRunLaunch,
) -> Result<ffi::ScanRunLaunchRequestDto, String> {
    launched(launch).map(launch_view)
}

/// Returns an executable copy of the launched request.
pub(crate) fn scan_run_launch_request(
    launch: &ScanRunLaunch,
) -> Result<Box<ScanRunRequest>, String> {
    launched(launch).map(|launched| Box::new(ScanRunRequest::from_core(launched.request().clone())))
}

/// Converts bridge inputs and runs the one Rust launch operation.
fn launch(
    installation_root: &str,
    intent: CrashLogScanIntent,
    overrides: &ffi::ScanRunLaunchOverridesDto,
) -> Result<Box<ScanRunLaunch>, String> {
    let installation_root = required_path(installation_root, "installation_root")?;
    let overrides = overrides_to_core(overrides)?;
    Ok(Box::new(ScanRunLaunch {
        outcome: prepare_launch(installation_root, intent, &overrides),
    }))
}

/// Returns the launched request, or the launch error as an exception message.
fn launched(launch: &ScanRunLaunch) -> Result<&CrashLogScanLaunchRequest, String> {
    launch.outcome.as_ref().map_err(|error| {
        format!(
            "Crash Log Scan Launch failed ({}): {error}",
            error.kind().as_str()
        )
    })
}

/// Converts presence-flagged bridge overrides into the core override builder.
fn overrides_to_core(
    value: &ffi::ScanRunLaunchOverridesDto,
) -> Result<CrashLogScanLaunchOverrides, String> {
    let mut overrides = CrashLogScanLaunchOverrides::new();
    if value.has_game {
        overrides = overrides.with_game(scan_run_game_id_to_core(value.game)?);
    }
    if value.has_game_version {
        let selection = GameVersionSelection::parse(&value.game_version)
            .ok_or_else(|| format!("unsupported game_version override: {}", value.game_version))?;
        overrides = overrides.with_game_version(selection);
    }
    if value.has_scan_path {
        overrides = overrides.with_scan_path(required_path(&value.scan_path, "scan_path")?);
    }
    if value.has_max_concurrent {
        overrides =
            overrides.with_max_concurrency(MaxConcurrency::from_count(value.max_concurrent));
    }
    if value.show_formid_values {
        overrides = overrides.with_show_formid_values();
    }
    if value.simplify_logs {
        overrides = overrides.with_simplify_logs();
    }
    Ok(overrides)
}

/// Projects one launched request into the request-construction DTOs plus diagnostics.
fn launch_view(launched: &CrashLogScanLaunchRequest) -> ffi::ScanRunLaunchRequestDto {
    let request = launched.request();
    let (intent, standard_source, unsolved_logs, targeted_inputs, fcx_enabled) = match request {
        Request::Standard(standard) => (
            ffi::ScanRunLaunchIntent::Standard,
            Some(standard.source()),
            Some(standard.unsolved_logs()),
            Vec::new(),
            standard.fcx_enabled(),
        ),
        Request::Targeted(targeted) => (
            ffi::ScanRunLaunchIntent::Targeted,
            None,
            None,
            targeted
                .source()
                .inputs
                .iter()
                .map(|path| path_text(path))
                .collect(),
            targeted.fcx_enabled(),
        ),
    };
    let (unsolved_logs, unsolved_logs_custom_destination) = match unsolved_logs {
        Some(StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault) => (
            ffi::ScanRunLaunchUnsolvedLogs::MoveToConfiguredOrDefault,
            String::new(),
        ),
        Some(StandardUnsolvedLogsIntent::MoveToCustom(destination)) => (
            ffi::ScanRunLaunchUnsolvedLogs::MoveToCustom,
            path_text(destination),
        ),
        // A Targeted request has no Unsolved Logs capability; the flag is a placeholder.
        Some(StandardUnsolvedLogsIntent::LeaveInPlace) | None => {
            (ffi::ScanRunLaunchUnsolvedLogs::LeaveInPlace, String::new())
        }
    };
    ffi::ScanRunLaunchRequestDto {
        intent,
        configuration: configuration_to_dto(request.configuration()),
        standard_source: standard_source_to_dto(standard_source),
        unsolved_logs,
        unsolved_logs_custom_destination,
        targeted_source: ffi::ScanRunTargetedSourceDto {
            inputs: targeted_inputs,
        },
        fcx_enabled,
        setup_context: setup_context_to_dto(launched.setup_context()),
        diagnostics: launched
            .diagnostics()
            .iter()
            .map(diagnostic_to_dto)
            .collect(),
    }
}

/// Projects the core run configuration into the bridge configuration DTO.
fn configuration_to_dto(configuration: &Configuration) -> ffi::ScanRunConfigurationDto {
    let (has_destination, destination) = optional_path_text(
        configuration
            .scan_facts
            .unsolved_logs_destination
            .as_deref(),
    );
    ffi::ScanRunConfigurationDto {
        installation_root: path_text(&configuration.installation_root),
        game: game_to_dto(configuration.game),
        game_version: configuration.game_version.clone(),
        show_formid_values: configuration.options.show_formid_values,
        simplify_logs: configuration.options.simplify_logs,
        formid_database_paths: configuration
            .scan_facts
            .formid_database_paths
            .iter()
            .map(|path| path_text(path))
            .collect(),
        has_configured_unsolved_logs_destination: has_destination,
        configured_unsolved_logs_destination: destination,
        has_max_concurrent: configuration.max_concurrent.is_some(),
        max_concurrent: configuration.max_concurrent.unwrap_or(0),
    }
}

/// Projects a Standard source, or an empty placeholder for a Targeted request.
fn standard_source_to_dto(
    source: Option<&StandardCrashLogScanSource>,
) -> ffi::ScanRunStandardSourceDto {
    let (has_custom, custom) =
        optional_path_text(source.and_then(|source| source.custom_scan_directory.as_deref()));
    let (has_documents, documents) =
        optional_path_text(source.and_then(|source| source.configured_documents_root.as_deref()));
    ffi::ScanRunStandardSourceDto {
        base_directory: source
            .map(|source| path_text(&source.base_directory))
            .unwrap_or_default(),
        has_custom_scan_directory: has_custom,
        custom_scan_directory: custom,
        has_configured_documents_root: has_documents,
        configured_documents_root: documents,
    }
}

/// Projects FCX setup facts, or an all-absent placeholder when FCX Mode is off.
fn setup_context_to_dto(context: Option<&CrashLogScanSetupContext>) -> ffi::ScanRunSetupContextDto {
    let field = |select: fn(&CrashLogScanSetupContext) -> Option<&Path>| {
        optional_path_text(context.and_then(select))
    };
    let (has_game_root, game_root) = field(|context| context.game_root.as_deref());
    let (has_docs_root, docs_root) = field(|context| context.docs_root.as_deref());
    let (has_game_exe_path, game_exe_path) = field(|context| context.game_exe_path.as_deref());
    let (has_xse_log_path, xse_log_path) = field(|context| context.xse_log_path.as_deref());
    ffi::ScanRunSetupContextDto {
        has_game_root,
        game_root,
        has_docs_root,
        docs_root,
        has_game_exe_path,
        game_exe_path,
        has_xse_log_path,
        xse_log_path,
    }
}

/// Projects one launch diagnostic.
fn diagnostic_to_dto(diagnostic: &CrashLogScanLaunchDiagnostic) -> ffi::ScanRunLaunchDiagnosticDto {
    ffi::ScanRunLaunchDiagnosticDto {
        kind: map_diagnostic_kind(diagnostic.kind()),
        code: diagnostic.code().to_string(),
        message: diagnostic.message().to_string(),
    }
}

/// Maps the core diagnostic kind onto the scanner-local bridge enum.
fn map_diagnostic_kind(kind: CrashLogScanLaunchDiagnosticKind) -> ffi::ScanRunLaunchDiagnosticKind {
    match kind {
        CrashLogScanLaunchDiagnosticKind::UserSettings => {
            ffi::ScanRunLaunchDiagnosticKind::UserSettings
        }
    }
}

/// Maps the core error kind onto the scanner-local bridge enum.
fn map_error_kind(kind: CrashLogScanLaunchErrorKind) -> ffi::ScanRunLaunchErrorKind {
    match kind {
        CrashLogScanLaunchErrorKind::TargetedWithoutInputs => {
            ffi::ScanRunLaunchErrorKind::TargetedWithoutInputs
        }
    }
}

/// Maps the shared game identity onto the scanner-local bridge enum.
fn game_to_dto(game: GameId) -> ffi::ScanRunGameId {
    match game {
        GameId::Fallout4 => ffi::ScanRunGameId::Fallout4,
        GameId::Fallout4VR => ffi::ScanRunGameId::Fallout4VR,
        GameId::Skyrim => ffi::ScanRunGameId::Skyrim,
        GameId::Starfield => ffi::ScanRunGameId::Starfield,
    }
}

/// Renders a path for C++ without failing on non-UTF-8 components.
fn path_text(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

/// Splits an optional path into the bridge's presence flag and text.
fn optional_path_text(path: Option<&Path>) -> (bool, String) {
    path.map_or((false, String::new()), |path| (true, path_text(path)))
}

// Keep the repository's required sibling-test declaration intact under rustfmt.
#[rustfmt::skip]
#[cfg(test)] #[path = "launch_tests.rs"] mod tests;
