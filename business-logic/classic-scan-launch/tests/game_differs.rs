//! The game-differs rule: one game's saved settings never leak into another game's scan.
//!
//! When the target game differs from the managed game, the saved game version, FCX Mode,
//! custom scan folder and setup folders are not applied, and each one that would otherwise
//! have shaped the launch is reported as a typed diagnostic. Every case writes a User
//! Settings document into a temporary Installation Root and observes only the launch request
//! and its diagnostics.

use classic_scan_launch::{
    CrashLogScanIntent, CrashLogScanLaunchDiagnostic, CrashLogScanLaunchDiagnosticKind,
    CrashLogScanLaunchOverrides, CrashLogScanLaunchRequest, GameVersionSelection,
    SavedGameSpecificValue, prepare_launch,
};
use classic_scanlog_core::scan_run::contract::Request;
use classic_shared_core::GameId;
use std::path::{Path, PathBuf};
use tempfile::TempDir;

/// Quotes an absolute path as a single-quoted YAML scalar so backslashes stay literal.
fn yaml_path(path: &Path) -> String {
    format!("'{}'", path.display().to_string().replace('\'', "''"))
}

/// A Fallout 4 Installation Root whose User Settings save every game-specific value.
struct SavedFallout4 {
    root: TempDir,
    custom: PathBuf,
    game: PathBuf,
    documents: PathBuf,
    executable: PathBuf,
}

/// Saves a game version, FCX Mode, a custom scan folder and all three setup folders for a
/// managed Fallout 4.
fn saved_fallout4() -> SavedFallout4 {
    let root = tempfile::tempdir().unwrap();
    let custom = root.path().join("Saved Custom Logs");
    let game = root.path().join("Fallout 4");
    let documents = root.path().join("Documents");
    let executable = game.join("Fallout4.exe");
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        format!(
            "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4\n  \
             Game Version: NextGen\n  FCX Mode: true\n  SCAN Custom Path: {}\n  \
             Game Folder Path: {}\n  Documents Folder Path: {}\n  Game EXE Path: {}\n",
            yaml_path(&custom),
            yaml_path(&game),
            yaml_path(&documents),
            yaml_path(&executable),
        ),
    )
    .unwrap();
    SavedFallout4 {
        root,
        custom,
        game,
        documents,
        executable,
    }
}

/// Returns the game-differs diagnostics as (value, managed game, target game) triples.
fn not_applied(
    launch: &CrashLogScanLaunchRequest,
) -> Vec<(SavedGameSpecificValue, GameId, GameId)> {
    launch
        .diagnostics()
        .iter()
        .filter_map(|diagnostic| match diagnostic {
            CrashLogScanLaunchDiagnostic::SavedValueNotApplied {
                value,
                managed_game,
                target_game,
            } => Some((*value, *managed_game, *target_game)),
            CrashLogScanLaunchDiagnostic::UserSettings(_) => None,
        })
        .collect()
}

/// Launches `intent` for Fallout 4 VR against a Fallout 4 managed game.
fn launch_vr(
    root: &Path,
    intent: CrashLogScanIntent,
    overrides: CrashLogScanLaunchOverrides,
) -> CrashLogScanLaunchRequest {
    prepare_launch(root, intent, &overrides.with_game(GameId::Fallout4VR)).unwrap()
}

#[test]
fn non_managed_game_applies_no_saved_game_specific_value_and_reports_each() {
    let saved = saved_fallout4();

    let launch = launch_vr(
        saved.root.path(),
        CrashLogScanIntent::Standard,
        CrashLogScanLaunchOverrides::new(),
    );

    let configuration = launch.request().configuration();
    assert_eq!(configuration.game, GameId::Fallout4VR);
    assert_eq!(configuration.game_version, "auto");
    let Request::Standard(request) = launch.request() else {
        panic!("a Standard intent must produce a Standard request");
    };
    assert!(!request.fcx_enabled());
    assert!(launch.setup_context().is_none());
    assert_eq!(request.source().custom_scan_directory, None);
    assert_eq!(request.source().configured_documents_root, None);
    // The base folder is not game-specific: it is always the Installation Root.
    assert_eq!(request.source().base_directory, saved.root.path());

    use SavedGameSpecificValue::{CustomScanFolder, FcxMode, GameVersion, SetupFolders};
    let (managed, target) = (GameId::Fallout4, GameId::Fallout4VR);
    assert_eq!(
        not_applied(&launch),
        [
            (GameVersion, managed, target),
            (FcxMode, managed, target),
            (CustomScanFolder, managed, target),
            (SetupFolders, managed, target),
        ]
    );
    let kinds: Vec<_> = launch
        .diagnostics()
        .iter()
        .map(CrashLogScanLaunchDiagnostic::kind)
        .collect();
    assert_eq!(
        kinds,
        [
            CrashLogScanLaunchDiagnosticKind::GameVersionNotApplied,
            CrashLogScanLaunchDiagnosticKind::FcxModeNotApplied,
            CrashLogScanLaunchDiagnosticKind::CustomScanFolderNotApplied,
            CrashLogScanLaunchDiagnosticKind::SetupFoldersNotApplied,
        ]
    );
    let codes: Vec<_> = launch
        .diagnostics()
        .iter()
        .map(CrashLogScanLaunchDiagnostic::code)
        .collect();
    assert_eq!(
        codes,
        [
            "game_version_not_applied",
            "fcx_mode_not_applied",
            "custom_scan_folder_not_applied",
            "setup_folders_not_applied",
        ]
    );
}

