use ratatui::Frame;
use ratatui::layout::{Constraint, Layout, Rect};
use ratatui::style::{Modifier, Style};
use ratatui::text::Line;
use ratatui::widgets::{Block, BorderType, Borders, Paragraph};

use crate::app::{ReportEntry, ResultsFocus};
use crate::results_markdown::MarkdownLink;
use crate::theme;

#[derive(Clone, Copy)]
pub struct ViewerLinkHitArea {
    pub link_index: usize,
    pub area: Rect,
}

#[derive(Default)]
pub struct ResultsClickAreas {
    pub search_input: Rect,
    pub sort_header: Rect,
    pub list_rows: Vec<(usize, Rect)>,
    pub refresh_button: Rect,
    pub delete_button: Rect,
    pub open_button: Rect,
    pub copy_button: Rect,
    pub viewer_area: Rect,
    pub viewer_viewport_height: usize,
    pub viewer_link_areas: Vec<ViewerLinkHitArea>,
    pub empty_scan_button: Rect,
}

pub struct ResultsTabRenderData<'a> {
    pub reports: &'a [ReportEntry],
    pub filtered_indices: &'a [usize],
    pub selected_filtered: Option<usize>,
    pub search_query: &'a str,
    pub sort_ascending: bool,
    pub focus: ResultsFocus,
    pub rendered_lines: &'a [Line<'static>],
    pub rendered_links: &'a [MarkdownLink],
    pub active_link_index: Option<usize>,
    pub scroll_offset: usize,
    pub list_panel_width: u16,
}

