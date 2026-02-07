//! CLASSIC GUI - Application entry point
//!
//! Production startup sequence: logging, renderer fallback, Tokio runtime,
//! self-healing state load, window creation, and event loop.
//! Uses the global Tokio runtime from classic-shared-core (ONE RUNTIME RULE).

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

slint::include_modules!();

use std::rc::Rc;
use std::sync::Arc;
use std::time::Duration;

use classic_config_core::ClassicConfig;
use classic_shared_core::{get_runtime, set_dispatcher, AsyncBridge, SlintDispatcher};
use parking_lot::Mutex;
use slint::{ModelRc, SharedString, VecModel};
use tokio_util::sync::CancellationToken;

use classic_gui::{
    browse_folder, copy_to_clipboard, detect_game_version, game_version_index_to_string,
    game_version_string_to_index, get_report_content, load_settings, load_window_state,
    parse_markdown, prepare_report_entries, reset_to_defaults, save_path_setting,
    save_setting_bool, save_setting_string, save_window_state, ReportData, ScanWindowProperties,
    TabGeometry, WindowState,
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
    /// Application settings persisted to YAML
    settings: ClassicConfig,
}

fn main() {
    // 1. Initialize logging FIRST (before anything that might log)
    let _log_guard = classic_gui::init_logging();

    tracing::info!("CLASSIC GUI v{} starting", env!("CARGO_PKG_VERSION"));

    // 2. Initialize renderer with GPU-to-software fallback
    if let Err(e) = init_renderer() {
        tracing::error!("Fatal: renderer initialization failed: {}", e);
        std::process::exit(1);
    }

    // 3. Initialize global Tokio runtime (ONE RUNTIME RULE)
    let _ = get_runtime();

    // 3b. Initialize event loop dispatcher for AsyncBridge
    set_dispatcher(SlintDispatcher);

    // 4. Load state with self-healing for corrupted files
    let state = Arc::new(Mutex::new(load_state_with_healing()));

    // 5. Create main window
    let window = MainWindow::new().expect("Failed to create main window");

    // 6. Restore window state (with default geometry + off-screen validation)
    restore_state(&window, &state);

    // 7. Set up callbacks
    setup_callbacks(&window, &state);

    // 8. Mark initialization complete - state saves now enabled
    {
        state.lock().initialized = true;
    }

    // 9. Run Slint event loop (blocks until window closes)
    window.run().expect("Failed to run application");

    // 10. Save final state on exit
    save_final_state(&window, &state);

    tracing::info!("CLASSIC GUI shutting down normally");
}

/// Initialize the Slint rendering backend with GPU-to-software fallback.
///
/// Tries Skia first (which auto-falls back from GPU to CPU rasterization).
/// If Skia entirely fails to initialize, falls back to the software renderer.
fn init_renderer() -> Result<(), slint::PlatformError> {
    // Try Skia first (auto GPU-to-software within Skia)
    let result = slint::BackendSelector::new()
        .renderer_name("skia".into())
        .select();

    match result {
        Ok(()) => {
            tracing::info!("Renderer: Skia initialized");
            Ok(())
        }
        Err(skia_err) => {
            tracing::warn!(
                "Skia renderer failed: {}, trying software renderer",
                skia_err
            );
            // Fall back to pure software renderer
            match slint::BackendSelector::new()
                .renderer_name("software".into())
                .select()
            {
                Ok(()) => {
                    tracing::info!("Renderer: Software fallback initialized");
                    Ok(())
                }
                Err(sw_err) => {
                    tracing::error!(
                        "All renderers failed. Skia: {}. Software: {}",
                        skia_err,
                        sw_err
                    );
                    Err(sw_err)
                }
            }
        }
    }
}

