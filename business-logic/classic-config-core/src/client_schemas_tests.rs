//! Drift guard: every bundled shippable YAML `schema_version` header must be
//! accepted by the client's own [`SchemaCompat`] constant.
//!
//! If a contributor bumps a shipped file's header without raising the client
//! constant (or the reverse), the client silently refuses its own bundled file
//! at load time. These tests catch that on every `cargo test --workspace`.
//! They read `CLASSIC Data/databases/client-schema-ranges.yaml` for the
//! `client_schemas_const` bindings and compare against the real constants and
//! the real [`schema_compat_check`], with no source-text parsing.

use super::*;
use classic_shared_core::yaml::{
    Compatibility, SchemaCompat, extract_schema_version, schema_compat_check,
};
use std::path::{Path, PathBuf};
use yaml_rust2::{Yaml, YamlLoader};

/// Repo-root `CLASSIC Data/databases` directory, which holds the bundled
/// shippable YAML files and `client-schema-ranges.yaml`.
fn bundled_databases_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("CLASSIC Data")
        .join("databases")
}

/// Resolves a `client_schemas_const` name from `client-schema-ranges.yaml` to
/// the constant it names in [`crate::client_schemas`].
///
/// Rust has no reflection over constants, so this table is the one place a new
/// constant must be registered. An unregistered name is reported as drift
/// rather than skipped.
fn client_schemas_const(name: &str) -> Option<SchemaCompat> {
    match name {
        "MAIN_YAML" => Some(MAIN_YAML),
        "GAME_FALLOUT4_YAML" => Some(GAME_FALLOUT4_YAML),
        _ => None,
    }
}

/// Parses one YAML file and returns its first document, or a finding.
fn load_single_document(path: &Path) -> Result<Yaml, String> {
    let text = std::fs::read_to_string(path)
        .map_err(|error| format!("{}: cannot read: {error}", path.display()))?;
    let mut documents = YamlLoader::load_from_str(&text)
        .map_err(|error| format!("{}: invalid YAML: {error}", path.display()))?;
    if documents.is_empty() {
        return Err(format!("{}: empty YAML document", path.display()));
    }
    Ok(documents.swap_remove(0))
}

/// Collects every schema drift finding for the databases directory `dir`.
///
/// Checks, for every shippable file the client knows
/// ([`shippable_schema_entries`]):
/// - `client-schema-ranges.yaml` lists it with a `client_schemas_const` that
///   names a registered constant equal to the client's accepted range;
/// - the bundled file's root `schema_version` header is accepted by that
///   range under the real [`schema_compat_check`].
///
/// Returns an empty vector when there is no drift. All findings are
/// collected rather than stopping at the first.
fn schema_drift_findings(dir: &Path) -> Vec<String> {
    let mut findings = Vec::new();
    let ranges_path = dir.join("client-schema-ranges.yaml");
    let ranges = match load_single_document(&ranges_path) {
        Ok(ranges) => ranges,
        Err(finding) => return vec![finding],
    };
    let Some(range_entries) = ranges["files"].as_vec() else {
        return vec![format!(
            "{}: missing top-level `files` list",
            ranges_path.display()
        )];
    };

    for entry in shippable_schema_entries() {
        let file_name = entry.file_name.as_str();
        let Some(range_entry) = range_entries
            .iter()
            .find(|candidate| candidate["name"].as_str() == Some(file_name))
        else {
            findings.push(format!(
                "{file_name}: shippable file is not listed in client-schema-ranges.yaml"
            ));
            continue;
        };
        let Some(const_name) = range_entry["client_schemas_const"].as_str() else {
            findings.push(format!(
                "{file_name}: client-schema-ranges.yaml entry has no string `client_schemas_const`"
            ));
            continue;
        };
        match client_schemas_const(const_name) {
            None => findings.push(format!(
                "{file_name}: client_schemas_const {const_name:?} is not a constant in client_schemas.rs"
            )),
            Some(named) if named != entry.accepted => findings.push(format!(
                "{file_name}: client_schemas_const {const_name:?} is {named:?}, but the client accepts this file with {:?}",
                entry.accepted
            )),
            Some(_) => {}
        }

        let file_path = dir.join(file_name);
        let document = match load_single_document(&file_path) {
            Ok(document) => document,
            Err(finding) => {
                findings.push(finding);
                continue;
            }
        };
        let version = match extract_schema_version(&document) {
            Ok(version) => version,
            Err(error) => {
                findings.push(format!("{file_name}: {}", error.with_file(file_name)));
                continue;
            }
        };
        match schema_compat_check(&version, &entry.accepted) {
            Compatibility::Compatible => {}
            refused => findings.push(format!(
                "{file_name}: bundled schema_version {}.{} is refused by the client ({refused:?}); \
                 bump the client constant or revert the file header",
                version.major, version.minor
            )),
        }
    }
    findings
}

#[test]
fn bundled_yaml_schema_versions_are_accepted_by_client_schema_constants() {
    let findings = schema_drift_findings(&bundled_databases_dir());
    assert!(
        findings.is_empty(),
        "bundled YAML schema drift:\n{}",
        findings.join("\n")
    );
}

/// Copies the real databases directory into a temp dir with one file's text
/// rewritten, so the drift check can be proven to fail on a seeded break.
fn seeded_databases_dir(file_name: &str, edit: impl Fn(&str) -> String) -> tempfile::TempDir {
    let temp = tempfile::tempdir().expect("temp dir");
    let source = bundled_databases_dir();
    for name in [
        "client-schema-ranges.yaml",
        "CLASSIC Main.yaml",
        "CLASSIC Fallout4.yaml",
    ] {
        let text = std::fs::read_to_string(source.join(name)).expect("read bundled file");
        let text = if name == file_name { edit(&text) } else { text };
        std::fs::write(temp.path().join(name), text).expect("write seeded file");
    }
    temp
}

#[test]
fn schema_drift_is_reported_for_a_seeded_major_bump() {
    let current = schema_version_line(&bundled_databases_dir().join("CLASSIC Main.yaml"));
    let seeded = seeded_databases_dir("CLASSIC Main.yaml", |text| {
        text.replacen(&current, "schema_version: \"99.0\"", 1)
    });

    let findings = schema_drift_findings(seeded.path());

    assert_eq!(findings.len(), 1, "findings: {findings:?}");
    assert!(
        findings[0].starts_with("CLASSIC Main.yaml: bundled schema_version 99.0 is refused"),
        "unexpected finding: {}",
        findings[0]
    );
}

#[test]
fn schema_drift_is_reported_for_an_unknown_client_schemas_const() {
    let seeded = seeded_databases_dir("client-schema-ranges.yaml", |text| {
        text.replacen(
            "client_schemas_const: \"GAME_FALLOUT4_YAML\"",
            "client_schemas_const: \"GAME_SKYRIM_YAML\"",
            1,
        )
    });

    let findings = schema_drift_findings(seeded.path());

    assert_eq!(
        findings,
        vec![
            "CLASSIC Fallout4.yaml: client_schemas_const \"GAME_SKYRIM_YAML\" is not a constant in client_schemas.rs"
                .to_string()
        ]
    );
}

/// Returns the root-level `schema_version: "X.Y"` line of a bundled file so a
/// seeded edit replaces exactly that header and not a nested one.
fn schema_version_line(path: &Path) -> String {
    let text = std::fs::read_to_string(path).expect("read bundled file");
    text.lines()
        .find(|line| line.starts_with("schema_version:"))
        .expect("root schema_version line")
        .to_string()
}
