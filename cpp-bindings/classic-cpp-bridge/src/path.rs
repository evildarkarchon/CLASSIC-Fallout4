//! Path helper bridge for CXX FFI.
//!
//! Bridges the two path helpers the GUI's game-path dialogs call: the
//! registry-backed Fallout 4 executable name for a selected game version, and
//! the custom-scan restricted-folder check (owned by
//! `classic_scanlog_core::custom_scan`). The bridge is consumer-driven, so the
//! rest of `classic-path-core` (detection, validation, INI checks, backups)
//! stays Rust-only until a frontend calls it.
//!
//! # Architecture
//!
//! This module provides the `classic::path` C++ namespace.  All bridge
//! functions accept plain `&str` arguments (never `&Path`) because CXX
//! cannot share `std::path::Path` across the FFI boundary.

// The custom-scan folder policy is owned by scanlog core (#254 follow-up);
// the bridge names and the `classic::path` namespace are unchanged.
use classic_scanlog_core::is_restricted_path as core_is_restricted_path;
use std::path::Path;

// ─────────────────────────────────────────────────────────────────────────────
// Fallout4-specific helpers
// ─────────────────────────────────────────────────────────────────────────────

fn resolve_fallout4_version_info(
    selected_game_version: &str,
) -> Option<classic_version_registry_core::VersionInfo> {
    classic_config_core::resolve_registry_version_info("Fallout4", selected_game_version)
}

fn resolve_fallout4_exe_name(selected_game_version: &str) -> String {
    resolve_fallout4_version_info(selected_game_version)
        .map(|info| format!("{}.exe", info.docs_name))
        .unwrap_or_else(|| "Fallout4.exe".to_string())
}

// ─────────────────────────────────────────────────────────────────────────────
// Predicate helpers — fail-soft bool
// ─────────────────────────────────────────────────────────────────────────────

/// Returns `true` if `path` is a restricted Windows system directory.
fn check_restricted_path(path: &str) -> bool {
    core_is_restricted_path(Path::new(path))
}

// ─────────────────────────────────────────────────────────────────────────────
// CXX bridge declaration — namespace = "classic::path"
// ─────────────────────────────────────────────────────────────────────────────

#[cxx::bridge(namespace = "classic::path")]
mod ffi {
    extern "Rust" {
        /// Resolve the expected Fallout 4 executable name for a selected version.
        fn resolve_fallout4_exe_name(selected_game_version: &str) -> String;

        /// Returns `true` if `path` is a restricted Windows system directory.
        fn check_restricted_path(path: &str) -> bool;
    }
}

#[cfg(test)]
#[path = "path_tests.rs"]
mod tests;
