//! Shared layout utilities and responsive sizing for TUI screens.
//!
//! This module provides a centralized layout management system for the CLASSIC TUI application.
//! It handles responsive sizing, minimum terminal size validation, and provides reusable layout
//! functions for common UI patterns like centered popups and split-pane layouts.
//!
//! # Features
//!
//! - **Responsive Layouts**: Adapts to terminal size with compact mode for small terminals (<30 lines)
//! - **Main Screen Layout**: 5-section vertical layout (header, folders, buttons, output, status)
//! - **Folder Section**: 2-row vertical split for staging and custom folder selectors
//! - **Button Row**: 4-column horizontal split for action buttons
//! - **Centered Popups**: Percentage-based popup positioning for dialogs and overlays
//! - **Minimum Size Validation**: Enforces 80x24 minimum terminal size with helpful error messages
//!
//! # Layout Strategies
//!
//! The module implements two layout strategies based on terminal height:
//!
//! ## Standard Layout (>= 30 lines)
//! Uses fixed heights and percentage-based sizing for optimal appearance:
//! - Header: 3 lines
//! - Folders: 15% of height
//! - Buttons: 3 lines
//! - Output: Remaining space (min 10 lines)
//! - Status: 1 line
//!
//! ## Compact Layout (< 30 lines)
//! Uses minimum constraints to ensure usability on small terminals:
//! - Header: Min 3 lines
//! - Folders: Min 6 lines
//! - Buttons: Min 3 lines
//! - Output: Min 8 lines (critical for readability)
//! - Status: 1 line
//!
//! # Terminal Size Requirements
//!
//! - **Minimum Width**: 80 columns (ensures buttons and labels fit)
//! - **Minimum Height**: 24 lines (ensures all UI elements are visible)
//! - **Recommended**: 100x30 or larger for optimal experience
//!
//! # Example Usage
//!
//! ```rust,no_run
//! use classic_tui::ui::layout::TuiLayout;
//! use ratatui::layout::Rect;
//!
//! // Create main screen layout
//! let area = Rect::new(0, 0, 100, 40);
//! let (header, folders, buttons, output, status) = TuiLayout::main_screen(area);
//!
//! // Create a centered popup (50% width, 50% height)
//! let popup = TuiLayout::centered_rect(50, 50, area);
//!
//! // Validate terminal size
//! let (is_valid, width_msg, height_msg) = TuiLayout::check_minimum_size(area);
//! if !is_valid {
//!     // Display error messages to user
//!     println!("{}", width_msg.unwrap_or_default());
//!     println!("{}", height_msg.unwrap_or_default());
//! }
//! ```
//!
//! # Testing
//!
//! The module includes comprehensive tests for:
//! - Standard vs. compact layout behavior
//! - Folder section 50/50 split
//! - Button row 25/25/25/25 split
//! - Centered popup positioning
//! - Minimum size validation (width, height, both)

use ratatui::layout::{Constraint, Direction, Layout, Rect};

/// Layout constants for the TUI
pub struct TuiLayout;

