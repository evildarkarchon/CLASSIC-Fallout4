use super::*;
use std::fs;
use std::path::Path;
use tempfile::TempDir;

// ── Game Setup Intake tests ───────────────────────────────────────────────

fn write_valid_fallout4_docs_inis(docs_root: &Path) {
    fs::write(docs_root.join("Fallout4.ini"), "[General]\n").expect("main ini");
    fs::write(docs_root.join("Fallout4Custom.ini"), "[Archive]\n").expect("custom ini");
    fs::write(docs_root.join("Fallout4Prefs.ini"), "[General]\n").expect("prefs ini");
}

#[test]
fn test_run_game_setup_intake_from_user_settings_uses_typed_paths_without_writing() {
    let root = TempDir::new().expect("temp dir");
    let game_root = root.path().join("Fallout4");
    let docs_root = root.path().join("Docs");
    let mods_root = root.path().join("Mods");
    let custom_scan_root = root.path().join("Crash Logs");
    fs::create_dir_all(&game_root).expect("game root");
    fs::create_dir_all(&docs_root).expect("docs root");
    fs::create_dir_all(&mods_root).expect("mods root");
    fs::create_dir_all(&custom_scan_root).expect("custom scan root");
    write_valid_fallout4_docs_inis(&docs_root);
    let configured_exe = game_root.join("Fallout4Custom.exe");
    fs::write(&configured_exe, b"not a real pe").expect("configured exe");
    let papyrus_log = docs_root.join("Logs/Script/Papyrus.0.log");
    fs::create_dir_all(papyrus_log.parent().expect("Papyrus parent")).expect("Papyrus parent");
    fs::write(&papyrus_log, b"Papyrus log").expect("Papyrus log");
    let settings = format!(
        concat!(
            "schema_version: \"1.0\"\n",
            "CLASSIC_Settings:\n",
            "  Managed Game: Fallout4\n",
            "  Game Version: auto\n",
            "  Game Folder Path: '{}'\n",
            "  Game EXE Path: '{}'\n",
            "  Documents Folder Path: '{}'\n",
            "  MODS Folder Path: '{}'\n",
            "  SCAN Custom Path: '{}'\n",
            "  Papyrus Log Path: '{}'\n",
        ),
        game_root.display(),
        configured_exe.display(),
        docs_root.display(),
        mods_root.display(),
        custom_scan_root.display(),
        papyrus_log.display(),
    );
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    fs::write(&settings_path, &settings).expect("User Settings fixture");

    let result = run_game_setup_intake_from_user_settings(&root.path().display().to_string(), "");

    assert_ne!(result.status, "fatal_error");
    assert_eq!(
        result.game_root,
        game_root.to_string_lossy(),
        "typed game root should reach intake"
    );
    assert_eq!(
        result.docs_root,
        docs_root.to_string_lossy(),
        "typed documents root should reach intake"
    );
    assert_eq!(
        result.game_executable,
        configured_exe.to_string_lossy(),
        "typed executable should reach intake"
    );
    assert_eq!(
        fs::read(&settings_path).expect("re-read User Settings"),
        settings.as_bytes(),
        "root-based typed intake must remain read-only"
    );
}
