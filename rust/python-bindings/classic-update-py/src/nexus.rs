//! Python bindings for Nexus Mods integration.

use classic_update_core as core;
use pyo3::prelude::*;

/// Python wrapper for NexusModInfo.
///
/// This class contains basic information about a mod on Nexus Mods.
///
/// Attributes:
///     name: Mod name.
///     version: Current version string.
///     description: Mod description (truncated).
///     author: Author username.
///     endorsements: Number of endorsements (optional).
///     downloads: Number of downloads (optional).
///     last_updated: Last update date string.
///     url: Mod page URL.
///
/// Example:
///     >>> import classic_update
///     >>> client = classic_update.NexusClient()
///     >>> info = await client.get_mod_info("fallout4", 1234)
///     >>> print(f"{info.name} by {info.author}")
///     >>> print(f"Version: {info.version}")
#[pyclass(name = "NexusModInfo")]
#[derive(Clone)]
pub struct PyNexusModInfo {
    inner: core::NexusModInfo,
}

impl From<core::NexusModInfo> for PyNexusModInfo {
    fn from(info: core::NexusModInfo) -> Self {
        Self { inner: info }
    }
}

#[pymethods]
impl PyNexusModInfo {
    /// Gets the mod name.
    #[getter]
    fn name(&self) -> &str {
        &self.inner.name
    }

    /// Gets the current version string.
    #[getter]
    fn version(&self) -> &str {
        &self.inner.version
    }

    /// Gets the mod description (truncated).
    #[getter]
    fn description(&self) -> &str {
        &self.inner.description
    }

    /// Gets the author username.
    #[getter]
    fn author(&self) -> &str {
        &self.inner.author
    }

    /// Gets the number of endorsements (if available).
    #[getter]
    fn endorsements(&self) -> Option<u64> {
        self.inner.endorsements
    }

    /// Gets the number of downloads (if available).
    #[getter]
    fn downloads(&self) -> Option<u64> {
        self.inner.downloads
    }

    /// Gets the last update date string.
    #[getter]
    fn last_updated(&self) -> &str {
        &self.inner.last_updated
    }

    /// Gets the mod page URL.
    #[getter]
    fn url(&self) -> &str {
        &self.inner.url
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!(
            "NexusModInfo(name='{}', version='{}', author='{}')",
            self.inner.name, self.inner.version, self.inner.author
        )
    }

    /// String representation.
    fn __str__(&self) -> String {
        format!(
            "{} v{} by {}",
            self.inner.name, self.inner.version, self.inner.author
        )
    }
}

/// Python wrapper for NexusClient.
///
/// This class provides access to Nexus Mods via web scraping.
///
/// Warning:
///     Web scraping is fragile and may break if Nexus changes their site structure.
///     Use with caution and implement proper error handling.
///
/// Example:
///     >>> import classic_update
///     >>> import asyncio
///     >>>
///     >>> async def check_mods():
///     ...     client = classic_update.NexusClient()
///     ...
///     ...     # Get mod info
///     ...     info = await client.get_mod_info("fallout4", 1234)
///     ...     print(f"Mod: {info.name}")
///     ...     print(f"Version: {info.version}")
///     ...     print(f"Author: {info.author}")
///     ...
///     ...     # Check for updates
///     ...     if await client.has_update("fallout4", 1234, "1.0"):
///     ...         print("Mod has been updated!")
///     >>>
///     >>> asyncio.run(check_mods())
#[pyclass(name = "NexusClient")]
pub struct PyNexusClient {
    inner: core::NexusClient,
}

#[pymethods]
impl PyNexusClient {
    /// Creates a new Nexus Mods client.
    ///
    /// Returns:
    ///     A new NexusClient instance.
    ///
    /// Example:
    ///     >>> client = classic_update.NexusClient()
    #[new]
    fn new() -> Self {
        Self {
            inner: core::NexusClient::new(),
        }
    }

    /// Gets information about a specific mod (async).
    ///
    /// Args:
    ///     game: Game identifier (e.g., "fallout4", "skyrimspecialedition").
    ///     mod_id: Numeric mod ID.
    ///
    /// Returns:
    ///     Mod information extracted from the mod page.
    ///
    /// Raises:
    ///     RuntimeError: If the request fails or page structure is unexpected.
    ///     FileNotFoundError: If the mod doesn't exist.
    ///
    /// Example:
    ///     >>> info = await client.get_mod_info("fallout4", 1234)
    ///     >>> print(f"Mod: {info.name}")
    fn get_mod_info<'py>(
        &self,
        py: Python<'py>,
        game: String,
        mod_id: u64,
    ) -> PyResult<Bound<'py, PyAny>> {
        let client = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            client
                .get_mod_info(&game, mod_id)
                .await
                .map(PyNexusModInfo::from)
                .map_err(|e| match e {
                    core::UpdateError::NotFound(_) => {
                        pyo3::exceptions::PyFileNotFoundError::new_err(format!(
                            "Mod {} not found",
                            mod_id
                        ))
                    }
                    _ => pyo3::exceptions::PyRuntimeError::new_err(format!("Nexus error: {}", e)),
                })
        })
    }

    /// Checks if a mod version has been updated (async).
    ///
    /// Args:
    ///     game: Game identifier.
    ///     mod_id: Numeric mod ID.
    ///     cached_version: Previously cached version string.
    ///
    /// Returns:
    ///     True if the current version differs from the cached version.
    ///
    /// Raises:
    ///     RuntimeError: If the request fails.
    ///     FileNotFoundError: If the mod doesn't exist.
    ///
    /// Example:
    ///     >>> updated = await client.has_update("fallout4", 1234, "1.0")
    ///     >>> if updated:
    ///     ...     print("Mod has been updated!")
    fn has_update<'py>(
        &self,
        py: Python<'py>,
        game: String,
        mod_id: u64,
        cached_version: String,
    ) -> PyResult<Bound<'py, PyAny>> {
        let client = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            client
                .has_update(&game, mod_id, &cached_version)
                .await
                .map_err(|e| match e {
                    core::UpdateError::NotFound(_) => {
                        pyo3::exceptions::PyFileNotFoundError::new_err(format!(
                            "Mod {} not found",
                            mod_id
                        ))
                    }
                    _ => pyo3::exceptions::PyRuntimeError::new_err(format!("Nexus error: {}", e)),
                })
        })
    }

    /// String representation.
    fn __repr__(&self) -> &'static str {
        "NexusClient()"
    }

    /// String representation.
    fn __str__(&self) -> &'static str {
        "Nexus Mods Client"
    }
}

/// Register Nexus components with the Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyNexusClient>()?;
    m.add_class::<PyNexusModInfo>()?;
    Ok(())
}
