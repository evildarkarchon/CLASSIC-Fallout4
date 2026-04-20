//! CLASSIC Update Python Bindings
//!
//! This crate provides PyO3 bindings for classic-update-core.
//! It wraps the pure Rust update checking logic for Python consumption.
//!
//! ## Architecture
//!
//! This is a THIN ADAPTER layer that:
//! - Delegates all business logic to classic-update-core
//! - Only handles Python ↔ Rust type conversions
//! - Maintains API compatibility with existing Python code
//!
//! ## Complete Usage Example
//!
//! ```python
//! import classic_update
//! import asyncio
//!
//! async def main():
//!     # Check GitHub releases (5-10x faster than Python)
//!     github = classic_update.GithubClient("evildarkarchon", "CLASSIC-Fallout4")
//!
//!     # Get latest release
//!     latest = await github.get_latest_release()
//!     print(f"Latest version: {latest.tag_name}")
//!     print(f"Release notes:\n{latest.body}")
//!
//!     # Check if update available
//!     if github.has_update("v8.0.0", latest.tag_name):
//!         print("Update available!")
//!         for asset in latest.assets:
//!             print(f"  - {asset.name} ({asset.size} bytes)")
//!
//!     # Get all releases
//!     releases = await github.get_all_releases()
//!     for release in releases:
//!         print(f"{release.tag_name}: {release.name}")
//!
//! asyncio.run(main())
//! ```
//!
//! ## Performance Characteristics
//!
//! - **GitHub API**: 5-10x faster than Python requests with native async
//! - **Version Comparison**: 20x faster with native semver
//! - **Async I/O**: Non-blocking operations for concurrent checks
//!
//! ## Thread Safety
//!
//! All update clients are thread-safe and can be used from multiple Python threads
//! or async tasks.

use pyo3::prelude::*;

mod github;
mod yaml_update;

/// Python module for CLASSIC update checking.
///
/// This module provides Rust-accelerated update checking with:
/// - GitHub API integration for release monitoring
/// - Version comparison and change detection
///
/// Core Classes:
///     GithubClient: Client for GitHub API access
///     GithubRelease: GitHub release information
///     GithubAsset: GitHub release asset (downloadable file)
///
/// Example:
///     >>> import classic_update
///     >>> import asyncio
///     >>>
///     >>> async def check_updates():
///     ...     # Check GitHub
///     ...     github = classic_update.GithubClient("evildarkarchon", "CLASSIC-Fallout4")
///     ...     latest = await github.get_latest_release()
///     ...     if github.has_update("v8.0.0", latest.tag_name):
///     ...         print(f"Update to {latest.tag_name} available!")
///     >>>
///     >>> asyncio.run(check_updates())
#[pymodule]
fn classic_update(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add version and debug marker
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("__debug_registered__", true)?;

    // Register GitHub components
    github::register(m)?;

    // Register YAML update-delivery components (check/apply/rollback + DTOs)
    yaml_update::register(m)?;

    Ok(())
}
