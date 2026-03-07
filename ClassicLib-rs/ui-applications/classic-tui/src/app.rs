use std::collections::HashSet;
use std::hash::{Hash, Hasher};
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use classic_config_core::{ClassicConfig, YamlSource};
use classic_file_io_core::BackupManager;
use classic_file_io_core::BackupType;
use classic_file_io_core::LogCollector;
use classic_path_core::{DocsPathFinder, validate_custom_scan_path};
use classic_scanlog_core::{AnalysisConfig, OrchestratorCore};
use classic_shared_core::get_runtime;
use classic_update_core::GithubClient;
use ratatui::Terminal;
use ratatui::backend::Backend;
use ratatui::layout::Rect;
use tokio::sync::mpsc;
use tokio_util::sync::CancellationToken;
use yaml_rust2::YamlLoader;

use crate::results_markdown::{MarkdownLink, render_markdown};
use crate::state::{
    WindowState, load_settings, load_window_state, save_settings, save_window_state,
};
use crate::tabs::articles_tab::{ARTICLE_LINKS, ArticlesClickAreas};
use crate::tabs::backup_tab::BackupClickAreas;
use crate::tabs::main_tab::{MainClickAreas, MainFocus};
use crate::tabs::results_tab::ResultsClickAreas;
use crate::widgets::path_input::PathValidationState;

const STATUS_CLEAR_SECONDS: u64 = 5;
pub const BACKUP_TYPES: [BackupType; 4] = [
    BackupType::XSE,
    BackupType::ReShade,
    BackupType::Vulkan,
    BackupType::ENB,
];

fn open_url_default(url: &str) -> Result<(), String> {
    open::that(url).map_err(|error| error.to_string())
}

fn open_url_noop(_url: &str) -> Result<(), String> {
    Ok(())
}

fn write_clipboard_default(text: &str) -> Result<(), String> {
    let mut clipboard = arboard::Clipboard::new().map_err(|error| error.to_string())?;
    clipboard
        .set_text(text.to_string())
        .map_err(|error| error.to_string())
}

