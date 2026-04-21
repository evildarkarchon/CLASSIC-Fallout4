//! Backup management for configuration files.
//!
//! This module provides functionality for creating and managing backups of game configuration
//! files (INI files, save games, etc.) with version tracking based on XSE log information.
//!
//! # Features
//!
//! - Extract version information from XSE logs
//! - Create versioned backups with metadata
//! - Validate backup integrity
//! - Manage backup directories
//!
//! # Examples
//!
//! ```rust,no_run
//! use classic_path_core::BackupManager;
//! use std::path::Path;
//!
//! // Create backup manager
//! let backup_dir = Path::new("C:\\Users\\Name\\Documents\\My Games\\Fallout4\\Backups");
//! let manager = BackupManager::new(backup_dir);
//!
//! // Extract version from XSE log
//! let xse_log = Path::new("C:\\Users\\Name\\Documents\\My Games\\Fallout4\\F4SE\\f4se.log");
//! let version = manager.extract_version_from_xse_log(xse_log)?;
//!
//! // Create backup with version metadata
//! let ini_file = Path::new("C:\\Users\\Name\\Documents\\My Games\\Fallout4\\Fallout4.ini");
//! manager.create_backup(ini_file, &version)?;
//! # Ok::<(), Box<dyn std::error::Error>>(())
//! ```

use crate::error::{BackupError, BackupResult};
use regex::Regex;
use std::fs;
use std::path::{Path, PathBuf};

/// Version information extracted from XSE log.
///
/// Contains the full version string and parsed components for creating
/// structured backup directories.
///
/// # Examples
///
/// ```rust
/// use classic_path_core::XseVersion;
///
/// let version = XseVersion::new("1.10.163.0");
/// assert_eq!(version.full_version(), "1.10.163.0");
/// ```
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct XseVersion {
    /// Full version string (e.g., "1.10.163.0")
    full_version: String,
}

impl XseVersion {
    /// Create a new XseVersion from a version string.
    ///
    /// # Arguments
    ///
    /// * `version` - The full version string (e.g., "1.10.163.0")
    ///
    /// # Returns
    ///
    /// A new XseVersion instance.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_path_core::XseVersion;
    ///
    /// let version = XseVersion::new("1.10.163.0");
    /// assert_eq!(version.full_version(), "1.10.163.0");
    /// ```
    pub fn new(version: impl Into<String>) -> Self {
        Self {
            full_version: version.into(),
        }
    }

    /// Get the full version string.
    ///
    /// # Returns
    ///
    /// The complete version string (e.g., "1.10.163.0").
    pub fn full_version(&self) -> &str {
        &self.full_version
    }

    /// Get a sanitized version suitable for directory names.
    ///
    /// Replaces dots with underscores to create valid directory names.
    ///
    /// # Returns
    ///
    /// A sanitized version string (e.g., "1_10_163_0").
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_path_core::XseVersion;
    ///
    /// let version = XseVersion::new("1.10.163.0");
    /// assert_eq!(version.sanitized(), "1_10_163_0");
    /// ```
    pub fn sanitized(&self) -> String {
        self.full_version.replace('.', "_")
    }
}

/// Backup manager for configuration files.
///
/// Handles creation and management of versioned backups with metadata
/// extracted from XSE logs.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::BackupManager;
/// use std::path::Path;
///
/// let backup_dir = Path::new("Backups");
/// let manager = BackupManager::new(backup_dir);
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
#[derive(Debug, Clone)]
pub struct BackupManager {
    /// Root directory for all backups
    backup_root: PathBuf,
}

impl BackupManager {
    /// Create a new BackupManager.
    ///
    /// # Arguments
    ///
    /// * `backup_root` - Root directory where backups will be stored
    ///
    /// # Returns
    ///
    /// A new BackupManager instance.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_path_core::BackupManager;
    /// use std::path::Path;
    ///
    /// let manager = BackupManager::new("Backups");
    /// ```
    pub fn new(backup_root: impl Into<PathBuf>) -> Self {
        Self {
            backup_root: backup_root.into(),
        }
    }

