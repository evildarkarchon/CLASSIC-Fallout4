//! Python bindings for classic-resource-core.
//!
//! This module provides Python access to resource management functionality,
//! including file type detection, resource enumeration, and validation.

use pyo3::prelude::*;
use pyo3::exceptions::{PyIOError, PyValueError};
use std::path::PathBuf;

/// Resource type enumeration for Python.
#[pyclass(module = "classic_resource", name = "ResourceType")]
#[derive(Clone)]
pub struct PyResourceType {
    inner: classic_resource_core::ResourceType,
}

#[pymethods]
impl PyResourceType {
    /// Get the resource type name as a string.
    ///
    /// # Returns
    ///
    /// A string representing the resource type.
    ///
    /// # Examples
    ///
    /// ```python
    /// import classic_resource
    ///
    /// rt = classic_resource.ResourceType.texture()
    /// assert rt.as_str() == "texture"
    /// ```
    fn as_str(&self) -> &str {
        self.inner.as_str()
    }

    /// Get all file extensions for this resource type.
    ///
    /// # Returns
    ///
    /// A list of file extensions (without the dot).
    ///
    /// # Examples
    ///
    /// ```python
    /// import classic_resource
    ///
    /// rt = classic_resource.ResourceType.texture()
    /// assert "dds" in rt.extensions()
    /// ```
    fn extensions(&self) -> Vec<String> {
        self.inner
            .extensions()
            .iter()
            .map(|&s| s.to_string())
            .collect()
    }

    /// Create a Texture resource type.
    #[staticmethod]
    fn texture() -> Self {
        Self {
            inner: classic_resource_core::ResourceType::Texture,
        }
    }

    /// Create a Mesh resource type.
    #[staticmethod]
    fn mesh() -> Self {
        Self {
            inner: classic_resource_core::ResourceType::Mesh,
        }
    }

    /// Create a Script resource type.
    #[staticmethod]
    fn script() -> Self {
        Self {
            inner: classic_resource_core::ResourceType::Script,
        }
    }

    /// Create a Plugin resource type.
    #[staticmethod]
    fn plugin() -> Self {
        Self {
            inner: classic_resource_core::ResourceType::Plugin,
        }
    }

    /// Create a Sound resource type.
    #[staticmethod]
    fn sound() -> Self {
        Self {
            inner: classic_resource_core::ResourceType::Sound,
        }
    }

    /// Create an Animation resource type.
    #[staticmethod]
    fn animation() -> Self {
        Self {
            inner: classic_resource_core::ResourceType::Animation,
        }
    }

    /// Create an Interface resource type.
    #[staticmethod]
    fn interface() -> Self {
        Self {
            inner: classic_resource_core::ResourceType::Interface,
        }
    }

    /// Create a Strings resource type.
    #[staticmethod]
    fn strings() -> Self {
        Self {
            inner: classic_resource_core::ResourceType::Strings,
        }
    }

    /// Create an Archive resource type.
    #[staticmethod]
    fn archive() -> Self {
        Self {
            inner: classic_resource_core::ResourceType::Archive,
        }
    }

    /// Create a Config resource type.
    #[staticmethod]
    fn config() -> Self {
        Self {
            inner: classic_resource_core::ResourceType::Config,
        }
    }

    /// Create an Other resource type.
    #[staticmethod]
    fn other() -> Self {
        Self {
            inner: classic_resource_core::ResourceType::Other,
        }
    }

    /// Compare resource types for equality.
    fn __eq__(&self, other: &Self) -> bool {
        self.inner == other.inner
    }

    /// String representation of resource type.
    fn __str__(&self) -> String {
        self.inner.as_str().to_string()
    }

    /// Debug representation of resource type.
    fn __repr__(&self) -> String {
        format!("ResourceType.{}()", self.inner.as_str())
    }
}

