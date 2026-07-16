//! Node projection of the focused semantic Crashgen Settings Analyzer.

use std::collections::HashSet;

use classic_config_core::{
    AutoscanReportPlacement, ConfigLayout, CrashgenSettingsSnapshot, OutcomeKind, RuleSeverity,
};
use classic_scanlog_core::{
    AnalyzerError, CrashgenEntry, CrashgenSettingsAnalysisInput, CrashgenSettingsAnalysisResult,
    CrashgenSettingsAnalyzer as CoreCrashgenSettingsAnalyzer,
};
use napi::bindgen_prelude::{JsObjectValue, ToNapiValue};
use napi::{Env, JsError, JsValue};

use crate::crashgen_rules::{JsCrashgenRegistryEntry, parse_js_rules_to_core};

/// Focused semantic analyzer identity shared across language bindings.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsAnalyzerKind {
    /// Crashgen Expectations and Disabled Setting Notices.
    #[napi(value = "crashgen_settings")]
    CrashgenSettings,
    /// Known crash messages, stack patterns, and DLL involvement.
    #[napi(value = "crash_suspect")]
    CrashSuspect,
    /// Conflict, frequent-crash, solution, and important-mod guidance.
    #[napi(value = "mod_guidance")]
    ModGuidance,
    /// Plugin identity and occurrence evidence.
    #[napi(value = "plugin_evidence")]
    PluginEvidence,
    /// Resolved and unresolved FormID evidence.
    #[napi(value = "formid_finding")]
    FormIdFinding,
    /// Authored named-record evidence.
    #[napi(value = "named_record_finding")]
    NamedRecordFinding,
}

/// Detected layout of the analyzed Crashgen configuration.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsCrashgenConfigLayout {
    /// Buffout 4 OG layout (`Buffout4/config.toml`).
    #[napi(value = "og")]
    Og,
    /// VR layout (`Buffout4.toml`).
    #[napi(value = "vr")]
    Vr,
    /// Layout could not be determined.
    #[napi(value = "unknown")]
    Unknown,
}

/// Semantic category of one Crashgen Expectation Outcome.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsCrashgenExpectationOutcomeKind {
    /// Informational or compatibility notice.
    #[napi(value = "notice")]
    Notice,
    /// Failed expectation.
    #[napi(value = "issue")]
    Issue,
    /// Successful expectation with authored pass guidance.
    #[napi(value = "success")]
    Success,
}

/// Authored severity retained from a Crashgen Expectation.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsCrashgenExpectationSeverity {
    /// Informational guidance.
    #[napi(value = "info")]
    Info,
    /// Warning guidance.
    #[napi(value = "warning")]
    Warning,
    /// Error guidance.
    #[napi(value = "error")]
    Error,
}

/// YAML-owned Autoscan Report destination for one expectation outcome.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsAutoscanReportPlacement {
    /// Settings-related destination.
    #[napi(value = "settings")]
    Settings,
    /// Promoted destination inside Error Information.
    #[napi(value = "error_information")]
    ErrorInformation,
}

/// One owned final Crashgen setting supplied for semantic analysis.
#[derive(Clone)]
#[napi(object)]
pub struct JsCrashgenSetting {
    /// Section containing the setting, or `undefined` for an unscoped setting.
    pub section: Option<String>,
    /// Exact setting key after caller-side parsing.
    pub key: String,
    /// Final setting value represented as text.
    pub value: String,
}

/// Parsed Crashgen version used by version predicates.
#[derive(Clone)]
#[napi(object)]
pub struct JsCrashgenVersion {
    /// Major version component.
    pub major: u32,
    /// Minor version component.
    pub minor: u32,
    /// Patch version component.
    pub patch: u32,
}

/// Owned input for one aggregate Crashgen Settings Analysis call.
#[derive(Clone)]
#[napi(object)]
pub struct JsCrashgenSettingsAnalysisInput {
    /// Final scoped and unscoped settings for one Crash Log.
    pub settings: Vec<JsCrashgenSetting>,
    /// Installed XSE plugin module names used by expectation predicates.
    pub installed_plugins: Vec<String>,
    /// Parsed Crashgen version, when available.
    pub crashgen_version: Option<JsCrashgenVersion>,
    /// Detected Crashgen configuration layout.
    pub config_layout: JsCrashgenConfigLayout,
}

