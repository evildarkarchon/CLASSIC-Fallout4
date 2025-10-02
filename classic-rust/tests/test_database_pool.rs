//! Tests for the Rust database pool implementation

use classic_core::database::pool::RustDatabasePool;
use pyo3::Python;
use std::path::PathBuf;
use tempfile::TempDir;
use rusqlite::Connection;

/// Initialize Python interpreter for tests
fn init_python() {
    use std::sync::Once;
    static INIT: Once = Once::new();
    INIT.call_once(|| {
        Python::initialize();
    });
}

/// Create a test database with sample data
fn create_test_database(path: &PathBuf, table_name: &str) -> Result<(), Box<dyn std::error::Error>> {
    let conn = Connection::open(path)?;

    // Create table
    conn.execute(
        &format!(
            "CREATE TABLE IF NOT EXISTS {} (
                formid TEXT NOT NULL,
                plugin TEXT NOT NULL,
                entry TEXT NOT NULL,
                PRIMARY KEY (formid, plugin)
            )",
            table_name
        ),
        [],
    )?;

    // Insert test data
    let test_data = vec![
        ("00012345", "Fallout4.esm", "TestEntry1"),
        ("00023456", "DLCCoast.esm", "TestEntry2"),
        ("00034567", "DLCNukaWorld.esm", "TestEntry3"),
        ("00045678", "TestMod.esp", "TestEntry4"),
    ];

    for (formid, plugin, entry) in test_data {
        conn.execute(
            &format!(
                "INSERT OR REPLACE INTO {} (formid, plugin, entry) VALUES (?1, ?2, ?3)",
                table_name
            ),
            [formid, plugin, entry],
        )?;
    }

    Ok(())
}

#[test]
fn test_pool_creation() {
    let pool = RustDatabasePool::new(Some(5), Some(60), Some("Fallout4".to_string()));
    let stats = pool.py_get_stats().unwrap();

    assert_eq!(stats.get("total_queries"), Some(&0));
    assert_eq!(stats.get("cache_hits"), Some(&0));
    assert_eq!(stats.get("cache_misses"), Some(&0));

    // Test game table getter/setter
    assert_eq!(pool.py_get_game_table(), "Fallout4");
    pool.py_set_game_table("Skyrim".to_string());
    assert_eq!(pool.py_get_game_table(), "Skyrim");
}

#[test]
fn test_database_initialization() {
    init_python();

    let temp_dir = TempDir::new().unwrap();
    let db_path = temp_dir.path().join("test.db");

    // Create test database
    create_test_database(&db_path, "Fallout4").unwrap();

    let pool = RustDatabasePool::new(None, None, Some("Fallout4".to_string()));

    Python::attach(|py| {
        pool.py_initialize(py, vec![db_path.to_string_lossy().to_string()]).unwrap();

        let stats = pool.py_get_stats().unwrap();
        assert_eq!(stats.get("total_connections"), Some(&1));
        assert_eq!(stats.get("active_connections"), Some(&1));
    });
}

#[test]
fn test_single_entry_lookup() {
    init_python();
    let temp_dir = TempDir::new().unwrap();
    let db_path = temp_dir.path().join("test.db");

    // Create test database
    create_test_database(&db_path, "Fallout4").unwrap();

    let pool = RustDatabasePool::new(None, None, Some("Fallout4".to_string()));

    Python::attach(|py| {
        pool.py_initialize(py, vec![db_path.to_string_lossy().to_string()]).unwrap();

        // Test successful lookup
        let result = pool.py_get_entry(py, "00012345".to_string(), "Fallout4.esm".to_string(), Some("Fallout4".to_string())).unwrap();
        assert_eq!(result, Some("TestEntry1".to_string()));

        // Test cache hit
        let stats_before = pool.py_get_stats().unwrap();
        let cache_hits_before = stats_before.get("cache_hits").copied().unwrap_or(0);

        let result = pool.py_get_entry(py, "00012345".to_string(), "Fallout4.esm".to_string(), Some("Fallout4".to_string())).unwrap();
        assert_eq!(result, Some("TestEntry1".to_string()));

        let stats_after = pool.py_get_stats().unwrap();
        let cache_hits_after = stats_after.get("cache_hits").copied().unwrap_or(0);
        assert_eq!(cache_hits_after, cache_hits_before + 1);

        // Test non-existent entry
        let result = pool.py_get_entry(py, "99999999".to_string(), "NonExistent.esp".to_string(), Some("Fallout4".to_string())).unwrap();
        assert_eq!(result, None);
    });
}

