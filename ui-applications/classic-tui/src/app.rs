use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use classic_file_io_core::BackupType;
use classic_path_core::validate_custom_scan_path;
use classic_scan_presentation::DisplaySeverity;
use classic_scanlog_core::scan_run::contract::{
    self as scan_run_contract, Cancellation, Configuration, CrashLogScanRunContinuation,
    Event as ScanRunEvent, InfrastructureError, LocalIgnoreRecoveryDecision, Options, ResumeError,
    RunResult,
};
use classic_scanlog_core::{
    CrashLogScanFacts, CrashLogScanSetupContext, StandardCrashLogScanSource,
    StandardUnsolvedLogsIntent, TargetedCrashLogScanSource,
};
use classic_shared_core::get_runtime;
use classic_update_core::NotificationStatus;
use classic_user_settings_core::{
    CommitEligibility, LegacyTuiStateImportOutcome, MigrationPlanningOutcome, Revision,
    UserSettings, UserSettingsCommitOutcome, UserSettingsMigrationApplyOutcome, UserSettingsUpdate,
    UserSettingsUpdatePreview, import_legacy_tui_state,
};
use ratatui::Terminal;
use ratatui::backend::Backend;
use ratatui::layout::Rect;
use tokio::sync::mpsc;

mod backup_workflow;
mod results_workflow;
mod update_workflow;

use crate::results_markdown::MarkdownLink;
use crate::scan_run::{
    LocalIgnoreRecoveryPrompt, PresentedLine, ScanRunIntent, build_request,
    describe_local_ignore_recovery, format_error, format_event, format_result, format_resume_error,
    join_presented,
};
use crate::state::{classic_root, legacy_tui_state_file_path};
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

/// Returns whether a run stopped to ask for a Local Ignore recovery decision rather than finishing.
///
/// A named predicate rather than an inline comparison for two reasons. It reads as the question the
/// two call sites are actually asking, and it keeps the only `CrashLogScanRunStatus::` in `app.rs`
/// inside a `bool`-returning function — which is what the shared runtime audit needs in order to
/// tell a control-flow match from a naming table without parsing Rust.
fn awaits_local_ignore_recovery(result: &RunResult) -> bool {
    result.status == classic_scanlog_core::CrashLogScanRunStatus::LocalIgnoreRecoveryRequired
}

/// Returns whether a run finished normally with at least one Crash Log to show for it.
///
/// The Results tab is worth switching to only when there is something in it, so a completed run
/// that discovered nothing does not pull the user away from what they were doing.
fn completed_with_scanned_logs(result: &RunResult) -> bool {
    result.status == classic_scanlog_core::CrashLogScanRunStatus::Completed && result.total > 0
}

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
    ScanSummary,
    ConfirmRemoveBackup(BackupType),
    ConfirmDeleteReport(String),
    /// A Crash Log Scan Run paused for an explicit Local Ignore recovery decision.
    ///
    /// This variant is intentionally payload-free. `Overlay` is cloned on every key press, so the
    /// non-cloneable continuation lives in [`App::pending_local_ignore_recovery`] instead.
    LocalIgnoreRecovery,
}

/// Non-cloneable owner of one Crash Log Scan Run paused on Local Ignore recovery.
///
/// The opaque single-use continuation and the run's cancellation control live here and are never
/// embedded in `Overlay` or any other cloneable or serializable presentation state. Accepting or
/// dismissing a decision moves the whole value out, which is what makes the continuation
/// single-use at the TUI seam as well as inside Rust.
pub struct PendingLocalIgnoreRecovery {
    /// Opaque process-local continuation retaining discovery and prepared intake.
    continuation: CrashLogScanRunContinuation,
    /// The paused run's monotonic cancellation control, reused so a prior cancel still wins.
    cancellation: Cancellation,
    /// Cloneable facts the overlay renders while awaiting a decision.
    prompt: LocalIgnoreRecoveryPrompt,
}

/// How the user answered a Local Ignore recovery question.
///
/// Rust defines only two decisions, so dismissal is not one of them; it is modelled here because
/// the TUI has to express it, and a named alternative reads better at the call site than a bool.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum RecoveryAnswer {
    /// Apply one explicit Rust-defined decision to the retained run.
    Accept(LocalIgnoreRecoveryDecision),
    /// Dismiss the question, cancelling before the retained recovery plan can be consumed.
    Dismiss,
}

