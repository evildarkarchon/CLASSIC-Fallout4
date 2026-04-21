//! INI file parsing and validation.
//!
//! This module provides functionality for parsing and validating INI configuration files,
//! particularly for Bethesda game settings (Fallout4.ini, Fallout4Prefs.ini, etc.).
//!
//! # Features
//!
//! - Parse INI files with section/key/value structure
//! - Validate INI file existence and structure
//! - Check for required sections and keys
//! - Get and validate configuration values
//! - Case-insensitive section/key matching
//!
//! # Case Normalization
//!
//! The underlying `configparser` crate normalizes all section and key names to lowercase.
//! This means:
//! - All lookups are automatically case-insensitive
//! - `sections()` returns lowercase section names
//! - `keys()` returns lowercase key names
//! - `get()`, `has_section()`, and `has_key()` accept any case for section/key names
//!
//! # Examples
//!
//! ```rust,no_run
//! use classic_path_core::IniFile;
//! use std::path::Path;
//!
//! let ini_path = Path::new("C:\\Users\\Name\\Documents\\My Games\\Fallout4\\Fallout4.ini");
//! let ini = IniFile::load(ini_path)?;
//!
//! // Check if section exists (case-insensitive)
//! if ini.has_section("Archive") {  // Works with "archive", "ARCHIVE", etc.
//!     // Get a value (case-insensitive)
//!     if let Some(value) = ini.get("Archive", "sResourceDataDirsFinal") {
//!         println!("Resource dirs: {}", value);
//!     }
//! }
//! # Ok::<(), Box<dyn std::error::Error>>(())
//! ```

use crate::error::{DocsPathError, DocsPathResult};
use configparser::ini::Ini;
use std::path::{Path, PathBuf};

/// Represents a parsed INI file with case-insensitive lookups.
///
/// This struct wraps the `configparser::ini::Ini` type and provides a more ergonomic
/// API for working with Bethesda game configuration files.
///
/// Note: The `configparser` crate automatically normalizes all section names to lowercase,
/// so all section lookups are case-insensitive by default.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::IniFile;
/// use std::path::Path;
///
/// let ini = IniFile::load(Path::new("Fallout4.ini"))?;
/// let value = ini.get("Display", "iSize W");
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
#[derive(Debug, Clone)]
pub struct IniFile {
    /// Path to the INI file
    path: PathBuf,

    /// Parsed INI data (section names are normalized to lowercase)
    data: Ini,
}

impl IniFile {
    /// Load and parse an INI file.
    ///
    /// # Arguments
    ///
    /// * `path` - Path to the INI file to load
    ///
    /// # Returns
    ///
    /// A parsed `IniFile` instance, or an error if loading/parsing fails.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::IniFile;
    /// use std::path::Path;
    ///
    /// let ini = IniFile::load(Path::new("Fallout4.ini"))?;
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn load(path: &Path) -> DocsPathResult<Self> {
        if !path.exists() {
            return Err(DocsPathError::IniParseError {
                path: path.to_path_buf(),
                reason: "File does not exist".to_string(),
            });
        }

        let mut data = Ini::new();
        data.load(path.to_str().ok_or_else(|| DocsPathError::IniParseError {
            path: path.to_path_buf(),
            reason: "Invalid path encoding".to_string(),
        })?)
        .map_err(|e| DocsPathError::IniParseError {
            path: path.to_path_buf(),
            reason: format!("Failed to parse INI: {}", e),
        })?;

        Ok(Self {
            path: path.to_path_buf(),
            data,
        })
    }

    /// Get the path to the INI file.
    ///
    /// # Returns
    ///
    /// Reference to the INI file path.
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Check if a section exists in the INI file (case-insensitive).
    ///
    /// # Arguments
    ///
    /// * `section` - The section name to check (case-insensitive)
    ///
    /// # Returns
    ///
    /// `true` if the section exists, `false` otherwise.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::IniFile;
    /// use std::path::Path;
    ///
    /// let ini = IniFile::load(Path::new("Fallout4.ini"))?;
    /// if ini.has_section("Display") {  // Works with any case
    ///     println!("Display section found");
    /// }
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn has_section(&self, section: &str) -> bool {
        let section_lower = section.to_lowercase();
        self.data.sections().iter().any(|s| s == &section_lower)
    }

    /// Check if a key exists in a section (case-insensitive).
    ///
    /// # Arguments
    ///
    /// * `section` - The section name
    /// * `key` - The key name to check
    ///
    /// # Returns
    ///
    /// `true` if the key exists in the section, `false` otherwise.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::IniFile;
    /// use std::path::Path;
    ///
    /// let ini = IniFile::load(Path::new("Fallout4.ini"))?;
    /// if ini.has_key("Display", "iSize W") {
    ///     println!("Window width setting found");
    /// }
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn has_key(&self, section: &str, key: &str) -> bool {
        self.get(section, key).is_some()
    }

    /// Get a value from the INI file (case-insensitive section lookup).
    ///
    /// # Arguments
    ///
    /// * `section` - The section name (case-insensitive)
    /// * `key` - The key name
    ///
    /// # Returns
    ///
    /// The value as a string if found, or `None` if the section or key doesn't exist.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::IniFile;
    /// use std::path::Path;
    ///
    /// let ini = IniFile::load(Path::new("Fallout4.ini"))?;
    /// if let Some(width) = ini.get("Display", "iSize W") {
    ///     println!("Window width: {}", width);
    /// }
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn get(&self, section: &str, key: &str) -> Option<String> {
        let section_lower = section.to_lowercase();
        self.data.get(&section_lower, key)
    }

