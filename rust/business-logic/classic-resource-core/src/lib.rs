//! Resource management for game files.
//!
//! This crate provides comprehensive resource handling for Bethesda game files,
//! including file type detection, path resolution, BA2 archive support, and
//! resource validation.
//!
//! # Features
//!
//! - **Resource Type Detection**: Identify file types (textures, meshes, scripts, etc.)
//! - **Path Resolution**: Resolve resource paths in game data directories
//! - **BA2 Archive Support**: Access resources in BA2 archives
//! - **Resource Enumeration**: List and filter resources
//! - **Resource Validation**: Check resource integrity and format
//!
//! # Examples
//!
//! ```rust
//! use classic_resource_core::{ResourceType, detect_resource_type};
//! use std::path::Path;
//!
//! // Detect resource type from extension
//! let path = Path::new("textures/armor.dds");
//! let resource_type = detect_resource_type(path);
//! assert_eq!(resource_type, ResourceType::Texture);
//! ```

use serde::{Deserialize, Serialize};
use std::convert::Infallible;
use std::path::{Path, PathBuf};
use std::str::FromStr;
use thiserror::Error;
use walkdir::WalkDir;

// Re-export path utilities
pub use classic_path_core::{PathError, PathResult};

/// Resource management errors.
#[derive(Error, Debug)]
pub enum ResourceError {
    /// Resource not found.
    #[error("Resource not found: {0}")]
    NotFound(PathBuf),

    /// Invalid resource type.
    #[error("Invalid resource type: {0}")]
    InvalidType(String),

    /// Archive access error.
    #[error("Archive error: {0}")]
    ArchiveError(String),

    /// I/O error.
    #[error("I/O error: {source}")]
    IoError {
        /// The underlying I/O error
        #[from]
        source: std::io::Error,
    },

    /// Path validation error.
    #[error("Path error: {0}")]
    PathError(#[from] PathError),
}

/// Result type for resource operations.
pub type ResourceResult<T> = Result<T, ResourceError>;

/// Resource type enumeration.
///
/// Represents the various types of game resources that can be managed.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ResourceType {
    /// Texture files (.dds, .png, .jpg)
    Texture,
    /// Mesh files (.nif)
    Mesh,
    /// Script files (.pex, .psc)
    Script,
    /// Plugin files (.esp, .esm, .esl)
    Plugin,
    /// Sound files (.wav, .xwm, .fuz)
    Sound,
    /// Animation files (.hkx)
    Animation,
    /// Interface files (.swf)
    Interface,
    /// String files (.strings, .dlstrings, .ilstrings)
    Strings,
    /// Archive files (.ba2, .bsa)
    Archive,
    /// INI configuration files (.ini)
    Config,
    /// Other/unknown file types
    Other,
}

impl ResourceType {
    /// Get the resource type name as a string.
    ///
    /// # Returns
    ///
    /// A static string representing the resource type.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_resource_core::ResourceType;
    ///
    /// assert_eq!(ResourceType::Texture.as_str(), "texture");
    /// assert_eq!(ResourceType::Plugin.as_str(), "plugin");
    /// ```
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Texture => "texture",
            Self::Mesh => "mesh",
            Self::Script => "script",
            Self::Plugin => "plugin",
            Self::Sound => "sound",
            Self::Animation => "animation",
            Self::Interface => "interface",
            Self::Strings => "strings",
            Self::Archive => "archive",
            Self::Config => "config",
            Self::Other => "other",
        }
    }

    /// Get all standard file extensions for this resource type.
    ///
    /// # Returns
    ///
    /// A slice of file extensions (without the dot).
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_resource_core::ResourceType;
    ///
    /// assert_eq!(ResourceType::Texture.extensions(), &["dds", "png", "jpg", "tga"]);
    /// assert_eq!(ResourceType::Plugin.extensions(), &["esp", "esm", "esl"]);
    /// ```
    #[must_use]
    pub fn extensions(self) -> &'static [&'static str] {
        match self {
            Self::Texture => &["dds", "png", "jpg", "tga"],
            Self::Mesh => &["nif"],
            Self::Script => &["pex", "psc"],
            Self::Plugin => &["esp", "esm", "esl"],
            Self::Sound => &["wav", "xwm", "fuz"],
            Self::Animation => &["hkx"],
            Self::Interface => &["swf"],
            Self::Strings => &["strings", "dlstrings", "ilstrings"],
            Self::Archive => &["ba2", "bsa"],
            Self::Config => &["ini"],
            Self::Other => &[],
        }
    }
}

