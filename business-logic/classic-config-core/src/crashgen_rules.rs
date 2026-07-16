//! Shared crashgen settings rule model and evaluator.

use std::collections::{HashMap, HashSet};

/// Rule severity.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RuleSeverity {
    /// Informational message.
    Info,
    /// Warning message.
    Warning,
    /// Error message.
    Error,
}

impl RuleSeverity {
    /// Parse severity from text.
    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_lowercase().as_str() {
            "info" => Some(Self::Info),
            "warning" | "warn" => Some(Self::Warning),
            "error" => Some(Self::Error),
            _ => None,
        }
    }
}

/// Config layout fact used by predicates.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConfigLayout {
    /// Buffout 4 OG layout (`Buffout4/config.toml`).
    Og,
    /// VR layout (`Buffout4.toml`).
    Vr,
    /// Layout could not be determined.
    Unknown,
}

impl ConfigLayout {
    /// Parse config layout from text.
    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_lowercase().as_str() {
            "og" => Some(Self::Og),
            "vr" => Some(Self::Vr),
            "unknown" => Some(Self::Unknown),
            _ => None,
        }
    }
}

/// Value type for a target setting.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TargetValueType {
    /// Boolean setting.
    Bool,
    /// Integer setting.
    Int,
    /// String setting.
    String,
}

impl TargetValueType {
    /// Parse value type from text.
    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_lowercase().as_str() {
            "bool" | "boolean" => Some(Self::Bool),
            "int" | "integer" => Some(Self::Int),
            "string" | "str" => Some(Self::String),
            _ => None,
        }
    }
}

/// Value expected by a check rule.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ExpectedValue {
    /// Expected bool.
    Bool(bool),
    /// Expected int.
    Int(i64),
    /// Expected string.
    String(String),
}

impl ExpectedValue {
    fn as_string(&self) -> String {
        match self {
            Self::Bool(v) => v.to_string(),
            Self::Int(v) => v.to_string(),
            Self::String(v) => v.clone(),
        }
    }
}

/// Rule predicate tree.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub enum Predicate {
    /// Always true.
    #[default]
    Always,
    /// Any plugin in list is present.
    PluginAny(Vec<String>),
    /// Config layout equals a value.
    ConfigLayoutIs(ConfigLayout),
    /// Crashgen version is lower than target version.
    CrashgenVersionLt((u32, u32, u32)),
    /// All predicates must be true.
    All(Vec<Predicate>),
    /// Any predicate must be true.
    Any(Vec<Predicate>),
    /// Negation predicate.
    Not(Box<Predicate>),
}

/// Preflight rule action kind.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PreflightActionKind {
    /// Emit message and skip remaining checks.
    NoticeAndSkipRemaining,
    /// Emit message but continue checks.
    Notice,
    /// Emit issue but continue checks.
    Issue,
}

impl PreflightActionKind {
    /// Parse action kind from text.
    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_lowercase().as_str() {
            "notice_and_skip_remaining" => Some(Self::NoticeAndSkipRemaining),
            "notice" => Some(Self::Notice),
            "issue" => Some(Self::Issue),
            _ => None,
        }
    }
}

/// Autoscan Report placement used to place rendered rule outcomes in a final report.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum AutoscanReportPlacement {
    /// Default settings-related destination.
    #[default]
    Settings,
    /// Promoted placement inside the `Error Information` section.
    ErrorInformation,
}

impl AutoscanReportPlacement {
    /// Parse Autoscan Report placement from text.
    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_lowercase().as_str() {
            "settings" => Some(Self::Settings),
            "error_information" | "errorinformation" => Some(Self::ErrorInformation),
            _ => None,
        }
    }

    /// Canonical YAML / binding string for this placement.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Settings => "settings",
            Self::ErrorInformation => "error_information",
        }
    }
}

/// Deprecated compatibility alias for Autoscan Report placement.
#[deprecated(note = "use AutoscanReportPlacement")]
pub type RuleReportBucket = AutoscanReportPlacement;

