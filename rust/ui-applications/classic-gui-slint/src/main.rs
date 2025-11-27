//! CLASSIC Slint GUI - Main Entry Point
//!
//! Pure Rust GUI using Slint framework with Fluent Design System for
//! Fallout 4 and Skyrim crash log analysis.

// Suppress documentation warnings for generated Slint code
#![allow(missing_docs)]
#![allow(unsafe_code)] // Allow unsafe for ThreadSafeTimer

slint::include_modules!();

mod app_state;
mod geometry;
mod handlers;
mod models;

use anyhow::Result;
use app_state::AppState;
use classic_shared_core::AsyncBridge;
use geometry::WindowGeometry;
use notify::RecursiveMode;
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

use slint::{PhysicalPosition, PhysicalSize};

/// Wrapper for slint::Timer to allow it to be passed between threads (needed for AsyncBridge)
/// This is safe because we only access the timer on the UI thread.
#[allow(dead_code)] // The field 0 is conceptually used even if not directly accessed
struct ThreadSafeTimer(slint::Timer);
unsafe impl Send for ThreadSafeTimer {}
unsafe impl Sync for ThreadSafeTimer {}

/// Pending action awaiting user confirmation
///
/// This enum tracks which action is waiting for user confirmation via the confirmation dialog.
/// When a user confirms an action, the appropriate handler is invoked based on this state.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum PendingConfirmation {
    None,
    // Future actions can be added here, e.g.:
    // DeleteAllReports,
    // ClearPapyrusLogs,
    // ResetSettings,
}

