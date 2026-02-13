//! Linux-specific path operations.
//!
//! This module provides Steam/Proton path detection for Linux:
//! - Home directory detection
//! - Steam library VDF parsing
//! - Proton prefix path construction

use crate::error::{DocsPathError, DocsPathResult};
use std::fs;
use std::path::PathBuf;

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
/// use classic_path_core::platform::linux::parse_steam_library_vdf;
///
/// // Find Fallout 4 (Steam ID: 377160)
/// let library = parse_steam_library_vdf(377160)?;
/// println!("Library: {}", library.display());
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn parse_steam_library_vdf(game_steam_id: u32) -> DocsPathResult<PathBuf> {
    let home = get_home_directory()?;
    let vdf_path = home.join(".local/share/Steam/steamapps/libraryfolders.vdf");

    if !vdf_path.exists() {
        return Err(DocsPathError::SteamLibraryNotFound(vdf_path));
    }

    let content = fs::read_to_string(&vdf_path).map_err(|e| DocsPathError::IoError(e))?;

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
        if trimmed.starts_with("\"path\"") {
            if let Some(path) = extract_vdf_value(trimmed) {
                current_library_path = Some(path);
            }
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
        if in_apps_section && trimmed.starts_with(&format!("\"{}\"", game_id_str)) {
            if let Some(path) = current_library_path {
                return Ok(PathBuf::from(path));
            }
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
/// ```rust,no_run
/// use classic_path_core::platform::linux::construct_proton_docs_path;
/// use std::path::PathBuf;
///
/// let library = PathBuf::from("/home/user/.local/share/Steam");
/// let docs_path = construct_proton_docs_path(&library, 377160, "My Games/Fallout4");
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn construct_proton_docs_path(
    library_path: &PathBuf,
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
mod tests {
    use super::*;

    #[test]
    fn test_parse_vdf_content() {
        let vdf_content = r#"
"libraryfolders"
{
    "0"
    {
        "path"    "/home/user/.local/share/Steam"
        "label"   ""
        "apps"
        {
            "377160"    "12345"
            "489830"    "67890"
        }
    }
    "1"
    {
        "path"    "/mnt/games/SteamLibrary"
        "label"   "Games"
        "apps"
        {
            "22380"     "111111"
        }
    }
}
"#;

        // Test finding Fallout 4 (377160)
        let result = parse_vdf_content(vdf_content, 377160);
        assert!(result.is_ok());
        assert_eq!(
            result.unwrap(),
            PathBuf::from("/home/user/.local/share/Steam")
        );

        // Test finding Skyrim SE (489830)
        let result = parse_vdf_content(vdf_content, 489830);
        assert!(result.is_ok());
        assert_eq!(
            result.unwrap(),
            PathBuf::from("/home/user/.local/share/Steam")
        );

        // Test finding Fallout 3 (22380) in second library
        let result = parse_vdf_content(vdf_content, 22380);
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), PathBuf::from("/mnt/games/SteamLibrary"));

        // Test game not in library
        let result = parse_vdf_content(vdf_content, 999999);
        assert!(result.is_err());
        match result {
            Err(DocsPathError::GameNotInSteamLibrary(id)) => assert_eq!(id, 999999),
            _ => panic!("Expected GameNotInSteamLibrary error"),
        }
    }

    #[test]
    fn test_extract_vdf_value() {
        assert_eq!(
            extract_vdf_value(r#""path"    "/home/user/Steam""#),
            Some("/home/user/Steam".to_string())
        );

        assert_eq!(
            extract_vdf_value(r#""label"   "Games Drive""#),
            Some("Games Drive".to_string())
        );

        assert_eq!(
            extract_vdf_value(r#""377160"    "12345""#),
            Some("12345".to_string())
        );

        // Invalid format
        assert_eq!(extract_vdf_value("invalid"), None);
    }

    #[test]
    fn test_construct_proton_docs_path() {
        let library = PathBuf::from("/home/user/.local/share/Steam");
        let docs_path = construct_proton_docs_path(&library, 377160, "My Games/Fallout4");

        let expected = PathBuf::from(
            "/home/user/.local/share/Steam/steamapps/compatdata/377160/pfx/drive_c/users/steamuser/My Documents/My Games/Fallout4",
        );

        assert_eq!(docs_path, expected);
    }

    #[test]
    fn test_get_home_directory() {
        // Home directory should exist on Linux
        let result = get_home_directory();
        assert!(result.is_ok());

        let home = result.unwrap();
        assert!(home.is_absolute());
    }
}
