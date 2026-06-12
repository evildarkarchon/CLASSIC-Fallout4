//! PE file version extraction.
//!
//! This module extracts version information from Windows PE (Portable Executable) files
//! using the VS_VERSIONINFO resource. It supports both `.exe` and `.dll` files.
//!
//! # Overview
//!
//! PE files on Windows contain embedded version information in a `VS_VERSIONINFO` resource.
//! This module reads that resource and extracts the file version as a 4-part tuple
//! `(major, minor, patch, build)`.
//!
//! # Examples
//!
//! ```rust,no_run
//! use classic_version_core::pe_version::extract_pe_version;
//! use std::path::Path;
//!
//! let path = Path::new("C:\\Games\\Fallout4\\Fallout4.exe");
//! match extract_pe_version(path) {
//!     Ok((major, minor, patch, build)) => {
//!         println!("Version: {}.{}.{}.{}", major, minor, patch, build);
//!     }
//!     Err(e) => eprintln!("Failed to read PE version: {}", e),
//! }
//! ```

use std::path::Path;
use thiserror::Error;

/// Errors that can occur during PE version extraction.
#[derive(Error, Debug)]
pub enum PeVersionError {
    /// Failed to read the PE file from disk.
    #[error("Failed to read PE file '{path}': {source}")]
    IoError {
        /// The path that could not be read.
        path: std::path::PathBuf,
        /// The underlying I/O error.
        source: std::io::Error,
    },

    /// The file is not a valid PE file.
    #[error("Not a valid PE file: {0}")]
    InvalidPe(String),

    /// No version information found in the PE file.
    #[error("No version information found in PE file: {0}")]
    NoVersionInfo(std::path::PathBuf),

    /// The path does not point to a valid executable.
    #[error("Invalid executable path: {0}")]
    InvalidPath(std::path::PathBuf),
}

/// Result type for PE version operations.
pub type PeVersionResult<T> = Result<T, PeVersionError>;

/// Check if a path points to a valid executable or DLL file.
///
/// Validates that:
/// - The path exists
/// - The path is a file
/// - The extension is `.exe` or `.dll` (case-insensitive)
///
/// # Arguments
///
/// * `path` - The path to check
///
/// # Returns
///
/// `true` if the path is a valid executable or DLL, `false` otherwise.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_version_core::pe_version::is_valid_executable_path;
/// use std::path::Path;
///
/// assert!(is_valid_executable_path(Path::new("C:\\Windows\\notepad.exe")));
/// assert!(!is_valid_executable_path(Path::new("readme.txt")));
/// ```
#[must_use]
pub fn is_valid_executable_path(path: &Path) -> bool {
    if !path.exists() || !path.is_file() {
        return false;
    }

    match path.extension().and_then(|e| e.to_str()) {
        Some(ext) => {
            let lower = ext.to_lowercase();
            lower == "exe" || lower == "dll"
        }
        None => false,
    }
}

/// Extract the file version from a PE file's VS_VERSIONINFO resource.
///
/// Reads the PE file and extracts the `VS_FIXEDFILEINFO` structure from the
/// version resource. The version is returned as a 4-part tuple matching the
/// Windows FILEVERSION format.
///
/// # Arguments
///
/// * `path` - Path to the PE file (.exe or .dll)
///
/// # Returns
///
/// A tuple of `(major, minor, patch, build)` version components.
///
/// # Errors
///
/// Returns `PeVersionError` if:
/// - The file cannot be read
/// - The file is not a valid PE file
/// - No version resource is found
///
/// # Examples
///
/// ```rust,no_run
/// use classic_version_core::pe_version::extract_pe_version;
/// use std::path::Path;
///
/// let (major, minor, patch, build) = extract_pe_version(
///     Path::new("C:\\Games\\Fallout4\\Fallout4.exe")
/// )?;
/// assert_eq!(major, 1);
/// # Ok::<(), classic_version_core::pe_version::PeVersionError>(())
/// ```
pub fn extract_pe_version(path: &Path) -> PeVersionResult<(u16, u16, u16, u16)> {
    if !is_valid_executable_path(path) {
        return Err(PeVersionError::InvalidPath(path.to_path_buf()));
    }

    // Read the file contents
    let file_data = std::fs::read(path).map_err(|e| PeVersionError::IoError {
        path: path.to_path_buf(),
        source: e,
    })?;

    // Parse as PE file (handles both PE32 and PE64 automatically)
    let pe = pelite::PeFile::from_bytes(&file_data)
        .map_err(|e| PeVersionError::InvalidPe(format!("{}: {}", path.display(), e)))?;

    // The Wrap type's resources() method unifies PE32/PE64 into a common Resources type
    let resources = pe.resources().map_err(|e| {
        PeVersionError::InvalidPe(format!("No resources in {}: {}", path.display(), e))
    })?;

    let version_info = resources
        .version_info()
        .map_err(|_| PeVersionError::NoVersionInfo(path.to_path_buf()))?;

    let fixed = version_info
        .fixed()
        .ok_or_else(|| PeVersionError::NoVersionInfo(path.to_path_buf()))?;

    Ok((
        fixed.dwFileVersion.Major,
        fixed.dwFileVersion.Minor,
        fixed.dwFileVersion.Patch,
        fixed.dwFileVersion.Build,
    ))
}

#[cfg(test)]
#[path = "pe_version_tests.rs"]
mod tests;
