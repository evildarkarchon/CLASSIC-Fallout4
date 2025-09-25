//! High-performance log parsing with segment detection and SIMD optimizations
//!
//! This module provides efficient crash log parsing with:
//! - Compiled regex patterns for performance
//! - Parallel processing with rayon
//! - SIMD operations for boundary detection (where applicable)
//! - Smart caching for repeated patterns
//! - Expected 15-30x improvement over Python implementation

use pyo3::prelude::*;
use rayon::prelude::*;
use regex::Regex;
use std::sync::Arc;
use once_cell::sync::Lazy;
use dashmap::DashMap;
use memchr::{memchr, memmem};
use std::collections::HashMap;

/// Pre-compiled regex patterns for common crash log patterns
static COMMON_PATTERNS: Lazy<HashMap<&'static str, Regex>> = Lazy::new(|| {
    let mut patterns = HashMap::new();
    patterns.insert("error", Regex::new(r"(?i)\b(error|exception|crash|fault|violation)\b").unwrap());
    patterns.insert("formid", Regex::new(r"(?i)\b(?:form\s*id|formid)[:\s]+([0-9a-f]{8})\b").unwrap());
    patterns.insert("plugin", Regex::new(r"(?i)\[([0-9a-f]{2})\]\s+(.+\.es[lmp])").unwrap());
    patterns.insert("address", Regex::new(r"0x[0-9A-Fa-f]{8,16}").unwrap());
    patterns.insert("module", Regex::new(r"(\w+\.dll)\s+v?([0-9.]+)?").unwrap());
    patterns.insert("stack_frame", Regex::new(r"\[([0-9]+)\]\s+0x[0-9A-Fa-f]+").unwrap());
    patterns.insert("register", Regex::new(r"(RAX|RBX|RCX|RDX|RSI|RDI|RBP|RSP|R[0-9]{1,2})\s*:\s*0x[0-9A-Fa-f]+").unwrap());
    patterns
});

/// Segment boundary definitions for different crash log formats
static SEGMENT_BOUNDARIES: Lazy<Vec<(&'static str, &'static str)>> = Lazy::new(|| {
    vec![
        ("[Compatibility]", "SYSTEM SPECS:"),
        ("SYSTEM SPECS:", "PROBABLE CALL STACK:"),
        ("PROBABLE CALL STACK:", "MODULES:"),
        ("MODULES:", "PLUGINS:"),
        ("PLUGINS:", "REGISTERS:"),
        ("REGISTERS:", "STACK:"),
        ("STACK:", "EOF"),
    ]
});

/// High-performance log parser with parallel processing and SIMD optimizations
#[pyclass]
pub struct LogParser {
    segment_boundaries: Vec<(String, String)>,
    compiled_patterns: Arc<Vec<Regex>>,
    /// Cache for parsed segments to avoid re-parsing
    segment_cache: Arc<DashMap<u64, Vec<Vec<String>>>>,
    /// Cache for pattern matches
    pattern_cache: Arc<DashMap<String, Vec<(usize, String, String)>>>,
    /// Custom patterns added at runtime
    custom_patterns: Arc<DashMap<String, Regex>>,
}

#[pymethods]
impl LogParser {
    #[new]
    #[pyo3(signature = (custom_boundaries=None))]
    pub fn new(custom_boundaries: Option<Vec<(String, String)>>) -> PyResult<Self> {
        let segment_boundaries = if let Some(boundaries) = custom_boundaries {
            boundaries
        } else {
            SEGMENT_BOUNDARIES
                .iter()
                .map(|(start, end)| (start.to_string(), end.to_string()))
                .collect()
        };

        // Initialize with common patterns
        let patterns: Vec<Regex> = COMMON_PATTERNS.values().cloned().collect();

        Ok(Self {
            segment_boundaries,
            compiled_patterns: Arc::new(patterns),
            segment_cache: Arc::new(DashMap::new()),
            pattern_cache: Arc::new(DashMap::new()),
            custom_patterns: Arc::new(DashMap::new()),
        })
    }

    /// Add a custom regex pattern for matching
    pub fn add_pattern(&self, name: String, pattern: String) -> PyResult<()> {
        let regex = Regex::new(&pattern)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid regex: {}", e)))?;
        self.custom_patterns.insert(name, regex);
        Ok(())
    }

