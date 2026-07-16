//! Node projection of the aggregate semantic Mod Guidance Analyzer.

use std::collections::HashSet;

use classic_config_core::{
    CoreModEntry, CoreModExclude, ModConflictEntry, ModSolutionCriteria, ModSolutionEntry,
};
use classic_scanlog_core::{
    AnalyzerError, ImportantModGuidance as CoreImportantModGuidance,
    ModConflictGuidance as CoreModConflictGuidance, ModGuidanceAnalysisInput,
    ModGuidanceAnalysisResult, ModGuidanceAnalyzer as CoreModGuidanceAnalyzer,
    ModGuidanceMatchState as CoreModGuidanceMatchState,
    ModSolutionGuidance as CoreModSolutionGuidance,
};
use indexmap::IndexMap;
use napi::Env;

use crate::crashgen_settings_analyzer::{JsAnalyzerKind, analyzer_error_to_napi};

/// Match strategy for one frequent-crash or solution rule.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsModGuidanceCriteriaKind {
    /// Match when any configured criterion is present.
    #[napi(value = "any")]
    Any,
    /// Match only when every configured criterion is present.
    #[napi(value = "all")]
    All,
}

/// Semantic match state shared by every Mod Guidance result family.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsModGuidanceMatchState {
    /// Configured guidance matched installed plugin or XSE evidence.
    #[napi(value = "matched")]
    Matched,
    /// An applicable important mod was not found.
    #[napi(value = "missing")]
    Missing,
    /// An installed GPU-specific mod does not match the detected GPU vendor.
    #[napi(value = "gpu_mismatch")]
    GpuMismatch,
}

impl From<CoreModGuidanceMatchState> for JsModGuidanceMatchState {
    fn from(value: CoreModGuidanceMatchState) -> Self {
        match value {
            CoreModGuidanceMatchState::Matched => Self::Matched,
            CoreModGuidanceMatchState::Missing => Self::Missing,
            CoreModGuidanceMatchState::GpuMismatch => Self::GpuMismatch,
        }
    }
}

/// One owned conflict rule used to construct the analyzer.
#[derive(Clone)]
#[napi(object)]
pub struct JsModConflictRule {
    /// Matcher identity for the first mod.
    pub mod_a: String,
    /// Matcher identity for the second mod.
    pub mod_b: String,
    /// Authored display name for the first mod.
    pub name_a: String,
    /// Authored display name for the second mod.
    pub name_b: String,
    /// Authored explanation of the conflict.
    pub description: String,
    /// Authored remediation guidance.
    pub fix: String,
    /// Optional authored external reference.
    pub link: Option<String>,
}

/// One owned frequent-crash or solution rule used to construct the analyzer.
#[derive(Clone)]
#[napi(object)]
pub struct JsModSolutionRule {
    /// Stable YAML-authored entry identifier.
    pub id: String,
    /// Whether any or all criteria must match.
    pub criteria_kind: JsModGuidanceCriteriaKind,
    /// Plugin-name substrings evaluated by the configured strategy.
    pub criteria: Vec<String>,
    /// Plugin-name substrings that suppress an otherwise matched rule.
    pub exceptions: Vec<String>,
    /// Authored display name.
    pub name: String,
    /// Authored guidance body.
    pub description: String,
}

/// One owned important-mod rule used to construct the analyzer.
#[derive(Clone)]
#[napi(object)]
pub struct JsImportantModRule {
    /// Detection token matched against plugin and XSE module names.
    pub detect: String,
    /// Authored display name.
    pub name: String,
    /// Authored recommendation text.
    pub description: String,
    /// Optional authored GPU affinity.
    pub gpu: Option<String>,
    /// Optional authored warning for an installed GPU mismatch.
    pub gpu_mismatch_warning: Option<String>,
    /// Optional plugin names where any installed entry suppresses this rule.
    pub exclude_when_plugin_any: Option<Vec<String>>,
}

/// One ordered installed-plugin fact supplied for semantic analysis.
#[derive(Clone)]
#[napi(object)]
pub struct JsModGuidancePlugin {
    /// Installed plugin filename.
    pub name: String,
    /// Load-order identifier associated with the plugin.
    pub id: String,
}

/// Owned input for one aggregate Mod Guidance analysis call.
#[derive(Clone)]
#[napi(object)]
pub struct JsModGuidanceAnalysisInput {
    /// Installed plugins in load order.
    pub plugins: Vec<JsModGuidancePlugin>,
    /// Detected GPU vendor, when available.
    pub user_gpu: Option<String>,
    /// Installed XSE module filenames.
    pub xse_modules: Vec<String>,
}

