use ratatui::{
    layout::Rect,
    style::{Color, Style},
    text::Line,
    widgets::{Block, Borders, Paragraph},
    Frame,
};
use std::path::{Path, PathBuf};

/// Widget for folder path selection
pub struct FolderSelector {
    label: String,
    value: Option<PathBuf>,
    focused: bool,
    dirty: bool, // Track if widget needs redraw
}

impl FolderSelector {
    /// Create a new folder selector with a label
    pub fn new(label: impl Into<String>) -> Self {
        Self {
            label: label.into(),
            value: None,
            focused: false,
            dirty: true, // Start dirty to force initial render
        }
    }

    /// Set the folder path
    pub fn set_value(&mut self, path: PathBuf) {
        if self.value.as_ref() != Some(&path) {
            self.value = Some(path);
            self.dirty = true; // Mark dirty on value change
        }
    }

    /// Get the current path
    pub fn value(&self) -> Option<&Path> {
        self.value.as_deref()
    }

    /// Set focus state
    pub fn set_focused(&mut self, focused: bool) {
        if self.focused != focused {
            self.focused = focused;
            self.dirty = true; // Mark dirty on focus change (affects border color)
        }
    }

    /// Check if the current path is valid (exists and is a directory)
    pub fn validate(&self) -> bool {
        self.value
            .as_ref()
            .map(|p| p.exists() && p.is_dir())
            .unwrap_or(false)
    }

    /// Check if this widget has focus
    pub fn is_focused(&self) -> bool {
        self.focused
    }

    /// Check if widget needs redraw
    pub fn is_dirty(&self) -> bool {
        self.dirty
    }

    /// Mark widget as clean after rendering
    pub fn mark_clean(&mut self) {
        self.dirty = false;
    }

    /// Force widget to be dirty (useful for external state changes)
    pub fn mark_dirty(&mut self) {
        self.dirty = true;
    }

    /// Render the folder selector widget
    pub fn render(&self, f: &mut Frame, area: Rect) {
        let display_path = self
            .value
            .as_ref()
            .map(|p| p.display().to_string())
            .unwrap_or_else(|| "[Not Set]".to_string());

        let lines = vec![Line::from(self.label.as_str()), Line::from(display_path)];

        let border_color = if self.focused {
            Color::Yellow
        } else if self.validate() {
            Color::Green
        } else {
            Color::Red
        };

        let widget = Paragraph::new(lines).block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color)),
        );

        f.render_widget(widget, area);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[test]
    fn test_folder_selector_creation() {
        let selector = FolderSelector::new("Test Folder");
        assert_eq!(selector.label, "Test Folder");
        assert_eq!(selector.value(), None);
        assert!(!selector.focused);
    }

    #[test]
    fn test_set_value() {
        let mut selector = FolderSelector::new("Test");
        let path = PathBuf::from("C:\\Test");
        selector.set_value(path.clone());
        assert_eq!(selector.value(), Some(path.as_path()));
    }

    #[test]
    fn test_validate_nonexistent_path() {
        let mut selector = FolderSelector::new("Test");
        selector.set_value(PathBuf::from("C:\\NonexistentPath12345"));
        assert!(!selector.validate());
    }

    #[test]
    fn test_validate_existing_path() {
        let mut selector = FolderSelector::new("Test");
        // Use current directory which should exist
        let current_dir = env::current_dir().unwrap();
        selector.set_value(current_dir);
        assert!(selector.validate());
    }

    #[test]
    fn test_focus_state() {
        let mut selector = FolderSelector::new("Test");
        assert!(!selector.focused);

        selector.set_focused(true);
        assert!(selector.focused);

        selector.set_focused(false);
        assert!(!selector.focused);
    }
}
