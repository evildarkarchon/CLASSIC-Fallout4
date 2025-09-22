//! High-performance log parsing with segment detection

use pyo3::prelude::*;
use rayon::prelude::*;
use regex::Regex;
use std::sync::Arc;

/// Log parser with parallel processing capabilities
#[pyclass]
pub struct LogParser {
    segment_boundaries: Vec<(String, String)>,
    compiled_patterns: Arc<Vec<Regex>>,
}

#[pymethods]
impl LogParser {
    #[new]
    pub fn new() -> PyResult<Self> {
        let segment_boundaries = vec![
            ("SYSTEM SPECS:".to_string(), "PROBABLE CALL STACK:".to_string()),
            ("PROBABLE CALL STACK:".to_string(), "REGISTERS:".to_string()),
            ("REGISTERS:".to_string(), "STACK:".to_string()),
        ];

        let patterns = vec![
            Regex::new(r"(?i)error").unwrap(),
            Regex::new(r"(?i)exception").unwrap(),
            Regex::new(r"(?i)crash").unwrap(),
        ];

        Ok(Self {
            segment_boundaries,
            compiled_patterns: Arc::new(patterns),
        })
    }

    /// Parse log into segments using parallel processing
    pub fn parse_segments(&self, lines: Vec<String>) -> Vec<Vec<String>> {
        let mut segments = Vec::new();
        let mut current_segment = Vec::new();
        let mut in_segment = false;

        for line in lines {
            // Check for segment boundaries
            for (start, end) in &self.segment_boundaries {
                if line.contains(start) {
                    if !current_segment.is_empty() {
                        segments.push(current_segment.clone());
                        current_segment.clear();
                    }
                    in_segment = true;
                } else if line.contains(end) {
                    segments.push(current_segment.clone());
                    current_segment.clear();
                    in_segment = false;
                }
            }

            if in_segment {
                current_segment.push(line);
            }
        }

        // Add any remaining segment
        if !current_segment.is_empty() {
            segments.push(current_segment);
        }

        segments
    }

    /// Find all pattern matches in parallel
    pub fn find_patterns(&self, lines: Vec<String>) -> Vec<(usize, String, String)> {
        let patterns = self.compiled_patterns.clone();

        lines.par_iter()
            .enumerate()
            .flat_map(|(line_num, line)| {
                patterns.iter()
                    .filter_map(move |pattern| {
                        if pattern.is_match(line) {
                            Some((line_num, pattern.as_str().to_string(), line.clone()))
                        } else {
                            None
                        }
                    })
            })
            .collect()
    }

    /// Extract specific section from log
    pub fn extract_section(&self, lines: Vec<String>, start_marker: String, end_marker: String) -> Option<Vec<String>> {
        let mut section = Vec::new();
        let mut in_section = false;

        for line in lines {
            if line.contains(&start_marker) {
                in_section = true;
                continue;
            }
            if line.contains(&end_marker) {
                break;
            }
            if in_section {
                section.push(line);
            }
        }

        if section.is_empty() {
            None
        } else {
            Some(section)
        }
    }
}
