//! Node projection of aggregate semantic FormID Finding analysis.

use classic_scanlog_core::{
    AnalyzerError, FormIDFindingAnalysisInput as CoreAnalysisInput,
    FormIDFindingAnalysisResult as CoreAnalysisResult, FormIDFindingAnalyzer as CoreAnalyzer,
    FormIDPlugin as CorePlugin, FormIDValueLookupStatus as CoreValueLookupStatus,
};
use napi::bindgen_prelude::AsyncTask;
use napi::{Env, Task};

use crate::crashgen_settings_analyzer::{JsAnalyzerKind, analyzer_error_to_napi};
use crate::database::JsFormIdValueLookup;

/// One owned plugin identity and its load-order prefix.
#[derive(Clone)]
#[napi(object)]
pub struct JsFormIdPlugin {
    /// Plugin filename in caller-provided casing.
    pub name: String,
    /// Two-digit full-plugin or five-digit `FE` light-plugin prefix.
    pub prefix: String,
}

/// Owned Crash Log facts for one aggregate FormID Finding analysis call.
#[derive(Clone)]
#[napi(object)]
pub struct JsFormIdFindingAnalysisInput {
    /// Crash Log evidence lines in caller-provided casing.
    pub crash_lines: Vec<String>,
    /// Parsed plugin identities and load-order prefixes.
    pub plugins: Vec<JsFormIdPlugin>,
}

/// Stable semantic state of optional value lookup for one finding.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsFormIdValueLookupStatus {
    /// The identifier did not resolve to a plugin, so lookup was inapplicable.
    #[napi(value = "not_applicable")]
    NotApplicable,
    /// Value lookup was explicitly disabled.
    #[napi(value = "disabled")]
    Disabled,
    /// Lookup completed successfully without finding a value.
    #[napi(value = "missing")]
    Missing,
    /// Lookup completed successfully and returned a value.
    #[napi(value = "found")]
    Found,
}

/// One distinct semantic FormID Finding.
#[derive(Clone)]
#[napi(object)]
pub struct JsFormIdFinding {
    /// Canonical uppercase eight-digit FormID including its load-order prefix.
    pub identifier: String,
    /// Number of matching occurrences in the supplied evidence.
    pub occurrences: u32,
    /// Resolved plugin name, absent when the prefix is unresolved.
    pub plugin: Option<String>,
    /// Semantic lookup state distinct from the optional value payload.
    pub value_lookup_status: JsFormIdValueLookupStatus,
    /// Human-readable value returned by a successful lookup hit.
    pub value: Option<String>,
}

/// Completed FormID Finding analysis, including explicit empty success.
#[derive(Clone)]
#[napi(object)]
pub struct JsFormIdFindingAnalysisResult {
    /// Distinct findings in canonical identifier order.
    pub findings: Vec<JsFormIdFinding>,
}

/// Immutable Node handle over aggregate semantic FormID Finding analysis.
#[derive(Debug)]
#[napi]
pub struct FormIdFindingAnalyzer {
    inner: CoreAnalyzer,
}

#[napi]
impl FormIdFindingAnalyzer {
    /// Creates an analyzer over an existing opaque FormID Value Lookup handle.
    ///
    /// The analyzer clones the core facade, so the JavaScript lookup and analyzer
    /// handles may be reused independently without exposing adapter internals.
    #[napi(constructor)]
    pub fn new(value_lookup: &JsFormIdValueLookup) -> Self {
        build_analyzer(value_lookup.core_clone())
    }

    /// Returns the stable focused-analyzer identity for this handle.
    #[napi(getter)]
    pub fn kind(&self) -> JsAnalyzerKind {
        JsAnalyzerKind::FormIdFinding
    }