    /// Clear all caches to free memory
    pub fn clear_caches(&self) {
        self.segment_cache.clear();
        self.pattern_cache.clear();
    }

    /// Parse log into segments using SIMD-optimized boundary detection
    pub fn parse_segments(&self, lines: Vec<String>) -> Vec<Vec<String>> {
        // Calculate a hash for cache lookup
        let cache_key = self.calculate_hash(&lines);

        // Check cache first
        if let Some(cached) = self.segment_cache.get(&cache_key) {
            return cached.clone();
        }

        let mut segments = Vec::new();
        let mut current_segment = Vec::new();
        let mut current_boundary_idx = 0;
        let mut collecting = false;

        // Use SIMD-optimized search for boundary detection
        for (_idx, line) in lines.iter().enumerate() {
            if current_boundary_idx >= self.segment_boundaries.len() {
                break;
            }

            let (start_boundary, end_boundary) = &self.segment_boundaries[current_boundary_idx];

            // Use SIMD-optimized string search when possible
            if self.fast_contains(line, if collecting { end_boundary } else { start_boundary }) {
                if collecting {
                    // End of current segment
                    if !current_segment.is_empty() {
                        segments.push(current_segment.clone());
                        current_segment.clear();
                    }
                    current_boundary_idx += 1;
                    collecting = false;
                } else {
                    // Start of new segment
                    collecting = true;
                }
            } else if collecting {
                current_segment.push(line.clone());
            }
        }

        // Add any remaining segment
        if !current_segment.is_empty() {
            segments.push(current_segment);
        }

        // Cache the result
        self.segment_cache.insert(cache_key, segments.clone());

        segments
    }

    /// Parse segments in parallel for large logs
    #[pyo3(name = "parse_segments_parallel", signature = (lines, chunk_size=None))]
    pub fn parse_segments_parallel(&self, lines: Vec<String>, chunk_size: Option<usize>) -> Vec<Vec<String>> {
        let chunk_size = chunk_size.unwrap_or(1000);

        if lines.len() < chunk_size {
            return self.parse_segments(lines);
        }

        // Split into chunks and process in parallel
        let chunks: Vec<_> = lines.chunks(chunk_size)
            .map(|chunk| chunk.to_vec())
            .collect();

        let results: Vec<Vec<Vec<String>>> = chunks
            .par_iter()
            .map(|chunk| self.parse_segments(chunk.clone()))
            .collect();

        // Merge results
        let mut merged_segments: Vec<Vec<String>> = Vec::new();
        for chunk_segments in results {
            for segment in chunk_segments {
                if !segment.is_empty() {
                    if let Some(last) = merged_segments.last_mut() {
                        // Check if we should merge with the previous segment
                        // (handles segments that span chunk boundaries)
                        if self.should_merge_segments(last, &segment) {
                            last.extend(segment.clone());
                        } else {
                            merged_segments.push(segment.clone());
                        }
                    } else {
                        merged_segments.push(segment.clone());
                    }
                }
            }
        }

        merged_segments
    }

    /// Find all pattern matches in parallel with caching
    pub fn find_patterns(&self, lines: Vec<String>) -> Vec<(usize, String, String)> {
        // Generate cache key from first few lines (for performance)
        let cache_key = lines.iter()
            .take(5)
            .map(|s| s.as_str())
            .collect::<Vec<_>>()
            .join("|");

        // Check cache
        if let Some(cached) = self.pattern_cache.get(&cache_key) {
            return cached.clone();
        }

        // Use the chunked version for processing
        self.find_patterns_chunked(lines, None)
    }

