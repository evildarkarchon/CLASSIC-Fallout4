//! Papyrus log monitoring and analysis
//!
//! This module provides functionality for monitoring and analyzing Papyrus logs in real-time.
//! It tracks various statistics including dumps, stacks, warnings, and errors, with support
//! for continuous "tail -f" style monitoring.

use std::path::{Path, PathBuf};
use std::time::SystemTime;
use thiserror::Error;

/// Errors that can occur during Papyrus log analysis
#[derive(Debug, Error)]
pub enum PapyrusError {
    /// I/O error reading log file
    #[error("Failed to read Papyrus log: {0}")]
    IoError(#[from] std::io::Error),

    /// Log file not found
    #[error("Papyrus log file not found at: {0}")]
    LogNotFound(PathBuf),

    /// Encoding detection failed
    #[error("Failed to detect file encoding")]
    EncodingError,
}

/// Statistics collected from Papyrus logs
#[derive(Debug, Clone, Default, PartialEq)]
pub struct PapyrusStats {
    /// Number of "Dumping Stacks" entries (plural)
    pub dumps: usize,

    /// Number of "Dumping Stack" entries (singular)
    pub stacks: usize,

    /// Number of warning messages
    pub warnings: usize,

    /// Number of error messages
    pub errors: usize,

    /// Last modified timestamp of the log file
    pub last_modified: Option<SystemTime>,

    /// Total lines processed
    pub lines_processed: usize,
}

impl PapyrusStats {
    /// Create a new empty statistics instance
    pub fn new() -> Self {
        Self::default()
    }

    /// Calculate the dumps to stacks ratio
    ///
    /// Returns 0.0 if there are no dumps or stacks
    pub fn dumps_to_stacks_ratio(&self) -> f64 {
        if self.dumps == 0 || self.stacks == 0 {
            0.0
        } else {
            self.dumps as f64 / self.stacks as f64
        }
    }

    /// Get the total number of issues (warnings + errors)
    pub fn total_issues(&self) -> usize {
        self.warnings + self.errors
    }

    /// Calculate the error to warning ratio
    ///
    /// Returns 0.0 if there are no warnings
    pub fn error_to_warning_ratio(&self) -> f64 {
        if self.warnings == 0 {
            if self.errors > 0 { f64::INFINITY } else { 0.0 }
        } else {
            self.errors as f64 / self.warnings as f64
        }
    }

    /// Determine the severity level based on error/warning counts
    ///
    /// Returns:
    /// - "OK" if no errors, or errors are less than 25% of warnings
    /// - "Warning" if errors are between 25-100% of warnings
    /// - "Critical" if errors exceed warnings
    pub fn severity_level(&self) -> &'static str {
        if self.errors == 0 {
            "OK"
        } else if self.warnings == 0 {
            // Errors exist but no warnings - critical
            "Critical"
        } else {
            let ratio = self.errors as f64 / self.warnings as f64;
            if ratio <= 0.25 {
                "OK"
            } else if ratio <= 1.0 {
                "Warning"
            } else {
                "Critical"
            }
        }
    }

    /// Update statistics by processing a single new line
    ///
    /// This is used for incremental updates during "tail -f" style monitoring
    pub fn process_line(&mut self, line: &str) {
        self.lines_processed += 1;

        if line.contains("Dumping Stacks") {
            // Plural - multiple stacks dumped
            self.dumps += 1;
        } else if line.contains("Dumping Stack") {
            // Singular - single stack
            self.stacks += 1;
        }

        if line.contains(" warning: ") {
            self.warnings += 1;
        }

        if line.contains(" error: ") {
            self.errors += 1;
        }
    }
}

/// Papyrus log analyzer with support for both one-time analysis and continuous monitoring
pub struct PapyrusAnalyzer {
    /// Path to the Papyrus log file
    log_path: PathBuf,

    /// Current statistics
    stats: PapyrusStats,

    /// Last read position in the file (for tail -f behavior)
    last_position: u64,
}

