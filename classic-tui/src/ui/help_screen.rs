//! Help screen rendering for keyboard shortcuts reference.
//!
//! This module provides the help screen UI that displays all available keyboard shortcuts
//! and navigation commands for the CLASSIC TUI application. The screen is accessible via
//! the F1 key from any screen and provides a comprehensive reference for users.
//!
//! # Features
//!
//! - Displays keyboard shortcuts organized by category (Main Screen, Navigation, Folder Paths)
//! - Shows update notification banner when available
//! - Adjusts working area to accommodate notification overlay
//! - Uses consistent color scheme (Cyan headers, Yellow highlights)
//!
//! # Layout
//!
//! The help screen is rendered as a single bordered paragraph containing:
//! - Application title with styling
//! - Categorized keyboard shortcuts with key bindings
//! - Brief descriptions of folder path purposes
//! - Instructions for returning to main screen (ESC key)
//!
//! # Example
//!
//! ```rust,no_run
//! use classic_tui::ui::help_screen::render_help_screen;
//! use classic_tui::app::App;
//! use ratatui::backend::CrosstermBackend;
//! use ratatui::Terminal;
//! use std::io;
//!
//! let mut terminal = Terminal::new(CrosstermBackend::new(io::stdout())).unwrap();
//! let app = App::new();
//!
//! terminal.draw(|f| {
//!     render_help_screen(f, &app);
//! }).unwrap();
//! ```

use crate::app::App;
use ratatui::{
    layout::{Alignment, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

/// Render the help screen with keyboard shortcuts
pub fn render_help_screen(f: &mut Frame, app: &App) {
    let mut working_area = f.area();

    // Render update notification banner if visible (at top)
    if let Some(ref notification) = app.update_notification {
        if notification.is_visible() {
            notification.render(f, working_area);
            // Adjust working area to account for banner height
            working_area = Rect {
                x: working_area.x,
                y: working_area.y + notification.height(),
                width: working_area.width,
                height: working_area.height.saturating_sub(notification.height()),
            };
        }
    }

    let help_text = vec![
        Line::from(""),
        Line::from(vec![Span::styled(
            "CLASSIC - Keyboard Shortcuts",
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        )]),
        Line::from(""),
        Line::from("═══════════════════════════════════════════════════════════"),
        Line::from(""),
        Line::from(vec![Span::styled(
            "Main Screen:",
            Style::default().add_modifier(Modifier::BOLD),
        )]),
        Line::from("  F5 / R       - Start Crash Logs Scan"),
        Line::from("  F6 / G       - Start Game Files Scan"),
        Line::from("  F7 / P       - Toggle Papyrus Monitor"),
        Line::from("  Ctrl+L       - Clear output viewer"),
        Line::from("  Ctrl+O       - Open Settings screen"),
        Line::from("  /            - Search output (not yet implemented)"),
        Line::from("  ↑/↓          - Scroll output viewer"),
        Line::from("  Page Up/Down - Scroll output viewer (page)"),
        Line::from(""),
        Line::from(vec![Span::styled(
            "Navigation:",
            Style::default().add_modifier(Modifier::BOLD),
        )]),
        Line::from("  F1           - Show this help screen"),
        Line::from("  ESC          - Return to previous screen"),
        Line::from("  Q            - Quit application"),
        Line::from("  Tab          - Cycle through interactive elements"),
        Line::from(""),
        Line::from(vec![Span::styled(
            "Folder Paths:",
            Style::default().add_modifier(Modifier::BOLD),
        )]),
        Line::from("  Staging Mods Folder - Location of your mod manager's mods"),
        Line::from("  Custom Scan Folder  - Additional crash logs directory"),
        Line::from(""),
        Line::from("═══════════════════════════════════════════════════════════"),
        Line::from(""),
        Line::from(vec![Span::styled(
            "Press ESC to return to main screen",
            Style::default().fg(Color::Yellow),
        )]),
    ];

    let help_widget = Paragraph::new(help_text).alignment(Alignment::Left).block(
        Block::default()
            .borders(Borders::ALL)
            .title(" Help ")
            .border_style(Style::default().fg(Color::Green)),
    );

    f.render_widget(help_widget, working_area);
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    #[test]
    fn test_render_help_screen() {
        let backend = TestBackend::new(100, 40);
        let mut terminal = Terminal::new(backend).unwrap();

        let app = App::new();

        terminal
            .draw(|f| {
                render_help_screen(f, &app);
            })
            .unwrap();

        // Should not panic
    }
}
