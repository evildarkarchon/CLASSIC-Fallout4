//! CLASSIC GUI - Application entry point
//!
//! Initializes the Slint GUI application and runs the event loop.
//! Uses the global Tokio runtime from classic-shared-core (ONE RUNTIME RULE).

slint::include_modules!();

use std::rc::Rc;
use std::sync::Arc;
use std::time::Duration;

use classic_shared_core::{get_runtime, AsyncBridge};
use parking_lot::Mutex;
use slint::{ModelRc, SharedString, VecModel};
use tokio_util::sync::CancellationToken;

use classic_gui::{
    browse_folder, copy_to_clipboard, get_report_content, load_window_state, parse_markdown,
    prepare_report_entries, save_window_state, ReportData, ScanWindowProperties, TabGeometry,
    WindowState,
};

// Implement ScanWindowProperties for the generated MainWindow
impl ScanWindowProperties for MainWindow {
    fn set_scan_progress(&self, value: f32) {
        self.set_scan_progress(value);
    }

    fn set_scan_status(&self, value: slint::SharedString) {
        self.set_scan_status(value);
    }

    fn set_scan_in_progress(&self, value: bool) {
        self.set_scan_in_progress(value);
    }
}

/// Application state shared between callbacks
struct AppState {
    /// Cancellation token for current scan operation
    cancel_token: Option<CancellationToken>,
    /// Window state for persistence
    window_state: WindowState,
    /// Flag to prevent saving during initialization
    initialized: bool,
    /// Scan reports for the Results tab
    reports: Option<ReportData>,
}

impl AppState {
    /// Create new app state with loaded window state
    fn new() -> Self {
        Self {
            cancel_token: None,
            window_state: load_window_state(),
            initialized: false,
            reports: None,
        }
    }
}

fn main() {
    // Initialize global Tokio runtime before Slint event loop
    // This ensures ONE RUNTIME RULE compliance
    let _ = get_runtime();

    // Create shared state and load persisted state
    let state = Arc::new(Mutex::new(AppState::new()));

    // Create main window
    let window = MainWindow::new().expect("Failed to create main window");

    // Restore window state from disk
    restore_state(&window, &state);

    // Set up callbacks
    setup_callbacks(&window, &state);

    // Mark initialization complete - state saves now enabled
    {
        let mut state = state.lock();
        state.initialized = true;
    }

    // Run Slint event loop (blocks until window closes)
    window.run().expect("Failed to run application");

    // Save final state on exit
    save_final_state(&window, &state);
}

/// Restore window state from persisted data
fn restore_state(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    let state = state.lock();
    let ws = &state.window_state;

    // Restore paths
    if !ws.crash_log_path.is_empty() {
        window.set_crash_log_path(ws.crash_log_path.clone().into());
    }
    if !ws.game_path.is_empty() {
        window.set_game_path(ws.game_path.clone().into());
    }

    // Restore active tab
    window.set_active_tab_index(ws.active_tab);

    // Restore window geometry for active tab
    let geometry = ws.get_tab_geometry(ws.active_tab);
    if geometry.width > 0 && geometry.height > 0 {
        // Restore size
        window.window().set_size(slint::LogicalSize::new(
            geometry.width as f32,
            geometry.height as f32,
        ));

        // Restore position (only if valid - some platforms don't support this)
        if geometry.x != 0 || geometry.y != 0 {
            window.window().set_position(slint::LogicalPosition::new(
                geometry.x as f32,
                geometry.y as f32,
            ));
        }
    }
}

/// Save final state before exit
fn save_final_state(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    let mut state = state.lock();

    // Capture current paths
    state.window_state.crash_log_path = window.get_crash_log_path().to_string();
    state.window_state.game_path = window.get_game_path().to_string();

    // Capture current tab
    let active_tab = window.get_active_tab_index();
    state.window_state.active_tab = active_tab;

    // Capture window geometry for current tab
    let size = window.window().size();
    let position = window.window().position();
    state.window_state.set_tab_geometry(
        active_tab,
        TabGeometry {
            x: position.x as i32,
            y: position.y as i32,
            width: size.width as u32,
            height: size.height as u32,
            maximized: false, // TODO: Slint doesn't expose maximized state
        },
    );

    // Save to disk
    if let Err(e) = save_window_state(&state.window_state) {
        eprintln!("Failed to save window state: {}", e);
    }
}

