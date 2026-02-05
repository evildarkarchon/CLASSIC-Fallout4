//! Window state persistence
//!
//! Saves and restores window geometry (position, size, maximized) per tab.
//! State is stored in the user's config directory as JSON.

use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

use directories::ProjectDirs;
use serde::{Deserialize, Serialize};

/// Window geometry for a single tab
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TabGeometry {
    /// X position of window
    pub x: i32,
    /// Y position of window
    pub y: i32,
    /// Width of window
    pub width: u32,
    /// Height of window
    pub height: u32,
    /// Whether window is maximized
    pub maximized: bool,
}

/// Complete window state with per-tab geometries
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct WindowState {
    /// Current active tab index
    pub active_tab: i32,
    /// Per-tab window geometries (key is tab index as string)
    pub tab_geometries: HashMap<String, TabGeometry>,
    /// Crash log folder path from last session
    pub crash_log_path: String,
    /// Game folder path from last session
    pub game_path: String,
}

impl WindowState {
    /// Get geometry for a specific tab, or default if not saved
    pub fn get_tab_geometry(&self, tab_index: i32) -> TabGeometry {
        self.tab_geometries
            .get(&tab_index.to_string())
            .cloned()
            .unwrap_or_default()
    }

    /// Set geometry for a specific tab
    pub fn set_tab_geometry(&mut self, tab_index: i32, geometry: TabGeometry) {
        self.tab_geometries.insert(tab_index.to_string(), geometry);
    }
}

/// Get the path to the state file
fn state_file_path() -> Option<PathBuf> {
    ProjectDirs::from("com", "classic", "classic-gui")
        .map(|dirs| dirs.config_dir().join("window_state.json"))
}

/// Load window state from disk
///
/// Returns default state if file doesn't exist or can't be parsed.
pub fn load_window_state() -> WindowState {
    let Some(path) = state_file_path() else {
        return WindowState::default();
    };

    if !path.exists() {
        return WindowState::default();
    }

    fs::read_to_string(&path)
        .ok()
        .and_then(|content| serde_json::from_str(&content).ok())
        .unwrap_or_default()
}

/// Save window state to disk
///
/// Creates the config directory if it doesn't exist.
pub fn save_window_state(state: &WindowState) -> Result<(), Box<dyn std::error::Error>> {
    let Some(path) = state_file_path() else {
        return Err("Could not determine config directory".into());
    };

    // Ensure config directory exists
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }

    let json = serde_json::to_string_pretty(state)?;
    fs::write(&path, json)?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tab_geometry_default() {
        let geometry = TabGeometry::default();
        assert_eq!(geometry.x, 0);
        assert_eq!(geometry.y, 0);
        assert_eq!(geometry.width, 0);
        assert_eq!(geometry.height, 0);
        assert!(!geometry.maximized);
    }

    #[test]
    fn test_window_state_get_set_geometry() {
        let mut state = WindowState::default();

        let geometry = TabGeometry {
            x: 100,
            y: 200,
            width: 800,
            height: 600,
            maximized: false,
        };

        state.set_tab_geometry(0, geometry.clone());

        let retrieved = state.get_tab_geometry(0);
        assert_eq!(retrieved.x, 100);
        assert_eq!(retrieved.width, 800);
    }

    #[test]
    fn test_get_nonexistent_tab_returns_default() {
        let state = WindowState::default();
        let geometry = state.get_tab_geometry(99);
        assert_eq!(geometry.x, 0);
        assert_eq!(geometry.width, 0);
    }

    #[test]
    fn test_state_serialization() {
        let mut state = WindowState {
            active_tab: 1,
            crash_log_path: "/path/to/logs".to_string(),
            game_path: "/path/to/game".to_string(),
            ..Default::default()
        };

        state.set_tab_geometry(
            0,
            TabGeometry {
                x: 50,
                y: 50,
                width: 1024,
                height: 768,
                maximized: true,
            },
        );

        let json = serde_json::to_string(&state).unwrap();
        let parsed: WindowState = serde_json::from_str(&json).unwrap();

        assert_eq!(parsed.active_tab, 1);
        assert_eq!(parsed.crash_log_path, "/path/to/logs");
        assert_eq!(parsed.get_tab_geometry(0).width, 1024);
    }

    #[test]
    fn test_state_file_path_exists() {
        // Verify ProjectDirs returns a valid path on this platform
        let path = state_file_path();
        assert!(path.is_some(), "state_file_path() returned None");
    }
}
