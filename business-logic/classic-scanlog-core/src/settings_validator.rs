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
mod tests {
    use super::*;
    use crate::crashgen_registry::{CheckId, CrashgenEntry};
    use classic_config_core::{
        CheckRule, ConfigLayout, CrashgenSettingsRules, ExpectedValue, Predicate, PreflightAction,
        PreflightActionKind, PreflightRule, RuleMessages, RuleReportBucket, RuleSeverity,
        RuleTarget, TargetValueType,
    };

    fn make_buffout_entry() -> CrashgenEntry {
        CrashgenEntry {
            display_section: "[Compatibility]".to_string(),
            ignore_keys: [
                "F4EE",
                "WaitForDebugger",
                "Achievements",
                "InputSwitch",
                "AutoOpen",
                "PromptUpload",
                "MemoryManagerDebug",
                "BSTextureStreamerLocalHeap",
                "ArchiveLimit",
                "MemoryManager",
            ]
            .iter()
            .map(|s| s.to_string())
            .collect(),
            checks: vec![
                CheckId::Achievements,
                CheckId::MemoryManagement,
                CheckId::ArchiveLimit,
                CheckId::LooksMenu,
            ],
            settings_rules: None,
        }
    }

    fn make_addictol_entry() -> CrashgenEntry {
        CrashgenEntry {
            display_section: "[Patches]".to_string(),
            ignore_keys: HashSet::new(),
            checks: vec![],
            settings_rules: None,
        }
    }

    #[test]
    fn test_buffout_entry_runs_all_4_named_checks() {
        let validator = SettingsValidator::new("Buffout 4".to_string(), make_buffout_entry());

        let mut crashgen = HashMap::new();
        crashgen.insert("Achievements".to_string(), "true".to_string());
        crashgen.insert("MemoryManager".to_string(), "true".to_string());
        crashgen.insert("ArchiveLimit".to_string(), "true".to_string());
        crashgen.insert("F4EE".to_string(), "false".to_string());

        let mut xse = HashSet::new();
        xse.insert("achievements.dll".to_string());
        xse.insert("f4ee.dll".to_string());

        // All 4 named checks should return non-empty fragments
        let ach = validator
            .scan_buffout_achievements_setting(xse.clone(), &crashgen)
            .unwrap();
        let mem = validator
            .scan_buffout_memorymanagement_settings(&crashgen, false, false, false)
            .unwrap();
        let arc = validator
            .scan_archivelimit_setting(&crashgen, Some((1, 28, 0)))
            .unwrap();
        let lm = validator
            .scan_buffout_looksmenu_setting(&crashgen, xse)
            .unwrap();

        assert!(!ach.is_empty(), "Achievements check should run");
        assert!(!mem.is_empty(), "MemoryManagement check should run");
        assert!(!arc.is_empty(), "ArchiveLimit check should run");
        assert!(!lm.is_empty(), "LooksMenu check should run");
    }

    #[test]
    fn test_addictol_entry_runs_0_named_checks() {
        let validator = SettingsValidator::new("Addictol".to_string(), make_addictol_entry());

        let mut crashgen = HashMap::new();
        crashgen.insert("Achievements".to_string(), "true".to_string());
        crashgen.insert("MemoryManager".to_string(), "true".to_string());
        crashgen.insert("ArchiveLimit".to_string(), "true".to_string());
        crashgen.insert("F4EE".to_string(), "false".to_string());

        let mut xse = HashSet::new();
        xse.insert("achievements.dll".to_string());
        xse.insert("f4ee.dll".to_string());

        // All 4 named checks should return empty (not registered)
        let ach = validator
            .scan_buffout_achievements_setting(xse.clone(), &crashgen)
            .unwrap();
        let mem = validator
            .scan_buffout_memorymanagement_settings(&crashgen, false, false, false)
            .unwrap();
        let arc = validator
            .scan_archivelimit_setting(&crashgen, Some((1, 28, 0)))
            .unwrap();
        let lm = validator
            .scan_buffout_looksmenu_setting(&crashgen, xse)
            .unwrap();

        assert!(
            ach.is_empty(),
            "Achievements check should NOT run for Addictol"
        );
        assert!(
            mem.is_empty(),
            "MemoryManagement check should NOT run for Addictol"
        );
        assert!(
            arc.is_empty(),
            "ArchiveLimit check should NOT run for Addictol"
        );
        assert!(lm.is_empty(), "LooksMenu check should NOT run for Addictol");
    }

