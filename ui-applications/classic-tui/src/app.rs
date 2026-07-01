use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};

use classic_config_core::ClassicConfig;
use classic_file_io_core::BackupType;
use classic_file_io_core::LogCollector;
use classic_path_core::validate_custom_scan_path;
use classic_scanlog_core::{
    CrashLogScanIntake, CrashLogScanOptions, CrashLogScanRun, CrashLogScanRunEvent,
    CrashLogScanRunEventKind, CrashLogScanRunMode, CrashLogScanRunRequest,
    StandardCrashLogScanRunOptions, UnsolvedLogsPolicy,
};
use classic_shared_core::get_runtime;
use classic_update_core::NotificationStatus;
use ratatui::Terminal;
use ratatui::backend::Backend;
use ratatui::layout::Rect;
use tokio::sync::mpsc;
use tokio_util::sync::CancellationToken;

mod backup_workflow;
mod results_workflow;
mod update_workflow;

use crate::results_markdown::MarkdownLink;
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

fn format_scan_run_progress(event: &CrashLogScanRunEvent) -> (f64, String) {
    let percent = if event.total == 0 {
        0.0
    } else {
        (event.completed as f64 / event.total as f64) * 100.0
    };
    let filename = event
        .crash_log
        .file_name()
        .map(|name| name.to_string_lossy().to_string())
        .unwrap_or_else(|| "unknown".to_string());
    let action = match event.kind {
        CrashLogScanRunEventKind::Queued => "Queued",
        CrashLogScanRunEventKind::Started | CrashLogScanRunEventKind::Phase => "Scanning",
        CrashLogScanRunEventKind::Completed => "Scanned",
        CrashLogScanRunEventKind::Failed => "Failed",
    };

    (percent, format!("{percent:.0}% - {action} {filename}"))
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
    UpdateResult(Result<NotificationStatus, String>),
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
    pub last_update_notification: Option<NotificationStatus>,
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
            last_update_notification: None,
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
            last_update_notification: None,
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
        if let Some(clear_at) = self.status_clear_at
            && Instant::now() >= clear_at
        {
            self.scan_status = "Ready".to_string();
            self.scan_progress = 0.0;
            self.status_clear_at = None;
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
            AsyncMessage::UpdateResult(result) => {
                self.update_checking = false;
                match &result {
                    Ok(status) => {
                        self.scan_status = update_workflow::format_update_status(status);
                        if let Some(display) = status.display.as_ref() {
                            let body = display.body.trim();
                            if !body.is_empty() {
                                tracing::info!(target: "classic_tui::update", "{}", body);
                            }
                            if let Some(cta) = display.cta_url.as_deref() {
                                tracing::info!(target: "classic_tui::update", "See: {cta}");
                            }
                        }
                    }
                    Err(message) => {
                        self.scan_status = format!("Update check failed: {message}");
                    }
                }
                self.last_update_notification = result.ok();
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
        let selected_game_version = self.config.game_version.clone();
        let configured_docs_root = self.config.paths.docs_root.clone();
        let show_formid_values = self.config.show_formid_values;
        let fcx_mode = self.config.fcx_mode;
        let simplify_logs = self.config.simplify_logs;
        let move_unsolved_logs = self.config.move_unsolved_logs;
        let yaml_dir_root = std::env::current_dir().unwrap_or_default();
        let yaml_dir_data = yaml_dir_root.join("CLASSIC Data");
        let base_folder = yaml_dir_root.clone();

        get_runtime().spawn(async move {
            let collector = LogCollector::new_for_scan(
                base_folder,
                yaml_dir_data.clone(),
                "Fallout4",
                &selected_game_version,
                configured_docs_root.as_deref(),
                custom_folder,
            );
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

            let total = log_paths.len();

            let options = CrashLogScanOptions::new(show_formid_values, fcx_mode, simplify_logs);
            let ready = match CrashLogScanIntake::from_yaml_paths(
                yaml_dir_root.clone(),
                yaml_dir_data.clone(),
                "Fallout4",
                selected_game_version,
                options,
            )
            .prepare()
            .await
            {
                Ok(ready) => ready,
                Err(error) => {
                    let _ = tx.send(AsyncMessage::ScanError(format!(
                        "Failed to initialize scanner: {error}"
                    )));
                    return;
                }
            };

            let cancellation = Arc::new(AtomicBool::new(cancel_token.is_cancelled()));
            let cancellation_watcher = {
                let cancellation = Arc::clone(&cancellation);
                let cancel_token = cancel_token.clone();
                tokio::spawn(async move {
                    cancel_token.cancelled().await;
                    cancellation.store(true, Ordering::Relaxed);
                })
            };

            let mode = CrashLogScanRunMode::Standard(StandardCrashLogScanRunOptions {
                unsolved_logs: if move_unsolved_logs {
                    UnsolvedLogsPolicy::MoveTo {
                        directory: yaml_dir_root.join("CLASSIC Backup").join("Unsolved Logs"),
                    }
                } else {
                    UnsolvedLogsPolicy::LeaveInPlace
                },
            });
            let request = CrashLogScanRunRequest {
                logs: log_paths,
                mode,
                max_concurrent: None,
                cancellation: Some(cancellation),
                preserve_order: false,
            };
            let run = CrashLogScanRun::new(ready);
            let result = run
                .run(request, |event| {
                    let (percent, status) = format_scan_run_progress(&event);
                    let _ = tx.send(AsyncMessage::ScanProgress { percent, status });
                })
                .await;

            cancellation_watcher.abort();

            let result = match result {
                Ok(result) => result,
                Err(error) => {
                    let _ = tx.send(AsyncMessage::ScanError(format!(
                        "Failed to scan logs: {error}"
                    )));
                    return;
                }
            };

            let processed = result.succeeded + result.failed;
            let errors = result.failed;
            let cancelled = result.cancelled > 0;

            let _ = tx.send(AsyncMessage::ScanComplete {
                processed,
                total,
                errors,
                cancelled,
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
#[path = "app_tests.rs"]
mod tests;
