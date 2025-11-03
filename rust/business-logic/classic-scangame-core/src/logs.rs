//! Log File Error Detection Module
//!
//! Provides high-performance log file scanning and error detection for game crash logs.
//! Replaces Python LogProcessor with native Rust implementation offering:
//! - Parallel log file processing
//! - Efficient pattern matching with aho-corasick
//! - Automatic encoding detection
//! - Memory-efficient error collection
//!
//! ## Architecture
//!
//! Scans log directories and detects errors based on configurable patterns:
//! - Include patterns (catch_log_errors)
//! - Exclude file patterns (exclude_log_files)
//! - Exclude error patterns (exclude_log_errors)

use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};

use aho_corasick::AhoCorasick;
use rayon::prelude::*;
use thiserror::Error;

/// Errors that can occur during log processing
#[derive(Debug, Error)]
pub enum LogError {
    /// Failed to read log file
    #[error("Failed to read log file: {0}")]
    IoError(#[from] std::io::Error),

    /// Directory not found
    #[error("Directory not found: {0}")]
    DirectoryNotFound(String),

    /// Pattern compilation error
    #[error("Pattern compilation error: {0}")]
    PatternError(String),
}

/// Result type for log operations
pub type Result<T> = std::result::Result<T, LogError>;

/// Log error entry
#[derive(Debug, Clone)]
pub struct LogErrorEntry {
    /// Path to the log file
    pub file_path: PathBuf,

    /// Error lines found in the log (limited to last 50)
    pub errors: Vec<String>,

    /// Total number of errors found (before truncation)
    pub total_errors: usize,
}

/// Log file processor
///
/// Scans directories for log files and detects errors based on configurable patterns.
/// Provides high-performance parallel processing with efficient pattern matching.
///
/// # Example
///
/// ```rust
/// use classic_scangame_core::logs::LogProcessor;
/// use std::path::Path;
///
/// let catch_errors = vec!["error".to_string(), "fatal".to_string()];
/// let ignore_files = vec!["crash-".to_string()];
/// let ignore_errors = vec!["warning".to_string()];
///
/// let processor = LogProcessor::new(catch_errors, ignore_files, ignore_errors)?;
/// let report = processor.process_logs(Path::new("/logs"))?;
/// println!("{}", report);
/// ```
pub struct LogProcessor {
    /// Pattern matcher for error detection
    error_matcher: AhoCorasick,

    /// Pattern matcher for error exclusion
    exclude_matcher: Option<AhoCorasick>,

    /// File name patterns to exclude (lowercase)
    exclude_files: HashSet<String>,

    /// Original error patterns (for reference)
    error_patterns: Vec<String>,
}

impl LogProcessor {
    /// Create a new log processor with pattern configuration
    ///
    /// # Arguments
    ///
    /// * `catch_errors` - Patterns to match for error detection (case-insensitive)
    /// * `exclude_files` - File name patterns to exclude (e.g., ["crash-"])
    /// * `exclude_errors` - Error patterns to exclude (case-insensitive)
    ///
    /// # Returns
    ///
    /// Configured LogProcessor or error if patterns cannot be compiled
    ///
    /// # Example
    ///
    /// ```rust
    /// let processor = LogProcessor::new(
    ///     vec!["error".to_string()],
    ///     vec!["crash-".to_string()],
    ///     vec!["ignore".to_string()]
    /// )?;
    /// ```
    pub fn new(
        catch_errors: Vec<String>,
        exclude_files: Vec<String>,
        exclude_errors: Vec<String>,
    ) -> Result<Self> {
        // Build error matcher (case-insensitive)
        let error_matcher = AhoCorasick::builder()
            .ascii_case_insensitive(true)
            .build(&catch_errors)
            .map_err(|e| LogError::PatternError(e.to_string()))?;

        // Build exclude matcher if patterns provided
        let exclude_matcher = if exclude_errors.is_empty() {
            None
        } else {
            Some(
                AhoCorasick::builder()
                    .ascii_case_insensitive(true)
                    .build(&exclude_errors)
                    .map_err(|e| LogError::PatternError(e.to_string()))?,
            )
        };

        // Convert exclude files to lowercase set
        let exclude_files: HashSet<String> = exclude_files
            .into_iter()
            .map(|s| s.to_lowercase())
            .collect();

        Ok(Self {
            error_matcher,
            exclude_matcher,
            exclude_files,
            error_patterns: catch_errors,
        })
    }

