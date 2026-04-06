const FCX_HANDLER_RS: &str = include_str!("../src/fcx_handler.rs");
const PARSER_RS: &str = include_str!("../src/parser.rs");
const VERSION_RS: &str = include_str!("../src/version.rs");
const PLUGIN_ANALYZER_RS: &str = include_str!("../src/plugin_analyzer.rs");
const REPORT_RS: &str = include_str!("../src/report.rs");
const ORCHESTRATOR_RS: &str = include_str!("../src/orchestrator.rs");
const FORMID_ANALYZER_RS: &str = include_str!("../src/formid_analyzer.rs");
const FORMID_RS: &str = include_str!("../src/formid.rs");

fn assert_uses_std_lazylock(file_name: &str, source: &str) {
    assert!(
        source.contains("LazyLock"),
        "{file_name} should use std::sync::LazyLock after the Phase 7 sweep"
    );
    assert!(
        !source.contains("once_cell::sync::Lazy"),
        "{file_name} should no longer import once_cell::sync::Lazy"
    );
}

#[test]
fn scanlog_lazy_statics_use_std_lazylock() {
    for (file_name, source) in [
        ("fcx_handler.rs", FCX_HANDLER_RS),
        ("parser.rs", PARSER_RS),
        ("version.rs", VERSION_RS),
        ("plugin_analyzer.rs", PLUGIN_ANALYZER_RS),
        ("report.rs", REPORT_RS),
        ("orchestrator.rs", ORCHESTRATOR_RS),
        ("formid_analyzer.rs", FORMID_ANALYZER_RS),
        ("formid.rs", FORMID_RS),
    ] {
        assert_uses_std_lazylock(file_name, source);
    }
}