/// Load application state with self-healing for corrupted files.
///
/// If window state (JSON) fails to parse or panics, deletes and recreates it.
/// If settings (YAML) fails to load or panics, deletes and recreates it.
/// Each file is healed independently -- a corrupted state file does
/// not cause settings to be reset, and vice versa.
fn load_state_with_healing() -> AppState {
    // Try loading window state with healing
    let window_state = match std::panic::catch_unwind(load_window_state) {
        Ok(state) => state,
        Err(_) => {
            tracing::warn!("Window state load panicked, resetting to defaults");
            if let Some(path) = classic_gui::state_file_path() {
                let _ = std::fs::remove_file(&path);
            }
            WindowState::default()
        }
    };

    // Try loading settings with healing
    let settings = match std::panic::catch_unwind(load_settings) {
        Ok(config) => config,
        Err(_) => {
            tracing::warn!("Settings load panicked, resetting to defaults");
            if let Some(path) = classic_gui::settings_file_path() {
                let _ = std::fs::remove_file(&path);
            }
            ClassicConfig::default()
        }
    };

    AppState {
        cancel_token: None,
        window_state,
        initialized: false,
        reports: None,
        settings,
    }
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

    // Restore window geometry for active tab with off-screen validation
    let geometry = ws.get_tab_geometry(ws.active_tab);
    if geometry.width > 0 && geometry.height > 0 {
        // Validate position is not wildly off-screen
        // (e.g., monitor disconnected, saved position is now invisible)
        let x_valid = geometry.x > -200 && geometry.x < 10000;
        let y_valid = geometry.y > -200 && geometry.y < 10000;

        // Restore size
        window.window().set_size(slint::LogicalSize::new(
            geometry.width as f32,
            geometry.height as f32,
        ));

        // Restore position only if valid
        if x_valid && y_valid && (geometry.x != 0 || geometry.y != 0) {
            window.window().set_position(slint::LogicalPosition::new(
                geometry.x as f32,
                geometry.y as f32,
            ));
        }
    } else {
        // No saved geometry -- use default 800x600
        window
            .window()
            .set_size(slint::LogicalSize::new(800.0, 600.0));
    }

    // Populate settings UI from loaded config
    populate_settings_ui(window, &state.settings);
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
        tracing::warn!("Failed to save window state: {}", e);
    }
}

