//! Comprehensive tests for the pattern matching module
//!
//! This module tests the PatternMatcher implementation with:
//! - Basic pattern matching functionality
//! - Multi-pattern matching with Aho-Corasick
//! - Cache effectiveness and management
//! - Case-insensitive matching
//! - Edge cases (empty patterns, invalid input, special characters)
//! - Performance characteristics
//! - PyO3 Python integration

use classic_core::scanlog::PatternMatcher;
use std::time::Instant;

// ===== Unit Tests (Pure Rust) =====

#[test]
fn test_pattern_matcher_creation_basic() {
    let patterns = vec!["error".to_string(), "warning".to_string(), "info".to_string()];
    let matcher = PatternMatcher::new(patterns.clone()).unwrap();

    let (pattern_count, cache_size) = matcher.get_stats();
    assert_eq!(pattern_count, 3);
    assert_eq!(cache_size, 0); // Cache starts empty
}

#[test]
fn test_pattern_matcher_creation_empty() {
    let patterns: Vec<String> = vec![];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let (pattern_count, _) = matcher.get_stats();
    assert_eq!(pattern_count, 0);
}

#[test]
fn test_pattern_matcher_creation_single() {
    let patterns = vec!["single_pattern".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let (pattern_count, _) = matcher.get_stats();
    assert_eq!(pattern_count, 1);
}

// ===== Basic Matching Tests =====

#[test]
fn test_has_match_simple() {
    let patterns = vec!["error".to_string(), "warning".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    assert!(matcher.has_match("This is an error message"));
    assert!(matcher.has_match("Warning: something happened"));
    assert!(!matcher.has_match("This is just info"));
}

#[test]
fn test_has_match_case_insensitive() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    // Should match regardless of case
    assert!(matcher.has_match("ERROR"));
    assert!(matcher.has_match("Error"));
    assert!(matcher.has_match("eRrOr"));
    assert!(matcher.has_match("error"));
}

#[test]
fn test_has_match_empty_text() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    assert!(!matcher.has_match(""));
}

#[test]
fn test_has_match_no_patterns() {
    let patterns: Vec<String> = vec![];
    let matcher = PatternMatcher::new(patterns).unwrap();

    assert!(!matcher.has_match("Any text here"));
}

// ===== Find First Tests =====

#[test]
fn test_find_first_basic() {
    let patterns = vec!["error".to_string(), "warning".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let result = matcher.find_first("This is an error at position 11");
    assert!(result.is_some());

    let (position, pattern) = result.unwrap();
    assert_eq!(position, 11);
    assert_eq!(pattern, "error");
}

#[test]
fn test_find_first_multiple_matches() {
    let patterns = vec!["error".to_string(), "warning".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    // Should find the first occurrence (earliest position)
    let result = matcher.find_first("warning and error both present");
    assert!(result.is_some());

    let (position, pattern) = result.unwrap();
    assert_eq!(position, 0); // "warning" starts at 0
    assert_eq!(pattern, "warning");
}

#[test]
fn test_find_first_no_match() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let result = matcher.find_first("Nothing to find here");
    assert!(result.is_none());
}

#[test]
fn test_find_first_case_insensitive() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let result = matcher.find_first("Found ERROR at position 6");
    assert!(result.is_some());

    let (position, pattern) = result.unwrap();
    assert_eq!(position, 6);
    assert_eq!(pattern, "error");
}

// ===== Find All Tests =====

#[test]
fn test_find_all_single_match() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let matches = matcher.find_all("This is an error message");
    assert_eq!(matches.len(), 1);
    assert_eq!(matches[0].0, 11); // Position
    assert_eq!(matches[0].1, "error"); // Pattern
}

#[test]
fn test_find_all_multiple_patterns() {
    let patterns = vec![
        "error".to_string(),
        "warning".to_string(),
        "info".to_string()
    ];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let text = "error at start, warning in middle, info at end";
    let matches = matcher.find_all(text);

    assert_eq!(matches.len(), 3);

    // Verify all patterns found
    let found_patterns: Vec<&str> = matches.iter().map(|(_, p)| p.as_str()).collect();
    assert!(found_patterns.contains(&"error"));
    assert!(found_patterns.contains(&"warning"));
    assert!(found_patterns.contains(&"info"));
}