/// Resource file information.
#[pyclass(module = "classic_resource", name = "ResourceInfo")]
#[derive(Clone)]
pub struct PyResourceInfo {
    inner: classic_resource_core::ResourceInfo,
}

#[pymethods]
impl PyResourceInfo {
    /// Create a new ResourceInfo from a path.
    ///
    /// # Arguments
    ///
    /// * `path` - The resource file path
    ///
    /// # Examples
    ///
    /// ```python
    /// import classic_resource
    ///
    /// info = classic_resource.ResourceInfo("texture.dds")
    /// assert info.path() == "texture.dds"
    /// ```
    #[new]
    fn new(path: String) -> Self {
        Self {
            inner: classic_resource_core::ResourceInfo::new(PathBuf::from(path)),
        }
    }

    /// Get the resource path.
    ///
    /// # Returns
    ///
    /// The file path as a string.
    fn path(&self) -> String {
        self.inner.path.display().to_string()
    }

    /// Get the detected resource type.
    ///
    /// # Returns
    ///
    /// The ResourceType for this resource.
    fn resource_type(&self) -> PyResourceType {
        PyResourceType {
            inner: self.inner.resource_type,
        }
    }

    /// Get the file size in bytes.
    ///
    /// # Returns
    ///
    /// File size in bytes (0 if unknown).
    fn size(&self) -> u64 {
        self.inner.size
    }

    /// String representation of resource info.
    fn __str__(&self) -> String {
        format!(
            "ResourceInfo(path='{}', type='{}', size={})",
            self.inner.path.display(),
            self.inner.resource_type.as_str(),
            self.inner.size
        )
    }

    /// Debug representation of resource info.
    fn __repr__(&self) -> String {
        format!(
            "ResourceInfo(path='{}', type='{}', size={})",
            self.inner.path.display(),
            self.inner.resource_type.as_str(),
            self.inner.size
        )
    }
}

/// Detect the resource type from a file path.
///
/// # Arguments
///
/// * `path` - The file path to examine
///
/// # Returns
///
/// The detected ResourceType.
///
/// # Examples
///
/// ```python
/// import classic_resource
///
/// rt = classic_resource.detect_resource_type("textures/armor.dds")
/// assert rt.as_str() == "texture"
///
/// rt = classic_resource.detect_resource_type("scripts/myquest.pex")
/// assert rt.as_str() == "script"
/// ```
#[pyfunction]
fn detect_resource_type(path: &str) -> PyResourceType {
    PyResourceType {
        inner: classic_resource_core::detect_resource_type(&PathBuf::from(path)),
    }
}

/// Check if a file is a supported resource type.
///
/// # Arguments
///
/// * `path` - The file path to check
///
/// # Returns
///
/// True if the file is a recognized resource type.
///
/// # Examples
///
/// ```python
/// import classic_resource
///
/// assert classic_resource.is_supported_resource("texture.dds")
/// assert classic_resource.is_supported_resource("plugin.esp")
/// assert not classic_resource.is_supported_resource("readme.txt")
/// ```
#[pyfunction]
fn is_supported_resource(path: &str) -> bool {
    classic_resource_core::is_supported_resource(&PathBuf::from(path))
}

