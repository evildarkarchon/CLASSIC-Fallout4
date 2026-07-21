use super::*;

#[test]
fn python_projection_returns_typed_counts_and_explicit_empty_success() {
    Python::initialize();
    Python::attach(|py| {
        let analyzer = PyNamedRecordFindingAnalyzer::new(
            vec!["ActorBase".to_string()],
            vec!["System".to_string()],
        )
        .unwrap();
        let populated = analyzer
            .analyze(
                py,
                PyNamedRecordFindingAnalysisInput::new(vec![
                    "ActorBase_Player".to_string(),
                    "ActorBase_System".to_string(),
                    "ActorBase_Player".to_string(),
                ]),
            )
            .unwrap();
        let empty = analyzer
            .analyze(
                py,
                PyNamedRecordFindingAnalysisInput::new(vec!["unrelated".to_string()]),
            )
            .unwrap();

        assert_eq!(populated.findings.len(), 1);
        assert_eq!(populated.findings[0].record, "ActorBase_Player");
        assert_eq!(populated.findings[0].occurrences, 2);
        assert!(empty.findings.is_empty());
    });
}

#[test]
fn invalid_configuration_raises_shared_named_record_error() {
    Python::initialize();
    Python::attach(|py| {
        let error =
            PyNamedRecordFindingAnalyzer::new(vec![" ".to_string()], Vec::new()).unwrap_err();
        let value = error.value(py);

        assert_eq!(
            value
                .getattr("analyzer_kind")
                .unwrap()
                .getattr("code")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "named_record_finding"
        );
        assert_eq!(
            value.getattr("code").unwrap().extract::<String>().unwrap(),
            "invalid_configuration"
        );
    });
}
