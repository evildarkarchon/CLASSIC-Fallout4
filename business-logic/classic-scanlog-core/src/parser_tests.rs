use super::*;
use crate::segment_key;

fn create_sample_log() -> Vec<Arc<str>> {
    vec![
        Arc::from("Unhandled exception at 0x7FF123456789| ACCESS_VIOLATION"),
        Arc::from("Fallout 4 v1.10.163"),
        Arc::from("Buffout 4 v1.28.6"),
        Arc::from("[Compatibility]"),
        Arc::from("F4EE: true"),
        Arc::from("SYSTEM SPECS:"),
        Arc::from("CPU: AMD Ryzen 9 5900X"),
        Arc::from("GPU: NVIDIA GeForce RTX 3080"),
        Arc::from("PROBABLE CALL STACK:"),
        Arc::from("[0] 0x7FF123456789 Fallout4.exe+0123456"),
        Arc::from("MODULES:"),
        Arc::from("Fallout4.exe v1.10.163"),
        Arc::from("PLUGINS:"),
        Arc::from("[00] Fallout4.esm"),
        Arc::from("REGISTERS:"),
        Arc::from("RAX: 0x0000000000000000"),
        Arc::from("STACK:"),
        Arc::from("0x000000000000: 0x12345678"),
        Arc::from("EOF"),
    ]
}

fn create_sample_log_patches_only() -> Vec<Arc<str>> {
    vec![
        Arc::from("Unhandled exception at 0x7FF123456789| ACCESS_VIOLATION"),
        Arc::from("Fallout 4 v1.11.191"),
        Arc::from("Addictol v1.0.0 Feb 16 2026 08:02:06"),
        Arc::from("[Patches]"),
        Arc::from("bThreads: true"),
        Arc::from("SYSTEM SPECS:"),
        Arc::from("CPU: AMD Ryzen 7 5800XT"),
        Arc::from("PROBABLE CALL STACK:"),
        Arc::from("[0] 0x7FF7380973B8 Fallout4.exe+21773B8"),
        Arc::from("MODULES:"),
        Arc::from("Fallout4.exe v1.11.191"),
        Arc::from("PLUGINS:"),
        Arc::from("[00] Fallout4.esm"),
        Arc::from("REGISTERS:"),
        Arc::from("RAX: 0x0000000000000000"),
        Arc::from("STACK:"),
        Arc::from("0x000000000000: 0x12345678"),
        Arc::from("EOF"),
    ]
}

#[test]
fn test_parser_creation() {
    let parser = LogParser::new(None).unwrap();
    assert!(parser.get_stats().get("compiled_patterns").unwrap() > &0);
}

#[test]
fn test_parse_all_sections_arc_basic_segmentation() {
    let parser = LogParser::new(None).unwrap();
    let log_lines = create_sample_log();
    let sections = parser.parse_all_sections_arc(&log_lines);
    // Named sections map should be non-empty and settings should have content
    assert!(!sections.is_empty());
    assert!(
        !sections[segment_key::SETTINGS].is_empty(),
        "settings section should contain log header lines"
    );
}

#[test]
fn test_parse_all_sections_arc_patches_in_settings() {
    let parser = LogParser::new(None).unwrap();
    let log_lines = create_sample_log_patches_only();
    let sections = parser.parse_all_sections_arc(&log_lines);
    // Anchor-first: [Patches] content lives in the settings section
    assert!(
        sections[segment_key::SETTINGS]
            .iter()
            .any(|line| line.contains("[Patches]") || line.contains("bThreads")),
        "settings section should contain [Patches] or bThreads line"
    );
}

#[test]
fn test_parse_all_sections_arc_preserves_xse_modules() {
    let parser = LogParser::new(None).unwrap();
    let log_lines = make_log_with_known_header();
    let sections = parser.parse_all_sections_arc(&log_lines);

    // Named sections should correctly separate modules, xse_modules, and plugins
    assert!(
        sections[segment_key::MODULES]
            .iter()
            .any(|line| line.contains("module.dll")),
        "modules section should contain module.dll"
    );
    assert!(
        sections[segment_key::XSE_MODULES]
            .iter()
            .any(|line| line.contains("f4se_plugin.dll")),
        "xse_modules section should contain f4se_plugin.dll"
    );
    assert!(
        sections[segment_key::PLUGINS]
            .iter()
            .any(|line| line.contains("Fallout4.esm")),
        "plugins section should contain Fallout4.esm"
    );
}

// ===== Tests for parse_all_sections_arc (anchor-first segmentation) =====

