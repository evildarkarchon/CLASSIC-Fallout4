//! Pins that User Settings never uses the shared path/mtime YAML-file cache.
//!
//! The Python `classic_user_settings` facade selects no YAML-file cache scope
//! because this core only uses `YamlOperations` as a stateless parse, dump,
//! and dot-path helper. If a future change starts reading or writing User
//! Settings through `load_yaml_file` / `save_yaml_file`, the entries would land
//! in the process default scope that `classic_config.clear_yaml_cache()` owns,
//! and this probe fails so the change can choose a scope instead. The default
//! scope is process-global, so this probe lives in its own test binary.

use classic_shared_core::yaml::YamlFileCacheScope;
use classic_user_settings_core::{
    UserSettings, UserSettingsCommitOutcome, UserSettingsUpdate, UserSettingsUpdatePreview,
};

/// `(hits, misses, entries)` for one YAML-file cache scope.
fn counters(scope: &YamlFileCacheScope) -> (u64, u64, usize) {
    let stats = scope.stats();
    (stats.hits, stats.misses, stats.size)
}

#[test]
fn open_preview_and_commit_leave_the_default_yaml_file_cache_untouched() {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Update Check: true\n",
    )
    .unwrap();
    let default_before = counters(&YamlFileCacheScope::default_scope());

    let settings = UserSettings::open(root.path());
    let UserSettingsUpdatePreview::Accepted(accepted) =
        settings.preview_update(UserSettingsUpdate::new().with_update_check(false))
    else {
        panic!("valid Update Check change should be accepted");
    };
    let outcome = accepted.commit(root.path()).unwrap();
    assert!(matches!(
        outcome,
        UserSettingsCommitOutcome::Committed { .. }
    ));
    assert!(
        !UserSettings::open(root.path())
            .update_preferences()
            .update_check()
    );

    assert_eq!(
        counters(&YamlFileCacheScope::default_scope()),
        default_before,
        "User Settings must not read, fill, or count the shared YAML-file cache"
    );
}
