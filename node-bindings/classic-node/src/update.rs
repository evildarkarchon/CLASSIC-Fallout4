//! Update checking bindings (classic-update-core)
//!
//! Exposes GithubClient class for release checking and version comparison
//! to JavaScript/TypeScript, plus the yaml-update-delivery orchestrator.
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
//! - `JsYamlClientSchemaEntry` — Input entry for `checkYamlUpdate`/`applyYamlUpdate`.
//! - `JsYamlUpdateFile` — One file inside a YAML manifest (compatible or incompatible).
//! - `JsYamlUpdateStatus` — Discriminated status DTO for the YAML update check path.
//! - `JsYamlUpdateFileOutcome` — Per-file install outcome.
//! - `JsYamlUpdateReport` — Aggregate install report.
//! - `JsYamlRollbackOutcome` — Rollback result.
//!
//! ### Free Functions
//! - `hasUpdate(currentVersion, latestVersion)` — Quick semver comparison (no client needed).
//! - `getLatestRelease(owner, repo)` — One-shot latest release fetch.
//! - `checkForUpdates(owner, repo, currentVersion)` — Convenience: fetch + compare.
//! - `checkYamlUpdate(pagesUrl, tagPrefix, entries, enabled)` — YAML manifest check.
//! - `applyYamlUpdate(pagesUrl, tagPrefix, entries, enabled, approvedReleaseTag, approvedFileNames)` — Fetch + download + install the approved set.
//! - `rollbackYamlUpdate(fileName)` — Swap cache entry with its `.prev` sibling.

use classic_settings_core::{SchemaCompat, SchemaVersion};
use classic_update_core as core;
use std::path::PathBuf;

/// Convert any Display error to a napi::Error.
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

