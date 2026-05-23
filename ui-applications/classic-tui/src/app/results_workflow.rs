use std::collections::HashSet;
use std::hash::{Hash, Hasher};
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use super::{App, Overlay, ReportEntry, ResultsFocus, STATUS_CLEAR_SECONDS, TabIndex};
use crate::results_markdown::render_markdown;

impl App {
    pub fn refresh_results_reports(&mut self) {
        self.refresh_results_reports_with_status(true);
    }

    pub(super) fn refresh_results_reports_with_status(&mut self, show_status: bool) {
        let previous_selected_path = self.results.selected_report_path.clone();
        self.results.reports = discover_result_reports(self.config.paths.scan_custom.clone());
        self.results.last_snapshot_hash = hash_reports_snapshot(&self.results.reports);
        self.results.last_poll_at = Some(Instant::now());
        self.apply_results_filter_sort();

        if let Some(previous_path) = previous_selected_path
            && let Some((filtered_pos, _)) =
                self.results
                    .filtered_indices
                    .iter()
                    .enumerate()
                    .find(|(_, report_index)| {
                        self.results.reports[**report_index].path == previous_path
                    })
        {
            self.results.selected_filtered = Some(filtered_pos);
            self.load_selected_report_content();
        }

        if show_status {
            let count = self.results.reports.len();
            self.scan_status = if count == 0 {
                "No scan results found".to_string()
            } else {
                format!("Found {count} scan results")
            };
            self.status_clear_at = Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
        }
    }

    pub(super) fn poll_results_if_due(&mut self) {
        if !matches!(self.active_tab, TabIndex::Results) {
            return;
        }

        let now = Instant::now();
        if let Some(last_poll) = self.results.last_poll_at
            && now.duration_since(last_poll) < Duration::from_secs(2)
        {
            return;
        }

        self.results.last_poll_at = Some(now);

        let current_snapshot = hash_reports_snapshot(&discover_result_reports(
            self.config.paths.scan_custom.clone(),
        ));

        if current_snapshot != self.results.last_snapshot_hash {
            self.refresh_results_reports_with_status(false);
        }
    }

    pub fn apply_results_filter_sort(&mut self) {
        let query = self.results.search_query.to_lowercase();
        self.results.filtered_indices = self
            .results
            .reports
            .iter()
            .enumerate()
            .filter_map(|(index, entry)| {
                let name = entry.filename.to_lowercase();
                if query.is_empty() || name.contains(&query) {
                    Some(index)
                } else {
                    None
                }
            })
            .collect();

        self.results.filtered_indices.sort_by(|left, right| {
            self.results.reports[*left]
                .filename
                .cmp(&self.results.reports[*right].filename)
        });

        if !self.results.sort_ascending {
            self.results.filtered_indices.reverse();
        }

        self.results.has_results = !self.results.filtered_indices.is_empty();

        if self.results.filtered_indices.is_empty() {
            self.results.selected_filtered = None;
            self.results.selected_report_content.clear();
            self.results.selected_report_path = None;
            self.results.rendered_lines.clear();
            self.results.rendered_links.clear();
            self.results.active_link_index = None;
            self.results.total_lines = 0;
            self.results.scroll_offset = 0;
            return;
        }

        let selected = self
            .results
            .selected_filtered
            .unwrap_or(0)
            .min(self.results.filtered_indices.len() - 1);
        self.results.selected_filtered = Some(selected);
        self.load_selected_report_content();
        self.clamp_results_scroll();
    }

    pub fn results_select_next(&mut self) {
        let len = self.results.filtered_indices.len();
        if len == 0 {
            return;
        }
        let current = self.results.selected_filtered.unwrap_or(0);
        self.results.selected_filtered = Some((current + 1).min(len - 1));
        self.load_selected_report_content();
    }

    pub fn results_select_prev(&mut self) {
        if self.results.filtered_indices.is_empty() {
            return;
        }
        let current = self.results.selected_filtered.unwrap_or(0);
        self.results.selected_filtered = Some(current.saturating_sub(1));
        self.load_selected_report_content();
    }

    pub fn results_select_filtered_index(&mut self, index: usize) {
        if self.results.filtered_indices.is_empty() {
            return;
        }
        self.results.selected_filtered = Some(index.min(self.results.filtered_indices.len() - 1));
        self.load_selected_report_content();
    }

    pub fn results_toggle_sort(&mut self) {
        self.results.sort_ascending = !self.results.sort_ascending;
        self.apply_results_filter_sort();
    }

