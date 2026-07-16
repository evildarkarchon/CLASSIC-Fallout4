//! Semantic Mod Guidance analysis.

use std::collections::HashSet;
use std::sync::Arc;

use aho_corasick::{AhoCorasick, MatchKind};
use classic_config_core::{
    CoreModEntry, CoreModExclude, ModConflictEntry, ModSolutionCriteria, ModSolutionEntry,
};
use indexmap::IndexMap;

use crate::analyzer::{AnalyzerError, AnalyzerErrorCode, AnalyzerKind, AnalyzerResult};

/// Owned Crash Log facts consumed by one aggregate Mod Guidance analysis call.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct ModGuidanceAnalysisInput {
    /// Installed plugin names mapped to their load-order identifiers.
    pub plugins: IndexMap<String, String>,
    /// Detected GPU vendor, when available.
    pub user_gpu: Option<String>,
    /// Installed XSE module filenames.
    pub xse_modules: HashSet<String>,
}

/// Semantic match state shared by every Mod Guidance result family.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ModGuidanceMatchState {
    /// Configured guidance matched installed plugin or XSE evidence.
    Matched,
    /// An applicable important mod was not found.
    Missing,
    /// An installed GPU-specific mod does not match the detected GPU vendor.
    GpuMismatch,
}

/// One matched YAML-authored mod conflict.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ModConflictGuidance {
    /// Explicit state retained for binding consumers.
    pub state: ModGuidanceMatchState,
    /// YAML-authored matcher identity for the first mod.
    pub mod_a: String,
    /// YAML-authored matcher identity for the second mod.
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
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ModSolutionGuidance {
    /// Explicit state retained for binding consumers.
    pub state: ModGuidanceMatchState,
    /// Stable YAML-authored entry identifier.
    pub id: String,
    /// Authored display name.
    pub name: String,
    /// Authored guidance body.
    pub description: String,
    /// Load-order identifiers whose plugins satisfied the configured criteria.
    pub matched_plugin_ids: Vec<String>,
}

/// One applicable important-mod result.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ImportantModGuidance {
    /// Installed, missing, or GPU-mismatched state.
    pub state: ModGuidanceMatchState,
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
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct ModGuidanceAnalysisResult {
    /// Matched mod conflicts in configuration order.
    pub conflicts: Vec<ModConflictGuidance>,
    /// Matched frequent-crash guidance in configuration order.
    pub frequent_crashes: Vec<ModSolutionGuidance>,
    /// Matched solution guidance in configuration order.
    pub solutions: Vec<ModSolutionGuidance>,
    /// Applicable important-mod states in configuration order.
    pub important_mods: Vec<ImportantModGuidance>,
}

#[derive(Debug)]
struct CompiledConfiguration {
    conflicts: Vec<CompiledConflict>,
    conflict_matcher: Option<AhoCorasick>,
    conflict_tokens: Vec<String>,
    frequent_crashes: Vec<CompiledSolution>,
    solutions: Vec<CompiledSolution>,
    important_mods: Vec<CompiledImportantMod>,
    important_matcher: Option<AhoCorasick>,
}

#[derive(Debug)]
struct CompiledConflict {
    entry: ModConflictEntry,
    mod_a_token: String,
    mod_b_token: String,
}

#[derive(Debug)]
struct CompiledSolution {
    entry: ModSolutionEntry,
    criterion_tokens: HashSet<String>,
    criterion_matchers: Vec<AhoCorasick>,
    exception_matchers: Vec<(String, AhoCorasick)>,
}

#[derive(Debug)]
struct CompiledImportantMod {
    entry: CoreModEntry,
    excluded_plugins: HashSet<String>,
}

/// Immutable analyzer for conflict, frequent-crash, solution, and important-mod guidance.
///
/// Construction validates authored configuration and compiles every substring
/// matcher. Clones share immutable state and keep all per-log facts local to
/// each aggregate `analyze` call.
#[derive(Clone, Debug)]
pub struct ModGuidanceAnalyzer {
    configuration: Arc<CompiledConfiguration>,
}

impl ModGuidanceAnalyzer {
    /// Validates and compiles all four YAML-backed Mod Guidance rule families.
    pub fn new(
        conflicts: Vec<ModConflictEntry>,
        frequent_crashes: Vec<ModSolutionEntry>,
        solutions: Vec<ModSolutionEntry>,
        important_mods: Vec<CoreModEntry>,
    ) -> AnalyzerResult<Self> {
        let (conflicts, conflict_matcher, conflict_tokens) = compile_conflicts(conflicts)?;
        let frequent_crashes = compile_solution_group(frequent_crashes, "frequent-crash")?;
        let solutions = compile_solution_group(solutions, "solution")?;
        let (important_mods, important_matcher) = compile_important_mods(important_mods)?;

        Ok(Self {
            configuration: Arc::new(CompiledConfiguration {
                conflicts,
                conflict_matcher,
                conflict_tokens,
                frequent_crashes,
                solutions,
                important_mods,
                important_matcher,
            }),
        })
    }

