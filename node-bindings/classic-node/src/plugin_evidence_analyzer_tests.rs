use super::*;

#[test]
fn owned_projection_returns_typed_counts_and_explicit_empty_success() {
    let analyzer = build_analyzer(vec!["Fallout4.esm".to_string()]).unwrap();

    let populated = analyzer
        .analyze_owned(JsPluginEvidenceAnalysisInput {
            call_stack: vec!["Example.ESP".to_string(), "example.esp".to_string()],
            plugins: vec!["Example.ESP".to_string(), "Fallout4.esm".to_string()],
        })
        .unwrap();
    let empty = analyzer
        .analyze_owned(JsPluginEvidenceAnalysisInput {
            call_stack: Vec::new(),
            plugins: vec!["Example.ESP".to_string()],
        })
        .unwrap();

    assert_eq!(populated.evidence.len(), 1);
    assert_eq!(populated.evidence[0].plugin, "example.esp");
    assert_eq!(populated.evidence[0].occurrences, 2);
    assert!(empty.evidence.is_empty());
}

#[test]
fn invalid_configuration_retains_shared_plugin_evidence_error() {
    let error = build_analyzer(vec![" ".to_string()]).unwrap_err();

    assert_eq!(error.analyzer().as_str(), "plugin_evidence");
    assert_eq!(error.code().as_str(), "invalid_configuration");
}
