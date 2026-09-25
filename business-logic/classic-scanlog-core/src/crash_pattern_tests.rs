use super::*;

#[test]
fn hexadecimal_aliases_are_case_insensitive() {
    for (code, expected) in [
        ("0xC0000005", "ACCESS_VIOLATION"),
        ("0XC00000FD", "STACK_OVERFLOW"),
        ("0xc0000094", "INT_DIVIDE_BY_ZERO"),
        ("0x80000003", "BREAKPOINT"),
        ("0xC000001D", "ILLEGAL_INSTRUCTION"),
        ("0xC0000409", "STACK_BUFFER_OVERRUN"),
    ] {
        assert_eq!(
            detect_crash_pattern(&format!("Unhandled exception {code}")),
            Some(expected)
        );
    }
}

#[test]
fn symbolic_names_keep_their_stable_tokens() {
    for (symbol, expected) in [
        ("exception_access_violation", "ACCESS_VIOLATION"),
        ("EXCEPTION_STACK_OVERFLOW", "STACK_OVERFLOW"),
        ("EXCEPTION_INT_DIVIDE_BY_ZERO", "INT_DIVIDE_BY_ZERO"),
        ("EXCEPTION_BREAKPOINT", "BREAKPOINT"),
        ("EXCEPTION_ILLEGAL_INSTRUCTION", "ILLEGAL_INSTRUCTION"),
        ("EXCEPTION_STACK_BUFFER_OVERRUN", "STACK_BUFFER_OVERRUN"),
        ("STATUS_HEAP_CORRUPTION", "HEAP_CORRUPTION"),
    ] {
        assert_eq!(detect_crash_pattern(symbol), Some(expected));
    }
}

#[test]
fn bounded_header_scan_keeps_first_line_and_table_precedence() {
    assert_eq!(
        detect_crash_pattern("EXCEPTION_STACK_OVERFLOW\nEXCEPTION_ACCESS_VIOLATION"),
        Some("STACK_OVERFLOW")
    );
    assert_eq!(
        detect_crash_pattern("EXCEPTION_STACK_OVERFLOW EXCEPTION_ACCESS_VIOLATION"),
        Some("ACCESS_VIOLATION")
    );
    assert_eq!(
        detect_crash_pattern(&format!("{}EXCEPTION_BREAKPOINT", "ordinary\n".repeat(29))),
        Some("BREAKPOINT")
    );
    assert_eq!(
        detect_crash_pattern(&format!("{}EXCEPTION_BREAKPOINT", "ordinary\n".repeat(30))),
        None
    );
}

#[test]
fn unknown_and_empty_content_have_no_pattern() {
    assert_eq!(detect_crash_pattern(""), None);
    assert_eq!(
        detect_crash_pattern("Unhandled exception EXCEPTION_UNKNOWN_TYPE"),
        None
    );
}
