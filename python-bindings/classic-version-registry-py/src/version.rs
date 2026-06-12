//! Python bindings for GameVersion.

use classic_version_registry_core as core;
use pyo3::prelude::*;

/// A 4-component game version (major.minor.patch.build).
///
/// Represents game versions like "1.10.163.0" used by Bethesda games.
/// Supports parsing, comparison, and semantic distance calculations.
///
/// Attributes:
///     major: Major version component.
///     minor: Minor version component.
///     patch: Patch version component.
///     build: Build version component.
///
/// Example:
///     >>> v = GameVersion("1.10.163.0")
///     >>> print(v.major, v.minor, v.patch, v.build)
///     1 10 163 0
///     >>> print(v)
///     1.10.163.0
#[pyclass(name = "GameVersion", from_py_object)]
#[derive(Clone)]
pub struct PyGameVersion {
    pub(crate) inner: core::GameVersion,
}

impl From<core::GameVersion> for PyGameVersion {
    fn from(v: core::GameVersion) -> Self {
        Self { inner: v }
    }
}

#[pymethods]
impl PyGameVersion {
    /// Create a GameVersion from a version string.
    ///
    /// Accepts 3-component ("1.10.163") or 4-component ("1.10.163.0") versions.
    ///
    /// Args:
    ///     version_str: Version string to parse.
    ///
    /// Raises:
    ///     ValueError: If the version string is invalid.
    #[new]
    fn new(version_str: &str) -> PyResult<Self> {
        let inner = core::GameVersion::parse(version_str).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("Invalid version: {e}"))
        })?;
        Ok(Self { inner })
    }

    /// Gets the major version component.
    #[getter]
    fn major(&self) -> u32 {
        self.inner.major
    }

    /// Gets the minor version component.
    #[getter]
    fn minor(&self) -> u32 {
        self.inner.minor
    }

    /// Gets the patch version component.
    #[getter]
    fn patch(&self) -> u32 {
        self.inner.patch
    }

    /// Gets the build version component.
    #[getter]
    fn build(&self) -> u32 {
        self.inner.build
    }

    /// Calculate semantic distance to another version.
    ///
    /// Uses weighted formula: major*1,000,000 + minor*1,000 + patch*1.
    ///
    /// Args:
    ///     other: The other GameVersion to compare against.
    ///
    /// Returns:
    ///     The semantic distance as an integer.
    fn semantic_distance(&self, other: &PyGameVersion) -> u64 {
        self.inner.semantic_distance(&other.inner)
    }

    /// Check if this version has the same major version as another.
    fn same_major(&self, other: &PyGameVersion) -> bool {
        self.inner.same_major(&other.inner)
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!("GameVersion('{}')", self.inner)
    }

    /// String representation.
    fn __str__(&self) -> String {
        self.inner.to_string()
    }

    /// Equality comparison.
    fn __eq__(&self, other: &PyGameVersion) -> bool {
        self.inner == other.inner
    }

    /// Hash support.
    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.inner.hash(&mut hasher);
        hasher.finish()
    }

    /// Less-than comparison.
    fn __lt__(&self, other: &PyGameVersion) -> bool {
        self.inner < other.inner
    }

    /// Less-than-or-equal comparison.
    fn __le__(&self, other: &PyGameVersion) -> bool {
        self.inner <= other.inner
    }

    /// Greater-than comparison.
    fn __gt__(&self, other: &PyGameVersion) -> bool {
        self.inner > other.inner
    }

    /// Greater-than-or-equal comparison.
    fn __ge__(&self, other: &PyGameVersion) -> bool {
        self.inner >= other.inner
    }
}

/// Register version components with the Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyGameVersion>()?;
    Ok(())
}
