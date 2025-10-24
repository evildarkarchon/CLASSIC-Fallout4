use crate::app::{App, ScanState};
use crate::ui::layout::TuiLayout;
use crate::widgets::FolderPicker;
use ratatui::{
    layout::{Alignment, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Paragraph, Wrap},
    Frame,
};

/// Render the main screen
pub fn render_main_screen(f: &mut Frame, app: &mut App) {
    let (header_area, folder_area, button_area, output_area, status_area) =
        TuiLayout::main_screen(f.area());

    render_header(f, header_area);
    render_folder_section(f, folder_area, app);
    render_button_section(f, button_area, app);
    render_output_viewer(f, output_area, app);
    render_status_bar(f, status_area, app);

    // Render folder picker overlay if active
    if let Some(ref mut picker) = app.staging_picker {
        if picker.is_active() {
            render_folder_picker_overlay(f, picker, "Select Staging Mods Folder");
        }
    }
    if let Some(ref mut picker) = app.custom_picker {
        if picker.is_active() {
            render_folder_picker_overlay(f, picker, "Select Custom Scan Folder");
        }
    }
}

/// Render the header with title
fn render_header(f: &mut Frame, area: Rect) {
    let title = vec![
        Line::from(vec![
            Span::styled(
                "CLASSIC",
                Style::default()
                    .fg(Color::Cyan)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::raw(" - Crash Log Auto Scanner & Setup Integrity Checker"),
        ]),
        Line::from("Terminal User Interface"),
    ];

    let header = Paragraph::new(title)
        .alignment(Alignment::Center)
        .block(Block::default().borders(Borders::ALL));

    f.render_widget(header, area);
}

/// Render the folder selection section
fn render_folder_section(f: &mut Frame, area: Rect, app: &App) {
    let (staging_area, custom_area) = TuiLayout::folder_section(area);

    // Staging mods folder
    let staging_path = app
        .staging_folder
        .as_ref()
        .map(|p| p.display().to_string())
        .unwrap_or_else(|| "[Not Set]".to_string());

    let staging_widget = Paragraph::new(vec![
        Line::from("STAGING MODS FOLDER"),
        Line::from(staging_path),
    ])
    .block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Blue)),
    );

    f.render_widget(staging_widget, staging_area);

    // Custom scan folder
    let custom_path = app
        .custom_folder
        .as_ref()
        .map(|p| p.display().to_string())
        .unwrap_or_else(|| "[Not Set]".to_string());

    let custom_widget = Paragraph::new(vec![
        Line::from("CUSTOM SCAN FOLDER"),
        Line::from(custom_path),
    ])
    .block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Blue)),
    );

    f.render_widget(custom_widget, custom_area);
}

/// Render the button section with scan buttons and options
fn render_button_section(f: &mut Frame, area: Rect, app: &App) {
    let (crash_area, game_area, papyrus_area, update_area) = TuiLayout::button_row(area);

    // Crash Logs Scan button
    let crash_style = match &app.scan_state {
        ScanState::CrashScanning { .. } => Style::default().fg(Color::Yellow),
        _ => Style::default().fg(Color::Green),
    };

    let crash_text = match &app.scan_state {
        ScanState::CrashScanning { progress } => {
            format!("Scanning... {:.0}%", progress * 100.0)
        }
        _ => "[F5] Crash Logs Scan".to_string(),
    };

    let crash_button = Paragraph::new(crash_text)
        .alignment(Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(crash_style),
        );

    f.render_widget(crash_button, crash_area);

    // Game Files Scan button
    let game_style = match &app.scan_state {
        ScanState::GameScanning { .. } => Style::default().fg(Color::Yellow),
        _ => Style::default().fg(Color::Green),
    };

    let game_text = match &app.scan_state {
        ScanState::GameScanning { progress } => {
            format!("Scanning... {:.0}%", progress * 100.0)
        }
        _ => "[F6] Game Files Scan".to_string(),
    };

    let game_button = Paragraph::new(game_text)
        .alignment(Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(game_style),
        );

    f.render_widget(game_button, game_area);

    // Papyrus Monitor button
    let papyrus_style = match &app.scan_state {
        ScanState::PapyrusMonitoring => Style::default().fg(Color::Yellow),
        _ => Style::default().fg(Color::Cyan),
    };

    let papyrus_text = match &app.scan_state {
        ScanState::PapyrusMonitoring => "[F7] Monitoring...".to_string(),
        _ => "[F7] Papyrus Monitor".to_string(),
    };

    let papyrus_button = Paragraph::new(papyrus_text)
        .alignment(Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(papyrus_style),
        );

    f.render_widget(papyrus_button, papyrus_area);

    // Update check toggle
    let update_symbol = if app.check_updates { "[X]" } else { "[ ]" };
    let update_text = format!("{} Check for Updates", update_symbol);

    let update_widget = Paragraph::new(update_text)
        .alignment(Alignment::Center)
        .block(Block::default().borders(Borders::ALL));

    f.render_widget(update_widget, update_area);
}

