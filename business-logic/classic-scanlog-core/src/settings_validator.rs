//! Settings Validator - Crash generator settings validation
//!
//! This module validates crash generator settings for:
//! - YAML-backed Crashgen Expectations
//! - Disabled settings detection
//!
//! `scan_all_settings()` runs the configured Crashgen Expectations when present
//! and appends Disabled Setting Notices for all non-ignored disabled settings.

use crate::crashgen_registry::CrashgenEntry;
use crate::crashgen_settings_analyzer::{
    CrashgenSettingsAnalysisInput, CrashgenSettingsAnalysisResult, CrashgenSettingsAnalyzer,
};
use crate::error::{Result, ScanLogError};
use crate::report::{AutoscanReportContribution, CrashgenExpectationContribution, ReportFragment};
use classic_config_core::{AutoscanReportPlacement, ConfigLayout, CrashgenSettingsSnapshot};
use std::collections::HashSet;

#[derive(Clone, Debug)]
pub(crate) struct BucketedSettingsFragment {
    #[allow(dead_code)]
    pub bucket: AutoscanReportPlacement,
    pub fragment: ReportFragment,
}

impl BucketedSettingsFragment {
    fn new(bucket: AutoscanReportPlacement, fragment: ReportFragment) -> Self {
        Self { bucket, fragment }
    }
}

/// Settings validator driven by per-crashgen registry entries.
///
/// Constructed with a pre-resolved `CrashgenEntry` (looked up from the
/// `CrashgenRegistry` before the scan begins). YAML-backed Crashgen
/// Expectations are the only per-crashgen expectation source.
#[derive(Clone)]
pub struct SettingsValidator {
    /// Resolved crashgen name for use in human-readable messages.
    crashgen_name: String,
    /// Validated semantic analyzer constructed once for this compatibility facade.
    analyzer: std::result::Result<CrashgenSettingsAnalyzer, crate::AnalyzerError>,
}

impl SettingsValidator {
    /// Creates a new settings validator from a pre-resolved crashgen name and entry.
    ///
    /// # Arguments
    ///
    /// * `crashgen_name` - Display name of the crash generator (e.g., `"Buffout 4"`)
    /// * `entry` - Pre-resolved `CrashgenEntry` from the `CrashgenRegistry`
    pub fn new(crashgen_name: String, entry: CrashgenEntry) -> Self {
        let analyzer = CrashgenSettingsAnalyzer::new(crashgen_name.clone(), entry);
        Self {
            crashgen_name,
            analyzer,
        }
    }

    /// Run all YAML-backed Crashgen Expectations and Disabled Setting Notices.
    pub fn scan_all_settings(
        &self,
        crashgen: &CrashgenSettingsSnapshot,
        xse_modules: &HashSet<String>,
        crashgen_version: Option<(u32, u32, u32)>,
        config_layout: ConfigLayout,
    ) -> Result<Vec<ReportFragment>> {
        Ok(self
            .scan_all_settings_bucketed(crashgen, xse_modules, crashgen_version, config_layout)?
            .into_iter()
            .map(|fragment| fragment.fragment)
            .collect())
    }

    pub(crate) fn scan_all_settings_bucketed(
        &self,
        crashgen: &CrashgenSettingsSnapshot,
        xse_modules: &HashSet<String>,
        crashgen_version: Option<(u32, u32, u32)>,
        config_layout: ConfigLayout,
    ) -> Result<Vec<BucketedSettingsFragment>> {
        Ok(self
            .scan_all_settings_contributions(
                crashgen,
                xse_modules,
                crashgen_version,
                config_layout,
            )?
            .into_iter()
            .filter_map(|contribution| {
                contribution
                    .legacy_settings_fragment()
                    .map(|(bucket, fragment)| BucketedSettingsFragment::new(bucket, fragment))
            })
            .collect())
    }

    pub(crate) fn scan_all_settings_contributions(
        &self,
        crashgen: &CrashgenSettingsSnapshot,
        xse_modules: &HashSet<String>,
        crashgen_version: Option<(u32, u32, u32)>,
        config_layout: ConfigLayout,
    ) -> Result<Vec<AutoscanReportContribution>> {
        let analysis = self.analyze(crashgen, xse_modules, crashgen_version, config_layout)?;
        let mut contributions = analysis
            .expectation_outcomes
            .into_iter()
            .map(|outcome| {
                AutoscanReportContribution::CrashgenExpectation(CrashgenExpectationContribution {
                    kind: outcome.kind,
                    severity: outcome.severity,
                    message: outcome.message,
                    fix: outcome.fix,
                    placement: outcome.placement,
                })
            })
            .collect::<Vec<_>>();
        contributions.extend(analysis.disabled_setting_notices.into_iter().map(|notice| {
            AutoscanReportContribution::DisabledSettingNotice {
                setting_name: notice.setting_name,
                crashgen_name: self.crashgen_name.clone(),
            }
        }));

        Ok(contributions)
    }

    /// Check for disabled settings in crash generator configuration.
    ///
    /// This check runs universally for every crashgen (not gated on named checks).
    /// Uses `self.entry.ignore_keys` as the skip set — for the default entry this
    /// is empty, so all disabled settings are flagged.
    pub fn check_disabled_settings(
        &self,
        crashgen: &CrashgenSettingsSnapshot,
    ) -> Result<ReportFragment> {
        let analysis = self.analyze(crashgen, &HashSet::new(), None, ConfigLayout::Unknown)?;
        let lines = analysis
            .disabled_setting_notices
            .into_iter()
            .flat_map(|notice| {
                AutoscanReportContribution::DisabledSettingNotice {
                    setting_name: notice.setting_name,
                    crashgen_name: self.crashgen_name.clone(),
                }
                .legacy_settings_fragment()
                .map(|(_, fragment)| fragment.to_list())
                .unwrap_or_default()
            })
            .collect();

        Ok(ReportFragment::from_lines(lines))
    }

    fn analyze(
        &self,
        crashgen: &CrashgenSettingsSnapshot,
        xse_modules: &HashSet<String>,
        crashgen_version: Option<(u32, u32, u32)>,
        config_layout: ConfigLayout,
    ) -> Result<CrashgenSettingsAnalysisResult> {
        let analyzer = self.analyzer.as_ref().map_err(|error| {
            ScanLogError::ConfigError(format!(
                "{} [{}]: {}",
                error.analyzer().as_str(),
                error.code().as_str(),
                error.message()
            ))
        })?;
        analyzer
            .analyze(CrashgenSettingsAnalysisInput {
                settings: crashgen.clone(),
                installed_plugins: xse_modules.clone(),
                crashgen_version,
                config_layout,
            })
            .map_err(|error| {
                ScanLogError::AnalysisError(format!(
                    "{} [{}]: {}",
                    error.analyzer().as_str(),
                    error.code().as_str(),
                    error.message()
                ))
            })
    }
}

#[cfg(test)]
#[path = "settings_validator_tests.rs"]
mod tests;