/// Retained outcome of the most recent Crash Log Scan Run, including a resumed run.
#[derive(Debug)]
pub enum LastScanRun {
    /// One Crash Log Scan Run result, whether terminal or paused for a recovery decision.
    ///
    /// Boxed because `RunResult` dwarfs the two typed failure variants.
    Run(Box<RunResult>),
    /// A run-wide typed infrastructure failure.
    Failed(InfrastructureError),
    /// A typed failure raised while resuming a retained Local Ignore recovery.
    RecoveryFailed(ResumeError),
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
    ScanEvent(ScanRunEvent),
    ScanFinished(Box<Result<RunResult, InfrastructureError>>),
    /// Terminal outcome of resuming a retained Local Ignore recovery continuation.
    ScanResumeFinished(Box<Result<RunResult, ResumeError>>),
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
    /// The severity core gave the status row, paired with the exact text it applied to.
    ///
    /// Paired rather than stored alone because `scan_status` is written from around sixty places,
    /// and all but a handful — backup outcomes, clipboard results, settings migrations — have
    /// nothing to do with a Crash Log Scan Run and no severity to offer. Keeping the text beside
    /// the severity means any of those writes silently invalidates it, so a failed run's red cannot
    /// bleed onto the unrelated message that replaced it. The invariant holds by construction
    /// instead of by sixty call sites remembering to clear a flag.
    scan_status_severity: Option<(String, DisplaySeverity)>,
    pub scan_summary_scroll: u16,
    /// Scroll offset for the recovery overlay, so long diagnostics stay reachable on any terminal.
    pub local_ignore_recovery_scroll: u16,
    pub status_clear_at: Option<Instant>,
    pub update_checking: bool,
    pub last_update_notification: Option<NotificationStatus>,
    pub papyrus_active: bool,
    pub pending_backup_remove: Option<BackupType>,
    pub pending_delete_report: Option<PathBuf>,

    pub should_quit: bool,
    pub click_areas: ClickAreas,
    pub tick_count: usize,

    /// Revision-cohesive view of the shared canonical User Settings store.
    pub settings: UserSettings,
    /// Explicit root against which the canonical store is opened and committed.
    pub classic_root: PathBuf,
    legacy_tui_state_path: Option<PathBuf>,
    settings_persistence_enabled: bool,

    pub async_tx: mpsc::UnboundedSender<AsyncMessage>,
    pub async_rx: mpsc::UnboundedReceiver<AsyncMessage>,
    pub scan_cancellation: Option<Cancellation>,
    pub last_scan_run: Option<LastScanRun>,
    /// Continuation-owning state for a run paused on Local Ignore recovery, if any.
    pub pending_local_ignore_recovery: Option<PendingLocalIgnoreRecovery>,

    pub url_opener: UrlOpener,
    pub clipboard_writer: ClipboardWriter,
}

impl Default for App {
    fn default() -> Self {
        Self::new()
    }
}

impl App {
    /// Opens the shared canonical User Settings store for the normal TUI process.
    pub fn new() -> Self {
        Self::new_with_settings_root(classic_root(), legacy_tui_state_file_path())
    }

    /// Opens the TUI against an explicit CLASSIC root and optional legacy import source.
    ///
    /// This constructor is the filesystem seam used by focused tests and embedders. The legacy
    /// path is never read automatically; it is retained only for an explicit Settings action.
    pub fn new_with_settings_root(
        classic_root: impl Into<PathBuf>,
        legacy_tui_state_path: Option<PathBuf>,
    ) -> Self {
        let classic_root = classic_root.into();
        let settings = UserSettings::open(&classic_root);
        Self::from_settings(
            classic_root,
            legacy_tui_state_path,
            settings,
            true,
            open_url_default,
            write_clipboard_default,
        )
    }

    /// Builds an isolated default-backed TUI without enabling filesystem persistence.
    pub fn new_for_testing() -> Self {
        Self::from_settings(
            PathBuf::new(),
            None,
            UserSettings::published_defaults(),
            false,
            open_url_noop,
            write_clipboard_noop,
        )
    }

