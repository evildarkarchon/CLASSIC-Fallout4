//! Node projection of focused semantic Plugin Evidence analysis.

use classic_scanlog_core::{
    AnalyzerError, PluginEvidenceAnalysisInput as CoreAnalysisInput,
    PluginEvidenceAnalysisResult as CoreAnalysisResult, PluginEvidenceAnalyzer as CoreAnalyzer,
};
use napi::Env;

use crate::crashgen_settings_analyzer::{JsAnalyzerKind, analyzer_error_to_napi};

/// Owned input for one aggregate Plugin Evidence analysis call.
#[derive(Clone)]
#[napi(object)]
pub struct JsPluginEvidenceAnalysisInput {
    /// Call-stack lines in caller-provided casing.
    pub call_stack: Vec<String>,
    /// Plugin identities parsed from the Crash Log.
    pub plugins: Vec<String>,
}

/// One typed plugin identity and its call-stack occurrence count.
#[derive(Clone)]
#[napi(object)]
pub struct JsPluginEvidence {
    /// Normalized plugin identity.
    pub plugin: String,
    /// Number of call-stack lines containing the plugin identity.
    pub occurrences: u32,
}

/// Completed Plugin Evidence analysis, including explicit empty success.
#[derive(Clone)]
#[napi(object)]
pub struct JsPluginEvidenceAnalysisResult {
    /// Typed Plugin Evidence in candidate order.
    pub evidence: Vec<JsPluginEvidence>,
}

/// Immutable Node handle over validated Plugin Evidence configuration.
#[derive(Debug)]
#[napi]
pub struct PluginEvidenceAnalyzer {
    inner: CoreAnalyzer,
}

#[napi]
impl PluginEvidenceAnalyzer {
    /// Validates and normalizes owned plugin-ignore configuration.
    ///
    /// @throws An error with stable `analyzerKind`, `code`, and `message` fields.
    #[napi(constructor)]
    pub fn new(env: Env, ignored_plugins: Vec<String>) -> napi::Result<Self> {
        build_analyzer(ignored_plugins).map_err(|error| analyzer_error_to_napi(env, error))
    }

    /// Returns the stable focused-analyzer identity for this handle.
    #[napi(getter)]
    pub fn kind(&self) -> JsAnalyzerKind {
        JsAnalyzerKind::PluginEvidence
    }

    /// Runs one aggregate semantic analysis over owned Crash Log evidence.
    ///
    /// @returns Typed evidence, including an explicit empty array on no match.
    /// @throws An error with stable `analyzerKind`, `code`, and `message` fields.
    #[napi]
    pub fn analyze(
        &self,
        env: Env,
        input: JsPluginEvidenceAnalysisInput,
    ) -> napi::Result<JsPluginEvidenceAnalysisResult> {
        self.analyze_owned(input)
            .map_err(|error| analyzer_error_to_napi(env, error))
    }
}

impl PluginEvidenceAnalyzer {
    /// Runs the mechanical carrier projection without requiring a JavaScript environment.
    fn analyze_owned(
        &self,
        input: JsPluginEvidenceAnalysisInput,
    ) -> Result<JsPluginEvidenceAnalysisResult, AnalyzerError> {
        self.inner
            .analyze(CoreAnalysisInput {
                call_stack: input.call_stack,
                plugins: input.plugins,
            })
            .map(result_to_js)
    }
}

/// Constructs the thin Node handle while retaining the core typed error.
fn build_analyzer(ignored_plugins: Vec<String>) -> Result<PluginEvidenceAnalyzer, AnalyzerError> {
    CoreAnalyzer::new(ignored_plugins).map(|inner| PluginEvidenceAnalyzer { inner })
}

/// Projects the core semantic result mechanically without presentation data.
fn result_to_js(result: CoreAnalysisResult) -> JsPluginEvidenceAnalysisResult {
    JsPluginEvidenceAnalysisResult {
        evidence: result
            .evidence
            .into_iter()
            .map(|entry| JsPluginEvidence {
                plugin: entry.plugin,
                occurrences: entry.occurrences,
            })
            .collect(),
    }
}

#[cfg(test)]
#[path = "plugin_evidence_analyzer_tests.rs"]
mod tests;
