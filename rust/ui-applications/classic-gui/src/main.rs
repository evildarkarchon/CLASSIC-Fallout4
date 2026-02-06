//! CLASSIC GUI - Application entry point
//!
//! Initializes the Slint GUI application and runs the event loop.
//! Uses the global Tokio runtime from classic-shared-core (ONE RUNTIME RULE).

slint::include_modules!();

use std::sync::Arc;

use std::time::Duration;

use classic_shared_core::{get_runtime, AsyncBridge};
use parking_lot::Mutex;
use tokio_util::sync::CancellationToken;

use classic_gui::{
    browse_folder, load_window_state, save_window_state, ScanWindowProperties, TabGeometry,
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
}

impl AppState {
    /// Create new app state with loaded window state
    fn new() -> Self {
        Self {
            cancel_token: None,
            window_state: load_window_state(),
            initialized: false,
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

fn setup_callbacks(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    setup_scan_callbacks(window, state);
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
            AsyncBridge::run_with_ui_update(
                classic_gui::scan_crash_logs(window_weak.clone(), cancel_token, crash_log_path),
                move |result| {
                    if let Some(w) = window_weak_completion.upgrade() {
                        match result {
                            Ok(scan_result) => {
                                w.set_scan_progress(100.0);
                                w.set_scan_status(scan_result.format_status().into());
                                w.set_scan_in_progress(false);

                                // Auto-switch to Results tab on success with results
                                // (not on cancel or zero logs per CONTEXT.md)
                                if scan_result.has_results() {
                                    w.set_active_tab_index(1); // Results tab
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
                    let window_weak_clear = window_weak_completion.clone();
                    AsyncBridge::spawn_background(async move {
                        tokio::time::sleep(Duration::from_secs(5)).await;
                        let _ = window_weak_clear.upgrade_in_event_loop(|w| {
                            if !w.get_scan_in_progress() {
                                w.set_scan_status("".into());
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
