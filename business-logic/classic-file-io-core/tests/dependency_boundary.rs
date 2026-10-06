//! Structural guard for file I/O core's inward dependency boundary.
//!
//! Crash Log collection and Targeted input resolution moved to
//! `classic-scanlog-core` (#254). Their XSE Folder resolution and
//! operation-context cancellation were file I/O's only reasons to depend on
//! `classic-xse-core` and `classic-operation-context`; scanlog depends on file
//! I/O, so either edge returning would reverse ownership. A successful call
//! cannot observe a missing Cargo edge, so this reads the manifest directly.

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
fn file_io_core_has_no_xse_or_operation_context_dependency() {
    let manifest_path = Path::new(env!("CARGO_MANIFEST_DIR")).join("Cargo.toml");
    let manifest = std::fs::read_to_string(&manifest_path).expect("read file I/O manifest");
    let names = normal_dependency_names(&manifest);

    // Sanity check that the parser saw the real table, so an empty parse
    // cannot make the absence assertions pass vacuously.
    assert!(
        names.iter().any(|name| name == "classic-shared-core"),
        "expected classic-shared-core in {names:?}"
    );
    for forbidden in ["classic-xse-core", "classic-operation-context"] {
        assert!(
            !names.iter().any(|name| name == forbidden),
            "classic-file-io-core must not depend on {forbidden}; Crash Log collection is owned by classic-scanlog-core"
        );
    }
}

/// YAML Data install, rollback, and self-heal moved to `classic-config-core`
/// (#248). That path was file I/O's only reason to depend on
/// `classic-durable-publication`; config consumes Durable Publication
/// directly, so the edge must not come back with a stray helper.
#[test]
fn file_io_core_has_no_durable_publication_dependency() {
    let manifest_path = Path::new(env!("CARGO_MANIFEST_DIR")).join("Cargo.toml");
    let manifest = std::fs::read_to_string(&manifest_path).expect("read file I/O manifest");
    let names = normal_dependency_names(&manifest);

    // Same vacuity guard as above: prove the table was actually parsed.
    assert!(
        names.iter().any(|name| name == "classic-shared-core"),
        "expected classic-shared-core in {names:?}"
    );
    assert!(
        !names
            .iter()
            .any(|name| name == "classic-durable-publication"),
        "classic-file-io-core must not depend on classic-durable-publication; YAML Data install/rollback/self-heal is owned by classic-config-core"
    );
}