/// Preflight action payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PreflightAction {
    /// Action kind.
    pub kind: PreflightActionKind,
    /// Autoscan Report placement for the rendered message.
    ///
    /// Field name is retained as a compatibility name for one transition.
    pub bucket: AutoscanReportPlacement,
    /// Severity.
    pub severity: RuleSeverity,
    /// Message text.
    pub message: String,
    /// Optional fix guidance.
    pub fix: Option<String>,
}

/// Preflight rule.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PreflightRule {
    /// Stable rule id.
    pub id: String,
    /// Predicate deciding whether the action applies.
    pub when: Predicate,
    /// Action to execute.
    pub action: PreflightAction,
}

/// Setting target.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RuleTarget {
    /// TOML section.
    pub section: String,
    /// TOML key.
    pub key: String,
    /// Value type.
    pub value_type: TargetValueType,
}

/// Message templates for check rule outcomes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RuleMessages {
    /// Message for failed expectation.
    pub fail: String,
    /// Optional fix text.
    pub fix: Option<String>,
    /// Optional message for successful expectation.
    pub pass: Option<String>,
}

/// Check rule.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CheckRule {
    /// Stable rule id.
    pub id: String,
    /// Setting target.
    pub target: RuleTarget,
    /// Predicate deciding whether this check runs.
    pub when: Predicate,
    /// Expected setting value.
    pub expect: ExpectedValue,
    /// Message templates.
    pub messages: RuleMessages,
    /// Severity for failed check.
    pub severity: RuleSeverity,
}

/// Full settings rules block.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CrashgenSettingsRules {
    /// Schema version.
    pub version: u32,
    /// Preflight rules.
    pub preflight: Vec<PreflightRule>,
    /// Check rules.
    pub checks: Vec<CheckRule>,
}

/// Evaluation context provided by caller.
#[derive(Debug, Clone)]
pub struct EvaluationContext {
    /// Display crashgen name.
    pub crashgen_name: String,
    /// Display section for templating.
    pub display_section: String,
    /// Installed plugin dll names (lowercase).
    pub installed_plugins: HashSet<String>,
    /// Section-aware crash generator settings.
    pub settings: CrashgenSettingsSnapshot,
    /// Config layout fact.
    pub config_layout: ConfigLayout,
    /// Parsed crashgen version tuple.
    pub crashgen_version: Option<(u32, u32, u32)>,
}

/// Outcome category.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutcomeKind {
    /// Informational/notice event.
    Notice,
    /// Failed check / issue.
    Issue,
    /// Successful check event.
    Success,
}

/// Evaluated outcome.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvaluationOutcome {
    /// Rule id.
    pub id: String,
    /// Outcome kind.
    pub kind: OutcomeKind,
    /// Autoscan Report placement for the rendered message.
    ///
    /// Field name is retained as a compatibility name for one transition.
    pub bucket: AutoscanReportPlacement,
    /// Severity.
    pub severity: RuleSeverity,
    /// Rendered message.
    pub message: String,
    /// Optional fix text.
    pub fix: Option<String>,
    /// Optional section for setting-related outcomes.
    pub section: Option<String>,
    /// Optional setting key.
    pub setting: Option<String>,
    /// Optional expected value.
    pub expected: Option<String>,
    /// Optional actual value.
    pub actual: Option<String>,
}

/// Evaluator return payload.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct EvaluationResult {
    /// Emitted outcomes in evaluation order.
    pub outcomes: Vec<EvaluationOutcome>,
    /// Whether a preflight requested skipping remaining checks.
    pub skip_remaining: bool,
}

/// Section-aware crash generator settings used by Crashgen Expectations.
///
/// Lookups normalize section names by trimming whitespace, accepting either
/// `Compatibility` or `[Compatibility]`, and comparing case-insensitively.
/// Setting keys are trimmed at insertion and lookup time but otherwise remain
/// exact and case-sensitive.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CrashgenSettingsSnapshot {
    sections: HashMap<String, HashMap<String, String>>,
    unscoped: HashMap<String, String>,
}

