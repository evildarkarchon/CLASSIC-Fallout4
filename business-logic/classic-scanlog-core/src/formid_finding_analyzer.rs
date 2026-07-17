//! Semantic FormID Finding analysis.

use std::collections::{BTreeMap, HashMap};

use classic_database_core::{FormIdValueLookup, FormIdValueLookupError, FormIdValueLookupOutcome};

use crate::analyzer::{AnalyzerError, AnalyzerErrorCode, AnalyzerKind, AnalyzerResult};
use crate::formid_analyzer::extract_formids_batch;

/// One owned plugin identity and its load-order prefix.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FormIDPlugin {
    /// Plugin filename in caller-provided casing.
    pub name: String,
    /// Two-digit full-plugin or five-digit `FE` light-plugin prefix.
    pub prefix: String,
}

/// Owned Crash Log facts consumed by one FormID Finding analysis call.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct FormIDFindingAnalysisInput {
    /// Crash Log evidence lines in caller-provided casing.
    pub crash_lines: Vec<String>,
    /// Parsed plugin identities and load-order prefixes.
    pub plugins: Vec<FormIDPlugin>,
}

/// Stable semantic state of optional FormID Value Lookup for one finding.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FormIDValueLookupStatus {
    /// The identifier could not be associated with a plugin, so lookup was inapplicable.
    NotApplicable,
    /// Value lookup was explicitly disabled.
    Disabled,
    /// Lookup completed successfully without finding a value.
    Missing,
    /// Lookup completed successfully and returned the finding's optional value.
    Found,
}

/// One distinct FormID observed in Crash Log evidence.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FormIDFinding {
    /// Canonical uppercase eight-digit FormID, including its load-order prefix.
    pub identifier: String,
    /// Number of matching FormID occurrences in the supplied evidence.
    pub occurrences: u32,
    /// Plugin resolved from the identifier prefix, or `None` when unresolved.
    pub plugin: Option<String>,
    /// Semantic lookup state, distinct from the optional value payload.
    pub value_lookup_status: FormIDValueLookupStatus,
    /// Human-readable value returned by a successful lookup hit.
    pub value: Option<String>,
}

/// Completed FormID Finding analysis, including explicit empty success.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct FormIDFindingAnalysisResult {
    /// Distinct findings in canonical identifier order, including unresolved identifiers.
    pub findings: Vec<FormIDFinding>,
}

/// Immutable analyzer for aggregate FormID extraction, counting, plugin resolution, and lookup.
#[derive(Clone, Debug)]
pub struct FormIDFindingAnalyzer {
    value_lookup: FormIdValueLookup,
}

impl FormIDFindingAnalyzer {
    /// Creates an analyzer over an opaque owned FormID Value Lookup facade.
    pub fn new(value_lookup: FormIdValueLookup) -> Self {
        Self { value_lookup }
    }

    /// Analyzes owned Crash Log facts without producing report text.
    ///
    /// Lookup misses remain successful typed data. Malformed lookup replies and
    /// operational failures use the shared analyzer error and fail the whole call.
    pub async fn analyze(
        &self,
        input: FormIDFindingAnalysisInput,
    ) -> AnalyzerResult<FormIDFindingAnalysisResult> {
        let plugins = normalize_plugins(input.plugins)?;
        let extracted = extract_formids_batch(vec![input.crash_lines])
            .into_iter()
            .next()
            .unwrap_or_default();
        let identifiers = aggregate_identifiers(extracted)?;

        let mut staged = Vec::with_capacity(identifiers.len());
        let mut lookup_pairs = Vec::new();
        for (identifier, occurrences) in identifiers {
            let (prefix, suffix) = split_identifier(&identifier);
            let plugin = plugins.get(prefix).cloned();
            if let Some(plugin) = plugin.as_ref() {
                lookup_pairs.push((suffix.to_string(), plugin.clone()));
            }
            staged.push((identifier, occurrences, plugin));
        }

        let mut lookup_outcomes = self
            .value_lookup
            .lookup_batch(lookup_pairs)
            .await
            .map_err(lookup_error)?
            .into_iter();
        let findings = staged
            .into_iter()
            .map(|(identifier, occurrences, plugin)| {
                let (value_lookup_status, value) = if plugin.is_some() {
                    // Treat an adapter/cardinality contract violation as typed failure instead of
                    // allowing a malformed backend reply to panic a binding host.
                    match lookup_outcomes.next().ok_or_else(|| {
                        malformed_result(
                            "FormID Value Lookup returned fewer outcomes than resolved identifiers",
                        )
                    })? {
                        FormIdValueLookupOutcome::Disabled => {
                            (FormIDValueLookupStatus::Disabled, None)
                        }
                        FormIdValueLookupOutcome::Missing => {
                            (FormIDValueLookupStatus::Missing, None)
                        }
                        FormIdValueLookupOutcome::Found(value) => {
                            (FormIDValueLookupStatus::Found, Some(value))
                        }
                    }
                } else {
                    (FormIDValueLookupStatus::NotApplicable, None)
                };
                Ok(FormIDFinding {
                    identifier,
                    occurrences,
                    plugin,
                    value_lookup_status,
                    value,
                })
            })
            .collect::<AnalyzerResult<Vec<_>>>()?;

        if lookup_outcomes.next().is_some() {
            return Err(malformed_result(
                "FormID Value Lookup returned more outcomes than resolved identifiers",
            ));
        }

        Ok(FormIDFindingAnalysisResult { findings })
    }
}

