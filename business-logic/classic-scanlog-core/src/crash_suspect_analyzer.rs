//! Semantic Crash Suspect analysis.

use std::sync::Arc;

use aho_corasick::AhoCorasick;
use classic_config_core::{SuspectErrorRule, SuspectStackRule};

use crate::analyzer::{AnalyzerError, AnalyzerErrorCode, AnalyzerKind, AnalyzerResult};

/// Owned Crash Log facts consumed by one Crash Suspect analysis call.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct CrashSuspectAnalysisInput {
    /// Main error text extracted from the Crash Log.
    pub main_error: String,
    /// Complete call-stack evidence used by stack rules.
    pub call_stack: String,
}

/// Identifies which Crash Suspect evidence source produced a finding.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CrashSuspectFindingKind {
    /// A configured main-error rule matched.
    MainErrorRule,
    /// A configured stack rule matched.
    StackRule,
    /// The main error reports DLL involvement.
    DllInvolvement,
}

/// One semantic Crash Suspect Finding without report presentation mechanics.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum CrashSuspectFinding {
    /// One matched configured main-error rule.
    MainErrorRule {
        /// Stable configured rule identifier.
        rule_id: String,
        /// Authored rule name.
        name: String,
        /// Authored rule severity.
        severity: i32,
    },
    /// One matched configured stack rule.
    StackRule {
        /// Stable configured rule identifier.
        rule_id: String,
        /// Authored rule name.
        name: String,
        /// Authored rule severity.
        severity: i32,
    },
    /// The main error reports DLL involvement.
    DllInvolvement,
}

impl CrashSuspectFinding {
    /// Returns the stable finding-kind discriminator projected by foreign bindings.
    pub const fn kind(&self) -> CrashSuspectFindingKind {
        match self {
            Self::MainErrorRule { .. } => CrashSuspectFindingKind::MainErrorRule,
            Self::StackRule { .. } => CrashSuspectFindingKind::StackRule,
            Self::DllInvolvement => CrashSuspectFindingKind::DllInvolvement,
        }
    }
}

/// Completed Crash Suspect analysis, including an explicit empty success.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct CrashSuspectAnalysisResult {
    /// Individual findings in rule-configuration order, followed by DLL involvement.
    pub findings: Vec<CrashSuspectFinding>,
}

#[derive(Debug)]
struct CompiledConfiguration {
    main_error_rules: Vec<CompiledMainErrorRule>,
    stack_rules: Vec<CompiledStackRule>,
}

#[derive(Debug)]
struct CompiledMainErrorRule {
    rule: SuspectErrorRule,
    matcher: AhoCorasick,
}

#[derive(Debug)]
struct CompiledStackRule {
    rule: SuspectStackRule,
    required_main_error_matcher: Option<AhoCorasick>,
    optional_main_error_matcher: Option<AhoCorasick>,
    stack_matcher: Option<AhoCorasick>,
    exclusion_matcher: Option<AhoCorasick>,
}

/// Immutable analyzer for known crash messages, stack patterns, and DLL involvement.
#[derive(Clone, Debug)]
pub struct CrashSuspectAnalyzer {
    configuration: Arc<CompiledConfiguration>,
}

impl CrashSuspectAnalyzer {
    /// Creates an immutable analyzer from owned Crash Suspect rules.
    pub fn new(
        main_error_rules: Vec<SuspectErrorRule>,
        stack_rules: Vec<SuspectStackRule>,
    ) -> AnalyzerResult<Self> {
        let mut rule_ids = std::collections::HashSet::new();
        let main_error_rules = main_error_rules
            .into_iter()
            .map(|rule| compile_main_error_rule(rule, &mut rule_ids))
            .collect::<AnalyzerResult<Vec<_>>>()?;
        let stack_rules = stack_rules
            .into_iter()
            .map(|rule| compile_stack_rule(rule, &mut rule_ids))
            .collect::<AnalyzerResult<Vec<_>>>()?;

        Ok(Self {
            configuration: Arc::new(CompiledConfiguration {
                main_error_rules,
                stack_rules,
            }),
        })
    }

    /// Analyzes one owned Crash Log input and returns semantic findings.
    pub fn analyze(
        &self,
        input: CrashSuspectAnalysisInput,
    ) -> AnalyzerResult<CrashSuspectAnalysisResult> {
        let mut findings = self.main_error_findings(&input.main_error);
        findings.extend(self.stack_findings(&input.main_error, &input.call_stack));

        let main_error_lower = input.main_error.to_lowercase();
        if main_error_lower.contains(".dll") && !main_error_lower.contains("tbbmalloc") {
            findings.push(CrashSuspectFinding::DllInvolvement);
        }

        Ok(CrashSuspectAnalysisResult { findings })
    }

    /// Matches configured main-error rules for one Crash Log.
    fn main_error_findings(&self, main_error: &str) -> Vec<CrashSuspectFinding> {
        self.configuration
            .main_error_rules
            .iter()
            .filter(|rule| rule.matcher.is_match(main_error))
            .map(|rule| CrashSuspectFinding::MainErrorRule {
                rule_id: rule.rule.id.clone(),
                name: rule.rule.name.clone(),
                severity: rule.rule.severity,
            })
            .collect()
    }

    /// Matches configured stack rules for one Crash Log.
    fn stack_findings(&self, main_error: &str, call_stack: &str) -> Vec<CrashSuspectFinding> {
        self.configuration
            .stack_rules
            .iter()
            .filter(|rule| stack_rule_matches(rule, main_error, call_stack))
            .map(|rule| CrashSuspectFinding::StackRule {
                rule_id: rule.rule.id.clone(),
                name: rule.rule.name.clone(),
                severity: rule.rule.severity,
            })
            .collect()
    }
}

