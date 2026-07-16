use std::collections::HashSet;
use std::sync::Arc;

use classic_config_core::{
    CoreModEntry, CoreModExclude, ModConflictEntry, ModSolutionCriteria, ModSolutionEntry,
};
use indexmap::IndexMap;

use super::*;
use crate::{AnalyzerErrorCode, AnalyzerKind};

fn conflict() -> ModConflictEntry {
    ModConflictEntry {
        mod_a: "alpha".to_string(),
        mod_b: "beta".to_string(),
        name_a: "Alpha Mod".to_string(),
        name_b: "Beta Mod".to_string(),
        description: "Authored conflict description".to_string(),
        fix: "Install the authored compatibility patch".to_string(),
        link: Some("https://example.invalid/patch".to_string()),
    }
}

fn solution(id: &str, criterion: &str, name: &str, description: &str) -> ModSolutionEntry {
    ModSolutionEntry {
        id: id.to_string(),
        criteria: ModSolutionCriteria::Any(vec![criterion.to_string()]),
        exceptions: Vec::new(),
        name: name.to_string(),
        description: description.to_string(),
    }
}

fn important_mods() -> Vec<CoreModEntry> {
    vec![
        CoreModEntry {
            detect: "installed.dll".to_string(),
            name: "Installed Important Mod".to_string(),
            description: "Installed authored description".to_string(),
            gpu: None,
            gpu_mismatch_warning: None,
            exclude_when: None,
        },
        CoreModEntry {
            detect: "missing.dll".to_string(),
            name: "Missing Important Mod".to_string(),
            description: "Missing authored description\nwith a second line".to_string(),
            gpu: Some("amd".to_string()),
            gpu_mismatch_warning: None,
            exclude_when: None,
        },
        CoreModEntry {
            detect: "rival.dll".to_string(),
            name: "Rival GPU Mod".to_string(),
            description: "Rival authored description".to_string(),
            gpu: Some("nvidia".to_string()),
            gpu_mismatch_warning: Some("Authored mismatch warning\nkeep this line".to_string()),
            exclude_when: Some(CoreModExclude::PluginAny(vec![
                "TotalConversion.esm".to_string(),
            ])),
        },
    ]
}

fn analyzer() -> ModGuidanceAnalyzer {
    ModGuidanceAnalyzer::new(
        vec![conflict()],
        vec![solution(
            "frequent",
            "frequent.esp",
            "Frequent Crash Mod",
            "Authored frequent-crash guidance",
        )],
        vec![solution(
            "solution",
            "solution.esp",
            "Solution Mod",
            "Authored solution guidance",
        )],
        important_mods(),
    )
    .expect("valid Mod Guidance configuration")
}

fn populated_input() -> ModGuidanceAnalysisInput {
    ModGuidanceAnalysisInput {
        plugins: IndexMap::from([
            ("Alpha.esp".to_string(), "02".to_string()),
            ("Beta.esp".to_string(), "03".to_string()),
            ("Frequent.esp".to_string(), "04".to_string()),
            ("Solution.esp".to_string(), "05".to_string()),
            ("Rival.esp".to_string(), "06".to_string()),
        ]),
        user_gpu: Some("amd".to_string()),
        xse_modules: HashSet::from(["Installed.dll".to_string(), "Rival.dll".to_string()]),
    }
}

