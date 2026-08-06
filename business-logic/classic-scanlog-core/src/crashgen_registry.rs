//! Per-crashgen settings configuration registry.
//!
//! Provides a YAML-driven registry that maps crashgen names to their
//! per-crashgen settings: display section, ignore key list, and Crashgen Expectations.
//!
//! # Registry lookup
//!
//! Lookup is case-insensitive and whitespace-normalized (all whitespace stripped).
//! An unknown crashgen falls back to the `default` entry, which has an empty
//! ignore list and no Crashgen Expectations.

use std::collections::{HashMap, HashSet};

use classic_config_core::CrashgenSettingsRules;

/// Per-crashgen settings configuration entry.
///
/// Holds the display section header name, the list of settings keys to skip
/// during disabled-settings checks, and the YAML-backed Crashgen Expectations.
#[derive(Debug, Clone)]
pub struct CrashgenEntry {
    /// Bracket header used by this crashgen (e.g., `"[Compatibility]"`), for display only.
    pub display_section: String,
    /// Settings keys excluded from Disabled Setting Notice analysis.
    pub ignore_keys: HashSet<String>,
    /// Optional YAML-backed Crashgen Expectations.
    pub settings_rules: Option<CrashgenSettingsRules>,
}

impl CrashgenEntry {
    /// Creates a default entry with an empty ignore list and no Crashgen Expectations.
    ///
    /// Used as the fallback for unregistered crashgens.
    pub fn default_entry() -> Self {
        Self {
            display_section: String::new(),
            ignore_keys: HashSet::new(),
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
