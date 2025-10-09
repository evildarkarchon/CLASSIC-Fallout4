//! FormIDAnalyzerCore - Pure Rust FormID analysis (NO PyO3)
//!
//! This module provides FormID extraction, validation, and database lookup
//! functionality using pure Rust data structures.

use crate::error::Result;
use classic_database_core::DatabasePool;
use once_cell::sync::Lazy;
use regex::Regex;
use std::collections::HashMap;
use rayon::prelude::*;
use std::sync::Arc;
use linked_hash_map::LinkedHashMap;

/// Precompiled FormID pattern - exact match to Python's pattern
/// Pattern: r"^\s*Form ID:\s*0x([0-9A-F]{8})" with case-insensitive flag
static FORMID_PATTERN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?i)^\s*Form ID:\s*0x([0-9A-F]{8})").unwrap()
});

/// Core FormID analyzer - pure Rust implementation (NO PyO3)
pub struct FormIDAnalyzerCore {
    show_formid_values: bool,
    crashgen_name: String,
    // Database pool for FormID lookups (from classic-database-core)
    db_pool: Option<Arc<DatabasePool>>,
    // Important mods lists for priority matching
    important_mods: Vec<String>,
    mods_single: Vec<String>,
    mods_double: Vec<String>,
}

impl FormIDAnalyzerCore {
    /// Create a new FormID analyzer with pure Rust data structures
    pub fn new(
        db_pool: Option<Arc<DatabasePool>>,
        show_formid_values: bool,
        crashgen_name: String,
        important_mods: Vec<String>,
        mods_single: Vec<String>,
        mods_double: Vec<String>,
    ) -> Result<Self> {
        Ok(Self {
            show_formid_values,
            crashgen_name,
            db_pool,
            important_mods,
            mods_single,
            mods_double,
        })
    }

    /// Extract FormIDs from a segment of callstack - exact match to Python behavior
    pub fn extract_formids(&self, segment_callstack: Vec<String>) -> Vec<String> {
        let mut formids_matches = Vec::new();

        if segment_callstack.is_empty() {
            return formids_matches;
        }

        // Process each line exactly as Python does
        for line in segment_callstack {
            if let Some(captures) = FORMID_PATTERN.captures(&line) {
                if let Some(formid_match) = captures.get(1) {
                    let formid_id = formid_match.as_str().to_uppercase();

                    // Skip if it starts with FF (plugin limit)
                    // Note: NULL FormIDs (00000000) are intentionally kept as they indicate errors
                    // This matches Python's behavior exactly
                    if !formid_id.starts_with("FF") {
                        formids_matches.push(format!("Form ID: {}", formid_id));
                    }
                }
            }
        }

        formids_matches
    }

    /// Perform FormID matching with plugins - returns formatted report lines
    pub async fn formid_match(
        &self,
        formids_matches: Vec<String>,
        crashlog_plugins: &HashMap<String, String>
    ) -> Result<Vec<String>> {
        if formids_matches.is_empty() {
            return Ok(vec!["* COULDN'T FIND ANY FORM ID SUSPECTS *\n\n".to_string()]);
        }

        let mut lines = Vec::new();

        // Count occurrences and sort - matching Python's Counter(sorted(formids_matches))
        let mut sorted_formids = formids_matches.clone();
        sorted_formids.sort();

        // Use LinkedHashMap to preserve insertion order like Python's dict
        let mut formids_found: LinkedHashMap<String, usize> = LinkedHashMap::new();
        for formid in sorted_formids {
            *formids_found.entry(formid).or_insert(0) += 1;
        }

        // Process each FormID exactly as Python does
        for (formid_full, count) in formids_found.iter() {
            let parts: Vec<&str> = formid_full.splitn(2, ": ").collect();
            if parts.len() < 2 {
                continue;
            }

            let formid_value = parts[1];
            if formid_value.len() < 2 {
                continue;
            }
            let formid_prefix = &formid_value[..2];
            let formid_suffix = &formid_value[2..];

            // Find matching plugin
            for (plugin, plugin_id) in crashlog_plugins.iter() {
                if plugin_id == formid_prefix {
                    // Perform database lookup if available
                    if self.show_formid_values {
                        if let Some(ref pool) = self.db_pool {
                            if let Ok(Some(description)) = pool.get_entry(formid_suffix, plugin, None).await {
                                lines.push(format!("- {} | [{}] | {} | {}\n", formid_full, plugin, description, count));
                            } else {
                                lines.push(format!("- {} | [{}] | {}\n", formid_full, plugin, count));
                            }
                        } else {
                            lines.push(format!("- {} | [{}] | {}\n", formid_full, plugin, count));
                        }
                    } else {
                        lines.push(format!("- {} | [{}] | {}\n", formid_full, plugin, count));
                    }
                    break;
                }
            }
        }

        // Add footer information - exact same text as Python
        lines.extend(vec![
            "\n[Last number counts how many times each Form ID shows up in the crash log.]\n".to_string(),
            format!("These Form IDs were caught by {} and some of them might be related to this crash.\n",
                    self.crashgen_name),
            "You can try searching any listed Form IDs in xEdit and see if they lead to relevant records.\n\n".to_string(),
        ]);

        Ok(lines)
    }

    /// Lookup FormID value from database
    pub async fn lookup_formid_value(&self, formid: &str, plugin: &str) -> Option<String> {
        if let Some(ref pool) = self.db_pool {
            pool.get_entry(formid, plugin, None).await.ok().flatten()
        } else {
            None
        }
    }
}

/// Parallel FormID extraction for bulk processing
pub fn extract_formids_batch(callstack_segments: Vec<Vec<String>>) -> Vec<Vec<String>> {
    // Use rayon for parallel processing
    callstack_segments
        .par_iter()
        .map(|segment| {
            let mut formids = Vec::new();

            for line in segment {
                if let Some(captures) = FORMID_PATTERN.captures(line) {
                    if let Some(formid_match) = captures.get(1) {
                        let formid_id = formid_match.as_str().to_uppercase();

                        // Skip FF-prefixed FormIDs (plugin limit)
                        // Keep 00000000 (NULL) FormIDs as they indicate errors
                        if !formid_id.starts_with("FF") {
                            formids.push(format!("Form ID: {}", formid_id));
                        }
                    }
                }
            }

            formids
        })
        .collect()
}

/// Validate FormID format without extraction
pub fn is_valid_formid(formid: &str) -> bool {
    // Remove potential "Form ID: " prefix and "0x" prefix
    let cleaned = formid
        .trim()
        .trim_start_matches("Form ID:")
        .trim()
        .trim_start_matches("0x")
        .trim_start_matches("0X");

    // Check if it's a valid 8-character hex string
    cleaned.len() <= 8 && cleaned.chars().all(|c| c.is_ascii_hexdigit())
}

/// Batch validate FormIDs
pub fn validate_formids_batch(formids: Vec<String>) -> Vec<bool> {
    formids
        .par_iter()
        .map(|formid| is_valid_formid(formid))
        .collect()
}
