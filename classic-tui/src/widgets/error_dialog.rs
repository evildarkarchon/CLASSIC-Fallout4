///! Error dialog widget for displaying errors with clipboard support.
///!
///! This module provides a TUI error dialog that displays error messages with
///! color-coded severity indicators, scrollable details, and clipboard integration.

use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Paragraph, Wrap},
    Frame,
};

/// Severity level for error dialogs.
///
/// Determines the color coding and visual presentation of the error.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorSeverity {
    /// Critical error (red) - operation failed, user action required
    #[allow(dead_code)]
    Error,
    /// Warning (yellow) - operation completed with issues
    #[allow(dead_code)]
    Warning,
    /// Information (blue) - operation completed successfully with notes
    #[allow(dead_code)]
    Info,
}

impl ErrorSeverity {
    /// Get the display color for this severity level.
    ///
    /// # Returns
    ///
    /// - Error: Red
    /// - Warning: Yellow
    /// - Info: Blue
    pub fn color(&self) -> Color {
        match self {
            Self::Error => Color::Red,
            Self::Warning => Color::Yellow,
            Self::Info => Color::Blue,
        }
    }

    /// Get the symbol/icon for this severity level.
    ///
    /// # Returns
    ///
    /// - Error: "✗"
    /// - Warning: "⚠"
    /// - Info: "ℹ"
    pub fn symbol(&self) -> &'static str {
        match self {
            Self::Error => "✗",
            Self::Warning => "⚠",
            Self::Info => "ℹ",
        }
    }

    /// Get the label text for this severity level.
    pub fn label(&self) -> &'static str {
        match self {
            Self::Error => "ERROR",
            Self::Warning => "WARNING",
            Self::Info => "INFO",
        }
    }
}

/// Error dialog state and content.
///
/// Manages the error dialog's content, scroll position, and visual state.
#[derive(Debug, Clone)]
pub struct ErrorDialog {
    /// Error title (brief description)
    pub title: String,
    /// Primary error message
    pub message: String,
    /// Optional detailed error information (stack trace, context, etc.)
    pub details: Option<String>,
    /// Severity level (affects color and icon)
    pub severity: ErrorSeverity,
    /// Current scroll offset for details (0 = top)
    pub scroll_offset: usize,
    /// Whether the dialog is currently active/visible
    pub active: bool,
}

impl ErrorDialog {
    /// Create a new error dialog.
    ///
    /// # Arguments
    ///
    /// * `title` - Brief error title
    /// * `message` - Primary error message
    /// * `details` - Optional detailed information
    /// * `severity` - Severity level (Error, Warning, or Info)
    ///
    /// # Examples
    ///
    /// ```no_run
    /// use classic_tui::widgets::error_dialog::{ErrorDialog, ErrorSeverity};
    ///
    /// let dialog = ErrorDialog::new(
    ///     "Database Connection Failed",
    ///     "Could not connect to SQLite database",
    ///     Some("Connection timeout after 30 seconds"),
    ///     ErrorSeverity::Error,
    /// );
    /// ```
    pub fn new(
        title: impl Into<String>,
        message: impl Into<String>,
        details: Option<impl Into<String>>,
        severity: ErrorSeverity,
    ) -> Self {
        Self {
            title: title.into(),
            message: message.into(),
            details: details.map(|d| d.into()),
            severity,
            scroll_offset: 0,
            active: false,
        }
    }

    /// Create an error dialog for a standard error.
    ///
    /// This is a convenience constructor for creating error dialogs from
    /// any type that implements `std::error::Error`.
    ///
    /// # Arguments
    ///
    /// * `title` - Brief error title
    /// * `error` - The error to display
    ///
    /// # Examples
    ///
    /// ```no_run
    /// use classic_tui::widgets::error_dialog::ErrorDialog;
    /// use std::io;
    ///
    /// let io_error = io::Error::new(io::ErrorKind::NotFound, "file not found");
    /// let dialog = ErrorDialog::from_error("File Operation Failed", &io_error);
    /// ```
    pub fn from_error(title: impl Into<String>, error: &dyn std::error::Error) -> Self {
        let message = error.to_string();
        let details = format!("{:?}", error);

        Self::new(title, message, Some(details), ErrorSeverity::Error)
    }

    /// Create a warning dialog.
    ///
    /// Convenience constructor for warning-level messages.
    pub fn warning(title: impl Into<String>, message: impl Into<String>) -> Self {
        Self::new(title, message, None::<String>, ErrorSeverity::Warning)
    }

