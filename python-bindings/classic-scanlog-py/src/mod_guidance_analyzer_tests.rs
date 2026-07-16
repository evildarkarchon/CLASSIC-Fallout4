use super::*;

fn analyzer() -> PyModGuidanceAnalyzer {
    PyModGuidanceAnalyzer::new(
        vec![PyModGuidanceConflictRule::new(
            "alpha".to_string(),
            "beta".to_string(),
            "Alpha Mod".to_string(),
            "Beta Mod".to_string(),
            "Authored conflict description".to_string(),
            "Install the authored compatibility patch".to_string(),
            Some("https://example.invalid/patch".to_string()),
        )],
        vec![PyModGuidanceSolutionRule::new(
            "frequent-crash".to_string(),
            PyModGuidanceCriteriaKind::Any,
            vec!["crashfix".to_string()],
            Vec::new(),
            "Frequent Crash Mod".to_string(),
            "Authored frequent-crash guidance".to_string(),
        )],
        vec![PyModGuidanceSolutionRule::new(
            "solution".to_string(),
            PyModGuidanceCriteriaKind::All,
            vec!["solution".to_string(), "alpha".to_string()],
            Vec::new(),
            "Solution Mod".to_string(),
            "Authored solution guidance".to_string(),
        )],
        vec![
            PyModGuidanceImportantModRule::new(
                "installed.dll".to_string(),
                "Installed Important Mod".to_string(),
                "Installed authored description".to_string(),
                None,
                None,
                None,
            ),
            PyModGuidanceImportantModRule::new(
                "missing.dll".to_string(),
                "Missing Important Mod".to_string(),
                "Missing authored description".to_string(),
                Some("amd".to_string()),
                None,
                None,
            ),
            PyModGuidanceImportantModRule::new(
                "wronggpu.dll".to_string(),
                "Wrong GPU Important Mod".to_string(),
                "Wrong GPU authored description".to_string(),
                Some("nvidia".to_string()),
                Some("Authored GPU mismatch warning".to_string()),
                None,
            ),
        ],
    )
    .unwrap()
}

#[test]
fn criteria_kind_variants_are_available_to_python_callers() {
    Python::attach(|py| {
        let criteria_kind = py.get_type::<PyModGuidanceCriteriaKind>();

        let any = criteria_kind
            .getattr("Any")
            .unwrap()
            .extract::<PyModGuidanceCriteriaKind>()
            .unwrap();
        let all = criteria_kind
            .getattr("All")
            .unwrap()
            .extract::<PyModGuidanceCriteriaKind>()
            .unwrap();

        assert_eq!(any, PyModGuidanceCriteriaKind::Any);
        assert_eq!(all, PyModGuidanceCriteriaKind::All);
        assert_eq!(any.value(), "any");
        assert_eq!(all.value(), "all");
    });
}

#[test]
fn python_projection_returns_aggregate_semantic_guidance() {
    Python::attach(|py| {
        let plugins = PyDict::new(py);
        plugins.set_item("Alpha.esp", "01").unwrap();
        plugins.set_item("Beta.esp", "02").unwrap();
        plugins.set_item("CrashFix.esp", "03").unwrap();
        plugins.set_item("Solution.esp", "04").unwrap();
        let input = PyModGuidanceAnalysisInput::new(
            &plugins,
            Some("amd".to_string()),
            HashSet::from(["Installed.dll".to_string(), "WrongGpu.dll".to_string()]),
        )
        .unwrap();

        let result = analyzer().analyze(py, input).unwrap();

        assert_eq!(result.conflicts.len(), 1);
        assert_eq!(result.conflicts[0].state, PyModGuidanceMatchState::Matched);
        assert_eq!(result.conflicts[0].name_a, "Alpha Mod");
        assert_eq!(result.frequent_crashes[0].matched_plugin_ids, ["03"]);
        assert_eq!(result.solutions[0].matched_plugin_ids, ["04", "01"]);
        assert_eq!(
            result
                .important_mods
                .iter()
                .map(|guidance| guidance.state)
                .collect::<Vec<_>>(),
            [
                PyModGuidanceMatchState::Matched,
                PyModGuidanceMatchState::Missing,
                PyModGuidanceMatchState::GpuMismatch,
            ]
        );
        assert_eq!(
            result.important_mods[2].gpu_mismatch_warning.as_deref(),
            Some("Authored GPU mismatch warning")
        );
    });
}

#[test]
fn python_projection_preserves_important_mod_plugin_exclusions() {
    Python::attach(|py| {
        let analyzer = PyModGuidanceAnalyzer::new(
            Vec::new(),
            Vec::new(),
            Vec::new(),
            vec![PyModGuidanceImportantModRule::new(
                "installed.dll".to_string(),
                "Excluded Important Mod".to_string(),
                "Must not be returned".to_string(),
                None,
                None,
                Some(vec!["Suppressor.esp".to_string()]),
            )],
        )
        .unwrap();
        let plugins = PyDict::new(py);
        plugins.set_item("Suppressor.esp", "01").unwrap();
        let input = PyModGuidanceAnalysisInput::new(
            &plugins,
            Some("amd".to_string()),
            HashSet::from(["Installed.dll".to_string()]),
        )
        .unwrap();

        let result = analyzer.analyze(py, input).unwrap();

        assert!(result.important_mods.is_empty());
    });
}

#[test]
fn invalid_configuration_raises_the_shared_analyzer_error() {
    Python::attach(|py| {
        let error = PyModGuidanceAnalyzer::new(
            vec![PyModGuidanceConflictRule::new(
                String::new(),
                "beta".to_string(),
                "Alpha Mod".to_string(),
                "Beta Mod".to_string(),
                "Description".to_string(),
                "Fix".to_string(),
                None,
            )],
            Vec::new(),
            Vec::new(),
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
            "mod_guidance"
        );
        assert_eq!(
            value.getattr("code").unwrap().extract::<String>().unwrap(),
            "invalid_configuration"
        );
    });
}
