use super::*;
use classic_config_core::CoreModExclude;
use pyo3::types::{PyDict, PyList, PyModule};

#[test]
fn from_yamldata_preserves_core_mod_exclusion_metadata() {
    Python::attach(|py| -> PyResult<()> {
        let entry = PyDict::new(py);
        entry.set_item("detect", "prp.esp")?;
        entry.set_item("name", "PRP")?;
        entry.set_item("description", "Install PRP when London is not present")?;
        entry.set_item("gpu_mismatch_warning", "PRP is tuned for NVIDIA users")?;

        let exclude_when = PyDict::new(py);
        exclude_when.set_item("plugin_any", vec!["LondonWorldspace.esm"])?;
        entry.set_item("exclude_when", exclude_when)?;

        let game_mods_core = PyList::empty(py);
        game_mods_core.append(entry)?;

        let kwargs = PyDict::new(py);
        kwargs.set_item("game_mods_core", game_mods_core)?;

        let types = PyModule::import(py, "types")?;
        let yamldata = types.getattr("SimpleNamespace")?.call((), Some(&kwargs))?;

        let config = PyAnalysisConfig::from_yamldata(
            &yamldata,
            "Fallout4".to_string(),
            "Original".to_string(),
            false,
            false,
            false,
            Vec::new(),
        )?;

        assert_eq!(config.inner.mods_core.len(), 1);
        let entry = &config.inner.mods_core[0];
        assert_eq!(
            entry.gpu_mismatch_warning.as_deref(),
            Some("PRP is tuned for NVIDIA users")
        );
        assert_eq!(
            entry.exclude_when,
            Some(CoreModExclude::PluginAny(vec![
                "LondonWorldspace.esm".to_string(),
            ]))
        );

        Ok(())
    })
    .expect("Python core-mod metadata round-trip should succeed");
}

#[test]
fn suspect_error_rules_setter_rejects_malformed_rule_payloads() {
    Python::attach(|py| -> PyResult<()> {
        let config = Py::new(
            py,
            PyAnalysisConfig::new("Fallout4".to_string(), "Original".to_string()),
        )?;

        let error_rule = PyDict::new(py);
        error_rule.set_item("id", "rule-id")?;
        error_rule.set_item("name", "Missing matcher")?;
        error_rule.set_item("severity", 1)?;

        let error_rules = PyList::empty(py);
        error_rules.append(&error_rule)?;

        let err = match config.bind(py).setattr("suspect_error_rules", &error_rules) {
            Ok(()) => panic!("missing main_error_contains_any should fail"),
            Err(err) => err,
        };

        assert!(err.to_string().contains("main_error_contains_any"));
        Ok(())
    })
    .expect("malformed error rules should produce a Python error");
}

#[test]
fn suspect_stack_rules_setter_rejects_malformed_rule_payloads() {
    Python::attach(|py| -> PyResult<()> {
        let config = Py::new(
            py,
            PyAnalysisConfig::new("Fallout4".to_string(), "Original".to_string()),
        )?;

        let count_rule = PyDict::new(py);
        count_rule.set_item("substring", "foo")?;

        let count_rules = PyList::empty(py);
        count_rules.append(&count_rule)?;

        let stack_rule = PyDict::new(py);
        stack_rule.set_item("id", "stack-rule")?;
        stack_rule.set_item("name", "Missing count")?;
        stack_rule.set_item("severity", 2)?;
        stack_rule.set_item("main_error_required_any", vec!["foo"])?;
        stack_rule.set_item("main_error_optional_any", Vec::<String>::new())?;
        stack_rule.set_item("stack_contains_any", vec!["foo"])?;
        stack_rule.set_item("exclude_if_stack_contains_any", Vec::<String>::new())?;
        stack_rule.set_item("stack_contains_at_least", count_rules)?;

        let stack_rules = PyList::empty(py);
        stack_rules.append(&stack_rule)?;

        let err = match config.bind(py).setattr("suspect_stack_rules", &stack_rules) {
            Ok(()) => panic!("missing nested count field should fail"),
            Err(err) => err,
        };

        assert!(err.to_string().contains("count"));
        Ok(())
    })
    .expect("malformed stack rules should produce a Python error");
}

#[test]
fn from_yamldata_rejects_malformed_error_rule_payloads() {
    Python::attach(|py| -> PyResult<()> {
        let error_rule = PyDict::new(py);
        error_rule.set_item("id", "rule-id")?;
        error_rule.set_item("name", "Missing matcher")?;
        error_rule.set_item("severity", 1)?;

        let error_rules = PyList::empty(py);
        error_rules.append(&error_rule)?;

        let kwargs = PyDict::new(py);
        kwargs.set_item("suspect_error_rules", error_rules)?;

        let types = PyModule::import(py, "types")?;
        let yamldata = types.getattr("SimpleNamespace")?.call((), Some(&kwargs))?;

        let err = match PyAnalysisConfig::from_yamldata(
            &yamldata,
            "Fallout4".to_string(),
            "Original".to_string(),
            false,
            false,
            false,
            Vec::new(),
        ) {
            Ok(_) => panic!("missing main_error_contains_any should fail"),
            Err(err) => err,
        };

        assert!(err.to_string().contains("main_error_contains_any"));
        Ok(())
    })
    .expect("malformed error rules should produce a Python error");
}

#[test]
fn from_yamldata_rejects_malformed_stack_rule_payloads() {
    Python::attach(|py| -> PyResult<()> {
        let count_rule = PyDict::new(py);
        count_rule.set_item("substring", "foo")?;

        let count_rules = PyList::empty(py);
        count_rules.append(&count_rule)?;

        let stack_rule = PyDict::new(py);
        stack_rule.set_item("id", "stack-rule")?;
        stack_rule.set_item("name", "Missing count")?;
        stack_rule.set_item("severity", 2)?;
        stack_rule.set_item("main_error_required_any", vec!["foo"])?;
        stack_rule.set_item("main_error_optional_any", Vec::<String>::new())?;
        stack_rule.set_item("stack_contains_any", vec!["foo"])?;
        stack_rule.set_item("exclude_if_stack_contains_any", Vec::<String>::new())?;
        stack_rule.set_item("stack_contains_at_least", count_rules)?;

        let stack_rules = PyList::empty(py);
        stack_rules.append(&stack_rule)?;

        let kwargs = PyDict::new(py);
        kwargs.set_item("suspect_stack_rules", stack_rules)?;

        let types = PyModule::import(py, "types")?;
        let yamldata = types.getattr("SimpleNamespace")?.call((), Some(&kwargs))?;

        let err = match PyAnalysisConfig::from_yamldata(
            &yamldata,
            "Fallout4".to_string(),
            "Original".to_string(),
            false,
            false,
            false,
            Vec::new(),
        ) {
            Ok(_) => panic!("missing nested count field should fail"),
            Err(err) => err,
        };

        assert!(err.to_string().contains("count"));
        Ok(())
    })
    .expect("malformed stack rules should produce a Python error");
}
