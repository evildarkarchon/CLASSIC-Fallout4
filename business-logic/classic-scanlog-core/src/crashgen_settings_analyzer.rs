//! Semantic Crashgen Settings Analysis.

use std::collections::HashSet;
use std::sync::Arc;

use classic_config_core::{
    AutoscanReportPlacement, ConfigLayout, CrashgenExpectationParseDiagnostic,
    CrashgenSettingsRules, CrashgenSettingsSnapshot, EvaluationContext, ExpectedValue, OutcomeKind,
    Predicate, RuleSeverity, TargetValueType, evaluate_rules,
};

use crate::analyzer::{AnalyzerError, AnalyzerErrorCode, AnalyzerKind, AnalyzerResult};
use crate::crashgen_registry::CrashgenEntry;

/// Owned facts consumed by one Crashgen Settings Analysis call.
#[derive(Clone, Debug)]
pub struct CrashgenSettingsAnalysisInput {
    /// Final section-aware crashgen settings for the Crash Log.
    pub settings: CrashgenSettingsSnapshot,
    /// Installed XSE plugin module names for expectation predicates.
    pub installed_plugins: HashSet<String>,
    /// Parsed crashgen version, when available.
    pub crashgen_version: Option<(u32, u32, u32)>,
    /// Detected crashgen configuration layout.
    pub config_layout: ConfigLayout,
}

impl Default for CrashgenSettingsAnalysisInput {
    fn default() -> Self {
        Self {
            settings: CrashgenSettingsSnapshot::default(),
            installed_plugins: HashSet::default(),
            crashgen_version: None,
            config_layout: ConfigLayout::Unknown,
        }
    }
}

/// One typed result from evaluating a YAML-owned Crashgen Expectation.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CrashgenExpectationOutcome {
    /// Stable identifier authored for the originating rule.
    pub rule_id: String,
    /// Semantic outcome category.
    pub kind: OutcomeKind,
    /// Authored severity.
    pub severity: RuleSeverity,
    /// Authored and template-expanded message without report markup.
    pub message: String,
    /// Optional authored and template-expanded fix without report markup.
    pub fix: Option<String>,
    /// YAML-owned destination used later by Autoscan Report Assembly.
    pub placement: AutoscanReportPlacement,
    /// Target section for setting checks, when applicable.
    pub section: Option<String>,
    /// Target setting key for setting checks, when applicable.
    pub setting: Option<String>,
    /// Expected setting value for setting checks, when applicable.
    pub expected: Option<String>,
    /// Actual setting value for setting checks, when applicable.
    pub actual: Option<String>,
}

/// Universal notice for one non-ignored disabled crashgen setting.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DisabledSettingNotice {
    /// Disabled setting key exactly as retained by the settings snapshot.
    pub setting_name: String,
}

/// Completed Crashgen Settings Analysis, including an explicit empty success.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct CrashgenSettingsAnalysisResult {
    /// YAML-backed Crashgen Expectation outcomes in evaluator order.
    pub expectation_outcomes: Vec<CrashgenExpectationOutcome>,
    /// Universal Disabled Setting Notices kept separate from expectations.
    pub disabled_setting_notices: Vec<DisabledSettingNotice>,
}

#[derive(Debug)]
struct CompiledConfiguration {
    crashgen_name: String,
    display_section: String,
    ignore_keys: HashSet<String>,
    rules: Option<CrashgenSettingsRules>,
}

/// Immutable Crashgen Settings Analyzer with validated, compiled configuration.
///
/// Clones share the same immutable configuration and can analyze independent
/// owned inputs concurrently without sharing per-call state.
#[derive(Clone, Debug)]
pub struct CrashgenSettingsAnalyzer {
    configuration: Arc<CompiledConfiguration>,
}

impl CrashgenSettingsAnalyzer {
    /// Validates and compiles one crashgen registry entry into an immutable analyzer.
    ///
    /// Unsupported rule versions, empty rule identifiers, duplicate identifiers,
    /// invalid targets, and mismatched expected-value types are rejected before
    /// any Crash Log is analyzed.
    pub fn new(crashgen_name: String, entry: CrashgenEntry) -> AnalyzerResult<Self> {
        Self::from_parsed_configuration(crashgen_name, entry, Vec::new())
    }

    /// Constructs an analyzer from carrier-neutral parser output and rejects diagnostics.
    ///
    /// Binding adapters use this constructor after converting their local input
    /// carrier through `classic_config_core::parse_crashgen_expectations`. This
    /// keeps strict analyzer-construction policy and its error text in Rust core
    /// while the general configuration parser remains intentionally tolerant.
    pub fn from_parsed_configuration(
        crashgen_name: String,
        entry: CrashgenEntry,
        diagnostics: Vec<CrashgenExpectationParseDiagnostic>,
    ) -> AnalyzerResult<Self> {
        if !diagnostics.is_empty() {
            let details = diagnostics
                .into_iter()
                .map(|diagnostic| format!("{}: {}", diagnostic.path, diagnostic.message))
                .collect::<Vec<_>>()
                .join("; ");
            return Err(invalid_configuration(format!(
                "Crashgen Expectations configuration is invalid: {details}"
            )));
        }
        if crashgen_name.trim().is_empty() {
            return Err(invalid_configuration(
                "crashgen name must not be empty".to_string(),
            ));
        }

        let rules = entry
            .settings_rules
            .map(validate_and_compile_rules)
            .transpose()?;
        Ok(Self {
            configuration: Arc::new(CompiledConfiguration {
                crashgen_name,
                display_section: entry.display_section,
                ignore_keys: entry.ignore_keys,
                rules,
            }),
        })
    }