    /// Extract version information from an XSE log file.
    ///
    /// Parses the XSE log to find the version line and extract the version number.
    ///
    /// # Arguments
    ///
    /// * `xse_log_path` - Path to the XSE log file (e.g., "f4se.log")
    ///
    /// # Returns
    ///
    /// The extracted version information.
    ///
    /// # Errors
    ///
    /// Returns error if:
    /// - Log file doesn't exist
    /// - Log file can't be read
    /// - Version string not found in log
    /// - Version format is invalid
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::BackupManager;
    /// use std::path::Path;
    ///
    /// let manager = BackupManager::new("Backups");
    /// let xse_log = Path::new("f4se.log");
    ///
    /// match manager.extract_version_from_xse_log(xse_log) {
    ///     Ok(version) => println!("Version: {}", version.full_version()),
    ///     Err(e) => println!("Failed to extract version: {}", e),
    /// }
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn extract_version_from_xse_log(&self, xse_log_path: &Path) -> BackupResult<XseVersion> {
        // Check if log file exists
        if !xse_log_path.exists() {
            return Err(BackupError::XseLogNotFound(xse_log_path.to_path_buf()));
        }

        // Read log file
        let content = fs::read_to_string(xse_log_path)?;

        // Parse version from log
        // Looking for lines like: "F4SE version = 0.6.23"
        // or "runtime version = 1.10.163.0"
        let version_regex =
            Regex::new(r"(?i)(?:runtime )?version\s*[=:]\s*(\d+(?:\.\d+)+)").unwrap();

        for line in content.lines() {
            if let Some(captures) = version_regex.captures(line) {
                if let Some(version_match) = captures.get(1) {
                    let version_str = version_match.as_str();
                    return Ok(XseVersion::new(version_str));
                }
            }
        }

        // Version not found
        Err(BackupError::VersionNotFound)
    }

    /// Create a backup of a file with version metadata.
    ///
    /// Creates a versioned backup directory structure and copies the file into it.
    /// Directory structure: `backup_root/version_sanitized/filename`
    ///
    /// # Arguments
    ///
    /// * `source_file` - Path to the file to back up
    /// * `version` - Version information for organizing the backup
    ///
    /// # Returns
    ///
    /// Path to the created backup file.
    ///
    /// # Errors
    ///
    /// Returns error if:
    /// - Source file doesn't exist
    /// - Backup directory can't be created
    /// - File copy fails
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::{BackupManager, XseVersion};
    /// use std::path::Path;
    ///
    /// let manager = BackupManager::new("Backups");
    /// let version = XseVersion::new("1.10.163.0");
    /// let ini_file = Path::new("Fallout4.ini");
    ///
    /// let backup_path = manager.create_backup(ini_file, &version)?;
    /// println!("Backup created at: {}", backup_path.display());
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn create_backup(&self, source_file: &Path, version: &XseVersion) -> BackupResult<PathBuf> {
        // Check source file exists
        if !source_file.exists() {
            return Err(BackupError::SourceNotFound(source_file.to_path_buf()));
        }

        // Create versioned backup directory
        let version_dir = self.backup_root.join(version.sanitized());
        fs::create_dir_all(&version_dir).map_err(|e| BackupError::CreateDirectoryFailed {
            path: version_dir.clone(),
            source: e,
        })?;

        // Determine destination path
        let file_name = source_file
            .file_name()
            .ok_or_else(|| BackupError::InvalidVersionFormat("No filename".to_string()))?;
        let dest_path = version_dir.join(file_name);

        // Copy file to backup
        fs::copy(source_file, &dest_path).map_err(|e| BackupError::CopyFileFailed {
            src: source_file.to_path_buf(),
            dst: dest_path.clone(),
            source: e,
        })?;

        Ok(dest_path)
    }

    /// Get the backup root directory.
    ///
    /// # Returns
    ///
    /// Reference to the backup root path.
    pub fn backup_root(&self) -> &Path {
        &self.backup_root
    }

    /// List all version directories in the backup root.
    ///
    /// # Returns
    ///
    /// Vector of version directory names, or empty vector if backup root doesn't exist.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::BackupManager;
    ///
    /// let manager = BackupManager::new("Backups");
    /// for version in manager.list_versions()? {
    ///     println!("Backup version: {}", version);
    /// }
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn list_versions(&self) -> BackupResult<Vec<String>> {
        if !self.backup_root.exists() {
            return Ok(Vec::new());
        }

        let mut versions = Vec::new();
        let entries = fs::read_dir(&self.backup_root)?;

        for entry in entries {
            let entry = entry?;
            if entry.path().is_dir() {
                if let Some(name) = entry.file_name().to_str() {
                    versions.push(name.to_string());
                }
            }
        }

        versions.sort();
        Ok(versions)
    }

    /// Get the path to a specific version's backup directory.
    ///
    /// # Arguments
    ///
    /// * `version` - The version to get the path for
    ///
    /// # Returns
    ///
    /// Path to the version's backup directory.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_path_core::{BackupManager, XseVersion};
    ///
    /// let manager = BackupManager::new("Backups");
    /// let version = XseVersion::new("1.10.163.0");
    /// let version_dir = manager.get_version_path(&version);
    /// ```
    pub fn get_version_path(&self, version: &XseVersion) -> PathBuf {
        self.backup_root.join(version.sanitized())
    }
}

#[cfg(test)]
#[path = "backup_tests.rs"]
mod tests;