#[test]
fn test_find_all_duplicate_patterns() {
    let patterns = vec!["test".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let matches = matcher.find_all("test test test");
    assert_eq!(matches.len(), 3);

    // Verify positions
    assert_eq!(matches[0].0, 0);
    assert_eq!(matches[1].0, 5);
    assert_eq!(matches[2].0, 10);
}

#[test]
fn test_find_all_overlapping_patterns() {
    let patterns = vec!["abc".to_string(), "bcd".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    // Aho-Corasick finds overlapping matches
    let matches = matcher.find_all("abcd");

    // Should find "abc" at position 0
    assert!(matches.iter().any(|(pos, pat)| *pos == 0 && pat == "abc"));
}

#[test]
fn test_find_all_no_matches() {
    let patterns = vec!["error".to_string(), "warning".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let matches = matcher.find_all("Nothing to find here");
    assert_eq!(matches.len(), 0);
}

#[test]
fn test_find_all_empty_text() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let matches = matcher.find_all("");
    assert_eq!(matches.len(), 0);
}

// ===== Replace All Tests =====

#[test]
fn test_replace_all_basic() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let result = matcher.replace_all("This is an error message", "SUCCESS");
    assert_eq!(result, "This is an SUCCESS message");
}

#[test]
fn test_replace_all_multiple_occurrences() {
    let patterns = vec!["test".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let result = matcher.replace_all("test test test", "PASS");
    assert_eq!(result, "PASS PASS PASS");
}

#[test]
fn test_replace_all_multiple_patterns() {
    let patterns = vec!["error".to_string(), "warning".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    // All patterns replaced with same string
    let result = matcher.replace_all("error and warning both replaced", "REDACTED");
    assert_eq!(result, "REDACTED and REDACTED both replaced");
}

#[test]
fn test_replace_all_case_insensitive() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let result = matcher.replace_all("ERROR and error both replaced", "OK");
    assert_eq!(result, "OK and OK both replaced");
}

#[test]
fn test_replace_all_no_matches() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let original = "Nothing to replace here";
    let result = matcher.replace_all(original, "REPLACEMENT");
    assert_eq!(result, original);
}

#[test]
fn test_replace_all_empty_replacement() {
    let patterns = vec!["test".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let result = matcher.replace_all("test this test", "");
    assert_eq!(result, " this ");
}

// ===== Cache Tests =====

#[test]
fn test_cache_population() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let (_, cache_size_before) = matcher.get_stats();
    assert_eq!(cache_size_before, 0);

    // First call - populates cache
    let _ = matcher.find_all("This is an error");

    let (_, cache_size_after) = matcher.get_stats();
    assert_eq!(cache_size_after, 1);
}

#[test]
fn test_cache_hit() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let text = "This is an error message";

    // First call - cache miss
    let matches1 = matcher.find_all(text);

    // Second call - cache hit (should return same results)
    let matches2 = matcher.find_all(text);

    assert_eq!(matches1, matches2);

    let (_, cache_size) = matcher.get_stats();
    assert_eq!(cache_size, 1);
}

#[test]
fn test_cache_multiple_texts() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let texts = vec![
        "First error",
        "Second error",
        "Third error",
    ];

    for text in &texts {
        let _ = matcher.find_all(text);
    }

    let (_, cache_size) = matcher.get_stats();
    assert_eq!(cache_size, 3);
}

#[test]
fn test_cache_clear() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    // Populate cache
    let _ = matcher.find_all("error 1");
    let _ = matcher.find_all("error 2");
    let _ = matcher.find_all("error 3");

    let (_, cache_size_before) = matcher.get_stats();
    assert_eq!(cache_size_before, 3);

    // Clear cache
    matcher.clear_cache();

    let (_, cache_size_after) = matcher.get_stats();
    assert_eq!(cache_size_after, 0);
}