#[test]
fn test_batch_lookup() {
    init_python();
    use pyo3::types::PyList;
    use pyo3::Python;

    let temp_dir = TempDir::new().unwrap();
    let db_path = temp_dir.path().join("test.db");

    // Create test database
    create_test_database(&db_path, "Fallout4").unwrap();

    let pool = RustDatabasePool::new(None, None, Some("Fallout4".to_string()));

    Python::attach(|py| {
        pool.py_initialize(py, vec![db_path.to_string_lossy().to_string()]).unwrap();

        // Test the new batch_lookup method
        let pairs = vec![
            ("00012345", "Fallout4.esm"),
            ("00023456", "DLCCoast.esm"),
            ("99999999", "NonExistent.esp"),
        ];

        let py_list = PyList::new(py, pairs.iter().map(|(f, p)| (f, p))).expect("Failed to create PyList");

        // Test batch_lookup (new method)
        let results = pool.py_batch_lookup(
            py,
            &py_list,
            Some("Fallout4".to_string())
        ).unwrap();

        assert_eq!(results.get(&("00012345".to_string(), "Fallout4.esm".to_string())), Some(&"TestEntry1".to_string()));
        assert_eq!(results.get(&("00023456".to_string(), "DLCCoast.esm".to_string())), Some(&"TestEntry2".to_string()));
        assert_eq!(results.get(&("99999999".to_string(), "NonExistent.esp".to_string())), None);
    });
}

#[test]
fn test_batch_entries_legacy() {
    init_python();
    use pyo3::types::PyList;
    use pyo3::Python;

    let temp_dir = TempDir::new().unwrap();
    let db_path = temp_dir.path().join("test.db");

    // Create test database
    create_test_database(&db_path, "Fallout4").unwrap();

    let pool = RustDatabasePool::new(None, None, Some("Fallout4".to_string()));

    Python::attach(|py| {
        pool.py_initialize(py, vec![db_path.to_string_lossy().to_string()]).unwrap();

        // Create Python list of tuples
        let pairs = vec![
            ("00012345", "Fallout4.esm"),
            ("00023456", "DLCCoast.esm"),
            ("99999999", "NonExistent.esp"),
        ];

        let py_list = PyList::new(py, pairs.iter().map(|(f, p)| (f, p))).expect("Failed to create PyList");

        let results = pool.py_get_entries_batch(
            py,
            &py_list,
            Some("Fallout4".to_string()),
            None
        ).unwrap();

        assert_eq!(results.get("00012345:Fallout4.esm"), Some(&"TestEntry1".to_string()));
        assert_eq!(results.get("00023456:DLCCoast.esm"), Some(&"TestEntry2".to_string()));
        assert_eq!(results.get("99999999:NonExistent.esp"), None);

        // Check stats
        let stats = pool.py_get_stats().unwrap();
        assert!(stats.get("total_queries").copied().unwrap_or(0) >= 3);
    });
}

#[test]
fn test_cache_operations() {
    init_python();
    let pool = RustDatabasePool::new(None, Some(1), Some("Fallout4".to_string())); // 1 second TTL

    Python::attach(|py| {
        let temp_dir = TempDir::new().unwrap();
        let db_path = temp_dir.path().join("test.db");

        create_test_database(&db_path, "Fallout4").unwrap();
        pool.py_initialize(py, vec![db_path.to_string_lossy().to_string()]).unwrap();

        // Populate cache
        pool.py_get_entry(py, "00012345".to_string(), "Fallout4.esm".to_string(), Some("Fallout4".to_string())).unwrap();
        pool.py_get_entry(py, "00023456".to_string(), "DLCCoast.esm".to_string(), Some("Fallout4".to_string())).unwrap();

        let stats = pool.py_get_stats().unwrap();
        assert_eq!(stats.get("cache_size"), Some(&2));

        // Clear cache
        let cleared = pool.py_clear_cache(Some(false));
        assert_eq!(cleared, 2);

        let stats = pool.py_get_stats().unwrap();
        assert_eq!(stats.get("cache_size"), Some(&0));

        // Test TTL change
        pool.py_set_cache_ttl(300);

        // Test expired-only clear (should clear nothing since cache is empty)
        let cleared = pool.py_clear_cache(Some(true));
        assert_eq!(cleared, 0);
    });
}

