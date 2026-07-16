use super::*;

#[test]
fn python_projection_returns_typed_counts_and_explicit_empty_success() {
    Python::initialize();
    Python::attach(|py| {
        let analyzer = PyPluginEvidenceAnalyzer::new(vec!["Fallout4.esm".to_string()]).unwrap();
        let populated = analyzer
            .analyze(
                py,
                PyPluginEvidenceAnalysisInput::new(
                    vec!["Example.ESP".to_string(), "example.esp".to_string()],
                    vec!["Example.ESP".to_string(), "Fallout4.esm".to_string()],
                ),
            )
            .unwrap();
        let empty = analyzer
            .analyze(
                py,
                PyPluginEvidenceAnalysisInput::new(Vec::new(), vec!["Example.ESP".to_string()]),
            )
            .unwrap();

        assert_eq!(populated.evidence.len(), 1);
        assert_eq!(populated.evidence[0].plugin, "example.esp");
        assert_eq!(populated.evidence[0].occurrences, 2);
        assert!(empty.evidence.is_empty());
    });
}

#[test]
fn invalid_configuration_raises_the_shared_analyzer_error() {
    Python::initialize();
    Python::attach(|py| {
        let error = PyPluginEvidenceAnalyzer::new(vec![" ".to_string()]).unwrap_err();
        let value = error.value(py);

        assert_eq!(
            value
                .getattr("analyzer_kind")
                .unwrap()
                .getattr("code")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "plugin_evidence"
        );
        assert_eq!(
            value.getattr("code").unwrap().extract::<String>().unwrap(),
            "invalid_configuration"
        );
    });
}
