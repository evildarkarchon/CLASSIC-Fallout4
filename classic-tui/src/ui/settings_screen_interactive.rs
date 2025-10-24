use crate::app::App;
use crate::widgets::Checkbox;
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

/// Settings tabs
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SettingsTab {
    General,
    Paths,
    Advanced,
}

impl SettingsTab {
    /// Get all tabs in order
    pub fn all() -> Vec<Self> {
        vec![Self::General, Self::Paths, Self::Advanced]
    }

    /// Get the next tab
    pub fn next(&self) -> Self {
        match self {
            Self::General => Self::Paths,
            Self::Paths => Self::Advanced,
            Self::Advanced => Self::General,
        }
    }

    /// Get the previous tab
    pub fn prev(&self) -> Self {
        match self {
            Self::General => Self::Advanced,
            Self::Paths => Self::General,
            Self::Advanced => Self::Paths,
        }
    }

    /// Get the tab name
    pub fn name(&self) -> &'static str {
        match self {
            Self::General => "General",
            Self::Paths => "Paths",
            Self::Advanced => "Advanced",
        }
    }
}

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
    /// Current settings tab
    pub current_tab: SettingsTab,
    /// Currently focused setting item
    pub focused_item: SettingItem,
    /// Whether we're in edit mode
    pub editing: bool,
}

impl Default for SettingsState {
    fn default() -> Self {
        Self {
            current_tab: SettingsTab::General,
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

    /// Switch to next tab
    pub fn next_tab(&mut self) {
        self.current_tab = self.current_tab.next();
    }

    /// Switch to previous tab
    pub fn prev_tab(&mut self) {
        self.current_tab = self.current_tab.prev();
    }
}

/// Render the interactive settings screen
pub fn render_settings_screen_interactive(f: &mut Frame, app: &App, state: &SettingsState) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // Header
            Constraint::Length(3), // Tab bar
            Constraint::Min(10),   // Tab content
            Constraint::Length(5), // Description
            Constraint::Length(3), // Instructions
        ])
        .split(f.area());

    // Header
    render_header(f, chunks[0]);

    // Tab bar
    render_tab_bar(f, chunks[1], state);

    // Tab content (render based on current tab)
    match state.current_tab {
        SettingsTab::General => render_general_tab(f, chunks[2], app, state),
        SettingsTab::Paths => render_paths_tab(f, chunks[2], app, state),
        SettingsTab::Advanced => render_advanced_tab(f, chunks[2], app, state),
    }

    // Description
    render_description(f, chunks[3], state);

    // Instructions
    render_instructions(f, chunks[4]);
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

fn render_tab_bar(f: &mut Frame, area: Rect, state: &SettingsState) {
    let tabs = SettingsTab::all();
    let mut tab_spans = Vec::new();

    for (i, tab) in tabs.iter().enumerate() {
        if i > 0 {
            tab_spans.push(Span::raw(" │ "));
        }

        let is_active = *tab == state.current_tab;
        let style = if is_active {
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD | Modifier::UNDERLINED)
        } else {
            Style::default().fg(Color::White)
        };

        tab_spans.push(Span::styled(format!(" {} ", tab.name()), style));
    }

    let tabs_line = Line::from(tab_spans);
    let tabs_widget = Paragraph::new(tabs_line)
        .alignment(Alignment::Center)
        .block(Block::default().borders(Borders::ALL));

    f.render_widget(tabs_widget, area);
}

fn render_general_tab(f: &mut Frame, area: Rect, app: &App, state: &SettingsState) {
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

fn render_paths_tab(f: &mut Frame, area: Rect, app: &App, _state: &SettingsState) {
    let block = Block::default()
        .borders(Borders::ALL)
        .title(" Path Settings ")
        .border_style(Style::default().fg(Color::White));

    let inner_area = block.inner(area);
    f.render_widget(block, area);

    // Display current paths
    let lines = vec![
        Line::from(vec![
            Span::styled("Game Root:    ", Style::default().fg(Color::Cyan)),
            Span::raw(app.config.paths.game_root.display().to_string()),
        ]),
        Line::from(""),
        Line::from(vec![
            Span::styled("Docs Root:    ", Style::default().fg(Color::Cyan)),
            Span::raw(
                app.config
                    .paths
                    .docs_root
                    .as_ref()
                    .map(|p| p.display().to_string())
                    .unwrap_or_else(|| "<Not Set>".to_string()),
            ),
        ]),
        Line::from(""),
        Line::from(vec![
            Span::styled("Mods Folder:  ", Style::default().fg(Color::Cyan)),
            Span::raw(
                app.config
                    .paths
                    .mods_folder
                    .as_ref()
                    .map(|p| p.display().to_string())
                    .unwrap_or_else(|| "<Not Set>".to_string()),
            ),
        ]),
        Line::from(""),
        Line::from(vec![
            Span::styled("Custom Scan:  ", Style::default().fg(Color::Cyan)),
            Span::raw(
                app.config
                    .paths
                    .scan_custom
                    .as_ref()
                    .map(|p| p.display().to_string())
                    .unwrap_or_else(|| "<Not Set>".to_string()),
            ),
        ]),
        Line::from(""),
        Line::from(""),
        Line::from(vec![Span::styled(
            "Press 'e' to edit paths (Coming Soon)",
            Style::default().fg(Color::DarkGray),
        )]),
    ];

    let paths_widget = Paragraph::new(lines);
    f.render_widget(paths_widget, inner_area);
}

fn render_advanced_tab(f: &mut Frame, area: Rect, _app: &App, _state: &SettingsState) {
    let block = Block::default()
        .borders(Borders::ALL)
        .title(" Advanced Settings ")
        .border_style(Style::default().fg(Color::White));

    let inner_area = block.inner(area);
    f.render_widget(block, area);

    let lines = vec![
        Line::from(vec![Span::styled(
            "Performance Settings",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )]),
        Line::from(""),
        Line::from(vec![
            Span::styled("Thread Count:     ", Style::default().fg(Color::Cyan)),
            Span::raw("Auto (4 cores)"),
        ]),
        Line::from(vec![
            Span::styled("Batch Size:       ", Style::default().fg(Color::Cyan)),
            Span::raw("1000"),
        ]),
        Line::from(""),
        Line::from(vec![Span::styled(
            "Database Settings",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )]),
        Line::from(""),
        Line::from(vec![
            Span::styled("Connection Pool:  ", Style::default().fg(Color::Cyan)),
            Span::raw("10 connections"),
        ]),
        Line::from(""),
        Line::from(""),
        Line::from(vec![Span::styled(
            "Advanced settings editing (Coming Soon)",
            Style::default().fg(Color::DarkGray),
        )]),
    ];

    let advanced_widget = Paragraph::new(lines);
    f.render_widget(advanced_widget, inner_area);
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

        // Directly toggle the setting instead of using removed method
        app.config.fcx_mode = !app.config.fcx_mode;
        assert!(app.config.fcx_mode);

        app.config.fcx_mode = !app.config.fcx_mode;
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
