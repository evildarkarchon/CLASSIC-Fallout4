//! Build-time extractor for `CLASSIC_APP_VERSION`.
//!
//! Reads `CLASSIC Main.yaml` (the install-immutable source of truth for the
//! application version) at build time and exposes `CLASSIC_Info.version`
//! as `env!("CLASSIC_APP_VERSION")` to the TUI binary. The TUI's update
//! check uses that constant instead of loading the YAML at startup so a
//! per-user YAML cache update cannot move the broadcast version ahead of
//! the actual binary.
//!
//! This mirrors the CLI's CMake-based extraction (see
//! `classic-cli/CMakeLists.txt`) so all native frontends derive their
//! installed-binary version from the same install-immutable source. The
//! GUI uses an analogous CMake block (`classic-gui/CMakeLists.txt`).
//!
//! Drift guards:
//! - The extracted YAML version MUST match `CARGO_PKG_VERSION` (Cargo.toml
//!   `version`). A mismatch fails the build with a diagnostic naming both
//!   sides so a release that forgets to bump one of them is caught at
//!   compile time, not at runtime.
//! - `cargo::rerun-if-changed` watches both the YAML and `Cargo.toml` so a
//!   version edit invalidates the cached env var.

use std::path::PathBuf;

fn main() {
    let manifest_dir = PathBuf::from(
        std::env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR must be set by Cargo"),
    );
    // ui-applications/classic-tui/build.rs → repo root via two parents.
    let yaml_path = manifest_dir
        .join("..")
        .join("..")
        .join("CLASSIC Data")
        .join("databases")
        .join("CLASSIC Main.yaml");

    // Use forward slashes in the rerun-if-changed line; Cargo accepts
    // either separator on Windows but forward slashes match the rest of
    // the build-script ecosystem.
    let yaml_path_display = yaml_path.display().to_string();
    println!("cargo::rerun-if-changed={yaml_path_display}");
    println!("cargo::rerun-if-changed=Cargo.toml");
    println!("cargo::rerun-if-changed=build.rs");

    let yaml_text = match std::fs::read_to_string(&yaml_path) {
        Ok(s) => s,
        Err(e) => panic!(
            "classic-tui build.rs: failed to read `{yaml_path_display}`: {e}; \
             this file is the documented single source of truth for the \
             application version (see classic-cli/CMakeLists.txt for the \
             matching CMake extraction)"
        ),
    };

    let version = match extract_classic_info_version(&yaml_text) {
        Ok(v) => v,
        Err(reason) => panic!(
            "classic-tui build.rs: could not extract `CLASSIC_Info.version` \
             from `{yaml_path_display}`: {reason}"
        ),
    };

    let cargo_pkg_version =
        std::env::var("CARGO_PKG_VERSION").expect("CARGO_PKG_VERSION must be set by Cargo");
    if version != cargo_pkg_version {
        panic!(
            "classic-tui build.rs: CLASSIC_Info.version `{version}` in \
             `{yaml_path_display}` disagrees with Cargo.toml \
             `version = \"{cargo_pkg_version}\"`. Update Cargo.toml's \
             `version` to match the YAML, or fix the YAML if Cargo.toml \
             is correct."
        );
    }

    println!("cargo::rustc-env=CLASSIC_APP_VERSION={version}");
}

/// Extract the value of `CLASSIC_Info.version` from a `CLASSIC Main.yaml`
/// text body. Returns `Ok(version)` (without any leading `v`/`V`) on
/// success, or `Err(reason)` on a structural mismatch.
///
/// Deliberately minimal: this is build-time scaffolding, not a YAML parser.
/// The accepted shape is `CLASSIC_Info.version: v?MAJOR.MINOR.PATCH`,
/// matching the schema-2.0 contract enforced at runtime by
/// `classic_config_core::shippable::validate_release_semver_shape`.
fn extract_classic_info_version(yaml_text: &str) -> Result<String, String> {
    let mut in_section = false;
    for line in yaml_text.lines() {
        let trimmed = line.trim_start();
        // Skip blank lines and comments without affecting section state.
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        // A column-0 header ending in `:` opens (or closes) a top-level
        // section. The line may contain a comment after the colon, so
        // strip that before comparing.
        if !line.starts_with(char::is_whitespace) {
            let header = trimmed
                .split_once('#')
                .map(|(h, _)| h)
                .unwrap_or(trimmed)
                .trim_end();
            in_section = header == "CLASSIC_Info:";
            continue;
        }
        if !in_section {
            continue;
        }
        // Inside CLASSIC_Info — look for `  version: <value>`. Indentation
        // is 2 spaces in the canonical file but accept any non-zero
        // leading whitespace.
        let Some(value) = trimmed.strip_prefix("version:") else {
            continue;
        };
        // Strip any trailing comment from the value side.
        let value = value
            .split_once('#')
            .map(|(v, _)| v)
            .unwrap_or(value)
            .trim();
        if value.is_empty() {
            return Err("`CLASSIC_Info.version` is empty".into());
        }
        // YAML-style quoting: tolerate single- or double-quoted scalar.
        let value = value
            .strip_prefix('"')
            .and_then(|v| v.strip_suffix('"'))
            .or_else(|| value.strip_prefix('\'').and_then(|v| v.strip_suffix('\'')))
            .unwrap_or(value);
        let bare = value
            .strip_prefix('v')
            .or_else(|| value.strip_prefix('V'))
            .unwrap_or(value);
        let parts: Vec<&str> = bare.split('.').collect();
        if parts.len() != 3 {
            return Err(format!(
                "`CLASSIC_Info.version: {value}` is not MAJOR.MINOR.PATCH \
                 (got {} dot-separated components)",
                parts.len()
            ));
        }
        for part in &parts {
            if part.is_empty() || !part.bytes().all(|b| b.is_ascii_digit()) {
                return Err(format!(
                    "`CLASSIC_Info.version: {value}` contains a non-digit \
                     component `{part}`; prerelease suffixes and build \
                     metadata are not allowed under the schema-2.0 contract"
                ));
            }
        }
        return Ok(bare.to_string());
    }
    Err(
        "could not find `CLASSIC_Info.version` (no `CLASSIC_Info:` section, \
         or no `version:` key inside it)"
            .into(),
    )
}
