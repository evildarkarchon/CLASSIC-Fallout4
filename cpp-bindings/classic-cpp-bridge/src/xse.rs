//! XSE bridge for CXX FFI (D-01, CXXS-09).
//!
//! Bridges the XSE helpers the GUI calls: the typed loader name for an
//! `XseType`, and XSE log location for a Crash Log Scan's setup. The bridge is
//! consumer-driven, so the rest of `classic-xse-core` (installation and version
//! detection, XSE Folder resolution) stays Rust-only until a frontend calls it.

// The XSE log follows XSE Folder rules, which read config-owned Game Local
// facts, so its Rust owner is the composing scangame entry point rather than
// `classic-xse-core` (#252).
use classic_scangame_core::resolve_xse_log_for_scan as core_resolve_xse_log_for_scan;
use classic_xse_core::XseType as CoreXseType;
use std::path::Path;

// ─────────────────────────────────────────────────────────────────────
// XseType bridge ↔ core mapping
// ─────────────────────────────────────────────────────────────────────

fn from_bridge_xse_type(t: ffi::XseType) -> CoreXseType {
    match t {
        ffi::XseType::F4SE => CoreXseType::F4SE,
        ffi::XseType::F4SEVR => CoreXseType::F4SEVR,
        ffi::XseType::SKSE => CoreXseType::SKSE,
        ffi::XseType::SKSE64 => CoreXseType::SKSE64,
        ffi::XseType::SKSEVR => CoreXseType::SKSEVR,
        ffi::XseType::SFSE => CoreXseType::SFSE,
        _ => CoreXseType::F4SE, // CXX may add sentinel variants; default to F4SE
    }
}

// ─────────────────────────────────────────────────────────────────────
// Typed API (CXXS-09 widening — uses XseType shared enum)
// ─────────────────────────────────────────────────────────────────────

fn xse_get_loader_name(t: ffi::XseType) -> String {
    from_bridge_xse_type(t).loader_name().to_string()
}

/// Locate the XSE log through `classic_scangame_core::resolve_xse_log_for_scan`.
///
/// An empty string means "no log" (no XSE Folder resolved, or the folder or
/// log is missing). An operational failure becomes `Err`, which CXX raises in
/// C++ as `rust::Error` carrying the core's "cannot inspect XSE log ..."
/// message. An empty `configured_docs_root` means "none".
fn resolve_xse_log_for_scan(
    yaml_dir_data: &str,
    game: &str,
    selected_game_version: &str,
    configured_docs_root: &str,
) -> Result<String, String> {
    let configured_docs_root = if configured_docs_root.trim().is_empty() {
        None
    } else {
        Some(Path::new(configured_docs_root))
    };

    core_resolve_xse_log_for_scan(
        Path::new(yaml_dir_data),
        game,
        selected_game_version,
        configured_docs_root,
    )
    .map(|log| {
        log.map(|path| path.to_string_lossy().to_string())
            .unwrap_or_default()
    })
    .map_err(|error| error.to_string())
}

// ─────────────────────────────────────────────────────────────────────
// CXX bridge block — D-04 shared enum + extern "Rust" fns
// ─────────────────────────────────────────────────────────────────────

#[cxx::bridge(namespace = "classic::xse")]
mod ffi {
    #[repr(u8)]
    enum XseType {
        F4SE = 0,
        F4SEVR = 1,
        SKSE = 2,
        SKSE64 = 3,
        SKSEVR = 4,
        SFSE = 5,
    }

    extern "Rust" {
        // Typed API (CXXS-09 widening)
        fn xse_get_loader_name(t: XseType) -> String;
        fn resolve_xse_log_for_scan(
            yaml_dir_data: &str,
            game: &str,
            selected_game_version: &str,
            configured_docs_root: &str,
        ) -> Result<String>;
    }
}

#[cfg(test)]
#[path = "xse_tests.rs"]
mod tests;
