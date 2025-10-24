use anyhow::Result;
use classic_config_core::ClassicConfig;
use classic_file_io_core::{BackupInfo, BackupType};
use classic_scanlog_core::papyrus::PapyrusStats;
use std::collections::HashMap;
use std::path::PathBuf;

// Forward declare SettingsState to avoid circular dependency
pub use crate::ui::SettingsState;
use crate::widgets::FolderPickerState;

/// Application state for the TUI
pub struct App {
    /// Configuration loaded from YAML or defaults
    pub config: ClassicConfig,
    /// Current UI state (which screen is active)
    pub ui_state: UiState,
    /// Current scan state
    pub scan_state: ScanState,
    /// Whether the application should quit
    pub should_quit: bool,
    /// Staging mods folder path
    pub staging_folder: Option<PathBuf>,
    /// Custom scan folder path
    pub custom_folder: Option<PathBuf>,
    /// Output buffer for display
    pub output_lines: Vec<String>,
    /// Scroll offset for output viewer
    pub scroll_offset: usize,
    /// Check for updates flag
    pub check_updates: bool,
    /// Settings screen state
    pub settings_state: SettingsState,
    /// Staging folder picker state
    pub staging_picker: Option<FolderPickerState>,
    /// Custom folder picker state
    pub custom_picker: Option<FolderPickerState>,
    /// Papyrus monitoring statistics
    pub papyrus_stats: Option<PapyrusStats>,
    /// Recent Papyrus log lines for display
    pub papyrus_log_lines: Vec<String>,
    /// Backup status for all backup types
    pub backup_status: HashMap<BackupType, BackupInfo>,
    /// List of report file paths in Crash Logs/Reports/ directory
    pub report_files: Vec<PathBuf>,
    /// Currently selected report index
    pub selected_report_index: usize,
    /// Content of currently loaded report
    pub current_report_content: Vec<String>,
    /// Scroll offset for report viewer
    pub report_scroll_offset: usize,
    /// Search query string
    pub search_query: String,
    /// List of search match positions (line_index, column_start, column_end)
    pub search_matches: Vec<(usize, usize, usize)>,
    /// Current match index being viewed
    pub current_match_index: usize,
    /// Whether search mode is active
    pub search_active: bool,
}

/// UI state representing which screen is active
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UiState {
    /// Main screen with folder selectors and scan buttons
    MainScreen,
    /// Help screen showing keyboard shortcuts
    HelpScreen,
    /// Settings screen for configuration
    SettingsScreen,
    /// Papyrus monitor screen
    PapyrusScreen,
    /// Backup operations screen
    BackupScreen,
    /// Results viewer screen
    ResultsScreen,
}

/// Scan state representing the current scan operation
#[derive(Debug, Clone)]
pub enum ScanState {
    /// No scan is running
    Idle,
    /// Crash log scan in progress with completion percentage (0.0 to 1.0)
    CrashScanning {
        /// Scan progress from 0.0 to 1.0
        progress: f64,
    },
    /// Game files scan in progress with completion percentage (0.0 to 1.0)
    GameScanning {
        /// Scan progress from 0.0 to 1.0
        progress: f64,
    },
    /// Papyrus monitoring active
    PapyrusMonitoring,
    /// Scan completed successfully with result summary
    Completed {
        /// Summary of scan results
        results: ScanResults,
    },
    /// Scan failed with error
    Error(String),
}

/// Scan results summary
#[derive(Debug, Clone)]
pub struct ScanResults {
    pub scanned_count: usize,
    pub patterns_matched: usize,
    pub formids_resolved: usize,
    pub suspects_count: usize,
}

impl App {
    /// Create a new application instance with default configuration
    pub fn new() -> Self {
        Self {
            config: ClassicConfig::default(),
            ui_state: UiState::MainScreen,
            scan_state: ScanState::Idle,
            should_quit: false,
            staging_folder: None,
            custom_folder: None,
            output_lines: Vec::new(),
            scroll_offset: 0,
            check_updates: true,
            settings_state: SettingsState::new(),
            staging_picker: None,
            custom_picker: None,
            papyrus_stats: None,
            papyrus_log_lines: Vec::new(),
            backup_status: HashMap::new(),
            report_files: Vec::new(),
            selected_report_index: 0,
            current_report_content: Vec::new(),
            report_scroll_offset: 0,
            search_query: String::new(),
            search_matches: Vec::new(),
            current_match_index: 0,
            search_active: false,
        }
    }

    /// Create application from loaded configuration
    pub fn with_config(config: ClassicConfig) -> Self {
        let mut app = Self::new();
        app.config = config;
        app.staging_folder = app.config.paths.mods_folder.clone();
        app.custom_folder = app.config.paths.scan_custom.clone();
        app
    }