/// Save state to disk (called during operation)
fn persist_state(state: &Arc<Mutex<AppState>>) {
    let state = state.lock();
    if !state.initialized {
        return; // Skip during initialization
    }
    if let Err(e) = save_window_state(&state.window_state) {
        eprintln!("Failed to save window state: {}", e);
    }
}

/// Parse markdown content and push blocks to the Slint report-blocks model
fn update_report_blocks(window: &MainWindow, markdown_content: &str) {
    let blocks = parse_markdown(markdown_content);
    let model = Rc::new(VecModel::default());
    for block in &blocks {
        model.push(MarkdownBlock {
            block_type: block.block_type,
            text: SharedString::from(block.text.as_str()),
            heading_level: block.heading_level,
            is_bold: block.is_bold,
            is_italic: block.is_italic,
            indent_level: block.indent_level,
            bullet_marker: SharedString::from(block.bullet_marker.as_str()),
        });
    }
    window.set_report_blocks(ModelRc::from(model));
}

fn setup_callbacks(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    setup_scan_callbacks(window, state);
    setup_results_callbacks(window, state);
    setup_browse_callbacks(window, state);
    setup_tab_callback(window, state);
}

/// Set up scan start/cancel callbacks
fn setup_scan_callbacks(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    // Start scan callback
    {
        let window_weak = window.as_weak();
        let state = Arc::clone(state);

        window.on_start_scan(move || {
            let window_weak = window_weak.clone();

            // Create new cancellation token
            let cancel_token = CancellationToken::new();

            // Store token for cancel button
            {
                let mut state = state.lock();
                state.cancel_token = Some(cancel_token.clone());
            }

            // Get crash log path from UI
            let crash_log_path = window_weak
                .upgrade()
                .map(|w| w.get_crash_log_path().to_string())
                .unwrap_or_default();

            // Set UI to scanning state (immediate progress display per CONTEXT.md)
            if let Some(w) = window_weak.upgrade() {
                w.set_scan_in_progress(true);
                w.set_scan_progress(-1.0); // Indeterminate during discovery
                w.set_scan_status("Discovering crash logs...".into());
            }

            // Spawn real scan operation using OrchestratorCore
            let window_weak_completion = window_weak.clone();
            let state_completion = Arc::clone(&state);
            AsyncBridge::run_with_ui_update(
                classic_gui::scan_crash_logs(window_weak.clone(), cancel_token, crash_log_path),
                move |result| {
                    if let Some(w) = window_weak_completion.upgrade() {
                        match result {
                            Ok(scan_result) => {
                                let has_results = scan_result.has_results();
                                let status_text = scan_result.format_status();
                                let reports = scan_result.reports;

                                w.set_scan_progress(100.0);
                                w.set_scan_status(status_text.into());
                                w.set_scan_in_progress(false);

                                if has_results {
                                    // Build sorted report entries (descending by default)
                                    let entries = prepare_report_entries(&reports, false);

                                    // Create Slint model from entries
                                    let model = Rc::new(VecModel::default());
                                    for entry in &entries {
                                        model.push(ReportEntry {
                                            filename: SharedString::from(entry.filename.as_str()),
                                            timestamp: SharedString::from(
                                                entry.timestamp.as_str(),
                                            ),
                                            source_index: entry.source_index,
                                        });
                                    }
                                    w.set_report_list_model(ModelRc::from(model));
                                    w.set_has_reports(true);

                                    // Auto-select first report and show its content
                                    if let Some(first) = entries.first() {
                                        w.set_selected_report_index(0);
                                        let content =
                                            get_report_content(&reports, first.source_index);
                                        w.set_report_content(SharedString::from(&content));
                                        update_report_blocks(&w, &content);
                                    }

                                    // Switch to Results tab
                                    w.set_active_tab_index(1);
                                }

                                // Store reports in AppState for use by results callbacks
                                {
                                    let mut app_state = state_completion.lock();
                                    app_state.reports = Some(ReportData { reports });
                                }
                            }
                            Err(msg) => {
                                w.set_scan_progress(0.0);
                                w.set_scan_status(msg.into());
                                w.set_scan_in_progress(false);
                            }
                        }
                    }

                    // Auto-clear status after 5 seconds (Claude's discretion per CONTEXT.md)
                    // Only clears if no new scan is in progress (user may have started another)
                    let window_weak_clear = window_weak_completion.clone();
                    AsyncBridge::spawn_background(async move {
                        tokio::time::sleep(Duration::from_secs(5)).await;
                        let _ = window_weak_clear.upgrade_in_event_loop(|w| {
                            if !w.get_scan_in_progress() {
                                w.set_scan_status("Ready".into());
                                w.set_scan_progress(0.0);
                            }
                        });
                    });
                },
            );
        });
    }

    // Cancel scan callback
    {
        let state = Arc::clone(state);

        window.on_cancel_scan(move || {
            let state = state.lock();
            if let Some(ref token) = state.cancel_token {
                token.cancel();
            }
        });
    }
}

