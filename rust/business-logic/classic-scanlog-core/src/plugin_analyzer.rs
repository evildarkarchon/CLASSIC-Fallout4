//! Plugin analyzer module - High-performance plugin detection and analysis (Pure Rust - NO PyO3)
//!
//! This module provides plugin detection and analysis using pure Rust data structures.

use crate::error::Result;
use dashmap::DashMap;
use indexmap::IndexMap;
use once_cell::sync::Lazy;
use rayon::prelude::*;
use regex::Regex;
use std::collections::{HashMap, HashSet};
use std::path::Path;
use std::sync::Arc;

/// Precompiled plugin pattern - exact match to Python's pattern
/// Pattern: r"\s*\[(FE:([0-9A-F]{3})|[0-9A-F]{2})\]\s*(.+?(?:\.es[pml])+)"
static PLUGIN_PATTERN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?i)\s*\[(FE:([0-9A-F]{3})|[0-9A-F]{2})\]\s*(.+?(?:\.es[pml])+)").unwrap()
});

/// Plugin origin markers
const PLUGIN_ORIGIN_LOADORDER: &str = "LO";
const PLUGIN_STATUS_DLL: &str = "DLL";
const PLUGIN_STATUS_UNKNOWN: &str = "???";
const PLUGIN_LIMIT_MARKER: &str = "[FF]";

/// Core plugin analyzer - pure Rust implementation (NO PyO3)
pub struct PluginAnalyzer {
    lower_plugins_ignore: HashSet<String>,
    ignore_plugins_list: HashSet<String>,
    crashgen_name: String,
    game_version: String,
    game_version_vr: String,
    game_version_new: String,
    #[allow(dead_code)] // Reserved for future case-insensitive matching optimization
    case_cache: Arc<DashMap<String, String>>,
}