impl PapyrusAnalyzer {
    /// Create a new Papyrus analyzer for the given log file
    ///
    /// # Arguments
    ///
    /// * `log_path` - Path to the Papyrus.0.log file
    ///
    /// # Returns
    ///
    /// A new `PapyrusAnalyzer` instance
    pub fn new(log_path: PathBuf) -> Self {
        Self {
            log_path,
            stats: PapyrusStats::new(),
            last_position: 0,
        }
    }

    /// Start monitoring from the END of the file (ignore prior history)
    ///
    /// This positions the analyzer at the end of the current file so that
    /// only NEW lines added after this point will be tracked.
    /// This implements true "tail -f" behavior for monitoring sessions.
    ///
    /// # Errors
    ///
    /// Returns error if file doesn't exist or can't be read
    pub fn start_monitoring(&mut self) -> Result<(), PapyrusError> {
        if !self.log_path.exists() {
            return Err(PapyrusError::LogNotFound(self.log_path.clone()));
        }

        // Get current file size and position at end
        let metadata = std::fs::metadata(&self.log_path)?;
        self.last_position = metadata.len();

        // Reset stats (we only care about new activity)
        self.stats = PapyrusStats::new();
        self.stats.last_modified = metadata.modified().ok();

        Ok(())
    }

    /// Check if the log file exists
    pub fn log_exists(&self) -> bool {
        self.log_path.exists()
    }

    /// Get the log file path
    pub fn log_path(&self) -> &Path {
        &self.log_path
    }

    /// Get current statistics
    pub fn stats(&self) -> &PapyrusStats {
        &self.stats
    }

    /// Reset statistics and position (start monitoring from beginning)
    pub fn reset(&mut self) {
        self.stats = PapyrusStats::new();
        self.last_position = 0;
    }

    /// Perform a full analysis of the log file from the beginning
    ///
    /// This reads the entire file and calculates statistics.
    ///
    /// # Returns
    ///
    /// `PapyrusStats` containing the collected statistics
    ///
    /// # Errors
    ///
    /// Returns error if:
    /// - Log file doesn't exist
    /// - Failed to read the file
    pub fn analyze_full(&mut self) -> Result<PapyrusStats, PapyrusError> {
        // Check if log exists
        if !self.log_path.exists() {
            return Err(PapyrusError::LogNotFound(self.log_path.clone()));
        }

        // Get file metadata for last modified time
        let metadata = std::fs::metadata(&self.log_path)?;
        self.stats.last_modified = metadata.modified().ok();

        // Read the log file with UTF-8 encoding, ignoring invalid sequences
        let content = std::fs::read_to_string(&self.log_path).or_else(
            |_| -> Result<String, std::io::Error> {
                // If UTF-8 fails, try reading as bytes and convert lossily
                let bytes = std::fs::read(&self.log_path)?;
                Ok(String::from_utf8_lossy(&bytes).to_string())
            },
        )?;

        // Update position to end of file
        self.last_position = content.len() as u64;

        // Reset stats and process all lines
        self.stats.dumps = 0;
        self.stats.stacks = 0;
        self.stats.warnings = 0;
        self.stats.errors = 0;
        self.stats.lines_processed = 0;

        for line in content.lines() {
            self.stats.process_line(line);
        }

        Ok(self.stats.clone())
    }

