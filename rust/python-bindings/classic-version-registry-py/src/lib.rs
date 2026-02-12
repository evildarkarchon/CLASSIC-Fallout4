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
//! # Get singleton registry
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

use pyo3::prelude::*;

mod matching;
mod models;
mod registry;
mod version;

/// Python module for CLASSIC version registry.
///
/// Provides game version detection, matching, and registry lookup
/// powered by Rust for performance and reliability.
///
/// Core Classes:
///     VersionRegistry: Singleton registry for game version metadata
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
#[pymodule]
fn classic_version_registry(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("__debug_registered__", true)?;

    // Register all components
    version::register(m)?;
    models::register(m)?;
    matching::register(m)?;
    registry::register(m)?;

    Ok(())
}
