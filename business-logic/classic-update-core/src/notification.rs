//! App-update notification manifest fetching and classification.
//!
//! Mirrors the architectural shape of [`crate::yaml_update`] (Pages-first
//! with ETag, Releases fallback, typed manifest DTO, classification step)
//! but is *payload-free*: no SHA-256 checksums, no file download, no atomic
//! install, no rollback. See `docs/api/app-update-notification-delivery.md`
//! for the full delivery contract.
//!
//! # Channels
//!
//! 1. **Primary** — `https://<owner>.github.io/<repo>/app-notification/manifest-latest.json`
//!    with an `If-None-Match` ETag on subsequent fetches (shared helper in
//!    [`crate::manifest_fetch`]).
//! 2. **Fallback** — `GET /repos/{owner}/{repo}/releases` filtered by the
//!    dedicated `app-notification-v*` tag prefix, pulling `manifest.json`
//!    from the newest release.
//!
//! # No credentials
//!
//! Neither channel requires authentication. `GithubClient` may still attach
//! an `Authorization` header if `$GITHUB_TOKEN` is set (inherited from
//! `yaml_update`'s conventions) but nothing in this module *requires* one.

use crate::error::{Result, UpdateError};
use crate::github::GithubClient;
use crate::manifest_fetch::{
    CACHED_MANIFEST_FILENAME, ETAG_FILENAME, PagesError, try_pages, write_body_atomically,
};
use classic_path_core::PathError;
use semver::Version;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

/// GitHub Pages path segment where the notification manifest is mirrored.
const PAGES_PATH_SEGMENT: &str = "app-notification/manifest-latest.json";

/// Tag prefix used by the notification publish workflow and the Releases
/// fallback filter. Disjoint from both `v*` (binary releases) and
/// `yaml-data-v*` (YAML data publishes).
const TAG_PREFIX: &str = "app-notification-v";

/// Release-asset name the fallback downloads from the newest
/// `app-notification-v*` release.
const FALLBACK_ASSET_NAME: &str = "manifest.json";

/// Highest `manifest_version` MAJOR this client can parse. Bump only when a
/// breaking change to the notification manifest shape lands. MINOR may
/// advance freely — serde tolerates unknown fields so older clients keep
/// reading newer MINOR publishes.
///
/// Scoped `pub(crate)` intentionally: the value is already carried to
/// bindings via the `ManifestUnsupportedVersion { max_supported }` error
/// payload, so there is no reason to widen the public API surface (which
/// would require refreshing all three binding parity baselines).
pub(crate) const MAX_NOTIFICATION_MANIFEST_MAJOR: u32 = 1;

/// Synthetic cache marker written alongside `manifest-latest.json` when a
/// Releases-API fallback seeds the cache. Its presence and mtime are how
/// the next check knows the cached body is fallback-origin (not Pages) and
/// how old that fallback is. Required by
/// `specs/app-update-notification/spec.md` ("Fallback manifest populates
/// cache" — "synthetic cache marker").
const FALLBACK_MARKER_FILENAME: &str = "fallback.marker";

/// How long a fallback-seeded cache body remains reusable for subsequent
/// Pages-outage checks before we re-hit the Releases API. Short enough that
/// a maintainer's notification republish is picked up within a business day,
/// long enough that a prolonged Pages outage doesn't thrash the 60 req/hr
/// unauthenticated Releases rate limit.
const FALLBACK_CACHE_TTL: Duration = Duration::from_secs(6 * 60 * 60);

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

/// Optional display payload attached to a notification manifest. When
/// present, frontends SHOULD surface `title` and `body`, and SHOULD treat
/// `cta_url` as a call-to-action link.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AppNotificationDisplay {
    /// Short heading, e.g. `"Update available"`.
    pub title: String,
    /// Longer body text; may include changelog highlights.
    pub body: String,
    /// Optional call-to-action URL (download page, changelog, etc.).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cta_url: Option<String>,
}

/// The published app-notification manifest blob.
///
/// Serde tolerates unknown fields by default (we deliberately do NOT
/// annotate with `#[serde(deny_unknown_fields)]`), so future manifests
/// can add optional metadata without breaking older clients. Matches the
/// "unknown fields are tolerated" scenario in
/// `specs/app-update-notification/spec.md`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AppNotificationManifest {
    /// `MAJOR.MINOR` manifest shape identifier (e.g. `"1.0"`). Matches
    /// `^\d+\.\d+$`; validated post-deserialization.
    pub manifest_version: String,
    /// Binary-release tag the manifest advertises (e.g. `"v9.2.0"`).
    pub release_tag: String,
    /// Semantic version of the latest published binary (e.g. `"9.2.0"`).
    pub latest_version: String,
    /// RFC 3339 UTC timestamp of publication.
    pub published_at: String,
    /// Minimum client semver still considered supported. Absence means
    /// the publisher makes no deprecation claim for older clients.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub min_supported_version: Option<String>,
    /// Optional display payload for user-facing presentation.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub display: Option<AppNotificationDisplay>,
}

