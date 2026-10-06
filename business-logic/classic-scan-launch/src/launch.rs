//! The one Crash Log Scan Launch operation and the request it returns.

use crate::diagnostic::{CrashLogScanLaunchDiagnostic, SavedGameSpecificValue};
use crate::error::CrashLogScanLaunchError;
use crate::overrides::{CrashLogScanLaunchOverrides, MaxConcurrency};
use classic_config_core::resolve_registry_version_info_in;
use classic_scangame_core::resolve_xse_log_for_scan_in_scopes;
use classic_scanlog_core::scan_run::contract::{Configuration, Options, Request};
use classic_scanlog_core::{
    CrashLogScanFacts, CrashLogScanSetupContext, StandardCrashLogScanSource,
    StandardUnsolvedLogsIntent, TargetedCrashLogScanSource,
};
use classic_shared_core::GameId;
use classic_shared_core::yaml::YamlFileCacheScope;
use classic_user_settings_core::{
    CrashLogScanSettings, GameSetupSettings, GameVersionSelection, UserSettings,
};
use classic_version_registry_core::VersionRegistryScope;
use std::path::{Component, Path, PathBuf};

/// Which Crash Logs a launch scans.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CrashLogScanIntent {
    /// Scan CLASSIC's normal locations under the Installation Root, plus the custom scan
    /// folder when one is saved or overridden.
    Standard,
    /// Scan exactly these user-selected files or folders, in this order.
    ///
    /// An empty list is rejected with [`CrashLogScanLaunchError::TargetedWithoutInputs`].
    Targeted(Vec<PathBuf>),
}

/// The Crash Log Scan Run request a launch produced, with the diagnostics to show beside it.
///
/// The request is ready to execute. When FCX Mode is enabled it already carries its Crash
/// Log Scan Setup Context, which [`Self::setup_context`] exposes without unpacking the
/// request.
#[derive(Debug, Clone)]
pub struct CrashLogScanLaunchRequest {
    request: Request,
    diagnostics: Vec<CrashLogScanLaunchDiagnostic>,
}

impl CrashLogScanLaunchRequest {
    /// Returns the Crash Log Scan Run request.
    #[must_use]
    pub const fn request(&self) -> &Request {
        &self.request
    }

    /// Returns the Crash Log Scan Setup Context when FCX Mode is enabled, otherwise `None`.
    #[must_use]
    pub const fn setup_context(&self) -> Option<&CrashLogScanSetupContext> {
        match &self.request {
            Request::Standard(request) => request.setup_context(),
            Request::Targeted(request) => request.setup_context(),
        }
    }

    /// Returns the launch diagnostics, in the order they were produced.
    #[must_use]
    pub fn diagnostics(&self) -> &[CrashLogScanLaunchDiagnostic] {
        &self.diagnostics
    }

    /// Consumes the launch and returns the request alone, for execution.
    #[must_use]
    pub fn into_request(self) -> Request {
        self.request
    }

    /// Consumes the launch and returns the request and its diagnostics.
    #[must_use]
    pub fn into_parts(self) -> (Request, Vec<CrashLogScanLaunchDiagnostic>) {
        (self.request, self.diagnostics)
    }
}

/// Builds the Crash Log Scan Run request for one launch.
///
/// Opens User Settings read-only under `installation_root` and merges them with
/// `overrides`, where a supplied override always wins over the saved value. It never
/// writes User Settings and never runs the scan.
///
/// - A Standard scan's base folder is always `installation_root`; the scan path override
///   and the saved custom scan folder are the explicit way to scan elsewhere.
/// - FormID database rows come from User Settings' game-aware read for the scanned game,
///   so a Fallout 4 VR scan reads the shared Fallout 4 rows.
/// - When the scanned game differs from the managed game, the saved game version (auto is
///   used), FCX Mode, custom scan folder and setup folders are not applied, and each one
///   that would otherwise have shaped this launch is reported as
///   [`CrashLogScanLaunchDiagnostic::SavedValueNotApplied`]. Overrides still win.
/// - Degraded User Settings (malformed, newer, needing migration) are not an error: the
///   request is built from the values User Settings projected for that document, and its
///   diagnostics are reported as [`CrashLogScanLaunchDiagnostic::UserSettings`].
///
/// - When FCX Mode is on, by saved setting or by override, the request carries its Crash
///   Log Scan Setup Context for either intent: the saved game and documents folders (none
///   when the scanned game differs from the managed game), the game executable, and the
///   XSE log located through
///   [`classic_scangame_core::resolve_xse_log_for_scan_in_scopes`]. Missing folders are
///   not an error; FCX setup validation reports them.
///
/// Version Registry metadata and the Game Local document are read through the process
/// default scopes; see [`prepare_launch_in_scopes`] for caller-owned scopes.
///
/// # Errors
///
/// Returns [`CrashLogScanLaunchError::TargetedWithoutInputs`] for a Targeted intent with
/// no inputs. User Settings are not opened in that case. Returns
/// [`CrashLogScanLaunchError::XseLogInspect`] when FCX Mode is on and the XSE log location
/// cannot be inspected for a reason other than absence.
pub fn prepare_launch(
    installation_root: impl AsRef<Path>,
    intent: CrashLogScanIntent,
    overrides: &CrashLogScanLaunchOverrides,
) -> Result<CrashLogScanLaunchRequest, CrashLogScanLaunchError> {
    prepare_launch_in_scopes(
        installation_root,
        intent,
        overrides,
        &VersionRegistryScope::default_scope(),
        &YamlFileCacheScope::default_scope(),
    )
}

