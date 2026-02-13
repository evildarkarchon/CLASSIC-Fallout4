//! File similarity comparison using longest common subsequence ratio.
//!
//! This module provides file similarity comparison functionality, mirroring Python's
//! `difflib.SequenceMatcher.ratio()` behavior. It compares two text files line-by-line
//! and returns a similarity ratio between 0.0 (completely different) and 1.0 (identical).
//!
//! # Algorithm
//!
//! The similarity ratio is computed using the Longest Common Subsequence (LCS) algorithm.
//! Given two sequences of lines A and B:
//!
//! ```text
//! ratio = (2.0 * LCS_length) / (len(A) + len(B))
//! ```
//!
//! This matches the formula used by Python's `SequenceMatcher.ratio()`.
//!
//! # Examples
//!
//! ```rust,no_run
//! use classic_file_io_core::similarity::calculate_similarity;
//! use std::path::Path;
//!
//! let ratio = calculate_similarity(
//!     Path::new("file1.txt"),
//!     Path::new("file2.txt"),
//! ).unwrap();
//!
//! println!("Similarity: {:.1}%", ratio * 100.0);
//! ```

use std::path::Path;

/// Calculate the similarity ratio between two text files.
///
/// Reads both files as UTF-8 text (with lossy conversion for non-UTF-8 bytes),
/// splits them into lines, and computes the LCS-based similarity ratio.
///
/// # Arguments
///
/// * `path1` - Path to the first file
/// * `path2` - Path to the second file
///
/// # Returns
///
/// A `f64` between 0.0 (completely different) and 1.0 (identical).
/// Returns 0.0 if either file cannot be read.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_file_io_core::similarity::calculate_similarity;
/// use std::path::Path;
///
/// let ratio = calculate_similarity(
///     Path::new("original.ini"),
///     Path::new("modified.ini"),
/// )?;
///
/// if ratio > 0.9 {
///     println!("Files are very similar");
/// }
/// # Ok::<(), std::io::Error>(())
/// ```
pub fn calculate_similarity(path1: &Path, path2: &Path) -> Result<f64, std::io::Error> {
    let content1 = read_file_lossy(path1)?;
    let content2 = read_file_lossy(path2)?;

    Ok(similarity_ratio(&content1, &content2))
}

/// Calculate similarity ratio between two strings.
///
/// This is the pure computation function, useful for testing and cases where
/// file content is already in memory.
///
/// # Arguments
///
/// * `text1` - First text content
/// * `text2` - Second text content
///
/// # Returns
///
/// A `f64` between 0.0 and 1.0 representing the similarity.
#[must_use]
pub fn similarity_ratio(text1: &str, text2: &str) -> f64 {
    if text1 == text2 {
        return 1.0;
    }

    let lines1: Vec<&str> = text1.lines().collect();
    let lines2: Vec<&str> = text2.lines().collect();

    let total = lines1.len() + lines2.len();
    if total == 0 {
        return 1.0; // Both empty
    }

    let lcs_len = longest_common_subsequence_length(&lines1, &lines2);
    (2.0 * lcs_len as f64) / total as f64
}

/// Read a file as a UTF-8 string with lossy conversion.
///
/// Non-UTF-8 bytes are replaced with the Unicode replacement character.
fn read_file_lossy(path: &Path) -> Result<String, std::io::Error> {
    let bytes = std::fs::read(path)?;
    Ok(String::from_utf8_lossy(&bytes).into_owned())
}

/// Compute the length of the longest common subsequence of two line sequences.
///
/// Uses the standard dynamic programming approach with O(m*n) time and O(min(m,n)) space.
fn longest_common_subsequence_length(a: &[&str], b: &[&str]) -> usize {
    let m = a.len();
    let n = b.len();

    // Optimize: use shorter sequence for the DP row
    if m < n {
        return longest_common_subsequence_length_inner(b, a);
    }

    longest_common_subsequence_length_inner(a, b)
}

/// Inner LCS computation where `a` is the longer sequence.
///
/// Uses two rows of DP storage to minimize memory: O(len(b)) space.
fn longest_common_subsequence_length_inner(a: &[&str], b: &[&str]) -> usize {
    let n = b.len();
    let mut prev = vec![0usize; n + 1];
    let mut curr = vec![0usize; n + 1];

    for item_a in a {
        for (j, item_b) in b.iter().enumerate() {
            if item_a == item_b {
                curr[j + 1] = prev[j] + 1;
            } else {
                curr[j + 1] = curr[j].max(prev[j + 1]);
            }
        }
        std::mem::swap(&mut prev, &mut curr);
        curr.fill(0);
    }

    prev[n]
}

#[cfg(test)]
mod tests {
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
}