    /// Find patterns in parallel chunks for better performance
    #[pyo3(name = "find_patterns_chunked", signature = (lines, chunk_size=None))]
    pub fn find_patterns_chunked(&self, lines: Vec<String>, chunk_size: Option<usize>) -> Vec<(usize, String, String)> {
        // Generate cache key for caching
        let cache_key = lines.iter()
            .take(5)
            .map(|s| s.as_str())
            .collect::<Vec<_>>()
            .join("|");
        let patterns = self.compiled_patterns.clone();
        let custom_patterns = self.custom_patterns.clone();
        let chunk_size = chunk_size.unwrap_or(100);

        // Process lines in parallel chunks
        let chunks: Vec<_> = lines.chunks(chunk_size).map(|c| c.to_vec()).collect();
        let results: Vec<_> = chunks
            .par_iter()
            .enumerate()
            .flat_map(|(chunk_idx, chunk)| {
                chunk.iter()
                    .enumerate()
                    .flat_map(|(idx, line)| {
                        let line_num = chunk_idx * chunk_size + idx;
                        let mut matches = Vec::new();

                        // Check compiled patterns
                        for pattern in patterns.iter() {
                            if let Some(mat) = pattern.find(line) {
                                matches.push((line_num, pattern.as_str().to_string(), mat.as_str().to_string()));
                            }
                        }

                        // Check custom patterns
                        for entry in custom_patterns.iter() {
                            if let Some(mat) = entry.value().find(line) {
                                matches.push((line_num, entry.key().clone(), mat.as_str().to_string()));
                            }
                        }

                        matches
                    })
                    .collect::<Vec<_>>()
            })
            .collect();

        // Cache for small results
        if results.len() < 1000 {
            self.pattern_cache.insert(cache_key, results.clone());
        }

        results
    }

    /// Extract section from log (Python-exposed method)
    #[pyo3(name = "extract_section")]
    pub fn py_extract_section(&self, lines: Vec<String>, start_marker: String, end_marker: String) -> Option<Vec<String>> {
        self.extract_section(lines, start_marker, end_marker)
    }

    /// Extract multiple sections batch (Python-exposed method)
    #[pyo3(name = "extract_sections_batch")]
    pub fn py_extract_sections_batch(&self, lines: Vec<String>, markers: Vec<(String, String)>) -> Vec<Option<Vec<String>>> {
        self.extract_sections_batch(lines, markers)
    }

    /// Parse crash header (Python-exposed method)
    #[pyo3(name = "parse_crash_header")]
    pub fn py_parse_crash_header(&self, lines: Vec<String>) -> PyResult<HashMap<String, String>> {
        self.parse_crash_header(lines)
    }

    /// Get specific section by name (commonly used sections)
    #[pyo3(name = "get_section")]
    pub fn get_section(&self, lines: Vec<String>, section_name: String) -> Option<Vec<String>> {
        let (start, end) = match section_name.to_uppercase().as_str() {
            "COMPATIBILITY" => ("[Compatibility]", "SYSTEM SPECS:"),
            "SYSTEM" | "SPECS" => ("SYSTEM SPECS:", "PROBABLE CALL STACK:"),
            "CALLSTACK" | "STACK" => ("PROBABLE CALL STACK:", "MODULES:"),
            "MODULES" => ("MODULES:", "PLUGINS:"),
            "PLUGINS" => ("PLUGINS:", "REGISTERS:"),
            "REGISTERS" => ("REGISTERS:", "STACK:"),
            "MEMORY" | "STACK_DUMP" => ("STACK:", "EOF"),
            _ => return None,
        };
        self.extract_section(lines, start.to_string(), end.to_string())
    }

    /// Parse and extract all important sections at once
    #[pyo3(name = "parse_all_sections")]
    pub fn parse_all_sections(&self, lines: Vec<String>) -> HashMap<String, Vec<String>> {
        let sections = vec![
            ("compatibility", "[Compatibility]", "SYSTEM SPECS:"),
            ("system", "SYSTEM SPECS:", "PROBABLE CALL STACK:"),
            ("callstack", "PROBABLE CALL STACK:", "MODULES:"),
            ("modules", "MODULES:", "PLUGINS:"),
            ("plugins", "PLUGINS:", "REGISTERS:"),
            ("registers", "REGISTERS:", "STACK:"),
            ("stack_dump", "STACK:", "EOF"),
        ];

        sections.par_iter()
            .filter_map(|(name, start, end)| {
                self.extract_section(lines.clone(), start.to_string(), end.to_string())
                    .map(|section| (name.to_string(), section))
            })
            .collect()
    }

