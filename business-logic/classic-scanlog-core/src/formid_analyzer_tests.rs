use super::*;

#[test]
fn batch_extraction_preserves_segments_and_filters_ff_prefixes() {
    let results = extract_formids_batch(vec![
        vec![
            "Form ID: 0x01123456".to_string(),
            "Form ID: 0xFFABCDEF".to_string(),
        ],
        vec!["Form ID: 0x00000000".to_string()],
    ]);

    assert_eq!(results[0], vec!["Form ID: 01123456"]);
    assert_eq!(results[1], vec!["Form ID: 00000000"]);
}

#[test]
fn validation_accepts_optional_prefixes_and_rejects_null_or_non_hex_values() {
    assert!(is_valid_formid("Form ID: 0x12345678"));
    assert!(is_valid_formid("ABCDEF"));
    assert!(!is_valid_formid("0x00000000"));
    assert!(!is_valid_formid("not-a-formid"));
}

#[test]
fn batch_validation_preserves_input_order() {
    assert_eq!(
        validate_formids_batch(vec!["1".to_string(), "0".to_string(), "ABCDEF".to_string(),]),
        vec![true, false, true]
    );
}
