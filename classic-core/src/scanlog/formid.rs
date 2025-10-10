//! FormID analysis - Ultra-fast FormID parsing and validation

use dashmap::DashMap;
use once_cell::sync::Lazy;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use regex::Regex;
use std::collections::HashMap;
// use anyhow::Result; // Currently unused

/// Precompiled FormID regex pattern
static FORMID_PATTERN: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"(?i)(?:0x)?([0-9a-f]{1,8})").unwrap());

/// High-performance FormID analyzer with caching
#[pyclass]
pub struct FormIDAnalyzer {
    pattern_cache: DashMap<String, Regex>,
    formid_cache: DashMap<(String, String), Option<String>>,
}

#[pymethods]
impl FormIDAnalyzer {
    #[new]
    pub fn new() -> Self {
        Self {
            pattern_cache: DashMap::new(),
            formid_cache: DashMap::new(),
        }
    }

    /// Parse and validate a FormID string
    pub fn parse_formid(&self, formid: &str) -> Option<u32> {
        let captures = FORMID_PATTERN.captures(formid)?;
        let hex_str = captures.get(1)?;
        u32::from_str_radix(hex_str.as_str(), 16).ok()
    }

    /// Batch analyze FormIDs with plugin resolution
    #[pyo3(signature = (formids, plugins))]
    pub fn analyze_batch(
        &self,
        formids: Vec<String>,
        plugins: Bound<'_, PyDict>,
    ) -> PyResult<Vec<(String, Option<String>)>> {
        let mut results = Vec::with_capacity(formids.len());

        // Convert PyDict to HashMap for faster lookups
        let plugin_map: HashMap<String, String> = plugins
            .iter()
            .map(|(k, v)| {
                let key = k.extract::<String>()?;
                let value = v.extract::<String>()?;
                Ok((key, value))
            })
            .collect::<PyResult<HashMap<_, _>>>()?;

        for formid in formids {
            if let Some(parsed) = self.parse_formid(&formid) {
                // Extract plugin index (upper 2 bytes)
                let plugin_index = (parsed >> 24) as usize;
                let plugin_name = plugin_map.get(&plugin_index.to_string()).cloned();
                results.push((formid, plugin_name));
            } else {
                results.push((formid, None));
            }
        }

        Ok(results)
    }

    /// Clear all caches
    pub fn clear_cache(&self) {
        self.pattern_cache.clear();
        self.formid_cache.clear();
    }

    /// Get cache statistics
    pub fn cache_stats(&self) -> (usize, usize) {
        (self.pattern_cache.len(), self.formid_cache.len())
    }
}
