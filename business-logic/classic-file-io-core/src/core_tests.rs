use super::*;
use serial_test::serial;
use std::io::Write;
use tempfile::TempDir;

// ==================== FileIOCore Creation Tests ====================

#[test]
fn test_new_with_default_parameters() {
    let core = FileIOCore::default();
    assert_eq!(core.default_encoding, "utf-8");
    assert_eq!(core.default_errors, "ignore");
}

#[test]
fn test_new_with_custom_parameters() {
    let core = FileIOCore::new("windows-1252", "strict", 200, 100);
    assert_eq!(core.default_encoding, "windows-1252");
    assert_eq!(core.default_errors, "strict");
}

#[test]
fn test_new_with_zero_cache_size() {
    // Cache size should be clamped to minimum of 1
    let core = FileIOCore::new("utf-8", "ignore", 0, 10);
    assert_eq!(core.default_encoding, "utf-8");
}

#[test]
fn test_clone_refs() {
    let core = FileIOCore::default();
    let cloned = core.clone_refs();
    assert_eq!(cloned.default_encoding, core.default_encoding);
    assert_eq!(cloned.default_errors, core.default_errors);
}

// ==================== Async File Read/Write Tests ====================

#[tokio::test]
async fn test_read_file_success() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("test.txt");
    std::fs::write(&file_path, "Hello, World!").unwrap();

    let core = FileIOCore::default();
    let content = core.read_file(&file_path).await.unwrap();
    assert_eq!(content, "Hello, World!");
}

#[tokio::test]
async fn test_read_file_not_found() {
    let core = FileIOCore::default();
    let result = core.read_file(Path::new("/nonexistent/file.txt")).await;
    assert!(result.is_err());
}

#[tokio::test]
async fn test_read_file_cached() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("cached.txt");
    std::fs::write(&file_path, "Cached content").unwrap();

    let core = FileIOCore::default();

    // First read - from disk
    let content1 = core.read_file(&file_path).await.unwrap();
    assert_eq!(content1, "Cached content");

    // Second read - should be from cache
    let content2 = core.read_file(&file_path).await.unwrap();
    assert_eq!(content2, "Cached content");
}

#[tokio::test]
async fn test_write_file_success() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("output.txt");

    let core = FileIOCore::default();
    core.write_file(&file_path, "Test content").await.unwrap();

    let content = std::fs::read_to_string(&file_path).unwrap();
    assert_eq!(content, "Test content");
}

#[tokio::test]
async fn test_write_file_invalidates_cache() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("cache_test.txt");

    let core = FileIOCore::default();
    core.write_file(&file_path, "Initial").await.unwrap();

    // Read to populate cache
    let content1 = core.read_file(&file_path).await.unwrap();
    assert_eq!(content1, "Initial");

    // Write new content (should invalidate cache)
    core.write_file(&file_path, "Updated").await.unwrap();

    // Read again - should get new content
    let content2 = core.read_file(&file_path).await.unwrap();
    assert_eq!(content2, "Updated");
}

// ==================== Bytes Read/Write Tests ====================

#[tokio::test]
async fn test_read_bytes_success() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("binary.bin");
    let test_bytes = vec![0x00, 0x01, 0x02, 0xFF, 0xFE];
    std::fs::write(&file_path, &test_bytes).unwrap();

    let core = FileIOCore::default();
    let bytes = core.read_bytes(&file_path).await.unwrap();
    assert_eq!(bytes, test_bytes);
}

#[tokio::test]
async fn test_read_bytes_not_found() {
    let core = FileIOCore::default();
    let result = core.read_bytes(Path::new("/nonexistent/binary.bin")).await;
    assert!(result.is_err());
}

#[tokio::test]
async fn test_write_bytes_success() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("output.bin");
    let test_bytes = vec![0xDE, 0xAD, 0xBE, 0xEF];

    let core = FileIOCore::default();
    core.write_bytes(&file_path, test_bytes.clone())
        .await
        .unwrap();

    let read_bytes = std::fs::read(&file_path).unwrap();
    assert_eq!(read_bytes, test_bytes);
}

#[tokio::test]
async fn test_write_bytes_creates_parent_dirs() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("nested").join("dir").join("file.bin");

    let core = FileIOCore::default();
    core.write_bytes(&file_path, vec![0x01, 0x02])
        .await
        .unwrap();

    assert!(file_path.exists());
}