/// Borrowed view of one final crashgen setting in a snapshot.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CrashgenSettingRef<'a> {
    /// Normalized section name, or `None` when the setting appeared before any section.
    pub section: Option<&'a str>,
    /// Trimmed setting key.
    pub key: &'a str,
    /// Setting value.
    pub value: &'a str,
}

impl CrashgenSettingsSnapshot {
    /// Create an empty settings snapshot.
    pub fn new() -> Self {
        Self::default()
    }

    /// Insert or replace a setting in a section.
    ///
    /// Later inserts for the same normalized section and exact key replace
    /// earlier values. An empty section is treated as unscoped.
    pub fn insert(&mut self, section: &str, key: &str, value: impl Into<String>) {
        let normalized_section = normalize_section_name(section);
        if normalized_section.is_empty() {
            self.insert_unscoped(key, value);
            return;
        }

        let key = key.trim();
        if key.is_empty() {
            return;
        }

        self.sections
            .entry(normalized_section)
            .or_default()
            .insert(key.to_string(), value.into());
    }

    /// Insert or replace a setting that appeared before any parsed section.
    pub fn insert_unscoped(&mut self, key: &str, value: impl Into<String>) {
        let key = key.trim();
        if key.is_empty() {
            return;
        }

        self.unscoped.insert(key.to_string(), value.into());
    }

    /// Return the setting value for a section/key target.
    ///
    /// Unscoped settings are never used as a fallback for sectioned lookups.
    pub fn value_for(&self, section: &str, key: &str) -> Option<&str> {
        let normalized_section = normalize_section_name(section);
        if normalized_section.is_empty() {
            return None;
        }

        self.sections
            .get(&normalized_section)?
            .get(key.trim())
            .map(String::as_str)
    }

    /// Return whether the snapshot has no scoped or unscoped settings.
    pub fn is_empty(&self) -> bool {
        self.sections.values().all(HashMap::is_empty) && self.unscoped.is_empty()
    }

    /// Iterate over the final setting values retained by the snapshot.
    pub fn final_settings(&self) -> impl Iterator<Item = CrashgenSettingRef<'_>> {
        self.unscoped
            .iter()
            .map(|(key, value)| CrashgenSettingRef {
                section: None,
                key: key.as_str(),
                value: value.as_str(),
            })
            .chain(self.sections.iter().flat_map(|(section, settings)| {
                settings.iter().map(move |(key, value)| CrashgenSettingRef {
                    section: Some(section.as_str()),
                    key: key.as_str(),
                    value: value.as_str(),
                })
            }))
    }
}

fn normalize_section_name(section: &str) -> String {
    let trimmed = section.trim();
    let unbracketed = trimmed
        .strip_prefix('[')
        .and_then(|value| value.strip_suffix(']'))
        .unwrap_or(trimmed)
        .trim();

    unbracketed.to_lowercase()
}

