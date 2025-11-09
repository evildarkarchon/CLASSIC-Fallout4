//! Keyboard input handling and event routing for all TUI screens.
//!
//! This module provides centralized keyboard input handling for the CLASSIC TUI application.
//! It dispatches key events to screen-specific handlers based on the current UI state, handles
//! global key bindings (Q to quit, Ctrl+C), and manages modal overlays (error dialogs, folder pickers).
//!
//! # Architecture
//!
//! The input handler follows a hierarchical dispatch pattern:
//! 1. **Modal Overlays** (highest priority): Error dialogs, update notifications, folder pickers
//! 2. **Global Bindings**: Q to quit, Ctrl+C to quit (work on all screens)
//! 3. **Screen-Specific Bindings**: Dispatched based on [`UiState`]
//!
//! This ensures modals always capture input first, preventing key events from bleeding through
//! to underlying screens.
//!
//! # Key Binding Organization
//!
//! Each screen has a dedicated handler function:
//! - [`handle_main_screen_keys`]: Main screen (F5 scan, F6 game scan, F7 papyrus, etc.)
//! - [`handle_help_screen_keys`]: Help screen (ESC to return)
//! - [`handle_settings_screen_keys`]: Settings screen (Tab, ↑/↓, Space to toggle, S to save)
//! - [`handle_papyrus_screen_keys`]: Papyrus monitoring (F7/P toggle, C clear, ESC back)
//! - [`handle_backup_screen_keys`]: Backup operations (1-4 backup, 5-8 restore, 9-0 remove)
//! - [`handle_results_screen_keys`]: Results viewer (↑/↓ scroll, / search, n/N navigate matches)
//! - [`handle_articles_screen_keys`]: Articles browser (Left/Right categories, ↑/↓ articles, Tab URLs)
//!
//! # Global Key Bindings
//!
//! These work on all screens (unless a modal is active):
//! - **Q**: Quit application
//! - **Ctrl+C**: Quit application (standard terminal convention)
//! - **F1**: Show help screen (navigation aid)
//!
//! # Modal Overlay Bindings
//!
//! - **Error Dialog**: ESC to close, ↑/↓ to scroll, C to copy to clipboard
//! - **Update Notification**: U to open browser, X to dismiss
//! - **Folder Picker**: ↑/↓ navigate, Enter select, Backspace parent, ESC cancel
//!
//! # Main Screen Bindings
//!
//! - **F2/S**: Open staging mods folder picker
//! - **F3/C**: Open custom scan folder picker
//! - **F5/R**: Start crash logs scan
//! - **F6/G**: Start game files scan
//! - **F7/P**: Toggle Papyrus monitor
//! - **F8/B**: Show backup operations screen
//! - **F9**: Show results viewer
//! - **F10**: Show articles/resources screen
//! - **Ctrl+L**: Clear output viewer
//! - **Ctrl+O**: Open settings screen
//! - **↑/↓**: Scroll output (1 line)
//! - **Page Up/Down**: Scroll output (10 lines)
//! - **/**: Search output (TODO - not yet implemented)
//!
//! # Settings Screen Bindings
//!
//! - **Tab**: Switch to next tab (General → Paths → Advanced)
//! - **Shift+Tab**: Switch to previous tab
//! - **↑/↓**: Navigate between settings in current tab
//! - **Space/Enter**: Toggle checkbox (General tab) or open folder picker (Paths tab)
//! - **E**: Edit path (Paths tab) - alternative to Space/Enter
//! - **S**: Save configuration changes
//! - **ESC**: Return to main screen (discards unsaved changes)
//!
//! # Papyrus Screen Bindings
//!
//! - **F7/P**: Toggle monitoring on/off
//! - **C**: Clear log output
//! - **↑/↓**: Scroll log output (if implemented)
//! - **ESC**: Return to main screen
//!
//! # Backup Screen Bindings
//!
//! - **1**: Backup XSE (F4SE/SKSE)
//! - **2**: Backup ReShade
//! - **3**: Backup Vulkan
//! - **4**: Backup ENB
//! - **5**: Restore XSE
//! - **6**: Restore ReShade
//! - **7**: Restore Vulkan
//! - **8**: Restore ENB
//! - **9**: Remove XSE backup
//! - **0**: Remove ReShade backup
//! - **-**: Remove Vulkan backup
//! - **=**: Remove ENB backup
//! - **ESC**: Return to main screen
//!
//! # Results Screen Bindings
//!
//! - **↑/↓**: Navigate report list (left pane) or scroll content (right pane)
//! - **Page Up/Down**: Scroll content by page
//! - **Home/End**: Jump to start/end of report
//! - **/**: Activate search mode (TODO - UI complete, backend pending)
//! - **n**: Next search match
//! - **N**: Previous search match (Shift+n)
//! - **ESC**: Exit search mode or return to main screen
//!
//! # Articles Screen Bindings
//!
//! - **Left/Right**: Switch between categories
//! - **↑/↓**: Navigate articles in current category
//! - **Tab**: Cycle through URLs in current article (if URLs detected)
//! - **Enter**: Open currently selected URL in browser
//! - **ESC**: Return to main screen
//!
//! # Implementation Notes
//!
//! - All handler functions return `Option<UiMessage>` for command pattern
//! - `None` means no action (key ignored or handled internally)
//! - `Some(UiMessage)` enqueues a command for the main event loop to process
//! - Handlers check app state (e.g., `app.is_scanning()`) to conditionally enable keys
//! - Modal overlays checked first to prevent input leakage to underlying screens
//!
//! # Example
//!
//! ```rust,no_run
//! use classic_tui::handlers::input_handler::handle_key_event;
//! use classic_tui::app::App;
//! use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
//!
//! let mut app = App::new();
//! let key_event = KeyEvent::new(KeyCode::Char('q'), KeyModifiers::empty());
//!
//! if let Some(msg) = handle_key_event(&mut app, key_event) {
//!     // Process the UI message (e.g., quit application)
//!     println!("Received message: {:?}", msg);
//! }
//! ```

