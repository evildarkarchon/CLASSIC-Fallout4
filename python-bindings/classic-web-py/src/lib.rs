//! Python bindings for classic-web-core.
//!
//! This module provides Python access to web utilities, including URL validation,
//! user agent generation, and mod site constants.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

/// Mod site enumeration for Python.
#[pyclass(module = "classic_web", name = "ModSite", from_py_object)]
#[derive(Clone)]
pub struct PyModSite {
    inner: classic_web_core::ModSite,
}

#[pymethods]
impl PyModSite {
    /// Get the mod site name as a string.
    ///
    /// # Returns
    ///
    /// The mod site name.
    ///
    /// # Examples
    ///
    /// ```python
    /// import classic_web
    ///
    /// site = classic_web.ModSite.nexus_mods()
    /// assert site.name() == "Nexus Mods"
    /// ```
    fn name(&self) -> &str {
        self.inner.name()
    }

    /// Get the mod site base URL.
    ///
    /// # Returns
    ///
    /// The base URL for the mod site.
    ///
    /// # Examples
    ///
    /// ```python
    /// import classic_web
    ///
    /// site = classic_web.ModSite.nexus_mods()
    /// assert site.base_url() == "https://www.nexusmods.com"
    /// ```
    fn base_url(&self) -> &str {
        self.inner.base_url()
    }

    /// Create a NexusMods site.
    #[staticmethod]
    fn nexus_mods() -> Self {
        Self {
            inner: classic_web_core::ModSite::NexusMods,
        }
    }

    /// Create a BethesdaNet site.
    #[staticmethod]
    fn bethesda_net() -> Self {
        Self {
            inner: classic_web_core::ModSite::BethesdaNet,
        }
    }

    /// Create a ModDB site.
    #[staticmethod]
    fn mod_db() -> Self {
        Self {
            inner: classic_web_core::ModSite::ModDB,
        }
    }

    /// Compare mod sites for equality.
    fn __eq__(&self, other: &Self) -> bool {
        self.inner == other.inner
    }

    /// String representation of mod site.
    fn __str__(&self) -> String {
        self.inner.name().to_string()
    }

    /// Debug representation of mod site.
    fn __repr__(&self) -> String {
        let variant = match self.inner {
            classic_web_core::ModSite::NexusMods => "nexus_mods",
            classic_web_core::ModSite::BethesdaNet => "bethesda_net",
            classic_web_core::ModSite::ModDB => "mod_db",
        };
        format!("ModSite.{}()", variant)
    }
}

/// Get the default user agent string for CLASSIC.
///
/// # Returns
///
/// A user agent string in the format "CLASSIC/8.0.0".
///
/// # Examples
///
/// ```python
/// import classic_web
///
/// ua = classic_web.get_user_agent()
/// assert ua.startswith("CLASSIC/")
/// ```
#[pyfunction]
fn get_user_agent() -> String {
    classic_web_core::get_user_agent()
}

/// Get a user agent string with a custom suffix.
///
/// # Arguments
///
/// * `suffix` - Additional information to append to the user agent.
///
/// # Returns
///
/// A user agent string with the suffix appended.
///
/// # Examples
///
/// ```python
/// import classic_web
///
/// ua = classic_web.get_user_agent_with_suffix("NexusMods")
/// assert "NexusMods" in ua
/// ```
#[pyfunction]
fn get_user_agent_with_suffix(suffix: &str) -> String {
    classic_web_core::get_user_agent_with_suffix(suffix)
}

