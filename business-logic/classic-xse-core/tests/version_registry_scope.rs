//! Probe that XSE Folder resolution reads only a caller-selected Version
//! Registry scope.
//!
//! A scope's snapshot is taken from the process working directory on first
//! use, so this probe changes the working directory; it lives in its own test
//! binary (process) so no other test observes that change.

use std::path::Path;

use classic_version_registry_core::{VersionRegistryScope, get_version_registry};
use classic_xse_core::{
    resolve_xse_folder_for_scan, resolve_xse_folder_for_scan_in_version_registry_scope,
};

/// Restores the original working directory on drop, even if the probe panics.
struct RestoreCwd(std::path::PathBuf);

impl Drop for RestoreCwd {
    fn drop(&mut self) {
        // Best effort: a failed restore must not mask the probe's own panic.
        let _ = std::env::set_current_dir(&self.0);
    }
}

/// Write a Version Registry root whose `FO4_OG` entry names its own XSE.
fn write_custom_root(root: &Path) {
    let yaml = r#"Version_Registry:
  versions:
    - id: FO4_OG
      game: Fallout4
      is_vr: false
      version: "1.10.163.0"
      short_name: OG
      docs_name: Fallout4
      xse:
        acronym: CUSTOMSE
        compatible_version: "0.6.23"
"#;
    std::fs::write(root.join("CLASSIC Main.yaml"), yaml).expect("write yaml root");
}

#[test]
fn xse_folder_derives_from_the_supplied_scope_only() {
    let _restore = RestoreCwd(std::env::current_dir().expect("current dir"));
    // Take the default snapshot before entering a custom root, so this probe
    // cannot be the one that initializes it from that root.
    let _ = get_version_registry();
    let registry_root = tempfile::tempdir().expect("registry root");
    let yaml_dir_data = tempfile::tempdir().expect("yaml dir without Local.yaml");
    let docs_root = tempfile::tempdir().expect("configured docs root");
    write_custom_root(registry_root.path());

    let scope = VersionRegistryScope::new_isolated();
    std::env::set_current_dir(registry_root.path()).expect("enter registry root");

    let scoped = resolve_xse_folder_for_scan_in_version_registry_scope(
        yaml_dir_data.path(),
        "Fallout4",
        "Original",
        Some(docs_root.path()),
        &scope,
    );
    let unscoped = resolve_xse_folder_for_scan(
        yaml_dir_data.path(),
        "Fallout4",
        "Original",
        Some(docs_root.path()),
    );

    assert_eq!(scoped, Some(docs_root.path().join("CUSTOMSE")));
    assert_eq!(unscoped, Some(docs_root.path().join("F4SE")));
}