/// Classification outcome produced by [`classify`] or the fetch orchestrator.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Classification {
    /// Installed version is `>=` `latest_version`.
    UpToDate,
    /// Installed version is `<` `latest_version`; an upgrade is available.
    UpdateAvailable,
    /// Installed version is `<` `min_supported_version`; client is
    /// deprecated and SHOULD be upgraded.
    DeprecatedClient,
    /// Installed version could not be parsed as semver; classification
    /// cannot be determined. The caller SHOULD surface the companion
    /// [`NotificationStatus::parse_error`] message to the user.
    Unknown,
    /// No notification manifest exists on either the Pages or Releases
    /// channel. Produced only when both channels report the manifest absent.
    #[serde(rename = "not_published")]
    NotPublished,
}

/// Full result returned from [`check_app_notification`]. Carries the
/// classification plus the manifest fields a consumer needs to render
/// the result.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NotificationStatus {
    /// Outcome of the installed-vs-manifest comparison.
    pub classification: Classification,
    /// `latest_version` from the manifest, echoed for consumer rendering.
    pub latest_version: String,
    /// `published_at` from the manifest, echoed for consumer rendering.
    pub published_at: String,
    /// `min_supported_version` from the manifest, when set.
    pub min_supported_version: Option<String>,
    /// Optional display payload from the manifest.
    pub display: Option<AppNotificationDisplay>,
    /// When `classification == Unknown`, this carries a human-readable
    /// description of the installed-version parse failure so callers can
    /// surface it instead of silently treating the result as `UpToDate`.
    pub parse_error: Option<String>,
}

impl NotificationStatus {
    fn not_published() -> Self {
        Self {
            classification: Classification::NotPublished,
            latest_version: String::new(),
            published_at: String::new(),
            min_supported_version: None,
            display: None,
            parse_error: None,
        }
    }
}

// ---------------------------------------------------------------------------
// Manifest fetch
// ---------------------------------------------------------------------------

/// Fetch the notification manifest using the shared Pages-first helper.
///
/// Returns the parsed manifest on success. Pages-side transport or
/// invalid-body failures are reported as `Err` so the caller
/// ([`check_app_notification`]) can decide whether to fall back to the
/// Releases API.
///
/// `pages_url` is the absolute HTTPS URL of the Pages-hosted manifest.
/// Production callers pass [`build_app_notification_pages_url`]; tests
/// inject a mockito URL. The `cache_dir` argument points at the directory
/// where the cached manifest body and ETag are persisted; passing `None`
/// disables caching entirely.
pub async fn fetch_app_notification_manifest(
    client: &GithubClient,
    pages_url: &str,
    cache_dir: Option<&Path>,
) -> Result<AppNotificationManifest> {
    match try_pages(
        client,
        pages_url,
        cache_dir,
        parse_notification_manifest,
        validate_notification_manifest,
    )
    .await
    {
        Ok(manifest) => Ok(manifest),
        Err(PagesError::UnsupportedVersion(err)) => Err(err),
        Err(PagesError::Invalid(err)) | Err(PagesError::Transport(err)) => Err(err),
    }
}

/// Build the canonical GitHub Pages URL for the app-notification
/// manifest, using the `GithubClient`'s configured owner and repo.
/// Exposed publicly so the CXX/Node/Python binding layers can reuse the
/// exact URL-building logic rather than duplicating it.
pub fn build_app_notification_pages_url(client: &GithubClient) -> String {
    build_pages_url(client)
}

/// Fetch the notification manifest via the Releases-API fallback.
///
/// Lists non-draft releases filtered by the `app-notification-v*` tag
/// prefix, selects the highest-sorted tag, and pulls its attached
/// `manifest.json` asset. Prereleases are excluded so a maintainer's
/// reachability probe window does not surface unannounced manifests.
pub async fn fetch_via_releases_fallback(client: &GithubClient) -> Result<AppNotificationManifest> {
    fetch_via_releases_fallback_bytes(client)
        .await
        .map(|(manifest, _bytes)| manifest)
}

/// Internal variant of [`fetch_via_releases_fallback`] that additionally
/// returns the original asset bytes so callers can persist them to the
/// shared Pages cache location. Caching re-serialized manifest JSON would
/// drop unknown forward-compatible fields (the manifest struct does NOT
/// use `#[serde(deny_unknown_fields)]`, and serde silently discards
/// unknown keys during parse), so the only correct cache body is the raw
/// server response.
async fn fetch_via_releases_fallback_bytes(
    client: &GithubClient,
) -> Result<(AppNotificationManifest, Vec<u8>)> {
    // Exclude drafts AND prereleases — the publish workflow briefly flags
    // a new release as prerelease during reachability probing, and we
    // don't want to race that window.
    let releases = client.get_all_releases(false, false).await?;

    let mut candidates: Vec<_> = releases
        .into_iter()
        .filter(|r| r.tag_name.starts_with(TAG_PREFIX))
        .collect();

    if candidates.is_empty() {
        return Err(UpdateError::NotFound(format!(
            "no releases matching prefix `{TAG_PREFIX}` found via API fallback"
        )));
    }

    // Notification tags use the same semver scheme as binary releases
    // (`app-notification-vMAJOR.MINOR.PATCH`). Parse the semver suffix so
    // `9.10.0` sorts above `9.9.0`. Unparseable tags are demoted so they
    // never beat a parseable one.
    candidates.sort_by(|a, b| {
        let a_key = parse_notification_tag(&a.tag_name);
        let b_key = parse_notification_tag(&b.tag_name);
        match (a_key, b_key) {
            // Descending semver order.
            (Some(ak), Some(bk)) => bk.cmp(&ak),
            (Some(_), None) => std::cmp::Ordering::Less,
            (None, Some(_)) => std::cmp::Ordering::Greater,
            // Deterministic tie-break for unparseable tags.
            (None, None) => b.tag_name.cmp(&a.tag_name),
        }
    });
    let release = candidates.remove(0);

    let asset = release
        .assets
        .iter()
        .find(|a| a.name == FALLBACK_ASSET_NAME)
        .ok_or_else(|| {
            UpdateError::NotFound(format!(
                "release `{}` has no `{FALLBACK_ASSET_NAME}` asset",
                release.tag_name
            ))
        })?;

    let mut req = client.http_client().get(&asset.browser_download_url);
    if let Some(token) = client.token() {
        req = req.header("Authorization", format!("Bearer {token}"));
    }

    let response = req.send().await.map_err(UpdateError::HttpError)?;
    if !response.status().is_success() {
        return Err(UpdateError::GithubError(format!(
            "notification manifest asset GET returned {}",
            response.status()
        )));
    }
    let bytes = response
        .bytes()
        .await
        .map_err(UpdateError::HttpError)?
        .to_vec();
    let manifest = parse_notification_manifest(&bytes)?;
    validate_notification_manifest(&manifest)?;
    Ok((manifest, bytes))
}

