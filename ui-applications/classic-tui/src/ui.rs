use ratatui::Frame;
use ratatui::layout::{Alignment, Constraint, Layout, Position, Rect};
use ratatui::style::{Modifier, Style};
use ratatui::text::Line;
use ratatui::widgets::{Block, BorderType, Borders, Gauge, Paragraph, Tabs};

use crate::app::{App, ClickAreas, Overlay, TabIndex};
use crate::tabs::articles_tab::{ArticlesTabRenderData, render_articles_tab};
use crate::tabs::backup_tab::{BackupTabRenderData, render_backup_tab};
use crate::tabs::main_tab::{MainFocus, MainTabRenderData, render_main_tab};
use crate::tabs::results_tab::{ResultsTabRenderData, render_results_tab};
use crate::theme;

impl App {
    pub fn render(&mut self, frame: &mut Frame<'_>) {
        let area = frame.area();

        if area.width < 80 || area.height < 24 {
            let warning = Paragraph::new("Terminal too small. Minimum: 80x24")
                .alignment(Alignment::Center)
                .style(Style::default().fg(theme::ERROR));
            frame.render_widget(warning, area);
            return;
        }

        let [title_area, tabs_area, content_area, status_area] = Layout::vertical([
            Constraint::Length(1),
            Constraint::Length(1),
            Constraint::Min(10),
            Constraint::Length(1),
        ])
        .areas(area);

        self.render_title(frame, title_area);
        self.render_tabs(frame, tabs_area);

        let mut click_areas = ClickAreas {
            tab_areas: tab_areas(tabs_area),
            ..ClickAreas::default()
        };

        match self.active_tab {
            TabIndex::MainOptions => {
                let data = MainTabRenderData {
                    staging_mods: &self.staging_mods_input.value,
                    custom_scan: &self.custom_scan_input.value,
                    focus: self.main_focus,
                    scan_in_progress: self.scan_in_progress,
                    update_checking: self.update_checking,
                    papyrus_active: self.papyrus_active,
                    staging_validation: self.staging_validation_state(),
                    custom_validation: self.custom_validation_state(),
                };
                click_areas.main = render_main_tab(frame, content_area, &data);
            }
            TabIndex::FileBackup => {
                let data = BackupTabRenderData {
                    selected_row: self.backup_selected_row,
                    exists: self.backup_exists,
                };
                click_areas.backup = render_backup_tab(frame, content_area, &data);
            }
            TabIndex::Articles => {
                let data = ArticlesTabRenderData {
                    selected: self.articles_selected,
                };
                click_areas.articles = render_articles_tab(frame, content_area, &data);
            }
            TabIndex::Results => {
                let data = ResultsTabRenderData {
                    reports: &self.results.reports,
                    filtered_indices: &self.results.filtered_indices,
                    selected_filtered: self.results.selected_filtered,
                    search_query: &self.results.search_query,
                    sort_ascending: self.results.sort_ascending,
                    focus: self.results.focus,
                    rendered_lines: &self.results.rendered_lines,
                    rendered_links: &self.results.rendered_links,
                    active_link_index: self.results.active_link_index,
                    scroll_offset: self.results.scroll_offset,
                    list_panel_width: self.results.list_panel_width,
                };
                click_areas.results = render_results_tab(frame, content_area, &data);
                self.results_set_viewport_height(click_areas.results.viewer_viewport_height);
            }
        }

        self.click_areas = click_areas;
        self.render_status(frame, status_area);
        self.render_overlay(frame, area);
        self.render_cursor(frame);
    }

    fn render_title(&self, frame: &mut Frame<'_>, area: Rect) {
        let title = "CLASSIC v9.0.0";
        let hints = "F1:Help  Ctrl+O:Settings  Q:Quit";
        let mut line = format!(" {title}");
        if area.width as usize > line.len() + hints.len() {
            let gap = area.width as usize - line.len() - hints.len();
            line.push_str(&" ".repeat(gap));
            line.push_str(hints);
        }
        frame.render_widget(
            Paragraph::new(line).style(Style::default().fg(theme::TEXT_PRIMARY)),
            area,
        );
    }

    fn render_tabs(&self, frame: &mut Frame<'_>, area: Rect) {
        let tabs = Tabs::new(TabIndex::NAMES)
            .select(self.active_tab as usize)
            .highlight_style(
                Style::default()
                    .fg(theme::ACCENT_BLUE)
                    .add_modifier(Modifier::BOLD),
            )
            .divider(" │ ");
        frame.render_widget(tabs, area);
    }

