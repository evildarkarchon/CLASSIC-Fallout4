use super::*;

/// Build a minimal but realistic Wrye Bash HTML report for testing
fn sample_html() -> &'static str {
    r#"<html><body>
        <h3>Missing Masters</h3>
        <p>•&nbsp; ArmorKeywords.esm</p>
        <p>•&nbsp; AWKCR.esp</p>
        <h3>ESL Capable</h3>
        <p>•&nbsp; SmallMod.esp</p>
        <p>•&nbsp; TinyPatch.esl</p>
        <h3>Active Plugins:</h3>
        <p>•&nbsp; Fallout4.esm</p>
        <p>•&nbsp; DLCCoast.esm</p>
        <h3>Delinquent Masters</h3>
        <p>•&nbsp; OldMod.esp</p>
        <p>Some non-plugin text that should be ignored</p>
        </body></html>"#
}

#[test]
fn test_parse_extracts_sections() {
    let parser = WryeBashParser::new(HashMap::new());
    let issues = parser.parse(sample_html());

    // Should have 3 sections (Active Plugins is skipped)
    assert_eq!(issues.len(), 3);
    assert_eq!(issues[0].section_title, "Missing Masters");
    assert_eq!(issues[1].section_title, "ESL Capable");
    assert_eq!(issues[2].section_title, "Delinquent Masters");
}

#[test]
fn test_parse_extracts_plugins() {
    let parser = WryeBashParser::new(HashMap::new());
    let issues = parser.parse(sample_html());

    // Missing Masters should have 2 plugins
    assert_eq!(issues[0].plugins.len(), 2);
    assert!(issues[0].plugins[0].contains("ArmorKeywords.esm"));
    assert!(issues[0].plugins[1].contains("AWKCR.esp"));

    // ESL Capable should have 2 plugins
    assert_eq!(issues[1].plugins.len(), 2);

    // Delinquent Masters should have 1 plugin (non-plugin text is filtered)
    assert_eq!(issues[2].plugins.len(), 1);
    assert!(issues[2].plugins[0].contains("OldMod.esp"));
}

#[test]
fn test_parse_skips_active_plugins() {
    let parser = WryeBashParser::new(HashMap::new());
    let issues = parser.parse(sample_html());

    assert!(
        !issues.iter().any(|i| i.section_title == "Active Plugins:"),
        "Active Plugins section should be skipped"
    );
}

#[test]
fn test_parse_with_warnings() {
    let mut warnings = HashMap::new();
    warnings.insert(
        "Missing Masters".to_string(),
        "  WARNING: Some masters are missing!\n".to_string(),
    );

    let parser = WryeBashParser::new(warnings);
    let issues = parser.parse(sample_html());

    assert!(issues[0].warning_message.is_some());
    assert!(
        issues[0]
            .warning_message
            .as_ref()
            .unwrap()
            .contains("missing")
    );
    // ESL Capable has no warning
    assert!(issues[1].warning_message.is_none());
}

#[test]
fn test_parse_empty_html() {
    let parser = WryeBashParser::new(HashMap::new());
    let issues = parser.parse("");

    assert!(issues.is_empty());
}

#[test]
fn test_parse_malformed_html() {
    let parser = WryeBashParser::new(HashMap::new());
    let issues = parser.parse("<html><h3>Broken");

    // scraper is lenient - should still parse the h3
    assert_eq!(issues.len(), 1);
    assert_eq!(issues[0].section_title, "Broken");
    assert!(issues[0].plugins.is_empty());
}

#[test]
fn test_parse_html_no_h3() {
    let parser = WryeBashParser::new(HashMap::new());
    let issues = parser.parse("<html><body><p>No sections here</p></body></html>");

    assert!(issues.is_empty());
}

#[test]
fn test_format_section_header_short() {
    let header = WryeBashParser::format_section_header("Missing Masters");
    assert!(header.contains("="));
    assert!(header.contains("Missing Masters"));
}

#[test]
fn test_format_section_header_long() {
    let long_title = "This Is A Very Long Section Title That Exceeds Thirty Two Characters";
    let header = WryeBashParser::format_section_header(long_title);
    // Long titles are returned as-is
    assert_eq!(header, long_title);
}

#[test]
fn test_format_report_esl_capable() {
    let issues = vec![WryeIssue {
        section_title: "ESL Capable".to_string(),
        plugins: vec!["SmallMod.esp".to_string(), "TinyPatch.esl".to_string()],
        warning_message: None,
        severity: WryeSeverity::Info,
    }];

    let report = WryeBashParser::format_report(&issues);
    assert!(report.contains("2 plugins"));
    assert!(report.contains("SimpleESLify"));
    // ESL Capable section should NOT list individual plugins
    assert!(!report.contains("> SmallMod.esp"));
}

#[test]
fn test_format_report_with_plugins() {
    let issues = vec![WryeIssue {
        section_title: "Missing Masters".to_string(),
        plugins: vec!["AWKCR.esp".to_string()],
        warning_message: Some("  Fix your load order!\n".to_string()),
        severity: WryeSeverity::Warning,
    }];

    let report = WryeBashParser::format_report(&issues);
    assert!(report.contains("Missing Masters"));
    assert!(report.contains("> AWKCR.esp"));
    assert!(report.contains("Fix your load order!"));
}

#[test]
fn test_format_report_empty() {
    let report = WryeBashParser::format_report(&[]);
    assert!(report.is_empty());
}

#[test]
fn test_bullet_cleanup() {
    // Verify the Unicode non-breaking space bullet prefix is stripped
    let html = "<html><body><h3>Test</h3><p>\u{2022}\u{a0} MyMod.esp</p></body></html>";
    let parser = WryeBashParser::new(HashMap::new());
    let issues = parser.parse(html);

    assert_eq!(issues.len(), 1);
    assert_eq!(issues[0].plugins.len(), 1);
    assert_eq!(issues[0].plugins[0], "MyMod.esp");
}