fn main() -> Result<(), slint::PlatformError> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_target(false)
        .with_thread_ids(false)
        .with_level(true)
        .init();

    // Get version from Cargo.toml at compile time
    const VERSION: &str = env!("CARGO_PKG_VERSION");

    tracing::info!("Starting CLASSIC GUI v{}", VERSION);

    // Create default app_state first (will be loaded async after window creation)
    let app_state = Arc::new(parking_lot::RwLock::new(AppState::default()));

    // Track pending confirmation action
    let pending_confirmation = Arc::new(parking_lot::Mutex::new(PendingConfirmation::None));

    // Load saved window geometry
    let geometry = Arc::new(parking_lot::Mutex::new(WindowGeometry::load()));
    let initial_geometry = geometry.lock().clone();
    tracing::debug!("Loaded window geometry: {:?}", initial_geometry);

    // Create the main window
    let main_window = MainWindow::new()?;

    // Set version dynamically from CARGO_PKG_VERSION
    main_window.set_app_version(VERSION.into());

    // Flag to ensure file watcher is initialized only once
    let file_watcher_initialized = Arc::new(AtomicBool::new(false));
    // Store debounce timer instance to stop on exit
    let main_slint_timer: Arc<parking_lot::Mutex<Option<ThreadSafeTimer>>> =
        Arc::new(parking_lot::Mutex::new(None));

    // Apply saved geometry
    let window = main_window.window();
    window.set_size(PhysicalSize::new(
        initial_geometry.width as u32,
        initial_geometry.height as u32,
    ));

    // Set position if not default (-1 means center)
    if initial_geometry.x >= 0 && initial_geometry.y >= 0 {
        window.set_position(PhysicalPosition::new(
            initial_geometry.x,
            initial_geometry.y,
        ));
    }

    // Track last tab index for geometry saving
    let last_tab_index = Arc::new(parking_lot::Mutex::new(0));

    // Handle tab changes for per-tab geometry
    main_window.on_tab_changed({
        let window_weak = main_window.as_weak();
        let geometry = geometry.clone();
        let last_tab_index = last_tab_index.clone();
        move |new_tab_index| {
            if let Some(window) = window_weak.upgrade() {
                let slint_window = window.window();
                let size = slint_window.size();

                let mut geo = geometry.lock();
                let mut last_idx = last_tab_index.lock();

                // Save size for previous tab
                geo.set_tab_size(*last_idx, size.width as i32, size.height as i32);

                // Update current tab index
                *last_idx = new_tab_index;

                // Apply size for new tab
                if let Some((w, h)) = geo.get_tab_size(new_tab_index) {
                    slint_window.set_size(PhysicalSize::new(w as u32, h as u32));
                } else {
                    // Default defaults
                    if new_tab_index == 3 {
                        // Results tab
                        slint_window.set_size(PhysicalSize::new(1000, 600));
                    } else {
                        slint_window.set_size(PhysicalSize::new(650, 350));
                    }
                }
            }
        }
    });

    // Load application configuration asynchronously using AsyncBridge
    {
        let window_weak = main_window.as_weak();
        let state = app_state.clone();

        tracing::info!("Loading application configuration...");

        let main_slint_timer_arc_clone = main_slint_timer.clone(); // Clone BEFORE moving into closure

        AsyncBridge::run_with_ui_update(AppState::load(), move |result| {
            // ... existing AppState loading and UI update logic ...
            let main_slint_timer_arc_clone_inner = main_slint_timer_arc_clone.clone(); // Clone for inner closure if needed (or just use the captured one)
            match result {
                Ok(loaded_state_arc) => {
                    let loaded_app_state_read_guard = loaded_state_arc.read(); // Get a read guard for the source AppState
                    let mut current_app_state_write_guard = state.write(); // Get a write guard for the shared AppState

                    // Manually update the fields of the AppState that is already in `state`
                    current_app_state_write_guard.game = loaded_app_state_read_guard.game.clone();
                    current_app_state_write_guard.config =
                        loaded_app_state_read_guard.config.clone();
                    current_app_state_write_guard.mods_folder =
                        loaded_app_state_read_guard.mods_folder.clone();
                    current_app_state_write_guard.scan_folder =
                        loaded_app_state_read_guard.scan_folder.clone();
                    current_app_state_write_guard.auto_refresh_interval_ms =
                        loaded_app_state_read_guard.auto_refresh_interval_ms;

                    // Drop guards immediately after use
                    drop(loaded_app_state_read_guard);
                    drop(current_app_state_write_guard);

                    let state_guard = state.read(); // Acquire read guard for state after it's been updated, for broader scope

                    tracing::info!(
                        "Configuration loaded successfully - Game: {}, Root: {}",
                        state_guard.game_name(),
                        state_guard.game_root().display()
                    );

                    // Extract FileWatcher and debounce duration early
                    // We must clone FileWatcher to own it, and get the u64 duration
                    // Then we drop the guard to release the borrow on 'state'
                    let file_watcher_instance = state_guard.file_watcher().clone();
                    let debounce_duration_ms = state_guard.auto_refresh_interval_ms();
                    let docs_root = state_guard.docs_root().cloned();
                    let scan_folder = state_guard.scan_folder().cloned();
                    drop(state_guard); // CRITICAL: Drop guard here

                    // Update UI with loaded paths
                    if let Some(w) = window_weak.upgrade() {
                        // Re-acquire guard strictly for UI updates if needed, or just use values if we extracted them (we didn't extract paths)
                        // Actually, we already updated UI above using state_guard. Wait, the previous code updated UI *inside* the guard scope.
                        // Let's re-acquire for UI path setting if we moved it.
                        // Ah, I see I need to move the UI update logic too or re-acquire.
                        // Let's re-acquire for UI updates to be safe and simple.
                        let state_guard = state.read();
                        if let Some(mods_folder) = state_guard.mods_folder() {
                            w.set_mods_folder_path(
                                mods_folder.to_string_lossy().to_string().into(),
                            );
                            tracing::debug!(
                                "Loaded mods folder from config: {}",
                                mods_folder.display()
                            );
                        }
                        if let Some(scan_folder) = state_guard.scan_folder() {
                            w.set_scan_folder_path(
                                scan_folder.to_string_lossy().to_string().into(),
                            );
                            tracing::debug!(
                                "Loaded scan folder from config: {}",
                                scan_folder.display()
                            );
                        }
                        drop(state_guard); // Drop again

                        // Initialize file watcher if not already initialized
                        if !file_watcher_initialized.load(Ordering::SeqCst) {
                            let window_for_refresh = w.as_weak();

                            // Initialize background watcher and get receiver for events
                            // Now passing the debounce duration to the watcher init
                            let event_receiver = match file_watcher_instance
                                .init(Duration::from_millis(debounce_duration_ms))
                            {
                                Ok(rx) => rx,
                                Err(e) => {
                                    tracing::error!("Failed to initialize file watcher: {}", e);
                                    return;
                                }
                            };

                            // Create Slint timer on the UI thread to process events
                            let timer_storage_arc = main_slint_timer_arc_clone_inner.clone();
                            let file_watcher_for_timer = file_watcher_instance.clone();

                            let timer = slint::Timer::default();
                            // Poll frequently (100ms) since debouncing is handled in the background thread
                            timer.start(
                                slint::TimerMode::Repeated,
                                Duration::from_millis(100),
                                move || {
                                    // Only process events if watcher is not paused
                                    if !file_watcher_for_timer.is_paused() {
                                        // Check if we have any debounced events waiting
                                        // We use try_recv() to avoid blocking the UI thread
                                        let mut refresh_needed = false;

                                        while let Ok(changed_paths) = event_receiver.try_recv() {
                                            if !changed_paths.is_empty() {
                                                tracing::debug!(
                                                    "Received {} file changes from watcher",
                                                    changed_paths.len()
                                                );
                                                refresh_needed = true;
                                            }
                                        }

                                        if refresh_needed
                                            && let Some(ui) = window_for_refresh.upgrade()
                                        {
                                            tracing::info!(
                                                "Triggering reports refresh due to file changes"
                                            );
                                            ui.invoke_refresh_reports();
                                        }
                                    }
                                },
                            );
                            *timer_storage_arc.lock() = Some(ThreadSafeTimer(timer)); // Store the timer

                            // Add watch paths
                            // 1. Crash Logs folder
                            if let Some(ref docs) = docs_root {
                                let crash_logs = docs.join("Crash Logs");
                                if crash_logs.exists()
                                    && let Err(e) = file_watcher_instance
                                        .add_path(&crash_logs, RecursiveMode::NonRecursive)
                                {
                                    tracing::error!("Failed to watch Crash Logs: {}", e);
                                }
                                // 3. Unsolved Logs folder
                                let unsolved = docs.join("CLASSIC Backup").join("Unsolved Logs");
                                if unsolved.exists()
                                    && let Err(e) = file_watcher_instance
                                        .add_path(&unsolved, RecursiveMode::NonRecursive)
                                {
                                    tracing::error!("Failed to watch Unsolved Logs: {}", e);
                                }
                            } else {
                                // Fallback to current directory "Crash Logs" if docs_root not set
                                let crash_logs = PathBuf::from("Crash Logs");
                                if crash_logs.exists()
                                    && let Err(e) = file_watcher_instance
                                        .add_path(&crash_logs, RecursiveMode::NonRecursive)
                                {
                                    tracing::error!("Failed to watch Crash Logs (fallback): {}", e);
                                }
                            }

                            // 2. Custom scan folder
                            if let Some(ref custom) = scan_folder
                                && custom.exists()
                                && let Err(e) = file_watcher_instance
                                    .add_path(custom, RecursiveMode::NonRecursive)
                            {
                                tracing::error!("Failed to watch Custom folder: {}", e);
                            }
                            file_watcher_initialized.store(true, Ordering::SeqCst);
                        }

                        // Check for updates if enabled in settings
                        let state_guard = state.read();
                        if state_guard.update_check() {
                            tracing::info!("Automatic update check enabled");
                            let window_for_update = w.as_weak();
                            let version = w.get_app_version().to_string();

                            // Use AsyncBridge to run update check with proper Tokio runtime context
                            classic_shared_core::AsyncBridge::run_with_ui_update(
                                async move {
                                    // Load update preferences
                                    let prefs = handlers::update_check::UpdatePreferences::load()
                                        .await
                                        .unwrap_or_default();

                                    if prefs.dont_check_again {
                                        tracing::info!(
                                            "Update checking disabled by user preference"
                                        );
                                        return None;
                                    }

                                    // Check for updates
                                    match handlers::update_check::check_for_updates(&version).await
                                    {
                                        Ok(Some(info)) => {
                                            // Check if this version was skipped
                                            if prefs.should_skip(&info.version) {
                                                tracing::info!(
                                                    "Skipping previously dismissed update: {}",
                                                    info.version
                                                );
                                                return None;
                                            }
                                            Some((version, info))
                                        }
                                        Ok(None) => {
                                            tracing::info!("No update available on startup");
                                            None
                                        }
                                        Err(e) => {
                                            tracing::warn!("Automatic update check failed: {}", e);
                                            None
                                        }
                                    }
                                },
                                move |result| {
                                    if let Some((version, info)) = result {
                                        // Show update dialog
                                        if let Some(w) = window_for_update.upgrade() {
                                            tracing::info!(
                                                "Update available on startup: {}",
                                                info.version
                                            );
                                            w.set_update_available(true);
                                            w.set_update_current_version(version.into());
                                            w.set_update_latest_version(info.version.into());
                                            w.set_update_release_notes(info.release_notes.into());
                                            w.set_update_error_message("".into());
                                            w.set_show_update_dialog(true);
                                        }
                                    }
                                },
                            );
                        } else {
                            tracing::debug!("Automatic update check disabled in settings");
                        }
                    }
                }
                Err(e) => {
                    tracing::error!("Failed to load configuration: {}", e);
                    tracing::warn!("Using default configuration (some features may not work)");
                }
            }
        });
    }

    // Setup window lifecycle callbacks
    let window_weak = main_window.as_weak();
    let geometry_clone = geometry.clone();
    let last_tab_index_clone = last_tab_index.clone();
    let app_state_clone_for_close = app_state.clone();
    let main_slint_timer_for_close = main_slint_timer.clone(); // Clone for capturing in closure
    main_window.on_window_closed(move || {
        tracing::info!("Window closed by user");

        // Save window geometry before closing
        if let Some(main_window) = window_weak.upgrade() {
            let window = main_window.window();
            let size = window.size();
            let position = window.position();

            let mut geo = geometry_clone.lock();
            geo.width = size.width as i32;
            geo.height = size.height as i32;
            geo.x = position.x;
            geo.y = position.y;

            // Save size for current tab
            let current_tab = *last_tab_index_clone.lock();
            geo.set_tab_size(current_tab, size.width as i32, size.height as i32);

            if let Err(e) = geo.save() {
                tracing::error!("Failed to save window geometry: {}", e);
            }

            // Stop the slint timer
            *main_slint_timer_for_close.lock() = None; // Drop the timer

            // Stop the file watcher gracefully
            let state_guard = app_state_clone_for_close.read();
            state_guard.file_watcher().stop();
            tracing::info!("File watcher stopped on application exit.");
        }
    });

    // ========================================
    // MAIN TAB EVENT CALLBACKS
    // ========================================

    // Folder browsing callbacks
    main_window.on_browse_mods_folder({
        let window_weak = main_window.as_weak();
        let state = app_state.clone();
        move || {
            tracing::debug!("Browse mods folder clicked");
            if let Ok(Some(path)) = handlers::folders::browse_mods_folder()
                && let Some(window) = window_weak.upgrade()
            {
                // Update UI
                window.set_mods_folder_path(path.to_string_lossy().to_string().into());

                // Save to AppState
                let mut state_guard = state.write();
                state_guard.set_mods_folder(path);
                tracing::info!("Mods folder updated in AppState");
            }
        }
    });

    main_window.on_browse_scan_folder({
        let window_weak = main_window.as_weak();
        let state = app_state.clone();
        move || {
            tracing::debug!("Browse scan folder clicked");
            if let Ok(Some(path)) = handlers::folders::browse_scan_folder()
                && let Some(window) = window_weak.upgrade()
            {
                // Update UI
                window.set_scan_folder_path(path.to_string_lossy().to_string().into());

                // Save to AppState
                let mut state_guard = state.write();
                state_guard.set_scan_folder(path);
                tracing::info!("Scan folder updated in AppState");
            }
        }
    });

    // Scan operation callbacks
    main_window.on_scan_crash_logs({
        let window_weak = main_window.as_weak();
        let state = app_state.clone();
        move || {
            tracing::debug!("Scan crash logs clicked");
            let window = window_weak.clone();
            let state_clone = state.clone();
            let state_for_callback = state.clone();

            // Set loading state immediately
            if let Some(w) = window.upgrade() {
                w.set_scan_in_progress(true);
            }

            // Clone state again for the callback closure to avoid move error
            let callback_state = state_for_callback.clone();

            // Use AsyncBridge to run scan with proper Tokio runtime context
            classic_shared_core::AsyncBridge::run_with_ui_update(
                async move { handlers::scan::handle_scan_crash_logs(state_clone.clone()).await },
                move |result| {
                    if let Some(w) = window.upgrade() {
                        w.set_scan_in_progress(false);

                        match result {
                            Ok(scan_result) => {
                                // Auto-refresh results list to show new/updated reports
                                w.invoke_refresh_reports();
                                tracing::debug!(
                                    "Auto-refreshed results list after scan completion"
                                );

                                if scan_result.success {
                                    // Auto-switch to Results tab if setting is enabled
                                    let auto_switch = {
                                        let state_guard = callback_state.read();
                                        state_guard.auto_switch_to_results()
                                    };

                                    if auto_switch {
                                        w.set_current_tab(3); // Tab 3 = Results
                                        tracing::debug!(
                                            "Auto-switched to Results tab after successful scan"
                                        );
                                    }

                                    // Show success dialog
                                    w.set_success_title("Crash Logs Scan Complete".into());
                                    let message = std::format!(
                                        "{}\n\n{}",
                                        scan_result.message,
                                        scan_result.summary_details.join("\n")
                                    );
                                    w.set_success_message(message.into());
                                    w.set_show_success_dialog(true);
                                    tracing::info!("Crash logs scan succeeded");
                                } else {
                                    // Show error dialog (no logs found or partial failure)
                                    w.set_error_title("Crash Logs Scan Issue".into());
                                    let message = std::format!(
                                        "{}\n\n{}",
                                        scan_result.message,
                                        scan_result.summary_details.join("\n")
                                    );
                                    w.set_error_message(message.into());
                                    w.set_show_error_dialog(true);
                                    tracing::warn!("Crash logs scan completed with issues");
                                }
                            }
                            Err(e) => {
                                tracing::error!("Crash logs scan failed: {}", e);

                                // Auto-refresh even on error (partial results may exist)
                                w.invoke_refresh_reports();
                                tracing::debug!("Auto-refreshed results list after scan error");

                                w.set_error_title("Crash Logs Scan Error".into());
                                w.set_error_message(
                                    std::format!("Failed to scan crash logs:\n\n{}", e).into(),
                                );
                                w.set_show_error_dialog(true);
                            }
                        }
                    }
                },
            );
        }
    });

    main_window.on_scan_game_files({
        let window_weak = main_window.as_weak();
        let state = app_state.clone();
        move || {
            tracing::debug!("Scan game files clicked");
            let window = window_weak.clone();
            let state_clone = state.clone();
            let state_for_callback = state.clone();

            // Set loading state immediately
            if let Some(w) = window.upgrade() {
                w.set_scan_in_progress(true);
            }

            // Clone state again for the callback closure to avoid move error
            let callback_state = state_for_callback.clone();

            // Use AsyncBridge to run scan with proper Tokio runtime context
            classic_shared_core::AsyncBridge::run_with_ui_update(
                async move { handlers::scan::handle_scan_game_files(state_clone.clone()).await },
                move |result| {
                    if let Some(w) = window.upgrade() {
                        w.set_scan_in_progress(false);

                        match result {
                            Ok(scan_result) => {
                                // Auto-refresh results list to show new/updated reports
                                w.invoke_refresh_reports();
                                tracing::debug!(
                                    "Auto-refreshed results list after scan completion"
                                );

                                if scan_result.success {
                                    // Auto-switch to Results tab if setting is enabled
                                    let auto_switch = {
                                        let state_guard = callback_state.read();
                                        state_guard.auto_switch_to_results()
                                    };

                                    if auto_switch {
                                        w.set_current_tab(3); // Tab 3 = Results
                                        tracing::debug!(
                                            "Auto-switched to Results tab after successful scan"
                                        );
                                    }

                                    // Show success dialog
                                    w.set_success_title("Game Files Scan Complete".into());
                                    let mut message_parts = vec![scan_result.message.clone()];

                                    if !scan_result.summary_details.is_empty() {
                                        message_parts.push(scan_result.summary_details.join("\n"));
                                    }
                                    if !scan_result.fcx_issues_report.is_empty() {
                                        message_parts.push("\nDetailed FCX issues can be found in the report. Please check the Results tab.".to_string());
                                    }

                                    let message = message_parts.join("\n\n");
                                    w.set_success_message(message.into());
                                    w.set_show_success_dialog(true);
                                    tracing::info!("Game files scan succeeded");
                                } else {
                                    // Show error dialog
                                    w.set_error_title("Game Files Scan Issue".into());
                                    let message = std::format!(
                                        "{}\n\n{}",
                                        scan_result.message,
                                        scan_result.summary_details.join("\n")
                                    );
                                    w.set_error_message(message.into());
                                    w.set_show_error_dialog(true);
                                    tracing::warn!("Game files scan completed with issues");
                                }
                            }
                            Err(e) => {
                                tracing::error!("Game files scan failed: {}", e);

                                // Auto-refresh even on error (partial results may exist)
                                w.invoke_refresh_reports();
                                tracing::debug!("Auto-refreshed results list after scan error");

                                w.set_error_title("Game Files Scan Error".into());
                                w.set_error_message(
                                    std::format!("Failed to scan game files:\n\n{}", e).into(),
                                );
                                w.set_show_error_dialog(true);
                            }
                        }
                    }
                },
            );
        }
    });

    // Settings and utility callbacks
    main_window.on_show_about(|| {
        tracing::debug!("Show about clicked");
        if let Err(e) = handlers::settings::show_about() {
            tracing::error!("Failed to show About dialog: {}", e);
        }
    });

    main_window.on_show_help(|| {
        tracing::debug!("Show help clicked");
        if let Err(e) = handlers::settings::show_help() {
            tracing::error!("Failed to show Help dialog: {}", e);
        }
    });

    main_window.on_open_settings({
        let window_weak = main_window.as_weak();
        let state = app_state.clone();
        move || {
            tracing::debug!("Open settings clicked");

            if let Some(w) = window_weak.upgrade() {
                // Load current settings from AppState
                let settings =
                    handlers::settings_dialog::SettingsData::from_app_state(state.clone());

                // Populate UI with current settings
                w.set_settings_fcx_mode(settings.fcx_mode);
                w.set_settings_show_formid_values(settings.show_formid_values);
                w.set_settings_stat_logging(settings.stat_logging);
                w.set_settings_update_check(settings.update_check);
                w.set_settings_vr_mode(settings.vr_mode);
                w.set_settings_auto_switch_to_results(settings.auto_switch_to_results);
                w.set_settings_auto_refresh_interval_s(settings.auto_refresh_interval_s as i32);
                w.set_settings_move_unsolved_logs(settings.move_unsolved_logs);
                w.set_settings_simplify_logs(settings.simplify_logs);
                w.set_settings_game_root(settings.game_root.into());
                w.set_settings_docs_root(settings.docs_root.into());
                w.set_settings_ini_folder(settings.ini_folder.into());
                w.set_settings_mods_folder(settings.mods_folder.into());
                w.set_settings_scan_custom(settings.scan_custom.into());

                // Show the dialog
                w.set_show_settings_dialog(true);

                tracing::info!("Settings dialog opened with current configuration");
            }
        }
    });

    main_window.on_open_crash_logs_folder({
        let state = app_state.clone();
        move || {
            tracing::debug!("Open crash logs folder clicked");
            if let Err(e) = handlers::settings::open_crash_logs_folder(state.clone()) {
                tracing::error!("Failed to open crash logs folder: {}", e);
            }
        }
    });

    main_window.on_check_updates({
        let window_weak = main_window.as_weak();
        move || {
            tracing::debug!("Check updates clicked");
            let window = window_weak.clone();

            // Set checking state immediately
            if let Some(w) = window.upgrade() {
                w.set_update_checking(true);
            }

            // Get current version
            let current_version = if let Some(w) = window.upgrade() {
                w.get_app_version().to_string()
            } else {
                return;
            };
            let current_version_for_callback = current_version.clone();

            // Use AsyncBridge to run update check with proper Tokio runtime context
            classic_shared_core::AsyncBridge::run_with_ui_update(
                async move { handlers::update_check::check_for_updates(&current_version).await },
                move |result| {
                    if let Some(w) = window.upgrade() {
                        w.set_update_checking(false);

                        match result {
                            Ok(Some(info)) => {
                                // Update available
                                tracing::info!(
                                    "Update available: {} -> {}",
                                    current_version_for_callback,
                                    info.version
                                );

                                w.set_update_available(true);
                                w.set_update_current_version(
                                    current_version_for_callback.clone().into(),
                                );
                                w.set_update_latest_version(info.version.into());
                                w.set_update_release_notes(info.release_notes.into());
                                w.set_update_error_message("".into());
                                w.set_show_update_dialog(true);
                            }
                            Ok(None) => {
                                // No update available
                                tracing::info!(
                                    "No update available (current: {})",
                                    current_version_for_callback
                                );

                                w.set_success_title("No Updates Available".into());
                                w.set_success_message(
                                    std::format!(
                                        "You are using the latest version ({})",
                                        current_version_for_callback
                                    )
                                    .into(),
                                );
                                w.set_show_success_dialog(true);
                            }
                            Err(e) => {
                                // Update check failed
                                tracing::error!("Update check failed: {}", e);

                                w.set_update_available(false);
                                w.set_update_error_message(
                                    std::format!("Failed to check for updates:\n\n{}", e).into(),
                                );

                                // Show error in update dialog for context
                                w.set_show_update_dialog(true);
                            }
                        }
                    }
                },
            );
        }
    });

    // Papyrus monitoring callback
    main_window.on_toggle_papyrus({
        let window_weak = main_window.as_weak();
        let state = app_state.clone();
        move || {
            tracing::debug!("Toggle Papyrus clicked");
            let window = window_weak.clone();
            let state_clone = state.clone();

            // Get current state
            let current_state = if let Some(w) = window.upgrade() {
                w.get_papyrus_monitoring()
            } else {
                return;
            };

            // Use AsyncBridge to run toggle with proper Tokio runtime context
            classic_shared_core::AsyncBridge::run_with_ui_update(
                async move {
                    handlers::papyrus::toggle_papyrus_monitoring(current_state, state_clone).await
                },
                move |result| {
                    if let Some(w) = window.upgrade() {
                        match result {
                            Ok(new_state) => {
                                w.set_papyrus_monitoring(new_state);
                                if new_state {
                                    tracing::info!("Papyrus monitoring started");
                                } else {
                                    tracing::info!("Papyrus monitoring stopped");
                                }
                            }
                            Err(e) => {
                                tracing::error!("Failed to toggle Papyrus monitoring: {}", e);
                                w.set_error_title("Papyrus Monitoring Error".into());
                                w.set_error_message(
                                    std::format!("Failed to toggle Papyrus monitoring:\n\n{}", e)
                                        .into(),
                                );
                                w.set_show_error_dialog(true);
                            }
                        }
                    }
                },
            );
        }
    });

    // ========================================
    // BACKUPS TAB EVENT CALLBACKS
    // ========================================

    // Helper macro to reduce boilerplate for backup operations
    // Uses AsyncBridge to coordinate between Tokio runtime and Slint event loop
    macro_rules! setup_backup_operation {
        ($window:expr, $callback:ident, $category:expr, $operation:expr, $handler:ident, $state:expr) => {
            $window.$callback({
                let window_weak = $window.as_weak();
                let state = $state.clone();
                move || {
                    tracing::info!("{} {} operation", $operation.verb(), $category.display_name());
                    let window = window_weak.clone();
                    let state = state.clone();

                    // Set loading state on UI thread
                    if let Some(w) = window.upgrade() {
                        w.set_operation_in_progress(true);
                    }

                    // Execute async operation via AsyncBridge
                    AsyncBridge::run_with_ui_update(
                        handlers::backup::$handler($category, state),
                        move |result| {
                            // This callback runs on the Slint event loop
                            match result {
                                Ok(result) => {
                                    if let Some(w) = window.upgrade() {
                                        w.set_operation_in_progress(false);

                                        if result.success {
                                            // Show success dialog
                                            w.set_success_title(std::format!("{} {}", $operation.verb(), $category.display_name()).into());
                                            w.set_success_message(result.message.into());
                                            w.set_show_success_dialog(true);

                                            // Update backup status after successful backup
                                            if matches!($operation, handlers::backup::BackupOperation::Backup) {
                                                let window_weak = w.as_weak();
                                                let category = $category;

                                                // Use AsyncBridge for status check
                                                AsyncBridge::run_with_ui_update(
                                                    handlers::backup::check_backup_exists(category),
                                                    move |exists| {
                                                        if let Some(w) = window_weak.upgrade() {
                                                            match category {
                                                                handlers::backup::BackupCategory::Xse => w.set_xse_backup_exists(exists),
                                                                handlers::backup::BackupCategory::Reshade => w.set_reshade_backup_exists(exists),
                                                                handlers::backup::BackupCategory::Vulkan => w.set_vulkan_backup_exists(exists),
                                                                handlers::backup::BackupCategory::Enb => w.set_enb_backup_exists(exists),
                                                            }
                                                        }
                                                    }
                                                );
                                            }
                                        } else {
                                            // Show error dialog
                                            w.set_error_title(std::format!("{} {} Failed", $operation.verb(), $category.display_name()).into());
                                            w.set_error_message(result.message.into());
                                            w.set_show_error_dialog(true);
                                        }
                                    }
                                }
                                Err(e) => {
                                    tracing::error!("{} {} failed: {}", $operation.verb(), $category.display_name(), e);
                                    if let Some(w) = window.upgrade() {
                                        w.set_operation_in_progress(false);
                                        w.set_error_title(std::format!("{} {} Error", $operation.verb(), $category.display_name()).into());
                                        w.set_error_message(std::format!("Failed:\n\n{}", e).into());
                                        w.set_show_error_dialog(true);
                                    }
                                }
                            }
                        }
                    );
                }
            });
        };
    }

    // XSE operations
    setup_backup_operation!(
        main_window,
        on_backup_xse,
        handlers::backup::BackupCategory::Xse,
        handlers::backup::BackupOperation::Backup,
        perform_backup,
        app_state
    );
    setup_backup_operation!(
        main_window,
        on_restore_xse,
        handlers::backup::BackupCategory::Xse,
        handlers::backup::BackupOperation::Restore,
        perform_restore,
        app_state
    );
    setup_backup_operation!(
        main_window,
        on_remove_xse,
        handlers::backup::BackupCategory::Xse,
        handlers::backup::BackupOperation::Remove,
        perform_remove,
        app_state
    );

    // RESHADE operations
    setup_backup_operation!(
        main_window,
        on_backup_reshade,
        handlers::backup::BackupCategory::Reshade,
        handlers::backup::BackupOperation::Backup,
        perform_backup,
        app_state
    );
    setup_backup_operation!(
        main_window,
        on_restore_reshade,
        handlers::backup::BackupCategory::Reshade,
        handlers::backup::BackupOperation::Restore,
        perform_restore,
        app_state
    );
    setup_backup_operation!(
        main_window,
        on_remove_reshade,
        handlers::backup::BackupCategory::Reshade,
        handlers::backup::BackupOperation::Remove,
        perform_remove,
        app_state
    );

    // VULKAN operations
    setup_backup_operation!(
        main_window,
        on_backup_vulkan,
        handlers::backup::BackupCategory::Vulkan,
        handlers::backup::BackupOperation::Backup,
        perform_backup,
        app_state
    );
    setup_backup_operation!(
        main_window,
        on_restore_vulkan,
        handlers::backup::BackupCategory::Vulkan,
        handlers::backup::BackupOperation::Restore,
        perform_restore,
        app_state
    );
    setup_backup_operation!(
        main_window,
        on_remove_vulkan,
        handlers::backup::BackupCategory::Vulkan,
        handlers::backup::BackupOperation::Remove,
        perform_remove,
        app_state
    );

    // ENB operations
    setup_backup_operation!(
        main_window,
        on_backup_enb,
        handlers::backup::BackupCategory::Enb,
        handlers::backup::BackupOperation::Backup,
        perform_backup,
        app_state
    );
    setup_backup_operation!(
        main_window,
        on_restore_enb,
        handlers::backup::BackupCategory::Enb,
        handlers::backup::BackupOperation::Restore,
        perform_restore,
        app_state
    );
    setup_backup_operation!(
        main_window,
        on_remove_enb,
        handlers::backup::BackupCategory::Enb,
        handlers::backup::BackupOperation::Remove,
        perform_remove,
        app_state
    );

    // Open backups folder
    main_window.on_open_backups_folder(|| {
        tracing::info!("Opening backups folder...");
        if let Err(e) = handlers::backup::open_backups_folder() {
            tracing::error!("Failed to open backups folder: {}", e);
        }
    });

    // Check initial backup status asynchronously after window creation
    {
        let window_weak = main_window.as_weak();

        // Use AsyncBridge to run all status checks in parallel
        AsyncBridge::run_with_ui_update(
            async {
                // Check backup status for all categories in parallel
                let xse =
                    handlers::backup::check_backup_exists(handlers::backup::BackupCategory::Xse);
                let reshade = handlers::backup::check_backup_exists(
                    handlers::backup::BackupCategory::Reshade,
                );
                let vulkan =
                    handlers::backup::check_backup_exists(handlers::backup::BackupCategory::Vulkan);
                let enb =
                    handlers::backup::check_backup_exists(handlers::backup::BackupCategory::Enb);

                // Await all checks concurrently
                tokio::join!(xse, reshade, vulkan, enb)
            },
            move |results| {
                // Update UI on Slint event loop
                if let Some(window) = window_weak.upgrade() {
                    window.set_xse_backup_exists(results.0);
                    window.set_reshade_backup_exists(results.1);
                    window.set_vulkan_backup_exists(results.2);
                    window.set_enb_backup_exists(results.3);
                }
            },
        );
    }

    // ========================================
    // ARTICLES TAB EVENT CALLBACKS
    // ========================================

    main_window.on_open_url({
        let main_window_weak = main_window.as_weak();
        move |url| {
            let url_str = url.as_str();
            tracing::debug!("Opening URL: {}", url_str);

            if let Err(e) = handlers::articles::handle_open_url(url_str) {
                tracing::error!("Failed to open URL '{}': {}", url_str, e);
                if let Some(w) = main_window_weak.upgrade() {
                    w.set_error_title("Failed to Open URL".into());
                    w.set_error_message(
                        std::format!("Could not open URL '{}':\n\n{}", url_str, e).into(),
                    );
                    w.set_show_error_dialog(true);
                }
            }
        }
    });

    // ========================================
    // RESULTS TAB EVENT CALLBACKS
    // ========================================

    // Helper function to convert ReportItem to Slint ReportData
    fn report_item_to_slint(item: &models::ReportItem) -> ReportData {
        ReportData {
            filename: item.filename.clone().into(),
            path: item.path.to_string_lossy().to_string().into(),
            display_date: item.display_date.clone().into(),
            file_size: item.file_size.clone().into(),
        }
    }

    // Refresh reports callback
    main_window.on_refresh_reports({
        let window_weak = main_window.as_weak();
        let state = app_state.clone();
        move || {
            tracing::info!("Refreshing reports list...");
            let window = window_weak.clone();
            let state_clone = state.clone();

            // Use AsyncBridge to run scan off UI thread
            classic_shared_core::AsyncBridge::run_with_ui_update(
                async move {
                    // Wrap synchronous operation in async block
                    handlers::results::scan_reports(state_clone)
                },
                move |result| {
                    if let Some(w) = window.upgrade() {
                        match result {
                            Ok(reports) => {
                                // Convert to Slint ReportData structs
                                let slint_reports: Vec<ReportData> =
                                    reports.iter().map(report_item_to_slint).collect();

                                // Update UI
                                let model = std::rc::Rc::new(slint::VecModel::from(slint_reports));
                                w.set_reports_list(model.into());

                                // Auto-select first report if available
                                if !reports.is_empty() {
                                    w.set_selected_report_index(0);
                                    w.set_selected_report_path(
                                        reports[0].path.to_string_lossy().to_string().into(),
                                    );
                                } else {
                                    w.set_selected_report_index(-1);
                                    w.set_selected_report_path("".into());
                                }

                                tracing::info!("Reports list updated: {} report(s)", reports.len());
                            }
                            Err(e) => {
                                tracing::error!("Failed to scan reports: {}", e);
                                w.set_error_title("Report Scan Error".into());
                                w.set_error_message(
                                    std::format!("Failed to scan reports:\n\n{}", e).into(),
                                );
                                w.set_show_error_dialog(true);
                            }
                        }
                    }
                },
            );
        }
    });

    // Delete report callback
    main_window.on_delete_report({
        let window_weak = main_window.as_weak();
        let _state = app_state.clone();
        move || {
            let window = window_weak.clone();
            let _state = _state.clone();

            // Get currently selected report path
            if let Some(w) = window.upgrade() {
                let selected_path = w.get_selected_report_path();
                if selected_path.is_empty() {
                    tracing::warn!("No report selected for deletion");
                    return;
                }

                let report_path = std::path::PathBuf::from(selected_path.as_str());
                let filename = report_path
                    .file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or("Unknown");

                tracing::info!("Deleting report: {}", filename);

                // Perform deletion
                match handlers::results::delete_report(&report_path) {
                    Ok(()) => {
                        // Clear selected report
                        w.set_selected_report_index(-1);
                        w.set_selected_report_path("".into());

                        // Refresh the list
                        w.invoke_refresh_reports();

                        // Show success message
                        w.set_success_title("Report Deleted".into());
                        w.set_success_message(
                            std::format!("Successfully deleted: {}", filename).into(),
                        );
                        w.set_show_success_dialog(true);
                    }
                    Err(e) => {
                        tracing::error!("Failed to delete report: {}", e);
                        w.set_error_title("Delete Failed".into());
                        w.set_error_message(
                            std::format!("Failed to delete report:\n\n{}", e).into(),
                        );
                        w.set_show_error_dialog(true);
                    }
                }
            }
        }
    });

    // Open reports folder callback
    main_window.on_open_reports_folder({
        let window_weak = main_window.as_weak();
        let state = app_state.clone();
        move || {
            tracing::info!("Opening reports folder...");

            if let Err(e) = handlers::results::open_reports_folder(state.clone()) {
                tracing::error!("Failed to open reports folder: {}", e);
                if let Some(w) = window_weak.upgrade() {
                    w.set_error_title("Open Folder Failed".into());
                    w.set_error_message(std::format!("Failed to open folder:\n\n{}", e).into());
                    w.set_show_error_dialog(true);
                }
            }
        }
    });

    // Report selected callback - Load and display markdown content
    main_window.on_report_selected({
        let window_weak = main_window.as_weak();
        move |path| {
            let path_str = path.to_string();
            tracing::debug!("Report selected: {}", path_str);

            let window = window_weak.clone();
            let report_path = std::path::PathBuf::from(path_str.clone());

            // Use AsyncBridge to load markdown off UI thread
            classic_shared_core::AsyncBridge::run_with_ui_update(
                async move {
                    // Wrap synchronous operation in async block
                    handlers::markdown::load_markdown(&report_path)
                },
                move |result| {
                    if let Some(w) = window.upgrade() {
                        match result {
                            Ok(markdown_content) => {
                                // Update markdown content
                                w.set_markdown_content(markdown_content.text.into());

                                // Update metadata
                                let metadata = MarkdownMetadata {
                                    filename: markdown_content.filename.into(),
                                    file_size: markdown_content.file_size.into(),
                                    display_date: markdown_content.display_date.into(),
                                };
                                w.set_markdown_metadata(metadata);

                                // Reset zoom level
                                w.set_zoom_level(100);

                                tracing::info!("Loaded markdown report: {}", path_str);
                            }
                            Err(e) => {
                                tracing::error!("Failed to load markdown: {}", e);
                                w.set_error_title("Failed to Load Report".into());
                                w.set_error_message(
                                    std::format!("Could not load markdown file:\n\n{}", e).into(),
                                );
                                w.set_show_error_dialog(true);
                            }
                        }
                    }
                },
            );
        }
    });

    // Zoom controls for markdown viewer
    main_window.on_zoom_in({
        let window_weak = main_window.as_weak();
        move || {
            if let Some(w) = window_weak.upgrade() {
                let current_zoom = w.get_zoom_level();
                let new_zoom = (current_zoom + 25).min(150); // Max 150%
                w.set_zoom_level(new_zoom);
                tracing::debug!("Zoom in: {}%", new_zoom);
            }
        }
    });

    main_window.on_zoom_out({
        let window_weak = main_window.as_weak();
        move || {
            if let Some(w) = window_weak.upgrade() {
                let current_zoom = w.get_zoom_level();
                let new_zoom = (current_zoom - 25).max(50); // Min 50%
                w.set_zoom_level(new_zoom);
                tracing::debug!("Zoom out: {}%", new_zoom);
            }
        }
    });

    main_window.on_zoom_reset({
        let window_weak = main_window.as_weak();
        move || {
            if let Some(w) = window_weak.upgrade() {
                w.set_zoom_level(100);
                tracing::debug!("Zoom reset: 100%");
            }
        }
    });

    // Copy to clipboard functionality
    main_window.on_copy_to_clipboard({
        let window_weak = main_window.as_weak();
        move || {
            if let Some(w) = window_weak.upgrade() {
                let content = w.get_markdown_content();
                let content_str = content.as_str();

                if content_str.is_empty() {
                    tracing::warn!("No content to copy to clipboard");
                    return;
                }

                tracing::debug!("Copying {} characters to clipboard", content_str.len());

                match handlers::clipboard::copy_to_clipboard(content_str) {
                    Ok(()) => {
                        tracing::info!("Successfully copied report to clipboard");

                        // Show success feedback
                        w.set_success_title("Copied to Clipboard".into());
                        w.set_success_message(
                            std::format!(
                                "Report copied to clipboard ({} characters)",
                                content_str.len()
                            )
                            .into(),
                        );
                        w.set_show_success_dialog(true);
                    }
                    Err(e) => {
                        tracing::error!("Failed to copy to clipboard: {}", e);

                        // Show error feedback
                        w.set_error_title("Copy Failed".into());
                        w.set_error_message(
                            std::format!("Failed to copy to clipboard:\n\n{}", e).into(),
                        );
                        w.set_show_error_dialog(true);
                    }
                }
            }
        }
    });

    // Initial reports scan
    {
        tracing::info!("Performing initial reports scan...");
        main_window.invoke_refresh_reports();
    }

    // TODO: File watcher auto-refresh
    // Auto-refresh is currently disabled due to thread-safety complexity with Slint UI updates.
    // The manual refresh button works perfectly. A better implementation using Slint Timer
    // or a different async pattern can be added in a future update.
    // For now, users can manually refresh the list using the Refresh button.
    tracing::info!("File watcher auto-refresh: disabled (use manual refresh button)");

    // Exit callback
    main_window.on_exit_app(|| {
        tracing::info!("Exit clicked");
        std::process::exit(0);
    });

    // Copy error to clipboard
    main_window.on_copy_error_to_clipboard({
        let window_weak = main_window.as_weak();
        move || {
            if let Some(w) = window_weak.upgrade() {
                let title = w.get_error_title().to_string();
                let message = w.get_error_message().to_string();
                let details = w.get_error_details().to_string();

                // Format: Title\n\nMessage\n\nDetails:\n\nTraceback
                let formatted = if !details.is_empty() {
                    std::format!("{}\n\n{}\n\nDetails:\n\n{}", title, message, details)
                } else {
                    std::format!("{}\n\n{}", title, message)
                };

                // Copy to clipboard
                match arboard::Clipboard::new() {
                    Ok(mut clipboard) => {
                        if let Err(e) = clipboard.set_text(&formatted) {
                            tracing::error!("Failed to copy to clipboard: {}", e);
                        } else {
                            tracing::debug!("Error details copied to clipboard");
                        }
                    }
                    Err(e) => {
                        tracing::error!("Failed to access clipboard: {}", e);
                    }
                }
            }
        }
    });

    // ========================================
    // DIALOG CALLBACKS
    // ========================================

    // Settings dialog callbacks
    main_window.on_settings_save({
        let window_weak = main_window.as_weak();
        let state = app_state.clone();
        move || {
            tracing::info!("Saving settings...");
            let window = window_weak.clone();
            let state_clone = state.clone();

            // Gather settings from UI
            let settings = if let Some(w) = window.upgrade() {
                handlers::settings_dialog::SettingsData {
                    fcx_mode: w.get_settings_fcx_mode(),
                    show_formid_values: w.get_settings_show_formid_values(),
                    stat_logging: w.get_settings_stat_logging(),
                    update_check: w.get_settings_update_check(),
                    vr_mode: w.get_settings_vr_mode(),
                    auto_switch_to_results: w.get_settings_auto_switch_to_results(),
                    auto_refresh_interval_s: w.get_settings_auto_refresh_interval_s() as u64,
                    move_unsolved_logs: w.get_settings_move_unsolved_logs(),
                    simplify_logs: w.get_settings_simplify_logs(),
                    update_source: "".to_string(), // Initialize the new field
                    game_root: w.get_settings_game_root().to_string(),
                    docs_root: w.get_settings_docs_root().to_string(),
                    ini_folder: w.get_settings_ini_folder().to_string(),
                    mods_folder: w.get_settings_mods_folder().to_string(),
                    scan_custom: w.get_settings_scan_custom().to_string(),
                }
            } else {
                return;
            };

            // Use AsyncBridge to save settings with proper Tokio runtime context
            classic_shared_core::AsyncBridge::run_with_ui_update(
                async move {
                    // Validate settings
                    match settings.validate() {
                        Ok(()) => {
                            // Save to AppState and YAML
                            settings.save_to_app_state(state_clone).await
                        }
                        Err(e) => Err(e),
                    }
                },
                move |result| {
                    if let Some(w) = window.upgrade() {
                        match result {
                            Ok(()) => {
                                tracing::info!("Settings saved successfully");
                                w.set_show_settings_dialog(false);

                                // Show success message
                                w.set_success_title("Settings Saved".into());
                                w.set_success_message(
                                    "Your settings have been saved successfully.".into(),
                                );
                                w.set_show_success_dialog(true);
                            }
                            Err(e) => {
                                tracing::error!("Failed to save/validate settings: {}", e);
                                w.set_error_title("Settings Error".into());
                                w.set_error_message(
                                    std::format!("Failed to save settings:\n\n{}", e).into(),
                                );
                                w.set_show_error_dialog(true);
                            }
                        }
                    }
                },
            );
        }
    });

    main_window.on_settings_cancel({
        let window_weak = main_window.as_weak();
        move || {
            tracing::debug!("Settings cancelled");
            if let Some(w) = window_weak.upgrade() {
                w.set_show_settings_dialog(false);
            }
        }
    });

    main_window.on_settings_browse_path({
        let window_weak = main_window.as_weak();
        move |path_type| {
            let path_type_str = path_type.to_string();
            tracing::debug!("Browse settings path: {}", path_type_str);

            if let Some(w) = window_weak.upgrade() {
                // Get current path from UI based on path type
                let current_path = match path_type_str.as_str() {
                    "game-root" => w.get_settings_game_root(),
                    "docs-root" => w.get_settings_docs_root(),
                    "ini-folder" => w.get_settings_ini_folder(),
                    "mods-folder" => w.get_settings_mods_folder(),
                    "scan-custom" => w.get_settings_scan_custom(),
                    _ => slint::SharedString::from(""),
                };

                // Call file picker
                match handlers::settings_dialog::browse_settings_path(
                    &path_type_str,
                    current_path.as_str(),
                ) {
                    Ok(Some(path)) => {
                        let path_str = path.to_string_lossy().to_string();
                        tracing::info!("Path selected for {}: {}", path_type_str, path_str);

                        // Update UI with selected path
                        match path_type_str.as_str() {
                            "game-root" => w.set_settings_game_root(path_str.into()),
                            "docs-root" => w.set_settings_docs_root(path_str.into()),
                            "ini-folder" => w.set_settings_ini_folder(path_str.into()),
                            "mods-folder" => w.set_settings_mods_folder(path_str.into()),
                            "scan-custom" => w.set_settings_scan_custom(path_str.into()),
                            _ => {}
                        }
                    }
                    Ok(None) => {
                        tracing::debug!("Path selection cancelled for {}", path_type_str);
                    }
                    Err(e) => {
                        tracing::error!("Failed to browse for {}: {}", path_type_str, e);
                        w.set_error_title("Path Selection Error".into());
                        w.set_error_message(
                            std::format!("Failed to open file picker:\n\n{}", e).into(),
                        );
                        w.set_show_error_dialog(true);
                    }
                }
            }
        }
    });

    // About dialog callbacks
    main_window.on_about_close({
        let window_weak = main_window.as_weak();
        move || {
            tracing::debug!("About dialog closed");
            if let Some(w) = window_weak.upgrade() {
                w.set_show_about_dialog(false);
            }
        }
    });

    main_window.on_about_open_github(|| {
        tracing::info!("Opening GitHub page...");
        if let Err(e) = handlers::articles::handle_open_url(
            "https://github.com/evildarkarchon/CLASSIC-Fallout4",
        ) {
            tracing::error!("Failed to open GitHub: {}", e);
        }
    });

    main_window.on_about_open_nexus(|| {
        tracing::info!("Opening Nexus Mods page...");
        if let Err(e) =
            handlers::articles::handle_open_url("https://www.nexusmods.com/fallout4/mods/56255")
        {
            tracing::error!("Failed to open Nexus Mods: {}", e);
        }
    });

    // Update dialog callbacks
    main_window.on_update_close({
        let window_weak = main_window.as_weak();
        move || {
            tracing::debug!("Update dialog closed");
            if let Some(w) = window_weak.upgrade() {
                w.set_show_update_dialog(false);
            }
        }
    });

    main_window.on_update_download({
        let window_weak = main_window.as_weak();
        move || {
            tracing::info!("Opening download page...");
            // Get the latest version URL (GitHub releases)
            if let Err(e) = handlers::articles::handle_open_url(
                "https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/latest",
            ) {
                tracing::error!("Failed to open download page: {}", e);
            }

            // Close dialog
            if let Some(w) = window_weak.upgrade() {
                w.set_show_update_dialog(false);
            }
        }
    });

    main_window.on_update_skip({
        let window_weak = main_window.as_weak();
        move || {
            tracing::debug!("Update skipped");
            let window = window_weak.clone();

            // Get settings from UI
            let (latest_version, dont_check_again) = if let Some(w) = window.upgrade() {
                (
                    w.get_update_latest_version().to_string(),
                    w.get_update_dont_check_again(),
                )
            } else {
                return;
            };

            // Use AsyncBridge to save preferences with proper Tokio runtime context
            classic_shared_core::AsyncBridge::run_with_ui_update(
                async move {
                    // Load current preferences
                    let mut prefs = handlers::update_check::UpdatePreferences::load().await?;

                    // Save skipped version
                    prefs.skip_version(latest_version.clone());

                    // Save "don't check again" if checkbox was checked
                    if dont_check_again {
                        prefs.set_dont_check_again(true);
                        tracing::info!("User opted to disable update checking");
                    } else {
                        tracing::info!("User skipped version: {}", latest_version);
                    }

                    // Persist preferences
                    prefs.save().await?;
                    Ok(())
                },
                move |result: anyhow::Result<()>| {
                    if let Some(w) = window.upgrade() {
                        if let Err(e) = result {
                            tracing::error!("Failed to save update preferences: {}", e);
                        }
                        // Close dialog regardless of result
                        w.set_show_update_dialog(false);
                    }
                },
            );
        }
    });

    // Papyrus dialog callbacks
    main_window.on_papyrus_close({
        let window_weak = main_window.as_weak();
        move || {
            tracing::debug!("Papyrus dialog closed");
            if let Some(w) = window_weak.upgrade() {
                w.set_show_papyrus_dialog(false);
            }
        }
    });

    main_window.on_papyrus_start_monitoring({
        let window_weak = main_window.as_weak();
        let state = app_state.clone();
        move || {
            tracing::info!("Starting Papyrus monitoring...");
            let window = window_weak.clone();
            let state_clone = state.clone();

            // Use AsyncBridge to start monitoring with proper Tokio runtime context
            classic_shared_core::AsyncBridge::run_with_ui_update(
                async move { handlers::papyrus::start_monitoring(state_clone).await },
                move |result| {
                    if let Some(w) = window.upgrade() {
                        match result {
                            Ok(()) => {
                                w.set_papyrus_monitoring(true);
                                tracing::info!("Papyrus monitoring started successfully");
                            }
                            Err(e) => {
                                tracing::error!("Failed to start Papyrus monitoring: {}", e);
                                w.set_error_title("Monitoring Error".into());
                                w.set_error_message(
                                    std::format!("Failed to start monitoring:\n\n{}", e).into(),
                                );
                                w.set_show_error_dialog(true);
                            }
                        }
                    }
                },
            );
        }
    });

    main_window.on_papyrus_stop_monitoring({
        let window_weak = main_window.as_weak();
        move || {
            tracing::info!("Stopping Papyrus monitoring...");
            let window = window_weak.clone();

            // Use AsyncBridge to stop monitoring with proper Tokio runtime context
            classic_shared_core::AsyncBridge::run_with_ui_update(
                async move { handlers::papyrus::stop_monitoring().await },
                move |result| {
                    if let Some(w) = window.upgrade() {
                        match result {
                            Ok(()) => {
                                w.set_papyrus_monitoring(false);
                                tracing::info!("Papyrus monitoring stopped successfully");
                            }
                            Err(e) => {
                                tracing::error!("Failed to stop Papyrus monitoring: {}", e);
                            }
                        }
                    }
                },
            );
        }
    });

    main_window.on_papyrus_clear_stats({
        let window_weak = main_window.as_weak();
        move || {
            tracing::debug!("Clearing Papyrus stats...");
            handlers::papyrus::clear_stats();

            // Reset UI counters
            if let Some(w) = window_weak.upgrade() {
                w.set_papyrus_error_count(0);
                w.set_papyrus_warning_count(0);
                w.set_papyrus_info_count(0);
                w.set_papyrus_dumps_count(0);
                w.set_papyrus_stacks_count(0);
                w.set_papyrus_log_content("".into());
                tracing::info!("Papyrus stats cleared");
            }
        }
    });

    main_window.on_papyrus_update_stats({
        let window_weak = main_window.as_weak();
        move || {
            // Get current stats from Rust
            let stats = handlers::papyrus::get_current_stats();

            // Update UI (convert usize to i32 for Slint)
            if let Some(w) = window_weak.upgrade() {
                w.set_papyrus_error_count(stats.errors as i32);
                w.set_papyrus_warning_count(stats.warnings as i32);
                w.set_papyrus_info_count(0); // Core analyzer doesn't track info-level messages
                w.set_papyrus_dumps_count(stats.dumps as i32);
                w.set_papyrus_stacks_count(stats.stacks as i32);

                // Note: Core analyzer doesn't expose recent_entries for log display
                // Log content would need to be read separately if needed
                tracing::debug!(
                    "Updated Papyrus stats: E={} W={} D={} S={}",
                    stats.errors,
                    stats.warnings,
                    stats.dumps,
                    stats.stacks
                );
            }
        }
    });

    // Confirmation dialog callbacks
    main_window.on_confirmation_confirmed({
        let window_weak = main_window.as_weak();
        let pending = pending_confirmation.clone();
        move || {
            let action = *pending.lock();
            tracing::debug!("Confirmation: User confirmed action: {:?}", action);

            if let Some(w) = window_weak.upgrade() {
                w.set_show_confirmation_dialog(false);

                // Execute the pending action
                match action {
                    PendingConfirmation::None => {
                        tracing::debug!("No action to execute");
                    } // Future actions can be handled here:
                      // PendingConfirmation::DeleteAllReports => { ... }
                      // PendingConfirmation::ClearPapyrusLogs => { ... }
                }

                // Clear the pending action
                *pending.lock() = PendingConfirmation::None;
            }
        }
    });

    main_window.on_confirmation_cancelled({
        let window_weak = main_window.as_weak();
        let pending = pending_confirmation.clone();
        move || {
            let action = *pending.lock();
            tracing::debug!("Confirmation: User cancelled action: {:?}", action);

            if let Some(w) = window_weak.upgrade() {
                w.set_show_confirmation_dialog(false);

                // Clear the pending action
                *pending.lock() = PendingConfirmation::None;
            }
        }
    });

    // Help dialog callbacks
    main_window.on_help_close({
        let window_weak = main_window.as_weak();
        move || {
            tracing::debug!("Help: User closed help dialog");
            if let Some(w) = window_weak.upgrade() {
                w.set_show_help_dialog(false);
            }
        }
    });

    main_window.on_help_show_topic({
        let window_weak = main_window.as_weak();
        move |category, topic| {
            tracing::debug!("Help: Loading topic {}/{}", category, topic);
            let window = window_weak.clone();
            let category_str = category.to_string();
            let topic_str = topic.to_string();
            let category_for_error = category_str.clone();
            let topic_for_error = topic_str.clone();

            // Use AsyncBridge to load help topic with proper Tokio runtime context
            classic_shared_core::AsyncBridge::run_with_ui_update(
                async move { handlers::help::get_help_topic(&category_str, &topic_str).await },
                move |result| {
                    if let Some(w) = window.upgrade() {
                        match result {
                            Ok(help_topic) => {
                                // Log before moving values
                                tracing::info!("Help topic loaded: {}", help_topic.title);
                                tracing::debug!(
                                    "Help topic has {} related topics",
                                    help_topic.related.len()
                                );

                                // Set help dialog properties
                                w.set_help_title(help_topic.title.into());
                                w.set_help_content(help_topic.content.into());

                                // Convert related topics to Slint format
                                let related_topics: Vec<RelatedTopicData> = help_topic
                                    .related
                                    .into_iter()
                                    .map(|rt| RelatedTopicData {
                                        category: rt.category.into(),
                                        topic: rt.topic.into(),
                                        display: rt.display.into(),
                                    })
                                    .collect();

                                w.set_help_related_topics(slint::ModelRc::new(
                                    slint::VecModel::from(related_topics),
                                ));

                                // Show the dialog
                                w.set_show_help_dialog(true);
                            }
                            Err(e) => {
                                tracing::error!(
                                    "Failed to load help topic {}/{}: {}",
                                    category_for_error,
                                    topic_for_error,
                                    e
                                );
                                // Show error in dialog
                                w.set_error_title("Help Error".into());
                                w.set_error_message(
                                    format!("Failed to load help topic:\n\n{}", e).into(),
                                );
                                w.set_show_error_dialog(true);
                            }
                        }
                    }
                },
            );
        }
    });

    main_window.on_show_context_help({
        let window_weak = main_window.as_weak();
        move || {
            tracing::debug!("F1 pressed - showing context-sensitive help");
            let window = window_weak.clone();

            // Get current tab to determine context
            let (category, topic) = if let Some(w) = window.upgrade() {
                let current_tab = w.get_current_tab();
                match current_tab {
                    0 => ("main", "scan_crash_logs"),    // Main tab
                    1 => ("backups", "backup_overview"), // Backups tab
                    3 => ("results", "view_report"),     // Results tab
                    _ => ("main", "scan_crash_logs"),    // Default to main
                }
            } else {
                return;
            };

            // Use AsyncBridge to load help topic with proper Tokio runtime context
            classic_shared_core::AsyncBridge::run_with_ui_update(
                async move { handlers::help::get_help_topic(category, topic).await },
                move |result| {
                    if let Some(w) = window.upgrade() {
                        match result {
                            Ok(help_topic) => {
                                tracing::info!("F1 Help: Loaded {}/{}", category, topic);

                                // Set help dialog properties
                                w.set_help_title(help_topic.title.into());
                                w.set_help_content(help_topic.content.into());

                                // Convert related topics to Slint format
                                let related_topics: Vec<RelatedTopicData> = help_topic
                                    .related
                                    .into_iter()
                                    .map(|rt| RelatedTopicData {
                                        category: rt.category.into(),
                                        topic: rt.topic.into(),
                                        display: rt.display.into(),
                                    })
                                    .collect();

                                w.set_help_related_topics(slint::ModelRc::new(
                                    slint::VecModel::from(related_topics),
                                ));

                                // Show the dialog
                                w.set_show_help_dialog(true);
                            }
                            Err(e) => {
                                tracing::error!("Failed to load context help: {}", e);
                                // Silently fail - don't show error for F1
                            }
                        }
                    }
                },
            );
        }
    });

    // Pastebin dialog callbacks
    main_window.on_pastebin_cancel({
        let window_weak = main_window.as_weak();
        move || {
            tracing::debug!("Pastebin: User cancelled");
            if let Some(w) = window_weak.upgrade() {
                w.set_show_pastebin_dialog(false);
                w.set_pastebin_url_input("".into()); // Clear input
            }
        }
    });

    main_window.on_pastebin_open({
        let window_weak = main_window.as_weak();
        move || {
            tracing::debug!("Pastebin: User clicked Open");
            let window = window_weak.clone();

            // Get URL from input
            let url = if let Some(w) = window.upgrade() {
                w.get_pastebin_url_input().to_string()
            } else {
                return;
            };

            if url.is_empty() {
                tracing::warn!("Pastebin URL is empty");
                return;
            }

            // Set loading state immediately
            if let Some(w) = window.upgrade() {
                w.set_pastebin_loading(true);
            }

            // Use AsyncBridge to download from Pastebin with proper Tokio runtime context
            classic_shared_core::AsyncBridge::run_with_ui_update(
                async move {
                    // Download from Pastebin
                    let content = handlers::pastebin::download_from_pastebin(&url).await?;
                    tracing::info!("Successfully downloaded {} bytes from Pastebin", content.len());

                    // Save to Crash Logs folder for scanning
                    let crashlogs_dir = std::path::PathBuf::from("Crash Logs");
                    if !crashlogs_dir.exists() {
                        std::fs::create_dir_all(&crashlogs_dir)?;
                    }

                    // Generate filename with timestamp
                    let timestamp = chrono::Local::now().format("%Y%m%d_%H%M%S");
                    let filename = std::format!("crash-{}.log", timestamp);
                    let file_path = crashlogs_dir.join(&filename);

                    // Write content to crash log file
                    tokio::fs::write(&file_path, &content).await?;
                    tracing::info!("Saved Pastebin crash log to: {}", file_path.display());

                    Ok((filename, content.len()))
                },
                move |result: anyhow::Result<(String, usize)>| {
                    if let Some(w) = window.upgrade() {
                        w.set_pastebin_loading(false);

                        match result {
                            Ok((filename, size)) => {
                                // Close Pastebin dialog
                                w.set_show_pastebin_dialog(false);
                                w.set_pastebin_url_input("".into());

                                // Show success message and offer to scan
                                w.set_success_title("Crash Log Downloaded".into());
                                w.set_success_message(
                                    std::format!(
                                        "Successfully downloaded crash log from Pastebin.\n\nFile: {}\nSize: {} bytes\n\nThe crash log has been saved to the Crash Logs folder.\nYou can now scan it using the 'Scan Crash Logs' button.",
                                        filename,
                                        size
                                    ).into()
                                );
                                w.set_show_success_dialog(true);

                                tracing::info!("Pastebin crash log ready for scanning");
                            }
                            Err(e) => {
                                tracing::error!("Failed to download/save from Pastebin: {}", e);

                                // Show error dialog
                                w.set_error_title("Pastebin Error".into());
                                w.set_error_message(
                                    std::format!("Failed to download crash log from Pastebin:\n\n{}", e).into()
                                );
                                w.set_show_error_dialog(true);
                            }
                        }
                    }
                },
            );
        }
    });

    // Run the application
    tracing::info!("Starting CLASSIC GUI v{}", VERSION);
    main_window.run()
}
