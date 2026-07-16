use super::*;

fn conflict() -> JsModConflictRule {
    JsModConflictRule {
        mod_a: "alpha".to_string(),
        mod_b: "beta".to_string(),
        name_a: "Alpha Mod".to_string(),
        name_b: "Beta Mod".to_string(),
        description: "Authored conflict description".to_string(),
        fix: "Install the compatibility patch".to_string(),
        link: Some("https://example.invalid/patch".to_string()),
    }
}

fn solution(id: &str, criterion: &str, name: &str) -> JsModSolutionRule {
    JsModSolutionRule {
        id: id.to_string(),
        criteria_kind: JsModGuidanceCriteriaKind::Any,
        criteria: vec![criterion.to_string()],
        exceptions: Vec::new(),
        name: name.to_string(),
        description: format!("Authored {name} guidance"),
    }
}

fn important_mods() -> Vec<JsImportantModRule> {
    vec![
        JsImportantModRule {
            detect: "installed.dll".to_string(),
            name: "Installed Mod".to_string(),
            description: "Installed authored description".to_string(),
            gpu: None,
            gpu_mismatch_warning: None,
            exclude_when_plugin_any: None,
        },
        JsImportantModRule {
            detect: "missing.dll".to_string(),
            name: "Missing Mod".to_string(),
            description: "Missing authored description".to_string(),
            gpu: Some("amd".to_string()),
            gpu_mismatch_warning: None,
            exclude_when_plugin_any: None,
        },
        JsImportantModRule {
            detect: "rival.dll".to_string(),
            name: "Rival Mod".to_string(),
            description: "Rival authored description".to_string(),
            gpu: Some("nvidia".to_string()),
            gpu_mismatch_warning: Some("Authored mismatch warning".to_string()),
            exclude_when_plugin_any: None,
        },
    ]
}

fn analyzer() -> ModGuidanceAnalyzer {
    build_analyzer(
        vec![conflict()],
        vec![solution("frequent", "frequent.esp", "Frequent Crash Mod")],
        vec![solution("solution", "solution.esp", "Solution Mod")],
        important_mods(),
    )
    .unwrap()
}

fn populated_input() -> JsModGuidanceAnalysisInput {
    JsModGuidanceAnalysisInput {
        plugins: vec![
            JsModGuidancePlugin {
                name: "Alpha.esp".to_string(),
                id: "02".to_string(),
            },
            JsModGuidancePlugin {
                name: "Beta.esp".to_string(),
                id: "03".to_string(),
            },
            JsModGuidancePlugin {
                name: "Frequent.esp".to_string(),
                id: "04".to_string(),
            },
            JsModGuidancePlugin {
                name: "Solution.esp".to_string(),
                id: "05".to_string(),
            },
        ],
        user_gpu: Some("amd".to_string()),
        xse_modules: vec!["Installed.dll".to_string(), "Rival.dll".to_string()],
    }
}

#[test]
fn owned_projection_preserves_all_authored_fields_and_match_states() {
    let result = analyzer().analyze_owned(populated_input()).unwrap();

    assert_eq!(result.conflicts.len(), 1);
    assert_eq!(result.conflicts[0].state, JsModGuidanceMatchState::Matched);
    assert_eq!(result.conflicts[0].mod_a, "alpha");
    assert_eq!(result.conflicts[0].mod_b, "beta");
    assert_eq!(result.conflicts[0].name_a, "Alpha Mod");
    assert_eq!(result.conflicts[0].name_b, "Beta Mod");
    assert_eq!(
        result.conflicts[0].description,
        "Authored conflict description"
    );
    assert_eq!(result.conflicts[0].fix, "Install the compatibility patch");
    assert_eq!(
        result.conflicts[0].link.as_deref(),
        Some("https://example.invalid/patch")
    );

    assert_eq!(result.frequent_crashes.len(), 1);
    assert_eq!(result.frequent_crashes[0].id, "frequent");
    assert_eq!(result.frequent_crashes[0].matched_plugin_ids, vec!["04"]);
    assert_eq!(result.solutions.len(), 1);
    assert_eq!(result.solutions[0].id, "solution");

    assert_eq!(result.important_mods.len(), 3);
    assert_eq!(
        result.important_mods[0].state,
        JsModGuidanceMatchState::Matched
    );
    assert_eq!(
        result.important_mods[1].state,
        JsModGuidanceMatchState::Missing
    );
    assert_eq!(
        result.important_mods[2].state,
        JsModGuidanceMatchState::GpuMismatch
    );
    assert_eq!(
        result.important_mods[2].gpu_mismatch_warning.as_deref(),
        Some("Authored mismatch warning")
    );
}

#[test]
fn all_criteria_and_exclusion_configuration_project_to_core() {
    let analyzer = build_analyzer(
        Vec::new(),
        vec![JsModSolutionRule {
            id: "both".to_string(),
            criteria_kind: JsModGuidanceCriteriaKind::All,
            criteria: vec!["first.esp".to_string(), "second.esp".to_string()],
            exceptions: Vec::new(),
            name: "Both".to_string(),
            description: "Both matched".to_string(),
        }],
        Vec::new(),
        vec![JsImportantModRule {
            detect: "excluded.dll".to_string(),
            name: "Excluded".to_string(),
            description: "Must not appear".to_string(),
            gpu: None,
            gpu_mismatch_warning: None,
            exclude_when_plugin_any: Some(vec!["exception.esp".to_string()]),
        }],
    )
    .unwrap();
    let result = analyzer
        .analyze_owned(JsModGuidanceAnalysisInput {
            plugins: vec![
                JsModGuidancePlugin {
                    name: "First.esp".to_string(),
                    id: "02".to_string(),
                },
                JsModGuidancePlugin {
                    name: "Second.esp".to_string(),
                    id: "03".to_string(),
                },
                JsModGuidancePlugin {
                    name: "Exception.esp".to_string(),
                    id: "04".to_string(),
                },
            ],
            user_gpu: None,
            xse_modules: vec!["Excluded.dll".to_string()],
        })
        .unwrap();

    assert_eq!(
        result.frequent_crashes[0].matched_plugin_ids,
        vec!["02", "03"]
    );
    assert!(result.important_mods.is_empty());
}

#[test]
fn completed_no_match_analysis_returns_four_explicit_empty_collections() {
    let analyzer = build_analyzer(Vec::new(), Vec::new(), Vec::new(), Vec::new()).unwrap();
    let result = analyzer
        .analyze_owned(JsModGuidanceAnalysisInput {
            plugins: Vec::new(),
            user_gpu: None,
            xse_modules: Vec::new(),
        })
        .unwrap();

    assert!(result.conflicts.is_empty());
    assert!(result.frequent_crashes.is_empty());
    assert!(result.solutions.is_empty());
    assert!(result.important_mods.is_empty());
}

#[test]
fn invalid_configuration_retains_shared_mod_guidance_error() {
    let mut invalid = conflict();
    invalid.mod_a.clear();

    let error = build_analyzer(vec![invalid], Vec::new(), Vec::new(), Vec::new()).unwrap_err();

    assert_eq!(error.analyzer().as_str(), "mod_guidance");
    assert_eq!(error.code().as_str(), "invalid_configuration");
}
