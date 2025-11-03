//! Script Extender (XSE) utilities for CLASSIC.
//!
//! This crate provides comprehensive XSE handling for Bethesda games,
//! including version detection, file location, and status checking.
//!
//! # Features
//!
//! - **XSE Type Detection**: Identify F4SE, SKSE, SFSE, etc.
//! - **Version Detection**: Parse and validate XSE versions
//! - **File Location**: Find XSE executables and DLLs
//! - **Status Checking**: Verify installation and compatibility
//! - **Version Comparison**: Check if XSE version is compatible
//!
//! # Examples
//!
//! ```rust
//! use classic_xse_core::{XseType, detect_xse_version};
//! use std::path::Path;
//!
//! // Detect F4SE version from file path
//! if let Ok(version) = detect_xse_version(Path::new("f4se_loader.exe"), XseType::F4SE) {
//!     println!("F4SE version: {}", version);
//! }
//! ```

use classic_constants_core::GameId;
use semver::Version;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use thiserror::Error;

// Re-export version utilities
pub use classic_version_core::{compare_versions, parse_version, try_parse_version};

/// XSE management errors.
#[derive(Error, Debug)]
pub enum XseError {
    /// XSE not found.
    #[error("XSE not found at: {0}")]
    NotFound(PathBuf),

    /// Invalid XSE type.
    #[error("Invalid XSE type: {0}")]
    InvalidType(String),

    /// Version detection failed.
    #[error("Failed to detect XSE version: {0}")]
    VersionDetectionFailed(String),

    /// Version incompatibility.
    #[error("XSE version {found} is incompatible with game version {expected}")]
    IncompatibleVersion {
        /// The found XSE version
        found: String,
        /// The expected/compatible game version
        expected: String,
    },

    /// I/O error.
    #[error("I/O error: {source}")]
    IoError {
        /// The underlying I/O error
        #[from]
        source: std::io::Error,
    },

    /// Path error.
    #[error("Path error: {0}")]
    PathError(#[from] classic_path_core::PathError),
}

/// Result type for XSE operations.
pub type XseResult<T> = Result<T, XseError>;

/// Script Extender type enumeration.
///
/// Represents the various script extenders for different Bethesda games.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum XseType {
    /// Fallout 4 Script Extender (F4SE)
    F4SE,
    /// Fallout 4 VR Script Extender (F4SEVR)
    F4SEVR,
    /// Skyrim Script Extender (SKSE)
    SKSE,
    /// Skyrim Special Edition Script Extender (SKSE64)
    SKSE64,
    /// Skyrim VR Script Extender (SKSEVR)
    SKSEVR,
    /// Starfield Script Extender (SFSE)
    SFSE,
}

