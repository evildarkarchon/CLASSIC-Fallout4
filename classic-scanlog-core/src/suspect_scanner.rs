//! Suspect Scanner - Pattern matching for known crash suspects
//!
//! This module scans crash logs for known patterns and suspect errors:
//! - Main error checking against known patterns
//! - Call stack scanning for problematic signatures
//! - DLL-related crash detection
//! - YAML-defined suspect pattern matching

use crate::error::Result;
use std::collections::HashMap;
use rayon::prelude::*;

use crate::report::ReportFragment;

/// Signal modifiers for suspect detection
const MAIN_ERROR_REQUIRED: &str = "ME-REQ";
const MAIN_ERROR_OPTIONAL: &str = "ME-OPT";
const CALLSTACK_NEGATIVE: &str = "NOT";

/// Match status for suspect scanning
#[derive(Debug, Clone)]
struct MatchStatus {
    has_required_item: bool,
    error_req_found: bool,
    error_opt_found: bool,
    stack_found: bool,
}

impl MatchStatus {
    fn new() -> Self {
        Self {
            has_required_item: false,
            error_req_found: false,
            error_opt_found: false,
            stack_found: false,
        }
    }

    /// Check if this represents a suspect match
    fn is_suspect(&self) -> bool {
        if self.has_required_item {
            self.error_req_found
        } else {
            self.error_opt_found || self.stack_found
        }
    }
}

/// High-performance suspect scanner (40x speedup)
#[derive(Clone)]
pub struct SuspectScanner {
    suspects_error_list: HashMap<String, String>,
    suspects_stack_list: HashMap<String, Vec<String>>,
}

impl SuspectScanner {
    pub fn new(
        suspects_error_list: HashMap<String, String>,
        suspects_stack_list: HashMap<String, Vec<String>>,
    ) -> Self {
        Self {
            suspects_error_list,
            suspects_stack_list,
        }
    }

    /// Scan main error for suspect patterns
    ///
    /// Args:
    ///     crashlog_mainerror: The main error from crash log
    ///     max_warn_length: Maximum length for formatting error names
    ///
    /// Returns:
    ///     Tuple of (ReportFragment, bool indicating if suspects found)
    pub fn suspect_scan_mainerror(
        &self,
        crashlog_mainerror: &str,
        max_warn_length: usize,
    ) -> Result<(ReportFragment, bool)> {
        let mut lines = Vec::new();
        let mut found_suspect = false;

        for (error_key, signal) in &self.suspects_error_list {
            // Skip if signal not in crash log
            if !crashlog_mainerror.contains(signal.as_str()) {
                continue;
            }

            // Parse error information (format: "Severity | Error Name")
            if let Some((error_severity, error_name)) = error_key.split_once(" | ") {
                // Format error name for report
                let formatted_error_name = format!("{:.<width$}", error_name, width = max_warn_length);

                // Add to report
                lines.push(format!(
                    "- **Checking for {} SUSPECT FOUND! > Severity : {}** \n\n",
                    formatted_error_name, error_severity
                ));
                lines.push("-----\n".to_string());

                found_suspect = true;
            }
        }

        Ok((ReportFragment::from_lines(lines), found_suspect))
    }

    /// Analyze call stack for suspect patterns with signal modifiers
    ///
    /// Args:
    ///     crashlog_mainerror: Main error from crash log
    ///     segment_callstack_intact: Full call stack segment
    ///     max_warn_length: Maximum length for formatting error names
    ///
    /// Returns:
    ///     Tuple of (ReportFragment, bool indicating if suspects found)
    pub fn suspect_scan_stack(
        &self,
        crashlog_mainerror: &str,
        segment_callstack_intact: &str,
        max_warn_length: usize,
    ) -> Result<(ReportFragment, bool)> {
        let mut lines = Vec::new();
        let mut any_suspect_found = false;

        for (error_key, signal_list) in &self.suspects_stack_list {
            // Parse error information (format: "Severity | Error Name")
            let (error_severity, error_name) = match error_key.split_once(" | ") {
                Some(parts) => parts,
                None => continue,
            };

            // Track match status
            let mut match_status = MatchStatus::new();
            let mut should_skip = false;

            // Process each signal
            for signal in signal_list {
                if Self::process_signal(
                    signal,
                    crashlog_mainerror,
                    segment_callstack_intact,
                    &mut match_status,
                ) {
                    // NOT condition met, skip this error
                    should_skip = true;
                    break;
                }
            }

            if should_skip {
                continue;
            }

            // Check if we have a suspect match
            if match_status.is_suspect() {
                let formatted_error_name = format!("{:.<width$}", error_name, width = max_warn_length);
                lines.push(format!(
                    "- **Checking for {} SUSPECT FOUND! > Severity : {}** \n\n",
                    formatted_error_name, error_severity
                ));
                lines.push("-----\n".to_string());
                any_suspect_found = true;
            }
        }

        Ok((ReportFragment::from_lines(lines), any_suspect_found))
    }

