//! Public cached installation paths and document reports from owned inputs.

use super::{RunnerResult, invalid, text};
use classic_path_core::{DocsPathFinder, DocumentsChecker, GamePathFinder};
use serde_json::{Value, json};
use std::{env, fs, path::Path};

/// Inventory all durable files and directories, including unexpected writes.
fn inventory(
    root: &Path,
    directory: &Path,
    files: &mut Vec<Value>,
    directories: &mut Vec<String>,
) -> RunnerResult<()> {
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        let relative = entry
            .path()
            .strip_prefix(root)?
            .to_string_lossy()
            .replace('\\', "/");
        if entry.file_type()?.is_dir() {
            directories.push(relative);
            inventory(root, &entry.path(), files, directories)?;
        } else if entry.file_type()?.is_file() {
            files.push(json!({"path": relative, "content": fs::read_to_string(entry.path())?}));
        } else {
            return Err(invalid("unexpected installation artifact").into());
        }
    }
    Ok(())
}

/// Execute only valid cached lookups; platform fallback is never an expected outcome.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    let game = text(&fixture["gamePath"])?;
    let docs = text(&fixture["docsPath"])?;
    if !matches!(
        (game.as_str(), docs.as_str()),
        ("game", "docs") | ("Game Folder", "Docs Folder")
    ) {
        return Err(invalid("unsupported installation cache paths").into());
    }
    if fixture["files"] != json!({format!("{game}/Fallout4.exe"): "owned executable marker"}) {
        return Err(invalid("installation fixture needs a valid cached executable").into());
    }
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    fs::create_dir(root.join(&game))?;
    fs::create_dir(root.join(&docs))?;
    fs::write(
        root.join("CLASSIC Main.yaml"),
        text(&fixture["registryYaml"])?,
    )?;
    fs::write(
        root.join(&game).join("Fallout4.exe"),
        "owned executable marker",
    )?;
    let previous = env::current_dir()?;
    env::set_current_dir(root)?;
    // Relative inputs exclude host parent names (such as OneDrive) from the
    // checker contract. This dedicated receipt runner executes scenarios serially.
    let result = (|| -> RunnerResult<Value> {
        let game_finder = GamePathFinder::new("Fallout4.exe", None::<&str>, "Fallout4", false);
        let docs_finder = DocsPathFinder::new("My Games/Fallout4").with_steam_app_id(12345);
        game_finder.validate_game_path(Path::new(&game))?;
        docs_finder.validate_docs_path(Path::new(&docs))?;
        let game_path = game_finder.find_game_path(Some(Path::new(&game)), None)?;
        let docs_path = docs_finder.find_docs_path(Some(&docs))?;
        let checks = DocumentsChecker::new("Fallout4").run_all_checks(Path::new(&docs))?;
        let checker = DocumentsChecker::new("Fallout4");
        if checker.check_onedrive_in_path(Path::new(&docs)).is_some() {
            return Err(invalid("owned documents path unexpectedly reports OneDrive").into());
        }
        for (index, name) in ["Fallout4.ini", "Fallout4Custom.ini", "Fallout4Prefs.ini"]
            .iter()
            .enumerate()
        {
            let check = checker.validate_ini_file(Path::new(&docs), name)?;
            if check.exists
                || check.is_valid
                || !check.has_issue()
                || check.ini_name != *name
                || check.message != checks[index]
            {
                return Err(
                    invalid("per-file INI diagnosis disagrees with aggregate check").into(),
                );
            }
        }
        docs_finder.validate_ini_files(Path::new(&docs), &[])?;
        if docs_finder
            .validate_ini_files(Path::new(&docs), &["Fallout4.ini"])
            .is_ok()
        {
            return Err(invalid("missing required INI was accepted").into());
        }
        let scan = Path::new("validation/owned/scan");
        fs::create_dir_all(scan)?;
        classic_path_core::validate_custom_scan_path(scan)?;
        classic_path_core::validate_settings_path(
            Path::new(&game),
            "Game Path",
            Some(&["Fallout4.exe".to_string()]),
        )?;
        classic_path_core::validate_settings_paths(
            Path::new(&game),
            Path::new(&docs),
            Some(scan),
            "Fallout4.exe",
        )?;
        classic_path_core::check_drive_exists(root)?;
        classic_path_core::check_read_permissions(Path::new(&game))?;
        classic_path_core::check_write_permissions(Path::new(&game))?;
        classic_path_core::validate_path_with_permissions(Path::new(&game), true, true)?;
        if !classic_path_core::is_valid_path(Path::new(&game))
            || classic_path_core::is_valid_path(Path::new("missing-path"))
        {
            return Err(invalid("path existence disagrees with owned tree").into());
        }
        classic_path_core::validate_required_files(Path::new(&game), &["Fallout4.exe".into()])?;
        if classic_path_core::validate_required_files(Path::new(&game), &["missing.ini".into()])
            .is_ok()
        {
            return Err(invalid("required-files validation accepted an absent file").into());
        }
        #[cfg(windows)]
        {
            let readonly_file = scan.join("readonly.txt");
            fs::write(&readonly_file, "retained bytes")?;
            let mut permissions = fs::metadata(&readonly_file)?.permissions();
            permissions.set_readonly(true);
            fs::set_permissions(&readonly_file, permissions)?;
            if !fs::metadata(&readonly_file)?.permissions().readonly() {
                return Err(invalid("readonly precondition was not established").into());
            }
            classic_path_core::remove_readonly(&readonly_file)?;
            if fs::metadata(&readonly_file)?.permissions().readonly()
                || fs::read_to_string(&readonly_file)? != "retained bytes"
            {
                return Err(invalid(
                    "readonly removal changed bytes or failed to restore write access",
                )
                .into());
            }
        }
        classic_path_core::validate_path_exists(Path::new(&game))?;
        classic_path_core::validate_is_directory(Path::new(&docs))?;
        classic_path_core::validate_is_file(&Path::new(&game).join("Fallout4.exe"))?;
        if classic_path_core::is_restricted_path(scan)
            || !classic_path_core::is_restricted_path(Path::new("Windows/System32/test"))
        {
            return Err(invalid("restricted-path classification changed").into());
        }
        if !classic_path_core::is_valid_executable_path(&Path::new(&game).join("Fallout4.exe"))
            || classic_path_core::is_valid_executable_path(Path::new("CLASSIC Main.yaml"))
        {
            return Err(invalid("executable path classification changed").into());
        }
        fs::remove_dir_all("validation")?;
        fs::write(
            "path-detection.log",
            format!("plugin directory = \"{game}/Data/F4SE/Plugins\"\n"),
        )?;
        if classic_path_core::parse_xse_log(Path::new("path-detection.log"))? != Path::new(&game) {
            return Err(invalid("XSE log extraction changed game root").into());
        }
        fs::remove_file("path-detection.log")?;
        let mut files = Vec::new();
        let mut directories = Vec::new();
        inventory(root, root, &mut files, &mut directories)?;
        files.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
        directories.sort();
        Ok(
            json!({"gamePath": game_path.to_string_lossy(), "docsPath": docs_path.to_string_lossy(),
                  "checks": checks, "files": files, "directories": directories}),
        )
    })();
    env::set_current_dir(previous)?;
    result
}
