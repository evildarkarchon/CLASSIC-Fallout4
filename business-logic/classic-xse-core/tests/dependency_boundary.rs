//! Structural guard: XSE consumes Game Local facts without depending on config.
//!
//! `classic-config-core` owns the Game Local document; XSE receives its facts
//! as plain `XseGameLocalFacts` from a composing caller
//! (`classic_scangame_core::resolve_xse_folder_for_scan`). Config sits beside
//! XSE, and scangame depends on both, so an XSE -> config edge would put the
//! Game Local read back into XSE. A successful call cannot observe a missing
//! Cargo edge, so this reads the manifest directly.

use std::path::Path;

/// Returns the internal package names declared in a manifest's normal
/// `[dependencies]` table (target-specific and dev tables are excluded).
fn normal_dependency_names(manifest: &str) -> Vec<String> {
    let mut in_dependencies = false;
    let mut names = Vec::new();
    for line in manifest.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with('[') {
            in_dependencies = trimmed == "[dependencies]";
            continue;
        }
        if !in_dependencies || trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        if let Some((name, _)) = trimmed.split_once('=') {
            names.push(name.trim().to_string());
        }
    }
    names
}

#[test]
fn xse_core_has_no_config_dependency() {
    let manifest_path = Path::new(env!("CARGO_MANIFEST_DIR")).join("Cargo.toml");
    let manifest = std::fs::read_to_string(&manifest_path).expect("read XSE manifest");
    let names = normal_dependency_names(&manifest);

    // Sanity check that the parser saw the real table, so an empty parse
    // cannot make the absence assertion pass vacuously.
    assert!(
        names.iter().any(|name| name == "classic-shared-core"),
        "expected classic-shared-core in {names:?}"
    );
    assert!(
        !names.iter().any(|name| name == "classic-config-core"),
        "classic-xse-core must not depend on classic-config-core; Game Local facts arrive as XseGameLocalFacts"
    );
}

#[test]
fn xse_core_source_does_not_read_game_local_yaml() {
    // The Local.yaml read moved to config (`read_game_local_facts`); XSE's
    // source must not grow its own YAML read of that document again.
    let source = std::fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("src")
            .join("lib.rs"),
    )
    .expect("read XSE lib.rs");

    // Field docs may still name the `Game_Info.*` keys, so match reads and
    // path construction rather than key names.
    for forbidden in ["YamlOperations", "load_yaml", "Local.yaml\")"] {
        assert!(
            !source.contains(forbidden),
            "classic-xse-core/src/lib.rs must not contain {forbidden:?}"
        );
    }
}
