//! Pattern matching engine with multi-pattern optimization

use aho_corasick::{AhoCorasick, Match};
use dashmap::DashMap;
use std::sync::Arc;
use crate::error::{Result, ScanLogError};

/// Multi-pattern matcher using Aho-Corasick algorithm
pub struct PatternMatcher {
    patterns: Arc<Vec<String>>,
    matcher: Arc<AhoCorasick>,
    match_cache: DashMap<String, Vec<(usize, String)>>,
}

impl PatternMatcher {
    pub fn new(patterns: Vec<String>) -> Result<Self> {
        let matcher = AhoCorasick::builder()
            .ascii_case_insensitive(true)
            .build(&patterns)
            .map_err(|e| ScanLogError::PatternError(e.to_string()))?;

        Ok(Self {
            patterns: Arc::new(patterns),
            matcher: Arc::new(matcher),
            match_cache: DashMap::new(),
        })
    }

    /// Find all pattern matches in text
    pub fn find_all(&self, text: &str) -> Vec<(usize, String)> {
        // Check cache first
        if let Some(cached) = self.match_cache.get(text) {
            return cached.clone();
        }

        let matches: Vec<(usize, String)> = self.matcher
            .find_iter(text)
            .map(|m: Match| {
                let pattern_idx = m.pattern().as_usize();
                (m.start(), self.patterns[pattern_idx].clone())
            })
            .collect();

        // Cache the result
        self.match_cache.insert(text.to_string(), matches.clone());

        matches
    }

    /// Check if any pattern matches
    pub fn has_match(&self, text: &str) -> bool {
        self.matcher.is_match(text)
    }

    /// Find first match
    pub fn find_first(&self, text: &str) -> Option<(usize, String)> {
        self.matcher.find(text).map(|m| {
            let pattern_idx = m.pattern().as_usize();
            (m.start(), self.patterns[pattern_idx].clone())
        })
    }

    /// Replace all matches with a replacement string
    pub fn replace_all(&self, text: &str, replacement: &str) -> String {
        // Create a vec with the same replacement for each pattern
        let replacements: Vec<&str> = vec![replacement; self.patterns.len()];
        self.matcher.replace_all(text, &replacements)
    }

    /// Get pattern statistics
    pub fn get_stats(&self) -> (usize, usize) {
        (self.patterns.len(), self.match_cache.len())
    }

    /// Clear the match cache
    pub fn clear_cache(&self) {
        self.match_cache.clear();
    }
}