    /// Optimized batch operation: complete log analysis in single FFI call
    /// This reduces FFI overhead from 7+ calls to just 1 per log
    #[pyo3(name = "parse_complete")]
    pub fn parse_complete(
        &self,
        lines: Vec<String>,
        segment_boundaries: Vec<(String, String)>,
        _xse_acronym: String,
    ) -> PyResult<(String, String, String, Vec<Vec<String>>)> {
        // Parse header info in single pass (first 50 lines typically contain all metadata)
        let mut game_version = "UNKNOWN".to_string();
        let mut crashgen_version = "UNKNOWN".to_string();
        let mut main_error = "UNKNOWN".to_string();

        // Single pass for all header info
        for line in lines.iter().take(50) {
            // Game version detection
            if line.starts_with("Fallout 4 v") || line.starts_with("Skyrim Special Edition v")
                || line.starts_with("Skyrim SE v") || line.starts_with("Skyrim VR v") {
                game_version = line.trim().to_string();
            }

            // Crash generator detection
            if line.contains("Crash Log") || line.contains("Buffout")
                || line.contains("Crashgen") || line.contains("Trainwreck") {
                crashgen_version = line.trim().to_string();
            }

            // Main error detection
            if line.starts_with("Unhandled exception") || line.contains("EXCEPTION_") {
                main_error = line.replace('|', "\n").trim().to_string();
            }
        }

        // Extract all segments in parallel using provided boundaries
        let segments: Vec<Vec<String>> = segment_boundaries
            .par_iter()
            .map(|(start, end)| {
                self.extract_section(lines.clone(), start.clone(), end.clone())
                    .unwrap_or_default()
            })
            .collect();

        Ok((game_version, crashgen_version, main_error, segments))
    }

    /// Count lines in each segment for analysis
    #[pyo3(name = "get_segment_sizes")]
    pub fn get_segment_sizes(&self, lines: Vec<String>) -> HashMap<String, usize> {
        let segments = self.parse_all_sections(lines);
        segments.into_iter()
            .map(|(name, section)| (name, section.len()))
            .collect()
    }

    /// Get performance statistics
    pub fn get_stats(&self) -> HashMap<String, usize> {
        let mut stats = HashMap::new();
        stats.insert("segment_cache_size".to_string(), self.segment_cache.len());
        stats.insert("pattern_cache_size".to_string(), self.pattern_cache.len());
        stats.insert("custom_patterns".to_string(), self.custom_patterns.len());
        stats.insert("compiled_patterns".to_string(), self.compiled_patterns.len());
        stats
    }

    /// Find all FormIDs in the log using optimized pattern matching
    #[pyo3(name = "extract_formids")]
    pub fn extract_formids(&self, lines: Vec<String>) -> Vec<String> {
        let formid_pattern = &COMMON_PATTERNS["formid"];

        lines.par_iter()
            .flat_map(|line| {
                formid_pattern.captures_iter(line)
                    .map(|cap| cap[0].to_string())
                    .collect::<Vec<_>>()
            })
            .collect()
    }

    /// Find all plugins mentioned in the log
    #[pyo3(name = "extract_plugins")]
    pub fn extract_plugins(&self, lines: Vec<String>) -> Vec<(String, String)> {
        let plugin_pattern = &COMMON_PATTERNS["plugin"];

        lines.par_iter()
            .flat_map(|line| {
                plugin_pattern.captures_iter(line)
                    .filter_map(|cap| {
                        if cap.len() >= 3 {
                            Some((cap[1].to_string(), cap[2].to_string()))
                        } else {
                            None
                        }
                    })
                    .collect::<Vec<_>>()
            })
            .collect()
    }

    /// Find all memory addresses in the log
    #[pyo3(name = "extract_addresses")]
    pub fn extract_addresses(&self, lines: Vec<String>) -> Vec<String> {
        let address_pattern = &COMMON_PATTERNS["address"];

        lines.par_iter()
            .flat_map(|line| {
                address_pattern.find_iter(line)
                    .map(|mat| mat.as_str().to_string())
                    .collect::<Vec<_>>()
            })
            .collect()
    }

    /// Find error and exception patterns
    #[pyo3(name = "find_errors")]
    pub fn find_errors(&self, lines: Vec<String>) -> Vec<(usize, String)> {
        let error_pattern = &COMMON_PATTERNS["error"];

        lines.par_iter()
            .enumerate()
            .filter_map(|(idx, line)| {
                if error_pattern.is_match(line) {
                    Some((idx, line.clone()))
                } else {
                    None
                }
            })
            .collect()
    }

