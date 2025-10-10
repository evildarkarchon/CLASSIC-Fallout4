//! Mod detector module - High-performance mod detection and conflict analysis
//!
//! This module provides exact behavioral parity with Python's DetectMods
//! while leveraging Rust's performance optimizations.

use pyo3::prelude::*;
use rayon::prelude::*;
use regex::Regex;
use std::collections::{HashMap, HashSet};

/// Convert dictionary keys to lowercase
fn convert_to_lowercase(data: &HashMap<String, String>) -> HashMap<String, String> {
    data.iter()
        .map(|(k, v)| (k.to_lowercase(), v.clone()))
        .collect()
}

/// Validate that a mod has a warning
fn validate_warning(mod_name: &str, warning: &str) -> PyResult<()> {
    if warning.is_empty() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "ERROR: {} has no warning in the database!",
            mod_name
        )));
    }
    Ok(())
}

/// Detect single mods based on YAML mappings and crash log plugins
#[pyfunction]
#[pyo3(signature = (yaml_dict, crashlog_plugins))]
pub fn detect_mods_single(
    _py: Python<'_>,
    yaml_dict: HashMap<String, String>,
    crashlog_plugins: HashMap<String, String>,
) -> PyResult<Vec<String>> {
    let mut lines = Vec::new();
    let yaml_dict_lower = convert_to_lowercase(&yaml_dict);
    let crashlog_plugins_lower = convert_to_lowercase(&crashlog_plugins);

    // Sort mod names by length (longest first) to find most specific matches first
    let mut mod_items: Vec<(String, String)> = yaml_dict_lower.into_iter().collect();
    mod_items.sort_by(|a, b| b.0.len().cmp(&a.0.len()));

    if mod_items.is_empty() {
        return Ok(vec![]);
    }

    // Build patterns for efficient matching
    let mod_patterns: Vec<String> = mod_items
        .iter()
        .map(|(mod_name, _)| regex::escape(mod_name))
        .collect();

    // Create a single compiled pattern with alternation for efficient matching
    let combined_pattern = Regex::new(&format!("(?i){}", mod_patterns.join("|"))).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Regex error: {}", e))
    })?;

    // Create a lookup dictionary for O(1) access to mod warnings
    let mod_lookup: HashMap<String, String> = mod_items.iter().cloned().collect();

    // Track matching plugins for each mod
    let mut mod_matches: HashMap<String, String> = HashMap::new();

    // Process each plugin once with the combined pattern
    for (plugin_name, plugin_id) in &crashlog_plugins_lower {
        if let Some(mat) = combined_pattern.find(plugin_name) {
            let matched_mod = mat.as_str().to_lowercase();
            // Only store the first match for each mod
            if !mod_matches.contains_key(&matched_mod) {
                mod_matches.insert(matched_mod, plugin_id.clone());
            }
        }
    }

    // Build output lines for all matches
    let mut sorted_mods: Vec<_> = mod_matches.keys().cloned().collect();
    sorted_mods.sort_by(|a, b| b.len().cmp(&a.len()));

    for mod_name in sorted_mods {
        let mod_warning = &mod_lookup[&mod_name];
        validate_warning(&mod_name, mod_warning)?;

        let plugin_id = &mod_matches[&mod_name];
        let plugin_list = format!("[{}]", plugin_id);

        // Build the complete entry using hybrid approach with Qt-compatible newlines
        let warning_lines: Vec<&str> = mod_warning.lines().collect();
        if !warning_lines.is_empty() {
            // First line (mod name) goes on the same line as FOUND header
            let mod_name_display = warning_lines[0].trim();
            lines.push(format!(
                "**[!] FOUND : {} {}**\n\n",
                plugin_list, mod_name_display
            ));

            // Remaining lines are indented with double newlines for Qt compatibility
            for line in &warning_lines[1..] {
                if !line.trim().is_empty() {
                    lines.push(format!("    {}\n\n", line));
                } else {
                    lines.push("\n".to_string());
                }
            }
        } else {
            lines.push(format!("**[!] FOUND : {}**\n\n", plugin_list));
        }
    }

    Ok(lines)
}

