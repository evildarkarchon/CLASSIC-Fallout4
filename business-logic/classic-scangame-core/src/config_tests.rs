use super::*;
use std::fs;
use tempfile::TempDir;

#[test]
fn test_hash_calculation() {
    let temp_dir = TempDir::new().unwrap();
    let file_path = temp_dir.path().join("test.ini");
    fs::write(&file_path, b"test content").unwrap();

    let hash = calculate_file_hash(&file_path).unwrap();
    assert!(!hash.is_empty());
    assert_eq!(hash.len(), 64); // SHA256 produces 64 hex characters
}

#[test]
fn test_similarity_identical_files() {
    let temp_dir = TempDir::new().unwrap();
    let file1 = temp_dir.path().join("test1.ini");
    let file2 = temp_dir.path().join("test2.ini");

    let content = "[Section]\nkey=value\n";
    fs::write(&file1, content).unwrap();
    fs::write(&file2, content).unwrap();

    let similarity = calculate_text_similarity(&file1, &file2).unwrap();
    assert_eq!(similarity, 1.0);
}

#[test]
fn test_detector_creation() {
    let detector = ConfigDuplicateDetector::new();
    assert_eq!(detector.whitelist.len(), 1);
    assert_eq!(detector.whitelist[0], "F4EE");
}
