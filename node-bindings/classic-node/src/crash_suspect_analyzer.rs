//! Node projection of the focused semantic Crash Suspect Analyzer.

use classic_config_core::{SuspectErrorRule, SuspectStackCountRule, SuspectStackRule};
use classic_scanlog_core::{
    AnalyzerError, CrashSuspectAnalysisInput, CrashSuspectAnalysisResult,
    CrashSuspectAnalyzer as CoreCrashSuspectAnalyzer,
    CrashSuspectFinding as CoreCrashSuspectFinding,
    CrashSuspectFindingKind as CoreCrashSuspectFindingKind,
};
use napi::Env;

use crate::crashgen_settings_analyzer::{JsAnalyzerKind, analyzer_error_to_napi};

/// Evidence source that produced one Crash Suspect Finding.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsCrashSuspectFindingKind {
    /// A configured main-error rule matched.
    #[napi(value = "main_error_rule")]
    MainErrorRule,
    /// A configured stack rule matched.
    #[napi(value = "stack_rule")]
    StackRule,
    /// The main error reports DLL involvement.
    #[napi(value = "dll_involvement")]
    DllInvolvement,
}

impl From<CoreCrashSuspectFindingKind> for JsCrashSuspectFindingKind {
    fn from(value: CoreCrashSuspectFindingKind) -> Self {
        match value {
            CoreCrashSuspectFindingKind::MainErrorRule => Self::MainErrorRule,
            CoreCrashSuspectFindingKind::StackRule => Self::StackRule,
            CoreCrashSuspectFindingKind::DllInvolvement => Self::DllInvolvement,
        }
    }
}

/// One minimum-occurrence condition in a Crash Suspect stack rule.
#[derive(Clone)]
#[napi(object)]
pub struct JsCrashSuspectStackCountRule {
    /// Substring counted in the call stack.
    pub substring: String,
    /// Minimum required non-overlapping occurrences.
    pub count: u32,
}

/// One owned main-error rule used to construct the analyzer.
#[derive(Clone)]
#[napi(object)]
pub struct JsCrashSuspectMainErrorRule {
    /// Stable rule identifier.
    pub id: String,
    /// Authored display name.
    pub name: String,
    /// Authored severity used for ordering and presentation.
    pub severity: i32,
    /// Main-error substrings where any match triggers the rule.
    pub main_error_contains_any: Vec<String>,
}

/// One owned stack rule used to construct the analyzer.
#[derive(Clone)]
#[napi(object)]
pub struct JsCrashSuspectStackRule {
    /// Stable rule identifier.
    pub id: String,
    /// Authored display name.
    pub name: String,
    /// Authored severity used for ordering and presentation.
    pub severity: i32,
    /// Main-error substrings where any match is required when configured.
    pub main_error_required_any: Vec<String>,
    /// Optional main-error substrings that can trigger the rule.
    pub main_error_optional_any: Vec<String>,
    /// Stack substrings where any match can trigger the rule.
    pub stack_contains_any: Vec<String>,
    /// Stack substrings that suppress the rule.
    pub exclude_if_stack_contains_any: Vec<String>,
    /// Minimum-occurrence stack conditions.
    pub stack_contains_at_least: Vec<JsCrashSuspectStackCountRule>,
}

/// Owned input for one aggregate Crash Suspect analysis call.
#[derive(Clone)]
#[napi(object)]
pub struct JsCrashSuspectAnalysisInput {
    /// Main error extracted from the Crash Log.
    pub main_error: String,
    /// Complete call-stack evidence.
    pub call_stack: String,
}

/// One semantic Crash Suspect Finding without report presentation fields.
#[derive(Clone)]
#[napi(object)]
pub struct JsCrashSuspectFinding {
    /// Evidence source that produced the finding.
    pub kind: JsCrashSuspectFindingKind,
    /// Stable rule identifier, absent for DLL involvement.
    pub rule_id: Option<String>,
    /// Authored rule name, absent for DLL involvement.
    pub name: Option<String>,
    /// Authored severity, absent for DLL involvement.
    pub severity: Option<i32>,
}

/// Completed Crash Suspect analysis, including explicit empty success.
#[derive(Clone)]
#[napi(object)]
pub struct JsCrashSuspectAnalysisResult {
    /// Individual semantic findings in rule-configuration order.
    pub findings: Vec<JsCrashSuspectFinding>,
}

/// Immutable Node handle over validated Crash Suspect matcher configuration.
#[derive(Debug)]
#[napi]
pub struct CrashSuspectAnalyzer {
    inner: CoreCrashSuspectAnalyzer,
}