    /// Evaluates every configured Mod Guidance family in one aggregate call.
    ///
    /// A successful call always returns a result value. No-match analysis is
    /// represented by four empty collections, never by absence or an error.
    pub fn analyze(
        &self,
        input: ModGuidanceAnalysisInput,
    ) -> AnalyzerResult<ModGuidanceAnalysisResult> {
        let plugins = input
            .plugins
            .into_iter()
            .map(|(name, id)| (name.to_lowercase(), id))
            .collect::<Vec<_>>();
        let plugin_names = plugins
            .iter()
            .map(|(name, _)| name.clone())
            .collect::<HashSet<_>>();
        let xse_modules = input
            .xse_modules
            .into_iter()
            .map(|module| module.to_lowercase())
            .collect::<Vec<_>>();
        let important_haystack = plugins
            .iter()
            .map(|(name, _)| name.as_str())
            .chain(xse_modules.iter().map(String::as_str))
            .collect::<Vec<_>>()
            .join(" ");
        let conflict_tokens = matched_token_identities(
            self.configuration.conflict_matcher.as_ref(),
            &self.configuration.conflict_tokens,
            plugins.iter().map(|(name, _)| name.as_str()),
        );

        Ok(ModGuidanceAnalysisResult {
            conflicts: analyze_conflicts(&self.configuration.conflicts, &conflict_tokens),
            frequent_crashes: analyze_solutions(&self.configuration.frequent_crashes, &plugins),
            solutions: analyze_solutions(&self.configuration.solutions, &plugins),
            important_mods: analyze_important_mods(
                &self.configuration.important_mods,
                self.configuration.important_matcher.as_ref(),
                &important_haystack,
                &plugin_names,
                input.user_gpu.as_deref(),
            ),
        })
    }
}

/// Validates conflicts and compiles one shared longest-match token automaton.
fn compile_conflicts(
    entries: Vec<ModConflictEntry>,
) -> AnalyzerResult<(Vec<CompiledConflict>, Option<AhoCorasick>, Vec<String>)> {
    let mut tokens = Vec::new();
    let conflicts = entries
        .into_iter()
        .map(|entry| {
            validate_required(&entry.mod_a, "conflict mod_a")?;
            validate_required(&entry.mod_b, "conflict mod_b")?;
            validate_required(&entry.name_a, "conflict name_a")?;
            validate_required(&entry.name_b, "conflict name_b")?;
            validate_required(&entry.description, "conflict description")?;
            validate_required(&entry.fix, "conflict fix")?;

            let mod_a_token = entry.mod_a.to_lowercase();
            let mod_b_token = entry.mod_b.to_lowercase();
            tokens.extend([mod_a_token.clone(), mod_b_token.clone()]);
            Ok(CompiledConflict {
                entry,
                mod_a_token,
                mod_b_token,
            })
        })
        .collect::<AnalyzerResult<Vec<_>>>()?;
    tokens.sort();
    tokens.dedup();
    tokens.sort_by(|left, right| right.len().cmp(&left.len()).then_with(|| left.cmp(right)));
    let matcher = if tokens.is_empty() {
        None
    } else {
        Some(
            AhoCorasick::builder()
                .match_kind(MatchKind::LeftmostLongest)
                .build(&tokens)
                .map_err(|error| {
                    invalid_configuration(format!(
                        "conflict matcher could not be compiled: {error}"
                    ))
                })?,
        )
    };
    Ok((conflicts, matcher, tokens))
}

