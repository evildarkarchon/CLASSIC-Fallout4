use super::*;

// ============================================
// RecordScanner creation tests
// ============================================

#[test]
fn test_record_scanner_new() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string(), "Weapon".to_string()],
        vec!["System".to_string()],
        "Buffout 4".to_string(),
    );

    // Just verify it creates successfully
    assert!(scanner.lower_records.contains("actorbase"));
    assert!(scanner.lower_records.contains("weapon"));
    assert!(scanner.lower_ignore.contains("system"));
}

#[test]
fn test_record_scanner_empty_lists() {
    let scanner = RecordScanner::new(vec![], vec![], "Buffout 4".to_string());

    assert!(scanner.lower_records.is_empty());
    assert!(scanner.lower_ignore.is_empty());
}

// ============================================
// contains_record tests
// ============================================

#[test]
fn test_contains_record_match() {
    let targets = vec!["ActorBase".to_string()];
    let ignores: Vec<String> = vec![];

    assert!(contains_record("ActorBase_Player", &targets, &ignores));
}

#[test]
fn test_contains_record_no_match() {
    let targets = vec!["ActorBase".to_string()];
    let ignores: Vec<String> = vec![];

    assert!(!contains_record("Weapon_Pistol", &targets, &ignores));
}

#[test]
fn test_contains_record_case_insensitive() {
    let targets = vec!["ActorBase".to_string()];
    let ignores: Vec<String> = vec![];

    assert!(contains_record("ACTORBASE_Player", &targets, &ignores));
    assert!(contains_record("actorbase_player", &targets, &ignores));
}

#[test]
fn test_contains_record_with_ignore() {
    let targets = vec!["ActorBase".to_string()];
    let ignores = vec!["System".to_string()];

    assert!(!contains_record("ActorBase_System", &targets, &ignores));
    assert!(contains_record("ActorBase_Player", &targets, &ignores));
}

#[test]
fn test_contains_record_multiple_targets() {
    let targets = vec!["ActorBase".to_string(), "Weapon".to_string()];
    let ignores: Vec<String> = vec![];

    assert!(contains_record("ActorBase_Player", &targets, &ignores));
    assert!(contains_record("Weapon_Pistol", &targets, &ignores));
    assert!(!contains_record("Armor_Helmet", &targets, &ignores));
}

#[test]
fn test_contains_record_empty_targets() {
    let targets: Vec<String> = vec![];
    let ignores: Vec<String> = vec![];

    assert!(!contains_record("ActorBase_Player", &targets, &ignores));
}

// ============================================
// scan_named_records tests
// ============================================

#[test]
fn test_scan_named_records_empty_callstack() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string()],
        vec![],
        "Buffout 4".to_string(),
    );

    let (report, matches) = scanner.scan_named_records(&[]);
    assert!(matches.is_empty());
    assert!(!report.is_empty());
    let output = report.join("");
    assert!(output.contains("COULDN'T FIND"));
}

#[test]
fn test_scan_named_records_no_matches() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string()],
        vec![],
        "Buffout 4".to_string(),
    );

    let callstack = vec!["Some random line".to_string(), "Another line".to_string()];

    let (report, matches) = scanner.scan_named_records(&callstack);
    assert!(matches.is_empty());
    let output = report.join("");
    assert!(output.contains("COULDN'T FIND"));
}

#[test]
fn test_scan_named_records_with_rsp_format() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string()],
        vec![],
        "Buffout 4".to_string(),
    );

    // RSP format: [RSP+XX] followed by content at offset 30
    let callstack = vec!["[RSP+50] 0x12345678 0xABCD ActorBase_Player".to_string()];

    let (report, matches) = scanner.scan_named_records(&callstack);
    assert!(!matches.is_empty());
    let output = report.join("");
    assert!(!output.contains("COULDN'T FIND"));
}

#[test]
fn test_scan_named_records_without_rsp() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string()],
        vec![],
        "Buffout 4".to_string(),
    );

    let callstack = vec!["ActorBase_Player reference".to_string()];

    let (_report, matches) = scanner.scan_named_records(&callstack);
    assert!(!matches.is_empty());
    assert!(matches[0].contains("ActorBase_Player"));
}

#[test]
fn test_scan_named_records_filters_ignored() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string()],
        vec!["System".to_string()],
        "Buffout 4".to_string(),
    );

    let callstack = vec![
        "ActorBase_System reference".to_string(), // Should be filtered
        "ActorBase_Player reference".to_string(), // Should be kept
    ];

    let (_report, matches) = scanner.scan_named_records(&callstack);
    assert_eq!(matches.len(), 1);
    assert!(matches[0].contains("Player"));
}