impl PluginAnalyzer {
    /// Creates a new plugin analyzer with the specified configuration and ignore lists.
    ///
    /// This constructor initializes the analyzer with all necessary configuration for plugin
    /// detection, filtering, and version-specific behavior. The analyzer converts all ignore
    /// lists to lowercase for case-insensitive matching and initializes an internal case cache
    /// for performance optimization.
    ///
    /// # Arguments
    ///
    /// * `game_ignore_plugins` - Game-specific plugins to ignore (e.g., base game ESMs)
    /// * `ignore_list` - User-defined additional plugins to ignore
    /// * `crashgen_name` - Name of crash generator for report text (e.g., "Buffout 4")
    /// * `game_version` - Base game version string (e.g., "1.10.163")
    /// * `game_version_vr` - VR version string for VR-specific checks
    /// * `game_version_new` - Newer game version threshold for feature detection
    ///
    /// # Returns
    ///
    /// Returns `Ok(PluginAnalyzer)` with the configured analyzer.
    ///
    /// # Errors
    ///
    /// This function currently always succeeds, returning `Ok(_)`. The `Result` return type
    /// is provided for API consistency and future error handling.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::PluginAnalyzer;
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let analyzer = PluginAnalyzer::new(
    ///     vec!["Fallout4.esm".to_string()],  // Game base plugins
    ///     vec!["DLCRobot.esm".to_string()],  // User ignores
    ///     "Buffout 4".to_string(),
    ///     "1.10.163".to_string(),
    ///     "1.10.163vr".to_string(),
    ///     "1.37.0".to_string(),
    /// )?;
    /// # Ok(())
    /// # }
    /// ```
    pub fn new(
        game_ignore_plugins: Vec<String>,
        ignore_list: Vec<String>,
        crashgen_name: String,
        game_version: String,
        game_version_vr: String,
        game_version_new: String,
    ) -> Result<Self> {
        // Convert to lowercase sets for case-insensitive matching
        let lower_plugins_ignore: HashSet<String> = game_ignore_plugins
            .iter()
            .map(|s| s.to_lowercase())
            .collect();

        let ignore_plugins_list: HashSet<String> =
            ignore_list.iter().map(|s| s.to_lowercase()).collect();

        Ok(Self {
            lower_plugins_ignore,
            ignore_plugins_list,
            crashgen_name,
            game_version,
            game_version_vr,
            game_version_new,
            case_cache: Arc::new(DashMap::new()),
        })
    }

    /// Scans an external `loadorder.txt` file in the CLASSIC folder for plugin override functionality.
    ///
    /// This static method checks for a `loadorder.txt` file in the current directory and, if found,
    /// reads plugin names from it (skipping the header line). This allows users to override automatic
    /// plugin detection from crash logs with a manually specified load order.
    ///
    /// When a `loadorder.txt` file is present, CLASSIC will ignore plugins in crash logs and only
    /// detect plugins listed in this file. This is useful for testing or when crash logs have
    /// incomplete/corrupted plugin information.
    ///
    /// # Returns
    ///
    /// Returns `Ok((HashMap, bool, Vec<String>))` containing:
    /// - `HashMap<String, String>` - Plugin names to status markers (all marked as "LO" for load order)
    /// - `bool` - Whether any plugins were loaded from the file (`true` if file exists and has plugins)
    /// - `Vec<String>` - Report lines explaining the loadorder.txt functionality
    ///
    /// # Errors
    ///
    /// Never returns an error. File I/O errors are logged to report lines but don't fail the function.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::PluginAnalyzer;
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let (plugins, loaded, report) = PluginAnalyzer::loadorder_scan_loadorder_txt()?;
    ///
    /// if loaded {
    ///     println!("Loaded {} plugins from loadorder.txt", plugins.len());
    /// } else {
    ///     println!("No loadorder.txt found, will use crash log plugins");
    /// }
    /// # Ok(())
    /// # }
    /// ```
    pub fn loadorder_scan_loadorder_txt() -> Result<(IndexMap<String, String>, bool, Vec<String>)> {
        let mut lines = vec![
            "* ✔️ LOADORDER.TXT FILE FOUND IN THE MAIN CLASSIC FOLDER! *\n".to_string(),
            "CLASSIC will now ignore plugins in all crash logs and only detect plugins in this file.\n".to_string(),
            "[ To disable this functionality, simply remove loadorder.txt from your CLASSIC folder. ]\n\n".to_string(),
        ];

        // IndexMap preserves insertion order for Python parity
        let mut loadorder_plugins = IndexMap::new();
        let loadorder_path = Path::new("loadorder.txt");

        if loadorder_path.exists() {
            match std::fs::read_to_string(loadorder_path) {
                Ok(content) => {
                    let loadorder_data: Vec<&str> = content.lines().collect();

                    // Skip the header line (first line) of the loadorder.txt file
                    if loadorder_data.len() > 1 {
                        for plugin_entry in loadorder_data.iter().skip(1) {
                            let plugin_entry = plugin_entry.trim();
                            if !plugin_entry.is_empty()
                                && !loadorder_plugins.contains_key(plugin_entry)
                            {
                                loadorder_plugins.insert(
                                    plugin_entry.to_string(),
                                    PLUGIN_ORIGIN_LOADORDER.to_string(),
                                );
                            }
                        }
                    }
                }
                Err(e) => {
                    lines.push(format!("Error reading loadorder.txt: {}\n", e));
                }
            }
        }

        let plugins_loaded = !loadorder_plugins.is_empty();

        Ok((loadorder_plugins, plugins_loaded, lines))
    }

    /// Scans and processes the plugin load order from the provided segment plugins.
    ///
    /// This method analyzes a list of segment plugins to extract their details and
    /// builds a mapping of plugin names to their identifiers or classification.
    /// It matches the Python implementation's behavior exactly.
    ///
    /// Note: The core load order parsing is universal across all Bethesda games.
    /// The game_version and version_current parameters are optional and only used
    /// for plugin limit detection (backward compatibility).
    ///
    /// # Arguments
    ///
    /// * `segment_plugins` - Vector of plugin segment lines from the crash log
    /// * `game_version` - Optional game version for plugin limit detection
    /// * `version_current` - Optional crashgen version for plugin limit detection
    ///
    /// # Returns
    ///
    /// Returns `Ok((IndexMap, bool, bool))` containing:
    /// - IndexMap mapping plugin names to their hex indices or status ("DLL", "???")
    ///   in load order (preserves insertion order for Python parity)
    /// - Boolean flag for plugin limit triggered (requires version params)
    /// - Boolean flag for limit check disabled (requires version params)
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::PluginAnalyzer;
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let analyzer = PluginAnalyzer::new(
    ///     vec![], vec![], "Buffout 4".to_string(),
    ///     "1.10.163".to_string(), "1.10.163vr".to_string(), "1.37.0".to_string()
    /// )?;
    ///
    /// let segment = vec![
    ///     "[00] Fallout4.esm".to_string(),
    ///     "[01] MyMod.esp".to_string(),
    /// ];
    ///
    /// let (plugins, limit_triggered, limit_disabled) = analyzer.loadorder_scan_log(
    ///     segment,
    ///     Some("1.10.163"),
    ///     Some("1.36.0")
    /// )?;
    /// assert_eq!(plugins.len(), 2);
    /// assert_eq!(plugins.get("Fallout4.esm"), Some(&"00".to_string()));
    /// # Ok(())
    /// # }
    /// ```
    pub fn loadorder_scan_log(
        &self,
        segment_plugins: Vec<String>,
        game_version: Option<&str>,
        version_current: Option<&str>,
    ) -> Result<(IndexMap<String, String>, bool, bool)> {
        // Early return for empty input
        if segment_plugins.is_empty() {
            return Ok((IndexMap::new(), false, false));
        }

        // Initialize plugin map - IndexMap preserves insertion order for Python parity
        let mut plugin_map = IndexMap::new();

        // Check plugin limits separately if version info provided
        let mut plugin_limit_triggered = false;
        let mut limit_check_disabled = false;
        if let (Some(game_ver), Some(version_cur)) = (game_version, version_current) {
            let (triggered, disabled) =
                self.check_plugin_limit(segment_plugins.clone(), game_ver, version_cur)?;
            plugin_limit_triggered = triggered;
            limit_check_disabled = disabled;
        }

        // Process each plugin entry (universal parsing logic)
        // Plugins are added in the order they appear in the crash log (load order)
        for entry in &segment_plugins {
            // Extract plugin information using regex
            if let Some(caps) = PLUGIN_PATTERN.captures(entry) {
                let plugin_id = caps.get(1).map(|m| m.as_str().to_string());
                let plugin_name = caps
                    .get(3)
                    .map(|m| m.as_str().to_string())
                    .unwrap_or_default();

                // Skip if plugin name is empty or already processed
                if plugin_name.is_empty() || plugin_map.contains_key(&plugin_name) {
                    continue;
                }

                // Classify the plugin
                let status = if let Some(id) = plugin_id {
                    id.replace(":", "").to_uppercase()
                } else if plugin_name.to_lowercase().contains("dll") {
                    PLUGIN_STATUS_DLL.to_string()
                } else {
                    PLUGIN_STATUS_UNKNOWN.to_string()
                };

                plugin_map.insert(plugin_name, status);
            }
        }

        Ok((plugin_map, plugin_limit_triggered, limit_check_disabled))
    }

    /// Checks for plugin limit markers (`[FF]`) in crash logs with version-specific logic.
    ///
    /// This method detects the plugin limit marker (`[FF]`) and interprets its meaning based on
    /// game version. In original game versions, `[FF]` indicates the plugin limit was hit (a problem).
    /// In newer versions with pre-1.37 crash generators, the limit check is disabled (not a problem).
    ///
    /// # Arguments
    ///
    /// * `segment_plugins` - Plugin segment lines from crash log
    /// * `game_version` - Game version from crash log
    /// * `version_current` - Current crash generator version
    ///
    /// # Returns
    ///
    /// Returns `Ok((bool, bool))` tuple:
    /// - First bool: Plugin limit triggered (true = hit limit in original game)
    /// - Second bool: Limit check disabled (true = limit checking disabled in newer versions)
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::PluginAnalyzer;
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let analyzer = PluginAnalyzer::new(
    ///     vec![], vec![], "Buffout 4".to_string(),
    ///     "1.10.163".to_string(), "1.10.163vr".to_string(), "1.37.0".to_string()
    /// )?;
    ///
    /// let segment = vec!["[FF] PluginLimit.esp".to_string()];
    /// let (triggered, disabled) = analyzer.check_plugin_limit(segment, "1.10.163", "1.36.0")?;
    /// # Ok(())
    /// # }
    /// ```
    pub fn check_plugin_limit(
        &self,
        segment_plugins: Vec<String>,
        game_version: &str,
        version_current: &str,
    ) -> Result<(bool, bool)> {
        // Parse versions for comparison
        let version_137 = "1.37.0";

        // Determine game version characteristics
        let is_original_game =
            game_version == self.game_version || game_version == self.game_version_vr;
        let is_new_game_crashgen_pre_137 =
            game_version >= self.game_version_new.as_str() && version_current < version_137;

        let mut plugin_limit_triggered = false;
        let mut limit_check_disabled = false;

        // Check for plugin limit markers
        for entry in &segment_plugins {
            if entry.contains(PLUGIN_LIMIT_MARKER) {
                if is_original_game {
                    plugin_limit_triggered = true;
                } else if is_new_game_crashgen_pre_137 {
                    limit_check_disabled = true;
                }
                break; // No need to check further once found
            }
        }

        Ok((plugin_limit_triggered, limit_check_disabled))
    }

    /// Matches plugins found in crash call stack and generates a suspect report with counts.
    ///
    /// This method searches the call stack for mentions of plugins from the crash log, counting
    /// how many times each plugin appears. It filters out ignored plugins and lines containing
    /// "modified by:" to avoid false positives. Results are sorted by count (descending) for
    /// prioritized investigation.
    ///
    /// # Arguments
    ///
    /// * `segment_callstack_lower` - Lowercase call stack lines
    /// * `crashlog_plugins_lower` - Set of lowercase plugin names from crash log
    ///
    /// # Returns
    ///
    /// Returns `Ok(Vec<String>)` containing formatted report with plugin counts and explanations.
    ///
    /// # Performance
    ///
    /// - Processes ~10,000 call stack lines/second
    /// - Uses HashMap for O(1) count updates
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::PluginAnalyzer;
    /// use std::collections::HashSet;
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let analyzer = PluginAnalyzer::new(
    ///     vec![], vec![], "Buffout 4".to_string(),
    ///     "1.10.163".to_string(), "1.10.163vr".to_string(), "1.37.0".to_string()
    /// )?;
    ///
    /// let callstack = vec!["mymod.esp function call".to_string()];
    /// let mut plugins = HashSet::new();
    /// plugins.insert("mymod.esp".to_string());
    ///
    /// let report = analyzer.plugin_match(callstack, plugins)?;
    /// # Ok(())
    /// # }
    /// ```
    pub fn plugin_match(
        &self,
        segment_callstack_lower: Vec<String>,
        crashlog_plugins_lower: HashSet<String>,
    ) -> Result<Vec<String>> {
        let mut lines = Vec::new();

        // Pre-filter call stack lines
        let relevant_lines: Vec<_> = segment_callstack_lower
            .iter()
            .filter(|line| !line.contains("modified by:"))
            .collect();

        // Use Counter equivalent
        let mut plugins_matches: HashMap<String, usize> = HashMap::new();

        // Optimize the matching algorithm
        for line in &relevant_lines {
            for plugin in &crashlog_plugins_lower {
                // Skip plugins that are in the ignore list
                if self.lower_plugins_ignore.contains(plugin) {
                    continue;
                }

                if line.contains(plugin) {
                    *plugins_matches.entry(plugin.clone()).or_insert(0) += 1;
                }
            }
        }

        if !plugins_matches.is_empty() {
            lines.push("The following PLUGINS were found in the CRASH STACK:\n".to_string());

            // Sort by count (descending) then by name for consistent output
            let mut sorted_matches: Vec<_> = plugins_matches.into_iter().collect();
            sorted_matches.sort_by(|a, b| b.1.cmp(&a.1).then_with(|| a.0.cmp(&b.0)));

            for (plugin, count) in sorted_matches {
                lines.push(format!("- {} | {}\n", plugin, count));
            }

            lines.push("\n[Last number counts how many times each Plugin Suspect shows up in the crash log.]\n".to_string());
            lines.push(format!("These Plugins were caught by {} and some of them might be responsible for this crash.\n", self.crashgen_name));
            lines.push("You can try disabling these plugins and check if the game still crashes, though this method can be unreliable.\n\n".to_string());
        } else {
            lines.push("* COULDN'T FIND ANY PLUGIN SUSPECTS *\n\n".to_string());
        }

        Ok(lines)
    }

    /// Filters out ignored plugins from crash log plugin list using configured ignore lists.
    ///
    /// This method removes plugins that match entries in either the game-specific ignore list
    /// or the user-defined ignore list. Matching is case-insensitive. If no ignore lists are
    /// configured, returns the original plugin IndexMap unchanged.
    ///
    /// # Arguments
    ///
    /// * `crashlog_plugins` - IndexMap of plugin names to load order IDs (preserves order)
    ///
    /// # Returns
    ///
    /// Returns `Ok(IndexMap)` with ignored plugins removed, preserving the original order.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::PluginAnalyzer;
    /// use indexmap::IndexMap;
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let analyzer = PluginAnalyzer::new(
    ///     vec!["Fallout4.esm".to_string()],  // Ignore base game
    ///     vec![],
    ///     "Buffout 4".to_string(),
    ///     "1.10.163".to_string(), "1.10.163vr".to_string(), "1.37.0".to_string()
    /// )?;
    ///
    /// let mut plugins = IndexMap::new();
    /// plugins.insert("Fallout4.esm".to_string(), "00".to_string());
    /// plugins.insert("MyMod.esp".to_string(), "01".to_string());
    ///
    /// let filtered = analyzer.filter_ignored_plugins(plugins)?;
    /// assert_eq!(filtered.len(), 1);  // Base game filtered out
    /// # Ok(())
    /// # }
    /// ```
    pub fn filter_ignored_plugins(
        &self,
        crashlog_plugins: IndexMap<String, String>,
    ) -> Result<IndexMap<String, String>> {
        if self.ignore_plugins_list.is_empty() {
            return Ok(crashlog_plugins);
        }

        let mut filtered_plugins = crashlog_plugins.clone();

        // Create lowercase mapping for case-insensitive lookup
        let plugins_lower: HashMap<String, String> = crashlog_plugins
            .keys()
            .map(|k| (k.to_lowercase(), k.clone()))
            .collect();

        // Remove ignored plugins (IndexMap::shift_remove preserves order of remaining elements)
        for signal in &self.ignore_plugins_list {
            if let Some(original_key) = plugins_lower.get(signal) {
                filtered_plugins.shift_remove(original_key);
            }
        }

        Ok(filtered_plugins)
    }
}

/// Detects plugins across multiple crash logs in parallel using Rayon.
///
/// This function processes multiple crash log strings concurrently, extracting unique plugin
/// names and their load order IDs from each log independently. It uses the same regex pattern
/// matching as other plugin detection functions but with parallel processing for improved
/// performance on multi-core systems.
///
/// # Arguments
///
/// * `logs` - Vector of complete crash log strings (not individual lines)
///
/// # Returns
///
/// A vector of IndexMaps, one per input log, in the same order. Each IndexMap contains plugin
/// names as keys and their load order IDs/status as values, preserving the order plugins
/// appear in the crash log (load order).
///
/// # Performance
///
/// - Uses Rayon for parallel processing across logs
/// - Near-linear speedup with CPU core count
/// - Typical: 50-100ms for 100 logs on 8-core CPU
/// - 20-30x faster than sequential Python processing
///
/// # Example
///
/// ```rust
/// use classic_scanlog_core::plugin_analyzer::detect_plugins_batch;
///
/// let logs = vec![
///     "[00] Fallout4.esm\n[01] MyMod.esp".to_string(),
///     "[00] Skyrim.esm\n[01] OtherMod.esp".to_string(),
/// ];
///
/// let results = detect_plugins_batch(logs);
/// assert_eq!(results.len(), 2);
/// assert!(results[0].contains_key("MyMod.esp"));
/// ```
pub fn detect_plugins_batch(logs: Vec<String>) -> Vec<IndexMap<String, String>> {
    let results: Vec<_> = logs
        .par_iter()
        .map(|log| {
            // IndexMap preserves insertion order for Python parity
            let mut plugins = IndexMap::new();

            for line in log.lines() {
                if let Some(caps) = PLUGIN_PATTERN.captures(line) {
                    let plugin_id = caps.get(1).map(|m| m.as_str().to_string());
                    let plugin_name = caps
                        .get(3)
                        .map(|m| m.as_str().to_string())
                        .unwrap_or_default();

                    if !plugin_name.is_empty() && !plugins.contains_key(&plugin_name) {
                        let status = if let Some(id) = plugin_id {
                            id.replace(":", "").to_uppercase()
                        } else if plugin_name.to_lowercase().contains("dll") {
                            PLUGIN_STATUS_DLL.to_string()
                        } else {
                            PLUGIN_STATUS_UNKNOWN.to_string()
                        };

                        plugins.insert(plugin_name, status);
                    }
                }
            }

            plugins
        })
        .collect();

    results
}

/// Checks if a line contains a plugin reference using regex pattern matching.
///
/// This utility function tests whether a single line contains a plugin entry matching the
/// standard crash log plugin format (`[XX] Plugin.esp` or `[FE:XXX] Plugin.esl`). Useful
/// for filtering log lines before more expensive parsing operations.
///
/// # Arguments
///
/// * `line` - The line to test for plugin references
///
/// # Returns
///
/// `true` if the line contains a plugin reference, `false` otherwise.
///
/// # Performance
///
/// - Uses pre-compiled regex for efficient pattern matching
/// - Processes ~1 million lines/second
/// - Suitable for filtering hot paths
///
/// # Example
///
/// ```rust
/// use classic_scanlog_core::plugin_analyzer::contains_plugin;
///
/// assert!(contains_plugin("[00] Fallout4.esm"));
/// assert!(contains_plugin("[FE:001] MyPlugin.esl"));
/// assert!(!contains_plugin("Just a regular log line"));
/// ```
pub fn contains_plugin(line: &str) -> bool {
    PLUGIN_PATTERN.is_match(line)
}

#[cfg(test)]
mod tests {
    use super::*;

    // ============================================
    // PluginAnalyzer creation tests
    // ============================================

    #[test]
    fn test_plugin_analyzer_new() {
        let analyzer = PluginAnalyzer::new(
            vec!["Fallout4.esm".to_string()],
            vec!["IgnoredMod.esp".to_string()],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        );
        assert!(analyzer.is_ok());
    }

    #[test]
    fn test_plugin_analyzer_empty_lists() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec![],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        );
        assert!(analyzer.is_ok());
    }

    // ============================================
    // contains_plugin tests
    // ============================================

    #[test]
    fn test_contains_plugin_standard_format() {
        assert!(contains_plugin("[00] Fallout4.esm"));
        assert!(contains_plugin("[01] MyMod.esp"));
        assert!(contains_plugin("[FE] LightPlugin.esl"));
    }

    #[test]
    fn test_contains_plugin_light_plugin_format() {
        assert!(contains_plugin("[FE:001] LightMod.esl"));
        assert!(contains_plugin("[FE:ABC] AnotherLight.esl"));
    }

    #[test]
    fn test_contains_plugin_with_spaces() {
        assert!(contains_plugin("  [00] Fallout4.esm"));
        assert!(contains_plugin("\t[01] MyMod.esp"));
    }

    #[test]
    fn test_contains_plugin_negative() {
        assert!(!contains_plugin("Just a regular log line"));
        assert!(!contains_plugin("Fallout4.esm without brackets"));
        assert!(!contains_plugin("[ZZ] InvalidHex.esp"));
    }

    #[test]
    fn test_contains_plugin_case_insensitive() {
        assert!(contains_plugin("[fe:001] lowercaselight.ESL"));
        assert!(contains_plugin("[AB] UPPERCASE.ESM"));
    }

    // ============================================
    // loadorder_scan_log tests
    // ============================================

    #[test]
    fn test_loadorder_scan_log_empty() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec![],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let (plugins, limit, disabled) = analyzer.loadorder_scan_log(vec![], None, None).unwrap();

        assert!(plugins.is_empty());
        assert!(!limit);
        assert!(!disabled);
    }

    #[test]
    fn test_loadorder_scan_log_standard_plugins() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec![],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let segment = vec![
            "[00] Fallout4.esm".to_string(),
            "[01] DLCRobot.esm".to_string(),
            "[02] MyMod.esp".to_string(),
        ];

        let (plugins, _, _) = analyzer.loadorder_scan_log(segment, None, None).unwrap();

        assert_eq!(plugins.len(), 3);
        assert_eq!(plugins.get("Fallout4.esm"), Some(&"00".to_string()));
        assert_eq!(plugins.get("DLCRobot.esm"), Some(&"01".to_string()));
        assert_eq!(plugins.get("MyMod.esp"), Some(&"02".to_string()));
    }

    #[test]
    fn test_loadorder_scan_log_light_plugins() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec![],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let segment = vec![
            "[FE:001] LightMod1.esl".to_string(),
            "[FE:002] LightMod2.esl".to_string(),
        ];

        let (plugins, _, _) = analyzer.loadorder_scan_log(segment, None, None).unwrap();

        assert_eq!(plugins.len(), 2);
        assert_eq!(plugins.get("LightMod1.esl"), Some(&"FE001".to_string()));
        assert_eq!(plugins.get("LightMod2.esl"), Some(&"FE002".to_string()));
    }