/// Set up Results tab callbacks for report selection, search, sort, and copy
fn setup_results_callbacks(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    // Report selection callback -- updates viewer when user clicks a report
    {
        let window_weak = window.as_weak();
        let state = Arc::clone(state);
        window.on_report_selected(move |source_index| {
            let state = state.lock();
            if let Some(ref report_data) = state.reports {
                let content = get_report_content(&report_data.reports, source_index);
                if let Some(w) = window_weak.upgrade() {
                    w.set_report_content(SharedString::from(&content));
                    update_report_blocks(&w, &content);
                }
            }
        });
    }

    // Search filter callback -- rebuilds model with filtered entries
    {
        let window_weak = window.as_weak();
        let state = Arc::clone(state);

        window.on_report_search_changed(move |text| {
            let text_str = text.to_string();

            let state = state.lock();
            if let Some(ref report_data) = state.reports {
                if let Some(w) = window_weak.upgrade() {
                    let sort_ascending = w.get_report_sort_ascending();
                    let entries = prepare_report_entries(&report_data.reports, sort_ascending);

                    // Filter by filename (case-insensitive)
                    let text_lower = text_str.to_lowercase();
                    let filtered: Vec<_> = entries
                        .into_iter()
                        .filter(|entry| {
                            text_lower.is_empty()
                                || entry.filename.to_lowercase().contains(&text_lower)
                        })
                        .collect();

                    // Rebuild model with filtered entries
                    let model = Rc::new(VecModel::default());
                    for entry in &filtered {
                        model.push(ReportEntry {
                            filename: SharedString::from(entry.filename.as_str()),
                            timestamp: SharedString::from(entry.timestamp.as_str()),
                            source_index: entry.source_index,
                        });
                    }
                    w.set_report_list_model(ModelRc::from(model));

                    // Auto-select first filtered result
                    if let Some(first) = filtered.first() {
                        w.set_selected_report_index(0);
                        let content =
                            get_report_content(&report_data.reports, first.source_index);
                        w.set_report_content(SharedString::from(&content));
                        update_report_blocks(&w, &content);
                    }
                }
            }
        });
    }

    // Sort toggle callback -- re-sorts and rebuilds model
    {
        let window_weak = window.as_weak();
        let state = Arc::clone(state);

        window.on_report_sort_toggled(move || {
            let state = state.lock();
            if let Some(ref report_data) = state.reports {
                if let Some(w) = window_weak.upgrade() {
                    let new_ascending = !w.get_report_sort_ascending();
                    w.set_report_sort_ascending(new_ascending);

                    let entries = prepare_report_entries(&report_data.reports, new_ascending);

                    let model = Rc::new(VecModel::default());
                    for entry in &entries {
                        model.push(ReportEntry {
                            filename: SharedString::from(entry.filename.as_str()),
                            timestamp: SharedString::from(entry.timestamp.as_str()),
                            source_index: entry.source_index,
                        });
                    }
                    w.set_report_list_model(ModelRc::from(model));

                    // Auto-select first after re-sort
                    if let Some(first) = entries.first() {
                        w.set_selected_report_index(0);
                        let content =
                            get_report_content(&report_data.reports, first.source_index);
                        w.set_report_content(SharedString::from(&content));
                        update_report_blocks(&w, &content);
                    }
                }
            }
        });
    }

    // Copy All callback -- copies viewer content to system clipboard
    {
        let window_weak = window.as_weak();
        window.on_report_copy_all(move || {
            if let Some(w) = window_weak.upgrade() {
                let content = w.get_report_content().to_string();
                if !content.is_empty() {
                    let _ = copy_to_clipboard(&content);
                }
            }
        });
    }
}