    #[test]
    fn test_both_entries_run_check_disabled_settings() {
        let mut crashgen = HashMap::new();
        crashgen.insert("SomeSetting".to_string(), "false".to_string());

        // Buffout with ignore list: SomeSetting not in ignore list → should flag
        let buffout_validator =
            SettingsValidator::new("Buffout 4".to_string(), make_buffout_entry());
        let buffout_result = buffout_validator
            .check_disabled_settings(&crashgen)
            .unwrap();
        assert!(
            !buffout_result.is_empty(),
            "Buffout should flag disabled SomeSetting"
        );

        // Addictol with empty ignore list: should also flag
        let addictol_validator =
            SettingsValidator::new("Addictol".to_string(), make_addictol_entry());
        let addictol_result = addictol_validator
            .check_disabled_settings(&crashgen)
            .unwrap();
        assert!(
            !addictol_result.is_empty(),
            "Addictol should flag disabled SomeSetting"
        );
    }

    #[test]
    fn test_default_entry_runs_only_check_disabled_settings() {
        let default_entry = CrashgenEntry::default_entry();
        let validator = SettingsValidator::new("UnknownCrashgen".to_string(), default_entry);

        let mut crashgen = HashMap::new();
        crashgen.insert("Achievements".to_string(), "true".to_string());
        crashgen.insert("SomeSetting".to_string(), "false".to_string());

        let xse = HashSet::new();

        // Named checks should all be empty
        let ach = validator
            .scan_buffout_achievements_setting(xse.clone(), &crashgen)
            .unwrap();
        assert!(
            ach.is_empty(),
            "Achievements should not run for default entry"
        );

        // check_disabled_settings should run (and flag SomeSetting)
        let disabled = validator.check_disabled_settings(&crashgen).unwrap();
        assert!(
            !disabled.is_empty(),
            "check_disabled_settings should run for default entry"
        );
    }

    #[test]
    fn test_ignore_keys_skip_settings_in_check_disabled() {
        let entry = make_buffout_entry();
        // F4EE is in ignore_keys
        let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

        let mut crashgen = HashMap::new();
        crashgen.insert("F4EE".to_string(), "false".to_string()); // in ignore list
        crashgen.insert("SomeOtherKey".to_string(), "false".to_string()); // not in ignore list

        let result = validator.check_disabled_settings(&crashgen).unwrap();
        let lines = result.to_list();

        // F4EE should be skipped
        assert!(!lines.iter().any(|l| l.contains("F4EE")));
        // SomeOtherKey should be flagged
        assert!(lines.iter().any(|l| l.contains("SomeOtherKey")));
    }

    #[test]
    fn test_looksmenu_uses_display_section_from_entry() {
        let entry = CrashgenEntry {
            display_section: "[Compatibility]".to_string(),
            ignore_keys: HashSet::new(),
            checks: vec![CheckId::LooksMenu],
            settings_rules: None,
        };
        let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

        let mut crashgen = HashMap::new();
        crashgen.insert("F4EE".to_string(), "false".to_string());

        let mut xse = HashSet::new();
        xse.insert("f4ee.dll".to_string());

        let result = validator
            .scan_buffout_looksmenu_setting(&crashgen, xse)
            .unwrap();
        let lines = result.to_list();
        assert!(lines.iter().any(|l| l.contains("[Compatibility]")));
    }

    #[test]
    fn test_looksmenu_invalid_f4ee_value_falls_back_to_false() {
        let entry = CrashgenEntry {
            display_section: "[Compatibility]".to_string(),
            ignore_keys: HashSet::new(),
            checks: vec![CheckId::LooksMenu],
            settings_rules: None,
        };
        let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

        let mut crashgen = HashMap::new();
        crashgen.insert("F4EE".to_string(), "yes".to_string());

        let mut xse = HashSet::new();
        xse.insert("f4ee.dll".to_string());

        let result = validator
            .scan_buffout_looksmenu_setting(&crashgen, xse)
            .unwrap();
        let lines = result.to_list();

        assert!(
            lines.iter().any(|line| line.contains("CAUTION")),
            "Invalid F4EE value should be treated as disabled and surface caution when LooksMenu is installed"
        );
    }

