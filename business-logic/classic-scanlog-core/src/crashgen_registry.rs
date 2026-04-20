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
#[path = "crashgen_registry_tests.rs"]
mod tests;
