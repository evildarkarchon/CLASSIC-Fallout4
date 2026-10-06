//! Structural guard for the Crash Log Scan Launch dependency boundary (ADR-0009).
//!
//! Launch sits above both owners it composes: scanlog core, which owns the Crash Log Scan
//! Run request, and User Settings, which owns the saved values. The Crash Log Scan Setup
//! Context definition keeps User Settings loading out of scanlog core, so scanlog core must
//! never gain a normal dependency on User Settings (its dev-dependency for tests is fine).
//! A successful build cannot observe a missing or extra Cargo edge, so this reads the
//! manifests directly.

use std::path::Path;

/// Returns the package names declared in a manifest's normal `[dependencies]` table
/// (target-specific, dev and build tables are excluded).
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

/// Reads one business-logic crate's manifest and returns its normal dependency names.
fn business_logic_dependencies(crate_directory: &str) -> Vec<String> {
    let manifest_path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join(crate_directory)
        .join("Cargo.toml");
    let manifest = std::fs::read_to_string(&manifest_path)
        .unwrap_or_else(|error| panic!("read {}: {error}", manifest_path.display()));
    normal_dependency_names(&manifest)
}

#[test]
fn launch_depends_on_scanlog_core_and_user_settings() {
    let names = business_logic_dependencies("classic-scan-launch");

    for required in ["classic-scanlog-core", "classic-user-settings-core"] {
        assert!(
            names.iter().any(|name| name == required),
            "classic-scan-launch must depend on {required}; found {names:?}"
        );
    }
}

#[test]
fn scanlog_core_does_not_depend_on_user_settings() {
    let names = business_logic_dependencies("classic-scanlog-core");

    // Vacuity guard: prove the real table was parsed before asserting an absence.
    assert!(
        names.iter().any(|name| name == "classic-shared-core"),
        "expected classic-shared-core in {names:?}"
    );
    assert!(
        !names
            .iter()
            .any(|name| name == "classic-user-settings-core"),
        "classic-scanlog-core must not depend on classic-user-settings-core; \
         Crash Log Scan Launch owns reading User Settings for a scan"
    );
}
