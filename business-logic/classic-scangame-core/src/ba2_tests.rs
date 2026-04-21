use super::*;
#[cfg(not(windows))]
use std::path::Path;

#[test]
fn test_ba2_issues_default() {
    let issues = BA2Issues::default();
    assert!(!issues.has_issues());
    assert_eq!(issues.total_count(), 0);
}

#[test]
fn test_ba2_issues_merge() {
    let mut issues1 = BA2Issues::default();
    issues1.tex_dims.push("issue1".to_string());

    let mut issues2 = BA2Issues::default();
    issues2.tex_frmt.push("issue2".to_string());

    issues1.merge(issues2);

    assert_eq!(issues1.total_count(), 2);
    assert!(issues1.has_issues());
}

#[test]
fn test_scanner_creation() {
    let scanner = BA2Scanner::new();
    assert_eq!(scanner.xse_patterns.len(), 4);

    let custom_scanner = BA2Scanner::with_xse_patterns(vec!["f4se".to_string()]);
    assert_eq!(custom_scanner.xse_patterns.len(), 1);
}

#[cfg(not(windows))]
#[test]
fn test_scan_archive_unsupported_platform() {
    let scanner = BA2Scanner::new();
    let result = scanner.scan_archive(Path::new("mod.ba2"));
    assert!(matches!(result, Err(BA2Error::UnsupportedPlatform)));
}