    /// Create an info dialog.
    ///
    /// Convenience constructor for informational messages.
    pub fn info(title: impl Into<String>, message: impl Into<String>) -> Self {
        Self::new(title, message, None::<String>, ErrorSeverity::Info)
    }

    /// Activate the dialog (make it visible).
    pub fn activate(&mut self) {
        self.active = true;
        self.scroll_offset = 0; // Reset scroll when showing
    }

    /// Deactivate the dialog (hide it).
    pub fn deactivate(&mut self) {
        self.active = false;
    }

    /// Check if the dialog is active.
    pub fn is_active(&self) -> bool {
        self.active
    }

    /// Scroll the details view up by the specified number of lines.
    ///
    /// # Arguments
    ///
    /// * `lines` - Number of lines to scroll up (clamped to 0)
    pub fn scroll_up(&mut self, lines: usize) {
        self.scroll_offset = self.scroll_offset.saturating_sub(lines);
    }

    /// Scroll the details view down by the specified number of lines.
    ///
    /// # Arguments
    ///
    /// * `lines` - Number of lines to scroll down
    /// * `max_lines` - Maximum number of detail lines (to prevent scrolling past end)
    pub fn scroll_down(&mut self, lines: usize, max_lines: usize) {
        let new_offset = self.scroll_offset + lines;
        if new_offset < max_lines {
            self.scroll_offset = new_offset;
        }
    }

    /// Get the full error text formatted for clipboard copying.
    ///
    /// Returns a formatted string containing title, message, and details
    /// that can be copied to clipboard for bug reports.
    ///
    /// # Returns
    ///
    /// Formatted error text ready for clipboard
    pub fn get_clipboard_text(&self) -> String {
        let timestamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S");

        if let Some(details) = &self.details {
            format!(
                "=== CLASSIC TUI {} ===\n\
                 Timestamp: {}\n\
                 Title: {}\n\
                 Message: {}\n\n\
                 Details:\n{}\n\
                 ================================",
                self.severity.label(),
                timestamp,
                self.title,
                self.message,
                details
            )
        } else {
            format!(
                "=== CLASSIC TUI {} ===\n\
                 Timestamp: {}\n\
                 Title: {}\n\
                 Message: {}\n\
                 ================================",
                self.severity.label(),
                timestamp,
                self.title,
                self.message
            )
        }
    }

