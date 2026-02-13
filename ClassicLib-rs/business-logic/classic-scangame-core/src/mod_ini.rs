//! Mod INI Scanner - Configuration Issue Detection Across Multiple INI Files
//!
//! Orchestrates scanning of mod configuration files (INI/CONF) for a game installation.
//! Uses `ConfigFileCache` for encoding-aware file loading and provides comprehensive
//! issue detection for VSync settings, console commands, mod-specific checks, and duplicates.
//!
//! Replaces Python `ClassicLib.scanning.game.scan_mod_inis.scan_mod_inis_async()`.
//!
//! ## Checks Performed
//!
//! 1. **Console command** - `sStartingConsoleCommand` in game INI files (startup slowdown)
//! 2. **VSync detection** - across dxvk.conf, enblocal.ini, reshade.ini, etc.
//! 3. **Mod-specific issues**:
//!    - ESPExplorer: commented-out hotkey
//!    - EPO: particle count too high (>5000)
//!    - F4EE: locked head parts / face tints
//!    - High FPS Physics Fix: loading screen FPS too low (<600)
//! 4. **Duplicate detection** - identical or near-identical INI files

use std::path::{Path, PathBuf};

use crate::config_cache::{ConfigCacheError, ConfigFileCache};
use crate::ini::{ConfigIssue, IssueSeverity};

/// Result of a mod INI scan
#[derive(Debug)]
pub struct ModIniScanResult {
    /// Formatted report message for display
    pub message: String,

    /// Structured list of detected configuration issues
    pub issues: Vec<ConfigIssue>,

    /// List of files with VSync enabled
    pub vsync_files: Vec<VsyncEntry>,

    /// Duplicate files detected
    pub duplicates: Vec<DuplicateEntry>,
}

/// A file with VSync enabled
#[derive(Debug, Clone)]
pub struct VsyncEntry {
    /// Path to the config file
    pub file_path: PathBuf,

    /// Setting name that has VSync enabled
    pub setting: String,
}

/// A duplicate configuration file pair
#[derive(Debug, Clone)]
pub struct DuplicateEntry {
    /// Lowercase filename
    pub file_name: String,

    /// All paths where this file was found
    pub paths: Vec<PathBuf>,
}

/// VSync setting definition (file, section, key)
struct VsyncSetting {
    file_name: &'static str,
    section: &'static str,
    setting: &'static str,
}

/// Standard VSync settings to check (excluding highfpsphysicsfix which is handled separately)
const VSYNC_SETTINGS: &[VsyncSetting] = &[
    VsyncSetting {
        file_name: "enblocal.ini",
        section: "ENGINE",
        setting: "ForceVSync",
    },
    VsyncSetting {
        file_name: "longloadingtimesfix.ini",
        section: "Limiter",
        setting: "EnableVSync",
    },
    VsyncSetting {
        file_name: "reshade.ini",
        section: "APP",
        setting: "ForceVsync",
    },
    VsyncSetting {
        file_name: "fallout4_test.ini",
        section: "CreationKit",
        setting: "VSyncRender",
    },
];

/// Mod INI Scanner orchestrator
///
/// Scans a game directory for mod configuration files and detects issues.
/// This is the main entry point for INI-based game scanning.
///
/// # Example
///
/// ```rust,no_run
/// use classic_scangame_core::mod_ini::ModIniScanner;
/// use std::path::Path;
///
/// let result = ModIniScanner::scan(
///     Path::new("C:/Games/Fallout4"),
///     "Fallout4",
/// )?;
/// println!("{}", result.message);
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub struct ModIniScanner;

impl ModIniScanner {
    /// Scan mod INI files and produce a comprehensive report
    ///
    /// # Arguments
    ///
    /// * `game_root` - Root directory of the game installation
    /// * `game_name` - Game name (e.g., "Fallout4") for console command detection
    ///
    /// # Returns
    ///
    /// A `ModIniScanResult` with the formatted message, issues, VSync entries, and duplicates
    pub fn scan(
        game_root: &Path,
        game_name: &str,
    ) -> std::result::Result<ModIniScanResult, ConfigCacheError> {
        let mut cache = ConfigFileCache::new(game_root, &["F4EE"])?;
        Self::scan_with_cache(&mut cache, game_name)
    }

