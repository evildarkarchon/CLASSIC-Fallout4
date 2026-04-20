use super::*;

fn make_buffout_entry() -> CrashgenEntry {
    CrashgenEntry {
        display_section: "[Compatibility]".to_string(),
        ignore_keys: ["F4EE", "WaitForDebugger", "Achievements"]
            .iter()
            .map(|s| s.to_string())
            .collect(),
        checks: vec![
            CheckId::Achievements,
            CheckId::MemoryManagement,
            CheckId::ArchiveLimit,
            CheckId::LooksMenu,
        ],
        settings_rules: None,
    }
}

fn make_addictol_entry() -> CrashgenEntry {
    CrashgenEntry {
        display_section: "[Patches]".to_string(),
        ignore_keys: HashSet::new(),
        checks: vec![],
        settings_rules: None,
    }
}

fn make_registry() -> CrashgenRegistry {
    let mut entries = HashMap::new();
    entries.insert("Buffout 4".to_string(), make_buffout_entry());
    entries.insert("Addictol".to_string(), make_addictol_entry());
    CrashgenRegistry::new(entries, CrashgenEntry::default_entry())
}

#[test]
fn test_known_crashgen_returns_its_entry() {
    let registry = make_registry();
    let entry = registry.lookup("Buffout 4");
    assert_eq!(entry.display_section, "[Compatibility]");
    assert!(entry.checks.contains(&CheckId::Achievements));
    assert!(entry.checks.contains(&CheckId::MemoryManagement));
    assert!(entry.checks.contains(&CheckId::ArchiveLimit));
    assert!(entry.checks.contains(&CheckId::LooksMenu));
    assert_eq!(entry.checks.len(), 4);
}

#[test]
fn test_unknown_crashgen_falls_back_to_default() {
    let registry = make_registry();
    let entry = registry.lookup("SomethingUnknown");
    assert!(entry.checks.is_empty());
    assert!(entry.ignore_keys.is_empty());
    assert!(entry.display_section.is_empty());
}

#[test]
fn test_lookup_is_case_insensitive() {
    let registry = make_registry();
    let entry_lower = registry.lookup("buffout 4");
    let entry_mixed = registry.lookup("BUFFOUT 4");
    let entry_normal = registry.lookup("Buffout 4");
    assert_eq!(entry_lower.display_section, entry_normal.display_section);
    assert_eq!(entry_mixed.display_section, entry_normal.display_section);
}

#[test]
fn test_lookup_is_whitespace_normalized() {
    let registry = make_registry();
    // Strip all internal whitespace (e.g., "buffout4" matches "Buffout 4")
    let entry = registry.lookup("buffout4");
    assert_eq!(entry.display_section, "[Compatibility]");
}

#[test]
fn test_lookup_matches_pre_normalized_keys() {
    let registry = make_registry();

    // Constructed key is normalized in `CrashgenRegistry::new`, so these
    // differently formatted lookups must all resolve identically.
    let a = registry.lookup(" Buffout  4 ");
    let b = registry.lookup("buffout4");
    let c = registry.lookup("BUFFOUT\t4");

    assert_eq!(a.display_section, "[Compatibility]");
    assert_eq!(b.display_section, a.display_section);
    assert_eq!(c.display_section, a.display_section);
}

#[test]
fn test_addictol_returns_empty_checks() {
    let registry = make_registry();
    let entry = registry.lookup("Addictol");
    assert!(entry.checks.is_empty());
    assert!(entry.ignore_keys.is_empty());
    assert_eq!(entry.display_section, "[Patches]");
}

#[test]
fn test_check_id_from_str() {
    assert_eq!(CheckId::parse("achievements"), Some(CheckId::Achievements));
    assert_eq!(
        CheckId::parse("memory_management"),
        Some(CheckId::MemoryManagement)
    );
    assert_eq!(
        CheckId::parse("MemoryManagement"),
        Some(CheckId::MemoryManagement)
    );
    assert_eq!(CheckId::parse("archive_limit"), Some(CheckId::ArchiveLimit));
    assert_eq!(CheckId::parse("looksmenu"), Some(CheckId::LooksMenu));
    assert_eq!(CheckId::parse("looks_menu"), Some(CheckId::LooksMenu));
    assert_eq!(CheckId::parse("unknown_check"), None);
}