/// Validate and parse a URL string.
///
/// # Arguments
///
/// * `url_str` - The URL string to validate.
///
/// # Returns
///
/// The validated URL as a string.
///
/// # Raises
///
/// * `ValueError` - If the URL is invalid.
///
/// # Examples
///
/// ```python
/// import classic_web
///
/// url = classic_web.validate_url("https://www.nexusmods.com")
/// assert url == "https://www.nexusmods.com/"
///
/// try:
///     classic_web.validate_url("not a url")
/// except ValueError as e:
///     print(f"Invalid URL: {e}")
/// ```
#[pyfunction]
fn validate_url(url_str: &str) -> PyResult<String> {
    classic_web_core::validate_url(url_str)
        .map(|url| url.to_string())
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

/// Check if a URL string is valid.
///
/// # Arguments
///
/// * `url_str` - The URL string to check.
///
/// # Returns
///
/// True if the URL is valid, False otherwise.
///
/// # Examples
///
/// ```python
/// import classic_web
///
/// assert classic_web.is_valid_url("https://www.nexusmods.com")
/// assert not classic_web.is_valid_url("not a url")
/// ```
#[pyfunction]
fn is_valid_url(url_str: &str) -> bool {
    classic_web_core::is_valid_url(url_str)
}

/// Extract the domain from a URL.
///
/// # Arguments
///
/// * `url_str` - The URL string to extract from.
///
/// # Returns
///
/// The domain as a string.
///
/// # Raises
///
/// * `ValueError` - If the URL is invalid or has no domain.
///
/// # Examples
///
/// ```python
/// import classic_web
///
/// domain = classic_web.extract_domain("https://www.nexusmods.com/fallout4/mods/123")
/// assert domain == "www.nexusmods.com"
/// ```
#[pyfunction]
fn extract_domain(url_str: &str) -> PyResult<String> {
    classic_web_core::extract_domain(url_str).map_err(|e| PyValueError::new_err(e.to_string()))
}

/// Join a base URL with a path.
///
/// # Arguments
///
/// * `base` - The base URL.
/// * `path` - The path to join.
///
/// # Returns
///
/// The joined URL as a string.
///
/// # Raises
///
/// * `ValueError` - If the base URL is invalid or joining fails.
///
/// # Examples
///
/// ```python
/// import classic_web
///
/// url = classic_web.join_url("https://www.nexusmods.com", "fallout4/mods")
/// assert url == "https://www.nexusmods.com/fallout4/mods"
/// ```
#[pyfunction]
fn join_url(base: &str, path: &str) -> PyResult<String> {
    classic_web_core::join_url(base, path).map_err(|e| PyValueError::new_err(e.to_string()))
}

/// Build a URL with query parameters.
///
/// # Arguments
///
/// * `base` - The base URL.
/// * `params` - List of tuples containing (key, value) pairs for query parameters.
///
/// # Returns
///
/// The URL with query parameters as a string.
///
/// # Raises
///
/// * `ValueError` - If the base URL is invalid.
///
/// # Examples
///
/// ```python
/// import classic_web
///
/// url = classic_web.build_url_with_query(
///     "https://www.nexusmods.com/fallout4/mods",
///     [("game_id", "1151"), ("adult", "false")]
/// )
/// assert "game_id=1151" in url
/// assert "adult=false" in url
/// ```
#[pyfunction]
fn build_url_with_query(base: &str, params: Vec<(String, String)>) -> PyResult<String> {
    // Convert Python list of tuples to Vec of (&str, &str)
    let param_refs: Vec<(&str, &str)> = params
        .iter()
        .map(|(k, v)| (k.as_str(), v.as_str()))
        .collect();

    classic_web_core::build_url_with_query(base, &param_refs)
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

/// Python module for web utilities.
///
/// This module provides comprehensive web utilities for CLASSIC, including
/// URL validation, user agent generation, and mod site constants.
#[pymodule]
fn classic_web(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register classes
    m.add_class::<PyModSite>()?;

    // User agent functions
    m.add_function(wrap_pyfunction!(get_user_agent, m)?)?;
    m.add_function(wrap_pyfunction!(get_user_agent_with_suffix, m)?)?;

    // URL validation
    m.add_function(wrap_pyfunction!(validate_url, m)?)?;
    m.add_function(wrap_pyfunction!(is_valid_url, m)?)?;
    m.add_function(wrap_pyfunction!(extract_domain, m)?)?;

    // URL building
    m.add_function(wrap_pyfunction!(join_url, m)?)?;
    m.add_function(wrap_pyfunction!(build_url_with_query, m)?)?;

    // Constants
    m.add("CLASSIC_VERSION", classic_web_core::CLASSIC_VERSION)?;
    m.add("USER_AGENT_PREFIX", classic_web_core::USER_AGENT_PREFIX)?;

    // Module metadata
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("__doc__", "Web utilities for CLASSIC")?;

    Ok(())
}
