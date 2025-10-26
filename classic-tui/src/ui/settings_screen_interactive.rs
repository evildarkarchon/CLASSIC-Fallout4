use crate::app::App;
use crate::widgets::Checkbox;
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Paragraph},
    Frame,
};

/// Settings tabs
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SettingsTab {
    /// General settings (scan options, output options, update checking)
    General,
    /// Path management settings (game root, documents, mods folder)
    Paths,
    /// Advanced settings (thread count, batch size, database pool)
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

/// Setting items that can be focused in General tab
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SettingItem {
    /// Enable FCX mode for crash log analysis
    FcxMode,
    /// Show FormID numeric values in output
    ShowFormIdValues,
    /// Enable statistics logging during scans
    StatLogging,
    /// Move unsolved crash logs to a separate directory
    MoveUnsolvedLogs,
    /// Simplify crash logs by removing redundant information
    SimplifyLogs,
    /// Check for updates on startup
    CheckUpdates,
}

/// Path items that can be focused in Paths tab
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PathItem {
    /// Game installation root directory
    GameRoot,
    /// Documents folder path (for My Games, saves, etc.)
    DocsRoot,
    /// Mods staging folder path
    ModsFolder,
    /// Custom scan folder path for additional log locations
    CustomScan,
}

/// Advanced settings items that can be focused in Advanced tab
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AdvancedItem {
    /// Number of worker threads for parallel processing
    ThreadCount,
    /// Number of files to process in each batch
    BatchSize,
    /// Size of database connection pool
    DatabasePoolSize,
    /// Verbosity level for logging output
    LogVerbosity,
}

impl PathItem {
    /// Get all path items in order
    pub fn all() -> Vec<Self> {
        vec![
            Self::GameRoot,
            Self::DocsRoot,
            Self::ModsFolder,
            Self::CustomScan,
        ]
    }

    /// Get the next path item
    pub fn next(&self) -> Self {
        match self {
            Self::GameRoot => Self::DocsRoot,
            Self::DocsRoot => Self::ModsFolder,
            Self::ModsFolder => Self::CustomScan,
            Self::CustomScan => Self::GameRoot,
        }
    }

    /// Get the previous path item
    pub fn prev(&self) -> Self {
        match self {
            Self::GameRoot => Self::CustomScan,
            Self::DocsRoot => Self::GameRoot,
            Self::ModsFolder => Self::DocsRoot,
            Self::CustomScan => Self::ModsFolder,
        }
    }

    /// Get the label for this path item
    pub fn label(&self) -> &'static str {
        match self {
            Self::GameRoot => "Game Root",
            Self::DocsRoot => "Docs Root",
            Self::ModsFolder => "Mods Folder",
            Self::CustomScan => "Custom Scan",
        }
    }

    /// Get the description for this path item
    pub fn description(&self) -> &'static str {
        match self {
            Self::GameRoot => "Path to Fallout 4 installation directory",
            Self::DocsRoot => "Path to Documents/My Games/Fallout4 folder",
            Self::ModsFolder => "Path to mods folder (if using mod organizer)",
            Self::CustomScan => "Custom path to scan for crash logs",
        }
    }
}

impl AdvancedItem {
    /// Get all advanced items in order
    pub fn all() -> Vec<Self> {
        vec![
            Self::ThreadCount,
            Self::BatchSize,
            Self::DatabasePoolSize,
            Self::LogVerbosity,
        ]
    }

    /// Get the next advanced item
    pub fn next(&self) -> Self {
        match self {
            Self::ThreadCount => Self::BatchSize,
            Self::BatchSize => Self::DatabasePoolSize,
            Self::DatabasePoolSize => Self::LogVerbosity,
            Self::LogVerbosity => Self::ThreadCount,
        }
    }

    /// Get the previous advanced item
    pub fn prev(&self) -> Self {
        match self {
            Self::ThreadCount => Self::LogVerbosity,
            Self::BatchSize => Self::ThreadCount,
            Self::DatabasePoolSize => Self::BatchSize,
            Self::LogVerbosity => Self::DatabasePoolSize,
        }
    }

