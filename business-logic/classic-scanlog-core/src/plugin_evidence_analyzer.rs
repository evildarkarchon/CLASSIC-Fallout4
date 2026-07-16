//! Semantic Plugin Evidence analysis.

use std::collections::HashSet;
use std::sync::Arc;

use aho_corasick::AhoCorasick;

use crate::analyzer::{AnalyzerError, AnalyzerErrorCode, AnalyzerKind, AnalyzerResult};

/// Owned Crash Log facts consumed by one Plugin Evidence analysis call.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct PluginEvidenceAnalysisInput {
    /// Call-stack lines in their caller-provided casing.
    pub call_stack: Vec<String>,
    /// Plugin identities parsed from the Crash Log.
    pub plugins: Vec<String>,
}

/// One plugin identity observed in Crash Log call-stack evidence.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PluginEvidence {
    /// Normalized plugin identity.
    pub plugin: String,
    /// Number of call-stack lines containing the plugin identity.
    pub occurrences: u32,
}

/// Completed Plugin Evidence analysis, including explicit empty success.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct PluginEvidenceAnalysisResult {
    /// Typed evidence in candidate plugin order.
    pub evidence: Vec<PluginEvidence>,
}

#[derive(Debug)]
struct CompiledConfiguration {
    ignored_plugins: HashSet<String>,
}

/// Immutable analyzer for plugin identities observed in call-stack evidence.
#[derive(Clone, Debug)]
pub struct PluginEvidenceAnalyzer {
    configuration: Arc<CompiledConfiguration>,
}

impl PluginEvidenceAnalyzer {
    /// Creates an immutable analyzer from owned plugin-ignore configuration.
    pub fn new(ignored_plugins: Vec<String>) -> AnalyzerResult<Self> {
        let ignored_plugins = ignored_plugins
            .into_iter()
            .map(|plugin| {
                let plugin = plugin.trim();
                if plugin.is_empty() {
                    return Err(invalid_configuration(
                        "Plugin Evidence ignored plugin must not be empty".to_string(),
                    ));
                }
                Ok(plugin.to_lowercase())
            })
            .collect::<AnalyzerResult<HashSet<_>>>()?;
        Ok(Self {
            configuration: Arc::new(CompiledConfiguration { ignored_plugins }),
        })
    }

    /// Analyzes owned call-stack and plugin facts without producing report text.
    pub fn analyze(
        &self,
        input: PluginEvidenceAnalysisInput,
    ) -> AnalyzerResult<PluginEvidenceAnalysisResult> {
        let mut seen = HashSet::new();
        let plugins = input
            .plugins
            .into_iter()
            .map(|plugin| plugin.trim().to_lowercase())
            .filter(|plugin| {
                !plugin.is_empty()
                    && !self.configuration.ignored_plugins.contains(plugin)
                    && seen.insert(plugin.clone())
            })
            .collect::<Vec<_>>();
        if plugins.is_empty() {
            return Ok(PluginEvidenceAnalysisResult::default());
        }

        let matcher = AhoCorasick::new(&plugins).map_err(|error| {
            invalid_configuration(format!(
                "Plugin Evidence matcher could not be compiled: {error}"
            ))
        })?;
        let mut counts = vec![0_u32; plugins.len()];
        for line in input.call_stack {
            let line = line.to_lowercase();
            if line.contains("modified by:") {
                continue;
            }
            let mut matched_patterns = HashSet::new();
            for matched in matcher.find_iter(&line) {
                let index = matched.pattern().as_usize();
                if matched_patterns.insert(index) {
                    counts[index] = counts[index].checked_add(1).ok_or_else(|| {
                        invalid_configuration(
                            "Plugin Evidence occurrence count exceeded u32".to_string(),
                        )
                    })?;
                }
            }
        }

        Ok(PluginEvidenceAnalysisResult {
            evidence: plugins
                .into_iter()
                .zip(counts)
                .filter_map(|(plugin, occurrences)| {
                    (occurrences > 0).then_some(PluginEvidence {
                        plugin,
                        occurrences,
                    })
                })
                .collect(),
        })
    }
}

/// Creates the shared typed error for invalid Plugin Evidence configuration.
fn invalid_configuration(message: String) -> AnalyzerError {
    AnalyzerError::new(
        AnalyzerKind::PluginEvidence,
        AnalyzerErrorCode::InvalidConfiguration,
        message,
    )
}

#[cfg(test)]
#[path = "plugin_evidence_analyzer_tests.rs"]
mod tests;
