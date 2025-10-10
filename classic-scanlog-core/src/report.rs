//! High-performance report generation with string interning and parallel processing
//!
//! This module implements Phase 5 of the Rust migration plan, providing:
//! - Immutable report fragments for functional composition
//! - String interning/pooling for memory efficiency
//! - Parallel fragment processing for speed
//! - Efficient string building strategies

// Error types not needed in pure Rust - using standard Result
use dashmap::DashMap;
use once_cell::sync::Lazy;
use parking_lot::RwLock;
use rayon::prelude::*;
use std::sync::Arc;
use string_cache::DefaultAtom;

/// Global string pool for interning frequently used strings
static STRING_POOL: Lazy<StringPool> = Lazy::new(|| StringPool::new());

/// String pool for efficient memory usage through string interning
#[derive(Clone, Debug)]
pub struct StringPool {
    pool: Arc<DashMap<String, DefaultAtom>>,
    stats: Arc<RwLock<PoolStats>>,
}

#[derive(Default, Debug)]
struct PoolStats {
    lookups: usize,
    hits: usize,
    insertions: usize,
}

impl StringPool {
    /// Create a new string pool
    pub fn new() -> Self {
        Self {
            pool: Arc::new(DashMap::new()),
            stats: Arc::new(RwLock::new(PoolStats::default())),
        }
    }

    /// Intern a string, returning a reference to the pooled version
    pub fn intern(&self, s: &str) -> String {
        let mut stats = self.stats.write();
        stats.lookups += 1;

        if let Some(interned) = self.pool.get(s) {
            stats.hits += 1;
            return interned.as_ref().to_string();
        }

        let atom = DefaultAtom::from(s);
        self.pool.insert(s.to_string(), atom.clone());
        stats.insertions += 1;
        atom.as_ref().to_string()
    }

    /// Intern multiple strings in parallel
    pub fn intern_batch(&self, strings: &[String]) -> Vec<String> {
        strings.par_iter().map(|s| self.intern(s)).collect()
    }

    /// Get pool statistics
    pub fn get_stats(&self) -> (usize, usize, usize, usize) {
        let stats = self.stats.read();
        (self.pool.len(), stats.lookups, stats.hits, stats.insertions)
    }

    /// Clear the pool
    pub fn clear(&self) {
        self.pool.clear();
        *self.stats.write() = PoolStats::default();
    }
}

/// Immutable report fragment for functional composition
#[derive(Clone, Debug)]
pub struct ReportFragment {
    /// Immutable content lines
    content: Arc<Vec<String>>,
    /// Whether this fragment contains meaningful content
    has_content: bool,
    /// Optional string pool reference for memory efficiency
    pool: Option<StringPool>,
}

impl ReportFragment {
    /// Create an empty fragment
    pub fn empty() -> Self {
        Self {
            content: Arc::new(Vec::new()),
            has_content: false,
            pool: None,
        }
    }

    /// Create a fragment from lines
    pub fn from_lines(lines: Vec<String>) -> Self {
        let has_content = !lines.is_empty();
        Self {
            content: Arc::new(lines),
            has_content,
            pool: None,
        }
    }

    /// Create a fragment with string pooling
    pub fn from_lines_pooled(lines: Vec<String>, pool: &StringPool) -> Self {
        let pooled_lines = lines.into_iter().map(|line| pool.intern(&line)).collect();

        Self {
            content: Arc::new(pooled_lines),
            has_content: true,
            pool: Some(pool.clone()),
        }
    }

    /// Add a header to this fragment
    pub fn with_header(&self, header_lines: Vec<String>) -> Self {
        if !self.has_content {
            return self.clone();
        }

        let mut new_content = header_lines;
        new_content.extend(self.content.iter().cloned());

        Self {
            content: Arc::new(new_content),
            has_content: true,
            pool: self.pool.clone(),
        }
    }

