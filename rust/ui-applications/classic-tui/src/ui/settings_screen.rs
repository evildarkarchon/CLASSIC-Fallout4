use crate::app::App;
use ratatui::{
    Frame,
    layout::{Alignment, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
};

/// Render the settings screen
#[allow(dead_code)]
pub fn render_settings_screen(f: &mut Frame, app: &App) {
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

    let settings_text = vec![
        Line::from(""),
        Line::from(vec![Span::styled(
            "CLASSIC - Settings",
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        )]),
        Line::from(""),
        Line::from("═══════════════════════════════════════════════════════════"),
        Line::from(""),
        Line::from(vec![Span::styled(
            "Scan Options:",
            Style::default().add_modifier(Modifier::BOLD),
        )]),
        Line::from(format!(
            "  FCX Mode:              {}",
            if app.config.fcx_mode {
                "Enabled"
            } else {
                "Disabled"
            }
        )),
        Line::from(format!(
            "  Show FormID Values:    {}",
            if app.config.show_formid_values {
                "Yes"
            } else {
                "No"
            }
        )),
        Line::from(format!(
            "  Statistical Logging:   {}",
            if app.config.stat_logging {
                "Enabled"
            } else {
                "Disabled"
            }
        )),
        Line::from(format!(
            "  Move Unsolved Logs:    {}",
            if app.config.move_unsolved_logs {
                "Yes"
            } else {
                "No"
            }
        )),
        Line::from(format!(
            "  Simplify Logs:         {}",
            if app.config.simplify_logs {
                "Yes"
            } else {
                "No"
            }
        )),
        Line::from(""),
        Line::from(vec![Span::styled(
            "Update Options:",
            Style::default().add_modifier(Modifier::BOLD),
        )]),
        Line::from(format!(
            "  Check for Updates:     {}",
            if app.check_updates { "Yes" } else { "No" }
        )),
        Line::from(""),
        Line::from(vec![Span::styled(
            "Paths:",
            Style::default().add_modifier(Modifier::BOLD),
        )]),
        Line::from(format!(
            "  Game Root:     {}",
            app.config.paths.game_root.display()
        )),
        Line::from(format!(
            "  INI Folder:    {}",
            app.config
                .paths
                .ini_folder
                .as_ref()
                .map(|p| p.display().to_string())
                .unwrap_or_else(|| "[Default]".to_string())
        )),
        Line::from(format!(
            "  Mods Folder:   {}",
            app.config
                .paths
                .mods_folder
                .as_ref()
                .map(|p| p.display().to_string())
                .unwrap_or_else(|| "[Not Set]".to_string())
        )),
        Line::from(format!(
            "  Scan Custom:   {}",
            app.config
                .paths
                .scan_custom
                .as_ref()
                .map(|p| p.display().to_string())
                .unwrap_or_else(|| "[Not Set]".to_string())
        )),
        Line::from(""),
        Line::from("═══════════════════════════════════════════════════════════"),
        Line::from(""),
        Line::from(vec![Span::styled(
            "Settings are saved automatically when changed.",
            Style::default().fg(Color::Yellow),
        )]),
        Line::from(vec![Span::styled(
            "Press ESC to return to main screen",
            Style::default().fg(Color::Yellow),
        )]),
    ];

    let settings_widget = Paragraph::new(settings_text)
        .alignment(Alignment::Left)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(" Settings ")
                .border_style(Style::default().fg(Color::Magenta)),
        );

    f.render_widget(settings_widget, working_area);
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::Terminal;
    use ratatui::backend::TestBackend;

    #[test]
    fn test_render_settings_screen() {
        let backend = TestBackend::new(100, 40);
        let mut terminal = Terminal::new(backend).unwrap();

        let app = App::new();

        terminal
            .draw(|f| {
                render_settings_screen(f, &app);
            })
            .unwrap();

        // Should not panic
    }
}