// ---------------------------------------------------------------------------
// Classification
// ---------------------------------------------------------------------------

/// Compare the caller-supplied installed version against the manifest's
/// `latest_version` and optional `min_supported_version`, emitting one of
/// four comparison [`Classification`] outcomes.
///
/// The installed-version string is trimmed of a leading `v` or `V`
/// before semver parse. When `installed_version` fails semver parsing
/// the returned status has `classification = Unknown` and a non-empty
/// `parse_error` describing the failure.
pub fn classify(installed_version: &str, manifest: &AppNotificationManifest) -> NotificationStatus {
    let stripped = installed_version
        .strip_prefix('v')
        .or_else(|| installed_version.strip_prefix('V'))
        .unwrap_or(installed_version);

    match Version::parse(stripped) {
        Ok(installed) => {
            // min_supported_version takes precedence over latest_version:
            // a deprecated client still reports DeprecatedClient even when
            // it happens to equal `latest_version` (edge case, but keeps
            // the signal ordered by severity).
            if let Some(min_str) = manifest.min_supported_version.as_deref() {
                let min_stripped = min_str
                    .strip_prefix('v')
                    .or_else(|| min_str.strip_prefix('V'))
                    .unwrap_or(min_str);
                if let Ok(min_version) = Version::parse(min_stripped) {
                    if installed < min_version {
                        return status_from(Classification::DeprecatedClient, manifest, None);
                    }
                }
            }

            let latest_stripped = manifest
                .latest_version
                .strip_prefix('v')
                .or_else(|| manifest.latest_version.strip_prefix('V'))
                .unwrap_or(manifest.latest_version.as_str());
            match Version::parse(latest_stripped) {
                Ok(latest) => {
                    let classification = if installed < latest {
                        Classification::UpdateAvailable
                    } else {
                        // installed >= latest — treat CI/pre-release builds
                        // "ahead of latest" as UpToDate, not UpdateAvailable.
                        Classification::UpToDate
                    };
                    status_from(classification, manifest, None)
                }
                Err(err) => {
                    // Manifest itself carries an unparseable latest_version —
                    // surface as Unknown so the consumer does not silently
                    // claim UpToDate.
                    let message = format!(
                        "manifest latest_version `{}` is not valid semver: {err}",
                        manifest.latest_version,
                    );
                    status_from(Classification::Unknown, manifest, Some(message))
                }
            }
        }
        Err(err) => {
            let message =
                format!("installed version `{installed_version}` is not valid semver: {err}");
            status_from(Classification::Unknown, manifest, Some(message))
        }
    }
}

/// Orchestrator: Pages → Releases fallback → classify. Returns a populated
/// [`NotificationStatus`] with classification and the manifest fields a
/// consumer needs to render the check outcome.
///
/// `owner` / `repo` are the GitHub org/repo slug (e.g. `("evildarkarchon",
/// "CLASSIC-Fallout4")`). `installed_version` is the caller-reported
/// client semver (leading `v`/`V` tolerated).
pub async fn check_app_notification(
    owner: &str,
    repo: &str,
    installed_version: &str,
) -> Result<NotificationStatus> {
    check_app_notification_with_env(owner, repo, installed_version, process_env_lookup).await
}

