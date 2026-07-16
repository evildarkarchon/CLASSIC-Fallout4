//! Semantic Named Record Finding analysis.

use std::collections::HashSet;
use std::sync::Arc;

use aho_corasick::AhoCorasick;
use indexmap::IndexMap;

use crate::analyzer::{AnalyzerError, AnalyzerErrorCode, AnalyzerKind, AnalyzerResult};
use crate::record_scanner::RecordScanner;

/// Owned Crash Log facts consumed by one Named Record Finding analysis call.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct NamedRecordFindingAnalysisInput {
    /// Crash Log lines in their caller-provided casing.
    pub crash_lines: Vec<String>,
}

/// One distinct named record observed in Crash Log evidence.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NamedRecordFinding {
    /// Extracted record text in its source casing.
    pub record: String,
    /// Number of times the exact extracted record occurred.
    pub occurrences: u32,
}

/// Completed Named Record Finding analysis, including explicit empty success.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct NamedRecordFindingAnalysisResult {
    /// Distinct typed findings in first-observed order.
    pub findings: Vec<NamedRecordFinding>,
}

#[derive(Debug)]
struct CompiledConfiguration {
    target_matcher: Option<AhoCorasick>,
    ignore_matcher: Option<AhoCorasick>,
}

/// Immutable analyzer for authored named records observed in Crash Log evidence.
#[derive(Clone, Debug)]
pub struct NamedRecordFindingAnalyzer {
    configuration: Arc<CompiledConfiguration>,
}

impl NamedRecordFindingAnalyzer {
    /// Validates owned record configuration and compiles reusable matcher state.
    pub fn new(target_records: Vec<String>, ignored_records: Vec<String>) -> AnalyzerResult<Self> {
        let target_records = normalize_patterns(target_records, "target record")?;
        let ignored_records = normalize_patterns(ignored_records, "ignored record")?;
        Ok(Self {
            configuration: Arc::new(CompiledConfiguration {
                target_matcher: compile_matcher(target_records, "target record")?,
                ignore_matcher: compile_matcher(ignored_records, "ignored record")?,
            }),
        })
    }

    /// Analyzes owned Crash Log lines without producing report text.
    pub fn analyze(
        &self,
        input: NamedRecordFindingAnalysisInput,
    ) -> AnalyzerResult<NamedRecordFindingAnalysisResult> {
        let Some(target_matcher) = &self.configuration.target_matcher else {
            return Ok(NamedRecordFindingAnalysisResult::default());
        };
        let mut findings = IndexMap::<String, u32>::new();
        for line in input.crash_lines {
            let lower_line = line.to_lowercase();
            if !target_matcher.is_match(&lower_line)
                || self
                    .configuration
                    .ignore_matcher
                    .as_ref()
                    .is_some_and(|matcher| matcher.is_match(&lower_line))
            {
                continue;
            }
            let Some(record) = RecordScanner::extract_record_line(&line, "[RSP+", 30)
                .filter(|record| !record.is_empty())
            else {
                continue;
            };
            let occurrences = findings.entry(record).or_default();
            *occurrences = occurrences.checked_add(1).ok_or_else(|| {
                analysis_failure("Named Record Finding occurrence count exceeded u32")
            })?;
        }

        Ok(NamedRecordFindingAnalysisResult {
            findings: findings
                .into_iter()
                .map(|(record, occurrences)| NamedRecordFinding {
                    record,
                    occurrences,
                })
                .collect(),
        })
    }
}

/// Normalizes and validates caller-authored matcher patterns.
fn normalize_patterns(patterns: Vec<String>, label: &str) -> AnalyzerResult<Vec<String>> {
    let mut seen = HashSet::new();
    patterns
        .into_iter()
        .map(|pattern| {
            let pattern = pattern.trim();
            if pattern.is_empty() {
                return Err(invalid_configuration(format!(
                    "Named Record Finding {label} must not be empty"
                )));
            }
            Ok(pattern.to_lowercase())
        })
        .filter_map(|pattern| match pattern {
            Ok(pattern) if seen.insert(pattern.clone()) => Some(Ok(pattern)),
            Ok(_) => None,
            Err(error) => Some(Err(error)),
        })
        .collect()
}

/// Compiles one immutable multi-pattern matcher during analyzer construction.
fn compile_matcher(patterns: Vec<String>, label: &str) -> AnalyzerResult<Option<AhoCorasick>> {
    if patterns.is_empty() {
        return Ok(None);
    }
    AhoCorasick::new(patterns).map(Some).map_err(|error| {
        invalid_configuration(format!(
            "Named Record Finding {label} matcher could not be compiled: {error}"
        ))
    })
}

/// Creates the shared typed error for invalid Named Record Finding configuration.
fn invalid_configuration(message: String) -> AnalyzerError {
    AnalyzerError::new(
        AnalyzerKind::NamedRecordFinding,
        AnalyzerErrorCode::InvalidConfiguration,
        message,
    )
}

/// Creates the shared typed error for a Named Record Finding analysis failure.
fn analysis_failure(message: impl Into<String>) -> AnalyzerError {
    // The shared contract currently uses InvalidConfiguration for matcher/count failures.
    AnalyzerError::new(
        AnalyzerKind::NamedRecordFinding,
        AnalyzerErrorCode::InvalidConfiguration,
        message,
    )
}

#[cfg(test)]
#[path = "named_record_finding_analyzer_tests.rs"]
mod tests;
