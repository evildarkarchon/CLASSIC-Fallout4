use super::*;

#[test]
fn python_projection_preserves_optional_plugin_and_value_fields() {
    let analyzer = PyFormIDFindingAnalyzer::in_memory(vec![PyFormIDFindingLookupEntry::new(
        "123456".to_string(),
        "Found.esp".to_string(),
        PyFormIDFindingLookupReplyKind::Found,
        Some("Resolved value".to_string()),
        None,
    )])
    .expect("deterministic analyzer should construct");
    let input = PyFormIDFindingAnalysisInput::new(
        vec![
            "Form ID: 0x01123456".to_string(),
            "Form ID: 0x02ABCDEF".to_string(),
        ],
        vec![PyFormIDPlugin::new(
            "Found.esp".to_string(),
            "01".to_string(),
        )],
    );
    let result = classic_shared_core::get_runtime()
        .block_on(analyzer.inner.analyze(input.inner))
        .map(PyFormIDFindingAnalysisResult::from)
        .expect("analysis should succeed");

    assert_eq!(result.findings.len(), 2);
    assert_eq!(result.findings[0].plugin.as_deref(), Some("Found.esp"));
    assert_eq!(result.findings[0].value.as_deref(), Some("Resolved value"));
    assert_eq!(result.findings[1].plugin, None);
    assert_eq!(
        result.findings[1].value_lookup_status,
        PyFormIDValueLookupStatus::NotApplicable
    );
}
