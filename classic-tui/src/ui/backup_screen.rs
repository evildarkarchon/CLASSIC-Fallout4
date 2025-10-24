use crate::app::App;
use classic_file_io_core::BackupType;
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

/// Render the backup operations screen
pub fn render_backup_screen(f: &mut Frame, app: &App) {
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

    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),  // Header
            Constraint::Min(20),    // Backup sections
            Constraint::Length(3),  // Status bar
        ])
        .split(working_area);

    // Header
    render_header(f, chunks[0]);

    // Backup sections
    render_backup_sections(f, chunks[1], app);

    // Status bar
    render_status_bar(f, chunks[2]);
}

fn render_header(f: &mut Frame, area: Rect) {
    let header_text = vec![Line::from(vec![Span::styled(
        "Backup Operations",
        Style::default()
            .fg(Color::Cyan)
            .add_modifier(Modifier::BOLD),
    )])];

    let header = Paragraph::new(header_text)
        .alignment(Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::Cyan)),
        );

    f.render_widget(header, area);
}

fn render_backup_sections(f: &mut Frame, area: Rect, app: &App) {
    // Split into 4 sections (one for each backup type)
    let sections = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage(25), // XSE
            Constraint::Percentage(25), // ReShade
            Constraint::Percentage(25), // Vulkan
            Constraint::Percentage(25), // ENB
        ])
        .split(area);

    // Render each backup type section with real status
    render_backup_type_section(
        f,
        sections[0],
        "XSE (F4SE/SKSE)",
        app.backup_exists(BackupType::XSE),
    );
    render_backup_type_section(f, sections[1], "ReShade", app.backup_exists(BackupType::ReShade));
    render_backup_type_section(f, sections[2], "Vulkan", app.backup_exists(BackupType::Vulkan));
    render_backup_type_section(f, sections[3], "ENB", app.backup_exists(BackupType::ENB));
}

fn render_backup_type_section(f: &mut Frame, area: Rect, title: &str, backup_exists: bool) {
    // Split into 3 columns for buttons
    let columns = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(33), // Backup button
            Constraint::Percentage(33), // Restore button
            Constraint::Percentage(34), // Remove button
        ])
        .split(area);

    // Status indicator
    let status_symbol = if backup_exists { "[✓]" } else { "[ ]" };
    let status_color = if backup_exists {
        Color::Green
    } else {
        Color::DarkGray
    };

    // Backup button
    render_button(
        f,
        columns[0],
        &format!("{} {} - Backup", status_symbol, title),
        Color::Blue,
        status_color,
    );

    // Restore button (enabled only if backup exists)
    let restore_color = if backup_exists {
        Color::Yellow
    } else {
        Color::DarkGray
    };
    render_button(f, columns[1], "Restore", restore_color, status_color);

    // Remove button (enabled only if backup exists)
    let remove_color = if backup_exists {
        Color::Red
    } else {
        Color::DarkGray
    };
    render_button(f, columns[2], "Remove", remove_color, status_color);
}

fn render_button(f: &mut Frame, area: Rect, text: &str, fg_color: Color, border_color: Color) {
    let button_text = vec![Line::from(vec![Span::styled(
        text,
        Style::default()
            .fg(fg_color)
            .add_modifier(Modifier::BOLD),
    )])];

    let button = Paragraph::new(button_text)
        .alignment(Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color)),
        );

    f.render_widget(button, area);
}

fn render_status_bar(f: &mut Frame, area: Rect) {
    let instructions = vec![Line::from(vec![
        Span::styled("1-4", Style::default().fg(Color::Yellow)),
        Span::raw(" Backup | "),
        Span::styled("5-8", Style::default().fg(Color::Yellow)),
        Span::raw(" Restore | "),
        Span::styled("9-0,-,=", Style::default().fg(Color::Yellow)),
        Span::raw(" Remove | "),
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
    fn test_render_backup_screen() {
        let backend = TestBackend::new(100, 30);
        let mut terminal = Terminal::new(backend).unwrap();

        let app = App::new();

        terminal
            .draw(|f| {
                render_backup_screen(f, &app);
            })
            .unwrap();

        // Should not panic - rendering should work
    }
}
