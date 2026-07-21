//! Private coordination of semantic Autoscan Report Contributions.

use std::collections::HashSet;

use classic_config_core::{ConfigLayout, CrashgenSettingsSnapshot};
use classic_database_core::FormIdValueLookup;
use indexmap::IndexMap;

use crate::analyzer::{AnalyzerError, AnalyzerErrorCode};
use crate::crash_suspect_analyzer::{
    CrashSuspectAnalysisInput, CrashSuspectAnalysisResult, CrashSuspectAnalyzer,
};
use crate::crashgen_settings_analyzer::{
    CrashgenSettingsAnalysisInput, CrashgenSettingsAnalysisResult, CrashgenSettingsAnalyzer,
};
use crate::error::{Result, ScanLogError};
use crate::formid_finding_analyzer::{
    FormIDFindingAnalysisInput, FormIDFindingAnalysisResult, FormIDFindingAnalyzer, FormIDPlugin,
};
use crate::gpu_detector::GpuDetector;
use crate::mod_guidance_analyzer::{
    ModGuidanceAnalysisInput, ModGuidanceAnalysisResult, ModGuidanceAnalyzer,
};
use crate::named_record_finding_analyzer::{
    NamedRecordFindingAnalysisInput, NamedRecordFindingAnalysisResult, NamedRecordFindingAnalyzer,
};
use crate::plugin_evidence_analyzer::{
    PluginEvidenceAnalysisInput, PluginEvidenceAnalysisResult, PluginEvidenceAnalyzer,
};

/// Aggregate semantic results offered to Autoscan Report Assembly for one Crash Log.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(crate) struct AutoscanReportContributions {
    /// Crashgen Settings Analysis, or `None` when the analysis was not performed.
    pub(crate) crashgen_settings: Option<CrashgenSettingsAnalysisResult>,
    /// Crash Suspect analysis, which is present for every completed collection.
    pub(crate) crash_suspects: Option<CrashSuspectAnalysisResult>,
    /// Mod Guidance, or `None` when plugin parsing did not produce a result.
    pub(crate) mod_guidance: Option<ModGuidanceAnalysisResult>,
    /// Plugin Evidence, or `None` when no plugin candidates were available.
    pub(crate) plugin_evidence: Option<PluginEvidenceAnalysisResult>,
    /// FormID Findings, or `None` when no combined crash evidence was available.
    pub(crate) formid_findings: Option<FormIDFindingAnalysisResult>,
    /// Named Record Findings, or `None` when analysis was unconfigured or had no evidence.
    pub(crate) named_record_findings: Option<NamedRecordFindingAnalysisResult>,
}

impl AutoscanReportContributions {
    /// Returns the number of individual Crash Suspect Findings.
    pub(crate) fn suspect_count(&self) -> usize {
        self.crash_suspects
            .as_ref()
            .map_or(0, |result| result.findings.len())
    }

    /// Returns the total number of FormID occurrences retained by semantic analysis.
    pub(crate) fn formid_count(&self) -> usize {
        self.formid_findings.as_ref().map_or(0, |result| {
            result
                .findings
                .iter()
                .map(|finding| finding.occurrences as usize)
                .sum()
        })
    }
}

/// Borrowed prepared evidence needed by the semantic contribution collector.
#[derive(Clone, Copy)]
pub(crate) struct AutoscanReportCollectionInput<'a> {
    /// Final section-aware Crashgen settings parsed from this Crash Log.
    pub(crate) crashgen_settings: &'a CrashgenSettingsSnapshot,
    /// Installed module names used by settings predicates and Mod Guidance.
    pub(crate) xse_modules: &'a HashSet<String>,
    /// Parsed Crashgen version, when available.
    pub(crate) crashgen_version: Option<(u32, u32, u32)>,
    /// Detected Crashgen configuration layout.
    pub(crate) config_layout: ConfigLayout,
    /// Whether fake bot-compatible mode suppresses Crashgen Settings Analysis.
    pub(crate) fake_bot_compatible_mode: bool,
    /// Main error text used by Crash Suspect analysis.
    pub(crate) main_error: &'a str,
    /// Combined call-stack, register, and stack-dump evidence as individual lines.
    pub(crate) combined_crash_lines: &'a [String],
    /// Combined crash evidence as one string for Crash Suspect stack matching.
    pub(crate) combined_crash_text: &'a str,
    /// System segment lines used to derive optional GPU facts.
    pub(crate) system_segment_lines: &'a [String],
    /// Parsed plugins in load-order order, or `None` when parsing did not run or failed.
    pub(crate) plugins: Option<&'a IndexMap<String, String>>,
}

/// Coordinates immutable semantic analyzers for one prepared Crash Log.
pub(crate) struct AutoscanReportContributionCollector<'a> {
    crashgen_settings: &'a CrashgenSettingsAnalyzer,
    crash_suspects: &'a CrashSuspectAnalyzer,
    mod_guidance: &'a ModGuidanceAnalyzer,
    plugin_evidence: &'a PluginEvidenceAnalyzer,
    formid_findings: &'a FormIDFindingAnalyzer,
    named_record_findings: Option<&'a NamedRecordFindingAnalyzer>,
}

