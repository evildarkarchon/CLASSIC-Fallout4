use super::*;
use tempfile::NamedTempFile;

// =========================================================================
// Test Helper Functions
// =========================================================================

/// Create a temporary SQLite database with test table and sample data.
///
/// Returns the temp file handle (which keeps the file alive) and the path.
async fn create_test_database(
    table_name: &str,
    entries: &[(&str, &str, &str)], // (formid, plugin, entry)
) -> Result<(NamedTempFile, PathBuf), DatabaseError> {
    let temp_file = NamedTempFile::with_suffix(".db").map_err(DatabaseError::IoError)?;
    let db_path = temp_file.path().to_path_buf();

    // Create database with test table
    let conn_str = format!("sqlite://{}?mode=rwc", db_path.display());
    let pool = SqlitePoolOptions::new()
        .max_connections(1)
        .connect(&conn_str)
        .await
        .map_err(|e| DatabaseError::OpenError(e.to_string()))?;

    // Create table
    let create_table_sql = format!(
        "CREATE TABLE IF NOT EXISTS {} (
            formid TEXT NOT NULL,
            plugin TEXT NOT NULL,
            entry TEXT NOT NULL,
            PRIMARY KEY (formid, plugin)
        )",
        table_name
    );
    sqlx::query(&create_table_sql)
        .execute(&pool)
        .await
        .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

    // Insert test data
    for (formid, plugin, entry) in entries {
        let insert_sql = format!(
            "INSERT OR REPLACE INTO {} (formid, plugin, entry) VALUES (?, ?, ?)",
            table_name
        );
        sqlx::query(&insert_sql)
            .bind(*formid)
            .bind(*plugin)
            .bind(*entry)
            .execute(&pool)
            .await
            .map_err(|e| DatabaseError::QueryError(e.to_string()))?;
    }

    pool.close().await;
    Ok((temp_file, db_path))
}

// =========================================================================
// Pool Lifecycle Tests
// =========================================================================

/// Test that Arc::strong_count correctly tracks clones of DatabasePool.
///
/// This validates the Drop implementation's clone-safety logic:
/// - When multiple clones exist, dropping one should not trigger the warning
/// - Only when the last reference is dropped should the warning fire
#[test]
fn test_database_pool_clone_arc_count() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestGame".to_string());

    // Initially, strong count should be 1
    assert_eq!(
        Arc::strong_count(&pool.pools),
        1,
        "Initial pool should have strong_count of 1"
    );

    // After cloning, strong count should be 2
    let clone1 = pool.clone();
    assert_eq!(
        Arc::strong_count(&pool.pools),
        2,
        "After cloning, strong_count should be 2"
    );

    // Both references point to the same Arc
    assert!(
        Arc::ptr_eq(&pool.pools, &clone1.pools),
        "Clones should share the same underlying Arc"
    );

    // After another clone, strong count should be 3
    let clone2 = pool.clone();
    assert_eq!(
        Arc::strong_count(&pool.pools),
        3,
        "After second clone, strong_count should be 3"
    );

    // Drop one clone - strong count should decrease to 2
    drop(clone1);
    assert_eq!(
        Arc::strong_count(&pool.pools),
        2,
        "After dropping one clone, strong_count should be 2"
    );

    // The warning condition should be false when other clones exist
    // (strong_count > 1, so condition is false regardless of pools.is_empty())
    assert!(
        Arc::strong_count(&pool.pools) > 1,
        "With remaining clones, strong_count should be > 1"
    );

    // Drop another clone - strong count should decrease to 1
    drop(clone2);
    assert_eq!(
        Arc::strong_count(&pool.pools),
        1,
        "After dropping all clones, strong_count should be 1"
    );
}

/// Test that the warning condition is correctly evaluated.
///
/// The warning should only fire when:
/// 1. This is the last Arc reference (strong_count == 1)
/// 2. AND pools are not empty
#[test]
fn test_drop_warning_condition_logic() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestGame".to_string());

    // With no pools initialized, the warning condition should be false
    // even when this is the last reference
    let should_warn_empty = Arc::strong_count(&pool.pools) == 1 && !pool.pools.is_empty();
    assert!(
        !should_warn_empty,
        "Should not warn when pools are empty (even if last reference)"
    );

    // Clone and verify warning condition is false for non-last references
    let clone = pool.clone();
    let should_warn_with_clone = Arc::strong_count(&pool.pools) == 1 && !pool.pools.is_empty();
    assert!(
        !should_warn_with_clone,
        "Should not warn when other clones exist"
    );

    // Drop the clone
    drop(clone);

    // Now it's the last reference, but pools are still empty
    let should_warn_last_empty = Arc::strong_count(&pool.pools) == 1 && !pool.pools.is_empty();
    assert!(
        !should_warn_last_empty,
        "Should not warn when pools are empty"
    );

    // Note: We can't easily test the case where pools are non-empty without
    // actually connecting to a database, but the logic is validated above.
}

/// Test pool creation with default max connections.
#[test]
fn test_pool_creation_default_connections() {
    let pool = DatabasePool::new(None, Duration::from_secs(300), "Fallout4".to_string());

    // Should use calculated max connections (based on CPU cores)
    let max_conn = pool.get_max_connections();
    assert!(max_conn.is_some(), "max_connections should be set");
    let value = max_conn.unwrap();
    assert!(
        (8..=64).contains(&value),
        "max_connections should be clamped between 8 and 64, got {}",
        value
    );
}

/// Test pool creation with custom max connections.
#[test]
fn test_pool_creation_custom_connections() {
    let pool = DatabasePool::new(Some(16), Duration::from_secs(600), "Skyrim".to_string());

    assert_eq!(pool.get_max_connections(), Some(16));
    assert_eq!(pool.get_game_table(), "Skyrim");
}

/// Test pool creation with in-memory cache initialization.
#[test]
fn test_pool_creation_cache_initialized() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestGame".to_string());

    // Cache should be empty initially
    assert_eq!(pool.cache_size(), 0, "Cache should be empty on creation");
    assert!(
        !pool.is_available(),
        "Pool should have no connections initially"
    );
}

