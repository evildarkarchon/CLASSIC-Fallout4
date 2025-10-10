use ratatui::{
    layout::Rect,
    style::{Color, Style},
    text::Line,
    widgets::{Block, Borders, Paragraph, Wrap},
    Frame,
};

/// Widget for displaying scrollable output text
pub struct OutputViewer {
    lines: Vec<String>,
    scroll_offset: usize,
    search_query: Option<String>,
    max_lines: usize,
}

impl OutputViewer {
    /// Create a new output viewer
    pub fn new() -> Self {
        Self {
            lines: Vec::new(),
            scroll_offset: 0,
            search_query: None,
            max_lines: 10000, // Limit to prevent memory issues
        }
    }

    /// Append a line to the output
    pub fn append(&mut self, line: String) {
        self.lines.push(line);

        // Trim old lines if we exceed max
        if self.lines.len() > self.max_lines {
            let excess = self.lines.len() - self.max_lines;
            self.lines.drain(0..excess);
            // Adjust scroll offset
            self.scroll_offset = self.scroll_offset.saturating_sub(excess);
        }

        // Auto-scroll to bottom
        self.scroll_offset = self.lines.len().saturating_sub(1);
    }

    /// Clear all output
    pub fn clear(&mut self) {
        self.lines.clear();
        self.scroll_offset = 0;
    }

    /// Scroll up by the specified number of lines
    pub fn scroll_up(&mut self, lines: usize) {
        self.scroll_offset = self.scroll_offset.saturating_sub(lines);
    }

    /// Scroll down by the specified number of lines
    pub fn scroll_down(&mut self, lines: usize, visible_lines: usize) {
        let max_scroll = self.lines.len().saturating_sub(visible_lines);
        self.scroll_offset = (self.scroll_offset + lines).min(max_scroll);
    }

    /// Set search query (not yet implemented in rendering)
    pub fn search(&mut self, query: String) {
        self.search_query = Some(query);
    }

    /// Clear search query
    pub fn clear_search(&mut self) {
        self.search_query = None;
    }

    /// Get the current number of lines
    pub fn line_count(&self) -> usize {
        self.lines.len()
    }

    /// Render the output viewer widget
    pub fn render(&self, f: &mut Frame, area: Rect) {
        let content_height = area.height.saturating_sub(2) as usize; // Account for borders
        let total_lines = self.lines.len();

        // Determine visible range
        let start_line = self.scroll_offset;
        let end_line = (start_line + content_height).min(total_lines);

        let visible_lines: Vec<Line> = if total_lines == 0 {
            vec![
                Line::from(""),
                Line::from("Waiting for scan..."),
                Line::from(""),
                Line::from("(Press F5 for Crash Scan, F6 for Game Scan)"),
            ]
        } else {
            self.lines[start_line..end_line]
                .iter()
                .map(|s| Line::from(s.as_str()))
                .collect()
        };

        let title = if total_lines > 0 {
            format!(
                " OUTPUT VIEWER (Lines {}-{} of {}) ",
                start_line + 1,
                end_line,
                total_lines
            )
        } else {
            " OUTPUT VIEWER ".to_string()
        };

        let widget = Paragraph::new(visible_lines)
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .title(title)
                    .border_style(Style::default().fg(Color::White)),
            )
            .wrap(Wrap { trim: false });

        f.render_widget(widget, area);
    }
}

impl Default for OutputViewer {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_output_viewer_creation() {
        let viewer = OutputViewer::new();
        assert_eq!(viewer.line_count(), 0);
        assert_eq!(viewer.scroll_offset, 0);
    }

    #[test]
    fn test_append_lines() {
        let mut viewer = OutputViewer::new();

        viewer.append("Line 1".to_string());
        viewer.append("Line 2".to_string());
        viewer.append("Line 3".to_string());

        assert_eq!(viewer.line_count(), 3);
        // Should auto-scroll to bottom
        assert_eq!(viewer.scroll_offset, 2);
    }

    #[test]
    fn test_clear() {
        let mut viewer = OutputViewer::new();
        viewer.append("Test".to_string());
        assert_eq!(viewer.line_count(), 1);

        viewer.clear();
        assert_eq!(viewer.line_count(), 0);
        assert_eq!(viewer.scroll_offset, 0);
    }

    #[test]
    fn test_scroll_operations() {
        let mut viewer = OutputViewer::new();

        for i in 0..20 {
            viewer.append(format!("Line {}", i));
        }

        // Scroll up
        viewer.scroll_up(5);
        assert_eq!(viewer.scroll_offset, 14); // Was at 19, scroll up 5

        // Scroll down (limited by max_scroll = 20 - 10 = 10)
        viewer.scroll_down(3, 10);
        assert_eq!(viewer.scroll_offset, 10); // Clamped to max (14 + 3 would be 17, but max is 10)

        // Scroll up to top
        viewer.scroll_up(100);
        assert_eq!(viewer.scroll_offset, 0);
    }

    #[test]
    fn test_max_lines_limit() {
        let mut viewer = OutputViewer::new();
        viewer.max_lines = 100;

        // Add more than max_lines
        for i in 0..150 {
            viewer.append(format!("Line {}", i));
        }

        // Should be limited to max_lines
        assert_eq!(viewer.line_count(), 100);

        // Should contain the most recent lines (50-149)
        assert!(viewer.lines[0].contains("50"));
        assert!(viewer.lines[99].contains("149"));
    }

    #[test]
    fn test_search_functionality() {
        let mut viewer = OutputViewer::new();
        assert!(viewer.search_query.is_none());

        viewer.search("test query".to_string());
        assert_eq!(viewer.search_query, Some("test query".to_string()));

        viewer.clear_search();
        assert!(viewer.search_query.is_none());
    }
}