/// Detect mod conflicts or combinations
#[pyfunction]
#[pyo3(signature = (yaml_dict, crashlog_plugins))]
pub fn detect_mods_double(
    _py: Python<'_>,
    yaml_dict: HashMap<String, String>,
    crashlog_plugins: HashMap<String, String>,
) -> PyResult<Vec<String>> {
    let mut lines = Vec::new();
    let yaml_dict_lower = convert_to_lowercase(&yaml_dict);
    let crashlog_plugins_lower = convert_to_lowercase(&crashlog_plugins);

    // Build a set of all unique mod names from the pairs
    let mut all_mod_names: HashSet<String> = HashSet::new();
    let mut mod_pairs_map: HashMap<(String, String), String> = HashMap::new();

    for (mod_pair, mod_warning) in yaml_dict_lower {
        let parts: Vec<&str> = mod_pair.split(" | ").collect();
        if parts.len() == 2 {
            let mod1 = parts[0].to_string();
            let mod2 = parts[1].to_string();
            all_mod_names.insert(mod1.clone());
            all_mod_names.insert(mod2.clone());
            mod_pairs_map.insert((mod1, mod2), mod_warning);
        }
    }

    if all_mod_names.is_empty() {
        return Ok(vec![]);
    }

    // Create a single regex pattern to find all mods in one pass
    let mod_patterns: Vec<String> = all_mod_names
        .iter()
        .map(|mod_name| regex::escape(mod_name))
        .collect();
    let combined_pattern = Regex::new(&format!("(?i){}", mod_patterns.join("|"))).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Regex error: {}", e))
    })?;

    // Find which mods are present in the plugins
    let mut mods_present: HashSet<String> = HashSet::new();
    for plugin_name in crashlog_plugins_lower.keys() {
        for mat in combined_pattern.find_iter(plugin_name) {
            mods_present.insert(mat.as_str().to_lowercase());
        }
    }

    // Check for conflicting pairs
    for ((mod1, mod2), mod_warning) in &mod_pairs_map {
        if mods_present.contains(mod1) && mods_present.contains(mod2) {
            validate_warning(&format!("{} | {}", mod1, mod2), mod_warning)?;
            lines.push("[!] CAUTION : Conflicting mods detected\n".to_string());
            lines.push(mod_warning.clone());
            if !mod_warning.ends_with('\n') {
                lines.push("\n".to_string());
            }
            lines.push("\n".to_string());
        }
    }

    Ok(lines)
}

/// Detect important mods and check GPU compatibility
#[pyfunction]
pub fn detect_mods_important(
    _py: Python<'_>,
    yaml_dict: HashMap<String, String>,
    crashlog_plugins: HashMap<String, String>,
    gpu_rival: Option<&str>,
    xse_modules: HashSet<String>,
) -> PyResult<Vec<String>> {
    let mut lines = vec!["### Checking for Important Mods\n\n".to_string()];

    // Convert plugin names to lowercase once
    let plugin_names_lower: Vec<String> =
        crashlog_plugins.keys().map(|k| k.to_lowercase()).collect();

    // Add XSE module names (DLL files) to the search space
    let module_names_lower: Vec<String> = xse_modules.iter().map(|m| m.to_lowercase()).collect();

    let mut all_names = plugin_names_lower;
    all_names.extend(module_names_lower);
    let all_plugins_text = all_names.join(" ");

    // Build patterns for all mod IDs
    let mut mod_patterns: HashMap<String, Regex> = HashMap::new();
    for mod_entry in yaml_dict.keys() {
        let parts: Vec<&str> = mod_entry.split(" | ").collect();
        if parts.len() == 2 {
            let mod_id = parts[0];
            let pattern = Regex::new(&format!("(?i){}", regex::escape(&mod_id.to_lowercase())))
                .map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Regex error: {}", e))
                })?;
            mod_patterns.insert(mod_entry.clone(), pattern);
        }
    }

    for (mod_entry, mod_warning) in &yaml_dict {
        let parts: Vec<&str> = mod_entry.split(" | ").collect();
        if parts.len() != 2 {
            continue;
        }

        let _mod_id = parts[0];
        let mod_display_name = parts[1];

        let mod_found = mod_patterns
            .get(mod_entry)
            .map(|pattern| pattern.is_match(&all_plugins_text))
            .unwrap_or(false);

        if mod_found {
            if let Some(gpu) = gpu_rival {
                if mod_warning.to_lowercase().contains(gpu) {
                    lines.push("\n\n".to_string());
                    lines.push(format!(
                        "❓ {} is installed, BUT IT SEEMS YOU DON'T HAVE AN {} GPU?\n",
                        mod_display_name,
                        gpu.to_uppercase()
                    ));
                    lines.push("IF THIS IS CORRECT, COMPLETELY UNINSTALL THIS MOD TO AVOID ANY PROBLEMS! \n\n".to_string());
                } else {
                    lines.push(format!("\n✔️ {} is installed!\n\n", mod_display_name));
                }
            } else {
                lines.push(format!("\n✔️ {} is installed!\n\n", mod_display_name));
            }
        } else if let Some(gpu) = gpu_rival {
            if !mod_warning.is_empty() && !mod_warning.to_lowercase().contains(gpu) {
                lines.push(format!("\n❌ {} is not installed!\n", mod_display_name));
                lines.push(mod_warning.clone());
                lines.push("\n\n".to_string());
            }
        }
    }

    Ok(lines)
}

