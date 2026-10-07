//! Behavioral checks for the Crash Log Scan Setup Context a launch builds when FCX Mode is on.
//!
//! Each case writes a User Settings document (and, where the case needs them, the game
//! executable and XSE log files) into a temporary Installation Root, launches through the
//! public interface, and observes only the setup context or the typed launch error. Every
//! case saves a documents folder, so the XSE log lookup never falls through to the host's
//! real documents discovery.

use classic_scan_launch::{
    CrashLogScanIntent, CrashLogScanLaunchError, CrashLogScanLaunchErrorKind,
    CrashLogScanLaunchOverrides, CrashLogScanLaunchRequest, prepare_launch,
};
use classic_scanlog_core::CrashLogScanSetupContext;
use classic_scanlog_core::scan_run::contract::Request;
use std::path::{Path, PathBuf};
use tempfile::TempDir;

/// Quotes an absolute path as a single-quoted YAML scalar so backslashes stay literal.
fn yaml_path(path: &Path) -> String {
    format!("'{}'", path.display().to_string().replace('\'', "''"))
}

/// Creates an empty file (and its parent folders) and returns its path.
fn touch(path: PathBuf) -> PathBuf {
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(&path, b"").unwrap();
    path
}

/// An Installation Root with the game and documents folder paths it saves.
struct Installation {
    root: TempDir,
    game: PathBuf,
    documents: PathBuf,
}

impl Installation {
    /// Creates an Installation Root whose saved game and documents folders sit inside it.
    ///
    /// The folders are only named, not created; each case creates what it needs.
    fn new() -> Self {
        let root = tempfile::tempdir().unwrap();
        let game = root.path().join("Fallout 4");
        let documents = root.path().join("Documents");
        Self {
            root,
            game,
            documents,
        }
    }

    /// Writes User Settings for `managed_game` with the saved folders plus `extra` lines.
    fn save(&self, managed_game: &str, extra: &str) {
        std::fs::write(
            self.root.path().join("CLASSIC Settings.yaml"),
            format!(
                "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: {managed_game}\n  \
                 Game Folder Path: {}\n  Documents Folder Path: {}\n{extra}",
                yaml_path(&self.game),
                yaml_path(&self.documents)
            ),
        )
        .unwrap();
    }

    /// Launches `intent` with `overrides`.
    fn launch(
        &self,
        intent: CrashLogScanIntent,
        overrides: &CrashLogScanLaunchOverrides,
    ) -> Result<CrashLogScanLaunchRequest, CrashLogScanLaunchError> {
        prepare_launch(self.root.path(), intent, overrides)
    }

    /// Launches a Standard scan with no overrides and returns its setup context.
    fn standard_setup_context(&self) -> CrashLogScanSetupContext {
        self.launch(
            CrashLogScanIntent::Standard,
            &CrashLogScanLaunchOverrides::new(),
        )
        .expect("the launch produces a request")
        .setup_context()
        .expect("FCX Mode carries a setup context")
        .clone()
    }
}

#[test]
fn saved_fcx_mode_draws_the_setup_context_from_saved_setup_for_the_managed_game() {
    let installation = Installation::new();
    let executable = touch(installation.game.join("Fallout4.exe"));
    let xse_log = touch(installation.documents.join("F4SE").join("f4se.log"));
    installation.save(
        "Fallout 4",
        &format!(
            "  Game Version: NextGen\n  FCX Mode: true\n  Game EXE Path: {}\n",
            yaml_path(&executable)
        ),
    );

    let context = installation.standard_setup_context();

    assert_eq!(context.game_root, Some(installation.game.clone()));
    assert_eq!(context.docs_root, Some(installation.documents.clone()));
    assert_eq!(context.game_exe_path, Some(executable));
    assert_eq!(context.xse_log_path, Some(xse_log));
}

#[test]
fn fallout4_vr_setup_context_carries_its_own_xse_log() {
    let installation = Installation::new();
    // Both logs share VR's `F4SE` folder; VR must read only its own.
    touch(installation.documents.join("F4SE").join("f4se.log"));
    let vr_log = touch(installation.documents.join("F4SE").join("f4sevr.log"));
    installation.save("Fallout 4 VR", "  Game Version: VR\n  FCX Mode: true\n");

    let context = installation.standard_setup_context();

    assert_eq!(context.xse_log_path, Some(vr_log));
    // No executable is saved, so the version's own executable under the game folder applies.
    assert_eq!(
        context.game_exe_path,
        Some(installation.game.join("Fallout4VR.exe"))
    );
}

#[test]
fn missing_setup_folders_still_produce_a_request_with_the_saved_folders() {
    let installation = Installation::new();
    installation.save("Fallout 4", "  FCX Mode: true\n");

    let context = installation.standard_setup_context();

    // Neither folder exists; FCX setup validation, not the launch, reports that.
    assert_eq!(context.game_root, Some(installation.game.clone()));
    assert_eq!(context.docs_root, Some(installation.documents.clone()));
    assert_eq!(
        context.game_exe_path,
        Some(installation.game.join("Fallout4.exe"))
    );
    assert_eq!(context.xse_log_path, None);
}