impl<'a> AutoscanReportContributionCollector<'a> {
    /// Borrows the immutable analyzers reused by concurrent per-log collection.
    pub(crate) fn new(
        crashgen_settings: &'a CrashgenSettingsAnalyzer,
        crash_suspects: &'a CrashSuspectAnalyzer,
        mod_guidance: &'a ModGuidanceAnalyzer,
        plugin_evidence: &'a PluginEvidenceAnalyzer,
        formid_findings: &'a FormIDFindingAnalyzer,
        named_record_findings: Option<&'a NamedRecordFindingAnalyzer>,
    ) -> Self {
        Self {
            crashgen_settings,
            crash_suspects,
            mod_guidance,
            plugin_evidence,
            formid_findings,
            named_record_findings,
        }
    }

    /// Runs every applicable semantic analyzer without rendering report text.
    ///
    /// A present empty aggregate means its analysis completed without findings;
    /// absence means the prepared evidence did not admit that analysis. Analyzer
    /// failures abort collection and become the existing per-log analysis error,
    /// except FormID Value Lookup failures: values are optional enrichment, so
    /// collection retries operational or malformed lookup failures with lookup
    /// disabled.
    pub(crate) async fn collect(
        &self,
        input: AutoscanReportCollectionInput<'_>,
    ) -> Result<AutoscanReportContributions> {
        let crashgen_settings =
            if !input.fake_bot_compatible_mode && !input.crashgen_settings.is_empty() {
                Some(
                    self.crashgen_settings
                        .analyze(CrashgenSettingsAnalysisInput {
                            settings: input.crashgen_settings.clone(),
                            installed_plugins: input.xse_modules.clone(),
                            crashgen_version: input.crashgen_version,
                            config_layout: input.config_layout,
                        })
                        .map_err(analyzer_failure)?,
                )
            } else {
                None
            };

        let crash_suspects = Some(
            self.crash_suspects
                .analyze(CrashSuspectAnalysisInput {
                    main_error: input.main_error.to_string(),
                    call_stack: input.combined_crash_text.to_string(),
                })
                .map_err(analyzer_failure)?,
        );

        let mod_guidance = if let Some(plugins) = input.plugins {
            Some(
                self.mod_guidance
                    .analyze(ModGuidanceAnalysisInput {
                        plugins: plugins.clone(),
                        user_gpu: detected_gpu(input.system_segment_lines),
                        xse_modules: input.xse_modules.clone(),
                    })
                    .map_err(analyzer_failure)?,
            )
        } else {
            None
        };

        let plugin_evidence =
            if let Some(plugins) = input.plugins.filter(|plugins| !plugins.is_empty()) {
                Some(
                    self.plugin_evidence
                        .analyze(PluginEvidenceAnalysisInput {
                            call_stack: input.combined_crash_lines.to_vec(),
                            plugins: plugins.keys().cloned().collect(),
                        })
                        .map_err(analyzer_failure)?,
                )
            } else {
                None
            };

        let formid_findings = if input.combined_crash_lines.is_empty() {
            None
        } else {
            let analysis_input = || FormIDFindingAnalysisInput {
                crash_lines: input.combined_crash_lines.to_vec(),
                plugins: input
                    .plugins
                    .into_iter()
                    .flat_map(|plugins| plugins.iter())
                    .map(|(name, prefix)| FormIDPlugin {
                        name: name.clone(),
                        prefix: prefix.clone(),
                    })
                    .collect(),
            };
            let result = match self.formid_findings.analyze(analysis_input()).await {
                Ok(result) => result,
                Err(error)
                    if matches!(
                        error.code(),
                        AnalyzerErrorCode::MalformedResult | AnalyzerErrorCode::OperationalFailure
                    ) =>
                {
                    // FormID descriptions are optional report enrichment, so a broken database
                    // must not discard the suspects that were already extracted from the log.
                    FormIDFindingAnalyzer::new(FormIdValueLookup::disabled())
                        .analyze(analysis_input())
                        .await
                        .map_err(analyzer_failure)?
                }
                Err(error) => return Err(analyzer_failure(error)),
            };
            Some(result)
        };

        let named_record_findings = if input.combined_crash_lines.is_empty() {
            None
        } else if let Some(analyzer) = self.named_record_findings {
            Some(
                analyzer
                    .analyze(NamedRecordFindingAnalysisInput {
                        crash_lines: input.combined_crash_lines.to_vec(),
                    })
                    .map_err(analyzer_failure)?,
            )
        } else {
            None
        };

        Ok(AutoscanReportContributions {
            crashgen_settings,
            crash_suspects,
            mod_guidance,
            plugin_evidence,
            formid_findings,
            named_record_findings,
        })
    }
}

/// Converts the shared analyzer envelope into the established per-log failure shape.
fn analyzer_failure(error: AnalyzerError) -> ScanLogError {
    ScanLogError::AnalysisError(error.formatted_message())
}

/// Derives the normalized optional GPU manufacturer consumed by Mod Guidance.
fn detected_gpu(system_segment_lines: &[String]) -> Option<String> {
    if system_segment_lines.is_empty() {
        return None;
    }

    let gpu_info = GpuDetector::get_gpu_info(system_segment_lines);
    let manufacturer = gpu_info.manufacturer.as_str();
    (manufacturer != "Unknown").then(|| manufacturer.to_lowercase())
}

#[cfg(test)]
#[path = "autoscan_report_contribution_collector_tests.rs"]
mod tests;
