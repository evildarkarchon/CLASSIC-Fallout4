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

    /// Resource not found (404)
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
}

/// Result type alias for update operations.
pub type Result<T> = std::result::Result<T, UpdateError>;

#[cfg(test)]
#[path = "error_tests.rs"]
mod tests;
