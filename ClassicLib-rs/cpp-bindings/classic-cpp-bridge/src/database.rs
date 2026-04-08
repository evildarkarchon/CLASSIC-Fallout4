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
            map.into_iter().map(|(k, v)| format!("{k}\t{v}")).collect()
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

// ── Typed FormID accessors (CXXS-05) ───────────────────────────────
// Additive per D-08 — existing db_pool_get_entry (returns "") and
// db_pool_get_entries_batch (returns Vec<String> tab-delimited) are UNCHANGED.

/// Typed single-entry FormID lookup.
///
/// Returns a `FormIdEntryDto` with `found: true` if the entry exists in the
/// database (or cache), or `found: false` for misses or errors. The input
/// `formid` and `plugin` are echoed back in the result so C++ callers do not
/// have to track the input separately.
///
/// Bridge contract: this is the typed complement to `db_pool_get_entry`
/// (which returns `""` on miss). Both fns coexist per D-08 (additive, not
/// replacing). The `found` flag is derived from whether the core returned
/// `Ok(Some(_))` — so an `Ok(None)` miss or any `Err` both produce
/// `found: false`.
fn db_pool_get_entry_typed(pool: &DbPool, formid: &str, plugin: &str) -> ffi::FormIdEntryDto {
    let result = get_runtime().block_on(pool.inner.get_entry(formid, plugin, None));
    let (value, found) = match result {
        Ok(Some(v)) => (v, true),
        Ok(None) => (String::new(), false),
        Err(_) => (String::new(), false),
    };
    ffi::FormIdEntryDto {
        formid: formid.to_string(),
        plugin: plugin.to_string(),
        value,
        found,
    }
}

/// Typed batch FormID lookup with positional repackaging.
///
/// Bridge contract (Codex review MEDIUM correction):
/// - The core `get_entries_batch` returns a HIT-ONLY HashMap keyed by
///   `"formid:plugin"`. Misses are ABSENT from the map — not present with
///   empty or null value. This is a MAJOR contract distinction C++ callers
///   must understand.
/// - This wrapper repackages the result into ONE `FormIdEntryDto` PER INPUT
///   PAIR so that `result[i]` corresponds to `(formids[i], plugins[i])`.
///   Misses get `found: false` and `value: ""`.
/// - Length mismatch between `formids` and `plugins` returns an empty Vec
///   (fail-soft, NOT an error). This matches the existing tab-delimited
///   wrapper philosophy.
/// - Empty input returns empty Vec immediately (no runtime cost).
/// - The internal `batch_size` is set to 100 — a balance between SQL query
///   overhead and UI thread responsiveness. C++ callers requesting more than
///   ~1000 entries in one call should chunk on their side to avoid blocking
///   the Qt event loop; this wrapper does NOT chunk on behalf of the caller.
fn db_pool_get_entries_batch_typed(
    pool: &DbPool,
    formids: &[String],
    plugins: &[String],
) -> Vec<ffi::FormIdEntryDto> {
    if formids.len() != plugins.len() || formids.is_empty() {
        return Vec::new();
    }

    let pairs: Vec<(String, String)> = formids
        .iter()
        .zip(plugins.iter())
        .map(|(f, p)| (f.clone(), p.clone()))
        .collect();

    // Core API: get_entries_batch(formid_plugin_pairs, table, batch_size)
    // Returns HashMap<String, String> keyed by "formid:plugin", hit-only.
    let map = get_runtime()
        .block_on(pool.inner.get_entries_batch(pairs.clone(), None, 100))
        .unwrap_or_default();

    // Positional repackaging — one DTO per input pair, result[i] == (formids[i], plugins[i]).
    // Misses (absent from hit-only map) get found: false.
    pairs
        .into_iter()
        .map(|(formid, plugin)| {
            let lookup_key = format!("{}:{}", formid, plugin);
            match map.get(&lookup_key) {
                Some(v) => ffi::FormIdEntryDto {
                    formid,
                    plugin,
                    value: v.clone(),
                    found: true,
                },
                None => ffi::FormIdEntryDto {
                    formid,
                    plugin,
                    value: String::new(),
                    found: false,
                },
            }
        })
        .collect()
}

#[cxx::bridge(namespace = "classic::database")]
mod ffi {
    // CXXS-05: Typed FormID lookup DTO (additive per D-08)

    /// Typed DTO for a single FormID database lookup result.
    ///
    /// C++ callers should check `found` before using `value`. An uninitialized
    /// pool, a cache miss, or a DB error all produce `found: false` with an
    /// empty `value`. The `formid` and `plugin` fields echo the input so
    /// callers do not have to track the input separately in batch scenarios.
    struct FormIdEntryDto {
        formid: String,
        plugin: String,
        value: String,
        found: bool,
    }

