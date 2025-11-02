//! Update notification banner widget.
//!
//! This module provides a non-intrusive notification banner that displays
//! when a new version of CLASSIC is available.

use crate::handlers::update_handler::UpdateInfo;
use ratatui::{
    layout::{Alignment, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

/// Update notification state and display.
///
/// Displays a banner at the top of the screen when an update is available,
/// with keyboard shortcuts to view details or dismiss the notification.
#[derive(Debug, Clone)]
pub struct UpdateNotification {
    /// Information about the available update
    pub update_info: UpdateInfo,
    /// Whether the notification is currently visible
    pub visible: bool,
}

impl UpdateNotification {
    /// Create a new update notification.
    ///
    /// # Arguments
    ///
    /// * `update_info` - Information about the available update
    ///
    /// # Examples
    ///
    /// ```no_run
    /// use classic_tui::widgets::update_notification::UpdateNotification;
    /// use classic_tui::handlers::update_handler::UpdateInfo;
    ///
    /// let update_info = UpdateInfo {
    ///     version: "v1.2.3".to_string(),
    ///     name: "CLASSIC v1.2.3".to_string(),
    ///     body: "Bug fixes and improvements".to_string(),
    ///     html_url: "https://github.com/...".to_string(),
    ///     prerelease: false,
    /// };
    ///
    /// let notification = UpdateNotification::new(update_info);
    /// ```
    pub fn new(update_info: UpdateInfo) -> Self {
        Self {
            update_info,
            visible: true,
        }
    }

    /// Show the notification (make it visible).
    pub fn show(&mut self) {
        self.visible = true;
    }

    /// Hide the notification (dismiss it).
    pub fn hide(&mut self) {
        self.visible = false;
    }

    /// Check if the notification is currently visible.
    pub fn is_visible(&self) -> bool {
        self.visible
    }

    /// Render the update notification banner.
    ///
    /// Displays at the top of the screen with update information and
    /// keyboard shortcuts. Banner is styled differently for prereleases.
    ///
    /// # Arguments
    ///
    /// * `f` - Terminal frame to draw on
    /// * `area` - Full screen area (banner will be positioned at top)
    pub fn render(&self, f: &mut Frame, area: Rect) {
        if !self.visible {
            return;
        }

        // Create banner area at top of screen (3 lines tall)
        let banner_area = Rect {
            x: area.x,
            y: area.y,
            width: area.width,
            height: 3,
        };

        // Color and symbol based on prerelease status
        let (border_color, symbol, version_label) = if self.update_info.prerelease {
            (Color::Yellow, "⚠", "Pre-release")
        } else {
            (Color::Green, "↑", "Update Available")
        };

        // Create banner block with colored border
        let block = Block::default()
            .borders(Borders::ALL)
            .border_style(
                Style::default()
                    .fg(border_color)
                    .add_modifier(Modifier::BOLD),
            );

        // Build notification text
        let notification_text = vec![Line::from(vec![
            Span::styled(
                format!(" {} ", symbol),
                Style::default()
                    .fg(border_color)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(
                version_label,
                Style::default()
                    .fg(border_color)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::raw(": "),
            Span::styled(
                &self.update_info.version,
                Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
            ),
            Span::raw(" - "),
            Span::styled(&self.update_info.name, Style::default().fg(Color::White)),
            Span::raw("   "),
            Span::styled(
                "U",
                Style::default()
                    .fg(Color::Yellow)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::raw(" View Details | "),
            Span::styled(
                "D",
                Style::default()
                    .fg(Color::Yellow)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::raw(" Dismiss"),
        ])];

        let paragraph = Paragraph::new(notification_text)
            .block(block)
            .alignment(Alignment::Left);

        f.render_widget(paragraph, banner_area);
    }

    /// Get the height of the notification banner when visible.
    ///
    /// # Returns
    ///
    /// Returns 3 if visible, 0 if hidden.
    pub fn height(&self) -> u16 {
        if self.visible {
            3
        } else {
            0
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_update_info() -> UpdateInfo {
        UpdateInfo {
            version: "v1.2.3".to_string(),
            name: "CLASSIC v1.2.3".to_string(),
            body: "Bug fixes and improvements".to_string(),
            html_url: "https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/tag/v1.2.3"
                .to_string(),
            prerelease: false,
        }
    }

    #[test]
    fn test_update_notification_new() {
        let update_info = create_test_update_info();
        let notification = UpdateNotification::new(update_info.clone());

        assert_eq!(notification.update_info, update_info);
        assert!(notification.visible);
    }

    #[test]
    fn test_update_notification_show_hide() {
        let update_info = create_test_update_info();
        let mut notification = UpdateNotification::new(update_info);

        assert!(notification.is_visible());

        notification.hide();
        assert!(!notification.is_visible());

        notification.show();
        assert!(notification.is_visible());
    }

    #[test]
    fn test_update_notification_height() {
        let update_info = create_test_update_info();
        let mut notification = UpdateNotification::new(update_info);

        assert_eq!(notification.height(), 3);

        notification.hide();
        assert_eq!(notification.height(), 0);

        notification.show();
        assert_eq!(notification.height(), 3);
    }

    #[test]
    fn test_prerelease_notification() {
        let mut update_info = create_test_update_info();
        update_info.prerelease = true;

        let notification = UpdateNotification::new(update_info);
        assert!(notification.update_info.prerelease);
    }
}
