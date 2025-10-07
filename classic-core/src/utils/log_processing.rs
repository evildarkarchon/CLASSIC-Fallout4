//! Specialized string utilities optimized for crash log processing
//!
//! This module provides high-performance string operations specifically
//! designed for parsing and analyzing Bethesda game crash logs.

use pyo3::prelude::*;
use rayon::prelude::*;
use regex::Regex;
use aho_corasick::{AhoCorasick, AhoCorasickBuilder};
use dashmap::DashMap;
use once_cell::sync::Lazy;
use std::sync::Arc;
use memchr::memmem;

use super::performance::Timer;

/// Cache for compiled regex patterns
static PATTERN_CACHE: Lazy<Arc<DashMap<String, Regex>>> = Lazy::new(|| {
    Arc::new(DashMap::new())
});

/// Log processor optimized for crash log analysis
#[pyclass]
pub struct LogProcessor {
    /// Multi-pattern matcher for efficient searching
    pattern_matcher: Option<AhoCorasick>,
    /// Segment boundaries for log parsing
    segment_patterns: Vec<(String, String)>,
    /// Cache for frequently used patterns
    local_cache: Arc<DashMap<String, Regex>>,
}

#[pymethods]
impl LogProcessor {
    #[new]
    pub fn new() -> Self {
        // Common patterns in crash logs
        let default_segments = vec![
            ("MODULES:".to_string(), "STACK:".to_string()),
            ("STACK:".to_string(), "REGISTERS:".to_string()),
            ("REGISTERS:".to_string(), "STACK WALK:".to_string()),
            ("PROBABLE CALL STACK:".to_string(), "REGISTERS:".to_string()),
        ];

        Self {
            pattern_matcher: None,
            segment_patterns: default_segments,
            local_cache: Arc::new(DashMap::new()),
        }
    }

    /// Initialize multi-pattern matcher with common crash log patterns
    #[pyo3(signature = (patterns))]
    pub fn init_pattern_matcher(&mut self, patterns: Vec<String>) -> PyResult<()> {
        let ac = AhoCorasickBuilder::new()
            .ascii_case_insensitive(true)
            .build(&patterns)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

        self.pattern_matcher = Some(ac);
        Ok(())
    }

    /// Find all occurrences of multiple patterns in text (optimized for crash logs)
    #[pyo3(signature = (text, patterns))]
    pub fn find_all_patterns(&self, text: String, patterns: Vec<String>) -> Vec<(String, Vec<usize>)> {
        let _timer = Timer::start("find_all_patterns");

        // Build temporary matcher if not initialized
        let ac = match &self.pattern_matcher {
            Some(matcher) => matcher.clone(),
            None => {
                AhoCorasickBuilder::new()
                    .ascii_case_insensitive(true)
                    .build(&patterns)
                    .unwrap()
            }
        };

        let mut results: Vec<(String, Vec<usize>)> = patterns
            .iter()
            .map(|p| (p.clone(), Vec::new()))
            .collect();

        for mat in ac.find_iter(&text) {
            results[mat.pattern().as_usize()].1.push(mat.start());
        }

        drop(_timer);
        results
    }

    /// Parse log into segments based on section headers
    #[pyo3(signature = (lines))]
    pub fn parse_segments(&self, lines: Vec<String>) -> Vec<(String, Vec<String>)> {
        let mut timer = Timer::start("parse_segments");
        timer.set_bytes(lines.iter().map(|l| l.len() as u64).sum());

        let mut segments = Vec::new();
        let mut current_section = String::from("HEADER");
        let mut current_lines = Vec::new();

        for line in lines {
            let line_upper = line.to_uppercase();

            // Check if this line starts a new section
            let mut found_section = false;
            for (start, _) in &self.segment_patterns {
                if line_upper.contains(start) {
                    // Save previous section
                    if !current_lines.is_empty() {
                        segments.push((current_section.clone(), current_lines.clone()));
                        current_lines.clear();
                    }
                    current_section = start.clone();
                    found_section = true;
                    break;
                }
            }

            if !found_section {
                current_lines.push(line);
            }
        }

        // Save last section
        if !current_lines.is_empty() {
            segments.push((current_section, current_lines));
        }

        segments
    }