#[test]
fn test_scan_named_records_case_insensitive() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string()],
        vec![],
        "Buffout 4".to_string(),
    );

    let callstack = vec!["ACTORBASE_PLAYER".to_string()];

    let (_report, matches) = scanner.scan_named_records(&callstack);
    assert!(!matches.is_empty());
}

#[test]
fn test_scan_named_records_counts() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string()],
        vec![],
        "Buffout 4".to_string(),
    );

    let callstack = vec![
        "ActorBase_Player".to_string(),
        "ActorBase_Player".to_string(), // Duplicate
        "ActorBase_NPC".to_string(),
    ];

    let (report, _matches) = scanner.scan_named_records(&callstack);
    let output = report.join("");
    // Should contain count information
    assert!(output.contains("| 2") || output.contains("|2")); // Player appears twice
    assert!(output.contains("| 1") || output.contains("|1")); // NPC appears once
}

#[test]
fn test_scan_named_records_with_crashgen_name_override_uses_effective_name() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string()],
        vec![],
        "Buffout 4".to_string(),
    );

    let callstack = vec!["ActorBase_Player reference".to_string()];
    let (report, _matches) =
        scanner.scan_named_records_with_crashgen_name(&callstack, "Addictol");
    let output = report.join("");

    assert!(output.contains("caught by Addictol"));
    assert!(!output.contains("caught by Buffout 4"));
}

// ============================================
// extract_records tests
// ============================================

#[test]
fn test_extract_records_empty() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string()],
        vec![],
        "Buffout 4".to_string(),
    );

    let records = scanner.extract_records(&[]);
    assert!(records.is_empty());
}

#[test]
fn test_extract_records_simple() {
    let scanner =
        RecordScanner::new(vec!["Weapon".to_string()], vec![], "Buffout 4".to_string());

    let callstack = vec!["Weapon_Pistol reference".to_string()];

    let records = scanner.extract_records(&callstack);
    assert!(!records.is_empty());
}

#[test]
fn test_extract_records_rsp_format() {
    let scanner =
        RecordScanner::new(vec!["Weapon".to_string()], vec![], "Buffout 4".to_string());

    // Line must be long enough for RSP offset (30 chars)
    let callstack = vec!["[RSP+50] 0x12345678 0xABCD Weapon_Pistol".to_string()];

    let records = scanner.extract_records(&callstack);
    // Should extract content after offset 30
    assert!(!records.is_empty());
}

#[test]
fn test_scan_named_records_with_misaligned_lowercase_input_panics() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string(), "Weapon".to_string()],
        vec![],
        "Buffout 4".to_string(),
    );

    let callstack = vec!["ActorBase_Player".to_string(), "Weapon_Pistol".to_string()];
    let lowered = vec!["actorbase_player".to_string()];

    let result = std::panic::catch_unwind(|| {
        scanner.scan_named_records_with_crashgen_name_and_lowercase(
            &callstack,
            &lowered,
            "Buffout 4",
        )
    });

    assert!(result.is_err());
}

#[test]
fn test_scan_named_records_with_aligned_lowercase_input_matches_original_callstack() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string(), "Weapon".to_string()],
        vec![],
        "Buffout 4".to_string(),
    );

    let callstack = vec!["ActorBase_Player".to_string(), "Weapon_Pistol".to_string()];
    let lowered = callstack
        .iter()
        .map(|line| line.to_lowercase())
        .collect::<Vec<_>>();

    let (_report, matches) = scanner.scan_named_records_with_crashgen_name_and_lowercase(
        &callstack,
        &lowered,
        "Buffout 4",
    );

    assert_eq!(matches.len(), 2);
    assert!(matches.iter().any(|line| line.contains("ActorBase_Player")));
    assert!(matches.iter().any(|line| line.contains("Weapon_Pistol")));
}