pub fn render_results_tab(
    frame: &mut Frame<'_>,
    content_area: Rect,
    data: &ResultsTabRenderData<'_>,
) -> ResultsClickAreas {
    if data.filtered_indices.is_empty() {
        return render_empty_results(frame, content_area);
    }

    let [left_panel, right_panel] = Layout::horizontal([
        Constraint::Length(data.list_panel_width.max(30)),
        Constraint::Min(30),
    ])
    .areas(content_area);

    let mut click_areas = ResultsClickAreas::default();

    let [search_area, sort_area, list_area, actions_area] = Layout::vertical([
        Constraint::Length(3),
        Constraint::Length(1),
        Constraint::Min(6),
        Constraint::Length(3),
    ])
    .areas(left_panel);

    let search_border = if matches!(data.focus, ResultsFocus::List) {
        theme::BORDER_FOCUS
    } else {
        theme::BORDER_DEFAULT
    };
    let search = Paragraph::new(format!("Filter: {}", data.search_query)).block(
        Block::default()
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(search_border)),
    );
    frame.render_widget(search, search_area);
    click_areas.search_input = search_area;

    let sort_label = if data.sort_ascending {
        "Report ▲"
    } else {
        "Report ▼"
    };
    frame.render_widget(
        Paragraph::new(sort_label).style(Style::default().fg(theme::TEXT_MUTED)),
        sort_area,
    );
    click_areas.sort_header = sort_area;

    let list_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(theme::BORDER_DEFAULT));
    let list_inner = list_block.inner(list_area);
    frame.render_widget(list_block, list_area);

    click_areas.list_rows.clear();
    for (line_index, filtered_index) in data.filtered_indices.iter().enumerate() {
        if line_index as u16 >= list_inner.height {
            break;
        }
        let row_area = Rect::new(
            list_inner.x,
            list_inner.y + line_index as u16,
            list_inner.width,
            1,
        );

        let report = &data.reports[*filtered_index];
        let is_selected = data.selected_filtered == Some(line_index);
        let marker = if is_selected { "►" } else { " " };
        let style = if is_selected {
            Style::default()
                .bg(theme::BG_ELEVATED)
                .fg(theme::TEXT_PRIMARY)
        } else {
            Style::default().fg(theme::TEXT_PRIMARY)
        };

        frame.render_widget(
            Paragraph::new(format!("{marker} {}", report.filename)).style(style),
            row_area,
        );
        click_areas.list_rows.push((line_index, row_area));
    }

    let [refresh_area, delete_area, open_area] = Layout::horizontal([
        Constraint::Ratio(1, 3),
        Constraint::Ratio(1, 3),
        Constraint::Ratio(1, 3),
    ])
    .areas(actions_area);

    render_action_button(frame, refresh_area, "Refresh");
    render_action_button(frame, delete_area, "Delete");
    render_action_button(frame, open_area, "Open");
    click_areas.refresh_button = refresh_area;
    click_areas.delete_button = delete_area;
    click_areas.open_button = open_area;

    let [metadata_area, toolbar_area, viewer_area] = Layout::vertical([
        Constraint::Length(3),
        Constraint::Length(1),
        Constraint::Min(6),
    ])
    .areas(right_panel);

    if let Some(selected) = data.selected_filtered {
        if let Some(report_index) = data.filtered_indices.get(selected)
            && let Some(report) = data.reports.get(*report_index)
        {
            let metadata = format!(
                "{}\nDate: {}\nSize: {}",
                report.filename,
                if report.timestamp.is_empty() {
                    "Unknown"
                } else {
                    &report.timestamp
                },
                report.size_label
            );
            frame.render_widget(
                Paragraph::new(metadata).style(Style::default().fg(theme::TEXT_PRIMARY)),
                metadata_area,
            );
        }
    }

    let [link_info_area, copy_area] =
        Layout::horizontal([Constraint::Min(10), Constraint::Length(12)]).areas(toolbar_area);

    let link_info = if data.rendered_links.is_empty() {
        "Links: 0".to_string()
    } else if let Some(index) = data.active_link_index {
        let label = data
            .rendered_links
            .get(index)
            .map(|link| link.label.as_str())
            .unwrap_or("");
        format!(
            "Link {}/{}: {}",
            index + 1,
            data.rendered_links.len(),
            label
        )
    } else {
        format!("Links: {}", data.rendered_links.len())
    };
    frame.render_widget(
        Paragraph::new(link_info).style(Style::default().fg(theme::TEXT_MUTED)),
        link_info_area,
    );

    frame.render_widget(
        Paragraph::new("Copy All")
            .style(
                Style::default()
                    .fg(theme::TEXT_MUTED)
                    .add_modifier(Modifier::BOLD),
            )
            .centered()
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .border_type(BorderType::Rounded)
                    .border_style(Style::default().fg(theme::BORDER_DEFAULT)),
            ),
        copy_area,
    );
    click_areas.copy_button = copy_area;
    click_areas.viewer_link_areas.clear();

    let viewer_border = if matches!(data.focus, ResultsFocus::Viewer) {
        theme::BORDER_FOCUS
    } else {
        theme::BORDER_DEFAULT
    };
    let viewer_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(viewer_border));
    let viewer_inner = viewer_block.inner(viewer_area);
    frame.render_widget(viewer_block, viewer_area);

    let text_area = if viewer_inner.width > 1 {
        Rect::new(
            viewer_inner.x,
            viewer_inner.y,
            viewer_inner.width - 1,
            viewer_inner.height,
        )
    } else {
        viewer_inner
    };

    let visible_lines: Vec<Line<'static>> = data
        .rendered_lines
        .iter()
        .skip(data.scroll_offset)
        .take(text_area.height as usize)
        .cloned()
        .collect();

    frame.render_widget(
        Paragraph::new(visible_lines).style(Style::default().fg(theme::TEXT_PRIMARY)),
        text_area,
    );

    click_areas.viewer_link_areas =
        collect_visible_link_hit_areas(text_area, data.scroll_offset, data.rendered_links);

    if viewer_inner.width > 1 {
        let scrollbar_area = Rect::new(
            viewer_inner.x + viewer_inner.width - 1,
            viewer_inner.y,
            1,
            viewer_inner.height,
        );
        render_scrollbar(
            frame,
            scrollbar_area,
            data.rendered_lines.len(),
            text_area.height as usize,
            data.scroll_offset,
        );
    }

    click_areas.viewer_area = viewer_area;
    click_areas.viewer_viewport_height = text_area.height as usize;

    click_areas
}