    /// Extract FormIDs from text using optimized pattern matching
    #[pyo3(signature = (text))]
    pub fn extract_formids(&self, text: String) -> Vec<String> {
        let mut timer = Timer::start("extract_formids");
        timer.set_bytes(text.len() as u64);

        // Get or compile regex pattern
        let pattern = self.get_or_compile_pattern(
            "formid",
            r"(?i)(?:0x)?([0-9a-f]{6,8})\b"
        );

        pattern.find_iter(&text)
            .map(|m| m.as_str().to_string())
            .collect()
    }

    /// Extract plugin names from crash log
    #[pyo3(signature = (text))]
    pub fn extract_plugins(&self, text: String) -> Vec<String> {
        let _timer = Timer::start("extract_plugins");

        // Common plugin file extensions
        let extensions = vec![".esp", ".esm", ".esl", ".esq"];
        let mut plugins = Vec::new();

        for line in text.lines() {
            let line_lower = line.to_lowercase();
            for ext in &extensions {
                if line_lower.contains(ext) {
                    // Extract plugin name (look for word boundaries)
                    if let Some(plugin) = self.extract_plugin_name(line, ext) {
                        if !plugins.contains(&plugin) {
                            plugins.push(plugin);
                        }
                    }
                }
            }
        }

        drop(_timer);
        plugins
    }

    /// Find stack frames with addresses and module information
    #[pyo3(signature = (lines))]
    pub fn extract_stack_frames(&self, lines: Vec<String>) -> Vec<(String, Option<String>, Option<String>)> {
        let _timer = Timer::start("extract_stack_frames");

        lines.par_iter()
            .filter_map(|line| {
                // Pattern: address module+offset or address symbol
                let pattern = self.get_or_compile_pattern(
                    "stack_frame",
                    r"(?i)([0-9a-f]{8,16})\s+(\w+(?:\.\w+)?)\s*\+?\s*([0-9a-f]+)?"
                );

                pattern.captures(line).map(|caps| {
                    let address = caps.get(1).map(|m| m.as_str().to_string()).unwrap_or_default();
                    let module = caps.get(2).map(|m| m.as_str().to_string());
                    let offset = caps.get(3).map(|m| m.as_str().to_string());
                    (address, module, offset)
                })
            })
            .collect()
    }

    /// Fast line filtering based on keywords
    #[pyo3(signature = (lines, include_keywords=None, exclude_keywords=None))]
    pub fn filter_lines(
        &self,
        lines: Vec<String>,
        include_keywords: Option<Vec<String>>,
        exclude_keywords: Option<Vec<String>>,
    ) -> Vec<String> {
        let _timer = Timer::start("filter_lines");

        lines.par_iter()
            .filter(|line| {
                let line_lower = line.to_lowercase();

                // Check include keywords
                if let Some(ref includes) = include_keywords {
                    if !includes.iter().any(|kw| line_lower.contains(&kw.to_lowercase())) {
                        return false;
                    }
                }

                // Check exclude keywords
                if let Some(ref excludes) = exclude_keywords {
                    if excludes.iter().any(|kw| line_lower.contains(&kw.to_lowercase())) {
                        return false;
                    }
                }

                true
            })
            .cloned()
            .collect()
    }

    /// Count occurrences of patterns in parallel
    #[pyo3(signature = (text, patterns))]
    pub fn count_patterns(&self, text: String, patterns: Vec<String>) -> Vec<(String, usize)> {
        let _timer = Timer::start("count_patterns");

        patterns.par_iter()
            .map(|pattern| {
                let count = text.matches(pattern.as_str()).count();
                (pattern.clone(), count)
            })
            .collect()
    }

    /// Split crash log into logical sections
    #[pyo3(signature = (text))]
    pub fn split_into_sections(&self, text: String) -> Vec<(String, String)> {
        let mut timer = Timer::start("split_into_sections");
        timer.set_bytes(text.len() as u64);

        let mut sections = Vec::new();
        let mut current_section = String::from("HEADER");
        let mut current_content = String::new();

        // Section markers commonly found in crash logs
        let markers = vec![
            "SYSTEM SPECS:", "PROBABLE CALL STACK:", "REGISTERS:",
            "STACK WALK:", "MODULES:", "STACK:", "MEMORY MAP:",
            "GAME LOADED:", "PLUGINS:", "SETTINGS:", "INI CONFIGURATION:",
        ];

        for line in text.lines() {
            let line_upper = line.to_uppercase();

            let mut found_marker = false;
            for marker in &markers {
                if line_upper.starts_with(marker) {
                    // Save previous section
                    if !current_content.is_empty() {
                        sections.push((current_section.clone(), current_content.clone()));
                        current_content.clear();
                    }
                    current_section = marker.to_string();
                    found_marker = true;
                    break;
                }
            }

            if !found_marker {
                current_content.push_str(line);
                current_content.push('\n');
            }
        }

        // Save last section
        if !current_content.is_empty() {
            sections.push((current_section, current_content));
        }

        sections
    }