/// Test pool initialization with valid database file.
#[tokio::test]
async fn test_pool_initialization_with_file() {
    let table_name = "TestTable";
    let entries = [("12345678", "TestPlugin.esp", "Test Entry")];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
    let result = pool.initialize(vec![db_path]).await;

    assert!(
        result.is_ok(),
        "Initialization should succeed: {:?}",
        result.err()
    );
    assert!(
        pool.is_available(),
        "Pool should be available after initialization"
    );
}

/// Test pool statistics tracking.
#[tokio::test]
async fn test_pool_statistics_tracking() {
    let table_name = "StatsTable";
    let entries = [("AABBCCDD", "Stats.esp", "Stats Entry")];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    // Initial stats
    let stats = pool.get_stats().unwrap();
    assert_eq!(stats.total_queries, 0, "Initial queries should be 0");
    assert_eq!(stats.cache_hits, 0, "Initial cache hits should be 0");
    assert_eq!(stats.cache_misses, 0, "Initial cache misses should be 0");
    assert_eq!(stats.cache_evictions, 0, "Initial evictions should be 0");
    assert_eq!(stats.cleanup_runs, 0, "Initial cleanup runs should be 0");
    assert_eq!(
        stats.cleanup_removed, 0,
        "Initial cleanup removed should be 0"
    );
    assert_eq!(stats.cleanup_elapsed_total_ns, 0);
    assert_eq!(stats.cleanup_elapsed_max_ns, 0);
    assert_eq!(stats.eviction_elapsed_total_ns, 0);
    assert_eq!(stats.eviction_elapsed_max_ns, 0);

    // Perform a query
    let _ = pool.get_entry("AABBCCDD", "Stats.esp", None).await;

    // Stats should be updated
    let stats_after = pool.get_stats().unwrap();
    assert_eq!(stats_after.total_queries, 1, "Should have 1 query");
    assert_eq!(
        stats_after.cache_misses, 1,
        "First query should be a cache miss"
    );
    assert_eq!(stats_after.cache_evictions, 0);
    assert_eq!(stats_after.cleanup_runs, 0);
    assert_eq!(stats_after.cleanup_removed, 0);

    pool.close().await.unwrap();
}

/// Test pool close and cleanup.
#[tokio::test]
async fn test_pool_close_and_cleanup() {
    let table_name = "CloseTable";
    let entries = [("11111111", "Close.esp", "Close Entry")];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    // Add something to cache
    let _ = pool.get_entry("11111111", "Close.esp", None).await;
    assert!(pool.cache_size() > 0, "Cache should have entries");

    // Close the pool
    let result = pool.close().await;
    assert!(result.is_ok(), "Close should succeed");
    assert!(
        !pool.is_available(),
        "Pool should not be available after close"
    );
    assert_eq!(pool.cache_size(), 0, "Cache should be cleared after close");
}

/// Test max connections recalculation.
#[test]
fn test_recalculate_max_connections() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestGame".to_string());
    assert_eq!(pool.get_max_connections(), Some(4));

    pool.recalculate_max_connections();

    let new_max = pool.get_max_connections().unwrap();
    // Should be recalculated based on CPU cores (clamped 8-64)
    assert!(
        (8..=64).contains(&new_max),
        "Recalculated max should be clamped"
    );
}

/// Test set_max_connections updates the value.
#[test]
fn test_set_max_connections() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestGame".to_string());
    assert_eq!(pool.get_max_connections(), Some(4));

    pool.set_max_connections(32);
    assert_eq!(pool.get_max_connections(), Some(32));
}

/// Test global budget distribution with deterministic split.
#[tokio::test]
async fn test_global_budget_distribution_multi_db() {
    let table_name = "BudgetTable";
    let entries = [("BUDGET01", "Budget.esp", "Budget Entry")];
    let (_temp_file1, db_path1) = create_test_database(table_name, &entries).await.unwrap();
    let (_temp_file2, db_path2) = create_test_database(table_name, &entries).await.unwrap();
    let (_temp_file3, db_path3) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(8), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path1, db_path2, db_path3])
        .await
        .unwrap();

    let stats = pool.get_stats().unwrap();
    assert_eq!(stats.configured_connection_budget, 8);
    assert_eq!(stats.effective_connection_budget, 8);
    assert_eq!(stats.active_pool_count, 3);
    assert_eq!(stats.min_pool_allocation, 2);
    assert_eq!(stats.max_pool_allocation, 3);
    assert_eq!(stats.allocation_spread, 1);
}

/// Test low-budget clamp keeps allocations non-zero per active DB.
#[tokio::test]
async fn test_low_budget_clamp_distribution() {
    let table_name = "LowBudgetTable";
    let entries = [("LOWBUD01", "Budget.esp", "Budget Entry")];
    let (_temp_file1, db_path1) = create_test_database(table_name, &entries).await.unwrap();
    let (_temp_file2, db_path2) = create_test_database(table_name, &entries).await.unwrap();
    let (_temp_file3, db_path3) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(2), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path1, db_path2, db_path3])
        .await
        .unwrap();

    let stats = pool.get_stats().unwrap();
    assert_eq!(stats.configured_connection_budget, 2);
    assert_eq!(stats.effective_connection_budget, 3);
    assert_eq!(stats.active_pool_count, 3);
    assert_eq!(stats.min_pool_allocation, 1);
    assert_eq!(stats.max_pool_allocation, 1);
    assert_eq!(stats.allocation_spread, 0);
}

