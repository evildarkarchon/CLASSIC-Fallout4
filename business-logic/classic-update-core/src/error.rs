//! Update system error types.

use thiserror::Error;

/// Errors that can occur during update operations.
#[derive(Debug, Error)]
pub enum UpdateError {
    /// Failed to create the HTTP client itself (e.g., invalid TLS config, bad proxy settings).
    /// Uses `#[from]` so `reqwest::Error` converts automatically via `?` at the build site.
    #[error("Failed to create HTTP client: {0}")]
    ClientBuild(#[from] reqwest::Error),

    /// HTTP-layer error during a request or response (e.g., network failure, timeout, bad status).
    /// Mapped explicitly via `.map_err(UpdateError::HttpError)` — NOT auto-converted via `?`,
    /// because `#[from]` is already claimed by `ClientBuild` for the same `reqwest::Error` source type.
    #[error("HTTP error: {0}")]
    HttpError(reqwest::Error),

    /// Failed to parse JSON response
    #[error("JSON parsing error: {0}")]
    JsonError(#[from] serde_json::Error),

    /// Version comparison error
    #[error("Version error: {0}")]
    VersionError(#[from] semver::Error),

    /// URL parsing error
    #[error("URL parsing error: {0}")]
    UrlError(#[from] url::ParseError),

    /// GitHub API error
    #[error("GitHub API error: {0}")]
    GithubError(String),

    /// Rate limit exceeded
    #[error("Rate limit exceeded. Retry after: {0:?}")]
    RateLimitExceeded(Option<std::time::Duration>),

    /// Resource not found (404). For app-notification checks, absence on both
    /// the Pages and Releases channels is folded into `Ok(NotPublished)`
    /// rather than surfaced as a fetch failure.
    #[error("Resource not found: {0}")]
    NotFound(String),

    /// Network timeout
    #[error("Network timeout")]
    Timeout,

    /// Generic update error
    #[error("Update error: {0}")]
    Generic(String),

    /// A fetched manifest is structurally invalid (missing required field,
    /// empty `files` array, malformed sub-field, etc.).
    ///
    /// Produced by `yaml_update::fetch_yaml_manifest` when the manifest
    /// deserializes but fails post-parse validation.
    #[error("manifest invalid: {reason}")]
    ManifestInvalid {
        /// Human-readable diagnostic identifying the offending field or shape.
        reason: String,
    },

    /// The fetched manifest carries a `manifest_version` the client does not
    /// know how to parse. The client declares its `MAX_MANIFEST_VERSION`
    /// constant in `yaml_update`; newer servers emitting a higher version
    /// number must stay backward-compatible or the client refuses the manifest.
    #[error("manifest_version {found} not supported (max supported: {max_supported})")]
    ManifestUnsupportedVersion {
        /// The `manifest_version` the server sent.
        found: u32,
        /// The highest `manifest_version` this client can parse.
        max_supported: u32,
    },

    /// SHA-256 of a downloaded file disagrees with the manifest-declared
    /// value. Produced by `yaml_update::apply_yaml_update` when
    /// `install_atomic` returns `FileIOError::ChecksumMismatch`; surfaced as
    /// an update-layer error so GUI/CLI callers can pattern-match without
    /// reaching into the file-io crate's error taxonomy.
    #[error("SHA-256 mismatch for {file}: expected {expected}, got {actual}")]
    ChecksumMismatch {
        /// Manifest-declared file name (e.g. `CLASSIC Main.yaml`).
        file: String,
        /// Hex-encoded digest the manifest claimed.
        expected: String,
        /// Hex-encoded digest we actually computed from the downloaded bytes.
        actual: String,
    },

    /// The user set `Update Check: false` but still invoked apply. The
    /// caller (bridge, binding, CLI) must surface this as a user-visible
    /// message and not retry silently. No HTTP was issued.
    ///
    /// Produced by `yaml_update::apply_yaml_update_with_decision` when the
    /// passed `UpdateCheckConfig` is disabled. Apply deliberately refuses
    /// to run without an explicit enabled flag — the check-time decision
    /// alone is not enough, because the user may toggle the setting off
    /// between review and apply.
    #[error("update check is disabled; apply refused")]
    UpdateCheckDisabled,

    /// The reviewed decision no longer matches the live manifest. The
    /// user approved release `approved`, but the manifest we just fetched
    /// is tagged `manifest`. Installing anyway would replace files the
    /// user never reviewed. No files were installed.
    ///
    /// Produced by `yaml_update::apply_yaml_update_with_decision` when
    /// `YamlManifest::release_tag` differs from
    /// `ApprovedUpdate::release_tag`. The GUI / CLI should prompt the
    /// user to re-check and re-review.
    #[error(
        "approved release `{approved}` does not match current manifest release `{manifest}`; re-check required"
    )]
    DecisionStale {
        /// Release tag the user approved at review time.
        approved: String,
        /// Release tag the freshly-fetched manifest actually advertises.
        manifest: String,
    },

    /// The reviewed decision still points at the same release tag, but at
    /// least one approved file now advertises different bytes than the user
    /// reviewed.
    #[error(
        "approved file `{file}` for release `{release_tag}` changed digest from `{approved_sha256}` to `{manifest_sha256}`; re-check required"
    )]
    DecisionDigestStale {
        /// Release tag whose approved file digest drifted.
        release_tag: String,
        /// Canonical file name whose digest changed.
        file: String,
        /// Digest the user approved at review time.
        approved_sha256: String,
        /// Digest the freshly-fetched manifest now advertises.
        manifest_sha256: String,
    },