impl XseType {
    /// Get the XSE type name as a string.
    ///
    /// # Returns
    ///
    /// A static string representing the XSE type.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::XseType;
    ///
    /// assert_eq!(XseType::F4SE.as_str(), "F4SE");
    /// assert_eq!(XseType::SKSE64.as_str(), "SKSE64");
    /// ```
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::F4SE => "F4SE",
            Self::F4SEVR => "F4SEVR",
            Self::SKSE => "SKSE",
            Self::SKSE64 => "SKSE64",
            Self::SKSEVR => "SKSEVR",
            Self::SFSE => "SFSE",
        }
    }

    /// Parse an XSE type from a string.
    ///
    /// # Arguments
    ///
    /// * `s` - The string to parse (case-insensitive)
    ///
    /// # Returns
    ///
    /// The corresponding `XseType`, or an error if unknown.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::XseType;
    ///
    /// assert_eq!(XseType::from_str("f4se").unwrap(), XseType::F4SE);
    /// assert_eq!(XseType::from_str("SKSE64").unwrap(), XseType::SKSE64);
    /// assert!(XseType::from_str("unknown").is_err());
    /// ```
    pub fn from_str(s: &str) -> XseResult<Self> {
        match s.to_uppercase().as_str() {
            "F4SE" => Ok(Self::F4SE),
            "F4SEVR" => Ok(Self::F4SEVR),
            "SKSE" => Ok(Self::SKSE),
            "SKSE64" => Ok(Self::SKSE64),
            "SKSEVR" => Ok(Self::SKSEVR),
            "SFSE" => Ok(Self::SFSE),
            _ => Err(XseError::InvalidType(s.to_string())),
        }
    }

    /// Get the XSE type for a game ID.
    ///
    /// # Arguments
    ///
    /// * `game_id` - The game identifier
    ///
    /// # Returns
    ///
    /// The corresponding `XseType`.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::XseType;
    /// use classic_constants_core::GameId;
    ///
    /// assert_eq!(XseType::from_game_id(GameId::Fallout4), XseType::F4SE);
    /// assert_eq!(XseType::from_game_id(GameId::Fallout4VR), XseType::F4SEVR);
    /// assert_eq!(XseType::from_game_id(GameId::Skyrim), XseType::SKSE64);
    /// ```
    #[must_use]
    pub fn from_game_id(game_id: GameId) -> Self {
        match game_id {
            GameId::Fallout4 => Self::F4SE,
            GameId::Fallout4VR => Self::F4SEVR,
            GameId::Skyrim => Self::SKSE64,
            GameId::Starfield => Self::SFSE,
        }
    }

    /// Get the loader executable name for this XSE type.
    ///
    /// # Returns
    ///
    /// The executable filename (e.g., "f4se_loader.exe").
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::XseType;
    ///
    /// assert_eq!(XseType::F4SE.loader_name(), "f4se_loader.exe");
    /// assert_eq!(XseType::SKSE64.loader_name(), "skse64_loader.exe");
    /// ```
    #[must_use]
    pub fn loader_name(self) -> &'static str {
        match self {
            Self::F4SE => "f4se_loader.exe",
            Self::F4SEVR => "f4sevr_loader.exe",
            Self::SKSE => "skse_loader.exe",
            Self::SKSE64 => "skse64_loader.exe",
            Self::SKSEVR => "sksevr_loader.exe",
            Self::SFSE => "sfse_loader.exe",
        }
    }

    /// Get the DLL name for this XSE type.
    ///
    /// # Returns
    ///
    /// The DLL filename (e.g., "f4se_1_10_163.dll").
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::XseType;
    ///
    /// assert_eq!(XseType::F4SE.dll_prefix(), "f4se_");
    /// assert_eq!(XseType::SKSE64.dll_prefix(), "skse64_");
    /// ```
    #[must_use]
    pub fn dll_prefix(self) -> &'static str {
        match self {
            Self::F4SE => "f4se_",
            Self::F4SEVR => "f4sevr_",
            Self::SKSE => "skse_",
            Self::SKSE64 => "skse64_",
            Self::SKSEVR => "sksevr_",
            Self::SFSE => "sfse_",
        }
    }
}

// ============================================================================
// XSE Information
// ============================================================================

/// XSE installation information.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct XseInfo {
    /// XSE type
    pub xse_type: XseType,
    /// Installation path
    pub path: PathBuf,
    /// Detected version
    pub version: Option<Version>,
    /// Whether XSE is installed
    pub installed: bool,
}

impl XseInfo {
    /// Create a new XseInfo.
    ///
    /// # Arguments
    ///
    /// * `xse_type` - The XSE type
    /// * `path` - The installation path
    ///
    /// # Returns
    ///
    /// A new `XseInfo` instance.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::{XseInfo, XseType};
    /// use std::path::PathBuf;
    ///
    /// let info = XseInfo::new(XseType::F4SE, PathBuf::from("C:\\Games\\Fallout4"));
    /// assert_eq!(info.xse_type, XseType::F4SE);
    /// ```
    #[must_use]
    pub fn new(xse_type: XseType, path: PathBuf) -> Self {
        Self {
            xse_type,
            path,
            version: None,
            installed: false,
        }
    }