    /// Scan using an existing `ConfigFileCache`
    ///
    /// Useful when the cache is shared with other scanning operations.
    pub fn scan_with_cache(
        cache: &mut ConfigFileCache,
        game_name: &str,
    ) -> std::result::Result<ModIniScanResult, ConfigCacheError> {
        let mut message_parts: Vec<String> = Vec::new();
        let mut all_issues: Vec<ConfigIssue> = Vec::new();

        // 1. Check console command settings
        let console_msgs = Self::check_console_commands(cache, game_name);
        message_parts.extend(console_msgs);

        // 2. Check VSync settings
        let vsync_entries = Self::check_vsync(cache, game_name);
        if !vsync_entries.is_empty() {
            message_parts.push(
                "* NOTICE : VSYNC IS CURRENTLY ENABLED IN THE FOLLOWING FILES *\n".to_string(),
            );
            for entry in &vsync_entries {
                message_parts.push(format!(
                    "{} | SETTING: {}\n",
                    entry.file_path.display(),
                    entry.setting
                ));
            }
        }

        // 3. Detect mod-specific issues
        let issues = Self::detect_mod_issues(cache);
        all_issues.extend(issues);

        // 4. Check for duplicate files
        let duplicates = Self::collect_duplicates(cache);
        if !duplicates.is_empty() {
            message_parts
                .push("* NOTICE : DUPLICATES FOUND OF THE FOLLOWING FILES *\n".to_string());
            let mut all_paths: Vec<&Path> = Vec::new();
            for dup in &duplicates {
                for p in &dup.paths {
                    all_paths.push(p.as_path());
                }
            }
            all_paths.sort_by_key(|p| p.file_name());
            for p in &all_paths {
                message_parts.push(format!("{}\n", p.display()));
            }
        }

        Ok(ModIniScanResult {
            message: message_parts.join(""),
            issues: all_issues,
            vsync_files: vsync_entries,
            duplicates,
        })
    }

    /// Check for `sStartingConsoleCommand` in game INI files
    fn check_console_commands(cache: &mut ConfigFileCache, game_name: &str) -> Vec<String> {
        let mut messages = Vec::new();
        let game_lower = game_name.to_lowercase();

        // Collect matching files first (avoid borrow issues)
        let matching: Vec<(String, PathBuf)> = cache
            .iter()
            .filter(|(name, _)| name.starts_with(&game_lower))
            .map(|(name, path)| (name.to_string(), path.to_path_buf()))
            .collect();

        for (file_lower, file_path) in matching {
            if cache.has_setting(&file_lower, "General", "sStartingConsoleCommand") {
                messages.push(format!(
                    "[!] NOTICE: {} contains the *sStartingConsoleCommand* setting.\n",
                    file_path.display()
                ));
                messages.push(
                    "In rare cases, this setting can slow down the initial game startup time for some players.\n\
                     You can test your initial startup time difference by removing this setting from the INI file.\n-----\n"
                        .to_string(),
                );
            }
        }

        messages
    }

    /// Check VSync settings across configuration files
    fn check_vsync(cache: &mut ConfigFileCache, game_name: &str) -> Vec<VsyncEntry> {
        let mut entries = Vec::new();

        // Check dxvk.conf separately (uses game-specific section)
        let dxvk_section = format!("{game_name}.exe");
        if let Some(true) = cache.get_bool("dxvk.conf", &dxvk_section, "dxgi.syncInterval") {
            if let Some(path) = cache.get_path("dxvk.conf") {
                entries.push(VsyncEntry {
                    file_path: path.to_path_buf(),
                    setting: "dxgi.syncInterval".to_string(),
                });
            }
        }

        // Check standard VSync settings
        for vs in VSYNC_SETTINGS {
            if let Some(true) = cache.get_bool(vs.file_name, vs.section, vs.setting) {
                if let Some(path) = cache.get_path(vs.file_name) {
                    entries.push(VsyncEntry {
                        file_path: path.to_path_buf(),
                        setting: vs.setting.to_string(),
                    });
                }
            }
        }

        // Check highfpsphysicsfix.ini separately (different section)
        if let Some(true) = cache.get_bool("highfpsphysicsfix.ini", "Main", "EnableVSync") {
            if let Some(path) = cache.get_path("highfpsphysicsfix.ini") {
                entries.push(VsyncEntry {
                    file_path: path.to_path_buf(),
                    setting: "EnableVSync".to_string(),
                });
            }
        }

        entries
    }