    /// Process all log files in a directory
    ///
    /// # Arguments
    ///
    /// * `folder_path` - Directory containing log files
    ///
    /// # Returns
    ///
    /// Formatted error report string
    ///
    /// # Example
    ///
    /// ```rust
    /// let report = processor.process_logs(Path::new("/logs"))?;
    /// if !report.is_empty() {
    ///     println!("Errors found:\n{}", report);
    /// }
    /// ```
    pub fn process_logs(&self, folder_path: &Path) -> Result<String> {
        if !folder_path.exists() {
            return Err(LogError::DirectoryNotFound(
                folder_path.display().to_string(),
            ));
        }

        // Find valid log files
        let log_files = self.find_log_files(folder_path)?;

        if log_files.is_empty() {
            return Ok(String::new());
        }

        // Process files in parallel
        let results: Vec<Option<LogErrorEntry>> = log_files
            .par_iter()
            .map(|log_path| self.process_single_log(log_path))
            .collect();

        // Format error report
        Ok(self.format_report(&results))
    }

    /// Find valid log files in directory
    fn find_log_files(&self, folder_path: &Path) -> Result<Vec<PathBuf>> {
        let mut log_files = Vec::new();

        for entry in fs::read_dir(folder_path)? {
            let entry = entry?;
            let path = entry.path();

            // Check if it's a .log file
            if !path.is_file() {
                continue;
            }

            if let Some(ext) = path.extension() {
                if ext.to_string_lossy().to_lowercase() != "log" {
                    continue;
                }
            } else {
                continue;
            }

            // Check if file should be excluded
            if self.should_exclude_file(&path) {
                continue;
            }

            log_files.push(path);
        }

        Ok(log_files)
    }

    /// Check if file should be excluded
    fn should_exclude_file(&self, path: &Path) -> bool {
        let path_str = path.to_string_lossy().to_lowercase();

        // Always exclude crash logs
        if path_str.contains("crash-") {
            return true;
        }

        // Check against exclude patterns
        self.exclude_files
            .iter()
            .any(|pattern| path_str.contains(pattern))
    }

    /// Process a single log file
    fn process_single_log(&self, log_path: &Path) -> Option<LogErrorEntry> {
        // Read file with UTF-8, ignoring errors
        let content = match fs::read_to_string(log_path) {
            Ok(c) => c,
            Err(_) => {
                // Try to read as bytes and convert
                let bytes = fs::read(log_path).ok()?;
                String::from_utf8_lossy(&bytes).to_string()
            }
        };

        // Find errors in content
        let (errors, total_errors) = self.find_errors(&content);

        if errors.is_empty() {
            None
        } else {
            Some(LogErrorEntry {
                file_path: log_path.to_path_buf(),
                errors,
                total_errors,
            })
        }
    }

    /// Find error lines in log content
    ///
    /// Returns a tuple of (error_lines, total_count) where error_lines is limited to the last 50 errors
    fn find_errors(&self, content: &str) -> (Vec<String>, usize) {
        let mut errors = Vec::new();

        for line in content.lines() {
            // Check if line contains any error pattern
            if !self.error_matcher.is_match(line) {
                continue;
            }

            // Check if line should be excluded
            if let Some(ref exclude_matcher) = self.exclude_matcher {
                if exclude_matcher.is_match(line) {
                    continue;
                }
            }

            // Add error line
            errors.push(format!("ERROR > {}", line));
        }

        // Keep track of total count before truncation
        let total_errors = errors.len();

        // Limit to last 50 errors (tail -50)
        if total_errors > 50 {
            let skip_count = total_errors - 50;
            errors = errors.into_iter().skip(skip_count).collect();
        }

        (errors, total_errors)
    }

