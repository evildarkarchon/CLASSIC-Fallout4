//! Python bindings for crashgen version parsing and status checks.

use classic_scanlog_core::version as core;
use pyo3::prelude::*;

/// Parsed crash generator version components exposed to Python.
#[pyclass(name = "CrashgenVersion")]
#[derive(Clone)]
pub struct PyCrashgenVersion {
    inner: core::CrashgenVersion,
}

impl From<core::CrashgenVersion> for PyCrashgenVersion {
    fn from(inner: core::CrashgenVersion) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyCrashgenVersion {
    #[new]
    fn new(version_str: &str) -> PyResult<Self> {
        let inner = core::CrashgenVersion::parse(version_str).ok_or_else(|| {
            pyo3::exceptions::PyValueError::new_err("Invalid crash generator version string")
        })?;
        Ok(Self { inner })
    }

    #[getter]
    fn major(&self) -> u64 {
        self.inner.major
    }

    #[getter]
    fn minor(&self) -> u64 {
        self.inner.minor
    }

    #[getter]
    fn patch(&self) -> u64 {
        self.inner.patch
    }

    #[getter]
    fn original(&self) -> String {
        self.inner.original.clone()
    }

    fn to_tuple(&self) -> (u32, u32, u32) {
        self.inner.to_tuple()
    }

    fn __repr__(&self) -> String {
        format!("CrashgenVersion('{}')", self.inner)
    }

    fn __str__(&self) -> String {
        self.inner.to_string()
    }

    fn __eq__(&self, other: &PyCrashgenVersion) -> bool {
        self.inner == other.inner
    }

    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.inner.major.hash(&mut hasher);
        self.inner.minor.hash(&mut hasher);
        self.inner.patch.hash(&mut hasher);
        hasher.finish()
    }
}

/// Crashgen version validation status exposed to Python.
#[pyclass(name = "CrashgenVersionStatus")]
#[derive(Clone)]
pub struct PyCrashgenVersionStatus {
    inner: core::CrashgenVersionStatus,
}

impl From<core::CrashgenVersionStatus> for PyCrashgenVersionStatus {
    fn from(inner: core::CrashgenVersionStatus) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyCrashgenVersionStatus {
    #[classattr]
    const VALID: &'static str = "valid";

    #[classattr]
    const OUTDATED: &'static str = "outdated";

    #[classattr]
    const NEWER_THAN_KNOWN: &'static str = "newer_than_known";

    #[classattr]
    const NO_SUPPORTED_VERSION: &'static str = "no_supported_version";

    fn __repr__(&self) -> String {
        format!("CrashgenVersionStatus('{}')", self.as_str())
    }

    fn __str__(&self) -> &'static str {
        self.as_str()
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> PyResult<bool> {
        if let Ok(value) = other.extract::<String>() {
            return Ok(self.as_str() == value);
        }
        if let Ok(other_status) = other.extract::<PyRef<'_, PyCrashgenVersionStatus>>() {
            return Ok(self.as_str() == other_status.as_str());
        }
        Ok(false)
    }

    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.as_str().hash(&mut hasher);
        hasher.finish()
    }
}

impl PyCrashgenVersionStatus {
    fn as_str(&self) -> &'static str {
        match self.inner {
            core::CrashgenVersionStatus::Valid => "valid",
            core::CrashgenVersionStatus::Outdated => "outdated",
            core::CrashgenVersionStatus::NewerThanKnown => "newer_than_known",
            core::CrashgenVersionStatus::NoSupportedVersion => "no_supported_version",
        }
    }
}

#[pyfunction]
/// Parse a crash generator version string into a structured object.
pub fn parse_crashgen_version(version_str: &str) -> Option<PyCrashgenVersion> {
    core::CrashgenVersion::parse(version_str).map(PyCrashgenVersion::from)
}

#[pyfunction]
/// Compare a detected crashgen version against the supported version list.
pub fn check_crashgen_version_status(
    detected_version: &str,
    valid_versions: Vec<String>,
) -> PyCrashgenVersionStatus {
    let valid_refs: Vec<&str> = valid_versions.iter().map(String::as_str).collect();
    PyCrashgenVersionStatus::from(core::check_crashgen_version_status(
        detected_version,
        &valid_refs,
    ))
}

/// Register crashgen version helpers on a Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCrashgenVersion>()?;
    m.add_class::<PyCrashgenVersionStatus>()?;
    m.add_function(wrap_pyfunction!(parse_crashgen_version, m)?)?;
    m.add_function(wrap_pyfunction!(check_crashgen_version_status, m)?)?;
    Ok(())
}
