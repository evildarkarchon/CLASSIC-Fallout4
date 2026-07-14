use crossterm::event::{
    Event, KeyCode, KeyEvent, KeyEventKind, KeyModifiers, MouseButton, MouseEvent, MouseEventKind,
};
use ratatui::layout::Position;

use crate::app::{App, Overlay, TabIndex};
use crate::tabs::main_tab::MainFocus;

impl App {
    pub fn handle_event(&mut self, event: Event) {
        match event {
            Event::Key(key) if key.kind == KeyEventKind::Press => self.handle_key(key),
            Event::Mouse(mouse) => self.handle_mouse(mouse),
            Event::Paste(text) => self.handle_paste(&text),
            _ => {}
        }
    }

    fn handle_key(&mut self, key: KeyEvent) {
        if let Some(overlay) = self.active_overlay.clone() {
            match overlay {
                Overlay::ConfirmRemoveBackup(_) => match key.code {
                    KeyCode::Esc | KeyCode::Char('n') => self.close_overlay(),
                    KeyCode::Enter | KeyCode::Char('y') => self.confirm_backup_remove(),
                    _ => {}
                },
                Overlay::ConfirmDeleteReport(_) => match key.code {
                    KeyCode::Esc | KeyCode::Char('n') => self.cancel_results_delete(),
                    KeyCode::Enter | KeyCode::Char('y') => self.confirm_results_delete(),
                    _ => {}
                },
                Overlay::Settings => match key.code {
                    KeyCode::Esc => self.close_overlay(),
                    KeyCode::Char('m') | KeyCode::Char('M') => self.apply_user_settings_migration(),
                    KeyCode::Char('i') | KeyCode::Char('I') => self.import_legacy_tui_state(),
                    _ => {}
                },
                _ => match key.code {
                    KeyCode::Esc | KeyCode::Enter => self.close_overlay(),
                    _ => {}
                },
            }
            return;
        }

        if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
            self.should_quit = true;
            return;
        }

