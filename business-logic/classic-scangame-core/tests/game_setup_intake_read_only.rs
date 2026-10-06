//! Structural guard: Game Setup Intake stays read-only.
//!
//! Intake returns typed Game Setup Checks and optional Game Setup Path Updates;
//! the caller decides whether to persist a proposal through User Settings
//! (`UserSettings::preview_update` and a later conflict-safe commit). The
//! `game-setup-intake` conformance scenarios prove that a run leaves the setup
//! tree byte-identical, but only for the paths those fixtures reach. A write
//! call added to an unexercised branch, or a User Settings update/commit
//! performed on the caller's behalf, would not be observed there, so this reads
//! the intake source directly.

use std::path::Path;

/// Reads `src/game_setup_intake.rs` with `//` comment lines removed, so doc text
/// that explains the contract ("never persists", "preview_update") cannot trip
/// the absence checks below.
fn intake_source_code() -> String {
    let source = std::fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("src")
            .join("game_setup_intake.rs"),
    )
    .expect("read Game Setup Intake source");
    source
        .lines()
        .filter(|line| !line.trim_start().starts_with("//"))
        .collect::<Vec<_>>()
        .join("\n")
}

#[test]
fn intake_source_has_no_filesystem_write_calls() {
    let code = intake_source_code();
    // Sanity check that the real module was read, so an empty or renamed file
    // cannot make the absence assertions pass vacuously.
    assert!(code.contains("pub struct GameSetupIntake"));

    for forbidden in [
        "fs::write",
        "File::create",
        "OpenOptions",
        "create_dir",
        "remove_file",
        "remove_dir",
        "fs::rename",
        "fs::copy",
        "set_permissions",
        "install_atomic",
    ] {
        assert!(
            !code.contains(forbidden),
            "Game Setup Intake must stay read-only; found {forbidden:?} in game_setup_intake.rs"
        );
    }
}

#[test]
fn intake_consumes_only_the_already_opened_game_setup_settings_group() {
    let code = intake_source_code();

    // The only User Settings item intake may name is the typed, already-opened
    // Game Setup group. Opening, previewing, or committing settings is the
    // caller's decision about a returned proposal, not part of intake.
    assert!(
        code.contains("use classic_user_settings_core::GameSetupSettings;"),
        "expected intake to import exactly the GameSetupSettings group"
    );
    for forbidden in [
        "UserSettings::open",
        "UserSettingsUpdate",
        "preview_update",
        "commit",
        "bootstrap",
    ] {
        assert!(
            !code.contains(forbidden),
            "Game Setup Intake must not open, update, or commit User Settings; found {forbidden:?}"
        );
    }
}
