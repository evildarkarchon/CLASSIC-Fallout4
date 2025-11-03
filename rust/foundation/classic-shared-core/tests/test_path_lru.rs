//! Unit tests for PathHandler LRU cache eviction

use classic_shared_core::path_core::PathHandler;
use std::env;

#[test]
fn test_lru_cache_bounded() {
    // Create handler with small cache limit
    let handler = PathHandler::new_with_limits(300, 10);

    let current_dir = env::current_dir().expect("Failed to get current directory");

    // Fill cache to capacity
    for i in 0..10 {
        let path = current_dir
            .join(format!("test_file_{}.txt", i))
            .to_string_lossy()
            .to_string();
        handler.normalize_path(&path).ok();
    }

    let (cache_size, _) = handler.cache_stats();
    assert!(
        cache_size <= 10,
        "Cache should not exceed max size: {} <= 10",
        cache_size
    );
}

#[test]
fn test_lru_eviction_on_overflow() {
    // Create handler with cache limit of 5
    let handler = PathHandler::new_with_limits(300, 5);

    let current_dir = env::current_dir().expect("Failed to get current directory");

    // Fill cache to capacity
    for i in 0..5 {
        let path = current_dir
            .join(format!("test_file_{}.txt", i))
            .to_string_lossy()
            .to_string();
        handler.normalize_path(&path).ok();
    }

    let (cache_size_before, _) = handler.cache_stats();
    assert_eq!(cache_size_before, 5, "Cache should be at capacity");

    // Add one more entry, should trigger eviction
    let overflow_path = current_dir
        .join("overflow_file.txt")
        .to_string_lossy()
        .to_string();
    handler.normalize_path(&overflow_path).ok();

    let (cache_size_after, _) = handler.cache_stats();
    assert!(
        cache_size_after <= 5,
        "Cache should evict entries and stay within limit: {} <= 5",
        cache_size_after
    );
}

#[test]
#[allow(unused)]
fn test_cache_metrics() {
    let handler = PathHandler::new_with_limits(300, 100);

    let current_dir = env::current_dir().expect("Failed to get current directory");
    let test_path = current_dir
        .join("metrics_test.txt")
        .to_string_lossy()
        .to_string();

    // First access - cache miss
    handler.normalize_path(&test_path).ok();
    let (hits1, misses1, rate1) = handler.cache_metrics();
    assert_eq!(misses1, 1, "First access should be a miss");

    // Second access - cache hit
    handler.normalize_path(&test_path).ok();
    let (hits2, misses2, rate2) = handler.cache_metrics();
    assert_eq!(hits2, 1, "Second access should be a hit");
    assert_eq!(misses2, 1, "Miss count should not change");
    assert!(rate2 > 0.0 && rate2 <= 1.0, "Hit rate should be valid");

    // Multiple cache hits
    for _ in 0..10 {
        handler.normalize_path(&test_path).ok();
    }

    let (hits3, misses3, rate3) = handler.cache_metrics();
    assert_eq!(hits3, 11, "Should have 11 total hits");
    assert_eq!(misses3, 1, "Should still have 1 miss");
    assert!(rate3 > 0.9, "Hit rate should be > 90%: {}", rate3);
}

#[test]
fn test_unbounded_cache() {
    // Unbounded cache (max_size = 0)
    let handler = PathHandler::new(300);

    let current_dir = env::current_dir().expect("Failed to get current directory");

    // Add many entries
    for i in 0..1000 {
        let path = current_dir
            .join(format!("test_file_{}.txt", i))
            .to_string_lossy()
            .to_string();
        handler.normalize_path(&path).ok();
    }

    let (cache_size, _) = handler.cache_stats();
    assert_eq!(cache_size, 1000, "Unbounded cache should store all entries");
}

#[test]
fn test_lru_favors_frequently_used() {
    let handler = PathHandler::new_with_limits(300, 5);

    let current_dir = env::current_dir().expect("Failed to get current directory");

    // Create paths
    let paths: Vec<String> = (0..10)
        .map(|i| {
            current_dir
                .join(format!("test_file_{}.txt", i))
                .to_string_lossy()
                .to_string()
        })
        .collect();

    // Access first 3 paths multiple times (high hit count)
    for _ in 0..10 {
        for i in 0..3 {
            handler.normalize_path(&paths[i]).ok();
        }
    }

    // Access paths 3-4 once (low hit count)
    for i in 3..5 {
        handler.normalize_path(&paths[i]).ok();
    }

    let (cache_size_before, _) = handler.cache_stats();
    assert_eq!(cache_size_before, 5, "Cache should be at capacity");

    // Access paths 5-9 (should trigger eviction of least-used entries)
    for i in 5..10 {
        handler.normalize_path(&paths[i]).ok();
    }

    // First 3 paths (high hit count) should still be cached
    let (hits_before, _, _) = handler.cache_metrics();
    handler.normalize_path(&paths[0]).ok();
    handler.normalize_path(&paths[1]).ok();
    handler.normalize_path(&paths[2]).ok();
    let (hits_after, _, _) = handler.cache_metrics();

    // At least some of the frequently-used paths should still be cached
    let new_hits = hits_after - hits_before;
    assert!(
        new_hits > 0,
        "Frequently accessed paths should be retained: {} new hits",
        new_hits
    );
}

#[test]
fn test_cache_clear() {
    let handler = PathHandler::new_with_limits(300, 100);

    let current_dir = env::current_dir().expect("Failed to get current directory");

    // Add entries
    for i in 0..10 {
        let path = current_dir
            .join(format!("test_file_{}.txt", i))
            .to_string_lossy()
            .to_string();
        handler.normalize_path(&path).ok();
    }

    let (cache_size_before, _) = handler.cache_stats();
    assert_eq!(cache_size_before, 10, "Cache should have 10 entries");

    // Clear cache
    handler.clear_cache();

    let (cache_size_after, _) = handler.cache_stats();
    assert_eq!(cache_size_after, 0, "Cache should be empty after clear");
}