use crate::app::{App, UiState};
use crate::events::UiMessage;
use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

/// Handle keyboard input events
pub fn handle_key_event(app: &mut App, key: KeyEvent) -> Option<UiMessage> {
    // If error dialog is active, handle error dialog-specific keys first
    if app.is_error_dialog_active() {
        return handle_error_dialog_keys(key);
    }

    // If update notification is visible, check for update-specific keys
    if app.is_update_notification_visible()
        && let Some(msg) = handle_update_notification_keys(key) {
            return Some(msg);
        }

    // If folder picker is active, handle picker-specific keys first
    if app.is_folder_picker_active() {
        return handle_folder_picker_keys(key);
    }

    // Global key bindings (work on all screens)
    if key.code == KeyCode::Char('q') || key.code == KeyCode::Char('Q') {
        return Some(UiMessage::Quit);
    }

    // Ctrl+C to quit
    if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
        return Some(UiMessage::Quit);
    }

    // Screen-specific key bindings
    match app.ui_state {
        UiState::MainScreen => handle_main_screen_keys(app, key),
        UiState::HelpScreen => handle_help_screen_keys(key),
        UiState::SettingsScreen => handle_settings_screen_keys(app, key),
        UiState::PapyrusScreen => handle_papyrus_screen_keys(key),
        UiState::BackupScreen => handle_backup_screen_keys(key),
        UiState::ResultsScreen => handle_results_screen_keys(app, key),
        UiState::ArticlesScreen => handle_articles_screen_keys(app, key),
    }
}

