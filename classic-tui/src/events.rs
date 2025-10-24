use crate::app::ScanResults;

/// Messages sent from scan handlers to the UI
#[derive(Debug, Clone)]
pub enum ScanMessage {
    /// Scan progress update (0.0 to 1.0)
    Progress(f64),
    /// Output line to display
    Output(String),
    /// Scan completed successfully with results
    Completed(ScanResults),
    /// Scan failed with error message
    Error(String),
}

/// Messages for UI events
#[derive(Debug, Clone)]
pub enum UiMessage {
    /// Quit the application
    Quit,
    /// Switch to main screen
    ShowMainScreen,
    /// Switch to help screen
    ShowHelpScreen,
    /// Switch to settings screen
    ShowSettingsScreen,
    /// Switch to Papyrus screen
    ShowPapyrusScreen,
    /// Switch to backup operations screen
    ShowBackupScreen,
    /// Switch to results viewer screen
    ShowResultsScreen,
    /// Select next report in results list
    SelectNextReport,
    /// Select previous report in results list
    SelectPreviousReport,
    /// Scroll report viewer up
    ScrollReportUp(usize),
    /// Scroll report viewer down
    ScrollReportDown(usize),
    /// Refresh report file list
    RefreshReports,
    /// Start search mode in report viewer
    StartSearch,
    /// Exit search mode
    ExitSearch,
    /// Add character to search query
    SearchAddChar(char),
    /// Remove last character from search query
    SearchBackspace,
    /// Navigate to next search match
    SearchNextMatch,
    /// Navigate to previous search match
    SearchPreviousMatch,
    /// Start crash log scan
    StartCrashScan,
    /// Start game files scan
    StartGameScan,
    /// Toggle Papyrus monitoring
    TogglePapyrusMonitor,
    /// Clear output viewer
    ClearOutput,
    /// Scroll output up
    ScrollUp(usize),
    /// Scroll output down
    ScrollDown(usize),
    /// Update staging folder path
    UpdateStagingFolder(std::path::PathBuf),
    /// Update custom scan folder path
    UpdateCustomFolder(std::path::PathBuf),
    /// Toggle update check
    ToggleUpdateCheck,
    /// Save settings to disk
    SaveSettings,
    /// Switch to next settings tab
    NextSettingsTab,
    /// Switch to previous settings tab
    PreviousSettingsTab,
    /// Open staging folder picker
    OpenStagingPicker,
    /// Open custom folder picker
    OpenCustomPicker,
    /// Close active folder picker
    CloseFolderPicker,
    /// Select folder from active picker
    SelectFolder,
    /// Navigate folder picker up
    FolderPickerUp,
    /// Navigate folder picker down
    FolderPickerDown,
    /// Enter selected directory in folder picker
    FolderPickerEnter,
    /// Go to parent directory in folder picker
    FolderPickerParent,
    /// Create backup of specified type (XSE=0, ReShade=1, Vulkan=2, ENB=3)
    CreateBackup(usize),
    /// Restore backup of specified type
    RestoreBackup(usize),
    /// Remove backup of specified type
    RemoveBackup(usize),
    /// Refresh backup status
    RefreshBackupStatus,
}

impl ScanMessage {
    /// Create a progress message
    pub fn progress(value: f64) -> Self {
        Self::Progress(value.clamp(0.0, 1.0))
    }

    /// Create an output message
    pub fn output(line: impl Into<String>) -> Self {
        Self::Output(line.into())
    }

    /// Create a completed message with results
    pub fn completed(results: ScanResults) -> Self {
        Self::Completed(results)
    }

    /// Create an error message
    pub fn error(msg: impl Into<String>) -> Self {
        Self::Error(msg.into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_scan_message_progress_clamping() {
        let msg = ScanMessage::progress(1.5);
        match msg {
            ScanMessage::Progress(p) => assert_eq!(p, 1.0),
            _ => panic!("Expected Progress variant"),
        }

        let msg = ScanMessage::progress(-0.5);
        match msg {
            ScanMessage::Progress(p) => assert_eq!(p, 0.0),
            _ => panic!("Expected Progress variant"),
        }
    }

    #[test]
    fn test_scan_message_constructors() {
        let output = ScanMessage::output("Test output");
        assert!(matches!(output, ScanMessage::Output(_)));

        let error = ScanMessage::error("Test error");
        assert!(matches!(error, ScanMessage::Error(_)));

        let results = ScanResults {
            scanned_count: 10,
            patterns_matched: 5,
            formids_resolved: 20,
            suspects_count: 3,
        };
        let completed = ScanMessage::completed(results);
        assert!(matches!(completed, ScanMessage::Completed(_)));
    }
}
