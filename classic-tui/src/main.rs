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
use handlers::{handle_key_event, ScanHandler};
use ratatui::{backend::CrosstermBackend, Terminal};
use std::io;
use std::time::Duration;
use tokio::sync::mpsc;
use ui::{
    render_help_screen, render_main_screen, render_papyrus_screen,
    render_settings_screen_interactive,
};

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing (logging)
    tracing_subscriber::fmt::init();

    // Load configuration
    let mut config = ClassicConfig::load_or_default().await?;

    // Load paths from Local.yaml
    config.load_local_yaml_paths("Fallout4").await?;

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
    let scan_handler = ScanHandler::new();

    // Main event loop
    let result = run_app(
        &mut terminal,
        &mut app,
        &mut scan_rx,
        &scan_handler,
        &scan_tx,
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
    scan_handler: &ScanHandler,
    scan_tx: &mpsc::Sender<ScanMessage>,
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
        })?;

        // Poll for keyboard events (non-blocking, 16ms = ~60 FPS)
        if event::poll(Duration::from_millis(16))? {
            if let Event::Key(key) = event::read()? {
                if let Some(msg) = handle_key_event(app, key) {
                    handle_ui_message(app, msg, scan_handler, scan_tx).await?;
                }
            }
        }

        // Process scan messages
        while let Ok(msg) = scan_rx.try_recv() {
            handle_scan_message(app, msg);
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
            app.toggle_papyrus_monitor();
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