/// Save state to disk (called during operation)
fn persist_state(state: &Arc<Mutex<AppState>>) {
    let state = state.lock();
    if !state.initialized {
        return; // Skip during initialization
    }
    if let Err(e) = save_window_state(&state.window_state) {
        tracing::warn!("Failed to save window state: {}", e);
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
    setup_settings_callbacks(window, state);
}

/// Set up scan start/cancel callbacks
fn setup_scan_callbacks(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    // Start scan callback
    {
        let window_weak = window.as_weak();
        let state = Arc::clone(state);

        window.on_start_scan_logs(move || {
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

            // Spawn real scan operation using run_cancellable for dual cancellation:
            // - Bridge-level: run_cancellable races the future against the token
            // - Inner-loop: scan_crash_logs checks is_cancelled() per-log for responsiveness
            let window_weak_completion = window_weak.clone();
            let state_completion = Arc::clone(&state);
            AsyncBridge::run_cancellable(
                cancel_token.clone(),
                classic_gui::scan_crash_logs(window_weak.clone(), cancel_token, crash_log_path),
                move |result| {
                    if let Some(w) = window_weak_completion.upgrade() {
                        match result {
                            None => {
                                // Bridge-level cancellation (token cancelled between await points)
                                w.set_scan_progress(0.0);
                                w.set_scan_status("Cancelled".into());
                                w.set_scan_in_progress(false);
                            }
                            Some(Ok(scan_result)) => {
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
                            Some(Err(msg)) => {
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

    // Start game files scan callback (stub - not yet implemented)
    {
        let window_weak = window.as_weak();
        window.on_start_scan_game(move || {
            if let Some(w) = window_weak.upgrade() {
                w.set_scan_status("Game file scanning not yet implemented".into());
            }
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

/// Populate all settings UI controls from a ClassicConfig
///
/// Called during initialization and after Reset to Defaults.
/// Must be called while `initialized` is `false` to prevent save loops.
fn populate_settings_ui(window: &MainWindow, config: &ClassicConfig) {
    // General tab
    window.set_setting_game_version_index(game_version_string_to_index(&config.game_version));
    window.set_setting_update_check(config.update_check);
    window.set_setting_fcx_mode(config.fcx_mode);

    // Auto-detection hint for game version "Auto"
    if config.game_version == "auto" {
        let hint = detect_game_version(config);
        window.set_setting_auto_detected_hint(hint.into());
    } else {
        window.set_setting_auto_detected_hint(SharedString::default());
    }

    // Scanning tab
    window.set_setting_simplify_logs(config.simplify_logs);
    window.set_setting_show_formid_values(config.show_formid_values);
    window.set_setting_move_unsolved_logs(config.move_unsolved_logs);
    window.set_setting_auto_switch_after_scan(config.auto_switch_to_results);

    // Paths tab
    if let Some(ref path) = config.paths.ini_folder {
        window.set_setting_ini_path(path.to_string_lossy().to_string().into());
    } else {
        window.set_setting_ini_path(SharedString::default());
    }
    window.set_setting_ini_error(SharedString::default());
    window.set_setting_ini_has_error(false);

    if let Some(ref path) = config.paths.mods_folder {
        window.set_setting_mods_path(path.to_string_lossy().to_string().into());
    } else {
        window.set_setting_mods_path(SharedString::default());
    }
    window.set_setting_mods_error(SharedString::default());
    window.set_setting_mods_has_error(false);
}

/// Set up all settings tab callbacks for live save-on-change persistence
fn setup_settings_callbacks(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    setup_settings_general_callbacks(window, state);
    setup_settings_scanning_callbacks(window, state);
    setup_settings_paths_callbacks(window, state);
    setup_settings_reset_callback(window, state);
}

/// Set up General sub-tab callbacks (game version, update check, FCX mode)
fn setup_settings_general_callbacks(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    // Game version dropdown changed
    {
        let window_weak = window.as_weak();
        let state = Arc::clone(state);
        window.on_setting_game_version_changed(move |index| {
            let mut state = state.lock();
            if !state.initialized {
                return;
            }
            let version_str = game_version_index_to_string(index);
            if let Err(e) = save_setting_string(&mut state.settings, "game_version", version_str) {
                tracing::warn!("Failed to save game_version: {}", e);
            }

            // If "Auto" selected (index 0), run detection and update hint
            if let Some(w) = window_weak.upgrade() {
                if index == 0 {
                    let hint = detect_game_version(&state.settings);
                    w.set_setting_auto_detected_hint(hint.into());
                } else {
                    w.set_setting_auto_detected_hint(SharedString::default());
                }
            }
        });
    }

    // Update check toggle changed
    {
        let state = Arc::clone(state);
        window.on_setting_update_check_changed(move |checked| {
            let mut state = state.lock();
            if !state.initialized {
                return;
            }
            if let Err(e) = save_setting_bool(&mut state.settings, "update_check", checked) {
                tracing::warn!("Failed to save update_check: {}", e);
            }
        });
    }

    // FCX mode toggle changed
    {
        let state = Arc::clone(state);
        window.on_setting_fcx_mode_changed(move |checked| {
            let mut state = state.lock();
            if !state.initialized {
                return;
            }
            if let Err(e) = save_setting_bool(&mut state.settings, "fcx_mode", checked) {
                tracing::warn!("Failed to save fcx_mode: {}", e);
            }
        });
    }
}

/// Set up Scanning sub-tab callbacks (simplify logs, show formid, move unsolved, auto switch)
fn setup_settings_scanning_callbacks(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    // Simplify logs toggle
    {
        let state = Arc::clone(state);
        window.on_setting_simplify_logs_changed(move |checked| {
            let mut state = state.lock();
            if !state.initialized {
                return;
            }
            if let Err(e) = save_setting_bool(&mut state.settings, "simplify_logs", checked) {
                tracing::warn!("Failed to save simplify_logs: {}", e);
            }
        });
    }

    // Show FormID values toggle
    {
        let state = Arc::clone(state);
        window.on_setting_show_formid_values_changed(move |checked| {
            let mut state = state.lock();
            if !state.initialized {
                return;
            }
            if let Err(e) =
                save_setting_bool(&mut state.settings, "show_formid_values", checked)
            {
                tracing::warn!("Failed to save show_formid_values: {}", e);
            }
        });
    }

    // Move unsolved logs toggle
    {
        let state = Arc::clone(state);
        window.on_setting_move_unsolved_logs_changed(move |checked| {
            let mut state = state.lock();
            if !state.initialized {
                return;
            }
            if let Err(e) =
                save_setting_bool(&mut state.settings, "move_unsolved_logs", checked)
            {
                tracing::warn!("Failed to save move_unsolved_logs: {}", e);
            }
        });
    }

    // Auto switch after scan toggle
    {
        let state = Arc::clone(state);
        window.on_setting_auto_switch_after_scan_changed(move |checked| {
            let mut state = state.lock();
            if !state.initialized {
                return;
            }
            if let Err(e) =
                save_setting_bool(&mut state.settings, "auto_switch_to_results", checked)
            {
                tracing::warn!("Failed to save auto_switch_to_results: {}", e);
            }
        });
    }
}

/// Set up Paths sub-tab callbacks (browse dialogs and path accepted handlers)
fn setup_settings_paths_callbacks(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    // Browse INI folder
    {
        let window_weak = window.as_weak();
        let state = Arc::clone(state);
        window.on_setting_browse_ini(move || {
            let window_weak = window_weak.clone();
            let state = Arc::clone(&state);

            let current_path = window_weak
                .upgrade()
                .map(|w| w.get_setting_ini_path().to_string())
                .unwrap_or_default();

            let start_dir = if current_path.is_empty() {
                None
            } else {
                Some(current_path)
            };

            AsyncBridge::run_with_ui_update(
                async move {
                    browse_folder("Select INI Folder", start_dir.as_deref()).await
                },
                move |result| {
                    if let Some(path) = result {
                        let mut s = state.lock();
                        if !s.initialized {
                            return;
                        }
                        match save_path_setting(&mut s.settings, "ini_folder", &path) {
                            Ok(()) => {
                                if let Some(w) = window_weak.upgrade() {
                                    w.set_setting_ini_path(path.into());
                                    w.set_setting_ini_has_error(false);
                                    w.set_setting_ini_error(SharedString::default());
                                }
                            }
                            Err(e) => {
                                if let Some(w) = window_weak.upgrade() {
                                    w.set_setting_ini_has_error(true);
                                    w.set_setting_ini_error(e.into());
                                }
                            }
                        }
                    }
                },
            );
        });
    }

    // Browse mods folder
    {
        let window_weak = window.as_weak();
        let state = Arc::clone(state);
        window.on_setting_browse_mods(move || {
            let window_weak = window_weak.clone();
            let state = Arc::clone(&state);

            let current_path = window_weak
                .upgrade()
                .map(|w| w.get_setting_mods_path().to_string())
                .unwrap_or_default();

            let start_dir = if current_path.is_empty() {
                None
            } else {
                Some(current_path)
            };

            AsyncBridge::run_with_ui_update(
                async move {
                    browse_folder("Select Mods Folder", start_dir.as_deref()).await
                },
                move |result| {
                    if let Some(path) = result {
                        let mut s = state.lock();
                        if !s.initialized {
                            return;
                        }
                        match save_path_setting(&mut s.settings, "mods_folder", &path) {
                            Ok(()) => {
                                if let Some(w) = window_weak.upgrade() {
                                    w.set_setting_mods_path(path.into());
                                    w.set_setting_mods_has_error(false);
                                    w.set_setting_mods_error(SharedString::default());
                                }
                            }
                            Err(e) => {
                                if let Some(w) = window_weak.upgrade() {
                                    w.set_setting_mods_has_error(true);
                                    w.set_setting_mods_error(e.into());
                                }
                            }
                        }
                    }
                },
            );
        });
    }

    // INI path accepted (Enter key or focus loss)
    {
        let window_weak = window.as_weak();
        let state = Arc::clone(state);
        window.on_setting_ini_path_accepted(move |text| {
            let mut s = state.lock();
            if !s.initialized {
                return;
            }
            let path_str = text.to_string();
            match save_path_setting(&mut s.settings, "ini_folder", &path_str) {
                Ok(()) => {
                    if let Some(w) = window_weak.upgrade() {
                        w.set_setting_ini_has_error(false);
                        w.set_setting_ini_error(SharedString::default());
                    }
                }
                Err(e) => {
                    if let Some(w) = window_weak.upgrade() {
                        w.set_setting_ini_has_error(true);
                        w.set_setting_ini_error(e.into());
                    }
                }
            }
        });
    }

    // Mods path accepted
    {
        let window_weak = window.as_weak();
        let state = Arc::clone(state);
        window.on_setting_mods_path_accepted(move |text| {
            let mut s = state.lock();
            if !s.initialized {
                return;
            }
            let path_str = text.to_string();
            match save_path_setting(&mut s.settings, "mods_folder", &path_str) {
                Ok(()) => {
                    if let Some(w) = window_weak.upgrade() {
                        w.set_setting_mods_has_error(false);
                        w.set_setting_mods_error(SharedString::default());
                    }
                }
                Err(e) => {
                    if let Some(w) = window_weak.upgrade() {
                        w.set_setting_mods_has_error(true);
                        w.set_setting_mods_error(e.into());
                    }
                }
            }
        });
    }

}

/// Set up Reset to Defaults callback
fn setup_settings_reset_callback(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    let window_weak = window.as_weak();
    let state = Arc::clone(state);

    window.on_setting_reset_to_defaults(move || {
        let mut s = state.lock();
        // Temporarily disable saves to prevent loops during UI repopulation
        let was_initialized = s.initialized;
        s.initialized = false;

        // Reset to defaults and save to YAML
        s.settings = reset_to_defaults();

        // Repopulate all UI controls from fresh defaults
        if let Some(w) = window_weak.upgrade() {
            populate_settings_ui(&w, &s.settings);
        }

        // Re-enable saves
        s.initialized = was_initialized;
    });
}