fn make_log_with_known_header() -> Vec<Arc<str>> {
    vec![
        Arc::from("Buffout 4 v1.28.6"),
        Arc::from("[Compatibility]"),
        Arc::from("F4EE: true"),
        Arc::from("SYSTEM SPECS:"),
        Arc::from("CPU: AMD Ryzen 9"),
        Arc::from("PROBABLE CALL STACK:"),
        Arc::from("[0] 0x7FF1 func"),
        Arc::from("MODULES:"),
        Arc::from("module.dll v1.0"),
        Arc::from("F4SE PLUGINS:"),
        Arc::from("f4se_plugin.dll v1.0"),
        Arc::from("PLUGINS:"),
        Arc::from("[00] Fallout4.esm"),
        Arc::from("REGISTERS:"),
        Arc::from("RAX: 0x0"),
        Arc::from("STACK:"),
        Arc::from("0x000: 0x123"),
    ]
}

fn make_log_with_unknown_header() -> Vec<Arc<str>> {
    vec![
        Arc::from("UnknownCrashgen v2.0"),
        Arc::from("[NewForkHeader]"),
        Arc::from("Setting: true"),
        Arc::from("SYSTEM SPECS:"),
        Arc::from("CPU: Intel i9"),
        Arc::from("PROBABLE CALL STACK:"),
        Arc::from("[0] 0x7FF2 func"),
        Arc::from("MODULES:"),
        Arc::from("kernel32.dll v10.0"),
        Arc::from("NEWMOD PLUGINS:"),
        Arc::from("plugin.dll v1.0"),
        Arc::from("PLUGINS:"),
        Arc::from("[00] Fallout4.esm"),
        Arc::from("REGISTERS:"),
        Arc::from("RAX: 0x0"),
        Arc::from("STACK:"),
        Arc::from("0x000: 0xABC"),
    ]
}

fn make_log_no_header() -> Vec<Arc<str>> {
    vec![
        Arc::from("UnknownCrashgen v1.0"),
        Arc::from("Setting: false"),
        Arc::from("SYSTEM SPECS:"),
        Arc::from("CPU: Intel i7"),
        Arc::from("PROBABLE CALL STACK:"),
        Arc::from("MODULES:"),
        Arc::from("PLUGINS:"),
        Arc::from("[00] Fallout4.esm"),
        Arc::from("REGISTERS:"),
        Arc::from("STACK:"),
    ]
}

#[test]
fn test_all_sections_all_8_keys_always_present() {
    let parser = LogParser::new(None).unwrap();
    let log = make_log_with_known_header();
    let sections = parser.parse_all_sections_arc(&log);
    use crate::segment_key;
    for key in segment_key::ALL_KEYS {
        assert!(sections.contains_key(*key), "Missing key: {key}");
    }
    assert_eq!(sections.len(), 8);
}

#[test]
fn test_all_sections_known_header_segments_correctly() {
    let parser = LogParser::new(None).unwrap();
    let log = make_log_with_known_header();
    let sections = parser.parse_all_sections_arc(&log);
    use crate::segment_key;

    // Settings section contains pre-SYSTEM SPECS: lines including [Compatibility]
    let settings = &sections[segment_key::SETTINGS];
    assert!(settings.iter().any(|l| l.trim() == "[Compatibility]"));
    assert!(settings.iter().any(|l| l.contains("F4EE")));

    // System section has CPU info
    let system = &sections[segment_key::SYSTEM];
    assert!(system.iter().any(|l| l.contains("CPU")));

    // Plugins section has Fallout4.esm
    let plugins = &sections[segment_key::PLUGINS];
    assert!(plugins.iter().any(|l| l.contains("Fallout4.esm")));

    // modules: DLLs before F4SE PLUGINS:
    let modules = &sections[segment_key::MODULES];
    assert!(modules.iter().any(|l| l.contains("module.dll")));

    // xse_modules: content after F4SE PLUGINS:
    let xse_modules = &sections[segment_key::XSE_MODULES];
    assert!(xse_modules.iter().any(|l| l.contains("f4se_plugin.dll")));
}

#[test]
fn test_all_sections_unknown_header_same_structure_as_known() {
    let parser = LogParser::new(None).unwrap();
    let known = parser.parse_all_sections_arc(&make_log_with_known_header());
    let unknown = parser.parse_all_sections_arc(&make_log_with_unknown_header());
    use crate::segment_key;

    // Both should have content in settings
    assert!(!known[segment_key::SETTINGS].is_empty());
    assert!(!unknown[segment_key::SETTINGS].is_empty());

    // Both should have the same named keys
    for key in segment_key::ALL_KEYS {
        assert!(known.contains_key(*key));
        assert!(unknown.contains_key(*key));
    }

    // Unknown header [NewForkHeader] ends up in settings segment
    assert!(unknown[segment_key::SETTINGS]
        .iter()
        .any(|l| l.contains("[NewForkHeader]")));
}

