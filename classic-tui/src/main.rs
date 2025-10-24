  //! CLASSIC TUI - Terminal User Interface for crash log analysis
//!
//! Interactive terminal interface built with Ratatui/Crossterm for analyzing
//! Fallout 4 and Skyrim crash logs.

mod app;
mod events;
mod handlers;
mod ui;
mod widgets;

use anyhow::Result;
use app::{App, UiState};
use classic_config_core::ClassicConfig;
use crossterm::{
    event::{self, Event},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use events::{ScanMessage, UiMessage};
use handlers::{
    handle_key_event, papyrus_handler::PapyrusHandler, papyrus_handler::PapyrusMessage,
    BackupHandler, ScanHandler,
};
use ratatui::{backend::CrosstermBackend, Terminal};
use std::io;
use std::time::Duration;
use tokio::sync::mpsc;
use ui::{
    render_backup_screen, render_help_screen, render_main_screen, render_papyrus_screen,
    render_results_screen, render_settings_screen_interactive,
};

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing (logging)
    tracing_subscriber::fmt::init();

    // Load configuration
    let mut config = ClassicConfig::load_or_default().await?;

    // Load paths from Local.yaml
    config.load_local_yaml_paths("Fallout4").await?;

    // Get Papyrus log path from config BEFORE creating app (Documents\My Games\Fallout4\Logs\Script\Papyrus.0.log)
    let papyrus_log_path = config
        .paths
        .docs_root
        .as_ref()
        .map(|p| p.join("Logs").join("Script").join("Papyrus.0.log"));

    // Get game root path BEFORE creating app
    let game_root = config.paths.game_root.clone();

    // Create application
    let mut app = App::with_config(config);

    // Setup terminal
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    // Create message channels
    let (scan_tx, mut scan_rx) = mpsc::channel::<ScanMessage>(100);
    let (papyrus_tx, mut papyrus_rx) = mpsc::channel::<PapyrusMessage>(100);
    let scan_handler = ScanHandler::new();

    // Create Papyrus handler if path exists
    let papyrus_handler = papyrus_log_path
        .filter(|p| p.exists())
        .map(PapyrusHandler::new);

    // Create Backup handler with game root path
    let mut backup_handler = BackupHandler::new(game_root);

    // Refresh initial backup status
    if let Ok(status) = backup_handler.refresh_status().await {
        app.update_backup_status(status);
    }

    // Main event loop
    let result = run_app(
        &mut terminal,
        &mut app,
        &mut scan_rx,
        &mut papyrus_rx,
        &scan_handler,
        &scan_tx,
        &papyrus_tx,
        papyrus_handler,
        &mut backup_handler,
    )
    .await;

    // Restore terminal
    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;

    result
}

/// Main application loop
async fn run_app(
    terminal: &mut Terminal<CrosstermBackend<io::Stdout>>,
    app: &mut App,
    scan_rx: &mut mpsc::Receiver<ScanMessage>,
    papyrus_rx: &mut mpsc::Receiver<PapyrusMessage>,
    scan_handler: &ScanHandler,
    scan_tx: &mpsc::Sender<ScanMessage>,
    papyrus_tx: &mpsc::Sender<PapyrusMessage>,
    mut papyrus_handler: Option<PapyrusHandler>,
    backup_handler: &mut BackupHandler,
) -> Result<()> {
    loop {
        // Render UI
        terminal.draw(|f| match app.ui_state {
            UiState::MainScreen => render_main_screen(f, app),
            UiState::HelpScreen => render_help_screen(f, app),
            UiState::SettingsScreen => {
                let state = &app.settings_state.clone();
                render_settings_screen_interactive(f, app, state)
            }
            UiState::PapyrusScreen => render_papyrus_screen(f, app),
            UiState::BackupScreen => render_backup_screen(f, app),
            UiState::ResultsScreen => render_results_screen(f, app),
        })?;

        // Poll for keyboard events (non-blocking, 16ms = ~60 FPS)
        if event::poll(Duration::from_millis(16))? {
            if let Event::Key(key) = event::read()? {
                if let Some(msg) = handle_key_event(app, key) {
                    handle_ui_message(
                        app,
                        msg,
                        scan_handler,
                        scan_tx,
                        papyrus_tx,
                        &mut papyrus_handler,
                        backup_handler,
                    )
                    .await?;
                }
            }
        }

        // Process scan messages
        while let Ok(msg) = scan_rx.try_recv() {
            let should_refresh_results = matches!(msg, ScanMessage::Completed(_) | ScanMessage::Error(_));
            handle_scan_message(app, msg);

            // Auto-refresh results if on Results screen and scan completed/failed
            if should_refresh_results && app.ui_state == UiState::ResultsScreen {
                if let Err(e) = app.load_report_files().await {
                    app.add_output(format!("Error auto-refreshing reports: {}", e));
                }
            }
        }

        // Process Papyrus messages
        while let Ok(msg) = papyrus_rx.try_recv() {
            handle_papyrus_message(app, msg);
        }

        // Check if should quit
        if app.should_quit {
            break;
        }
    }

    Ok(())
}

