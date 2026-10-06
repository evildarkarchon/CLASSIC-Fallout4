//! Probes that the Local.yaml-reading XSE Folder composition reads its Game
//! Local document only through the caller-selected YAML-file cache scope.
//!
//! The default YAML-file cache scope is process-global, so this probe lives in
//! its own test binary with a single test.

use classic_scangame_core::resolve_xse_folder_for_scan_in_scopes;
use classic_shared_core::yaml::YamlFileCacheScope;
use classic_version_registry_core::VersionRegistryScope;
use std::path::PathBuf;
use tempfile::tempdir;

/// `(hits, misses, entries)` for one YAML-file cache scope.
fn counters(scope: &YamlFileCacheScope) -> (u64, u64, usize) {
    let stats = scope.stats();
    (stats.hits, stats.misses, stats.size)
}

#[test]
fn scoped_composition_reads_game_local_only_through_the_supplied_scope() {
    let root = tempdir().expect("installation root");
    let data = root.path().join("CLASSIC Data");
    std::fs::create_dir_all(&data).expect("CLASSIC Data directory");
    std::fs::write(
        data.join("CLASSIC Fallout4 Local.yaml"),
        "Game_Info:\n  Docs_Folder_XSE: probe-xse\n",
    )
    .expect("Game Local document");
    let facade_scope = YamlFileCacheScope::new_isolated();
    let default_before = counters(&YamlFileCacheScope::default_scope());

    // An explicit XSE Folder needs no registry entry, so no host discovery runs.
    let folder = resolve_xse_folder_for_scan_in_scopes(
        &data,
        "Fallout4",
        "auto",
        None,
        &VersionRegistryScope::new_isolated(),
        &facade_scope,
    );

    assert_eq!(folder, Some(PathBuf::from("probe-xse")));
    assert_eq!(counters(&facade_scope), (0, 1, 1));
    assert_eq!(
        counters(&YamlFileCacheScope::default_scope()),
        default_before,
        "a scoped composition must not read, fill, or count the default scope"
    );
}