/// Applies the structured stack-rule conditions without creating report text.
fn stack_rule_matches(rule: &CompiledStackRule, main_error: &str, call_stack: &str) -> bool {
    if rule
        .exclusion_matcher
        .as_ref()
        .is_some_and(|matcher| matcher.is_match(call_stack))
    {
        return false;
    }

    if let Some(required_matcher) = &rule.required_main_error_matcher {
        // Required main-error signals intentionally dominate optional stack signals for parity.
        return required_matcher.is_match(main_error);
    }

    rule.optional_main_error_matcher
        .as_ref()
        .is_some_and(|matcher| matcher.is_match(main_error))
        || rule
            .stack_matcher
            .as_ref()
            .is_some_and(|matcher| matcher.is_match(call_stack))
        || rule
            .rule
            .stack_contains_at_least
            .iter()
            .any(|count_rule| call_stack.matches(&count_rule.substring).count() >= count_rule.count)
}

/// Validates and compiles one main-error rule before the analyzer is shared.
fn compile_main_error_rule(
    rule: SuspectErrorRule,
    rule_ids: &mut std::collections::HashSet<String>,
) -> AnalyzerResult<CompiledMainErrorRule> {
    validate_common_rule_fields(&rule.id, &rule.name, "main-error", rule_ids)?;
    validate_signals(
        &rule.main_error_contains_any,
        "main-error rule main_error_contains_any",
        true,
    )?;
    let matcher = compile_matcher(&rule.main_error_contains_any, &rule.id)?
        .expect("nonempty main-error matchers always compile to Some");
    Ok(CompiledMainErrorRule { rule, matcher })
}

/// Validates and compiles one stack rule before the analyzer is shared.
fn compile_stack_rule(
    rule: SuspectStackRule,
    rule_ids: &mut std::collections::HashSet<String>,
) -> AnalyzerResult<CompiledStackRule> {
    validate_common_rule_fields(&rule.id, &rule.name, "stack", rule_ids)?;
    validate_signals(
        &rule.main_error_required_any,
        "stack rule main_error_required_any",
        false,
    )?;
    validate_signals(
        &rule.main_error_optional_any,
        "stack rule main_error_optional_any",
        false,
    )?;
    validate_signals(
        &rule.stack_contains_any,
        "stack rule stack_contains_any",
        false,
    )?;
    validate_signals(
        &rule.exclude_if_stack_contains_any,
        "stack rule exclude_if_stack_contains_any",
        false,
    )?;
    if rule
        .stack_contains_at_least
        .iter()
        .any(|count_rule| count_rule.substring.trim().is_empty() || count_rule.count == 0)
    {
        return Err(invalid_configuration(format!(
            "Crash Suspect stack rule '{}' has an invalid stack_contains_at_least matcher",
            rule.id
        )));
    }
    if rule.main_error_required_any.is_empty()
        && rule.main_error_optional_any.is_empty()
        && rule.stack_contains_any.is_empty()
        && rule.stack_contains_at_least.is_empty()
    {
        return Err(invalid_configuration(format!(
            "Crash Suspect stack rule '{}' has no positive matcher",
            rule.id
        )));
    }

    Ok(CompiledStackRule {
        required_main_error_matcher: compile_matcher(&rule.main_error_required_any, &rule.id)?,
        optional_main_error_matcher: compile_matcher(&rule.main_error_optional_any, &rule.id)?,
        stack_matcher: compile_matcher(&rule.stack_contains_any, &rule.id)?,
        exclusion_matcher: compile_matcher(&rule.exclude_if_stack_contains_any, &rule.id)?,
        rule,
    })
}

/// Validates the authored identity shared by both rule families.
fn validate_common_rule_fields(
    id: &str,
    name: &str,
    family: &str,
    rule_ids: &mut std::collections::HashSet<String>,
) -> AnalyzerResult<()> {
    if id.trim().is_empty() {
        return Err(invalid_configuration(format!(
            "Crash Suspect {family} rule id must not be empty"
        )));
    }
    if name.trim().is_empty() {
        return Err(invalid_configuration(format!(
            "Crash Suspect {family} rule '{id}' name must not be empty"
        )));
    }
    if !rule_ids.insert(id.to_string()) {
        return Err(invalid_configuration(format!(
            "duplicate Crash Suspect rule id '{id}'"
        )));
    }
    Ok(())
}

/// Rejects empty matcher strings before Aho-Corasick could treat them as universal matches.
fn validate_signals(signals: &[String], field: &str, required: bool) -> AnalyzerResult<()> {
    if (required && signals.is_empty()) || signals.iter().any(|signal| signal.trim().is_empty()) {
        return Err(invalid_configuration(format!(
            "Crash Suspect {field} must contain nonempty signals"
        )));
    }
    Ok(())
}

/// Compiles one optional substring matcher and preserves matcher-build failures as typed errors.
fn compile_matcher(patterns: &[String], rule_id: &str) -> AnalyzerResult<Option<AhoCorasick>> {
    if patterns.is_empty() {
        return Ok(None);
    }
    AhoCorasick::new(patterns).map(Some).map_err(|error| {
        invalid_configuration(format!(
            "Crash Suspect rule '{rule_id}' matcher could not be compiled: {error}"
        ))
    })
}

/// Creates the shared stable error shape for Crash Suspect configuration failures.
fn invalid_configuration(message: String) -> AnalyzerError {
    AnalyzerError::new(
        AnalyzerKind::CrashSuspect,
        AnalyzerErrorCode::InvalidConfiguration,
        message,
    )
}

#[cfg(test)]
#[path = "crash_suspect_analyzer_tests.rs"]
mod tests;
