use super::*;

// ==================== EncodingDetector Creation Tests ====================

#[test]
fn test_encoding_detector_new() {
    let detector = EncodingDetector::new();
    // Just verify it creates without panicking
    let _ = detector;
}

#[test]
fn test_encoding_detector_default() {
    let detector = EncodingDetector;
    // Verify default trait works
    let _ = detector;
}

// ==================== UTF-8 Detection Tests ====================

#[test]
fn test_detect_utf8_bom() {
    let detector = EncodingDetector::new();
    // UTF-8 BOM followed by ASCII text
    let bytes = [0xEF, 0xBB, 0xBF, b'H', b'e', b'l', b'l', b'o'];
    let encoding = detector.detect(&bytes);
    assert_eq!(encoding.name(), "UTF-8");
}

#[test]
fn test_detect_utf8_no_bom() {
    let detector = EncodingDetector::new();
    let bytes = b"Hello, World!";
    let encoding = detector.detect(bytes);
    assert_eq!(encoding.name(), "UTF-8");
}

#[test]
fn test_detect_utf8_with_unicode() {
    let detector = EncodingDetector::new();
    // UTF-8 encoded Japanese characters
    let text = "こんにちは"; // "Hello" in Japanese
    let bytes = text.as_bytes();
    let encoding = detector.detect(bytes);
    assert_eq!(encoding.name(), "UTF-8");
}

#[test]
fn test_detect_utf8_with_emojis() {
    let detector = EncodingDetector::new();
    let text = "Hello 🌍🎉";
    let bytes = text.as_bytes();
    let encoding = detector.detect(bytes);
    assert_eq!(encoding.name(), "UTF-8");
}

#[test]
fn test_detect_utf8_empty() {
    let detector = EncodingDetector::new();
    let encoding = detector.detect(&[]);
    // Empty input should default to UTF-8
    assert_eq!(encoding.name(), "UTF-8");
}

#[test]
fn test_detect_utf8_ascii_only() {
    let detector = EncodingDetector::new();
    let bytes = b"Pure ASCII text 123";
    let encoding = detector.detect(bytes);
    // ASCII is valid UTF-8
    assert_eq!(encoding.name(), "UTF-8");
}

// ==================== Windows-1252 Fallback Tests ====================

#[test]
fn test_detect_windows_1252_invalid_utf8() {
    let detector = EncodingDetector::new();
    // Windows-1252 specific bytes that are invalid UTF-8
    // 0x80-0x9F are control characters in Windows-1252 that don't exist in UTF-8
    let bytes = [0x80, 0x81, 0x82, 0x83];
    let encoding = detector.detect(&bytes);
    assert_eq!(encoding.name(), "windows-1252");
}

#[test]
fn test_detect_windows_1252_euro_sign() {
    let detector = EncodingDetector::new();
    // 0x80 is Euro sign in Windows-1252, invalid in UTF-8
    let bytes = [b'P', b'r', b'i', b'c', b'e', b':', b' ', 0x80, b'1', b'0'];
    let encoding = detector.detect(&bytes);
    assert_eq!(encoding.name(), "windows-1252");
}

#[test]
fn test_detect_windows_1252_smart_quotes() {
    let detector = EncodingDetector::new();
    // 0x93 and 0x94 are smart quotes in Windows-1252
    let bytes = [0x93, b'H', b'e', b'l', b'l', b'o', 0x94];
    let encoding = detector.detect(&bytes);
    assert_eq!(encoding.name(), "windows-1252");
}

#[test]
fn test_detect_windows_1252_trademark() {
    let detector = EncodingDetector::new();
    // 0x99 is trademark symbol in Windows-1252
    let bytes = [b'B', b'r', b'a', b'n', b'd', 0x99];
    let encoding = detector.detect(&bytes);
    assert_eq!(encoding.name(), "windows-1252");
}

// ==================== detect_name Tests ====================

#[test]
fn test_detect_name_utf8() {
    let detector = EncodingDetector::new();
    let bytes = b"Simple UTF-8 text";
    let name = detector.detect_name(bytes);
    assert_eq!(name, "UTF-8");
}

#[test]
fn test_detect_name_windows_1252() {
    let detector = EncodingDetector::new();
    // Invalid UTF-8 bytes
    let bytes = [0x80, 0x85, 0x91];
    let name = detector.detect_name(&bytes);
    assert_eq!(name, "windows-1252");
}

#[test]
fn test_detect_name_returns_owned_string() {
    let detector = EncodingDetector::new();
    let bytes = b"Test";
    let name = detector.detect_name(bytes);
    // Verify it's an owned String that can be used independently
    assert!(!name.is_empty());
    let cloned = name.clone();
    assert_eq!(name, cloned);
}

// ==================== Edge Cases ====================

#[test]
fn test_detect_single_byte() {
    let detector = EncodingDetector::new();

    // Valid UTF-8 single byte (ASCII)
    let encoding = detector.detect(b"A");
    assert_eq!(encoding.name(), "UTF-8");
}

#[test]
fn test_detect_single_invalid_byte() {
    let detector = EncodingDetector::new();

    // Single byte that's invalid UTF-8 (continuation byte)
    let encoding = detector.detect(&[0x80]);
    assert_eq!(encoding.name(), "windows-1252");
}

#[test]
fn test_detect_mixed_content() {
    let detector = EncodingDetector::new();

    // Mix of valid ASCII and Windows-1252 specific bytes
    let bytes = [
        b'H', b'e', b'l', b'l', b'o', 0x85, b' ', b'W', b'o', b'r', b'l', b'd',
    ];
    let encoding = detector.detect(&bytes);
    // 0x85 (ellipsis) is invalid UTF-8
    assert_eq!(encoding.name(), "windows-1252");
}

#[test]
fn test_detect_utf8_bom_only() {
    let detector = EncodingDetector::new();
    // Just the BOM, no content
    let bytes = [0xEF, 0xBB, 0xBF];
    let encoding = detector.detect(&bytes);
    assert_eq!(encoding.name(), "UTF-8");
}

#[test]
fn test_detect_large_utf8_content() {
    let detector = EncodingDetector::new();
    // Create a large UTF-8 string
    let large_text = "Lorem ipsum ".repeat(1000);
    let encoding = detector.detect(large_text.as_bytes());
    assert_eq!(encoding.name(), "UTF-8");
}

#[test]
fn test_detect_null_bytes() {
    let detector = EncodingDetector::new();
    // String with null bytes (still valid UTF-8)
    let bytes = [b'A', 0x00, b'B', 0x00, b'C'];
    let encoding = detector.detect(&bytes);
    assert_eq!(encoding.name(), "UTF-8");
}

#[test]
fn test_detect_high_ascii() {
    let detector = EncodingDetector::new();
    // High ASCII values that are valid in both encodings
    // 0xC0-0xFF can start multi-byte UTF-8 sequences
    // But 0xC0 0xC1 followed by non-continuation bytes are invalid UTF-8
    let bytes = [0xC0, 0x41]; // Invalid UTF-8 (0xC0 must be followed by continuation byte)
    let encoding = detector.detect(&bytes);
    assert_eq!(encoding.name(), "windows-1252");
}
