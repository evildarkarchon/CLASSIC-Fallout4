//! Window geometry persistence
//!
//! This module handles saving and restoring window size and position
//! between application sessions using JSON serialization. Window geometry
//! is stored in the user's config directory (`~/.config/CLASSIC/window_geometry.json`
//! on Linux, `%APPDATA%\CLASSIC\window_geometry.json` on Windows).

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

/// Window geometry configuration
///
/// Stores window dimensions and position for persistence between sessions.
/// Coordinates use screen pixels with the origin at the top-left corner.
///
/// # Special Values
///
/// A value of `-1` for `x` or `y` indicates the window should be centered
/// on screen in that dimension.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WindowGeometry {
    /// Window width in pixels
    pub width: i32,
    /// Window height in pixels
    pub height: i32,
    /// Window X position in screen coordinates, or -1 to center horizontally
    pub x: i32,
    /// Window Y position in screen coordinates, or -1 to center vertically
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

        fs::create_dir_all(&config_dir).context("Failed to create CLASSIC config directory")?;

        Ok(config_dir.join("window_geometry.json"))
    }

    /// Load window geometry from config file
    pub fn load() -> Self {
        Self::config_path()
            .and_then(|path| {
                let contents = fs::read_to_string(&path)
                    .with_context(|| format!("Failed to read geometry from {:?}", path))?;

                serde_json::from_str(&contents).context("Failed to parse geometry JSON")
            })
            .unwrap_or_else(|err| {
                tracing::debug!("Using default geometry: {}", err);
                Self::default()
            })
    }

    /// Save window geometry to config file
    pub fn save(&self) -> Result<()> {
        let path = Self::config_path()?;

        let json = serde_json::to_string_pretty(self).context("Failed to serialize geometry")?;

        fs::write(&path, json)
            .with_context(|| format!("Failed to write geometry to {:?}", path))?;

        tracing::debug!("Saved window geometry: {:?}", self);
        Ok(())
    }
}
