//! FormID database bridge for CXX FFI.
//!
//! Bridges `classic_database_core::DatabasePool` for SQLite-backed FormID lookups
//! with caching. All async operations are wrapped with `get_runtime().block_on()`.

use classic_database_core::DatabasePool;
use classic_shared_core::get_runtime;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;

/// Opaque wrapper around `DatabasePool` for CXX FFI.
pub struct DbPool {
    inner: Arc<DatabasePool>,
}

fn db_pool_new(game_table: &str, max_connections: u32, cache_ttl_secs: u64) -> Box<DbPool> {
    let max_conn = if max_connections > 0 {
        Some(max_connections as usize)
    } else {
        None
    };
    Box::new(DbPool {
        inner: Arc::new(DatabasePool::new(
            max_conn,
            Duration::from_secs(cache_ttl_secs),
            game_table.to_string(),
        )),
    })
}

fn db_pool_initialize(pool: &DbPool, db_paths: &[String]) -> Result<(), String> {
    let paths: Vec<PathBuf> = db_paths.iter().map(PathBuf::from).collect();
    get_runtime()
        .block_on(pool.inner.initialize(paths))
        .map_err(|e| format!("{e}"))
}

fn db_pool_get_entry(pool: &DbPool, formid: &str, plugin: &str) -> String {
    match get_runtime().block_on(pool.inner.get_entry(formid, plugin, None)) {
        Ok(Some(entry)) => entry,
        Ok(None) => String::new(),
        Err(_) => String::new(),
    }
}

fn db_pool_get_entries_batch(pool: &DbPool, formids: &[String], plugins: &[String]) -> Vec<String> {
    let pairs: Vec<(String, String)> = formids
        .iter()
        .zip(plugins.iter())
        .map(|(f, p)| (f.clone(), p.clone()))
        .collect();
    let result = get_runtime().block_on(pool.inner.get_entries_batch(pairs, None, 50));
    match result {
        Ok(map) => {
            // Return as "formid\tvalue" pairs for C++ to parse
            map.into_iter()
                .map(|(k, v)| format!("{k}\t{v}"))
                .collect()
        }
        Err(_) => Vec::new(),
    }
}

fn db_pool_is_available(pool: &DbPool) -> bool {
    pool.inner.is_available()
}

fn db_pool_cache_size(pool: &DbPool) -> usize {
    pool.inner.cache_size()
}

fn db_pool_clear_cache(pool: &DbPool, expired_only: bool) -> usize {
    pool.inner.clear_cache(expired_only)
}

fn db_pool_close(pool: &DbPool) -> Result<(), String> {
    get_runtime()
        .block_on(pool.inner.close())
        .map_err(|e| format!("{e}"))
}

fn db_pool_game_table(pool: &DbPool) -> String {
    pool.inner.get_game_table()
}

#[cxx::bridge(namespace = "classic::database")]
mod ffi {
    extern "Rust" {
        type DbPool;

        fn db_pool_new(game_table: &str, max_connections: u32, cache_ttl_secs: u64) -> Box<DbPool>;
        fn db_pool_initialize(pool: &DbPool, db_paths: &[String]) -> Result<()>;
        fn db_pool_get_entry(pool: &DbPool, formid: &str, plugin: &str) -> String;
        fn db_pool_get_entries_batch(pool: &DbPool, formids: &[String], plugins: &[String]) -> Vec<String>;
        fn db_pool_is_available(pool: &DbPool) -> bool;
        fn db_pool_cache_size(pool: &DbPool) -> usize;
        fn db_pool_clear_cache(pool: &DbPool, expired_only: bool) -> usize;
        fn db_pool_close(pool: &DbPool) -> Result<()>;
        fn db_pool_game_table(pool: &DbPool) -> String;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_db_pool_new() {
        let pool = db_pool_new("Fallout4", 4, 300);
        assert_eq!(db_pool_game_table(&pool), "Fallout4");
    }

    #[test]
    fn test_db_pool_not_available_before_init() {
        let pool = db_pool_new("Fallout4", 4, 300);
        assert!(!db_pool_is_available(&pool));
    }

    #[test]
    fn test_db_pool_cache_operations() {
        let pool = db_pool_new("Fallout4", 4, 300);
        assert_eq!(db_pool_cache_size(&pool), 0);
        let cleared = db_pool_clear_cache(&pool, false);
        assert_eq!(cleared, 0);
    }

    #[test]
    fn test_db_pool_get_entry_before_init() {
        let pool = db_pool_new("Fallout4", 4, 300);
        let entry = db_pool_get_entry(&pool, "00000001", "Fallout4.esm");
        assert!(entry.is_empty());
    }
}