    /// Get a value as an integer.
    ///
    /// # Arguments
    ///
    /// * `section` - The section name
    /// * `key` - The key name
    ///
    /// # Returns
    ///
    /// The value parsed as an `i32`, or `None` if not found or not a valid integer.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::IniFile;
    /// use std::path::Path;
    ///
    /// let ini = IniFile::load(Path::new("Fallout4.ini"))?;
    /// if let Some(width) = ini.get_int("Display", "iSize W") {
    ///     println!("Window width: {} pixels", width);
    /// }
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn get_int(&self, section: &str, key: &str) -> Option<i32> {
        self.get(section, key).and_then(|v| v.parse().ok())
    }

    /// Get a value as a boolean.
    ///
    /// Recognizes: "1", "true", "yes", "on" as true; "0", "false", "no", "off" as false.
    /// Case-insensitive.
    ///
    /// # Arguments
    ///
    /// * `section` - The section name
    /// * `key` - The key name
    ///
    /// # Returns
    ///
    /// The value parsed as a `bool`, or `None` if not found or not a valid boolean.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::IniFile;
    /// use std::path::Path;
    ///
    /// let ini = IniFile::load(Path::new("Fallout4.ini"))?;
    /// if let Some(enabled) = ini.get_bool("Archive", "bInvalidateOlderFiles") {
    ///     println!("Loose files enabled: {}", enabled);
    /// }
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn get_bool(&self, section: &str, key: &str) -> Option<bool> {
        let value = self.get(section, key)?;
        let value_lower = value.to_lowercase();
        match value_lower.as_str() {
            "1" | "true" | "yes" | "on" => Some(true),
            "0" | "false" | "no" | "off" => Some(false),
            _ => None,
        }
    }

    /// List all sections in the INI file.
    ///
    /// Note: Section names are returned in lowercase as normalized by the configparser crate.
    ///
    /// # Returns
    ///
    /// A vector of section names (all lowercase).
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::IniFile;
    /// use std::path::Path;
    ///
    /// let ini = IniFile::load(Path::new("Fallout4.ini"))?;
    /// for section in ini.sections() {
    ///     println!("Section: {}", section);
    /// }
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn sections(&self) -> Vec<String> {
        self.data.sections()
    }

    /// List all keys in a section.
    ///
    /// # Arguments
    ///
    /// * `section` - The section name (case-insensitive)
    ///
    /// # Returns
    ///
    /// A vector of key names, or an empty vector if the section doesn't exist.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::IniFile;
    /// use std::path::Path;
    ///
    /// let ini = IniFile::load(Path::new("Fallout4.ini"))?;
    /// for key in ini.keys("Display") {
    ///     println!("Key: {}", key);
    /// }
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn keys(&self, section: &str) -> Vec<String> {
        let section_lower = section.to_lowercase();
        if let Some(keys) = self.data.get_map_ref().get(&section_lower) {
            return keys.keys().cloned().collect();
        }
        Vec::new()
    }

    /// Validate that required sections exist.
    ///
    /// # Arguments
    ///
    /// * `required_sections` - List of section names that must exist
    ///
    /// # Returns
    ///
    /// `Ok(())` if all sections exist, or an error describing the missing section.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::IniFile;
    /// use std::path::Path;
    ///
    /// let ini = IniFile::load(Path::new("Fallout4.ini"))?;
    /// ini.validate_sections(&["Display", "Archive", "General"])?;
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn validate_sections(&self, required_sections: &[&str]) -> DocsPathResult<()> {
        for section in required_sections {
            if !self.has_section(section) {
                return Err(DocsPathError::IniValidationFailed {
                    ini: self.path.display().to_string(),
                    reason: format!("Required section '{}' not found", section),
                });
            }
        }
        Ok(())
    }

    /// Validate that required keys exist in a section.
    ///
    /// # Arguments
    ///
    /// * `section` - The section name
    /// * `required_keys` - List of key names that must exist in the section
    ///
    /// # Returns
    ///
    /// `Ok(())` if all keys exist, or an error describing the missing key.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::IniFile;
    /// use std::path::Path;
    ///
    /// let ini = IniFile::load(Path::new("Fallout4.ini"))?;
    /// ini.validate_keys("Display", &["iSize W", "iSize H"])?;
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn validate_keys(&self, section: &str, required_keys: &[&str]) -> DocsPathResult<()> {
        if !self.has_section(section) {
            return Err(DocsPathError::IniValidationFailed {
                ini: self.path.display().to_string(),
                reason: format!("Section '{}' not found", section),
            });
        }

        for key in required_keys {
            if !self.has_key(section, key) {
                return Err(DocsPathError::IniValidationFailed {
                    ini: self.path.display().to_string(),
                    reason: format!("Required key '{}' not found in section '{}'", key, section),
                });
            }
        }
        Ok(())
    }
}

#[cfg(test)]
#[path = "ini_parser_tests.rs"]
mod tests;
