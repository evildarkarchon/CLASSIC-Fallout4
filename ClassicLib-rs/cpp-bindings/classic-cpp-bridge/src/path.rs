//! Path detection bridge for CXX FFI.
//!
//! Bridges `classic-path-core` helpers so the Qt GUI can reuse the same
//! automatic game/docs detection logic as other implementations.

use classic_path_core::{DocsPathFinder, GamePathFinder};
use std::path::Path;

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

fn detect_fallout4_game_path(cached_path: &str, selected_game_version: &str) -> String {
    let version_info = resolve_fallout4_version_info(selected_game_version);
    let game_exe = version_info
        .as_ref()
        .map(|info| format!("{}.exe", info.docs_name))
        .unwrap_or_else(|| "Fallout4.exe".to_string());
    let finder = GamePathFinder::new(
        &game_exe,
        None::<&str>,
        "Fallout4",
        version_info.as_ref().is_some_and(|info| info.is_vr),
    );

    let cached = if cached_path.is_empty() {
        None
    } else {
        Some(Path::new(cached_path))
    };

    finder
        .find_game_path(cached, None)
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_default()
}

fn detect_fallout4_docs_path(cached_path: &str, selected_game_version: &str) -> String {
    let relative = resolve_fallout4_version_info(selected_game_version)
        .map(|info| format!(r"My Games\{}", info.docs_name))
        .unwrap_or_else(|| r"My Games\Fallout4".to_string());
    let finder = DocsPathFinder::new(relative);

    let cached = if cached_path.is_empty() {
        None
    } else {
        Some(cached_path)
    };

    finder
        .find_docs_path(cached)
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_default()
}

#[cxx::bridge(namespace = "classic::path")]
mod ffi {
    extern "Rust" {
        /// Detect Fallout 4 game root path.
        ///
        /// Returns empty string if detection fails.
        fn detect_fallout4_game_path(cached_path: &str, selected_game_version: &str) -> String;

        /// Resolve the expected Fallout 4 executable name for a selected version.
        fn resolve_fallout4_exe_name(selected_game_version: &str) -> String;

        /// Detect Fallout 4 docs path (e.g. My Games/Fallout4).
        ///
        /// Returns empty string if detection fails.
        fn detect_fallout4_docs_path(cached_path: &str, selected_game_version: &str) -> String;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_fallout4_game_path_empty_input() {
        let result = detect_fallout4_game_path("", "Original");
        // May be empty on systems without game installation.
        assert!(!result.contains('\0'));
    }

    #[test]
    fn test_resolve_fallout4_exe_name_uses_registry_metadata() {
        assert_eq!(resolve_fallout4_exe_name("Original"), "Fallout4.exe");
        assert_eq!(resolve_fallout4_exe_name("VR"), "Fallout4VR.exe");
    }

    #[test]
    fn test_detect_fallout4_docs_path_empty_input() {
        let result = detect_fallout4_docs_path("", "Original");
        // May be empty on non-Windows test hosts or missing docs dir.
        assert!(!result.contains('\0'));
    }
}
