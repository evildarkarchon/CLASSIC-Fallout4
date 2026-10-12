//! Game file scanning bridge for CXX FFI.
//!
//! Bridges `classic_scangame_core` for Game Setup Intake, the only scangame
//! capability the CLI and GUI call. The per-checker sub-domains (BA2, INI, ENB,
//! TOML, Wrye, Integrity, Crashgen) stay Rust-only behind that intake.

use classic_scangame_core::{GameSetupIntake, GameSetupIntakeResult};
use classic_user_settings_core::UserSettings;
use std::path::{Path, PathBuf};

// ─────────────────────────────────────────────────────────────────────────────
// Game Setup Intake entry points
// ─────────────────────────────────────────────────────────────────────────────

/// Opens typed User Settings and runs Game Setup Intake without mutating the snapshot or disk.
///
/// The optional XSE log remains an explicit caller fact because it is not persisted as part of
/// the Game Setup settings group. Blank input means that no detection hint was supplied.
fn run_game_setup_intake_from_user_settings(
    classic_root: &str,
    xse_log_path: &str,
) -> ffi::GameSetupIntakeDto {
    let settings = UserSettings::open(Path::new(classic_root));
    let mut intake = GameSetupIntake::from_user_settings(settings.game_setup_settings());
    if !xse_log_path.trim().is_empty() {
        intake = intake.with_xse_log_path(PathBuf::from(xse_log_path));
    }
    game_setup_result_to_dto(intake.run())
}

/// Converts a core intake result into the CXX DTO without changing proposal order.
///
/// `path_update_count` is derived from the emitted proposal vector. Paths cross the
/// string-only CXX boundary with the bridge's existing lossy non-UTF-8 convention.
fn game_setup_result_to_dto(result: GameSetupIntakeResult) -> ffi::GameSetupIntakeDto {
    let has_errors = result.has_errors();
    let total_checks = result.total_checks() as u32;
    let failed_checks = result.failed_checks() as u32;
    let path_updates = result
        .path_updates
        .iter()
        .map(|update| ffi::GameSetupPathUpdateDto {
            kind: update.kind.clone(),
            path: update.path.to_string_lossy().into_owned(),
        })
        .collect::<Vec<_>>();
    ffi::GameSetupIntakeDto {
        rendered_report: result.rendered_report,
        status: result.status.as_str().to_string(),
        has_errors,
        total_checks,
        failed_checks,
        action_count: result.actions.len() as u32,
        path_update_count: path_updates.len() as u32,
        path_updates,
        game_root: result
            .paths
            .game_root
            .map(|path| path.to_string_lossy().into_owned())
            .unwrap_or_default(),
        docs_root: result
            .paths
            .docs_root
            .map(|path| path.to_string_lossy().into_owned())
            .unwrap_or_default(),
        game_executable: result
            .paths
            .game_exe_path
            .map(|path| path.to_string_lossy().into_owned())
            .unwrap_or_default(),
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// CXX bridge — namespace classic::scangame
// ─────────────────────────────────────────────────────────────────────────────

#[cxx::bridge(namespace = "classic::scangame")]
mod ffi {
    // ── Game Setup Intake DTOs ───────────────────────────────────────────────
    /// One caller-consent-gated path proposal discovered by Game Setup Intake.
    struct GameSetupPathUpdateDto {
        kind: String,
        path: String,
    }

    /// Flattened Game Setup result with ordered consent-gated path proposals.
    ///
    /// `path_update_count` remains as a compatibility summary and always equals
    /// `path_updates.len()`. UTF-8-representable paths are exact; other native path
    /// values follow the bridge's established lossy string conversion.
    struct GameSetupIntakeDto {
        rendered_report: String,
        status: String,
        has_errors: bool,
        total_checks: u32,
        failed_checks: u32,
        action_count: u32,
        path_update_count: u32,
        path_updates: Vec<GameSetupPathUpdateDto>,
        game_root: String,
        docs_root: String,
        game_executable: String,
    }

    extern "Rust" {
        // ── Game Setup Intake ───────────────────────────────────────────────
        /// Open typed User Settings and run setup intake without writing any settings.
        fn run_game_setup_intake_from_user_settings(
            classic_root: &str,
            xse_log_path: &str,
        ) -> GameSetupIntakeDto;
    }
}

#[cfg(test)]
#[path = "scangame_tests.rs"]
mod tests;