/// One matched YAML-authored mod conflict.
#[derive(Clone)]
#[napi(object)]
pub struct JsModConflictGuidance {
    /// Explicit semantic match state.
    pub state: JsModGuidanceMatchState,
    /// Matcher identity for the first mod.
    pub mod_a: String,
    /// Matcher identity for the second mod.
    pub mod_b: String,
    /// Authored display name for the first mod.
    pub name_a: String,
    /// Authored display name for the second mod.
    pub name_b: String,
    /// Authored explanation of the conflict.
    pub description: String,
    /// Authored remediation guidance.
    pub fix: String,
    /// Optional authored external reference.
    pub link: Option<String>,
}

/// One matched frequent-crash or solution guidance entry.
#[derive(Clone)]
#[napi(object)]
pub struct JsModSolutionGuidance {
    /// Explicit semantic match state.
    pub state: JsModGuidanceMatchState,
    /// Stable YAML-authored entry identifier.
    pub id: String,
    /// Authored display name.
    pub name: String,
    /// Authored guidance body.
    pub description: String,
    /// Load-order identifiers whose plugins satisfied the criteria.
    pub matched_plugin_ids: Vec<String>,
}

/// One applicable important-mod result.
#[derive(Clone)]
#[napi(object)]
pub struct JsImportantModGuidance {
    /// Installed, missing, or GPU-mismatched state.
    pub state: JsModGuidanceMatchState,
    /// YAML-authored detection token retained as semantic identity.
    pub detect: String,
    /// Authored display name.
    pub name: String,
    /// Authored recommendation text.
    pub description: String,
    /// Optional authored GPU affinity.
    pub gpu: Option<String>,
    /// Optional authored warning for an installed GPU mismatch.
    pub gpu_mismatch_warning: Option<String>,
}

/// Completed aggregate Mod Guidance analysis, including explicit empty success.
#[derive(Clone)]
#[napi(object)]
pub struct JsModGuidanceAnalysisResult {
    /// Matched conflicts in configuration order.
    pub conflicts: Vec<JsModConflictGuidance>,
    /// Matched frequent-crash guidance in configuration order.
    pub frequent_crashes: Vec<JsModSolutionGuidance>,
    /// Matched solution guidance in configuration order.
    pub solutions: Vec<JsModSolutionGuidance>,
    /// Applicable important-mod states in configuration order.
    pub important_mods: Vec<JsImportantModGuidance>,
}

/// Immutable Node handle over validated aggregate Mod Guidance configuration.
#[derive(Debug)]
#[napi]
pub struct ModGuidanceAnalyzer {
    inner: CoreModGuidanceAnalyzer,
}

#[napi]
impl ModGuidanceAnalyzer {
    /// Validates and compiles all four owned Mod Guidance rule families.
    ///
    /// @throws An error with stable `analyzerKind`, `code`, and `message` fields.
    #[napi(constructor)]
    pub fn new(
        env: Env,
        conflicts: Vec<JsModConflictRule>,
        frequent_crashes: Vec<JsModSolutionRule>,
        solutions: Vec<JsModSolutionRule>,
        important_mods: Vec<JsImportantModRule>,
    ) -> napi::Result<Self> {
        build_analyzer(conflicts, frequent_crashes, solutions, important_mods)
            .map_err(|error| analyzer_error_to_napi(env, error))
    }

    /// Returns the stable focused-analyzer identity for this handle.
    #[napi(getter)]
    pub fn kind(&self) -> JsAnalyzerKind {
        JsAnalyzerKind::ModGuidance
    }

    /// Evaluates conflict, frequent-crash, solution, and important-mod guidance.
    ///
    /// @returns Typed semantic results, including four explicit empty arrays on no match.
    /// @throws An error with stable `analyzerKind`, `code`, and `message` fields.
    #[napi]
    pub fn analyze(
        &self,
        env: Env,
        input: JsModGuidanceAnalysisInput,
    ) -> napi::Result<JsModGuidanceAnalysisResult> {
        self.analyze_owned(input)
            .map_err(|error| analyzer_error_to_napi(env, error))
    }
}

impl ModGuidanceAnalyzer {
    /// Runs the mechanical carrier projection without requiring a JavaScript environment.
    fn analyze_owned(
        &self,
        input: JsModGuidanceAnalysisInput,
    ) -> Result<JsModGuidanceAnalysisResult, AnalyzerError> {
        self.inner
            .analyze(ModGuidanceAnalysisInput {
                plugins: input
                    .plugins
                    .into_iter()
                    .map(|plugin| (plugin.name, plugin.id))
                    .collect::<IndexMap<_, _>>(),
                user_gpu: input.user_gpu,
                xse_modules: input.xse_modules.into_iter().collect::<HashSet<_>>(),
            })
            .map(result_to_js)
    }
}

