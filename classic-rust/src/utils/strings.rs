//! High-performance string processing utilities

use pyo3::prelude::*;
use smartstring::alias::String as SmartString;
use string_cache::DefaultAtom;
use dashmap::DashMap;
use rayon::prelude::*;
use std::sync::Arc;

/// String processor with interning and parallel operations
#[pyclass]
pub struct StringProcessor {
    string_pool: Arc<DashMap<String, DefaultAtom>>,
}

#[pymethods]
impl StringProcessor {
    #[new]
    pub fn new() -> Self {
        Self {
            string_pool: Arc::new(DashMap::new()),
        }
    }

    /// Intern a string for memory efficiency
    pub fn intern(&self, s: String) -> String {
        if let Some(interned) = self.string_pool.get(&s) {
            return interned.as_ref().to_string();
        }

        let atom = DefaultAtom::from(s.clone());
        self.string_pool.insert(s.clone(), atom);
        s
    }

    /// Process multiple strings in parallel
    pub fn process_batch(&self, strings: Vec<String>, operation: String) -> Vec<String> {
        strings.par_iter()
            .map(|s| match operation.as_str() {
                "upper" => s.to_uppercase(),
                "lower" => s.to_lowercase(),
                "trim" => s.trim().to_string(),
                "normalize" => self.normalize_string(s),
                _ => s.clone(),
            })
            .collect()
    }

    /// Normalize a string (trim, lowercase, remove extra whitespace)
    fn normalize_string(&self, s: &str) -> String {
        let mut result = SmartString::new();
        let mut prev_was_space = false;

        for ch in s.trim().chars() {
            if ch.is_whitespace() {
                if !prev_was_space {
                    result.push(' ');
                    prev_was_space = true;
                }
            } else {
                result.push(ch.to_ascii_lowercase());
                prev_was_space = false;
            }
        }

        result.to_string()
    }

    /// Find common prefix of multiple strings
    pub fn common_prefix(&self, strings: Vec<String>) -> String {
        if strings.is_empty() {
            return String::new();
        }

        let min_len = strings.iter().map(|s| s.len()).min().unwrap_or(0);
        let first = &strings[0];

        for i in 0..min_len {
            let ch = first.chars().nth(i).unwrap();
            if !strings.iter().all(|s| s.chars().nth(i) == Some(ch)) {
                return first[..i].to_string();
            }
        }

        first[..min_len].to_string()
    }

    /// Split text into lines efficiently
    pub fn split_lines(&self, text: String) -> Vec<String> {
        text.par_lines()
            .map(|line| line.to_string())
            .collect()
    }

    /// Join lines with a separator
    pub fn join_lines(&self, lines: Vec<String>, separator: String) -> String {
        lines.join(&separator)
    }

    /// Get string pool statistics
    pub fn pool_stats(&self) -> usize {
        self.string_pool.len()
    }

    /// Clear the string pool
    pub fn clear_pool(&self) {
        self.string_pool.clear();
    }
}