/// Builds the Crash Log Scan Run request like [`prepare_launch`], reading Version
/// Registry metadata only from `version_registry` and the Game Local document only through
/// `yaml_file_cache`.
///
/// A binding facade that executes its runs in its own scopes passes them here, so the FCX
/// setup facts it launches with come from the same snapshot its run reads. The scopes are
/// read only when FCX Mode is on.
///
/// # Errors
///
/// The same as [`prepare_launch`].
pub fn prepare_launch_in_scopes(
    installation_root: impl AsRef<Path>,
    intent: CrashLogScanIntent,
    overrides: &CrashLogScanLaunchOverrides,
    version_registry: &VersionRegistryScope,
    yaml_file_cache: &YamlFileCacheScope,
) -> Result<CrashLogScanLaunchRequest, CrashLogScanLaunchError> {
    if matches!(&intent, CrashLogScanIntent::Targeted(inputs) if inputs.is_empty()) {
        return Err(CrashLogScanLaunchError::TargetedWithoutInputs);
    }
    let installation_root = installation_root.as_ref();
    let settings = UserSettings::open(installation_root);
    let scan = settings.crash_log_scan_settings();
    let setup = settings.game_setup_settings();

    let mut diagnostics: Vec<_> = settings
        .diagnostics()
        .iter()
        .cloned()
        .map(CrashLogScanLaunchDiagnostic::UserSettings)
        .collect();
    let game = overrides.game().unwrap_or_else(|| setup.managed_game());
    let saved = SavedForGame::resolve(scan, setup, game, &intent, overrides, &mut diagnostics);

    let configuration = configuration(installation_root, scan, game, &saved, overrides);
    // The FCX override turns FCX Mode on for any game, but the setup folders still come from
    // the game-differs-filtered saved values: a game other than the managed one gets none.
    let setup_context = if saved.fcx_mode || overrides.fcx_mode() {
        Some(setup_context(
            installation_root,
            &saved,
            &configuration,
            version_registry,
            yaml_file_cache,
        )?)
    } else {
        None
    };
    let request = match intent {
        CrashLogScanIntent::Standard => {
            let source = StandardCrashLogScanSource {
                base_directory: installation_root.to_path_buf(),
                custom_scan_directory: overrides
                    .scan_path()
                    .map(Path::to_path_buf)
                    .or_else(|| saved.custom_scan_folder.map(PathBuf::from)),
                configured_documents_root: saved.documents_root.map(PathBuf::from),
            };
            let unsolved_logs = if scan.move_unsolved_logs() {
                StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault
            } else {
                StandardUnsolvedLogsIntent::LeaveInPlace
            };
            match setup_context {
                Some(context) => {
                    Request::standard_with_fcx(configuration, source, unsolved_logs, context)
                }
                None => Request::standard(configuration, source, unsolved_logs),
            }
        }
        CrashLogScanIntent::Targeted(inputs) => {
            let source = TargetedCrashLogScanSource { inputs };
            match setup_context {
                Some(context) => Request::targeted_with_fcx(configuration, source, context),
                None => Request::targeted(configuration, source),
            }
        }
    };

    Ok(CrashLogScanLaunchRequest {
        request,
        diagnostics,
    })
}

