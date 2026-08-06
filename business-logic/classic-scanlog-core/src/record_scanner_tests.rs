use super::*;

#[test]
fn record_scanner_normalizes_target_and_ignore_configuration() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string(), "Weapon".to_string()],
        vec!["System".to_string()],
    );

    assert!(scanner.lower_records.contains("actorbase"));
    assert!(scanner.lower_records.contains("weapon"));
    assert!(scanner.lower_ignore.contains("system"));
}

#[test]
fn contains_record_is_case_insensitive_and_applies_ignores() {
    let targets = vec!["ActorBase".to_string(), "Weapon".to_string()];
    let ignores = vec!["System".to_string()];

    assert!(contains_record("ACTORBASE_Player", &targets, &ignores));
    assert!(contains_record("weapon_Pistol", &targets, &ignores));
    assert!(!contains_record("ActorBase_System", &targets, &ignores));
    assert!(!contains_record("Armor_Helmet", &targets, &ignores));
}

#[test]
fn extract_records_preserves_raw_matches_and_rsp_extraction() {
    let scanner = RecordScanner::new(vec!["Weapon".to_string()], Vec::new());
    let rsp_line = "[RSP+50] 0x12345678 0xABCD Weapon_Pistol".to_string();
    let expected_rsp = rsp_line.get(30..).unwrap().trim().to_string();

    let records = scanner
        .try_extract_records(&["Weapon_Rifle".to_string(), rsp_line])
        .unwrap();

    assert_eq!(records, vec!["Weapon_Rifle".to_string(), expected_rsp]);
}

#[test]
fn extraction_filters_ignored_records_and_returns_empty_success() {
    let scanner = RecordScanner::new(vec!["ActorBase".to_string()], vec!["System".to_string()]);

    assert_eq!(
        scanner
            .try_extract_records(&[
                "ActorBase_System".to_string(),
                "ActorBase_Player".to_string(),
            ])
            .unwrap(),
        vec!["ActorBase_Player".to_string()]
    );
    assert!(scanner.try_extract_records(&[]).unwrap().is_empty());
}

#[test]
fn matchers_are_built_once_for_repeated_extraction() {
    let scanner = RecordScanner::new(vec!["ActorBase".to_string()], vec!["System".to_string()]);
    assert!(scanner.record_matcher.get().is_none());

    scanner
        .try_extract_records(&["ActorBase_Player".to_string()])
        .unwrap();
    let matcher = scanner.record_matcher.get().unwrap().as_ref().unwrap();
    let pointer = std::ptr::from_ref(matcher);

    scanner
        .try_extract_records(&["ActorBase_Player".to_string()])
        .unwrap();
    assert_eq!(
        std::ptr::from_ref(scanner.record_matcher.get().unwrap().as_ref().unwrap()),
        pointer
    );
}

#[test]
fn clear_cache_remains_a_safe_noop() {
    let scanner = RecordScanner::new(Vec::new(), Vec::new());
    scanner.clear_cache();
}

#[test]
fn semantic_batch_utility_preserves_segment_order_and_filters_ignores() {
    let result = try_scan_records_batch(
        vec![
            vec!["ActorBase_System".to_string()],
            vec!["Weapon_Pistol".to_string()],
            vec!["ActorBase_Player".to_string()],
        ],
        vec!["ActorBase".to_string(), "Weapon".to_string()],
        vec!["System".to_string()],
    )
    .unwrap();

    assert!(result[0].is_empty());
    assert_eq!(result[1], vec!["Weapon_Pistol".to_string()]);
    assert_eq!(result[2], vec!["ActorBase_Player".to_string()]);
}

#[test]
fn infallible_batch_utility_returns_all_segments_for_valid_configuration() {
    let result = scan_records_batch(
        vec![vec!["ACTORBASE_PLAYER".to_string()], Vec::new()],
        vec!["actorbase".to_string()],
        Vec::new(),
    );

    assert_eq!(result.len(), 2);
    assert_eq!(result[0], vec!["ACTORBASE_PLAYER".to_string()]);
    assert!(result[1].is_empty());
}
