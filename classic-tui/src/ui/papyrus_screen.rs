use crate::app::App;
use classic_scanlog_core::papyrus::PapyrusStats;
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

/// Helper to get status color based on severity level
fn get_status_color(stats: &PapyrusStats) -> Color {
    match stats.severity_level() {
        "Critical" => Color::Red,
        "Warning" => Color::Yellow,
        "OK" => Color::Green,
        _ => Color::White,
    }
}

/// Helper to get status symbol based on severity
fn get_status_symbol(stats: &PapyrusStats) -> &'static str {
    match stats.severity_level() {
        "Critical" => "[X]",
        "Warning" => "[!]",
        _ if stats.dumps > 0 => "[v]",
        _ => "[OK]",
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
    let stats_text = if let Some(ref stats) = app.papyrus_stats {
        // Real statistics from monitoring
        let status_color = get_status_color(stats);
        let status_symbol = get_status_symbol(stats);
        let severity = stats.severity_level();
        let error_warning_ratio = stats.error_to_warning_ratio();
        let dumps_stacks_ratio = stats.dumps_to_stacks_ratio();

        vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("Status: ", Style::default().add_modifier(Modifier::BOLD)),
                Span::styled(status_symbol, Style::default().fg(status_color)),
                Span::raw(" "),
                Span::styled(
                    severity,
                    Style::default()
                        .fg(status_color)
                        .add_modifier(Modifier::BOLD),
                ),
            ]),
            Line::from(""),
            Line::from(format!("  Stack Dumps:  {}", stats.dumps)),
            Line::from(format!("  Stack Traces: {}", stats.stacks)),
            Line::from(format!("  Warnings:     {}", stats.warnings)),
            Line::from(format!("  Errors:       {}", stats.errors)),
            Line::from(""),
            Line::from(format!(
                "  Error/Warning Ratio:  {:.2}",
                error_warning_ratio
            )),
            Line::from(format!(
                "  Dumps/Stacks Ratio:   {:.2}",
                dumps_stacks_ratio
            )),
            Line::from(format!("  Lines Processed:      {}", stats.lines_processed)),
        ]
    } else {
        // No stats yet - monitoring not started
        vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("Status: ", Style::default().add_modifier(Modifier::BOLD)),
                Span::styled("[--]", Style::default().fg(Color::DarkGray)),
                Span::raw(" "),
                Span::styled(
                    "Not Started",
                    Style::default()
                        .fg(Color::DarkGray)
                        .add_modifier(Modifier::BOLD),
                ),
            ]),
            Line::from(""),
            Line::from(Span::styled(
                "  Press F7 or P to start monitoring",
                Style::default().fg(Color::Cyan),
            )),
        ]
    };

    let stats_widget = Paragraph::new(stats_text).alignment(Alignment::Left).block(
        Block::default()
            .borders(Borders::ALL)
            .title(" Statistics ")
            .border_style(Style::default().fg(Color::White)),
    );

    f.render_widget(stats_widget, area);
}

fn render_log_output(f: &mut Frame, area: Rect, app: &App) {
    // Display Papyrus log lines if monitoring is active
    let output_text: Vec<Line> = if !app.papyrus_log_lines.is_empty() {
        // Show real log lines from Papyrus monitoring
        app.papyrus_log_lines
            .iter()
            .rev() // Show newest first
            .take(area.height as usize - 2) // Account for borders
            .rev() // Reverse back to chronological order
            .map(|line| {
                // Color-code based on content
                if line.contains(" error: ") {
                    Line::from(Span::styled(line.clone(), Style::default().fg(Color::Red)))
                } else if line.contains(" warning: ") {
                    Line::from(Span::styled(
                        line.clone(),
                        Style::default().fg(Color::Yellow),
                    ))
                } else if line.contains("Dumping Stacks") || line.contains("Dumping Stack") {
                    Line::from(Span::styled(
                        line.clone(),
                        Style::default().fg(Color::Magenta),
                    ))
                } else {
                    Line::from(line.clone())
                }
            })
            .collect()
    } else if matches!(app.scan_state, crate::app::ScanState::PapyrusMonitoring) {
        // Monitoring is active but no lines yet
        vec![
            Line::from(""),
            Line::from(Span::styled(
                "Monitoring active - waiting for new log activity...",
                Style::default().fg(Color::Cyan),
            )),
            Line::from(""),
            Line::from("Log lines will appear here in real-time as they are written."),
        ]
    } else {
        // Not monitoring yet
        vec![
            Line::from(""),
            Line::from(Span::styled(
                "Papyrus monitoring monitors Papyrus.0.log in real-time.",
                Style::default().fg(Color::Yellow),
            )),
            Line::from(""),
            Line::from("It tracks:"),
            Line::from("  • Stack dumps and traces"),
            Line::from("  • Error messages"),
            Line::from("  • Warning messages"),
            Line::from("  • Error/warning severity ratios"),
            Line::from(""),
            Line::from(Span::styled(
                "Press F7 or P to start monitoring",
                Style::default().fg(Color::Cyan),
            )),
        ]
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
    fn test_render_papyrus_screen() {
        let backend = TestBackend::new(100, 40);
        let mut terminal = Terminal::new(backend).unwrap();

        let app = App::new();

        terminal
            .draw(|f| {
                render_papyrus_screen(f, &app);
            })
            .unwrap();

        // Should not panic - rendering should work without stats
    }

    #[test]
    fn test_render_with_stats() {
        let backend = TestBackend::new(100, 40);
        let mut terminal = Terminal::new(backend).unwrap();

        let mut app = App::new();
        // Add some stats
        let stats = PapyrusStats {
            dumps: 5,
            stacks: 10,
            warnings: 3,
            errors: 1,
            last_modified: None,
            lines_processed: 100,
        };
        app.update_papyrus_stats(stats);
        app.add_papyrus_lines(vec!["Test line 1".to_string(), "Test line 2".to_string()]);

        terminal
            .draw(|f| {
                render_papyrus_screen(f, &app);
            })
            .unwrap();

        // Should render with stats
    }
}
