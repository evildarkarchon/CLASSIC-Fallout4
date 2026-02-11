//! Update checking bindings (classic-update-core)
//!
//! Exposes GithubClient class for release checking and version comparison
//! to JavaScript/TypeScript.
//!
//! ## Async Pattern
//! All async functions respect the ONE RUNTIME RULE by spawning work on the shared
//! Tokio runtime via `classic_shared_core::get_runtime()`.
//!
//! ## Exported API
//!
//! ### Classes
//! - `GithubClient` — Client for GitHub release checking and version comparison.
//!
//! ### DTOs
//! - `JsGithubRelease` — GitHub release information (tag, name, body, assets, etc.)
//! - `JsGithubAsset` — Downloadable file attached to a release.
//!
//! ### Free Functions
//! - `hasUpdate(currentVersion, latestVersion)` — Quick semver comparison (no client needed).
//! - `getLatestRelease(owner, repo)` — One-shot latest release fetch.
//! - `checkForUpdates(owner, repo, currentVersion)` — Convenience: fetch + compare.

use classic_update_core as core;

/// Convert any Display error to a napi::Error.
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

// ============================================================================
// DTO Structs
// ============================================================================

/// A downloadable file attached to a GitHub release.
///
/// Exposed as a plain JS object via `#[napi(object)]`.
#[napi(object)]
#[derive(Clone)]
pub struct JsGithubAsset {
    /// Asset filename (e.g., "CLASSIC-9.0.0-win64.zip")
    pub name: String,
    /// File size in bytes
    pub size: f64,
    /// Direct download URL
    pub browser_download_url: String,
    /// MIME content type (e.g., "application/zip")
    pub content_type: String,
    /// Number of times this asset has been downloaded
    pub download_count: f64,
}

/// GitHub release information.
///
/// Contains version tag, release notes, assets, and metadata.
/// Exposed as a plain JS object via `#[napi(object)]`.
#[napi(object)]
#[derive(Clone)]
pub struct JsGithubRelease {
    /// Release tag name (e.g., "v9.0.0")
    pub tag_name: String,
    /// Human-readable release title
    pub name: String,
    /// Release notes in Markdown format
    pub body: String,
    /// Whether this is a pre-release
    pub prerelease: bool,
    /// Whether this is a draft (unpublished) release
    pub draft: bool,
    /// URL to the release page on GitHub
    pub html_url: String,
    /// Downloadable files attached to this release
    pub assets: Vec<JsGithubAsset>,
    /// ISO 8601 creation timestamp
    pub created_at: String,
    /// ISO 8601 publication timestamp, or `undefined` for drafts
    pub published_at: Option<String>,
}

/// Result of a `checkForUpdates` call.
///
/// Bundles the latest release information with a boolean indicating
/// whether the caller's current version is outdated.
#[napi(object)]
#[derive(Clone)]
pub struct JsUpdateCheckResult {
    /// Whether an update is available (latest > current)
    pub update_available: bool,
    /// The latest release information
    pub latest_release: JsGithubRelease,
}

// ============================================================================
// Conversion helpers
// ============================================================================

/// Convert a core `GithubAsset` to its JS DTO.
fn core_asset_to_js(asset: &core::GithubAsset) -> JsGithubAsset {
    JsGithubAsset {
        name: asset.name.clone(),
        // NAPI-RS represents u64 as f64 for JavaScript number compatibility
        size: asset.size as f64,
        browser_download_url: asset.browser_download_url.clone(),
        content_type: asset.content_type.clone(),
        download_count: asset.download_count as f64,
    }
}

/// Convert a core `GithubRelease` to its JS DTO.
fn core_release_to_js(release: &core::GithubRelease) -> JsGithubRelease {
    JsGithubRelease {
        tag_name: release.tag_name.clone(),
        name: release.name.clone(),
        body: release.body.clone(),
        prerelease: release.prerelease,
        draft: release.draft,
        html_url: release.html_url.clone(),
        assets: release.assets.iter().map(core_asset_to_js).collect(),
        created_at: release.created_at.clone(),
        published_at: release.published_at.clone(),
    }
}

// ============================================================================
// GithubClient class
// ============================================================================

/// Client for checking GitHub releases and comparing versions.
///
/// Wraps `classic_update_core::GithubClient` with NAPI-RS bindings.
/// Automatically uses the `GITHUB_TOKEN` environment variable (or `.env` file)
/// for authenticated requests (increases rate limit from 60 to 5,000 req/hour).
///
/// ## Example (JavaScript)
/// ```js
/// const client = new GithubClient("evildarkarchon", "CLASSIC-Fallout4");
/// const latest = await client.getLatestRelease();
/// console.log(`Latest: ${latest.tagName}`);
///
/// if (client.hasUpdate("v8.0.0", latest.tagName)) {
///   console.log("Update available!");
/// }
/// ```
#[napi]
pub struct GithubClient {
    inner: core::GithubClient,
}

#[napi]
impl GithubClient {
    /// Create a new GitHub client for the specified repository.
    ///
    /// @param owner - Repository owner (e.g., "evildarkarchon").
    /// @param repo  - Repository name (e.g., "CLASSIC-Fallout4").
    /// @param token - Optional GitHub personal access token. If omitted, falls
    ///                back to the `GITHUB_TOKEN` environment variable.
    #[napi(constructor)]
    pub fn new(owner: String, repo: String, token: Option<String>) -> Self {
        // Filter empty strings — empty should behave like None and fall through
        // to the env-var-based constructor.
        let token = token.filter(|t| !t.is_empty());

        let inner = if let Some(t) = token {
            core::GithubClient::with_token(owner, repo, Some(t))
        } else {
            core::GithubClient::new(owner, repo)
        };
        Self { inner }
    }

