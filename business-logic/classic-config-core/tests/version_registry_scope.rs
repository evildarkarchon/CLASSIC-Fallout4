//! Probes that config's Version Registry fallbacks read only a caller-selected
//! scope.
//!
//! A scope's snapshot is taken from the process working directory on first
//! use. These probes change the working directory, so they live in their own
//! test binary (process) and serialize on [`CWD_LOCK`].

use std::path::{Path, PathBuf};
use std::sync::{Mutex, MutexGuard};

use classic_config_core::{YamlDataCore, resolve_registry_version_info_in};
use classic_version_registry_core::{VersionRegistryScope, get_version_registry};

static CWD_LOCK: Mutex<()> = Mutex::new(());

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

/// Write a Version Registry root whose only non-VR Fallout 4 entry is an `OG`
/// build the shipped registry does not know.
fn write_custom_root(root: &Path, game_version: &str) {
    let yaml = format!(
        r#"Version_Registry:
  versions:
    - id: FO4_OG
      game: Fallout4
      is_vr: false
      version: "{game_version}"
      display_name: Custom Original
      short_name: OG
      docs_name: Fallout4
"#
    );
    std::fs::write(root.join("CLASSIC Main.yaml"), yaml).expect("write yaml root");
}

const MAIN_YAML: &str = r#"
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-15"
"#;

/// Game YAML that leaves `GameVersion` to the Version Registry fallback.
const GAME_YAML_WITH_ROOT: &str = r#"
Game_Info:
  Main_Root_Name: "Fallout 4"
"#;

/// Game YAML with no `Main_Root_Name`, so no registry fallback is needed.
const GAME_YAML_WITHOUT_ROOT: &str = r#"
Game_Info:
  GameVersion: "1.10.163"
"#;

const IGNORE_YAML: &str = "CLASSIC_Ignore_Fallout4: []\n";

fn build(game_yaml: &str, scope: &VersionRegistryScope) -> YamlDataCore {
    YamlDataCore::from_yaml_content_in_version_registry_scope(
        MAIN_YAML,
        game_yaml,
        IGNORE_YAML,
        "Fallout4".to_string(),
        "Original".to_string(),
        scope,
    )
    .expect("yaml data builds")
}

#[test]
fn yaml_data_fallbacks_read_only_the_supplied_scope() {
    let cwd = CwdGuard::acquire();
    // Take the default snapshot before entering a custom root, so this probe
    // cannot be the one that initializes it from that root.
    let shipped_og = get_version_registry()
        .get_by_id("FO4_OG")
        .expect("shipped FO4_OG")
        .version;
    let root = tempfile::tempdir().expect("root");
    write_custom_root(root.path(), "1.10.999.0");

    let scope = VersionRegistryScope::new_isolated();
    cwd.enter(root.path());

    let scoped = build(GAME_YAML_WITH_ROOT, &scope);
    let unscoped = YamlDataCore::from_yaml_content(
        MAIN_YAML,
        GAME_YAML_WITH_ROOT,
        IGNORE_YAML,
        "Fallout4".to_string(),
        "Original".to_string(),
    )
    .expect("yaml data builds");

    assert_eq!(scoped.game_version, "1.10.999");
    assert_eq!(
        unscoped.game_version,
        format!(
            "{}.{}.{}",
            shipped_og.major, shipped_og.minor, shipped_og.patch
        )
    );

    let resolved = resolve_registry_version_info_in(scope.registry(), "Fallout 4", "Original")
        .expect("scoped registry info");
    assert_eq!(resolved.display_name, "Custom Original");
}

#[test]
fn yaml_data_without_main_root_name_does_not_take_the_snapshot() {
    let cwd = CwdGuard::acquire();
    let first_root = tempfile::tempdir().expect("first root");
    let later_root = tempfile::tempdir().expect("later root");
    write_custom_root(first_root.path(), "1.10.111.0");
    write_custom_root(later_root.path(), "1.10.222.0");

    let scope = VersionRegistryScope::new_isolated();

    // Without Main_Root_Name the build needs no registry metadata, so the
    // scope must still be untouched afterwards...
    cwd.enter(first_root.path());
    let without_root = build(GAME_YAML_WITHOUT_ROOT, &scope);
    assert_eq!(without_root.game_version, "1.10.163");

    // ...which the first build that does need it proves by snapshotting the
    // root active at that later moment.
    cwd.enter(later_root.path());
    assert_eq!(build(GAME_YAML_WITH_ROOT, &scope).game_version, "1.10.222");
}
