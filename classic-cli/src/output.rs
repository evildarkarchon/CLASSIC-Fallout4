use console::Style;
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use std::time::Duration;

/// Output formatter for CLI
///
/// Provides formatted output with colors, progress bars, and statistics.
pub struct OutputFormatter {
    multi_progress: MultiProgress,
    info_style: Style,
    success_style: Style,
    warning_style: Style,
    error_style: Style,
}

impl OutputFormatter {
    /// Create a new output formatter
    pub fn new() -> Self {
        Self {
            multi_progress: MultiProgress::new(),
            info_style: Style::new().blue(),
            success_style: Style::new().green().bold(),
            warning_style: Style::new().yellow(),
            error_style: Style::new().red().bold(),
        }
    }

    /// Print header banner
    pub fn print_header(&self, version: &str) {
        let header = format!(
            "CLASSIC v{} - Crash Log Auto Scanner\n{}",
            version,
            "=".repeat(60)
        );
        println!("{}", self.info_style.apply_to(header));
        println!();
    }

    /// Print an info message
    pub fn print_info(&self, message: &str) {
        println!("  {} {}", self.info_style.apply_to("ℹ"), message);
    }

    /// Print a success message
    pub fn print_success(&self, message: &str) {
        println!("  {} {}", self.success_style.apply_to("✓"), message);
    }

    /// Print a warning message
    pub fn print_warning(&self, message: &str) {
        println!("  {} {}", self.warning_style.apply_to("⚠"), message);
    }

    /// Print an error message
    pub fn print_error(&self, message: &str) {
        println!("  {} {}", self.error_style.apply_to("✗"), message);
    }

    /// Create a progress bar for file scanning with enhanced visuals
    pub fn create_progress_bar(&self, total: u64, message: &str) -> ProgressBar {
        let pb = self.multi_progress.add(ProgressBar::new(total));
        pb.set_style(
            ProgressStyle::default_bar()
                .template("{msg}\n[{bar:40.cyan/blue}] {pos}/{len} ({percent}%) - {elapsed_precise} ETA: {eta}")
                .expect("Invalid progress bar template")
                .progress_chars("█▓░"),
        );
        pb.set_message(message.to_string());
        pb.enable_steady_tick(Duration::from_millis(100));
        pb
    }

    /// Update progress bar with current status
    pub fn update_progress(&self, pb: &ProgressBar, current: u64, message: &str) {
        pb.set_position(current);
        pb.set_message(message.to_string());
    }

    /// Print scan results summary
    pub fn print_scan_summary(&self, stats: &ScanStats) {
        println!();
        println!("{}", self.success_style.apply_to("Results:"));
        println!("  Scanned: {} logs", stats.scanned_logs);
        println!("  Patterns matched: {}", stats.patterns_matched);
        println!("  FormIDs resolved: {}", stats.formids_resolved);
        println!("  Suspects identified: {}", stats.suspects_identified);
        println!();
    }

    /// Print footer with report location
    pub fn print_footer(&self, report_path: &str) {
        println!(
            "Reports saved to: {}",
            self.success_style.apply_to(report_path)
        );
        println!();
        println!("Press Enter to continue...");
    }

    /// Flush output and wait for user input
    pub fn wait_for_input(&self) -> std::io::Result<()> {
        use std::io::{BufRead, stdin};
        let stdin = stdin();
        let _ = stdin.lock().lines().next();
        Ok(())
    }
}

impl Default for OutputFormatter {
    fn default() -> Self {
        Self::new()
    }
}

/// Scan statistics
#[derive(Debug, Clone, Default)]
pub struct ScanStats {
    pub scanned_logs: usize,
    pub patterns_matched: usize,
    pub formids_resolved: usize,
    pub suspects_identified: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_output_formatter_creation() {
        let formatter = OutputFormatter::new();
        assert!(true); // Just verify it can be created
    }

    #[test]
    fn test_scan_stats_default() {
        let stats = ScanStats::default();
        assert_eq!(stats.scanned_logs, 0);
        assert_eq!(stats.patterns_matched, 0);
        assert_eq!(stats.formids_resolved, 0);
        assert_eq!(stats.suspects_identified, 0);
    }
}