    /// Switch to a different UI screen
    pub fn switch_screen(&mut self, state: UiState) {
        self.ui_state = state;
    }

    /// Add a line to the output buffer
    pub fn add_output(&mut self, line: String) {
        self.output_lines.push(line);
        // Auto-scroll to bottom when new output arrives
        self.scroll_offset = self.output_lines.len().saturating_sub(1);
    }

    /// Clear the output buffer
    pub fn clear_output(&mut self) {
        self.output_lines.clear();
        self.scroll_offset = 0;
    }

    /// Scroll output up by the specified number of lines
    pub fn scroll_up(&mut self, lines: usize) {
        self.scroll_offset = self.scroll_offset.saturating_sub(lines);
    }

    /// Scroll output down by the specified number of lines
    pub fn scroll_down(&mut self, lines: usize, visible_lines: usize) {
        let max_scroll = self.output_lines.len().saturating_sub(visible_lines);
        self.scroll_offset = (self.scroll_offset + lines).min(max_scroll);
    }

    /// Update staging folder path
    pub fn set_staging_folder(&mut self, path: PathBuf) {
        self.staging_folder = Some(path.clone());
        self.config.paths.mods_folder = Some(path);
    }

    /// Update custom scan folder path
    pub fn set_custom_folder(&mut self, path: PathBuf) {
        self.custom_folder = Some(path.clone());
        self.config.paths.scan_custom = Some(path);
    }

    /// Start a crash log scan
    pub fn start_crash_scan(&mut self) {
        self.scan_state = ScanState::CrashScanning { progress: 0.0 };
        self.clear_output();
        self.add_output("Starting crash log scan...".to_string());
    }

    /// Start a game files scan
    pub fn start_game_scan(&mut self) {
        self.scan_state = ScanState::GameScanning { progress: 0.0 };
        self.clear_output();
        self.add_output("Starting game files scan...".to_string());
    }

    /// Toggle Papyrus monitoring
    pub fn toggle_papyrus_monitor(&mut self) {
        match self.scan_state {
            ScanState::PapyrusMonitoring => {
                self.scan_state = ScanState::Idle;
                self.add_output("Papyrus monitoring stopped.".to_string());
            }
            _ => {
                self.scan_state = ScanState::PapyrusMonitoring;
                self.switch_screen(UiState::PapyrusScreen);
                self.clear_output();
                self.add_output("Papyrus monitoring started...".to_string());
            }
        }
    }

    /// Update scan progress
    pub fn update_progress(&mut self, progress: f64) {
        match &mut self.scan_state {
            ScanState::CrashScanning { progress: p } | ScanState::GameScanning { progress: p } => {
                *p = progress;
            }
            _ => {}
        }
    }

    /// Mark scan as completed with results
    pub fn complete_scan(&mut self, results: ScanResults) {
        self.scan_state = ScanState::Completed { results };
    }

    /// Mark scan as failed with error
    pub fn scan_error(&mut self, error: String) {
        self.scan_state = ScanState::Error(error.clone());
        self.add_output(format!("Error: {}", error));
    }

    /// Check if a scan is currently running
    pub fn is_scanning(&self) -> bool {
        matches!(
            self.scan_state,
            ScanState::CrashScanning { .. } | ScanState::GameScanning { .. }
        )
    }

    /// Save current configuration to YAML
    pub async fn save_config(&self) -> Result<()> {
        let config_path = self.config.get_config_path();
        self.config.save_to_yaml(&config_path).await?;
        Ok(())
    }

    /// Open staging folder picker
    pub fn open_staging_picker(&mut self) {
        let mut picker = FolderPickerState::new(self.staging_folder.clone());
        picker.activate();
        self.staging_picker = Some(picker);
    }

    /// Open custom folder picker
    pub fn open_custom_picker(&mut self) {
        let mut picker = FolderPickerState::new(self.custom_folder.clone());
        picker.activate();
        self.custom_picker = Some(picker);
    }

    /// Close staging folder picker
    pub fn close_staging_picker(&mut self) {
        self.staging_picker = None;
    }

    /// Close custom folder picker
    pub fn close_custom_picker(&mut self) {
        self.custom_picker = None;
    }

    /// Check if any folder picker is active
    pub fn is_folder_picker_active(&self) -> bool {
        self.staging_picker
            .as_ref()
            .map(|p| p.is_active())
            .unwrap_or(false)
            || self
                .custom_picker
                .as_ref()
                .map(|p| p.is_active())
                .unwrap_or(false)
    }

