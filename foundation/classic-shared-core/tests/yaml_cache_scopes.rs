//! Public-interface probes for the two scoped generic YAML caches.
//!
//! `classic_shared_core::yaml` owns two distinct caches: the logical-key
//! settings cache and the path/mtime-aware YAML-file cache. Each is reachable
//! through an opaque scope handle so a binding adapter (the merged Python
//! extension) can give every former extension facade its own store, while the
//! unscoped free functions keep using one process default scope.
//!
//! These tests pin the contract the adapter relies on:
//!
//! - an isolated scope never sees, clears, or counts another scope's entries;
//! - each scope keeps the cache's existing capacity, freshness, counter, and
//!   clear-versus-reset rules;
//! - the unscoped functions and `YamlOperations::new()` are the default scope;
//! - the two caches stay distinct even when a caller holds both handles.

use classic_shared_core::yaml::{
    LogicalKeyCacheScope, YamlFileCacheScope, YamlOperations, cache_size, cache_stats, clear_cache,
    clear_global_yaml_cache, get_cached, is_cached, load_settings_sync, reset_cache_stats,
    reset_yaml_cache_stats, yaml_cache_stats,
};
use serial_test::serial;
use std::io::Write;
use std::path::Path;
use std::time::Duration;
use tempfile::{NamedTempFile, tempdir};

/// Write `content` to a fresh temporary YAML file that lives until dropped.
fn yaml_file(content: &str) -> NamedTempFile {
    let mut file = NamedTempFile::new().expect("create temp yaml");
    file.write_all(content.as_bytes()).expect("write temp yaml");
    file.flush().expect("flush temp yaml");
    file
}

/// Empty both default scopes and zero their counters before a `#[serial]`
/// test that observes them.
fn reset_default_scopes() {
    clear_cache();
    reset_cache_stats();
    clear_global_yaml_cache();
    reset_yaml_cache_stats();
}

// ---------------------------------------------------------------------------
// Path/mtime-aware YAML-file cache
// ---------------------------------------------------------------------------

#[test]
#[serial]
fn yaml_operations_new_uses_the_default_file_cache_scope() {
    reset_default_scopes();
    let file = yaml_file("key: value\n");

    let ops = YamlOperations::new();
    assert_eq!(ops.cache_scope(), &YamlFileCacheScope::default_scope());
    ops.load_yaml_file(file.path()).unwrap();
    ops.load_yaml_file(file.path()).unwrap();

    let unscoped = yaml_cache_stats();
    let scoped = YamlFileCacheScope::default_scope().stats();
    assert_eq!((unscoped.hits, unscoped.misses, unscoped.size), (1, 1, 1));
    assert_eq!((scoped.hits, scoped.misses, scoped.size), (1, 1, 1));
    assert_eq!(scoped.capacity, unscoped.capacity);
}

#[test]
#[serial]
fn isolated_file_cache_scope_does_not_share_entries_or_counters() {
    reset_default_scopes();
    let file = yaml_file("key: value\n");

    let scope = YamlFileCacheScope::new_isolated();
    assert_ne!(scope, YamlFileCacheScope::default_scope());
    let scoped_ops = YamlOperations::with_cache_scope(scope.clone());
    assert_eq!(scoped_ops.cache_scope(), &scope);

    scoped_ops.load_yaml_file(file.path()).unwrap();
    scoped_ops.load_yaml_file(file.path()).unwrap();

    let stats = scope.stats();
    assert_eq!((stats.hits, stats.misses, stats.size), (1, 1, 1));
    assert_eq!(
        stats.capacity, 128,
        "isolated scopes keep the 128-entry bound"
    );

    let default = yaml_cache_stats();
    assert_eq!((default.hits, default.misses, default.size), (0, 0, 0));

    // A default-scope load is a miss even though the isolated scope holds
    // the same path.
    YamlOperations::new().load_yaml_file(file.path()).unwrap();
    assert_eq!(yaml_cache_stats().misses, 1);
    assert_eq!(yaml_cache_stats().hits, 0);
}