    /// Read and process only new lines added since last check (tail -f behavior)
    ///
    /// This implements incremental monitoring by only reading new content
    /// that has been appended to the file since the last read.
    ///
    /// # Returns
    ///
    /// Tuple of (new lines added, updated statistics), or None if no changes
    ///
    /// # Errors
    ///
    /// Returns error if:
    /// - Failed to read the file
    /// - File was truncated (size < last_position)
    pub fn check_for_updates(
        &mut self,
    ) -> Result<Option<(Vec<String>, PapyrusStats)>, PapyrusError> {
        if !self.log_path.exists() {
            return Err(PapyrusError::LogNotFound(self.log_path.clone()));
        }

        // Get current file size
        let metadata = std::fs::metadata(&self.log_path)?;
        let current_size = metadata.len();

        // Check if file was modified
        if current_size == self.last_position {
            // No changes
            return Ok(None);
        }

        if current_size < self.last_position {
            // File was truncated or rotated, re-read from beginning
            self.reset();
            return self.analyze_full().map(|stats| Some((vec![], stats)));
        }

        // Read only the new content
        use std::fs::File;
        use std::io::{Read, Seek, SeekFrom};

        let mut file = File::open(&self.log_path)?;
        file.seek(SeekFrom::Start(self.last_position))?;

        let mut new_content = Vec::new();
        file.read_to_end(&mut new_content)?;

        // Update position
        self.last_position = current_size;

        // Update last modified time
        self.stats.last_modified = metadata.modified().ok();

        // Convert to string and process new lines
        let new_text = String::from_utf8_lossy(&new_content);
        let new_lines: Vec<String> = new_text.lines().map(|s| s.to_string()).collect();

        for line in &new_lines {
            self.stats.process_line(line);
        }

        Ok(Some((new_lines, self.stats.clone())))
    }

