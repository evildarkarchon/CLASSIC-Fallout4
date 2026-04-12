//! Python bindings for version matching.

use classic_version_registry_core as core;
use pyo3::prelude::*;

use crate::models::PyVersionInfo;

/// Confidence level for version matching results.
///
/// Indicates how confident we are that the matched version is correct.
///
/// Values:
///     EXACT: Exact version match found in registry.
///     RANGE: Version falls within a defined compatible_range.
///     NEAREST: Matched to nearest known version by semantic distance.
///     DEFAULT: Using default fallback version for the game.
///     UNKNOWN: No suitable match found.
///
/// Example:
///     >>> result = registry.match_version("1.10.163.0", "Fallout4", False)
///     >>> result.confidence
///     'exact'
///     >>> result.confidence == MatchConfidence.EXACT
///     True
#[pyclass(name = "MatchConfidence")]
#[derive(Clone)]
pub struct PyMatchConfidence {
    inner: core::MatchConfidence,
}

impl From<core::MatchConfidence> for PyMatchConfidence {
    fn from(confidence: core::MatchConfidence) -> Self {
        Self { inner: confidence }
    }
}

#[pymethods]
impl PyMatchConfidence {
    /// "exact" constant.
    #[classattr]
    const EXACT: &'static str = "exact";

    /// "range" constant.
    #[classattr]
    const RANGE: &'static str = "range";

    /// "nearest" constant.
    #[classattr]
    const NEAREST: &'static str = "nearest";

    /// "default" constant.
    #[classattr]
    const DEFAULT: &'static str = "default";

    /// "unknown" constant.
    #[classattr]
    const UNKNOWN: &'static str = "unknown";

    /// Check if this is a high-confidence match (Exact or Range).
    fn is_high_confidence(&self) -> bool {
        self.inner.is_high_confidence()
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!("MatchConfidence('{}')", self.as_str())
    }

    /// String representation.
    fn __str__(&self) -> &'static str {
        self.as_str()
    }

    /// Equality comparison (supports string comparison).
    fn __eq__(&self, other: &Bound<'_, PyAny>) -> PyResult<bool> {
        // Allow comparison with string values
        if let Ok(s) = other.extract::<String>() {
            return Ok(self.as_str() == s);
        }
        // Allow comparison with PyMatchConfidence instances
        if let Ok(other_mc) = other.extract::<PyRef<'_, PyMatchConfidence>>() {
            return Ok(self.as_str() == other_mc.as_str());
        }
        Ok(false)
    }

    /// Hash support.
    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.as_str().hash(&mut hasher);
        hasher.finish()
    }
}

impl PyMatchConfidence {
    fn as_str(&self) -> &'static str {
        match self.inner {
            core::MatchConfidence::Exact => "exact",
            core::MatchConfidence::Range => "range",
            core::MatchConfidence::Nearest => "nearest",
            core::MatchConfidence::Default => "default",
            core::MatchConfidence::Unknown => "unknown",
        }
    }
}

/// Result of version matching.
///
/// Contains the matched version (if any), the confidence level,
/// and a message describing the match result.
///
/// Attributes:
///     version_info: The matched VersionInfo, or None.
///     confidence: Confidence level string ("exact", "range", etc.).
///     detected: The originally detected version string.
///     message: Human-readable message about the match.
///     is_exact: Whether this was an exact match.
///     is_fallback: Whether this was a fallback match.
///     should_warn: Whether the user should be warned.
///     is_valid: Whether this is a valid match.
///
/// Example:
///     >>> result = registry.match_version("1.10.163.0", "Fallout4", False)
///     >>> result.is_exact
///     True
///     >>> result.version_info.id
///     'FO4_OG'
#[pyclass(name = "MatchResult")]
#[derive(Clone)]
pub struct PyMatchResult {
    inner: core::MatchResult,
}

impl From<core::MatchResult> for PyMatchResult {
    fn from(result: core::MatchResult) -> Self {
        Self { inner: result }
    }
}

#[pymethods]
impl PyMatchResult {
    /// Gets the matched version info, if any.
    #[getter]
    fn version_info(&self) -> Option<PyVersionInfo> {
        self.inner.version_info.clone().map(PyVersionInfo::from)
    }

    /// Gets the confidence level as a string.
    #[getter]
    fn confidence(&self) -> &'static str {
        match self.inner.confidence {
            core::MatchConfidence::Exact => "exact",
            core::MatchConfidence::Range => "range",
            core::MatchConfidence::Nearest => "nearest",
            core::MatchConfidence::Default => "default",
            core::MatchConfidence::Unknown => "unknown",
        }
    }

    /// Gets the confidence level as a MatchConfidence object.
    #[getter]
    fn confidence_enum(&self) -> PyMatchConfidence {
        PyMatchConfidence::from(self.inner.confidence)
    }

    /// Gets the originally detected version string.
    #[getter]
    fn detected(&self) -> String {
        self.inner.detected.to_string()
    }

    /// Gets the human-readable message.
    #[getter]
    fn message(&self) -> &str {
        &self.inner.message
    }

    /// Whether this was an exact match.
    #[getter]
    fn is_exact(&self) -> bool {
        self.inner.is_exact()
    }

    /// Whether this was a fallback match (Nearest, Default, or Unknown).
    #[getter]
    fn is_fallback(&self) -> bool {
        self.inner.is_fallback()
    }

    /// Whether the user should be warned about this match.
    #[getter]
    fn should_warn(&self) -> bool {
        self.inner.should_warn()
    }

    /// Whether this is a valid match (version_info present and not Unknown).
    #[getter]
    fn is_valid(&self) -> bool {
        self.inner.is_valid()
    }

    /// String representation.
    fn __repr__(&self) -> String {
        let info_id = self
            .inner
            .version_info
            .as_ref()
            .map(|v| v.id.as_str())
            .unwrap_or("None");
        format!(
            "MatchResult(confidence='{}', version_id='{}', detected='{}')",
            self.confidence(),
            info_id,
            self.inner.detected
        )
    }
}

/// Register matching components with the Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyMatchConfidence>()?;
    m.add_class::<PyMatchResult>()?;
    Ok(())
}
