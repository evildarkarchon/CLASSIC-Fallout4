use super::*;

fn analyzer() -> PyCrashSuspectAnalyzer {
    PyCrashSuspectAnalyzer::new(
        vec![PyCrashSuspectMainErrorRule::new(
            "main-rule".to_string(),
            "Main Rule".to_string(),
            5,
            vec!["plugin.dll".to_string()],
        )],
        vec![PyCrashSuspectStackRule::new(
            "stack-rule".to_string(),
            "Stack Rule".to_string(),
            4,
            Vec::new(),
            Vec::new(),
            vec!["StackSignal".to_string()],
            Vec::new(),
            Vec::new(),
        )],
    )
    .unwrap()
}

#[test]
fn python_projection_returns_individual_semantic_findings() {
    Python::attach(|py| {
        let result = analyzer()
            .analyze(
                py,
                PyCrashSuspectAnalysisInput::new(
                    "plugin.dll".to_string(),
                    "StackSignal".to_string(),
                ),
            )
            .unwrap();

        assert_eq!(result.findings.len(), 3);
        assert_eq!(
            result.findings[0].kind,
            PyCrashSuspectFindingKind::MainErrorRule
        );
        assert_eq!(result.findings[0].rule_id.as_deref(), Some("main-rule"));
        assert_eq!(result.findings[0].name.as_deref(), Some("Main Rule"));
        assert_eq!(result.findings[0].severity, Some(5));
        assert_eq!(
            result.findings[2].kind,
            PyCrashSuspectFindingKind::DllInvolvement
        );
        assert!(result.findings[2].rule_id.is_none());
    });
}

#[test]
fn invalid_configuration_raises_the_shared_analyzer_error() {
    Python::attach(|py| {
        let error = PyCrashSuspectAnalyzer::new(
            vec![PyCrashSuspectMainErrorRule::new(
                String::new(),
                "Invalid".to_string(),
                1,
                vec!["signal".to_string()],
            )],
            Vec::new(),
        )
        .unwrap_err();

        let value = error.value(py);
        assert_eq!(
            value
                .getattr("analyzer_kind")
                .unwrap()
                .getattr("code")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "crash_suspect"
        );
        assert_eq!(
            value.getattr("code").unwrap().extract::<String>().unwrap(),
            "invalid_configuration"
        );
    });
}
