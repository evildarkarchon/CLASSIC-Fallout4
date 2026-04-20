use super::*;
use serial_test::serial;
use std::collections::HashSet;
use std::io::Write;
use tempfile::NamedTempFile;

#[test]
#[serial]
fn test_hash_file_basic() -> Result<(), Box<dyn std::error::Error>> {
    // Create temp file with known content
    let mut temp_file = NamedTempFile::new()?;
    temp_file.write_all(b"Hello, World!")?;
    temp_file.flush()?;

    let hash = FileHasher::hash_file(temp_file.path())?;

    // Verify hash length (SHA256 = 64 hex chars)
    assert_eq!(hash.len(), 64);
    // Verify known SHA256 hash of "Hello, World!"
    assert_eq!(
        hash,
        "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
    );

    Ok(())
}

#[test]
#[serial]
fn test_hash_file_caching() -> Result<(), Box<dyn std::error::Error>> {
    FileHasher::clear_cache();
    FileHasher::reset_cache_stats();

    let mut temp_file = NamedTempFile::new()?;
    temp_file.write_all(b"Test caching")?;
    temp_file.flush()?;

    // First call - should cache
    let hash1 = FileHasher::hash_file(temp_file.path())?;
    assert_eq!(FileHasher::cache_size(), 1);
    let miss_stats = FileHasher::cache_stats();
    assert_eq!(miss_stats.misses, 1);
    assert_eq!(miss_stats.hits, 0);
    assert_eq!(miss_stats.size, 1);

    // Second call - should hit cache
    let hash2 = FileHasher::hash_file(temp_file.path())?;
    assert_eq!(hash1, hash2);
    assert_eq!(FileHasher::cache_size(), 1);
    let hit_stats = FileHasher::cache_stats();
    assert_eq!(hit_stats.misses, 1);
    assert_eq!(hit_stats.hits, 1);
    assert_eq!(hit_stats.size, 1);
    assert_eq!(hit_stats.capacity, 1024);
    assert_eq!(hit_stats.hit_rate, 0.5);

    FileHasher::clear_cache();
    assert_eq!(FileHasher::cache_size(), 0);

    Ok(())
}

#[test]
fn test_hash_nonexistent_file() {
    let result = FileHasher::hash_file(Path::new("nonexistent_file.txt"));
    assert!(result.is_err());
    assert!(matches!(result.unwrap_err(), FileIOError::NotFound(_)));
}

#[test]
#[serial]
fn test_hash_files_parallel() -> Result<(), Box<dyn std::error::Error>> {
    FileHasher::clear_cache();

    // Create multiple temp files
    let mut files = Vec::new();
    let mut temp_files = Vec::new();

    for i in 0..5 {
        let mut temp_file = NamedTempFile::new()?;
        temp_file.write_all(format!("Content {}", i).as_bytes())?;
        temp_file.flush()?;
        files.push(temp_file.path().to_path_buf());
        temp_files.push(temp_file); // Keep alive
    }

    let paths: Vec<&Path> = files.iter().map(|p| p.as_path()).collect();
    let results = FileHasher::hash_files_parallel(&paths)?;

    // Verify all succeeded
    assert_eq!(results.len(), 5);
    for (_, hash_opt) in &results {
        assert!(hash_opt.is_some());
        assert_eq!(hash_opt.as_ref().unwrap().len(), 64);
    }

    Ok(())
}

#[test]
#[serial]
fn test_hash_files_to_map() -> Result<(), Box<dyn std::error::Error>> {
    FileHasher::clear_cache();

    let mut temp_file = NamedTempFile::new()?;
    temp_file.write_all(b"Map test")?;
    temp_file.flush()?;

    let paths = vec![temp_file.path()];
    let map = FileHasher::hash_files_to_map(&paths)?;

    assert_eq!(map.len(), 1);
    assert!(map.contains_key(temp_file.path()));
    assert_eq!(map.get(temp_file.path()).unwrap().len(), 64);

    Ok(())
}

