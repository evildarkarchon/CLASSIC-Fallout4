//! Settings Validator - Crash generator settings validation
//!
//! This module validates crash generator settings for:
//! - Buffout achievements compatibility
//! - Memory management settings (with X-Cell/ScrapHeap detection)
//! - Archive limit settings
//! - LooksMenu (F4EE) compatibility
//! - Disabled settings detection

use crate::error::Result;
use std::collections::{HashMap, HashSet};

use crate::report::ReportFragment;

/// High-performance settings validator
#[derive(Clone)]
pub struct SettingsValidator {
    crashgen_name: String,
    crashgen_ignore: HashSet<String>,
}

impl SettingsValidator {
    /// Creates a new settings validator for crash generator configuration.
    ///
    /// This constructor initializes a validator that can check crash generator
    /// settings for common misconfigurations and compatibility issues with
    /// installed mods like X-Cell, ScrapHeap, and Achievements mods.
    ///
    /// # Arguments
    ///
    /// * `crashgen_name` - The name of the crash generator (e.g., "Buffout 4")
    /// * `crashgen_ignore` - List of setting names to ignore during validation
    ///
    /// # Returns
    ///
    /// A new `SettingsValidator` instance ready to validate crash generator settings.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::settings_validator::SettingsValidator;
    ///
    /// let validator = SettingsValidator::new(
    ///     "Buffout 4".to_string(),
    ///     vec!["SomeIgnoredSetting".to_string()]
    /// );
    /// ```
    pub fn new(crashgen_name: String, crashgen_ignore: Vec<String>) -> Self {
        Self {
            crashgen_name,
            crashgen_ignore: crashgen_ignore.into_iter().collect(),
        }
    }