#[test]
#[serial]
fn clearing_or_resetting_one_file_cache_scope_leaves_the_other_untouched() {
    reset_default_scopes();
    let file = yaml_file("key: value\n");

    let scope = YamlFileCacheScope::new_isolated();
    let scoped_ops = YamlOperations::with_cache_scope(scope.clone());
    scoped_ops.load_yaml_file(file.path()).unwrap();
    YamlOperations::new().load_yaml_file(file.path()).unwrap();

    clear_global_yaml_cache();
    reset_yaml_cache_stats();
    assert_eq!(yaml_cache_stats().size, 0);
    assert_eq!(scope.stats().size, 1, "default clear must not evict scope");
    assert_eq!(scope.stats().misses, 1, "default reset must not zero scope");

    YamlOperations::new().load_yaml_file(file.path()).unwrap();
    scope.clear();
    assert_eq!(scope.stats().size, 0);
    assert_eq!(
        scope.stats().misses,
        1,
        "clear evicts entries, keeps counters"
    );
    assert_eq!(
        yaml_cache_stats().size,
        1,
        "scope clear must not evict default"
    );

    scope.reset_stats();
    assert_eq!((scope.stats().hits, scope.stats().misses), (0, 0));
    assert_eq!(
        yaml_cache_stats().misses,
        1,
        "scope reset must not zero default"
    );
}

#[test]
fn clear_cache_on_any_operations_object_clears_its_whole_scope() {
    let file_a = yaml_file("a: 1\n");
    let file_b = yaml_file("b: 2\n");
    let scope = YamlFileCacheScope::new_isolated();
    let first = YamlOperations::with_cache_scope(scope.clone());
    let second = YamlOperations::with_cache_scope(scope.clone());

    first.load_yaml_file(file_a.path()).unwrap();
    second.load_yaml_file(file_b.path()).unwrap();
    assert_eq!(scope.stats().size, 2);

    // The method is invoked on one object but empties the scope it shares.
    second.clear_cache();
    assert_eq!(scope.stats().size, 0);
    assert_eq!(first.get_cache_stats()["cached_files"], 0);
}

#[test]
fn isolated_file_cache_scope_keeps_mtime_freshness() {
    let dir = tempdir().unwrap();
    let path = dir.path().join("fresh.yaml");
    std::fs::write(&path, "version: 1\n").unwrap();

    let scope = YamlFileCacheScope::new_isolated();
    let ops = YamlOperations::with_cache_scope(scope.clone());
    assert_eq!(
        ops.load_yaml_file(&path).unwrap()["version"].as_i64(),
        Some(1)
    );

    // Coarse filesystem timestamps need a visible gap before the rewrite.
    std::thread::sleep(Duration::from_millis(1100));
    std::fs::write(&path, "version: 2\n").unwrap();

    assert_eq!(
        ops.load_yaml_file(&path).unwrap()["version"].as_i64(),
        Some(2)
    );
    let stats = scope.stats();
    assert_eq!((stats.hits, stats.misses), (0, 2));
}

#[test]
fn save_through_a_scope_invalidates_only_that_scope() {
    let dir = tempdir().unwrap();
    let path = dir.path().join("saved.yaml");
    std::fs::write(&path, "value: 1\n").unwrap();

    let scope = YamlFileCacheScope::new_isolated();
    let other = YamlFileCacheScope::new_isolated();
    let ops = YamlOperations::with_cache_scope(scope.clone());
    let other_ops = YamlOperations::with_cache_scope(other.clone());
    ops.load_yaml_file(&path).unwrap();
    other_ops.load_yaml_file(&path).unwrap();

    let yaml = ops.parse_yaml("value: 2\n").unwrap();
    ops.save_yaml_file(&path, &yaml).unwrap();

    assert_eq!(scope.stats().size, 0);
    assert_eq!(other.stats().size, 1);
}

// ---------------------------------------------------------------------------
// Logical-key settings cache
// ---------------------------------------------------------------------------

#[test]
#[serial]
fn unscoped_logical_key_functions_use_the_default_scope() {
    reset_default_scopes();
    let file = yaml_file("game: Fallout4\n");

    load_settings_sync("default_key", file.path()).unwrap();
    let scope = LogicalKeyCacheScope::default_scope();
    assert!(scope.is_cached("default_key"));
    assert!(scope.get_cached("default_key").is_some());
    assert_eq!(cache_stats().hits, 1);

    scope.clear_cache();
    assert_eq!(cache_size(), 0);
}

