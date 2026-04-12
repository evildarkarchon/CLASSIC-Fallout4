//! Suspect Scanner - Pattern matching for known crash suspects
//!
//! This module scans crash logs for known patterns and suspect errors:
//! - Main error checking against known patterns
//! - Call stack scanning for problematic signatures
//! - DLL-related crash detection
//! - YAML-defined suspect pattern matching

use crate::error::Result;
use classic_config_core::{SuspectErrorRule, SuspectStackRule};
use rayon::prelude::*;

use crate::report::ReportFragment;

/// Match status for suspect scanning
#[derive(Debug, Clone)]
struct MatchStatus {
    has_required_item: bool,
    required_main_error_found: bool,
    error_opt_found: bool,
    stack_found: bool,
}

impl MatchStatus {
    fn new() -> Self {
        Self {
            has_required_item: false,
            required_main_error_found: false,
            error_opt_found: false,
            stack_found: false,
        }
    }

    /// Check if this represents a suspect match
    fn is_suspect(&self) -> bool {
        if self.has_required_item {
            self.required_main_error_found
        } else {
            self.error_opt_found || self.stack_found
        }
    }
}

/// High-performance suspect scanner (40x speedup)
#[derive(Clone)]
pub struct SuspectScanner {
    suspect_error_rules: Vec<SuspectErrorRule>,
    suspect_stack_rules: Vec<SuspectStackRule>,
}