    /// Update Papyrus statistics
    pub fn update_papyrus_stats(&mut self, stats: PapyrusStats) {
        self.papyrus_stats = Some(stats);
    }

    /// Add new Papyrus log lines
    pub fn add_papyrus_lines(&mut self, lines: Vec<String>) {
        // Keep only the last 1000 lines to prevent unbounded growth
        const MAX_LINES: usize = 1000;
        self.papyrus_log_lines.extend(lines);
        if self.papyrus_log_lines.len() > MAX_LINES {
            let keep_from = self.papyrus_log_lines.len() - MAX_LINES;
            self.papyrus_log_lines = self.papyrus_log_lines[keep_from..].to_vec();
        }
    }

    /// Clear Papyrus monitoring data
    pub fn clear_papyrus_data(&mut self) {
        self.papyrus_stats = None;
        self.papyrus_log_lines.clear();
    }

    /// Update backup status
    pub fn update_backup_status(&mut self, status: HashMap<BackupType, BackupInfo>) {
        self.backup_status = status;
    }

    /// Check if a backup exists for the given type
    pub fn backup_exists(&self, backup_type: BackupType) -> bool {
        self.backup_status
            .get(&backup_type)
            .map(|info| info.exists)
            .unwrap_or(false)
    }

    /// Load report files from the Crash Logs/Reports/ directory
    pub async fn load_report_files(&mut self) -> Result<()> {
        use std::fs;

        // Construct path to reports directory from docs_root
        let reports_dir = if let Some(docs_root) = &self.config.paths.docs_root {
            docs_root.join("Crash Logs").join("Reports")
        } else {
            // Fallback to default location if docs_root not available
            return Ok(());
        };

        if !reports_dir.exists() {
            self.report_files.clear();
            return Ok(());
        }

        let mut files = Vec::new();

        if let Ok(entries) = fs::read_dir(&reports_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_file() {
                    // Check if it's a text file (has .txt or .log extension)
                    if let Some(ext) = path.extension() {
                        if ext == "txt" || ext == "log" {
                            files.push(path);
                        }
                    }
                }
            }
        }

        // Sort by filename in descending order (newest first)
        files.sort_by(|a, b| {
            b.file_name()
                .cmp(&a.file_name())
        });

        self.report_files = files;
        self.selected_report_index = 0;

        // Load first report if available
        if !self.report_files.is_empty() {
            self.load_selected_report().await?;
        }

        Ok(())
    }

    /// Load the currently selected report
    pub async fn load_selected_report(&mut self) -> Result<()> {
        if self.selected_report_index >= self.report_files.len() {
            self.current_report_content.clear();
            return Ok(());
        }

        let report_path = &self.report_files[self.selected_report_index];

        // Read file directly with tokio
        match tokio::fs::read_to_string(report_path).await {
            Ok(content) => {
                self.current_report_content = content.lines().map(|s| s.to_string()).collect();
                self.report_scroll_offset = 0;
                Ok(())
            }
            Err(e) => {
                self.current_report_content = vec![format!("Error loading report: {}", e)];
                Ok(())
            }
        }
    }

    /// Select the next report in the list
    pub async fn select_next_report(&mut self) -> Result<()> {
        if !self.report_files.is_empty() && self.selected_report_index < self.report_files.len() - 1 {
            self.selected_report_index += 1;
            self.load_selected_report().await?;
        }
        Ok(())
    }

    /// Select the previous report in the list
    pub async fn select_previous_report(&mut self) -> Result<()> {
        if self.selected_report_index > 0 {
            self.selected_report_index -= 1;
            self.load_selected_report().await?;
        }
        Ok(())
    }

    /// Scroll the report viewer up
    pub fn scroll_report_up(&mut self, lines: usize) {
        self.report_scroll_offset = self.report_scroll_offset.saturating_sub(lines);
    }

    /// Scroll the report viewer down
    pub fn scroll_report_down(&mut self, lines: usize, visible_lines: usize) {
        let max_scroll = self.current_report_content.len().saturating_sub(visible_lines);
        self.report_scroll_offset = (self.report_scroll_offset + lines).min(max_scroll);
    }

    /// Start search mode
    pub fn start_search(&mut self) {
        self.search_active = true;
        self.search_query.clear();
        self.search_matches.clear();
        self.current_match_index = 0;
    }

    /// Exit search mode
    pub fn exit_search(&mut self) {
        self.search_active = false;
        self.search_query.clear();
        self.search_matches.clear();
        self.current_match_index = 0;
    }

    /// Update search query and find all matches
    pub fn search_in_report(&mut self, query: &str) {
        self.search_query = query.to_lowercase();
        self.search_matches.clear();
        self.current_match_index = 0;

        if self.search_query.is_empty() {
            return;
        }

        // Find all matches (case-insensitive)
        for (line_idx, line) in self.current_report_content.iter().enumerate() {
            let line_lower = line.to_lowercase();
            let mut start = 0;

            while let Some(pos) = line_lower[start..].find(&self.search_query) {
                let actual_pos = start + pos;
                self.search_matches.push((
                    line_idx,
                    actual_pos,
                    actual_pos + self.search_query.len(),
                ));
                start = actual_pos + 1;
            }
        }

        // Scroll to first match if any
        if !self.search_matches.is_empty() {
            self.scroll_to_current_match(30); // TODO: Get actual visible lines
        }
    }

    /// Navigate to next search match
    pub fn next_search_match(&mut self, visible_lines: usize) {
        if self.search_matches.is_empty() {
            return;
        }

        self.current_match_index = (self.current_match_index + 1) % self.search_matches.len();
        self.scroll_to_current_match(visible_lines);
    }

    /// Navigate to previous search match
    pub fn previous_search_match(&mut self, visible_lines: usize) {
        if self.search_matches.is_empty() {
            return;
        }

        if self.current_match_index == 0 {
            self.current_match_index = self.search_matches.len() - 1;
        } else {
            self.current_match_index -= 1;
        }
        self.scroll_to_current_match(visible_lines);
    }

    /// Scroll to make current match visible
    fn scroll_to_current_match(&mut self, visible_lines: usize) {
        if self.search_matches.is_empty() {
            return;
        }

        let (line_idx, _, _) = self.search_matches[self.current_match_index];

        // Center the match in the viewport if possible
        let center_offset = visible_lines / 2;
        self.report_scroll_offset = line_idx.saturating_sub(center_offset);
    }

    /// Add character to search query
    pub fn add_search_char(&mut self, c: char) {
        self.search_query.push(c.to_lowercase().next().unwrap_or(c));
        self.search_in_report(&self.search_query.clone());
    }

    /// Remove last character from search query
    pub fn backspace_search(&mut self) {
        self.search_query.pop();
        self.search_in_report(&self.search_query.clone());
    }
}