/// Testable form of [`check_app_notification`] that reads cache-root
/// environment variables through a caller-supplied closure.
///
/// Production code calls [`check_app_notification`], which threads
/// `std::env::var` through this function. Integration tests pass a
/// closure backed by a `HashMap` so they can drive the cache resolver
/// at a sandboxed location on disk without mutating the process
/// environment (process-env mutation is `unsafe` in edition 2024 and
/// forbidden by this crate's `unsafe_code = "deny"` lint). This is the
/// seam that makes the `NotificationCacheIo` path end-to-end observable
/// — the test plants a regular file where the namespaced cache
/// directory should live, the injected env points
/// `ensure_notification_cache_dir_with_env` at that location, and
/// `create_dir_all` fails deterministically with an `io::Error`.
///
/// The closure SHOULD return `None` for unset *or* empty values so an
/// empty `%LOCALAPPDATA%` degrades to the next fallback rather than
/// producing an empty path. That matches
/// [`classic_path_core::notification_cache_dir_with_env`]'s contract.
///
/// Caller-input validation runs before client/cache setup so an
/// unparseable `installed_version` remains deterministic even on
/// machines whose notification cache cannot be materialized.
pub async fn check_app_notification_with_env<F>(
    owner: &str,
    repo: &str,
    installed_version: &str,
    env: F,
) -> Result<NotificationStatus>
where
    F: Fn(&str) -> Option<String>,
{
    // Keep public callers on the same deterministic error path as
    // `check_app_notification_with`: bad caller input wins before any
    // client construction or cache directory materialization.
    validate_installed_version(installed_version)?;

    let client = GithubClient::new(owner, repo)?;
    let cache_dir = map_ensure_cache_result(
        classic_path_core::ensure_notification_cache_dir_with_env(owner, repo, env),
    )?;

    let pages_url = build_pages_url(&client);
    check_app_notification_with(&client, &pages_url, cache_dir.as_deref(), installed_version).await
}

/// Read a process env var, returning `None` for unset *or* empty values
/// so that `%LOCALAPPDATA%=""` degrades to the next fallback rather
/// than producing a bogus empty path. Mirrors
/// `classic_path_core::notification_cache::process_env_lookup` so
/// production callers of [`check_app_notification`] see byte-identical
/// env resolution through either entry point.
fn process_env_lookup(name: &str) -> Option<String> {
    match std::env::var(name) {
        Ok(s) if !s.is_empty() => Some(s),
        _ => None,
    }
}

/// Project a [`classic_path_core::ensure_notification_cache_dir`] result
/// onto this module's two-way contract:
///
/// - `Ok(dir)` ⇒ `Ok(Some(dir))` — cache available.
/// - `Err(PathError::IoError { path, source })` ⇒
///   `Err(UpdateError::NotificationCacheIo { .. })` — the cache root was
///   resolvable but directory creation failed (permission denied, disk
///   full, parent-is-a-file, etc.). Surfaced as the typed variant so the
///   binding-layer `CACHE_IO` discriminator is actually reachable.
/// - `Err(PathError::InvalidPath(..))` ⇒ `Ok(None)` — the cache root
///   itself couldn't be resolved (e.g. `LOCALAPPDATA`/`APPDATA`/`HOME`
///   all unset in a stripped-down env, or owner/repo failed the
///   path-segment validator). Degrades to no-caching per design D-06
///   "best-effort, rebuildable"; the `NotificationCacheIo` docstring
///   explicitly calls out that this class of failure is NOT reported
///   through that variant.
///
/// Split as a free function so unit tests can drive both branches with
/// hand-constructed `PathError` values without mutating the process
/// environment (edition-2024 `unsafe` + this crate's `unsafe_code`
/// policy would make that awkward otherwise).
fn map_ensure_cache_result(
    result: std::result::Result<PathBuf, PathError>,
) -> Result<Option<PathBuf>> {
    match result {
        Ok(dir) => Ok(Some(dir)),
        Err(PathError::IoError { path, source }) => {
            Err(UpdateError::NotificationCacheIo { path, source })
        }
        Err(PathError::InvalidPath(msg)) => {
            // Env-resolution / segment-validation failure. Best-effort
            // degrade to no-caching per design D-06; callers still see
            // a successful check if the network legs work.
            log::warn!(
                "notification cache directory unavailable; proceeding without caching: {msg}"
            );
            Ok(None)
        }
        // `ensure_notification_cache_dir` does not produce any other
        // variant today, but match exhaustively so a future path-core
        // extension cannot silently collapse an I/O-flavored failure
        // into the degrade-to-None branch. Wrap under
        // `NotificationCacheIo` with the `io::ErrorKind::Other` fallback
        // since the source variants we catch here don't all carry a
        // `PathBuf` the caller could meaningfully retry against.
        Err(other) => {
            let message = other.to_string();
            Err(UpdateError::NotificationCacheIo {
                path: PathBuf::new(),
                source: std::io::Error::other(message),
            })
        }
    }
}

