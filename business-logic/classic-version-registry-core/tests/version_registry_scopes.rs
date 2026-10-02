//! Behavior probes for Version Registry scopes.
//!
//! A scope's snapshot is taken from the process working directory on first
//! use, so every probe that can initialize a snapshot holds [`CWD_LOCK`]: the
//! working directory is process-global and the test harness runs tests on
//! parallel threads.

use std::path::{Path, PathBuf};
use std::sync::{Mutex, MutexGuard};

use classic_version_registry_core::{
    Fallout4Version, GameVersion, VersionRegistryScope, get_version_registry,
};
use semver::Version;

static CWD_LOCK: Mutex<()> = Mutex::new(());

/// Serialize working-directory changes and restore the original directory
/// when the guard drops, even if the probe panics.
struct CwdGuard {
    original: PathBuf,
    _lock: MutexGuard<'static, ()>,
}

impl CwdGuard {
    fn acquire() -> Self {
        // A probe that panicked while holding the lock already restored the
        // directory through its own guard, so a poisoned lock is still usable.
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

/// Write a minimal `CLASSIC Main.yaml` at `root` whose only Fallout 4 entry
/// is `FO4_OG` with the given display name, game version, and F4SE version.
fn write_yaml_root(root: &Path, display_name: &str, game_version: &str, f4se_version: &str) {
    let yaml = format!(
        r#"Version_Registry:
  versions:
    - id: FO4_OG
      game: Fallout4
      is_vr: false
      version: "{game_version}"
      display_name: {display_name}
      short_name: OG
      docs_name: Fallout4
      xse:
        acronym: F4SE
        compatible_version: "{f4se_version}"
"#
    );
    std::fs::write(root.join("CLASSIC Main.yaml"), yaml).expect("write yaml root");
}

fn og_display_name(scope: &VersionRegistryScope) -> String {
    scope
        .registry()
        .get_by_id("FO4_OG")
        .expect("FO4_OG entry")
        .display_name
        .clone()
}

#[test]
fn default_scope_is_the_unscoped_registry_snapshot() {
    let _cwd = CwdGuard::acquire();
    let default_scope = VersionRegistryScope::default_scope();

    assert!(std::ptr::eq(
        default_scope.registry(),
        get_version_registry()
    ));
    assert_eq!(default_scope, VersionRegistryScope::default_scope());
}

#[test]
fn isolated_scopes_are_distinct_handles_and_clones_share_one_snapshot() {
    let _cwd = CwdGuard::acquire();
    let scope = VersionRegistryScope::new_isolated();
    let clone = scope.clone();

    assert_ne!(scope, VersionRegistryScope::default_scope());
    assert_ne!(scope, VersionRegistryScope::new_isolated());
    assert_eq!(scope, clone);
    assert!(std::ptr::eq(scope.registry(), clone.registry()));
    assert!(!std::ptr::eq(scope.registry(), get_version_registry()));
}

#[test]
fn snapshot_is_taken_at_first_use_from_that_scopes_root_and_never_reloads() {
    let cwd = CwdGuard::acquire();
    let root_a = tempfile::tempdir().expect("root a");
    let root_b = tempfile::tempdir().expect("root b");
    let empty_root = tempfile::tempdir().expect("empty root");
    write_yaml_root(root_a.path(), "Root A Original", "1.10.163.0", "0.6.23");
    write_yaml_root(root_b.path(), "Root B Original", "1.10.163.0", "0.6.23");

    // Both handles exist before any root is entered, so whatever each one
    // reports proves when its snapshot was taken (first use), not created.
    let scope_a = VersionRegistryScope::new_isolated();
    let scope_b = VersionRegistryScope::new_isolated();
    let fallback_scope = VersionRegistryScope::new_isolated();

    cwd.enter(root_a.path());
    assert_eq!(og_display_name(&scope_a), "Root A Original");

    cwd.enter(root_b.path());
    assert_eq!(og_display_name(&scope_b), "Root B Original");
    // Stable: A's first-use snapshot ignores the later working directory.
    assert_eq!(og_display_name(&scope_a), "Root A Original");

    // Stable: rewriting A's file and returning to it does not reload A.
    write_yaml_root(root_a.path(), "Root A Rewritten", "1.10.163.0", "0.6.23");
    cwd.enter(root_a.path());
    assert_eq!(og_display_name(&scope_a), "Root A Original");

    // A root without YAML falls back to the embedded CLASSIC Main.yaml.
    cwd.enter(empty_root.path());
    let fallback_og = fallback_scope
        .registry()
        .get_by_id("FO4_OG")
        .expect("embedded FO4_OG");
    assert_eq!(fallback_og.display_name, "Fallout 4 Original");
    assert_eq!(og_display_name(&scope_b), "Root B Original");
}

#[test]
fn known_version_queries_and_matching_answer_from_the_scope_snapshot() {
    let cwd = CwdGuard::acquire();
    let root = tempfile::tempdir().expect("root");
    // A version and F4SE build that the shipped registry does not know.
    write_yaml_root(root.path(), "Custom Original", "1.10.999.0", "0.6.99");

    // Take the default snapshot before entering the custom root so this
    // probe cannot be the one that initializes it from that root.
    let shipped = get_version_registry();
    let scope = VersionRegistryScope::new_isolated();
    cwd.enter(root.path());
    let registry = scope.registry();

    assert!(registry.is_known_fallout4_version(&Version::new(1, 10, 999)));
    assert!(registry.is_known_f4se_version(&Version::new(0, 6, 99)));
    assert!(!registry.is_known_fallout4_version(&Version::new(1, 10, 163)));

    let detected = GameVersion::new(1, 10, 999, 0);
    let matched = registry.match_version(&detected, "Fallout4", false);
    assert_eq!(
        matched.version_info.map(|info| info.display_name),
        Some("Custom Original".to_string())
    );

    let info = Fallout4Version::Original
        .version_info_in(registry)
        .expect("scoped FO4_OG");
    assert_eq!(info.display_name, "Custom Original");

    // The shipped default snapshot keeps its own answers.
    assert!(!shipped.is_known_fallout4_version(&Version::new(1, 10, 999)));
    assert!(shipped.is_known_fallout4_version(&Version::new(1, 10, 163)));
}

#[test]
fn first_use_leaves_the_shared_yaml_file_cache_untouched() {
    let cwd = CwdGuard::acquire();
    // Settle the default snapshot first so its own load is not counted here.
    let _ = get_version_registry();
    let root = tempfile::tempdir().expect("root");
    write_yaml_root(root.path(), "Cache Probe Original", "1.10.163.0", "0.6.23");
    let before = classic_shared_core::yaml::yaml_cache_stats();

    let scope = VersionRegistryScope::new_isolated();
    cwd.enter(root.path());
    assert_eq!(og_display_name(&scope), "Cache Probe Original");

    // The default YAML-file cache scope belongs to another owner (the config
    // facade once the Python facades merge); a snapshot load must not add
    // entries to it or move its counters.
    let after = classic_shared_core::yaml::yaml_cache_stats();
    assert_eq!(
        (after.hits, after.misses, after.size),
        (before.hits, before.misses, before.size)
    );
}

#[test]
fn handle_moved_to_another_thread_names_the_same_snapshot() {
    let _cwd = CwdGuard::acquire();
    let scope = VersionRegistryScope::new_isolated();
    let here: *const _ = scope.registry();

    let moved = scope.clone();
    let there = std::thread::spawn(move || moved.registry() as *const _ as usize)
        .join()
        .expect("worker thread");

    assert_eq!(here as usize, there);
}