/// One typed, unrendered result from a YAML-authored Crashgen Expectation.
#[derive(Clone)]
#[napi(object)]
pub struct JsCrashgenExpectationOutcome {
    /// Stable identifier authored for the originating rule.
    pub rule_id: String,
    /// Semantic outcome category.
    pub kind: JsCrashgenExpectationOutcomeKind,
    /// Authored severity.
    pub severity: JsCrashgenExpectationSeverity,
    /// Authored and template-expanded message without report markup.
    pub message: String,
    /// Optional authored and template-expanded fix without report markup.
    pub fix: Option<String>,
    /// YAML-owned destination used later by Autoscan Report Assembly.
    pub placement: JsAutoscanReportPlacement,
    /// Target section for setting checks, when applicable.
    pub section: Option<String>,
    /// Target setting key for setting checks, when applicable.
    pub setting: Option<String>,
    /// Expected setting value for setting checks, when applicable.
    pub expected: Option<String>,
    /// Actual setting value for setting checks, when applicable.
    pub actual: Option<String>,
}

/// Universal notice for one non-ignored disabled Crashgen setting.
#[derive(Clone)]
#[napi(object)]
pub struct JsDisabledSettingNotice {
    /// Disabled setting key exactly as retained by the settings snapshot.
    pub setting_name: String,
}

/// Completed Crashgen Settings Analysis, including explicit empty success arrays.
#[derive(Clone)]
#[napi(object)]
pub struct JsCrashgenSettingsAnalysisResult {
    /// YAML-backed Crashgen Expectation Outcomes in evaluator order.
    pub expectation_outcomes: Vec<JsCrashgenExpectationOutcome>,
    /// Universal Disabled Setting Notices kept separate from expectations.
    pub disabled_setting_notices: Vec<JsDisabledSettingNotice>,
}

/// Immutable Node handle over validated, compiled Crashgen Settings configuration.
///
/// Construction and analysis failures throw errors whose `analyzerKind`,
/// `code`, and `message` preserve the complete shared core error contract.
#[derive(Debug)]
#[napi]
pub struct CrashgenSettingsAnalyzer {
    inner: CoreCrashgenSettingsAnalyzer,
}

#[napi]
impl CrashgenSettingsAnalyzer {
    /// Validates and compiles one Crashgen registry entry into an immutable analyzer.
    ///
    /// @param crashgenName Display name used by authored message templates.
    /// @param entry Owned registry entry containing ignore keys and expectations.
    /// @throws An error with stable `analyzerKind`, `code`, and `message` fields.
    #[napi(constructor)]
    pub fn new(
        env: Env,
        crashgen_name: String,
        entry: JsCrashgenRegistryEntry,
    ) -> napi::Result<Self> {
        build_analyzer(crashgen_name, entry).map_err(|error| analyzer_error_to_napi(env, error))
    }

    /// Returns the stable focused-analyzer identity for this handle.
    #[napi(getter)]
    pub fn kind(&self) -> JsAnalyzerKind {
        JsAnalyzerKind::CrashgenSettings
    }

    /// Runs aggregate semantic analysis over one owned Crash Log input.
    ///
    /// A successful call always returns a result object, including when both
    /// arrays are empty. The result contains no rendered report lines.
    ///
    /// @param input Owned settings, plugin, version, and layout facts.
    /// @returns Typed expectation outcomes and separate disabled-setting notices.
    /// @throws An error with stable `analyzerKind`, `code`, and `message` fields.
    #[napi]
    pub fn analyze(
        &self,
        env: Env,
        input: JsCrashgenSettingsAnalysisInput,
    ) -> napi::Result<JsCrashgenSettingsAnalysisResult> {
        self.analyze_owned(input)
            .map_err(|error| analyzer_error_to_napi(env, error))
    }
}

impl CrashgenSettingsAnalyzer {
    /// Runs the carrier projection without requiring a JavaScript environment.
    fn analyze_owned(
        &self,
        input: JsCrashgenSettingsAnalysisInput,
    ) -> Result<JsCrashgenSettingsAnalysisResult, AnalyzerError> {
        self.inner.analyze(input_to_core(input)).map(result_to_js)
    }
}

/// Builds the immutable adapter before JavaScript-specific error projection.
fn build_analyzer(
    crashgen_name: String,
    entry: JsCrashgenRegistryEntry,
) -> Result<CrashgenSettingsAnalyzer, AnalyzerError> {
    let parsed_rules = parse_js_rules_to_core(entry.settings_rules, entry.settings_rules_version);
    let core_entry = CrashgenEntry {
        display_section: entry.display_section,
        ignore_keys: entry.ignore_keys.into_iter().collect(),
        settings_rules: parsed_rules.rules,
    };
    CoreCrashgenSettingsAnalyzer::from_parsed_configuration(
        crashgen_name,
        core_entry,
        parsed_rules.diagnostics,
    )
    .map(|inner| CrashgenSettingsAnalyzer { inner })
}

