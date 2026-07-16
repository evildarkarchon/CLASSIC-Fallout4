use super::*;
use std::sync::Arc;

#[test]
fn analyze_returns_typed_plugin_identity_and_occurrence_counts() {
    let analyzer = PluginEvidenceAnalyzer::new(Vec::new()).unwrap();

    let result = analyzer
        .analyze(PluginEvidenceAnalysisInput {
            call_stack: vec![
                "Alpha.ESP called Beta.esm".to_string(),
                "alpha.esp called twice on one alpha.esp line".to_string(),
                "beta.esm appeared again".to_string(),
            ],
            plugins: vec!["Alpha.ESP".to_string(), "Beta.esm".to_string()],
        })
        .unwrap();

    assert_eq!(
        result,
        PluginEvidenceAnalysisResult {
            evidence: vec![
                PluginEvidence {
                    plugin: "alpha.esp".to_string(),
                    occurrences: 2,
                },
                PluginEvidence {
                    plugin: "beta.esm".to_string(),
                    occurrences: 2,
                },
            ],
        }
    );
}

#[test]
fn construction_rejects_empty_ignored_plugin_with_shared_typed_error() {
    let error = PluginEvidenceAnalyzer::new(vec!["   ".to_string()]).unwrap_err();

    assert_eq!(error.analyzer(), crate::AnalyzerKind::PluginEvidence);
    assert_eq!(error.code(), crate::AnalyzerErrorCode::InvalidConfiguration);
    assert_eq!(
        error.message(),
        "Plugin Evidence ignored plugin must not be empty"
    );
}

#[test]
fn completed_analysis_without_evidence_is_an_explicit_empty_result() {
    let analyzer = PluginEvidenceAnalyzer::new(Vec::new()).unwrap();

    let result = analyzer
        .analyze(PluginEvidenceAnalysisInput {
            call_stack: vec!["unrelated stack line".to_string()],
            plugins: vec!["Example.esp".to_string()],
        })
        .unwrap();

    assert_eq!(result, PluginEvidenceAnalysisResult::default());
}

#[test]
fn analysis_filters_ignored_plugins_modified_by_lines_and_duplicate_identities() {
    let analyzer = PluginEvidenceAnalyzer::new(vec!["Fallout4.esm".to_string()]).unwrap();

    let result = analyzer
        .analyze(PluginEvidenceAnalysisInput {
            call_stack: vec![
                "Fallout4.esm and Useful.ESP".to_string(),
                "modified by: useful.esp".to_string(),
                "useful.esp useful.esp".to_string(),
            ],
            plugins: vec![
                "Fallout4.esm".to_string(),
                "Useful.ESP".to_string(),
                "useful.esp".to_string(),
            ],
        })
        .unwrap();

    assert_eq!(
        result.evidence,
        vec![PluginEvidence {
            plugin: "useful.esp".to_string(),
            occurrences: 2,
        }]
    );
}

#[test]
fn analysis_discards_blank_candidates_and_normalizes_padded_duplicates() {
    let analyzer = PluginEvidenceAnalyzer::new(Vec::new()).unwrap();

    let result = analyzer
        .analyze(PluginEvidenceAnalysisInput {
            call_stack: vec!["example.esp and unrelated spacing".to_string()],
            plugins: vec![
                " ".to_string(),
                " Example.ESP ".to_string(),
                "example.esp".to_string(),
            ],
        })
        .unwrap();

    assert_eq!(
        result.evidence,
        vec![PluginEvidence {
            plugin: "example.esp".to_string(),
            occurrences: 1,
        }]
    );
}

#[test]
fn one_immutable_handle_is_safe_for_concurrent_analysis_without_leaking_counts() {
    let analyzer = Arc::new(PluginEvidenceAnalyzer::new(Vec::new()).unwrap());
    let threads = (1..=8)
        .map(|occurrences| {
            let analyzer = Arc::clone(&analyzer);
            std::thread::spawn(move || {
                analyzer
                    .analyze(PluginEvidenceAnalysisInput {
                        call_stack: vec!["example.esp".to_string(); occurrences],
                        plugins: vec!["Example.esp".to_string()],
                    })
                    .unwrap()
            })
        })
        .collect::<Vec<_>>();

    for (index, thread) in threads.into_iter().enumerate() {
        assert_eq!(
            thread.join().unwrap().evidence[0].occurrences,
            index as u32 + 1
        );
    }
}

#[test]
fn immutable_analyzer_handle_is_send_and_sync() {
    fn assert_send_sync<T: Send + Sync>() {}

    assert_send_sync::<PluginEvidenceAnalyzer>();
}