    /// Benchmark parsing performance on given data
    #[pyo3(name = "benchmark")]
    pub fn benchmark(&self, lines: Vec<String>, iterations: usize) -> HashMap<String, f64> {
        use std::time::Instant;
        let mut results = HashMap::new();

        // Benchmark segment parsing
        let start = Instant::now();
        for _ in 0..iterations {
            let _ = self.parse_segments(lines.clone());
        }
        let elapsed = start.elapsed().as_secs_f64() / iterations as f64;
        results.insert("parse_segments_avg_ms".to_string(), elapsed * 1000.0);

        // Benchmark pattern finding
        let start = Instant::now();
        for _ in 0..iterations {
            let _ = self.find_patterns(lines.clone());
        }
        let elapsed = start.elapsed().as_secs_f64() / iterations as f64;
        results.insert("find_patterns_avg_ms".to_string(), elapsed * 1000.0);

        // Calculate throughput
        let lines_per_sec = lines.len() as f64 / elapsed;
        results.insert("lines_per_second".to_string(), lines_per_sec);

        results
    }
}

// Private implementation methods
impl LogParser {
    /// SIMD-optimized string contains check
    fn fast_contains(&self, haystack: &str, needle: &str) -> bool {
        // Use memchr for single-byte patterns
        if needle.len() == 1 {
            if let Some(byte) = needle.bytes().next() {
                return memchr(byte, haystack.as_bytes()).is_some();
            }
        }

        // Use memmem for multi-byte patterns
        if needle.len() < 32 {
            let finder = memmem::Finder::new(needle);
            return finder.find(haystack.as_bytes()).is_some();
        }

        // Fall back to standard contains for larger patterns
        haystack.contains(needle)
    }

