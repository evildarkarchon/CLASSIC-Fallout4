//! Node projection of focused semantic Named Record Finding analysis.

use classic_scanlog_core::{
    AnalyzerError, NamedRecordFindingAnalysisInput as CoreAnalysisInput,
    NamedRecordFindingAnalysisResult as CoreAnalysisResult,
    NamedRecordFindingAnalyzer as CoreAnalyzer,
};
use napi::Env;

use crate::crashgen_settings_analyzer::{JsAnalyzerKind, analyzer_error_to_napi};

/// Owned Crash Log lines for one aggregate Named Record Finding analysis call.
#[derive(Clone)]
#[napi(object)]
pub struct JsNamedRecordFindingAnalysisInput {
    /// Crash Log lines in caller-provided casing.
    pub crash_lines: Vec<String>,
}

/// One distinct named record and its exact occurrence count.
#[derive(Clone)]
#[napi(object)]
pub struct JsNamedRecordFinding {
    /// Extracted record text in its source casing.
    pub record: String,
    /// Number of exact extracted record occurrences.
    pub occurrences: u32,
}

/// Completed Named Record Finding analysis, including explicit empty success.
#[derive(Clone)]
#[napi(object)]
pub struct JsNamedRecordFindingAnalysisResult {
    /// Distinct typed findings in first-observed order.
    pub findings: Vec<JsNamedRecordFinding>,
}

/// Immutable Node handle over validated, compiled Named Record Finding configuration.
#[derive(Debug)]
#[napi]
pub struct NamedRecordFindingAnalyzer {
    inner: CoreAnalyzer,
}

#[napi]
impl NamedRecordFindingAnalyzer {
    /// Validates configuration and compiles matcher state immediately.
    ///
    /// @throws An error with stable `analyzerKind`, `code`, and `message` fields.
    #[napi(constructor)]
    pub fn new(
        env: Env,
        target_records: Vec<String>,
        ignored_records: Vec<String>,
    ) -> napi::Result<Self> {
        build_analyzer(target_records, ignored_records)
            .map_err(|error| analyzer_error_to_napi(env, error))
    }

    /// Returns the stable focused-analyzer identity for this handle.
    #[napi(getter)]
    pub fn kind(&self) -> JsAnalyzerKind {
        JsAnalyzerKind::NamedRecordFinding
    }

    /// Runs one aggregate semantic analysis over owned Crash Log lines.
    ///
    /// @returns Typed distinct findings, including an explicit empty array on no match.
    /// @throws An error with stable `analyzerKind`, `code`, and `message` fields.
    #[napi]
    pub fn analyze(
        &self,
        env: Env,
        input: JsNamedRecordFindingAnalysisInput,
    ) -> napi::Result<JsNamedRecordFindingAnalysisResult> {
        self.analyze_owned(input)
            .map_err(|error| analyzer_error_to_napi(env, error))
    }
}

impl NamedRecordFindingAnalyzer {
    /// Runs the mechanical carrier projection without requiring a JavaScript environment.
    fn analyze_owned(
        &self,
        input: JsNamedRecordFindingAnalysisInput,
    ) -> Result<JsNamedRecordFindingAnalysisResult, AnalyzerError> {
        self.inner
            .analyze(CoreAnalysisInput {
                crash_lines: input.crash_lines,
            })
            .map(result_to_js)
    }
}

/// Constructs the thin Node handle while retaining the core typed error.
fn build_analyzer(
    target_records: Vec<String>,
    ignored_records: Vec<String>,
) -> Result<NamedRecordFindingAnalyzer, AnalyzerError> {
    CoreAnalyzer::new(target_records, ignored_records)
        .map(|inner| NamedRecordFindingAnalyzer { inner })
}

/// Projects the core semantic result mechanically without presentation data.
fn result_to_js(result: CoreAnalysisResult) -> JsNamedRecordFindingAnalysisResult {
    JsNamedRecordFindingAnalysisResult {
        findings: result
            .findings
            .into_iter()
            .map(|finding| JsNamedRecordFinding {
                record: finding.record,
                occurrences: finding.occurrences,
            })
            .collect(),
    }
}

#[cfg(test)]
#[path = "named_record_finding_analyzer_tests.rs"]
mod tests;
