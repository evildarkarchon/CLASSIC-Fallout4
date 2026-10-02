//! Transitional facade over CLASSIC's version helpers and known-version
//! queries.
//!
//! This crate owns no behavior. Until it retires (#258) it re-exports, under
//! their historical paths:
//!
//! - the domain-neutral helpers — loose version parsing, comparison,
//!   extraction, formatting, and PE file-version extraction — owned by
//!   [`classic_shared_core::version`] (#243);
//! - the known-version queries [`is_known_fallout4_version`] and
//!   [`is_known_f4se_version`], owned by the Version Registry
//!   ([`classic_version_registry_core`], #244).
//!
//! New callers should import those owners directly.
//!
//! # Examples
//!
//! ```rust,no_run
//! use classic_shared_core::version::parse_version;
//! use classic_version_registry_core::is_known_fallout4_version;
//!
//! let version = parse_version("1.10.163.0").unwrap();
//! assert!(is_known_fallout4_version(&version));
//! ```

/// Transitional facade over [`classic_shared_core::version::pe_version`].
///
/// Kept so `classic_version_core::pe_version::*` keeps resolving until this
/// crate retires (#258). New callers import the shared-core owner.
pub use classic_shared_core::version::pe_version;

// Transitional facade: the loose-parsing and PE items are owned by
// `classic_shared_core::version`. These root re-exports end with #258.
pub use classic_shared_core::version::{
    PeVersionError, PeVersionResult, VersionError, VersionResult, compare_versions,
    extract_all_versions, extract_pe_version, extract_version_from_filename,
    extract_version_from_log, format_version, is_valid_executable_path, parse_version,
    try_parse_version,
};

// Re-export VersionRegistry for version information
pub use classic_version_registry_core::{
    VersionInfo, VersionRegistry, VersionRegistryError, get_version_registry,
};

// Re-export NULL_VERSION for convenience
pub use classic_version_registry_core::NULL_VERSION;

// Transitional facade: the known-version queries are Version Registry policy
// (#244). These root re-exports end with #258.
pub use classic_version_registry_core::{is_known_f4se_version, is_known_fallout4_version};

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