#[test]
fn aggregate_analysis_preserves_authored_guidance_and_match_state() {
    let result = analyzer().analyze(populated_input()).unwrap();

    assert_eq!(result.conflicts.len(), 1);
    assert_eq!(result.conflicts[0].state, ModGuidanceMatchState::Matched);
    assert_eq!(result.conflicts[0].mod_a, "alpha");
    assert_eq!(result.conflicts[0].mod_b, "beta");
    assert_eq!(result.conflicts[0].name_a, "Alpha Mod");
    assert_eq!(result.conflicts[0].name_b, "Beta Mod");
    assert_eq!(
        result.conflicts[0].description,
        "Authored conflict description"
    );
    assert_eq!(
        result.conflicts[0].fix,
        "Install the authored compatibility patch"
    );
    assert_eq!(
        result.conflicts[0].link.as_deref(),
        Some("https://example.invalid/patch")
    );

    assert_eq!(result.frequent_crashes.len(), 1);
    assert_eq!(result.frequent_crashes[0].id, "frequent");
    assert_eq!(
        result.frequent_crashes[0].state,
        ModGuidanceMatchState::Matched
    );
    assert_eq!(result.frequent_crashes[0].matched_plugin_ids, vec!["04"]);
    assert_eq!(
        result.frequent_crashes[0].description,
        "Authored frequent-crash guidance"
    );

    assert_eq!(result.solutions.len(), 1);
    assert_eq!(result.solutions[0].id, "solution");
    assert_eq!(result.solutions[0].name, "Solution Mod");
    assert_eq!(
        result.solutions[0].description,
        "Authored solution guidance"
    );

    assert_eq!(result.important_mods.len(), 3);
    assert_eq!(result.important_mods[0].detect, "installed.dll");
    assert_eq!(
        result.important_mods[0].state,
        ModGuidanceMatchState::Matched
    );
    assert_eq!(
        result.important_mods[1].state,
        ModGuidanceMatchState::Missing
    );
    assert_eq!(
        result.important_mods[1].description,
        "Missing authored description\nwith a second line"
    );
    assert_eq!(
        result.important_mods[2].state,
        ModGuidanceMatchState::GpuMismatch
    );
    assert_eq!(result.important_mods[2].gpu.as_deref(), Some("nvidia"));
    assert_eq!(
        result.important_mods[2].gpu_mismatch_warning.as_deref(),
        Some("Authored mismatch warning\nkeep this line")
    );
}

#[test]
fn structured_criteria_exceptions_exclusions_and_unknown_gpu_keep_existing_semantics() {
    let all_entry = ModSolutionEntry {
        id: "requires-both".to_string(),
        criteria: ModSolutionCriteria::All(vec!["first.esp".to_string(), "second.esp".to_string()]),
        exceptions: Vec::new(),
        name: "Requires Both".to_string(),
        description: "Both plugins matched".to_string(),
    };
    let suppressed_entry = ModSolutionEntry {
        id: "suppressed".to_string(),
        criteria: ModSolutionCriteria::Any(vec!["first.esp".to_string()]),
        exceptions: vec!["exception.esp".to_string()],
        name: "Suppressed".to_string(),
        description: "Must not appear".to_string(),
    };
    let important = vec![
        CoreModEntry {
            detect: "excluded.dll".to_string(),
            name: "Excluded".to_string(),
            description: "Must not appear".to_string(),
            gpu: None,
            gpu_mismatch_warning: None,
            exclude_when: Some(CoreModExclude::PluginAny(vec!["exception.esp".to_string()])),
        },
        CoreModEntry {
            detect: "unknown-gpu-missing.dll".to_string(),
            name: "Unknown GPU Missing".to_string(),
            description: "Must wait for GPU facts".to_string(),
            gpu: None,
            gpu_mismatch_warning: None,
            exclude_when: None,
        },
    ];
    let analyzer = ModGuidanceAnalyzer::new(
        Vec::new(),
        vec![all_entry, suppressed_entry],
        Vec::new(),
        important,
    )
    .unwrap();
    let input = ModGuidanceAnalysisInput {
        plugins: IndexMap::from([
            ("First.esp".to_string(), "02".to_string()),
            ("Second.esp".to_string(), "03".to_string()),
            ("Exception.esp".to_string(), "04".to_string()),
        ]),
        user_gpu: None,
        xse_modules: HashSet::from(["Excluded.dll".to_string()]),
    };

    let result = analyzer.analyze(input).unwrap();

    assert_eq!(result.frequent_crashes.len(), 1);
    assert_eq!(result.frequent_crashes[0].id, "requires-both");
    assert_eq!(
        result.frequent_crashes[0].matched_plugin_ids,
        vec!["02", "03"]
    );
    assert!(result.important_mods.is_empty());
}

#[test]
fn completed_no_match_analysis_is_an_explicit_empty_result() {
    let analyzer = ModGuidanceAnalyzer::new(Vec::new(), Vec::new(), Vec::new(), Vec::new())
        .expect("empty configuration is valid");

    let result = analyzer
        .analyze(ModGuidanceAnalysisInput::default())
        .unwrap();

    assert_eq!(result, ModGuidanceAnalysisResult::default());
}