    /// Calculate hash for cache key
    fn calculate_hash(&self, lines: &[String]) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        // Hash first and last few lines for uniqueness
        for line in lines.iter().take(5).chain(lines.iter().rev().take(5)) {
            line.hash(&mut hasher);
        }
        hasher.finish()
    }

    /// Check if two segments should be merged (for parallel processing)
    fn should_merge_segments(&self, last: &[String], current: &[String]) -> bool {
        // Segments should be merged if the last line of 'last' and first line of 'current'
        // don't contain any boundary markers
        if last.is_empty() || current.is_empty() {
            return false;
        }

        let last_line = &last[last.len() - 1];
        let first_line = &current[0];

        // Check if either line contains a boundary marker
        for (start, end) in &self.segment_boundaries {
            if last_line.contains(start) || last_line.contains(end) ||
               first_line.contains(start) || first_line.contains(end) {
                return false;
            }
        }

        true
    }

    /// Extract specific section from log with SIMD-optimized search
    fn extract_section(&self, lines: Vec<String>, start_marker: String, end_marker: String) -> Option<Vec<String>> {
        // Find start position using SIMD search
        let start_pos = lines.par_iter()
            .position_any(|line| self.fast_contains(line, &start_marker))
            .map(|pos| pos + 1)?;  // Skip the marker line

        // Find end position
        let end_pos = lines[start_pos..].par_iter()
            .position_any(|line| self.fast_contains(line, &end_marker))
            .map(|pos| start_pos + pos)
            .unwrap_or(lines.len());

        if start_pos >= end_pos {
            None
        } else {
            Some(lines[start_pos..end_pos].to_vec())
        }
    }

    /// Extract multiple sections in parallel
    fn extract_sections_batch(&self, lines: Vec<String>, markers: Vec<(String, String)>) -> Vec<Option<Vec<String>>> {
        markers.par_iter()
            .map(|(start, end)| self.extract_section(lines.clone(), start.clone(), end.clone()))
            .collect()
    }

    /// Parse and analyze crash header information (internal)
    fn parse_crash_header(&self, lines: Vec<String>) -> PyResult<HashMap<String, String>> {
        let mut header_info = HashMap::new();

        // Use parallel search for common header patterns
        let results: Vec<_> = lines.par_iter()
            .take(50)  // Headers are usually in the first 50 lines
            .filter_map(|line| {
                // Game version
                if line.starts_with("Fallout 4 v") || line.starts_with("Skyrim SE v") {
                    return Some(("game_version".to_string(), line.trim().to_string()));
                }

                // Crash generator version
                if line.contains("Crash Logger") || line.contains("Buffout") {
                    return Some(("crashgen_version".to_string(), line.trim().to_string()));
                }

                // Main error
                if line.starts_with("Unhandled exception") {
                    let replaced = line.replacen("|", "\n", 1);
                    return Some(("main_error".to_string(), replaced));
                }

                // System info patterns
                if let Some(caps) = COMMON_PATTERNS["address"].captures(line) {
                    if line.contains("at address") {
                        return Some(("crash_address".to_string(), caps[0].to_string()));
                    }
                }

                None
            })
            .collect();

        for (key, value) in results {
            header_info.insert(key, value);
        }

        Ok(header_info)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_sample_log() -> Vec<String> {
        vec![
            "Unhandled exception at 0x7FF123456789| ACCESS_VIOLATION".to_string(),
            "Fallout 4 v1.10.163".to_string(),
            "Buffout 4 v1.28.6".to_string(),
            "[Compatibility]".to_string(),
            "F4EE: true".to_string(),
            "SYSTEM SPECS:".to_string(),
            "CPU: AMD Ryzen 9 5900X".to_string(),
            "GPU: NVIDIA GeForce RTX 3080".to_string(),
            "PROBABLE CALL STACK:".to_string(),
            "[0] 0x7FF123456789 Fallout4.exe+0123456".to_string(),
            "MODULES:".to_string(),
            "Fallout4.exe v1.10.163".to_string(),
            "PLUGINS:".to_string(),
            "[00] Fallout4.esm".to_string(),
            "REGISTERS:".to_string(),
            "RAX: 0x0000000000000000".to_string(),
            "STACK:".to_string(),
            "0x000000000000: 0x12345678".to_string(),
            "EOF".to_string(),
        ]
    }

    #[test]
    fn test_parser_creation() {
        let parser = LogParser::new(None).unwrap();
        assert!(parser.get_stats().get("compiled_patterns").unwrap() > &0);
    }

    #[test]
    fn test_segment_parsing() {
        let parser = LogParser::new(None).unwrap();
        let log_lines = create_sample_log();
        let segments = parser.parse_segments(log_lines);
        assert!(segments.len() > 0);
    }

    #[test]
    fn test_pattern_matching() {
        let parser = LogParser::new(None).unwrap();
        let log_lines = create_sample_log();
        let matches = parser.find_patterns(log_lines);
        // Should find at least the error/exception patterns
        assert!(matches.len() > 0);
    }

    #[test]
    fn test_section_extraction() {
        let parser = LogParser::new(None).unwrap();
        let log_lines = create_sample_log();
        let section = parser.extract_section(
            log_lines,
            "SYSTEM SPECS:".to_string(),
            "PROBABLE CALL STACK:".to_string()
        );
        assert!(section.is_some());
        let section = section.unwrap();
        assert!(section.iter().any(|line| line.contains("CPU")));
    }

    #[test]
    fn test_crash_header_parsing() {
        let parser = LogParser::new(None).unwrap();
        let log_lines = create_sample_log();
        let header = parser.parse_crash_header(log_lines).unwrap();
        assert!(header.contains_key("game_version"));
        assert!(header.contains_key("crashgen_version"));
        assert!(header.contains_key("main_error"));
    }

    #[test]
    fn test_extract_formids() {
        let parser = LogParser::new(None).unwrap();
        let lines = vec![
            "FormID: 0x12345678 in plugin".to_string(),
            "Another formid 0xABCDEF00 found".to_string(),
            "No formid here".to_string(),
        ];
        let formids = parser.extract_formids(lines);
        assert_eq!(formids.len(), 2);
    }

    #[test]
    fn test_get_section() {
        let parser = LogParser::new(None).unwrap();
        let log_lines = create_sample_log();
        let plugins_section = parser.get_section(log_lines.clone(), "PLUGINS".to_string());
        assert!(plugins_section.is_some());
        let plugins = plugins_section.unwrap();
        assert!(plugins.iter().any(|line| line.contains("Fallout4.esm")));
    }

    #[test]
    fn test_parse_all_sections() {
        let parser = LogParser::new(None).unwrap();
        let log_lines = create_sample_log();
        let sections = parser.parse_all_sections(log_lines);
        assert!(sections.contains_key("system"));
        assert!(sections.contains_key("plugins"));
        assert!(sections.contains_key("modules"));
    }

    #[test]
    fn test_parallel_processing() {
        let parser = LogParser::new(None).unwrap();
        let mut large_log = Vec::new();
        for i in 0..10000 {
            large_log.push(format!("Log line {}", i));
        }
        large_log.push("MODULES:".to_string());
        for i in 0..1000 {
            large_log.push(format!("Module line {}", i));
        }

        let segments = parser.parse_segments_parallel(large_log, Some(500));
        assert!(segments.len() > 0);
    }
}