/// Build a core `UpdateCheckConfig` from the JS-facing `enabled` flag and
/// an optional explicit bundled-YAML root.
///
/// Node hosts run inside `node.exe` (or `bun.exe`), so the core fallback
/// that probes `std::env::current_exe()` for the install-tree shippable
/// copy cannot succeed — the parent of the interpreter is not the CLASSIC
/// install. Callers should resolve the package-local path (e.g. from
/// `__dirname` joined with `"CLASSIC Data/databases"`) and pass it here so
/// clean installs whose bundled bytes match the manifest are classified as
/// `upToDate` instead of false-positive `updateAvailable`. Passing `null`
/// (or an empty string) keeps the current_exe() fallback.
fn build_yaml_update_config(
    enabled: bool,
    bundled_yaml_dir: Option<String>,
) -> core::UpdateCheckConfig {
    let mut cfg = if enabled {
        core::UpdateCheckConfig::enabled()
    } else {
        core::UpdateCheckConfig::disabled()
    };
    if let Some(dir) = bundled_yaml_dir {
        if !dir.is_empty() {
            cfg = cfg.with_bundled_yaml_dir(PathBuf::from(dir));
        }
    }
    cfg
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
    pub fn new(owner: String, repo: String, token: Option<String>) -> napi::Result<Self> {
        // Filter empty strings — empty should behave like None and fall through
        // to the env-var-based constructor.
        let token = token.filter(|t| !t.is_empty());

        let inner = if let Some(t) = token {
            core::GithubClient::with_token(owner, repo, Some(t))
        } else {
            core::GithubClient::new(owner, repo)
        }
        .map_err(to_napi_err)?;

        Ok(Self { inner })
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
    let client = core::GithubClient::new("_", "_").map_err(to_napi_err)?;
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
    let client = core::GithubClient::new(owner, repo).map_err(to_napi_err)?;
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
    let client = core::GithubClient::new(&owner, &repo).map_err(to_napi_err)?;
    let handle = classic_shared_core::get_runtime().handle().clone();

    let current = current_version.clone();
    let release = handle
        .spawn(async move { client.get_latest_release().await })
        .await
        .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
        .map_err(to_napi_err)?;

    // Compare versions (synchronous, no network)
    let temp_client = core::GithubClient::new("_", "_").map_err(to_napi_err)?;
    let update_available = temp_client
        .has_update(&current, &release.tag_name)
        .map_err(to_napi_err)?;

    Ok(JsUpdateCheckResult {
        update_available,
        latest_release: core_release_to_js(&release),
    })
}

// ============================================================================
// YAML Update Delivery (yaml-update-delivery change)
// ============================================================================

/// String tag for `JsYamlUpdateStatus.tag`. Mirrors the CXX bridge's `TAG_*`
/// constants in spirit, but we use string tags here because TypeScript
/// consumers expect string-discriminated unions.
const YAML_TAG_DISABLED: &str = "disabled";
const YAML_TAG_UPDATE_AVAILABLE: &str = "updateAvailable";
const YAML_TAG_UP_TO_DATE: &str = "upToDate";
const YAML_TAG_UNKNOWN: &str = "unknown";

/// One entry in the per-file schema set that gates `checkYamlUpdate` /
/// `applyYamlUpdate`. Callers build one of these per shippable file
/// (e.g. "CLASSIC Main.yaml") with the client-accepted MAJOR.MINOR range
/// and (optionally) the currently-installed MAJOR.MINOR version.
#[napi(object)]
#[derive(Clone)]
pub struct JsYamlClientSchemaEntry {
    /// Canonical file name (e.g. `"CLASSIC Main.yaml"`).
    pub name: String,
    /// MAJOR the client is built to parse.
    pub accepted_major: u32,
    /// Minimum MINOR the client still supports at `acceptedMajor`.
    pub accepted_minimum_minor: u32,
    /// When `true`, `installedMajor` / `installedMinor` are treated as the
    /// currently-installed schema version. When `false`, the client treats
    /// every compatible manifest entry as "newer".
    pub has_installed: bool,
    /// MAJOR currently installed (ignored when `hasInstalled` is false).
    pub installed_major: u32,
    /// MINOR currently installed (ignored when `hasInstalled` is false).
    pub installed_minor: u32,
}

/// One file entry inside [`JsYamlUpdateStatus`] or [`JsYamlUpdateReport`].
///
/// Mirrors `YamlManifestFile` in `classic-update-core`, with the optional
/// `min_client_schema`/`max_client_schema` dropped because the binding
/// consumers don't currently read them.
#[napi(object)]
#[derive(Clone)]
pub struct JsYamlUpdateFile {
    /// Canonical file name.
    pub name: String,
    /// `MAJOR.MINOR` string from the manifest.
    pub schema_version: String,
    /// Hex-encoded SHA-256 of the file bytes.
    pub sha256: String,
    /// Size in bytes. NAPI represents u64 as f64 (JS number).
    pub size_bytes: f64,
    /// Absolute HTTPS URL of the release asset.
    pub download_url: String,
}

/// One rejection entry inside [`JsYamlUpdateStatus`]. Parallels the
/// `incompatibleFiles` list.
#[napi(object)]
#[derive(Clone)]
pub struct JsYamlRejectedFile {
    /// The file the client couldn't accept.
    pub file: JsYamlUpdateFile,
    /// Short, human-readable reason.
    pub reason: String,
}

/// Discriminated status DTO returned by `checkYamlUpdate`. Read `tag` first
/// — its value is one of:
/// - `"disabled"`: `Update Check: false`; nothing fetched.
/// - `"updateAvailable"`: `compatibleFiles` + `incompatibleFiles` populated.
/// - `"upToDate"`: `releaseTag` + `publishedAt` populated; may also carry
///   `incompatibleFiles` when a newer release exists but this CLASSIC build
///   cannot install those files.
/// - `"unknown"`: `unknownReason` populated.
#[napi(object)]
#[derive(Clone)]
pub struct JsYamlUpdateStatus {
    /// Discriminator. See module doc for possible values.
    pub tag: String,
    /// Manifest's `release_tag`, populated for `updateAvailable` / `upToDate`.
    pub release_tag: String,
    /// Manifest's `published_at`, populated for `updateAvailable` / `upToDate`.
    pub published_at: String,
    /// Files the client can install (compatible + newer). `updateAvailable` only.
    pub compatible_files: Vec<JsYamlUpdateFile>,
    /// Files the client rejected, each paired with its reason. Populated for
    /// `updateAvailable`, and also for some `upToDate` results when the
    /// published release contains files this build cannot install.
    pub incompatible_files: Vec<JsYamlRejectedFile>,
    /// Reason for `"unknown"` (e.g. `"manifest_version 2 not supported"`).
    pub unknown_reason: String,
}

/// Per-file install outcome inside [`JsYamlUpdateReport`]. When
/// `installed == true`, `schemaVersion` + `createdPrev` are populated.
/// When `installed == false`, `failureReason` is populated.
#[napi(object)]
#[derive(Clone)]
pub struct JsYamlUpdateFileOutcome {
    /// Canonical file name.
    pub name: String,
    /// `true` for `Installed`, `false` for `Failed`.
    pub installed: bool,
    /// Schema version installed (empty when `installed` is false).
    pub schema_version: String,
    /// Whether a `.prev` sibling was created (ignored when failed).
    pub created_prev: bool,
    /// Short reason when failed (empty on success).
    pub failure_reason: String,
}

/// Aggregate result of `applyYamlUpdate`.
#[napi(object)]
#[derive(Clone)]
pub struct JsYamlUpdateReport {
    /// Files that were installed atomically.
    pub installed: Vec<JsYamlUpdateFileOutcome>,
    /// Files that were skipped or failed.
    pub failed: Vec<JsYamlUpdateFileOutcome>,
}

/// Result of `rollbackYamlUpdate`. `rolledBack == false` with no exception
/// means `NoPreviousVersion` (the file has no `.prev` sibling).
#[napi(object)]
#[derive(Clone)]
pub struct JsYamlRollbackOutcome {
    /// `true` when the `.prev` copy is now the canonical cache entry.
    pub rolled_back: bool,
    /// The file that was queried / rolled back.
    pub file_name: String,
}

fn js_entries_to_core(entries: &[JsYamlClientSchemaEntry]) -> core::ClientSchemaSet {
    let mut set = core::ClientSchemaSet::new();
    for entry in entries {
        let accepted = SchemaCompat::new(entry.accepted_major, entry.accepted_minimum_minor);
        let installed = if entry.has_installed {
            Some(SchemaVersion::new(
                entry.installed_major,
                entry.installed_minor,
            ))
        } else {
            None
        };
        set.insert(entry.name.clone(), accepted, installed);
    }
    set
}

fn core_file_to_js(f: &core::YamlManifestFile) -> JsYamlUpdateFile {
    JsYamlUpdateFile {
        name: f.name.clone(),
        schema_version: f.schema_version.clone(),
        sha256: f.sha256.clone(),
        size_bytes: f.size_bytes as f64,
        download_url: f.download_url.clone(),
    }
}

fn core_status_to_js(status: core::YamlUpdateStatus) -> JsYamlUpdateStatus {
    let mut dto = JsYamlUpdateStatus {
        tag: YAML_TAG_DISABLED.into(),
        release_tag: String::new(),
        published_at: String::new(),
        compatible_files: Vec::new(),
        incompatible_files: Vec::new(),
        unknown_reason: String::new(),
    };
    match status {
        core::YamlUpdateStatus::Disabled => {
            dto.tag = YAML_TAG_DISABLED.into();
        }
        core::YamlUpdateStatus::UpToDate {
            manifest,
            incompatible_files,
        } => {
            dto.tag = YAML_TAG_UP_TO_DATE.into();
            dto.release_tag = manifest.release_tag;
            dto.published_at = manifest.published_at;
            // Carry rejection diagnostics through even on the "nothing to
            // do" branch so Node consumers can display the same skipped-file
            // UX regardless of tag.
            dto.incompatible_files = incompatible_files
                .iter()
                .map(|r| JsYamlRejectedFile {
                    file: core_file_to_js(&r.file),
                    reason: r.reason.clone(),
                })
                .collect();
        }
        core::YamlUpdateStatus::UpdateAvailable {
            manifest,
            compatible_files,
            incompatible_files,
        } => {
            dto.tag = YAML_TAG_UPDATE_AVAILABLE.into();
            dto.release_tag = manifest.release_tag;
            dto.published_at = manifest.published_at;
            dto.compatible_files = compatible_files.iter().map(core_file_to_js).collect();
            dto.incompatible_files = incompatible_files
                .iter()
                .map(|r| JsYamlRejectedFile {
                    file: core_file_to_js(&r.file),
                    reason: r.reason.clone(),
                })
                .collect();
        }
        core::YamlUpdateStatus::Unknown { reason } => {
            dto.tag = YAML_TAG_UNKNOWN.into();
            dto.unknown_reason = reason;
        }
    }
    dto
}

fn core_outcome_to_js(outcome: &core::FileInstallOutcome) -> JsYamlUpdateFileOutcome {
    match outcome {
        core::FileInstallOutcome::Installed {
            name,
            schema_version,
            created_prev,
        } => JsYamlUpdateFileOutcome {
            name: name.clone(),
            installed: true,
            schema_version: schema_version.clone(),
            created_prev: *created_prev,
            failure_reason: String::new(),
        },
        core::FileInstallOutcome::Failed { name, reason } => JsYamlUpdateFileOutcome {
            name: name.clone(),
            installed: false,
            schema_version: String::new(),
            created_prev: false,
            failure_reason: reason.clone(),
        },
    }
}

/// Check for a YAML data update.
///
/// Drives the Pages-first manifest fetch with anonymous API fallback, then
/// classifies the manifest against `entries`. When `enabled` is `false`,
/// returns `{ tag: "disabled" }` immediately without any HTTP call.
///
/// @param pagesUrl   Absolute HTTPS URL of the Pages manifest (normally
///                   `https://<owner>.github.io/<repo>/yaml-data/manifest-latest.json`).
/// @param tagPrefix  Release-tag prefix for the anonymous API fallback
///                   (e.g. `"yaml-data-v"`).
/// @param entries    Per-file accepted-range + currently-installed schema
///                   the client knows about.
/// @param enabled    `false` → short-circuit with `tag: "disabled"`.
/// @param bundledYamlDir  Install-tree directory containing the bundled
///                        shippable YAML files (`CLASSIC Data/databases`).
///                        Node callers should pass the package-local path
///                        (for example `path.join(__dirname, "CLASSIC Data", "databases")`)
///                        so clean installs whose bundled bytes already
///                        match the manifest are classified as `upToDate`.
///                        `null` / omitted falls back to probing
///                        `current_exe()`, which yields the wrong path under
///                        `node.exe` / `bun.exe`.
/// @throws on network failure that even the fallback can't recover from.
#[napi]
pub async fn check_yaml_update(
    pages_url: String,
    tag_prefix: String,
    entries: Vec<JsYamlClientSchemaEntry>,
    enabled: bool,
    bundled_yaml_dir: Option<String>,
) -> napi::Result<JsYamlUpdateStatus> {
    let client =
        core::GithubClient::new("evildarkarchon", "CLASSIC-Fallout4").map_err(to_napi_err)?;
    let set = js_entries_to_core(&entries);
    let config = build_yaml_update_config(enabled, bundled_yaml_dir);
    let handle = classic_shared_core::get_runtime().handle().clone();
    let status = handle
        .spawn(async move {
            core::check_yaml_update(&client, &pages_url, &tag_prefix, &set, config).await
        })
        .await
        .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
        .map_err(to_napi_err)?;
    Ok(core_status_to_js(status))
}

/// Fetch + download + atomically install the files the user approved at
/// check time.
///
/// This is the reviewed-decision form of apply:
///
/// - `enabled` mirrors the `Update Check` settings toggle. Passing `false`
///   rejects the call with an `update check disabled` error before any
///   HTTP is issued — the user's opt-out survives between check and apply.
/// - `approvedReleaseTag` + `approvedFileNames` come from a prior
///   `checkYamlUpdate` call the user confirmed. They pin the install to
///   the exact release the user reviewed; if the publisher has rotated
///   the manifest to a newer tag in the meantime, the call throws a
///   `decision stale` error instead of silently installing the new
///   release.
///
/// Returns per-file outcomes — a mixed batch is a valid success (the
/// successful subset is installed).
///
/// @param pagesUrl            Absolute Pages URL of `manifest-latest.json`.
/// @param tagPrefix           Release-tag prefix for the anonymous API fallback.
/// @param entries             Per-file accepted-range + installed-schema set.
/// @param enabled             Honors the `Update Check: false` setting end-to-end.
/// @param approvedReleaseTag  Release tag the user reviewed.
/// @param approvedFileNames   File names the user reviewed.
/// @param bundledYamlDir      Install-tree directory containing the bundled
///                            shippable YAML files (`CLASSIC Data/databases`).
///                            Node callers should pass the package-local path
///                            because the fallback probes `current_exe()` and
///                            therefore resolves to `node.exe` / `bun.exe`
///                            instead of the CLASSIC package directory.
/// @throws when the whole batch fails, when the update check is disabled,
///         or when the decision is stale.
#[napi]
pub async fn apply_yaml_update(
    pages_url: String,
    tag_prefix: String,
    entries: Vec<JsYamlClientSchemaEntry>,
    enabled: bool,
    approved_release_tag: String,
    approved_file_names: Vec<String>,
    bundled_yaml_dir: Option<String>,
) -> napi::Result<JsYamlUpdateReport> {
    let client =
        core::GithubClient::new("evildarkarchon", "CLASSIC-Fallout4").map_err(to_napi_err)?;
    let set = js_entries_to_core(&entries);
    let config = build_yaml_update_config(enabled, bundled_yaml_dir);
    let approved = core::ApprovedUpdate {
        release_tag: approved_release_tag,
        file_names: approved_file_names,
    };
    let handle = classic_shared_core::get_runtime().handle().clone();
    let report = handle
        .spawn(async move {
            core::apply_yaml_update_with_decision(
                &client,
                &pages_url,
                &tag_prefix,
                &set,
                config,
                &approved,
            )
            .await
        })
        .await
        .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
        .map_err(to_napi_err)?;
    Ok(JsYamlUpdateReport {
        installed: report.installed.iter().map(core_outcome_to_js).collect(),
        failed: report.failed.iter().map(core_outcome_to_js).collect(),
    })
}

/// Swap the cached YAML file with its `.prev` sibling (if any).
///
/// Returns `rolledBack: false` with no exception when the file has no
/// `.prev` (steady-state after a fresh install).
///
/// @param fileName Canonical file name (e.g. `"CLASSIC Main.yaml"`).
#[napi]
pub fn rollback_yaml_update(file_name: String) -> napi::Result<JsYamlRollbackOutcome> {
    let outcome = core::rollback_yaml_update(&file_name).map_err(to_napi_err)?;
    Ok(match outcome {
        core::RollbackOutcome::RolledBack { file_name } => JsYamlRollbackOutcome {
            rolled_back: true,
            file_name,
        },
        core::RollbackOutcome::NoPreviousVersion { file_name } => JsYamlRollbackOutcome {
            rolled_back: false,
            file_name,
        },
    })
}
