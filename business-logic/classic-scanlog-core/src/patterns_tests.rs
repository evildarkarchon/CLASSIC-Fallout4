use super::*;

// ============================================
// PatternMatcher creation tests
// ============================================

#[test]
fn test_pattern_matcher_new_empty() {
    let matcher = PatternMatcher::new(vec![]).unwrap();
    assert_eq!(matcher.get_stats(), (0, 0));
}

#[test]
fn test_pattern_matcher_new_single_pattern() {
    let patterns = vec!["ACCESS_VIOLATION".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    assert_eq!(matcher.get_stats(), (1, 0));
}

#[test]
fn test_pattern_matcher_new_multiple_patterns() {
    let patterns = vec![
        "ACCESS_VIOLATION".to_string(),
        "STACK_OVERFLOW".to_string(),
        "BREAKPOINT".to_string(),
    ];
    let matcher = PatternMatcher::new(patterns).unwrap();
    assert_eq!(matcher.get_stats(), (3, 0));
}

// ============================================
// has_match tests
// ============================================

#[test]
fn test_has_match_true() {
    let patterns = vec!["ERROR".to_string(), "FAULT".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    assert!(matcher.has_match("An ERROR occurred"));
}

#[test]
fn test_has_match_false() {
    let patterns = vec!["ERROR".to_string(), "FAULT".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    assert!(!matcher.has_match("Everything is fine"));
}

#[test]
fn test_has_match_case_insensitive() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    assert!(matcher.has_match("An ERROR occurred"));
    assert!(matcher.has_match("an error occurred"));
    assert!(matcher.has_match("An Error Occurred"));
}

#[test]
fn test_has_match_empty_patterns() {
    let matcher = PatternMatcher::new(vec![]).unwrap();
    // With empty patterns, should not match anything
    assert!(!matcher.has_match("Some text"));
}

#[test]
fn test_has_match_partial() {
    let patterns = vec!["VIOLATION".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    assert!(matcher.has_match("ACCESS_VIOLATION at 0x12345"));
}

// ============================================
// find_first tests
// ============================================

#[test]
fn test_find_first_match() {
    let patterns = vec!["ERROR".to_string(), "FAULT".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    let result = matcher.find_first("An ERROR occurred");
    assert!(result.is_some());
    let (pos, pattern) = result.unwrap();
    assert_eq!(pos, 3); // "An " is 3 chars
    assert_eq!(pattern.to_lowercase(), "error");
}

#[test]
fn test_find_first_no_match() {
    let patterns = vec!["ERROR".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    assert!(matcher.find_first("Everything fine").is_none());
}

#[test]
fn test_find_first_multiple_patterns() {
    let patterns = vec!["FIRST".to_string(), "SECOND".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    let result = matcher.find_first("Start FIRST then SECOND");
    assert!(result.is_some());
    let (pos, _) = result.unwrap();
    assert_eq!(pos, 6); // "Start " is 6 chars
}

// ============================================
// find_all tests
// ============================================

#[test]
fn test_find_all_single_match() {
    let patterns = vec!["ERROR".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    let matches = matcher.find_all("An ERROR occurred");
    assert_eq!(matches.len(), 1);
    assert_eq!(matches[0].0, 3);
}

#[test]
fn test_find_all_multiple_matches() {
    let patterns = vec!["ERROR".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    let matches = matcher.find_all("ERROR first, then ERROR again");
    assert_eq!(matches.len(), 2);
}

#[test]
fn test_find_all_different_patterns() {
    let patterns = vec!["ERROR".to_string(), "FAULT".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    let matches = matcher.find_all("ERROR and FAULT detected");
    assert_eq!(matches.len(), 2);
}

#[test]
fn test_find_all_no_matches() {
    let patterns = vec!["ERROR".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    let matches = matcher.find_all("Everything is fine");
    assert!(matches.is_empty());
}

#[test]
fn test_find_all_empty_text() {
    let patterns = vec!["ERROR".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    let matches = matcher.find_all("");
    assert!(matches.is_empty());
}

// ============================================
// replace_all tests
// ============================================

#[test]
fn test_replace_all_single() {
    let patterns = vec!["ERROR".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    let result = matcher.replace_all("An ERROR occurred", "[REDACTED]");
    assert_eq!(result, "An [REDACTED] occurred");
}

#[test]
fn test_replace_all_multiple() {
    let patterns = vec!["ERROR".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    let result = matcher.replace_all("ERROR then ERROR again", "X");
    assert_eq!(result, "X then X again");
}

#[test]
fn test_replace_all_different_patterns() {
    let patterns = vec!["ERROR".to_string(), "FAULT".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    let result = matcher.replace_all("ERROR and FAULT", "ISSUE");
    assert_eq!(result, "ISSUE and ISSUE");
}

#[test]
fn test_replace_all_no_match() {
    let patterns = vec!["ERROR".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    let result = matcher.replace_all("Everything fine", "X");
    assert_eq!(result, "Everything fine");
}

#[test]
fn test_replace_all_case_insensitive() {
    let patterns = vec!["error".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    let result = matcher.replace_all("ERROR occurred", "ISSUE");
    assert_eq!(result, "ISSUE occurred");
}

// ============================================
// Cache tests
// ============================================

#[test]
fn test_cache_hit() {
    let patterns = vec!["ERROR".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    // First call populates cache
    let matches1 = matcher.find_all("An ERROR occurred");

    // Second call should hit cache
    let matches2 = matcher.find_all("An ERROR occurred");

    assert_eq!(matches1, matches2);
    assert_eq!(matcher.get_stats().1, 1); // 1 cached entry
}

#[test]
fn test_clear_cache() {
    let patterns = vec!["ERROR".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();

    // Populate cache
    let _ = matcher.find_all("An ERROR occurred");
    assert_eq!(matcher.get_stats().1, 1);

    // Clear cache
    matcher.clear_cache();
    assert_eq!(matcher.get_stats().1, 0);
}

// ============================================
// Edge case tests
// ============================================

#[test]
fn test_pattern_with_special_chars() {
    // Aho-Corasick treats patterns as literal strings
    let patterns = vec!["[ERROR]".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    assert!(matcher.has_match("Some [ERROR] here"));
    assert!(!matcher.has_match("Some ERROR here"));
}

#[test]
fn test_overlapping_patterns() {
    // Aho-Corasick uses non-overlapping leftmost-first matching by default
    // In "ABC", "AB" is found at 0, but "BC" overlaps at 1 so it's skipped
    let patterns = vec!["AB".to_string(), "BC".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    // With non-overlapping semantics, only "AB" is matched
    let matches = matcher.find_all("ABC");
    assert_eq!(matches.len(), 1);
    assert_eq!(matches[0].0, 0);
}

#[test]
fn test_non_overlapping_patterns() {
    // Test that non-overlapping patterns are all found
    let patterns = vec!["AB".to_string(), "CD".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    let matches = matcher.find_all("AB CD");
    assert_eq!(matches.len(), 2);
}

#[test]
fn test_long_text() {
    let patterns = vec!["NEEDLE".to_string()];
    let matcher = PatternMatcher::new(patterns).unwrap();
    let long_text = format!("{}NEEDLE{}", "X".repeat(10000), "Y".repeat(10000));
    assert!(matcher.has_match(&long_text));
}
