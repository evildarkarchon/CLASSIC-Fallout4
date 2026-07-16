use super::*;
use std::sync::Arc;

#[test]
fn analyze_returns_distinct_records_with_occurrence_counts() {
    let analyzer = NamedRecordFindingAnalyzer::new(
        vec!["ActorBase".to_string(), "Weapon".to_string()],
        Vec::new(),
    )
    .unwrap();

    let result = analyzer
        .analyze(NamedRecordFindingAnalysisInput {
            crash_lines: vec![
                "ActorBase_Player".to_string(),
                "Weapon_Pistol".to_string(),
                "ActorBase_Player".to_string(),
            ],
        })
        .unwrap();

    assert_eq!(
        result,
        NamedRecordFindingAnalysisResult {
            findings: vec![
                NamedRecordFinding {
                    record: "ActorBase_Player".to_string(),
                    occurrences: 2,
                },
                NamedRecordFinding {
                    record: "Weapon_Pistol".to_string(),
                    occurrences: 1,
                },
            ],
        }
    );
}

#[test]
fn completed_analysis_without_matches_is_an_explicit_empty_result() {
    let analyzer =
        NamedRecordFindingAnalyzer::new(vec!["ActorBase".to_string()], Vec::new()).unwrap();

    let result = analyzer
        .analyze(NamedRecordFindingAnalysisInput {
            crash_lines: vec!["unrelated evidence".to_string()],
        })
        .unwrap();

    assert_eq!(result, NamedRecordFindingAnalysisResult::default());
}

#[test]
fn construction_rejects_empty_patterns_with_shared_typed_error() {
    let error = NamedRecordFindingAnalyzer::new(vec!["  ".to_string()], Vec::new()).unwrap_err();

    assert_eq!(error.analyzer(), AnalyzerKind::NamedRecordFinding);
    assert_eq!(error.code(), AnalyzerErrorCode::InvalidConfiguration);
    assert_eq!(
        error.message(),
        "Named Record Finding target record must not be empty"
    );
}

#[test]
fn construction_compiles_matchers_and_analysis_filters_ignored_evidence() {
    let analyzer =
        NamedRecordFindingAnalyzer::new(vec!["ActorBase".to_string()], vec!["System".to_string()])
            .unwrap();

    assert!(analyzer.configuration.target_matcher.is_some());
    assert!(analyzer.configuration.ignore_matcher.is_some());
    let result = analyzer
        .analyze(NamedRecordFindingAnalysisInput {
            crash_lines: vec![
                "ActorBase_System".to_string(),
                "ActorBase_Player".to_string(),
            ],
        })
        .unwrap();

    assert_eq!(
        result.findings,
        vec![NamedRecordFinding {
            record: "ActorBase_Player".to_string(),
            occurrences: 1,
        }]
    );
}

#[test]
fn analysis_preserves_legacy_rsp_record_extraction() {
    let analyzer = NamedRecordFindingAnalyzer::new(vec!["Weapon".to_string()], Vec::new()).unwrap();
    let line = "[RSP+50] 0x12345678 0xABCD Weapon_Pistol".to_string();
    let expected = line.get(30..).unwrap().trim().to_string();

    let result = analyzer
        .analyze(NamedRecordFindingAnalysisInput {
            crash_lines: vec![line],
        })
        .unwrap();

    assert_eq!(result.findings[0].record, expected);
}

#[test]
fn one_immutable_handle_is_safe_for_concurrent_analysis_without_leaking_counts() {
    let analyzer = Arc::new(
        NamedRecordFindingAnalyzer::new(vec!["ActorBase".to_string()], Vec::new()).unwrap(),
    );
    let threads = (1..=8)
        .map(|occurrences| {
            let analyzer = Arc::clone(&analyzer);
            std::thread::spawn(move || {
                analyzer
                    .analyze(NamedRecordFindingAnalysisInput {
                        crash_lines: vec!["ActorBase_Player".to_string(); occurrences],
                    })
                    .unwrap()
            })
        })
        .collect::<Vec<_>>();

    for (index, thread) in threads.into_iter().enumerate() {
        assert_eq!(
            thread.join().unwrap().findings[0].occurrences,
            index as u32 + 1
        );
    }
}

#[test]
fn immutable_analyzer_handle_is_send_and_sync() {
    fn assert_send_sync<T: Send + Sync>() {}

    assert_send_sync::<NamedRecordFindingAnalyzer>();
}
