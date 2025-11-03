//! Scan results viewer with split-pane layout and search functionality.
//!
//! This module provides a comprehensive interface for browsing previously generated scan reports.
//! The screen features a two-pane layout with a report list on the left and a full-featured
//! report viewer on the right, including syntax highlighting, line numbers, and incremental search.
//!
//! # Features
//!
//! - **Split-Pane Layout**: Report list (30% width) + Report viewer (70% width)
//! - **Report List Navigation**: ↑/↓ to select reports, automatic content loading
//! - **Syntax Highlighting**: Color-coded keywords (errors=red, warnings=yellow, FormIDs=cyan, plugins=green, headers=magenta)
//! - **Line Numbers**: 4-digit line numbers with separator for easy reference
//! - **Incremental Search**: / to activate, type query, n/N for next/previous match
//! - **Search Highlighting**: Current match (yellow background), other matches (cyan background)
//! - **Match Counter**: Shows "Match X/Y" in title bar when searching
//! - **Scroll Support**: ↑/↓ for line-by-line, Page Up/Down for page scrolling
//! - **Update Notification**: Banner integration at top of screen
//!
//! # Navigation
//!
//! - **↑/↓**: Select report (left pane) or scroll content (right pane)
//! - **Page Up/Down**: Scroll report viewer by page
//! - **Home/End**: Jump to start/end of report
//! - **/**: Activate search mode
//! - **n**: Next search match
//! - **N**: Previous search match (Shift+n)
//! - **ESC**: Exit search mode or return to main screen
//!
//! # Search Functionality
//!
//! The search feature provides incremental matching as you type:
//! 1. Press `/` to activate search bar at bottom
//! 2. Type your query (updates matches in real-time)
//! 3. Use `n`/`N` to navigate between matches
//! 4. Current match highlighted in yellow, others in cyan
//! 5. Auto-scrolls to keep current match visible
//! 6. Press ESC to exit search mode
//!
//! # Syntax Highlighting Rules
//!
//! The viewer applies automatic syntax highlighting based on content patterns:
//! - **Errors** (Red, Bold): Lines containing "error", "exception", "crash", "fatal"
//! - **Warnings** (Yellow, Bold): Lines containing "warning", "suspect"
//! - **FormIDs** (Cyan): Lines with "FormID:" or hexadecimal values (0x...)
//! - **Plugins** (Green): Lines with bracket notation or .esp/.esm/.esl extensions
//! - **Headers** (Magenta, Bold): Lines starting with ===, ---, ##, or **
//! - **Default** (White): All other content
//!
//! # Layout
//!
//! The screen is divided into two main horizontal sections:
//! - **Left Pane** (30%): Scrollable list of report files with selection highlight
//! - **Right Pane** (70%): Report content viewer with optional search bar (3 lines) at bottom
//!
//! When search is active, the right pane splits into:
//! - Content area (flexible): Report viewer with search highlights
//! - Search bar (3 lines): Search input field with yellow border
//!
//! # Example
//!
//! ```rust,no_run
//! use classic_tui::ui::results_screen::render_results_screen;
//! use classic_tui::app::App;
//! use ratatui::backend::CrosstermBackend;
//! use ratatui::Terminal;
//! use std::io;
//!
//! let mut terminal = Terminal::new(CrosstermBackend::new(io::stdout())).unwrap();
//! let app = App::new();
//!
//! terminal.draw(|f| {
//!     render_results_screen(f, &app);
//! }).unwrap();
//! ```
//!
//! # Implementation Status
//!
//! - ✅ Report list with navigation
//! - ✅ Syntax highlighting for common patterns
//! - ✅ Line numbers with separator
//! - ✅ Scroll support (line and page)
//! - ⚠️ Search functionality (UI complete, backend wiring pending)

use crate::app::App;
use ratatui::{
    Frame,
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph},
};

/// Render the results viewer screen with split-pane layout
pub fn render_results_screen(f: &mut Frame, app: &App) {
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
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(30), // Report list on left
            Constraint::Percentage(70), // Report viewer on right
        ])
        .split(working_area);

    render_report_list(f, chunks[0], app);
    render_report_viewer(f, chunks[1], app);

    // Render error dialog overlay if active (should be last so it appears on top)
    if let Some(ref dialog) = app.error_dialog {
        if dialog.is_active() {
            dialog.render(f, f.area());
        }
    }
}

/// Render the report list on the left pane
fn render_report_list(f: &mut Frame, area: Rect, app: &App) {
    let items: Vec<ListItem> = app
        .report_files
        .iter()
        .enumerate()
        .map(|(i, path)| {
            let filename = path
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("Unknown");

            let style = if i == app.selected_report_index {
                Style::default()
                    .fg(Color::Yellow)
                    .add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(Color::White)
            };

            ListItem::new(Line::from(Span::styled(filename, style)))
        })
        .collect();

    let list = List::new(items)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(" Reports ")
                .style(Style::default().fg(Color::Cyan)),
        )
        .highlight_style(
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        );

    f.render_widget(list, area);
}