    /// Detect mod-specific configuration issues
    fn detect_mod_issues(cache: &mut ConfigFileCache) -> Vec<ConfigIssue> {
        let mut issues = Vec::new();

        // ESPExplorer hotkey check
        if cache.contains("espexplorer.ini") {
            if let Some(issue) = cache.detect_issue(
                "espexplorer.ini",
                "General",
                "HotKey",
                "0x79",
                "Hotkey is commented out and won't work. Change to hex code 0x79 for F10.",
                |val| val.contains("; F10"),
                IssueSeverity::Warning,
            ) {
                issues.push(issue);
            }
        }

        // EPO particle count check
        if cache.contains("epo.ini") {
            if let Some(issue) = cache.detect_issue(
                "epo.ini",
                "Particles",
                "iMaxDesired",
                "5000",
                "High particle count can cause performance issues and crashes.",
                |val| val.trim().parse::<i64>().is_ok_and(|v| v > 5000),
                IssueSeverity::Warning,
            ) {
                issues.push(issue);
            }
        }

        // F4EE settings checks
        if cache.contains("f4ee.ini") {
            if let Some(issue) = cache.detect_issue(
                "f4ee.ini",
                "CharGen",
                "bUnlockHeadParts",
                "1",
                "Head parts are locked. Set to 1 to unlock all head parts.",
                |val| val.trim() == "0",
                IssueSeverity::Warning,
            ) {
                issues.push(issue);
            }

            if let Some(issue) = cache.detect_issue(
                "f4ee.ini",
                "CharGen",
                "bUnlockTints",
                "1",
                "Face tints are locked. Set to 1 to unlock all face tints.",
                |val| val.trim() == "0",
                IssueSeverity::Warning,
            ) {
                issues.push(issue);
            }
        }

        // High FPS Physics Fix loading screen FPS check
        if cache.contains("highfpsphysicsfix.ini") {
            if let Some(issue) = cache.detect_issue(
                "highfpsphysicsfix.ini",
                "Limiter",
                "LoadingScreenFPS",
                "600.0",
                "Loading screen FPS is too low. Increase to 600.0 to prevent physics issues.",
                |val| val.trim().parse::<f64>().is_ok_and(|v| v < 600.0),
                IssueSeverity::Warning,
            ) {
                issues.push(issue);
            }
        }

        issues
    }

