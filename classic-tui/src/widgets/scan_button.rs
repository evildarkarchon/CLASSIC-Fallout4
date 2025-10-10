use ratatui::{
    layout::{Alignment, Rect},
    style::{Color, Style},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

/// Type of scan operation
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ScanType {
    CrashLogs,
    GameFiles,
}

/// State of a scan button
#[derive(Debug, Clone)]
pub enum ButtonState {
    Idle,
    Scanning { progress: f64 },
    Completed,
    Error(String),
}

/// Widget for scan operation buttons
pub struct ScanButton {
    label: String,
    scan_type: ScanType,
    state: ButtonState,
    shortcut: String,
}

impl ScanButton {
    /// Create a new scan button
    pub fn new(label: impl Into<String>, scan_type: ScanType, shortcut: impl Into<String>) -> Self {
        Self {
            label: label.into(),
            scan_type,
            state: ButtonState::Idle,
            shortcut: shortcut.into(),
        }
    }

    /// Get the scan type
    pub fn scan_type(&self) -> ScanType {
        self.scan_type
    }

    /// Start scanning
    pub fn start_scan(&mut self) {
        self.state = ButtonState::Scanning { progress: 0.0 };
    }

    /// Update scan progress (0.0 to 1.0)
    pub fn update_progress(&mut self, progress: f64) {
        if let ButtonState::Scanning { progress: p } = &mut self.state {
            *p = progress.clamp(0.0, 1.0);
        }
    }

    /// Mark scan as completed
    pub fn complete(&mut self) {
        self.state = ButtonState::Completed;
    }

    /// Mark scan as failed with error
    pub fn error(&mut self, message: impl Into<String>) {
        self.state = ButtonState::Error(message.into());
    }

    /// Reset to idle state
    pub fn reset(&mut self) {
        self.state = ButtonState::Idle;
    }

    /// Check if currently scanning
    pub fn is_scanning(&self) -> bool {
        matches!(self.state, ButtonState::Scanning { .. })
    }

    /// Render the scan button widget
    pub fn render(&self, f: &mut Frame, area: Rect) {
        let (text, color) = match &self.state {
            ButtonState::Idle => (format!("[{}] {}", self.shortcut, self.label), Color::Green),
            ButtonState::Scanning { progress } => (
                format!("Scanning... {:.0}%", progress * 100.0),
                Color::Yellow,
            ),
            ButtonState::Completed => ("Completed!".to_string(), Color::Cyan),
            ButtonState::Error(_) => ("Error!".to_string(), Color::Red),
        };

        let widget = Paragraph::new(text).alignment(Alignment::Center).block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(color)),
        );

        f.render_widget(widget, area);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_scan_button_creation() {
        let button = ScanButton::new("Crash Logs", ScanType::CrashLogs, "F5");
        assert_eq!(button.label, "Crash Logs");
        assert_eq!(button.scan_type, ScanType::CrashLogs);
        assert_eq!(button.shortcut, "F5");
        assert!(matches!(button.state, ButtonState::Idle));
    }

    #[test]
    fn test_scan_state_transitions() {
        let mut button = ScanButton::new("Test", ScanType::CrashLogs, "F5");

        // Start scan
        button.start_scan();
        assert!(button.is_scanning());
        assert!(matches!(button.state, ButtonState::Scanning { .. }));

        // Update progress
        button.update_progress(0.5);
        if let ButtonState::Scanning { progress } = button.state {
            assert_eq!(progress, 0.5);
        } else {
            panic!("Expected Scanning state");
        }

        // Complete scan
        button.complete();
        assert!(!button.is_scanning());
        assert!(matches!(button.state, ButtonState::Completed));

        // Reset
        button.reset();
        assert!(matches!(button.state, ButtonState::Idle));
    }

    #[test]
    fn test_error_state() {
        let mut button = ScanButton::new("Test", ScanType::GameFiles, "F6");
        button.error("Test error");

        match &button.state {
            ButtonState::Error(msg) => assert_eq!(msg, "Test error"),
            _ => panic!("Expected Error state"),
        }
    }

    #[test]
    fn test_progress_clamping() {
        let mut button = ScanButton::new("Test", ScanType::CrashLogs, "F5");
        button.start_scan();

        // Test upper bound
        button.update_progress(1.5);
        if let ButtonState::Scanning { progress } = button.state {
            assert_eq!(progress, 1.0);
        }

        // Test lower bound
        button.update_progress(-0.5);
        if let ButtonState::Scanning { progress } = button.state {
            assert_eq!(progress, 0.0);
        }
    }
}