/// Normalizes and validates caller-owned plugin/load-order facts.
fn normalize_plugins(plugins: Vec<FormIDPlugin>) -> AnalyzerResult<HashMap<String, String>> {
    let mut normalized = HashMap::with_capacity(plugins.len());
    for plugin in plugins {
        let name = plugin.name.trim();
        let prefix = plugin.prefix.trim().to_uppercase();
        if name.is_empty() {
            return Err(invalid_configuration(
                "FormID Finding plugin name must not be empty",
            ));
        }
        if !valid_plugin_prefix(&prefix) {
            return Err(invalid_configuration(format!(
                "FormID Finding plugin '{name}' has invalid load-order prefix '{}'",
                plugin.prefix
            )));
        }
        if prefix == "FE" {
            // Legacy Buffout logs assign the generic FE marker to every light plugin. It lacks
            // the three-digit light-plugin index needed to resolve an FExxx FormID safely.
            continue;
        }
        if let Some(existing) = normalized.insert(prefix.clone(), name.to_string())
            && existing != name
        {
            return Err(invalid_configuration(format!(
                "FormID Finding load-order prefix '{prefix}' is assigned to multiple plugins"
            )));
        }
    }
    Ok(normalized)
}

/// Returns whether a prefix is a full-plugin byte or an `FE` light-plugin index.
fn valid_plugin_prefix(prefix: &str) -> bool {
    (prefix.len() == 2 && prefix.bytes().all(|byte| byte.is_ascii_hexdigit()))
        || (prefix.len() == 5
            && prefix.starts_with("FE")
            && prefix.bytes().all(|byte| byte.is_ascii_hexdigit()))
}

/// Counts distinct normalized identifiers without leaking aggregation mechanics.
fn aggregate_identifiers(extracted: Vec<String>) -> AnalyzerResult<BTreeMap<String, u32>> {
    let mut identifiers = BTreeMap::new();
    for extracted_identifier in extracted {
        let Some(identifier) = extracted_identifier.strip_prefix("Form ID: ") else {
            return Err(invalid_configuration(
                "FormID extraction returned an invalid semantic identifier",
            ));
        };
        let occurrences = identifiers.entry(identifier.to_string()).or_insert(0_u32);
        *occurrences = occurrences
            .checked_add(1)
            .ok_or_else(|| invalid_configuration("FormID Finding occurrence count exceeded u32"))?;
    }
    Ok(identifiers)
}

/// Splits one valid full identifier into its plugin prefix and lookup suffix.
fn split_identifier(identifier: &str) -> (&str, &str) {
    if identifier.starts_with("FE") {
        (&identifier[..5], &identifier[5..])
    } else {
        (&identifier[..2], &identifier[2..])
    }
}

/// Creates the shared typed error for invalid FormID Finding input.
fn invalid_configuration(message: impl Into<String>) -> AnalyzerError {
    AnalyzerError::new(
        AnalyzerKind::FormIdFinding,
        AnalyzerErrorCode::InvalidConfiguration,
        message,
    )
}

/// Creates the shared typed error for an invalid lookup result shape.
fn malformed_result(message: impl Into<String>) -> AnalyzerError {
    AnalyzerError::new(
        AnalyzerKind::FormIdFinding,
        AnalyzerErrorCode::MalformedResult,
        message,
    )
}

/// Preserves strict lookup failure categories in the shared analyzer envelope.
fn lookup_error(error: FormIdValueLookupError) -> AnalyzerError {
    let code = match error.code() {
        "malformed_result" => AnalyzerErrorCode::MalformedResult,
        _ => AnalyzerErrorCode::OperationalFailure,
    };
    AnalyzerError::new(AnalyzerKind::FormIdFinding, code, error.message())
}

// Keep the repository's required sibling-test declaration intact under rustfmt.
#[rustfmt::skip]
#[cfg(test)] #[path = "formid_finding_analyzer_tests.rs"] mod tests;
