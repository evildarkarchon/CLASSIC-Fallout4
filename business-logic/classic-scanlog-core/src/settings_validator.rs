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
use crate::report::ReportFragment;
use classic_config_core::{
    ConfigLayout, EvaluationContext, EvaluationOutcome, OutcomeKind, RuleReportBucket,
    RuleSeverity, evaluate_rules,
};
use std::collections::{HashMap, HashSet};

#[derive(Clone, Debug)]
pub(crate) struct BucketedSettingsFragment {
    pub bucket: RuleReportBucket,
    pub fragment: ReportFragment,
}

impl BucketedSettingsFragment {
    fn new(bucket: RuleReportBucket, fragment: ReportFragment) -> Self {
        Self { bucket, fragment }
    }

    fn settings(fragment: ReportFragment) -> Self {
        Self::new(RuleReportBucket::Settings, fragment)
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
        crashgen: &HashMap<String, String>,
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
        crashgen: &HashMap<String, String>,
        xse_modules: &HashSet<String>,
        crashgen_version: Option<(u32, u32, u32)>,
        config_layout: ConfigLayout,
    ) -> Result<Vec<BucketedSettingsFragment>> {
        let mut fragments = Vec::new();

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
                let mut lines = Vec::new();
                lines.extend(match outcome.bucket {
                    RuleReportBucket::Settings => self.render_settings_bucket_lines(&outcome),
                    RuleReportBucket::ErrorInformation => {
                        self.render_error_information_bucket_lines(&outcome)
                    }
                });
                fragments.push(BucketedSettingsFragment::new(
                    outcome.bucket,
                    ReportFragment::from_lines(lines),
                ));
            }
        }

        let disabled_fragment = self.check_disabled_settings(crashgen)?;
        if !disabled_fragment.is_empty() {
            fragments.push(BucketedSettingsFragment::settings(disabled_fragment));
        }

        Ok(fragments)
    }

    fn render_settings_bucket_lines(&self, outcome: &EvaluationOutcome) -> Vec<String> {
        let mut lines = Vec::new();
        match outcome.kind {
            OutcomeKind::Issue => {
                lines.push(format!("# ❌ CAUTION : {} # \n", outcome.message));
                if let Some(fix) = outcome.fix.as_deref() {
                    lines.push(format!(" FIX: {}\n\n-----\n", fix));
                } else {
                    lines.push("\n-----\n".to_string());
                }
            }
            OutcomeKind::Notice => {
                lines.push(format!(
                    "# {} NOTICE : {} # \n",
                    Self::notice_icon(outcome.severity),
                    outcome.message
                ));
                if let Some(fix) = outcome.fix.as_deref() {
                    lines.push(format!(" {}\n\n-----\n", fix));
                } else {
                    lines.push("\n-----\n".to_string());
                }
            }
            OutcomeKind::Success => {
                lines.push(format!("✔️ {}\n\n-----\n", outcome.message));
            }
        }
        lines
    }

    fn render_error_information_bucket_lines(&self, outcome: &EvaluationOutcome) -> Vec<String> {
        let mut lines = Vec::new();
        match outcome.kind {
            OutcomeKind::Issue => {
                lines.push(format!("**# ❌ CAUTION : {} #**\n\n", outcome.message));
                if let Some(fix) = outcome.fix.as_deref() {
                    lines.push(format!("FIX: {}\n\n", fix));
                }
            }
            OutcomeKind::Notice => {
                lines.push(format!(
                    "**# {} NOTICE : {} #**\n\n",
                    Self::notice_icon(outcome.severity),
                    outcome.message
                ));
                if let Some(fix) = outcome.fix.as_deref() {
                    lines.push(format!("{}\n\n", fix));
                }
            }
            OutcomeKind::Success => {
                lines.push(format!("**✔️ {}**\n\n", outcome.message));
            }
        }
        lines
    }

    fn notice_icon(severity: RuleSeverity) -> &'static str {
        if severity == RuleSeverity::Error {
            "❌"
        } else if severity == RuleSeverity::Warning {
            "⚠️"
        } else {
            "[!]"
        }
    }

    /// Check for disabled settings in crash generator configuration.
    ///
    /// This check runs universally for every crashgen (not gated on named checks).
    /// Uses `self.entry.ignore_keys` as the skip set — for the default entry this
    /// is empty, so all disabled settings are flagged.
    pub fn check_disabled_settings(
        &self,
        crashgen: &HashMap<String, String>,
    ) -> Result<ReportFragment> {
        let mut lines = Vec::new();

        for (key, value) in crashgen.iter() {
            let setting_name = key.clone();

            if let Ok(false) = value.parse::<bool>() {
                if !self.entry.ignore_keys.contains(&setting_name) {
                    lines.push(format!(
                        "* NOTICE : {} is disabled in your {} settings, is this intentional? * \n\n-----\n",
                        setting_name, self.crashgen_name
                    ));
                }
            }
        }

        Ok(ReportFragment::from_lines(lines))
    }
}

#[cfg(test)]
#[path = "settings_validator_tests.rs"]
mod tests;