/// Render the output viewer with scrollable content
fn render_output_viewer(f: &mut Frame, area: Rect, app: &App) {
    // Calculate visible lines
    let content_height = area.height.saturating_sub(2) as usize; // Account for borders
    let total_lines = app.output_lines.len();

    // Determine which lines to display
    let start_line = app.scroll_offset;
    let end_line = (start_line + content_height).min(total_lines);

    let visible_lines: Vec<Line> = if total_lines == 0 {
        vec![
            Line::from(""),
            Line::from("Waiting for scan..."),
            Line::from(""),
            Line::from(Span::styled(
                "(Press F5 for Crash Scan, F6 for Game Scan, / to search)",
                Style::default().fg(Color::DarkGray),
            )),
        ]
    } else {
        app.output_lines[start_line..end_line]
            .iter()
            .map(|s| Line::from(s.as_str()))
            .collect()
    };

    let title = if total_lines > 0 {
        format!(
            " OUTPUT VIEWER (Lines {}-{} of {}) ",
            start_line + 1,
            end_line,
            total_lines
        )
    } else {
        " OUTPUT VIEWER ".to_string()
    };

    let output_widget = Paragraph::new(visible_lines)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(title)
                .border_style(Style::default().fg(Color::White)),
        )
        .wrap(Wrap { trim: false });

    f.render_widget(output_widget, area);
}

/// Render the status bar with key hints
fn render_status_bar(f: &mut Frame, area: Rect, app: &App) {
    // If folder picker is active, show picker-specific hints
    let key_hints = if app.is_folder_picker_active() {
        " ↑↓ Navigate | Enter Open Dir | Space/Shift+Enter Select | Backspace Parent | ESC Cancel "
    } else {
        match app.ui_state {
            crate::app::UiState::MainScreen => {
                " F1 Help | F2 Staging | F3 Custom | F5 Crash | F6 Game | F7 Papyrus | F8 Backup | F9 Results | Q Quit "
            }
            crate::app::UiState::HelpScreen => " ESC Back | Q Quit ",
            crate::app::UiState::SettingsScreen => " ESC Back | Tab/Shift+Tab Tabs | ↑↓ Navigate | Space/Enter Toggle | S Save | Q Quit ",
            crate::app::UiState::PapyrusScreen => " ESC Back | F7 Stop | Q Quit ",
            crate::app::UiState::BackupScreen => " ESC Back | 1-4 Backup | 5-8 Restore | Q Quit ",
            crate::app::UiState::ResultsScreen => " ESC Back | ↑↓ Select | PgUp/PgDn Scroll | / Search | n/N Navigate | Q Quit ",
        }
    };

    let status_text = if app.is_scanning() {
        let progress_text = match &app.scan_state {
            ScanState::CrashScanning { progress } | ScanState::GameScanning { progress } => {
                format!(" Scanning... {:.0}% ", progress * 100.0)
            }
            _ => String::new(),
        };
        format!("{} |{}", key_hints, progress_text)
    } else {
        key_hints.to_string()
    };

    let status_widget = Paragraph::new(status_text)
        .style(Style::default().bg(Color::DarkGray).fg(Color::White))
        .alignment(Alignment::Left);

    f.render_widget(status_widget, area);
}

/// Render folder picker as a centered overlay
fn render_folder_picker_overlay(
    f: &mut Frame,
    picker: &mut crate::widgets::FolderPickerState,
    title: &str,
) {
    // Calculate centered area (80% width, 70% height)
    let area = f.area();
    let popup_width = (area.width * 80) / 100;
    let popup_height = (area.height * 70) / 100;

    let popup_area = Rect {
        x: (area.width - popup_width) / 2,
        y: (area.height - popup_height) / 2,
        width: popup_width,
        height: popup_height,
    };

    // Clear the area behind the popup
    f.render_widget(Clear, popup_area);

    // Render the folder picker
    let picker_widget = FolderPicker::new(title)
        .border_style(Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))
        .selected_style(
            Style::default()
                .fg(Color::Black)
                .bg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        );

    picker_widget.render(f, popup_area, picker);
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    #[test]
    fn test_render_main_screen() {
        let backend = TestBackend::new(100, 40);
        let mut terminal = Terminal::new(backend).unwrap();

        let mut app = App::new();

        terminal
            .draw(|f| {
                render_main_screen(f, &mut app);
            })
            .unwrap();

        // Should not panic
    }

    #[test]
    fn test_output_viewer_empty() {
        let backend = TestBackend::new(80, 20);
        let mut terminal = Terminal::new(backend).unwrap();

        let app = App::new();

        terminal
            .draw(|f| {
                let area = f.area();
                render_output_viewer(f, area, &app);
            })
            .unwrap();

        // Should show "Waiting for scan..." message
    }

    #[test]
    fn test_output_viewer_with_content() {
        let backend = TestBackend::new(80, 20);
        let mut terminal = Terminal::new(backend).unwrap();

        let mut app = App::new();
        app.add_output("Line 1".to_string());
        app.add_output("Line 2".to_string());
        app.add_output("Line 3".to_string());

        terminal
            .draw(|f| {
                let area = f.area();
                render_output_viewer(f, area, &app);
            })
            .unwrap();

        // Should render without panic
    }

    #[test]
    fn test_button_section_scanning_state() {
        let backend = TestBackend::new(100, 10);
        let mut terminal = Terminal::new(backend).unwrap();

        let mut app = App::new();
        app.start_crash_scan();
        app.update_progress(0.5);

        terminal
            .draw(|f| {
                let area = f.area();
                render_button_section(f, area, &app);
            })
            .unwrap();

        // Should show progress indicator
    }
}