/// Parse a resource type from a string.
///
/// # Arguments
///
/// * `type_name` - The resource type name (case-insensitive)
///
/// # Returns
///
/// The corresponding ResourceType.
///
/// # Examples
///
/// ```python
/// import classic_resource
///
/// rt = classic_resource.parse_resource_type("texture")
/// assert rt.as_str() == "texture"
///
/// rt = classic_resource.parse_resource_type("PLUGIN")
/// assert rt.as_str() == "plugin"
/// ```
#[pyfunction]
fn parse_resource_type(type_name: &str) -> PyResourceType {
    PyResourceType {
        inner: classic_resource_core::ResourceType::from_str(type_name),
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
/// * `filter_type` - Optional resource type filter (use None for all types)
///
/// # Returns
///
/// A list of ResourceInfo objects for all found resources.
///
/// # Raises
///
/// * `IOError` - If directory traversal fails
///
/// # Examples
///
/// ```python
/// import classic_resource
///
/// # Enumerate all resources
/// resources = classic_resource.enumerate_resources("Data")
/// print(f"Found {len(resources)} resources")
///
/// # Enumerate only textures
/// textures = classic_resource.enumerate_resources("Data", classic_resource.ResourceType.texture())
/// print(f"Found {len(textures)} textures")
/// ```
#[pyfunction]
fn enumerate_resources(root: &str, filter_type: Option<PyResourceType>) -> PyResult<Vec<PyResourceInfo>> {
    let filter = filter_type.map(|rt| rt.inner);

    classic_resource_core::enumerate_resources(&PathBuf::from(root), filter)
        .map(|resources| {
            resources
                .into_iter()
                .map(|info| PyResourceInfo { inner: info })
                .collect()
        })
        .map_err(|e| PyIOError::new_err(e.to_string()))
}

/// Count resources in a directory by type.
///
/// # Arguments
///
/// * `root` - The root directory to scan
///
/// # Returns
///
/// A list of tuples containing (ResourceType, count).
///
/// # Raises
///
/// * `IOError` - If directory traversal fails
///
/// # Examples
///
/// ```python
/// import classic_resource
///
/// counts = classic_resource.count_resources_by_type("Data")
/// for resource_type, count in counts:
///     print(f"{resource_type.as_str()}: {count} files")
/// ```
#[pyfunction]
fn count_resources_by_type(root: &str) -> PyResult<Vec<(PyResourceType, usize)>> {
    classic_resource_core::count_resources_by_type(&PathBuf::from(root))
        .map(|counts| {
            counts
                .into_iter()
                .map(|(rt, count)| (PyResourceType { inner: rt }, count))
                .collect()
        })
        .map_err(|e| PyIOError::new_err(e.to_string()))
}

/// Check if a resource file exists and is readable.
///
/// # Arguments
///
/// * `path` - The resource path to validate
///
/// # Returns
///
/// None if valid.
///
/// # Raises
///
/// * `IOError` - If the file doesn't exist or cannot be accessed
/// * `ValueError` - If the path is not a file
///
/// # Examples
///
/// ```python
/// import classic_resource
///
/// try:
///     classic_resource.validate_resource("texture.dds")
///     print("Resource is valid")
/// except IOError as e:
///     print(f"Validation failed: {e}")
/// ```
#[pyfunction]
fn validate_resource(path: &str) -> PyResult<()> {
    classic_resource_core::validate_resource(&PathBuf::from(path))
        .map_err(|e| match e {
            classic_resource_core::ResourceError::NotFound(_) => {
                PyIOError::new_err(format!("Resource not found: {}", path))
            }
            classic_resource_core::ResourceError::InvalidType(msg) => {
                PyValueError::new_err(msg)
            }
            _ => PyIOError::new_err(e.to_string()),
        })
}

/// Python module for resource management.
///
/// This module provides comprehensive resource handling for Bethesda game files,
/// including file type detection, resource enumeration, and validation.
#[pymodule]
fn classic_resource(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register classes
    m.add_class::<PyResourceType>()?;
    m.add_class::<PyResourceInfo>()?;

    // Resource type detection
    m.add_function(wrap_pyfunction!(detect_resource_type, m)?)?;
    m.add_function(wrap_pyfunction!(is_supported_resource, m)?)?;
    m.add_function(wrap_pyfunction!(parse_resource_type, m)?)?;

    // Resource enumeration
    m.add_function(wrap_pyfunction!(enumerate_resources, m)?)?;
    m.add_function(wrap_pyfunction!(count_resources_by_type, m)?)?;

    // Resource validation
    m.add_function(wrap_pyfunction!(validate_resource, m)?)?;

    // Module metadata
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("__doc__", "Resource management for game files")?;

    Ok(())
}