// ==================== Lines Read/Write Tests ====================

#[tokio::test]
async fn test_read_lines_success() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("lines.txt");
    std::fs::write(&file_path, "Line 1\nLine 2\nLine 3").unwrap();

    let core = FileIOCore::default();
    let lines = core.read_lines(&file_path).await.unwrap();
    assert_eq!(lines, vec!["Line 1", "Line 2", "Line 3"]);
}

#[tokio::test]
async fn test_read_lines_empty_file() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("empty.txt");
    std::fs::write(&file_path, "").unwrap();

    let core = FileIOCore::default();
    let lines = core.read_lines(&file_path).await.unwrap();
    assert!(lines.is_empty());
}

#[tokio::test]
async fn test_write_lines_success() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("output_lines.txt");
    let lines = vec![
        "First".to_string(),
        "Second".to_string(),
        "Third".to_string(),
    ];

    let core = FileIOCore::default();
    core.write_lines(&file_path, lines).await.unwrap();

    let content = std::fs::read_to_string(&file_path).unwrap();
    assert_eq!(content, "First\nSecond\nThird\n");
}

#[tokio::test]
async fn test_write_lines_empty_vector() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("empty_lines.txt");

    let core = FileIOCore::default();
    core.write_lines(&file_path, vec![]).await.unwrap();

    let content = std::fs::read_to_string(&file_path).unwrap();
    assert_eq!(content, "\n");
}

// ==================== Append File Tests ====================
// Note: These tests use #[serial] because async file operations may not
// flush immediately, causing race conditions with sync reads in parallel tests.

#[tokio::test]
#[serial]
async fn test_append_file_to_existing() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("append.txt");
    std::fs::write(&file_path, "Initial\n").unwrap();

    let core = FileIOCore::default();
    core.append_file(&file_path, "Appended\n").await.unwrap();

    let content = std::fs::read_to_string(&file_path).unwrap();
    assert_eq!(content, "Initial\nAppended\n");
}

#[tokio::test]
#[serial]
async fn test_append_file_creates_new() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("new_append.txt");

    let core = FileIOCore::default();
    core.append_file(&file_path, "First line\n").await.unwrap();
    core.append_file(&file_path, "Second line\n").await.unwrap();

    let content = std::fs::read_to_string(&file_path).unwrap();
    assert_eq!(content, "First line\nSecond line\n");
}

#[tokio::test]
#[serial]
async fn test_append_file_creates_parent_dirs() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("logs").join("app.log");

    let core = FileIOCore::default();
    core.append_file(&file_path, "Log entry\n").await.unwrap();

    assert!(file_path.exists());
}

// ==================== Stream Lines Tests ====================

#[tokio::test]
async fn test_stream_lines_success() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("stream.txt");
    std::fs::write(&file_path, "Line A\nLine B\nLine C").unwrap();

    let core = FileIOCore::default();
    let mut lines = core.stream_lines(&file_path).await.unwrap();

    let mut collected = Vec::new();
    while let Some(line) = lines.next_line().await.unwrap() {
        collected.push(line);
    }

    assert_eq!(collected, vec!["Line A", "Line B", "Line C"]);
}

#[test]
fn test_stream_lines_sync_success() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("sync_stream.txt");
    std::fs::write(&file_path, "Sync A\nSync B").unwrap();

    let core = FileIOCore::default();
    let lines = core.stream_lines_sync(&file_path).unwrap();

    let collected: Vec<String> = lines.map_while(Result::ok).collect();
    assert_eq!(collected, vec!["Sync A", "Sync B"]);
}

// ==================== File Metadata Tests ====================

#[test]
fn test_file_exists_true() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("exists.txt");
    std::fs::write(&file_path, "content").unwrap();

    let core = FileIOCore::default();
    assert!(core.file_exists(&file_path));
}

#[test]
fn test_file_exists_false() {
    let core = FileIOCore::default();
    assert!(!core.file_exists(Path::new("/nonexistent/path/file.txt")));
}

#[test]
fn test_file_exists_directory() {
    let temp = TempDir::new().unwrap();
    let core = FileIOCore::default();
    assert!(core.file_exists(temp.path()));
}