/// Handle UI messages from input handler
async fn handle_ui_message(
    app: &mut App,
    msg: UiMessage,
    scan_handler: &ScanHandler,
    scan_tx: &mpsc::Sender<ScanMessage>,
    papyrus_tx: &mpsc::Sender<PapyrusMessage>,
    papyrus_handler: &mut Option<PapyrusHandler>,
    backup_handler: &mut BackupHandler,
) -> Result<()> {
    match msg {
        UiMessage::Quit => {
            app.should_quit = true;
        }
        UiMessage::ShowMainScreen => {
            app.switch_screen(UiState::MainScreen);
        }
        UiMessage::ShowHelpScreen => {
            app.switch_screen(UiState::HelpScreen);
        }
        UiMessage::ShowSettingsScreen => {
            app.switch_screen(UiState::SettingsScreen);
        }
        UiMessage::ShowPapyrusScreen => {
            app.switch_screen(UiState::PapyrusScreen);
        }
        UiMessage::ShowBackupScreen => {
            app.switch_screen(UiState::BackupScreen);
            // Refresh backup status when entering screen
            if let Ok(status) = backup_handler.refresh_status().await {
                app.update_backup_status(status);
            }
        }
        UiMessage::ShowResultsScreen => {
            app.switch_screen(UiState::ResultsScreen);
            // Load report files when entering screen
            if let Err(e) = app.load_report_files().await {
                app.add_output(format!("Error loading reports: {}", e));
            }
        }
        UiMessage::StartCrashScan => {
            app.start_crash_scan();
            let tx = scan_tx.clone();
            // Use paths from configuration
            let scan_path = app.custom_folder.clone();
            let mods_folder = app.staging_folder.clone();
            let handler = ScanHandler::with_paths(scan_path, mods_folder);
            tokio::spawn(async move {
                if let Err(e) = handler.start_crash_scan(tx.clone()).await {
                    let _ = tx
                        .send(ScanMessage::error(format!("Scan error: {}", e)))
                        .await;
                }
            });
        }
        UiMessage::StartGameScan => {
            app.start_game_scan();
            let tx = scan_tx.clone();
            // Use paths from configuration
            let scan_path = app.custom_folder.clone();
            let mods_folder = app.staging_folder.clone();
            let handler = ScanHandler::with_paths(scan_path, mods_folder);
            tokio::spawn(async move {
                if let Err(e) = handler.start_game_scan(tx.clone()).await {
                    let _ = tx
                        .send(ScanMessage::error(format!("Scan error: {}", e)))
                        .await;
                }
            });
        }
        UiMessage::TogglePapyrusMonitor => {
            if matches!(app.scan_state, app::ScanState::PapyrusMonitoring) {
                // Stop monitoring
                if let Some(handler) = papyrus_handler.as_mut() {
                    handler.stop_monitoring().await;
                }
                app.toggle_papyrus_monitor();
                app.clear_papyrus_data();
            } else {
                // Start monitoring
                app.toggle_papyrus_monitor();
                if let Some(handler) = papyrus_handler.as_mut() {
                    let tx = papyrus_tx.clone();
                    match handler.start_monitoring(tx).await {
                        Ok(()) => {
                            app.add_output("Papyrus monitoring started successfully.".to_string());
                        }
                        Err(e) => {
                            app.add_output(format!("Error starting Papyrus monitor: {}", e));
                            app.scan_error(format!("Failed to start Papyrus monitor: {}", e));
                        }
                    }
                } else {
                    app.add_output("Papyrus log file not found. Check configuration.".to_string());
                    app.scan_error("Papyrus.0.log not found".to_string());
                }
            }
        }
        UiMessage::ClearOutput => {
            app.clear_output();
        }
        UiMessage::ScrollUp(lines) => {
            app.scroll_up(lines);
        }
        UiMessage::ScrollDown(lines) => {
            // Calculate visible lines based on terminal size
            // For now, use a reasonable default
            app.scroll_down(lines, 20);
        }
        UiMessage::UpdateStagingFolder(path) => {
            app.set_staging_folder(path);
        }
        UiMessage::UpdateCustomFolder(path) => {
            app.set_custom_folder(path);
        }
        UiMessage::ToggleUpdateCheck => {
            app.check_updates = !app.check_updates;
        }
        UiMessage::SaveSettings => {
            // Save configuration to YAML file
            if let Err(e) = app.save_config().await {
                // Log error but don't crash
                eprintln!("Failed to save settings: {}", e);
            } else {
                // Could add a success message to output
                app.add_output("Settings saved successfully.".to_string());
            }
        }
        UiMessage::NextSettingsTab => {
            app.settings_state.next_tab();
        }
        UiMessage::PreviousSettingsTab => {
            app.settings_state.prev_tab();
        }
        UiMessage::OpenStagingPicker => {
            app.open_staging_picker();
        }
        UiMessage::OpenCustomPicker => {
            app.open_custom_picker();
        }
        UiMessage::CloseFolderPicker => {
            app.close_staging_picker();
            app.close_custom_picker();
        }
        UiMessage::SelectFolder => {
            // Determine which picker is active and get the selected path
            use handlers::folder_handler::{handle_folder_selection, FolderType};

            if let Some(ref picker) = app.staging_picker {
                if picker.is_active() {
                    let selected_path = picker.get_selected_path();
                    app.close_staging_picker();
                    if let Err(e) =
                        handle_folder_selection(app, FolderType::Staging, selected_path).await
                    {
                        app.add_output(format!("Error selecting folder: {}", e));
                    }
                }
            } else if let Some(ref picker) = app.custom_picker {
                if picker.is_active() {
                    let selected_path = picker.get_selected_path();
                    app.close_custom_picker();
                    if let Err(e) =
                        handle_folder_selection(app, FolderType::Custom, selected_path).await
                    {
                        app.add_output(format!("Error selecting folder: {}", e));
                    }
                }
            }
        }
        UiMessage::FolderPickerUp => {
            if let Some(ref mut picker) = app.staging_picker {
                picker.move_up();
            } else if let Some(ref mut picker) = app.custom_picker {
                picker.move_up();
            }
        }
        UiMessage::FolderPickerDown => {
            if let Some(ref mut picker) = app.staging_picker {
                picker.move_down();
            } else if let Some(ref mut picker) = app.custom_picker {
                picker.move_down();
            }
        }
        UiMessage::FolderPickerEnter => {
            if let Some(ref mut picker) = app.staging_picker {
                picker.enter_selected();
            } else if let Some(ref mut picker) = app.custom_picker {
                picker.enter_selected();
            }
        }
        UiMessage::FolderPickerParent => {
            if let Some(ref mut picker) = app.staging_picker {
                picker.go_up();
            } else if let Some(ref mut picker) = app.custom_picker {
                picker.go_up();
            }
        }
        UiMessage::CreateBackup(index) => {
            use classic_file_io_core::BackupType;
            let backup_types = BackupType::all();
            if let Some(&backup_type) = backup_types.get(index) {
                app.add_output(format!("Creating {} backup...", backup_type.display_name()));
                match backup_handler.create_backup(backup_type).await {
                    Ok(info) => {
                        app.add_output(format!(
                            "✓ Backup created: {} file(s) backed up",
                            info.file_count
                        ));
                        if let Ok(status) = backup_handler.refresh_status().await {
                            app.update_backup_status(status);
                        }
                    }
                    Err(e) => {
                        app.add_output(format!("✗ Backup failed: {}", e));
                    }
                }
            }
        }
        UiMessage::RestoreBackup(index) => {
            use classic_file_io_core::BackupType;
            let backup_types = BackupType::all();
            if let Some(&backup_type) = backup_types.get(index) {
                if backup_handler.backup_exists(backup_type) {
                    app.add_output(format!("Restoring {} backup...", backup_type.display_name()));
                    match backup_handler.restore_backup(backup_type).await {
                        Ok(count) => {
                            app.add_output(format!("✓ Restored {} file(s)", count));
                        }
                        Err(e) => {
                            app.add_output(format!("✗ Restore failed: {}", e));
                        }
                    }
                } else {
                    app.add_output(format!(
                        "No backup exists for {}",
                        backup_type.display_name()
                    ));
                }
            }
        }
        UiMessage::RemoveBackup(index) => {
            use classic_file_io_core::BackupType;
            let backup_types = BackupType::all();
            if let Some(&backup_type) = backup_types.get(index) {
                if backup_handler.backup_exists(backup_type) {
                    app.add_output(format!("Removing {} backup...", backup_type.display_name()));
                    match backup_handler.remove_backup(backup_type).await {
                        Ok(()) => {
                            app.add_output("✓ Backup removed".to_string());
                            if let Ok(status) = backup_handler.refresh_status().await {
                                app.update_backup_status(status);
                            }
                        }
                        Err(e) => {
                            app.add_output(format!("✗ Remove failed: {}", e));
                        }
                    }
                } else {
                    app.add_output(format!(
                        "No backup exists for {}",
                        backup_type.display_name()
                    ));
                }
            }
        }
        UiMessage::RefreshBackupStatus => {
            app.add_output("Refreshing backup status...".to_string());
            match backup_handler.refresh_status().await {
                Ok(status) => {
                    app.update_backup_status(status);
                    app.add_output("✓ Backup status refreshed".to_string());
                }
                Err(e) => {
                    app.add_output(format!("✗ Refresh failed: {}", e));
                }
            }
        }
        UiMessage::SelectNextReport => {
            if let Err(e) = app.select_next_report().await {
                app.add_output(format!("Error selecting report: {}", e));
            }
        }
        UiMessage::SelectPreviousReport => {
            if let Err(e) = app.select_previous_report().await {
                app.add_output(format!("Error selecting report: {}", e));
            }
        }
        UiMessage::ScrollReportUp(lines) => {
            app.scroll_report_up(lines);
        }
        UiMessage::ScrollReportDown(lines) => {
            // Calculate visible lines (approximate, terminal height minus borders)
            let visible_lines = 30; // TODO: Get actual terminal height
            app.scroll_report_down(lines, visible_lines);
        }
        UiMessage::RefreshReports => {
            if let Err(e) = app.load_report_files().await {
                app.add_output(format!("Error refreshing reports: {}", e));
            }
        }
        UiMessage::StartSearch => {
            app.start_search();
        }
        UiMessage::ExitSearch => {
            app.exit_search();
        }
        UiMessage::SearchAddChar(c) => {
            app.add_search_char(c);
        }
        UiMessage::SearchBackspace => {
            app.backspace_search();
        }
        UiMessage::SearchNextMatch => {
            let visible_lines = 30; // TODO: Get actual terminal height
            app.next_search_match(visible_lines);
        }
        UiMessage::SearchPreviousMatch => {
            let visible_lines = 30; // TODO: Get actual terminal height
            app.previous_search_match(visible_lines);
        }
    }

    Ok(())
}