    pub fn results_push_search_char(&mut self, ch: char) {
        self.results.search_query.push(ch);
        self.apply_results_filter_sort();
    }

    pub fn results_backspace_search(&mut self) {
        self.results.search_query.pop();
        self.apply_results_filter_sort();
    }

    pub fn results_set_focus_list(&mut self) {
        self.results.focus = ResultsFocus::List;
    }

    pub fn results_set_focus_viewer(&mut self) {
        self.results.focus = ResultsFocus::Viewer;
    }

    pub fn results_toggle_focus(&mut self) {
        self.results.focus = if matches!(self.results.focus, ResultsFocus::List) {
            ResultsFocus::Viewer
        } else {
            ResultsFocus::List
        };
    }

    pub fn results_select_next_link(&mut self) {
        if self.results.rendered_links.is_empty() {
            self.scan_status = "No links in report".to_string();
            self.status_clear_at = Some(Instant::now() + Duration::from_secs(3));
            return;
        }

        let len = self.results.rendered_links.len();
        let next = self
            .results
            .active_link_index
            .map(|index| (index + 1) % len)
            .unwrap_or(0);
        self.results_set_active_link(next);
    }

    pub fn results_select_prev_link(&mut self) {
        if self.results.rendered_links.is_empty() {
            self.scan_status = "No links in report".to_string();
            self.status_clear_at = Some(Instant::now() + Duration::from_secs(3));
            return;
        }

        let len = self.results.rendered_links.len();
        let prev = self
            .results
            .active_link_index
            .map(|index| if index == 0 { len - 1 } else { index - 1 })
            .unwrap_or(len - 1);
        self.results_set_active_link(prev);
    }

    pub fn results_open_active_link(&mut self) {
        if self.results.rendered_links.is_empty() {
            self.scan_status = "No links in report".to_string();
            self.status_clear_at = Some(Instant::now() + Duration::from_secs(3));
            return;
        }

        let index = self.results.active_link_index.unwrap_or(0);
        self.results_open_link_index(index);
    }

    pub fn results_open_link_index(&mut self, index: usize) {
        if index >= self.results.rendered_links.len() {
            return;
        }

        self.results_set_active_link(index);
        let link = &self.results.rendered_links[index];
        match (self.url_opener)(&link.url) {
            Ok(()) => {
                self.scan_status = format!("Opened link: {}", link.url);
            }
            Err(error) => {
                self.scan_status = format!("Failed to open link: {error}");
            }
        }
        self.status_clear_at = Some(Instant::now() + Duration::from_secs(3));
    }

    pub fn results_clear_active_link(&mut self) {
        self.results.active_link_index = None;
    }

    pub fn results_set_viewport_height(&mut self, height: usize) {
        self.results.viewport_height = height;
        self.clamp_results_scroll();
        self.ensure_active_link_visible();
    }

    pub fn results_scroll_by(&mut self, delta: isize) {
        if delta >= 0 {
            self.results.scroll_offset = self.results.scroll_offset.saturating_add(delta as usize);
        } else {
            self.results.scroll_offset =
                self.results.scroll_offset.saturating_sub((-delta) as usize);
        }
        self.clamp_results_scroll();
    }

    pub fn results_scroll_page_down(&mut self) {
        let page = self.results.viewport_height.max(1);
        self.results.scroll_offset = self.results.scroll_offset.saturating_add(page);
        self.clamp_results_scroll();
    }

    pub fn results_scroll_page_up(&mut self) {
        let page = self.results.viewport_height.max(1);
        self.results.scroll_offset = self.results.scroll_offset.saturating_sub(page);
    }

    pub fn results_scroll_home(&mut self) {
        self.results.scroll_offset = 0;
    }

    pub fn results_scroll_end(&mut self) {
        self.results.scroll_offset = self.max_results_scroll();
    }

    pub fn results_copy_all(&mut self) {
        if self.results.selected_report_content.is_empty() {
            self.scan_status = "No report content to copy".to_string();
            self.status_clear_at = Some(Instant::now() + Duration::from_secs(3));
            return;
        }

        match (self.clipboard_writer)(&self.results.selected_report_content) {
            Ok(()) => {
                self.scan_status = "Copied to clipboard".to_string();
            }
            Err(error) => {
                self.scan_status = format!("Copy failed: {error}");
            }
        }
        self.status_clear_at = Some(Instant::now() + Duration::from_secs(3));
    }

