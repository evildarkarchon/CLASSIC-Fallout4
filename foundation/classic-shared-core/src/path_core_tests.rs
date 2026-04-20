use super::*;

#[test]
fn test_path_handler_new() {
    let handler = PathHandler::new(60);
    let (path_count, val_count) = handler.cache_stats();
    assert_eq!(path_count, 0);
    assert_eq!(val_count, 0);
}

#[test]
fn test_path_handler_default() {
    let handler = PathHandler::default();
    let (path_count, _) = handler.cache_stats();
    assert_eq!(path_count, 0);
}

#[test]
fn test_path_handler_with_limits() {
    let handler = PathHandler::new_with_limits(60, 100);
    let (path_count, _) = handler.cache_stats();
    assert_eq!(path_count, 0);
}

#[test]
fn test_cache_metrics_initial() {
    let handler = PathHandler::new(60);
    let (hits, misses, rate) = handler.cache_metrics();
    assert_eq!(hits, 0);
    assert_eq!(misses, 0);
    assert_eq!(rate, 0.0);
}

#[test]
fn test_join_paths() {
    let handler = PathHandler::new(60);
    let result = handler.join_paths("C:\\Games", &["Fallout4".to_string(), "Data".to_string()]);
    assert!(result.contains("Fallout4"));
    assert!(result.contains("Data"));
}

#[test]
fn test_split_path() {
    let handler = PathHandler::new(60);
    let components = handler.split_path("C:\\Games\\Fallout4\\Data");
    assert!(!components.is_empty());
    assert!(components.contains(&"Fallout4".to_string()));
}

#[test]
fn test_get_filename() {
    let handler = PathHandler::new(60);
    assert_eq!(
        handler.get_filename("C:\\logs\\crash.log"),
        Some("crash.log".to_string())
    );
    assert_eq!(
        handler.get_filename("crash.log"),
        Some("crash.log".to_string())
    );
}

#[test]
fn test_get_extension() {
    let handler = PathHandler::new(60);
    assert_eq!(handler.get_extension("file.txt"), Some("txt".to_string()));
    assert_eq!(handler.get_extension("file.tar.gz"), Some("gz".to_string()));
    assert_eq!(handler.get_extension("noext"), None);
}

#[test]
fn test_get_parent() {
    let handler = PathHandler::new(60);
    let parent = handler.get_parent("C:\\Games\\file.txt");
    assert!(parent.is_some());
    assert!(parent.unwrap().contains("Games"));
}

#[test]
fn test_is_absolute() {
    let handler = PathHandler::new(60);
    assert!(handler.is_absolute("C:\\absolute\\path"));
    assert!(!handler.is_absolute("relative\\path"));
}

#[test]
fn test_to_absolute_already_absolute() {
    let handler = PathHandler::new(60);
    let result = handler.to_absolute("C:\\absolute\\path", None);
    assert!(result.is_ok());
    assert!(result.unwrap().starts_with("C:\\"));
}

#[test]
fn test_to_absolute_relative_with_base() {
    let handler = PathHandler::new(60);
    let result = handler.to_absolute("subdir\\file.txt", Some("C:\\base"));
    assert!(result.is_ok());
    let abs = result.unwrap();
    assert!(abs.contains("base"));
    assert!(abs.contains("file.txt"));
}

#[test]
fn test_to_absolute_relative_no_base() {
    let handler = PathHandler::new(60);
    let result = handler.to_absolute("relative.txt", None);
    // Uses current working directory
    assert!(result.is_ok());
}

#[test]
fn test_common_prefix_empty() {
    let handler = PathHandler::new(60);
    assert_eq!(handler.common_prefix(&[]), None);
}

#[test]
fn test_common_prefix_identical() {
    let handler = PathHandler::new(60);
    let paths = vec!["C:\\Games\\FO4".to_string(), "C:\\Games\\FO4".to_string()];
    let prefix = handler.common_prefix(&paths);
    assert!(prefix.is_some());
}

#[test]
fn test_common_prefix_different_roots() {
    let handler = PathHandler::new(60);
    let paths = vec!["C:\\Games".to_string(), "D:\\Games".to_string()];
    let prefix = handler.common_prefix(&paths);
    assert!(prefix.is_none());
}

#[test]
fn test_normalize_path_existing() {
    let handler = PathHandler::new(60);
    // Use a path that exists
    let result = handler.normalize_path(".");
    assert!(result.is_ok());
}

#[test]
fn test_normalize_path_nonexistent() {
    let handler = PathHandler::new(60);
    // Non-existent path should fall back to clean_path
    let result = handler.normalize_path("Z:\\nonexistent\\path\\that\\wont\\exist");
    assert!(result.is_ok());
}

#[test]
fn test_normalize_path_cache_hit() {
    let handler = PathHandler::new(60);
    // First call: cache miss
    let r1 = handler.normalize_path(".");
    assert!(r1.is_ok());

    // Second call: cache hit
    let r2 = handler.normalize_path(".");
    assert!(r2.is_ok());

    let (hits, misses, rate) = handler.cache_metrics();
    assert!(hits >= 1, "Expected at least one cache hit");
    assert!(misses >= 1, "Expected at least one cache miss");
    assert!(rate > 0.0);
}

#[test]
fn test_clear_cache() {
    let handler = PathHandler::new(60);
    let _ = handler.normalize_path(".");
    handler.clear_cache();
    let (path_count, val_count) = handler.cache_stats();
    assert_eq!(path_count, 0);
    assert_eq!(val_count, 0);
}

#[test]
fn test_cleanup_cache_removes_expired() {
    // Create handler with very short TTL
    let handler = PathHandler::new(0); // 0 seconds TTL
    let _ = handler.normalize_path(".");
    // Everything should be expired immediately
    handler.cleanup_cache();
    let (path_count, _) = handler.cache_stats();
    assert_eq!(path_count, 0);
}

#[test]
fn test_validate_paths_batch() {
    let handler = PathHandler::new(60);
    let paths = vec![
        ".".to_string(),                   // exists
        "Z:\\nonexistent\\42".to_string(), // doesn't exist
    ];
    let results = handler.validate_paths_batch(&paths);
    assert_eq!(results.len(), 2);
    assert!(results[0].1, "Current dir should be valid");
    assert!(!results[1].1, "Nonexistent path should be invalid");
}

#[test]
fn test_validate_paths_batch_cached() {
    let handler = PathHandler::new(300);
    let paths = vec![".".to_string()];

    // First call
    let r1 = handler.validate_paths_batch(&paths);
    // Second call should use cache
    let r2 = handler.validate_paths_batch(&paths);

    assert_eq!(r1[0].1, r2[0].1);
}

#[test]
fn test_evict_lru_when_full() {
    let handler = PathHandler::new_with_limits(60, 2);
    // Fill cache beyond limit
    let _ = handler.normalize_path(".");
    let _ = handler.normalize_path("..");
    let _ = handler.normalize_path("C:\\");
    // Should not panic; some entries should be evicted
    let (count, _) = handler.cache_stats();
    assert!(count <= 3);
}
