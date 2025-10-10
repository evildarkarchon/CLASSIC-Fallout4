use ratatui::{
    layout::{Alignment, Rect},
    style::{Color, Style},
    widgets::Paragraph,
    Frame,
};

/// Widget for displaying status bar with key hints and progress
pub struct StatusBar {
    message: String,
    key_hints: String,
    dirty: bool, // Track if widget needs redraw
}

impl StatusBar {
    /// Create a new status bar
    pub fn new() -> Self {
        Self {
            message: String::new(),
            key_hints: " F1 Help | F5 Crash Scan | F6 Game Scan | Q Quit ".to_string(),
            dirty: true, // Start dirty to force initial render
        }
    }

    /// Set the status message
    pub fn set_message(&mut self, message: impl Into<String>) {
        let new_message = message.into();
        if self.message != new_message {
            self.message = new_message;
            self.dirty = true; // Mark dirty on message change
        }
    }

    /// Clear the status message
    pub fn clear_message(&mut self) {
        if !self.message.is_empty() {
            self.message.clear();
            self.dirty = true; // Mark dirty on message clear
        }
    }

    /// Set the key hints
    pub fn set_key_hints(&mut self, hints: impl Into<String>) {
        let new_hints = hints.into();
        if self.key_hints != new_hints {
            self.key_hints = new_hints;
            self.dirty = true; // Mark dirty on hints change
        }
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

    /// Render the status bar widget
    pub fn render(&self, f: &mut Frame, area: Rect) {
        let text = if self.message.is_empty() {
            self.key_hints.clone()
        } else {
            format!("{} | {}", self.key_hints, self.message)
        };

        let widget = Paragraph::new(text)
            .style(Style::default().bg(Color::DarkGray).fg(Color::White))
            .alignment(Alignment::Left);

        f.render_widget(widget, area);
    }
}

impl Default for StatusBar {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_status_bar_creation() {
        let bar = StatusBar::new();
        assert!(bar.message.is_empty());
        assert!(!bar.key_hints.is_empty());
    }

    #[test]
    fn test_set_message() {
        let mut bar = StatusBar::new();
        bar.set_message("Test message");
        assert_eq!(bar.message, "Test message");
    }

    #[test]
    fn test_clear_message() {
        let mut bar = StatusBar::new();
        bar.set_message("Test");
        assert!(!bar.message.is_empty());

        bar.clear_message();
        assert!(bar.message.is_empty());
    }

    #[test]
    fn test_set_key_hints() {
        let mut bar = StatusBar::new();
        let hints = "Custom hints";
        bar.set_key_hints(hints);
        assert_eq!(bar.key_hints, hints);
    }
}