#[test]
fn test_cache_independence() {
    let patterns = vec!["test".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let text1 = "prefix test suffix";
    let text2 = "another prefix test another suffix";

    let matches1 = matcher.find_all(text1);
    let matches2 = matcher.find_all(text2);

    // Different texts should have different cached results (different positions)
    assert_ne!(matches1[0].0, matches2[0].0);

    let (_, cache_size) = matcher.get_stats();
    assert_eq!(cache_size, 2);
}

// ===== Edge Cases =====

#[test]
fn test_special_characters_in_patterns() {
    // Aho-Corasick treats patterns as literal strings, not regex
    let patterns = vec![
        "error[0]".to_string(),
        "warning*".to_string(),
        "info+test".to_string(),
    ];
    let matcher = PatternMatcher::new(patterns).unwrap();

    assert!(matcher.has_match("Found error[0] here"));
    assert!(matcher.has_match("Found warning* here"));
    assert!(matcher.has_match("Found info+test here"));
}

#[test]
fn test_unicode_patterns() {
    let patterns = vec![
        "错误".to_string(),  // Chinese for "error"
        "エラー".to_string(),  // Japanese for "error"
        "ошибка".to_string(),  // Russian for "error"
    ];
    let matcher = PatternMatcher::new(patterns).unwrap();

    assert!(matcher.has_match("Found 错误 in text"));
    assert!(matcher.has_match("Found エラー in text"));
    assert!(matcher.has_match("Found ошибка in text"));
}

#[test]
fn test_whitespace_patterns() {
    let patterns = vec![
        "error ".to_string(),  // Pattern with trailing space
        " warning".to_string(), // Pattern with leading space
        "info\t".to_string(),   // Pattern with tab
    ];
    let matcher = PatternMatcher::new(patterns).unwrap();

    assert!(matcher.has_match("This is error code"));
    assert!(matcher.has_match("This is warning message"));
    assert!(matcher.has_match("This is info\tdata"));
}

#[test]
fn test_very_long_pattern() {
    let long_pattern = "a".repeat(1000);
    let patterns = vec![long_pattern.clone()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let text = format!("prefix {} suffix", long_pattern);
    assert!(matcher.has_match(&text));
}

#[test]
fn test_very_long_text() {
    let patterns = vec!["needle".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    // Create very long text with needle in the middle
    let prefix = "x".repeat(10000);
    let long_text = format!("{}needle{}", prefix, "y".repeat(10000));

    let matches = matcher.find_all(&long_text);
    assert_eq!(matches.len(), 1);
    assert_eq!(matches[0].0, prefix.len()); // Position right after prefix
}

#[test]
fn test_many_patterns() {
    // Test with a large number of patterns
    let patterns: Vec<String> = (0..1000)
        .map(|i| format!("pattern{}", i))
        .collect();

    let matcher = PatternMatcher::new(patterns.clone()).unwrap();

    let (pattern_count, _) = matcher.get_stats();
    assert_eq!(pattern_count, 1000);

    // Should find specific pattern
    assert!(matcher.has_match("Found pattern500 here"));
}

#[test]
fn test_duplicate_patterns_in_list() {
    let patterns = vec![
        "error".to_string(),
        "error".to_string(),  // Duplicate
        "warning".to_string(),
    ];
    let matcher = PatternMatcher::new(patterns).unwrap();

    // Aho-Corasick handles duplicates, but counts them
    let (pattern_count, _) = matcher.get_stats();
    assert_eq!(pattern_count, 3); // Includes duplicate
}

#[test]
fn test_substring_patterns() {
    let patterns = vec![
        "test".to_string(),
        "testing".to_string(),  // "testing" contains "test"
    ];
    let matcher = PatternMatcher::new(patterns).unwrap();

    // Should find both patterns in "testing"
    let matches = matcher.find_all("testing");
    assert!(matches.len() >= 1);
}

// ===== Performance Tests =====

#[test]
fn test_performance_many_matches() {
    let patterns = vec!["test".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    // Text with many occurrences
    let text = (0..1000).map(|_| "test ").collect::<String>();

    let start = Instant::now();
    let matches = matcher.find_all(&text);
    let elapsed = start.elapsed();

    assert_eq!(matches.len(), 1000);
    println!("Found 1000 matches in {:?}", elapsed);
}

#[test]
fn test_performance_cache_benefit() {
    let patterns = vec!["error".to_string(), "warning".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let text = "error and warning both present ".repeat(100);

    // First call - no cache
    let start = Instant::now();
    let _ = matcher.find_all(&text);
    let first_time = start.elapsed();

    // Second call - with cache
    let start = Instant::now();
    let _ = matcher.find_all(&text);
    let cached_time = start.elapsed();

    println!("First call: {:?}, Cached call: {:?}", first_time, cached_time);

    // Cached call should be faster (usually much faster)
    // Note: This is not guaranteed due to system variance, so we just print
}

#[test]
#[ignore] // Run with --ignored flag for benchmarks
fn bench_find_all_large_text() {
    let patterns = vec![
        "error".to_string(),
        "warning".to_string(),
        "info".to_string(),
        "debug".to_string(),
    ];
    let matcher = PatternMatcher::new(patterns).unwrap();

    let sizes = vec![1000, 10000, 100000, 1000000];

    for size in sizes {
        let text = "error warning info debug ".repeat(size / 25);

        let start = Instant::now();
        let matches = matcher.find_all(&text);
        let elapsed = start.elapsed();

        println!("Text size: {} chars, Matches: {}, Time: {:?}",
                 text.len(), matches.len(), elapsed);
    }
}

#[test]
#[ignore]
fn bench_many_patterns() {
    let sizes = vec![10, 100, 1000];

    for size in sizes {
        let patterns: Vec<String> = (0..size)
            .map(|i| format!("pattern{}", i))
            .collect();

        let matcher = PatternMatcher::new(patterns).unwrap();

        let text = "pattern500 appears here";

        let start = Instant::now();
        let matches = matcher.find_all(text);
        let elapsed = start.elapsed();

        println!("Pattern count: {}, Matches: {}, Time: {:?}",
                 size, matches.len(), elapsed);
    }
}

// ===== PyO3 Integration Tests =====

#[cfg(test)]
mod pyo3_tests {
    use pyo3::prelude::*;
    use pyo3::types::PyList;

    // Helper to create PatternMatcher instance via Python
    fn with_pattern_matcher<F>(patterns: Vec<String>, test_fn: F)
    where
        F: FnOnce(Python, Bound<PyAny>),
    {
        pyo3::Python::initialize();
        Python::attach(|py| {
            // Create the Rust module
            let module = pyo3::types::PyModule::new(py, "classic_core_scanlog").unwrap();
            classic_core::scanlog::register_module(&module).unwrap();

            let matcher_class = module.getattr("PatternMatcher").unwrap();

            // Convert Rust Vec to Python list
            let py_patterns = PyList::new(py, patterns.iter().map(|s| s.as_str())).unwrap();

            let matcher = matcher_class.call1((py_patterns,)).unwrap();

            test_fn(py, matcher);
        });
    }

    #[test]
    fn test_pyo3_creation() {
        let patterns = vec!["error".to_string(), "warning".to_string()];
        with_pattern_matcher(patterns, |_py, _matcher| {
            // If we got here, creation succeeded
            assert!(true);
        });
    }

    #[test]
    fn test_pyo3_has_match() {
        let patterns = vec!["error".to_string()];
        with_pattern_matcher(patterns, |_py, matcher| {
            let result = matcher.call_method1("has_match", ("This is an error",)).unwrap();
            assert!(result.extract::<bool>().unwrap());
        });
    }

    #[test]
    fn test_pyo3_find_first() {
        let patterns = vec!["error".to_string()];
        with_pattern_matcher(patterns, |_py, matcher| {
            let result = matcher.call_method1("find_first", ("error at start",)).unwrap();
            assert!(!result.is_none());

            // Result should be tuple of (position, pattern)
            let (pos, pattern): (usize, String) = result.extract().unwrap();
            assert_eq!(pos, 0);
            assert_eq!(pattern, "error");
        });
    }

    #[test]
    fn test_pyo3_find_all() {
        let patterns = vec!["test".to_string()];
        with_pattern_matcher(patterns, |_py, matcher| {
            let result = matcher.call_method1("find_all", ("test test test",)).unwrap();

            // Result should be list of tuples
            let matches: Vec<(usize, String)> = result.extract().unwrap();
            assert_eq!(matches.len(), 3);
        });
    }

    #[test]
    fn test_pyo3_replace_all() {
        let patterns = vec!["error".to_string()];
        with_pattern_matcher(patterns, |_py, matcher| {
            let result = matcher.call_method1("replace_all", ("error message", "SUCCESS")).unwrap();
            let result_str = result.extract::<String>().unwrap();
            assert_eq!(result_str, "SUCCESS message");
        });
    }

    #[test]
    fn test_pyo3_get_stats() {
        let patterns = vec!["error".to_string(), "warning".to_string()];
        with_pattern_matcher(patterns, |_py, matcher| {
            let stats = matcher.call_method0("get_stats").unwrap();
            let (pattern_count, cache_size): (usize, usize) = stats.extract().unwrap();

            assert_eq!(pattern_count, 2);
            assert_eq!(cache_size, 0); // Cache starts empty
        });
    }

    #[test]
    fn test_pyo3_clear_cache() {
        let patterns = vec!["test".to_string()];
        with_pattern_matcher(patterns, |_py, matcher| {
            // Populate cache
            let _ = matcher.call_method1("find_all", ("test text",)).unwrap();

            let stats1 = matcher.call_method0("get_stats").unwrap();
            let (_, cache_size_before): (usize, usize) = stats1.extract().unwrap();
            assert_eq!(cache_size_before, 1);

            // Clear cache
            matcher.call_method0("clear_cache").unwrap();

            let stats2 = matcher.call_method0("get_stats").unwrap();
            let (_, cache_size_after): (usize, usize) = stats2.extract().unwrap();
            assert_eq!(cache_size_after, 0);
        });
    }

    #[test]
    fn test_pyo3_error_handling_empty_patterns() {
        pyo3::Python::initialize();
        Python::attach(|py| {
            let module = pyo3::types::PyModule::new(py, "classic_core_scanlog").unwrap();
            classic_core::scanlog::register_module(&module).unwrap();

            let matcher_class = module.getattr("PatternMatcher").unwrap();

            // Create with empty list
            let empty_list = PyList::new(py, &[] as &[&str]).unwrap();
            let matcher = matcher_class.call1((empty_list,));

            // Should succeed with empty patterns
            assert!(matcher.is_ok());
        });
    }

    #[test]
    fn test_pyo3_unicode_handling() {
        let patterns = vec!["错误".to_string()];
        with_pattern_matcher(patterns, |_py, matcher| {
            let result = matcher.call_method1("has_match", ("Found 错误 here",)).unwrap();
            assert!(result.extract::<bool>().unwrap());
        });
    }

    #[test]
    fn test_pyo3_cache_across_calls() {
        let patterns = vec!["test".to_string()];
        with_pattern_matcher(patterns, |_py, matcher| {
            let text = "test message";

            // First call
            let matches1 = matcher.call_method1("find_all", (text,)).unwrap();

            // Second call (should use cache)
            let matches2 = matcher.call_method1("find_all", (text,)).unwrap();

            // Both should have same results
            let m1: Vec<(usize, String)> = matches1.extract().unwrap();
            let m2: Vec<(usize, String)> = matches2.extract().unwrap();
            assert_eq!(m1, m2);

            // Cache should have one entry
            let stats = matcher.call_method0("get_stats").unwrap();
            let (_, cache_size): (usize, usize) = stats.extract().unwrap();
            assert_eq!(cache_size, 1);
        });
    }
}
