//! Probes that Game Local facts are read through the caller-selected
//! path/mtime YAML-file cache scope.
//!
//! `read_game_local_facts_in_yaml_file_cache_scope` lets a binding facade keep
//! its Game Local reads in its own core-owned scope, while the unscoped
//! `read_game_local_facts` keeps using the process default scope that Rust,
//! CXX, and Node callers have always used. The default scope is
//! process-global, so these probes live in their own test binary and run
//! serially.

use classic_config_core::{
    game_local_yaml_path, read_game_local_facts, read_game_local_facts_in_yaml_file_cache_scope,
};
use classic_shared_core::yaml::YamlFileCacheScope;
use std::path::{Path, PathBuf};
use tempfile::tempdir;

/// `(hits, misses, entries)` for one YAML-file cache scope.
fn counters(scope: &YamlFileCacheScope) -> (u64, u64, usize) {
    let stats = scope.stats();
    (stats.hits, stats.misses, stats.size)
}

/// Writes a Fallout 4 Game Local document recording an explicit XSE Folder.
fn write_game_local(yaml_dir_data: &Path) {
    std::fs::create_dir_all(yaml_dir_data).expect("CLASSIC Data directory");
    std::fs::write(
        game_local_yaml_path(yaml_dir_data, "Fallout4"),
        "Game_Info:\n  Docs_Folder_XSE: probe-xse\n",
    )
    .expect("Game Local document");
}

#[test]
#[serial_test::serial]
fn scoped_game_local_read_fills_only_the_supplied_scope() {
    let root = tempdir().expect("installation root");
    let data = root.path().join("CLASSIC Data");
    write_game_local(&data);
    let facade_scope = YamlFileCacheScope::new_isolated();
    let default_before = counters(&YamlFileCacheScope::default_scope());

    let facts = read_game_local_facts_in_yaml_file_cache_scope(&data, "Fallout4", &facade_scope);
    assert_eq!(facts.docs_folder_xse, Some(PathBuf::from("probe-xse")));
    assert_eq!(
        counters(&facade_scope),
        (0, 1, 1),
        "first read misses and fills the scope"
    );

    let again = read_game_local_facts_in_yaml_file_cache_scope(&data, "Fallout4", &facade_scope);
    assert_eq!(again, facts);
    assert_eq!(
        counters(&facade_scope),
        (1, 1, 1),
        "unchanged document hits the scope"
    );

    assert_eq!(
        counters(&YamlFileCacheScope::default_scope()),
        default_before,
        "a scoped read must not read, fill, or count the default scope"
    );
}

#[test]
#[serial_test::serial]
fn unscoped_game_local_read_keeps_using_the_default_scope() {
    let root = tempdir().expect("installation root");
    let data = root.path().join("CLASSIC Data");
    write_game_local(&data);
    let bystander = YamlFileCacheScope::new_isolated();
    let default_scope = YamlFileCacheScope::default_scope();
    let (_, misses_before, _) = counters(&default_scope);

    let facts = read_game_local_facts(&data, "Fallout4");

    assert_eq!(facts.docs_folder_xse, Some(PathBuf::from("probe-xse")));
    assert_eq!(counters(&default_scope).1, misses_before + 1);
    assert_eq!(counters(&bystander), (0, 0, 0));
}
