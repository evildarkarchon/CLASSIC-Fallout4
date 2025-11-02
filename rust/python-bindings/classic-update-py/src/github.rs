//! Python bindings for GitHub API integration.

use classic_update_core as core;
use pyo3::prelude::*;

/// Python wrapper for GithubRelease.
///
/// This class contains all relevant information about a GitHub release.
///
/// Attributes:
///     tag_name: Release tag name (e.g., "v8.0.0").
///     name: Release name/title.
///     body: Release notes in Markdown format.
///     prerelease: Whether this is a pre-release.
///     draft: Whether this is a draft release.
///     html_url: URL to the release page.
///     assets: List of downloadable files.
///     created_at: Release creation timestamp.
///     published_at: Release publication timestamp (optional).
///
/// Example:
///     >>> import classic_update
///     >>> client = classic_update.GithubClient("evildarkarchon", "CLASSIC-Fallout4")
///     >>> release = await client.get_latest_release()
///     >>> print(f"Version: {release.tag_name}")
///     >>> print(f"Notes: {release.body}")
#[pyclass(name = "GithubRelease")]
#[derive(Clone)]
pub struct PyGithubRelease {
    inner: core::GithubRelease,
}

impl From<core::GithubRelease> for PyGithubRelease {
    fn from(release: core::GithubRelease) -> Self {
        Self { inner: release }
    }
}

#[pymethods]
impl PyGithubRelease {
    /// Gets the release tag name.
    #[getter]
    fn tag_name(&self) -> &str {
        &self.inner.tag_name
    }

    /// Gets the release name/title.
    #[getter]
    fn name(&self) -> &str {
        &self.inner.name
    }

    /// Gets the release notes.
    #[getter]
    fn body(&self) -> &str {
        &self.inner.body
    }

    /// Checks if this is a pre-release.
    #[getter]
    fn prerelease(&self) -> bool {
        self.inner.prerelease
    }

    /// Checks if this is a draft release.
    #[getter]
    fn draft(&self) -> bool {
        self.inner.draft
    }

    /// Gets the release page URL.
    #[getter]
    fn html_url(&self) -> &str {
        &self.inner.html_url
    }

    /// Gets the list of release assets.
    #[getter]
    fn assets(&self) -> Vec<PyGithubAsset> {
        self.inner
            .assets
            .iter()
            .map(|asset| PyGithubAsset::from(asset.clone()))
            .collect()
    }

    /// Gets the creation timestamp.
    #[getter]
    fn created_at(&self) -> &str {
        &self.inner.created_at
    }

    /// Gets the publication timestamp (if published).
    #[getter]
    fn published_at(&self) -> Option<&str> {
        self.inner.published_at.as_deref()
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!(
            "GithubRelease(tag_name='{}', name='{}', prerelease={})",
            self.inner.tag_name, self.inner.name, self.inner.prerelease
        )
    }

    /// String representation.
    fn __str__(&self) -> String {
        format!("{} - {}", self.inner.tag_name, self.inner.name)
    }
}

/// Python wrapper for GithubAsset.
///
/// This class represents a downloadable file attached to a GitHub release.
///
/// Attributes:
///     name: Asset name.
///     size: Asset size in bytes.
///     browser_download_url: Download URL.
///     content_type: MIME type.
///     download_count: Number of downloads.
///
/// Example:
///     >>> for asset in release.assets:
///     ...     print(f"{asset.name} ({asset.size} bytes)")
///     ...     print(f"  Download: {asset.browser_download_url}")
#[pyclass(name = "GithubAsset")]
#[derive(Clone)]
pub struct PyGithubAsset {
    inner: core::GithubAsset,
}

impl From<core::GithubAsset> for PyGithubAsset {
    fn from(asset: core::GithubAsset) -> Self {
        Self { inner: asset }
    }
}

#[pymethods]
impl PyGithubAsset {
    /// Gets the asset name.
    #[getter]
    fn name(&self) -> &str {
        &self.inner.name
    }

    /// Gets the asset size in bytes.
    #[getter]
    fn size(&self) -> u64 {
        self.inner.size
    }

    /// Gets the download URL.
    #[getter]
    fn browser_download_url(&self) -> &str {
        &self.inner.browser_download_url
    }

    /// Gets the MIME type.
    #[getter]
    fn content_type(&self) -> &str {
        &self.inner.content_type
    }

    /// Gets the download count.
    #[getter]
    fn download_count(&self) -> u64 {
        self.inner.download_count
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!(
            "GithubAsset(name='{}', size={}, downloads={})",
            self.inner.name, self.inner.size, self.inner.download_count
        )
    }

    /// String representation.
    fn __str__(&self) -> &str {
        &self.inner.name
    }
}