    /// Combine two fragments
    pub fn combine(&self, other: &ReportFragment) -> Self {
        if !self.has_content && !other.has_content {
            return Self::empty();
        }

        let mut combined = Vec::with_capacity(self.content.len() + other.content.len());
        combined.extend(self.content.iter().cloned());
        combined.extend(other.content.iter().cloned());

        Self {
            content: Arc::new(combined),
            has_content: self.has_content || other.has_content,
            pool: self.pool.clone().or(other.pool.clone()),
        }
    }

    /// Convert to a list of strings
    pub fn to_list(&self) -> Vec<String> {
        self.content.to_vec()
    }

    /// Get the number of lines
    pub fn len(&self) -> usize {
        self.content.len()
    }

    /// Check if empty
    pub fn is_empty(&self) -> bool {
        self.content.is_empty()
    }
}

/// High-performance report composer with parallel fragment processing
pub struct ReportComposer {
    fragments: Vec<ReportFragment>,
    pool: StringPool,
    parallel_threshold: usize,
}

impl ReportComposer {
    /// Create a new composer
    pub fn new() -> Self {
        Self {
            fragments: Vec::new(),
            pool: STRING_POOL.clone(),
            parallel_threshold: 10, // Use parallel processing for 10+ fragments
        }
    }

    /// Add a fragment to the composer
    pub fn add(&mut self, fragment: ReportFragment) {
        self.fragments.push(fragment);
    }

    /// Add multiple fragments
    pub fn add_many(&mut self, fragments: Vec<ReportFragment>) {
        self.fragments.extend(fragments);
    }

    /// Compose all fragments into a single fragment
    pub fn compose(&self) -> ReportFragment {
        if self.fragments.is_empty() {
            return ReportFragment::empty();
        }

        if self.fragments.len() == 1 {
            return self.fragments[0].clone();
        }

        // Use parallel composition for many fragments
        if self.fragments.len() >= self.parallel_threshold {
            self.compose_parallel()
        } else {
            self.compose_sequential()
        }
    }

    /// Sequential composition for small numbers of fragments
    fn compose_sequential(&self) -> ReportFragment {
        let mut result = self.fragments[0].clone();
        for fragment in &self.fragments[1..] {
            result = result.combine(fragment);
        }
        result
    }

    /// Parallel composition for large numbers of fragments
    fn compose_parallel(&self) -> ReportFragment {
        // Use divide-and-conquer parallel reduction
        self.fragments
            .par_iter()
            .cloned()
            .reduce(|| ReportFragment::empty(), |a, b| a.combine(&b))
    }

    /// Compose fragments and optimize memory usage
    pub fn compose_optimized(&self) -> ReportFragment {
        let fragment = self.compose();

        // If using string pool, intern all strings
        if self.pool.pool.len() > 0 {
            let optimized_content = fragment
                .content
                .par_iter()
                .map(|s| self.pool.intern(s))
                .collect();

            ReportFragment {
                content: Arc::new(optimized_content),
                has_content: fragment.has_content,
                pool: Some(self.pool.clone()),
            }
        } else {
            fragment
        }
    }

    /// Build the final report as a single string
    pub fn build_string(&self) -> String {
        let fragment = self.compose_optimized();

        // Use efficient string building
        let total_size: usize = fragment
            .content
            .iter()
            .map(|s| s.len() + 1) // +1 for newline
            .sum();

        let mut result = String::with_capacity(total_size);
        for line in fragment.content.iter() {
            result.push_str(line);
            if !line.ends_with('\n') {
                result.push('\n');
            }
        }

        result
    }

    /// Get the number of fragments
    pub fn fragment_count(&self) -> usize {
        self.fragments.len()
    }

    /// Process fragments in parallel with a transformation function
    pub fn process_fragments_parallel<F>(&mut self, transform: F)
    where
        F: Fn(&ReportFragment) -> ReportFragment + Sync + Send,
    {
        self.fragments = self.fragments.par_iter().map(transform).collect();
    }
}

/// Generator for report fragments with efficient string building
pub struct ReportGenerator {
    pool: StringPool,
}

impl ReportGenerator {
    pub fn new() -> Self {
        Self {
            pool: STRING_POOL.clone(),
        }
    }

