use crate::app::{App, UiState};
use crate::events::UiMessage;
use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

/// Handle keyboard input events
pub fn handle_key_event(app: &mut App, key: KeyEvent) -> Option<UiMessage> {
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
    match key.code {
        KeyCode::Esc => Some(UiMessage::ShowMainScreen),

        // Arrow keys for navigation
        KeyCode::Up => {
            app.settings_state.focus_prev();
            None
        }
        KeyCode::Down => {
            app.settings_state.focus_next();
            None
        }

        // Space or Enter to toggle
        KeyCode::Char(' ') | KeyCode::Enter => {
            // Get the focused item before borrowing app mutably
            let focused_item = app.settings_state.focused_item;
            // Toggle the setting based on focused item
            match focused_item {
                crate::ui::SettingItem::FcxMode => app.config.fcx_mode = !app.config.fcx_mode,
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
                crate::ui::SettingItem::CheckUpdates => app.check_updates = !app.check_updates,
            }
            None
        }

        // 'S' to save configuration
        KeyCode::Char('s') | KeyCode::Char('S') => Some(UiMessage::SaveSettings),

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