/// Handle scan messages from scan handler
fn handle_scan_message(app: &mut App, msg: ScanMessage) {
    match msg {
        ScanMessage::Progress(progress) => {
            app.update_progress(progress);
        }
        ScanMessage::Output(line) => {
            app.add_output(line);
        }
        ScanMessage::Completed(results) => {
            app.complete_scan(results.clone());
            app.add_output(format!(
                "Scan completed! Scanned: {}, Patterns: {}, FormIDs: {}, Suspects: {}",
                results.scanned_count,
                results.patterns_matched,
                results.formids_resolved,
                results.suspects_count
            ));
        }
        ScanMessage::Error(error) => {
            app.scan_error(error);
        }
    }
}

/// Handle Papyrus monitoring messages
fn handle_papyrus_message(app: &mut App, msg: PapyrusMessage) {
    match msg {
        PapyrusMessage::Started => {
            app.add_output("Papyrus monitoring started.".to_string());
        }
        PapyrusMessage::StatsUpdate(stats) => {
            app.update_papyrus_stats(stats);
        }
        PapyrusMessage::NewLines(lines) => {
            app.add_papyrus_lines(lines);
        }
        PapyrusMessage::Error(error) => {
            app.add_output(format!("Papyrus monitor error: {}", error));
        }
        PapyrusMessage::Stopped => {
            app.add_output("Papyrus monitoring stopped.".to_string());
        }
    }
}