/// Validates stable identifiers and compiles one structured guidance group.
fn compile_solution_group(
    entries: Vec<ModSolutionEntry>,
    group: &str,
) -> AnalyzerResult<Vec<CompiledSolution>> {
    let mut ids = HashSet::new();
    entries
        .into_iter()
        .map(|entry| {
            validate_required(&entry.id, &format!("{group} id"))?;
            if !ids.insert(entry.id.clone()) {
                return Err(invalid_configuration(format!(
                    "duplicate {group} Mod Guidance id '{}'",
                    entry.id
                )));
            }
            validate_required(&entry.name, &format!("{group} name"))?;
            validate_required(&entry.description, &format!("{group} description"))?;
            if entry.criteria.values().is_empty() {
                return Err(invalid_configuration(format!(
                    "{group} Mod Guidance '{}' has no criteria",
                    entry.id
                )));
            }

            let criterion_tokens = entry
                .criteria
                .values()
                .iter()
                .map(|token| {
                    validate_required(token, &format!("{group} criterion"))?;
                    Ok(token.to_lowercase())
                })
                .collect::<AnalyzerResult<HashSet<_>>>()?;
            let criterion_matchers = entry
                .criteria
                .values()
                .iter()
                .map(|token| compile_matcher(token, &format!("{group} criterion")))
                .collect::<AnalyzerResult<Vec<_>>>()?;
            let exception_matchers = entry
                .exceptions
                .iter()
                .map(|token| {
                    validate_required(token, &format!("{group} exception"))?;
                    Ok((
                        token.to_lowercase(),
                        compile_matcher(token, &format!("{group} exception"))?,
                    ))
                })
                .collect::<AnalyzerResult<Vec<_>>>()?;

            Ok(CompiledSolution {
                entry,
                criterion_tokens,
                criterion_matchers,
                exception_matchers,
            })
        })
        .collect()
}

/// Validates important-mod identities and compiles detection matchers.
fn compile_important_mods(
    entries: Vec<CoreModEntry>,
) -> AnalyzerResult<(Vec<CompiledImportantMod>, Option<AhoCorasick>)> {
    let mut detects = HashSet::new();
    let compiled = entries
        .into_iter()
        .map(|entry| {
            validate_required(&entry.detect, "important-mod detect")?;
            validate_required(&entry.name, "important-mod name")?;
            validate_required(&entry.description, "important-mod description")?;
            if !detects.insert(entry.detect.to_lowercase()) {
                return Err(invalid_configuration(format!(
                    "duplicate important-mod detect '{}'",
                    entry.detect
                )));
            }
            if let Some(gpu) = &entry.gpu {
                validate_required(gpu, "important-mod gpu")?;
            }
            if entry
                .gpu_mismatch_warning
                .as_ref()
                .is_some_and(|warning| warning.trim().is_empty())
            {
                return Err(invalid_configuration(format!(
                    "important-mod '{}' has an empty gpu_mismatch_warning",
                    entry.detect
                )));
            }

            let excluded_plugins = match &entry.exclude_when {
                Some(CoreModExclude::PluginAny(plugins)) => {
                    if plugins.is_empty() {
                        return Err(invalid_configuration(format!(
                            "important-mod '{}' has an empty exclusion",
                            entry.detect
                        )));
                    }
                    plugins
                        .iter()
                        .map(|plugin| {
                            validate_required(plugin, "important-mod exclusion plugin")?;
                            Ok(plugin.to_lowercase())
                        })
                        .collect::<AnalyzerResult<HashSet<_>>>()?
                }
                None => HashSet::new(),
            };

            Ok(CompiledImportantMod {
                entry,
                excluded_plugins,
            })
        })
        .collect::<AnalyzerResult<Vec<_>>>()?;
    let matcher = if compiled.is_empty() {
        None
    } else {
        Some(
            AhoCorasick::builder()
                .match_kind(MatchKind::LeftmostLongest)
                .build(
                    compiled
                        .iter()
                        .map(|entry| entry.entry.detect.to_lowercase()),
                )
                .map_err(|error| {
                    invalid_configuration(format!(
                        "important-mod matcher could not be compiled: {error}"
                    ))
                })?,
        )
    };
    Ok((compiled, matcher))
}

/// Returns one semantic conflict for each pair present in installed plugins.
fn analyze_conflicts(
    conflicts: &[CompiledConflict],
    present_tokens: &HashSet<String>,
) -> Vec<ModConflictGuidance> {
    conflicts
        .iter()
        .filter(|conflict| {
            present_tokens.contains(&conflict.mod_a_token)
                && present_tokens.contains(&conflict.mod_b_token)
        })
        .map(|conflict| ModConflictGuidance {
            state: ModGuidanceMatchState::Matched,
            mod_a: conflict.entry.mod_a.clone(),
            mod_b: conflict.entry.mod_b.clone(),
            name_a: conflict.entry.name_a.clone(),
            name_b: conflict.entry.name_b.clone(),
            description: conflict.entry.description.clone(),
            fix: conflict.entry.fix.clone(),
            link: conflict.entry.link.clone(),
        })
        .collect()
}

/// Collects non-overlapping longest-match token identities across separate names.
fn matched_token_identities<'a>(
    matcher: Option<&AhoCorasick>,
    tokens: &[String],
    names: impl Iterator<Item = &'a str>,
) -> HashSet<String> {
    let Some(matcher) = matcher else {
        return HashSet::new();
    };
    names
        .flat_map(|name| matcher.find_iter(name))
        .map(|matched| tokens[matched.pattern().as_usize()].clone())
        .collect()
}