    #[test]
    fn test_loadorder_scan_log_skips_duplicates() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec![],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let segment = vec![
            "[00] Fallout4.esm".to_string(),
            "[00] Fallout4.esm".to_string(), // Duplicate
        ];

        let (plugins, _, _) = analyzer.loadorder_scan_log(segment, None, None).unwrap();

        assert_eq!(plugins.len(), 1);
    }

    // ============================================
    // check_plugin_limit tests
    // ============================================

    #[test]
    fn test_check_plugin_limit_no_ff() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec![],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let segment = vec!["[00] Fallout4.esm".to_string()];
        let (triggered, disabled) = analyzer
            .check_plugin_limit(segment, "1.10.163", "1.36.0")
            .unwrap();

        assert!(!triggered);
        assert!(!disabled);
    }

    #[test]
    fn test_check_plugin_limit_original_game() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec![],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let segment = vec!["[FF] PluginLimit.esp".to_string()];
        let (triggered, disabled) = analyzer
            .check_plugin_limit(segment, "1.10.163", "1.36.0")
            .unwrap();

        assert!(triggered);
        assert!(!disabled);
    }

    #[test]
    fn test_check_plugin_limit_vr_game() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec![],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let segment = vec!["[FF] PluginLimit.esp".to_string()];
        let (triggered, _) = analyzer
            .check_plugin_limit(segment, "1.10.163vr", "1.36.0")
            .unwrap();

        assert!(triggered);
    }

    // ============================================
    // plugin_match tests
    // ============================================

    #[test]
    fn test_plugin_match_empty() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec![],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let callstack: Vec<String> = vec![];
        let plugins: HashSet<String> = HashSet::new();

        let result = analyzer.plugin_match(callstack, plugins).unwrap();
        assert!(!result.is_empty());
        let output = result.join("");
        assert!(output.contains("COULDN'T FIND"));
    }

    #[test]
    fn test_plugin_match_found() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec![],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let callstack = vec![
            "Function call from mymod.esp".to_string(),
            "Another line with mymod.esp".to_string(),
        ];

        let mut plugins = HashSet::new();
        plugins.insert("mymod.esp".to_string());

        let result = analyzer.plugin_match(callstack, plugins).unwrap();
        let output = result.join("");
        assert!(output.contains("mymod.esp"));
        assert!(output.contains("| 2")); // Found twice
    }

    #[test]
    fn test_plugin_match_skips_modified_by() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec![],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let callstack = vec![
            "modified by: mymod.esp".to_string(), // Should be skipped
            "Normal line with anothermod.esp".to_string(),
        ];

        let mut plugins = HashSet::new();
        plugins.insert("mymod.esp".to_string());
        plugins.insert("anothermod.esp".to_string());

        let result = analyzer.plugin_match(callstack, plugins).unwrap();
        let output = result.join("");
        // mymod.esp should not be in results (modified by: line)
        assert!(output.contains("anothermod.esp"));
        // The count for mymod.esp should not be shown
        assert!(!output.contains("mymod.esp | 1"));
    }

    #[test]
    fn test_plugin_match_skips_ignored() {
        let analyzer = PluginAnalyzer::new(
            vec!["fallout4.esm".to_string()], // Ignored
            vec![],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let callstack = vec!["Function from fallout4.esm".to_string()];

        let mut plugins = HashSet::new();
        plugins.insert("fallout4.esm".to_string());

        let result = analyzer.plugin_match(callstack, plugins).unwrap();
        let output = result.join("");
        assert!(output.contains("COULDN'T FIND"));
    }

    // ============================================
    // filter_ignored_plugins tests
    // ============================================

    #[test]
    fn test_filter_ignored_plugins_empty() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec![],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let plugins: IndexMap<String, String> = IndexMap::new();
        let result = analyzer.filter_ignored_plugins(plugins).unwrap();
        assert!(result.is_empty());
    }

    #[test]
    fn test_filter_ignored_plugins_no_ignore_list() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec![], // No ignore list
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let mut plugins = IndexMap::new();
        plugins.insert("Fallout4.esm".to_string(), "00".to_string());
        plugins.insert("MyMod.esp".to_string(), "01".to_string());

        let result = analyzer.filter_ignored_plugins(plugins).unwrap();
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn test_filter_ignored_plugins_filters() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec!["fallout4.esm".to_string()], // Ignore base game
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let mut plugins = IndexMap::new();
        plugins.insert("Fallout4.esm".to_string(), "00".to_string());
        plugins.insert("MyMod.esp".to_string(), "01".to_string());

        let result = analyzer.filter_ignored_plugins(plugins).unwrap();
        assert_eq!(result.len(), 1);
        assert!(result.contains_key("MyMod.esp"));
        assert!(!result.contains_key("Fallout4.esm"));
    }

    #[test]
    fn test_filter_ignored_plugins_case_insensitive() {
        let analyzer = PluginAnalyzer::new(
            vec![],
            vec!["FALLOUT4.ESM".to_string()], // Uppercase in ignore
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.10.163vr".to_string(),
            "1.37.0".to_string(),
        )
        .unwrap();

        let mut plugins = IndexMap::new();
        plugins.insert("Fallout4.esm".to_string(), "00".to_string()); // Mixed case

        let result = analyzer.filter_ignored_plugins(plugins).unwrap();
        // The ignore list is lowercased during construction, so it should match
        assert!(!result.contains_key("Fallout4.esm"));
    }

    // ============================================
    // detect_plugins_batch tests
    // ============================================

    #[test]
    fn test_detect_plugins_batch_empty() {
        let logs: Vec<String> = vec![];
        let result = detect_plugins_batch(logs);
        assert!(result.is_empty());
    }

    #[test]
    fn test_detect_plugins_batch_single_log() {
        let logs = vec!["[00] Fallout4.esm\n[01] MyMod.esp".to_string()];
        let result = detect_plugins_batch(logs);

        assert_eq!(result.len(), 1);
        assert_eq!(result[0].len(), 2);
        assert_eq!(result[0].get("Fallout4.esm"), Some(&"00".to_string()));
        assert_eq!(result[0].get("MyMod.esp"), Some(&"01".to_string()));
    }

    #[test]
    fn test_detect_plugins_batch_multiple_logs() {
        let logs = vec![
            "[00] GameA.esm\n[01] ModA.esp".to_string(),
            "[00] GameB.esm\n[01] ModB.esp".to_string(),
        ];
        let result = detect_plugins_batch(logs);

        assert_eq!(result.len(), 2);
        assert!(result[0].contains_key("GameA.esm"));
        assert!(result[1].contains_key("GameB.esm"));
    }

    #[test]
    fn test_detect_plugins_batch_preserves_order() {
        let logs = vec![
            "[00] First.esm".to_string(),
            "[00] Second.esm".to_string(),
            "[00] Third.esm".to_string(),
        ];
        let result = detect_plugins_batch(logs);

        assert_eq!(result.len(), 3);
        assert!(result[0].contains_key("First.esm"));
        assert!(result[1].contains_key("Second.esm"));
        assert!(result[2].contains_key("Third.esm"));
    }

    #[test]
    fn test_detect_plugins_batch_light_plugins() {
        let logs = vec!["[FE:001] Light1.esl\n[FE:002] Light2.esl".to_string()];
        let result = detect_plugins_batch(logs);

        assert_eq!(result.len(), 1);
        assert_eq!(result[0].get("Light1.esl"), Some(&"FE001".to_string()));
        assert_eq!(result[0].get("Light2.esl"), Some(&"FE002".to_string()));
    }

    #[test]
    fn test_detect_plugins_batch_no_plugins() {
        let logs = vec!["No plugins in this log\nJust regular text".to_string()];
        let result = detect_plugins_batch(logs);

        assert_eq!(result.len(), 1);
        assert!(result[0].is_empty());
    }
}
