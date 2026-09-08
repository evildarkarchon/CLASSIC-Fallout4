use super::*;

#[test]
fn token_classification_preserves_legacy_main_error_text() {
    let content = "Unhandled exception 0xC0000005 at 0x12345678";
    assert_eq!(classify_crash_pattern(content), "ACCESS_VIOLATION");
    assert_eq!(detect_crash_pattern(content), content);
    assert!(classify_crash_pattern("no known failure").is_empty());
}

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
fn vr_detection_uses_core_case_insensitive_executable_markers() {
    assert!(detect_vr_log("FALLOUT4VR.EXE loaded"));
    assert!(detect_vr_log("SKYRIMVR.EXE loaded"));
    assert!(!detect_vr_log("SkyrimSE.exe loaded"));
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