    /// Generate a header fragment
    pub fn generate_header(&self, filename: &str, version: &str) -> ReportFragment {
        let lines = vec![
            format!("# {}\n", filename),
            format!("**AUTOSCAN REPORT GENERATED BY {}**\n\n", version),
            "> **FOR BEST VIEWING EXPERIENCE OPEN THIS FILE IN NOTEPAD++ OR SIMILAR**\n\n"
                .to_string(),
            "> **PLEASE READ EVERYTHING CAREFULLY AND BEWARE OF FALSE POSITIVES**\n\n".to_string(),
            "---\n\n".to_string(),
        ];

        ReportFragment::from_lines_pooled(lines, &self.pool)
    }

    /// Generate an error section
    pub fn generate_error_section(
        &self,
        main_error: &str,
        crashgen_version: &str,
        crashgen_name: &str,
        is_latest: bool,
        warn_outdated: &str,
    ) -> ReportFragment {
        let mut lines = vec![
            "### Error Information\n\n".to_string(),
            format!("**Main Error:** {}\n\n", main_error),
            format!(
                "**Detected {} Version:** {}\n\n",
                crashgen_name, crashgen_version
            ),
        ];

        if is_latest {
            lines.push(format!(
                "✅ *You have the latest version of {}!*\n\n",
                crashgen_name
            ));
        } else {
            lines.push(format!("⚠️ {}\n\n", warn_outdated));
        }

        ReportFragment::from_lines_pooled(lines, &self.pool)
    }

    /// Generate a suspect section
    pub fn generate_suspect_section(&self, found_suspects: Vec<String>) -> ReportFragment {
        if found_suspects.is_empty() {
            let lines = vec![
                "### Checking If Log Matches Any Known Crash Suspects\n\n".to_string(),
                "# FOUND NO CRASH ERRORS / SUSPECTS THAT MATCH THE CURRENT DATABASE #\n"
                    .to_string(),
                "Check below for mods that can cause frequent crashes and other problems.\n\n"
                    .to_string(),
            ];
            ReportFragment::from_lines_pooled(lines, &self.pool)
        } else {
            let mut lines =
                vec!["### Checking If Log Matches Any Known Crash Suspects\n\n".to_string()];
            lines.extend(found_suspects);
            lines.push("* FOR DETAILED DESCRIPTIONS AND POSSIBLE SOLUTIONS TO ANY ABOVE DETECTED CRASH SUSPECTS *\n".to_string());
            lines.push("* SEE: https://docs.google.com/document/d/17FzeIMJ256xE85XdjoPvv_Zi3C5uHeSTQh6wOZugs4c *\n\n".to_string());

            ReportFragment::from_lines_pooled(lines, &self.pool)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_string_pool() {
        let pool = StringPool::new();

        let s1 = pool.intern("hello");
        let s2 = pool.intern("hello");
        assert_eq!(s1, s2);

        let (size, lookups, hits, insertions) = pool.get_stats();
        assert_eq!(size, 1);
        assert_eq!(lookups, 2);
        assert_eq!(hits, 1);
        assert_eq!(insertions, 1);
    }

    #[test]
    fn test_report_fragment() {
        let fragment1 = ReportFragment::from_lines(vec!["line1".to_string(), "line2".to_string()]);
        let fragment2 = ReportFragment::from_lines(vec!["line3".to_string()]);

        let combined = fragment1.combine(&fragment2);
        assert_eq!(combined.len(), 3);
        assert_eq!(combined.to_list(), vec!["line1", "line2", "line3"]);
    }

    #[test]
    fn test_report_composer() {
        let mut composer = ReportComposer::new();

        for i in 0..20 {
            let fragment = ReportFragment::from_lines(vec![format!("Line {}", i)]);
            composer.add(fragment);
        }

        let result = composer.compose();
        assert_eq!(result.len(), 20);

        let text = composer.build_string();
        assert!(text.contains("Line 0"));
        assert!(text.contains("Line 19"));
    }
}
