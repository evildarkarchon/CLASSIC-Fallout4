//! Pattern matching engine with multi-pattern optimization

use crate::error::Result;
use aho_corasick::{AhoCorasick, Match};
use dashmap::DashMap;
use std::sync::Arc;

/// Multi-pattern matcher using Aho-Corasick algorithm
pub struct PatternMatcher {
    patterns: Arc<Vec<String>>,
    matcher: Arc<AhoCorasick>,
    match_cache: DashMap<String, Vec<(usize, String)>>,
}

impl PatternMatcher {
    /// Creates a new pattern matcher with the specified patterns.
    ///
    /// This constructor initializes a `PatternMatcher` using the Aho-Corasick algorithm
    /// for efficient multi-pattern matching. The matcher is configured for case-insensitive
    /// ASCII matching and includes an internal cache for repeated matches.
    ///
    /// # Arguments
    ///
    /// * `patterns` - A vector of patterns to match against text. Patterns can include
    ///   error messages, stack trace signatures, module names, or other identifiable
    ///   strings from crash logs.
    ///
    /// # Returns
    ///
    /// A new `PatternMatcher` instance configured with the provided patterns, or an error
    /// if pattern compilation fails.
    ///
    /// # Errors
    ///
    /// Returns `ScanLogError::PatternError` if the Aho-Corasick automaton cannot be built
    /// from the provided patterns (e.g., if patterns are malformed or exceed internal limits).
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::patterns::PatternMatcher;
    ///
    /// let patterns = vec![
    ///     "ACCESS_VIOLATION".to_string(),
    ///     "EXCEPTION_STACK_OVERFLOW".to_string(),
    ///     "EXCEPTION_BREAKPOINT".to_string(),
    /// ];
    ///
    /// let matcher = PatternMatcher::new(patterns)?;
    /// assert!(matcher.has_match("Unhandled exception: ACCESS_VIOLATION at 0x7FF123456"));
    /// # Ok::<(), classic_scanlog_core::error::ScanLogError>(())
    /// ```
    pub fn new(patterns: Vec<String>) -> Result<Self> {
        let matcher = AhoCorasick::builder()
            .ascii_case_insensitive(true)
            .build(&patterns)?;

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

        let matches: Vec<(usize, String)> = self
            .matcher
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