    /// Get the repository owner.
    #[napi(getter)]
    pub fn owner(&self) -> String {
        self.inner.owner().to_string()
    }

    /// Get the repository name.
    #[napi(getter)]
    pub fn repo(&self) -> String {
        self.inner.repo().to_string()
    }

    /// Get the full GitHub repository URL.
    #[napi]
    pub fn repo_url(&self) -> String {
        self.inner.repo_url()
    }

    /// Check whether `latestVersion` is newer than `currentVersion`.
    ///
    /// Both strings accept an optional "v" prefix (e.g., "v8.0.0" or "8.0.0").
    ///
    /// @param currentVersion - The version to compare from.
    /// @param latestVersion  - The version to compare to.
    /// @returns `true` if latestVersion > currentVersion.
    /// @throws if either version string is not valid semver.
    #[napi]
    pub fn has_update(
        &self,
        current_version: String,
        latest_version: String,
    ) -> napi::Result<bool> {
        self.inner
            .has_update(&current_version, &latest_version)
            .map_err(to_napi_err)
    }

    /// Fetch the latest release for this repository.
    ///
    /// Returns the latest non-draft, non-prerelease release.
    /// Respects the ONE RUNTIME RULE.
    ///
    /// @returns A promise resolving to `JsGithubRelease`.
    /// @throws on HTTP errors, rate limiting, or if no releases exist.
    #[napi]
    pub async fn get_latest_release(&self) -> napi::Result<JsGithubRelease> {
        let client = self.inner.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();

        handle
            .spawn(async move { client.get_latest_release().await })
            .await
            .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
            .map(|r| core_release_to_js(&r))
            .map_err(to_napi_err)
    }

    /// Fetch all releases for this repository.
    ///
    /// @param includePrereleases - Include pre-releases (default: `false`).
    /// @param includeDrafts      - Include draft releases (default: `false`).
    /// @returns A promise resolving to an array of `JsGithubRelease`.
    /// @throws on HTTP errors or rate limiting.
    #[napi]
    pub async fn get_all_releases(
        &self,
        include_prereleases: Option<bool>,
        include_drafts: Option<bool>,
    ) -> napi::Result<Vec<JsGithubRelease>> {
        let client = self.inner.clone();
        let prereleases = include_prereleases.unwrap_or(false);
        let drafts = include_drafts.unwrap_or(false);
        let handle = classic_shared_core::get_runtime().handle().clone();

        handle
            .spawn(async move { client.get_all_releases(prereleases, drafts).await })
            .await
            .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
            .map(|releases| releases.iter().map(core_release_to_js).collect())
            .map_err(to_napi_err)
    }
}

// ============================================================================
// Free (stateless) functions
// ============================================================================

/// Quick semver comparison without creating a client.
///
/// @param currentVersion - The version you have (e.g., "v8.0.0").
/// @param latestVersion  - The version to compare against.
/// @returns `true` if latestVersion > currentVersion.
/// @throws if either version string is not valid semver.
#[napi]
pub fn has_update(current_version: String, latest_version: String) -> napi::Result<bool> {
    // GithubClient::has_update does not use any network — safe to create a throwaway.
    let client = core::GithubClient::new("_", "_");
    client
        .has_update(&current_version, &latest_version)
        .map_err(to_napi_err)
}

/// Fetch the latest release for a repository in a single call.
///
/// This is a convenience wrapper around `new GithubClient(owner, repo).getLatestRelease()`.
///
/// @param owner - Repository owner.
/// @param repo  - Repository name.
/// @returns A promise resolving to `JsGithubRelease`.
/// @throws on HTTP errors, rate limiting, or if no releases exist.
#[napi]
pub async fn get_latest_release(owner: String, repo: String) -> napi::Result<JsGithubRelease> {
    let client = core::GithubClient::new(owner, repo);
    let handle = classic_shared_core::get_runtime().handle().clone();

    handle
        .spawn(async move { client.get_latest_release().await })
        .await
        .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
        .map(|r| core_release_to_js(&r))
        .map_err(to_napi_err)
}

/// Check for updates in a single call: fetches the latest release and compares versions.
///
/// Combines `getLatestRelease` + `hasUpdate` into one convenient async function.
///
/// @param owner          - Repository owner (e.g., "evildarkarchon").
/// @param repo           - Repository name (e.g., "CLASSIC-Fallout4").
/// @param currentVersion - Your current version string (e.g., "v8.0.0").
/// @returns A promise resolving to `JsUpdateCheckResult`.
/// @throws on HTTP errors, rate limiting, version parse errors, or if no releases exist.
#[napi]
pub async fn check_for_updates(
    owner: String,
    repo: String,
    current_version: String,
) -> napi::Result<JsUpdateCheckResult> {
    let client = core::GithubClient::new(&owner, &repo);
    let handle = classic_shared_core::get_runtime().handle().clone();

    let current = current_version.clone();
    let release = handle
        .spawn(async move { client.get_latest_release().await })
        .await
        .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
        .map_err(to_napi_err)?;

    // Compare versions (synchronous, no network)
    let temp_client = core::GithubClient::new("_", "_");
    let update_available = temp_client
        .has_update(&current, &release.tag_name)
        .map_err(to_napi_err)?;

    Ok(JsUpdateCheckResult {
        update_available,
        latest_release: core_release_to_js(&release),
    })
}