    /// Render the error dialog as an overlay.
    ///
    /// This should be called last in the render pipeline to draw the dialog
    /// on top of other UI elements.
    ///
    /// # Arguments
    ///
    /// * `f` - Terminal frame to draw on
    /// * `area` - Full screen area (dialog will be centered)
    pub fn render(&self, f: &mut Frame, area: Rect) {
        if !self.active {
            return;
        }

        // Calculate centered dialog size (80% width, 60% height)
        let dialog_width = (area.width as f32 * 0.8) as u16;
        let dialog_height = (area.height as f32 * 0.6) as u16;
        let dialog_x = (area.width.saturating_sub(dialog_width)) / 2;
        let dialog_y = (area.height.saturating_sub(dialog_height)) / 2;

        let dialog_area = Rect {
            x: area.x + dialog_x,
            y: area.y + dialog_y,
            width: dialog_width,
            height: dialog_height,
        };

        // Clear the background
        f.render_widget(Clear, dialog_area);

        // Create the dialog block with color-coded border
        let severity_color = self.severity.color();
        let border_style = Style::default()
            .fg(severity_color)
            .add_modifier(Modifier::BOLD);

        let block = Block::default()
            .borders(Borders::ALL)
            .border_style(border_style)
            .title(format!(" {} {} ", self.severity.symbol(), self.severity.label()))
            .title_alignment(Alignment::Center);

        // Split dialog into sections
        let inner = block.inner(dialog_area);
        f.render_widget(block, dialog_area);

        let sections = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3),  // Title
                Constraint::Length(3),  // Message
                Constraint::Min(5),     // Details (scrollable)
                Constraint::Length(2),  // Help text
            ])
            .split(inner);

        // Render title
        let title_text = Line::from(vec![
            Span::styled(
                &self.title,
                Style::default()
                    .fg(severity_color)
                    .add_modifier(Modifier::BOLD),
            ),
        ]);
        let title_para = Paragraph::new(title_text)
            .alignment(Alignment::Center)
            .wrap(Wrap { trim: true });
        f.render_widget(title_para, sections[0]);

        // Render message
        let message_para = Paragraph::new(self.message.as_str())
            .alignment(Alignment::Left)
            .wrap(Wrap { trim: true });
        f.render_widget(message_para, sections[1]);

        // Render details (if present)
        if let Some(details) = &self.details {
            let details_block = Block::default()
                .borders(Borders::TOP)
                .title(" Details ")
                .border_style(Style::default().fg(Color::Gray));

            let details_inner = details_block.inner(sections[2]);
            f.render_widget(details_block, sections[2]);

            // Split details into lines for scrolling
            let detail_lines: Vec<Line> = details
                .lines()
                .skip(self.scroll_offset)
                .map(|line| Line::from(line.to_string()))
                .collect();

            let details_para = Paragraph::new(detail_lines)
                .alignment(Alignment::Left)
                .wrap(Wrap { trim: false });
            f.render_widget(details_para, details_inner);
        }

        // Render help text
        let help_text = Line::from(vec![
            Span::styled("C", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::raw(" Copy to Clipboard   "),
            Span::styled("ESC", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::raw(" Close   "),
            Span::styled("↑↓", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::raw(" Scroll Details"),
        ]);
        let help_para = Paragraph::new(help_text)
            .alignment(Alignment::Center);
        f.render_widget(help_para, sections[3]);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_severity_color() {
        assert_eq!(ErrorSeverity::Error.color(), Color::Red);
        assert_eq!(ErrorSeverity::Warning.color(), Color::Yellow);
        assert_eq!(ErrorSeverity::Info.color(), Color::Blue);
    }

    #[test]
    fn test_error_severity_symbol() {
        assert_eq!(ErrorSeverity::Error.symbol(), "✗");
        assert_eq!(ErrorSeverity::Warning.symbol(), "⚠");
        assert_eq!(ErrorSeverity::Info.symbol(), "ℹ");
    }

    #[test]
    fn test_error_dialog_new() {
        let dialog = ErrorDialog::new(
            "Test Error",
            "This is a test message",
            Some("Detailed information"),
            ErrorSeverity::Error,
        );

        assert_eq!(dialog.title, "Test Error");
        assert_eq!(dialog.message, "This is a test message");
        assert_eq!(dialog.details, Some("Detailed information".to_string()));
        assert_eq!(dialog.severity, ErrorSeverity::Error);
        assert_eq!(dialog.scroll_offset, 0);
        assert!(!dialog.active);
    }

    #[test]
    fn test_error_dialog_activate_deactivate() {
        let mut dialog = ErrorDialog::new(
            "Test",
            "Message",
            None::<String>,
            ErrorSeverity::Info,
        );

        assert!(!dialog.is_active());

        dialog.activate();
        assert!(dialog.is_active());

        dialog.deactivate();
        assert!(!dialog.is_active());
    }

    #[test]
    fn test_error_dialog_scroll() {
        let mut dialog = ErrorDialog::new(
            "Test",
            "Message",
            Some("Line 1\nLine 2\nLine 3\nLine 4"),
            ErrorSeverity::Error,
        );

        assert_eq!(dialog.scroll_offset, 0);

        dialog.scroll_down(2, 10);
        assert_eq!(dialog.scroll_offset, 2);

        dialog.scroll_up(1);
        assert_eq!(dialog.scroll_offset, 1);

        dialog.scroll_up(10); // Should clamp to 0
        assert_eq!(dialog.scroll_offset, 0);
    }

    #[test]
    fn test_error_dialog_from_error() {
        let io_error = std::io::Error::new(std::io::ErrorKind::NotFound, "file not found");
        let dialog = ErrorDialog::from_error("IO Error", &io_error);

        assert_eq!(dialog.title, "IO Error");
        assert_eq!(dialog.severity, ErrorSeverity::Error);
        assert!(dialog.message.contains("file not found"));
        assert!(dialog.details.is_some());
    }

    #[test]
    fn test_convenience_constructors() {
        let warning = ErrorDialog::warning("Warning Title", "Warning message");
        assert_eq!(warning.severity, ErrorSeverity::Warning);
        assert!(warning.details.is_none());

        let info = ErrorDialog::info("Info Title", "Info message");
        assert_eq!(info.severity, ErrorSeverity::Info);
        assert!(info.details.is_none());
    }

    #[test]
    fn test_get_clipboard_text() {
        let dialog = ErrorDialog::new(
            "Test Error",
            "Error message",
            Some("Stack trace here"),
            ErrorSeverity::Error,
        );

        let text = dialog.get_clipboard_text();
        assert!(text.contains("Test Error"));
        assert!(text.contains("Error message"));
        assert!(text.contains("Stack trace here"));
        assert!(text.contains("ERROR"));
    }
}
