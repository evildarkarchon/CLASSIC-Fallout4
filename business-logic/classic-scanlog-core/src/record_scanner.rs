//! RecordScanner - Pure Rust record detection and analysis
//!
//! This module handles named record detection with high performance.
//! No PyO3 dependencies - accepts plain data structures.

use crate::error::{Result as ScanLogResult, ScanLogError};
use aho_corasick::{AhoCorasick, AhoCorasickBuilder, BuildError};
use rayon::prelude::*;
use std::collections::HashSet;
use std::sync::OnceLock;

type MatcherBuildResult = std::result::Result<AhoCorasick, BuildError>;

/// Record scanner for detecting and analyzing named records in crash logs
pub struct RecordScanner {
    lower_records: HashSet<String>,
    lower_ignore: HashSet<String>,
    // Aho-Corasick automatons for efficient multi-pattern matching.
    // Build failures are cached too so pathological config does not retry work
    // or panic on every scan.
    record_matcher: OnceLock<MatcherBuildResult>,
    ignore_matcher: OnceLock<MatcherBuildResult>,
}

impl RecordScanner {
    /// Creates a new record scanner with target and ignore lists for named record detection.
    ///
    /// This constructor initializes the scanner with lists of target record names to find and
    /// ignore terms to filter out. All inputs are converted to lowercase for case-insensitive
    /// matching. The Aho-Corasick automatons are built lazily on first use for performance.
    ///
    /// # Arguments
    ///
    /// * `classic_records_list` - List of target record names to detect (e.g., "ActorBase", "Weapon")
    /// * `game_ignore_records` - List of terms that should exclude a line from matching
    ///
    /// # Returns
    ///
    /// A new `RecordScanner` instance ready for named record detection.
    ///
    /// # Performance
    ///
    /// - Aho-Corasick automatons built lazily (`OnceLock`)
    /// - Multi-pattern matching: O(n) scan regardless of pattern count
    /// - Typical: 5-10ms for 10,000 lines with 200 target records
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::RecordScanner;
    ///
    /// let scanner = RecordScanner::new(
    ///     vec!["ActorBase".to_string(), "Weapon".to_string()],
    ///     vec!["System".to_string()],
    /// );
    /// ```
    pub fn new(classic_records_list: Vec<String>, game_ignore_records: Vec<String>) -> Self {
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
            record_matcher: OnceLock::new(),
            ignore_matcher: OnceLock::new(),
        }
    }

    /// Extracts named records from callstack without generating a report.
    ///
    /// This utility returns raw matched record strings without formatting, grouping, or report
    /// prose. Use `NamedRecordFindingAnalyzer` when distinct records and counts are required.
    ///
    /// # Arguments
    ///
    /// * `segment_callstack` - Callstack lines to search
    ///
    /// # Returns
    ///
    /// Vector of matched record strings extracted from the callstack.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::RecordScanner;
    ///
    /// let scanner = RecordScanner::new(vec!["Weapon".to_string()], vec![]);
    ///
    /// let callstack = vec!["[RSP+50] Weapon_SuperSledge".to_string()];
    /// let records = scanner.extract_records(&callstack);
    /// ```
    pub fn extract_records(&self, segment_callstack: &[String]) -> Vec<String> {
        self.try_extract_records(segment_callstack)
            .unwrap_or_default()
    }

    /// Fallible variant of [`Self::extract_records`].
    pub fn try_extract_records(&self, segment_callstack: &[String]) -> ScanLogResult<Vec<String>> {
        const RSP_MARKER: &str = "[RSP+";
        const RSP_OFFSET: usize = 30;
        let segment_callstack_lower: Vec<String> = segment_callstack
            .iter()
            .map(|line| line.to_lowercase())
            .collect();

        self.try_find_matching_records_internal(
            segment_callstack,
            &segment_callstack_lower,
            RSP_MARKER,
            RSP_OFFSET,
        )
    }

    /// Clears internal caches (currently a no-op for API compatibility).
    ///
    /// This method is provided for API consistency with other scanners that may have caching.
    /// Currently, `RecordScanner` uses `OnceLock` for Aho-Corasick automatons which cannot
    /// be cleared after initialization, so this is a no-op. Future versions may add clearable
    /// caches if needed.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::RecordScanner;
    ///
    /// let scanner = RecordScanner::new(vec![], vec![]);
    /// scanner.clear_cache();  // No-op currently
    /// ```
    pub fn clear_cache(&self) {
        // Currently no caching beyond OnceLock, but provided for API compatibility
    }

    fn build_matcher(patterns: &HashSet<String>) -> MatcherBuildResult {
        let patterns: Vec<String> = patterns.iter().cloned().collect();
        AhoCorasickBuilder::new()
            .ascii_case_insensitive(true)
            .build(&patterns)
    }

    fn matcher_from_lock<'a>(
        lock: &'a OnceLock<MatcherBuildResult>,
        patterns: &HashSet<String>,
    ) -> ScanLogResult<&'a AhoCorasick> {
        lock.get_or_init(|| Self::build_matcher(patterns))
            .as_ref()
            .map_err(|err| ScanLogError::PatternError(err.clone()))
    }

    fn record_matcher(&self) -> ScanLogResult<&AhoCorasick> {
        Self::matcher_from_lock(&self.record_matcher, &self.lower_records)
    }

    fn ignore_matcher(&self) -> ScanLogResult<&AhoCorasick> {
        Self::matcher_from_lock(&self.ignore_matcher, &self.lower_ignore)
    }

    /// Internal method to find matching records
    fn try_find_matching_records_internal(
        &self,
        segment_callstack: &[String],
        segment_callstack_lower: &[String],
        rsp_marker: &str,
        rsp_offset: usize,
    ) -> ScanLogResult<Vec<String>> {
        if segment_callstack.len() != segment_callstack_lower.len() {
            return Err(ScanLogError::InvalidInput(
                "lowercased callstack slice should stay aligned with the original callstack"
                    .to_string(),
            ));
        }

        let mut records_matches = Vec::new();

        // Build Aho-Corasick automatons for efficient multi-pattern matching if not already built.
        let record_matcher = self.record_matcher()?;
        let ignore_matcher = self.ignore_matcher()?;

        for (line, lower_line) in segment_callstack.iter().zip(segment_callstack_lower) {
            // Check if line contains any target record
            let has_target = record_matcher.is_match(lower_line.as_str());

            // Check if line contains any ignored terms
            let has_ignored = ignore_matcher.is_match(lower_line.as_str());

            if has_target
                && !has_ignored
                && let Some(record) = Self::extract_record_line(line, rsp_marker, rsp_offset)
            {
                records_matches.push(record);
            }
        }

        Ok(records_matches)
    }

    pub(crate) fn extract_record_line(
        line: &str,
        rsp_marker: &str,
        rsp_offset: usize,
    ) -> Option<String> {
        if line.contains(rsp_marker) {
            if line.len() > rsp_offset {
                return line
                    .get(rsp_offset..)
                    .map(|record| record.trim().to_string());
            }
            None
        } else {
            Some(line.trim().to_string())
        }
    }
}

