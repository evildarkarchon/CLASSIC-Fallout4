//! RecordScanner - Exact Rust port of Python RecordScanner
//!
//! This module handles named record detection with exact behavioral parity
//! to the Python implementation while leveraging Rust's performance.

use pyo3::prelude::*;
use pyo3::types::PyList;
use std::collections::{HashMap, HashSet};
use rayon::prelude::*;
use aho_corasick::{AhoCorasick, AhoCorasickBuilder};
use once_cell::sync::OnceCell;

/// Record scanner for detecting and analyzing named records in crash logs
#[pyclass]
pub struct RecordScanner {
    lower_records: HashSet<String>,
    lower_ignore: HashSet<String>,
    crashgen_name: String,
    // Aho-Corasick automaton for efficient multi-pattern matching
    record_matcher: OnceCell<AhoCorasick>,
    ignore_matcher: OnceCell<AhoCorasick>,
}

#[pymethods]
impl RecordScanner {
    #[new]
    pub fn new(yamldata: &Bound<'_, PyAny>) -> PyResult<Self> {
        // Extract data from yamldata exactly as Python does
        let classic_records_list: Vec<String> = yamldata
            .getattr("classic_records_list")?
            .extract()?;

        let game_ignore_records: Vec<String> = yamldata
            .getattr("game_ignore_records")?
            .extract()?;

        let crashgen_name: String = yamldata
            .getattr("crashgen_name")?
            .extract()?;

        // Convert to lowercase sets exactly as Python does
        let lower_records: HashSet<String> = classic_records_list
            .iter()
            .map(|s| s.to_lowercase())
            .collect();

        let lower_ignore: HashSet<String> = game_ignore_records
            .iter()
            .map(|s| s.to_lowercase())
            .collect();

        Ok(Self {
            lower_records,
            lower_ignore,
            crashgen_name,
            record_matcher: OnceCell::new(),
            ignore_matcher: OnceCell::new(),
        })
    }

    /// Scan for named records and return report fragment and matches
    pub fn scan_named_records(
        &self,
        py: Python<'_>,
        segment_callstack: Vec<String>
    ) -> PyResult<(Py<PyAny>, Vec<String>)> {
        // Constants matching Python implementation
        const RSP_MARKER: &str = "[RSP+";
        const RSP_OFFSET: usize = 30;

        let records_matches = self.find_matching_records_internal(
            &segment_callstack,
            RSP_MARKER,
            RSP_OFFSET
        );

        // Generate report fragment
        let report_fragment_module = py.import("ClassicLib.ScanLog.ReportFragment")?;
        let report_fragment_class = report_fragment_module.getattr("ReportFragment")?;

        let fragment = if !records_matches.is_empty() {
            self.generate_found_records_fragment(py, &records_matches, &report_fragment_class)?
        } else {
            let lines = vec!["* COULDN'T FIND ANY NAMED RECORDS *\n\n"];
            let py_lines = PyList::new(py, lines)?;
            report_fragment_class
                .call_method1("from_lines", (py_lines,))?
                .unbind()
        };

        Ok((fragment, records_matches))
    }

    /// Extract records from segment callstack
    pub fn extract_records(&self, segment_callstack: Vec<String>) -> Vec<String> {
        const RSP_MARKER: &str = "[RSP+";
        const RSP_OFFSET: usize = 30;

        self.find_matching_records_internal(&segment_callstack, RSP_MARKER, RSP_OFFSET)
    }

    /// Main method for record scanning - matches Python RecordScanner.record_scan
    pub fn record_scan(
        &self,
        py: Python<'_>,
        segment_crashgen: Vec<String>,
        report: &Bound<'_, PyAny>
    ) -> PyResult<()> {
        // Call scan_named_records to get the fragment
        let (fragment, _matches) = self.scan_named_records(py, segment_crashgen)?;

        // Add the fragment to the report
        report.call_method1("add_fragment", (fragment,))?;

        Ok(())
    }

    /// Clear any internal caches
    pub fn clear_cache(&self) {
        // Currently no caching, but provided for API compatibility
    }
}

impl RecordScanner {
    /// Internal method to find matching records - exact Python behavior
    fn find_matching_records_internal(
        &self,
        segment_callstack: &[String],
        rsp_marker: &str,
        rsp_offset: usize
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

            // Match Python's exact logic:
            // any(item in lower_line for item in self.lower_records) and
            // all(record not in lower_line for record in self.lower_ignore)
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

    /// Generate report fragment for found records
    fn generate_found_records_fragment(
        &self,
        py: Python<'_>,
        records_matches: &[String],
        report_fragment_class: &Bound<'_, PyAny>
    ) -> PyResult<Py<PyAny>> {
        let mut lines = Vec::new();

        // Count and sort the records - matches Python's Counter(sorted(records_matches))
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

        // Add explanatory notes - exact same text as Python
        lines.extend(vec![
            "\n[Last number counts how many times each Named Record shows up in the crash log.]\n".to_string(),
            format!("These records were caught by {} and some of them might be related to this crash.\n",
                    self.crashgen_name),
            "Named records should give extra info on involved game objects, record types or mod files.\n\n".to_string(),
        ]);

        let py_lines = PyList::new(py, lines)?;
        Ok(report_fragment_class
            .call_method1("from_lines", (py_lines,))?
            .unbind())
    }
}

/// Batch process multiple callstack segments in parallel
#[pyfunction]
pub fn scan_records_batch(
    segments: Vec<Vec<String>>,
    target_records: Vec<String>,
    ignore_records: Vec<String>
) -> Vec<Vec<String>> {
    const RSP_MARKER: &str = "[RSP+";
    const RSP_OFFSET: usize = 30;

    // Convert to lowercase sets
    let lower_targets: HashSet<String> = target_records
        .iter()
        .map(|s| s.to_lowercase())
        .collect();

    let lower_ignores: HashSet<String> = ignore_records
        .iter()
        .map(|s| s.to_lowercase())
        .collect();

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
#[pyfunction]
pub fn contains_record(line: &str, target_records: Vec<String>, ignore_records: Vec<String>) -> bool {
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