impl FromStr for ResourceType {
    type Err = Infallible;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Ok(match s.to_lowercase().as_str() {
            "texture" => Self::Texture,
            "mesh" => Self::Mesh,
            "script" => Self::Script,
            "plugin" => Self::Plugin,
            "sound" => Self::Sound,
            "animation" => Self::Animation,
            "interface" => Self::Interface,
            "strings" => Self::Strings,
            "archive" => Self::Archive,
            "config" => Self::Config,
            _ => Self::Other,
        })
    }
}

// ============================================================================
// Resource Type Detection
// ============================================================================

/// Detect the resource type from a file path.
///
/// Examines the file extension to determine the resource type.
///
/// # Arguments
///
/// * `path` - The file path to examine
///
/// # Returns
///
/// The detected `ResourceType`.
///
/// # Examples
///
/// ```rust
/// use classic_resource_core::{ResourceType, detect_resource_type};
/// use std::path::Path;
///
/// let path = Path::new("textures/armor.dds");
/// assert_eq!(detect_resource_type(path), ResourceType::Texture);
///
/// let path = Path::new("scripts/myquest.pex");
/// assert_eq!(detect_resource_type(path), ResourceType::Script);
/// ```
#[must_use]
pub fn detect_resource_type(path: &Path) -> ResourceType {
    if let Some(ext) = path.extension() {
        if let Some(ext_str) = ext.to_str() {
            let ext_lower = ext_str.to_lowercase();

            // Check each resource type's extensions
            if ResourceType::Texture
                .extensions()
                .contains(&ext_lower.as_str())
            {
                return ResourceType::Texture;
            }
            if ResourceType::Mesh
                .extensions()
                .contains(&ext_lower.as_str())
            {
                return ResourceType::Mesh;
            }
            if ResourceType::Script
                .extensions()
                .contains(&ext_lower.as_str())
            {
                return ResourceType::Script;
            }
            if ResourceType::Plugin
                .extensions()
                .contains(&ext_lower.as_str())
            {
                return ResourceType::Plugin;
            }
            if ResourceType::Sound
                .extensions()
                .contains(&ext_lower.as_str())
            {
                return ResourceType::Sound;
            }
            if ResourceType::Animation
                .extensions()
                .contains(&ext_lower.as_str())
            {
                return ResourceType::Animation;
            }
            if ResourceType::Interface
                .extensions()
                .contains(&ext_lower.as_str())
            {
                return ResourceType::Interface;
            }
            if ResourceType::Strings
                .extensions()
                .contains(&ext_lower.as_str())
            {
                return ResourceType::Strings;
            }
            if ResourceType::Archive
                .extensions()
                .contains(&ext_lower.as_str())
            {
                return ResourceType::Archive;
            }
            if ResourceType::Config
                .extensions()
                .contains(&ext_lower.as_str())
            {
                return ResourceType::Config;
            }
        }
    }

    ResourceType::Other
}

/// Check if a file is a supported resource type.
///
/// # Arguments
///
/// * `path` - The file path to check
///
/// # Returns
///
/// True if the file is a recognized resource type, false otherwise.
///
/// # Examples
///
/// ```rust
/// use classic_resource_core::is_supported_resource;
/// use std::path::Path;
///
/// assert!(is_supported_resource(Path::new("texture.dds")));
/// assert!(is_supported_resource(Path::new("plugin.esp")));
/// assert!(!is_supported_resource(Path::new("readme.txt")));
/// ```
#[must_use]
pub fn is_supported_resource(path: &Path) -> bool {
    detect_resource_type(path) != ResourceType::Other
}