        match key.code {
            KeyCode::F(1) => {
                self.active_overlay = Some(Overlay::Help);
                return;
            }
            KeyCode::F(5) => {
                if self.active_tab == TabIndex::Results {
                    self.refresh_results_reports();
                } else {
                    self.start_or_cancel_crash_scan();
                }
                return;
            }
            KeyCode::F(6) => {
                self.start_game_files_scan();
                return;
            }
            KeyCode::F(7) => {
                self.toggle_papyrus();
                return;
            }
            KeyCode::Char('q') if !key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.should_quit = true;
                return;
            }
            KeyCode::Char('o') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.active_overlay = Some(Overlay::Settings);
                return;
            }
            KeyCode::Char('1') => {
                self.set_active_tab(TabIndex::MainOptions);
                return;
            }
            KeyCode::Char('2') => {
                self.set_active_tab(TabIndex::FileBackup);
                return;
            }
            KeyCode::Char('3') => {
                self.set_active_tab(TabIndex::Articles);
                return;
            }
            KeyCode::Char('4') => {
                self.set_active_tab(TabIndex::Results);
                return;
            }
            _ => {}
        }

        match self.active_tab {
            TabIndex::MainOptions => self.handle_main_tab_key(key),
            TabIndex::FileBackup => self.handle_backup_tab_key(key),
            TabIndex::Articles => self.handle_articles_tab_key(key),
            TabIndex::Results => self.handle_results_tab_key(key),
        }
    }

    fn handle_paste(&mut self, text: &str) {
        if self.active_tab != TabIndex::MainOptions {
            return;
        }
        if let Some(input) = self.active_input_mut() {
            input.insert_text(text);
        }
    }

    fn handle_mouse(&mut self, mouse: MouseEvent) {
        if self.active_overlay.is_some() {
            return;
        }

        let position = Position::new(mouse.column, mouse.row);

        if self.active_tab == TabIndex::Results {
            match mouse.kind {
                MouseEventKind::ScrollDown
                    if self.click_areas.results.viewer_area.contains(position) =>
                {
                    self.results_set_focus_viewer();
                    self.results_scroll_by(3);
                    return;
                }
                MouseEventKind::ScrollUp
                    if self.click_areas.results.viewer_area.contains(position) =>
                {
                    self.results_set_focus_viewer();
                    self.results_scroll_by(-3);
                    return;
                }
                _ => {}
            }
        }

        if mouse.kind != MouseEventKind::Down(MouseButton::Left) {
            return;
        }

        for (tab, area) in &self.click_areas.tab_areas {
            if area.contains(position) {
                self.set_active_tab(*tab);
                return;
            }
        }

        if self.active_tab == TabIndex::FileBackup {
            self.handle_backup_mouse(position);
            return;
        }

        if self.active_tab == TabIndex::Articles {
            self.handle_articles_mouse(position);
            return;
        }

        if self.active_tab == TabIndex::Results {
            self.handle_results_mouse(position);
            return;
        }

        if self.active_tab != TabIndex::MainOptions {
            return;
        }

        if self.click_areas.main.staging_input.contains(position) {
            self.main_focus = MainFocus::StagingInput;
            return;
        }
        if self.click_areas.main.staging_browse.contains(position) {
            self.main_focus = MainFocus::StagingBrowse;
            self.open_folder_dialog_for_focus();
            return;
        }
        if self.click_areas.main.custom_input.contains(position) {
            self.main_focus = MainFocus::CustomInput;
            return;
        }
        if self.click_areas.main.custom_browse.contains(position) {
            self.main_focus = MainFocus::CustomBrowse;
            self.open_folder_dialog_for_focus();
            return;
        }

        if self.click_areas.main.scan_crash.contains(position) {
            self.main_focus = MainFocus::ScanCrash;
            self.start_or_cancel_crash_scan();
            return;
        }
        if self.click_areas.main.scan_game.contains(position) {
            self.main_focus = MainFocus::ScanGame;
            self.start_game_files_scan();
            return;
        }
        if self.click_areas.main.about.contains(position) {
            self.main_focus = MainFocus::About;
            self.active_overlay = Some(Overlay::About);
            return;
        }
        if self.click_areas.main.help.contains(position) {
            self.main_focus = MainFocus::Help;
            self.active_overlay = Some(Overlay::Help);
            return;
        }
        if self.click_areas.main.settings.contains(position) {
            self.main_focus = MainFocus::Settings;
            self.active_overlay = Some(Overlay::Settings);
            return;
        }
        if self.click_areas.main.open_logs.contains(position) {
            self.main_focus = MainFocus::OpenLogs;
            self.open_crash_logs_folder();
            return;
        }
        if self.click_areas.main.check_updates.contains(position) {
            self.main_focus = MainFocus::CheckUpdates;
            self.check_updates();
            return;
        }
        if self.click_areas.main.papyrus.contains(position) {
            self.main_focus = MainFocus::Papyrus;
            self.toggle_papyrus();
        }
    }

    fn handle_main_tab_key(&mut self, key: KeyEvent) {
        match key.code {
            KeyCode::Tab => {
                self.main_focus = self.main_focus.next();
            }
            KeyCode::BackTab => {
                self.main_focus = self.main_focus.prev();
            }
            KeyCode::Esc => {
                self.main_focus = MainFocus::ScanCrash;
            }
            KeyCode::Enter => {
                self.activate_focus();
            }
            KeyCode::Left => self
                .active_input_mut()
                .map(|input| input.move_left())
                .unwrap_or(()),
            KeyCode::Right => self
                .active_input_mut()
                .map(|input| input.move_right())
                .unwrap_or(()),
            KeyCode::Home => self
                .active_input_mut()
                .map(|input| input.move_home())
                .unwrap_or(()),
            KeyCode::End => self
                .active_input_mut()
                .map(|input| input.move_end())
                .unwrap_or(()),
            KeyCode::Backspace => self
                .active_input_mut()
                .map(|input| input.backspace())
                .unwrap_or(()),
            KeyCode::Delete => self
                .active_input_mut()
                .map(|input| input.delete())
                .unwrap_or(()),
            KeyCode::Char(ch)
                if self.is_input_focus() && !key.modifiers.contains(KeyModifiers::CONTROL) =>
            {
                if let Some(input) = self.active_input_mut() {
                    input.insert_char(ch);
                }
            }
            _ => {}
        }
    }

    fn handle_backup_tab_key(&mut self, key: KeyEvent) {
        match key.code {
            KeyCode::Up => self.backup_select_prev(),
            KeyCode::Down => self.backup_select_next(),
            KeyCode::Char('b') | KeyCode::Char('B') => self.backup_create_selected(),
            KeyCode::Char('r') | KeyCode::Char('R') => self.backup_restore_selected(),
            KeyCode::Char('d') | KeyCode::Char('D') => self.backup_request_remove_selected(),
            KeyCode::Char('o') | KeyCode::Char('O') => self.open_backups_folder(),
            _ => {}
        }
    }

    fn handle_articles_tab_key(&mut self, key: KeyEvent) {
        match key.code {
            KeyCode::Left => self.articles_move_left(),
            KeyCode::Right => self.articles_move_right(),
            KeyCode::Up => self.articles_move_up(),
            KeyCode::Down => self.articles_move_down(),
            KeyCode::Enter => self.open_selected_article(),
            _ => {}
        }
    }

    fn handle_backup_mouse(&mut self, position: Position) {
        let row_areas = self.click_areas.backup.rows;
        let action_areas = self.click_areas.backup.actions;

        for (index, row_area) in row_areas.iter().enumerate() {
            if row_area.contains(position) {
                self.backup_select_row(index);
            }

            let actions = action_areas[index];
            if actions.backup.contains(position) {
                self.backup_select_row(index);
                self.backup_create_selected();
                return;
            }
            if actions.restore.contains(position) {
                self.backup_select_row(index);
                self.backup_restore_selected();
                return;
            }
            if actions.remove.contains(position) {
                self.backup_select_row(index);
                self.backup_request_remove_selected();
                return;
            }
        }

        if self.click_areas.backup.open_backups.contains(position) {
            self.open_backups_folder();
        }
    }

    fn handle_articles_mouse(&mut self, position: Position) {
        let cell_areas = self.click_areas.articles.cells;
        for (index, cell_area) in cell_areas.iter().enumerate() {
            if cell_area.contains(position) {
                self.select_article(index);
                self.open_selected_article();
                return;
            }
        }
    }

    fn handle_results_tab_key(&mut self, key: KeyEvent) {
        match key.code {
            KeyCode::Up => {
                if matches!(self.results.focus, crate::app::ResultsFocus::Viewer) {
                    self.results_scroll_by(-1);
                } else {
                    self.results_select_prev();
                }
            }
            KeyCode::Down => {
                if matches!(self.results.focus, crate::app::ResultsFocus::Viewer) {
                    self.results_scroll_by(1);
                } else {
                    self.results_select_next();
                }
            }
            KeyCode::Enter => {
                if matches!(self.results.focus, crate::app::ResultsFocus::Viewer) {
                    self.results_open_active_link();
                } else {
                    self.results_select_filtered_index(self.results.selected_filtered.unwrap_or(0));
                }
            }
            KeyCode::Tab => self.results_toggle_focus(),
            KeyCode::Left => self.results_set_focus_list(),
            KeyCode::Right => self.results_set_focus_viewer(),
            KeyCode::PageDown => self.results_scroll_page_down(),
            KeyCode::PageUp => self.results_scroll_page_up(),
            KeyCode::Home => self.results_scroll_home(),
            KeyCode::End => self.results_scroll_end(),
            KeyCode::Esc => self.results_clear_active_link(),
            KeyCode::Char('s') | KeyCode::Char('S') => self.results_toggle_sort(),
            KeyCode::Char('o') | KeyCode::Char('O') => self.open_crash_logs_folder(),
            KeyCode::Char('n') | KeyCode::Char('N')
                if matches!(self.results.focus, crate::app::ResultsFocus::Viewer) =>
            {
                self.results_select_next_link();
            }
            KeyCode::Char('p') | KeyCode::Char('P')
                if matches!(self.results.focus, crate::app::ResultsFocus::Viewer) =>
            {
                self.results_select_prev_link();
            }
            KeyCode::Delete => self.results_request_delete_selected(),
            KeyCode::Backspace => {
                if matches!(self.results.focus, crate::app::ResultsFocus::List) {
                    self.results_backspace_search();
                }
            }
            KeyCode::Char('a') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.results_copy_all();
            }
            KeyCode::Char(ch)
                if !key.modifiers.contains(KeyModifiers::CONTROL)
                    && ch != 's'
                    && ch != 'S'
                    && ch != 'o'
                    && ch != 'O'
                    && matches!(self.results.focus, crate::app::ResultsFocus::List) =>
            {
                self.results_push_search_char(ch);
            }
            _ => {}
        }
    }

    fn handle_results_mouse(&mut self, position: Position) {
        if self
            .click_areas
            .results
            .empty_scan_button
            .contains(position)
        {
            self.results_empty_state_scan_click();
            return;
        }

        if self.click_areas.results.sort_header.contains(position) {
            self.results_set_focus_list();
            self.results_toggle_sort();
            return;
        }

        let link_areas = self.click_areas.results.viewer_link_areas.clone();
        for hit in link_areas {
            if hit.area.contains(position) {
                self.results_set_focus_viewer();
                self.results_open_link_index(hit.link_index);
                return;
            }
        }

        let row_areas = self.click_areas.results.list_rows.clone();
        for (filtered_index, row_area) in row_areas {
            if row_area.contains(position) {
                self.results_set_focus_list();
                self.results_select_filtered_index(filtered_index);
                return;
            }
        }

        if self.click_areas.results.refresh_button.contains(position) {
            self.refresh_results_reports();
            return;
        }

        if self.click_areas.results.delete_button.contains(position) {
            self.results_request_delete_selected();
            return;
        }

        if self.click_areas.results.copy_button.contains(position) {
            self.results_copy_all();
            return;
        }

        if self.click_areas.results.viewer_area.contains(position) {
            self.results_set_focus_viewer();
            return;
        }

        if self.click_areas.results.open_button.contains(position) {
            self.open_crash_logs_folder();
        }
    }

    fn activate_focus(&mut self) {
        match self.main_focus {
            MainFocus::StagingInput | MainFocus::CustomInput => {
                match self.save_paths_from_inputs() {
                    Ok(()) => {
                        self.scan_status = "User Settings paths saved".to_string();
                    }
                    Err(error) => {
                        self.scan_status = error;
                    }
                }
                self.status_clear_at = None;
            }
            MainFocus::StagingBrowse | MainFocus::CustomBrowse => {
                self.open_folder_dialog_for_focus()
            }
            MainFocus::ScanCrash => self.start_or_cancel_crash_scan(),
            MainFocus::ScanGame => self.start_game_files_scan(),
            MainFocus::About => self.active_overlay = Some(Overlay::About),
            MainFocus::Help => self.active_overlay = Some(Overlay::Help),
            MainFocus::Settings => self.active_overlay = Some(Overlay::Settings),
            MainFocus::OpenLogs => self.open_crash_logs_folder(),
            MainFocus::CheckUpdates => self.check_updates(),
            MainFocus::Papyrus => self.toggle_papyrus(),
        }
    }

    fn open_folder_dialog_for_focus(&mut self) {
        #[cfg(target_os = "linux")]
        {
            self.scan_status =
                "Folder browser is unavailable on this Linux build. Enter the path manually."
                    .to_string();
        }

        #[cfg(not(target_os = "linux"))]
        {
            let initial = match self.main_focus {
                MainFocus::StagingBrowse => self.staging_mods_input.value.trim(),
                MainFocus::CustomBrowse => self.custom_scan_input.value.trim(),
                _ => "",
            };

            let mut dialog = rfd::FileDialog::new();
            if !initial.is_empty() {
                dialog = dialog.set_directory(initial);
            }

            if let Some(path) = dialog.pick_folder() {
                let value = path.to_string_lossy().to_string();
                match self.main_focus {
                    MainFocus::StagingBrowse => self.staging_mods_input.set_value(value),
                    MainFocus::CustomBrowse => self.custom_scan_input.set_value(value),
                    _ => {}
                }

                if let Err(error) = self.save_paths_from_inputs() {
                    self.scan_status = error;
                }
            }
        }
    }

    fn is_input_focus(&self) -> bool {
        matches!(
            self.main_focus,
            MainFocus::StagingInput | MainFocus::CustomInput
        )
    }

    fn active_input_mut(&mut self) -> Option<&mut crate::app::InputState> {
        match self.main_focus {
            MainFocus::StagingInput => Some(&mut self.staging_mods_input),
            MainFocus::CustomInput => Some(&mut self.custom_scan_input),
            _ => None,
        }
    }
}
