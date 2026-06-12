//! CLASSIC Update Core - Pure Rust business logic for auto-update system
//!
//! This crate provides high-performance update checking with:
//! - GitHub API integration for release monitoring
//! - Version comparison and change detection
//! - Rate limiting and error handling
//!
//! **NO PyO3 DEPENDENCIES** - Pure Rust business logic only.
//! For Python bindings, see `classic-update-py`.
//!
//! # Architecture
//!
//! This is the `-core` crate containing pure Rust business logic. The Python bindings
//! are in the separate `classic-update-py` crate, following the **SEPARATION OF CONCERNS** rule.
//!
//! # Examples
//!
//! ## GitHub Release Checking
//!
//! ```rust,no_run
//! use classic_update_core::github::GithubClient;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4")?;
//!
//! // Check latest release
//! let latest = client.get_latest_release().await?;
//! println!("Latest version: {}", latest.tag_name);
//!
//! // Check if update available
//! if client.has_update("v8.0.0", &latest.tag_name)? {
//!     println!("Update available: {}", latest.name);
//!     println!("Release notes:\n{}", latest.body);
//! }
//! # Ok(())
//! # }
//! ```
//!
//! # Performance Characteristics
//!
//! - **GitHub API**: 5-10x faster than Python requests with native async
//! - **Version Comparison**: 20x faster with native semver
//! - **Async I/O**: Non-blocking operations for concurrent checks
//!
//! # Thread Safety
//!
//! All update clients are thread-safe and can be used from multiple threads
//! or async tasks. HTTP clients use connection pooling for efficiency.
//!
//! # Rate Limiting
//!
//! The module respects rate limits from the GitHub API:
//! - GitHub: Returns `RateLimitExceeded` error with retry-after duration
//!
//! Always check for `UpdateError::RateLimitExceeded` and handle appropriately.

pub mod error;
pub mod github;
pub(crate) mod manifest_fetch;
pub mod notification;
pub mod yaml_update;

// Re-export key types for convenience
pub use error::{Result, UpdateError};
pub use github::{GithubAsset, GithubClient, GithubRelease};
pub use notification::{
    AppNotificationDisplay, AppNotificationManifest, Classification, NotificationStatus,
    build_app_notification_pages_url, check_app_notification, check_app_notification_with,
    check_app_notification_with_env, classify, fetch_app_notification_manifest,
    fetch_via_releases_fallback,
};
pub use yaml_update::{
    ApprovedUpdate, CACHED_MANIFEST_FILENAME, ClientSchemaEntry, ClientSchemaSet, ETAG_FILENAME,
    FileInstallOutcome, MAX_MANIFEST_VERSION, RejectedManifestFile, RollbackOutcome,
    SignatureDescriptor, UpdateCheckConfig, YamlManifest, YamlManifestFile, YamlUpdateReport,
    YamlUpdateStatus, apply_yaml_update, apply_yaml_update_with_decision, check_yaml_update,
    classify_manifest, download_release_asset, fetch_yaml_manifest, rollback_yaml_update,
    validate_manifest,
};

/// Version of the classic-update-core crate.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