// ============================================================================
// Resource Enumeration
// ============================================================================

/// Resource file information.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResourceInfo {
    /// Full path to the resource
    pub path: PathBuf,
    /// Detected resource type
    pub resource_type: ResourceType,
    /// File size in bytes (0 if unknown)
    pub size: u64,
}

impl ResourceInfo {
    /// Create a new `ResourceInfo` from a path.
    ///
    /// # Arguments
    ///
    /// * `path` - The resource path
    ///
    /// # Returns
    ///
    /// A new `ResourceInfo` instance.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_resource_core::ResourceInfo;
    /// use std::path::PathBuf;
    ///
    /// let info = ResourceInfo::new(PathBuf::from("texture.dds"));
    /// assert_eq!(info.path, PathBuf::from("texture.dds"));
    /// ```
    #[must_use]
    pub fn new(path: PathBuf) -> Self {
        let resource_type = detect_resource_type(&path);
        Self {
            path,
            resource_type,
            size: 0,
        }
    }

    /// Create a new `ResourceInfo` with size information.
    ///
    /// # Arguments
    ///
    /// * `path` - The resource path
    /// * `size` - The file size in bytes
    ///
    /// # Returns
    ///
    /// A new `ResourceInfo` instance with size.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_resource_core::ResourceInfo;
    /// use std::path::PathBuf;
    ///
    /// let info = ResourceInfo::with_size(PathBuf::from("texture.dds"), 1024);
    /// assert_eq!(info.size, 1024);
    /// ```
    #[must_use]
    pub fn with_size(path: PathBuf, size: u64) -> Self {
        let resource_type = detect_resource_type(&path);
        Self {
            path,
            resource_type,
            size,
        }
    }
}

/// Enumerate resources in a directory.
///
/// Recursively walks the directory tree and collects information about
/// all supported resource files.
///
/// # Arguments
///
/// * `root` - The root directory to scan
/// * `filter_type` - Optional resource type filter
///
/// # Returns
///
/// A vector of `ResourceInfo` for all found resources.
///
/// # Errors
///
/// Returns `ResourceError::IoError` if directory traversal fails.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_resource_core::enumerate_resources;
/// use std::path::Path;
///
/// // Enumerate all resources
/// let resources = enumerate_resources(Path::new("Data"), None).unwrap();
/// println!("Found {} resources", resources.len());
/// ```
pub fn enumerate_resources(
    root: &Path,
    filter_type: Option<ResourceType>,
) -> ResourceResult<Vec<ResourceInfo>> {
    let mut resources = Vec::new();

    for entry in WalkDir::new(root)
        .follow_links(false)
        .into_iter()
        .filter_map(Result::ok)
    {
        let path = entry.path();

        // Skip directories
        if !path.is_file() {
            continue;
        }

        let resource_type = detect_resource_type(path);

        // Skip if not supported or doesn't match filter
        if resource_type == ResourceType::Other {
            continue;
        }

        if let Some(filter) = filter_type {
            if resource_type != filter {
                continue;
            }
        }

        let size = entry.metadata().map(|m| m.len()).unwrap_or(0);
        resources.push(ResourceInfo::with_size(path.to_path_buf(), size));
    }

    Ok(resources)
}

/// Count resources in a directory by type.
///
/// # Arguments
///
/// * `root` - The root directory to scan
///
/// # Returns
///
/// A vector of tuples containing (ResourceType, count).
///
/// # Errors
///
/// Returns `ResourceError::IoError` if directory traversal fails.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_resource_core::count_resources_by_type;
/// use std::path::Path;
///
/// let counts = count_resources_by_type(Path::new("Data")).unwrap();
/// for (resource_type, count) in counts {
///     println!("{}: {} files", resource_type.as_str(), count);
/// }
/// ```
pub fn count_resources_by_type(root: &Path) -> ResourceResult<Vec<(ResourceType, usize)>> {
    let resources = enumerate_resources(root, None)?;

    // Count by type
    let mut counts = std::collections::HashMap::new();
    for resource in resources {
        *counts.entry(resource.resource_type).or_insert(0) += 1;
    }

    // Convert to sorted vector
    let mut result: Vec<_> = counts.into_iter().collect();
    result.sort_by_key(|(rt, _)| rt.as_str());

    Ok(result)
}