#[test]
fn test_all_sections_no_header_produces_valid_settings() {
    let parser = LogParser::new(None).unwrap();
    let log = make_log_no_header();
    let sections = parser.parse_all_sections_arc(&log);
    use crate::segment_key;
    // settings should have some content (the header-less lines before SYSTEM SPECS:)
    let settings = &sections[segment_key::SETTINGS];
    // Has UnknownCrashgen header and Setting: false lines
    assert!(settings.iter().any(|l| l.contains("Setting: false")));
}

#[test]
fn test_all_sections_xse_modules_split_on_unknown_sub_header() {
    let parser = LogParser::new(None).unwrap();
    let log = make_log_with_unknown_header();
    let sections = parser.parse_all_sections_arc(&log);
    use crate::segment_key;
    // NEWMOD PLUGINS: is detected as XSE sub-header
    let xse = &sections[segment_key::XSE_MODULES];
    assert!(xse.iter().any(|l| l.contains("plugin.dll")));
    let modules = &sections[segment_key::MODULES];
    assert!(modules.iter().any(|l| l.contains("kernel32.dll")));
}

#[test]
fn test_all_sections_no_xse_subheader_leaves_xse_modules_empty() {
    let parser = LogParser::new(None).unwrap();
    // Log with no sub-header in MODULES section
    let log: Vec<Arc<str>> = vec![
        Arc::from("MODULES:"),
        Arc::from("module1.dll"),
        Arc::from("module2.dll"),
        Arc::from("PLUGINS:"),
        Arc::from("[00] Plugin.esp"),
    ];
    let sections = parser.parse_all_sections_arc(&log);
    use crate::segment_key;
    assert!(sections[segment_key::XSE_MODULES].is_empty());
    assert_eq!(sections[segment_key::MODULES].len(), 2);
}

#[test]
fn test_all_sections_missing_anchor_produces_empty_list() {
    let parser = LogParser::new(None).unwrap();
    // Log with no REGISTERS: section
    let log: Vec<Arc<str>> = vec![
        Arc::from("MODULES:"),
        Arc::from("PLUGINS:"),
        Arc::from("[00] Fallout4.esm"),
        Arc::from("STACK:"),
        Arc::from("dump line"),
    ];
    let sections = parser.parse_all_sections_arc(&log);
    use crate::segment_key;
    // registers should be empty (no REGISTERS: anchor)
    assert!(sections[segment_key::REGISTERS].is_empty());
    // stack_dump should have content
    assert!(!sections[segment_key::STACK_DUMP].is_empty());
}

#[test]
fn test_is_xse_subheader() {
    // bracket-style
    assert!(LogParser::is_xse_subheader("[F4SE PLUGINS]"));
    assert!(LogParser::is_xse_subheader("[SKSE64 PLUGINS]"));
    // ALL-CAPS colon-terminated
    assert!(LogParser::is_xse_subheader("F4SE PLUGINS:"));
    assert!(LogParser::is_xse_subheader("SKSE64 PLUGINS:"));
    assert!(LogParser::is_xse_subheader("NEWMOD PLUGINS:"));
    // Single-letter labels are too broad and must NOT split sections
    assert!(!LogParser::is_xse_subheader("A:"));
    // NOT a sub-header (lowercase/mixed)
    assert!(!LogParser::is_xse_subheader("module.dll v1.0"));
    assert!(!LogParser::is_xse_subheader("F4SE_plugin.dll"));
    // Game anchors are never considered sub-headers
    assert!(!LogParser::is_xse_subheader("PLUGINS:"));
    assert!(!LogParser::is_xse_subheader("SYSTEM SPECS:"));
    // Empty
    assert!(!LogParser::is_xse_subheader(""));
}

#[test]
fn test_all_sections_anchor_whitespace_insensitive() {
    let parser = LogParser::new(None).unwrap();
    // Log with leading whitespace on anchor lines
    let log: Vec<Arc<str>> = vec![
        Arc::from("setting line"),
        Arc::from("\tSYSTEM SPECS:"),
        Arc::from("CPU: test"),
        Arc::from("  PROBABLE CALL STACK:"),
        Arc::from("[0] frame"),
    ];
    let sections = parser.parse_all_sections_arc(&log);
    use crate::segment_key;
    // System section should have CPU line
    assert!(sections[segment_key::SYSTEM]
        .iter()
        .any(|l| l.contains("CPU")));
    // Callstack should have frame
    assert!(sections[segment_key::CALLSTACK]
        .iter()
        .any(|l| l.contains("[0]")));
}