/// The saved game-specific values this launch may use, after the game-differs rule.
///
/// For the managed game these are the saved values unchanged. For any other game they are
/// the values a launch uses with nothing saved: the saved ones belong to the managed game.
struct SavedForGame<'a> {
    game_version: GameVersionSelection,
    fcx_mode: bool,
    custom_scan_folder: Option<&'a str>,
    game_root: Option<&'a str>,
    documents_root: Option<&'a str>,
    game_executable: Option<&'a str>,
}

impl<'a> SavedForGame<'a> {
    /// Applies the game-differs rule for a launch scanning `game`.
    ///
    /// Appends one [`CrashLogScanLaunchDiagnostic::SavedValueNotApplied`] per saved value it
    /// withholds, in [`SavedGameSpecificValue`] declaration order. A value is reported only
    /// when the same launch against the managed game would have used it: an override that
    /// replaces it, or an intent that never reads it, means the game difference is not what
    /// kept it out, and reporting it would tell the user something false.
    fn resolve(
        scan: &'a CrashLogScanSettings,
        setup: &'a GameSetupSettings,
        game: GameId,
        intent: &CrashLogScanIntent,
        overrides: &CrashLogScanLaunchOverrides,
        diagnostics: &mut Vec<CrashLogScanLaunchDiagnostic>,
    ) -> Self {
        let saved = Self {
            game_version: scan.game_version_selection(),
            fcx_mode: scan.fcx_mode(),
            custom_scan_folder: scan.custom_scan_input(),
            game_root: setup.game_root(),
            documents_root: setup.documents_root(),
            game_executable: setup.game_executable(),
        };
        let managed_game = setup.managed_game();
        if game == managed_game {
            return saved;
        }

        let standard = matches!(intent, CrashLogScanIntent::Standard);
        // A Standard source reads the documents folder to find Crash Logs; FCX Mode reads
        // all three setup folders, whether it is saved on or overridden on. Either way they
        // would have shaped a managed-game launch.
        let fcx_mode = saved.fcx_mode || overrides.fcx_mode();
        let setup_folders_used = (standard && saved.documents_root.is_some())
            || (fcx_mode
                && (saved.game_root.is_some()
                    || saved.documents_root.is_some()
                    || saved.game_executable.is_some()));
        let withheld = [
            (
                SavedGameSpecificValue::GameVersion,
                overrides.game_version().is_none()
                    && saved.game_version != GameVersionSelection::Auto,
            ),
            // An FCX override turns FCX Mode on regardless, so the saved value is not what
            // the game difference kept out.
            (
                SavedGameSpecificValue::FcxMode,
                saved.fcx_mode && !overrides.fcx_mode(),
            ),
            (
                SavedGameSpecificValue::CustomScanFolder,
                standard && overrides.scan_path().is_none() && saved.custom_scan_folder.is_some(),
            ),
            (SavedGameSpecificValue::SetupFolders, setup_folders_used),
        ];
        diagnostics.extend(withheld.into_iter().filter(|(_, reported)| *reported).map(
            |(value, _)| CrashLogScanLaunchDiagnostic::SavedValueNotApplied {
                value,
                managed_game,
                target_game: game,
            },
        ));

        Self {
            game_version: GameVersionSelection::Auto,
            fcx_mode: false,
            custom_scan_folder: None,
            game_root: None,
            documents_root: None,
            game_executable: None,
        }
    }
}

/// Merges saved scan settings with the overrides into the shared run configuration.
fn configuration(
    installation_root: &Path,
    scan: &CrashLogScanSettings,
    game: GameId,
    saved: &SavedForGame<'_>,
    overrides: &CrashLogScanLaunchOverrides,
) -> Configuration {
    let game_version = overrides.game_version().unwrap_or(saved.game_version);
    let max_concurrency = overrides.max_concurrency().unwrap_or_else(|| {
        // Saved Max Concurrent Scans uses the same zero-means-adaptive convention.
        MaxConcurrency::from_count(usize::try_from(scan.max_concurrent_scans()).unwrap_or(0))
    });
    Configuration {
        installation_root: installation_root.to_path_buf(),
        game,
        game_version: game_version.as_str().to_string(),
        options: Options::new(
            scan.formid_value_lookup() || overrides.show_formid_values(),
            scan.simplify_logs() || overrides.simplify_logs(),
        ),
        scan_facts: CrashLogScanFacts {
            formid_database_paths: scan
                .formid_databases_for_game(game)
                .into_iter()
                .map(PathBuf::from)
                .collect(),
            unsolved_logs_destination: scan.unsolved_logs_destination().map(PathBuf::from),
        },
        max_concurrent: max_concurrency.limit(),
    }
}