    /// Evaluates all configured expectations and the universal disabled-setting pass.
    ///
    /// A successful call always returns a result value. When no rule or disabled
    /// setting matches, both result collections are empty.
    pub fn analyze(
        &self,
        mut input: CrashgenSettingsAnalysisInput,
    ) -> AnalyzerResult<CrashgenSettingsAnalysisResult> {
        input.installed_plugins = input
            .installed_plugins
            .into_iter()
            .map(|plugin| plugin.trim().to_lowercase())
            .collect();

        let expectation_outcomes = self
            .configuration
            .rules
            .as_ref()
            .map(|rules| {
                let context = EvaluationContext {
                    crashgen_name: self.configuration.crashgen_name.clone(),
                    display_section: self.configuration.display_section.clone(),
                    installed_plugins: input.installed_plugins,
                    settings: input.settings.clone(),
                    config_layout: input.config_layout,
                    crashgen_version: input.crashgen_version,
                };
                evaluate_rules(rules, &context)
                    .outcomes
                    .into_iter()
                    .map(|outcome| CrashgenExpectationOutcome {
                        rule_id: outcome.id,
                        kind: outcome.kind,
                        severity: outcome.severity,
                        message: outcome.message,
                        fix: outcome.fix,
                        placement: outcome.bucket,
                        section: outcome.section,
                        setting: outcome.setting,
                        expected: outcome.expected,
                        actual: outcome.actual,
                    })
                    .collect()
            })
            .unwrap_or_default();

        let disabled_setting_notices = input
            .settings
            .final_settings()
            .filter(|setting| {
                setting.value.parse::<bool>() == Ok(false)
                    && !self.configuration.ignore_keys.contains(setting.key)
            })
            .map(|setting| DisabledSettingNotice {
                setting_name: setting.key.to_string(),
            })
            .collect();

        Ok(CrashgenSettingsAnalysisResult {
            expectation_outcomes,
            disabled_setting_notices,
        })
    }
}

fn validate_and_compile_rules(
    mut rules: CrashgenSettingsRules,
) -> AnalyzerResult<CrashgenSettingsRules> {
    if rules.version != 1 {
        return Err(AnalyzerError::new(
            AnalyzerKind::CrashgenSettings,
            AnalyzerErrorCode::UnsupportedConfigurationVersion,
            format!(
                "unsupported Crashgen Expectations version {}",
                rules.version
            ),
        ));
    }

    let mut rule_ids = HashSet::new();
    for rule in &mut rules.preflight {
        validate_rule_id(&rule.id, &mut rule_ids)?;
        if rule.action.message.trim().is_empty() {
            return Err(invalid_configuration(format!(
                "Crashgen Expectation '{}' has an empty message",
                rule.id
            )));
        }
        compile_predicate(&mut rule.when, &rule.id)?;
    }

    for rule in &mut rules.checks {
        validate_rule_id(&rule.id, &mut rule_ids)?;
        if rule.target.section.trim().is_empty() || rule.target.key.trim().is_empty() {
            return Err(invalid_configuration(format!(
                "Crashgen Expectation '{}' has an empty setting target",
                rule.id
            )));
        }
        if rule.messages.fail.trim().is_empty() {
            return Err(invalid_configuration(format!(
                "Crashgen Expectation '{}' has an empty failure message",
                rule.id
            )));
        }
        if !expected_value_matches_type(&rule.expect, rule.target.value_type) {
            return Err(invalid_configuration(format!(
                "Crashgen Expectation '{}' has an expected value incompatible with its target type",
                rule.id
            )));
        }
        compile_predicate(&mut rule.when, &rule.id)?;
    }

    Ok(rules)
}

fn validate_rule_id(id: &str, seen: &mut HashSet<String>) -> AnalyzerResult<()> {
    let id = id.trim();
    if id.is_empty() {
        return Err(invalid_configuration(
            "Crashgen Expectation rule id must not be empty".to_string(),
        ));
    }
    if !seen.insert(id.to_string()) {
        return Err(invalid_configuration(format!(
            "duplicate Crashgen Expectation rule id '{id}'"
        )));
    }
    Ok(())
}

fn compile_predicate(predicate: &mut Predicate, rule_id: &str) -> AnalyzerResult<()> {
    match predicate {
        Predicate::PluginAny(plugins) => {
            if plugins.is_empty() || plugins.iter().any(|plugin| plugin.trim().is_empty()) {
                return Err(invalid_configuration(format!(
                    "Crashgen Expectation '{rule_id}' has an empty plugin matcher"
                )));
            }
            for plugin in plugins {
                *plugin = plugin.trim().to_lowercase();
            }
        }
        Predicate::All(items) | Predicate::Any(items) => {
            if items.is_empty() {
                return Err(invalid_configuration(format!(
                    "Crashgen Expectation '{rule_id}' has an empty predicate group"
                )));
            }
            for item in items {
                compile_predicate(item, rule_id)?;
            }
        }
        Predicate::Not(item) => compile_predicate(item, rule_id)?,
        Predicate::Always | Predicate::ConfigLayoutIs(_) | Predicate::CrashgenVersionLt(_) => {}
    }
    Ok(())
}

fn expected_value_matches_type(expected: &ExpectedValue, value_type: TargetValueType) -> bool {
    matches!(
        (expected, value_type),
        (ExpectedValue::Bool(_), TargetValueType::Bool)
            | (ExpectedValue::Int(_), TargetValueType::Int)
            | (ExpectedValue::String(_), TargetValueType::String)
    )
}

fn invalid_configuration(message: String) -> AnalyzerError {
    AnalyzerError::new(
        AnalyzerKind::CrashgenSettings,
        AnalyzerErrorCode::InvalidConfiguration,
        message,
    )
}

#[cfg(test)]
#[path = "crashgen_settings_analyzer_tests.rs"]
mod tests;