#[test]
fn managed_game_applies_every_saved_value_and_reports_nothing() {
    let saved = saved_fallout4();

    // Naming the managed game explicitly is not a game difference.
    let launch = prepare_launch(
        saved.root.path(),
        CrashLogScanIntent::Standard,
        &CrashLogScanLaunchOverrides::new().with_game(GameId::Fallout4),
    )
    .unwrap();

    assert_eq!(launch.request().configuration().game_version, "NextGen");
    let Request::Standard(request) = launch.request() else {
        panic!("a Standard intent must produce a Standard request");
    };
    assert!(request.fcx_enabled());
    assert_eq!(
        request.source().custom_scan_directory.as_deref(),
        Some(saved.custom.as_path())
    );
    assert_eq!(
        request.source().configured_documents_root.as_deref(),
        Some(saved.documents.as_path())
    );
    let context = launch.setup_context().expect("saved FCX Mode applies");
    assert_eq!(context.game_root.as_deref(), Some(saved.game.as_path()));
    assert_eq!(
        context.docs_root.as_deref(),
        Some(saved.documents.as_path())
    );
    assert_eq!(
        context.game_exe_path.as_deref(),
        Some(saved.executable.as_path())
    );
    assert!(
        launch.diagnostics().is_empty(),
        "{:?}",
        launch.diagnostics()
    );
}

#[test]
fn explicit_overrides_still_win_for_a_non_managed_game() {
    let saved = saved_fallout4();
    let one_off = saved.root.path().join("One-off Logs");

    let launch = launch_vr(
        saved.root.path(),
        CrashLogScanIntent::Standard,
        CrashLogScanLaunchOverrides::new()
            .with_game_version(GameVersionSelection::Vr)
            .with_scan_path(&one_off),
    );

    assert_eq!(launch.request().configuration().game_version, "VR");
    let Request::Standard(request) = launch.request() else {
        panic!("a Standard intent must produce a Standard request");
    };
    assert_eq!(
        request.source().custom_scan_directory.as_deref(),
        Some(one_off.as_path())
    );
    // An override replaced the saved value, so the saved value was never in play and the
    // game difference is not what kept it out.
    let values: Vec<_> = not_applied(&launch)
        .into_iter()
        .map(|(value, _, _)| value)
        .collect();
    assert_eq!(
        values,
        [
            SavedGameSpecificValue::FcxMode,
            SavedGameSpecificValue::SetupFolders
        ]
    );
}

#[test]
fn only_saved_values_that_would_have_applied_are_reported() {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4\n  \
         Game Version: auto\n  FCX Mode: false\n",
    )
    .unwrap();

    let launch = launch_vr(
        root.path(),
        CrashLogScanIntent::Standard,
        CrashLogScanLaunchOverrides::new(),
    );

    assert_eq!(launch.request().configuration().game_version, "auto");
    assert!(
        not_applied(&launch).is_empty(),
        "{:?}",
        launch.diagnostics()
    );
}

#[test]
fn targeted_scan_reports_only_values_a_targeted_launch_would_use() {
    let root = tempfile::tempdir().unwrap();
    let custom = root.path().join("Saved Custom Logs");
    let documents = root.path().join("Documents");
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        format!(
            "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4\n  \
             FCX Mode: false\n  SCAN Custom Path: {}\n  Documents Folder Path: {}\n",
            yaml_path(&custom),
            yaml_path(&documents),
        ),
    )
    .unwrap();

    let launch = launch_vr(
        root.path(),
        CrashLogScanIntent::Targeted(vec![root.path().join("crash.log")]),
        CrashLogScanLaunchOverrides::new(),
    );

    // A Targeted scan without FCX Mode reads neither the custom scan folder nor the setup
    // folders, even for the managed game, so neither was kept out by the game difference.
    assert!(
        not_applied(&launch).is_empty(),
        "{:?}",
        launch.diagnostics()
    );
}

#[test]
fn targeted_scan_for_a_non_managed_game_drops_saved_fcx_mode_and_its_setup_folders() {
    let saved = saved_fallout4();

    let launch = launch_vr(
        saved.root.path(),
        CrashLogScanIntent::Targeted(vec![saved.root.path().join("crash.log")]),
        CrashLogScanLaunchOverrides::new(),
    );

    assert!(launch.setup_context().is_none());
    assert!(matches!(launch.request(), Request::Targeted(request) if !request.fcx_enabled()));
    let values: Vec<_> = not_applied(&launch)
        .into_iter()
        .map(|(value, _, _)| value)
        .collect();
    assert_eq!(
        values,
        [
            SavedGameSpecificValue::GameVersion,
            SavedGameSpecificValue::FcxMode,
            SavedGameSpecificValue::SetupFolders,
        ]
    );
}