#[test]
fn test_is_directory_true() {
    let temp = TempDir::new().unwrap();
    let core = FileIOCore::default();
    assert!(core.is_directory(temp.path()));
}

#[test]
fn test_is_directory_false_for_file() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("file.txt");
    std::fs::write(&file_path, "content").unwrap();

    let core = FileIOCore::default();
    assert!(!core.is_directory(&file_path));
}

#[test]
fn test_is_directory_nonexistent() {
    let core = FileIOCore::default();
    assert!(!core.is_directory(Path::new("/nonexistent/dir")));
}

#[test]
fn test_get_file_size_success() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("sized.txt");
    std::fs::write(&file_path, "12345").unwrap();

    let core = FileIOCore::default();
    let size = core.get_file_size(&file_path);
    assert_eq!(size, Some(5));
}

#[test]
fn test_get_file_size_directory() {
    let temp = TempDir::new().unwrap();
    let core = FileIOCore::default();
    let size = core.get_file_size(temp.path());
    assert!(size.is_none());
}

#[test]
fn test_get_file_size_nonexistent() {
    let core = FileIOCore::default();
    let size = core.get_file_size(Path::new("/nonexistent/file.txt"));
    assert!(size.is_none());
}

// ==================== Cache Tests ====================

#[tokio::test]
async fn test_clear_cache() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("cache_clear.txt");
    std::fs::write(&file_path, "Cached").unwrap();

    let core = FileIOCore::default();

    // Populate cache
    core.read_file(&file_path).await.unwrap();
    core.file_exists(&file_path);
    core.ensure_path("some/path");

    assert!(core.metadata_cache_size() > 0);

    // Clear cache
    core.clear_cache().await;

    // After clearing, metadata cache should be empty
    assert_eq!(core.metadata_cache_size(), 0);
}

#[test]
fn test_metadata_cache_size() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("meta_test.txt");
    std::fs::write(&file_path, "test").unwrap();

    let core = FileIOCore::default();
    assert_eq!(core.metadata_cache_size(), 0);

    core.file_exists(&file_path);
    assert!(core.metadata_cache_size() > 0);
}

// ==================== Ensure Path Tests ====================

#[test]
fn test_ensure_path_caching() {
    let core = FileIOCore::default();

    let path1 = core.ensure_path("test/path/file.txt");
    let path2 = core.ensure_path("test/path/file.txt");

    // Should return same Arc (reference equality)
    assert!(Arc::ptr_eq(&path1, &path2));
}

#[test]
fn test_ensure_path_different_paths() {
    let core = FileIOCore::default();

    let path1 = core.ensure_path("path/one.txt");
    let path2 = core.ensure_path("path/two.txt");

    assert!(!Arc::ptr_eq(&path1, &path2));
    assert_eq!(*path1, PathBuf::from("path/one.txt"));
    assert_eq!(*path2, PathBuf::from("path/two.txt"));
}

// ==================== Walk Directory Tests ====================

#[test]
fn test_walk_directory_all_files() {
    let temp = TempDir::new().unwrap();
    std::fs::write(temp.path().join("file1.txt"), "").unwrap();
    std::fs::write(temp.path().join("file2.log"), "").unwrap();
    std::fs::create_dir(temp.path().join("subdir")).unwrap();
    std::fs::write(temp.path().join("subdir").join("file3.txt"), "").unwrap();

    let core = FileIOCore::default();
    let files = core.walk_directory(temp.path(), None, None).unwrap();

    assert_eq!(files.len(), 3);
}

#[test]
fn test_walk_directory_with_pattern() {
    let temp = TempDir::new().unwrap();
    std::fs::write(temp.path().join("test.txt"), "").unwrap();
    std::fs::write(temp.path().join("test.log"), "").unwrap();
    std::fs::write(temp.path().join("other.txt"), "").unwrap();

    let core = FileIOCore::default();
    let files = core
        .walk_directory(temp.path(), Some(r"^test\."), None)
        .unwrap();

    assert_eq!(files.len(), 2);
}

