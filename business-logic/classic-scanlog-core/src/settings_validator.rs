//! Settings Validator - Crash generator settings validation
//!
//! This module validates crash generator settings for:
//! - Achievements mod compatibility (named check — only when registered)
//! - Memory management settings with X-Cell/ScrapHeap detection (named check)
//! - Archive limit settings (named check)
//! - LooksMenu (F4EE) compatibility (named check)
//! - Disabled settings detection (universal — runs for all crashgens)
//!
//! Named checks run only when their `CheckId` is listed in the crashgen's
//! registry entry. `check_disabled_settings()` always runs for every crashgen.

use crate::crashgen_registry::{CheckId, CrashgenEntry};
use crate::error::Result;
use crate::report::ReportFragment;
use classic_config_core::{
    ConfigLayout, EvaluationContext, EvaluationOutcome, OutcomeKind, RuleReportBucket,
    RuleSeverity, evaluate_rules,
};
use log::warn;
use std::collections::{HashMap, HashSet};

const DEFAULT_DISPLAY_SECTION: &str = "[Compatibility]";

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
/// `CrashgenRegistry` before the scan begins). Named checks are gated on
/// the entry's `checks` list; `check_disabled_settings()` always runs.
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

    /// Run all settings checks, preferring YAML-defined rules when available.
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

            let mut fragments = Vec::new();
            let mut covered_achievements = false;
            let mut covered_memory = false;
            let mut covered_archive = false;
            let mut covered_looksmenu = false;

            for outcome in evaluation.outcomes {
                let mut lines = Vec::new();
                if let Some(setting) = outcome.setting.as_deref() {
                    match setting {
                        "Achievements" => covered_achievements = true,
                        "MemoryManager"
                        | "HavokMemorySystem"
                        | "BSTextureStreamerLocalHeap"
                        | "ScaleformAllocator"
                        | "SmallBlockAllocator" => covered_memory = true,
                        "ArchiveLimit" => covered_archive = true,
                        "F4EE" => covered_looksmenu = true,
                        _ => {}
                    }
                }

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

            if evaluation.skip_remaining {
                return Ok(fragments);
            }

            if !covered_achievements {
                let achievements_fragment =
                    self.scan_buffout_achievements_setting(xse_modules.clone(), crashgen)?;
                if !achievements_fragment.is_empty() {
                    fragments.push(BucketedSettingsFragment::settings(achievements_fragment));
                }
            }

            if !covered_memory {
                let has_xcell = [
                    "x-cell-fo4.dll",
                    "x-cell-og.dll",
                    "x-cell-ng2.dll",
                    "x-cell-ae.dll",
                ]
                .iter()
                .any(|dll| xse_modules.contains(*dll));
                let has_old_xcell = false;
                let has_baka_scrapheap = xse_modules.contains("bakascrapheap.dll");
                let memory_fragment = self.scan_buffout_memorymanagement_settings(
                    crashgen,
                    has_xcell,
                    has_old_xcell,
                    has_baka_scrapheap,
                )?;
                if !memory_fragment.is_empty() {
                    fragments.push(BucketedSettingsFragment::settings(memory_fragment));
                }
            }

            if !covered_archive {
                let archive_fragment =
                    self.scan_archivelimit_setting(crashgen, crashgen_version)?;
                if !archive_fragment.is_empty() {
                    fragments.push(BucketedSettingsFragment::settings(archive_fragment));
                }
            }

            if !covered_looksmenu {
                let looksmenu_fragment =
                    self.scan_buffout_looksmenu_setting(crashgen, xse_modules.clone())?;
                if !looksmenu_fragment.is_empty() {
                    fragments.push(BucketedSettingsFragment::settings(looksmenu_fragment));
                }
            }

            return Ok(fragments);
        }

        // No settings_rules defined -- return empty (no legacy fallback)
        Ok(Vec::new())
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

    /// Scan for Achievements mod conflicts.
    ///
    /// Runs only when `CheckId::Achievements` is in the crashgen's registry checks.
    pub fn scan_buffout_achievements_setting(
        &self,
        xse_modules: HashSet<String>,
        crashgen: &HashMap<String, String>,
    ) -> Result<ReportFragment> {
        if !self.entry.checks.contains(&CheckId::Achievements) {
            return Ok(ReportFragment::empty());
        }

        let mut lines = Vec::new();

        let achievements = crashgen
            .get("Achievements")
            .and_then(|v| v.parse::<bool>().ok())
            .unwrap_or(false);

        if achievements
            && (xse_modules.contains("achievements.dll")
                || xse_modules.contains("unlimitedsurvivalmode.dll"))
        {
            lines.push("# ❌ CAUTION : The Achievements Mod and/or Unlimited Survival Mode is installed, but Achievements is set to TRUE # \n".to_string());
            lines.push(format!(
                " FIX: Open {}'s TOML file and change Achievements to FALSE, this prevents conflicts with {}.\n\n-----\n",
                self.crashgen_name, self.crashgen_name
            ));
        } else {
            lines.push(format!(
                "✔️ Achievements parameter is correctly configured in your {} settings! \n\n-----\n",
                self.crashgen_name
            ));
        }

        Ok(ReportFragment::from_lines(lines))
    }

    /// Analyze and validate memory management settings.
    ///
    /// Runs only when `CheckId::MemoryManagement` is in the crashgen's registry checks.
    pub fn scan_buffout_memorymanagement_settings(
        &self,
        crashgen: &HashMap<String, String>,
        has_xcell: bool,
        has_old_xcell: bool,
        has_baka_scrapheap: bool,
    ) -> Result<ReportFragment> {
        if !self.entry.checks.contains(&CheckId::MemoryManagement) {
            return Ok(ReportFragment::empty());
        }

        let mut lines = Vec::new();
        let separator = "\n\n-----\n";

        // Check for old X-Cell version first
        if has_old_xcell {
            Self::add_warning(
                &mut lines,
                "You have an old version of X-Cell/Addictol installed, please update it to the latest version.",
                "Download the latest version from here: https://www.nexusmods.com/fallout4/mods/84214?tab=files",
                separator,
            );
        }

        // Validate main memory manager configuration
        let mem_manager_enabled = crashgen
            .get("MemoryManager")
            .and_then(|v| v.parse::<bool>().ok())
            .unwrap_or(false);

        self.validate_memory_config(
            &mut lines,
            mem_manager_enabled,
            has_xcell,
            has_baka_scrapheap,
            separator,
        );

        // Check X-Cell specific settings
        if has_xcell {
            self.validate_xcell_settings(&mut lines, crashgen, separator)?;
        }

        Ok(ReportFragment::from_lines(lines))
    }

    /// Scan and validate the ArchiveLimit setting.
    ///
    /// Runs only when `CheckId::ArchiveLimit` is in the crashgen's registry checks.
    pub fn scan_archivelimit_setting(
        &self,
        crashgen: &HashMap<String, String>,
        crashgen_version: Option<(u32, u32, u32)>,
    ) -> Result<ReportFragment> {
        if !self.entry.checks.contains(&CheckId::ArchiveLimit) {
            return Ok(ReportFragment::empty());
        }

        // Skip check for versions >= 1.29.0
        if let Some((major, minor, _)) = crashgen_version {
            if major > 1 || (major == 1 && minor >= 29) {
                return Ok(ReportFragment::empty());
            }
        }

        let mut lines = Vec::new();

        let archive_limit = crashgen
            .get("ArchiveLimit")
            .and_then(|v| v.parse::<bool>().ok())
            .unwrap_or(false);

        if archive_limit {
            lines.push("# ❌ CAUTION : ArchiveLimit is set to TRUE, this setting is known to cause instability. # \n".to_string());
            lines.push(format!(
                " FIX: Open {}'s TOML file and change ArchiveLimit to FALSE.\n\n-----\n",
                self.crashgen_name
            ));
        } else {
            lines.push(format!(
                "✔️ ArchiveLimit parameter is correctly configured in your {} settings! \n\n-----\n",
                self.crashgen_name
            ));
        }

        Ok(ReportFragment::from_lines(lines))
    }

    /// Analyze LooksMenu (F4EE) setting for compatibility.
    ///
    /// Runs only when `CheckId::LooksMenu` is in the crashgen's registry checks.
    /// The warning message references `self.entry.display_section` instead of
    /// the hardcoded string `[Compatibility]`.
    pub fn scan_buffout_looksmenu_setting(
        &self,
        crashgen: &HashMap<String, String>,
        xse_modules: HashSet<String>,
    ) -> Result<ReportFragment> {
        if !self.entry.checks.contains(&CheckId::LooksMenu) {
            return Ok(ReportFragment::empty());
        }

        let mut lines = Vec::new();

        if let Some(f4ee) = crashgen.get("F4EE") {
            let f4ee_enabled = match f4ee.parse::<bool>() {
                Ok(value) => value,
                Err(parse_error) => {
                    warn!(
                        "Invalid boolean value for F4EE in {} settings: {:?} ({})",
                        self.crashgen_name, f4ee, parse_error
                    );
                    false
                }
            };
            let display_section = if self.entry.display_section.is_empty() {
                DEFAULT_DISPLAY_SECTION
            } else {
                self.entry.display_section.as_str()
            };

            if !f4ee_enabled && xse_modules.contains("f4ee.dll") {
                lines.push(format!(
                    "# ❌ CAUTION : Looks Menu is installed, but F4EE parameter under {} is set to FALSE # \n",
                    display_section
                ));
                lines.push(format!(
                    " FIX: Open {}'s TOML file and change F4EE to TRUE, this prevents bugs and crashes from Looks Menu.\n\n-----\n",
                    self.crashgen_name
                ));
            } else {
                lines.push(format!(
                    "✔️ F4EE (Looks Menu) parameter is correctly configured in your {} settings! \n\n-----\n",
                    self.crashgen_name
                ));
            }
        }

        Ok(ReportFragment::from_lines(lines))
    }

    /// Scaffold for Addictol-specific TOML checks.
    ///
    /// This intentionally returns an informational fragment only. Concrete Addictol
    /// checks will be added in follow-up work and should be implemented here.
    pub fn scan_addictol_settings_scaffold(
        &self,
        _crashgen: &HashMap<String, String>,
    ) -> Result<ReportFragment> {
        Ok(ReportFragment::from_lines(vec![
            "# [!] NOTICE : Addictol detected — using Addictol TOML checks scaffold (rules pending). # \n\n-----\n"
                .to_string(),
        ]))
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

impl SettingsValidator {
    /// Add a success message
    fn add_success(lines: &mut Vec<String>, message: &str, separator: &str) {
        lines.push(format!("✔️ {}{}", message, separator));
    }

    /// Add a warning with fix instructions
    fn add_warning(lines: &mut Vec<String>, warning: &str, fix: &str, separator: &str) {
        lines.push(format!("# ❌ CAUTION : {} # \n", warning));
        lines.push(format!(" FIX: {}{}", fix, separator));
    }

    /// Validate memory manager configuration based on installed mods
    fn validate_memory_config(
        &self,
        lines: &mut Vec<String>,
        mem_enabled: bool,
        has_xcell: bool,
        has_baka: bool,
        separator: &str,
    ) {
        let config = (mem_enabled, has_xcell, has_baka);

        match config {
            (true, true, false) => {
                Self::add_warning(
                    lines,
                    "X-Cell/Addictol is installed, but MemoryManager parameter is set to TRUE",
                    &format!(
                        "Open {}'s TOML file and change MemoryManager to FALSE, this prevents conflicts with X-Cell/Addictol.",
                        self.crashgen_name
                    ),
                    separator,
                );
            }
            (true, false, true) => {
                Self::add_warning(
                    lines,
                    &format!(
                        "The Baka ScrapHeap Mod is installed, but is redundant with {}",
                        self.crashgen_name
                    ),
                    &format!(
                        "Uninstall the Baka ScrapHeap Mod, this prevents conflicts with {}.",
                        self.crashgen_name
                    ),
                    separator,
                );
            }
            (true, false, false) => {
                Self::add_success(
                    lines,
                    &format!(
                        "Memory Manager parameter is correctly configured in your {} settings!",
                        self.crashgen_name
                    ),
                    separator,
                );
            }
            (false, true, true) => {
                Self::add_warning(
                    lines,
                    "The Baka ScrapHeap Mod is installed, but is redundant with X-Cell/Addictol",
                    "Uninstall the Baka ScrapHeap Mod, this prevents conflicts with X-Cell/Addictol.",
                    separator,
                );
            }
            (false, true, false) => {
                Self::add_success(
                    lines,
                    &format!(
                        "Memory Manager parameter is correctly configured for use with X-Cell/Addictol in your {} settings!",
                        self.crashgen_name
                    ),
                    separator,
                );
            }
            (false, false, true) => {
                Self::add_warning(
                    lines,
                    &format!(
                        "The Baka ScrapHeap Mod is installed, but is redundant with {}",
                        self.crashgen_name
                    ),
                    &format!(
                        "Uninstall the Baka ScrapHeap Mod and open {}'s TOML file and change MemoryManager to TRUE, this improves performance.",
                        self.crashgen_name
                    ),
                    separator,
                );
            }
            _ => {} // (false, false, false) - no action needed
        }
    }

    /// Validate X-Cell specific memory settings
    fn validate_xcell_settings(
        &self,
        lines: &mut Vec<String>,
        crashgen: &HashMap<String, String>,
        separator: &str,
    ) -> Result<()> {
        let memory_settings = [
            ("HavokMemorySystem", "Havok Memory System"),
            ("BSTextureStreamerLocalHeap", "BSTextureStreamerLocalHeap"),
            ("ScaleformAllocator", "Scaleform Allocator"),
            ("SmallBlockAllocator", "Small Block Allocator"),
        ];

        for (setting_key, display_name) in &memory_settings {
            let setting_enabled = crashgen
                .get(*setting_key)
                .and_then(|v| v.parse::<bool>().ok())
                .unwrap_or(false);

            if setting_enabled {
                Self::add_warning(
                    lines,
                    &format!(
                        "X-Cell/Addictol is installed, but {} parameter is set to TRUE",
                        setting_key
                    ),
                    &format!(
                        "Open {}'s TOML file and change {} to FALSE, this prevents conflicts with X-Cell/Addictol.",
                        self.crashgen_name, setting_key
                    ),
                    separator,
                );
            } else {
                Self::add_success(
                    lines,
                    &format!(
                        "{} parameter is correctly configured for use with X-Cell/Addictol in your {} settings!",
                        display_name, self.crashgen_name
                    ),
                    separator,
                );
            }
        }

        Ok(())
    }
}

#[cfg(test)]
#[path = "settings_validator_tests.rs"]
mod tests;