/// Test set_max_connections is config-only until explicit rebalance.
#[tokio::test]
async fn test_set_max_connections_requires_explicit_rebalance() {
    let table_name = "RebalanceTable";
    let entries = [("REBAL001", "Budget.esp", "Budget Entry")];
    let (_temp_file1, db_path1) = create_test_database(table_name, &entries).await.unwrap();
    let (_temp_file2, db_path2) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(6), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path1, db_path2]).await.unwrap();

    let before = pool.get_stats().unwrap();
    assert_eq!(before.effective_connection_budget, 6);
    assert_eq!(before.min_pool_allocation, 3);
    assert_eq!(before.max_pool_allocation, 3);

    pool.set_max_connections(10);
    let after_set_only = pool.get_stats().unwrap();
    assert_eq!(
        after_set_only.effective_connection_budget, 6,
        "set_max_connections should not immediately rebuild active pools"
    );
    assert_eq!(after_set_only.min_pool_allocation, 3);
    assert_eq!(after_set_only.max_pool_allocation, 3);

    pool.rebalance_connections().await.unwrap();
    let after_rebalance = pool.get_stats().unwrap();
    assert_eq!(after_rebalance.configured_connection_budget, 10);
    assert_eq!(after_rebalance.effective_connection_budget, 10);
    assert_eq!(after_rebalance.min_pool_allocation, 5);
    assert_eq!(after_rebalance.max_pool_allocation, 5);
}

// =========================================================================
// Caching Tests
// =========================================================================

/// Test CacheEntry creation and expiration.
#[test]
fn test_cache_entry_creation() {
    let entry = CacheEntry::new("test_value".to_string(), Duration::from_secs(60));
    assert_eq!(entry.value, "test_value");
    assert!(!entry.is_expired(), "Fresh entry should not be expired");
}

/// Test CacheEntry expiration after TTL.
#[test]
fn test_cache_entry_expiration() {
    // Create entry with very short TTL
    let entry = CacheEntry::new("test_value".to_string(), Duration::from_millis(1));

    // Wait for expiration
    std::thread::sleep(Duration::from_millis(10));

    assert!(entry.is_expired(), "Entry should be expired after TTL");
}

/// Test CacheKey creation and hashing.
#[test]
fn test_cache_key_creation() {
    let key = CacheKey::new("Fallout4", "12345678", "TestMod.esp");

    assert_eq!(key.game_table, "Fallout4");
    assert_eq!(key.formid, "12345678");
    assert_eq!(key.plugin, "testmod.esp"); // Should be lowercase
}

/// Test CacheKey case-insensitive plugin matching.
#[test]
fn test_cache_key_case_insensitive_plugin() {
    let key1 = CacheKey::new("Fallout4", "12345678", "TestMod.ESP");
    let key2 = CacheKey::new("Fallout4", "12345678", "testmod.esp");
    let key3 = CacheKey::new("Fallout4", "12345678", "TESTMOD.ESP");

    // All should have same plugin (lowercase)
    assert_eq!(key1.plugin, key2.plugin);
    assert_eq!(key2.plugin, key3.plugin);

    // All should have same hash
    assert_eq!(key1.hash, key2.hash);
    assert_eq!(key2.hash, key3.hash);

    // Fully equivalent keys should compare equal
    assert_eq!(key1, key2);
    assert_eq!(key2, key3);
}

/// Test CacheKey distinctness for non-equivalent components.
#[test]
fn test_cache_key_distinct_components_are_not_equal() {
    let base = CacheKey::new("Fallout4", "12345678", "TestMod.esp");
    let different_table = CacheKey::new("Skyrim", "12345678", "TestMod.esp");
    let different_formid = CacheKey::new("Fallout4", "87654321", "TestMod.esp");
    let different_plugin = CacheKey::new("Fallout4", "12345678", "OtherMod.esp");

    assert_ne!(base, different_table);
    assert_ne!(base, different_formid);
    assert_ne!(base, different_plugin);
}

/// Test cache hit on second lookup.
#[tokio::test]
async fn test_cache_hit_on_second_lookup() {
    let table_name = "CacheHitTable";
    let entries = [("DEADBEEF", "CacheTest.esp", "Cache Test Entry")];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    // First lookup - cache miss
    let result1 = pool
        .get_entry("DEADBEEF", "CacheTest.esp", None)
        .await
        .unwrap();
    assert_eq!(result1, Some("Cache Test Entry".to_string()));

    let stats1 = pool.get_stats().unwrap();
    assert_eq!(stats1.cache_misses, 1);
    assert_eq!(stats1.cache_hits, 0);

    // Second lookup - cache hit
    let result2 = pool
        .get_entry("DEADBEEF", "CacheTest.esp", None)
        .await
        .unwrap();
    assert_eq!(result2, Some("Cache Test Entry".to_string()));

    let stats2 = pool.get_stats().unwrap();
    assert_eq!(stats2.cache_hits, 1);

    pool.close().await.unwrap();
}

/// Verify equivalent hit/miss behavior between single and batch lookups.
#[tokio::test]
async fn test_single_and_batch_cache_hit_miss_parity() {
    let table_name = "SingleBatchParityTable";
    let entries = [("PARITY01", "ParityCase.esp", "Parity Value")];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    let single_pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
    single_pool.initialize(vec![db_path.clone()]).await.unwrap();
    assert_eq!(
        single_pool
            .get_entry("PARITY01", "ParityCase.esp", None)
            .await
            .unwrap(),
        Some("Parity Value".to_string())
    );
    assert_eq!(
        single_pool
            .get_entry("PARITY01", "PARITYCASE.ESP", None)
            .await
            .unwrap(),
        Some("Parity Value".to_string())
    );

    let single_stats = single_pool.get_stats().unwrap();
    assert_eq!(single_stats.cache_misses, 1);
    assert_eq!(single_stats.cache_hits, 1);
    single_pool.close().await.unwrap();

    let batch_pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
    batch_pool.initialize(vec![db_path]).await.unwrap();

    let first_batch = batch_pool
        .get_entries_batch(
            vec![("PARITY01".to_string(), "ParityCase.esp".to_string())],
            None,
            100,
        )
        .await
        .unwrap();
    assert_eq!(
        first_batch.get("PARITY01:ParityCase.esp"),
        Some(&"Parity Value".to_string())
    );

    let second_batch = batch_pool
        .get_entries_batch(
            vec![("PARITY01".to_string(), "PARITYCASE.ESP".to_string())],
            None,
            100,
        )
        .await
        .unwrap();
    assert_eq!(
        second_batch.get("PARITY01:PARITYCASE.ESP"),
        Some(&"Parity Value".to_string())
    );

    let batch_stats = batch_pool.get_stats().unwrap();
    assert_eq!(batch_stats.cache_misses, 1);
    assert_eq!(batch_stats.cache_hits, 1);
    batch_pool.close().await.unwrap();
}