    pub fn results_request_delete_selected(&mut self) {
        let Some(path) = self.results.selected_report_path.clone() else {
            self.scan_status = "No report selected".to_string();
            self.status_clear_at = Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            return;
        };

        let name = path
            .file_name()
            .map(|name| name.to_string_lossy().to_string())
            .unwrap_or_else(|| "selected report".to_string());

        self.pending_delete_report = Some(path);
        self.active_overlay = Some(Overlay::ConfirmDeleteReport(name));
    }

    pub fn confirm_results_delete(&mut self) {
        let Some(path) = self.pending_delete_report.clone() else {
            self.close_overlay();
            return;
        };

        let name = path
            .file_name()
            .map(|name| name.to_string_lossy().to_string())
            .unwrap_or_else(|| "selected report".to_string());

        match std::fs::remove_file(&path) {
            Ok(()) => {
                let selected = self.results.selected_filtered;
                self.refresh_results_reports_with_status(false);
                if let Some(index) = selected {
                    self.results_select_filtered_index(index);
                }
                self.scan_status = format!("Deleted {name}");
            }
            Err(error) => {
                self.scan_status = format!("Failed to delete {name}: {error}");
            }
        }

        self.status_clear_at = Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
        self.pending_delete_report = None;
        self.active_overlay = None;
    }

    pub fn cancel_results_delete(&mut self) {
        self.pending_delete_report = None;
        self.active_overlay = None;
    }

    pub fn results_empty_state_scan_click(&mut self) {
        self.set_active_tab(TabIndex::MainOptions);
    }

    fn load_selected_report_content(&mut self) {
        let Some(selected_filtered) = self.results.selected_filtered else {
            self.results.selected_report_content.clear();
            self.results.selected_report_path = None;
            self.results.rendered_lines.clear();
            self.results.rendered_links.clear();
            self.results.active_link_index = None;
            self.results.total_lines = 0;
            self.results.scroll_offset = 0;
            return;
        };

        let Some(report_index) = self
            .results
            .filtered_indices
            .get(selected_filtered)
            .copied()
        else {
            self.results.selected_report_content.clear();
            self.results.selected_report_path = None;
            self.results.rendered_lines.clear();
            self.results.rendered_links.clear();
            self.results.active_link_index = None;
            self.results.total_lines = 0;
            self.results.scroll_offset = 0;
            return;
        };

        let Some(report) = self.results.reports.get(report_index) else {
            self.results.selected_report_content.clear();
            self.results.selected_report_path = None;
            self.results.rendered_lines.clear();
            self.results.rendered_links.clear();
            self.results.active_link_index = None;
            self.results.total_lines = 0;
            self.results.scroll_offset = 0;
            return;
        };

        self.results.selected_report_path = Some(report.path.clone());
        self.results.selected_report_content =
            std::fs::read_to_string(&report.path).unwrap_or_else(|_| String::new());
        let rendered = render_markdown(&self.results.selected_report_content);
        self.results.rendered_lines = rendered.lines;
        self.results.rendered_links = rendered.links;
        self.results.active_link_index = None;
        self.results.total_lines = self.results.rendered_lines.len();
        self.results.scroll_offset = 0;
        self.clamp_results_scroll();
    }

    fn max_results_scroll(&self) -> usize {
        self.results
            .total_lines
            .saturating_sub(self.results.viewport_height)
    }

    fn clamp_results_scroll(&mut self) {
        let max_scroll = self.max_results_scroll();
        if self.results.scroll_offset > max_scroll {
            self.results.scroll_offset = max_scroll;
        }
    }

    fn results_set_active_link(&mut self, index: usize) {
        if index >= self.results.rendered_links.len() {
            return;
        }
        self.results.active_link_index = Some(index);
        self.results_set_focus_viewer();
        self.ensure_active_link_visible();

        let link = &self.results.rendered_links[index];
        self.scan_status = format!(
            "Link {}/{}: {}",
            index + 1,
            self.results.rendered_links.len(),
            link.url
        );
        self.status_clear_at = Some(Instant::now() + Duration::from_secs(3));
    }

    fn ensure_active_link_visible(&mut self) {
        let Some(index) = self.results.active_link_index else {
            return;
        };
        let Some(link) = self.results.rendered_links.get(index) else {
            return;
        };

        if self.results.viewport_height == 0 {
            return;
        }

        if link.line_index < self.results.scroll_offset {
            self.results.scroll_offset = link.line_index;
        } else {
            let bottom = self.results.scroll_offset + self.results.viewport_height;
            if link.line_index >= bottom {
                self.results.scroll_offset = link
                    .line_index
                    .saturating_add(1)
                    .saturating_sub(self.results.viewport_height);
            }
        }

        self.clamp_results_scroll();
    }
}