/// Evaluates structured any/all criteria and exception suppression.
fn analyze_solutions(
    entries: &[CompiledSolution],
    plugins: &[(String, String)],
) -> Vec<ModSolutionGuidance> {
    entries
        .iter()
        .filter_map(|compiled| {
            let mut matched_plugin_ids = Vec::new();
            let mut matched_count = 0;
            for matcher in &compiled.criterion_matchers {
                if let Some((_, plugin_id)) = plugins
                    .iter()
                    .find(|(plugin_name, _)| matcher.is_match(plugin_name))
                {
                    matched_count += 1;
                    if !matched_plugin_ids.contains(plugin_id) {
                        matched_plugin_ids.push(plugin_id.clone());
                    }
                }
            }

            let matched = match &compiled.entry.criteria {
                ModSolutionCriteria::Any(_) => matched_count > 0,
                ModSolutionCriteria::All(criteria) => matched_count == criteria.len(),
            };
            if !matched {
                return None;
            }

            let suppressed = compiled.exception_matchers.iter().any(|(token, matcher)| {
                !compiled.criterion_tokens.contains(token)
                    && plugins
                        .iter()
                        .any(|(plugin_name, _)| matcher.is_match(plugin_name))
            });
            if suppressed {
                return None;
            }

            Some(ModSolutionGuidance {
                state: ModGuidanceMatchState::Matched,
                id: compiled.entry.id.clone(),
                name: compiled.entry.name.clone(),
                description: compiled.entry.description.clone(),
                matched_plugin_ids,
            })
        })
        .collect()
}

/// Evaluates installed, missing, mismatch, and exclusion states for important mods.
fn analyze_important_mods(
    entries: &[CompiledImportantMod],
    matcher: Option<&AhoCorasick>,
    haystack: &str,
    plugin_names: &HashSet<String>,
    user_gpu: Option<&str>,
) -> Vec<ImportantModGuidance> {
    let matched_pattern_ids = matcher
        .map(|matcher| {
            matcher
                .find_iter(haystack)
                .map(|matched| matched.pattern().as_usize())
                .collect::<HashSet<_>>()
        })
        .unwrap_or_default();
    entries
        .iter()
        .enumerate()
        .filter_map(|(entry_index, compiled)| {
            if compiled
                .excluded_plugins
                .iter()
                .any(|plugin| plugin_names.contains(plugin))
            {
                return None;
            }

            let found = matched_pattern_ids.contains(&entry_index);
            let gpu_matches = compiled
                .entry
                .gpu
                .as_deref()
                .is_some_and(|gpu| user_gpu.is_some_and(|user| gpu.eq_ignore_ascii_case(user)));
            let gpu_mismatch =
                compiled.entry.gpu.as_deref().is_some_and(|gpu| {
                    user_gpu.is_some_and(|user| !gpu.eq_ignore_ascii_case(user))
                });

            let state = if found && gpu_mismatch {
                ModGuidanceMatchState::GpuMismatch
            } else if found {
                ModGuidanceMatchState::Matched
            } else if user_gpu.is_some() && (compiled.entry.gpu.is_none() || gpu_matches) {
                ModGuidanceMatchState::Missing
            } else {
                return None;
            };

            Some(ImportantModGuidance {
                state,
                detect: compiled.entry.detect.clone(),
                name: compiled.entry.name.clone(),
                description: compiled.entry.description.clone(),
                gpu: compiled.entry.gpu.clone(),
                gpu_mismatch_warning: compiled.entry.gpu_mismatch_warning.clone(),
            })
        })
        .collect()
}

/// Compiles one literal case-insensitive substring matcher.
fn compile_matcher(pattern: &str, field: &str) -> AnalyzerResult<AhoCorasick> {
    AhoCorasick::builder()
        .match_kind(MatchKind::LeftmostLongest)
        .build([pattern.to_lowercase()])
        .map_err(|error| {
            invalid_configuration(format!("{field} matcher could not be compiled: {error}"))
        })
}

/// Rejects required authored fields that would create universal or empty guidance.
fn validate_required(value: &str, field: &str) -> AnalyzerResult<()> {
    if value.trim().is_empty() {
        return Err(invalid_configuration(format!(
            "Mod Guidance {field} must not be empty"
        )));
    }
    Ok(())
}

/// Creates the shared typed error for invalid Mod Guidance configuration.
fn invalid_configuration(message: String) -> AnalyzerError {
    AnalyzerError::new(
        AnalyzerKind::ModGuidance,
        AnalyzerErrorCode::InvalidConfiguration,
        message,
    )
}

#[cfg(test)]
#[path = "mod_guidance_analyzer_tests.rs"]
mod tests;