#[test]
fn test_walk_directory_with_extension_pattern() {
    let temp = TempDir::new().unwrap();
    std::fs::write(temp.path().join("a.log"), "").unwrap();
    std::fs::write(temp.path().join("b.log"), "").unwrap();
    std::fs::write(temp.path().join("c.txt"), "").unwrap();

    let core = FileIOCore::default();
    let files = core
        .walk_directory(temp.path(), Some(r"\.log$"), None)
        .unwrap();

    assert_eq!(files.len(), 2);
}

#[test]
fn test_walk_directory_with_max_depth() {
    let temp = TempDir::new().unwrap();
    std::fs::write(temp.path().join("root.txt"), "").unwrap();
    std::fs::create_dir(temp.path().join("level1")).unwrap();
    std::fs::write(temp.path().join("level1").join("l1.txt"), "").unwrap();
    std::fs::create_dir(temp.path().join("level1").join("level2")).unwrap();
    std::fs::write(temp.path().join("level1").join("level2").join("l2.txt"), "").unwrap();

    let core = FileIOCore::default();

    // Depth 1 = only root directory
    let files_d1 = core.walk_directory(temp.path(), None, Some(1)).unwrap();
    assert_eq!(files_d1.len(), 1);

    // Depth 2 = root + level1
    let files_d2 = core.walk_directory(temp.path(), None, Some(2)).unwrap();
    assert_eq!(files_d2.len(), 2);

    // Unlimited depth
    let files_all = core.walk_directory(temp.path(), None, None).unwrap();
    assert_eq!(files_all.len(), 3);
}

#[test]
fn test_walk_directory_invalid_pattern() {
    let temp = TempDir::new().unwrap();
    let core = FileIOCore::default();

    let result = core.walk_directory(temp.path(), Some(r"[invalid"), None);
    assert!(result.is_err());
}

#[test]
fn test_walk_directory_empty() {
    let temp = TempDir::new().unwrap();
    let core = FileIOCore::default();

    let files = core.walk_directory(temp.path(), None, None).unwrap();
    assert!(files.is_empty());
}

// ==================== Multiple Files Tests ====================

#[tokio::test]
async fn test_read_multiple_files_success() {
    let temp = TempDir::new().unwrap();
    let paths: Vec<PathBuf> = (0..3)
        .map(|i| {
            let path = temp.path().join(format!("file{}.txt", i));
            std::fs::write(&path, format!("Content {}", i)).unwrap();
            path
        })
        .collect();

    let core = FileIOCore::default();
    let results = core.read_multiple_files(paths.clone()).await;

    assert_eq!(results.len(), 3);

    // Results may be in any order due to buffer_unordered, so check each one
    for (path, result) in &results {
        assert!(paths.contains(path));
        let content = result.as_ref().unwrap();
        // Verify the content matches the file index
        let filename = path.file_name().unwrap().to_str().unwrap();
        let index: usize = filename
            .trim_start_matches("file")
            .trim_end_matches(".txt")
            .parse()
            .unwrap();
        assert_eq!(content, &format!("Content {}", index));
    }
}

#[tokio::test]
async fn test_read_multiple_files_partial_failure() {
    let temp = TempDir::new().unwrap();
    let existing = temp.path().join("exists.txt");
    std::fs::write(&existing, "Exists").unwrap();

    let paths = vec![existing.clone(), temp.path().join("nonexistent.txt")];

    let core = FileIOCore::default();
    let results = core.read_multiple_files(paths).await;

    assert_eq!(results.len(), 2);

    // Results may be in any order, so find by path
    let mut found_success = false;
    let mut found_error = false;
    for (path, result) in &results {
        if path == &existing {
            assert!(result.is_ok());
            assert_eq!(result.as_ref().unwrap(), "Exists");
            found_success = true;
        } else {
            assert!(result.is_err());
            found_error = true;
        }
    }
    assert!(found_success, "Should have found successful read");
    assert!(found_error, "Should have found failed read");
}

#[tokio::test]
async fn test_write_multiple_files_success() {
    let temp = TempDir::new().unwrap();
    let files: Vec<(PathBuf, String)> = (0..3)
        .map(|i| {
            (
                temp.path().join(format!("out{}.txt", i)),
                format!("Output {}", i),
            )
        })
        .collect();

    let core = FileIOCore::default();
    let results = core.write_multiple_files(files.clone()).await;

    assert_eq!(results.len(), 3);
    for (path, result) in results {
        assert!(result.is_ok());
        assert!(path.exists());
    }
}

