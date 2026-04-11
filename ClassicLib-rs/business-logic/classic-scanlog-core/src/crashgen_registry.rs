//! Per-crashgen settings configuration registry.
//!
//! Provides a YAML-driven registry that maps crashgen names to their
//! per-crashgen settings: display section, ignore key list, and named check set.
//!
//! # Registry lookup
//!
//! Lookup is case-insensitive and whitespace-normalized (all whitespace stripped).
//! An unknown crashgen falls back to the `default` entry, which has an empty
//! ignore list and no named checks.

use std::collections::{HashMap, HashSet};

use classic_config_core::CrashgenSettingsRules;

/// Named check identifiers for crash generator settings validation.
///
/// Each variant corresponds to one of the four named settings checks that
/// are conditionally run based on the crashgen registry entry.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum CheckId {
    /// Achievements mod compatibility check
    Achievements,
    /// Memory manager / X-Cell / ScrapHeap compatibility check
    MemoryManagement,
    /// ArchiveLimit stability check
    ArchiveLimit,
    /// LooksMenu (F4EE) compatibility check
    LooksMenu,
}

impl CheckId {
    /// Parse a check identifier string (case-insensitive, underscore/space agnostic).
    ///
    /// Returns `None` for unrecognized names.
    pub fn parse(s: &str) -> Option<Self> {
        let normalized: String = s.chars().filter(|c| *c != '_' && *c != ' ').collect();
        match normalized.to_lowercase().as_str() {
            "achievements" => Some(Self::Achievements),
            "memorymanagement" => Some(Self::MemoryManagement),
            "archivelimit" => Some(Self::ArchiveLimit),
            "looksmenu" => Some(Self::LooksMenu),
            _ => None,
        }
    }
}

/// Per-crashgen settings configuration entry.
///
/// Holds the display section header name, the list of settings keys to skip
/// during disabled-settings checks, and the set of named checks to run.
#[derive(Debug, Clone)]
pub struct CrashgenEntry {
    /// Bracket header used by this crashgen (e.g., `"[Compatibility]"`), for display only.
    pub display_section: String,
    /// Settings keys to skip in `check_disabled_settings()`.
    pub ignore_keys: HashSet<String>,
    /// Named checks to run for this crashgen.
    pub checks: Vec<CheckId>,
    /// Optional full settings rules block.
    pub settings_rules: Option<CrashgenSettingsRules>,
}

impl CrashgenEntry {
    /// Creates a default entry with an empty ignore list and no named checks.
    ///
    /// Used as the fallback for unregistered crashgens.
    pub fn default_entry() -> Self {
        Self {
            display_section: String::new(),
            ignore_keys: HashSet::new(),
            checks: Vec::new(),
            settings_rules: None,
        }
    }
}

/// Registry of per-crashgen settings configurations.
///
/// Loaded from YAML at startup. Provides `lookup` to resolve a crashgen name
/// to its configuration entry. Name matching is case-insensitive and
/// whitespace-normalized.
#[derive(Debug, Clone)]
pub struct CrashgenRegistry {
    entries: HashMap<String, CrashgenEntry>,
    default: CrashgenEntry,
}

impl CrashgenRegistry {
    /// Creates a registry from a map of crashgen name → entry.
    ///
    /// Input keys are normalized (whitespace-stripped, lowercased) at construction
    /// time so lookups are O(1) `HashMap::get` operations.
    ///
    /// The `default` entry is used for crashgens not present in `entries`.
    pub fn new(entries: HashMap<String, CrashgenEntry>, default: CrashgenEntry) -> Self {
        let entries = entries
            .into_iter()
            .map(|(k, v)| (Self::normalize(&k), v))
            .collect();
        Self { entries, default }
    }

    /// Looks up the registry entry for the given crashgen name.
    ///
    /// Normalizes the query by stripping all whitespace and lowercasing.
    /// Returns the `default` entry if no match is found.
    pub fn lookup(&self, name: &str) -> &CrashgenEntry {
        let normalized = Self::normalize(name);
        self.entries.get(&normalized).unwrap_or(&self.default)
    }

    /// Normalize a crashgen name for comparison: strip all whitespace, lowercase.
    fn normalize(s: &str) -> String {
        s.chars()
            .filter(|c| !c.is_whitespace())
            .collect::<String>()
            .to_lowercase()
    }

    /// Returns the default (fallback) entry.
    pub fn default_entry(&self) -> &CrashgenEntry {
        &self.default
    }
}

impl Default for CrashgenRegistry {
    fn default() -> Self {
        Self {
            entries: HashMap::new(),
            default: CrashgenEntry::default_entry(),
        }
    }
}

#[cfg(test)]
mod tests {
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
}
