//! Probes that scangame's registry-backed checks read only a caller-selected
//! Version Registry scope.
//!
//! A scope's snapshot is taken from the process working directory on first
//! use. These probes change the working directory, so they live in their own
//! test binary (process) and serialize on [`CWD_LOCK`].

use std::path::{Path, PathBuf};
use std::sync::{Mutex, MutexGuard};

use classic_file_io_core::FileHashScope;
use classic_scangame_core::game_setup_intake::{
    GameSetupCheckKind, GameSetupIntake, GameSetupIntakeResult,
};
use classic_scangame_core::xse::{AddressLibInfo, GameVersion, ValidationResult, XseChecker};
use classic_shared_core::GameId;
use classic_version_registry_core::{VersionRegistryScope, get_version_registry};

static CWD_LOCK: Mutex<()> = Mutex::new(());

const CUSTOM_ADDRESS_LIBRARY: &str = "custom-address-library.bin";

/// Serialize working-directory changes and restore the original directory on
/// drop, even if the probe panics.
struct CwdGuard {
    original: PathBuf,
    _lock: MutexGuard<'static, ()>,
}

impl CwdGuard {
    fn acquire() -> Self {
        // The guard of a probe that panicked already restored the directory,
        // so a poisoned lock is still safe to reuse.
        let lock = CWD_LOCK
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        Self {
            original: std::env::current_dir().expect("current dir"),
            _lock: lock,
        }
    }

    fn enter(&self, dir: &Path) {
        std::env::set_current_dir(dir).expect("enter yaml root");
    }
}

impl Drop for CwdGuard {
    fn drop(&mut self) {
        // Best effort: a failed restore must not mask the probe's own panic.
        let _ = std::env::set_current_dir(&self.original);
    }
}

/// Write a Version Registry root whose `FO4_OG` entry expects a custom
/// Address Library file and carries a recognizable display name.
fn write_custom_root(root: &Path) {
    let yaml = format!(
        r#"Version_Registry:
  versions:
    - id: FO4_OG
      game: Fallout4
      is_vr: false
      version: "1.10.163.0"
      display_name: Custom Original
      short_name: OG
      docs_name: Fallout4
      address_library:
        filename: {CUSTOM_ADDRESS_LIBRARY}
        format: bin
        nexus_url: https://example.invalid/custom
"#
    );
    std::fs::write(root.join("CLASSIC Main.yaml"), yaml).expect("write yaml root");
}

/// Enter a fresh custom registry root and return an isolated scope whose
/// first use happens inside it. The default snapshot is taken first, so these
/// probes can never be the ones that initialize it from a custom root.
fn custom_scope(cwd: &CwdGuard, root: &Path) -> VersionRegistryScope {
    let _ = get_version_registry();
    write_custom_root(root);
    let scope = VersionRegistryScope::new_isolated();
    cwd.enter(root);
    let _ = scope.registry();
    scope
}

fn registry_metadata_message(result: &GameSetupIntakeResult) -> &str {
    &result
        .checks
        .iter()
        .find(|check| check.kind == GameSetupCheckKind::RegistryMetadata)
        .expect("registry metadata check")
        .message
}

#[test]
fn address_library_info_reads_the_supplied_snapshot() {
    let cwd = CwdGuard::acquire();
    let root = tempfile::tempdir().expect("root");
    let scope = custom_scope(&cwd, root.path());

    assert_eq!(
        AddressLibInfo::original_in(scope.registry()).filename,
        CUSTOM_ADDRESS_LIBRARY
    );
    assert_eq!(
        AddressLibInfo::original().filename,
        "version-1-10-163-0.bin"
    );
}

#[test]
fn xse_checker_validates_against_its_scope() {
    let cwd = CwdGuard::acquire();
    let root = tempfile::tempdir().expect("root");
    let plugins = tempfile::tempdir().expect("plugins");
    std::fs::write(plugins.path().join(CUSTOM_ADDRESS_LIBRARY), b"").expect("plugin file");
    let scope = custom_scope(&cwd, root.path());

    let scoped = XseChecker::new(plugins.path(), GameVersion::Original)
        .expect("checker")
        .with_version_registry_scope(scope);
    let unscoped = XseChecker::new(plugins.path(), GameVersion::Original).expect("checker");

    assert_eq!(scoped.check(), ValidationResult::CorrectVersion);
    assert_eq!(unscoped.check(), ValidationResult::NotFound);
}

#[test]
fn game_setup_intake_reads_registry_facts_from_its_scope() {
    let cwd = CwdGuard::acquire();
    let root = tempfile::tempdir().expect("root");
    let scope = custom_scope(&cwd, root.path());
    let intake = GameSetupIntake::new(GameId::Fallout4, "Original");

    let scoped = intake.run_in_scopes(&FileHashScope::new_isolated(), &scope);
    let unscoped = intake.run_in_hash_scope(&FileHashScope::new_isolated());

    assert_eq!(
        registry_metadata_message(&scoped),
        "Using Version Registry metadata for Custom Original."
    );
    assert_eq!(
        registry_metadata_message(&unscoped),
        "Using Version Registry metadata for Fallout 4 Original."
    );
}

#[test]
fn xse_folder_from_game_local_facts_derives_from_its_scope() {
    let cwd = CwdGuard::acquire();
    // Take the default snapshot before entering the custom root, so this probe
    // cannot be the one that initializes it from that root.
    let _ = get_version_registry();
    let root = tempfile::tempdir().expect("root");
    std::fs::write(
        root.path().join("CLASSIC Main.yaml"),
        r#"Version_Registry:
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
"#,
    )
    .expect("write yaml root");
    // The recorded documents folder arrives through config's Game Local facts.
    let data = tempfile::tempdir().expect("CLASSIC Data");
    let docs = tempfile::tempdir().expect("recorded docs root");
    std::fs::write(
        data.path().join("CLASSIC Fallout4 Local.yaml"),
        format!(
            "Game_Info:\n  Root_Folder_Docs: '{}'\n",
            docs.path().display()
        ),
    )
    .expect("write Local.yaml");
    let scope = VersionRegistryScope::new_isolated();
    cwd.enter(root.path());

    let scoped = classic_scangame_core::resolve_xse_folder_for_scan_in_version_registry_scope(
        data.path(),
        "Fallout4",
        "Original",
        None,
        &scope,
    );
    let unscoped = classic_scangame_core::resolve_xse_folder_for_scan(
        data.path(),
        "Fallout4",
        "Original",
        None,
    );

    assert_eq!(scoped, Some(docs.path().join("CUSTOMSE")));
    assert_eq!(unscoped, Some(docs.path().join("F4SE")));
}