/// Test cache clear with expired_only=false.
#[tokio::test]
async fn test_cache_clear_all() {
    let table_name = "ClearAllTable";
    let entries = [
        ("00000001", "Test1.esp", "Entry 1"),
        ("00000002", "Test2.esp", "Entry 2"),
    ];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    // Populate cache
    let _ = pool.get_entry("00000001", "Test1.esp", None).await;
    let _ = pool.get_entry("00000002", "Test2.esp", None).await;
    assert!(pool.cache_size() >= 2, "Cache should have entries");

    // Clear all
    let removed = pool.clear_cache(false);
    assert!(removed >= 2, "Should have removed at least 2 entries");
    assert_eq!(pool.cache_size(), 0, "Cache should be empty");

    pool.close().await.unwrap();
}

/// Test cache clear with expired_only=true.
#[tokio::test]
async fn test_cache_clear_expired_only() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(300), "TestTable".to_string());

    // Manually insert entries with different TTLs
    let expired_key = CacheKey::new("TestTable", "expired", "plugin");
    let fresh_key = CacheKey::new("TestTable", "fresh", "plugin");

    pool.query_cache.insert(
        expired_key,
        CacheEntry::new("expired_value".to_string(), Duration::from_millis(1)),
    );
    pool.query_cache.insert(
        fresh_key.clone(),
        CacheEntry::new("fresh_value".to_string(), Duration::from_secs(300)),
    );

    // Wait for expiration
    std::thread::sleep(Duration::from_millis(10));

    assert_eq!(pool.cache_size(), 2, "Should have 2 entries before clear");

    // Clear expired only
    let removed = pool.clear_cache(true);
    assert_eq!(removed, 1, "Should have removed 1 expired entry");
    assert_eq!(pool.cache_size(), 1, "Should have 1 entry remaining");

    // Verify fresh entry is still there
    assert!(
        pool.query_cache.contains_key(&fresh_key),
        "Fresh entry should remain"
    );
}

/// Test set_cache_ttl updates TTL for new entries.
#[tokio::test]
async fn test_set_cache_ttl() {
    let table_name = "TtlTable";
    let entries = [("TTLTEST1", "Ttl.esp", "TTL Entry")];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    // Change TTL to very short
    pool.set_cache_ttl(Duration::from_millis(10));
    assert_eq!(
        pool.get_cache_ttl(),
        Duration::from_millis(10),
        "get_cache_ttl should reflect updated value"
    );

    // Lookup to populate cache
    let _ = pool.get_entry("TTLTEST1", "Ttl.esp", None).await;
    assert_eq!(pool.cache_size(), 1);

    // Wait for expiration
    std::thread::sleep(Duration::from_millis(20));

    // Clear expired
    let removed = pool.clear_cache(true);
    assert_eq!(removed, 1, "Entry should have expired with new TTL");

    pool.close().await.unwrap();
}

/// Test deterministic eviction order when cache exceeds capacity.
#[test]
fn test_cache_eviction_deterministic_oldest_first() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(300), "TestTable".to_string());
    pool.set_cache_capacity(2);

    pool.insert_with_eviction(
        CacheKey::new("TestTable", "00000001", "plugin.esp"),
        "Entry 1".to_string(),
        Duration::from_secs(300),
    );
    pool.insert_with_eviction(
        CacheKey::new("TestTable", "00000002", "plugin.esp"),
        "Entry 2".to_string(),
        Duration::from_secs(300),
    );
    pool.insert_with_eviction(
        CacheKey::new("TestTable", "00000003", "plugin.esp"),
        "Entry 3".to_string(),
        Duration::from_secs(300),
    );

    assert_eq!(
        pool.cache_size(),
        2,
        "Cache size must respect configured cap"
    );
    assert!(
        !pool
            .query_cache
            .contains_key(&CacheKey::new("TestTable", "00000001", "plugin.esp")),
        "Oldest key should be evicted first"
    );
    assert!(
        pool.query_cache
            .contains_key(&CacheKey::new("TestTable", "00000002", "plugin.esp"))
    );
    assert!(
        pool.query_cache
            .contains_key(&CacheKey::new("TestTable", "00000003", "plugin.esp"))
    );

    let stats = pool.get_stats().unwrap();
    assert_eq!(stats.cache_evictions, 1, "Should record one eviction");
}

/// Test capacity bound enforcement under sustained inserts.
#[tokio::test]
async fn test_cache_capacity_bound_under_sustained_inserts() {
    let table_name = "CapacityTable";
    let entries: Vec<_> = (0..20)
        .map(|i| {
            (
                format!("CAP{:06}", i),
                "Cap.esp".to_string(),
                format!("Entry {}", i),
            )
        })
        .collect();
    let entries_refs: Vec<(&str, &str, &str)> = entries
        .iter()
        .map(|(a, b, c)| (a.as_str(), b.as_str(), c.as_str()))
        .collect();
    let (_temp_file, db_path) = create_test_database(table_name, &entries_refs)
        .await
        .unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
    pool.set_cache_capacity(5);
    pool.initialize(vec![db_path]).await.unwrap();

    for (formid, plugin, _) in &entries {
        let _ = pool.get_entry(formid, plugin, None).await.unwrap();
    }

    assert!(
        pool.cache_size() <= 5,
        "Cache should stay within configured capacity"
    );

    let stats = pool.get_stats().unwrap();
    assert!(
        stats.cache_evictions >= 15,
        "Eviction count should increase under sustained inserts"
    );

    pool.close().await.unwrap();
}