#[test]
#[serial]
fn test_large_file_chunked_reading() -> Result<(), Box<dyn std::error::Error>> {
    // Create file larger than chunk size
    let mut temp_file = NamedTempFile::new()?;
    let data = vec![0u8; HASH_CHUNK_SIZE * 3]; // 3x chunk size
    temp_file.write_all(&data)?;
    temp_file.flush()?;

    let hash = FileHasher::hash_file(temp_file.path())?;

    // Verify hash was calculated successfully
    assert_eq!(hash.len(), 64);

    Ok(())
}

#[test]
#[serial]
fn test_hash_cache_stats_reset_preserves_cache_entries() -> Result<(), Box<dyn std::error::Error>> {
    FileHasher::clear_cache();
    FileHasher::reset_cache_stats();

    let mut temp_file = NamedTempFile::new()?;
    temp_file.write_all(b"stats reset")?;
    temp_file.flush()?;

    FileHasher::hash_file(temp_file.path())?;
    assert_eq!(FileHasher::cache_size(), 1);

    FileHasher::reset_cache_stats();
    let stats = FileHasher::cache_stats();
    assert_eq!(stats.hits, 0);
    assert_eq!(stats.misses, 0);
    assert_eq!(stats.size, 1);
    assert_eq!(stats.capacity, 1024);

    Ok(())
}

#[test]
#[serial]
fn test_hash_clear_cache_empties_entries_without_resetting_stats()
-> Result<(), Box<dyn std::error::Error>> {
    FileHasher::clear_cache();
    FileHasher::reset_cache_stats();

    let mut temp_file = NamedTempFile::new()?;
    temp_file.write_all(b"clear cache")?;
    temp_file.flush()?;

    FileHasher::hash_file(temp_file.path())?;
    let before_clear = FileHasher::cache_stats();
    assert_eq!(before_clear.size, 1);
    assert_eq!(before_clear.misses, 1);

    FileHasher::clear_cache();
    let after_clear = FileHasher::cache_stats();
    assert_eq!(after_clear.size, 0);
    assert_eq!(after_clear.capacity, 1024);
    assert_eq!(after_clear.misses, 1);
    assert_eq!(after_clear.hits, 0);

    Ok(())
}

#[test]
#[serial]
fn test_hash_cache_bounded_eviction() -> Result<(), Box<dyn std::error::Error>> {
    FileHasher::clear_cache();
    FileHasher::reset_cache_stats();

    let mut temp_files = Vec::new();
    let mut first_hash = None;

    for index in 0..1025 {
        let mut temp_file = NamedTempFile::new()?;
        temp_file.write_all(format!("bounded-cache-{index}").as_bytes())?;
        temp_file.flush()?;

        let hash = FileHasher::hash_file(temp_file.path())?;
        if index == 0 {
            first_hash = Some((temp_file.path().to_path_buf(), hash));
        }
        temp_files.push(temp_file);
    }

    let stats = FileHasher::cache_stats();
    assert_eq!(stats.capacity, 1024);
    assert!(stats.size <= stats.capacity);
    assert!(stats.size < 1025);
    assert_eq!(stats.misses, 1025);
    assert_eq!(stats.hits, 0);

    let (first_path, original_hash) = first_hash.expect("first file should exist");
    let rehashed = FileHasher::hash_file(&first_path)?;
    assert_eq!(rehashed, original_hash);

    let after_rehash = FileHasher::cache_stats();
    assert!(after_rehash.size <= after_rehash.capacity);
    assert_eq!(after_rehash.capacity, 1024);
    assert!(after_rehash.hits + after_rehash.misses >= 1026);
    assert!(after_rehash.misses >= 1025);

    let distinct_hashes = temp_files
        .iter()
        .map(|file| FileHasher::hash_file(file.path()))
        .collect::<Result<HashSet<_>, _>>()?;
    assert_eq!(distinct_hashes.len(), 1025);

    Ok(())
}
