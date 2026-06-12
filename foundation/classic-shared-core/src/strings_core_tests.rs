use super::*;

#[test]
fn test_string_processor_new() {
    let sp = StringProcessor::new();
    assert_eq!(sp.pool_stats(), 0);
}

#[test]
fn test_string_processor_default() {
    let sp = StringProcessor::default();
    assert_eq!(sp.pool_stats(), 0);
}

#[test]
fn test_intern_returns_same_string() {
    let sp = StringProcessor::new();
    let result = sp.intern("hello");
    assert_eq!(result, "hello");
}

#[test]
fn test_intern_deduplicates() {
    let sp = StringProcessor::new();
    sp.intern("foo");
    sp.intern("foo");
    sp.intern("bar");
    assert_eq!(sp.pool_stats(), 2); // Only 2 unique strings
}

#[test]
fn test_intern_spur_and_resolve() {
    let sp = StringProcessor::new();
    let spur = sp.intern_spur("hello world");
    let resolved = sp.resolve(&spur);
    assert_eq!(resolved, "hello world");
}

#[test]
fn test_process_batch_upper() {
    let sp = StringProcessor::new();
    let result = sp.process_batch(&["hello", "world"], StringOperation::Upper);
    assert_eq!(result, vec!["HELLO", "WORLD"]);
}

#[test]
fn test_process_batch_lower() {
    let sp = StringProcessor::new();
    let result = sp.process_batch(&["HELLO", "WORLD"], StringOperation::Lower);
    assert_eq!(result, vec!["hello", "world"]);
}

#[test]
fn test_process_batch_trim() {
    let sp = StringProcessor::new();
    let result = sp.process_batch(&["  hello  ", " world "], StringOperation::Trim);
    assert_eq!(result, vec!["hello", "world"]);
}

#[test]
fn test_process_batch_normalize() {
    let sp = StringProcessor::new();
    let result = sp.process_batch(&["  Hello   World  "], StringOperation::Normalize);
    assert_eq!(result, vec!["hello world"]);
}

#[test]
fn test_normalize_string() {
    let sp = StringProcessor::new();
    assert_eq!(sp.normalize_string("  Hello   World  "), "hello world");
    assert_eq!(sp.normalize_string("UPPER"), "upper");
    assert_eq!(sp.normalize_string(""), "");
    assert_eq!(sp.normalize_string("  "), "");
    assert_eq!(sp.normalize_string("a  b  c"), "a b c");
}

#[test]
fn test_common_prefix_empty() {
    let sp = StringProcessor::new();
    assert_eq!(sp.common_prefix(&[]), "");
}

#[test]
fn test_common_prefix_single() {
    let sp = StringProcessor::new();
    assert_eq!(sp.common_prefix(&["hello"]), "hello");
}

#[test]
fn test_common_prefix_identical() {
    let sp = StringProcessor::new();
    assert_eq!(sp.common_prefix(&["abc", "abc", "abc"]), "abc");
}

#[test]
fn test_common_prefix_different() {
    let sp = StringProcessor::new();
    assert_eq!(sp.common_prefix(&["abc", "abd", "abe"]), "ab");
}

#[test]
fn test_common_prefix_no_common() {
    let sp = StringProcessor::new();
    assert_eq!(sp.common_prefix(&["abc", "xyz"]), "");
}

#[test]
fn test_split_lines() {
    let sp = StringProcessor::new();
    let result = sp.split_lines("line1\nline2\nline3");
    assert_eq!(result, vec!["line1", "line2", "line3"]);
}

#[test]
fn test_split_lines_empty() {
    let sp = StringProcessor::new();
    let result = sp.split_lines("");
    assert!(result.is_empty());
}

#[test]
fn test_join_lines() {
    let sp = StringProcessor::new();
    let lines = vec!["a".to_string(), "b".to_string(), "c".to_string()];
    assert_eq!(sp.join_lines(&lines, "\n"), "a\nb\nc");
    assert_eq!(sp.join_lines(&lines, ", "), "a, b, c");
}

#[test]
fn test_string_operation_from_str() {
    assert_eq!(
        "upper".parse::<StringOperation>().unwrap(),
        StringOperation::Upper
    );
    assert_eq!(
        "lower".parse::<StringOperation>().unwrap(),
        StringOperation::Lower
    );
    assert_eq!(
        "trim".parse::<StringOperation>().unwrap(),
        StringOperation::Trim
    );
    assert_eq!(
        "normalize".parse::<StringOperation>().unwrap(),
        StringOperation::Normalize
    );
}

#[test]
fn test_string_operation_from_str_invalid() {
    let err = "invalid".parse::<StringOperation>().unwrap_err();
    assert!(err.to_string().contains("invalid"));
    assert!(err.to_string().contains("Valid values"));
}

#[test]
fn test_string_operation_debug() {
    assert_eq!(format!("{:?}", StringOperation::Upper), "Upper");
    assert_eq!(format!("{:?}", StringOperation::Lower), "Lower");
}

#[test]
fn test_string_operation_clone_eq() {
    let op = StringOperation::Trim;
    let cloned = op;
    assert_eq!(op, cloned);
}

#[test]
fn test_parse_string_operation_error_display() {
    let err = ParseStringOperationError {
        invalid_value: "bad".to_string(),
    };
    let msg = err.to_string();
    assert!(msg.contains("bad"));
    assert!(msg.contains("Invalid string operation"));
}
