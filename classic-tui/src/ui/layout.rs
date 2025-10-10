use ratatui::layout::{Constraint, Direction, Layout, Rect};

/// Layout constants for the TUI
pub struct TuiLayout;

impl TuiLayout {
    /// Create the main screen layout
    /// Returns: (header, folder_section, buttons, output, status_bar)
    pub fn main_screen(area: Rect) -> (Rect, Rect, Rect, Rect, Rect) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // Header
                Constraint::Length(8), // Folder selectors
                Constraint::Length(3), // Scan buttons
                Constraint::Min(10),   // Output viewer
                Constraint::Length(1), // Status bar
            ])
            .split(area);

        (chunks[0], chunks[1], chunks[2], chunks[3], chunks[4])
    }

    /// Create the folder section layout
    /// Returns: (staging_folder, custom_folder)
    pub fn folder_section(area: Rect) -> (Rect, Rect) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(4), // Staging mods folder
                Constraint::Length(4), // Custom scan folder
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
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_main_screen_layout() {
        let area = Rect::new(0, 0, 100, 50);
        let (header, folders, buttons, output, status) = TuiLayout::main_screen(area);

        assert_eq!(header.height, 3);
        assert_eq!(folders.height, 8);
        assert_eq!(buttons.height, 3);
        assert!(output.height >= 10);
        assert_eq!(status.height, 1);
    }

    #[test]
    fn test_folder_section_layout() {
        let area = Rect::new(0, 0, 100, 8);
        let (staging, custom) = TuiLayout::folder_section(area);

        assert_eq!(staging.height, 4);
        assert_eq!(custom.height, 4);
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
}
