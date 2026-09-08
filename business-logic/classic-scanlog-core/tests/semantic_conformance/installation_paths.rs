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
        let docs_finder = DocsPathFinder::new("My Games/Fallout4");
        game_finder.validate_game_path(Path::new(&game))?;
        docs_finder.validate_docs_path(Path::new(&docs))?;
        let game_path = game_finder.find_game_path(Some(Path::new(&game)), None)?;
        let docs_path = docs_finder.find_docs_path(Some(&docs))?;
        let checks = DocumentsChecker::new("Fallout4").run_all_checks(Path::new(&docs))?;
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
