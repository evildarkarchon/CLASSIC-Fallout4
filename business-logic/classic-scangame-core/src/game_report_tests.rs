use super::*;

fn make_issues(pairs: &[(&str, &[&str])]) -> BTreeMap<String, BTreeSet<String>> {
    let mut map = BTreeMap::new();
    for (key, values) in pairs {
        let set: BTreeSet<String> = values.iter().map(|v| v.to_string()).collect();
        map.insert(key.to_string(), set);
    }
    map
}

// ---- ScanValidators tests ----

#[test]
fn test_validators_unpacked_messages() {
    let v = ScanValidators::new();
    let msgs = v.get_issue_messages("F4SE", "unpacked");

    assert!(msgs.contains_key("tex_dims"));
    assert!(msgs.contains_key("tex_frmt"));
    assert!(msgs.contains_key("snd_frmt"));
    assert!(msgs.contains_key("xse_file"));
    assert!(msgs.contains_key("previs"));
    assert!(msgs.contains_key("animdata"));
    assert!(msgs.contains_key("cleanup"));
}

#[test]
fn test_validators_archived_messages() {
    let v = ScanValidators::new();
    let msgs = v.get_issue_messages("F4SE", "archived");

    assert!(msgs.contains_key("tex_dims"));
    assert!(msgs.contains_key("tex_frmt"));
    assert!(msgs.contains_key("snd_frmt"));
    assert!(msgs.contains_key("xse_file"));
    assert!(msgs.contains_key("ba2_frmt"));
    // Archived should NOT have unpacked-only keys
    assert!(!msgs.contains_key("previs"));
    assert!(!msgs.contains_key("animdata"));
    assert!(!msgs.contains_key("cleanup"));
}

#[test]
fn test_validators_xse_acronym_in_messages() {
    let v = ScanValidators::new();

    let f4se_msgs = v.get_issue_messages("F4SE", "unpacked");
    let xse_msg = &f4se_msgs["xse_file"][0];
    assert!(xse_msg.contains("F4SE"));

    let skse_msgs = v.get_issue_messages("SKSE", "unpacked");
    let xse_msg = &skse_msgs["xse_file"][0];
    assert!(xse_msg.contains("SKSE"));
}

#[test]
fn test_validators_caching() {
    let v = ScanValidators::new();

    // First call populates cache
    let msgs1 = v.get_issue_messages("F4SE", "unpacked");
    // Second call should return same data from cache
    let msgs2 = v.get_issue_messages("F4SE", "unpacked");

    assert_eq!(msgs1, msgs2);
}

#[test]
fn test_validators_unknown_mode() {
    let v = ScanValidators::new();
    let msgs = v.get_issue_messages("F4SE", "unknown");
    // Should still have base messages
    assert!(msgs.contains_key("tex_dims"));
    // But no mode-specific ones
    assert!(!msgs.contains_key("previs"));
    assert!(!msgs.contains_key("ba2_frmt"));
}

// ---- ScanReportBuilder tests ----

#[test]
fn test_build_unpacked_report_header() {
    let v = ScanValidators::new();
    let builder = ScanReportBuilder::new(&v);

    let issues = BTreeMap::new();
    let report = builder.build_unpacked_report(&issues, "F4SE");

    assert!(report.contains("MOD FILES SCAN"));
    assert!(report.contains("RESULTS FROM UNPACKED / LOOSE FILES"));
}

#[test]
fn test_build_unpacked_report_with_issues() {
    let v = ScanValidators::new();
    let builder = ScanReportBuilder::new(&v);

    let issues = make_issues(&[
        ("tex_frmt", &["  - TGA : textures/bad.tga\n"]),
        ("snd_frmt", &["  - MP3 : sounds/bad.mp3\n"]),
    ]);

    let report = builder.build_unpacked_report(&issues, "F4SE");

    assert!(report.contains("TEXTURE FILES HAVE INCORRECT FORMAT"));
    assert!(report.contains("bad.tga"));
    assert!(report.contains("SOUND FILES HAVE INCORRECT FORMAT"));
    assert!(report.contains("bad.mp3"));
}

#[test]
fn test_build_archived_report_header() {
    let v = ScanValidators::new();
    let builder = ScanReportBuilder::new(&v);

    let issues = BTreeMap::new();
    let report = builder.build_archived_report(&issues, "F4SE");

    assert!(report.contains("RESULTS FROM ARCHIVED / BA2 FILES"));
}

#[test]
fn test_build_archived_report_with_issues() {
    let v = ScanValidators::new();
    let builder = ScanReportBuilder::new(&v);

    let issues = make_issues(&[("ba2_frmt", &["  - invalid.ba2\n"])]);

    let report = builder.build_archived_report(&issues, "F4SE");

    assert!(report.contains("BA2 ARCHIVES HAVE INCORRECT FORMAT"));
    assert!(report.contains("invalid.ba2"));
}

#[test]
fn test_build_combined_report() {
    let v = ScanValidators::new();
    let builder = ScanReportBuilder::new(&v);

    let unpacked = make_issues(&[("tex_frmt", &["  - TGA : texture.tga\n"])]);
    let archived = make_issues(&[("ba2_frmt", &["  - invalid.ba2\n"])]);

    let report = builder.build_combined_report(&unpacked, &archived, "F4SE");

    assert!(report.contains("UNPACKED"));
    assert!(report.contains("ARCHIVED"));
    assert!(report.contains("texture.tga"));
    assert!(report.contains("invalid.ba2"));
}

#[test]
fn test_empty_issue_set_not_in_report() {
    let v = ScanValidators::new();
    let builder = ScanReportBuilder::new(&v);

    // tex_dims key exists but has no items
    let mut issues = BTreeMap::new();
    issues.insert("tex_dims".to_string(), BTreeSet::new());

    let report = builder.build_unpacked_report(&issues, "F4SE");

    // The header messages for tex_dims should NOT appear
    assert!(!report.contains("DDS DIMENSIONS ARE NOT DIVISIBLE BY 2"));
}

#[test]
fn test_unknown_issue_type_ignored() {
    let v = ScanValidators::new();
    let builder = ScanReportBuilder::new(&v);

    let issues = make_issues(&[("unknown_category", &["  - something\n"])]);

    let report = builder.build_unpacked_report(&issues, "F4SE");

    // Should not crash, and the unknown items should not appear
    assert!(!report.contains("something"));
}

#[test]
fn test_report_items_sorted() {
    let v = ScanValidators::new();
    let builder = ScanReportBuilder::new(&v);

    let issues = make_issues(&[(
        "tex_frmt",
        &[
            "  - TGA : z_texture.tga\n",
            "  - TGA : a_texture.tga\n",
            "  - TGA : m_texture.tga\n",
        ],
    )]);

    let report = builder.build_unpacked_report(&issues, "F4SE");

    // BTreeSet sorts items, so a < m < z
    let a_pos = report.find("a_texture").unwrap();
    let m_pos = report.find("m_texture").unwrap();
    let z_pos = report.find("z_texture").unwrap();
    assert!(a_pos < m_pos);
    assert!(m_pos < z_pos);
}
