//! Shared bounded classification of symbolic and hexadecimal crash-header patterns.

/// Returns a stable crash-pattern token from the first thirty lines, or `None`.
/// Matching is ASCII-case-insensitive; earlier lines win and the fixed token
/// priority resolves multiple recognized patterns on one line. This classifies
/// known errors without parsing or replacing the original main-error text.
pub fn detect_crash_pattern(content: &str) -> Option<&'static str> {
    // Keep aliases in the same case as the normalized header. The former Node
    // implementation uppercased input but left lowercase `0x` in its table,
    // making every numeric alias unreachable.
    const PATTERNS: &[(&str, &str)] = &[
        ("EXCEPTION_ACCESS_VIOLATION", "ACCESS_VIOLATION"),
        ("EXCEPTION_STACK_OVERFLOW", "STACK_OVERFLOW"),
        ("EXCEPTION_INT_DIVIDE_BY_ZERO", "INT_DIVIDE_BY_ZERO"),
        ("EXCEPTION_BREAKPOINT", "BREAKPOINT"),
        ("EXCEPTION_ILLEGAL_INSTRUCTION", "ILLEGAL_INSTRUCTION"),
        ("EXCEPTION_STACK_BUFFER_OVERRUN", "STACK_BUFFER_OVERRUN"),
        ("STATUS_HEAP_CORRUPTION", "HEAP_CORRUPTION"),
        ("0XC0000005", "ACCESS_VIOLATION"),
        ("0XC00000FD", "STACK_OVERFLOW"),
        ("0XC0000094", "INT_DIVIDE_BY_ZERO"),
        ("0X80000003", "BREAKPOINT"),
        ("0XC000001D", "ILLEGAL_INSTRUCTION"),
        ("0XC0000409", "STACK_BUFFER_OVERRUN"),
    ];
    // Search only the bounded header, not addresses or strings in a long dump.
    for line in content.lines().take(30) {
        let upper = line.to_ascii_uppercase();
        for &(pattern, token) in PATTERNS {
            if upper.contains(pattern) {
                return Some(token);
            }
        }
    }
    None
}

#[cfg(test)]
#[path = "crash_pattern_tests.rs"]
mod tests;