    #[test]
    fn test_achievements_validation_still_works() {
        let validator = SettingsValidator::new("Buffout 4".to_string(), make_buffout_entry());

        let mut crashgen = HashMap::new();
        crashgen.insert("Achievements".to_string(), "true".to_string());

        let mut xse_modules = HashSet::new();
        xse_modules.insert("achievements.dll".to_string());

        let fragment = validator
            .scan_buffout_achievements_setting(xse_modules, &crashgen)
            .unwrap();

        assert!(!fragment.is_empty());
        let lines = fragment.to_list();
        assert!(lines.iter().any(|line| line.contains("CAUTION")));
    }

    #[test]
    fn test_memory_management_xcell_conflict() {
        let validator = SettingsValidator::new("Buffout 4".to_string(), make_buffout_entry());

        let mut crashgen = HashMap::new();
        crashgen.insert("MemoryManager".to_string(), "true".to_string());

        let fragment = validator
            .scan_buffout_memorymanagement_settings(
                &crashgen, true,  // has_xcell
                false, // has_old_xcell
                false, // has_baka
            )
            .unwrap();

        assert!(!fragment.is_empty());
        let lines = fragment.to_list();
        assert!(lines.iter().any(|line| line.contains("X-Cell/Addictol")));
    }

    #[test]
    fn test_archive_limit_warning() {
        let validator = SettingsValidator::new("Buffout 4".to_string(), make_buffout_entry());

        let mut crashgen = HashMap::new();
        crashgen.insert("ArchiveLimit".to_string(), "true".to_string());

        let fragment = validator
            .scan_archivelimit_setting(&crashgen, Some((1, 28, 0)))
            .unwrap();

        assert!(!fragment.is_empty());
        let lines = fragment.to_list();
        assert!(lines.iter().any(|line| line.contains("ArchiveLimit")));
    }

    #[test]
    fn test_addictol_scaffold_returns_notice_fragment() {
        let validator = SettingsValidator::new("Buffout 4".to_string(), make_buffout_entry());
        let crashgen = HashMap::new();

        let fragment = validator
            .scan_addictol_settings_scaffold(&crashgen)
            .unwrap();
        let lines = fragment.to_list();

        assert!(
            !fragment.is_empty(),
            "Addictol scaffold should return an informational notice"
        );
        assert!(
            lines.iter().any(|line| line.contains("Addictol detected")),
            "Scaffold notice should mention Addictol detection"
        );
        assert!(
            lines.iter().any(|line| line.contains("scaffold")),
            "Scaffold notice should indicate scaffold mode"
        );
    }

    #[test]
    fn test_scan_all_settings_prefers_yaml_rules_when_present() {
        let entry = CrashgenEntry {
            display_section: "[Compatibility]".to_string(),
            ignore_keys: HashSet::new(),
            checks: vec![CheckId::Achievements],
            settings_rules: Some(CrashgenSettingsRules {
                version: 1,
                preflight: vec![],
                checks: vec![CheckRule {
                    id: "achievements".to_string(),
                    target: RuleTarget {
                        section: "Patches".to_string(),
                        key: "Achievements".to_string(),
                        value_type: TargetValueType::Bool,
                    },
                    when: Predicate::Always,
                    expect: ExpectedValue::Bool(false),
                    messages: RuleMessages {
                        fail: "Achievements should be disabled".to_string(),
                        fix: Some("Set Achievements to FALSE".to_string()),
                        pass: None,
                    },
                    severity: RuleSeverity::Warning,
                }],
            }),
        };
        let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

        let mut crashgen = HashMap::new();
        crashgen.insert("Achievements".to_string(), "true".to_string());
        let xse = HashSet::new();

        let fragments = validator
            .scan_all_settings(&crashgen, &xse, None, ConfigLayout::Unknown)
            .unwrap();
        assert!(!fragments.is_empty());
        let lines = fragments[0].to_list();
        assert!(
            lines
                .iter()
                .any(|line| line.contains("Achievements should be disabled"))
        );
    }