/// Set up browse folder callbacks
fn setup_browse_callbacks(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    // Browse crash logs callback
    {
        let window_weak = window.as_weak();
        let state = Arc::clone(state);

        window.on_browse_crash_logs(move || {
            let window_weak = window_weak.clone();
            let state = Arc::clone(&state);

            // Get current path for starting directory
            let current_path = window_weak
                .upgrade()
                .map(|w| w.get_crash_log_path().to_string())
                .unwrap_or_default();

            let start_dir = if current_path.is_empty() {
                None
            } else {
                Some(current_path.clone())
            };

            // Spawn async browse dialog
            AsyncBridge::run_with_ui_update(
                async move {
                    browse_folder(
                        "Select Crash Log Folder",
                        start_dir.as_deref(),
                    )
                    .await
                },
                move |result| {
                    if let Some(path) = result {
                        if let Some(w) = window_weak.upgrade() {
                            w.set_crash_log_path(path.clone().into());
                            // Update state and save
                            {
                                let mut state = state.lock();
                                state.window_state.crash_log_path = path;
                            }
                            persist_state(&state);
                        }
                    }
                },
            );
        });
    }

    // Browse game folder callback
    {
        let window_weak = window.as_weak();
        let state = Arc::clone(state);

        window.on_browse_game_folder(move || {
            let window_weak = window_weak.clone();
            let state = Arc::clone(&state);

            // Get current path for starting directory
            let current_path = window_weak
                .upgrade()
                .map(|w| w.get_game_path().to_string())
                .unwrap_or_default();

            let start_dir = if current_path.is_empty() {
                None
            } else {
                Some(current_path.clone())
            };

            // Spawn async browse dialog
            AsyncBridge::run_with_ui_update(
                async move {
                    browse_folder("Select Game Folder", start_dir.as_deref()).await
                },
                move |result| {
                    if let Some(path) = result {
                        if let Some(w) = window_weak.upgrade() {
                            w.set_game_path(path.clone().into());
                            // Update state and save
                            {
                                let mut state = state.lock();
                                state.window_state.game_path = path;
                            }
                            persist_state(&state);
                        }
                    }
                },
            );
        });
    }
}

/// Set up tab change callback for per-tab state persistence
fn setup_tab_callback(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    let window_weak = window.as_weak();
    let state = Arc::clone(state);

    window.on_tab_changed(move |new_tab| {
        let Some(w) = window_weak.upgrade() else {
            return;
        };

        {
            let mut state = state.lock();
            if !state.initialized {
                return;
            }

            // Save geometry for previous tab before switching
            let old_tab = state.window_state.active_tab;
            if old_tab != new_tab {
                let size = w.window().size();
                let position = w.window().position();
                state.window_state.set_tab_geometry(
                    old_tab,
                    TabGeometry {
                        x: position.x as i32,
                        y: position.y as i32,
                        width: size.width as u32,
                        height: size.height as u32,
                        maximized: false,
                    },
                );
            }

            state.window_state.active_tab = new_tab;
        }
        persist_state(&state);
    });
}
