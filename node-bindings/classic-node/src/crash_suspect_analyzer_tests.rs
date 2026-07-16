use super::*;

fn analyzer() -> CrashSuspectAnalyzer {
    build_analyzer(
        vec![JsCrashSuspectMainErrorRule {
            id: "main-rule".to_string(),
            name: "Main Rule".to_string(),
            severity: 5,
            main_error_contains_any: vec!["plugin.dll".to_string()],
        }],
        vec![JsCrashSuspectStackRule {
            id: "stack-rule".to_string(),
            name: "Stack Rule".to_string(),
            severity: 4,
            main_error_required_any: Vec::new(),
            main_error_optional_any: Vec::new(),
            stack_contains_any: vec!["StackSignal".to_string()],
            exclude_if_stack_contains_any: Vec::new(),
            stack_contains_at_least: Vec::new(),
        }],
    )
    .unwrap()
}

#[test]
fn owned_projection_returns_individual_semantic_findings() {
    let result = analyzer()
        .analyze_owned(JsCrashSuspectAnalysisInput {
            main_error: "plugin.dll".to_string(),
            call_stack: "StackSignal".to_string(),
        })
        .unwrap();

    assert_eq!(result.findings.len(), 3);
    assert_eq!(
        result.findings[0].kind,
        JsCrashSuspectFindingKind::MainErrorRule
    );
    assert_eq!(result.findings[0].rule_id.as_deref(), Some("main-rule"));
    assert_eq!(result.findings[0].name.as_deref(), Some("Main Rule"));
    assert_eq!(result.findings[0].severity, Some(5));
    assert_eq!(
        result.findings[1].kind,
        JsCrashSuspectFindingKind::StackRule
    );
    assert_eq!(
        result.findings[2].kind,
        JsCrashSuspectFindingKind::DllInvolvement
    );
    assert!(result.findings[2].rule_id.is_none());
}

#[test]
fn invalid_configuration_retains_shared_crash_suspect_error() {
    let error = build_analyzer(
        vec![JsCrashSuspectMainErrorRule {
            id: String::new(),
            name: "Invalid".to_string(),
            severity: 1,
            main_error_contains_any: vec!["signal".to_string()],
        }],
        Vec::new(),
    )
    .unwrap_err();

    assert_eq!(error.analyzer().as_str(), "crash_suspect");
    assert_eq!(error.code().as_str(), "invalid_configuration");
}
