use super::*;

/// Expected values were produced by the retired Python implementation
/// (`re.sub(r"(.)([A-Z][a-z]+)", ...)` then `re.sub(r"([a-z0-9])([A-Z])", ...)`).
#[test]
fn snake_case_matches_the_python_regex_passes() {
    for (name, expected) in [
        ("FormIdDatabaseAccess", "form_id_database_access"),
        ("CancelledBeforeDiscovery", "cancelled_before_discovery"),
        ("HTTPServer", "http_server"),
        ("Log2Phase", "log2_phase"),
        ("ABc", "a_bc"),
        ("A", "a"),
        ("UTF8Invalid", "utf8_invalid"),
        ("InvalidUtf8", "invalid_utf8"),
        ("getHTTPResponseCode", "get_http_response_code"),
        ("Aa_Bb", "aa__bb"),
    ] {
        assert_eq!(snake_case(name), expected, "{name}");
    }
}

#[test]
fn identifier_symbols_match_on_boundaries_and_others_as_substrings() {
    let source = "fn scan_run_contract_execute() {}\nfn scan_run_execute() {}\n";
    assert_eq!(find_symbol(source, "scan_run_execute"), Some(37));
    assert_eq!(find_symbol(source, "run_contract"), None);
    assert_eq!(find_symbol(source, "fn scan_run_c"), Some(0));
    assert_eq!(line_at(source, 37), 2);
}

#[test]
fn contained_rejects_absolute_and_escaping_paths() {
    let root = RepoRoot::new("repo");
    assert_eq!(
        contained(&root, "a/./b/../c.rs"),
        Some(PathBuf::from("repo/a/c.rs"))
    );
    assert_eq!(contained(&root, "../outside"), None);
    assert_eq!(contained(&root, "/etc/passwd"), None);
}