    /// Create a new XseInfo with version.
    ///
    /// # Arguments
    ///
    /// * `xse_type` - The XSE type
    /// * `path` - The installation path
    /// * `version` - The detected version
    /// * `installed` - Whether XSE is installed
    ///
    /// # Returns
    ///
    /// A new `XseInfo` instance with version.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::{XseInfo, XseType};
    /// use std::path::PathBuf;
    /// use semver::Version;
    ///
    /// let info = XseInfo::with_version(
    ///     XseType::F4SE,
    ///     PathBuf::from("C:\\Games\\Fallout4"),
    ///     Some(Version::new(0, 6, 23)),
    ///     true
    /// );
    /// assert!(info.installed);
    /// ```
    #[must_use]
    pub fn with_version(
        xse_type: XseType,
        path: PathBuf,
        version: Option<Version>,
        installed: bool,
    ) -> Self {
        Self {
            xse_type,
            path,
            version,
            installed,
        }
    }

    /// Check if the XSE is installed at the path.
    ///
    /// # Returns
    ///
    /// True if the XSE loader executable exists.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_xse_core::{XseInfo, XseType};
    /// use std::path::PathBuf;
    ///
    /// let info = XseInfo::new(XseType::F4SE, PathBuf::from("C:\\Games\\Fallout4"));
    /// if info.check_installed() {
    ///     println!("F4SE is installed");
    /// }
    /// ```
    pub fn check_installed(&self) -> bool {
        let loader_path = self.path.join(self.xse_type.loader_name());
        loader_path.exists() && loader_path.is_file()
    }

    /// Get the full path to the XSE loader executable.
    ///
    /// # Returns
    ///
    /// The full path to the loader executable.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::{XseInfo, XseType};
    /// use std::path::PathBuf;
    ///
    /// let info = XseInfo::new(XseType::F4SE, PathBuf::from("C:\\Games\\Fallout4"));
    /// let loader = info.loader_path();
    /// assert!(loader.ends_with("f4se_loader.exe"));
    /// ```
    #[must_use]
    pub fn loader_path(&self) -> PathBuf {
        self.path.join(self.xse_type.loader_name())
    }
}

// ============================================================================
// Version Detection
// ============================================================================

/// Detect XSE version from a loader executable.
///
/// Attempts to extract version information from the XSE loader filename
/// or by checking for version-specific DLL files.
///
/// # Arguments
///
/// * `loader_path` - Path to the XSE loader executable
/// * `xse_type` - The XSE type to detect
///
/// # Returns
///
/// The detected version, or an error if detection fails.
///
/// # Errors
///
/// Returns `XseError::NotFound` if the loader doesn't exist,
/// or `XseError::VersionDetectionFailed` if version cannot be determined.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_xse_core::{detect_xse_version, XseType};
/// use std::path::Path;
///
/// match detect_xse_version(Path::new("f4se_loader.exe"), XseType::F4SE) {
///     Ok(version) => println!("F4SE version: {}", version),
///     Err(e) => eprintln!("Detection failed: {}", e),
/// }
/// ```
pub fn detect_xse_version(loader_path: &Path, xse_type: XseType) -> XseResult<Version> {
    if !loader_path.exists() {
        return Err(XseError::NotFound(loader_path.to_path_buf()));
    }

    // Try to find version-specific DLL in the same directory
    if let Some(parent) = loader_path.parent() {
        let dll_prefix = xse_type.dll_prefix();

        // Look for DLLs matching the pattern (e.g., f4se_1_10_163.dll)
        if let Ok(entries) = std::fs::read_dir(parent) {
            for entry in entries.flatten() {
                let path = entry.path();
                if let Some(filename) = path.file_name().and_then(|n| n.to_str()) {
                    if filename.starts_with(dll_prefix) && filename.ends_with(".dll") {
                        // Extract version from filename
                        if let Some(version_str) = filename
                            .strip_prefix(dll_prefix)
                            .and_then(|s| s.strip_suffix(".dll"))
                        {
                            // Replace underscores with dots for version parsing
                            let version_dotted = version_str.replace('_', ".");
                            if let Ok(version) = parse_version(&version_dotted) {
                                return Ok(version);
                            }
                        }
                    }
                }
            }
        }
    }

    Err(XseError::VersionDetectionFailed(format!(
        "Could not detect version from {}",
        loader_path.display()
    )))
}

