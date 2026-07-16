use std::collections::HashSet;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use super::*;

fn analyzer_entry<'py>(py: Python<'py>, version: u32) -> PyResult<Bound<'py, PyDict>> {
    let action = PyDict::new(py);
    action.set_item("kind", "notice")?;
    action.set_item("placement", "error_information")?;
    action.set_item("severity", "warning")?;
    action.set_item("message", "Authored {crashgen_name} guidance")?;
    action.set_item("fix", "Authored fix")?;

    let when = PyDict::new(py);
    when.set_item("plugin_any", vec!["MixedCase.dll"])?;
    let preflight = PyDict::new(py);
    preflight.set_item("id", "compatibility_notice")?;
    preflight.set_item("when", when)?;
    preflight.set_item("action", action)?;

    let rules = PyDict::new(py);
    rules.set_item("version", version)?;
    rules.set_item("preflight", PyList::new(py, [preflight])?)?;

    let entry = PyDict::new(py);
    entry.set_item("display_section", "[Compatibility]")?;
    entry.set_item("ignore_keys", vec!["IgnoredSetting"])?;
    entry.set_item("settings_rules", rules)?;
    Ok(entry)
}

fn settings<'py>(py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
    let compatibility = PyDict::new(py);
    compatibility.set_item("DisabledSetting", "false")?;
    compatibility.set_item("IgnoredSetting", "false")?;
    let settings = PyDict::new(py);
    settings.set_item("Compatibility", compatibility)?;
    Ok(settings)
}

#[test]
fn python_projection_preserves_semantics_and_explicit_empty_results() {
    Python::initialize();
    Python::attach(|py| -> PyResult<()> {
        let analyzer = PyCrashgenSettingsAnalyzer::new(
            "Buffout 4".to_string(),
            analyzer_entry(py, 1)?.as_any(),
        )?;

        let input = PyCrashgenSettingsAnalysisInput::new(
            &settings(py)?,
            HashSet::from(["MIXEDCASE.DLL".to_string()]),
            None,
            Some("og".to_string()),
        )?;
        let populated = analyzer.analyze(py, input)?;
        assert_eq!(populated.expectation_outcomes.len(), 1);
        assert_eq!(
            populated.expectation_outcomes[0].message,
            "Authored Buffout 4 guidance"
        );
        assert_eq!(
            populated.expectation_outcomes[0].fix.as_deref(),
            Some("Authored fix")
        );
        assert_eq!(
            populated.expectation_outcomes[0].placement,
            PyAutoscanReportPlacement::ErrorInformation
        );
        assert_eq!(populated.disabled_setting_notices.len(), 1);
        assert_eq!(
            populated.disabled_setting_notices[0].setting_name,
            "DisabledSetting"
        );

        let empty_settings = PyDict::new(py);
        let empty_input =
            PyCrashgenSettingsAnalysisInput::new(&empty_settings, HashSet::new(), None, None)?;
        let empty = analyzer.analyze(py, empty_input)?;
        assert!(empty.expectation_outcomes.is_empty());
        assert!(empty.disabled_setting_notices.is_empty());
        Ok(())
    })
    .expect("Python analyzer projection should preserve the core result");
}

#[test]
fn python_construction_error_exposes_kind_code_and_message() {
    Python::initialize();
    Python::attach(|py| {
        let error = PyCrashgenSettingsAnalyzer::new(
            "Buffout 4".to_string(),
            analyzer_entry(py, 2).unwrap().as_any(),
        )
        .expect_err("unsupported versions must fail construction");
        let value = error.value(py);

        let kind = value
            .getattr("analyzer_kind")
            .unwrap()
            .extract::<PyAnalyzerKind>()
            .unwrap();
        assert_eq!(kind, PyAnalyzerKind::CrashgenSettings);
        assert_eq!(
            value.getattr("code").unwrap().extract::<String>().unwrap(),
            "unsupported_configuration_version"
        );
        assert_eq!(
            value
                .getattr("message")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "unsupported Crashgen Expectations version 2"
        );
    });
}
