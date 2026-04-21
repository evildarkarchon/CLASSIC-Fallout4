use std::fs;
use std::path::PathBuf;

use classic_config_core::{ClassicConfig, YamlSource};
use classic_shared_core::get_runtime;
use directories::ProjectDirs;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WindowState {
    pub active_tab: u8,
    pub results_panel_width: u16,
    pub sort_ascending: bool,
}

impl Default for WindowState {
    fn default() -> Self {
        Self {
            active_tab: 0,
            results_panel_width: 30,
            sort_ascending: false,
        }
    }
}

pub fn state_file_path() -> Option<PathBuf> {
    ProjectDirs::from("com", "classic", "classic-tui")
        .map(|dirs| dirs.config_dir().join("state.json"))
}

pub fn load_window_state() -> WindowState {
    let Some(path) = state_file_path() else {
        return WindowState::default();
    };

    if !path.exists() {
        return WindowState::default();
    }

    fs::read_to_string(path)
        .ok()
        .and_then(|content| serde_json::from_str::<WindowState>(&content).ok())
        .unwrap_or_default()
}

pub fn save_window_state(state: &WindowState) -> Result<(), Box<dyn std::error::Error>> {
    let Some(path) = state_file_path() else {
        return Err("Could not determine config directory".into());
    };

    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }

    let json = serde_json::to_string_pretty(state)?;
    fs::write(path, json)?;
    Ok(())
}

pub fn settings_file_path() -> PathBuf {
    YamlSource::Settings.path("Fallout4")
}

pub fn load_settings() -> ClassicConfig {
    let path = settings_file_path();
    if !path.exists() {
        return ClassicConfig::default();
    }

    match get_runtime().block_on(ClassicConfig::load_from_yaml(&path)) {
        Ok(config) => config,
        Err(error) => {
            tracing::warn!("Failed to load settings, using defaults: {error}");
            ClassicConfig::default()
        }
    }
}

pub fn save_settings(config: &ClassicConfig) -> Result<(), Box<dyn std::error::Error>> {
    let path = settings_file_path();
    get_runtime().block_on(config.save_to_yaml(&path))?;
    Ok(())
}
