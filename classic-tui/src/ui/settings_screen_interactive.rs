use crate::app::App;
use crate::widgets::Checkbox;
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

/// Setting items that can be focused
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SettingItem {
    FcxMode,
    ShowFormIdValues,
    StatLogging,
    MoveUnsolvedLogs,
    SimplifyLogs,
    CheckUpdates,
}

impl SettingItem {
    /// Get all setting items in order
    pub fn all() -> Vec<Self> {
        vec![
            Self::FcxMode,
            Self::ShowFormIdValues,
            Self::StatLogging,
            Self::MoveUnsolvedLogs,
            Self::SimplifyLogs,
            Self::CheckUpdates,
        ]
    }

    /// Get the next setting item
    pub fn next(&self) -> Self {
        let items = Self::all();
        let current_index = items.iter().position(|&item| item == *self).unwrap();
        let next_index = (current_index + 1) % items.len();
        items[next_index]
    }

    /// Get the previous setting item
    pub fn prev(&self) -> Self {
        let items = Self::all();
        let current_index = items.iter().position(|&item| item == *self).unwrap();
        let prev_index = if current_index == 0 {
            items.len() - 1
        } else {
            current_index - 1
        };
        items[prev_index]
    }

    /// Get the label for this setting
    pub fn label(&self) -> &'static str {
        match self {
            Self::FcxMode => "FCX Mode",
            Self::ShowFormIdValues => "Show FormID Values",
            Self::StatLogging => "Statistical Logging",
            Self::MoveUnsolvedLogs => "Move Unsolved Logs",
            Self::SimplifyLogs => "Simplify Logs",
            Self::CheckUpdates => "Check for Updates",
        }
    }

    /// Get the description for this setting
    pub fn description(&self) -> &'static str {
        match self {
            Self::FcxMode => "Enable FCX mode for enhanced FormID analysis",
            Self::ShowFormIdValues => "Display FormID values in scan output",
            Self::StatLogging => "Enable statistical logging during scans",
            Self::MoveUnsolvedLogs => "Move unsolved crash logs to a separate folder",
            Self::SimplifyLogs => "Simplify log output (may remove important info)",
            Self::CheckUpdates => "Check for application updates at startup",
        }
    }
}

/// Settings screen state
#[derive(Debug, Clone)]
pub struct SettingsState {
    /// Currently focused setting item
    pub focused_item: SettingItem,
    /// Whether we're in edit mode
    pub editing: bool,
}

impl Default for SettingsState {
    fn default() -> Self {
        Self {
            focused_item: SettingItem::FcxMode,
            editing: false,
        }
    }
}

impl SettingsState {
    /// Create a new settings state
    pub fn new() -> Self {
        Self::default()
    }

    /// Focus the next item
    pub fn focus_next(&mut self) {
        self.focused_item = self.focused_item.next();
    }

    /// Focus the previous item
    pub fn focus_prev(&mut self) {
        self.focused_item = self.focused_item.prev();
    }

    /// Get the value for the focused item
    pub fn get_value(&self, app: &App) -> bool {
        match self.focused_item {
            SettingItem::FcxMode => app.config.fcx_mode,
            SettingItem::ShowFormIdValues => app.config.show_formid_values,
            SettingItem::StatLogging => app.config.stat_logging,
            SettingItem::MoveUnsolvedLogs => app.config.move_unsolved_logs,
            SettingItem::SimplifyLogs => app.config.simplify_logs,
            SettingItem::CheckUpdates => app.check_updates,
        }
    }

    /// Toggle the focused setting
    pub fn toggle_focused(&self, app: &mut App) {
        match self.focused_item {
            SettingItem::FcxMode => app.config.fcx_mode = !app.config.fcx_mode,
            SettingItem::ShowFormIdValues => {
                app.config.show_formid_values = !app.config.show_formid_values
            }
            SettingItem::StatLogging => app.config.stat_logging = !app.config.stat_logging,
            SettingItem::MoveUnsolvedLogs => {
                app.config.move_unsolved_logs = !app.config.move_unsolved_logs
            }
            SettingItem::SimplifyLogs => app.config.simplify_logs = !app.config.simplify_logs,
            SettingItem::CheckUpdates => app.check_updates = !app.check_updates,
        }
    }
}

/// Render the interactive settings screen
pub fn render_settings_screen_interactive(f: &mut Frame, app: &App, state: &SettingsState) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // Header
            Constraint::Min(10),   // Settings list
            Constraint::Length(5), // Description
            Constraint::Length(3), // Instructions
        ])
        .split(f.area());

    // Header
    render_header(f, chunks[0]);

    // Settings list
    render_settings_list(f, chunks[1], app, state);

    // Description
    render_description(f, chunks[2], state);

    // Instructions
    render_instructions(f, chunks[3]);
}

