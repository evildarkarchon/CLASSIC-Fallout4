use super::*;

// ============================================
// RustFormIDAnalyzer creation tests
// ============================================

#[test]
fn test_rust_formid_analyzer_new() {
    let analyzer = RustFormIDAnalyzer::new();
    assert_eq!(analyzer.cache_stats(), (0, 0));
}

#[test]
fn test_rust_formid_analyzer_default() {
    let analyzer = RustFormIDAnalyzer::default();
    assert_eq!(analyzer.cache_stats(), (0, 0));
}

// ============================================
// FormID parsing tests
// ============================================

#[test]
fn test_parse_formid_with_0x_prefix() {
    let analyzer = RustFormIDAnalyzer::new();
    assert_eq!(analyzer.parse_formid("0x0A001234"), Some(0x0A001234));
}

#[test]
fn test_parse_formid_without_prefix() {
    let analyzer = RustFormIDAnalyzer::new();
    assert_eq!(analyzer.parse_formid("0A001234"), Some(0x0A001234));
}

#[test]
fn test_parse_formid_lowercase() {
    let analyzer = RustFormIDAnalyzer::new();
    assert_eq!(analyzer.parse_formid("0xabcdef12"), Some(0xABCDEF12));
}

#[test]
fn test_parse_formid_mixed_case() {
    let analyzer = RustFormIDAnalyzer::new();
    assert_eq!(analyzer.parse_formid("0xAbCdEf12"), Some(0xABCDEF12));
}

#[test]
fn test_parse_formid_short() {
    let analyzer = RustFormIDAnalyzer::new();
    // Shorter FormIDs (like 1-7 hex digits) should still work
    assert_eq!(analyzer.parse_formid("0x1"), Some(0x1));
    assert_eq!(analyzer.parse_formid("0xAB"), Some(0xAB));
    assert_eq!(analyzer.parse_formid("0xABCD"), Some(0xABCD));
}

#[test]
fn test_parse_formid_invalid() {
    let analyzer = RustFormIDAnalyzer::new();
    assert_eq!(analyzer.parse_formid("invalid"), None);
    assert_eq!(analyzer.parse_formid("0xGHIJKL"), None);
    assert_eq!(analyzer.parse_formid(""), None);
}

#[test]
fn test_parse_formid_too_long() {
    let analyzer = RustFormIDAnalyzer::new();
    // More than 8 hex digits should not match
    assert_eq!(analyzer.parse_formid("0x123456789"), None);
}

#[test]
fn test_parse_formid_null() {
    let analyzer = RustFormIDAnalyzer::new();
    assert_eq!(analyzer.parse_formid("0x00000000"), Some(0x00000000));
    assert_eq!(analyzer.parse_formid("00000000"), Some(0x00000000));
}

// ============================================
// FormID extraction tests
// ============================================

#[test]
fn test_extract_formids_empty_callstack() {
    let analyzer = RustFormIDAnalyzer::new();
    let result = analyzer.extract_formids(&[]);
    assert!(result.is_empty());
}

#[test]
fn test_extract_formids_no_matches() {
    let analyzer = RustFormIDAnalyzer::new();
    let callstack = vec![
        "No FormID here".to_string(),
        "Another random line".to_string(),
    ];
    let result = analyzer.extract_formids(&callstack);
    assert!(result.is_empty());
}

#[test]
fn test_extract_formids_single_match() {
    let analyzer = RustFormIDAnalyzer::new();
    let callstack = vec!["  Form ID: 0x0A001234 - something".to_string()];
    let result = analyzer.extract_formids(&callstack);
    assert_eq!(result.len(), 1);
    assert_eq!(result[0], "Form ID: 0A001234");
}

#[test]
fn test_extract_formids_multiple_matches() {
    let analyzer = RustFormIDAnalyzer::new();
    let callstack = vec![
        "Form ID: 0x0A001234".to_string(),
        "Form ID: 0x0B002345".to_string(),
        "FormID: 0x0C003456".to_string(), // Without space
    ];
    let result = analyzer.extract_formids(&callstack);
    assert_eq!(result.len(), 3);
}

#[test]
fn test_extract_formids_skips_ff_prefix() {
    let analyzer = RustFormIDAnalyzer::new();
    let callstack = vec![
        "Form ID: 0xFF001234".to_string(), // Should be skipped (plugin limit)
        "Form ID: 0x0A001234".to_string(), // Should be kept
    ];
    let result = analyzer.extract_formids(&callstack);
    assert_eq!(result.len(), 1);
    assert_eq!(result[0], "Form ID: 0A001234");
}

