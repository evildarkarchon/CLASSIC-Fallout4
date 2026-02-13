//! Integration tests for classic-database-core
//!
//! These tests verify cross-component workflows involving database operations,
//! caching, and FormID lookups using real SQLite databases.

use classic_database_core::{DatabaseError, DatabasePool};
use sqlx::sqlite::SqlitePoolOptions;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;
use tempfile::NamedTempFile;

// ============================================================================
// Test Helper Functions
// ============================================================================

/// Create a temporary SQLite database with test data.
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

// ============================================================================
// Complete Workflow Tests
// ============================================================================

mod database_workflows {
    use super::*;

    /// Test complete FormID lookup workflow
    #[tokio::test]
    async fn test_complete_formid_lookup_workflow() {
        let table_name = "WorkflowTable";
        let entries = [
            ("00000001", "Fallout4.esm", "Base Game Record 1"),
            ("00000002", "Fallout4.esm", "Base Game Record 2"),
            ("01000001", "DLCCoast.esm", "Far Harbor Record 1"),
            ("02000001", "TestMod.esp", "Mod Record 1"),
        ];
        let (_temp_file, db_path) = create_test_database(table_name, &entries)
            .await
            .expect("Failed to create test database");

        // Create and initialize pool
        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        pool.initialize(vec![db_path])
            .await
            .expect("Initialize should succeed");

        // Single lookups
        let result1 = pool
            .get_entry("00000001", "Fallout4.esm", None)
            .await
            .expect("Lookup should succeed");
        assert_eq!(result1, Some("Base Game Record 1".to_string()));

        let result2 = pool
            .get_entry("01000001", "DLCCoast.esm", None)
            .await
            .expect("Lookup should succeed");
        assert_eq!(result2, Some("Far Harbor Record 1".to_string()));

        // Missing entry
        let result3 = pool
            .get_entry("FFFFFFFF", "Missing.esp", None)
            .await
            .expect("Lookup should succeed");
        assert_eq!(result3, None);

        // Verify stats
        let stats = pool.get_stats().expect("Stats should be available");
        assert_eq!(stats.total_queries, 3, "Should have 3 total queries");
        assert!(stats.cache_hits > 0 || stats.cache_misses >= 2);

        pool.close().await.expect("Close should succeed");
    }

    /// Test batch lookup workflow
    #[tokio::test]
    async fn test_batch_lookup_workflow() {
        let table_name = "BatchWorkflowTable";
        let entries = [
            ("BATCH001", "Plugin.esp", "Entry 1"),
            ("BATCH002", "Plugin.esp", "Entry 2"),
            ("BATCH003", "Plugin.esp", "Entry 3"),
            ("BATCH004", "Other.esp", "Entry 4"),
            ("BATCH005", "Other.esp", "Entry 5"),
        ];
        let (_temp_file, db_path) = create_test_database(table_name, &entries)
            .await
            .expect("Failed to create test database");

        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        pool.initialize(vec![db_path])
            .await
            .expect("Initialize should succeed");

        // Batch lookup
        let pairs = vec![
            ("BATCH001".to_string(), "Plugin.esp".to_string()),
            ("BATCH002".to_string(), "Plugin.esp".to_string()),
            ("BATCH003".to_string(), "Plugin.esp".to_string()),
            ("BATCH004".to_string(), "Other.esp".to_string()),
            ("NOTEXIST".to_string(), "Missing.esp".to_string()),
        ];

        let results = pool
            .get_entries_batch(pairs, None, 100)
            .await
            .expect("Batch lookup should succeed");

        assert_eq!(results.len(), 4, "Should find 4 entries");
        assert_eq!(
            results.get("BATCH001:Plugin.esp"),
            Some(&"Entry 1".to_string())
        );
        assert_eq!(
            results.get("BATCH004:Other.esp"),
            Some(&"Entry 4".to_string())
        );
        assert!(!results.contains_key("NOTEXIST:Missing.esp"));

        pool.close().await.expect("Close should succeed");
    }

