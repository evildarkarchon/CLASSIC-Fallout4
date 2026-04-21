use super::*;
use std::io::Write;

#[test]
fn test_identical_files() {
    let dir = tempfile::tempdir().unwrap();
    let path1 = dir.path().join("file1.txt");
    let path2 = dir.path().join("file2.txt");

    let content = "line 1\nline 2\nline 3\n";
    std::fs::write(&path1, content).unwrap();
    std::fs::write(&path2, content).unwrap();

    let ratio = calculate_similarity(&path1, &path2).unwrap();
    assert!(
        (ratio - 1.0).abs() < f64::EPSILON,
        "Identical files should have ratio 1.0, got {}",
        ratio
    );
}

#[test]
fn test_completely_different_files() {
    let dir = tempfile::tempdir().unwrap();
    let path1 = dir.path().join("file1.txt");
    let path2 = dir.path().join("file2.txt");

    std::fs::write(&path1, "aaa\nbbb\nccc\n").unwrap();
    std::fs::write(&path2, "xxx\nyyy\nzzz\n").unwrap();

    let ratio = calculate_similarity(&path1, &path2).unwrap();
    assert!(
        (ratio - 0.0).abs() < f64::EPSILON,
        "Completely different files should have ratio 0.0, got {}",
        ratio
    );
}

#[test]
fn test_partially_similar_files() {
    let dir = tempfile::tempdir().unwrap();
    let path1 = dir.path().join("file1.txt");
    let path2 = dir.path().join("file2.txt");

    std::fs::write(&path1, "line 1\nline 2\nline 3\nline 4\n").unwrap();
    std::fs::write(&path2, "line 1\nmodified\nline 3\nline 4\n").unwrap();

    let ratio = calculate_similarity(&path1, &path2).unwrap();
    // 3 out of 4 lines match: LCS=3, ratio = 2*3/(4+4) = 0.75
    assert!(
        (ratio - 0.75).abs() < f64::EPSILON,
        "Expected 0.75 ratio, got {}",
        ratio
    );
}

#[test]
fn test_empty_files() {
    let dir = tempfile::tempdir().unwrap();
    let path1 = dir.path().join("file1.txt");
    let path2 = dir.path().join("file2.txt");

    std::fs::write(&path1, "").unwrap();
    std::fs::write(&path2, "").unwrap();

    let ratio = calculate_similarity(&path1, &path2).unwrap();
    assert!(
        (ratio - 1.0).abs() < f64::EPSILON,
        "Empty files should have ratio 1.0, got {}",
        ratio
    );
}

#[test]
fn test_one_empty_file() {
    let dir = tempfile::tempdir().unwrap();
    let path1 = dir.path().join("file1.txt");
    let path2 = dir.path().join("file2.txt");

    std::fs::write(&path1, "line 1\nline 2\n").unwrap();
    std::fs::write(&path2, "").unwrap();

    let ratio = calculate_similarity(&path1, &path2).unwrap();
    assert!(
        (ratio - 0.0).abs() < f64::EPSILON,
        "One empty file should have ratio 0.0, got {}",
        ratio
    );
}

#[test]
fn test_missing_file() {
    let dir = tempfile::tempdir().unwrap();
    let path1 = dir.path().join("file1.txt");
    let path2 = dir.path().join("nonexistent.txt");

    std::fs::write(&path1, "content").unwrap();

    let result = calculate_similarity(&path1, &path2);
    assert!(result.is_err());
}

#[test]
fn test_similarity_ratio_pure() {
    assert!((similarity_ratio("a\nb\nc", "a\nb\nc") - 1.0).abs() < f64::EPSILON);
    assert!((similarity_ratio("a\nb\nc", "x\ny\nz") - 0.0).abs() < f64::EPSILON);
    assert!((similarity_ratio("", "") - 1.0).abs() < f64::EPSILON);
}

#[test]
fn test_similarity_ratio_partial() {
    // "a\nb" vs "a\nc" -> LCS=1 ("a"), ratio = 2*1/(2+2) = 0.5
    let ratio = similarity_ratio("a\nb", "a\nc");
    assert!(
        (ratio - 0.5).abs() < f64::EPSILON,
        "Expected 0.5, got {}",
        ratio
    );
}

#[test]
fn test_lcs_basic() {
    let a = vec!["a", "b", "c", "d"];
    let b = vec!["a", "c", "d"];
    assert_eq!(longest_common_subsequence_length(&a, &b), 3);
}

#[test]
fn test_lcs_empty() {
    let a: Vec<&str> = vec![];
    let b = vec!["a", "b"];
    assert_eq!(longest_common_subsequence_length(&a, &b), 0);
}

#[test]
fn test_lcs_no_common() {
    let a = vec!["a", "b"];
    let b = vec!["x", "y"];
    assert_eq!(longest_common_subsequence_length(&a, &b), 0);
}

#[test]
fn test_lossy_encoding() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("binary.txt");

    // Write some bytes including invalid UTF-8
    let mut file = std::fs::File::create(&path).unwrap();
    file.write_all(b"hello\xFFworld\n").unwrap();

    // Should not panic, lossy conversion replaces invalid bytes
    let content = read_file_lossy(&path).unwrap();
    assert!(content.contains("hello"));
    assert!(content.contains("world"));
}