#[test]
fn test_matchers_are_built_lazily_once_per_scanner_instance() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string()],
        vec!["System".to_string()],
        "Buffout 4".to_string(),
    );

    assert!(scanner.record_matcher.get().is_none());
    assert!(scanner.ignore_matcher.get().is_none());

    let callstack = vec!["ActorBase_Player reference".to_string()];
    let _ = scanner.scan_named_records(&callstack);

    let record_matcher = scanner
        .record_matcher
        .get()
        .expect("record matcher should initialize on first scan");
    let ignore_matcher = scanner
        .ignore_matcher
        .get()
        .expect("ignore matcher should initialize on first scan");

    let record_matcher_ptr = std::ptr::from_ref(record_matcher);
    let ignore_matcher_ptr = std::ptr::from_ref(ignore_matcher);

    let _ = scanner.scan_named_records(&callstack);

    assert_eq!(
        std::ptr::from_ref(
            scanner
                .record_matcher
                .get()
                .expect("record matcher should stay cached")
        ),
        record_matcher_ptr,
    );
    assert_eq!(
        std::ptr::from_ref(
            scanner
                .ignore_matcher
                .get()
                .expect("ignore matcher should stay cached")
        ),
        ignore_matcher_ptr,
    );
}

// ============================================
// clear_cache tests
// ============================================

#[test]
fn test_clear_cache() {
    let scanner = RecordScanner::new(
        vec!["ActorBase".to_string()],
        vec![],
        "Buffout 4".to_string(),
    );

    // Should not panic
    scanner.clear_cache();
}

// ============================================
// scan_records_batch tests
// ============================================

#[test]
fn test_scan_records_batch_empty() {
    let segments: Vec<Vec<String>> = vec![];
    let targets = vec!["ActorBase".to_string()];
    let ignores: Vec<String> = vec![];

    let result = scan_records_batch(segments, targets, ignores);
    assert!(result.is_empty());
}

#[test]
fn test_scan_records_batch_single_segment() {
    let segments = vec![vec!["ActorBase_Player".to_string()]];
    let targets = vec!["ActorBase".to_string()];
    let ignores: Vec<String> = vec![];

    let result = scan_records_batch(segments, targets, ignores);
    assert_eq!(result.len(), 1);
    assert!(!result[0].is_empty());
}

#[test]
fn test_scan_records_batch_multiple_segments() {
    let segments = vec![
        vec!["ActorBase_Player".to_string()],
        vec!["Weapon_Pistol".to_string()],
        vec!["Armor_Helmet".to_string()], // No match
    ];
    let targets = vec!["ActorBase".to_string(), "Weapon".to_string()];
    let ignores: Vec<String> = vec![];

    let result = scan_records_batch(segments, targets, ignores);
    assert_eq!(result.len(), 3);
    assert!(!result[0].is_empty()); // Has ActorBase
    assert!(!result[1].is_empty()); // Has Weapon
    assert!(result[2].is_empty()); // No match
}

#[test]
fn test_scan_records_batch_with_ignores() {
    let segments = vec![
        vec!["ActorBase_System".to_string()], // Should be filtered
        vec!["ActorBase_Player".to_string()], // Should be kept
    ];
    let targets = vec!["ActorBase".to_string()];
    let ignores = vec!["System".to_string()];

    let result = scan_records_batch(segments, targets, ignores);
    assert_eq!(result.len(), 2);
    assert!(result[0].is_empty()); // Filtered
    assert!(!result[1].is_empty()); // Kept
}

#[test]
fn test_scan_records_batch_rsp_format() {
    let segments = vec![vec![
        "[RSP+50] 0x12345678 0xABCD ActorBase_Player".to_string(),
    ]];
    let targets = vec!["ActorBase".to_string()];
    let ignores: Vec<String> = vec![];

    let result = scan_records_batch(segments, targets, ignores);
    assert_eq!(result.len(), 1);
    assert!(!result[0].is_empty());
}

#[test]
fn test_scan_records_batch_preserves_order() {
    let segments = vec![
        vec!["First_Record".to_string()],
        vec!["Second_Record".to_string()],
        vec!["Third_Record".to_string()],
    ];
    let targets = vec![
        "First".to_string(),
        "Second".to_string(),
        "Third".to_string(),
    ];
    let ignores: Vec<String> = vec![];

    let result = scan_records_batch(segments, targets, ignores);
    assert_eq!(result.len(), 3);

    // Verify order is preserved
    assert!(result[0][0].contains("First"));
    assert!(result[1][0].contains("Second"));
    assert!(result[2][0].contains("Third"));
}

#[test]
fn test_scan_records_batch_case_insensitive() {
    let segments = vec![vec!["ACTORBASE_PLAYER".to_string()]];
    let targets = vec!["actorbase".to_string()]; // Lowercase
    let ignores: Vec<String> = vec![];

    let result = scan_records_batch(segments, targets, ignores);
    assert!(!result[0].is_empty());
}
