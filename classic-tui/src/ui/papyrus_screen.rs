use crate::app::App;
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

/// Statistics from Papyrus log monitoring
#[derive(Debug, Clone, Default)]
pub struct PapyrusStats {
    /// Number of stack dumps found
    pub dumps: usize,
    /// Number of stack traces found
    pub stacks: usize,
    /// Number of warnings found
    pub warnings: usize,
    /// Number of errors found
    pub errors: usize,
    /// Error/warning ratio
    pub ratio: f64,
    /// Last update timestamp
    pub last_update: String,
}

impl PapyrusStats {
    /// Create new empty stats
    pub fn new() -> Self {
        Self::default()
    }

    /// Get status color based on severity
    pub fn get_status_color(&self) -> Color {
        if self.errors > 10 {
            Color::Red
        } else if self.warnings > 20 {
            Color::Yellow
        } else {
            Color::Green
        }
    }

    /// Get status symbol
    pub fn get_status_symbol(&self) -> &'static str {
        if self.errors > 10 {
            "[X]"
        } else if self.warnings > 20 {
            "[!]"
        } else if self.dumps > 0 {
            "[v]"
        } else {
            "[OK]"
        }
    }
}

/// Render the Papyrus monitoring screen
pub fn render_papyrus_screen(f: &mut Frame, app: &App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),  // Header
            Constraint::Length(10), // Stats display
            Constraint::Min(10),    // Log output
            Constraint::Length(3),  // Status bar
        ])
        .split(f.area());

    // Header
    render_header(f, chunks[0], app);

    // Stats display
    render_stats(f, chunks[1], app);

    // Log output
    render_log_output(f, chunks[2], app);

    // Status bar with controls
    render_status_bar(f, chunks[3], app);
}

fn render_header(f: &mut Frame, area: Rect, app: &App) {
    let monitoring_status = match app.scan_state {
        crate::app::ScanState::PapyrusMonitoring => "ACTIVE",
        _ => "STOPPED",
    };

    let status_color = match app.scan_state {
        crate::app::ScanState::PapyrusMonitoring => Color::Green,
        _ => Color::Red,
    };

    let header_text = vec![Line::from(vec![
        Span::styled(
            "Papyrus Monitor - ",
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(
            monitoring_status,
            Style::default()
                .fg(status_color)
                .add_modifier(Modifier::BOLD),
        ),
    ])];

    let header = Paragraph::new(header_text)
        .alignment(Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::Cyan)),
        );

    f.render_widget(header, area);
}

fn render_stats(f: &mut Frame, area: Rect, app: &App) {
    // For now, show placeholder stats
    // In a full implementation, these would come from app.papyrus_stats
    let stats = PapyrusStats::new();

    let stats_text = vec![
        Line::from(""),
        Line::from(vec![
            Span::styled("Status: ", Style::default().add_modifier(Modifier::BOLD)),
            Span::styled(
                stats.get_status_symbol(),
                Style::default().fg(stats.get_status_color()),
            ),
        ]),
        Line::from(""),
        Line::from(format!("  Stack Dumps:  {}", stats.dumps)),
        Line::from(format!("  Stack Traces: {}", stats.stacks)),
        Line::from(format!("  Warnings:     {}", stats.warnings)),
        Line::from(format!("  Errors:       {}", stats.errors)),
        Line::from(format!("  Ratio:        {:.2}", stats.ratio)),
    ];

    let stats_widget = Paragraph::new(stats_text).alignment(Alignment::Left).block(
        Block::default()
            .borders(Borders::ALL)
            .title(" Statistics ")
            .border_style(Style::default().fg(Color::White)),
    );

    f.render_widget(stats_widget, area);
}

fn render_log_output(f: &mut Frame, area: Rect, app: &App) {
    // Display output lines from app
    let output_text: Vec<Line> = if app.output_lines.is_empty() {
        vec![
            Line::from(""),
            Line::from(Span::styled(
                "Papyrus log monitoring is not yet fully implemented.",
                Style::default().fg(Color::Yellow),
            )),
            Line::from(""),
            Line::from("This will monitor Papyrus.0.log in real-time for:"),
            Line::from("  • Stack dumps"),
            Line::from("  • Error messages"),
            Line::from("  • Warning messages"),
            Line::from("  • Performance issues"),
            Line::from(""),
            Line::from(Span::styled(
                "Press F7 or P to toggle monitoring",
                Style::default().fg(Color::Cyan),
            )),
        ]
    } else {
        app.output_lines
            .iter()
            .skip(app.scroll_offset)
            .take(area.height as usize - 2) // Account for borders
            .map(|line| Line::from(line.clone()))
            .collect()
    };

    let output_widget = Paragraph::new(output_text).block(
        Block::default()
            .borders(Borders::ALL)
            .title(" Log Output ")
            .border_style(Style::default().fg(Color::Green)),
    );

    f.render_widget(output_widget, area);
}

fn render_status_bar(f: &mut Frame, area: Rect, _app: &App) {
    let instructions = vec![Line::from(vec![
        Span::styled("F7/P", Style::default().fg(Color::Yellow)),
        Span::raw(" Start/Stop | "),
        Span::styled("C", Style::default().fg(Color::Yellow)),
        Span::raw(" Clear | "),
        Span::styled("ESC", Style::default().fg(Color::Yellow)),
        Span::raw(" Back | "),
        Span::styled("Q", Style::default().fg(Color::Yellow)),
        Span::raw(" Quit"),
    ])];

    let status_bar = Paragraph::new(instructions)
        .alignment(Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::DarkGray)),
        );

    f.render_widget(status_bar, area);
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    #[test]
    fn test_papyrus_stats_creation() {
        let stats = PapyrusStats::new();
        assert_eq!(stats.dumps, 0);
        assert_eq!(stats.errors, 0);
        assert_eq!(stats.warnings, 0);
    }

    #[test]
    fn test_papyrus_stats_status_color() {
        let mut stats = PapyrusStats::new();

        // Green for normal
        assert_eq!(stats.get_status_color(), Color::Green);

        // Yellow for warnings
        stats.warnings = 25;
        assert_eq!(stats.get_status_color(), Color::Yellow);

        // Red for errors
        stats.errors = 15;
        assert_eq!(stats.get_status_color(), Color::Red);
    }

    #[test]
    fn test_papyrus_stats_status_symbol() {
        let mut stats = PapyrusStats::new();

        // OK for normal
        assert_eq!(stats.get_status_symbol(), "[OK]");

        // Check for dumps
        stats.dumps = 1;
        assert_eq!(stats.get_status_symbol(), "[v]");

        // Warning symbol
        stats.warnings = 25;
        assert_eq!(stats.get_status_symbol(), "[!]");

        // Error symbol (highest priority)
        stats.errors = 15;
        assert_eq!(stats.get_status_symbol(), "[X]");
    }

    #[test]
    fn test_render_papyrus_screen() {
        let backend = TestBackend::new(100, 40);
        let mut terminal = Terminal::new(backend).unwrap();

        let app = App::new();

        terminal
            .draw(|f| {
                render_papyrus_screen(f, &app);
            })
            .unwrap();

        // Should not panic
    }
}
