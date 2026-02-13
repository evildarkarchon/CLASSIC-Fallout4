//! Game file scanning bridge for CXX FFI.
//!
//! Bridges `classic_scangame_core` for setup checks and path detection.

use classic_scangame_core::integrity::IntegrityConfig;
use classic_scangame_core::setup::{
    SetupCheckConfig, needs_path_detection as core_needs_path_detection, run_combined_checks,
};
use std::path::PathBuf;

fn run_setup_checks(
    game_exe_path: &str,
    _game_root: &str,
    game_name: &str,
) -> ffi::SetupCheckResult {
    let integrity = IntegrityConfig::new(
        PathBuf::from(game_exe_path),
        Vec::new(),
        game_name.to_string(),
    );
    let config = SetupCheckConfig {
        integrity,
        game_name: game_name.to_string(),
        docs_path: None,
        xse_hashes: Vec::new(),
    };
    let results = run_combined_checks(&config);
    ffi::SetupCheckResult {
        combined_output: results.combined(),
        has_errors: results.has_errors(),
        total_checks: results.total_checks() as u32,
    }
}

fn needs_path_detection(game_path: &str, docs_path: &str) -> ffi::PathDetectionNeeds {
    let gp = if game_path.is_empty() {
        None
    } else {
        Some(game_path)
    };
    let dp = if docs_path.is_empty() {
        None
    } else {
        Some(docs_path)
    };
    let (need_game, need_docs) = core_needs_path_detection(gp, dp);
    ffi::PathDetectionNeeds {
        needs_game_path: need_game,
        needs_docs_path: need_docs,
    }
}

#[cxx::bridge(namespace = "classic::scangame")]
mod ffi {
    struct SetupCheckResult {
        combined_output: String,
        has_errors: bool,
        total_checks: u32,
    }

    struct PathDetectionNeeds {
        needs_game_path: bool,
        needs_docs_path: bool,
    }

    extern "Rust" {
        fn run_setup_checks(
            game_exe_path: &str,
            game_root: &str,
            game_name: &str,
        ) -> SetupCheckResult;

        fn needs_path_detection(game_path: &str, docs_path: &str) -> PathDetectionNeeds;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_run_setup_checks_nonexistent() {
        let result = run_setup_checks("nonexistent_exe.exe", "nonexistent_root", "Fallout4");
        // Should complete without panic
        let _ = result.combined_output;
    }

    #[test]
    fn test_needs_path_detection_empty() {
        let result = needs_path_detection("", "");
        assert!(result.needs_game_path);
        assert!(result.needs_docs_path);
    }

    #[test]
    fn test_needs_path_detection_with_paths() {
        let result = needs_path_detection("C:\\Games\\Fallout4", "C:\\Users\\Docs");
        assert!(!result.needs_game_path);
        assert!(!result.needs_docs_path);
    }
}