    fn render_status(&self, frame: &mut Frame<'_>, area: Rect) {
        let [status_text_area, progress_area] =
            Layout::horizontal([Constraint::Min(10), Constraint::Length(24)]).areas(area);

        let status_text = if self.scan_progress < 0.0 {
            let spinner = ["-", "\\", "|", "/"];
            let index = self.tick_count % spinner.len();
            format!("{} {}", spinner[index], self.scan_status)
        } else {
            self.scan_status.clone()
        };

        frame.render_widget(
            Paragraph::new(status_text).style(Style::default().fg(theme::TEXT_PRIMARY)),
            status_text_area,
        );

        let percent = if self.scan_progress < 0.0 {
            0.0
        } else {
            self.scan_progress.clamp(0.0, 100.0)
        };

        let gauge = Gauge::default()
            .gauge_style(Style::default().fg(theme::ACCENT_BLUE))
            .percent(percent as u16)
            .label(format!("{percent:.0}%"));
        frame.render_widget(gauge, progress_area);
    }

    fn render_overlay(&self, frame: &mut Frame<'_>, area: Rect) {
        let Some(overlay) = self.active_overlay.as_ref() else {
            return;
        };

        let width = area.width.min(68);
        let height = area.height.min(11);
        let x = area.x + (area.width.saturating_sub(width)) / 2;
        let y = area.y + (area.height.saturating_sub(height)) / 2;
        let overlay_area = Rect::new(x, y, width, height);

        let (title, body): (&str, String) = match overlay {
            Overlay::About => (
                "About",
                "CLASSIC\nCrash Log Auto Scanner & Setup Integrity Checker\n\nVersion 9.0.0\n\nPress Esc to close"
                    .to_string(),
            ),
            Overlay::Help => (
                "Help",
                "F5: Crash Scan | F6: Game Scan | F7: Papyrus\nCtrl+O: Settings | 1-4: Switch Tabs | Q: Quit\n\nTab/Shift+Tab: Focus navigation\nPress Esc to close"
                    .to_string(),
            ),
            Overlay::Settings => (
                "Settings",
                self.settings_overlay_text(),
            ),
            Overlay::ConfirmRemoveBackup(backup_type) => {
                let text = format!(
                    "Remove {} backup?\n\nThis will delete all backed up files permanently.\n\nPress Enter to confirm, Esc to cancel",
                    backup_type.display_name()
                );
                ("Confirm Remove", text)
            }
            Overlay::ConfirmDeleteReport(filename) => {
                let text = format!(
                    "Delete {filename}?\n\nThis report will be permanently removed.\n\nPress Enter to confirm, Esc to cancel"
                );
                ("Confirm Delete", text)
            }
        };

        let block = Block::default()
            .title(Line::from(title).style(Style::default().add_modifier(Modifier::BOLD)))
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(theme::BORDER_FOCUS))
            .style(Style::default().bg(theme::BG_SURFACE));

        let paragraph = Paragraph::new(body)
            .style(Style::default().fg(theme::TEXT_PRIMARY))
            .block(block)
            .alignment(Alignment::Left);

        frame.render_widget(paragraph, overlay_area);
    }

    fn render_cursor(&self, frame: &mut Frame<'_>) {
        let area = match self.main_focus {
            MainFocus::StagingInput => self.click_areas.main.staging_input,
            MainFocus::CustomInput => self.click_areas.main.custom_input,
            _ => return,
        };

        if self.active_tab != TabIndex::MainOptions || self.active_overlay.is_some() {
            return;
        }

        let input = match self.main_focus {
            MainFocus::StagingInput => &self.staging_mods_input,
            MainFocus::CustomInput => &self.custom_scan_input,
            _ => return,
        };

        let x = area.x.saturating_add(1 + input.cursor as u16);
        let max_x = area.x.saturating_add(area.width.saturating_sub(2));
        let cursor_x = x.min(max_x);
        let cursor_y = area.y.saturating_add(1);

        frame.set_cursor_position(Position::new(cursor_x, cursor_y));
    }
}

fn tab_areas(area: Rect) -> Vec<(TabIndex, Rect)> {
    let mut areas = Vec::new();
    let mut x = area.x;

    for (index, name) in TabIndex::NAMES.iter().enumerate() {
        let width = name.len() as u16 + 2;
        let rect = Rect::new(x, area.y, width, area.height);
        areas.push((TabIndex::from_index(index), rect));
        x = x.saturating_add(width + 3);
    }

    areas
}