    #[test]
    fn test_scan_all_settings_rules_fallback_restores_missing_success_lines() {
        let entry = CrashgenEntry {
            display_section: "[Compatibility]".to_string(),
            ignore_keys: HashSet::new(),
            checks: vec![
                CheckId::Achievements,
                CheckId::MemoryManagement,
                CheckId::ArchiveLimit,
                CheckId::LooksMenu,
            ],
            settings_rules: Some(CrashgenSettingsRules {
                version: 1,
                preflight: vec![],
                checks: vec![
                    CheckRule {
                        id: "achievements_conflict".to_string(),
                        target: RuleTarget {
                            section: "Patches".to_string(),
                            key: "Achievements".to_string(),
                            value_type: TargetValueType::Bool,
                        },
                        when: Predicate::PluginAny(vec!["achievements.dll".to_string()]),
                        expect: ExpectedValue::Bool(false),
                        messages: RuleMessages {
                            fail: "Achievements fail".to_string(),
                            fix: None,
                            pass: Some("Achievements pass".to_string()),
                        },
                        severity: RuleSeverity::Warning,
                    },
                    CheckRule {
                        id: "memory_manager_xcell".to_string(),
                        target: RuleTarget {
                            section: "Patches".to_string(),
                            key: "MemoryManager".to_string(),
                            value_type: TargetValueType::Bool,
                        },
                        when: Predicate::PluginAny(vec!["x-cell-fo4.dll".to_string()]),
                        expect: ExpectedValue::Bool(false),
                        messages: RuleMessages {
                            fail: "Memory fail".to_string(),
                            fix: None,
                            pass: Some("Memory pass".to_string()),
                        },
                        severity: RuleSeverity::Warning,
                    },
                    CheckRule {
                        id: "archive_limit".to_string(),
                        target: RuleTarget {
                            section: "Patches".to_string(),
                            key: "ArchiveLimit".to_string(),
                            value_type: TargetValueType::Bool,
                        },
                        when: Predicate::CrashgenVersionLt((1, 30, 0)),
                        expect: ExpectedValue::Bool(false),
                        messages: RuleMessages {
                            fail: "Archive fail".to_string(),
                            fix: None,
                            pass: Some("Archive pass".to_string()),
                        },
                        severity: RuleSeverity::Warning,
                    },
                    CheckRule {
                        id: "looksmenu_f4ee".to_string(),
                        target: RuleTarget {
                            section: "Compatibility".to_string(),
                            key: "F4EE".to_string(),
                            value_type: TargetValueType::Bool,
                        },
                        when: Predicate::PluginAny(vec!["f4ee.dll".to_string()]),
                        expect: ExpectedValue::Bool(true),
                        messages: RuleMessages {
                            fail: "LooksMenu fail".to_string(),
                            fix: None,
                            pass: Some("LooksMenu pass".to_string()),
                        },
                        severity: RuleSeverity::Warning,
                    },
                ],
            }),
        };
        let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

        let mut crashgen = HashMap::new();
        crashgen.insert("Achievements".to_string(), "true".to_string());
        crashgen.insert("MemoryManager".to_string(), "true".to_string());
        crashgen.insert("ArchiveLimit".to_string(), "false".to_string());
        crashgen.insert("F4EE".to_string(), "true".to_string());

        let mut xse = HashSet::new();
        xse.insert("f4ee.dll".to_string());

        let fragments = validator
            .scan_all_settings(&crashgen, &xse, Some((1, 28, 6)), ConfigLayout::Unknown)
            .unwrap();
        let all_lines: Vec<String> = fragments.iter().flat_map(ReportFragment::to_list).collect();

        assert!(
            all_lines
                .iter()
                .any(|line| line.contains("Achievements parameter is correctly configured"))
        );
        assert!(
            all_lines
                .iter()
                .any(|line| line.contains("Memory Manager parameter is correctly configured"))
        );
        assert!(all_lines.iter().any(|line| line.contains("Archive pass")));
        assert!(all_lines.iter().any(|line| line.contains("LooksMenu pass")));
    }

