//! CLASSIC Version Registry Python Bindings
//!
//! This crate provides PyO3 bindings for classic-version-registry-core.
//! It wraps the pure Rust version registry for Python consumption.
//!
//! ## Architecture
//!
//! This is a THIN ADAPTER layer that:
//! - Delegates all business logic to classic-version-registry-core
//! - Only handles Python <-> Rust type conversions
//! - Maintains API compatibility with existing Python code
//!
//! ## Complete Usage Example
//!
//! ```python
//! import classic_version_registry
//!
//! # Get a handle to this module's registry snapshot
//! registry = classic_version_registry.VersionRegistry()
//!
//! # Lookup by ID
//! og = registry.get_by_id("FO4_OG")
//! print(f"OG version: {og.version}")
//! print(f"Address lib: {og.address_library.filename}")
//!
//! # Match unknown version
//! result = registry.match_version("1.10.500.0", "Fallout4", False)
//! if result.should_warn:
//!     print(f"Warning: {result.message}")
//!
//! # Convenience function
//! result = classic_version_registry.match_version_string("1.10.163.0", "Fallout4", False)
//! print(f"Matched: {result.version_info.display_name}")
//! ```

use std::sync::LazyLock;

use classic_version_registry_core::{VersionRegistry, VersionRegistryScope};
use pyo3::prelude::*;

mod fallout4_version;
mod matching;
mod models;
mod registry;
mod version;

/// This facade's own Version Registry scope.
///
/// Every registry read in this facade goes through this scope's lazy
/// first-use snapshot rather than the process default, so now that the Python
/// facades share one native extension (#259) each keeps the snapshot taken
/// from the working directory at its own first use.
static FACADE_SCOPE: LazyLock<VersionRegistryScope> =
    LazyLock::new(VersionRegistryScope::new_isolated);

/// Return this facade's registry snapshot, taking it on first use.
pub(crate) fn facade_registry() -> &'static VersionRegistry {
    FACADE_SCOPE.registry()
}

/// Python module for CLASSIC version registry.
///
/// Provides game version detection, matching, and registry lookup
/// powered by Rust for performance and reliability.
///
/// Core Classes:
///     VersionRegistry: this module's registry snapshot for game version metadata
///     GameVersion: 4-component game version (major.minor.patch.build)
///     VersionInfo: Complete version information for a game version
///     MatchResult: Result of version matching with confidence level
///     MatchConfidence: Confidence level enum for version matching
///
/// Example:
///     >>> import classic_version_registry
///     >>> registry = classic_version_registry.VersionRegistry()
///     >>> og = registry.get_by_id("FO4_OG")
///     >>> print(og.version)
pub(crate) fn register_facade(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("__debug_registered__", true)?;

    // Register all components
    fallout4_version::register(m)?;
    version::register(m)?;
    models::register(m)?;
    matching::register(m)?;
    registry::register(m)?;

    Ok(())
}

#[cfg(test)]
#[path = "mod_tests.rs"]
mod tests;