// ============================================================================
// Resource Validation
// ============================================================================

/// Check if a resource file exists and is readable.
///
/// # Arguments
///
/// * `path` - The resource path to validate
///
/// # Returns
///
/// Ok if the resource is valid and readable.
///
/// # Errors
///
/// Returns `ResourceError::NotFound` if the file doesn't exist,
/// or `ResourceError::IoError` if the file cannot be accessed.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_resource_core::validate_resource;
/// use std::path::Path;
///
/// match validate_resource(Path::new("texture.dds")) {
///     Ok(_) => println!("Resource is valid"),
///     Err(e) => eprintln!("Validation failed: {}", e),
/// }
/// ```
pub fn validate_resource(path: &Path) -> ResourceResult<()> {
    if !path.exists() {
        return Err(ResourceError::NotFound(path.to_path_buf()));
    }

    if !path.is_file() {
        return Err(ResourceError::InvalidType(format!(
            "Path is not a file: {}",
            path.display()
        )));
    }

    // Try to access metadata to verify readability
    path.metadata()?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_resource_type_as_str() {
        assert_eq!(ResourceType::Texture.as_str(), "texture");
        assert_eq!(ResourceType::Plugin.as_str(), "plugin");
        assert_eq!(ResourceType::Other.as_str(), "other");
    }

    #[test]
    fn test_resource_type_from_str() {
        assert_eq!("texture".parse::<ResourceType>().unwrap(), ResourceType::Texture);
        assert_eq!("TEXTURE".parse::<ResourceType>().unwrap(), ResourceType::Texture);
        assert_eq!("plugin".parse::<ResourceType>().unwrap(), ResourceType::Plugin);
        assert_eq!("unknown".parse::<ResourceType>().unwrap(), ResourceType::Other);
    }

    #[test]
    fn test_resource_type_extensions() {
        assert!(ResourceType::Texture.extensions().contains(&"dds"));
        assert!(ResourceType::Plugin.extensions().contains(&"esp"));
        assert!(ResourceType::Script.extensions().contains(&"pex"));
    }

    #[test]
    fn test_detect_resource_type() {
        assert_eq!(
            detect_resource_type(Path::new("texture.dds")),
            ResourceType::Texture
        );
        assert_eq!(
            detect_resource_type(Path::new("plugin.esp")),
            ResourceType::Plugin
        );
        assert_eq!(
            detect_resource_type(Path::new("script.pex")),
            ResourceType::Script
        );
        assert_eq!(
            detect_resource_type(Path::new("readme.txt")),
            ResourceType::Other
        );
    }

    #[test]
    fn test_detect_resource_type_case_insensitive() {
        assert_eq!(
            detect_resource_type(Path::new("texture.DDS")),
            ResourceType::Texture
        );
        assert_eq!(
            detect_resource_type(Path::new("plugin.ESP")),
            ResourceType::Plugin
        );
    }

    #[test]
    fn test_is_supported_resource() {
        assert!(is_supported_resource(Path::new("texture.dds")));
        assert!(is_supported_resource(Path::new("plugin.esp")));
        assert!(!is_supported_resource(Path::new("readme.txt")));
    }

    #[test]
    fn test_resource_info_new() {
        let info = ResourceInfo::new(PathBuf::from("texture.dds"));
        assert_eq!(info.path, PathBuf::from("texture.dds"));
        assert_eq!(info.resource_type, ResourceType::Texture);
        assert_eq!(info.size, 0);
    }

    #[test]
    fn test_resource_info_with_size() {
        let info = ResourceInfo::with_size(PathBuf::from("texture.dds"), 1024);
        assert_eq!(info.path, PathBuf::from("texture.dds"));
        assert_eq!(info.resource_type, ResourceType::Texture);
        assert_eq!(info.size, 1024);
    }
}
