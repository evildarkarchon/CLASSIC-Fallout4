use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

/// Checkbox widget for boolean settings
pub struct Checkbox {
    label: String,
    checked: bool,
    focused: bool,
}

impl Checkbox {
    /// Create a new checkbox
    pub fn new(label: impl Into<String>, checked: bool) -> Self {
        Self {
            label: label.into(),
            checked,
            focused: false,
        }
    }

    /// Get the checked state
    pub fn is_checked(&self) -> bool {
        self.checked
    }

    /// Set the checked state
    pub fn set_checked(&mut self, checked: bool) {
        self.checked = checked;
    }

    /// Toggle the checked state
    pub fn toggle(&mut self) {
        self.checked = !self.checked;
    }

    /// Set the focused state
    pub fn set_focused(&mut self, focused: bool) {
        self.focused = focused;
    }

    /// Check if focused
    pub fn is_focused(&self) -> bool {
        self.focused
    }

    /// Render the checkbox widget
    pub fn render(&self, f: &mut Frame, area: Rect) {
        let symbol = if self.checked { "[X]" } else { "[ ]" };

        let text = Line::from(vec![
            Span::styled(
                symbol,
                Style::default()
                    .fg(if self.checked {
                        Color::Green
                    } else {
                        Color::White
                    })
                    .add_modifier(if self.focused {
                        Modifier::BOLD
                    } else {
                        Modifier::empty()
                    }),
            ),
            Span::raw(" "),
            Span::styled(
                &self.label,
                Style::default().add_modifier(if self.focused {
                    Modifier::BOLD
                } else {
                    Modifier::empty()
                }),
            ),
        ]);

        let border_color = if self.focused {
            Color::Yellow
        } else {
            Color::White
        };

        let widget = Paragraph::new(text).block(
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

    #[test]
    fn test_checkbox_creation() {
        let checkbox = Checkbox::new("Test Option", false);
        assert_eq!(checkbox.label, "Test Option");
        assert!(!checkbox.is_checked());
        assert!(!checkbox.is_focused());
    }

    #[test]
    fn test_checkbox_toggle() {
        let mut checkbox = Checkbox::new("Test", false);
        assert!(!checkbox.is_checked());

        checkbox.toggle();
        assert!(checkbox.is_checked());

        checkbox.toggle();
        assert!(!checkbox.is_checked());
    }

    #[test]
    fn test_checkbox_set_checked() {
        let mut checkbox = Checkbox::new("Test", false);

        checkbox.set_checked(true);
        assert!(checkbox.is_checked());

        checkbox.set_checked(false);
        assert!(!checkbox.is_checked());
    }

    #[test]
    fn test_checkbox_focus() {
        let mut checkbox = Checkbox::new("Test", false);
        assert!(!checkbox.is_focused());

        checkbox.set_focused(true);
        assert!(checkbox.is_focused());

        checkbox.set_focused(false);
        assert!(!checkbox.is_focused());
    }
}