/// Handle keys on the main screen
fn handle_main_screen_keys(app: &mut App, key: KeyEvent) -> Option<UiMessage> {
    match key.code {
        // F1 - Help
        KeyCode::F(1) => Some(UiMessage::ShowHelpScreen),

        // F2 - Staging folder picker
        KeyCode::F(2) | KeyCode::Char('s') | KeyCode::Char('S') => {
            if !app.is_scanning() {
                Some(UiMessage::OpenStagingPicker)
            } else {
                None
            }
        }

        // F3 - Custom folder picker
        KeyCode::F(3) | KeyCode::Char('c') | KeyCode::Char('C') => {
            if !app.is_scanning() {
                Some(UiMessage::OpenCustomPicker)
            } else {
                None
            }
        }

        // F5 or 'r' - Crash scan
        KeyCode::F(5) | KeyCode::Char('r') | KeyCode::Char('R') => {
            if !app.is_scanning() {
                Some(UiMessage::StartCrashScan)
            } else {
                None
            }
        }

        // F6 or 'g' - Game scan
        KeyCode::F(6) | KeyCode::Char('g') | KeyCode::Char('G') => {
            if !app.is_scanning() {
                Some(UiMessage::StartGameScan)
            } else {
                None
            }
        }

        // F7 or 'p' - Papyrus monitor
        KeyCode::F(7) | KeyCode::Char('p') | KeyCode::Char('P') => {
            Some(UiMessage::TogglePapyrusMonitor)
        }

        // F8 or 'b' - Backup operations
        KeyCode::F(8) | KeyCode::Char('b') | KeyCode::Char('B') => {
            Some(UiMessage::ShowBackupScreen)
        }

        // F9 - Results viewer
        KeyCode::F(9) => Some(UiMessage::ShowResultsScreen),

        // F10 - Articles/Resources
        KeyCode::F(10) => Some(UiMessage::ShowArticlesScreen),

        // Ctrl+L - Clear output
        KeyCode::Char('l') | KeyCode::Char('L')
            if key.modifiers.contains(KeyModifiers::CONTROL) =>
        {
            Some(UiMessage::ClearOutput)
        }

        // Ctrl+O - Settings
        KeyCode::Char('o') | KeyCode::Char('O')
            if key.modifiers.contains(KeyModifiers::CONTROL) =>
        {
            Some(UiMessage::ShowSettingsScreen)
        }

        // Arrow keys for scrolling
        KeyCode::Up => Some(UiMessage::ScrollUp(1)),
        KeyCode::Down => Some(UiMessage::ScrollDown(1)),
        KeyCode::PageUp => Some(UiMessage::ScrollUp(10)),
        KeyCode::PageDown => Some(UiMessage::ScrollDown(10)),

        // TODO: '/' for search
        _ => None,
    }
}

/// Handle keys on the help screen
fn handle_help_screen_keys(key: KeyEvent) -> Option<UiMessage> {
    match key.code {
        KeyCode::Esc => Some(UiMessage::ShowMainScreen),
        _ => None,
    }
}

