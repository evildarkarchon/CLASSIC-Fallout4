use classic_config_core::{SuspectErrorRule, SuspectStackRule};
use std::sync::Arc;

use super::*;

#[test]
fn analyze_returns_one_semantic_finding_for_each_matched_rule_and_dll_notice() {
    let analyzer = CrashSuspectAnalyzer::new(
        vec![
            SuspectErrorRule {
                id: "lower_severity".to_string(),
                name: "Lower Severity".to_string(),
                severity: 2,
                main_error_contains_any: vec!["ACCESS_VIOLATION".to_string()],
            },
            SuspectErrorRule {
                id: "higher_severity".to_string(),
                name: "Higher Severity".to_string(),
                severity: 5,
                main_error_contains_any: vec!["plugin.dll".to_string()],
            },
        ],
        vec![SuspectStackRule {
            id: "stack_rule".to_string(),
            name: "Stack Rule".to_string(),
            severity: 4,
            main_error_required_any: Vec::new(),
            main_error_optional_any: Vec::new(),
            stack_contains_any: vec!["StackSignal".to_string()],
            exclude_if_stack_contains_any: Vec::new(),
            stack_contains_at_least: Vec::new(),
        }],
    )
    .unwrap();

    let result = analyzer
        .analyze(CrashSuspectAnalysisInput {
            main_error: "ACCESS_VIOLATION in plugin.dll".to_string(),
            call_stack: "StackSignal".to_string(),
        })
        .unwrap();

    assert_eq!(
        result.findings,
        vec![
            CrashSuspectFinding::MainErrorRule {
                rule_id: "lower_severity".to_string(),
                name: "Lower Severity".to_string(),
                severity: 2,
            },
            CrashSuspectFinding::MainErrorRule {
                rule_id: "higher_severity".to_string(),
                name: "Higher Severity".to_string(),
                severity: 5,
            },
            CrashSuspectFinding::StackRule {
                rule_id: "stack_rule".to_string(),
                name: "Stack Rule".to_string(),
                severity: 4,
            },
            CrashSuspectFinding::DllInvolvement,
        ]
    );
}

#[test]
fn construction_rejects_invalid_matcher_configuration_with_shared_typed_error() {
    let error = CrashSuspectAnalyzer::new(
        vec![SuspectErrorRule {
            id: String::new(),
            name: "Invalid Rule".to_string(),
            severity: 1,
            main_error_contains_any: vec!["signal".to_string()],
        }],
        Vec::new(),
    )
    .unwrap_err();

    assert_eq!(error.analyzer(), crate::AnalyzerKind::CrashSuspect);
    assert_eq!(error.code(), crate::AnalyzerErrorCode::InvalidConfiguration);
    assert_eq!(
        error.message(),
        "Crash Suspect main-error rule id must not be empty"
    );
}

#[test]
fn completed_analysis_without_matches_is_an_explicit_empty_result() {
    let analyzer = CrashSuspectAnalyzer::new(Vec::new(), Vec::new()).unwrap();

    let result = analyzer
        .analyze(CrashSuspectAnalysisInput::default())
        .unwrap();

    assert_eq!(result, CrashSuspectAnalysisResult::default());
}

#[test]
fn concurrent_calls_do_not_leak_findings_between_inputs() {
    let analyzer = Arc::new(
        CrashSuspectAnalyzer::new(
            vec![SuspectErrorRule {
                id: "isolated".to_string(),
                name: "Isolated Finding".to_string(),
                severity: 3,
                main_error_contains_any: vec!["MATCH".to_string()],
            }],
            Vec::new(),
        )
        .unwrap(),
    );
    let threads = (0..8)
        .map(|index| {
            let analyzer = Arc::clone(&analyzer);
            std::thread::spawn(move || {
                analyzer
                    .analyze(CrashSuspectAnalysisInput {
                        main_error: if index % 2 == 0 {
                            "MATCH".to_string()
                        } else {
                            "no finding".to_string()
                        },
                        call_stack: String::new(),
                    })
                    .unwrap()
            })
        })
        .collect::<Vec<_>>();

    for (index, thread) in threads.into_iter().enumerate() {
        let result = thread.join().unwrap();
        assert_eq!(result.findings.len(), usize::from(index % 2 == 0));
    }
}

#[test]
fn immutable_analyzer_handle_is_send_and_sync() {
    fn assert_send_sync<T: Send + Sync>() {}

    assert_send_sync::<CrashSuspectAnalyzer>();
}
