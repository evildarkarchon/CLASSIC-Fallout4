use super::*;
use pyo3::types::PyDict;
use std::collections::HashSet;

#[test]
fn crashgen_registry_adapter_preserves_raw_fields_and_skips_non_dict_entries() {
    Python::attach(|py| -> PyResult<()> {
        let entry = PyDict::new(py);
        entry.set_item("display_section", "[Compatibility]")?;
        entry.set_item("ignore_keys", vec!["bInvalidateOlderFiles", "ArchiveLimit"])?;
        entry.set_item(
            "checks",
            vec!["achievements", "unknown_check", "archive_limit"],
        )?;
        entry.set_item("settings_rules_version", 2_u32)?;

        let registry = PyDict::new(py);
        registry.set_item("Buffout 4", entry)?;
        registry.set_item("NotADict", "skip me")?;

        let parsed = parse_crashgen_registry_from_py(registry.as_any());

        assert_eq!(parsed.len(), 1);
        let buffout = parsed.get("Buffout 4").expect("entry should be preserved");
        assert_eq!(buffout.display_section, "[Compatibility]");
        assert_eq!(
            buffout.ignore_keys,
            vec![
                "bInvalidateOlderFiles".to_string(),
                "ArchiveLimit".to_string()
            ]
        );
        assert_eq!(
            buffout.checks,
            vec![
                "achievements".to_string(),
                "unknown_check".to_string(),
                "archive_limit".to_string(),
            ]
        );
        assert_eq!(buffout.settings_rules_version, Some(2));
        assert!(buffout.settings_rules.is_none());
        Ok(())
    })
    .expect("registry conversion should succeed");
}

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