#[test]
fn test_extract_formids_keeps_null_formid() {
    let analyzer = RustFormIDAnalyzer::new();
    let callstack = vec!["Form ID: 0x00000000".to_string()];
    let result = analyzer.extract_formids(&callstack);
    assert_eq!(result.len(), 1);
    assert_eq!(result[0], "Form ID: 00000000");
}

#[test]
fn test_extract_formids_case_insensitive() {
    let analyzer = RustFormIDAnalyzer::new();
    let callstack = vec![
        "form id: 0x0A001234".to_string(),
        "FORM ID: 0x0B002345".to_string(),
        "Form Id: 0x0C003456".to_string(),
    ];
    let result = analyzer.extract_formids(&callstack);
    assert_eq!(result.len(), 3);
}

// ============================================
// Batch analysis tests
// ============================================

#[test]
fn test_analyze_batch_empty() {
    let analyzer = RustFormIDAnalyzer::new();
    let plugins = HashMap::new();
    let result = analyzer.analyze_batch(vec![], &plugins);
    assert!(result.is_empty());
}

#[test]
fn test_analyze_batch_with_plugin_resolution() {
    let analyzer = RustFormIDAnalyzer::new();
    let mut plugins = HashMap::new();
    // Plugin index is extracted as (parsed >> 24), so 0x10 = 16 decimal
    plugins.insert("16".to_string(), "MyMod.esp".to_string());
    plugins.insert("17".to_string(), "AnotherMod.esp".to_string());

    let formids = vec![
        "0x10001234".to_string(), // Plugin index 0x10 = 16
        "0x11002345".to_string(), // Plugin index 0x11 = 17
    ];

    let result = analyzer.analyze_batch(formids, &plugins);
    assert_eq!(result.len(), 2);

    // Check plugin 16 (0x10)
    assert_eq!(result[0].0, "0x10001234");
    assert_eq!(result[0].1, Some("MyMod.esp".to_string()));

    // Check plugin 17 (0x11)
    assert_eq!(result[1].0, "0x11002345");
    assert_eq!(result[1].1, Some("AnotherMod.esp".to_string()));
}

#[test]
fn test_analyze_batch_unknown_plugin() {
    let analyzer = RustFormIDAnalyzer::new();
    let plugins = HashMap::new();
    let formids = vec!["0x10001234".to_string()];

    let result = analyzer.analyze_batch(formids, &plugins);
    assert_eq!(result.len(), 1);
    assert_eq!(result[0].0, "0x10001234");
    assert_eq!(result[0].1, None);
}

#[test]
fn test_analyze_batch_invalid_formid() {
    let analyzer = RustFormIDAnalyzer::new();
    let plugins = HashMap::new();
    let formids = vec!["invalid".to_string()];

    let result = analyzer.analyze_batch(formids, &plugins);
    assert_eq!(result.len(), 1);
    assert_eq!(result[0].0, "invalid");
    assert_eq!(result[0].1, None);
}

// ============================================
// Cache tests
// ============================================

#[test]
fn test_clear_cache() {
    let analyzer = RustFormIDAnalyzer::new();
    // Access something to populate cache
    let _ = analyzer.parse_formid("0x12345678");

    analyzer.clear_cache();
    assert_eq!(analyzer.cache_stats(), (0, 0));
}

// ============================================
// FormIDAnalyzer (wrapper) tests
// ============================================

#[test]
fn test_formid_analyzer_wrapper_new() {
    let analyzer = FormIDAnalyzer::new();
    assert_eq!(analyzer.cache_stats(), (0, 0));
}

#[test]
fn test_formid_analyzer_wrapper_default() {
    let analyzer = FormIDAnalyzer::default();
    assert_eq!(analyzer.cache_stats(), (0, 0));
}

#[test]
fn test_formid_analyzer_wrapper_parse() {
    let analyzer = FormIDAnalyzer::new();
    assert_eq!(analyzer.parse_formid("0x12345678"), Some(0x12345678));
}

#[test]
fn test_formid_analyzer_wrapper_extract() {
    let analyzer = FormIDAnalyzer::new();
    let callstack = vec!["Form ID: 0x0A001234".to_string()];
    let result = analyzer.extract_formids(&callstack);
    assert_eq!(result.len(), 1);
}

#[test]
fn test_formid_analyzer_wrapper_batch() {
    let analyzer = FormIDAnalyzer::new();
    let plugins = HashMap::new();
    let formids = vec!["0x12345678".to_string()];
    let result = analyzer.analyze_batch(formids, &plugins);
    assert_eq!(result.len(), 1);
}