fn render_header(f: &mut Frame, area: Rect) {
    let header = Paragraph::new(vec![Line::from(vec![Span::styled(
        "CLASSIC - Settings",
        Style::default()
            .fg(Color::Cyan)
            .add_modifier(Modifier::BOLD),
    )])])
    .alignment(Alignment::Center)
    .block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Magenta)),
    );

    f.render_widget(header, area);
}

fn render_settings_list(f: &mut Frame, area: Rect, app: &App, state: &SettingsState) {
    let inner_area = Block::default()
        .borders(Borders::ALL)
        .title(" Options ")
        .border_style(Style::default().fg(Color::White))
        .inner(area);

    // Render the block first
    f.render_widget(
        Block::default()
            .borders(Borders::ALL)
            .title(" Options ")
            .border_style(Style::default().fg(Color::White)),
        area,
    );

    // Calculate layout for checkboxes
    let items = SettingItem::all();
    let checkbox_height = 3;
    let mut constraints = vec![];
    for _ in 0..items.len() {
        constraints.push(Constraint::Length(checkbox_height));
    }
    constraints.push(Constraint::Min(1)); // Fill remaining space

    let checkbox_areas = Layout::default()
        .direction(Direction::Vertical)
        .constraints(constraints)
        .split(inner_area);

    // Render each checkbox
    for (idx, item) in items.iter().enumerate() {
        let value = match item {
            SettingItem::FcxMode => app.config.fcx_mode,
            SettingItem::ShowFormIdValues => app.config.show_formid_values,
            SettingItem::StatLogging => app.config.stat_logging,
            SettingItem::MoveUnsolvedLogs => app.config.move_unsolved_logs,
            SettingItem::SimplifyLogs => app.config.simplify_logs,
            SettingItem::CheckUpdates => app.check_updates,
        };

        let mut checkbox = Checkbox::new(item.label(), value);
        checkbox.set_focused(*item == state.focused_item);
        checkbox.render(f, checkbox_areas[idx]);
    }
}

fn render_description(f: &mut Frame, area: Rect, state: &SettingsState) {
    let description_text = vec![
        Line::from(""),
        Line::from(vec![Span::styled(
            state.focused_item.description(),
            Style::default().fg(Color::Gray),
        )]),
    ];

    let description = Paragraph::new(description_text)
        .alignment(Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(" Description ")
                .border_style(Style::default().fg(Color::DarkGray)),
        );

    f.render_widget(description, area);
}

fn render_instructions(f: &mut Frame, area: Rect) {
    let instructions = vec![Line::from(vec![
        Span::styled("↑/↓", Style::default().fg(Color::Yellow)),
        Span::raw(" Navigate | "),
        Span::styled("Space/Enter", Style::default().fg(Color::Yellow)),
        Span::raw(" Toggle | "),
        Span::styled("ESC", Style::default().fg(Color::Yellow)),
        Span::raw(" Back | "),
        Span::styled("S", Style::default().fg(Color::Yellow)),
        Span::raw(" Save"),
    ])];

    let instructions_widget = Paragraph::new(instructions)
        .alignment(Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::Green)),
        );

    f.render_widget(instructions_widget, area);
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    #[test]
    fn test_setting_item_navigation() {
        let item = SettingItem::FcxMode;
        let next = item.next();
        assert_eq!(next, SettingItem::ShowFormIdValues);

        let last = SettingItem::CheckUpdates;
        let next = last.next();
        assert_eq!(next, SettingItem::FcxMode); // Wraps around
    }

    #[test]
    fn test_settings_state_navigation() {
        let mut state = SettingsState::new();
        assert_eq!(state.focused_item, SettingItem::FcxMode);

        state.focus_next();
        assert_eq!(state.focused_item, SettingItem::ShowFormIdValues);

        state.focus_prev();
        assert_eq!(state.focused_item, SettingItem::FcxMode);
    }

    #[test]
    fn test_toggle_focused() {
        let mut state = SettingsState::new();
        let mut app = App::new();

        state.focused_item = SettingItem::FcxMode;
        assert!(!app.config.fcx_mode);

        state.toggle_focused(&mut app);
        assert!(app.config.fcx_mode);

        state.toggle_focused(&mut app);
        assert!(!app.config.fcx_mode);
    }

    #[test]
    fn test_render_settings_screen() {
        let backend = TestBackend::new(100, 40);
        let mut terminal = Terminal::new(backend).unwrap();

        let app = App::new();
        let state = SettingsState::new();

        terminal
            .draw(|f| {
                render_settings_screen_interactive(f, &app, &state);
            })
            .unwrap();

        // Should not panic
    }
}