/// Handle keys on the settings screen
fn handle_settings_screen_keys(app: &mut App, key: KeyEvent) -> Option<UiMessage> {
    use crate::ui::SettingsTab;

    match key.code {
        KeyCode::Esc => Some(UiMessage::ShowMainScreen),

        // Tab - Switch to next tab
        KeyCode::Tab if !key.modifiers.contains(KeyModifiers::SHIFT) => {
            Some(UiMessage::NextSettingsTab)
        }

        // Shift+Tab - Switch to previous tab
        KeyCode::BackTab | KeyCode::Tab if key.modifiers.contains(KeyModifiers::SHIFT) => {
            Some(UiMessage::PreviousSettingsTab)
        }

        // 'S' to save configuration
        KeyCode::Char('s') | KeyCode::Char('S') => Some(UiMessage::SaveSettings),

        // 'R' to reset current tab to defaults
        KeyCode::Char('r') | KeyCode::Char('R') => Some(UiMessage::ResetCurrentTab),

        // Arrow keys and Enter/Space - behavior depends on current tab
        KeyCode::Up => {
            match app.settings_state.current_tab {
                SettingsTab::General => {
                    app.settings_state.focus_prev();
                }
                SettingsTab::Paths => {
                    app.settings_state.focus_prev_path();
                }
                SettingsTab::Advanced => {
                    app.settings_state.focus_prev_advanced();
                }
            }
            None
        }
        KeyCode::Down => {
            match app.settings_state.current_tab {
                SettingsTab::General => {
                    app.settings_state.focus_next();
                }
                SettingsTab::Paths => {
                    app.settings_state.focus_next_path();
                }
                SettingsTab::Advanced => {
                    app.settings_state.focus_next_advanced();
                }
            }
            None
        }

        // Space or Enter - action depends on current tab
        KeyCode::Char(' ') | KeyCode::Enter | KeyCode::Char('e') | KeyCode::Char('E') => {
            match app.settings_state.current_tab {
                SettingsTab::General => {
                    // Toggle the setting based on focused item
                    let focused_item = app.settings_state.focused_item;
                    match focused_item {
                        crate::ui::SettingItem::FcxMode => {
                            app.config.fcx_mode = !app.config.fcx_mode
                        }
                        crate::ui::SettingItem::ShowFormIdValues => {
                            app.config.show_formid_values = !app.config.show_formid_values
                        }
                        crate::ui::SettingItem::StatLogging => {
                            app.config.stat_logging = !app.config.stat_logging
                        }
                        crate::ui::SettingItem::MoveUnsolvedLogs => {
                            app.config.move_unsolved_logs = !app.config.move_unsolved_logs
                        }
                        crate::ui::SettingItem::SimplifyLogs => {
                            app.config.simplify_logs = !app.config.simplify_logs
                        }
                        crate::ui::SettingItem::CheckUpdates => {
                            app.check_updates = !app.check_updates
                        }
                    }
                }
                SettingsTab::Paths => {
                    // Open folder picker for the focused path
                    return Some(UiMessage::OpenSettingsPathPicker);
                }
                SettingsTab::Advanced => {
                    // TODO: Add editing for advanced settings when implemented
                }
            }
            None
        }

        _ => None,
    }
}

/// Handle keys on the Papyrus screen
fn handle_papyrus_screen_keys(key: KeyEvent) -> Option<UiMessage> {
    match key.code {
        KeyCode::Esc => Some(UiMessage::ShowMainScreen),
        KeyCode::F(7) | KeyCode::Char('p') | KeyCode::Char('P') => {
            Some(UiMessage::TogglePapyrusMonitor)
        }
        _ => None,
    }
}

/// Handle keys on the Backup screen
fn handle_backup_screen_keys(key: KeyEvent) -> Option<UiMessage> {
    match key.code {
        // ESC - Return to main screen
        KeyCode::Esc => Some(UiMessage::ShowMainScreen),

        // Backup operations (1-4)
        KeyCode::Char('1') => Some(UiMessage::CreateBackup(0)), // XSE
        KeyCode::Char('2') => Some(UiMessage::CreateBackup(1)), // ReShade
        KeyCode::Char('3') => Some(UiMessage::CreateBackup(2)), // Vulkan
        KeyCode::Char('4') => Some(UiMessage::CreateBackup(3)), // ENB

        // Restore operations (5-8)
        KeyCode::Char('5') => Some(UiMessage::RestoreBackup(0)), // XSE
        KeyCode::Char('6') => Some(UiMessage::RestoreBackup(1)), // ReShade
        KeyCode::Char('7') => Some(UiMessage::RestoreBackup(2)), // Vulkan
        KeyCode::Char('8') => Some(UiMessage::RestoreBackup(3)), // ENB

        // Remove operations (9, 0, -, =)
        KeyCode::Char('9') => Some(UiMessage::RemoveBackup(0)), // XSE
        KeyCode::Char('0') => Some(UiMessage::RemoveBackup(1)), // ReShade
        KeyCode::Char('-') => Some(UiMessage::RemoveBackup(2)), // Vulkan
        KeyCode::Char('=') => Some(UiMessage::RemoveBackup(3)), // ENB

        // R - Refresh backup status
        KeyCode::Char('r') | KeyCode::Char('R') => Some(UiMessage::RefreshBackupStatus),

        _ => None,
    }
}