    /// Collect duplicate files from the cache
    fn collect_duplicates(cache: &ConfigFileCache) -> Vec<DuplicateEntry> {
        cache
            .duplicate_files
            .iter()
            .map(|(name, paths)| DuplicateEntry {
                file_name: name.clone(),
                paths: paths.clone(),
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    /// Helper: create a game root with files
    fn setup_game_root(files: &[(&str, &str)]) -> TempDir {
        let temp = TempDir::new().unwrap();
        for (name, content) in files {
            fs::write(temp.path().join(name), content).unwrap();
        }
        temp
    }

    #[test]
    fn test_scan_empty_directory() {
        let root = setup_game_root(&[]);
        let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();

        assert!(result.message.is_empty());
        assert!(result.issues.is_empty());
        assert!(result.vsync_files.is_empty());
        assert!(result.duplicates.is_empty());
    }

    #[test]
    fn test_console_command_detection() {
        let root = setup_game_root(&[(
            "fallout4.ini",
            "[General]\nsStartingConsoleCommand=bat autoexec\n",
        )]);

        let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
        assert!(result.message.contains("sStartingConsoleCommand"));
    }

    #[test]
    fn test_vsync_detection() {
        let root = setup_game_root(&[("enblocal.ini", "[ENGINE]\nForceVSync=true\n")]);

        let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
        assert_eq!(result.vsync_files.len(), 1);
        assert_eq!(result.vsync_files[0].setting, "ForceVSync");
        assert!(result.message.contains("VSYNC"));
    }

    #[test]
    fn test_vsync_highfps_separate() {
        let root = setup_game_root(&[(
            "highfpsphysicsfix.ini",
            "[Main]\nEnableVSync=true\n[Limiter]\nLoadingScreenFPS=600.0\n",
        )]);

        let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
        assert_eq!(result.vsync_files.len(), 1);
        assert_eq!(result.vsync_files[0].setting, "EnableVSync");
    }

    #[test]
    fn test_epo_particle_issue() {
        let root = setup_game_root(&[("epo.ini", "[Particles]\niMaxDesired=10000\n")]);

        let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
        assert_eq!(result.issues.len(), 1);
        assert_eq!(result.issues[0].setting, "iMaxDesired");
        assert_eq!(result.issues[0].recommended_value, "5000");
    }

    #[test]
    fn test_epo_particle_ok() {
        let root = setup_game_root(&[("epo.ini", "[Particles]\niMaxDesired=3000\n")]);

        let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
        assert!(result.issues.is_empty());
    }

    #[test]
    fn test_f4ee_issues() {
        let root = setup_game_root(&[(
            "f4ee.ini",
            "[CharGen]\nbUnlockHeadParts=0\nbUnlockTints=0\n",
        )]);

        let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
        assert_eq!(result.issues.len(), 2);
        assert!(
            result
                .issues
                .iter()
                .any(|i| i.setting == "bUnlockHeadParts")
        );
        assert!(result.issues.iter().any(|i| i.setting == "bUnlockTints"));
    }

    #[test]
    fn test_f4ee_no_issues_when_unlocked() {
        let root = setup_game_root(&[(
            "f4ee.ini",
            "[CharGen]\nbUnlockHeadParts=1\nbUnlockTints=1\n",
        )]);

        let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
        assert!(result.issues.is_empty());
    }

    #[test]
    fn test_highfps_loading_fps_issue() {
        let root = setup_game_root(&[(
            "highfpsphysicsfix.ini",
            "[Limiter]\nLoadingScreenFPS=120.0\n",
        )]);

        let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
        assert_eq!(result.issues.len(), 1);
        assert_eq!(result.issues[0].setting, "LoadingScreenFPS");
    }

    #[test]
    fn test_espexplorer_hotkey_issue() {
        let root = setup_game_root(&[("espexplorer.ini", "[General]\nHotKey=; F10\n")]);

        let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
        assert_eq!(result.issues.len(), 1);
        assert_eq!(result.issues[0].setting, "HotKey");
        assert_eq!(result.issues[0].recommended_value, "0x79");
    }

    #[test]
    fn test_multiple_issues_combined() {
        let root = setup_game_root(&[
            ("epo.ini", "[Particles]\niMaxDesired=10000\n"),
            ("f4ee.ini", "[CharGen]\nbUnlockHeadParts=0\n"),
            ("enblocal.ini", "[ENGINE]\nForceVSync=true\n"),
            (
                "fallout4.ini",
                "[General]\nsStartingConsoleCommand=bat autoexec\n",
            ),
        ]);

        let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();

        // 2 issues: EPO particle + F4EE head parts
        assert_eq!(result.issues.len(), 2);
        // 1 VSync entry
        assert_eq!(result.vsync_files.len(), 1);
        // Console command in message
        assert!(result.message.contains("sStartingConsoleCommand"));
        assert!(result.message.contains("VSYNC"));
    }

    #[test]
    fn test_nonexistent_game_root() {
        let result = ModIniScanner::scan(Path::new("/nonexistent"), "Fallout4");
        assert!(result.is_err());
    }

    #[test]
    fn test_duplicate_files() {
        // The ModIniScanner uses "F4EE" whitelist for duplicate detection,
        // so we need directories/files that match this pattern
        let root = TempDir::new().unwrap();
        let sub1 = root.path().join("F4EE");
        let sub2 = root.path().join("other_F4EE");
        fs::create_dir(&sub1).unwrap();
        fs::create_dir(&sub2).unwrap();

        let content = "[Section]\nkey=value\n";
        fs::write(sub1.join("test.ini"), content).unwrap();
        fs::write(sub2.join("test.ini"), content).unwrap();

        let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
        assert!(!result.duplicates.is_empty());
        assert!(result.message.contains("DUPLICATES"));
    }
}
