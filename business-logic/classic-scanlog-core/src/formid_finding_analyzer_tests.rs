use super::*;
use crate::{AnalyzerErrorCode, AnalyzerKind};
use classic_database_core::{
    FormIdValueLookup, FormIdValueLookupEntry, FormIdValueLookupInMemoryReply,
};

fn plugin(name: &str, prefix: &str) -> FormIDPlugin {
    FormIDPlugin {
        name: name.to_string(),
        prefix: prefix.to_string(),
    }
}

#[test]
fn analyze_aggregates_resolved_and_unresolved_identifiers() {
    let analyzer = FormIDFindingAnalyzer::new(FormIdValueLookup::disabled());
    let result = classic_shared_core::get_runtime()
        .block_on(analyzer.analyze(FormIDFindingAnalysisInput {
            crash_lines: vec![
                "Form ID: 0x01123456".to_string(),
                "Form ID: 0x01123456".to_string(),
                "Form ID: 0xFE123ABC".to_string(),
                "Form ID: 0x02999999".to_string(),
            ],
            plugins: vec![plugin("Regular.esp", "01"), plugin("Light.esl", "FE123")],
        }))
        .expect("semantic analysis should succeed");

    assert_eq!(
        result.findings,
        vec![
            FormIDFinding {
                identifier: "01123456".to_string(),
                occurrences: 2,
                plugin: Some("Regular.esp".to_string()),
                value_lookup_status: FormIDValueLookupStatus::Disabled,
                value: None,
            },
            FormIDFinding {
                identifier: "02999999".to_string(),
                occurrences: 1,
                plugin: None,
                value_lookup_status: FormIDValueLookupStatus::NotApplicable,
                value: None,
            },
            FormIDFinding {
                identifier: "FE123ABC".to_string(),
                occurrences: 1,
                plugin: Some("Light.esl".to_string()),
                value_lookup_status: FormIDValueLookupStatus::Disabled,
                value: None,
            },
        ]
    );
}

#[test]
fn analyze_returns_explicit_empty_success_when_no_identifiers_are_present() {
    let analyzer = FormIDFindingAnalyzer::new(FormIdValueLookup::disabled());
    let result = classic_shared_core::get_runtime()
        .block_on(analyzer.analyze(FormIDFindingAnalysisInput {
            crash_lines: vec!["no identifier on this line".to_string()],
            plugins: Vec::new(),
        }))
        .expect("no findings is a completed semantic result");

    assert_eq!(result, FormIDFindingAnalysisResult::default());
}

#[test]
fn analyze_ignores_ambiguous_generic_fe_plugins_but_resolves_indexed_light_plugins() {
    let analyzer = FormIDFindingAnalyzer::new(FormIdValueLookup::disabled());
    let result = classic_shared_core::get_runtime()
        .block_on(analyzer.analyze(FormIDFindingAnalysisInput {
            crash_lines: vec![
                "Form ID: 0xFE123ABC".to_string(),
                "Form ID: 0xFE456DEF".to_string(),
            ],
            plugins: vec![
                plugin("LegacyLightA.esl", "FE"),
                plugin("LegacyLightB.esl", "FE"),
                plugin("IndexedLight.esl", "FE123"),
            ],
        }))
        .expect("generic FE plugin markers must not fail semantic analysis");

    assert_eq!(result.findings.len(), 2);
    assert_eq!(
        result.findings[0].plugin.as_deref(),
        Some("IndexedLight.esl")
    );
    assert_eq!(
        result.findings[0].value_lookup_status,
        FormIDValueLookupStatus::Disabled
    );
    assert_eq!(result.findings[1].plugin, None);
    assert_eq!(
        result.findings[1].value_lookup_status,
        FormIDValueLookupStatus::NotApplicable
    );
}

#[test]
fn analyze_keeps_lookup_hits_and_misses_as_distinct_data() {
    let lookup = FormIdValueLookup::in_memory(vec![FormIdValueLookupEntry::new(
        "123456",
        "Found.esp",
        FormIdValueLookupInMemoryReply::Value(Some("Resolved value".to_string())),
    )]);
    let analyzer = FormIDFindingAnalyzer::new(lookup);
    let result = classic_shared_core::get_runtime()
        .block_on(analyzer.analyze(FormIDFindingAnalysisInput {
            crash_lines: vec![
                "Form ID: 0x01123456".to_string(),
                "Form ID: 0x02ABCDEF".to_string(),
            ],
            plugins: vec![plugin("Found.esp", "01"), plugin("Missing.esp", "02")],
        }))
        .expect("hit and miss are successful semantic outcomes");

    assert_eq!(
        result.findings[0].value_lookup_status,
        FormIDValueLookupStatus::Found
    );
    assert_eq!(result.findings[0].value.as_deref(), Some("Resolved value"));
    assert_eq!(
        result.findings[1].value_lookup_status,
        FormIDValueLookupStatus::Missing
    );
    assert_eq!(result.findings[1].value, None);
}

#[test]
fn analyze_maps_lookup_failure_to_the_shared_typed_error() {
    let lookup = FormIdValueLookup::in_memory(vec![FormIdValueLookupEntry::new(
        "123456",
        "Broken.esp",
        FormIdValueLookupInMemoryReply::OperationalFailure("fixture offline".to_string()),
    )]);
    let analyzer = FormIDFindingAnalyzer::new(lookup);
    let error = classic_shared_core::get_runtime()
        .block_on(analyzer.analyze(FormIDFindingAnalysisInput {
            crash_lines: vec!["Form ID: 0x01123456".to_string()],
            plugins: vec![plugin("Broken.esp", "01")],
        }))
        .expect_err("lookup failure must fail semantic analysis");

    assert_eq!(error.analyzer(), AnalyzerKind::FormIdFinding);
    assert_eq!(error.code(), AnalyzerErrorCode::OperationalFailure);
    assert!(error.message().contains("fixture offline"));
}

#[test]
fn analyze_rejects_invalid_plugin_prefix_as_typed_configuration_error() {
    let analyzer = FormIDFindingAnalyzer::new(FormIdValueLookup::disabled());
    let error = classic_shared_core::get_runtime()
        .block_on(analyzer.analyze(FormIDFindingAnalysisInput {
            crash_lines: vec!["Form ID: 0x01123456".to_string()],
            plugins: vec![plugin("Broken.esp", "1")],
        }))
        .expect_err("malformed load-order facts must be rejected");

    assert_eq!(error.analyzer(), AnalyzerKind::FormIdFinding);
    assert_eq!(error.code(), AnalyzerErrorCode::InvalidConfiguration);
}