impl SuspectScanner {
    /// Creates a new suspect scanner with the given pattern lists.
    ///
    /// This constructor initializes a scanner that can detect known crash suspects
    /// by matching patterns against crash log main errors and call stacks. The scanner
    /// supports structured rule fields for main-error requirements, exclusions,
    /// and minimum occurrence counts.
    ///
    /// # Arguments
    ///
    /// * `suspect_error_rules` - Ordered main-error suspect rules
    /// * `suspect_stack_rules` - Ordered stack suspect rules
    ///
    /// # Returns
    ///
    /// A new `SuspectScanner` instance ready to scan crash logs for suspects.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::suspect_scanner::SuspectScanner;
    /// use classic_config_core::{SuspectErrorRule, SuspectStackRule};
    ///
    /// let scanner = SuspectScanner::new(
    ///     vec![SuspectErrorRule {
    ///         id: "memory_access_violation".to_string(),
    ///         name: "Memory Access Violation".to_string(),
    ///         severity: 5,
    ///         main_error_contains_any: vec!["ACCESS_VIOLATION".to_string()],
    ///     }],
    ///     vec![SuspectStackRule {
    ///         id: "stack_overflow".to_string(),
    ///         name: "Stack Overflow".to_string(),
    ///         severity: 6,
    ///         main_error_required_any: vec!["EXCEPTION_STACK_OVERFLOW".to_string()],
    ///         main_error_optional_any: Vec::new(),
    ///         stack_contains_any: Vec::new(),
    ///         exclude_if_stack_contains_any: Vec::new(),
    ///         stack_contains_at_least: Vec::new(),
    ///     }],
    /// );
    /// ```
    pub fn new(
        suspect_error_rules: Vec<SuspectErrorRule>,
        suspect_stack_rules: Vec<SuspectStackRule>,
    ) -> Self {
        Self {
            suspect_error_rules,
            suspect_stack_rules,
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
        // Collect suspects with severity for sorting (Python parity: highest severity first)
        // Tuple: (severity_num, error_name_for_tiebreak, formatted_name, severity_str)
        let mut suspects: Vec<(i32, String, String, String)> = Vec::new();

        for rule in &self.suspect_error_rules {
            if !rule
                .main_error_contains_any
                .iter()
                .any(|signal| crashlog_mainerror.contains(signal.as_str()))
            {
                continue;
            }

            let formatted_error_name = format!("{:.<width$}", rule.name, width = max_warn_length);
            suspects.push((
                rule.severity,
                rule.name.clone(),
                formatted_error_name,
                rule.severity.to_string(),
            ));
        }

        // Sort by severity descending (highest first), then alphabetically by error name for determinism
        suspects.sort_by(|a, b| {
            match b.0.cmp(&a.0) {
                std::cmp::Ordering::Equal => a.1.cmp(&b.1), // Alphabetical tiebreak
                other => other,
            }
        });

        // Build output lines from sorted suspects
        let mut lines = Vec::new();
        let found_suspect = !suspects.is_empty();

        for (_, _, formatted_error_name, error_severity) in suspects {
            lines.push(format!(
                "- **Checking for {} SUSPECT FOUND! > Severity : {}** \n\n",
                formatted_error_name, error_severity
            ));
            lines.push("-----\n".to_string());
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
        // Collect suspects with severity for sorting (Python parity: highest severity first)
        // Tuple: (severity_num, error_name_for_tiebreak, formatted_name, severity_str)
        let mut suspects: Vec<(i32, String, String, String)> = Vec::new();

        for rule in &self.suspect_stack_rules {
            if rule
                .exclude_if_stack_contains_any
                .iter()
                .any(|signal| segment_callstack_intact.contains(signal))
            {
                continue;
            }

            let mut match_status = MatchStatus::new();
            match_status.has_required_item = !rule.main_error_required_any.is_empty();
            match_status.required_main_error_found = rule
                .main_error_required_any
                .iter()
                .any(|signal| crashlog_mainerror.contains(signal));
            match_status.error_opt_found = rule
                .main_error_optional_any
                .iter()
                .any(|signal| crashlog_mainerror.contains(signal));
            match_status.stack_found = rule
                .stack_contains_any
                .iter()
                .any(|signal| segment_callstack_intact.contains(signal))
                || rule.stack_contains_at_least.iter().any(|count_rule| {
                    segment_callstack_intact
                        .matches(&count_rule.substring)
                        .count()
                        >= count_rule.count
                });

            if match_status.is_suspect() {
                let formatted_error_name =
                    format!("{:.<width$}", rule.name, width = max_warn_length);
                suspects.push((
                    rule.severity,
                    rule.name.clone(),
                    formatted_error_name,
                    rule.severity.to_string(),
                ));
            }
        }

        // Sort by severity descending (highest first), then alphabetically by error name for determinism
        suspects.sort_by(|a, b| {
            match b.0.cmp(&a.0) {
                std::cmp::Ordering::Equal => a.1.cmp(&b.1), // Alphabetical tiebreak
                other => other,
            }
        });

        // Build output lines from sorted suspects
        let mut lines = Vec::new();
        let any_suspect_found = !suspects.is_empty();

        for (_, _, formatted_error_name, error_severity) in suspects {
            lines.push(format!(
                "- **Checking for {} SUSPECT FOUND! > Severity : {}** \n\n",
                formatted_error_name, error_severity
            ));
            lines.push("-----\n".to_string());
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
    /// Batch process multiple crash logs for suspects (parallel)
    ///
    /// This provides significant speedup for batch operations
    pub fn scan_suspects_batch(
        &self,
        crash_logs: Vec<(String, String)>, // Vec<(main_error, callstack)>
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
    use classic_config_core::{SuspectErrorRule, SuspectStackCountRule, SuspectStackRule};

    #[test]
    fn test_suspect_scan_mainerror() {
        let scanner = SuspectScanner::new(
            vec![SuspectErrorRule {
                id: "memory_access_violation".to_string(),
                name: "Memory Access Violation".to_string(),
                severity: 5,
                main_error_contains_any: vec!["ACCESS_VIOLATION".to_string()],
            }],
            Vec::new(),
        );

        let (fragment, found) = scanner
            .suspect_scan_mainerror("Error: ACCESS_VIOLATION at 0x12345", 50)
            .unwrap();

        assert!(found);
        assert!(!fragment.is_empty());
    }

    #[test]
    fn test_check_dll_crash() {
        let fragment =
            SuspectScanner::check_dll_crash("Error in plugin.dll at address 0x12345").unwrap();

        assert!(!fragment.is_empty());

        // Should not trigger for tbbmalloc
        let fragment2 = SuspectScanner::check_dll_crash("Error in tbbmalloc.dll").unwrap();

        assert!(fragment2.is_empty());
    }

    #[test]
    fn test_suspect_scan_stack_with_structured_conditions() {
        let scanner = SuspectScanner::new(
            Vec::new(),
            vec![SuspectStackRule {
                id: "structured_stack_rule".to_string(),
                name: "Structured Stack Rule".to_string(),
                severity: 4,
                main_error_required_any: vec!["OutOfMemory".to_string()],
                main_error_optional_any: vec!["MaybeRelated".to_string()],
                stack_contains_any: vec!["SomePattern".to_string()],
                exclude_if_stack_contains_any: Vec::new(),
                stack_contains_at_least: vec![SuspectStackCountRule {
                    substring: "RepeatedPattern".to_string(),
                    count: 3,
                }],
            }],
        );

        let (fragment, found) = scanner
            .suspect_scan_stack(
                "OutOfMemory error occurred",
                "SomePattern\nRepeatedPattern\nRepeatedPattern\nRepeatedPattern",
                50,
            )
            .unwrap();

        assert!(found);
        assert!(!fragment.is_empty());
    }

    #[test]
    fn test_suspect_scan_stack_exclusion_condition() {
        let scanner = SuspectScanner::new(
            Vec::new(),
            vec![SuspectStackRule {
                id: "excluded_rule".to_string(),
                name: "Excluded Rule".to_string(),
                severity: 2,
                main_error_required_any: Vec::new(),
                main_error_optional_any: Vec::new(),
                stack_contains_any: vec!["TargetPattern".to_string()],
                exclude_if_stack_contains_any: vec!["SkipPattern".to_string()],
                stack_contains_at_least: Vec::new(),
            }],
        );

        let (fragment, found) = scanner
            .suspect_scan_stack("main error", "TargetPattern\nSkipPattern", 50)
            .unwrap();

        assert!(!found);
        assert!(fragment.is_empty());
    }
}