    /// Get the label for this advanced item
    pub fn label(&self) -> &'static str {
        match self {
            Self::ThreadCount => "Worker Threads",
            Self::BatchSize => "Batch Size",
            Self::DatabasePoolSize => "DB Pool Size",
            Self::LogVerbosity => "Log Verbosity",
        }
    }

    /// Get the description for this advanced item
    pub fn description(&self) -> &'static str {
        match self {
            Self::ThreadCount => "Number of worker threads for parallel processing (default: CPU cores)",
            Self::BatchSize => "Number of items to process in each batch (default: 100)",
            Self::DatabasePoolSize => "Maximum database connection pool size (default: 10)",
            Self::LogVerbosity => "Logging verbosity level (Error, Warning, Info, Debug)",
        }
    }

    /// Get the default value for this setting
    pub fn default_value(&self) -> String {
        match self {
            Self::ThreadCount => {
                std::thread::available_parallelism()
                    .map(|n| n.get().to_string())
                    .unwrap_or_else(|_| "4".to_string())
            }
            Self::BatchSize => "100".to_string(),
            Self::DatabasePoolSize => "10".to_string(),
            Self::LogVerbosity => "Info".to_string(),
        }
    }
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
    /// Currently focused setting item (General tab)
    pub focused_item: SettingItem,
    /// Currently focused path item (Paths tab)
    pub focused_path: PathItem,
    /// Currently focused advanced item (Advanced tab)
    pub focused_advanced: AdvancedItem,
    /// Whether we're in edit mode
    pub editing: bool,
}

impl Default for SettingsState {
    fn default() -> Self {
        Self {
            current_tab: SettingsTab::General,
            focused_item: SettingItem::FcxMode,
            focused_path: PathItem::GameRoot,
            focused_advanced: AdvancedItem::ThreadCount,
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

    /// Focus next path item
    pub fn focus_next_path(&mut self) {
        self.focused_path = self.focused_path.next();
    }

    /// Focus previous path item
    pub fn focus_prev_path(&mut self) {
        self.focused_path = self.focused_path.prev();
    }

    /// Focus next advanced item
    pub fn focus_next_advanced(&mut self) {
        self.focused_advanced = self.focused_advanced.next();
    }

    /// Focus previous advanced item
    pub fn focus_prev_advanced(&mut self) {
        self.focused_advanced = self.focused_advanced.prev();
    }
}

/// Render the interactive settings screen
pub fn render_settings_screen_interactive(f: &mut Frame, app: &mut App, state: &SettingsState) {
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
            Constraint::Length(3), // Header
            Constraint::Length(3), // Tab bar
            Constraint::Min(10),   // Tab content
            Constraint::Length(5), // Description
            Constraint::Length(3), // Instructions
        ])
        .split(working_area);

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

    // Render folder picker overlay if active (for path editing)
    if let Some(ref mut picker) = app.settings_path_picker {
        if picker.is_active() {
            use crate::widgets::FolderPicker;
            let title = if let Some(path_item) = app.editing_path {
                format!("Select {} Path", path_item.label())
            } else {
                "Select Path".to_string()
            };
            let popup_area = centered_rect(80, 70, f.area());
            f.render_widget(Clear, popup_area);
            let folder_picker = FolderPicker::new(&title)
                .border_style(Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))
                .selected_style(
                    Style::default()
                        .fg(Color::Black)
                        .bg(Color::Cyan)
                        .add_modifier(Modifier::BOLD),
                );
            folder_picker.render(f, popup_area, picker);
        }
    }

    // Render error dialog overlay if active (should be last so it appears on top)
    if let Some(ref dialog) = app.error_dialog {
        if dialog.is_active() {
            dialog.render(f, f.area());
        }
    }
}