/// Projects the saved setup folders into the run-scoped FCX setup facts for the scanned
/// game and selected version.
///
/// The folders come from `saved`, after the game-differs rule, so a launch scanning a game
/// other than the managed one has no saved folders here.
///
/// Missing folders are not refused here: unsaved folders stay `None`, and saved folders
/// that do not exist are passed through, so FCX setup validation reports both in the Crash
/// Log Scan Setup Result rather than the launch refusing to start. A missing XSE log
/// likewise leaves `xse_log_path` empty.
///
/// # Errors
///
/// Returns [`CrashLogScanLaunchError::XseLogInspect`] when the XSE log location cannot be
/// inspected for a reason other than absence.
fn setup_context(
    installation_root: &Path,
    saved: &SavedForGame<'_>,
    configuration: &Configuration,
    version_registry: &VersionRegistryScope,
    yaml_file_cache: &YamlFileCacheScope,
) -> Result<CrashLogScanSetupContext, CrashLogScanLaunchError> {
    let game_root = saved_path(saved.game_root);
    let docs_root = saved_path(saved.documents_root);
    let game_exe_path = game_executable(
        saved_path(saved.game_executable),
        game_root.as_deref(),
        &executable_name(configuration, version_registry),
    );
    let xse_log_path = resolve_xse_log_for_scan_in_scopes(
        installation_root.join("CLASSIC Data"),
        configuration.game.as_str(),
        &configuration.game_version,
        docs_root.as_deref(),
        version_registry,
        yaml_file_cache,
    )
    .map_err(CrashLogScanLaunchError::from_xse_log_error)?;
    Ok(CrashLogScanSetupContext {
        game_root,
        docs_root,
        game_exe_path,
        xse_log_path,
    })
}

/// Reads one saved setup path, trimmed; blank text means no path.
fn saved_path(value: Option<&str>) -> Option<PathBuf> {
    value
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

/// Returns the game executable fact, by the rule the GUI applied before launch moved here.
///
/// A saved executable is kept only when it exists directly inside the game folder;
/// otherwise the selected version's executable under the game folder applies. Without a
/// game folder the saved executable, if any, passes through unchanged.
fn game_executable(
    saved: Option<PathBuf>,
    game_root: Option<&Path>,
    executable_name: &str,
) -> Option<PathBuf> {
    let Some(game_root) = game_root else {
        return saved;
    };
    if let Some(saved) = saved
        && saved.exists()
        && saved
            .parent()
            .is_some_and(|parent| same_folder(parent, game_root))
    {
        return Some(saved);
    }
    Some(game_root.join(executable_name))
}

/// Compares two folders case-insensitively and separator-agnostically, ignoring `.`
/// components and trailing separators, as the GUI's cleaned-path comparison did.
fn same_folder(left: &Path, right: &Path) -> bool {
    fn parts(path: &Path) -> Vec<String> {
        path.components()
            .filter(|component| !matches!(component, Component::CurDir))
            .map(|component| component.as_os_str().to_string_lossy().to_lowercase())
            .collect()
    }
    parts(left) == parts(right)
}

/// Returns the selected version's executable file name, `<docs_name>.exe` from its
/// Version Registry entry, defaulting to `Fallout4.exe` like the GUI did.
///
/// The Fallout 4 registry root is used for every game, as the GUI did. The one addition is
/// Fallout 4 VR on `auto`: its version is VR, so it names `Fallout4VR.exe` rather than the
/// flat-screen default the GUI's `auto` lookup fell back to.
fn executable_name(
    configuration: &Configuration,
    version_registry: &VersionRegistryScope,
) -> String {
    let selected_version = if configuration.game == GameId::Fallout4VR
        && configuration.game_version == GameVersionSelection::Auto.as_str()
    {
        GameVersionSelection::Vr.as_str()
    } else {
        configuration.game_version.as_str()
    };
    resolve_registry_version_info_in(version_registry.registry(), "Fallout4", selected_version)
        .map_or_else(
            || "Fallout4.exe".to_string(),
            |info| format!("{}.exe", info.docs_name),
        )
}
