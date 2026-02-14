//! Path detection bridge for CXX FFI.
//!
//! Bridges `classic-path-core` helpers so the Qt GUI can reuse the same
//! automatic game/docs detection logic as other implementations.

use classic_path_core::{DocsPathFinder, GamePathFinder};
use std::path::Path;

fn detect_fallout4_game_path(cached_path: &str, is_vr: bool) -> String {
    let game_exe = if is_vr {
        "Fallout4VR.exe"
    } else {
        "Fallout4.exe"
    };
    let finder = GamePathFinder::new(game_exe, None::<&str>, "Fallout4", is_vr);

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

fn detect_fallout4_docs_path(cached_path: &str, is_vr: bool) -> String {
    let relative = if is_vr {
        r"My Games\Fallout4VR"
    } else {
        r"My Games\Fallout4"
    };
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
        fn detect_fallout4_game_path(cached_path: &str, is_vr: bool) -> String;

        /// Detect Fallout 4 docs path (e.g. My Games/Fallout4).
        ///
        /// Returns empty string if detection fails.
        fn detect_fallout4_docs_path(cached_path: &str, is_vr: bool) -> String;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_fallout4_game_path_empty_input() {
        let result = detect_fallout4_game_path("", false);
        // May be empty on systems without game installation.
        assert!(!result.contains('\0'));
    }

    #[test]
    fn test_detect_fallout4_docs_path_empty_input() {
        let result = detect_fallout4_docs_path("", false);
        // May be empty on non-Windows test hosts or missing docs dir.
        assert!(!result.contains('\0'));
    }
}
