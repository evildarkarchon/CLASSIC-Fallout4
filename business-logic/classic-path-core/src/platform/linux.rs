//! Linux-specific path operations.
//!
//! This module provides Steam/Proton path detection for Linux:
//! - Home directory detection
//! - Steam library VDF parsing
//! - Proton prefix path construction

#![cfg_attr(target_os = "windows", allow(dead_code))]

use crate::error::{DocsPathError, DocsPathResult};
use std::fs;
use std::path::{Path, PathBuf};

/// Get the user's home directory on Linux.
///
/// # Returns
///
/// The home directory path, or an error if HOME env var not set.
pub fn get_home_directory() -> DocsPathResult<PathBuf> {
    dirs::home_dir().ok_or(DocsPathError::NotFound)
}

/// Parse Steam library VDF file to find game installation.
///
/// Parses `~/.local/share/Steam/steamapps/libraryfolders.vdf` to find the
/// library containing the specified game Steam ID.
///
/// VDF Format:
/// ```text
/// "libraryfolders"
/// {
///     "0"
///     {
///         "path"    "/home/user/.local/share/Steam"
///         "apps"
///         {
///             "377160"    "12345"  // Fallout 4 Steam ID
///         }
///     }
/// }
/// ```
///
/// # Arguments
///
/// * `game_steam_id` - The Steam application ID for the game
///
/// # Returns
///
/// The library path containing the game, or an error if not found.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::parse_steam_library;
///
/// // Find Fallout 4 (Steam ID: 377160)
/// let library = parse_steam_library(377160)?;
/// println!("Library: {}", library.display());
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn parse_steam_library_vdf(game_steam_id: u32) -> DocsPathResult<PathBuf> {
    let home = get_home_directory()?;
    let vdf_path = home.join(".local/share/Steam/steamapps/libraryfolders.vdf");

    if !vdf_path.exists() {
        return Err(DocsPathError::SteamLibraryNotFound(vdf_path));
    }

    let content = fs::read_to_string(&vdf_path).map_err(DocsPathError::IoError)?;

    parse_vdf_content(&content, game_steam_id)
}

/// Parse VDF content to find library path containing the game.
///
/// # Arguments
///
/// * `content` - The VDF file content as a string
/// * `game_steam_id` - The Steam application ID to search for
///
/// # Returns
///
/// The library path containing the game, or an error if not found.
fn parse_vdf_content(content: &str, game_steam_id: u32) -> DocsPathResult<PathBuf> {
    let game_id_str = game_steam_id.to_string();
    let mut current_library_path: Option<String> = None;
    let mut in_apps_section = false;

    for line in content.lines() {
        let trimmed = line.trim();

        // Look for "path" value in library entry
        if trimmed.starts_with("\"path\"")
            && let Some(path) = extract_vdf_value(trimmed)
        {
            current_library_path = Some(path);
        }

        // Detect "apps" section start
        if trimmed.starts_with("\"apps\"") {
            in_apps_section = true;
            continue;
        }

        // Detect section end
        if in_apps_section && trimmed == "}" {
            in_apps_section = false;
            current_library_path = None;
            continue;
        }

        // Look for game ID in apps section
        if in_apps_section
            && trimmed.starts_with(&format!("\"{}\"", game_id_str))
            && let Some(path) = current_library_path
        {
            return Ok(PathBuf::from(path));
        }
    }

    Err(DocsPathError::GameNotInSteamLibrary(game_steam_id))
}

/// Extract the value from a VDF key-value line.
///
/// Example: `"path"    "/home/user/Steam"` → `/home/user/Steam`
///
/// # Arguments
///
/// * `line` - A VDF line like `"key"    "value"`
///
/// # Returns
///
/// The extracted value string, or None if parsing failed.
fn extract_vdf_value(line: &str) -> Option<String> {
    // Split on quotes and take the last quoted value
    let parts: Vec<&str> = line.split('"').collect();

    // Format is: "key"    "value"
    // After split: ["", "key", "    ", "value", ""]
    if parts.len() >= 4 {
        Some(parts[3].to_string())
    } else {
        None
    }
}

/// Construct the Proton prefix documents path for a game.
///
/// Given a Steam library path and game Steam ID, constructs the full path
/// to the Windows "My Documents" folder within the Proton prefix.
///
/// # Arguments
///
/// * `library_path` - The Steam library path containing the game
/// * `game_steam_id` - The Steam application ID
/// * `docs_name` - The game-specific documents folder name (e.g., "My Games/Fallout4")
///
/// # Returns
///
/// The full path to the game's documents folder in the Proton prefix.
///
/// # Examples
///
/// ```ignore
/// // Internal helper used by DocsPathFinder's Linux workflow.
/// let library = std::path::PathBuf::from("/home/user/.local/share/Steam");
/// let docs_path = classic_path_core::platform::linux::construct_proton_docs_path(
///     &library,
///     377160,
///     "My Games/Fallout4",
/// );
/// ```
#[allow(dead_code)]
pub fn construct_proton_docs_path(
    library_path: &Path,
    game_steam_id: u32,
    docs_name: &str,
) -> PathBuf {
    library_path
        .join("steamapps/compatdata")
        .join(game_steam_id.to_string())
        .join("pfx/drive_c/users/steamuser/My Documents")
        .join(docs_name)
}

#[cfg(test)]
#[path = "linux_tests.rs"]
mod tests;
