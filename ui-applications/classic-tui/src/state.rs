//! TUI adapter paths for the shared canonical User Settings store.

use std::path::PathBuf;

use directories::ProjectDirs;

/// Returns the CLASSIC root used by every canonical User Settings operation.
///
/// The TUI already resolves YAML Data and Crash Logs relative to its working root, so using the
/// same explicit root avoids splitting one run across multiple settings locations.
pub fn classic_root() -> PathBuf {
    let current_dir = std::env::current_dir().unwrap_or_default();
    let executable_dir = std::env::current_exe()
        .ok()
        .and_then(|path| path.parent().map(PathBuf::from));

    let mut candidates = Vec::new();
    if let Some(application_dir) = executable_dir.as_ref() {
        candidates.push(application_dir.clone());
    }
    candidates.push(current_dir.clone());
    if let Some(application_dir) = executable_dir.as_ref() {
        // Match the native frontends' development/install search so every executable resolves the
        // same data root even when it is launched from a build output directory.
        if let Some(parent) = application_dir.parent() {
            candidates.push(parent.to_path_buf());
            if let Some(grandparent) = parent.parent() {
                candidates.push(grandparent.to_path_buf());
            }
            candidates.push(parent.join("install"));
        }
    }
    candidates.push(current_dir.join("install"));

    select_classic_root(candidates, executable_dir.unwrap_or(current_dir))
}

/// Selects the first native-frontend-compatible root, retaining a stable application fallback.
fn select_classic_root(candidates: Vec<PathBuf>, fallback: PathBuf) -> PathBuf {
    candidates
        .into_iter()
        .find(|candidate| candidate.join("CLASSIC Data").is_dir())
        .unwrap_or(fallback)
}

/// Returns the former TUI-only remembered-state path, when the platform exposes one.
///
/// This path is an import source only. Production reads and saves always use the shared
/// `CLASSIC Settings.yaml` store owned by `classic-user-settings-core`.
pub fn legacy_tui_state_file_path() -> Option<PathBuf> {
    ProjectDirs::from("com", "classic", "classic-tui")
        .map(|dirs| dirs.config_dir().join("state.json"))
}

#[cfg(test)]
#[path = "state_tests.rs"]
mod tests;