/// Testable form of [`check_app_notification`] that takes a caller-built
/// [`GithubClient`], an explicit Pages URL, and an optional cache
/// directory. Tests pass a client constructed via
/// [`GithubClient::with_base_url`] pointing at a mockito server, a
/// matching mockito-hosted Pages URL, and a tempdir for the cache.
pub async fn check_app_notification_with(
    client: &GithubClient,
    pages_url: &str,
    cache_dir: Option<&Path>,
    installed_version: &str,
) -> Result<NotificationStatus> {
    // Caller-input validation runs before any network or cache I/O so
    // an unparseable `installed_version` always surfaces as the typed
    // `NotificationInstalledVersionParse` variant rather than being
    // downgraded to a successful `Classification::Unknown` status.
    // `classify` still defends against a manifest-side `latest_version`
    // that slips past `validate_notification_manifest` (belt and
    // suspenders via the cache path), so its `Unknown` branch stays
    // reachable from that direction only.
    validate_installed_version(installed_version)?;

    match fetch_app_notification_manifest(client, pages_url, cache_dir).await {
        Ok(manifest) => {
            // Pages leg succeeded. Any fallback marker left on disk from a
            // previous outage is now stale — clear it so a future Pages
            // failure re-hits Releases for a fresh body instead of reusing
            // a body that Pages has since superseded.
            clear_fallback_marker(cache_dir);
            Ok(classify(installed_version, &manifest))
        }
        Err(pages_err) => {
            // A future MAJOR bump of `manifest_version` the client cannot
            // parse will fail identically at the Releases fallback (same
            // schema, same asset bytes). Short-circuit instead of wasting
            // an API request and returning an ambiguous
            // `NotificationFetchFailed`.
            if let UpdateError::ManifestUnsupportedVersion { .. } = pages_err {
                return Err(pages_err);
            }
            // During a prolonged Pages outage, reuse a fallback-seeded
            // manifest that is still within TTL instead of hammering the
            // Releases API on every startup. This is the reuse path the
            // spec requires ("Fallback manifest populates cache" + the
            // review finding on the cache seed never suppressing repeated
            // Releases hits).
            if let Some(cached) = try_fallback_cache(cache_dir) {
                return Ok(classify(installed_version, &cached));
            }
            match fetch_via_releases_fallback_bytes(client).await {
                Ok((manifest, bytes)) => {
                    // Seed the cache so the next check during the same
                    // outage window can short-circuit above. Errors here
                    // are logged and swallowed — a cache write failure
                    // MUST NOT demote a successful classification to a
                    // notification error.
                    persist_fallback_manifest_body(cache_dir, &bytes);
                    Ok(classify(installed_version, &manifest))
                }
                // Propagate schema/validation rejections from the Releases
                // fallback leg directly instead of folding them into the
                // ambiguous `NotificationFetchFailed`. The fallback asset is
                // the same schema as the Pages leg, so these deterministic
                // bindings-surface signals must not be reported as transient
                // transport failures exactly when Pages is down or blocked.
                Err(
                    fallback_err @ (UpdateError::ManifestUnsupportedVersion { .. }
                    | UpdateError::ManifestInvalid { .. }
                    | UpdateError::NotificationDecode { .. }),
                ) => Err(fallback_err),
                Err(fallback_err)
                    if matches!(&pages_err, UpdateError::NotFound(_))
                        && matches!(&fallback_err, UpdateError::NotFound(_)) =>
                {
                    Ok(NotificationStatus::not_published())
                }
                Err(fallback_err) => Err(UpdateError::NotificationFetchFailed {
                    pages_error: pages_err.to_string(),
                    releases_error: fallback_err.to_string(),
                }),
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Seed the Pages manifest cache with a Releases-API fallback body.
///
/// On a successful fallback we atomically replace the body at
/// [`CACHED_MANIFEST_FILENAME`] (same location the Pages leg uses)
/// via temp-file + rename, remove any stale [`ETAG_FILENAME`], and
/// write a fresh [`FALLBACK_MARKER_FILENAME`]. Clearing the ETag is
/// essential: the fallback asset carries no server-issued ETag that
/// pairs with Pages' CDN, so leaving a previous Pages ETag in place
/// would cause the next request to send `If-None-Match: <stale>`,
/// potentially take a `304 Not Modified`, and return the fallback
/// body as though it were Pages-authoritative. Removing the ETag
/// forces a full GET on the next call, which repopulates both files
/// with fresh Pages content.
///
/// # Atomicity invariant
///
/// A present, in-TTL marker implies the body it names was successfully
/// replaced by *this* call — not by a previous one. We get there by:
///
/// 1. Writing the new body to a unique temp sibling.
/// 2. `rename`-ing the sibling onto [`CACHED_MANIFEST_FILENAME`].
/// 3. *Only then* writing/refreshing the marker.
///
/// On any body-write failure (Windows `ERROR_SHARING_VIOLATION` from AV
/// holding the body file open is the motivating case), the marker is
/// explicitly removed. Without that step, the previous body bytes would
/// still be on disk paired with a still-fresh marker, and
/// `try_fallback_cache_at` would silently reuse stale `latest_version`
/// / `min_supported_version` state for up to `FALLBACK_CACHE_TTL`
/// exactly during the Pages outage when the fallback path is supposed
/// to be the source of truth.
///
/// The marker's mtime is what [`try_fallback_cache`] reads to enforce
/// [`FALLBACK_CACHE_TTL`] — as long as the marker exists and is within
/// TTL, a subsequent Pages outage reuses the cached body instead of
/// re-hitting the Releases API.
///
/// All I/O errors are logged and swallowed by design: the classification
/// result is already good, and a cache-population failure should not
/// demote it to `NotificationFetchFailed`.
fn persist_fallback_manifest_body(cache_dir: Option<&Path>, bytes: &[u8]) {
    let Some(dir) = cache_dir else {
        return;
    };
    if let Err(e) = std::fs::create_dir_all(dir) {
        log::warn!(
            "failed to ensure notification cache dir {} for fallback persist: {e}",
            dir.display(),
        );
        return;
    }

    let body_path = dir.join(CACHED_MANIFEST_FILENAME);
    let marker_path = dir.join(FALLBACK_MARKER_FILENAME);
    let etag_path = dir.join(ETAG_FILENAME);

    let body_ok = match write_body_atomically(&body_path, bytes) {
        Ok(()) => true,
        Err(e) => {
            log::warn!(
                "failed to atomically replace fallback manifest body at {}: {e}",
                body_path.display(),
            );
            false
        }
    };

    match std::fs::remove_file(&etag_path) {
        Ok(()) => {}
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(e) => {
            log::warn!(
                "failed to clear stale Pages ETag at {} after fallback: {e}",
                etag_path.display(),
            );
        }
    }

    if body_ok {
        if let Err(e) = std::fs::write(&marker_path, b"") {
            log::warn!(
                "failed to persist fallback cache marker to {}: {e}",
                marker_path.display(),
            );
        }
    } else {
        // The previous body may still be on disk because the atomic
        // replacement was rejected before it could rename onto it.
        // Drop the marker so `try_fallback_cache_at` refuses to reuse
        // that stale body and the next check routes back to Pages /
        // Releases instead of locking in stale state for TTL.
        match std::fs::remove_file(&marker_path) {
            Ok(()) => {}
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
            Err(e) => {
                log::warn!(
                    "failed to clear fallback cache marker at {} after body-write failure: {e}",
                    marker_path.display(),
                );
            }
        }
    }
}

/// Attempt to reuse a fallback-seeded cached manifest.
///
/// Returns `Some(manifest)` only when all of:
/// - a cache dir is configured,
/// - the [`FALLBACK_MARKER_FILENAME`] exists and its mtime is within
///   [`FALLBACK_CACHE_TTL`],
/// - the cached body parses and validates.
///
/// Any I/O failure, stale marker, or validation failure returns `None`,
/// which routes the caller to the full Releases-API fallback. The marker
/// mtime — not a persisted timestamp inside the marker itself — is the
/// authoritative age source so we don't have to synchronize a wall-clock
/// write with the body write.
fn try_fallback_cache(cache_dir: Option<&Path>) -> Option<AppNotificationManifest> {
    try_fallback_cache_at(cache_dir, SystemTime::now())
}

/// Testable form of [`try_fallback_cache`]. The `now` parameter is what
/// the TTL check measures marker-mtime against, so unit tests can pass a
/// future `now` to exercise the stale-marker branch without needing a
/// filesystem mtime-backdating helper.
fn try_fallback_cache_at(
    cache_dir: Option<&Path>,
    now: SystemTime,
) -> Option<AppNotificationManifest> {
    let dir = cache_dir?;
    let marker_path = dir.join(FALLBACK_MARKER_FILENAME);
    let metadata = std::fs::metadata(&marker_path).ok()?;
    let modified = metadata.modified().ok()?;
    let age = now.duration_since(modified).ok()?;
    if age > FALLBACK_CACHE_TTL {
        return None;
    }
    let body_path = dir.join(CACHED_MANIFEST_FILENAME);
    let bytes = std::fs::read(&body_path).ok()?;
    let manifest = parse_notification_manifest(&bytes).ok()?;
    validate_notification_manifest(&manifest).ok()?;
    Some(manifest)
}

/// Remove the fallback marker if present. Called on any successful Pages
/// fetch so the body written by `try_pages` is once again the
/// Pages-authoritative copy. A missing marker is a no-op.
fn clear_fallback_marker(cache_dir: Option<&Path>) {
    let Some(dir) = cache_dir else {
        return;
    };
    let marker_path = dir.join(FALLBACK_MARKER_FILENAME);
    match std::fs::remove_file(&marker_path) {
        Ok(()) => {}
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(e) => {
            log::warn!(
                "failed to clear fallback cache marker at {} after Pages success: {e}",
                marker_path.display(),
            );
        }
    }
}

fn build_pages_url(client: &GithubClient) -> String {
    format!(
        "https://{owner}.github.io/{repo}/{segment}",
        owner = client.owner(),
        repo = client.repo(),
        segment = PAGES_PATH_SEGMENT,
    )
}

fn parse_notification_manifest(bytes: &[u8]) -> Result<AppNotificationManifest> {
    // Parse once into a generic `Value` so missing-field detection can
    // inspect the root object programmatically. Relying on serde_json's
    // human-readable "missing field `<name>`" error text would tie this
    // projection to a string format that the crate does not guarantee
    // across versions. Syntax errors (invalid JSON bytes) propagate
    // through `?` as `UpdateError::JsonError`, matching previous behavior.
    let value: serde_json::Value = serde_json::from_slice(bytes)?;

    // When the root is an object (the only valid shape for this manifest),
    // check each required field up front so a missing one becomes a typed
    // `NotificationDecode { field }`. Required here MUST stay in sync with
    // the non-`Option`, non-`#[serde(default)]` fields on
    // `AppNotificationManifest` — see `validate_notification_manifest`
    // below, which enforces additional emptiness constraints on the same
    // set after a successful deserialize.
    if let Some(object) = value.as_object() {
        for field in [
            "manifest_version",
            "release_tag",
            "latest_version",
            "published_at",
        ] {
            if !object.contains_key(field) {
                return Err(UpdateError::NotificationDecode {
                    field: field.to_string(),
                });
            }
        }
    }

    // Fall back to serde's own structural deserialization for type/shape
    // errors on fields that are present (e.g. a number where a string was
    // expected). Those surface as `JsonError` — deliberately not projected
    // into `NotificationDecode`, which is reserved for the missing/invalid
    // *required-field* cases the binding layer pattern-matches on.
    serde_json::from_value::<AppNotificationManifest>(value).map_err(UpdateError::from)
}

fn validate_notification_manifest(manifest: &AppNotificationManifest) -> Result<()> {
    // `manifest_version` must be MAJOR.MINOR (two numeric components) AND
    // its MAJOR must not exceed this client's max. A future MAJOR bump
    // signals a breaking schema change — surface as the typed
    // `ManifestUnsupportedVersion` variant so `manifest_fetch::PagesError`
    // can route it past the Releases fallback (same-schema assets would
    // fail identically there).
    let (major, _minor) = parse_major_minor(&manifest.manifest_version).ok_or_else(|| {
        UpdateError::NotificationDecode {
            field: "manifest_version".into(),
        }
    })?;
    if major > MAX_NOTIFICATION_MANIFEST_MAJOR {
        return Err(UpdateError::ManifestUnsupportedVersion {
            found: major,
            max_supported: MAX_NOTIFICATION_MANIFEST_MAJOR,
        });
    }

    // `release_tag` must be a `v<SEMVER>` string (matches what the publish
    // workflow emits). An unparseable tag would otherwise slip past the
    // Pages validator and surface downstream as a classification that
    // silently doesn't match the binary-release tag namespace.
    if !is_release_tag(&manifest.release_tag) {
        return Err(UpdateError::NotificationDecode {
            field: "release_tag".into(),
        });
    }

    // `latest_version` must be valid semver. Classify already has a
    // defensive fallback, but rejecting at validate-time keeps bad
    // manifests out of the cache in the first place so a future `304` path
    // cannot return them.
    if !is_semver_with_optional_v(&manifest.latest_version) {
        return Err(UpdateError::NotificationDecode {
            field: "latest_version".into(),
        });
    }

    // `min_supported_version` is optional, but if set it MUST parse as
    // semver — otherwise the deprecation signal silently degrades to
    // "no-op" in `classify`, which is exactly how a mis-typed
    // `min_supported_version` would let deprecated clients keep running
    // without warning.
    if let Some(min) = manifest.min_supported_version.as_deref() {
        if !is_semver_with_optional_v(min) {
            return Err(UpdateError::NotificationDecode {
                field: "min_supported_version".into(),
            });
        }
    }

    // Cross-field invariant: `min_supported_version` MUST NOT exceed
    // `latest_version`. Each field parses individually by this point,
    // but `classify` gives `min_supported_version` precedence — so a
    // publisher typo like `latest_version=9.1.0` with
    // `min_supported_version=9.2.0` would otherwise mark even the
    // advertised latest build as `DeprecatedClient`. Rejecting at
    // validate-time also keeps the bad body out of the cache, so a
    // future `304` path cannot return it either.
    if let Some(min) = manifest.min_supported_version.as_deref() {
        if let (Some(min_v), Some(latest_v)) = (
            parse_semver_with_optional_v(min),
            parse_semver_with_optional_v(&manifest.latest_version),
        ) {
            if min_v > latest_v {
                return Err(UpdateError::ManifestInvalid {
                    reason: format!(
                        "min_supported_version `{}` exceeds latest_version `{}`",
                        min, manifest.latest_version,
                    ),
                });
            }
        }
    }

    // `published_at` must be an RFC 3339 timestamp (shape-only — we do not
    // validate calendar correctness like Feb 30 because the publisher
    // sources this from git's ISO-strict output).
    if !is_rfc3339(&manifest.published_at) {
        return Err(UpdateError::NotificationDecode {
            field: "published_at".into(),
        });
    }

    // `display.cta_url` is optional, but when set it MUST be HTTPS. The
    // GUI opens this URL from an update prompt, so a typo'd or
    // compromised manifest could downgrade the user onto an
    // unauthenticated destination at the exact moment they are being
    // asked to fetch an update. Defense in depth alongside the
    // publish-side check in `tools/publish_app_notification/validate.py`
    // — rejecting at runtime ALSO protects clients against a tampered
    // Pages or Releases asset that bypassed the publish workflow
    // entirely.
    if let Some(display) = manifest.display.as_ref() {
        if let Some(cta) = display.cta_url.as_deref() {
            if !is_https_cta_url(cta) {
                return Err(UpdateError::NotificationDecode {
                    field: "display.cta_url".into(),
                });
            }
        }
    }

    Ok(())
}

/// Parse a `MAJOR.MINOR` pair into `(major, minor)` u32s, rejecting any
/// other shape (single component, three components, leading/trailing dot,
/// non-digit runs, leading `v`, pre-release suffix, empty).
fn parse_major_minor(s: &str) -> Option<(u32, u32)> {
    let mut parts = s.split('.');
    let major_str = parts.next()?;
    let minor_str = parts.next()?;
    if parts.next().is_some() {
        return None;
    }
    if major_str.is_empty() || minor_str.is_empty() {
        return None;
    }
    if !major_str.bytes().all(|b| b.is_ascii_digit())
        || !minor_str.bytes().all(|b| b.is_ascii_digit())
    {
        return None;
    }
    let major = major_str.parse::<u32>().ok()?;
    let minor = minor_str.parse::<u32>().ok()?;
    Some((major, minor))
}

fn is_semver_with_optional_v(s: &str) -> bool {
    parse_semver_with_optional_v(s).is_some()
}

/// Parse a SemVer string that tolerates an optional leading `v`/`V`,
/// returning the parsed [`Version`] on success. Used by the cross-field
/// invariant check in [`validate_notification_manifest`] so the
/// `min_supported_version <= latest_version` comparison can reuse the
/// same prefix-tolerance as the individual shape checks.
fn parse_semver_with_optional_v(s: &str) -> Option<Version> {
    let stripped = s
        .strip_prefix('v')
        .or_else(|| s.strip_prefix('V'))
        .unwrap_or(s);
    Version::parse(stripped).ok()
}

fn is_release_tag(tag: &str) -> bool {
    // Publish workflow always emits `v<SEMVER>` (lowercase). Don't accept
    // bare semver — the manifest's `release_tag` has to match the live git
    // tag, and our tag namespace uses the `v` prefix.
    let Some(rest) = tag.strip_prefix('v') else {
        return false;
    };
    Version::parse(rest).is_ok()
}

/// Shape-only RFC 3339 check: `YYYY-MM-DDTHH:MM:SS(.fraction)?(Z|±HH:MM)`.
/// Accepts the `T`/`t` date-time separator per the spec. Does NOT validate
/// month/day/hour ranges — the publisher tool sources this field from git's
/// `iso-strict` output, so shape is sufficient.
fn is_rfc3339(s: &str) -> bool {
    let b = s.as_bytes();
    // Shortest valid form: `YYYY-MM-DDTHH:MM:SSZ` = 20 bytes.
    if b.len() < 20 {
        return false;
    }
    // Date: YYYY-MM-DD
    for i in [0, 1, 2, 3, 5, 6, 8, 9] {
        if !b[i].is_ascii_digit() {
            return false;
        }
    }
    if b[4] != b'-' || b[7] != b'-' {
        return false;
    }
    if b[10] != b'T' && b[10] != b't' {
        return false;
    }
    // Time: HH:MM:SS
    for i in [11, 12, 14, 15, 17, 18] {
        if !b[i].is_ascii_digit() {
            return false;
        }
    }
    if b[13] != b':' || b[16] != b':' {
        return false;
    }
    // Optional fractional seconds, then Z or ±HH:MM.
    let mut i = 19;
    if b.get(i) == Some(&b'.') {
        i += 1;
        let start = i;
        while i < b.len() && b[i].is_ascii_digit() {
            i += 1;
        }
        if i == start {
            return false;
        }
    }
    let Some(&tz_byte) = b.get(i) else {
        return false;
    };
    match tz_byte {
        b'Z' | b'z' => i == b.len() - 1,
        b'+' | b'-' => {
            if b.len() != i + 6 {
                return false;
            }
            b[i + 1].is_ascii_digit()
                && b[i + 2].is_ascii_digit()
                && b[i + 3] == b':'
                && b[i + 4].is_ascii_digit()
                && b[i + 5].is_ascii_digit()
        }
        _ => false,
    }
}

/// Return `true` only when `s` parses as a URL with the `https` scheme.
///
/// Uses the `url` crate so the scheme check is RFC 3986-correct (case
/// normalized, no leading whitespace tolerated, no scheme spoofing via
/// raw `https://` substring matches inside another URL component).
/// Mirrors the publish-side check in
/// `tools/publish_app_notification/validate.py::_validate_display`.
fn is_https_cta_url(s: &str) -> bool {
    url::Url::parse(s)
        .ok()
        .map(|u| u.scheme() == "https")
        .unwrap_or(false)
}

fn parse_notification_tag(tag: &str) -> Option<Version> {
    let remainder = tag.strip_prefix(TAG_PREFIX)?;
    Version::parse(remainder).ok()
}

/// Eagerly validate the caller-supplied installed-version string so the
/// orchestrator can short-circuit with the typed
/// `NotificationInstalledVersionParse` variant BEFORE any network or
/// cache I/O. The leading `v`/`V` is tolerated to match [`classify`].
///
/// Returning `Ok(())` on success (rather than the parsed [`Version`])
/// keeps `classify` as the single source of truth for prefix stripping
/// and the parse; this helper only exists so bindings can observe the
/// error variant the spec and `error-contract.md` promise.
fn validate_installed_version(installed_version: &str) -> Result<()> {
    let stripped = installed_version
        .strip_prefix('v')
        .or_else(|| installed_version.strip_prefix('V'))
        .unwrap_or(installed_version);
    match Version::parse(stripped) {
        Ok(_) => Ok(()),
        Err(source) => Err(UpdateError::NotificationInstalledVersionParse {
            input: installed_version.to_string(),
            source,
        }),
    }
}

fn status_from(
    classification: Classification,
    manifest: &AppNotificationManifest,
    parse_error: Option<String>,
) -> NotificationStatus {
    NotificationStatus {
        classification,
        latest_version: manifest.latest_version.clone(),
        published_at: manifest.published_at.clone(),
        min_supported_version: manifest.min_supported_version.clone(),
        display: manifest.display.clone(),
        parse_error,
    }
}

#[cfg(test)]
#[path = "notification_tests.rs"]
mod tests;