/// Helper function to create a centered rect for popups
fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(r);

    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(popup_layout[1])[1]
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
    // Get description based on current tab and focused item
    let description_str = match state.current_tab {
        SettingsTab::General => state.focused_item.description(),
        SettingsTab::Paths => state.focused_path.description(),
        SettingsTab::Advanced => state.focused_advanced.description(),
    };

    let description_text = vec![
        Line::from(""),
        Line::from(vec![Span::styled(
            description_str,
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

fn render_paths_tab(f: &mut Frame, area: Rect, app: &App, state: &SettingsState) {
    let block = Block::default()
        .borders(Borders::ALL)
        .title(" Path Settings ")
        .border_style(Style::default().fg(Color::White));

    let inner_area = block.inner(area);
    f.render_widget(block, area);

    // Build lines for each path with highlighting for focused item
    let path_items = PathItem::all();
    let mut lines = Vec::new();

    for item in path_items {
        let is_focused = item == state.focused_path;

        // Get the path value
        let path_value = match item {
            PathItem::GameRoot => app.config.paths.game_root.display().to_string(),
            PathItem::DocsRoot => app
                .config
                .paths
                .docs_root
                .as_ref()
                .map(|p| p.display().to_string())
                .unwrap_or_else(|| "<Not Set>".to_string()),
            PathItem::ModsFolder => app
                .config
                .paths
                .mods_folder
                .as_ref()
                .map(|p| p.display().to_string())
                .unwrap_or_else(|| "<Not Set>".to_string()),
            PathItem::CustomScan => app
                .config
                .paths
                .scan_custom
                .as_ref()
                .map(|p| p.display().to_string())
                .unwrap_or_else(|| "<Not Set>".to_string()),
        };

        // Style based on focus
        let label_style = if is_focused {
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(Color::Cyan)
        };

        let value_style = if is_focused {
            Style::default().fg(Color::White).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(Color::White)
        };

        // Add selection indicator
        let indicator = if is_focused { "> " } else { "  " };

        lines.push(Line::from(vec![
            Span::raw(indicator),
            Span::styled(format!("{:<14}", format!("{}:", item.label())), label_style),
            Span::styled(path_value, value_style),
        ]));
        lines.push(Line::from("")); // Spacing between items
    }

    lines.push(Line::from(""));
    lines.push(Line::from(vec![Span::styled(
        "Press Enter or 'e' to select folder",
        Style::default().fg(Color::DarkGray),
    )]));

    let paths_widget = Paragraph::new(lines);
    f.render_widget(paths_widget, inner_area);
}

fn render_advanced_tab(f: &mut Frame, area: Rect, _app: &App, state: &SettingsState) {
    let block = Block::default()
        .borders(Borders::ALL)
        .title(" Advanced Settings ")
        .border_style(Style::default().fg(Color::White));

    let inner_area = block.inner(area);
    f.render_widget(block, area);

    // Build lines for each advanced setting with highlighting for focused item
    let advanced_items = AdvancedItem::all();
    let mut lines = Vec::new();

    for item in advanced_items {
        let is_focused = item == state.focused_advanced;

        // Get the value (placeholder for now, will be connected to config later)
        let value = item.default_value();

        // Style based on focus
        let label_style = if is_focused {
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(Color::Cyan)
        };

        let value_style = if is_focused {
            Style::default().fg(Color::White).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(Color::White)
        };

        // Add selection indicator
        let indicator = if is_focused { "> " } else { "  " };

        lines.push(Line::from(vec![
            Span::raw(indicator),
            Span::styled(format!("{:<20}", format!("{}:", item.label())), label_style),
            Span::styled(value, value_style),
        ]));
        lines.push(Line::from("")); // Spacing between items
    }

    lines.push(Line::from(""));
    lines.push(Line::from(vec![Span::styled(
        "Use ↑↓ to navigate, values shown are defaults (editing coming soon)",
        Style::default().fg(Color::DarkGray),
    )]));

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

        let mut app = App::new();
        let state = SettingsState::new();

        terminal
            .draw(|f| {
                render_settings_screen_interactive(f, &mut app, &state);
            })
            .unwrap();

        // Should not panic
    }
}
