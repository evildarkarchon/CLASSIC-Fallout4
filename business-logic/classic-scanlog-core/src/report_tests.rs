use super::*;
use crate::version::CrashgenVersionStatus;

#[test]
fn test_string_pool() {
    let pool = StringPool::new();

    let s1 = pool.intern("hello");
    let s2 = pool.intern("hello");
    assert_eq!(s1, s2);

    let (size, lookups, hits, insertions) = pool.get_stats();
    assert_eq!(size, 1);
    assert_eq!(lookups, 2);
    assert_eq!(hits, 1);
    assert_eq!(insertions, 1);
}

#[test]
fn test_report_fragment() {
    let fragment1 = ReportFragment::from_lines(vec!["line1".to_string(), "line2".to_string()]);
    let fragment2 = ReportFragment::from_lines(vec!["line3".to_string()]);

    let combined = fragment1.combine(&fragment2);
    assert_eq!(combined.len(), 3);
    assert_eq!(combined.to_list(), vec!["line1", "line2", "line3"]);
}

#[test]
fn test_report_composer() {
    let mut composer = ReportComposer::new();

    for i in 0..20 {
        let fragment = ReportFragment::from_lines(vec![format!("Line {}", i)]);
        composer.add(fragment);
    }

    let result = composer.compose();
    assert_eq!(result.len(), 20);

    let text = composer.build_string();
    assert!(text.contains("Line 0"));
    assert!(text.contains("Line 19"));
}

#[test]
fn test_generate_error_section_uses_list_based_valid_message() {
    let generator =
        ReportGenerator::with_config("CLASSIC v9.0.0".to_string(), "Buffout 4".to_string());

    let section = generator.generate_error_section_with_status(
        "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\"",
        "Addictol v1.0.0",
        Some(CrashgenVersionStatus::Valid),
    );

    let text = section.to_list().join("");
    assert!(text.contains("valid version of Buffout 4"));
    assert!(!text.contains("latest version of Buffout 4"));
}

#[test]
fn test_generate_error_section_fake_bot_mode_notice_replaces_version_status() {
    let generator =
        ReportGenerator::with_config("CLASSIC v9.0.0".to_string(), "Buffout 4".to_string());

    let section = generator.generate_error_section_with_status_and_fake_mode(
        "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\"",
        "Buffout 4 v1.1.0",
        None,
        true,
    );

    let text = section.to_list().join("");
    assert!(text.contains("Bot Compatible Mode"));
    assert!(text.contains("Version and Settings checks are disabled"));
    assert!(!text.contains("Unable to verify Buffout 4 version"));
}