fn discover_result_reports(custom_scan: Option<PathBuf>) -> Vec<ReportEntry> {
    let mut entries = Vec::new();
    let mut seen = HashSet::new();

    let mut directories = vec![
        std::env::current_dir()
            .unwrap_or_default()
            .join("Crash Logs"),
    ];
    if let Some(custom) = custom_scan {
        directories.push(custom);
    }

    for directory in directories {
        if !directory.exists() || !directory.is_dir() {
            continue;
        }

        let Ok(read_dir) = std::fs::read_dir(&directory) else {
            continue;
        };

        for entry in read_dir.flatten() {
            let path = entry.path();
            if !path.is_file() {
                continue;
            }

            let is_markdown = path
                .extension()
                .and_then(|ext| ext.to_str())
                .is_some_and(|ext| ext.eq_ignore_ascii_case("md"));
            if !is_markdown {
                continue;
            }

            let canonical = path.canonicalize().unwrap_or(path.clone());
            if !seen.insert(canonical.to_string_lossy().to_lowercase()) {
                continue;
            }

            let filename = path
                .file_name()
                .map(|name| name.to_string_lossy().to_string())
                .unwrap_or_else(|| "unknown.md".to_string());

            let timestamp = extract_timestamp(&filename);
            let metadata = std::fs::metadata(&path).ok();
            let size_bytes = metadata.as_ref().map_or(0, |meta| meta.len());
            let size_label = format_size(size_bytes);
            let modified_unix_ms = metadata
                .and_then(|meta| meta.modified().ok())
                .and_then(|modified| modified.duration_since(std::time::UNIX_EPOCH).ok())
                .map_or(0, |duration| duration.as_millis());

            let mut report = ReportEntry::new(filename, path, timestamp, size_label);
            report.size_bytes = size_bytes;
            report.modified_unix_ms = modified_unix_ms;
            entries.push(report);
        }
    }

    entries
}

fn hash_reports_snapshot(reports: &[ReportEntry]) -> u64 {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();

    let mut records: Vec<(&Path, u64, u128)> = reports
        .iter()
        .map(|report| {
            (
                report.path.as_path(),
                report.size_bytes,
                report.modified_unix_ms,
            )
        })
        .collect();
    records.sort_by(|left, right| left.0.cmp(right.0));

    for (path, size, modified) in records {
        path.to_string_lossy().to_lowercase().hash(&mut hasher);
        size.hash(&mut hasher);
        modified.hash(&mut hasher);
    }

    hasher.finish()
}

fn extract_timestamp(filename: &str) -> String {
    let clean = filename.replace('.', "-");
    let parts: Vec<&str> = clean.split('-').collect();

    for i in 0..parts.len() {
        if parts[i].len() == 4 && parts[i].chars().all(|c| c.is_ascii_digit()) {
            let year: u32 = match parts[i].parse() {
                Ok(y) if (1900..=2100).contains(&y) => y,
                _ => continue,
            };

            if i + 2 >= parts.len() {
                continue;
            }

            let month: u32 = match parts[i + 1].parse() {
                Ok(m) if (1..=12).contains(&m) => m,
                _ => continue,
            };
            let day: u32 = match parts[i + 2].parse() {
                Ok(d) if (1..=31).contains(&d) => d,
                _ => continue,
            };

            if i + 5 < parts.len()
                && let (Ok(hour), Ok(minute), Ok(second)) = (
                    parts[i + 3].parse::<u32>(),
                    parts[i + 4].parse::<u32>(),
                    parts[i + 5].parse::<u32>(),
                )
                && hour < 24
                && minute < 60
                && second < 60
            {
                return format!(
                    "{:04}-{:02}-{:02} {:02}:{:02}:{:02}",
                    year, month, day, hour, minute, second
                );
            }

            return format!("{:04}-{:02}-{:02}", year, month, day);
        }
    }

    String::new()
}

fn format_size(size_bytes: u64) -> String {
    if size_bytes < 1024 {
        return format!("{} B", size_bytes);
    }
    let kib = size_bytes as f64 / 1024.0;
    if kib < 1024.0 {
        return format!("{kib:.1} KB");
    }
    let mib = kib / 1024.0;
    format!("{mib:.1} MB")
}