/// Converts Node rule objects to core-owned domain rules and validates them in core.
fn build_analyzer(
    conflicts: Vec<JsModConflictRule>,
    frequent_crashes: Vec<JsModSolutionRule>,
    solutions: Vec<JsModSolutionRule>,
    important_mods: Vec<JsImportantModRule>,
) -> Result<ModGuidanceAnalyzer, AnalyzerError> {
    CoreModGuidanceAnalyzer::new(
        conflicts.into_iter().map(conflict_to_core).collect(),
        frequent_crashes.into_iter().map(solution_to_core).collect(),
        solutions.into_iter().map(solution_to_core).collect(),
        important_mods
            .into_iter()
            .map(important_mod_to_core)
            .collect(),
    )
    .map(|inner| ModGuidanceAnalyzer { inner })
}

/// Projects one owned conflict rule into the core configuration type.
fn conflict_to_core(rule: JsModConflictRule) -> ModConflictEntry {
    ModConflictEntry {
        mod_a: rule.mod_a,
        mod_b: rule.mod_b,
        name_a: rule.name_a,
        name_b: rule.name_b,
        description: rule.description,
        fix: rule.fix,
        link: rule.link,
    }
}

/// Projects one owned solution rule into the core configuration type.
fn solution_to_core(rule: JsModSolutionRule) -> ModSolutionEntry {
    let criteria = match rule.criteria_kind {
        JsModGuidanceCriteriaKind::Any => ModSolutionCriteria::Any(rule.criteria),
        JsModGuidanceCriteriaKind::All => ModSolutionCriteria::All(rule.criteria),
    };
    ModSolutionEntry {
        id: rule.id,
        criteria,
        exceptions: rule.exceptions,
        name: rule.name,
        description: rule.description,
    }
}

/// Projects one owned important-mod rule into the core configuration type.
fn important_mod_to_core(rule: JsImportantModRule) -> CoreModEntry {
    CoreModEntry {
        detect: rule.detect,
        name: rule.name,
        description: rule.description,
        gpu: rule.gpu,
        gpu_mismatch_warning: rule.gpu_mismatch_warning,
        exclude_when: rule.exclude_when_plugin_any.map(CoreModExclude::PluginAny),
    }
}

/// Projects the core semantic result mechanically without adding presentation data.
fn result_to_js(result: ModGuidanceAnalysisResult) -> JsModGuidanceAnalysisResult {
    JsModGuidanceAnalysisResult {
        conflicts: result
            .conflicts
            .into_iter()
            .map(conflict_result_to_js)
            .collect(),
        frequent_crashes: result
            .frequent_crashes
            .into_iter()
            .map(solution_result_to_js)
            .collect(),
        solutions: result
            .solutions
            .into_iter()
            .map(solution_result_to_js)
            .collect(),
        important_mods: result
            .important_mods
            .into_iter()
            .map(important_mod_result_to_js)
            .collect(),
    }
}

/// Projects one core conflict result without adding presentation fields.
fn conflict_result_to_js(result: CoreModConflictGuidance) -> JsModConflictGuidance {
    JsModConflictGuidance {
        state: result.state.into(),
        mod_a: result.mod_a,
        mod_b: result.mod_b,
        name_a: result.name_a,
        name_b: result.name_b,
        description: result.description,
        fix: result.fix,
        link: result.link,
    }
}

/// Projects one core solution result without adding presentation fields.
fn solution_result_to_js(result: CoreModSolutionGuidance) -> JsModSolutionGuidance {
    JsModSolutionGuidance {
        state: result.state.into(),
        id: result.id,
        name: result.name,
        description: result.description,
        matched_plugin_ids: result.matched_plugin_ids,
    }
}

/// Projects one core important-mod result without adding presentation fields.
fn important_mod_result_to_js(result: CoreImportantModGuidance) -> JsImportantModGuidance {
    JsImportantModGuidance {
        state: result.state.into(),
        detect: result.detect,
        name: result.name,
        description: result.description,
        gpu: result.gpu,
        gpu_mismatch_warning: result.gpu_mismatch_warning,
    }
}

#[cfg(test)]
#[path = "mod_guidance_analyzer_tests.rs"]
mod tests;
