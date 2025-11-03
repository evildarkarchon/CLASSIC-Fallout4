//! Folder picker widget for navigating and selecting directories
//!
//! This widget provides an interactive file browser for selecting folders.
//! Features:
//! - Navigate directories with arrow keys
//! - Select with Enter
//! - Go up a directory with Backspace
//! - Show current path
//! - Filter to show only directories

use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Wrap},
    Frame,
};
use std::path::{Path, PathBuf};

/// State for the folder picker widget
pub struct FolderPickerState {
    /// Current directory being browsed
    current_dir: PathBuf,

    /// List of directory entries in current directory
    entries: Vec<DirEntry>,

    /// Currently selected entry index
    selected_index: usize,

    /// List state for ratatui
    list_state: ListState,

    /// Whether the picker is active/visible
    is_active: bool,

    /// Error message if directory read failed
    error: Option<String>,
}

/// Directory entry information
#[derive(Clone)]
struct DirEntry {
    /// Entry name
    name: String,

    /// Full path
    path: PathBuf,
}

#[allow(dead_code)]
impl FolderPickerState {
    /// Create a new folder picker starting at the given directory
    ///
    /// # Arguments
    ///
    /// * `start_dir` - Initial directory to browse, defaults to current directory if None
    ///
    /// # Returns
    ///
    /// A new `FolderPickerState` instance
    pub fn new(start_dir: Option<PathBuf>) -> Self {
        let current_dir = start_dir
            .or_else(|| std::env::current_dir().ok())
            .unwrap_or_else(|| PathBuf::from("/"));

        let mut state = Self {
            current_dir: current_dir.clone(),
            entries: Vec::new(),
            selected_index: 0,
            list_state: ListState::default(),
            is_active: false,
            error: None,
        };

        state.refresh_entries();
        state
    }

    /// Refresh the directory entries for the current directory
    fn refresh_entries(&mut self) {
        self.entries.clear();
        self.error = None;

        // Add parent directory entry if not at root
        if let Some(parent) = self.current_dir.parent() {
            self.entries.push(DirEntry {
                name: "..".to_string(),
                path: parent.to_path_buf(),
            });
        }

        // Read directory entries
        match std::fs::read_dir(&self.current_dir) {
            Ok(read_dir) => {
                let mut dirs: Vec<DirEntry> = read_dir
                    .filter_map(|entry| entry.ok())
                    .filter_map(|entry| {
                        let path = entry.path();
                        // Only show directories
                        if path.is_dir() {
                            Some(DirEntry {
                                name: entry.file_name().to_string_lossy().to_string(),
                                path,
                            })
                        } else {
                            None
                        }
                    })
                    .collect();

                // Sort directories alphabetically
                dirs.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));

                self.entries.extend(dirs);
            }
            Err(e) => {
                self.error = Some(format!("Failed to read directory: {}", e));
            }
        }

        // Reset selection to first item
        self.selected_index = 0;
        self.list_state.select(Some(0));
    }

    /// Activate the folder picker
    pub fn activate(&mut self) {
        self.is_active = true;
    }

    /// Deactivate the folder picker
    pub fn deactivate(&mut self) {
        self.is_active = false;
    }

    /// Check if the picker is active
    pub fn is_active(&self) -> bool {
        self.is_active
    }

    /// Move selection up
    pub fn move_up(&mut self) {
        if self.entries.is_empty() {
            return;
        }

        if self.selected_index > 0 {
            self.selected_index -= 1;
        } else {
            // Wrap to bottom
            self.selected_index = self.entries.len() - 1;
        }
        self.list_state.select(Some(self.selected_index));
    }

    /// Move selection down
    pub fn move_down(&mut self) {
        if self.entries.is_empty() {
            return;
        }

        if self.selected_index < self.entries.len() - 1 {
            self.selected_index += 1;
        } else {
            // Wrap to top
            self.selected_index = 0;
        }
        self.list_state.select(Some(self.selected_index));
    }

    /// Enter the currently selected directory
    pub fn enter_selected(&mut self) {
        if self.selected_index < self.entries.len() {
            let selected_entry = &self.entries[self.selected_index];
            self.current_dir = selected_entry.path.clone();
            self.refresh_entries();
        }
    }

    /// Go up to parent directory
    pub fn go_up(&mut self) {
        if let Some(parent) = self.current_dir.parent() {
            self.current_dir = parent.to_path_buf();
            self.refresh_entries();
        }
    }

    /// Get the currently selected path
    pub fn get_selected_path(&self) -> PathBuf {
        self.current_dir.clone()
    }

    /// Get the current directory path
    pub fn get_current_dir(&self) -> &Path {
        &self.current_dir
    }

    /// Set a new directory to browse
    pub fn set_directory(&mut self, dir: PathBuf) {
        if dir.is_dir() {
            self.current_dir = dir;
            self.refresh_entries();
        }
    }
}

