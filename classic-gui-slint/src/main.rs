// CLASSIC Slint GUI - Main Entry Point
// Pure Rust GUI using Slint framework with Fluent Design System

slint::include_modules!();

mod app_state;
mod geometry;
mod handlers;
mod models;

use anyhow::Result;
use app_state::{AppState, SharedAppState};
use classic_shared::AsyncBridge;
use geometry::WindowGeometry;
use slint::{PhysicalPosition, PhysicalSize};
use std::sync::Arc;
use tracing_subscriber;

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

    // Load saved window geometry
    let geometry = WindowGeometry::load();
    tracing::debug!("Loaded window geometry: {:?}", geometry);

    // Create the main window
    let main_window = MainWindow::new()?;

    // Set version dynamically from CARGO_PKG_VERSION
    main_window.set_app_version(VERSION.into());

    // Apply saved geometry
    let window = main_window.window();
    window.set_size(PhysicalSize::new(geometry.width as u32, geometry.height as u32));

    // Set position if not default (-1 means center)
    if geometry.x >= 0 && geometry.y >= 0 {
        window.set_position(PhysicalPosition::new(geometry.x, geometry.y));
    }

    // Load application configuration asynchronously using AsyncBridge
    {
        let window_weak = main_window.as_weak();
        let state = app_state.clone();

        tracing::info!("Loading application configuration...");

        AsyncBridge::run_with_ui_update(
            AppState::load(),
            move |result| {
                match result {
                    Ok(loaded_state) => {
                        // Replace the default state with loaded state
                        *state.write() = loaded_state.read().clone();

                        let state_guard = state.read();
                        tracing::info!(
                            "Configuration loaded successfully - Game: {}, Root: {}",
                            state_guard.game_name(),
                            state_guard.game_root().display()
                        );

                        // Update UI with loaded paths
                        if let Some(w) = window_weak.upgrade() {
                            if let Some(mods_folder) = state_guard.mods_folder() {
                                w.set_mods_folder_path(mods_folder.to_string_lossy().to_string().into());
                                tracing::debug!("Loaded mods folder from config: {}", mods_folder.display());
                            }
                            if let Some(scan_folder) = state_guard.scan_folder() {
                                w.set_scan_folder_path(scan_folder.to_string_lossy().to_string().into());
                                tracing::debug!("Loaded scan folder from config: {}", scan_folder.display());
                            }
                        }
                    }
                    Err(e) => {
                        tracing::error!("Failed to load configuration: {}", e);
                        tracing::warn!("Using default configuration (some features may not work)");
                    }
                }
            }
        );
    }

    // Setup window lifecycle callbacks
    let window_weak = main_window.as_weak();
    main_window.on_window_closed(move || {
        tracing::info!("Window closed by user");

        // Save window geometry before closing
        if let Some(main_window) = window_weak.upgrade() {
            let window = main_window.window();
            let size = window.size();
            let position = window.position();

            let geometry = WindowGeometry {
                width: size.width as i32,
                height: size.height as i32,
                x: position.x,
                y: position.y,
            };

            if let Err(e) = geometry.save() {
                tracing::error!("Failed to save window geometry: {}", e);
            }
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
            if let Ok(Some(path)) = handlers::folders::browse_mods_folder() {
                if let Some(window) = window_weak.upgrade() {
                    // Update UI
                    window.set_mods_folder_path(path.to_string_lossy().to_string().into());

                    // Save to AppState
                    let mut state_guard = state.write();
                    state_guard.set_mods_folder(path);
                    tracing::info!("Mods folder updated in AppState");
                }
            }
        }
    });

    main_window.on_browse_scan_folder({
        let window_weak = main_window.as_weak();
        let state = app_state.clone();
        move || {
            tracing::debug!("Browse scan folder clicked");
            if let Ok(Some(path)) = handlers::folders::browse_scan_folder() {
                if let Some(window) = window_weak.upgrade() {
                    // Update UI
                    window.set_scan_folder_path(path.to_string_lossy().to_string().into());

                    // Save to AppState
                    let mut state_guard = state.write();
                    state_guard.set_scan_folder(path);
                    tracing::info!("Scan folder updated in AppState");
                }
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
            let state = state.clone();

            // Spawn async task for scanning
            slint::spawn_local(async move {
                if let Some(w) = window.upgrade() {
                    w.set_scan_in_progress(true);
                }

                match handlers::scan::handle_scan_crash_logs(state).await {
                    Ok(scan_result) => {
                        if let Some(w) = window.upgrade() {
                            w.set_scan_in_progress(false);

                            if scan_result.success {
                                // Show success dialog
                                w.set_success_title("Crash Logs Scan Complete".into());
                                let message = format!(
                                    "{}\n\n{}",
                                    scan_result.message,
                                    scan_result.details.join("\n")
                                );
                                w.set_success_message(message.into());
                                w.set_show_success_dialog(true);
                                tracing::info!("Crash logs scan succeeded");
                            } else {
                                // Show error dialog (no logs found or partial failure)
                                w.set_error_title("Crash Logs Scan Issue".into());
                                let message = format!(
                                    "{}\n\n{}",
                                    scan_result.message,
                                    scan_result.details.join("\n")
                                );
                                w.set_error_message(message.into());
                                w.set_show_error_dialog(true);
                                tracing::warn!("Crash logs scan completed with issues");
                            }
                        }
                    }
                    Err(e) => {
                        tracing::error!("Crash logs scan failed: {}", e);
                        if let Some(w) = window.upgrade() {
                            w.set_scan_in_progress(false);
                            w.set_error_title("Crash Logs Scan Error".into());
                            w.set_error_message(format!("Failed to scan crash logs:\n\n{}", e).into());
                            w.set_show_error_dialog(true);
                        }
                    }
                }
            }).unwrap();
        }
    });

    main_window.on_scan_game_files({
        let window_weak = main_window.as_weak();
        let state = app_state.clone();
        move || {
            tracing::debug!("Scan game files clicked");
            let window = window_weak.clone();
            let state = state.clone();

            // Spawn async task for scanning
            slint::spawn_local(async move {
                if let Some(w) = window.upgrade() {
                    w.set_scan_in_progress(true);
                }

                match handlers::scan::handle_scan_game_files(state).await {
                    Ok(scan_result) => {
                        if let Some(w) = window.upgrade() {
                            w.set_scan_in_progress(false);

                            if scan_result.success {
                                // Show success dialog
                                w.set_success_title("Game Files Scan Complete".into());
                                let message = format!(
                                    "{}\n\n{}",
                                    scan_result.message,
                                    scan_result.details.join("\n")
                                );
                                w.set_success_message(message.into());
                                w.set_show_success_dialog(true);
                                tracing::info!("Game files scan succeeded");
                            } else {
                                // Show error dialog
                                w.set_error_title("Game Files Scan Issue".into());
                                let message = format!(
                                    "{}\n\n{}",
                                    scan_result.message,
                                    scan_result.details.join("\n")
                                );
                                w.set_error_message(message.into());
                                w.set_show_error_dialog(true);
                                tracing::warn!("Game files scan completed with issues");
                            }
                        }
                    }
                    Err(e) => {
                        tracing::error!("Game files scan failed: {}", e);
                        if let Some(w) = window.upgrade() {
                            w.set_scan_in_progress(false);
                            w.set_error_title("Game Files Scan Error".into());
                            w.set_error_message(format!("Failed to scan game files:\n\n{}", e).into());
                            w.set_show_error_dialog(true);
                        }
                    }
                }
            }).unwrap();
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

    main_window.on_open_settings(|| {
        tracing::debug!("Open settings clicked");
        if let Err(e) = handlers::settings::open_settings() {
            tracing::error!("Failed to open Settings: {}", e);
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
        move || {
            tracing::debug!("Check updates clicked");

            // Spawn async task for update check
            slint::spawn_local(async move {
                if let Err(e) = handlers::settings::check_updates().await {
                    tracing::error!("Update check failed: {}", e);
                    // TODO: Show error dialog
                }
            }).unwrap();
        }
    });

    // Papyrus monitoring callback
    main_window.on_toggle_papyrus({
        let window_weak = main_window.as_weak();
        let state = app_state.clone();
        move || {
            tracing::debug!("Toggle Papyrus clicked");
            let window = window_weak.clone();
            let state = state.clone();

            // Spawn async task for toggle
            slint::spawn_local(async move {
                if let Some(w) = window.upgrade() {
                    let current_state = w.get_papyrus_monitoring();

                    match handlers::papyrus::toggle_papyrus_monitoring(current_state, state).await {
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
                            // TODO: Show error dialog
                        }
                    }
                }
            }).unwrap();
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
                                            w.set_success_title(format!("{} {}", $operation.verb(), $category.display_name()).into());
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
                                            w.set_error_title(format!("{} {} Failed", $operation.verb(), $category.display_name()).into());
                                            w.set_error_message(result.message.into());
                                            w.set_show_error_dialog(true);
                                        }
                                    }
                                }
                                Err(e) => {
                                    tracing::error!("{} {} failed: {}", $operation.verb(), $category.display_name(), e);
                                    if let Some(w) = window.upgrade() {
                                        w.set_operation_in_progress(false);
                                        w.set_error_title(format!("{} {} Error", $operation.verb(), $category.display_name()).into());
                                        w.set_error_message(format!("Failed:\n\n{}", e).into());
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
    setup_backup_operation!(main_window, on_backup_xse, handlers::backup::BackupCategory::Xse, handlers::backup::BackupOperation::Backup, perform_backup, app_state);
    setup_backup_operation!(main_window, on_restore_xse, handlers::backup::BackupCategory::Xse, handlers::backup::BackupOperation::Restore, perform_restore, app_state);
    setup_backup_operation!(main_window, on_remove_xse, handlers::backup::BackupCategory::Xse, handlers::backup::BackupOperation::Remove, perform_remove, app_state);

    // RESHADE operations
    setup_backup_operation!(main_window, on_backup_reshade, handlers::backup::BackupCategory::Reshade, handlers::backup::BackupOperation::Backup, perform_backup, app_state);
    setup_backup_operation!(main_window, on_restore_reshade, handlers::backup::BackupCategory::Reshade, handlers::backup::BackupOperation::Restore, perform_restore, app_state);
    setup_backup_operation!(main_window, on_remove_reshade, handlers::backup::BackupCategory::Reshade, handlers::backup::BackupOperation::Remove, perform_remove, app_state);

    // VULKAN operations
    setup_backup_operation!(main_window, on_backup_vulkan, handlers::backup::BackupCategory::Vulkan, handlers::backup::BackupOperation::Backup, perform_backup, app_state);
    setup_backup_operation!(main_window, on_restore_vulkan, handlers::backup::BackupCategory::Vulkan, handlers::backup::BackupOperation::Restore, perform_restore, app_state);
    setup_backup_operation!(main_window, on_remove_vulkan, handlers::backup::BackupCategory::Vulkan, handlers::backup::BackupOperation::Remove, perform_remove, app_state);

    // ENB operations
    setup_backup_operation!(main_window, on_backup_enb, handlers::backup::BackupCategory::Enb, handlers::backup::BackupOperation::Backup, perform_backup, app_state);
    setup_backup_operation!(main_window, on_restore_enb, handlers::backup::BackupCategory::Enb, handlers::backup::BackupOperation::Restore, perform_restore, app_state);
    setup_backup_operation!(main_window, on_remove_enb, handlers::backup::BackupCategory::Enb, handlers::backup::BackupOperation::Remove, perform_remove, app_state);

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
                let xse = handlers::backup::check_backup_exists(handlers::backup::BackupCategory::Xse);
                let reshade = handlers::backup::check_backup_exists(handlers::backup::BackupCategory::Reshade);
                let vulkan = handlers::backup::check_backup_exists(handlers::backup::BackupCategory::Vulkan);
                let enb = handlers::backup::check_backup_exists(handlers::backup::BackupCategory::Enb);

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
            }
        );
    }

    // ========================================
    // ARTICLES TAB EVENT CALLBACKS
    // ========================================

    main_window.on_open_url(|url| {
        let url_str = url.as_str();
        tracing::debug!("Opening URL: {}", url_str);

        if let Err(e) = handlers::articles::handle_open_url(url_str) {
            tracing::error!("Failed to open URL '{}': {}", url_str, e);
            // TODO: Show error dialog to user
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
            let state = state.clone();

            // Spawn async task to scan reports
            slint::spawn_local(async move {
                match handlers::results::scan_reports(state) {
                    Ok(reports) => {
                        if let Some(w) = window.upgrade() {
                            // Convert to Slint ReportData structs
                            let slint_reports: Vec<ReportData> = reports
                                .iter()
                                .map(report_item_to_slint)
                                .collect();

                            // Update UI
                            let model = std::rc::Rc::new(slint::VecModel::from(slint_reports));
                            w.set_reports_list(model.into());

                            // Auto-select first report if available
                            if reports.len() > 0 {
                                w.set_selected_report_index(0);
                                w.set_selected_report_path(
                                    reports[0].path.to_string_lossy().to_string().into()
                                );
                            } else {
                                w.set_selected_report_index(-1);
                                w.set_selected_report_path("".into());
                            }

                            tracing::info!("Reports list updated: {} report(s)", reports.len());
                        }
                    }
                    Err(e) => {
                        tracing::error!("Failed to scan reports: {}", e);
                        if let Some(w) = window.upgrade() {
                            w.set_error_title("Report Scan Error".into());
                            w.set_error_message(format!("Failed to scan reports:\n\n{}", e).into());
                            w.set_show_error_dialog(true);
                        }
                    }
                }
            }).unwrap();
        }
    });

    // Delete report callback
    main_window.on_delete_report({
        let window_weak = main_window.as_weak();
        let state = app_state.clone();
        move || {
            let window = window_weak.clone();
            let state = state.clone();

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
                        w.set_success_message(format!("Successfully deleted: {}", filename).into());
                        w.set_show_success_dialog(true);
                    }
                    Err(e) => {
                        tracing::error!("Failed to delete report: {}", e);
                        w.set_error_title("Delete Failed".into());
                        w.set_error_message(format!("Failed to delete report:\n\n{}", e).into());
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
                    w.set_error_message(format!("Failed to open folder:\n\n{}", e).into());
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

            // Spawn async task to load markdown
            slint::spawn_local(async move {
                match handlers::markdown::load_markdown(&report_path) {
                    Ok(markdown_content) => {
                        if let Some(w) = window.upgrade() {
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
                    }
                    Err(e) => {
                        tracing::error!("Failed to load markdown: {}", e);
                        if let Some(w) = window.upgrade() {
                            w.set_error_title("Failed to Load Report".into());
                            w.set_error_message(format!("Could not load markdown file:\n\n{}", e).into());
                            w.set_show_error_dialog(true);
                        }
                    }
                }
            }).unwrap();
        }
    });

    // Zoom controls for markdown viewer
    main_window.on_zoom_in({
        let window_weak = main_window.as_weak();
        move || {
            if let Some(w) = window_weak.upgrade() {
                let current_zoom = w.get_zoom_level();
                let new_zoom = (current_zoom + 25).min(150);  // Max 150%
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
                let new_zoom = (current_zoom - 25).max(50);  // Min 50%
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
                            format!("Report copied to clipboard ({} characters)", content_str.len()).into()
                        );
                        w.set_show_success_dialog(true);
                    }
                    Err(e) => {
                        tracing::error!("Failed to copy to clipboard: {}", e);

                        // Show error feedback
                        w.set_error_title("Copy Failed".into());
                        w.set_error_message(
                            format!("Failed to copy to clipboard:\n\n{}", e).into()
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

    // Run the application
    tracing::info!("Starting CLASSIC GUI v{}", VERSION);
    main_window.run()
}