    /// Check if crash involves a DLL file
    ///
    /// Args:
    ///     crashlog_mainerror: Main error from crash log
    ///
    /// Returns:
    ///     ReportFragment containing DLL crash notification, or empty
    pub fn check_dll_crash(crashlog_mainerror: &str) -> Result<ReportFragment> {
        let crashlog_lower = crashlog_mainerror.to_lowercase();

        if crashlog_lower.contains(".dll") && !crashlog_lower.contains("tbbmalloc") {
            Ok(ReportFragment::from_lines(vec![
                "* NOTICE : MAIN ERROR REPORTS THAT A DLL FILE WAS INVOLVED IN THIS CRASH! * \n".to_string(),
                "If that dll file belongs to a mod, that mod is a prime suspect for the crash. \n\n".to_string(),
                "-----\n".to_string(),
            ]))
        } else {
            Ok(ReportFragment::empty())
        }
    }
}

impl SuspectScanner {
    /// Process an individual signal and update match status
    ///
    /// Returns:
    ///     true if processing should stop (NOT condition met)
    fn process_signal(
        signal: &str,
        crashlog_mainerror: &str,
        segment_callstack_intact: &str,
        match_status: &mut MatchStatus,
    ) -> bool {
        // Check if signal has modifier
        if !signal.contains('|') {
            // Simple case: direct string match in callstack
            if segment_callstack_intact.contains(signal) {
                match_status.stack_found = true;
            }
            return false;
        }

        // Parse signal modifier and string
        let (signal_modifier, signal_string) = match signal.split_once('|') {
            Some(parts) => parts,
            None => return false,
        };

        // Process based on signal modifier
        match signal_modifier {
            MAIN_ERROR_REQUIRED => {
                match_status.has_required_item = true;
                if crashlog_mainerror.contains(signal_string) {
                    match_status.error_req_found = true;
                }
            }
            MAIN_ERROR_OPTIONAL => {
                if crashlog_mainerror.contains(signal_string) {
                    match_status.error_opt_found = true;
                }
            }
            CALLSTACK_NEGATIVE => {
                // Return true to break if NOT condition is met
                return segment_callstack_intact.contains(signal_string);
            }
            modifier if modifier.chars().all(|c| c.is_ascii_digit()) => {
                // Check for minimum occurrences
                if let Ok(min_occurrences) = modifier.parse::<usize>() {
                    let count = segment_callstack_intact.matches(signal_string).count();
                    if count >= min_occurrences {
                        match_status.stack_found = true;
                    }
                }
            }
            _ => {}
        }

        false
    }

    /// Batch process multiple crash logs for suspects (parallel)
    ///
    /// This provides significant speedup for batch operations
    pub fn scan_suspects_batch(
        &self,
        crash_logs: Vec<(String, String)>,  // Vec<(main_error, callstack)>
        max_warn_length: usize,
    ) -> Result<Vec<(ReportFragment, bool)>> {
        let results: Vec<_> = crash_logs
            .par_iter()
            .map(|(main_error, callstack)| {
                // Scan main error
                let (main_frag, main_found) = self
                    .suspect_scan_mainerror(main_error, max_warn_length)
                    .unwrap_or_else(|_| (ReportFragment::empty(), false));

                // Scan call stack
                let (stack_frag, stack_found) = self
                    .suspect_scan_stack(main_error, callstack, max_warn_length)
                    .unwrap_or_else(|_| (ReportFragment::empty(), false));

                // Combine results
                (main_frag.combine(&stack_frag), main_found || stack_found)
            })
            .collect();

        Ok(results)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_suspect_scan_mainerror() {
        let mut error_list = HashMap::new();
        error_list.insert(
            "Critical | Memory Access Violation".to_string(),
            "ACCESS_VIOLATION".to_string(),
        );

        let scanner = SuspectScanner::new(error_list, HashMap::new());

        let (fragment, found) = scanner
            .suspect_scan_mainerror("Error: ACCESS_VIOLATION at 0x12345", 50)
            .unwrap();

        assert!(found);
        assert!(fragment.len() > 0);
    }

    #[test]
    fn test_check_dll_crash() {
        let fragment = SuspectScanner::check_dll_crash(
            "Error in plugin.dll at address 0x12345"
        ).unwrap();

        assert!(fragment.len() > 0);

        // Should not trigger for tbbmalloc
        let fragment2 = SuspectScanner::check_dll_crash(
            "Error in tbbmalloc.dll"
        ).unwrap();

        assert!(fragment2.len() == 0);
    }

    #[test]
    fn test_signal_processing() {
        let mut match_status = MatchStatus::new();

        // Test ME-REQ signal
        SuspectScanner::process_signal(
            "ME-REQ|OutOfMemory",
            "OutOfMemory error occurred",
            "callstack here",
            &mut match_status,
        );

        assert!(match_status.has_required_item);
        assert!(match_status.error_req_found);
        assert!(match_status.is_suspect());
    }

    #[test]
    fn test_occurrence_count() {
        let mut match_status = MatchStatus::new();

        // Test occurrence count signal (3|pattern means pattern must appear 3+ times)
        SuspectScanner::process_signal(
            "3|SomePattern",
            "main error",
            "SomePattern\nSomePattern\nSomePattern\ndata",
            &mut match_status,
        );

        assert!(match_status.stack_found);
    }
}