/// Folder picker widget
#[allow(dead_code)]
pub struct FolderPicker<'a> {
    /// Title for the picker
    title: &'a str,

    /// Border style
    border_style: Style,

    /// Selected item style
    selected_style: Style,

    /// Normal item style
    normal_style: Style,
}

#[allow(dead_code)]
impl<'a> FolderPicker<'a> {
    /// Create a new folder picker widget
    ///
    /// # Arguments
    ///
    /// * `title` - Title to display at the top of the picker
    ///
    /// # Returns
    ///
    /// A new `FolderPicker` instance with default styling
    pub fn new(title: &'a str) -> Self {
        Self {
            title,
            border_style: Style::default().fg(Color::Cyan),
            selected_style: Style::default()
                .fg(Color::Black)
                .bg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
            normal_style: Style::default().fg(Color::White),
        }
    }

    /// Set the border style
    pub fn border_style(mut self, style: Style) -> Self {
        self.border_style = style;
        self
    }

    /// Set the selected item style
    pub fn selected_style(mut self, style: Style) -> Self {
        self.selected_style = style;
        self
    }

    /// Set the normal item style
    pub fn normal_style(mut self, style: Style) -> Self {
        self.normal_style = style;
        self
    }

    /// Render the folder picker
    ///
    /// # Arguments
    ///
    /// * `f` - Frame to render to
    /// * `area` - Area to render within
    /// * `state` - Picker state containing current directory and selection
    pub fn render(&self, f: &mut Frame, area: Rect, state: &mut FolderPickerState) {
        // Split area into sections
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // Current path
                Constraint::Min(10),   // Directory list
                Constraint::Length(3), // Help text
            ])
            .split(area);

        // Render current path
        let path_text = format!("Current: {}", state.current_dir.display());
        let path_widget = Paragraph::new(path_text)
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .title(self.title)
                    .border_style(self.border_style),
            )
            .wrap(Wrap { trim: true });
        f.render_widget(path_widget, chunks[0]);

        // Render directory list
        if let Some(error) = &state.error {
            let error_widget = Paragraph::new(vec![
                Line::from(""),
                Line::from(Span::styled(
                    "Error reading directory:",
                    Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
                )),
                Line::from(error.as_str()),
            ])
            .block(Block::default().borders(Borders::ALL))
            .alignment(Alignment::Center);
            f.render_widget(error_widget, chunks[1]);
        } else if state.entries.is_empty() {
            let empty_widget = Paragraph::new("No directories found")
                .block(Block::default().borders(Borders::ALL))
                .alignment(Alignment::Center);
            f.render_widget(empty_widget, chunks[1]);
        } else {
            let items: Vec<ListItem> = state
                .entries
                .iter()
                .map(|entry| {
                    let icon = if entry.name == ".." {
                        "⬆ "
                    } else {
                        "📁 "
                    };
                    ListItem::new(format!("{}{}", icon, entry.name))
                })
                .collect();

            let list = List::new(items)
                .block(Block::default().borders(Borders::ALL).title("Directories"))
                .highlight_style(self.selected_style)
                .highlight_symbol(">> ");

            f.render_stateful_widget(list, chunks[1], &mut state.list_state);
        }

        // Render help text
        let help_text = vec![
            Line::from(vec![
                Span::styled("↑↓", Style::default().fg(Color::Yellow)),
                Span::raw(" Navigate | "),
                Span::styled("Enter", Style::default().fg(Color::Yellow)),
                Span::raw(" Select/Enter Dir | "),
                Span::styled("Backspace", Style::default().fg(Color::Yellow)),
                Span::raw(" Parent | "),
                Span::styled("Esc", Style::default().fg(Color::Yellow)),
                Span::raw(" Cancel"),
            ]),
        ];

        let help_widget = Paragraph::new(help_text)
            .block(Block::default().borders(Borders::ALL))
            .alignment(Alignment::Center);
        f.render_widget(help_widget, chunks[2]);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_folder_picker_creation() {
        let state = FolderPickerState::new(None);
        assert!(state.current_dir.is_absolute() || state.current_dir == PathBuf::from("/"));
        assert!(!state.is_active);
    }

    #[test]
    fn test_activate_deactivate() {
        let mut state = FolderPickerState::new(None);
        assert!(!state.is_active());

        state.activate();
        assert!(state.is_active());

        state.deactivate();
        assert!(!state.is_active());
    }

    #[test]
    fn test_navigation() {
        let mut state = FolderPickerState::new(None);

        if !state.entries.is_empty() {
            let initial_index = state.selected_index;

            state.move_down();
            assert_ne!(state.selected_index, initial_index);

            state.move_up();
            assert_eq!(state.selected_index, initial_index);
        }
    }

    #[test]
    fn test_get_current_dir() {
        let test_dir = std::env::current_dir().unwrap();
        let state = FolderPickerState::new(Some(test_dir.clone()));
        assert_eq!(state.get_current_dir(), test_dir.as_path());
    }
}
