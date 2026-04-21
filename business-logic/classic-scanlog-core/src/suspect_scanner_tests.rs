use super::*;
use classic_config_core::{SuspectErrorRule, SuspectStackCountRule, SuspectStackRule};

#[test]
fn test_suspect_scan_mainerror() {
    let scanner = SuspectScanner::new(
        vec![SuspectErrorRule {
            id: "memory_access_violation".to_string(),
            name: "Memory Access Violation".to_string(),
            severity: 5,
            main_error_contains_any: vec!["ACCESS_VIOLATION".to_string()],
        }],
        Vec::new(),
    );

    let (fragment, found) = scanner
        .suspect_scan_mainerror("Error: ACCESS_VIOLATION at 0x12345", 50)
        .unwrap();

    assert!(found);
    assert!(!fragment.is_empty());
}

#[test]
fn test_check_dll_crash() {
    let fragment =
        SuspectScanner::check_dll_crash("Error in plugin.dll at address 0x12345").unwrap();

    assert!(!fragment.is_empty());

    // Should not trigger for tbbmalloc
    let fragment2 = SuspectScanner::check_dll_crash("Error in tbbmalloc.dll").unwrap();

    assert!(fragment2.is_empty());
}

#[test]
fn test_suspect_scan_stack_with_structured_conditions() {
    let scanner = SuspectScanner::new(
        Vec::new(),
        vec![SuspectStackRule {
            id: "structured_stack_rule".to_string(),
            name: "Structured Stack Rule".to_string(),
            severity: 4,
            main_error_required_any: vec!["OutOfMemory".to_string()],
            main_error_optional_any: vec!["MaybeRelated".to_string()],
            stack_contains_any: vec!["SomePattern".to_string()],
            exclude_if_stack_contains_any: Vec::new(),
            stack_contains_at_least: vec![SuspectStackCountRule {
                substring: "RepeatedPattern".to_string(),
                count: 3,
            }],
        }],
    );

    let (fragment, found) = scanner
        .suspect_scan_stack(
            "OutOfMemory error occurred",
            "SomePattern\nRepeatedPattern\nRepeatedPattern\nRepeatedPattern",
            50,
        )
        .unwrap();

    assert!(found);
    assert!(!fragment.is_empty());
}

#[test]
fn test_suspect_scan_stack_exclusion_condition() {
    let scanner = SuspectScanner::new(
        Vec::new(),
        vec![SuspectStackRule {
            id: "excluded_rule".to_string(),
            name: "Excluded Rule".to_string(),
            severity: 2,
            main_error_required_any: Vec::new(),
            main_error_optional_any: Vec::new(),
            stack_contains_any: vec!["TargetPattern".to_string()],
            exclude_if_stack_contains_any: vec!["SkipPattern".to_string()],
            stack_contains_at_least: Vec::new(),
        }],
    );

    let (fragment, found) = scanner
        .suspect_scan_stack("main error", "TargetPattern\nSkipPattern", 50)
        .unwrap();

    assert!(!found);
    assert!(fragment.is_empty());
}