/// Python wrapper for GithubClient.
///
/// This class provides access to GitHub API for checking releases and updates.
///
/// Example:
///     >>> import classic_update
///     >>> import asyncio
///     >>>
///     >>> async def check_updates():
///     ...     client = classic_update.GithubClient("evildarkarchon", "CLASSIC-Fallout4")
///     ...
///     ...     # Get latest release
///     ...     latest = await client.get_latest_release()
///     ...     print(f"Latest version: {latest.tag_name}")
///     ...
///     ...     # Check if update available
///     ...     if client.has_update("v8.0.0", latest.tag_name):
///     ...         print("Update available!")
///     ...         print(f"Release notes:\\n{latest.body}")
///     >>>
///     >>> asyncio.run(check_updates())
#[pyclass(name = "GithubClient")]
pub struct PyGithubClient {
    inner: core::GithubClient,
}

#[pymethods]
impl PyGithubClient {
    /// Creates a new GitHub client for the specified repository.
    ///
    /// Args:
    ///     owner: Repository owner (e.g., "evildarkarchon").
    ///     repo: Repository name (e.g., "CLASSIC-Fallout4").
    ///
    /// Returns:
    ///     A new GithubClient instance.
    ///
    /// Example:
    ///     >>> client = classic_update.GithubClient("evildarkarchon", "CLASSIC-Fallout4")
    #[new]
    fn new(owner: String, repo: String) -> Self {
        Self {
            inner: core::GithubClient::new(owner, repo),
        }
    }

    /// Gets the latest release for the repository (async).
    ///
    /// Returns:
    ///     The latest non-draft, non-prerelease release.
    ///
    /// Raises:
    ///     RuntimeError: If the API request fails or no releases exist.
    ///
    /// Example:
    ///     >>> latest = await client.get_latest_release()
    ///     >>> print(f"Latest: {latest.tag_name}")
    fn get_latest_release<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let client = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            client
                .get_latest_release()
                .await
                .map(PyGithubRelease::from)
                .map_err(|e| {
                    pyo3::exceptions::PyRuntimeError::new_err(format!(
                        "GitHub API error: {}",
                        e
                    ))
                })
        })
    }

    /// Gets all releases for the repository (async).
    ///
    /// Args:
    ///     include_prereleases: Whether to include pre-releases (default: False).
    ///     include_drafts: Whether to include draft releases (default: False).
    ///
    /// Returns:
    ///     List of releases, sorted by publication date (newest first).
    ///
    /// Raises:
    ///     RuntimeError: If the API request fails.
    ///
    /// Example:
    ///     >>> releases = await client.get_all_releases()
    ///     >>> for release in releases:
    ///     ...     print(f"{release.tag_name}: {release.name}")
    #[pyo3(signature = (include_prereleases=false, include_drafts=false))]
    fn get_all_releases<'py>(
        &self,
        py: Python<'py>,
        include_prereleases: bool,
        include_drafts: bool,
    ) -> PyResult<Bound<'py, PyAny>> {
        let client = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            client
                .get_all_releases(include_prereleases, include_drafts)
                .await
                .map(|releases| {
                    releases
                        .into_iter()
                        .map(PyGithubRelease::from)
                        .collect::<Vec<_>>()
                })
                .map_err(|e| {
                    pyo3::exceptions::PyRuntimeError::new_err(format!(
                        "GitHub API error: {}",
                        e
                    ))
                })
        })
    }

    /// Checks if a newer version is available.
    ///
    /// Args:
    ///     current_version: Current version string (e.g., "v8.0.0" or "8.0.0").
    ///     latest_version: Latest version string to compare against.
    ///
    /// Returns:
    ///     True if latest_version is newer than current_version.
    ///
    /// Raises:
    ///     ValueError: If either version string is invalid.
    ///
    /// Example:
    ///     >>> if client.has_update("v8.0.0", "v8.1.0"):
    ///     ...     print("Update available!")
    fn has_update(&self, current_version: &str, latest_version: &str) -> PyResult<bool> {
        self.inner
            .has_update(current_version, latest_version)
            .map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!("Version error: {}", e))
            })
    }

    /// Gets the repository owner.
    ///
    /// Returns:
    ///     The repository owner string.
    #[getter]
    fn owner(&self) -> &str {
        self.inner.owner()
    }

    /// Gets the repository name.
    ///
    /// Returns:
    ///     The repository name string.
    #[getter]
    fn repo(&self) -> &str {
        self.inner.repo()
    }

    /// Constructs the full repository URL.
    ///
    /// Returns:
    ///     The full GitHub repository URL.
    ///
    /// Example:
    ///     >>> print(client.repo_url())
    ///     https://github.com/evildarkarchon/CLASSIC-Fallout4
    fn repo_url(&self) -> String {
        self.inner.repo_url()
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!(
            "GithubClient(owner='{}', repo='{}')",
            self.inner.owner(),
            self.inner.repo()
        )
    }

    /// String representation.
    fn __str__(&self) -> String {
        self.inner.repo_url()
    }
}

/// Register GitHub components with the Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyGithubClient>()?;
    m.add_class::<PyGithubRelease>()?;
    m.add_class::<PyGithubAsset>()?;
    Ok(())
}
