// Window geometry persistence
// Saves and restores window size and position between sessions

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WindowGeometry {
    pub width: i32,
    pub height: i32,
    pub x: i32,
    pub y: i32,
}

impl Default for WindowGeometry {
    fn default() -> Self {
        Self {
            width: 650,
            height: 350,
            x: -1, // -1 means center on screen
            y: -1,
        }
    }
}

impl WindowGeometry {
    /// Get the path to the geometry config file
    fn config_path() -> Result<PathBuf> {
        let config_dir = dirs::config_dir()
            .context("Failed to get config directory")?
            .join("CLASSIC");

        fs::create_dir_all(&config_dir)
            .context("Failed to create CLASSIC config directory")?;

        Ok(config_dir.join("window_geometry.json"))
    }

    /// Load window geometry from config file
    pub fn load() -> Self {
        Self::config_path()
            .and_then(|path| {
                let contents = fs::read_to_string(&path)
                    .with_context(|| format!("Failed to read geometry from {:?}", path))?;

                serde_json::from_str(&contents)
                    .context("Failed to parse geometry JSON")
            })
            .unwrap_or_else(|err| {
                tracing::debug!("Using default geometry: {}", err);
                Self::default()
            })
    }

    /// Save window geometry to config file
    pub fn save(&self) -> Result<()> {
        let path = Self::config_path()?;

        let json = serde_json::to_string_pretty(self)
            .context("Failed to serialize geometry")?;

        fs::write(&path, json)
            .with_context(|| format!("Failed to write geometry to {:?}", path))?;

        tracing::debug!("Saved window geometry: {:?}", self);
        Ok(())
    }
}