//! Source-backed contract audit for Phase 2 YAML dead code removal.

const LIB_RS: &str = include_str!("../src/yaml_ops/operations.rs");
const INTEGRATION_TESTS_RS: &str = include_str!("yaml_integration_tests.rs");
const YAML_BENCHMARKS_RS: &str = include_str!("../benches/yaml_benchmarks.rs");

#[test]
fn yaml_format_configuration_dead_api_stays_removed() {
    assert!(
        LIB_RS.contains("pub struct YamlOperations"),
        "classic-settings-core should continue exposing YamlOperations"
    );
    assert!(
        LIB_RS.contains("cache_enabled: bool"),
        "YamlOperations should remain the simplified cache-enabled wrapper"
    );

    for forbidden in [
        "YamlFormatConfig",
        "with_config(",
        "format_config:",
        "test_custom_format_config",
    ] {
        assert!(
            !LIB_RS.contains(forbidden),
            "lib.rs should not reintroduce removed YAML formatting API: {forbidden}"
        );
    }

    assert!(
        !INTEGRATION_TESTS_RS.contains("YamlFormatConfig"),
        "integration tests should not depend on removed YamlFormatConfig"
    );
    assert!(
        !YAML_BENCHMARKS_RS.contains("YamlFormatConfig"),
        "benchmarks should not depend on removed YamlFormatConfig"
    );
    assert!(
        YAML_BENCHMARKS_RS.contains("yaml_operations_benchmarks"),
        "benchmarks should keep the simplified yaml_operations_benchmarks entry point"
    );
}
