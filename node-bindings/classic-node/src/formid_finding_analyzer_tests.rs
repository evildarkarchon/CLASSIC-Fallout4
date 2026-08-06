use classic_database_core::{
    FormIdValueLookup, FormIdValueLookupEntry, FormIdValueLookupInMemoryReply,
};

use super::*;

fn plugin(name: &str, prefix: &str) -> JsFormIdPlugin {
    JsFormIdPlugin {
        name: name.to_string(),
        prefix: prefix.to_string(),
    }
}

async fn analyze_owned(
    analyzer: &FormIdFindingAnalyzer,
    input: JsFormIdFindingAnalysisInput,
) -> Result<JsFormIdFindingAnalysisResult, AnalyzerError> {
    analyzer
        .inner
        .analyze(input_to_core(input))
        .await
        .map(result_to_js)
}

#[test]
fn projects_resolved_unresolved_found_and_missing_findings() {
    let lookup = FormIdValueLookup::in_memory(vec![FormIdValueLookupEntry::new(
        "123456",
        "Found.esp",
        FormIdValueLookupInMemoryReply::Value(Some("Resolved value".to_string())),
    )]);
    let analyzer = build_analyzer(lookup);
    let result = classic_shared_core::get_runtime()
        .block_on(analyze_owned(&analyzer, JsFormIdFindingAnalysisInput {
            crash_lines: vec![
                "Form ID: 0x01123456".to_string(),
                "Form ID: 0x02ABCDEF".to_string(),
                "Form ID: 0x03999999".to_string(),
            ],
            plugins: vec![plugin("Found.esp", "01"), plugin("Missing.esp", "02")],
        }))
        .expect("semantic projection should succeed");

    assert_eq!(result.findings.len(), 3);
    assert_eq!(
        result.findings[0].value_lookup_status,
        JsFormIdValueLookupStatus::Found
    );
    assert_eq!(result.findings[0].value.as_deref(), Some("Resolved value"));
    assert_eq!(
        result.findings[1].value_lookup_status,
        JsFormIdValueLookupStatus::Missing
    );
    assert_eq!(result.findings[1].value, None);
    assert_eq!(result.findings[2].plugin, None);
    assert_eq!(
        result.findings[2].value_lookup_status,
        JsFormIdValueLookupStatus::NotApplicable
    );
}

#[test]
fn preserves_shared_lookup_failure_error() {
    let lookup = FormIdValueLookup::in_memory(vec![FormIdValueLookupEntry::new(
        "123456",
        "Broken.esp",
        FormIdValueLookupInMemoryReply::OperationalFailure("fixture offline".to_string()),
    )]);
    let analyzer = build_analyzer(lookup);
    let result = classic_shared_core::get_runtime().block_on(analyze_owned(&analyzer,
        JsFormIdFindingAnalysisInput {
            crash_lines: vec!["Form ID: 0x01123456".to_string()],
            plugins: vec![plugin("Broken.esp", "01")],
        },
    ));
    let error = match result {
        Ok(_) => panic!("lookup failure must remain an analyzer failure"),
        Err(error) => error,
    };

    assert_eq!(error.analyzer().as_str(), "formid_finding");
    assert_eq!(error.code().as_str(), "operational_failure");
    assert!(error.message().contains("fixture offline"));
}
