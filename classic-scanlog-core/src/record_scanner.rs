//! RecordScanner - Pure Rust record detection and analysis
//!
//! This module handles named record detection with high performance.
//! No PyO3 dependencies - accepts plain data structures.

use aho_corasick::{AhoCorasick, AhoCorasickBuilder};
use once_cell::sync::OnceCell;
use rayon::prelude::*;
use std::collections::{HashMap, HashSet};

/// Record scanner for detecting and analyzing named records in crash logs
pub struct RecordScanner {
    lower_records: HashSet<String>,
    lower_ignore: HashSet<String>,
    crashgen_name: String,
    // Aho-Corasick automaton for efficient multi-pattern matching
    record_matcher: OnceCell<AhoCorasick>,
    ignore_matcher: OnceCell<AhoCorasick>,
}

impl RecordScanner {
    /// Create new RecordScanner with plain data structures
    pub fn new(
        classic_records_list: Vec<String>,
        game_ignore_records: Vec<String>,
        crashgen_name: String,
    ) -> Self {
        // Convert to lowercase sets
        let lower_records: HashSet<String> = classic_records_list
            .iter()
            .map(|s| s.to_lowercase())
            .collect();

        let lower_ignore: HashSet<String> = game_ignore_records
            .iter()
            .map(|s| s.to_lowercase())
            .collect();

        Self {
            lower_records,
            lower_ignore,
            crashgen_name,
            record_matcher: OnceCell::new(),
            ignore_matcher: OnceCell::new(),
        }
    }

    /// Scan for named records and return matches with report lines
    pub fn scan_named_records(&self, segment_callstack: &[String]) -> (Vec<String>, Vec<String>) {
        const RSP_MARKER: &str = "[RSP+";
        const RSP_OFFSET: usize = 30;

        let records_matches =
            self.find_matching_records_internal(segment_callstack, RSP_MARKER, RSP_OFFSET);

        let report_lines = if !records_matches.is_empty() {
            self.generate_found_records_lines(&records_matches)
        } else {
            vec!["* COULDN'T FIND ANY NAMED RECORDS *\n\n".to_string()]
        };

        (report_lines, records_matches)
    }

    /// Extract records from segment callstack
    pub fn extract_records(&self, segment_callstack: &[String]) -> Vec<String> {
        const RSP_MARKER: &str = "[RSP+";
        const RSP_OFFSET: usize = 30;

        self.find_matching_records_internal(segment_callstack, RSP_MARKER, RSP_OFFSET)
    }

    /// Clear any internal caches
    pub fn clear_cache(&self) {
        // Currently no caching beyond OnceCell, but provided for API compatibility
    }

    /// Internal method to find matching records
    fn find_matching_records_internal(
        &self,
        segment_callstack: &[String],
        rsp_marker: &str,
        rsp_offset: usize,
    ) -> Vec<String> {
        let mut records_matches = Vec::new();

        // Build Aho-Corasick automaton for efficient multi-pattern matching if not already built
        let record_matcher = self.record_matcher.get_or_init(|| {
            let patterns: Vec<String> = self.lower_records.iter().cloned().collect();
            AhoCorasickBuilder::new()
                .ascii_case_insensitive(true)
                .build(&patterns)
                .unwrap()
        });

        let ignore_matcher = self.ignore_matcher.get_or_init(|| {
            let patterns: Vec<String> = self.lower_ignore.iter().cloned().collect();
            AhoCorasickBuilder::new()
                .ascii_case_insensitive(true)
                .build(&patterns)
                .unwrap()
        });

        for line in segment_callstack {
            let lower_line = line.to_lowercase();

            // Check if line contains any target record
            let has_target = record_matcher.is_match(&lower_line);

            // Check if line contains any ignored terms
            let has_ignored = ignore_matcher.is_match(&lower_line);

            if has_target && !has_ignored {
                // Extract the relevant part of the line based on format
                if line.contains(rsp_marker) {
                    if line.len() > rsp_offset {
                        records_matches.push(line[rsp_offset..].trim().to_string());
                    }
                } else {
                    records_matches.push(line.trim().to_string());
                }
            }
        }

        records_matches
    }

    /// Generate report lines for found records
    fn generate_found_records_lines(&self, records_matches: &[String]) -> Vec<String> {
        let mut lines = Vec::new();

        // Count and sort the records
        let mut sorted_records = records_matches.to_vec();
        sorted_records.sort();

        let mut records_found: HashMap<String, usize> = HashMap::new();
        for record in sorted_records {
            *records_found.entry(record).or_insert(0) += 1;
        }

        // Sort by key for consistent output
        let mut sorted_entries: Vec<_> = records_found.iter().collect();
        sorted_entries.sort_by_key(|(k, _)| k.as_str());

        // Add each record with its count
        for (record, count) in sorted_entries {
            lines.push(format!("- {} | {}\n", record, count));
        }

        // Add explanatory notes
        lines.extend(vec![
            "\n[Last number counts how many times each Named Record shows up in the crash log.]\n".to_string(),
            format!("These records were caught by {} and some of them might be related to this crash.\n",
                    self.crashgen_name),
            "Named records should give extra info on involved game objects, record types or mod files.\n\n".to_string(),
        ]);

        lines
    }
}

/// Batch process multiple callstack segments in parallel
pub fn scan_records_batch(
    segments: Vec<Vec<String>>,
    target_records: Vec<String>,
    ignore_records: Vec<String>,
) -> Vec<Vec<String>> {
    const RSP_MARKER: &str = "[RSP+";
    const RSP_OFFSET: usize = 30;

    // Convert to lowercase sets
    let lower_targets: HashSet<String> = target_records.iter().map(|s| s.to_lowercase()).collect();

    let lower_ignores: HashSet<String> = ignore_records.iter().map(|s| s.to_lowercase()).collect();

    // Build Aho-Corasick automatons for efficiency
    let target_patterns: Vec<_> = lower_targets.iter().cloned().collect();
    let target_matcher = AhoCorasickBuilder::new()
        .ascii_case_insensitive(true)
        .build(&target_patterns)
        .unwrap();

    let ignore_patterns: Vec<_> = lower_ignores.iter().cloned().collect();
    let ignore_matcher = AhoCorasickBuilder::new()
        .ascii_case_insensitive(true)
        .build(&ignore_patterns)
        .unwrap();

    // Process segments in parallel
    segments
        .par_iter()
        .map(|segment| {
            let mut matches = Vec::new();

            for line in segment {
                let lower_line = line.to_lowercase();

                // Check patterns
                if target_matcher.is_match(&lower_line) && !ignore_matcher.is_match(&lower_line) {
                    if line.contains(RSP_MARKER) {
                        if line.len() > RSP_OFFSET {
                            matches.push(line[RSP_OFFSET..].trim().to_string());
                        }
                    } else {
                        matches.push(line.trim().to_string());
                    }
                }
            }

            matches
        })
        .collect()
}

/// Check if a line contains any of the target records
pub fn contains_record(line: &str, target_records: &[String], ignore_records: &[String]) -> bool {
    let lower_line = line.to_lowercase();

    // Check if any target record is present
    let has_target = target_records
        .iter()
        .any(|record| lower_line.contains(&record.to_lowercase()));

    // Check if any ignore record is present
    let has_ignored = ignore_records
        .iter()
        .any(|record| lower_line.contains(&record.to_lowercase()));

    has_target && !has_ignored
}
