//! Settings Validator - Crash generator settings validation
//!
//! This module validates crash generator settings for:
//! - YAML-backed Crashgen Expectations
//! - Disabled settings detection
//!
//! `scan_all_settings()` runs the configured Crashgen Expectations when present
//! and appends Disabled Setting Notices for all non-ignored disabled settings.

use crate::crashgen_registry::CrashgenEntry;
use crate::error::Result;
use crate::report::{AutoscanReportContribution, CrashgenExpectationContribution, ReportFragment};
use classic_config_core::{
    AutoscanReportPlacement, ConfigLayout, CrashgenSettingsSnapshot, EvaluationContext,
    evaluate_rules,
};
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
    /// Pre-resolved registry entry for this crashgen.
    entry: CrashgenEntry,
}

impl SettingsValidator {
    /// Creates a new settings validator from a pre-resolved crashgen name and entry.
    ///
    /// # Arguments
    ///
    /// * `crashgen_name` - Display name of the crash generator (e.g., `"Buffout 4"`)
    /// * `entry` - Pre-resolved `CrashgenEntry` from the `CrashgenRegistry`
    pub fn new(crashgen_name: String, entry: CrashgenEntry) -> Self {
        Self {
            crashgen_name,
            entry,
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
        let mut contributions = Vec::new();

        if let Some(rules) = self.entry.settings_rules.as_ref() {
            let context = EvaluationContext {
                crashgen_name: self.crashgen_name.clone(),
                display_section: self.entry.display_section.clone(),
                installed_plugins: xse_modules.clone(),
                settings: crashgen.clone(),
                config_layout,
                crashgen_version,
            };
            let evaluation = evaluate_rules(rules, &context);

            for outcome in evaluation.outcomes {
                contributions.push(AutoscanReportContribution::CrashgenExpectation(
                    CrashgenExpectationContribution {
                        kind: outcome.kind,
                        severity: outcome.severity,
                        message: outcome.message,
                        fix: outcome.fix,
                        placement: outcome.bucket,
                    },
                ));
            }
        }

        contributions.extend(self.disabled_setting_notice_contributions(crashgen));

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
        let lines = self
            .disabled_setting_notice_contributions(crashgen)
            .into_iter()
            .filter_map(|contribution| {
                contribution
                    .legacy_settings_fragment()
                    .map(|(_, fragment)| fragment.to_list())
            })
            .flatten()
            .collect();

        Ok(ReportFragment::from_lines(lines))
    }

    fn disabled_setting_notice_contributions(
        &self,
        crashgen: &CrashgenSettingsSnapshot,
    ) -> Vec<AutoscanReportContribution> {
        let mut contributions = Vec::new();
        for setting in crashgen.final_settings() {
            let setting_name = setting.key.to_string();

            if let Ok(false) = setting.value.parse::<bool>()
                && !self.entry.ignore_keys.contains(&setting_name)
            {
                contributions.push(AutoscanReportContribution::DisabledSettingNotice {
                    setting_name,
                    crashgen_name: self.crashgen_name.clone(),
                });
            }
        }

        contributions
    }
}

#[cfg(test)]
#[path = "settings_validator_tests.rs"]
mod tests;