    /// Format error report for all processed logs
    fn format_report(&self, results: &[Option<LogErrorEntry>]) -> String {
        let mut report = String::new();

        for entry_opt in results {
            if let Some(entry) = entry_opt {
                report
                    .push_str("[!] CAUTION : THE FOLLOWING LOG FILE REPORTS ONE OR MORE ERRORS!\n");
                report
                    .push_str("[ Errors do not necessarily mean that the mod is not working. ]\n");
                report.push_str(&format!("\nLOG PATH > {}\n", entry.file_path.display()));

                // Show truncation notice if errors were limited
                if entry.total_errors > entry.errors.len() {
                    report.push_str(&format!(
                        "[ Showing last {} of {} total errors ]\n\n",
                        entry.errors.len(),
                        entry.total_errors
                    ));
                } else {
                    report.push('\n');
                }

                for error in &entry.errors {
                    report.push_str(error);
                    report.push('\n');
                }

                report.push_str(&format!(
                    "\n* TOTAL NUMBER OF DETECTED LOG ERRORS * : {}\n",
                    entry.total_errors
                ));
            }
        }

        report
    }

    /// Get configured error patterns
    pub fn error_patterns(&self) -> &[String] {
        &self.error_patterns
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn test_processor_creation() {
        let processor = LogProcessor::new(
            vec!["error".to_string()],
            vec!["crash-".to_string()],
            vec!["warning".to_string()],
        )
        .unwrap();

        assert_eq!(processor.error_patterns.len(), 1);
    }

    #[test]
    fn test_error_detection() {
        let temp_dir = TempDir::new().unwrap();
        let log_file = temp_dir.path().join("test.log");

        // Create test log with errors
        fs::write(
            &log_file,
            "INFO: Starting\nERROR: Something failed\nINFO: Continuing\n",
        )
        .unwrap();

        let processor = LogProcessor::new(vec!["error".to_string()], vec![], vec![]).unwrap();

        let report = processor.process_logs(temp_dir.path()).unwrap();
        assert!(report.contains("ERROR > ERROR: Something failed"));
    }

    #[test]
    fn test_error_exclusion() {
        let temp_dir = TempDir::new().unwrap();
        let log_file = temp_dir.path().join("test.log");

        fs::write(
            &log_file,
            "ERROR: This should be caught\nERROR: Warning - ignore this\n",
        )
        .unwrap();

        let processor = LogProcessor::new(
            vec!["error".to_string()],
            vec![],
            vec!["warning".to_string()],
        )
        .unwrap();

        let report = processor.process_logs(temp_dir.path()).unwrap();
        assert!(report.contains("This should be caught"));
        assert!(!report.contains("Warning - ignore this"));
    }

    #[test]
    fn test_crash_log_exclusion() {
        let temp_dir = TempDir::new().unwrap();
        let crash_log = temp_dir.path().join("crash-2024.log");

        fs::write(&crash_log, "ERROR: Crash happened\n").unwrap();

        let processor = LogProcessor::new(vec!["error".to_string()], vec![], vec![]).unwrap();

        let report = processor.process_logs(temp_dir.path()).unwrap();
        assert!(report.is_empty());
    }

    #[test]
    fn test_error_truncation() {
        let temp_dir = TempDir::new().unwrap();
        let log_file = temp_dir.path().join("test.log");

        // Create a log with 100 errors
        let mut log_content = String::new();
        for i in 1..=100 {
            log_content.push_str(&format!("ERROR: Error number {}\n", i));
        }
        fs::write(&log_file, log_content).unwrap();

        let processor = LogProcessor::new(vec!["error".to_string()], vec![], vec![]).unwrap();

        let report = processor.process_logs(temp_dir.path()).unwrap();

        // Should show truncation notice
        assert!(report.contains("Showing last 50 of 100 total errors"));

        // Should show total count as 100
        assert!(report.contains("TOTAL NUMBER OF DETECTED LOG ERRORS * : 100"));

        // Should contain last error (100) but not first error (1)
        assert!(report.contains("ERROR > ERROR: Error number 100"));
        // Use exact match with newline to avoid matching "10", "100", etc.
        assert!(!report.contains("ERROR > ERROR: Error number 1\n"));

        // Should contain error 51 (first of last 50)
        assert!(report.contains("ERROR > ERROR: Error number 51"));
    }
}