    /// Fast substring search using memchr
    #[pyo3(signature = (text, needle, case_insensitive=false))]
    pub fn fast_find(&self, text: String, needle: String, case_insensitive: bool) -> Vec<usize> {
        let _timer = Timer::start("fast_find");

        if case_insensitive {
            let text_lower = text.to_lowercase();
            let needle_lower = needle.to_lowercase();
            let finder = memmem::Finder::new(&needle_lower);
            finder.find_iter(text_lower.as_bytes())
                .map(|pos| pos)
                .collect()
        } else {
            let finder = memmem::Finder::new(&needle);
            finder.find_iter(text.as_bytes())
                .map(|pos| pos)
                .collect()
        }
    }

    /// Process lines in parallel with a custom function
    #[pyo3(signature = (lines, operation))]
    pub fn process_lines_parallel(&self, lines: Vec<String>, operation: String) -> Vec<String> {
        let _timer = Timer::start(format!("process_lines_{}", operation));

        lines.par_iter()
            .map(|line| {
                match operation.as_str() {
                    "trim" => line.trim().to_string(),
                    "upper" => line.to_uppercase(),
                    "lower" => line.to_lowercase(),
                    "strip_timestamps" => self.strip_timestamp(line),
                    "normalize_whitespace" => self.normalize_whitespace(line),
                    _ => line.clone(),
                }
            })
            .collect()
    }
}

// Internal helper methods (not exposed to Python)
impl LogProcessor {
    /// Get or compile a regex pattern with caching (internal use only)
    fn get_or_compile_pattern(&self, name: &str, pattern: &str) -> Regex {
        if let Some(cached) = self.local_cache.get(name) {
            return cached.clone();
        }

        if let Some(cached) = PATTERN_CACHE.get(pattern) {
            self.local_cache.insert(name.to_string(), cached.clone());
            return cached.clone();
        }

        let regex = Regex::new(pattern).unwrap_or_else(|_| Regex::new(r".*").unwrap());
        self.local_cache.insert(name.to_string(), regex.clone());
        PATTERN_CACHE.insert(pattern.to_string(), regex.clone());

        regex
    }

    /// Clear pattern caches
    pub fn clear_cache(&self) {
        self.local_cache.clear();
    }

    /// Get cache statistics
    pub fn cache_stats(&self) -> (usize, usize) {
        (self.local_cache.len(), PATTERN_CACHE.len())
    }
}

// Internal helper methods (not exposed to Python)
impl LogProcessor {
    /// Strip timestamp from log line (internal use only)
    fn strip_timestamp(&self, line: &str) -> String {
        // Common timestamp patterns
        let pattern = self.get_or_compile_pattern(
            "timestamp",
            r"^\s*\[?\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\]?\s*"
        );

        pattern.replace(line, "").to_string()
    }

    /// Normalize whitespace in a line (internal use only, not exposed to Python)
    fn normalize_whitespace(&self, line: &str) -> String {
        let mut result = String::with_capacity(line.len());
        let mut prev_was_space = false;

        for ch in line.chars() {
            if ch.is_whitespace() {
                if !prev_was_space {
                    result.push(' ');
                    prev_was_space = true;
                }
            } else {
                result.push(ch);
                prev_was_space = false;
            }
        }

        result.trim().to_string()
    }

    /// Helper to extract plugin name from a line (internal use only)
    fn extract_plugin_name(&self, line: &str, extension: &str) -> Option<String> {
        let line_lower = line.to_lowercase();
        if let Some(pos) = line_lower.find(extension) {
            // Find the start of the plugin name
            let start_chars = line[..pos].chars().rev();
            let mut start_pos = pos;

            for ch in start_chars {
                if ch.is_whitespace() || ch == '\\' || ch == '/' || ch == '[' || ch == '(' {
                    break;
                }
                start_pos -= ch.len_utf8();
            }

            let plugin = &line[start_pos..pos + extension.len()];
            if !plugin.is_empty() {
                return Some(plugin.to_string());
            }
        }
        None
    }
}