    // -----------------------------------------------------------------
    // Notification-channel error variants (design D-05).
    //
    // These cover the `classic_update_core::notification` module's
    // failure modes. They're kept as sibling variants (rather than
    // nested inside a `Notification(NotificationErrorKind)` wrapper)
    // so bindings that map `UpdateError -> per-language error shape`
    // already documented in `docs/api/error-contract.md` don't need a
    // second enum to destructure.
    // -----------------------------------------------------------------
    /// Both the Pages-first fetch and the Releases-API fallback failed
    /// for an app-notification check. Both cause strings are embedded
    /// so diagnostic logs can explain which channel failed how.
    /// When both channels report absence (`NotFound`), the check returns
    /// `Ok(NotificationStatus { classification: NotPublished, .. })`
    /// instead of this variant.
    ///
    /// Produced by [`crate::notification::check_app_notification`].
    #[error("notification fetch failed — pages: {pages_error}; releases: {releases_error}")]
    NotificationFetchFailed {
        /// Human-readable description of the Pages-leg failure.
        pages_error: String,
        /// Human-readable description of the Releases-fallback failure.
        releases_error: String,
    },

    /// The fetched notification manifest deserialized as JSON but lacks
    /// a required field (e.g. `latest_version`) or carries an invalid
    /// value (e.g. `manifest_version` not matching `^\d+\.\d+$`).
    ///
    /// Distinct from [`UpdateError::JsonError`] so callers can tell
    /// malformed bytes apart from structurally-invalid manifests.
    #[error("notification manifest decode failure: missing or invalid `{field}`")]
    NotificationDecode {
        /// Field name that was missing or invalid.
        field: String,
    },

    /// The caller-supplied installed-version string could not be parsed
    /// as a semantic version.
    ///
    /// Distinct from [`UpdateError::VersionError`] so binding consumers
    /// can surface "your installed version is unparseable" rather than
    /// conflating it with manifest-side version problems.
    #[error("installed version `{input}` is not a valid semver: {source}")]
    NotificationInstalledVersionParse {
        /// The installed-version string the caller provided.
        input: String,
        /// Underlying semver parse error.
        #[source]
        source: semver::Error,
    },

    /// The notification cache file (body or ETag) could not be read,
    /// written, or created.
    ///
    /// Produced when the cache directory is available but a specific
    /// I/O operation fails (missing parent, permission denied,
    /// disk full, etc.). Cache-directory *resolution* failures
    /// (no `LOCALAPPDATA`, no `HOME`) are not reported through this
    /// variant — instead, the notification check degrades to
    /// no-caching per design D-06 ("best-effort, rebuildable").
    #[error("notification cache I/O failure at {path}: {source}")]
    NotificationCacheIo {
        /// Offending cache path (file or directory).
        path: std::path::PathBuf,
        /// Underlying I/O error.
        #[source]
        source: std::io::Error,
    },
}

/// Result type alias for update operations.
pub type Result<T> = std::result::Result<T, UpdateError>;

#[cfg(test)]
#[path = "error_tests.rs"]
mod tests;
