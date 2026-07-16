use super::*;
use pyo3::types::PyDict;
use std::collections::HashSet;

#[test]
fn crashgen_entry_adapter_ignores_deprecated_checks_and_collects_ignore_keys() {
    Python::attach(|py| -> PyResult<()> {
        let entry = PyDict::new(py);
        entry.set_item("display_section", "[Memory]")?;
        entry.set_item("ignore_keys", vec!["MemoryManager", "HavokMemorySystem"])?;
        entry.set_item(
            "checks",
            vec!["memory_management", "unknown_check", "looksmenu"],
        )?;

        let parsed = crashgen_entry_from_py(entry.as_any());

        assert_eq!(parsed.display_section, "[Memory]");
        assert_eq!(
            parsed.ignore_keys,
            HashSet::from(["MemoryManager".to_string(), "HavokMemorySystem".to_string(),])
        );
        assert!(parsed.settings_rules.is_none());
        Ok(())
    })
    .expect("entry conversion should succeed");
}