/// Test hybrid proactive cleanup trigger uses threshold and interval gate.
#[test]
fn test_hybrid_proactive_cleanup_threshold_and_interval() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(300), "TestTable".to_string());
    pool.set_cache_cleanup_threshold(3);
    pool.set_cache_cleanup_interval(Duration::from_secs(1));

    pool.query_cache.insert(
        CacheKey::new("TestTable", "expired1", "plugin"),
        CacheEntry::new("expired1".to_string(), Duration::from_millis(1)),
    );
    pool.query_cache.insert(
        CacheKey::new("TestTable", "expired2", "plugin"),
        CacheEntry::new("expired2".to_string(), Duration::from_millis(1)),
    );
    std::thread::sleep(Duration::from_millis(10));

    // Below threshold: should not run.
    pool.maybe_run_proactive_cleanup(2);
    let stats_before = pool.get_stats().unwrap();
    assert_eq!(stats_before.cleanup_runs, 0);

    // Meets threshold but interval gate has not elapsed yet.
    pool.maybe_run_proactive_cleanup(1);
    let stats_interval_blocked = pool.get_stats().unwrap();
    assert_eq!(stats_interval_blocked.cleanup_runs, 0);

    // Once interval elapsed, cleanup should execute and remove expired entries.
    std::thread::sleep(Duration::from_millis(1_100));
    pool.maybe_run_proactive_cleanup(1);
    let stats_after = pool.get_stats().unwrap();
    assert_eq!(stats_after.cleanup_runs, 1);
    assert!(
        stats_after.cleanup_removed >= 2,
        "Cleanup should remove expired entries"
    );
    assert!(
        stats_after.cleanup_elapsed_total_ns > 0,
        "Cleanup timing should be recorded when proactive cleanup runs"
    );
    assert!(
        stats_after.cleanup_elapsed_max_ns > 0,
        "Cleanup max timing should be recorded when proactive cleanup runs"
    );
}

// =========================================================================
// Query Tests
// =========================================================================

/// Test get_entry returns correct value for existing FormID.
#[tokio::test]
async fn test_formid_lookup_hit() {
    let table_name = "LookupTable";
    let entries = [(
        "ABCD1234",
        "TestMod.esp",
        "This is a test entry for FormID lookup",
    )];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    let result = pool
        .get_entry("ABCD1234", "TestMod.esp", None)
        .await
        .unwrap();
    assert_eq!(
        result,
        Some("This is a test entry for FormID lookup".to_string())
    );

    pool.close().await.unwrap();
}

/// Test get_entry returns None for non-existent FormID.
#[tokio::test]
async fn test_formid_lookup_miss() {
    let table_name = "MissTable";
    let entries = [("11111111", "Existing.esp", "Existing Entry")];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    let result = pool
        .get_entry("99999999", "NonExistent.esp", None)
        .await
        .unwrap();
    assert_eq!(result, None);

    pool.close().await.unwrap();
}

/// Test get_entry with table override.
#[tokio::test]
async fn test_get_entry_with_table_override() {
    let table_name = "OverrideTable";
    let entries = [("OVERRIDE1", "Override.esp", "Override Entry")];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    // Create pool with different default table
    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "WrongTable".to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    // Use table override to query correct table
    let result = pool
        .get_entry("OVERRIDE1", "Override.esp", Some(table_name))
        .await
        .unwrap();
    assert_eq!(result, Some("Override Entry".to_string()));

    pool.close().await.unwrap();
}

/// Test batch FormID query.
#[tokio::test]
async fn test_batch_formid_query() {
    let table_name = "BatchTable";
    let entries = [
        ("BATCH001", "Batch.esp", "Entry 1"),
        ("BATCH002", "Batch.esp", "Entry 2"),
        ("BATCH003", "Batch.esp", "Entry 3"),
        ("BATCH004", "OtherMod.esp", "Entry 4"),
    ];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    let pairs = vec![
        ("BATCH001".to_string(), "Batch.esp".to_string()),
        ("BATCH002".to_string(), "Batch.esp".to_string()),
        ("BATCH003".to_string(), "Batch.esp".to_string()),
        ("BATCH004".to_string(), "OtherMod.esp".to_string()),
        ("NOTEXIST".to_string(), "Missing.esp".to_string()),
    ];

    let results = pool.get_entries_batch(pairs, None, 100).await.unwrap();

    assert_eq!(results.len(), 4, "Should find 4 entries");
    assert_eq!(
        results.get("BATCH001:Batch.esp"),
        Some(&"Entry 1".to_string())
    );
    assert_eq!(
        results.get("BATCH002:Batch.esp"),
        Some(&"Entry 2".to_string())
    );
    assert_eq!(
        results.get("BATCH003:Batch.esp"),
        Some(&"Entry 3".to_string())
    );
    assert_eq!(
        results.get("BATCH004:OtherMod.esp"),
        Some(&"Entry 4".to_string())
    );
    assert_eq!(results.get("NOTEXIST:Missing.esp"), None);

    pool.close().await.unwrap();
}

/// Test batch query with case-insensitive plugin matching.
#[tokio::test]
async fn test_batch_query_case_insensitive_plugin() {
    let table_name = "CaseTable";
    let entries = [("CASE0001", "TestMod.esp", "Case Test Entry")];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    // Query with different case
    let pairs = vec![("CASE0001".to_string(), "TESTMOD.ESP".to_string())];

    let results = pool.get_entries_batch(pairs, None, 100).await.unwrap();

    // Should find entry despite case difference
    assert_eq!(results.len(), 1, "Should find entry with different case");
    assert_eq!(
        results.get("CASE0001:TESTMOD.ESP"),
        Some(&"Case Test Entry".to_string())
    );

    pool.close().await.unwrap();
}

