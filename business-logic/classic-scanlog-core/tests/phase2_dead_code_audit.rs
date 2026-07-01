//! Source-backed contract audit for Phase 2 dead code removal.

const PARSER_RS: &str = include_str!("../src/parser.rs");
const VERSION_RS: &str = include_str!("../src/version.rs");
const PLUGIN_ANALYZER_RS: &str = include_str!("../src/plugin_analyzer.rs");
const SETTINGS_VALIDATOR_RS: &str = include_str!("../src/settings_validator.rs");
const SETTINGS_VALIDATOR_TESTS_RS: &str = include_str!("../src/settings_validator_tests.rs");

#[test]
fn parser_and_version_dead_symbols_do_not_reappear() {
    assert!(
        PARSER_RS.contains("parse_all_sections_arc"),
        "parser.rs should keep parse_all_sections_arc as the supported segmentation API"
    );
    for forbidden in [
        "#[allow(deprecated)]",
        "SEGMENT_BOUNDARIES",
        "fn named_sections_to_positional",
        "fn parse_segments(",
        "fn parse_segments_parallel(",
        "fn fast_contains(",
    ] {
        assert!(
            !PARSER_RS.contains(forbidden),
            "parser.rs should not reintroduce removed dead/deprecated symbol: {forbidden}"
        );
    }

    assert!(
        VERSION_RS.contains("check_version_status"),
        "version.rs should keep check_version_status as the supported replacement API"
    );
    assert!(
        !VERSION_RS.contains("fn is_outdated("),
        "version.rs should not reintroduce CrashgenVersion::is_outdated"
    );
}

#[test]
fn plugin_analyzer_and_settings_validator_dead_fallbacks_do_not_reappear() {
    assert!(
        !PLUGIN_ANALYZER_RS.contains("case_cache"),
        "PluginAnalyzer should stay free of the removed case_cache field"
    );
    assert!(
        !SETTINGS_VALIDATOR_RS.contains("scan_all_settings_legacy_bucketed"),
        "settings_validator.rs should not reintroduce the removed legacy bucketed fallback"
    );
    for forbidden in [
        "scan_buffout_achievements_setting",
        "scan_buffout_memorymanagement_settings",
        "scan_archivelimit_setting",
        "scan_buffout_looksmenu_setting",
        "scan_addictol_settings_scaffold",
    ] {
        assert!(
            !SETTINGS_VALIDATOR_RS.contains(forbidden),
            "settings_validator.rs should not reintroduce removed named-check API: {forbidden}"
        );
    }
    assert!(
        SETTINGS_VALIDATOR_RS.contains("check_disabled_settings(crashgen)?"),
        "scan_all_settings_bucketed should append Disabled Setting Notices after rule evaluation"
    );
    assert!(
        SETTINGS_VALIDATOR_TESTS_RS
            .contains("scan_all_settings_without_rules_returns_disabled_notices_only"),
        "settings_validator should keep the no-rules contract test for disabled notices only"
    );
}