#[test]
fn test_multiple_databases() {
    init_python();
    let temp_dir = TempDir::new().unwrap();
    let db1_path = temp_dir.path().join("main.db");
    let db2_path = temp_dir.path().join("local.db");

    // Create two databases with different data
    create_test_database(&db1_path, "Fallout4").unwrap();

    // Create second database with additional data
    let conn = Connection::open(&db2_path).unwrap();
    conn.execute(
        "CREATE TABLE IF NOT EXISTS Fallout4 (
            formid TEXT NOT NULL,
            plugin TEXT NOT NULL,
            entry TEXT NOT NULL,
            PRIMARY KEY (formid, plugin)
        )",
        [],
    ).unwrap();
    conn.execute(
        "INSERT INTO Fallout4 (formid, plugin, entry) VALUES (?1, ?2, ?3)",
        ["00056789", "LocalMod.esp", "LocalEntry"],
    ).unwrap();

    let pool = RustDatabasePool::new(None, None, Some("Fallout4".to_string()));

    Python::attach(|py| {
        pool.py_initialize(py, vec![
            db1_path.to_string_lossy().to_string(),
            db2_path.to_string_lossy().to_string(),
        ]).unwrap();

        // Test lookup from first database
        let result = pool.py_get_entry(py, "00012345".to_string(), "Fallout4.esm".to_string(), Some("Fallout4".to_string())).unwrap();
        assert_eq!(result, Some("TestEntry1".to_string()));

        // Test lookup from second database
        let result = pool.py_get_entry(py, "00056789".to_string(), "LocalMod.esp".to_string(), Some("Fallout4".to_string())).unwrap();
        assert_eq!(result, Some("LocalEntry".to_string()));

        let stats = pool.py_get_stats().unwrap();
        assert_eq!(stats.get("total_connections"), Some(&2));
    });
}

#[test]
fn test_optimization() {
    init_python();
    let temp_dir = TempDir::new().unwrap();
    let db_path = temp_dir.path().join("test.db");

    create_test_database(&db_path, "Fallout4").unwrap();

    let pool = RustDatabasePool::new(None, None, Some("Fallout4".to_string()));

    Python::attach(|py| {
        pool.py_initialize(py, vec![db_path.to_string_lossy().to_string()]).unwrap();

        // Should not panic
        pool.py_optimize(py).unwrap();
    });
}

#[test]
fn test_concurrent_access() {
    init_python();
    use std::thread;
    use std::sync::Arc;

    let temp_dir = TempDir::new().unwrap();
    let db_path = temp_dir.path().join("test.db");

    create_test_database(&db_path, "Fallout4").unwrap();

    let pool = Arc::new(RustDatabasePool::new(None, None, Some("Fallout4".to_string())));

    Python::attach(|py| {
        pool.py_initialize(py, vec![db_path.to_string_lossy().to_string()]).unwrap();
    });

    // Spawn multiple threads to access the pool concurrently
    let handles: Vec<_> = (0..10)
        .map(|i| {
            let pool_clone = Arc::clone(&pool);
            thread::spawn(move || {
                Python::attach(|py| {
                    for _ in 0..10 {
                        let formid = format!("{:08}", 12345 + i);
                        let _ = pool_clone.py_get_entry(
                            py,
                            formid,
                            "Fallout4.esm".to_string(),
                            Some("Fallout4".to_string())
                        );
                    }
                });
            })
        })
        .collect();

    for handle in handles {
        handle.join().unwrap();
    }

    Python::attach(|_py| {
        let stats = pool.py_get_stats().unwrap();
        assert!(stats.get("total_queries").copied().unwrap_or(0) >= 100);
    });
}