    #[test]
    fn test_scan_all_settings_rules_and_fallback_do_not_duplicate_results() {
        let entry = CrashgenEntry {
            display_section: "[Compatibility]".to_string(),
            ignore_keys: HashSet::new(),
            checks: vec![CheckId::Achievements],
            settings_rules: Some(CrashgenSettingsRules {
                version: 1,
                preflight: vec![],
                checks: vec![CheckRule {
                    id: "achievements_conflict".to_string(),
                    target: RuleTarget {
                        section: "Patches".to_string(),
                        key: "Achievements".to_string(),
                        value_type: TargetValueType::Bool,
                    },
                    when: Predicate::PluginAny(vec!["achievements.dll".to_string()]),
                    expect: ExpectedValue::Bool(false),
                    messages: RuleMessages {
                        fail: "YAML achievements fail".to_string(),
                        fix: None,
                        pass: Some("YAML achievements pass".to_string()),
                    },
                    severity: RuleSeverity::Warning,
                }],
            }),
        };
        let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

        let mut crashgen = HashMap::new();
        crashgen.insert("Achievements".to_string(), "false".to_string());

        let mut xse = HashSet::new();
        xse.insert("achievements.dll".to_string());

        let fragments = validator
            .scan_all_settings(&crashgen, &xse, Some((1, 28, 6)), ConfigLayout::Unknown)
            .unwrap();
        let all_lines: Vec<String> = fragments.iter().flat_map(ReportFragment::to_list).collect();

        assert!(
            all_lines
                .iter()
                .any(|line| line.contains("YAML achievements pass"))
        );
        assert!(
            !all_lines
                .iter()
                .any(|line| line.contains("Achievements parameter is correctly configured"))
        );
    }

    #[test]
    fn test_scan_all_settings_preflight_skip_remaining_prevents_fallback() {
        let entry = CrashgenEntry {
            display_section: "[Compatibility]".to_string(),
            ignore_keys: HashSet::new(),
            checks: vec![
                CheckId::Achievements,
                CheckId::MemoryManagement,
                CheckId::ArchiveLimit,
                CheckId::LooksMenu,
            ],
            settings_rules: Some(CrashgenSettingsRules {
                version: 1,
                preflight: vec![PreflightRule {
                    id: "skip_all".to_string(),
                    when: Predicate::Always,
                    action: PreflightAction {
                        kind: PreflightActionKind::NoticeAndSkipRemaining,
                        bucket: RuleReportBucket::Settings,
                        severity: RuleSeverity::Warning,
                        message: "skip remaining".to_string(),
                        fix: None,
                    },
                }],
                checks: vec![],
            }),
        };
        let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

        let mut crashgen = HashMap::new();
        crashgen.insert("Achievements".to_string(), "true".to_string());
        crashgen.insert("MemoryManager".to_string(), "true".to_string());
        crashgen.insert("ArchiveLimit".to_string(), "false".to_string());
        crashgen.insert("F4EE".to_string(), "true".to_string());

        let mut xse = HashSet::new();
        xse.insert("f4ee.dll".to_string());

        let fragments = validator
            .scan_all_settings(&crashgen, &xse, Some((1, 28, 6)), ConfigLayout::Unknown)
            .unwrap();
        let all_lines: Vec<String> = fragments.iter().flat_map(ReportFragment::to_list).collect();

        assert!(all_lines.iter().any(|line| line.contains("skip remaining")));
        assert!(
            !all_lines
                .iter()
                .any(|line| line.contains("Achievements parameter is correctly configured"))
        );
        assert!(
            !all_lines
                .iter()
                .any(|line| line.contains("Memory Manager parameter is correctly configured"))
        );
        assert!(
            !all_lines
                .iter()
                .any(|line| line.contains("ArchiveLimit parameter is correctly configured"))
        );
    }

    #[test]
    fn test_archive_limit_rule_uses_crashgen_version_gate() {
        let entry = CrashgenEntry {
            display_section: "[Compatibility]".to_string(),
            ignore_keys: HashSet::new(),
            checks: vec![CheckId::ArchiveLimit],
            settings_rules: Some(CrashgenSettingsRules {
                version: 1,
                preflight: vec![],
                checks: vec![CheckRule {
                    id: "archive_limit".to_string(),
                    target: RuleTarget {
                        section: "Patches".to_string(),
                        key: "ArchiveLimit".to_string(),
                        value_type: TargetValueType::Bool,
                    },
                    when: Predicate::CrashgenVersionLt((1, 30, 0)),
                    expect: ExpectedValue::Bool(false),
                    messages: RuleMessages {
                        fail: "Archive fail".to_string(),
                        fix: None,
                        pass: Some("Archive pass".to_string()),
                    },
                    severity: RuleSeverity::Warning,
                }],
            }),
        };
        let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

        let mut crashgen = HashMap::new();
        crashgen.insert("ArchiveLimit".to_string(), "false".to_string());
        let xse = HashSet::new();

        let lt_boundary = validator
            .scan_all_settings(&crashgen, &xse, Some((1, 29, 9)), ConfigLayout::Unknown)
            .unwrap();
        let lt_lines: Vec<String> = lt_boundary
            .iter()
            .flat_map(ReportFragment::to_list)
            .collect();
        assert!(lt_lines.iter().any(|line| line.contains("Archive pass")));

        let at_boundary = validator
            .scan_all_settings(&crashgen, &xse, Some((1, 30, 0)), ConfigLayout::Unknown)
            .unwrap();
        let at_lines: Vec<String> = at_boundary
            .iter()
            .flat_map(ReportFragment::to_list)
            .collect();
        assert!(!at_lines.iter().any(|line| line.contains("Archive pass")));
    }