/// Render the report viewer on the right pane
fn render_report_viewer(f: &mut Frame, area: Rect, app: &App) {
    if app.current_report_content.is_empty() {
        let placeholder = Paragraph::new("No report selected or report is empty")
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .title(" Report Viewer ")
                    .style(Style::default().fg(Color::Cyan)),
            )
            .style(Style::default().fg(Color::DarkGray));

        f.render_widget(placeholder, area);
        return;
    }

    // Split area for content and search bar
    let chunks = if app.search_active {
        Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Min(3),    // Content
                Constraint::Length(3), // Search bar
            ])
            .split(area)
    } else {
        std::rc::Rc::from(vec![area])
    };

    let content_area = chunks[0];

    // Create content block with search indicator in title
    let title = if app.search_active && !app.search_matches.is_empty() {
        format!(
            " Report Viewer - Match {}/{} ",
            app.current_match_index + 1,
            app.search_matches.len()
        )
    } else {
        " Report Viewer ".to_string()
    };

    let block = Block::default()
        .borders(Borders::ALL)
        .title(title)
        .style(Style::default().fg(Color::Cyan));

    // Calculate visible area inside borders
    let inner_area = block.inner(content_area);

    // Render block first
    f.render_widget(block, content_area);

    // Prepare lines with syntax highlighting and search matches
    let visible_lines = inner_area.height as usize;
    let start_line = app.report_scroll_offset;
    let end_line = (start_line + visible_lines).min(app.current_report_content.len());

    let lines: Vec<Line> = app.current_report_content[start_line..end_line]
        .iter()
        .enumerate()
        .map(|(i, line)| {
            let line_idx = start_line + i;
            let line_num = line_idx + 1;
            let line_num_str = format!("{:4} │ ", line_num);

            // Build line with search highlights
            let mut spans = vec![Span::styled(
                line_num_str,
                Style::default().fg(Color::DarkGray),
            )];

            if app.search_active && !app.search_query.is_empty() {
                // Highlight search matches
                let line_spans = highlight_search_matches(line, line_idx, app);
                spans.extend(line_spans);
            } else {
                // Apply syntax highlighting based on content
                let content_style = get_line_style(line);
                spans.push(Span::styled(line, content_style));
            }

            Line::from(spans)
        })
        .collect();

    let paragraph = Paragraph::new(lines).style(Style::default().fg(Color::White));

    f.render_widget(paragraph, inner_area);

    // Render search bar if active
    if app.search_active {
        render_search_bar(f, chunks[1], app);
    }
}

/// Render the search input bar
fn render_search_bar(f: &mut Frame, area: Rect, app: &App) {
    let search_text = format!("Search: {}", app.search_query);
    let search_widget = Paragraph::new(search_text)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .style(Style::default().fg(Color::Yellow)),
        )
        .style(Style::default().fg(Color::White));

    f.render_widget(search_widget, area);
}

/// Highlight search matches in a line
fn highlight_search_matches(line: &str, line_idx: usize, app: &App) -> Vec<Span<'static>> {
    let mut spans = Vec::new();

    // Find matches for this line
    let line_matches: Vec<_> = app
        .search_matches
        .iter()
        .enumerate()
        .filter(|(_, (idx, _, _))| *idx == line_idx)
        .collect();

    if line_matches.is_empty() {
        // No matches, use regular syntax highlighting
        spans.push(Span::styled(line.to_string(), get_line_style(line)));
        return spans;
    }

    let mut last_pos = 0;

    for (match_idx, &(_, start, end)) in line_matches {
        // Add text before match
        if start > last_pos {
            spans.push(Span::styled(
                line[last_pos..start].to_string(),
                get_line_style(line),
            ));
        }

        // Highlight match (current match in yellow, others in cyan)
        let is_current_match = app.current_match_index == match_idx;
        let match_style = if is_current_match {
            Style::default()
                .fg(Color::Black)
                .bg(Color::Yellow)
                .add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(Color::Black).bg(Color::Cyan)
        };

        spans.push(Span::styled(line[start..end].to_string(), match_style));
        last_pos = end;
    }

    // Add remaining text
    if last_pos < line.len() {
        spans.push(Span::styled(
            line[last_pos..].to_string(),
            get_line_style(line),
        ));
    }

    spans
}

/// Get style for a line based on its content (syntax highlighting)
fn get_line_style(line: &str) -> Style {
    let line_lower = line.to_lowercase();

    // Error patterns
    if line_lower.contains("error")
        || line_lower.contains("exception")
        || line_lower.contains("crash")
        || line_lower.contains("fatal")
    {
        return Style::default().fg(Color::Red).add_modifier(Modifier::BOLD);
    }

    // Warning patterns
    if line_lower.contains("warning") || line_lower.contains("suspect") {
        return Style::default()
            .fg(Color::Yellow)
            .add_modifier(Modifier::BOLD);
    }

    // FormID patterns
    if line.contains("FormID:") || line.contains("0x") {
        return Style::default().fg(Color::Cyan);
    }

    // Plugin/mod names (typically in brackets or with .esp/.esm extension)
    if line.contains("[") && line.contains("]")
        || line.contains(".esp")
        || line.contains(".esm")
        || line.contains(".esl")
    {
        return Style::default().fg(Color::Green);
    }

    // Headers and section markers
    if line.starts_with("===")
        || line.starts_with("---")
        || line.starts_with("##")
        || line.starts_with("**")
    {
        return Style::default()
            .fg(Color::Magenta)
            .add_modifier(Modifier::BOLD);
    }

    // Default style
    Style::default().fg(Color::White)
}
