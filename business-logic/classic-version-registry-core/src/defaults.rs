//! YAML-backed fallback helpers for Fallout 4 version metadata.
//!
//! These helpers preserve the legacy internal function names while sourcing
//! their data from the embedded `CLASSIC Main.yaml` instead of duplicated Rust
//! version tables.

use std::collections::HashMap;

use crate::models::{UnknownVersionHandling, VersionInfo};
use crate::registry::VersionRegistry;

/// Get the fallback Fallout 4 versions from the embedded `CLASSIC Main.yaml`.
///
/// # Panics
///
/// Panics if the embedded YAML fallback cannot be parsed. This indicates that
/// the checked-in `CLASSIC Main.yaml` no longer matches the registry parser.
#[must_use]
#[expect(
    dead_code,
    reason = "retained as a YAML-backed compatibility shim for source-surface scanners"
)]
pub fn get_default_versions() -> HashMap<String, VersionInfo> {
    let (versions, _, _) = VersionRegistry::load_embedded_defaults()
        .expect("embedded CLASSIC Main.yaml fallback must be valid")
        .into_parts();
    versions
}

/// Get fallback unknown-version handling from the embedded `CLASSIC Main.yaml`.
///
/// # Panics
///
/// Panics if the embedded YAML fallback cannot be parsed. This indicates that
/// the checked-in `CLASSIC Main.yaml` no longer matches the registry parser.
#[must_use]
#[expect(
    dead_code,
    reason = "retained as a YAML-backed compatibility shim for source-surface scanners"
)]
pub fn get_default_unknown_handling() -> UnknownVersionHandling {
    let (_, _, unknown_handling) = VersionRegistry::load_embedded_defaults()
        .expect("embedded CLASSIC Main.yaml fallback must be valid")
        .into_parts();
    unknown_handling
}