/// Evaluate all preflight and check rules for a context.
pub fn evaluate_rules(
    rules: &CrashgenSettingsRules,
    context: &EvaluationContext,
) -> EvaluationResult {
    let mut result = EvaluationResult::default();

    for rule in &rules.preflight {
        if evaluate_predicate(&rule.when, context) {
            let message = apply_template(&rule.action.message, context, None);
            let fix = rule
                .action
                .fix
                .as_ref()
                .map(|value| apply_template(value, context, None));

            result.outcomes.push(EvaluationOutcome {
                id: rule.id.clone(),
                kind: match rule.action.kind {
                    PreflightActionKind::Issue => OutcomeKind::Issue,
                    PreflightActionKind::Notice | PreflightActionKind::NoticeAndSkipRemaining => {
                        OutcomeKind::Notice
                    }
                },
                bucket: rule.action.bucket,
                severity: rule.action.severity,
                message,
                fix,
                section: None,
                setting: None,
                expected: None,
                actual: None,
            });

            if rule.action.kind == PreflightActionKind::NoticeAndSkipRemaining {
                result.skip_remaining = true;
                return result;
            }
        }
    }

    for rule in &rules.checks {
        if !evaluate_predicate(&rule.when, context) {
            continue;
        }

        let current = match context
            .settings
            .value_for(&rule.target.section, &rule.target.key)
        {
            Some(value) => value,
            None => continue,
        };
        let matches = value_matches(current, &rule.expect, rule.target.value_type);
        let token_setting = Some(rule.target.key.as_str());

        if !matches {
            result.outcomes.push(EvaluationOutcome {
                id: rule.id.clone(),
                kind: OutcomeKind::Issue,
                bucket: AutoscanReportPlacement::Settings,
                severity: rule.severity,
                message: apply_template(&rule.messages.fail, context, token_setting),
                fix: rule
                    .messages
                    .fix
                    .as_ref()
                    .map(|value| apply_template(value, context, token_setting)),
                section: Some(rule.target.section.clone()),
                setting: Some(rule.target.key.clone()),
                expected: Some(rule.expect.as_string()),
                actual: Some(current.to_string()),
            });
        } else if let Some(pass_message) = &rule.messages.pass {
            result.outcomes.push(EvaluationOutcome {
                id: rule.id.clone(),
                kind: OutcomeKind::Success,
                bucket: AutoscanReportPlacement::Settings,
                severity: RuleSeverity::Info,
                message: apply_template(pass_message, context, token_setting),
                fix: None,
                section: Some(rule.target.section.clone()),
                setting: Some(rule.target.key.clone()),
                expected: Some(rule.expect.as_string()),
                actual: Some(current.to_string()),
            });
        }
    }

    result
}

fn evaluate_predicate(predicate: &Predicate, context: &EvaluationContext) -> bool {
    match predicate {
        Predicate::Always => true,
        Predicate::PluginAny(plugins) => plugins.iter().any(|plugin| {
            context
                .installed_plugins
                .contains(&plugin.trim().to_lowercase())
        }),
        Predicate::ConfigLayoutIs(layout) => context.config_layout == *layout,
        Predicate::CrashgenVersionLt(target) => context
            .crashgen_version
            .is_some_and(|version| version < *target),
        Predicate::All(items) => items.iter().all(|item| evaluate_predicate(item, context)),
        Predicate::Any(items) => items.iter().any(|item| evaluate_predicate(item, context)),
        Predicate::Not(item) => !evaluate_predicate(item, context),
    }
}

fn parse_bool(value: &str) -> Option<bool> {
    match value.trim().to_lowercase().as_str() {
        "true" | "1" | "yes" | "on" => Some(true),
        "false" | "0" | "no" | "off" => Some(false),
        _ => None,
    }
}

fn value_matches(current: &str, expected: &ExpectedValue, value_type: TargetValueType) -> bool {
    match (value_type, expected) {
        (TargetValueType::Bool, ExpectedValue::Bool(expected_bool)) => {
            parse_bool(current).is_some_and(|current_bool| current_bool == *expected_bool)
        }
        (TargetValueType::Int, ExpectedValue::Int(expected_int)) => current
            .trim()
            .parse::<i64>()
            .is_ok_and(|current_int| current_int == *expected_int),
        (TargetValueType::String, ExpectedValue::String(expected_string)) => {
            current.trim() == expected_string
        }
        (_, ExpectedValue::String(expected_string)) => current.trim() == expected_string,
        (_, ExpectedValue::Bool(expected_bool)) => {
            parse_bool(current).is_some_and(|current_bool| current_bool == *expected_bool)
        }
        (_, ExpectedValue::Int(expected_int)) => current
            .trim()
            .parse::<i64>()
            .is_ok_and(|current_int| current_int == *expected_int),
    }
}

fn apply_template(template: &str, context: &EvaluationContext, setting: Option<&str>) -> String {
    let display_section = if context.display_section.is_empty() {
        "[Compatibility]"
    } else {
        context.display_section.as_str()
    };

    template
        .replace("{crashgen_name}", &context.crashgen_name)
        .replace("{display_section}", display_section)
        .replace("{setting}", setting.unwrap_or(""))
}

#[cfg(test)]
#[path = "crashgen_rules_tests.rs"]
mod tests;