fn collect_visible_link_hit_areas(
    text_area: Rect,
    scroll_offset: usize,
    links: &[MarkdownLink],
) -> Vec<ViewerLinkHitArea> {
    if text_area.width == 0 {
        return Vec::new();
    }

    links
        .iter()
        .filter_map(|link| {
            if link.line_index < scroll_offset {
                return None;
            }
            let relative_line = link.line_index - scroll_offset;
            if relative_line >= text_area.height as usize {
                return None;
            }

            let start_col = link.start_col.min(text_area.width as usize);
            let end_col = link.end_col.min(text_area.width as usize);
            if end_col <= start_col {
                return None;
            }

            Some(ViewerLinkHitArea {
                link_index: link.index,
                area: Rect::new(
                    text_area.x + start_col as u16,
                    text_area.y + relative_line as u16,
                    (end_col - start_col) as u16,
                    1,
                ),
            })
        })
        .collect()
}

fn render_empty_results(frame: &mut Frame<'_>, area: Rect) -> ResultsClickAreas {
    let mut click_areas = ResultsClickAreas::default();

    let [top, title, subtitle, button, bottom] = Layout::vertical([
        Constraint::Fill(1),
        Constraint::Length(1),
        Constraint::Length(1),
        Constraint::Length(3),
        Constraint::Fill(1),
    ])
    .areas(area);

    let _ = top;
    let _ = bottom;

    frame.render_widget(
        Paragraph::new("No scan results")
            .style(
                Style::default()
                    .fg(theme::TEXT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            )
            .centered(),
        title,
    );
    frame.render_widget(
        Paragraph::new("Run a scan to see results here")
            .style(Style::default().fg(theme::TEXT_MUTED))
            .centered(),
        subtitle,
    );

    let [_, button_area, _] = Layout::horizontal([
        Constraint::Fill(1),
        Constraint::Length(24),
        Constraint::Fill(1),
    ])
    .areas(button);

    render_action_button(frame, button_area, "Scan Crash Logs");
    click_areas.empty_scan_button = button_area;
    click_areas
}

fn render_action_button(frame: &mut Frame<'_>, area: Rect, label: &str) {
    frame.render_widget(
        Paragraph::new(label)
            .centered()
            .style(Style::default().fg(theme::TEXT_PRIMARY))
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .border_type(BorderType::Rounded)
                    .border_style(Style::default().fg(theme::BORDER_DEFAULT)),
            ),
        area,
    );
}

fn render_scrollbar(
    frame: &mut Frame<'_>,
    area: Rect,
    total_lines: usize,
    viewport_height: usize,
    scroll_offset: usize,
) {
    if area.height == 0 {
        return;
    }

    let track_height = area.height as usize;
    let max_scroll = total_lines.saturating_sub(viewport_height);

    let thumb_height = viewport_height
        .saturating_mul(track_height)
        .max(track_height)
        .checked_div(total_lines)
        .unwrap_or(track_height)
        .clamp(1, track_height);

    let thumb_pos = if max_scroll == 0 || track_height == thumb_height {
        0
    } else {
        scroll_offset.saturating_mul(track_height - thumb_height) / max_scroll
    };

    let mut lines = Vec::with_capacity(track_height);
    for y in 0..track_height {
        if y >= thumb_pos && y < thumb_pos + thumb_height {
            lines.push(Line::from("█"));
        } else {
            lines.push(Line::from("░"));
        }
    }

    frame.render_widget(Paragraph::new(lines), area);
}

#[cfg(test)]
#[path = "results_tab_tests.rs"]
mod tests;