    /// Projects one cohesive User Settings snapshot into TUI input and presentation state.
    fn from_settings(
        classic_root: PathBuf,
        legacy_tui_state_path: Option<PathBuf>,
        settings: UserSettings,
        settings_persistence_enabled: bool,
        url_opener: UrlOpener,
        clipboard_writer: ClipboardWriter,
    ) -> Self {
        let (tx, rx) = mpsc::unbounded_channel();

        let mut staging_mods_input = InputState::default();
        let mut custom_scan_input = InputState::default();

        if let Some(path) = settings.game_setup_settings().mods_root() {
            staging_mods_input.set_value(path.to_string());
        }
        if let Some(path) = settings.crash_log_scan_settings().custom_scan_input() {
            custom_scan_input.set_value(path.to_string());
        }

        let remembered = settings.frontend_state().tui();
        let remembered_active_tab = remembered.active_tab();
        let remembered_panel_width = remembered.results_panel_width();
        let remembered_sort_ascending = remembered.sort_ascending();
        let initial_status = settings_status(&settings, legacy_tui_state_path.as_deref());

        let mut app = Self {
            active_tab: TabIndex::from_index(remembered_active_tab as usize),
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
            scan_status: initial_status,
            // The startup status is this frontend's own, so it carries no core severity.
            scan_status_severity: None,
            scan_summary_scroll: 0,
            local_ignore_recovery_scroll: 0,
            status_clear_at: None,
            update_checking: false,
            last_update_notification: None,
            papyrus_active: false,
            pending_backup_remove: None,
            pending_delete_report: None,
            should_quit: false,
            click_areas: ClickAreas::default(),
            tick_count: 0,
            settings,
            classic_root,
            legacy_tui_state_path,
            settings_persistence_enabled,
            async_tx: tx,
            async_rx: rx,
            scan_cancellation: None,
            last_scan_run: None,
            pending_local_ignore_recovery: None,
            url_opener,
            clipboard_writer,
        };

        app.results.list_panel_width = remembered_panel_width;
        app.results.sort_ascending = remembered_sort_ascending;

        if matches!(app.active_tab, TabIndex::FileBackup) {
            app.refresh_backup_statuses();
        }
        if matches!(app.active_tab, TabIndex::Results) {
            app.refresh_results_reports_with_status(false);
        }

        app
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

    /// Applies one background workflow message to the TUI's retained presentation state.
    ///
    /// Crash Log Scan Run events update live progress, while terminal results and typed
    /// infrastructure errors remain available through the Last Scan overlay.
    pub fn handle_async_message(&mut self, message: AsyncMessage) {
        match message {
            AsyncMessage::ScanEvent(event) => {
                let presentation = format_event(&event);
                self.scan_progress = self.scan_progress.max(presentation.percent);
                self.set_scan_status(presentation.status, presentation.severity);
            }
            AsyncMessage::ScanFinished(outcome) => {
                self.scan_in_progress = false;
                match *outcome {
                    // Local Ignore recovery is an expected pause, not a finished run: keep the
                    // cancellation control alive so the retained continuation resumes under it.
                    Ok(result) if awaits_local_ignore_recovery(&result) => {
                        self.begin_local_ignore_recovery(result);
                    }
                    Ok(result) => {
                        self.scan_cancellation = None;
                        self.apply_terminal_run_result(result);
                    }
                    Err(error) => {
                        self.scan_cancellation = None;
                        let presentation = format_error(&error);
                        self.scan_progress = presentation.percent;
                        self.set_scan_status(presentation.status, presentation.severity);
                        self.status_clear_at =
                            Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
                        self.last_scan_run = Some(LastScanRun::Failed(error));
                    }
                }
            }
            AsyncMessage::ScanResumeFinished(outcome) => {
                self.scan_in_progress = false;
                self.scan_cancellation = None;
                match *outcome {
                    Ok(result) if awaits_local_ignore_recovery(&result) => {
                        // Resume reuses the retained plan exactly once, so a second recovery
                        // request is an adapter invariant to report rather than a loop to enter.
                        self.report_recovery_invariant(
                            "Crash Log Scan recovery returned an unexpected second recovery request",
                            result,
                        );
                    }
                    Ok(result) => self.apply_terminal_run_result(result),
                    Err(error) => {
                        let presentation = format_resume_error(&error);
                        self.scan_progress = presentation.percent;
                        self.set_scan_status(presentation.status, presentation.severity);
                        // Typed recovery failures stay actionable; they never silently expire.
                        self.status_clear_at = None;
                        self.last_scan_run = Some(LastScanRun::RecoveryFailed(error));
                    }
                }
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

    /// Applies one meaningful terminal run result to retained TUI presentation state.
    ///
    /// Shared by an initial run and a resumed one so both present identical Rust-owned facts.
    fn apply_terminal_run_result(&mut self, mut result: RunResult) {
        // The continuation comes out before anything renders. A terminal result carries none in
        // practice, but the ordering is the presentation crate's documented contract rather than a
        // property of this call site: rendering borrows the result, so a later `take()` would
        // borrow it across the move. Dropping it also keeps the retained `LastScanRun` free of a
        // resumable handle no terminal outcome will ever claim.
        drop(result.continuation.take());
        let presentation = format_result(&result);
        self.scan_progress = presentation.percent;
        self.set_scan_status(presentation.status, presentation.severity);
        let should_switch_to_results = completed_with_scanned_logs(&result);
        self.status_clear_at = Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
        if self
            .settings
            .frontend_state()
            .preferences()
            .auto_switch_after_scan()
            && should_switch_to_results
        {
            self.set_active_tab(TabIndex::Results);
        }
        self.last_scan_run = Some(LastScanRun::Run(Box::new(result)));
    }

    /// Reports a recovery invariant the TUI cannot act on, retaining the typed result behind it.
    ///
    /// These states are unanswerable rather than merely unsuccessful, so the status deliberately
    /// does not auto-clear: quietly returning to "Ready" would hide a question that was never put
    /// to the user.
    fn report_recovery_invariant(&mut self, message: &str, result: RunResult) {
        self.scan_progress = 0.0;
        self.scan_status = message.to_string();
        self.status_clear_at = None;
        self.last_scan_run = Some(LastScanRun::Run(Box::new(result)));
    }

    /// Takes ownership of a paused run's continuation and presents the recovery choice.
    ///
    /// The continuation is moved out of the result before anything is shown, so the retained run
    /// is owned by exactly one place and the summary overlay keeps the rest of the typed result.
    fn begin_local_ignore_recovery(&mut self, mut result: RunResult) {
        // Taken before the prompt is described, not after: describing the run renders it, rendering
        // borrows the result, and the presentation crate makes that ordering a contract precisely
        // so no adapter discovers it as a borrow error later.
        let retained = result.continuation.take();
        let prompt = describe_local_ignore_recovery(&result);
        let Some(continuation) = retained else {
            // Reported rather than guessed at: without a retained continuation the run cannot be
            // resumed, and deciding on the user's behalf is exactly what this contract forbids.
            self.scan_cancellation = None;
            self.report_recovery_invariant(
                "Crash Log Scan Run requested Local Ignore recovery without retaining its continuation",
                result,
            );
            return;
        };

        // A missing control means no cancellation was ever requested for this run, so a fresh
        // un-cancelled token is the accurate stand-in; the run's own control is deliberately kept
        // alive past `ScanFinished` for exactly this reason.
        let cancellation = self.scan_cancellation.take().unwrap_or_default();
        self.scan_progress = 0.0;
        self.local_ignore_recovery_scroll = 0;
        self.pending_local_ignore_recovery = Some(PendingLocalIgnoreRecovery {
            continuation,
            cancellation: cancellation.clone(),
            prompt: prompt.clone(),
        });
        self.last_scan_run = Some(LastScanRun::Run(Box::new(result)));

        if cancellation.is_cancelled() {
            // Cancellation observed before the question is asked already decided this run. Never
            // offer a destructive choice to a user who is on their way out; go straight to the
            // cancelled result the contract guarantees. This mirrors the pre-question cancellation
            // check in the native CLI's `read_cli_local_ignore_recovery_choice`.
            self.resume_local_ignore_recovery(RecoveryAnswer::Dismiss);
            return;
        }

        // A paused run is a question rather than a failure, which is the severity core gives the
        // status itself; it is named here because the prompt is this frontend's until the recovery
        // prompt renderer lands.
        self.set_scan_status(prompt.status_line(), DisplaySeverity::Warning);
        // No auto-clear: the question stays visible until the user answers it.
        self.status_clear_at = None;
        self.active_overlay = Some(Overlay::LocalIgnoreRecovery);
    }

    /// Accepts one explicit Rust-defined Local Ignore recovery decision and resumes the paused run.
    /// Returns whether the pending recovery can actually satisfy Reset To Default.
    ///
    /// False with no pending recovery at all, which is the safe answer for a key handler: there is
    /// nothing to accept.
    #[must_use]
    pub fn local_ignore_reset_available(&self) -> bool {
        self.pending_local_ignore_recovery
            .as_ref()
            .is_some_and(|pending| pending.prompt.reset_available)
    }

    pub fn accept_local_ignore_recovery(&mut self, decision: LocalIgnoreRecoveryDecision) {
        self.resume_local_ignore_recovery(RecoveryAnswer::Accept(decision));
    }

    /// Dismisses the recovery question without mutating Local Ignore or analyzing any Crash Log.
    ///
    /// Rust defines only two decisions, so dismissal is expressed by cancelling first and then
    /// resuming with the non-destructive placeholder. `resume` observes cancellation after it
    /// claims the continuation but before it consumes the recovery plan, so no backup,
    /// replacement, or analysis can happen and the run returns its ordinary cancelled result.
    pub fn cancel_local_ignore_recovery(&mut self) {
        self.resume_local_ignore_recovery(RecoveryAnswer::Dismiss);
    }

    /// Consumes the retained continuation exactly once through the shared Rust runtime.
    ///
    /// `answer` selects between applying a Rust-defined decision and dismissing the question;
    /// [`RecoveryAnswer::Dismiss`] cancels first and then resumes with the non-destructive
    /// placeholder decision, because Rust exposes no "cancel" decision of its own.
    ///
    /// Taking the pending state first means a second key press finds nothing to resume, which
    /// matches the continuation's own single-use contract instead of relying on the overlay
    /// closing in time. Does nothing when no run is paused.
    fn resume_local_ignore_recovery(&mut self, answer: RecoveryAnswer) {
        let Some(pending) = self.pending_local_ignore_recovery.take() else {
            return;
        };
        let PendingLocalIgnoreRecovery {
            continuation,
            cancellation,
            prompt,
        } = pending;

        let decision = match answer {
            RecoveryAnswer::Accept(decision) => decision,
            RecoveryAnswer::Dismiss => {
                cancellation.cancel();
                LocalIgnoreRecoveryDecision::ProceedWithoutIgnore
            }
        };

        self.active_overlay = None;
        self.scan_in_progress = true;
        self.scan_progress = -1.0;
        self.scan_status = match answer {
            RecoveryAnswer::Accept(_) => prompt.resume_status(),
            RecoveryAnswer::Dismiss => {
                "Cancelling; Local Ignore will not be modified...".to_string()
            }
        };
        self.status_clear_at = None;
        self.scan_cancellation = Some(cancellation.clone());

        let tx = self.async_tx.clone();
        get_runtime().spawn(async move {
            let delivery_cancellation = cancellation.clone();
            let event_tx = tx.clone();
            let mut observer = move |event| {
                // Losing the UI delivery channel explicitly requests safe cancellation so queued
                // work does not continue without a usable presentation consumer.
                if event_tx.send(AsyncMessage::ScanEvent(event)).is_err() {
                    delivery_cancellation.cancel();
                }
            };
            let result = continuation
                .resume(decision, &cancellation, Some(&mut observer))
                .await;
            let _ = tx.send(AsyncMessage::ScanResumeFinished(Box::new(result)));
        });
    }

    /// Returns the recovery overlay body, including the expected outcome of every offered decision.
    pub fn local_ignore_recovery_lines(&self) -> Vec<PresentedLine> {
        self.pending_local_ignore_recovery.as_ref().map_or_else(
            || {
                vec![PresentedLine {
                    severity: classic_scan_presentation::DisplaySeverity::Info,
                    text: "No Crash Log Scan Run is awaiting a Local Ignore recovery decision."
                        .to_string(),
                }]
            },
            |pending| pending.prompt.overlay_lines(),
        )
    }

    /// Returns [`Self::local_ignore_recovery_lines`] as plain text, for callers that draw no styling.
    pub fn local_ignore_recovery_text(&self) -> String {
        join_presented(&self.local_ignore_recovery_lines())
    }

    /// Validates the editable path fields and commits them as one canonical settings update.
    ///
    /// Validation failures leave both the in-memory snapshot and shared settings file unchanged.
    pub fn save_paths_from_inputs(&mut self) -> Result<(), String> {
        let staging = self.staging_mods_input.value.trim();
        let mods_folder = if staging.is_empty() {
            None
        } else {
            Some(staging.to_string())
        };

        let custom = self.custom_scan_input.value.trim();
        let custom_scan_input = if custom.is_empty() {
            None
        } else {
            let custom_path = PathBuf::from(custom);
            validate_custom_scan_path(&custom_path).map_err(|err| err.to_string())?;

            if self.is_inside_crash_logs(&custom_path) {
                return Err("Custom Scan Folder cannot be inside Crash Logs".to_string());
            }
            Some(custom.to_string())
        };

        let update = UserSettingsUpdate::new()
            .with_mods_folder(mods_folder)
            .with_custom_scan_input(custom_scan_input);
        self.commit_settings_update(update)
    }

    /// Validates and commits one explicit all-or-nothing update to the shared settings store.
    ///
    /// Missing settings are bootstrapped only because the caller invoked a concrete save action;
    /// migration-required and untrusted snapshots remain read-only until the user resolves them.
    fn commit_settings_update(&mut self, update: UserSettingsUpdate) -> Result<(), String> {
        if !self.settings_persistence_enabled {
            return Ok(());
        }
        let preview = if matches!(self.settings.revision(), Revision::Missing) {
            self.settings.preview_bootstrap(update)
        } else {
            self.settings.preview_update(update)
        };
        let accepted = match preview {
            UserSettingsUpdatePreview::Accepted(accepted) => accepted,
            UserSettingsUpdatePreview::Rejected(diagnostics) => {
                return Err(format_update_diagnostics(&diagnostics));
            }
        };
        match accepted
            .commit(&self.classic_root)
            .map_err(|error| format!("User Settings save failed: {error}"))?
        {
            UserSettingsCommitOutcome::Committed { .. } => {
                self.settings = UserSettings::open(&self.classic_root);
                Ok(())
            }
            UserSettingsCommitOutcome::Conflict { .. } => {
                self.settings = UserSettings::open(&self.classic_root);
                Err(
                    "User Settings changed in another process; review the latest values and retry"
                        .to_string(),
                )
            }
        }
    }

    /// Explicitly applies the currently displayed User Settings migration plan.
    pub fn apply_user_settings_migration(&mut self) {
        let outcome = match self.settings.plan_migration() {
            MigrationPlanningOutcome::NotRequired => {
                self.scan_status = "User Settings do not require migration".to_string();
                return;
            }
            MigrationPlanningOutcome::Unsupported(diagnostics) => {
                self.scan_status = diagnostics.first().map_or_else(
                    || "User Settings migration is unavailable".to_string(),
                    |diagnostic| format!("Migration unavailable: {}", diagnostic.message()),
                );
                return;
            }
            MigrationPlanningOutcome::Planned(plan) => plan.apply(&self.classic_root),
        };

        match outcome {
            Ok(UserSettingsMigrationApplyOutcome::Applied(receipt)) => {
                self.settings = UserSettings::open(&self.classic_root);
                self.scan_status = format!(
                    "User Settings migrated; verified backup retained at {}",
                    receipt.backup_path().display()
                );
            }
            Ok(UserSettingsMigrationApplyOutcome::Conflict { .. }) => {
                self.settings = UserSettings::open(&self.classic_root);
                self.scan_status =
                    "User Settings changed in another process; migration was not applied"
                        .to_string();
            }
            Err(error) => {
                self.scan_status = format!("User Settings migration failed: {error}");
            }
        }
        self.status_clear_at = None;
    }

    /// Explicitly imports the dormant legacy TUI state into the shared canonical store.
    pub fn import_legacy_tui_state(&mut self) {
        let Some(legacy_path) = self.legacy_tui_state_path.clone() else {
            self.scan_status = "No legacy TUI state path is available".to_string();
            return;
        };
        let outcome = import_legacy_tui_state(&self.classic_root, &legacy_path);
        match outcome {
            Ok(LegacyTuiStateImportOutcome::Applied(receipt)) => {
                self.settings = UserSettings::open(&self.classic_root);
                let remembered = self.settings.frontend_state().tui();
                self.active_tab = TabIndex::from_index(remembered.active_tab() as usize);
                self.results.list_panel_width = remembered.results_panel_width();
                self.results.sort_ascending = remembered.sort_ascending();
                self.scan_status = format!(
                    "Legacy TUI state imported; verified backup retained at {}",
                    receipt.backup_path().display()
                );
            }
            Ok(LegacyTuiStateImportOutcome::NoLegacySource) => {
                self.scan_status = "No legacy TUI state was found".to_string();
            }
            Ok(LegacyTuiStateImportOutcome::RequiresSettingsMigration { .. }) => {
                self.scan_status =
                    "Migrate User Settings first, then retry the legacy TUI state import"
                        .to_string();
            }
            Ok(LegacyTuiStateImportOutcome::UntrustedSettingsBase { .. }) => {
                self.scan_status =
                    "Legacy TUI state cannot be imported into degraded User Settings".to_string();
            }
            Ok(LegacyTuiStateImportOutcome::SettingsConflict { .. }) => {
                self.settings = UserSettings::open(&self.classic_root);
                self.scan_status =
                    "User Settings changed in another process; legacy state was not imported"
                        .to_string();
            }
            Ok(LegacyTuiStateImportOutcome::LegacySourceConflict { .. }) => {
                self.scan_status =
                    "Legacy TUI state changed during import; review it and retry".to_string();
            }
            Err(error) => {
                self.scan_status = format!("Legacy TUI state import failed: {error}");
            }
        }
        self.status_clear_at = None;
    }

    /// Returns migration, degraded-read, and legacy-import guidance for the Settings overlay.
    pub fn settings_overlay_text(&self) -> String {
        let mut lines = Vec::new();
        match self.settings.commit_eligibility() {
            CommitEligibility::RequiresMigration => lines.push(
                "Migration required. Press M to review/apply the canonical migration.".to_string(),
            ),
            CommitEligibility::BlockedUntrusted => {
                lines.push("User Settings are degraded and read-only.".to_string())
            }
            CommitEligibility::Eligible => {
                lines.push("Shared canonical User Settings are ready.".to_string())
            }
        }
        if self
            .legacy_tui_state_path
            .as_deref()
            .is_some_and(Path::exists)
        {
            lines.push(
                "Legacy TUI state is available. Press I to import it explicitly.".to_string(),
            );
        }
        for diagnostic in self.settings.diagnostics().iter().take(3) {
            lines.push(format!("{}: {}", diagnostic.code(), diagnostic.message()));
        }
        lines.push("Press Esc to close.".to_string());
        lines.join("\n\n")
    }

    /// Starts a crash-log scan from one cohesive User Settings snapshot, or cancels the active scan.
    ///
    /// All scan and setup inputs are projected before spawning work so concurrent settings changes
    /// cannot produce a request assembled from multiple revisions.
    pub fn start_or_cancel_crash_scan(&mut self) {
        if self.scan_in_progress {
            if let Some(cancellation) = &self.scan_cancellation {
                cancellation.cancel();
                self.scan_status =
                    "Cancellation requested; admitted logs will finish safely...".to_string();
            }
            return;
        }

        if let Err(error) = self.save_paths_from_inputs() {
            self.scan_status = error;
            self.status_clear_at = None;
            return;
        }

        self.start_crash_scan(None);
    }

    /// Starts a Targeted Crash Log Scan Run for explicit user-selected paths.
    ///
    /// This preserves the final contract's Targeted tag and cannot express Unsolved Logs movement.
    pub fn start_targeted_crash_scan(&mut self, inputs: Vec<PathBuf>) {
        if self.scan_in_progress {
            self.scan_status = "A scan is already in progress".to_string();
            return;
        }

        self.start_crash_scan(Some(inputs));
    }

    /// Projects one settings revision and launches it through the shared Rust runtime.
    fn start_crash_scan(&mut self, targeted_inputs: Option<Vec<PathBuf>>) {
        self.scan_in_progress = true;
        self.scan_progress = -1.0;
        self.scan_status = "Discovering crash logs...".to_string();
        self.status_clear_at = None;

        let tx = self.async_tx.clone();
        let scan = self.settings.crash_log_scan_settings();
        let setup = self.settings.game_setup_settings();
        let (managed_game, formid_database_paths) = self.scan_game_projection();
        let custom_folder = scan.custom_scan_input().map(PathBuf::from);
        let selected_game_version = scan.game_version_selection().as_str().to_string();
        let setup_game_root = setup.game_root().map(PathBuf::from);
        let configured_docs_root = setup.documents_root().map(PathBuf::from);
        let game_exe_path = setup.game_executable().map(PathBuf::from);
        let show_formid_values = scan.formid_value_lookup();
        let fcx_mode = scan.fcx_mode();
        let simplify_logs = scan.simplify_logs();
        let unsolved_logs_destination = scan.unsolved_logs_destination().map(PathBuf::from);
        let max_concurrent = usize::try_from(scan.max_concurrent_scans())
            .ok()
            .filter(|value| *value > 0);
        let installation_root = self.classic_root.clone();
        let base_folder = installation_root.clone();
        let configuration = Configuration {
            installation_root,
            game: managed_game,
            game_version: selected_game_version,
            options: Options::new(show_formid_values, simplify_logs),
            scan_facts: CrashLogScanFacts {
                formid_database_paths,
                unsolved_logs_destination,
            },
            max_concurrent,
        };
        let intent = match targeted_inputs {
            Some(inputs) => ScanRunIntent::Targeted(TargetedCrashLogScanSource { inputs }),
            None => ScanRunIntent::Standard {
                source: StandardCrashLogScanSource {
                    base_directory: base_folder,
                    custom_scan_directory: custom_folder,
                    configured_documents_root: configured_docs_root.clone(),
                },
                unsolved_logs: if scan.move_unsolved_logs() {
                    StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault
                } else {
                    StandardUnsolvedLogsIntent::LeaveInPlace
                },
            },
        };
        let setup_context = fcx_mode.then_some(CrashLogScanSetupContext {
            game_root: setup_game_root,
            docs_root: configured_docs_root,
            game_exe_path,
            xse_log_path: None,
        });
        let request = build_request(configuration, intent, setup_context);
        let cancellation = Cancellation::new();
        self.scan_cancellation = Some(cancellation.clone());

        get_runtime().spawn(async move {
            let delivery_cancellation = cancellation.clone();
            let event_tx = tx.clone();
            let mut observer = move |event| {
                // Losing the UI delivery channel explicitly requests safe cancellation so queued
                // work does not continue without a usable presentation consumer.
                if event_tx.send(AsyncMessage::ScanEvent(event)).is_err() {
                    delivery_cancellation.cancel();
                }
            };
            let result =
                scan_run_contract::execute(request, &cancellation, Some(&mut observer)).await;
            let _ = tx.send(AsyncMessage::ScanFinished(Box::new(result)));
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
        let path = self.classic_root.join("Crash Logs");
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
        if self.pending_local_ignore_recovery.is_some() {
            // Dismissing this overlay is itself a decision, not a passive close. Cancel explicitly
            // so the paused run returns its ordinary cancelled result instead of being abandoned.
            self.cancel_local_ignore_recovery();
            return;
        }
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
        if let Err(error) = self.persist_state_update() {
            self.scan_status = error;
            self.status_clear_at = None;
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

    /// Persists remembered presentation state through one canonical explicit update.
    pub fn persist_state(&mut self) {
        if let Err(error) = self.persist_state_update() {
            tracing::warn!("Failed to save canonical TUI remembered state: {error}");
        }
    }

    /// Builds the complete TUI remembered-state transition used by event and shutdown saves.
    fn persist_state_update(&mut self) -> Result<(), String> {
        let update = UserSettingsUpdate::new().with_tui_remembered_state(
            self.active_tab as i64,
            i64::from(self.results.list_panel_width),
            self.results.sort_ascending,
        );
        self.commit_settings_update(update)
    }

    fn is_inside_crash_logs(&self, custom_path: &Path) -> bool {
        let crash_logs = self.classic_root.join("Crash Logs");

        let custom = normalize_path(&self.classic_root, custom_path);
        let crash = normalize_path(&self.classic_root, &crash_logs);

        custom == crash || custom.starts_with(&crash)
    }

    /// Projects the canonical managed game and its analysis-data FormID databases from one snapshot.
    fn scan_game_projection(&self) -> (classic_shared_core::GameId, Vec<PathBuf>) {
        let managed_game = self.settings.game_setup_settings().managed_game();
        // Fallout 4 VR keeps its runtime identity but shares Fallout 4's analysis data and FormID database rows.
        let database_game = match managed_game {
            classic_shared_core::GameId::Fallout4VR => classic_shared_core::GameId::Fallout4,
            _ => managed_game,
        };
        let managed_game_key = database_game.as_str().to_string();
        let databases = self
            .settings
            .crash_log_scan_settings()
            .formid_databases()
            .get(&managed_game_key)
            .cloned()
            .unwrap_or_default()
            .into_iter()
            .map(PathBuf::from)
            .collect();
        (managed_game, databases)
    }

    /// Sets the status row from a core-rendered presentation, keeping its severity beside it.
    fn set_scan_status(&mut self, status: String, severity: DisplaySeverity) {
        self.scan_status_severity = Some((status.clone(), severity));
        self.scan_status = status;
    }

    /// Returns the severity core gave the status row, if a Crash Log Scan Run is what wrote it.
    ///
    /// `None` once anything else has written `scan_status`, which is the whole point of storing the
    /// text alongside: an unrelated message inherits no colour from the run before it.
    #[must_use]
    pub fn scan_status_severity(&self) -> Option<DisplaySeverity> {
        self.scan_status_severity
            .as_ref()
            .filter(|(text, _)| *text == self.scan_status)
            .map(|(_, severity)| *severity)
    }

    /// Returns the retained terminal scan presentation shown by the Last Scan overlay.
    ///
    /// Rendered on demand from the retained typed result rather than stored as text, so the overlay
    /// always reflects what core says about that run today. The result's continuation was already
    /// taken out before it was retained, so nothing here can be borrowing across a move.
    pub fn scan_run_summary_lines(&self) -> Vec<PresentedLine> {
        match self.last_scan_run.as_ref() {
            Some(LastScanRun::Run(result)) => format_result(result).details,
            Some(LastScanRun::Failed(error)) => format_error(error).details,
            Some(LastScanRun::RecoveryFailed(error)) => format_resume_error(error).details,
            // Not a statement about a run, so there is nothing for core to own here.
            None => vec![PresentedLine {
                severity: classic_scan_presentation::DisplaySeverity::Info,
                text: "No Crash Log Scan Run has completed yet.".to_string(),
            }],
        }
    }

    /// Returns [`Self::scan_run_summary_lines`] as plain text, for callers that draw no styling.
    pub fn scan_run_summary_text(&self) -> String {
        join_presented(&self.scan_run_summary_lines())
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

/// Builds the startup status presented through the existing TUI status convention.
fn settings_status(settings: &UserSettings, legacy_state_path: Option<&Path>) -> String {
    if settings.commit_eligibility() == CommitEligibility::RequiresMigration {
        return "User Settings migration required — open Settings with Ctrl+O".to_string();
    }
    if settings.commit_eligibility() == CommitEligibility::BlockedUntrusted {
        return settings.diagnostics().first().map_or_else(
            || "User Settings are degraded and read-only".to_string(),
            |diagnostic| format!("User Settings degraded: {}", diagnostic.message()),
        );
    }
    if legacy_state_path.is_some_and(Path::exists) {
        return "Legacy TUI state is available — open Settings with Ctrl+O to import".to_string();
    }
    "Ready".to_string()
}

/// Formats an all-or-nothing preview rejection for the single-line status convention.
fn format_update_diagnostics(
    diagnostics: &[classic_user_settings_core::UpdateDiagnostic],
) -> String {
    diagnostics.first().map_or_else(
        || "User Settings update was rejected".to_string(),
        |diagnostic| format!("User Settings update rejected: {}", diagnostic.message()),
    )
}

/// Resolves a possibly relative path against the App's canonical CLASSIC root.
fn normalize_path(classic_root: &Path, path: &Path) -> PathBuf {
    let absolute = if path.is_absolute() {
        path.to_path_buf()
    } else {
        classic_root.join(path)
    };

    absolute.canonicalize().unwrap_or(absolute)
}

#[cfg(test)]
#[path = "app_tests.rs"]
mod tests;