#[napi]
impl CrashSuspectAnalyzer {
    /// Validates and compiles owned Crash Suspect rules into an immutable analyzer.
    ///
    /// @throws An error with stable `analyzerKind`, `code`, and `message` fields.
    #[napi(constructor)]
    pub fn new(
        env: Env,
        main_error_rules: Vec<JsCrashSuspectMainErrorRule>,
        stack_rules: Vec<JsCrashSuspectStackRule>,
    ) -> napi::Result<Self> {
        build_analyzer(main_error_rules, stack_rules)
            .map_err(|error| analyzer_error_to_napi(env, error))
    }

    /// Returns the stable focused-analyzer identity for this handle.
    #[napi(getter)]
    pub fn kind(&self) -> JsAnalyzerKind {
        JsAnalyzerKind::CrashSuspect
    }

    /// Runs one aggregate semantic analysis over owned Crash Log evidence.
    ///
    /// @returns Individual typed findings, including an explicit empty array on no match.
    /// @throws An error with stable `analyzerKind`, `code`, and `message` fields.
    #[napi]
    pub fn analyze(
        &self,
        env: Env,
        input: JsCrashSuspectAnalysisInput,
    ) -> napi::Result<JsCrashSuspectAnalysisResult> {
        self.analyze_owned(input)
            .map_err(|error| analyzer_error_to_napi(env, error))
    }
}

impl CrashSuspectAnalyzer {
    /// Runs the mechanical carrier projection without requiring a JavaScript environment.
    fn analyze_owned(
        &self,
        input: JsCrashSuspectAnalysisInput,
    ) -> Result<JsCrashSuspectAnalysisResult, AnalyzerError> {
        self.inner
            .analyze(CrashSuspectAnalysisInput {
                main_error: input.main_error,
                call_stack: input.call_stack,
            })
            .map(result_to_js)
    }
}

/// Converts Node rule objects to core-owned domain rules and validates them in core.
fn build_analyzer(
    main_error_rules: Vec<JsCrashSuspectMainErrorRule>,
    stack_rules: Vec<JsCrashSuspectStackRule>,
) -> Result<CrashSuspectAnalyzer, AnalyzerError> {
    CoreCrashSuspectAnalyzer::new(
        main_error_rules
            .into_iter()
            .map(|rule| SuspectErrorRule {
                id: rule.id,
                name: rule.name,
                severity: rule.severity,
                main_error_contains_any: rule.main_error_contains_any,
            })
            .collect(),
        stack_rules
            .into_iter()
            .map(|rule| SuspectStackRule {
                id: rule.id,
                name: rule.name,
                severity: rule.severity,
                main_error_required_any: rule.main_error_required_any,
                main_error_optional_any: rule.main_error_optional_any,
                stack_contains_any: rule.stack_contains_any,
                exclude_if_stack_contains_any: rule.exclude_if_stack_contains_any,
                stack_contains_at_least: rule
                    .stack_contains_at_least
                    .into_iter()
                    .map(|count_rule| SuspectStackCountRule {
                        substring: count_rule.substring,
                        count: count_rule.count as usize,
                    })
                    .collect(),
            })
            .collect(),
    )
    .map(|inner| CrashSuspectAnalyzer { inner })
}

/// Projects the core semantic result mechanically without adding presentation data.
fn result_to_js(result: CrashSuspectAnalysisResult) -> JsCrashSuspectAnalysisResult {
    JsCrashSuspectAnalysisResult {
        findings: result
            .findings
            .into_iter()
            .map(|finding| {
                let kind = finding.kind().into();
                match finding {
                    CoreCrashSuspectFinding::MainErrorRule {
                        rule_id,
                        name,
                        severity,
                    } => JsCrashSuspectFinding {
                        kind,
                        rule_id: Some(rule_id),
                        name: Some(name),
                        severity: Some(severity),
                    },
                    CoreCrashSuspectFinding::StackRule {
                        rule_id,
                        name,
                        severity,
                    } => JsCrashSuspectFinding {
                        kind,
                        rule_id: Some(rule_id),
                        name: Some(name),
                        severity: Some(severity),
                    },
                    CoreCrashSuspectFinding::DllInvolvement => JsCrashSuspectFinding {
                        kind,
                        rule_id: None,
                        name: None,
                        severity: None,
                    },
                }
            })
            .collect(),
    }
}

#[cfg(test)]
#[path = "crash_suspect_analyzer_tests.rs"]
mod tests;
