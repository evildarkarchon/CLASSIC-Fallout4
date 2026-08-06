use super::*;

#[test]
fn owned_projection_returns_typed_counts_and_explicit_empty_success() {
    let analyzer =
        build_analyzer(vec!["ActorBase".to_string()], vec!["System".to_string()]).unwrap();
    let populated = analyzer
        .analyze_owned(JsNamedRecordFindingAnalysisInput {
            crash_lines: vec![
                "ActorBase_Player".to_string(),
                "ActorBase_System".to_string(),
                "ActorBase_Player".to_string(),
            ],
        })
        .unwrap();
    let empty = analyzer
        .analyze_owned(JsNamedRecordFindingAnalysisInput {
            crash_lines: vec!["unrelated".to_string()],
        })
        .unwrap();

    assert_eq!(populated.findings.len(), 1);
    assert_eq!(populated.findings[0].record, "ActorBase_Player");
    assert_eq!(populated.findings[0].occurrences, 2);
    assert!(empty.findings.is_empty());
}

#[test]
fn invalid_configuration_retains_shared_named_record_error() {
    let error = build_analyzer(vec![" ".to_string()], Vec::new()).unwrap_err();

    assert_eq!(error.analyzer().as_str(), "named_record_finding");
    assert_eq!(error.code().as_str(), "invalid_configuration");
}