#[test]
fn invalid_matcher_configuration_fails_during_construction() {
    let mut invalid = conflict();
    invalid.mod_a = " ".to_string();

    let error = ModGuidanceAnalyzer::new(vec![invalid], Vec::new(), Vec::new(), Vec::new())
        .expect_err("empty conflict matcher must be rejected before analysis");

    assert_eq!(error.analyzer(), AnalyzerKind::ModGuidance);
    assert_eq!(error.code(), AnalyzerErrorCode::InvalidConfiguration);
    assert!(error.message().contains("mod_a"));
}

#[test]
fn immutable_analyzer_is_reusable_across_threads() {
    let analyzer = Arc::new(analyzer());
    let tasks = (0..8)
        .map(|_| {
            let analyzer = Arc::clone(&analyzer);
            std::thread::spawn(move || analyzer.analyze(populated_input()))
        })
        .collect::<Vec<_>>();

    for task in tasks {
        let result = task
            .join()
            .expect("analysis thread should not panic")
            .unwrap();
        assert_eq!(result.conflicts.len(), 1);
        assert_eq!(result.frequent_crashes.len(), 1);
        assert_eq!(result.solutions.len(), 1);
        assert_eq!(result.important_mods.len(), 3);
    }
}

#[test]
fn important_mod_matching_prefers_the_leftmost_longest_overlapping_literal() {
    let entries = vec![
        CoreModEntry {
            detect: "overlap".to_string(),
            name: "Short".to_string(),
            description: "Short token".to_string(),
            gpu: None,
            gpu_mismatch_warning: None,
            exclude_when: None,
        },
        CoreModEntry {
            detect: "overlap-long".to_string(),
            name: "Long".to_string(),
            description: "Long token".to_string(),
            gpu: None,
            gpu_mismatch_warning: None,
            exclude_when: None,
        },
    ];
    let analyzer = ModGuidanceAnalyzer::new(Vec::new(), Vec::new(), Vec::new(), entries).unwrap();
    let input = ModGuidanceAnalysisInput {
        plugins: IndexMap::new(),
        user_gpu: None,
        xse_modules: HashSet::from(["Overlap-Long.dll".to_string()]),
    };

    let result = analyzer.analyze(input).unwrap();

    assert_eq!(result.important_mods.len(), 1);
    assert_eq!(result.important_mods[0].name, "Long");
}

#[test]
fn literal_matching_is_unicode_case_insensitive() {
    let analyzer = ModGuidanceAnalyzer::new(
        Vec::new(),
        Vec::new(),
        vec![solution(
            "unicode",
            "ÉLITE.esp",
            "Unicode Match",
            "Unicode case folding should match",
        )],
        Vec::new(),
    )
    .unwrap();
    let input = ModGuidanceAnalysisInput {
        plugins: IndexMap::from([("élite.esp".to_string(), "02".to_string())]),
        ..ModGuidanceAnalysisInput::default()
    };

    let result = analyzer.analyze(input).unwrap();

    assert_eq!(result.solutions.len(), 1);
    assert_eq!(result.solutions[0].id, "unicode");
}

#[test]
fn conflict_matching_preserves_longest_non_overlapping_token_semantics() {
    let entries = vec![
        ModConflictEntry {
            mod_a: "foo".to_string(),
            mod_b: "bar".to_string(),
            name_a: "Foo".to_string(),
            name_b: "Bar".to_string(),
            description: "Short-token conflict".to_string(),
            fix: "Do not report this conflict".to_string(),
            link: None,
        },
        ModConflictEntry {
            mod_a: "foobar".to_string(),
            mod_b: "never".to_string(),
            name_a: "Foobar".to_string(),
            name_b: "Never".to_string(),
            description: "Longest token reserves the overlap".to_string(),
            fix: "No conflict because Never is absent".to_string(),
            link: None,
        },
    ];
    let analyzer = ModGuidanceAnalyzer::new(entries, Vec::new(), Vec::new(), Vec::new()).unwrap();
    let input = ModGuidanceAnalysisInput {
        plugins: IndexMap::from([
            ("Foobar.esp".to_string(), "02".to_string()),
            ("Bar.esp".to_string(), "03".to_string()),
        ]),
        ..ModGuidanceAnalysisInput::default()
    };

    let result = analyzer.analyze(input).unwrap();

    assert!(result.conflicts.is_empty());
}