/// Batch detect mods across multiple crash logs
#[pyfunction]
pub fn detect_mods_batch(
    yaml_dict: HashMap<String, String>,
    crashlog_plugins_list: Vec<HashMap<String, String>>,
) -> PyResult<Vec<Vec<String>>> {
    let yaml_dict_lower = convert_to_lowercase(&yaml_dict);

    // Build patterns once
    let mod_patterns: Vec<String> = yaml_dict_lower
        .keys()
        .map(|mod_name| regex::escape(mod_name))
        .collect();

    if mod_patterns.is_empty() {
        return Ok(vec![vec![]; crashlog_plugins_list.len()]);
    }

    let combined_pattern = Regex::new(&format!("(?i){}", mod_patterns.join("|"))).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Regex error: {}", e))
    })?;

    // Process crash logs in parallel
    let results: Result<Vec<_>, _> = crashlog_plugins_list
        .par_iter()
        .map(|crashlog_plugins| {
            let mut lines = Vec::new();
            let crashlog_plugins_lower = convert_to_lowercase(crashlog_plugins);

            let mut mod_matches: HashMap<String, String> = HashMap::new();

            for (plugin_name, plugin_id) in &crashlog_plugins_lower {
                if let Some(mat) = combined_pattern.find(plugin_name) {
                    let matched_mod = mat.as_str().to_lowercase();
                    if !mod_matches.contains_key(&matched_mod) {
                        mod_matches.insert(matched_mod, plugin_id.clone());
                    }
                }
            }

            for (mod_name, plugin_id) in &mod_matches {
                if let Some(mod_warning) = yaml_dict_lower.get(mod_name) {
                    if mod_warning.is_empty() {
                        return Err(format!(
                            "ERROR: {} has no warning in the database!",
                            mod_name
                        ));
                    }

                    let plugin_list = format!("[{}]", plugin_id);
                    let warning_lines: Vec<&str> = mod_warning.lines().collect();

                    if !warning_lines.is_empty() {
                        let mod_name_display = warning_lines[0].trim();
                        lines.push(format!(
                            "**[!] FOUND : {} {}**\n\n",
                            plugin_list, mod_name_display
                        ));

                        for line in &warning_lines[1..] {
                            if !line.trim().is_empty() {
                                lines.push(format!("    {}\n\n", line));
                            } else {
                                lines.push("\n".to_string());
                            }
                        }
                    } else {
                        lines.push(format!("**[!] FOUND : {}**\n\n", plugin_list));
                    }
                }
            }

            Ok(lines)
        })
        .collect();

    results.map_err(|e: String| PyErr::new::<pyo3::exceptions::PyValueError, _>(e))
}
