//! Edge cases of the ported shape rules. Expected values were checked against
//! the retired Python validator (or, for the deliberate deltas, against the
//! Rust client's parsers).

use super::*;

#[test]
fn semver_shapes_match_the_python_patterns() {
    for ok in [
        "0.0.0",
        "9.2.0",
        "10.20.30",
        "1.0.0-0",
        "1.0.0-alpha.1",
        "1.0.0-0a",
        "1.0.0+001",
        "1.0.0-x-y.z+b.c",
    ] {
        assert!(is_semver(ok), "{ok}");
    }
    for bad in [
        "01.0.0", "1.0", "1.0.0-01", "1.0.0-", "1.0.0+", "v1.0.0", "1.0.0.0", " 1.0.0",
    ] {
        assert!(!is_semver(bad), "{bad}");
    }
}

#[test]
fn digits_are_ascii_and_a_trailing_newline_is_refused() {
    // Python's `re` accepted both; the Rust client parses neither.
    assert!(!is_semver("\u{663}.0.0"));
    assert!(!is_semver("1.0.0\n"));
    assert!(!is_manifest_version("1.0\n"));
    assert!(!is_rfc3339("2026-04-22T12:00:00Z\n"));
}

#[test]
fn rfc3339_needs_an_offset() {
    assert!(is_rfc3339("2026-04-22T12:00:00Z"));
    assert!(is_rfc3339("2026-04-22t12:00:00.123+05:30"));
    assert!(!is_rfc3339("2026-04-22T12:00:00"));
    assert!(!is_rfc3339("2026-04-22 12:00:00Z"));
}

#[test]
fn precedence_compares_numbers_of_any_length() {
    assert_eq!(
        semver_precedence("99999999999999999999.0.0", "100000000000000000000.0.0"),
        Ordering::Less
    );
    assert_eq!(
        semver_precedence("1.0.0-rc.1", "1.0.0-rc.1"),
        Ordering::Equal
    );
    assert_eq!(semver_precedence("1.0.0-1", "1.0.0-a"), Ordering::Less);
}

#[test]
fn cta_ipv6_scope_ids_and_ipvfuture_are_accepted() {
    assert!(is_https_cta_url("https://[fe80::1%25eth0]/x"));
    assert!(is_https_cta_url("https://[v1.fe80]/x"));
    assert!(!is_https_cta_url("https://[vz.fe80]/x"));
    assert!(!is_https_cta_url("https://x[::1]/x"));
    assert!(!is_https_cta_url("https://[::1]x/x"));
}