    /// Test game table switching workflow
    #[tokio::test]
    async fn test_game_table_switching_workflow() {
        // Create databases for multiple games
        let fallout_entries = [("F4000001", "Fallout4.esm", "Fallout 4 Entry")];
        let (_temp1, fallout_db) = create_test_database("Fallout4", &fallout_entries)
            .await
            .expect("Failed to create Fallout4 database");

        let skyrim_entries = [("SK000001", "Skyrim.esm", "Skyrim Entry")];
        let (_temp2, skyrim_db) = create_test_database("Skyrim", &skyrim_entries)
            .await
            .expect("Failed to create Skyrim database");

        // Start with Fallout4
        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), "Fallout4".to_string());
        pool.initialize(vec![fallout_db.clone(), skyrim_db.clone()])
            .await
            .expect("Initialize should succeed");

        // Query Fallout4 table
        let result1 = pool
            .get_entry("F4000001", "Fallout4.esm", None)
            .await
            .expect("Lookup should succeed");
        assert_eq!(result1, Some("Fallout 4 Entry".to_string()));

        // Switch to Skyrim
        pool.set_game_table("Skyrim");
        assert_eq!(pool.get_game_table(), "Skyrim");

        // Query Skyrim table
        let result2 = pool
            .get_entry("SK000001", "Skyrim.esm", None)
            .await
            .expect("Lookup should succeed");
        assert_eq!(result2, Some("Skyrim Entry".to_string()));

        pool.close().await.expect("Close should succeed");
    }
}

// ============================================================================
// Cache Workflow Tests
// ============================================================================

mod cache_workflows {
    use super::*;

