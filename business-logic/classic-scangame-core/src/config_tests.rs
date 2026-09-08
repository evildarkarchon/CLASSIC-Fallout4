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

#[test]
fn scan_publishes_groups_and_invalidates_reused_file_hashes() {
    let directory = TempDir::new().unwrap();
    let first = directory.path().join("a/F4EE.ini");
    let second = directory.path().join("b/F4EE.ini");
    fs::create_dir_all(first.parent().unwrap()).unwrap();
    fs::create_dir_all(second.parent().unwrap()).unwrap();
    fs::write(&first, "[First]\nkey=1\n").unwrap();
    fs::write(&second, "[First]\nkey=1\n").unwrap();
    let mut detector = ConfigDuplicateDetector::new();

    let returned = detector.scan_directory(directory.path()).unwrap();
    assert_eq!(returned["f4ee.ini"], vec![first.clone(), second.clone()]);
    let group = &detector.get_duplicates()["f4ee.ini"];
    assert_eq!(group.canonical, first);
    assert_eq!(group.duplicates, vec![second.clone()]);
    assert_eq!(group.hash, calculate_file_hash(&group.canonical).unwrap());

    fs::write(
        &second,
        "[DifferentSection]\nunrelated=abcdefghijklmnopqrstuvwxyz\n",
    )
    .unwrap();
    assert!(
        detector
            .scan_directory(directory.path())
            .unwrap()
            .is_empty()
    );
    assert!(detector.get_duplicates().is_empty());
}

#[test]
fn failed_rescan_does_not_expose_old_duplicate_groups() {
    let directory = TempDir::new().unwrap();
    let first = directory.path().join("a/F4EE.ini");
    let second = directory.path().join("b/F4EE.ini");
    fs::create_dir_all(first.parent().unwrap()).unwrap();
    fs::create_dir_all(second.parent().unwrap()).unwrap();
    fs::write(&first, "[First]\nkey=1\n").unwrap();
    fs::write(&second, "[First]\nkey=1\n").unwrap();
    let mut detector = ConfigDuplicateDetector::new();
    detector.scan_directory(directory.path()).unwrap();
    assert!(!detector.get_duplicates().is_empty());
    fs::write(&second, [0xff; 80]).unwrap();
    assert!(detector.scan_directory(directory.path()).is_err());
    assert!(detector.get_duplicates().is_empty());
}
