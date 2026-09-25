//! Registry convenience calls in an isolated receipt process.

use super::{RunnerResult, invalid, text};
use classic_registry_core::{self as registry, Keys};
use serde_json::{Value, json};
use std::path::Path;

/// Clear process-global state even when path conversion or observation fails.
struct Reset;
impl Drop for Reset {
    fn drop(&mut self) {
        registry::clear_all();
    }
}

/// Read nullable references and default-valued preferences through public getters.
fn context() -> Value {
    json!({"yamlCache": registry::get_yaml_cache::<String>(),
        "manualDocs": registry::get_manual_docs_gui::<String>(),
        "gamePath": registry::get_game_path_gui::<String>(),
        "autoDetected": registry::is_version_auto_detected(),
        "xseValid": registry::is_xse_valid(), "enbPresent": registry::is_enb_present(),
        "version": registry::get_game_version_string()})
}

/// Exercise one owner contract; all filesystem paths belong to a temporary directory.
pub(super) fn execute(family: &str, fixture: &Value) -> RunnerResult<Value> {
    registry::clear_all();
    let _reset = Reset;
    let request = &fixture["request"];
    if family == "registry-game" {
        registry::set_game(text(&request["game"])?);
        let game = registry::get_game();
        registry::set_game(text(&request["replacement"])?);
        let replacement = registry::get_game();
        registry::clear_all();
        return Ok(
            json!({"key":Keys::GAME,"game":game, "replacement":replacement,
            "afterClearPresent":registry::is_registered(Keys::GAME)}),
        );
    }
    if family == "registry-gui" {
        let default = registry::is_gui_mode();
        registry::register(Keys::IS_GUI_MODE, true);
        let enabled = registry::is_gui_mode();
        registry::register(Keys::IS_GUI_MODE, false);
        let disabled = registry::is_gui_mode();
        registry::clear_all();
        return Ok(
            json!({"key":Keys::IS_GUI_MODE,"default":default,"enabled":enabled,"disabled":disabled,
            "afterClear":registry::is_gui_mode()}),
        );
    }
    let workspace = tempfile::tempdir()?;
    let root = workspace.path();
    if family == "registry-paths" {
        let initial = registry::get_application_dir();
        registry::set_application_dir(root.join("first"));
        let path = relative(
            root,
            &registry::get_application_dir().ok_or_else(|| invalid("missing override"))?,
        )?;
        registry::set_application_dir(root.join("second"));
        let replacement = relative(
            root,
            &registry::get_application_dir().ok_or_else(|| invalid("missing override"))?,
        )?;
        registry::clear_all();
        return Ok(
            json!({"initial":initial,"path":path,"replacement":replacement,
            "afterClear":registry::get_application_dir(),"files":files(root)?}),
        );
    }
    if family != "registry-context" {
        return Err(invalid("unknown registry accessor family").into());
    }
    let initial = context();
    for key in [Keys::YAML_CACHE, Keys::MANUAL_DOCS_GUI, Keys::GAME_PATH_GUI] {
        registry::register(key, text(&request["value"])?);
    }
    // Python treats empty version strings as absent; keep reference emptiness independent.
    registry::register(Keys::GAME_VERSION, text(&request["version"])?);
    for key in [
        Keys::VERSION_AUTO_DETECTED,
        Keys::XSE_VALID,
        Keys::ENB_PRESENT,
    ] {
        registry::register(key, true);
    }
    registry::register(Keys::LOCAL_DIR, root.join("local"));
    let local = relative(root, &registry::get_local_dir())?;
    let stored = context();
    registry::clear_all();
    Ok(
        json!({"initial":initial,"stored":stored,"afterClear":context(),
        "localDir":local,"files":files(root)?}),
    )
}

/// Reject an escaped public path instead of normalizing away a wrong directory.
fn relative(root: &Path, path: &Path) -> RunnerResult<String> {
    Ok(path
        .strip_prefix(root)?
        .to_string_lossy()
        .replace('\\', "/"))
}

/// Retain any forbidden directory entry instead of assuming setters never write.
fn files(root: &Path) -> RunnerResult<Vec<String>> {
    let mut entries = std::fs::read_dir(root)?
        .map(|entry| Ok(entry?.file_name().to_string_lossy().into_owned()))
        .collect::<std::io::Result<Vec<_>>>()?;
    entries.sort();
    Ok(entries)
}