/// Handle keys on the Results screen
fn handle_results_screen_keys(app: &App, key: KeyEvent) -> Option<UiMessage> {
    // If search is active, handle search-specific keys
    if app.search_active {
        return match key.code {
            // ESC - Exit search mode
            KeyCode::Esc => Some(UiMessage::ExitSearch),

            // Backspace - Remove character from search
            KeyCode::Backspace => Some(UiMessage::SearchBackspace),

            // n/N - Navigate matches
            KeyCode::Char('n') => Some(UiMessage::SearchNextMatch),
            KeyCode::Char('N') => Some(UiMessage::SearchPreviousMatch),

            // Any printable character - Add to search
            KeyCode::Char(c) if !c.is_control() => Some(UiMessage::SearchAddChar(c)),

            _ => None,
        };
    }

    // Normal mode (not searching)
    match key.code {
        // ESC - Return to main screen
        KeyCode::Esc => Some(UiMessage::ShowMainScreen),

        // Up/Down - Select reports
        KeyCode::Up => Some(UiMessage::SelectPreviousReport),
        KeyCode::Down => Some(UiMessage::SelectNextReport),

        // PageUp/PageDown - Scroll report viewer
        KeyCode::PageUp => Some(UiMessage::ScrollReportUp(10)),
        KeyCode::PageDown => Some(UiMessage::ScrollReportDown(10)),

        // / - Start search
        KeyCode::Char('/') => Some(UiMessage::StartSearch),

        // R - Refresh report list
        KeyCode::Char('r') | KeyCode::Char('R') => Some(UiMessage::RefreshReports),

        _ => None,
    }
}

/// Handle keys on the Articles/Resources screen
fn handle_articles_screen_keys(_app: &App, key: KeyEvent) -> Option<UiMessage> {
    match key.code {
        // ESC - Return to main screen
        KeyCode::Esc => Some(UiMessage::ShowMainScreen),

        // Left/Right - Navigate categories
        KeyCode::Left => Some(UiMessage::PreviousArticleCategory),
        KeyCode::Right => Some(UiMessage::NextArticleCategory),

        // Up/Down - Navigate articles in current category
        KeyCode::Up => Some(UiMessage::PreviousArticle),
        KeyCode::Down => Some(UiMessage::NextArticle),

        // PageUp/PageDown - Scroll article content
        KeyCode::PageUp => Some(UiMessage::ScrollArticleUp(10)),
        KeyCode::PageDown => Some(UiMessage::ScrollArticleDown(10)),

        // Tab - Navigate to next link in article
        KeyCode::Tab => Some(UiMessage::NextArticleLink),

        // Shift+Tab - Navigate to previous link in article
        KeyCode::BackTab => Some(UiMessage::PreviousArticleLink),

        // Enter - Open currently selected link in browser
        KeyCode::Enter => Some(UiMessage::OpenArticleLink),

        _ => None,
    }
}

/// Handle keys when error dialog is active
fn handle_error_dialog_keys(key: KeyEvent) -> Option<UiMessage> {
    match key.code {
        // ESC - Close error dialog
        KeyCode::Esc => Some(UiMessage::CloseErrorDialog),

        // C or Ctrl+C - Copy error to clipboard
        KeyCode::Char('c') | KeyCode::Char('C') => Some(UiMessage::CopyErrorToClipboard),

        // Up arrow - Scroll error details up
        KeyCode::Up => Some(UiMessage::ScrollErrorUp(1)),

        // Down arrow - Scroll error details down
        KeyCode::Down => Some(UiMessage::ScrollErrorDown(1)),

        // PageUp - Scroll error details up faster
        KeyCode::PageUp => Some(UiMessage::ScrollErrorUp(10)),

        // PageDown - Scroll error details down faster
        KeyCode::PageDown => Some(UiMessage::ScrollErrorDown(10)),

        _ => None,
    }
}

/// Handle keys when update notification is visible
fn handle_update_notification_keys(key: KeyEvent) -> Option<UiMessage> {
    match key.code {
        // U - View update details (open in browser)
        KeyCode::Char('u') | KeyCode::Char('U') => Some(UiMessage::ViewUpdateDetails),

        // D - Dismiss notification
        KeyCode::Char('d') | KeyCode::Char('D') => Some(UiMessage::DismissUpdateNotification),

        // Any other key falls through to normal handling
        _ => None,
    }
}

