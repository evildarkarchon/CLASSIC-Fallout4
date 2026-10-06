//! TUI adapter paths for the shared canonical User Settings store.

use std::fmt;
use std::path::{Path, PathBuf};

use directories::ProjectDirs;

/// Locates the Installation Root used by every canonical User Settings operation.
///
/// The TUI resolves User Settings, YAML Data and Crash Logs relative to this one root, so a run
/// never splits across installations. The search itself is config's shared locator, fed with this
/// process's executable folder and working directory, so the TUI agrees with the GUI and
/// update-core and still finds the repository root from a `target/<profile>` build output folder.
///
/// # Errors
///
/// Returns [`InstallationRootNotFound`] when no candidate holds `CLASSIC Data`. There is
/// deliberately no fallback folder: opening settings somewhere else would silently create a
/// second, empty installation.
pub fn locate_installation_root() -> Result<PathBuf, InstallationRootNotFound> {
    let executable_dir = std::env::current_exe()
        .ok()
        .and_then(|path| path.parent().map(Path::to_path_buf));
    let working_dir = std::env::current_dir().ok();

    classic_config_core::locate_installation_root(executable_dir.as_deref(), working_dir.as_deref())
        .ok_or(InstallationRootNotFound {
            executable_dir,
            working_dir,
        })
}

/// No Installation Root was found from this process's executable folder or working directory.
///
/// Its `Display` text is the user-facing "CLASSIC Data not found" message the TUI prints before
/// it would otherwise take over the terminal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstallationRootNotFound {
    /// Folder holding the running executable, when the platform reported one.
    pub executable_dir: Option<PathBuf>,
    /// Process working directory, when it could be read.
    pub working_dir: Option<PathBuf>,
}

impl fmt::Display for InstallationRootNotFound {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let describe = |path: &Option<PathBuf>| {
            path.as_deref().map_or_else(
                || "(unavailable)".to_owned(),
                |path| path.display().to_string(),
            )
        };
        write!(
            f,
            "CLASSIC Data not found. Run classic-tui from the CLASSIC installation folder, or place \
             it next to the CLASSIC Data folder.\n  Executable folder: {}\n  Working directory: {}",
            describe(&self.executable_dir),
            describe(&self.working_dir)
        )
    }
}

impl std::error::Error for InstallationRootNotFound {}

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