/// Test batch query with empty input.
#[tokio::test]
async fn test_batch_query_empty_input() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestTable".to_string());

    let results = pool.get_entries_batch(vec![], None, 100).await.unwrap();
    assert!(
        results.is_empty(),
        "Empty input should return empty results"
    );
}

/// Test batch query adaptive batch sizing.
#[tokio::test]
async fn test_batch_query_adaptive_sizing() {
    let table_name = "AdaptiveTable";
    let mut entries = Vec::new();
    for i in 0..10 {
        entries.push((
            format!("ADAPT{:03}", i),
            "Adaptive.esp".to_string(),
            format!("Entry {}", i),
        ));
    }

    let entries_refs: Vec<(&str, &str, &str)> = entries
        .iter()
        .map(|(a, b, c)| (a.as_str(), b.as_str(), c.as_str()))
        .collect();
    let (_temp_file, db_path) = create_test_database(table_name, &entries_refs)
        .await
        .unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    // Small batch - should use adaptive sizing
    let pairs: Vec<(String, String)> = entries
        .iter()
        .map(|(f, p, _)| (f.clone(), p.clone()))
        .collect();

    let results = pool.get_entries_batch(pairs, None, 100).await.unwrap();
    assert_eq!(results.len(), 10, "Should find all 10 entries");

    pool.close().await.unwrap();
}

/// Test stable-shape padding for partial/final chunks.
#[tokio::test]
async fn test_batch_query_partial_final_chunk_padding_stats() {
    let table_name = "StablePaddingTable";
    let entries: Vec<_> = (0..17)
        .map(|i| {
            (
                format!("PAD{:04}", i),
                "Stable.esp".to_string(),
                format!("Stable Entry {}", i),
            )
        })
        .collect();
    let entries_refs: Vec<(&str, &str, &str)> = entries
        .iter()
        .map(|(a, b, c)| (a.as_str(), b.as_str(), c.as_str()))
        .collect();
    let (_temp_file, db_path) = create_test_database(table_name, &entries_refs)
        .await
        .unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    let pairs: Vec<(String, String)> = entries
        .iter()
        .map(|(formid, plugin, _)| (formid.clone(), plugin.clone()))
        .collect();
    let results = pool.get_entries_batch(pairs, None, 10).await.unwrap();
    assert_eq!(results.len(), 17, "all entries should be returned");

    let stats = pool.get_stats().unwrap();
    assert_eq!(stats.stable_shape_selections, 2);
    assert_eq!(
        stats.stable_shape_bucket_16, 1,
        "first 10-item chunk -> 16 bucket"
    );
    assert_eq!(
        stats.stable_shape_bucket_8, 1,
        "final 7-item chunk -> 8 bucket"
    );
    assert_eq!(
        stats.stable_shape_padding_pairs, 7,
        "10->16 pads 6 plus 7->8 pads 1"
    );

    pool.close().await.unwrap();
}

/// Test mixed hit/miss mapping preserves caller-visible output keys.
#[tokio::test]
async fn test_batch_query_mixed_hit_miss_preserves_output_keys() {
    let table_name = "MixedMappingTable";
    let entries = [("MIX0001", "Mix.esp", "Mixed Entry")];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    let pairs = vec![
        ("MIX0001".to_string(), "MIX.ESP".to_string()),
        ("MIX0001".to_string(), "mix.esp".to_string()),
        ("MISSING".to_string(), "Mix.esp".to_string()),
    ];
    let results = pool.get_entries_batch(pairs, None, 10).await.unwrap();

    assert_eq!(results.len(), 2, "only hit keys should be present");
    assert_eq!(
        results.get("MIX0001:MIX.ESP"),
        Some(&"Mixed Entry".to_string())
    );
    assert_eq!(
        results.get("MIX0001:mix.esp"),
        Some(&"Mixed Entry".to_string())
    );
    assert!(
        !results.contains_key("MISSING:Mix.esp"),
        "miss key should remain absent"
    );

    pool.close().await.unwrap();
}

/// Test UNION ALL query builder.
#[test]
fn test_build_union_all_query() {
    // Empty batch
    let query_empty = DatabasePool::build_union_all_query("TestTable", 0, false);
    assert!(
        query_empty.is_empty(),
        "Empty batch should produce empty query"
    );

    // Single item
    let query_single = DatabasePool::build_union_all_query("Fallout4", 1, false);
    assert!(query_single.contains("SELECT formid, plugin, entry FROM Fallout4"));
    assert!(
        !query_single.contains("UNION ALL"),
        "Single item should not have UNION ALL"
    );
    assert!(
        !query_single.contains("COLLATE nocase"),
        "Exact-case template should not include nocase collation"
    );

    // Multiple items
    let query_multi = DatabasePool::build_union_all_query("Skyrim", 3, true);
    let union_count = query_multi.matches("UNION ALL").count();
    assert_eq!(union_count, 2, "3 items should have 2 UNION ALL clauses");
    assert!(query_multi.contains("SELECT formid, plugin, entry FROM Skyrim"));
    assert!(
        query_multi.contains("COLLATE nocase"),
        "Case-insensitive template should include nocase collation"
    );
}

