use super::*;

#[test]
fn test_detect_vr_log_positive() {
    assert!(detect_vr_log("some content\nFallout4VR.esm\nmore content"));
    assert!(detect_vr_log("SkyrimVR.esm"));
}

#[test]
fn test_detect_vr_log_negative() {
    assert!(!detect_vr_log("Fallout4.esm\nregular content"));
    assert!(!detect_vr_log(""));
}

#[test]
fn test_detect_crash_pattern_empty() {
    let result = detect_crash_pattern("");
    // Empty content should not match any crash pattern
    assert!(result.is_empty());
}

#[test]
fn test_detect_crash_pattern_positive_fixture_excerpt() {
    let result = detect_crash_pattern(include_str!(
        "../../../../business-logic/classic-scanlog-core/benches/fixtures/crash-2022-06-05-12-58-02.log"
    ));

    assert_eq!(
        result,
        "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x7FF6A1C08F6A Fallout4.exe+1AF8F6A"
    );
}

#[test]
fn test_detect_crash_pattern_repeated_calls_keep_same_positive_result() {
    let input = include_str!(
        "../../../../business-logic/classic-scanlog-core/benches/fixtures/crash-2022-06-05-12-58-02.log"
    );

    let first = detect_crash_pattern(input);
    let second = detect_crash_pattern(input);

    assert!(!first.is_empty());
    assert_eq!(first, second);
}