#[tokio::test]
async fn test_write_multiple_files_creates_dirs() {
    let temp = TempDir::new().unwrap();
    let files = vec![
        (
            temp.path().join("dir1").join("file1.txt"),
            "Content 1".to_string(),
        ),
        (
            temp.path().join("dir2").join("file2.txt"),
            "Content 2".to_string(),
        ),
    ];

    let core = FileIOCore::default();
    let results = core.write_multiple_files(files.clone()).await;

    for (path, result) in results {
        assert!(result.is_ok());
        assert!(path.exists());
    }
}

// ==================== Mmap Tests ====================

#[tokio::test]
async fn test_read_file_mmap_small_file() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("small.txt");
    std::fs::write(&file_path, "Small content").unwrap();

    let core = FileIOCore::default();
    let content = core.read_file_mmap(&file_path).await.unwrap();
    assert_eq!(content, "Small content");
}

#[tokio::test]
async fn test_read_file_mmap_large_file() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("large.txt");

    // Create a file larger than 1MB threshold
    let large_content = "x".repeat(1024 * 1024 + 100);
    std::fs::write(&file_path, &large_content).unwrap();

    let core = FileIOCore::default();
    let content = core.read_file_mmap(&file_path).await.unwrap();
    assert_eq!(content, large_content);
}

#[tokio::test]
async fn test_read_file_mmap_large_non_utf8_matches_existing_decode_contract() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("large-windows-1252.txt");

    let mut bytes = vec![0xA9; 1024 * 1024 + 100];
    bytes.extend_from_slice(b" mmap contract");
    std::fs::write(&file_path, &bytes).unwrap();

    let core = FileIOCore::default();
    let expected = core.read_file_with_encoding(&file_path).await.unwrap();
    let mapped = core.read_file_mmap(&file_path).await.unwrap();

    assert_eq!(mapped, expected);
}

// ==================== Encoding Tests ====================

#[tokio::test]
async fn test_read_file_utf8_bom() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("utf8_bom.txt");

    // Write file with UTF-8 BOM
    let mut file = std::fs::File::create(&file_path).unwrap();
    file.write_all(&[0xEF, 0xBB, 0xBF]).unwrap(); // UTF-8 BOM
    file.write_all(b"BOM content").unwrap();

    let core = FileIOCore::default();
    let content = core.read_file(&file_path).await.unwrap();
    // Content should be readable (BOM may or may not be stripped depending on encoding detection)
    assert!(content.contains("BOM content"));
}

#[tokio::test]
async fn test_read_file_windows_1252() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("windows1252.txt");

    // Write Windows-1252 specific characters (copyright symbol = 0xA9)
    std::fs::write(&file_path, [0xA9, 0x20, 0x32, 0x30, 0x32, 0x34]).unwrap();

    let core = FileIOCore::default();
    let result = core.read_file(&file_path).await;
    // Should not error with default "ignore" error handling
    assert!(result.is_ok());
}

// ==================== DDS Header Tests ====================

#[tokio::test]
async fn test_read_dds_header_invalid_file() {
    let temp = TempDir::new().unwrap();
    let file_path = temp.path().join("not_dds.txt");
    std::fs::write(&file_path, "This is not a DDS file").unwrap();

    let core = FileIOCore::default();
    let result = core.read_dds_header(&file_path).await.unwrap();
    assert!(result.is_none());
}

#[test]
fn test_read_dds_headers_batch_empty() {
    let core = FileIOCore::default();
    let results = core.read_dds_headers_batch(vec![]);
    assert!(results.is_empty());
}

#[test]
fn test_read_dds_headers_batch_invalid_files() {
    let temp = TempDir::new().unwrap();
    let paths: Vec<PathBuf> = (0..3)
        .map(|i| {
            let path = temp.path().join(format!("fake{}.dds", i));
            std::fs::write(&path, "Not a DDS file").unwrap();
            path
        })
        .collect();

    let core = FileIOCore::default();
    let results = core.read_dds_headers_batch(paths.clone());

    assert_eq!(results.len(), 3);
    for (path, header) in results {
        assert!(paths.contains(&path));
        assert!(header.is_none());
    }
}