    /// Scan Buffout achievements setting for conflicts
    ///
    /// Args:
    ///     xse_modules: Set of loaded XSE plugin modules
    ///     crashgen: Crash generator configuration settings
    ///
    /// Returns:
    ///     ReportFragment containing validation results
    pub fn scan_buffout_achievements_setting(
        &self,
        xse_modules: HashSet<String>,
        crashgen: &HashMap<String, String>,
    ) -> Result<ReportFragment> {
        let mut lines = Vec::new();

        let achievements = crashgen
            .get("Achievements")
            .and_then(|v| v.parse::<bool>().ok())
            .unwrap_or(false);

        if achievements
            && (xse_modules.contains("achievements.dll")
                || xse_modules.contains("unlimitedsurvivalmode.dll"))
        {
            lines.push(format!(
                "# ❌ CAUTION : The Achievements Mod and/or Unlimited Survival Mode is installed, but Achievements is set to TRUE # \n"
            ));
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

    /// Analyze and validate memory management settings
    ///
    /// Args:
    ///     crashgen: Crash generator configuration settings
    ///     has_xcell: Whether X-Cell mod is installed
    ///     has_old_xcell: Whether outdated X-Cell is installed
    ///     has_baka_scrapheap: Whether Baka ScrapHeap mod is installed
    ///
    /// Returns:
    ///     ReportFragment containing validation results
    pub fn scan_buffout_memorymanagement_settings(
        &self,
        crashgen: &HashMap<String, String>,
        has_xcell: bool,
        has_old_xcell: bool,
        has_baka_scrapheap: bool,
    ) -> Result<ReportFragment> {
        let mut lines = Vec::new();
        let separator = "\n\n-----\n";

        // Check for old X-Cell version first
        if has_old_xcell {
            Self::add_warning(
                &mut lines,
                "You have an old version of X-Cell installed, please update it to the latest version.",
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

    /// Scan and validate ArchiveLimit setting
    ///
    /// Args:
    ///     crashgen: Crash generator configuration settings
    ///     crashgen_version: Version of the crash generator (optional)
    ///
    /// Returns:
    ///     ReportFragment containing validation results
    pub fn scan_archivelimit_setting(
        &self,
        crashgen: &HashMap<String, String>,
        crashgen_version: Option<(u32, u32, u32)>, // (major, minor, patch)
    ) -> Result<ReportFragment> {
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

    /// Analyze LooksMenu (F4EE) setting for compatibility
    ///
    /// Args:
    ///     crashgen: Crash generator configuration settings
    ///     xse_modules: Set of loaded XSE plugin modules
    ///
    /// Returns:
    ///     ReportFragment containing validation results
    pub fn scan_buffout_looksmenu_setting(
        &self,
        crashgen: &HashMap<String, String>,
        xse_modules: HashSet<String>,
    ) -> Result<ReportFragment> {
        let mut lines = Vec::new();

        if let Some(f4ee) = crashgen.get("F4EE") {
            let f4ee_enabled = f4ee.parse::<bool>().unwrap_or(false);

            if !f4ee_enabled && xse_modules.contains("f4ee.dll") {
                lines.push("# ❌ CAUTION : Looks Menu is installed, but F4EE parameter under [Compatibility] is set to FALSE # \n".to_string());
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

    /// Check for disabled settings in crash generator configuration
    ///
    /// Args:
    ///     crashgen: Crash generator configuration settings
    ///
    /// Returns:
    ///     ReportFragment containing notices about disabled settings
    pub fn check_disabled_settings(
        &self,
        crashgen: &HashMap<String, String>,
    ) -> Result<ReportFragment> {
        let mut lines = Vec::new();

        for (key, value) in crashgen.iter() {
            let setting_name = key.clone();

            if let Ok(false) = value.parse::<bool>() {
                if !self.crashgen_ignore.contains(&setting_name) {
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
        // Create configuration tuple for cleaner logic
        let config = (mem_enabled, has_xcell, has_baka);

        match config {
            (true, true, false) => {
                Self::add_warning(
                    lines,
                    "X-Cell is installed, but MemoryManager parameter is set to TRUE",
                    &format!(
                        "Open {}'s TOML file and change MemoryManager to FALSE, this prevents conflicts with X-Cell.",
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
                    "The Baka ScrapHeap Mod is installed, but is redundant with X-Cell",
                    "Uninstall the Baka ScrapHeap Mod, this prevents conflicts with X-Cell.",
                    separator,
                );
            }
            (false, true, false) => {
                Self::add_success(
                    lines,
                    &format!(
                        "Memory Manager parameter is correctly configured for use with X-Cell in your {} settings!",
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
                        "X-Cell is installed, but {} parameter is set to TRUE",
                        setting_key
                    ),
                    &format!(
                        "Open {}'s TOML file and change {} to FALSE, this prevents conflicts with X-Cell.",
                        self.crashgen_name, setting_key
                    ),
                    separator,
                );
            } else {
                Self::add_success(
                    lines,
                    &format!(
                        "{} parameter is correctly configured for use with X-Cell in your {} settings!",
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

    #[test]
    fn test_achievements_validation() {
        let validator = SettingsValidator::new("Buffout 4".to_string(), vec![]);

        let mut crashgen = HashMap::new();
        crashgen.insert("Achievements".to_string(), "true".to_string());

        let mut xse_modules = HashSet::new();
        xse_modules.insert("achievements.dll".to_string());

        let fragment = validator
            .scan_buffout_achievements_setting(xse_modules, &crashgen)
            .unwrap();

        assert!(fragment.len() > 0);
        let lines = fragment.to_list();
        assert!(lines.iter().any(|line| line.contains("CAUTION")));
    }

    #[test]
    fn test_memory_management_xcell_conflict() {
        let validator = SettingsValidator::new("Buffout 4".to_string(), vec![]);

        let mut crashgen = HashMap::new();
        crashgen.insert("MemoryManager".to_string(), "true".to_string());

        let fragment = validator
            .scan_buffout_memorymanagement_settings(
                &crashgen, true,  // has_xcell
                false, // has_old_xcell
                false, // has_baka
            )
            .unwrap();

        assert!(fragment.len() > 0);
        let lines = fragment.to_list();
        assert!(lines.iter().any(|line| line.contains("X-Cell")));
    }

    #[test]
    fn test_archive_limit_warning() {
        let validator = SettingsValidator::new("Buffout 4".to_string(), vec![]);

        let mut crashgen = HashMap::new();
        crashgen.insert("ArchiveLimit".to_string(), "true".to_string());

        let fragment = validator
            .scan_archivelimit_setting(&crashgen, Some((1, 28, 0)))
            .unwrap();

        assert!(fragment.len() > 0);
        let lines = fragment.to_list();
        assert!(lines.iter().any(|line| line.contains("ArchiveLimit")));
    }
}
