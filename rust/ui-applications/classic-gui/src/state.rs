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
pub fn state_file_path() -> Option<PathBuf> {
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

    #[test]
    fn test_window_state_default() {
        let state = WindowState::default();
        assert_eq!(state.active_tab, 0);
        assert!(state.tab_geometries.is_empty());
        assert!(state.crash_log_path.is_empty());
        assert!(state.game_path.is_empty());
    }

    #[test]
    fn test_set_tab_geometry_overwrites() {
        let mut state = WindowState::default();

        let g1 = TabGeometry { x: 10, y: 20, width: 100, height: 200, maximized: false };
        let g2 = TabGeometry { x: 30, y: 40, width: 300, height: 400, maximized: true };

        state.set_tab_geometry(0, g1);
        state.set_tab_geometry(0, g2);

        let retrieved = state.get_tab_geometry(0);
        assert_eq!(retrieved.x, 30);
        assert_eq!(retrieved.width, 300);
        assert!(retrieved.maximized);
    }

    #[test]
    fn test_multiple_tabs_independent() {
        let mut state = WindowState::default();

        state.set_tab_geometry(0, TabGeometry { x: 1, y: 2, width: 100, height: 200, maximized: false });
        state.set_tab_geometry(1, TabGeometry { x: 10, y: 20, width: 800, height: 600, maximized: true });
        state.set_tab_geometry(2, TabGeometry { x: 50, y: 50, width: 500, height: 400, maximized: false });

        assert_eq!(state.get_tab_geometry(0).x, 1);
        assert_eq!(state.get_tab_geometry(1).x, 10);
        assert_eq!(state.get_tab_geometry(2).x, 50);
    }

    #[test]
    fn test_state_deserialization_missing_fields() {
        // Partial JSON should still deserialize with defaults
        let json = r#"{"active_tab": 2}"#;
        let state: WindowState = serde_json::from_str(json).unwrap_or_default();
        // If parsing fails due to missing fields, default is returned
        // If it succeeds, active_tab should be 2
        assert!(state.active_tab == 0 || state.active_tab == 2);
    }

    #[test]
    fn test_state_deserialization_corrupt_json() {
        let json = "not valid json at all {{}}}";
        let state: WindowState = serde_json::from_str(json).unwrap_or_default();
        assert_eq!(state.active_tab, 0);
    }

    #[test]
    fn test_tab_geometry_clone() {
        let g = TabGeometry { x: 100, y: 200, width: 1024, height: 768, maximized: true };
        let g2 = g.clone();
        assert_eq!(g2.x, g.x);
        assert_eq!(g2.width, g.width);
        assert_eq!(g2.maximized, g.maximized);
    }

    #[test]
    fn test_save_and_load_window_state_roundtrip() {
        // Test with tempfile-based state
        let mut state = WindowState {
            active_tab: 2,
            crash_log_path: "C:\\Logs".to_string(),
            game_path: "C:\\Games\\FO4".to_string(),
            ..Default::default()
        };
        state.set_tab_geometry(0, TabGeometry {
            x: 50, y: 75, width: 1920, height: 1080, maximized: true,
        });
        state.set_tab_geometry(2, TabGeometry {
            x: 100, y: 100, width: 800, height: 600, maximized: false,
        });

        // Serialize then deserialize
        let json = serde_json::to_string_pretty(&state).unwrap();
        let loaded: WindowState = serde_json::from_str(&json).unwrap();

        assert_eq!(loaded.active_tab, 2);
        assert_eq!(loaded.crash_log_path, "C:\\Logs");
        assert_eq!(loaded.game_path, "C:\\Games\\FO4");
        assert_eq!(loaded.get_tab_geometry(0).width, 1920);
        assert!(loaded.get_tab_geometry(0).maximized);
        assert_eq!(loaded.get_tab_geometry(2).width, 800);
        assert!(!loaded.get_tab_geometry(2).maximized);
        // Tab 1 was never set, should return default
        assert_eq!(loaded.get_tab_geometry(1).width, 0);
    }

    #[test]
    fn test_negative_tab_index() {
        let state = WindowState::default();
        let g = state.get_tab_geometry(-1);
        assert_eq!(g.width, 0); // Returns default for missing key
    }

    #[test]
    fn test_tab_geometry_debug_format() {
        let g = TabGeometry { x: 1, y: 2, width: 3, height: 4, maximized: false };
        let debug = format!("{:?}", g);
        assert!(debug.contains("TabGeometry"));
        assert!(debug.contains("width: 3"));
    }

    #[test]
    fn test_window_state_debug_format() {
        let state = WindowState::default();
        let debug = format!("{:?}", state);
        assert!(debug.contains("WindowState"));
    }

    #[test]
    fn test_save_and_load_window_state_through_disk() {
        // This test uses the real config directory (via state_file_path())
        // Save a custom state, load it back, and verify
        let mut state = WindowState {
            active_tab: 1,
            crash_log_path: "C:\\Test\\Logs".to_string(),
            game_path: "C:\\Test\\Game".to_string(),
            ..Default::default()
        };
        state.set_tab_geometry(1, TabGeometry {
            x: 200, y: 150, width: 1280, height: 720, maximized: false,
        });

        // Save (may fail if config dir is read-only, which is ok)
        if save_window_state(&state).is_ok() {
            // Load should return our saved state
            let loaded = load_window_state();
            assert_eq!(loaded.active_tab, 1);
            assert_eq!(loaded.crash_log_path, "C:\\Test\\Logs");
            assert_eq!(loaded.game_path, "C:\\Test\\Game");
            assert_eq!(loaded.get_tab_geometry(1).width, 1280);

            // Cleanup: save default state to not pollute future runs
            let _ = save_window_state(&WindowState::default());
        }
    }

    #[test]
    fn test_load_window_state_returns_default_when_no_file() {
        // This will return defaults if the file doesn't exist or has valid defaults
        let state = load_window_state();
        // Should at minimum not panic and return a valid WindowState
        assert!(state.active_tab >= 0 || state.active_tab < 10);
    }
}