/// Check if XSE is installed in a directory.
///
/// # Arguments
///
/// * `game_path` - The game installation directory
/// * `xse_type` - The XSE type to check
///
/// # Returns
///
/// True if the XSE loader executable exists.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_xse_core::{is_xse_installed, XseType};
/// use std::path::Path;
///
/// if is_xse_installed(Path::new("C:\\Games\\Fallout4"), XseType::F4SE) {
///     println!("F4SE is installed");
/// }
/// ```
#[must_use]
pub fn is_xse_installed(game_path: &Path, xse_type: XseType) -> bool {
    let loader_path = game_path.join(xse_type.loader_name());
    loader_path.exists() && loader_path.is_file()
}

/// Get XSE information for a game directory.
///
/// # Arguments
///
/// * `game_path` - The game installation directory
/// * `xse_type` - The XSE type to check
///
/// # Returns
///
/// XseInfo with installation and version details.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_xse_core::{get_xse_info, XseType};
/// use std::path::Path;
///
/// let info = get_xse_info(Path::new("C:\\Games\\Fallout4"), XseType::F4SE);
/// if info.installed {
///     println!("F4SE version: {:?}", info.version);
/// }
/// ```
#[must_use]
pub fn get_xse_info(game_path: &Path, xse_type: XseType) -> XseInfo {
    let mut info = XseInfo::new(xse_type, game_path.to_path_buf());

    info.installed = info.check_installed();

    if info.installed {
        if let Ok(version) = detect_xse_version(&info.loader_path(), xse_type) {
            info.version = Some(version);
        }
    }

    info
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_xse_type_as_str() {
        assert_eq!(XseType::F4SE.as_str(), "F4SE");
        assert_eq!(XseType::SKSE64.as_str(), "SKSE64");
        assert_eq!(XseType::SFSE.as_str(), "SFSE");
    }

    #[test]
    fn test_xse_type_from_str() {
        assert_eq!(XseType::from_str("f4se").unwrap(), XseType::F4SE);
        assert_eq!(XseType::from_str("F4SE").unwrap(), XseType::F4SE);
        assert_eq!(XseType::from_str("skse64").unwrap(), XseType::SKSE64);
        assert!(XseType::from_str("unknown").is_err());
    }

    #[test]
    fn test_xse_type_from_game_id() {
        assert_eq!(XseType::from_game_id(GameId::Fallout4), XseType::F4SE);
        assert_eq!(XseType::from_game_id(GameId::Fallout4VR), XseType::F4SEVR);
        assert_eq!(XseType::from_game_id(GameId::Skyrim), XseType::SKSE64);
        assert_eq!(XseType::from_game_id(GameId::Starfield), XseType::SFSE);
    }

    #[test]
    fn test_xse_type_loader_name() {
        assert_eq!(XseType::F4SE.loader_name(), "f4se_loader.exe");
        assert_eq!(XseType::SKSE64.loader_name(), "skse64_loader.exe");
        assert_eq!(XseType::SFSE.loader_name(), "sfse_loader.exe");
    }

    #[test]
    fn test_xse_type_dll_prefix() {
        assert_eq!(XseType::F4SE.dll_prefix(), "f4se_");
        assert_eq!(XseType::SKSE64.dll_prefix(), "skse64_");
        assert_eq!(XseType::SFSE.dll_prefix(), "sfse_");
    }

    #[test]
    fn test_xse_info_new() {
        let info = XseInfo::new(XseType::F4SE, PathBuf::from("C:\\Games\\Fallout4"));
        assert_eq!(info.xse_type, XseType::F4SE);
        assert_eq!(info.path, PathBuf::from("C:\\Games\\Fallout4"));
        assert_eq!(info.version, None);
        assert!(!info.installed);
    }

    #[test]
    fn test_xse_info_with_version() {
        let info = XseInfo::with_version(
            XseType::F4SE,
            PathBuf::from("C:\\Games\\Fallout4"),
            Some(Version::new(0, 6, 23)),
            true,
        );
        assert_eq!(info.xse_type, XseType::F4SE);
        assert_eq!(info.version, Some(Version::new(0, 6, 23)));
        assert!(info.installed);
    }

    #[test]
    fn test_xse_info_loader_path() {
        let info = XseInfo::new(XseType::F4SE, PathBuf::from("C:\\Games\\Fallout4"));
        let loader = info.loader_path();
        assert!(loader.ends_with("f4se_loader.exe"));
    }
}