impl TuiLayout {
    /// Create the main screen layout with responsive sizing
    /// Returns: (header, folder_section, buttons, output, status_bar)
    pub fn main_screen(area: Rect) -> (Rect, Rect, Rect, Rect, Rect) {
        // Adaptive layout based on terminal height
        let chunks = if area.height < 30 {
            // Compact layout for small terminals (< 30 lines)
            Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Min(3),        // Header (min 3 lines)
                    Constraint::Min(6),        // Folder selectors (min 6 lines, 2x3)
                    Constraint::Min(3),        // Scan buttons (min 3 lines)
                    Constraint::Min(8),        // Output viewer (min 8 lines for readability)
                    Constraint::Length(1),     // Status bar (always 1 line)
                ])
                .split(area)
        } else {
            // Standard layout for normal terminals (>= 30 lines)
            Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Length(3),     // Header (3 lines)
                    Constraint::Percentage(15), // Folder selectors (~15% of height)
                    Constraint::Length(3),     // Scan buttons (3 lines)
                    Constraint::Min(10),       // Output viewer (remaining space, min 10)
                    Constraint::Length(1),     // Status bar (1 line)
                ])
                .split(area)
        };

        (chunks[0], chunks[1], chunks[2], chunks[3], chunks[4])
    }

    /// Create the folder section layout with responsive sizing
    /// Returns: (staging_folder, custom_folder)
    pub fn folder_section(area: Rect) -> (Rect, Rect) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Percentage(50), // Staging mods folder (50% of section)
                Constraint::Percentage(50), // Custom scan folder (50% of section)
            ])
            .split(area);

        (chunks[0], chunks[1])
    }

    /// Create the button row layout
    /// Returns: (crash_scan, game_scan, papyrus, update_check)
    pub fn button_row(area: Rect) -> (Rect, Rect, Rect, Rect) {
        let chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Percentage(25), // Crash Logs Scan
                Constraint::Percentage(25), // Game Files Scan
                Constraint::Percentage(25), // Papyrus Monitor
                Constraint::Percentage(25), // Check for Updates
            ])
            .split(area);

        (chunks[0], chunks[1], chunks[2], chunks[3])
    }

    /// Create a centered popup area
    pub fn centered_rect(percent_x: u16, percent_y: u16, area: Rect) -> Rect {
        let popup_layout = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Percentage((100 - percent_y) / 2),
                Constraint::Percentage(percent_y),
                Constraint::Percentage((100 - percent_y) / 2),
            ])
            .split(area);

        Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Percentage((100 - percent_x) / 2),
                Constraint::Percentage(percent_x),
                Constraint::Percentage((100 - percent_x) / 2),
            ])
            .split(popup_layout[1])[1]
    }

    /// Check if terminal size meets minimum requirements
    ///
    /// Returns (is_valid, width_msg, height_msg)
    pub fn check_minimum_size(area: Rect) -> (bool, Option<String>, Option<String>) {
        const MIN_WIDTH: u16 = 80;
        const MIN_HEIGHT: u16 = 24;

        let width_ok = area.width >= MIN_WIDTH;
        let height_ok = area.height >= MIN_HEIGHT;

        let width_msg = if !width_ok {
            Some(format!(
                "Terminal width too small: {} (minimum: {})",
                area.width, MIN_WIDTH
            ))
        } else {
            None
        };

        let height_msg = if !height_ok {
            Some(format!(
                "Terminal height too small: {} (minimum: {})",
                area.height, MIN_HEIGHT
            ))
        } else {
            None
        };

        (width_ok && height_ok, width_msg, height_msg)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_main_screen_layout_standard() {
        // Test standard layout (>= 30 lines)
        let area = Rect::new(0, 0, 100, 50);
        let (header, folders, buttons, output, status) = TuiLayout::main_screen(area);

        assert_eq!(header.height, 3);
        assert!(folders.height > 0); // Percentage-based, ~15% of 50 = 7-8 lines
        assert_eq!(buttons.height, 3);
        assert!(output.height >= 10);
        assert_eq!(status.height, 1);
    }

    #[test]
    fn test_main_screen_layout_compact() {
        // Test compact layout (< 30 lines)
        let area = Rect::new(0, 0, 100, 25);
        let (header, folders, buttons, output, status) = TuiLayout::main_screen(area);

        assert!(header.height >= 3);
        assert!(folders.height >= 6);
        assert!(buttons.height >= 3);
        assert!(output.height >= 8);
        assert_eq!(status.height, 1);
    }

    #[test]
    fn test_folder_section_layout() {
        let area = Rect::new(0, 0, 100, 10);
        let (staging, custom) = TuiLayout::folder_section(area);

        // Each folder gets 50% of the section height
        assert_eq!(staging.height, 5);
        assert_eq!(custom.height, 5);
    }

    #[test]
    fn test_button_row_layout() {
        let area = Rect::new(0, 0, 100, 3);
        let (crash, game, papyrus, update) = TuiLayout::button_row(area);

        // Each button should get 25% of the width
        assert!(crash.width >= 20 && crash.width <= 30);
        assert!(game.width >= 20 && game.width <= 30);
        assert!(papyrus.width >= 20 && papyrus.width <= 30);
        assert!(update.width >= 20 && update.width <= 30);
    }

    #[test]
    fn test_centered_rect() {
        let area = Rect::new(0, 0, 100, 50);
        let popup = TuiLayout::centered_rect(50, 50, area);

        // Should be roughly centered
        assert!(popup.x > 0 && popup.x < 50);
        assert!(popup.y > 0 && popup.y < 25);
        assert!(popup.width > 0 && popup.width <= 50);
        assert!(popup.height > 0 && popup.height <= 25);
    }

    #[test]
    fn test_minimum_size_ok() {
        let area = Rect::new(0, 0, 100, 50);
        let (is_valid, width_msg, height_msg) = TuiLayout::check_minimum_size(area);

        assert!(is_valid);
        assert!(width_msg.is_none());
        assert!(height_msg.is_none());
    }

    #[test]
    fn test_minimum_size_too_small() {
        let area = Rect::new(0, 0, 60, 20);
        let (is_valid, width_msg, height_msg) = TuiLayout::check_minimum_size(area);

        assert!(!is_valid);
        assert!(width_msg.is_some());
        assert!(height_msg.is_some());
        assert!(width_msg.unwrap().contains("60"));
        assert!(height_msg.unwrap().contains("20"));
    }

    #[test]
    fn test_minimum_size_width_ok_height_small() {
        let area = Rect::new(0, 0, 100, 20);
        let (is_valid, width_msg, height_msg) = TuiLayout::check_minimum_size(area);

        assert!(!is_valid);
        assert!(width_msg.is_none());
        assert!(height_msg.is_some());
    }
}