    /// Runs one aggregate semantic analysis on CLASSIC's shared runtime.
    ///
    /// @returns Typed resolved and unresolved findings, including explicit empty success.
    /// @throws An error with stable `analyzerKind`, `code`, and `message` fields.
    #[napi(ts_return_type = "Promise<JsFormIdFindingAnalysisResult>")]
    pub fn analyze(
        &self,
        input: JsFormIdFindingAnalysisInput,
    ) -> napi::Result<AsyncTask<FormIdFindingAnalysisTask>> {
        Ok(AsyncTask::new(FormIdFindingAnalysisTask {
            analyzer: self.inner.clone(),
            input: input_to_core(input),
        }))
    }
}

/// AsyncTask carrier that keeps shared-runtime work off the JavaScript thread.
pub struct FormIdFindingAnalysisTask {
    analyzer: CoreAnalyzer,
    input: CoreAnalysisInput,
}

/// Domain result retained until JavaScript-thread error projection is available.
pub enum FormIdFindingAnalysisTaskOutput {
    /// Completed semantic result.
    Success(JsFormIdFindingAnalysisResult),
    /// Shared typed analyzer failure.
    Failure(AnalyzerError),
}

impl Task for FormIdFindingAnalysisTask {
    type Output = FormIdFindingAnalysisTaskOutput;
    type JsValue = JsFormIdFindingAnalysisResult;

    /// Waits on the process-wide shared runtime from NAPI's worker pool.
    fn compute(&mut self) -> napi::Result<Self::Output> {
        let result =
            classic_shared_core::get_runtime().block_on(self.analyzer.analyze(self.input.clone()));
        Ok(match result {
            Ok(result) => FormIdFindingAnalysisTaskOutput::Success(result_to_js(result)),
            Err(error) => FormIdFindingAnalysisTaskOutput::Failure(error),
        })
    }

    /// Resolves the typed result or attaches stable analyzer metadata to the rejection.
    fn resolve(&mut self, env: Env, output: Self::Output) -> napi::Result<Self::JsValue> {
        match output {
            FormIdFindingAnalysisTaskOutput::Success(result) => Ok(result),
            FormIdFindingAnalysisTaskOutput::Failure(error) => {
                Err(analyzer_error_to_napi(env, error))
            }
        }
    }
}

/// Constructs the thin Node handle from an owned core lookup facade.
fn build_analyzer(value_lookup: classic_database_core::FormIdValueLookup) -> FormIdFindingAnalyzer {
    FormIdFindingAnalyzer {
        inner: CoreAnalyzer::new(value_lookup),
    }
}

/// Converts owned Node input into the core domain carrier.
fn input_to_core(input: JsFormIdFindingAnalysisInput) -> CoreAnalysisInput {
    CoreAnalysisInput {
        crash_lines: input.crash_lines,
        plugins: input
            .plugins
            .into_iter()
            .map(|plugin| CorePlugin {
                name: plugin.name,
                prefix: plugin.prefix,
            })
            .collect(),
    }
}

/// Projects a core semantic result mechanically without presentation data.
fn result_to_js(result: CoreAnalysisResult) -> JsFormIdFindingAnalysisResult {
    JsFormIdFindingAnalysisResult {
        findings: result
            .findings
            .into_iter()
            .map(|finding| JsFormIdFinding {
                identifier: finding.identifier,
                occurrences: finding.occurrences,
                plugin: finding.plugin,
                value_lookup_status: value_lookup_status_to_js(finding.value_lookup_status),
                value: finding.value,
            })
            .collect(),
    }
}

/// Maps the stable core lookup state to its Node string-enum projection.
fn value_lookup_status_to_js(status: CoreValueLookupStatus) -> JsFormIdValueLookupStatus {
    match status {
        CoreValueLookupStatus::NotApplicable => JsFormIdValueLookupStatus::NotApplicable,
        CoreValueLookupStatus::Disabled => JsFormIdValueLookupStatus::Disabled,
        CoreValueLookupStatus::Missing => JsFormIdValueLookupStatus::Missing,
        CoreValueLookupStatus::Found => JsFormIdValueLookupStatus::Found,
    }
}

// Keep the repository's required sibling-test declaration intact under rustfmt.
#[rustfmt::skip]
#[cfg(test)] #[path = "formid_finding_analyzer_tests.rs"] mod tests;