/// Scans multiple callstack segments for named records in parallel using Rayon.
///
/// This function processes multiple crash log callstack segments concurrently, extracting
/// named records from each segment independently. It builds Aho-Corasick automatons once
/// and reuses them across all segments for efficiency. Uses Rayon's parallel iterators for
/// improved performance on multi-core systems.
///
/// # Arguments
///
/// * `segments` - Vector of callstack segments, where each segment is a vector of lines
/// * `target_records` - List of record names to detect
/// * `ignore_records` - List of terms that should exclude a line from matching
///
/// # Returns
///
/// A vector of record vectors, one per input segment, in the same order. Each inner vector
/// contains the matched record strings for that segment.
///
/// # Performance
///
/// - Uses Rayon for parallel processing across segments
/// - Aho-Corasick automatons built once and reused
/// - Near-linear speedup with CPU core count
/// - Typical: 20-40ms for 50 segments on 8-core CPU
/// - 30-50x faster than sequential Python processing
///
/// # Example
///
/// ```rust
/// use classic_scanlog_core::record_scanner::scan_records_batch;
///
/// let segments = vec![
///     vec!["[RSP+50] ActorBase_Player".to_string()],
///     vec!["[RSP+50] Weapon_Pistol".to_string()],
/// ];
///
/// let results = scan_records_batch(
///     segments,
///     vec!["ActorBase".to_string(), "Weapon".to_string()],
///     vec![],
/// );
///
/// assert_eq!(results.len(), 2);
/// ```
pub fn scan_records_batch(
    segments: Vec<Vec<String>>,
    target_records: Vec<String>,
    ignore_records: Vec<String>,
) -> Vec<Vec<String>> {
    try_scan_records_batch(segments, target_records, ignore_records).unwrap_or_default()
}

/// Fallible variant of [`scan_records_batch`].
pub fn try_scan_records_batch(
    segments: Vec<Vec<String>>,
    target_records: Vec<String>,
    ignore_records: Vec<String>,
) -> ScanLogResult<Vec<Vec<String>>> {
    const RSP_MARKER: &str = "[RSP+";
    const RSP_OFFSET: usize = 30;

    // Convert to lowercase sets
    let lower_targets: HashSet<String> = target_records.iter().map(|s| s.to_lowercase()).collect();

    let lower_ignores: HashSet<String> = ignore_records.iter().map(|s| s.to_lowercase()).collect();

    // Build Aho-Corasick automatons for efficiency
    let target_matcher = RecordScanner::build_matcher(&lower_targets)?;
    let ignore_matcher = RecordScanner::build_matcher(&lower_ignores)?;

    // Process segments in parallel
    Ok(segments
        .par_iter()
        .map(|segment| {
            let mut matches = Vec::new();

            for line in segment {
                let lower_line = line.to_lowercase();

                // Check patterns
                if target_matcher.is_match(&lower_line)
                    && !ignore_matcher.is_match(&lower_line)
                    && let Some(record) =
                        RecordScanner::extract_record_line(line, RSP_MARKER, RSP_OFFSET)
                {
                    matches.push(record);
                }
            }

            matches
        })
        .collect())
}

/// Checks if a line contains any target record while not containing ignore terms.
///
/// This utility function tests whether a single line contains any of the target record
/// names and doesn't contain any of the ignore terms. All matching is case-insensitive.
/// Useful for filtering lines before more expensive pattern matching operations.
///
/// # Arguments
///
/// * `line` - The line to test for record references
/// * `target_records` - List of record names to match
/// * `ignore_records` - List of terms that should exclude the line
///
/// # Returns
///
/// `true` if the line contains a target record and no ignore terms, `false` otherwise.
///
/// # Performance
///
/// - Simple substring matching with lowercase conversion
/// - Processes ~500,000 lines/second
/// - Suitable for hot path filtering
///
/// # Example
///
/// ```rust
/// use classic_scanlog_core::record_scanner::contains_record;
///
/// let targets = vec!["ActorBase".to_string()];
/// let ignores = vec!["System".to_string()];
///
/// assert!(contains_record("ActorBase_Player", &targets, &ignores));
/// assert!(!contains_record("ActorBase_System", &targets, &ignores));
/// assert!(!contains_record("Weapon_Pistol", &targets, &ignores));
/// ```
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

#[cfg(test)]
#[path = "record_scanner_tests.rs"]
mod tests;