#[test]
#[serial]
fn isolated_logical_key_scope_does_not_share_entries_or_counters() {
    reset_default_scopes();
    let file = yaml_file("game: Fallout4\n");

    let scope = LogicalKeyCacheScope::new_isolated();
    assert_ne!(scope, LogicalKeyCacheScope::default_scope());
    let docs = scope.load_settings_sync("scoped_key", file.path()).unwrap();
    assert_eq!(docs[0]["game"].as_str(), Some("Fallout4"));

    assert!(scope.is_cached("scoped_key"));
    assert!(!is_cached("scoped_key"));
    assert!(get_cached("scoped_key").is_none());
    assert!(scope.get_cached("scoped_key").is_some());
    assert!(scope.get_cached("absent").is_none());

    let stats = scope.cache_stats();
    assert_eq!((stats.hits, stats.misses, stats.size), (1, 1, 1));
    assert_eq!(
        stats.capacity, 64,
        "isolated scopes keep the 64-entry bound"
    );
    let default = cache_stats();
    assert_eq!((default.hits, default.misses, default.size), (0, 1, 0));
    assert_eq!(scope.cache_keys(), vec!["scoped_key".to_string()]);
    assert_eq!(scope.cache_size(), 1);
}

#[test]
#[serial]
fn clearing_or_resetting_one_logical_key_scope_leaves_the_other_untouched() {
    reset_default_scopes();
    let file = yaml_file("game: Fallout4\n");

    let scope = LogicalKeyCacheScope::new_isolated();
    scope.load_settings_sync("scoped", file.path()).unwrap();
    load_settings_sync("default", file.path()).unwrap();
    scope.get_cached("scoped");
    get_cached("default");

    clear_cache();
    reset_cache_stats();
    assert!(scope.is_cached("scoped"));
    assert_eq!(scope.cache_stats().hits, 1);

    load_settings_sync("default", file.path()).unwrap();
    get_cached("default");
    assert!(scope.invalidate("scoped"));
    assert!(!scope.invalidate("default"), "invalidate is scope-local");
    scope.load_settings_sync("scoped", file.path()).unwrap();
    scope.clear_cache();
    assert_eq!(scope.cache_size(), 0);
    assert_eq!(scope.cache_stats().hits, 1, "clear keeps counters");
    assert!(is_cached("default"));

    scope.reset_cache_stats();
    assert_eq!(scope.cache_stats().hits, 0);
    assert_eq!(cache_stats().hits, 1, "scope reset must not zero default");
}

#[test]
fn logical_key_scope_batch_and_async_loads_stay_in_scope() {
    let first = yaml_file("a: 1\n");
    let second = yaml_file("b: 2\n");
    let paths: Vec<&Path> = vec![first.path(), second.path()];
    let scope = LogicalKeyCacheScope::new_isolated();

    assert_eq!(scope.load_batch_sync(&paths).unwrap(), 2);
    assert_eq!(scope.cache_size(), 2);
    assert!(scope.is_cached(&first.path().to_string_lossy()));

    let async_scope = LogicalKeyCacheScope::new_isolated();
    let runtime = classic_shared_core::get_runtime();
    runtime.block_on(async {
        async_scope
            .load_settings_async("async_key", first.path())
            .await
            .unwrap();
        assert_eq!(async_scope.load_batch_async(&paths).await.unwrap(), 2);
    });
    assert!(async_scope.is_cached("async_key"));
    assert_eq!(async_scope.cache_size(), 3);
    assert!(!scope.is_cached("async_key"));
}

// ---------------------------------------------------------------------------
// The two caches stay distinct
// ---------------------------------------------------------------------------

#[test]
fn file_cache_and_logical_key_cache_scopes_stay_distinct() {
    let file = yaml_file("game: Fallout4\n");
    let logical = LogicalKeyCacheScope::new_isolated();
    let file_scope = YamlFileCacheScope::new_isolated();
    let ops = YamlOperations::with_cache_scope(file_scope.clone());

    logical.load_settings_sync("settings", file.path()).unwrap();
    ops.load_yaml_file(file.path()).unwrap();

    file_scope.clear();
    assert!(
        logical.is_cached("settings"),
        "file-cache clear keeps logical keys"
    );

    ops.load_yaml_file(file.path()).unwrap();
    logical.clear_cache();
    assert_eq!(
        file_scope.stats().size,
        1,
        "logical clear keeps file entries"
    );
}
