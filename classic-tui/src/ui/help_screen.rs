use crate::app::App;
use ratatui::{
    layout::Alignment,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

/// Render the help screen with keyboard shortcuts
pub fn render_help_screen(f: &mut Frame, _app: &App) {
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

    f.render_widget(help_widget, f.area());
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