fn write_clipboard_noop(_text: &str) -> Result<(), String> {
    Ok(())
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TabIndex {
    MainOptions = 0,
    FileBackup = 1,
    Articles = 2,
    Results = 3,
}

impl TabIndex {
    pub const NAMES: [&'static str; 4] = ["Main Options", "File Backup", "Articles", "Results"];

    pub fn from_index(index: usize) -> Self {
        match index {
            1 => Self::FileBackup,
            2 => Self::Articles,
            3 => Self::Results,
            _ => Self::MainOptions,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Overlay {
    About,
    Help,
    Settings,
    ConfirmRemoveBackup(BackupType),
    ConfirmDeleteReport(String),
}

#[derive(Default)]
pub struct ClickAreas {
    pub tab_areas: Vec<(TabIndex, Rect)>,
    pub main: MainClickAreas,
    pub backup: BackupClickAreas,
    pub articles: ArticlesClickAreas,
    pub results: ResultsClickAreas,
}

#[derive(Clone)]
pub struct ReportEntry {
    pub filename: String,
    pub path: PathBuf,
    pub timestamp: String,
    pub size_label: String,
    pub size_bytes: u64,
    pub modified_unix_ms: u128,
}

impl ReportEntry {
    pub fn new(filename: String, path: PathBuf, timestamp: String, size_label: String) -> Self {
        Self {
            filename,
            path,
            timestamp,
            size_label,
            size_bytes: 0,
            modified_unix_ms: 0,
        }
    }

    #[cfg(test)]
    pub fn new_for_test(filename: &str) -> Self {
        Self {
            filename: filename.to_string(),
            path: PathBuf::from(filename),
            timestamp: String::new(),
            size_label: "1.0 KB".to_string(),
            size_bytes: 0,
            modified_unix_ms: 0,
        }
    }
}

pub struct ResultsState {
    pub reports: Vec<ReportEntry>,
    pub filtered_indices: Vec<usize>,
    pub search_query: String,
    pub sort_ascending: bool,
    pub selected_filtered: Option<usize>,
    pub selected_report_content: String,
    pub selected_report_path: Option<PathBuf>,
    pub rendered_lines: Vec<ratatui::text::Line<'static>>,
    pub rendered_links: Vec<MarkdownLink>,
    pub active_link_index: Option<usize>,
    pub scroll_offset: usize,
    pub viewport_height: usize,
    pub total_lines: usize,
    pub focus: ResultsFocus,
    pub list_panel_width: u16,
    pub has_results: bool,
    pub last_poll_at: Option<Instant>,
    pub last_snapshot_hash: u64,
}

impl Default for ResultsState {
    fn default() -> Self {
        Self {
            reports: Vec::new(),
            filtered_indices: Vec::new(),
            search_query: String::new(),
            sort_ascending: false,
            selected_filtered: None,
            selected_report_content: String::new(),
            selected_report_path: None,
            rendered_lines: Vec::new(),
            rendered_links: Vec::new(),
            active_link_index: None,
            scroll_offset: 0,
            viewport_height: 0,
            total_lines: 0,
            focus: ResultsFocus::List,
            list_panel_width: 30,
            has_results: false,
            last_poll_at: None,
            last_snapshot_hash: 0,
        }
    }
}

#[derive(Default)]
pub struct InputState {
    pub value: String,
    pub cursor: usize,
}

impl InputState {
    pub fn set_value(&mut self, value: String) {
        self.value = value;
        self.cursor = self.value.chars().count();
    }

    pub fn insert_char(&mut self, ch: char) {
        let mut chars: Vec<char> = self.value.chars().collect();
        chars.insert(self.cursor, ch);
        self.value = chars.into_iter().collect();
        self.cursor += 1;
    }

    pub fn insert_text(&mut self, text: &str) {
        for ch in text.chars() {
            self.insert_char(ch);
        }
    }

    pub fn backspace(&mut self) {
        if self.cursor == 0 {
            return;
        }
        let mut chars: Vec<char> = self.value.chars().collect();
        chars.remove(self.cursor - 1);
        self.value = chars.into_iter().collect();
        self.cursor -= 1;
    }

    pub fn delete(&mut self) {
        let mut chars: Vec<char> = self.value.chars().collect();
        if self.cursor >= chars.len() {
            return;
        }
        chars.remove(self.cursor);
        self.value = chars.into_iter().collect();
    }

    pub fn move_left(&mut self) {
        self.cursor = self.cursor.saturating_sub(1);
    }

    pub fn move_right(&mut self) {
        let len = self.value.chars().count();
        if self.cursor < len {
            self.cursor += 1;
        }
    }

    pub fn move_home(&mut self) {
        self.cursor = 0;
    }

    pub fn move_end(&mut self) {
        self.cursor = self.value.chars().count();
    }
}

pub enum AsyncMessage {
    ScanProgress {
        percent: f64,
        status: String,
    },
    ScanComplete {
        processed: usize,
        total: usize,
        errors: usize,
        cancelled: bool,
    },
    ScanError(String),
    UpdateResult(String),
    BackupStatuses([bool; 4]),
    BackupComplete(String),
    BackupError(String),
}

pub type UrlOpener = fn(&str) -> Result<(), String>;
pub type ClipboardWriter = fn(&str) -> Result<(), String>;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ResultsFocus {
    List,
    Viewer,
}

pub struct App {
    pub active_tab: TabIndex,
    pub active_overlay: Option<Overlay>,

    pub staging_mods_input: InputState,
    pub custom_scan_input: InputState,
    pub main_focus: MainFocus,
    pub backup_selected_row: usize,
    pub backup_exists: [bool; 4],
    pub articles_selected: usize,
    pub results: ResultsState,

    pub scan_in_progress: bool,
    pub scan_progress: f64,
    pub scan_status: String,
    pub status_clear_at: Option<Instant>,
    pub update_checking: bool,
    pub papyrus_active: bool,
    pub pending_backup_remove: Option<BackupType>,
    pub pending_delete_report: Option<PathBuf>,

    pub should_quit: bool,
    pub click_areas: ClickAreas,
    pub tick_count: usize,

    pub config: ClassicConfig,
    pub window_state: WindowState,

    pub async_tx: mpsc::UnboundedSender<AsyncMessage>,
    pub async_rx: mpsc::UnboundedReceiver<AsyncMessage>,
    pub cancel_token: Option<CancellationToken>,

    pub url_opener: UrlOpener,
    pub clipboard_writer: ClipboardWriter,
}

impl Default for App {
    fn default() -> Self {
        Self::new()
    }
}

impl App {
    pub fn new() -> Self {
        let config = load_settings();
        let window_state = load_window_state();
        let (tx, rx) = mpsc::unbounded_channel();

        let mut staging_mods_input = InputState::default();
        let mut custom_scan_input = InputState::default();

        if let Some(path) = config.paths.mods_folder.as_ref() {
            staging_mods_input.set_value(path.to_string_lossy().to_string());
        }
        if let Some(path) = config.paths.scan_custom.as_ref() {
            custom_scan_input.set_value(path.to_string_lossy().to_string());
        }

        let mut app = Self {
            active_tab: TabIndex::from_index(window_state.active_tab as usize),
            active_overlay: None,
            staging_mods_input,
            custom_scan_input,
            main_focus: MainFocus::StagingInput,
            backup_selected_row: 0,
            backup_exists: [false; 4],
            articles_selected: 0,
            results: ResultsState::default(),
            scan_in_progress: false,
            scan_progress: 0.0,
            scan_status: "Ready".to_string(),
            status_clear_at: None,
            update_checking: false,
            papyrus_active: false,
            pending_backup_remove: None,
            pending_delete_report: None,
            should_quit: false,
            click_areas: ClickAreas::default(),
            tick_count: 0,
            config,
            window_state,
            async_tx: tx,
            async_rx: rx,
            cancel_token: None,
            url_opener: open_url_default,
            clipboard_writer: write_clipboard_default,
        };

        app.results.list_panel_width = app.window_state.results_panel_width;
        app.results.sort_ascending = app.window_state.sort_ascending;

        if matches!(app.active_tab, TabIndex::FileBackup) {
            app.refresh_backup_statuses();
        }
        if matches!(app.active_tab, TabIndex::Results) {
            app.refresh_results_reports_with_status(false);
        }

        app
    }

    pub fn new_for_testing() -> Self {
        let (tx, rx) = mpsc::unbounded_channel();
        Self {
            active_tab: TabIndex::MainOptions,
            active_overlay: None,
            staging_mods_input: InputState::default(),
            custom_scan_input: InputState::default(),
            main_focus: MainFocus::StagingInput,
            backup_selected_row: 0,
            backup_exists: [false; 4],
            articles_selected: 0,
            results: ResultsState::default(),
            scan_in_progress: false,
            scan_progress: 0.0,
            scan_status: "Ready".to_string(),
            status_clear_at: None,
            update_checking: false,
            papyrus_active: false,
            pending_backup_remove: None,
            pending_delete_report: None,
            should_quit: false,
            click_areas: ClickAreas::default(),
            tick_count: 0,
            config: ClassicConfig::default(),
            window_state: WindowState::default(),
            async_tx: tx,
            async_rx: rx,
            cancel_token: None,
            url_opener: open_url_noop,
            clipboard_writer: write_clipboard_noop,
        }
    }

    pub fn run<B: Backend>(&mut self, terminal: &mut Terminal<B>) -> color_eyre::Result<()>
    where
        <B as Backend>::Error: std::error::Error + Send + Sync + 'static,
    {
        while !self.should_quit {
            terminal.draw(|frame| self.render(frame))?;

            while let Ok(message) = self.async_rx.try_recv() {
                self.handle_async_message(message);
            }

            if crossterm::event::poll(Duration::from_millis(16))? {
                let event = crossterm::event::read()?;
                self.handle_event(event);
            }

            self.tick();
        }

        self.persist_state();
        Ok(())
    }

    pub fn tick(&mut self) {
        self.tick_count = self.tick_count.wrapping_add(1);
        if let Some(clear_at) = self.status_clear_at {
            if Instant::now() >= clear_at {
                self.scan_status = "Ready".to_string();
                self.scan_progress = 0.0;
                self.status_clear_at = None;
            }
        }

        if matches!(self.active_tab, TabIndex::Results) {
            self.poll_results_if_due();
        }
    }

    pub fn handle_async_message(&mut self, message: AsyncMessage) {
        match message {
            AsyncMessage::ScanProgress { percent, status } => {
                self.scan_progress = percent;
                self.scan_status = status;
            }
            AsyncMessage::ScanComplete {
                processed,
                total,
                errors,
                cancelled,
            } => {
                self.scan_in_progress = false;
                self.cancel_token = None;
                self.scan_progress = if cancelled || total == 0 { 0.0 } else { 100.0 };
                self.scan_status = if total == 0 {
                    "No crash logs found".to_string()
                } else if cancelled {
                    format!("Cancelled ({processed} of {total} logs)")
                } else if errors > 0 {
                    format!("Scanned {total} logs ({errors} errors)")
                } else {
                    format!("Scanned {total} logs")
                };
                self.status_clear_at =
                    Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
                if self.config.auto_switch_to_results && total > 0 && !cancelled {
                    self.set_active_tab(TabIndex::Results);
                }
            }
            AsyncMessage::ScanError(message) => {
                self.scan_in_progress = false;
                self.cancel_token = None;
                self.scan_progress = 0.0;
                self.scan_status = message;
                self.status_clear_at =
                    Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            }
            AsyncMessage::UpdateResult(message) => {
                self.update_checking = false;
                self.scan_status = message;
                self.status_clear_at =
                    Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            }
            AsyncMessage::BackupStatuses(statuses) => {
                self.backup_exists = statuses;
            }
            AsyncMessage::BackupComplete(message) => {
                self.scan_status = message;
                self.status_clear_at =
                    Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            }
            AsyncMessage::BackupError(message) => {
                self.scan_status = message;
                self.status_clear_at =
                    Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            }
        }
    }

    pub fn save_paths_from_inputs(&mut self) -> Result<(), String> {
        let staging = self.staging_mods_input.value.trim();
        self.config.paths.mods_folder = if staging.is_empty() {
            None
        } else {
            Some(PathBuf::from(staging))
        };

        let custom = self.custom_scan_input.value.trim();
        if custom.is_empty() {
            self.config.paths.scan_custom = None;
        } else {
            let custom_path = PathBuf::from(custom);
            validate_custom_scan_path(&custom_path).map_err(|err| err.to_string())?;

            if self.is_inside_crash_logs(&custom_path) {
                return Err("Custom Scan Folder cannot be inside Crash Logs".to_string());
            }

            self.config.paths.scan_custom = Some(custom_path);
        }

        save_settings(&self.config).map_err(|e| format!("Failed to save settings: {e}"))
    }

    pub fn start_or_cancel_crash_scan(&mut self) {
        if self.scan_in_progress {
            if let Some(token) = &self.cancel_token {
                token.cancel();
            }
            return;
        }

        if let Err(error) = self.save_paths_from_inputs() {
            self.scan_status = error;
            self.scan_progress = 0.0;
            self.status_clear_at = Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            return;
        }

        self.scan_in_progress = true;
        self.scan_progress = -1.0;
        self.scan_status = "Discovering crash logs...".to_string();
        self.status_clear_at = None;

        let cancel_token = CancellationToken::new();
        self.cancel_token = Some(cancel_token.clone());

        let tx = self.async_tx.clone();
        let custom_folder = self.config.paths.scan_custom.clone();
        let xse_folder = resolve_xse_folder_for_scan(&self.config);
        let selected_game_version = if config_uses_vr_mode(&self.config) {
            "VR".to_string()
        } else {
            "auto".to_string()
        };
        let base_folder = std::env::current_dir().unwrap_or_default();

        get_runtime().spawn(async move {
            let collector = LogCollector::new(base_folder, xse_folder, custom_folder);
            let log_paths = match collector.collect_all().await {
                Ok(paths) => paths,
                Err(error) => {
                    let _ = tx.send(AsyncMessage::ScanError(format!(
                        "Failed to collect logs: {error}"
                    )));
                    return;
                }
            };

            if log_paths.is_empty() {
                let _ = tx.send(AsyncMessage::ScanComplete {
                    processed: 0,
                    total: 0,
                    errors: 0,
                    cancelled: false,
                });
                return;
            }

            let mut processed = 0usize;
            let mut errors = 0usize;
            let total = log_paths.len();

            let orchestrator = match OrchestratorCore::new(AnalysisConfig::new(
                "Fallout4".to_string(),
                selected_game_version,
            )) {
                Ok(orchestrator) => orchestrator,
                Err(error) => {
                    let _ = tx.send(AsyncMessage::ScanError(format!(
                        "Failed to initialize scanner: {error}"
                    )));
                    return;
                }
            };

            for (index, path) in log_paths.iter().enumerate() {
                if cancel_token.is_cancelled() {
                    let _ = tx.send(AsyncMessage::ScanComplete {
                        processed,
                        total,
                        errors,
                        cancelled: true,
                    });
                    return;
                }

                let percent = ((index + 1) as f64 / total as f64) * 100.0;
                let filename = path
                    .file_name()
                    .map(|name| name.to_string_lossy().to_string())
                    .unwrap_or_else(|| "unknown".to_string());

                let _ = tx.send(AsyncMessage::ScanProgress {
                    percent,
                    status: format!("{percent:.0}% - Scanning {filename}"),
                });

                match orchestrator
                    .process_log(path.to_string_lossy().to_string())
                    .await
                {
                    Ok(_) => processed += 1,
                    Err(_) => {
                        processed += 1;
                        errors += 1;
                    }
                }
            }

            let _ = tx.send(AsyncMessage::ScanComplete {
                processed,
                total,
                errors,
                cancelled: false,
            });
        });
    }

    pub fn start_game_files_scan(&mut self) {
        if self.scan_in_progress {
            self.scan_status = "A scan is already in progress".to_string();
            return;
        }

        self.scan_status = "Game files scan integration pending".to_string();
        self.status_clear_at = Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
    }

    pub fn toggle_papyrus(&mut self) {
        self.papyrus_active = !self.papyrus_active;
        self.scan_status = if self.papyrus_active {
            "Papyrus monitoring enabled".to_string()
        } else {
            "Papyrus monitoring disabled".to_string()
        };
        self.status_clear_at = Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
    }

    pub fn check_updates(&mut self) {
        if self.update_checking {
            return;
        }
        self.update_checking = true;
        self.scan_status = "Checking for updates...".to_string();
        self.scan_progress = -1.0;

        let tx = self.async_tx.clone();
        let current_version = env!("CARGO_PKG_VERSION").to_string();

        get_runtime().spawn(async move {
            let message = match GithubClient::new("evildarkarchon", "CLASSIC-Fallout4") {
                Ok(client) => match client.get_latest_release().await {
                    Ok(latest) => match client.has_update(&current_version, &latest.tag_name) {
                        Ok(true) => format!("Update available: {}", latest.tag_name),
                        Ok(false) => "You are up to date".to_string(),
                        Err(error) => format!("Update check failed: {error}"),
                    },
                    Err(error) => format!("Update check failed: {error}"),
                },
                Err(error) => format!("Update check failed: {error}"),
            };
            let _ = tx.send(AsyncMessage::UpdateResult(message));
        });
    }

    pub fn open_crash_logs_folder(&mut self) {
        let path = std::env::current_dir()
            .unwrap_or_default()
            .join("Crash Logs");
        if let Err(error) = std::fs::create_dir_all(&path) {
            self.scan_status = format!("Failed to prepare Crash Logs folder: {error}");
            return;
        }

        match open::that(path) {
            Ok(_) => {
                self.scan_status = "Opened Crash Logs folder".to_string();
                self.status_clear_at =
                    Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            }
            Err(error) => {
                self.scan_status = format!("Failed to open Crash Logs folder: {error}");
            }
        }
    }

    pub fn close_overlay(&mut self) {
        self.active_overlay = None;
        self.pending_backup_remove = None;
        self.pending_delete_report = None;
    }

    pub fn set_active_tab(&mut self, tab: TabIndex) {
        self.active_tab = tab;
        if matches!(tab, TabIndex::FileBackup) {
            self.refresh_backup_statuses();
        }
        if matches!(tab, TabIndex::Results) {
            self.refresh_results_reports_with_status(false);
        }
    }

    pub fn set_url_opener(&mut self, opener: UrlOpener) {
        self.url_opener = opener;
    }

    pub fn set_clipboard_writer(&mut self, writer: ClipboardWriter) {
        self.clipboard_writer = writer;
    }

    pub fn articles_move_left(&mut self) {
        let row = self.articles_selected / 3;
        let col = self.articles_selected % 3;
        let next_col = if col == 0 { 2 } else { col - 1 };
        self.articles_selected = row * 3 + next_col;
    }

    pub fn articles_move_right(&mut self) {
        let row = self.articles_selected / 3;
        let col = self.articles_selected % 3;
        let next_col = if col == 2 { 0 } else { col + 1 };
        self.articles_selected = row * 3 + next_col;
    }

    pub fn articles_move_up(&mut self) {
        let row = self.articles_selected / 3;
        let col = self.articles_selected % 3;
        let next_row = if row == 0 { 2 } else { row - 1 };
        self.articles_selected = next_row * 3 + col;
    }

    pub fn articles_move_down(&mut self) {
        let row = self.articles_selected / 3;
        let col = self.articles_selected % 3;
        let next_row = if row == 2 { 0 } else { row + 1 };
        self.articles_selected = next_row * 3 + col;
    }

    pub fn open_selected_article(&mut self) {
        self.open_article(self.articles_selected);
    }

    pub fn select_article(&mut self, index: usize) {
        self.articles_selected = index.min(ARTICLE_LINKS.len().saturating_sub(1));
    }

    pub fn refresh_results_reports(&mut self) {
        self.refresh_results_reports_with_status(true);
    }

    fn refresh_results_reports_with_status(&mut self, show_status: bool) {
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

    fn poll_results_if_due(&mut self) {
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

    pub fn backup_select_next(&mut self) {
        self.backup_selected_row = (self.backup_selected_row + 1) % BACKUP_TYPES.len();
    }

    pub fn backup_select_prev(&mut self) {
        self.backup_selected_row = if self.backup_selected_row == 0 {
            BACKUP_TYPES.len() - 1
        } else {
            self.backup_selected_row - 1
        };
    }

    pub fn backup_select_row(&mut self, row: usize) {
        self.backup_selected_row = row.min(BACKUP_TYPES.len() - 1);
    }

    pub fn refresh_backup_statuses(&mut self) {
        let tx = self.async_tx.clone();
        let game_root = self.game_root_for_backup();

        get_runtime().spawn(async move {
            let manager = BackupManager::new(game_root, None);
            let mut statuses = [false; 4];
            for (index, backup_type) in BACKUP_TYPES.iter().enumerate() {
                statuses[index] = manager.backup_exists(*backup_type).await.unwrap_or(false);
            }
            let _ = tx.send(AsyncMessage::BackupStatuses(statuses));
        });
    }

    pub fn backup_create_selected(&mut self) {
        self.run_backup_operation(self.selected_backup_type(), BackupOperation::Create);
    }

    pub fn backup_restore_selected(&mut self) {
        if !self.backup_exists[self.backup_selected_row] {
            self.scan_status = "No backup exists for selected type".to_string();
            self.status_clear_at = Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            return;
        }

        self.run_backup_operation(self.selected_backup_type(), BackupOperation::Restore);
    }

    pub fn backup_request_remove_selected(&mut self) {
        let backup_type = self.selected_backup_type();
        if !self.backup_exists[self.backup_selected_row] {
            self.scan_status = "No backup exists for selected type".to_string();
            self.status_clear_at = Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            return;
        }

        self.pending_backup_remove = Some(backup_type);
        self.active_overlay = Some(Overlay::ConfirmRemoveBackup(backup_type));
    }

    pub fn confirm_backup_remove(&mut self) {
        if let Some(backup_type) = self.pending_backup_remove {
            self.run_backup_operation(backup_type, BackupOperation::Remove);
        }
        self.pending_backup_remove = None;
        self.active_overlay = None;
    }

    pub fn open_backups_folder(&mut self) {
        let folder = self.game_root_for_backup().join("CLASSIC_Backups");
        if let Err(error) = std::fs::create_dir_all(&folder) {
            self.scan_status = format!("Failed to prepare backups folder: {error}");
            self.status_clear_at = Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            return;
        }

        match open::that(folder) {
            Ok(_) => {
                self.scan_status = "Opened CLASSIC backups folder".to_string();
                self.status_clear_at =
                    Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            }
            Err(error) => {
                self.scan_status = format!("Failed to open backups folder: {error}");
                self.status_clear_at =
                    Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            }
        }
    }

    pub fn staging_validation_state(&self) -> PathValidationState {
        let trimmed = self.staging_mods_input.value.trim();
        if trimmed.is_empty() {
            return PathValidationState::Default;
        }
        let path = Path::new(trimmed);
        if path.is_dir() {
            PathValidationState::Valid
        } else {
            PathValidationState::Invalid
        }
    }

    pub fn custom_validation_state(&self) -> PathValidationState {
        let trimmed = self.custom_scan_input.value.trim();
        if trimmed.is_empty() {
            return PathValidationState::Valid;
        }

        let path = Path::new(trimmed);
        if validate_custom_scan_path(path).is_err() || self.is_inside_crash_logs(path) {
            PathValidationState::Invalid
        } else {
            PathValidationState::Valid
        }
    }

    pub fn persist_state(&mut self) {
        self.window_state.active_tab = self.active_tab as u8;
        self.window_state.results_panel_width = self.results.list_panel_width;
        self.window_state.sort_ascending = self.results.sort_ascending;
        if let Err(error) = save_window_state(&self.window_state) {
            tracing::warn!("Failed to save window state: {error}");
        }
    }

    fn is_inside_crash_logs(&self, custom_path: &Path) -> bool {
        let crash_logs = std::env::current_dir()
            .unwrap_or_default()
            .join("Crash Logs");

        let custom = normalize_path(custom_path);
        let crash = normalize_path(&crash_logs);

        custom == crash || custom.starts_with(&crash)
    }

    fn selected_backup_type(&self) -> BackupType {
        BACKUP_TYPES[self.backup_selected_row.min(BACKUP_TYPES.len() - 1)]
    }

    fn open_article(&mut self, index: usize) {
        if let Some(article) = ARTICLE_LINKS.get(index) {
            match (self.url_opener)(article.url) {
                Ok(()) => {
                    self.scan_status = format!("Opened {}", article.label);
                }
                Err(error) => {
                    self.scan_status = format!("Failed to open {}: {error}", article.label);
                }
            }
            self.status_clear_at = Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
        }
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

    fn game_root_for_backup(&self) -> PathBuf {
        if self.config.paths.game_root.as_os_str().is_empty() {
            std::env::current_dir().unwrap_or_default()
        } else {
            self.config.paths.game_root.clone()
        }
    }

    fn run_backup_operation(&mut self, backup_type: BackupType, operation: BackupOperation) {
        let tx = self.async_tx.clone();
        let game_root = self.game_root_for_backup();

        let status = match operation {
            BackupOperation::Create => format!("Creating {} backup...", backup_type.display_name()),
            BackupOperation::Restore => {
                format!("Restoring {} backup...", backup_type.display_name())
            }
            BackupOperation::Remove => format!("Removing {} backup...", backup_type.display_name()),
        };
        self.scan_status = status;
        self.status_clear_at = None;

        get_runtime().spawn(async move {
            let manager = BackupManager::new(game_root, None);

            let result_message = match operation {
                BackupOperation::Create => match manager.create_backup(backup_type).await {
                    Ok(info) => Ok(format!(
                        "{} backup created ({} files)",
                        backup_type.display_name(),
                        info.file_count
                    )),
                    Err(error) => Err(format!(
                        "Failed to create {} backup: {}",
                        backup_type.display_name(),
                        error
                    )),
                },
                BackupOperation::Restore => match manager.restore_backup(backup_type).await {
                    Ok(count) => Ok(format!(
                        "{} backup restored ({} files)",
                        backup_type.display_name(),
                        count
                    )),
                    Err(error) => Err(format!(
                        "Failed to restore {} backup: {}",
                        backup_type.display_name(),
                        error
                    )),
                },
                BackupOperation::Remove => match manager.remove_backup(backup_type).await {
                    Ok(()) => Ok(format!("{} backup removed", backup_type.display_name())),
                    Err(error) => Err(format!(
                        "Failed to remove {} backup: {}",
                        backup_type.display_name(),
                        error
                    )),
                },
            };

            match result_message {
                Ok(message) => {
                    let _ = tx.send(AsyncMessage::BackupComplete(message));
                }
                Err(message) => {
                    let _ = tx.send(AsyncMessage::BackupError(message));
                }
            }

            let mut statuses = [false; 4];
            for (index, backup_type) in BACKUP_TYPES.iter().enumerate() {
                statuses[index] = manager.backup_exists(*backup_type).await.unwrap_or(false);
            }
            let _ = tx.send(AsyncMessage::BackupStatuses(statuses));
        });
    }
}

#[derive(Clone, Copy)]
enum BackupOperation {
    Create,
    Restore,
    Remove,
}

fn resolve_xse_folder_for_scan(config: &ClassicConfig) -> Option<PathBuf> {
    if let Some(xse_from_local) = xse_folder_from_local_yaml(config_uses_vr_mode(config)) {
        return Some(xse_from_local);
    }

    if let Some(docs_root) = &config.paths.docs_root
        && !docs_root.as_os_str().is_empty()
    {
        return Some(docs_root.join("F4SE"));
    }

    let relative_docs = if config_uses_vr_mode(config) {
        r"My Games\Fallout4VR"
    } else {
        r"My Games\Fallout4"
    };
    let finder = DocsPathFinder::new(relative_docs);
    finder
        .find_docs_path(None)
        .ok()
        .map(|path| path.join("F4SE"))
}

fn xse_folder_from_local_yaml(vr_mode: bool) -> Option<PathBuf> {
    let local_yaml_path = YamlSource::GameLocal.path("Fallout4");
    let content = std::fs::read_to_string(local_yaml_path).ok()?;
    parse_xse_folder_from_local_yaml(&content, vr_mode)
}

fn config_uses_vr_mode(config: &ClassicConfig) -> bool {
    config.game_version.eq_ignore_ascii_case("VR")
}

fn parse_xse_folder_from_local_yaml(content: &str, _vr_mode: bool) -> Option<PathBuf> {
    let docs = YamlLoader::load_from_str(content).ok()?;
    let doc = docs.first()?;
    // GameVR_Info has been deprecated; all config now uses Game_Info.
    // VR-specific metadata is provided by the Version Registry.
    let xse = doc["Game_Info"]["Docs_Folder_XSE"].as_str()?;
    if xse.trim().is_empty() {
        None
    } else {
        Some(PathBuf::from(xse))
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

fn normalize_path(path: &Path) -> PathBuf {
    let absolute = if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir().unwrap_or_default().join(path)
    };

    absolute.canonicalize().unwrap_or(absolute)
}

#[cfg(test)]
mod tests {
    use super::{App, AsyncMessage, TabIndex};
    use crate::widgets::path_input::PathValidationState;
    use std::path::PathBuf;
    use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

    #[test]
    fn custom_validation_marks_crash_logs_path_invalid() {
        let mut app = App::new_for_testing();
        let crash_logs = std::env::current_dir()
            .expect("current directory")
            .join("Crash Logs");
        app.custom_scan_input
            .set_value(crash_logs.to_string_lossy().to_string());

        assert_eq!(app.custom_validation_state(), PathValidationState::Invalid);
    }

    #[test]
    fn crash_logs_nesting_check_handles_forward_slash_absolute_paths() {
        let app = App::new_for_testing();
        let current_dir = std::env::current_dir().expect("current directory");
        let forward_slash_base = current_dir.to_string_lossy().replace('\\', "/");
        let custom_path = PathBuf::from(format!("{forward_slash_base}/Crash Logs/nested"));

        assert!(app.is_inside_crash_logs(&custom_path));
    }

    #[test]
    fn scan_complete_with_errors_updates_status_message() {
        let mut app = App::new_for_testing();
        app.handle_async_message(AsyncMessage::ScanComplete {
            processed: 3,
            total: 3,
            errors: 1,
            cancelled: false,
        });

        assert_eq!(app.scan_status, "Scanned 3 logs (1 errors)");
        assert_eq!(app.scan_progress, 100.0);
        assert!(app.status_clear_at.is_some());
    }

    #[test]
    fn scan_complete_switches_to_results_when_enabled() {
        let mut app = App::new_for_testing();
        app.config.auto_switch_to_results = true;
        app.active_tab = TabIndex::MainOptions;

        app.handle_async_message(AsyncMessage::ScanComplete {
            processed: 1,
            total: 1,
            errors: 0,
            cancelled: false,
        });

        assert!(matches!(app.active_tab, TabIndex::Results));
    }

    #[test]
    fn articles_open_uses_url_opener_abstraction() {
        fn fail_open(_url: &str) -> Result<(), String> {
            Err("blocked".to_string())
        }

        let mut app = App::new_for_testing();
        app.set_url_opener(fail_open);
        app.articles_selected = 0;
        app.open_selected_article();

        assert!(
            app.scan_status
                .contains("Failed to open BUFFOUT 4 INSTALLATION")
        );
    }

    #[test]
    fn results_filter_is_case_insensitive() {
        let mut app = App::new_for_testing();
        app.results.reports = vec![
            super::ReportEntry::new_for_test("Crash-Alpha.md"),
            super::ReportEntry::new_for_test("gamefiles-beta.md"),
        ];
        app.results.search_query = "crash".to_string();

        app.apply_results_filter_sort();

        assert_eq!(app.results.filtered_indices.len(), 1);
        let index = app.results.filtered_indices[0];
        assert_eq!(app.results.reports[index].filename, "Crash-Alpha.md");
    }

    #[test]
    fn results_refresh_preserves_selected_path_when_still_present() {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock")
            .as_nanos();
        let dir = std::env::temp_dir().join(format!("classic-tui-results-preserve-{unique}"));
        std::fs::create_dir_all(&dir).expect("create temp dir");
        let file_a = dir.join("preserve-a.md");
        let file_b = dir.join("preserve-b.md");
        std::fs::write(&file_a, "# A").expect("write a");
        std::fs::write(&file_b, "# B").expect("write b");

        let mut app = App::new_for_testing();
        app.active_tab = TabIndex::Results;
        app.config.paths.scan_custom = Some(dir.clone());
        app.results.search_query = "preserve-".to_string();
        app.refresh_results_reports_with_status(false);

        let selected = app
            .results
            .filtered_indices
            .iter()
            .enumerate()
            .find(|(_, index)| app.results.reports[**index].filename.contains("preserve-b"))
            .map(|(i, _)| i)
            .expect("selected row");
        app.results_select_filtered_index(selected);
        let selected_path = app
            .results
            .selected_report_path
            .clone()
            .expect("path selected");

        let file_c = dir.join("preserve-c.md");
        std::fs::write(&file_c, "# C").expect("write c");
        app.refresh_results_reports_with_status(false);

        assert_eq!(app.results.selected_report_path, Some(selected_path));
    }

    #[test]
    fn poll_results_refreshes_when_snapshot_changes() {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock")
            .as_nanos();
        let dir = std::env::temp_dir().join(format!("classic-tui-results-poll-{unique}"));
        std::fs::create_dir_all(&dir).expect("create temp dir");
        std::fs::write(dir.join("poll-a.md"), "# A").expect("write a");

        let mut app = App::new_for_testing();
        app.active_tab = TabIndex::Results;
        app.config.paths.scan_custom = Some(dir.clone());
        app.results.search_query = "poll-".to_string();
        app.refresh_results_reports_with_status(false);
        let before = app.results.filtered_indices.len();

        std::fs::write(dir.join("poll-b.md"), "# B").expect("write b");
        app.results.last_poll_at = Some(Instant::now() - Duration::from_secs(3));
        app.poll_results_if_due();

        let after = app.results.filtered_indices.len();
        assert!(after > before);
    }

    #[test]
    fn resolve_xse_folder_uses_docs_root_for_fo4() {
        let mut app = App::new_for_testing();
        app.config.paths.docs_root =
            Some(PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4"));
        app.config.game_version = "auto".to_string();

        let folder = super::resolve_xse_folder_for_scan(&app.config).expect("expected xse folder");
        assert_eq!(
            folder,
            PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4\F4SE")
        );
    }

    #[test]
    fn resolve_xse_folder_uses_docs_root_for_fo4_vr() {
        let mut app = App::new_for_testing();
        app.config.paths.docs_root = Some(PathBuf::from(
            r"C:\Users\Test\Documents\My Games\Fallout4VR",
        ));
        app.config.game_version = "VR".to_string();

        let folder = super::resolve_xse_folder_for_scan(&app.config).expect("expected xse folder");
        assert_eq!(
            folder,
            PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4VR\F4SE")
        );
    }

    #[test]
    fn parse_xse_folder_from_local_yaml_reads_game_info() {
        let yaml = r#"
Game_Info:
  Docs_Folder_XSE: C:\Users\Test\Documents\My Games\Fallout4\F4SE
"#;
        let parsed = super::parse_xse_folder_from_local_yaml(yaml, false);
        assert_eq!(
            parsed,
            Some(PathBuf::from(
                r"C:\Users\Test\Documents\My Games\Fallout4\F4SE"
            ))
        );
    }

    #[test]
    fn parse_xse_folder_from_local_yaml_vr_mode_uses_game_info() {
        // Even in VR mode, we now read from Game_Info (GameVR_Info is deprecated)
        let yaml = r#"
Game_Info:
  Docs_Folder_XSE: C:\Users\Test\Documents\My Games\Fallout4VR\F4SE
"#;
        let parsed = super::parse_xse_folder_from_local_yaml(yaml, true);
        assert_eq!(
            parsed,
            Some(PathBuf::from(
                r"C:\Users\Test\Documents\My Games\Fallout4VR\F4SE"
            ))
        );
    }
}
