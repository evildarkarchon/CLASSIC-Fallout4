//! High-performance report generation with string interning and parallel processing
//!
//! This module implements Phase 5 of the Rust migration plan, providing:
//! - Immutable report fragments for functional composition
//! - String interning/pooling for memory efficiency
//! - Parallel fragment processing for speed
//! - Efficient string building strategies

// Error types not needed in pure Rust - using standard Result
use crate::version::CrashgenVersionStatus;
use dashmap::DashMap;
use parking_lot::RwLock;
use rayon::prelude::*;
use std::sync::{Arc, LazyLock};
use string_cache::DefaultAtom;

/// Global string pool for interning frequently used strings
static STRING_POOL: LazyLock<StringPool> = LazyLock::new(StringPool::new);

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

impl Default for StringPool {
    fn default() -> Self {
        Self::new()
    }
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

impl Default for ReportComposer {
    fn default() -> Self {
        Self::new()
    }
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
            .reduce(ReportFragment::empty, |a, b| a.combine(&b))
    }

    /// Compose fragments and optimize memory usage
    pub fn compose_optimized(&self) -> ReportFragment {
        let fragment = self.compose();

        // If using string pool, intern all strings
        if !self.pool.pool.is_empty() {
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

    /// Get string pool statistics (size, lookups, hits, insertions).
    ///
    /// Returns a tuple containing:
    /// - Pool size (number of unique interned strings)
    /// - Lookup count (total number of intern attempts)
    /// - Hit count (cache hits from pool)
    /// - Insertion count (new strings added to pool)
    ///
    /// # Returns
    ///
    /// A tuple `(pool_size, lookups, hits, insertions)` representing
    /// the current state of the string interning pool.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::report::ReportComposer;
    ///
    /// let composer = ReportComposer::new();
    /// let (size, lookups, hits, insertions) = composer.get_pool_stats();
    /// println!("Pool has {} strings", size);
    /// ```
    pub fn get_pool_stats(&self) -> (usize, usize, usize, usize) {
        self.pool.get_stats()
    }
}

/// Generator for report fragments with efficient string building.
///
/// This generator produces report fragments that are **identical** to Python's
/// `ReportGeneratorFragments` output. This is a critical requirement - users
/// should not be able to distinguish between Rust and Python generated reports.
pub struct ReportGenerator {
    pool: StringPool,
    /// Bare SemVer version string for the CLASSIC application (e.g., "v8.0.0").
    /// The `CLASSIC ` product-name prefix is applied by the report generator's
    /// format strings, not stored here.
    classic_version: String,
    /// Name of the crash generator (e.g., "Buffout 4")
    crashgen_name: String,
}

impl Default for ReportGenerator {
    fn default() -> Self {
        Self::new()
    }
}

impl ReportGenerator {
    /// Creates a new report generator with the global string pool and default version.
    ///
    /// The generator uses the shared `STRING_POOL` for efficient memory usage
    /// through string interning. This allows multiple fragments to share
    /// common strings like headers, formatting markers, and error messages.
    ///
    /// # Returns
    ///
    /// A new `ReportGenerator` instance ready to generate report fragments.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::report::ReportGenerator;
    ///
    /// let generator = ReportGenerator::new();
    /// let header = generator.generate_header("crash.log");
    /// assert!(!header.is_empty());
    /// ```
    pub fn new() -> Self {
        // Empty default: the `CLASSIC ` decoration is supplied by the format string in
        // `generate_header` / `generate_footer`, so a caller using `new()` still gets a
        // header reading `**AUTOSCAN REPORT GENERATED BY CLASSIC **` (trailing space).
        // Production flows construct via `with_config` with the bare SemVer from
        // `CLASSIC_Info.version`.
        Self {
            pool: STRING_POOL.clone(),
            classic_version: String::new(),
            crashgen_name: "Crashgen".to_string(),
        }
    }

    /// Creates a report generator with specified configuration.
    ///
    /// # Arguments
    ///
    /// * `classic_version` - The bare SemVer version string (e.g., "v8.0.0"). The generator
    ///   prepends the `CLASSIC ` product-name prefix at format time, so the caller passes the
    ///   raw YAML value without decoration.
    /// * `crashgen_name` - The crash generator name (e.g., "Buffout 4")
    ///
    /// # Returns
    ///
    /// A configured `ReportGenerator` instance.
    pub fn with_config(classic_version: String, crashgen_name: String) -> Self {
        Self {
            pool: STRING_POOL.clone(),
            classic_version,
            crashgen_name,
        }
    }

    /// Generate a header fragment for the report.
    ///
    /// This produces output identical to Python's `ReportGeneratorFragments.generate_header()`.
    ///
    /// # Arguments
    ///
    /// * `crashlog_filename` - Name of the crash log file being analyzed
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the formatted header.
    pub fn generate_header(&self, crashlog_filename: &str) -> ReportFragment {
        let lines = vec![
            format!("# {}\n", crashlog_filename),
            format!(
                "**AUTOSCAN REPORT GENERATED BY CLASSIC {}**\n\n",
                self.classic_version
            ),
            "> **FOR BEST VIEWING EXPERIENCE OPEN THIS FILE IN NOTEPAD++ OR SIMILAR**\n\n"
                .to_string(),
            "> **PLEASE READ EVERYTHING CAREFULLY AND BEWARE OF FALSE POSITIVES**\n\n".to_string(),
            "---\n\n".to_string(),
        ];

        ReportFragment::from_lines_pooled(lines, &self.pool)
    }

    /// Generate an error section for the report.
    ///
    /// This produces output identical to Python's `ReportGeneratorFragments.generate_error_section()`.
    ///
    /// # Arguments
    ///
    /// * `main_error` - The main error message from the crash log
    /// * `crashgen_version` - The detected crashgen version string
    /// * `is_outdated` - Whether the crashgen version is outdated
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the formatted error section.
    pub fn generate_error_section(
        &self,
        main_error: &str,
        crashgen_version: &str,
        is_outdated: bool,
    ) -> ReportFragment {
        let status = if is_outdated {
            Some(CrashgenVersionStatus::Outdated)
        } else {
            Some(CrashgenVersionStatus::Valid)
        };
        self.generate_error_section_with_status(main_error, crashgen_version, status)
    }

    /// Generate an error section using list-based crashgen status.
    ///
    /// This is the preferred non-legacy version status path.
    pub fn generate_error_section_with_status(
        &self,
        main_error: &str,
        crashgen_version: &str,
        status: Option<CrashgenVersionStatus>,
    ) -> ReportFragment {
        self.generate_error_section_with_status_and_fake_mode(
            main_error,
            crashgen_version,
            status,
            false,
        )
    }

    /// Generate an error section with optional fake bot-compatible mode notice.
    pub fn generate_error_section_with_status_and_fake_mode(
        &self,
        main_error: &str,
        crashgen_version: &str,
        status: Option<CrashgenVersionStatus>,
        fake_bot_compatible_mode: bool,
    ) -> ReportFragment {
        let mut lines = vec![
            "### Error Information\n\n".to_string(),
            format!("**Main Error:** {}\n\n", main_error),
            format!(
                "**Detected {} Version:** {}\n\n",
                self.crashgen_name, crashgen_version
            ),
        ];

        if fake_bot_compatible_mode {
            lines.push("**# ⚠️ NOTICE : This report was generated in Bot Compatible Mode. Version and Settings checks are disabled. #**\n\n".to_string());
        } else {
            match status {
                Some(CrashgenVersionStatus::Valid) => {
                    lines.push(format!(
                        "✅ *You have a valid version of {}!*\n\n",
                        self.crashgen_name
                    ));
                }
                Some(CrashgenVersionStatus::NewerThanKnown) => {
                    lines.push(format!(
                        "✅ *Your {} version is newer than known versions.*\n\n",
                        self.crashgen_name
                    ));
                }
                Some(CrashgenVersionStatus::Outdated) => {
                    lines.push(format!(
                        "***❌ WARNING: YOUR {} IS OUTDATED! PLEASE UPDATE TO A VALID VERSION!***\n\n",
                        self.crashgen_name
                    ));
                }
                Some(CrashgenVersionStatus::NoSupportedVersion) => {
                    lines.push(
                        "⚠️ *No supported crash log generator for this game version yet.*\n\n"
                            .to_string(),
                    );
                }
                None => {
                    lines.push(format!(
                        "⚠️ *Unable to verify {} version.*\n\n",
                        self.crashgen_name
                    ));
                }
            }
        }

        lines.push("---\n\n".to_string());

        ReportFragment::from_lines_pooled(lines, &self.pool)
    }

    /// Generate the suspect section header.
    ///
    /// This produces output identical to Python's `generate_suspect_section_header()`.
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the suspect section header.
    pub fn generate_suspect_section_header(&self) -> ReportFragment {
        ReportFragment::from_lines(vec![
            "### Checking for Known Crash Messages, Errors and Suspects\n\n".to_string(),
        ])
    }

    /// Generate the suspect found footer based on whether suspects were detected.
    ///
    /// This produces output identical to Python's `generate_suspect_found_footer()`.
    ///
    /// # Arguments
    ///
    /// * `found_suspect` - Whether any suspects were detected
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the footer message.
    pub fn generate_suspect_found_footer(&self, found_suspect: bool) -> ReportFragment {
        if found_suspect {
            ReportFragment::from_lines(vec![
                "* **ONE OR MORE SUSPECTS DETECTED! CHECK LOG ABOVE FOR MORE INFORMATION!** *\n\n"
                    .to_string(),
                "---\n\n".to_string(),
            ])
        } else {
            ReportFragment::from_lines(vec![
                "* **NO SUSPECTS DETECTED** *\n\n".to_string(),
                "---\n\n".to_string(),
            ])
        }
    }

    /// Generate the settings section header.
    ///
    /// This produces output identical to Python's `generate_settings_section_header()`.
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the settings section header.
    pub fn generate_settings_section_header(&self) -> ReportFragment {
        ReportFragment::from_lines(vec![
            "### Checking for Settings-related Issues\n\n".to_string(),
        ])
    }

    /// Generate a mod check header with the specified check type.
    ///
    /// This produces output identical to Python's `generate_mod_check_header()`.
    ///
    /// # Arguments
    ///
    /// * `check_type` - Description of what type of mods are being checked
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the mod check header.
    pub fn generate_mod_check_header(&self, check_type: &str) -> ReportFragment {
        ReportFragment::from_lines(vec![format!(
            "### Checking For Mods That {}\n\n",
            check_type
        )])
    }

    /// Generate the plugin suspect header.
    ///
    /// This produces output identical to Python's `generate_plugin_suspect_header()`.
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the plugin suspect header.
    pub fn generate_plugin_suspect_header(&self) -> ReportFragment {
        ReportFragment::from_lines(vec![
            "### Checking for Plugin-related Errors\n\n".to_string(),
        ])
    }

    /// Generate the FormID section header.
    ///
    /// This produces output identical to Python's `generate_formid_section_header()`.
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the FormID section header.
    pub fn generate_formid_section_header(&self) -> ReportFragment {
        ReportFragment::from_lines(vec!["### Checking FormIDs\n\n".to_string()])
    }

    /// Generate the record section header.
    ///
    /// This produces output identical to Python's `generate_record_section_header()`.
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the record section header.
    pub fn generate_record_section_header(&self) -> ReportFragment {
        ReportFragment::from_lines(vec!["### Checking for Named Records\n\n".to_string()])
    }

    /// Generate the report footer.
    ///
    /// This produces output identical to Python's `generate_footer()`.
    /// The footer includes end of report marker, version info, and credits
    /// for the author and contributors.
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the report footer with credits.
    pub fn generate_footer(&self) -> ReportFragment {
        ReportFragment::from_lines(vec![
            "---\n\n".to_string(),
            "### End of Report\n\n".to_string(),
            format!("Generated by CLASSIC {}\n\n", self.classic_version),
            "---\n\n".to_string(),
            "Author/Made By: Poet (guidance.of.grace) | https://discord.gg/DfFYJtt8p4\n\n"
                .to_string(),
            "CONTRIBUTORS | evildarkarchon | kittivelae | AtomicFallout757 | wxMichael\n\n"
                .to_string(),
            "FO4 CLASSIC | https://www.nexusmods.com/fallout4/mods/56255\n".to_string(),
        ])
    }

    /// Generate a suspect section (legacy method for backward compatibility).
    ///
    /// Consider using `generate_suspect_section_header()` and `generate_suspect_found_footer()`
    /// for more granular control.
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
#[path = "report_tests.rs"]
mod tests;