    extern "Rust" {
        type DbPool;

        fn db_pool_new(game_table: &str, max_connections: u32, cache_ttl_secs: u64) -> Box<DbPool>;
        fn db_pool_initialize(pool: &DbPool, db_paths: &[String]) -> Result<()>;
        fn db_pool_get_entry(pool: &DbPool, formid: &str, plugin: &str) -> String;
        fn db_pool_get_entries_batch(
            pool: &DbPool,
            formids: &[String],
            plugins: &[String],
        ) -> Vec<String>;
        fn db_pool_is_available(pool: &DbPool) -> bool;
        fn db_pool_cache_size(pool: &DbPool) -> usize;
        fn db_pool_clear_cache(pool: &DbPool, expired_only: bool) -> usize;
        fn db_pool_close(pool: &DbPool) -> Result<()>;
        fn db_pool_game_table(pool: &DbPool) -> String;

        // CXXS-05: Typed FormID accessors (additive per D-08)
        fn db_pool_get_entry_typed(
            pool: &DbPool,
            formid: &str,
            plugin: &str,
        ) -> FormIdEntryDto;
        fn db_pool_get_entries_batch_typed(
            pool: &DbPool,
            formids: &[String],
            plugins: &[String],
        ) -> Vec<FormIdEntryDto>;
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

    // ── CXXS-05 typed FormID lookup tests ──────────────────────────────

    #[test]
    fn test_db_pool_get_entry_typed_uninitialized_returns_not_found() {
        let pool = db_pool_new("Fallout4", 4, 60);
        let result = db_pool_get_entry_typed(&pool, "0x000ABCDE", "Fallout4.esm");
        assert!(!result.found, "uninitialized pool should return found: false");
        assert_eq!(result.formid, "0x000ABCDE", "formid must be echoed back");
        assert_eq!(result.plugin, "Fallout4.esm", "plugin must be echoed back");
        assert!(result.value.is_empty(), "value should be empty on miss");
    }

    #[test]
    fn test_db_pool_get_entries_batch_typed_empty_returns_empty() {
        let pool = db_pool_new("Fallout4", 4, 60);
        let result = db_pool_get_entries_batch_typed(&pool, &[], &[]);
        assert!(result.is_empty(), "empty input must return empty Vec");
    }

    #[test]
    fn test_db_pool_get_entries_batch_typed_length_mismatch_returns_empty() {
        let pool = db_pool_new("Fallout4", 4, 60);
        // formids has 1 entry, plugins has 0 — length mismatch → fail-soft
        let result = db_pool_get_entries_batch_typed(
            &pool,
            &["0x000ABCDE".to_string()],
            &[],
        );
        assert!(result.is_empty(), "length mismatch must return empty Vec (fail-soft)");
    }

    #[test]
    fn test_db_pool_get_entries_batch_typed_positional_repackaging() {
        // Positional repackaging contract: result[i] corresponds to (formids[i], plugins[i]).
        // On an uninitialized pool all entries are misses, but the positional mapping must hold.
        let pool = db_pool_new("Fallout4", 4, 60);
        let result = db_pool_get_entries_batch_typed(
            &pool,
            &["0x000ABCDE".to_string(), "0x000FEDCB".to_string()],
            &["Fallout4.esm".to_string(), "DLC01.esm".to_string()],
        );
        assert_eq!(result.len(), 2, "one DTO per input pair (positional repackaging)");
        assert_eq!(result[0].formid, "0x000ABCDE");
        assert_eq!(result[0].plugin, "Fallout4.esm");
        assert!(!result[0].found);
        assert_eq!(result[1].formid, "0x000FEDCB");
        assert_eq!(result[1].plugin, "DLC01.esm");
        assert!(!result[1].found);
    }

    #[test]
    fn test_db_pool_get_entry_still_works_d08_regression() {
        // D-08 regression: existing fn must remain unchanged
        let pool = db_pool_new("Fallout4", 4, 300);
        let entry = db_pool_get_entry(&pool, "00000001", "Fallout4.esm");
        assert!(entry.is_empty(), "db_pool_get_entry must still return empty string on miss (D-08)");
    }

    #[test]
    fn test_db_pool_get_entries_batch_still_works_d08_regression() {
        // D-08 regression: existing fn must remain unchanged
        let pool = db_pool_new("Fallout4", 4, 300);
        let result = db_pool_get_entries_batch(
            &pool,
            &["00000001".to_string()],
            &["Fallout4.esm".to_string()],
        );
        // On uninitialized pool returns empty Vec (no tab-delimited hit entries)
        assert!(result.is_empty(), "db_pool_get_entries_batch must still work (D-08)");
    }
}