#[test]
fn targeted_intent_with_the_fcx_mode_override_includes_the_setup_context() {
    let installation = Installation::new();
    let xse_log = touch(installation.documents.join("F4SE").join("f4se.log"));
    installation.save("Fallout 4", "  FCX Mode: false\n");
    let input = installation.root.path().join("crash-one.log");

    let launch = installation
        .launch(
            CrashLogScanIntent::Targeted(vec![input]),
            &CrashLogScanLaunchOverrides::new().with_fcx_mode(),
        )
        .unwrap();

    let Request::Targeted(request) = launch.request() else {
        panic!("a Targeted intent must produce a Targeted request");
    };
    assert!(request.fcx_enabled());
    let context = launch.setup_context().expect("the override turns FCX on");
    assert_eq!(context.game_root, Some(installation.game.clone()));
    assert_eq!(context.docs_root, Some(installation.documents.clone()));
    assert_eq!(context.xse_log_path, Some(xse_log));
}

#[test]
fn absent_fcx_mode_override_keeps_saved_fcx_mode_off() {
    let installation = Installation::new();
    installation.save("Fallout 4", "  FCX Mode: false\n");

    let launch = installation
        .launch(
            CrashLogScanIntent::Standard,
            &CrashLogScanLaunchOverrides::new(),
        )
        .unwrap();

    assert!(launch.setup_context().is_none());
}

/// Saves a documents folder no platform can inspect: the YAML `\0` escape puts a NUL in it.
const UNINSPECTABLE_DOCUMENTS: &str = "  Documents Folder Path: \"/bad\\0docs\"\n";

#[test]
fn operational_xse_log_failure_is_a_typed_launch_error() {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        format!(
            "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4\n  \
             FCX Mode: true\n{UNINSPECTABLE_DOCUMENTS}"
        ),
    )
    .unwrap();

    let error = prepare_launch(
        root.path(),
        CrashLogScanIntent::Standard,
        &CrashLogScanLaunchOverrides::new(),
    )
    .unwrap_err();

    assert_eq!(error.kind(), CrashLogScanLaunchErrorKind::XseLogInspect);
    let CrashLogScanLaunchError::XseLogInspect { path, message } = &error else {
        panic!("expected the XSE log inspection error, got {error:?}");
    };
    assert!(
        path.ends_with(Path::new("F4SE").join("f4se.log")),
        "{path:?}"
    );
    assert!(!message.is_empty());
}

#[test]
fn the_xse_log_is_not_looked_up_when_fcx_mode_is_off() {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        format!(
            "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4\n  \
             FCX Mode: false\n{UNINSPECTABLE_DOCUMENTS}"
        ),
    )
    .unwrap();

    let launch = prepare_launch(
        root.path(),
        CrashLogScanIntent::Standard,
        &CrashLogScanLaunchOverrides::new(),
    );

    assert!(launch.is_ok(), "{launch:?}");
}

// The game executable fact follows the GUI's rule (`normalizeGameExecutablePath` with the
// selected version's executable name): a saved executable is kept only when it exists
// directly inside the saved game folder; otherwise the version's executable under the game
// folder applies; with no game folder the saved executable is passed through unchanged.

#[test]
fn saved_executable_inside_the_game_folder_is_kept() {
    let installation = Installation::new();
    let executable = touch(installation.game.join("Fallout4Launcher.exe"));
    installation.save(
        "Fallout 4",
        &format!(
            "  FCX Mode: true\n  Game EXE Path: {}\n",
            yaml_path(&executable)
        ),
    );

    assert_eq!(
        installation.standard_setup_context().game_exe_path,
        Some(executable)
    );
}

#[test]
fn saved_executable_outside_the_game_folder_is_replaced_by_the_versions_executable() {
    let installation = Installation::new();
    std::fs::create_dir_all(&installation.game).unwrap();
    let elsewhere = touch(installation.root.path().join("Other").join("Fallout4.exe"));
    installation.save(
        "Fallout 4",
        &format!(
            "  FCX Mode: true\n  Game EXE Path: {}\n",
            yaml_path(&elsewhere)
        ),
    );

    assert_eq!(
        installation.standard_setup_context().game_exe_path,
        Some(installation.game.join("Fallout4.exe"))
    );
}

#[test]
fn saved_executable_that_does_not_exist_is_replaced_by_the_versions_executable() {
    let installation = Installation::new();
    installation.save(
        "Fallout 4",
        &format!(
            "  Game Version: VR\n  FCX Mode: true\n  Game EXE Path: {}\n",
            yaml_path(&installation.game.join("Fallout4.exe"))
        ),
    );

    // The selected VR version names its own executable.
    assert_eq!(
        installation.standard_setup_context().game_exe_path,
        Some(installation.game.join("Fallout4VR.exe"))
    );
}

#[test]
fn saved_executable_passes_through_when_no_game_folder_is_saved() {
    let root = tempfile::tempdir().unwrap();
    let documents = root.path().join("Documents");
    let executable = root.path().join("Somewhere").join("Fallout4.exe");
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        format!(
            "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4\n  \
             FCX Mode: true\n  Documents Folder Path: {}\n  Game EXE Path: {}\n",
            yaml_path(&documents),
            yaml_path(&executable)
        ),
    )
    .unwrap();

    let context = prepare_launch(
        root.path(),
        CrashLogScanIntent::Standard,
        &CrashLogScanLaunchOverrides::new(),
    )
    .unwrap()
    .setup_context()
    .cloned()
    .unwrap();

    assert_eq!(context.game_root, None);
    assert_eq!(context.game_exe_path, Some(executable));
}
