use super::*;
use pyo3::types::{PyDict, PyList};

#[test]
fn new_rejects_malformed_error_rule_payloads() {
    Python::attach(|py| -> PyResult<()> {
        let error_rule = PyDict::new(py);
        error_rule.set_item("id", "rule-id")?;
        error_rule.set_item("name", "Missing matcher")?;
        error_rule.set_item("severity", 1)?;

        let error_rules = PyList::empty(py);
        error_rules.append(&error_rule)?;
        let stack_rules = PyList::empty(py);

        let err = match PySuspectScanner::new(error_rules.as_any(), stack_rules.as_any()) {
            Ok(_) => panic!("missing main_error_contains_any should fail"),
            Err(err) => err,
        };

        assert!(err.to_string().contains("main_error_contains_any"));
        Ok(())
    })
    .expect("malformed error rules should produce a Python error");
}

#[test]
fn new_rejects_malformed_stack_rule_payloads() {
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

        let error_rules = PyList::empty(py);
        let stack_rules = PyList::empty(py);
        stack_rules.append(&stack_rule)?;

        let err = match PySuspectScanner::new(error_rules.as_any(), stack_rules.as_any()) {
            Ok(_) => panic!("missing nested count field should fail"),
            Err(err) => err,
        };

        assert!(err.to_string().contains("count"));
        Ok(())
    })
    .expect("malformed stack rules should produce a Python error");
}