impl Default for App {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_app_creation() {
        let app = App::new();
        assert_eq!(app.ui_state, UiState::MainScreen);
        assert_eq!(app.output_lines.len(), 0);
        assert!(!app.should_quit);
    }

    #[test]
    fn test_screen_switching() {
        let mut app = App::new();
        assert_eq!(app.ui_state, UiState::MainScreen);

        app.switch_screen(UiState::HelpScreen);
        assert_eq!(app.ui_state, UiState::HelpScreen);

        app.switch_screen(UiState::SettingsScreen);
        assert_eq!(app.ui_state, UiState::SettingsScreen);
    }

    #[test]
    fn test_output_management() {
        let mut app = App::new();

        app.add_output("Line 1".to_string());
        app.add_output("Line 2".to_string());
        assert_eq!(app.output_lines.len(), 2);

        app.clear_output();
        assert_eq!(app.output_lines.len(), 0);
        assert_eq!(app.scroll_offset, 0);
    }

    #[test]
    fn test_scan_state_transitions() {
        let mut app = App::new();

        // Start crash scan
        app.start_crash_scan();
        assert!(app.is_scanning());
        assert!(matches!(app.scan_state, ScanState::CrashScanning { .. }));

        // Complete scan
        let results = ScanResults {
            scanned_count: 10,
            patterns_matched: 5,
            formids_resolved: 20,
            suspects_count: 3,
        };
        app.complete_scan(results);
        assert!(!app.is_scanning());
    }

    #[test]
    fn test_folder_path_updates() {
        let mut app = App::new();

        let staging = PathBuf::from("C:\\MO2\\mods");
        app.set_staging_folder(staging.clone());
        assert_eq!(app.staging_folder, Some(staging.clone()));
        assert_eq!(app.config.paths.mods_folder, Some(staging));

        let custom = PathBuf::from("D:\\CustomLogs");
        app.set_custom_folder(custom.clone());
        assert_eq!(app.custom_folder, Some(custom.clone()));
        assert_eq!(app.config.paths.scan_custom, Some(custom));
    }

    #[test]
    fn test_scroll_operations() {
        let mut app = App::new();

        // Add multiple lines
        for i in 0..20 {
            app.add_output(format!("Line {}", i));
        }

        // Scroll down should be limited by content
        app.scroll_down(5, 10);
        assert!(app.scroll_offset <= 10);

        // Scroll up
        app.scroll_up(3);
        assert!(app.scroll_offset < 10);

        // Scroll up to top
        app.scroll_up(100);
        assert_eq!(app.scroll_offset, 0);
    }
}