    /// Analyze the log file and return formatted summary text
    ///
    /// # Returns
    ///
    /// Formatted string with statistics, or error message if log not found
    pub fn analyze_to_string(&mut self) -> String {
        match self.analyze_full() {
            Ok(stats) => {
                format!(
                    "NUMBER OF DUMPS    : {}\n\
                     NUMBER OF STACKS   : {}\n\
                     DUMPS/STACKS RATIO : {:.3}\n\
                     NUMBER OF WARNINGS : {}\n\
                     NUMBER OF ERRORS   : {}\n\
                     SEVERITY           : {}\n\
                     LINES PROCESSED    : {}",
                    stats.dumps,
                    stats.stacks,
                    stats.dumps_to_stacks_ratio(),
                    stats.warnings,
                    stats.errors,
                    stats.severity_level(),
                    stats.lines_processed
                )
            }
            Err(_) => {
                "[!] ERROR : UNABLE TO FIND *Papyrus.0.log* (LOGGING IS DISABLED OR YOU DIDN'T RUN THE GAME)\n\
                 ENABLE PAPYRUS LOGGING MANUALLY OR WITH BETHINI AND START THE GAME TO GENERATE THE LOG FILE\n\
                 BethINi Link | Use Manual Download : https://www.nexusmods.com/site/mods/631?tab=files"
                    .to_string()
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Seek, SeekFrom, Write};
    use tempfile::NamedTempFile;

    #[test]
    fn test_papyrus_stats_ratios() {
        let mut stats = PapyrusStats::new();
        stats.dumps = 10;
        stats.stacks = 5;
        stats.warnings = 20;
        stats.errors = 5;

        assert_eq!(stats.dumps_to_stacks_ratio(), 2.0);
        assert_eq!(stats.error_to_warning_ratio(), 0.25);
        assert_eq!(stats.total_issues(), 25);
        assert_eq!(stats.severity_level(), "OK");
    }

    #[test]
    fn test_severity_levels() {
        let mut stats = PapyrusStats::new();

        // OK - no errors
        stats.warnings = 10;
        stats.errors = 0;
        assert_eq!(stats.severity_level(), "OK");

        // Warning - errors < warnings
        stats.errors = 5;
        assert_eq!(stats.severity_level(), "Warning");

        // Critical - errors >= warnings
        stats.errors = 10;
        assert_eq!(stats.severity_level(), "Warning");

        stats.errors = 15;
        assert_eq!(stats.severity_level(), "Critical");
    }

    #[test]
    fn test_process_line() {
        let mut stats = PapyrusStats::new();

        stats.process_line("Some log content");
        assert_eq!(stats.lines_processed, 1);
        assert_eq!(stats.dumps, 0);

        stats.process_line("Dumping Stacks for thread 0x1234");
        assert_eq!(stats.dumps, 1);

        stats.process_line("Dumping Stack for function foo");
        assert_eq!(stats.stacks, 1);

        stats.process_line("[2024/01/01] warning: Variable not initialized");
        assert_eq!(stats.warnings, 1);

        stats.process_line("[2024/01/01] error: Null reference");
        assert_eq!(stats.errors, 1);
    }

    #[test]
    fn test_analyze_full() {
        let mut temp_file = NamedTempFile::new().unwrap();
        writeln!(temp_file, "Some log content").unwrap();
        writeln!(temp_file, "Dumping Stacks for thread 0x1234").unwrap();
        writeln!(temp_file, "Dumping Stack for function foo").unwrap();
        writeln!(temp_file, "[2024/01/01] warning: Variable not initialized").unwrap();
        writeln!(temp_file, "[2024/01/01] error: Null reference").unwrap();
        writeln!(temp_file, "[2024/01/01] error: Stack overflow").unwrap();

        let mut analyzer = PapyrusAnalyzer::new(temp_file.path().to_path_buf());
        let stats = analyzer.analyze_full().unwrap();

        assert_eq!(stats.dumps, 1);
        assert_eq!(stats.stacks, 1);
        assert_eq!(stats.warnings, 1);
        assert_eq!(stats.errors, 2);
        assert_eq!(stats.lines_processed, 6);
    }

    #[test]
    fn test_tail_behavior() {
        let mut temp_file = NamedTempFile::new().unwrap();
        writeln!(temp_file, "Initial line").unwrap();
        writeln!(temp_file, "Dumping Stacks").unwrap();
        temp_file.flush().unwrap();

        let mut analyzer = PapyrusAnalyzer::new(temp_file.path().to_path_buf());

        // Initial full analysis
        let stats = analyzer.analyze_full().unwrap();
        assert_eq!(stats.dumps, 1);
        assert_eq!(stats.lines_processed, 2);

        // No changes - should return None
        let result = analyzer.check_for_updates().unwrap();
        assert!(result.is_none());

        // Append new lines
        writeln!(temp_file, "New line added").unwrap();
        writeln!(temp_file, "Dumping Stack").unwrap();
        writeln!(temp_file, "[2024/01/01] error: Something bad").unwrap();
        temp_file.flush().unwrap();

        // Check for updates - should detect new lines
        let result = analyzer.check_for_updates().unwrap();
        assert!(result.is_some());

        let (new_lines, updated_stats) = result.unwrap();
        assert_eq!(new_lines.len(), 3);
        assert_eq!(updated_stats.dumps, 1); // Still 1 from before
        assert_eq!(updated_stats.stacks, 1); // New stack detected
        assert_eq!(updated_stats.errors, 1); // New error detected
        assert_eq!(updated_stats.lines_processed, 5); // Total lines
    }

    #[test]
    fn test_file_truncation() {
        let mut temp_file = NamedTempFile::new().unwrap();
        writeln!(temp_file, "Line 1").unwrap();
        writeln!(temp_file, "Dumping Stacks").unwrap();
        temp_file.flush().unwrap();

        let mut analyzer = PapyrusAnalyzer::new(temp_file.path().to_path_buf());
        analyzer.analyze_full().unwrap();

        // Truncate file (simulate log rotation)
        temp_file.as_file_mut().seek(SeekFrom::Start(0)).unwrap();
        temp_file.as_file_mut().set_len(0).unwrap();
        writeln!(temp_file, "New start").unwrap();
        temp_file.flush().unwrap();

        // Should detect truncation and re-read from beginning
        let result = analyzer.check_for_updates().unwrap();
        assert!(result.is_some());

        let (_, stats) = result.unwrap();
        assert_eq!(stats.dumps, 0); // Old dump should be gone
        assert_eq!(stats.lines_processed, 1); // Only new line
    }

    #[test]
    fn test_analyze_nonexistent_log() {
        let mut analyzer = PapyrusAnalyzer::new(PathBuf::from("/nonexistent/path/Papyrus.0.log"));
        let result = analyzer.analyze_full();

        assert!(result.is_err());
        assert!(matches!(result, Err(PapyrusError::LogNotFound(_))));
    }
}