#[test]
fn test_section_extraction() {
    let parser = LogParser::new(None).unwrap();
    let log_lines_arc = create_sample_log();
    // Convert to Vec<String> for methods that haven't been optimized yet
    let log_lines: Vec<String> = log_lines_arc.iter().map(|s| s.to_string()).collect();
    let section = parser.extract_section(&log_lines, "SYSTEM SPECS:", "PROBABLE CALL STACK:");
    assert!(section.is_some());
    let section = section.unwrap();
    assert!(section.iter().any(|line| line.contains("CPU")));
}

#[test]
fn test_addictol_patches_header_in_settings_segment() {
    // With anchor-first segmentation, [Patches] is just content in the settings
    // segment — it does NOT need a [Compatibility] fallback in extract_section.
    let parser = LogParser::new(None).unwrap();
    let log_lines_arc = create_sample_log_patches_only();

    let sections = parser.parse_all_sections_arc(&log_lines_arc);
    use crate::segment_key;

    // Settings segment should contain both [Patches] and bThreads lines
    let settings = &sections[segment_key::SETTINGS];
    assert!(!settings.is_empty(), "Settings segment should not be empty");
    assert!(settings
        .iter()
        .any(|l| l.trim() == "[Patches]" || l.contains("[Patches]")));
    assert!(settings.iter().any(|l| l.contains("bThreads")));
}

#[test]
fn test_extract_section_compatibility_falls_back_to_patches_marker() {
    let parser = LogParser::new(None).unwrap();
    let log_lines_arc = create_sample_log_patches_only();
    let log_lines: Vec<String> = log_lines_arc.iter().map(|s| s.to_string()).collect();

    let section = parser.extract_section(&log_lines, "[Compatibility]", "SYSTEM SPECS:");
    assert!(section.is_some());
    let section = section.unwrap();
    assert!(section.iter().any(|line| line.contains("bThreads")));
}

#[test]
fn test_get_section_stack_alias_returns_callstack() {
    let parser = LogParser::new(None).unwrap();
    let log_lines_arc = create_sample_log();
    let log_lines: Vec<String> = log_lines_arc.iter().map(|s| s.to_string()).collect();

    let section = parser.get_section(&log_lines, "STACK");
    assert!(section.is_some());
    let section = section.unwrap();
    assert!(section
        .iter()
        .any(|line| line.contains("Fallout4.exe+0123456")));
}

#[test]
fn test_extract_formids() {
    let parser = LogParser::new(None).unwrap();
    let lines = vec![
        "FormID: 0x12345678 in plugin".to_string(),
        "Another formid 0xABCDEF00 found".to_string(),
        "No formid here".to_string(),
    ];
    let formids = parser.extract_formids(&lines);
    assert_eq!(formids.len(), 2);
}

#[test]
fn test_parse_crash_header_detects_addictol_version_line() {
    let parser = LogParser::new(None).unwrap();
    let lines = vec![
        "Fallout 4 v1.11.191".to_string(),
        "Addictol v1.0.0 Feb 16 2026 08:02:06".to_string(),
        "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x7FF7380973B8 Fallout4.exe+21773B8"
            .to_string(),
    ];

    let header = parser.parse_crash_header(&lines).unwrap();
    assert_eq!(
        header.get("crashgen_version"),
        Some(&"Addictol v1.0.0 Feb 16 2026 08:02:06".to_string())
    );
}

#[test]
fn test_parse_crash_header_tolerates_leading_quote_noise() {
    let parser = LogParser::new(None).unwrap();
    let lines = vec![
        "`Fallout 4 v1.11.191".to_string(),
        "\"Addictol v1.0.0 Feb 16 2026 08:02:06".to_string(),
        "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x7FF7380973B8 Fallout4.exe+21773B8"
            .to_string(),
    ];

    let header = parser.parse_crash_header(&lines).unwrap();
    assert_eq!(
        header.get("game_version"),
        Some(&"Fallout 4 v1.11.191".to_string())
    );
    assert_eq!(
        header.get("crashgen_version"),
        Some(&"Addictol v1.0.0 Feb 16 2026 08:02:06".to_string())
    );
}
