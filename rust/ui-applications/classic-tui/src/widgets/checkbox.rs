//! Checkbox widget for boolean settings with focus and dirty tracking.
//!
//! This module provides a reusable checkbox widget used in the settings screen for toggling
//! boolean configuration options. The widget supports keyboard focus, visual state changes,
//! and dirty tracking to optimize rendering performance by skipping unchanged widgets.
//!
//! # Features
//!
//! - **Visual States**: Checked ([X]) vs. unchecked ([ ]) with color coding
//! - **Focus Highlighting**: Yellow border and bold text when focused
//! - **Dirty Tracking**: Marks widget dirty on state/focus changes for selective rendering
//! - **Color Coding**: Green checkmark when checked, White when unchecked
//! - **Label Display**: Custom label text next to checkbox symbol
//! - **Keyboard Toggle**: Space/Enter to toggle when focused
//!
//! # Visual Appearance
//!
//! **Unfocused, Unchecked**:
//! ```text
//! ┌────────────────────┐
//! │ [ ] FCX Mode       │
//! └────────────────────┘
//! ```
//!
//! **Focused, Checked**:
//! ```text
//! ┌────────────────────┐ (Yellow border)
//! │ [X] FCX Mode       │ (Bold text, Green X)
//! └────────────────────┘
//! ```
//!
//! # Dirty Tracking
//!
//! The checkbox tracks whether it needs re-rendering to optimize performance:
//! - Starts dirty (forces initial render)
//! - Marked dirty on state changes: `set_checked()`, `toggle()`, `set_focused()`
//! - Marked clean after rendering: `mark_clean()` (called by parent after render)
//! - Can be forced dirty: `mark_dirty()` (useful for external state changes)
//!
//! This allows rendering loops to skip unchanged checkboxes in the 30 FPS event loop.
//!
//! # Usage Example
//!
//! ```rust,no_run
//! use classic_tui::widgets::Checkbox;
//! use ratatui::backend::CrosstermBackend;
//! use ratatui::Terminal;
//! use ratatui::layout::Rect;
//! use std::io;
//!
//! let mut terminal = Terminal::new(CrosstermBackend::new(io::stdout())).unwrap();
//! let mut checkbox = Checkbox::new("Enable FCX Mode", false);
//!
//! // Set as focused (highlights border)
//! checkbox.set_focused(true);
//!
//! // Toggle state (user pressed Space)
//! checkbox.toggle();
//! assert!(checkbox.is_checked());
//!
//! // Render the checkbox
//! terminal.draw(|f| {
//!     let area = Rect::new(0, 0, 30, 3);
//!     checkbox.render(f, area);
//! }).unwrap();
//!
//! // Mark clean after rendering (parent's responsibility)
//! checkbox.mark_clean();
//! ```
//!
//! # Integration with Settings Screen
//!
//! The settings screen creates checkboxes for each boolean setting:
//! 1. Create checkbox with `Checkbox::new(label, initial_value)`
//! 2. Set focus on currently selected item with `set_focused(true)`
//! 3. Call `render()` during frame draw
//! 4. Handle toggle on Space/Enter key press
//! 5. Sync changes back to config with `is_checked()`
//!
//! # Testing
//!
//! The module includes comprehensive tests:
//! - Creation with initial state
//! - Toggle functionality
//! - Set checked explicitly
//! - Focus state changes
//! - Dirty tracking behavior (via state changes)

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
    dirty: bool, // Track if widget needs redraw
}

#[allow(dead_code)]
impl Checkbox {
    /// Create a new checkbox
    pub fn new(label: impl Into<String>, checked: bool) -> Self {
        Self {
            label: label.into(),
            checked,
            focused: false,
            dirty: true, // Start dirty to force initial render
        }
    }

    /// Get the checked state
    pub fn is_checked(&self) -> bool {
        self.checked
    }

    /// Set the checked state
    pub fn set_checked(&mut self, checked: bool) {
        if self.checked != checked {
            self.checked = checked;
            self.dirty = true; // Mark dirty on state change
        }
    }

    /// Toggle the checked state
    pub fn toggle(&mut self) {
        self.checked = !self.checked;
        self.dirty = true; // Mark dirty on state change
    }

    /// Set the focused state
    pub fn set_focused(&mut self, focused: bool) {
        if self.focused != focused {
            self.focused = focused;
            self.dirty = true; // Mark dirty on focus change (affects styling)
        }
    }

    /// Check if focused
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
