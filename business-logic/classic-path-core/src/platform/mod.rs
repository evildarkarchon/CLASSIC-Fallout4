//! Platform-specific path operations.
//!
//! This module provides platform-specific implementations for:
//! - Windows: Registry queries, system paths
//! - Linux: Steam VDF parsing, Proton prefix paths
//!
//! The public API uses conditional compilation to expose the appropriate
//! platform implementation.

#[cfg(target_os = "windows")]
use crate::error::DocsPathError;
use crate::error::DocsPathResult;
use std::path::PathBuf;

#[cfg(target_os = "windows")]
pub mod windows;

pub mod linux;

/// Get the system documents path using platform-specific methods.
///
/// On Windows, queries the registry for the "Personal" documents folder.
/// On Linux, returns the user's home directory (Steam paths are handled separately).
///
/// # Returns
///
/// The system documents path, or an error if detection failed.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::get_system_documents_path;
///
/// let docs_path = get_system_documents_path()?;
/// println!("Documents: {}", docs_path.display());
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
#[cfg(target_os = "windows")]
pub fn get_system_documents_path() -> DocsPathResult<PathBuf> {
    windows::get_documents_path()
}

/// Get the system documents path (Linux).
///
/// Returns the user's home directory. Game-specific documents are typically
/// in Steam's Proton prefix, handled by `parse_steam_library`.
#[cfg(target_os = "linux")]
pub fn get_system_documents_path() -> DocsPathResult<PathBuf> {
    linux::get_home_directory()
}

/// Parse Steam library VDF to find game installation path.
///
/// Only available on Linux. Parses the Steam `libraryfolders.vdf` file to locate
/// the library containing the specified game Steam ID.
///
/// # Arguments
///
/// * `game_steam_id` - The Steam application ID for the game (e.g., 377160 for Fallout 4)
///
/// # Returns
///
/// The library path containing the game, or an error if not found.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::platform::parse_steam_library;
///
/// // Find Fallout 4 in Steam library
/// let library_path = parse_steam_library(377160)?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
#[cfg(target_os = "linux")]
pub fn parse_steam_library(game_steam_id: u32) -> DocsPathResult<PathBuf> {
    linux::parse_steam_library_vdf(game_steam_id)
}

/// Parse Steam library VDF (stub for Windows).
///
/// This function is not implemented on Windows as Steam library parsing
/// is only needed for Linux Proton paths.
#[cfg(target_os = "windows")]
pub fn parse_steam_library(_game_steam_id: u32) -> DocsPathResult<PathBuf> {
    Err(DocsPathError::NotFound)
}

// Re-export Windows-specific functions
#[cfg(target_os = "windows")]
pub use windows::remove_readonly;