#[test]
fn test_select_stable_bucket_len_boundaries() {
    assert_eq!(DatabasePool::select_stable_bucket_len(0), 0);
    assert_eq!(DatabasePool::select_stable_bucket_len(7), 8);
    assert_eq!(DatabasePool::select_stable_bucket_len(8), 8);
    assert_eq!(DatabasePool::select_stable_bucket_len(9), 16);
    assert_eq!(DatabasePool::select_stable_bucket_len(15), 16);
    assert_eq!(DatabasePool::select_stable_bucket_len(16), 16);
    assert_eq!(DatabasePool::select_stable_bucket_len(17), 32);
    assert_eq!(DatabasePool::select_stable_bucket_len(31), 32);
    assert_eq!(DatabasePool::select_stable_bucket_len(32), 32);
    assert_eq!(DatabasePool::select_stable_bucket_len(33), 64);
    assert_eq!(DatabasePool::select_stable_bucket_len(63), 64);
    assert_eq!(DatabasePool::select_stable_bucket_len(64), 64);
    assert_eq!(DatabasePool::select_stable_bucket_len(65), 128);
    assert_eq!(DatabasePool::select_stable_bucket_len(127), 128);
    assert_eq!(DatabasePool::select_stable_bucket_len(128), 128);
    assert_eq!(DatabasePool::select_stable_bucket_len(129), 256);
    assert_eq!(DatabasePool::select_stable_bucket_len(255), 256);
    assert_eq!(DatabasePool::select_stable_bucket_len(256), 256);
    assert_eq!(DatabasePool::select_stable_bucket_len(257), 512);
    assert_eq!(DatabasePool::select_stable_bucket_len(511), 512);
    assert_eq!(DatabasePool::select_stable_bucket_len(512), 512);
    assert_eq!(DatabasePool::select_stable_bucket_len(513), 1024);
    assert_eq!(DatabasePool::select_stable_bucket_len(1023), 1024);
    assert_eq!(DatabasePool::select_stable_bucket_len(1024), 1024);
    assert_eq!(DatabasePool::select_stable_bucket_len(1025), 1024);
}

#[test]
fn test_pad_batch_to_bucket_partial_chunk() {
    let batch = vec![
        (
            "PAD0001".to_string(),
            "Pad.esp".to_string(),
            "pad.esp".to_string(),
        ),
        (
            "PAD0002".to_string(),
            "Pad.esp".to_string(),
            "pad.esp".to_string(),
        ),
        (
            "PAD0003".to_string(),
            "Pad.esp".to_string(),
            "pad.esp".to_string(),
        ),
    ];

    let padded = DatabasePool::pad_batch_to_bucket(&batch, 8);
    assert_eq!(padded.len(), 8);
    assert_eq!(padded[0], batch[0]);
    assert_eq!(padded[1], batch[1]);
    assert_eq!(padded[2], batch[2]);
    assert_eq!(
        padded.last(),
        Some(&batch[2]),
        "Padding should duplicate the last real pair"
    );
}

#[test]
fn test_query_template_reuse_by_bucket_and_table() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestTable".to_string());
    let first = pool.get_or_build_stable_query_template("Fallout4", 16, false);
    let second = pool.get_or_build_stable_query_template("Fallout4", 16, false);
    let third = pool.get_or_build_stable_query_template("Skyrim", 16, false);
    let fourth = pool.get_or_build_stable_query_template("Fallout4", 16, true);

    assert_eq!(first, second, "same table + bucket should reuse query text");
    assert_ne!(
        first, third,
        "different table should produce different query text"
    );
    assert_ne!(
        first, fourth,
        "different collation mode should produce different query text"
    );
    assert_eq!(
        pool.query_template_cache.len(),
        3,
        "cache should contain one template per (table, bucket, collation mode)"
    );
}

// =========================================================================
// Error Handling Tests
// =========================================================================

/// Test initialization with missing database file.
#[tokio::test]
async fn test_init_missing_database_file() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestTable".to_string());
    let result = pool
        .initialize(vec![PathBuf::from("/nonexistent/path/database.db")])
        .await;

    // Should succeed but with no pools added (missing file is warned, not errored)
    assert!(result.is_ok(), "Should not error on missing file");
    assert!(
        !pool.is_available(),
        "Pool should not be available with missing file"
    );
}

/// Test get_entry on uninitialized pool.
#[tokio::test]
async fn test_query_on_uninitialized_pool() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestTable".to_string());

    // Query without initialization
    let result = pool.get_entry("12345678", "Test.esp", None).await;

    // Should return Ok(None) - no pools to query
    assert!(result.is_ok(), "Should not error on uninitialized pool");
    assert_eq!(result.unwrap(), None, "Should return None");
}

/// Test query after pool close.
#[tokio::test]
async fn test_query_on_closed_pool() {
    let table_name = "ClosedTable";
    let entries = [("CLOSED01", "Closed.esp", "Closed Entry")];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    // Close the pool
    pool.close().await.unwrap();

    // Query after close - should return None (no pools available)
    let result = pool.get_entry("CLOSED01", "Closed.esp", None).await;
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), None);
}

// =========================================================================
// Game Table Tests
// =========================================================================

/// Test set_game_table and get_game_table.
#[test]
fn test_set_get_game_table() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "Fallout4".to_string());
    assert_eq!(pool.get_game_table(), "Fallout4");

    pool.set_game_table("Skyrim");
    assert_eq!(pool.get_game_table(), "Skyrim");

    pool.set_game_table("FalloutNewVegas");
    assert_eq!(pool.get_game_table(), "FalloutNewVegas");
}

// =========================================================================
// Database Optimization Tests
// =========================================================================

/// Test optimize on database.
#[tokio::test]
async fn test_database_optimize() {
    let table_name = "OptTable";
    let entries = [("OPT00001", "Optimize.esp", "Optimize Entry")];
    let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path]).await.unwrap();

    // Optimize should succeed (runs ANALYZE)
    let result = pool.optimize().await;
    assert!(
        result.is_ok(),
        "Optimize should succeed: {:?}",
        result.err()
    );

    pool.close().await.unwrap();
}

// =========================================================================
// TTL Constants Tests
// =========================================================================

