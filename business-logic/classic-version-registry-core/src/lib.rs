//! CLASSIC Version Registry Core - Pure Rust version management
//!
//! This crate provides game version detection and matching for CLASSIC without
//! any PyO3 dependencies. It can be used directly by Rust applications (TUI, CLI)
//! or through Python bindings in a separate `-py` crate.
//!
//! ## Features
//!
//! - **Version Lookup**: Find version info by ID, exact version, or short name
//! - **Version Matching**: Match unknown versions to nearest known version
//! - **YAML Loading**: Load version data from CLASSIC Main.yaml
//! - **Embedded YAML Fallback**: Use the checked-in CLASSIC Main.yaml when runtime loading fails
//!
//! ## Architecture
//!
//! - Pure Rust - no PyO3, usable by TUI/CLI directly
//! - Thread-safe singleton pattern using `OnceLock`
//! - Custom `GameVersion` type for 4-component versions (e.g., 1.10.163.0)
//!
//! # Usage Example
//!
//! ```rust,no_run
//! use classic_version_registry_core::{get_version_registry, GameVersion};
//!
//! // Get singleton registry
//! let registry = get_version_registry();
//!
//! // Lookup by ID
//! if let Some(og) = registry.get_by_id("FO4_OG") {
//!     println!("OG version: {}", og.version);
//! }
//!
//! // Match unknown version
//! let detected = GameVersion::parse("1.10.500.0").unwrap();
//! let result = registry.match_version(&detected, "Fallout4", false);
//! if result.should_warn() {
//!     println!("Warning: {}", result.message);
//! }
//!
//! // Get correct versions for VR mode
//! let correct = registry.get_correct_versions(false);
//! for v in correct {
//!     println!("{}: {}", v.id, v.version);
//! }
//! ```

mod defaults;
mod error;
mod fallout4_version;
mod matching;
mod models;
mod registry;
mod version;

// Re-export public API
pub use error::VersionRegistryError;
pub use fallout4_version::*;
pub use matching::{MatchConfidence, MatchResult, VersionMatcher};
pub use models::{
    AddressLibFormat, AddressLibraryConfig, CompatibleRange, CrashgenConfig, LogLevel,
    UnknownVersionHandling, UnknownVersionStrategy, VersionInfo, XseConfig,
};
pub use registry::{VersionRegistry, get_version_registry};
pub use version::GameVersion;

/// Result type for version registry operations.
pub type Result<T> = std::result::Result<T, VersionRegistryError>;