/// Converts the owned Node input into the equally owned core aggregate input.
fn input_to_core(input: JsCrashgenSettingsAnalysisInput) -> CrashgenSettingsAnalysisInput {
    let mut settings = CrashgenSettingsSnapshot::new();
    for setting in input.settings {
        match setting.section {
            Some(section) => settings.insert(&section, &setting.key, setting.value),
            None => settings.insert_unscoped(&setting.key, setting.value),
        }
    }

    CrashgenSettingsAnalysisInput {
        settings,
        installed_plugins: input.installed_plugins.into_iter().collect::<HashSet<_>>(),
        crashgen_version: input
            .crashgen_version
            .map(|version| (version.major, version.minor, version.patch)),
        config_layout: config_layout_to_core(input.config_layout),
    }
}

/// Projects the core semantic result mechanically without adding presentation data.
fn result_to_js(result: CrashgenSettingsAnalysisResult) -> JsCrashgenSettingsAnalysisResult {
    JsCrashgenSettingsAnalysisResult {
        expectation_outcomes: result
            .expectation_outcomes
            .into_iter()
            .map(|outcome| JsCrashgenExpectationOutcome {
                rule_id: outcome.rule_id,
                kind: outcome_kind_to_js(outcome.kind),
                severity: severity_to_js(outcome.severity),
                message: outcome.message,
                fix: outcome.fix,
                placement: placement_to_js(outcome.placement),
                section: outcome.section,
                setting: outcome.setting,
                expected: outcome.expected,
                actual: outcome.actual,
            })
            .collect(),
        disabled_setting_notices: result
            .disabled_setting_notices
            .into_iter()
            .map(|notice| JsDisabledSettingNotice {
                setting_name: notice.setting_name,
            })
            .collect(),
    }
}

/// Converts the Node string enum into the core layout value.
fn config_layout_to_core(layout: JsCrashgenConfigLayout) -> ConfigLayout {
    match layout {
        JsCrashgenConfigLayout::Og => ConfigLayout::Og,
        JsCrashgenConfigLayout::Vr => ConfigLayout::Vr,
        JsCrashgenConfigLayout::Unknown => ConfigLayout::Unknown,
    }
}

/// Converts a core semantic outcome category into its stable Node string enum.
fn outcome_kind_to_js(kind: OutcomeKind) -> JsCrashgenExpectationOutcomeKind {
    match kind {
        OutcomeKind::Notice => JsCrashgenExpectationOutcomeKind::Notice,
        OutcomeKind::Issue => JsCrashgenExpectationOutcomeKind::Issue,
        OutcomeKind::Success => JsCrashgenExpectationOutcomeKind::Success,
    }
}

/// Converts authored core severity into its stable Node string enum.
fn severity_to_js(severity: RuleSeverity) -> JsCrashgenExpectationSeverity {
    match severity {
        RuleSeverity::Info => JsCrashgenExpectationSeverity::Info,
        RuleSeverity::Warning => JsCrashgenExpectationSeverity::Warning,
        RuleSeverity::Error => JsCrashgenExpectationSeverity::Error,
    }
}

/// Converts YAML-owned placement into its canonical Node string enum token.
fn placement_to_js(placement: AutoscanReportPlacement) -> JsAutoscanReportPlacement {
    match placement {
        AutoscanReportPlacement::Settings => JsAutoscanReportPlacement::Settings,
        AutoscanReportPlacement::ErrorInformation => JsAutoscanReportPlacement::ErrorInformation,
    }
}

/// Preserves the complete shared kind, code, and message in a Node error.
pub(crate) fn analyzer_error_to_napi(env: Env, error: AnalyzerError) -> napi::Error {
    let analyzer_kind = error.analyzer().as_str();
    let code = error.code().as_str().to_string();
    let message = error.message().to_string();
    let raw_error =
        JsError::from(napi::Error::new(code.clone(), message.clone())).into_unknown(env);

    match raw_error.coerce_to_object() {
        Ok(mut object) => match object.set_named_property("analyzerKind", analyzer_kind) {
            Ok(()) => object
                .into_unknown(&env)
                .map(napi::Error::from)
                .unwrap_or_else(|_| base_napi_error(env, code, message)),
            Err(_) => base_napi_error(env, code, message),
        },
        Err(_) => base_napi_error(env, code, message),
    }
}

/// Rebuilds the ordinary code/message error if attaching the kind property fails.
fn base_napi_error(env: Env, code: String, message: String) -> napi::Error {
    napi::Error::from(JsError::from(napi::Error::new(code, message)).into_unknown(env))
}

#[cfg(test)]
#[path = "crashgen_settings_analyzer_tests.rs"]
mod tests;