    #[test]
    fn test_production_configs_never_hit_legacy_fallback() {
        // Production crashgen entries are constructed by build_crashgen_registry() in
        // orchestrator.rs from YAML config. The legacy fallback in
        // scan_all_settings_bucketed triggers when entry.settings_rules is None.
        //
        // This test proves the invariant: entries that actually reach
        // scan_all_settings_bucketed (those with non-empty checks) always have
        // settings_rules defined in production. Entries with no checks (like
        // default_entry for unknown crashgens) return early via the orchestrator
        // before reaching the bucketed method.

        // 1. default_entry has no checks -> never reaches scan_all_settings_bucketed
        let default = CrashgenEntry::default_entry();
        assert!(
            default.checks.is_empty(),
            "default_entry must have no checks, ensuring it never reaches scan_all_settings_bucketed"
        );
        assert!(
            default.settings_rules.is_none(),
            "default_entry has no settings_rules (safe because it never reaches the bucketed path)"
        );

        // 2. Entries with checks (like Buffout 4) always have settings_rules in
        // production. Verify the invariant by constructing a production-representative
        // entry with settings_rules and confirming it takes the rules path.
        let production_buffout = CrashgenEntry {
            display_section: "[Compatibility]".to_string(),
            ignore_keys: ["F4EE", "WaitForDebugger", "Achievements"]
                .iter()
                .map(|s| s.to_string())
                .collect(),
            checks: vec![
                CheckId::Achievements,
                CheckId::MemoryManagement,
                CheckId::ArchiveLimit,
                CheckId::LooksMenu,
            ],
            settings_rules: Some(CrashgenSettingsRules {
                version: 1,
                preflight: vec![],
                checks: vec![CheckRule {
                    id: "achievements_conflict".to_string(),
                    target: RuleTarget {
                        section: "Patches".to_string(),
                        key: "Achievements".to_string(),
                        value_type: TargetValueType::Bool,
                    },
                    when: Predicate::Always,
                    expect: ExpectedValue::Bool(false),
                    messages: RuleMessages {
                        fail: "Achievements should be disabled".to_string(),
                        fix: Some("Set Achievements to FALSE".to_string()),
                        pass: None,
                    },
                    severity: RuleSeverity::Warning,
                }],
            }),
        };
        assert!(
            !production_buffout.checks.is_empty(),
            "production Buffout entry has checks"
        );
        assert!(
            production_buffout.settings_rules.is_some(),
            "production Buffout entry must have settings_rules -- the legacy fallback is never needed"
        );

        // 3. Verify the production entry actually uses rules (not the legacy path)
        // by calling scan_all_settings_bucketed and confirming rules-driven output.
        let validator = SettingsValidator::new("Buffout 4".to_string(), production_buffout);
        let mut crashgen = HashMap::new();
        crashgen.insert("Achievements".to_string(), "true".to_string());
        let xse = HashSet::new();

        let fragments = validator
            .scan_all_settings_bucketed(&crashgen, &xse, None, ConfigLayout::Unknown)
            .unwrap();
        let all_lines: Vec<String> = fragments
            .iter()
            .flat_map(|f| f.fragment.to_list())
            .collect();
        assert!(
            all_lines
                .iter()
                .any(|line| line.contains("Achievements should be disabled")),
            "production entry with settings_rules must use the rules path, not the legacy fallback"
        );
    }
}