    /// Test cache hit/miss workflow
    #[tokio::test]
    async fn test_cache_hit_miss_workflow() {
        let table_name = "CacheWorkflowTable";
        let entries = [("CACHE001", "Cache.esp", "Cached Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries)
            .await
            .expect("Failed to create test database");

        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        pool.initialize(vec![db_path])
            .await
            .expect("Initialize should succeed");

        // First query - cache miss
        let _ = pool
            .get_entry("CACHE001", "Cache.esp", None)
            .await
            .expect("Lookup should succeed");
        let stats1 = pool.get_stats().expect("Stats should be available");
        assert_eq!(stats1.cache_misses, 1, "First query should miss cache");
        assert_eq!(stats1.cache_hits, 0, "No cache hits yet");

        // Second query - cache hit
        let _ = pool
            .get_entry("CACHE001", "Cache.esp", None)
            .await
            .expect("Lookup should succeed");
        let stats2 = pool.get_stats().expect("Stats should be available");
        assert_eq!(stats2.cache_hits, 1, "Second query should hit cache");

        pool.close().await.expect("Close should succeed");
    }

    /// Test cache TTL expiration
    #[tokio::test]
    async fn test_cache_ttl_workflow() {
        let table_name = "TtlWorkflowTable";
        let entries = [("TTL00001", "Ttl.esp", "TTL Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries)
            .await
            .expect("Failed to create test database");

        // Create pool with very short TTL
        let pool = DatabasePool::new(
            Some(4),
            Duration::from_millis(50), // 50ms TTL
            table_name.to_string(),
        );
        pool.initialize(vec![db_path])
            .await
            .expect("Initialize should succeed");

        // First query
        let _ = pool
            .get_entry("TTL00001", "Ttl.esp", None)
            .await
            .expect("Lookup should succeed");
        assert_eq!(pool.cache_size(), 1, "Should have 1 cached entry");

        // Wait for expiration
        tokio::time::sleep(Duration::from_millis(100)).await;

        // Clear expired entries
        let removed = pool.clear_cache(true);
        assert_eq!(removed, 1, "Should remove 1 expired entry");
        assert_eq!(pool.cache_size(), 0, "Cache should be empty");

        pool.close().await.expect("Close should succeed");
    }

    /// Test cache clear operations
    #[tokio::test]
    async fn test_cache_clear_workflow() {
        let table_name = "ClearWorkflowTable";
        let entries = [
            ("CLEAR001", "Clear.esp", "Entry 1"),
            ("CLEAR002", "Clear.esp", "Entry 2"),
            ("CLEAR003", "Clear.esp", "Entry 3"),
        ];
        let (_temp_file, db_path) = create_test_database(table_name, &entries)
            .await
            .expect("Failed to create test database");

        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        pool.initialize(vec![db_path])
            .await
            .expect("Initialize should succeed");

        // Populate cache
        for i in 1..=3 {
            let _ = pool
                .get_entry(&format!("CLEAR00{}", i), "Clear.esp", None)
                .await;
        }
        assert!(pool.cache_size() >= 3, "Cache should have entries");

        // Clear all
        let removed = pool.clear_cache(false);
        assert!(removed >= 3, "Should remove at least 3 entries");
        assert_eq!(pool.cache_size(), 0, "Cache should be empty");

        pool.close().await.expect("Close should succeed");
    }
}

// ============================================================================
// Multi-Database Tests
// ============================================================================

mod multi_database {
    use super::*;

    /// Test querying across multiple database files
    #[tokio::test]
    async fn test_multi_database_fallback() {
        let table_name = "MultiDbTable";

        // Database 1 has some entries
        let entries1 = [
            ("MULTI001", "Multi.esp", "From DB1"),
            ("MULTI002", "Multi.esp", "From DB1"),
        ];
        let (_temp1, db1_path) = create_test_database(table_name, &entries1)
            .await
            .expect("Failed to create DB1");

        // Database 2 has different entries
        let entries2 = [
            ("MULTI003", "Multi.esp", "From DB2"),
            ("MULTI004", "Multi.esp", "From DB2"),
        ];
        let (_temp2, db2_path) = create_test_database(table_name, &entries2)
            .await
            .expect("Failed to create DB2");

        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        pool.initialize(vec![db1_path, db2_path])
            .await
            .expect("Initialize should succeed");

        // Should find entries from both databases
        let result1 = pool
            .get_entry("MULTI001", "Multi.esp", None)
            .await
            .expect("Lookup should succeed");
        assert_eq!(result1, Some("From DB1".to_string()));

        let result2 = pool
            .get_entry("MULTI003", "Multi.esp", None)
            .await
            .expect("Lookup should succeed");
        assert_eq!(result2, Some("From DB2".to_string()));

        pool.close().await.expect("Close should succeed");
    }

    /// Test batch query across multiple databases
    #[tokio::test]
    async fn test_multi_database_batch() {
        let table_name = "MultiBatchTable";

        let entries1 = [
            ("MBATCH01", "Plugin.esp", "DB1 Entry 1"),
            ("MBATCH02", "Plugin.esp", "DB1 Entry 2"),
        ];
        let (_temp1, db1_path) = create_test_database(table_name, &entries1)
            .await
            .expect("Failed to create DB1");

        let entries2 = [
            ("MBATCH03", "Plugin.esp", "DB2 Entry 1"),
            ("MBATCH04", "Plugin.esp", "DB2 Entry 2"),
        ];
        let (_temp2, db2_path) = create_test_database(table_name, &entries2)
            .await
            .expect("Failed to create DB2");

        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        pool.initialize(vec![db1_path, db2_path])
            .await
            .expect("Initialize should succeed");

        let pairs = vec![
            ("MBATCH01".to_string(), "Plugin.esp".to_string()),
            ("MBATCH02".to_string(), "Plugin.esp".to_string()),
            ("MBATCH03".to_string(), "Plugin.esp".to_string()),
            ("MBATCH04".to_string(), "Plugin.esp".to_string()),
        ];

        let results = pool
            .get_entries_batch(pairs, None, 100)
            .await
            .expect("Batch lookup should succeed");

        assert_eq!(results.len(), 4, "Should find all 4 entries");

        pool.close().await.expect("Close should succeed");
    }
}

// ============================================================================
// Error Handling Tests
// ============================================================================

mod error_handling {
    use super::*;

    /// Test handling of missing database files
    #[tokio::test]
    async fn test_missing_database_handling() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), "TestTable".to_string());

        // Initialize with nonexistent file - should not error but have no pools
        let result = pool
            .initialize(vec![PathBuf::from("/nonexistent/database.db")])
            .await;
        assert!(result.is_ok(), "Should not error on missing file");
        assert!(!pool.is_available(), "Pool should not be available");
    }

    /// Test query on uninitialized pool
    #[tokio::test]
    async fn test_query_uninitialized_pool() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), "TestTable".to_string());

        let result = pool
            .get_entry("12345678", "Test.esp", None)
            .await
            .expect("Query should not error");
        assert_eq!(result, None, "Should return None on uninitialized pool");
    }

    /// Test query after pool close
    #[tokio::test]
    async fn test_query_after_close() {
        let table_name = "CloseQueryTable";
        let entries = [("CLOSE001", "Close.esp", "Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries)
            .await
            .expect("Failed to create test database");

        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        pool.initialize(vec![db_path])
            .await
            .expect("Initialize should succeed");

        // Close pool
        pool.close().await.expect("Close should succeed");

        // Query after close should return None (no pools available)
        let result = pool
            .get_entry("CLOSE001", "Close.esp", None)
            .await
            .expect("Query should not error");
        assert_eq!(result, None, "Should return None after close");
    }
}

// ============================================================================
// Concurrent Access Tests
// ============================================================================

mod concurrent_access {
    use super::*;

    /// Test concurrent queries from multiple tasks
    #[tokio::test]
    async fn test_concurrent_queries() {
        let table_name = "ConcurrentTable";
        let entries: Vec<_> = (0..10)
            .map(|i| {
                (
                    format!("CONC{:04}", i),
                    "Concurrent.esp".to_string(),
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
            .expect("Failed to create test database");

        let pool = Arc::new(DatabasePool::new(
            Some(8),
            Duration::from_secs(300),
            table_name.to_string(),
        ));
        pool.initialize(vec![db_path])
            .await
            .expect("Initialize should succeed");

        // Spawn multiple concurrent query tasks
        let mut handles = Vec::new();
        for task_id in 0..4 {
            let pool_clone = pool.clone();
            handles.push(tokio::spawn(async move {
                for iteration in 0..10 {
                    let formid = format!("CONC{:04}", (task_id * 10 + iteration) % 10);
                    let result = pool_clone
                        .get_entry(&formid, "Concurrent.esp", None)
                        .await
                        .expect("Query should succeed");
                    assert!(result.is_some(), "Should find entry {}", formid);
                }
            }));
        }

        // Wait for all tasks
        for handle in handles {
            handle.await.expect("Task should complete");
        }

        // Verify stats show all queries
        let stats = pool.get_stats().expect("Stats should be available");
        assert!(stats.total_queries >= 40, "Should have at least 40 queries");

        pool.close().await.expect("Close should succeed");
    }

    /// Test concurrent batch queries
    #[tokio::test]
    async fn test_concurrent_batch_queries() {
        let table_name = "ConcurrentBatchTable";
        let entries: Vec<_> = (0..50)
            .map(|i| {
                (
                    format!("CBATCH{:03}", i),
                    "Batch.esp".to_string(),
                    format!("Batch Entry {}", i),
                )
            })
            .collect();
        let entries_refs: Vec<(&str, &str, &str)> = entries
            .iter()
            .map(|(a, b, c)| (a.as_str(), b.as_str(), c.as_str()))
            .collect();

        let (_temp_file, db_path) = create_test_database(table_name, &entries_refs)
            .await
            .expect("Failed to create test database");

        let pool = Arc::new(DatabasePool::new(
            Some(8),
            Duration::from_secs(300),
            table_name.to_string(),
        ));
        pool.initialize(vec![db_path])
            .await
            .expect("Initialize should succeed");

        // Each task does a batch query
        let mut handles = Vec::new();
        for task_id in 0..4 {
            let pool_clone = pool.clone();
            handles.push(tokio::spawn(async move {
                let pairs: Vec<_> = (0..10)
                    .map(|i| {
                        (
                            format!("CBATCH{:03}", (task_id * 10 + i) % 50),
                            "Batch.esp".to_string(),
                        )
                    })
                    .collect();

                let results = pool_clone
                    .get_entries_batch(pairs.clone(), None, 100)
                    .await
                    .expect("Batch query should succeed");

                assert!(!results.is_empty(), "Should find some entries");
            }));
        }

        for handle in handles {
            handle.await.expect("Task should complete");
        }

        pool.close().await.expect("Close should succeed");
    }
}

// ============================================================================
// Pool Cloning Tests
// ============================================================================

mod pool_cloning {
    use super::*;

    /// Test that pool clones share the same underlying connections
    #[tokio::test]
    async fn test_pool_clone_sharing() {
        let table_name = "CloneTable";
        let entries = [("CLONE001", "Clone.esp", "Clone Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries)
            .await
            .expect("Failed to create test database");

        let pool1 = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        pool1
            .initialize(vec![db_path])
            .await
            .expect("Initialize should succeed");

        let pool2 = pool1.clone();

        // Query from pool1
        let result1 = pool1
            .get_entry("CLONE001", "Clone.esp", None)
            .await
            .expect("Query should succeed");
        assert_eq!(result1, Some("Clone Entry".to_string()));

        // Query from pool2 should hit cache populated by pool1
        let result2 = pool2
            .get_entry("CLONE001", "Clone.esp", None)
            .await
            .expect("Query should succeed");
        assert_eq!(result2, Some("Clone Entry".to_string()));

        // Stats should reflect both queries (shared state)
        let stats = pool1.get_stats().expect("Stats should be available");
        assert_eq!(
            stats.total_queries, 2,
            "Should see queries from both clones"
        );
        assert!(stats.cache_hits >= 1, "Second query should hit cache");

        // Close from either clone should close the shared pool
        pool1.close().await.expect("Close should succeed");
    }
}

// ============================================================================
// Database Optimization Tests
// ============================================================================

mod optimization {
    use super::*;

    /// Test optimize operation
    #[tokio::test]
    async fn test_database_optimize() {
        let table_name = "OptimizeTable";
        let entries = [("OPT00001", "Opt.esp", "Optimize Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries)
            .await
            .expect("Failed to create test database");

        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        pool.initialize(vec![db_path])
            .await
            .expect("Initialize should succeed");

        // Optimize should succeed
        pool.optimize().await.expect("Optimize should succeed");

        // Database should still be queryable after optimize
        let result = pool
            .get_entry("OPT00001", "Opt.esp", None)
            .await
            .expect("Query should succeed after optimize");
        assert_eq!(result, Some("Optimize Entry".to_string()));

        pool.close().await.expect("Close should succeed");
    }
}
