//! Plugin analyzer module - High-performance plugin detection and analysis
//!
//! This module provides exact behavioral parity with Python's PluginAnalyzer
//! while leveraging Rust's performance optimizations.

use dashmap::DashMap;
use once_cell::sync::Lazy;
use pyo3::prelude::*;
use pyo3::types::PyDict;
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

/// Core plugin analyzer - exact behavioral match to Python PluginAnalyzer
#[pyclass]
pub struct PluginAnalyzer {
    lower_plugins_ignore: HashSet<String>,
    ignore_plugins_list: HashSet<String>,
    yamldata_crashgen_name: String,
    game_version: String,
    game_version_vr: String,
    game_version_new: String,
    #[allow(dead_code)] // Reserved for future case-insensitive matching optimization
    case_cache: Arc<DashMap<String, String>>,
}

#[pymethods]
impl PluginAnalyzer {
    #[new]
    #[pyo3(signature = (yamldata))]
    pub fn new(yamldata: &Bound<'_, PyAny>) -> PyResult<Self> {
        // Extract game ignore plugins
        let game_ignore_plugins: Vec<String> =
            if let Ok(ignore_list) = yamldata.getattr("game_ignore_plugins") {
                ignore_list.extract()?
            } else {
                Vec::new()
            };

        // Extract ignore list
        let ignore_list: Vec<String> = if let Ok(list) = yamldata.getattr("ignore_list") {
            list.extract()?
        } else {
            Vec::new()
        };

        // Extract game version info - handle both Version objects and strings
        let game_version = if let Ok(ver) = yamldata.getattr("game_version") {
            // Try to get string representation - Version objects have __str__ method
            if let Ok(ver_str) = ver.call_method0("__str__") {
                ver_str
                    .extract::<String>()
                    .unwrap_or_else(|_| "1.10.163".to_string())
            } else {
                ver.extract::<String>()
                    .unwrap_or_else(|_| "1.10.163".to_string())
            }
        } else {
            "1.10.163".to_string()
        };

        let game_version_vr = if let Ok(ver) = yamldata.getattr("game_version_vr") {
            // Try to get string representation - Version objects have __str__ method
            if let Ok(ver_str) = ver.call_method0("__str__") {
                ver_str
                    .extract::<String>()
                    .unwrap_or_else(|_| "1.10.163".to_string())
            } else {
                ver.extract::<String>()
                    .unwrap_or_else(|_| "1.10.163".to_string())
            }
        } else {
            "1.10.163".to_string()
        };

        let game_version_new = if let Ok(ver) = yamldata.getattr("game_version_new") {
            // Try to get string representation - Version objects have __str__ method
            if let Ok(ver_str) = ver.call_method0("__str__") {
                ver_str
                    .extract::<String>()
                    .unwrap_or_else(|_| "1.10.984".to_string())
            } else {
                ver.extract::<String>()
                    .unwrap_or_else(|_| "1.10.984".to_string())
            }
        } else {
            "1.10.984".to_string()
        };

        let crashgen_name = if let Ok(name) = yamldata.getattr("crashgen_name") {
            name.extract::<String>()
                .unwrap_or_else(|_| "Buffout4".to_string())
        } else {
            "Buffout4".to_string()
        };

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
            yamldata_crashgen_name: crashgen_name,
            game_version,
            game_version_vr,
            game_version_new,
            case_cache: Arc::new(DashMap::new()),
        })
    }

    /// Scans loadorder.txt file and returns plugin data
    /// Returns: (plugins_dict, plugins_loaded, report_lines)
    #[staticmethod]
    pub fn loadorder_scan_loadorder_txt(py: Python) -> PyResult<(Py<PyDict>, bool, Vec<String>)> {
        let mut lines = vec![
            "* ✔️ LOADORDER.TXT FILE FOUND IN THE MAIN CLASSIC FOLDER! *\n".to_string(),
            "CLASSIC will now ignore plugins in all crash logs and only detect plugins in this file.\n".to_string(),
            "[ To disable this functionality, simply remove loadorder.txt from your CLASSIC folder. ]\n\n".to_string(),
        ];

        let loadorder_plugins = PyDict::new(py);
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
                                && !loadorder_plugins.contains(plugin_entry)?
                            {
                                loadorder_plugins
                                    .set_item(plugin_entry, PLUGIN_ORIGIN_LOADORDER)?;
                            }
                        }
                    }
                }
                Err(e) => {
                    lines.push(format!("Error reading loadorder.txt: {}\n", e));
                }
            }
        }

        let plugins_loaded = loadorder_plugins.len() > 0;

        Ok((loadorder_plugins.into(), plugins_loaded, lines))
    }

    /// Scans log for plugins and returns just the load order
    /// This is the simplified version that only parses plugins, no version-specific logic
    pub fn loadorder_scan_log(&self, segment_plugins: Vec<String>) -> PyResult<Vec<String>> {
        // Early return for empty input
        if segment_plugins.is_empty() {
            return Ok(Vec::new());
        }

        // Collect unique plugins in order
        let mut plugin_list = Vec::new();
        let mut seen = HashSet::new();

        // Process each plugin entry to extract plugin names
        for entry in &segment_plugins {
            // Extract plugin information using regex
            if let Some(caps) = PLUGIN_PATTERN.captures(entry) {
                if let Some(plugin_name_match) = caps.get(3) {
                    let plugin_name = plugin_name_match.as_str().to_string();

                    // Add unique plugins in order
                    if !plugin_name.is_empty() && !seen.contains(&plugin_name) {
                        seen.insert(plugin_name.clone());
                        plugin_list.push(plugin_name);
                    }
                }
            }
        }

        Ok(plugin_list)
    }

    /// Check for plugin limit markers separately from load order parsing
    /// Returns: (plugin_limit_triggered, limit_check_disabled)
    pub fn check_plugin_limit(
        &self,
        segment_plugins: Vec<String>,
        game_version: &str,
        version_current: &str,
    ) -> PyResult<(bool, bool)> {
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

    /// Matches plugins in call stack and generates report
    pub fn plugin_match(
        &self,
        segment_callstack_lower: Vec<String>,
        crashlog_plugins_lower: HashSet<String>,
    ) -> PyResult<Vec<String>> {
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
            lines.push(format!("These Plugins were caught by {} and some of them might be responsible for this crash.\n", self.yamldata_crashgen_name));
            lines.push("You can try disabling these plugins and check if the game still crashes, though this method can be unreliable.\n\n".to_string());
        } else {
            lines.push("* COULDN'T FIND ANY PLUGIN SUSPECTS *\n\n".to_string());
        }

        Ok(lines)
    }

    /// Filters out ignored plugins from crashlog plugins
    pub fn filter_ignored_plugins(
        &self,
        crashlog_plugins: HashMap<String, String>,
    ) -> PyResult<HashMap<String, String>> {
        if self.ignore_plugins_list.is_empty() {
            return Ok(crashlog_plugins);
        }

        let mut filtered_plugins = crashlog_plugins.clone();

        // Create lowercase mapping
        let plugins_lower: HashMap<String, String> = crashlog_plugins
            .keys()
            .map(|k| (k.to_lowercase(), k.clone()))
            .collect();

        // Remove ignored plugins
        for signal in &self.ignore_plugins_list {
            if let Some(original_key) = plugins_lower.get(signal) {
                filtered_plugins.remove(original_key);
            }
        }

        Ok(filtered_plugins)
    }
}

/// Batch process plugin detection across multiple logs
#[pyfunction]
pub fn detect_plugins_batch(logs: Vec<String>) -> PyResult<Vec<HashMap<String, String>>> {
    let results: Vec<_> = logs
        .par_iter()
        .map(|log| {
            let mut plugins = HashMap::new();

            for line in log.lines() {
                if let Some(caps) = PLUGIN_PATTERN.captures(line) {
                    let plugin_id = caps.get(1).map(|m| m.as_str().to_string());
                    let plugin_name = caps
                        .get(3)
                        .map(|m| m.as_str().to_string())
                        .unwrap_or_default();

                    if !plugin_name.is_empty() && !plugins.contains_key(&plugin_name) {
                        let status = if let Some(id) = plugin_id {
                            id.replace(":", "")
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

    Ok(results)
}

/// Check if a line contains a plugin reference
#[pyfunction]
pub fn contains_plugin(line: &str) -> bool {
    PLUGIN_PATTERN.is_match(line)
}