/// Handle keys when folder picker is active
fn handle_folder_picker_keys(key: KeyEvent) -> Option<UiMessage> {
    match key.code {
        // Esc - Close folder picker
        KeyCode::Esc => Some(UiMessage::CloseFolderPicker),

        // Up arrow - Move selection up
        KeyCode::Up => Some(UiMessage::FolderPickerUp),

        // Down arrow - Move selection down
        KeyCode::Down => Some(UiMessage::FolderPickerDown),

        // Enter - Enter selected directory or confirm selection
        KeyCode::Enter => {
            // If Shift+Enter, select folder; otherwise enter directory
            if key.modifiers.contains(KeyModifiers::SHIFT) {
                Some(UiMessage::SelectFolder)
            } else {
                Some(UiMessage::FolderPickerEnter)
            }
        }

        // Backspace - Go to parent directory
        KeyCode::Backspace => Some(UiMessage::FolderPickerParent),

        // Space - Select current folder
        KeyCode::Char(' ') => Some(UiMessage::SelectFolder),

        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_quit_key() {
        let mut app = App::new();
        let key = KeyEvent::from(KeyCode::Char('q'));
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::Quit)));
    }

    #[test]
    fn test_ctrl_c_quit() {
        let mut app = App::new();
        let key = KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL);
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::Quit)));
    }

    #[test]
    fn test_help_key() {
        let mut app = App::new();
        let key = KeyEvent::from(KeyCode::F(1));
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::ShowHelpScreen)));
    }

    #[test]
    fn test_crash_scan_keys() {
        let mut app = App::new();

        // F5
        let key = KeyEvent::from(KeyCode::F(5));
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::StartCrashScan)));

        // 'r' key
        let key = KeyEvent::from(KeyCode::Char('r'));
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::StartCrashScan)));
    }

    #[test]
    fn test_game_scan_keys() {
        let mut app = App::new();

        // F6
        let key = KeyEvent::from(KeyCode::F(6));
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::StartGameScan)));

        // 'g' key
        let key = KeyEvent::from(KeyCode::Char('g'));
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::StartGameScan)));
    }

    #[test]
    fn test_papyrus_toggle() {
        let mut app = App::new();

        let key = KeyEvent::from(KeyCode::F(7));
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::TogglePapyrusMonitor)));

        let key = KeyEvent::from(KeyCode::Char('p'));
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::TogglePapyrusMonitor)));
    }

    #[test]
    fn test_scroll_keys() {
        let mut app = App::new();

        let key = KeyEvent::from(KeyCode::Up);
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::ScrollUp(1))));

        let key = KeyEvent::from(KeyCode::Down);
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::ScrollDown(1))));

        let key = KeyEvent::from(KeyCode::PageUp);
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::ScrollUp(10))));

        let key = KeyEvent::from(KeyCode::PageDown);
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::ScrollDown(10))));
    }

    #[test]
    fn test_ctrl_l_clear() {
        let mut app = App::new();
        let key = KeyEvent::new(KeyCode::Char('l'), KeyModifiers::CONTROL);
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::ClearOutput)));
    }

    #[test]
    fn test_ctrl_o_settings() {
        let mut app = App::new();
        let key = KeyEvent::new(KeyCode::Char('o'), KeyModifiers::CONTROL);
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::ShowSettingsScreen)));
    }

    #[test]
    fn test_esc_from_help_screen() {
        let mut app = App::new();
        app.switch_screen(UiState::HelpScreen);

        let key = KeyEvent::from(KeyCode::Esc);
        let msg = handle_key_event(&mut app, key);
        assert!(matches!(msg, Some(UiMessage::ShowMainScreen)));
    }

    #[test]
    fn test_scan_blocked_when_already_scanning() {
        let mut app = App::new();
        app.start_crash_scan(); // Start a scan

        // Try to start another scan - should return None
        let key = KeyEvent::from(KeyCode::F(5));
        let msg = handle_key_event(&mut app, key);
        assert!(msg.is_none());
    }
}
