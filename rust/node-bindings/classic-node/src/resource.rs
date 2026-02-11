//! Resource type detection bindings (classic-resource-core)
//!
//! Exposes resource type classification, directory enumeration, and resource
//! validation to JavaScript/TypeScript.

use napi::bindgen_prelude::*;
use std::path::PathBuf;

/// Convert any Display error to a napi::Error
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

// ============================================================================
// Resource Type
// ============================================================================

/// Map a core ResourceType to its string name.
fn resource_type_to_string(rt: classic_resource_core::ResourceType) -> String {
    rt.as_str().to_string()
}

/// Parse a string into a core ResourceType.
fn string_to_resource_type(s: &str) -> classic_resource_core::ResourceType {
    s.parse()
        .unwrap_or(classic_resource_core::ResourceType::Other)
}

/// Detect the resource type of a file from its path/extension.
///
/// Returns a string identifying the type: "texture", "mesh", "script",
/// "plugin", "sound", "animation", "interface", "strings", "archive",
/// "config", or "other".
#[napi]
pub fn detect_resource_type(path: String) -> String {
    let rt = classic_resource_core::detect_resource_type(&PathBuf::from(&path));
    resource_type_to_string(rt)
}

/// Check if a file is a supported (recognized) resource type.
///
/// Returns true for known game resource extensions (.dds, .esp, .nif, etc.)
/// and false for unrecognized types.
#[napi]
pub fn is_supported_resource(path: String) -> bool {
    classic_resource_core::is_supported_resource(&PathBuf::from(&path))
}

/// Parse a resource type name string and return its canonical form.
///
/// Accepts case-insensitive names like "texture", "PLUGIN", "Mesh".
/// Unrecognized names return "other".
#[napi]
pub fn parse_resource_type(type_name: String) -> String {
    let rt = string_to_resource_type(&type_name);
    resource_type_to_string(rt)
}

/// Get all standard file extensions for a named resource type.
///
/// Returns an array of extensions (without the dot), e.g. `["dds", "png", "jpg", "tga"]`
/// for "texture". Returns an empty array for "other" or unrecognized types.
#[napi]
pub fn get_resource_extensions(type_name: String) -> Vec<String> {
    let rt = string_to_resource_type(&type_name);
    rt.extensions().iter().map(|&s| s.to_string()).collect()
}

// ============================================================================
// Resource Info DTO
// ============================================================================

/// Information about a single resource file.
#[napi(object)]
pub struct ResourceInfo {
    /// Full path to the resource file
    pub path: String,
    /// Detected resource type name (e.g. "texture", "plugin")
    pub resource_type: String,
    /// File size in bytes (0 if unknown)
    pub size: f64,
}

impl From<classic_resource_core::ResourceInfo> for ResourceInfo {
    fn from(info: classic_resource_core::ResourceInfo) -> Self {
        Self {
            path: info.path.to_string_lossy().to_string(),
            resource_type: resource_type_to_string(info.resource_type),
            size: info.size as f64,
        }
    }
}

/// Create a ResourceInfo object from a path.
///
/// The resource type is auto-detected from the file extension.
/// Size is set to 0 (use enumerateResources for size-aware listing).
#[napi]
pub fn create_resource_info(path: String) -> ResourceInfo {
    classic_resource_core::ResourceInfo::new(PathBuf::from(&path)).into()
}

/// Create a ResourceInfo object from a path with a known size.
///
/// The resource type is auto-detected from the file extension.
#[napi]
pub fn create_resource_info_with_size(path: String, size: f64) -> ResourceInfo {
    classic_resource_core::ResourceInfo::with_size(PathBuf::from(&path), size as u64).into()
}

// ============================================================================
// Resource Enumeration
// ============================================================================

/// Enumerate all supported resource files in a directory tree.
///
/// Recursively walks the directory and returns info for all recognized
/// resource files. Optionally filter to a single resource type by passing
/// a type name string (e.g. "texture", "plugin").
///
/// @throws if the directory cannot be traversed.
#[napi]
pub fn enumerate_resources(root: String, filter_type: Option<String>) -> Result<Vec<ResourceInfo>> {
    let filter = filter_type.map(|s| string_to_resource_type(&s));

    classic_resource_core::enumerate_resources(&PathBuf::from(&root), filter)
        .map(|resources| resources.into_iter().map(ResourceInfo::from).collect())
        .map_err(to_napi_err)
}

/// Resource type count entry.
#[napi(object)]
pub struct ResourceCount {
    /// Resource type name (e.g. "texture", "plugin")
    pub resource_type: String,
    /// Number of files of this type
    pub count: u32,
}

/// Count resources in a directory grouped by type.
///
/// Returns an array of objects with `resourceType` and `count` fields,
/// sorted alphabetically by type name.
///
/// @throws if the directory cannot be traversed.
#[napi]
pub fn count_resources_by_type(root: String) -> Result<Vec<ResourceCount>> {
    classic_resource_core::count_resources_by_type(&PathBuf::from(&root))
        .map(|counts| {
            counts
                .into_iter()
                .map(|(rt, count)| ResourceCount {
                    resource_type: resource_type_to_string(rt),
                    count: count as u32,
                })
                .collect()
        })
        .map_err(to_napi_err)
}

// ============================================================================
// Resource Validation
// ============================================================================

/// Validate that a resource file exists and is readable.
///
/// @throws if the file does not exist, is not a file, or cannot be accessed.
#[napi]
pub fn validate_resource(path: String) -> Result<()> {
    classic_resource_core::validate_resource(&PathBuf::from(&path)).map_err(to_napi_err)
}