/// Test TTL constant values.
#[test]
fn test_ttl_constants() {
    assert_eq!(
        DEFAULT_CACHE_TTL_SECS, 300,
        "Default TTL should be 5 minutes"
    );
    assert_eq!(BATCH_CACHE_TTL_SECS, 1800, "Batch TTL should be 30 minutes");
    assert_eq!(MAX_CACHE_TTL_SECS, 3600, "Max TTL should be 60 minutes");
    assert_eq!(DEFAULT_QUERY_CACHE_CAPACITY, 20_000);
    assert_eq!(MIN_QUERY_CACHE_CAPACITY, 1);
    assert_eq!(DEFAULT_CACHE_CLEANUP_OP_THRESHOLD, 2048);
    assert_eq!(DEFAULT_CACHE_CLEANUP_INTERVAL_SECS, 30);

    // Verify ordering (compile-time assertions)
    const _: () = assert!(DEFAULT_CACHE_TTL_SECS < BATCH_CACHE_TTL_SECS);
    const _: () = assert!(BATCH_CACHE_TTL_SECS < MAX_CACHE_TTL_SECS);
    const _: () = assert!(MIN_QUERY_CACHE_CAPACITY < DEFAULT_QUERY_CACHE_CAPACITY);
    const _: () = assert!(DEFAULT_QUERY_CACHE_CAPACITY < MAX_QUERY_CACHE_CAPACITY);
    const _: () = assert!(MIN_CACHE_CLEANUP_OP_THRESHOLD < DEFAULT_CACHE_CLEANUP_OP_THRESHOLD);
    const _: () = assert!(DEFAULT_CACHE_CLEANUP_OP_THRESHOLD < MAX_CACHE_CLEANUP_OP_THRESHOLD);
    const _: () = assert!(MIN_CACHE_CLEANUP_INTERVAL_SECS < DEFAULT_CACHE_CLEANUP_INTERVAL_SECS);
    const _: () = assert!(DEFAULT_CACHE_CLEANUP_INTERVAL_SECS < MAX_CACHE_CLEANUP_INTERVAL_SECS);
}

#[test]
fn test_preferred_eviction_target_for_large_capacity() {
    assert_eq!(DatabasePool::preferred_eviction_target(2048), 2048);
    assert_eq!(DatabasePool::preferred_eviction_target(30_000), 28_125);
}

// =========================================================================
// Error Type Tests
// =========================================================================

/// Test DatabaseError variants.
#[test]
fn test_database_error_display() {
    let open_err = DatabaseError::OpenError("connection failed".to_string());
    assert!(open_err.to_string().contains("Failed to open database"));

    let query_err = DatabaseError::QueryError("syntax error".to_string());
    assert!(query_err.to_string().contains("Query execution failed"));

    let not_found = DatabaseError::NotFound("/path/to/db.sqlite".to_string());
    assert!(not_found.to_string().contains("Database file not found"));
}

// =========================================================================
// PoolStatistics Tests
// =========================================================================

/// Test PoolStatistics default values.
#[test]
fn test_pool_statistics_default() {
    let stats = PoolStatistics::default();
    assert_eq!(stats.total_queries, 0);
    assert_eq!(stats.cache_hits, 0);
    assert_eq!(stats.cache_misses, 0);
    assert_eq!(stats.total_connections, 0);
    assert_eq!(stats.active_connections, 0);
    assert_eq!(stats.cache_evictions, 0);
    assert_eq!(stats.cleanup_runs, 0);
    assert_eq!(stats.cleanup_removed, 0);
    assert_eq!(stats.cleanup_elapsed_total_ns, 0);
    assert_eq!(stats.cleanup_elapsed_max_ns, 0);
    assert_eq!(stats.eviction_elapsed_total_ns, 0);
    assert_eq!(stats.eviction_elapsed_max_ns, 0);
    assert_eq!(stats.configured_connection_budget, 0);
    assert_eq!(stats.effective_connection_budget, 0);
    assert_eq!(stats.active_pool_count, 0);
    assert_eq!(stats.min_pool_allocation, 0);
    assert_eq!(stats.max_pool_allocation, 0);
    assert_eq!(stats.allocation_spread, 0);
    assert_eq!(stats.stable_shape_selections, 0);
    assert_eq!(stats.stable_shape_padding_pairs, 0);
    assert_eq!(stats.stable_shape_bucket_8, 0);
    assert_eq!(stats.stable_shape_bucket_16, 0);
    assert_eq!(stats.stable_shape_bucket_32, 0);
    assert_eq!(stats.stable_shape_bucket_64, 0);
    assert_eq!(stats.stable_shape_bucket_128, 0);
    assert_eq!(stats.stable_shape_bucket_256, 0);
    assert_eq!(stats.stable_shape_bucket_512, 0);
    assert_eq!(stats.stable_shape_bucket_1024, 0);
}

/// Test PoolStatistics clone.
#[test]
fn test_pool_statistics_clone() {
    let stats = PoolStatistics {
        total_queries: 100,
        cache_hits: 75,
        cache_evictions: 2,
        ..Default::default()
    };

    let cloned = stats.clone();
    assert_eq!(cloned.total_queries, 100);
    assert_eq!(cloned.cache_hits, 75);
    assert_eq!(cloned.cache_evictions, 2);
}

// =========================================================================
// Multi-Database Tests
// =========================================================================

/// Test querying across multiple database files.
#[tokio::test]
async fn test_multi_database_query() {
    let table_name = "MultiTable";

    // Create first database with some entries
    let entries1 = [
        ("MULTI001", "Multi.esp", "Entry from DB1"),
        ("MULTI002", "Multi.esp", "Entry 2 from DB1"),
    ];
    let (_temp_file1, db_path1) = create_test_database(table_name, &entries1).await.unwrap();

    // Create second database with different entries
    let entries2 = [
        ("MULTI003", "Multi.esp", "Entry from DB2"),
        ("MULTI004", "Multi.esp", "Entry 2 from DB2"),
    ];
    let (_temp_file2, db_path2) = create_test_database(table_name, &entries2).await.unwrap();

    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
    pool.initialize(vec![db_path1, db_path2]).await.unwrap();

    // Should find entries from both databases
    let result1 = pool.get_entry("MULTI001", "Multi.esp", None).await.unwrap();
    assert_eq!(result1, Some("Entry from DB1".to_string()));

    let result2 = pool.get_entry("MULTI003", "Multi.esp", None).await.unwrap();
    assert_eq!(result2, Some("Entry from DB2".to_string()));

    pool.close().await.unwrap();
}
