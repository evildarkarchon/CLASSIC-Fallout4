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
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn create_test_ini(temp_dir: &Path, name: &str, content: &str) -> PathBuf {
        let ini_path = temp_dir.join(name);
        fs::write(&ini_path, content).unwrap();
        ini_path
    }

    #[test]
    fn test_load_ini() {
        let temp_dir = TempDir::new().unwrap();
        let ini_content = "[Display]\niSize W=1920\niSize H=1080\n";
        let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

        let ini = IniFile::load(&ini_path);
        assert!(ini.is_ok());
    }

    #[test]
    fn test_load_nonexistent() {
        let result = IniFile::load(Path::new("nonexistent.ini"));
        assert!(result.is_err());
        match result {
            Err(DocsPathError::IniParseError { reason, .. }) => {
                assert!(reason.contains("does not exist"));
            }
            _ => panic!("Expected IniParseError"),
        }
    }

    #[test]
    fn test_has_section() {
        let temp_dir = TempDir::new().unwrap();
        let ini_content = "[Display]\nkey=value\n[Archive]\nother=val\n";
        let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

        let ini = IniFile::load(&ini_path).unwrap();
        assert!(ini.has_section("Display"));
        assert!(ini.has_section("display")); // Case-insensitive
        assert!(ini.has_section("Archive"));
        assert!(!ini.has_section("NonExistent"));
    }

    #[test]
    fn test_has_key() {
        let temp_dir = TempDir::new().unwrap();
        let ini_content = "[Display]\niSize W=1920\niSize H=1080\n";
        let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

        let ini = IniFile::load(&ini_path).unwrap();
        assert!(ini.has_key("Display", "iSize W"));
        assert!(ini.has_key("display", "iSize W")); // Case-insensitive section
        assert!(!ini.has_key("Display", "NonExistent"));
    }

    #[test]
    fn test_get_value() {
        let temp_dir = TempDir::new().unwrap();
        let ini_content = "[Display]\niSize W=1920\niSize H=1080\n";
        let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

        let ini = IniFile::load(&ini_path).unwrap();
        assert_eq!(ini.get("Display", "iSize W"), Some("1920".to_string()));
        assert_eq!(ini.get("display", "iSize W"), Some("1920".to_string())); // Case-insensitive
        assert_eq!(ini.get("Display", "NonExistent"), None);
    }

    #[test]
    fn test_get_int() {
        let temp_dir = TempDir::new().unwrap();
        let ini_content = "[Display]\niSize W=1920\ninvalid=abc\n";
        let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

        let ini = IniFile::load(&ini_path).unwrap();
        assert_eq!(ini.get_int("Display", "iSize W"), Some(1920));
        assert_eq!(ini.get_int("Display", "invalid"), None);
        assert_eq!(ini.get_int("Display", "NonExistent"), None);
    }

    #[test]
    fn test_get_bool() {
        let temp_dir = TempDir::new().unwrap();
        let ini_content =
            "[Archive]\nbInvalidateOlderFiles=1\nbUseArchives=0\ntrue_val=true\nfalse_val=false\n";
        let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

        let ini = IniFile::load(&ini_path).unwrap();
        assert_eq!(ini.get_bool("Archive", "bInvalidateOlderFiles"), Some(true));
        assert_eq!(ini.get_bool("Archive", "bUseArchives"), Some(false));
        assert_eq!(ini.get_bool("Archive", "true_val"), Some(true));
        assert_eq!(ini.get_bool("Archive", "false_val"), Some(false));
    }

    #[test]
    fn test_sections() {
        let temp_dir = TempDir::new().unwrap();
        let ini_content = "[Display]\nkey=val\n[Archive]\nkey2=val2\n[General]\nkey3=val3\n";
        let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

        let ini = IniFile::load(&ini_path).unwrap();
        let sections = ini.sections();

        // configparser normalizes section names to lowercase
        assert_eq!(sections.len(), 3);
        assert!(sections.contains(&"display".to_string()));
        assert!(sections.contains(&"archive".to_string()));
        assert!(sections.contains(&"general".to_string()));
    }

    #[test]
    fn test_keys() {
        let temp_dir = TempDir::new().unwrap();
        let ini_content = "[Display]\niSize W=1920\niSize H=1080\nbFull Screen=0\n";
        let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

        let ini = IniFile::load(&ini_path).unwrap();
        let keys = ini.keys("Display");

        // configparser normalizes both section and key names to lowercase
        assert_eq!(keys.len(), 3);
        assert!(keys.contains(&"isize w".to_string()));
        assert!(keys.contains(&"isize h".to_string()));
        assert!(keys.contains(&"bfull screen".to_string()));
    }

    #[test]
    fn test_validate_sections() {
        let temp_dir = TempDir::new().unwrap();
        let ini_content = "[Display]\nkey=val\n[Archive]\nkey2=val2\n";
        let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

        let ini = IniFile::load(&ini_path).unwrap();

        // Should succeed
        assert!(ini.validate_sections(&["Display", "Archive"]).is_ok());

        // Should fail
        let result = ini.validate_sections(&["Display", "NonExistent"]);
        assert!(result.is_err());
        match result {
            Err(DocsPathError::IniValidationFailed { reason, .. }) => {
                assert!(reason.contains("NonExistent"));
            }
            _ => panic!("Expected IniValidationFailed"),
        }
    }

    #[test]
    fn test_validate_keys() {
        let temp_dir = TempDir::new().unwrap();
        let ini_content = "[Display]\niSize W=1920\niSize H=1080\n";
        let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

        let ini = IniFile::load(&ini_path).unwrap();

        // Should succeed
        assert!(
            ini.validate_keys("Display", &["iSize W", "iSize H"])
                .is_ok()
        );

        // Should fail - missing key
        let result = ini.validate_keys("Display", &["iSize W", "NonExistent"]);
        assert!(result.is_err());

        // Should fail - missing section
        let result = ini.validate_keys("NonExistent", &["key"]);
        assert!(result.is_err());
    }
}
