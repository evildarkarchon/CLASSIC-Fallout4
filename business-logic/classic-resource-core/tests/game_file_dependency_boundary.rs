//! Structural guard for the game-file policy's dependency boundary (#250).
//!
//! The game-target backup and game-file operations moved from
//! `classic-file-io-core` into resource core. They never relied on Durable
//! Publication, so the move must not drag that edge into resource core, and
//! resource core must reach file I/O directly (it reuses `FileIOError`) rather
//! than the other way round. A successful call cannot observe a missing Cargo
//! edge, so this reads the manifests directly.

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

/// Reads a sibling business-logic crate's manifest by directory name.
fn read_manifest(crate_dir: &str) -> String {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join(crate_dir)
        .join("Cargo.toml");
    std::fs::read_to_string(&path).unwrap_or_else(|err| panic!("read {}: {err}", path.display()))
}

#[test]
fn resource_core_owns_game_file_policy_without_durable_publication() {
    let names = normal_dependency_names(&read_manifest("classic-resource-core"));

    // Sanity check that the parser saw the real table, so an empty parse
    // cannot make the absence assertion pass vacuously.
    assert!(
        names.iter().any(|name| name == "classic-file-io-core"),
        "resource core must depend inward on classic-file-io-core; got {names:?}"
    );
    assert!(
        !names
            .iter()
            .any(|name| name == "classic-durable-publication"),
        "the game-file policy does not use Durable Publication; resource core must not depend on it"
    );
}

#[test]
fn file_io_core_does_not_depend_on_resource_core() {
    let names = normal_dependency_names(&read_manifest("classic-file-io-core"));

    assert!(
        names.iter().any(|name| name == "classic-shared-core"),
        "expected classic-shared-core in {names:?}"
    );
    assert!(
        !names.iter().any(|name| name == "classic-resource-core"),
        "classic-file-io-core must not depend on classic-resource-core; the game-file policy is owned by resource"
    );
}
