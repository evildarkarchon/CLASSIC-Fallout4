//! Session management for TUI application
//!
//! This module provides the SessionManager which tracks runtime state
//! and coordinates with persistence for save/load operations.

use super::persistence::{SessionState, UiStateData};
use crate::app::{App, UiState};
use crate::ui::{ArticleCategory, SettingsTab};
use anyhow::Result;

/// Manages session state during runtime and persistence
pub struct SessionManager {
    state: SessionState,
    dirty: bool,
}

impl SessionManager {
    /// Create a new session manager and load saved state
    pub fn new() -> Result<Self> {
        let state = SessionState::load()?;
        Ok(Self {
            state,
            dirty: false,
        })
    }

    /// Create a session manager with default state (no persistence)
    pub fn with_defaults() -> Self {
        Self {
            state: SessionState::default(),
            dirty: false,
        }
    }

    /// Get the last active screen
    pub fn last_screen(&self) -> UiState {
        self.state.last_screen.clone().into()
    }

    /// Set the last active screen
    pub fn set_last_screen(&mut self, screen: UiState) {
        self.state.last_screen = screen.into();
        self.dirty = true;
    }

    /// Get output scroll position (main screen)
    pub fn output_scroll_offset(&self) -> usize {
        self.state.output_scroll_offset
    }

    /// Set output scroll position (main screen)
    pub fn set_output_scroll_offset(&mut self, position: usize) {
        self.state.output_scroll_offset = position;
        self.dirty = true;
    }

    /// Get results list scroll position
    pub fn results_list_scroll(&self) -> usize {
        self.state.results_list_scroll
    }

    /// Set results list scroll position
    pub fn set_results_list_scroll(&mut self, position: usize) {
        self.state.results_list_scroll = position;
        self.dirty = true;
    }

    /// Get selected report index
    pub fn selected_report_index(&self) -> usize {
        self.state.selected_report_index
    }

    /// Set selected report index
    pub fn set_selected_report_index(&mut self, index: usize) {
        self.state.selected_report_index = index;
        self.dirty = true;
    }

    /// Get report viewer scroll position
    pub fn report_scroll_offset(&self) -> usize {
        self.state.report_scroll_offset
    }

    /// Set report viewer scroll position
    pub fn set_report_scroll_offset(&mut self, position: usize) {
        self.state.report_scroll_offset = position;
        self.dirty = true;
    }

    /// Get selected article index
    pub fn selected_article_index(&self) -> usize {
        self.state.selected_article_index
    }

    /// Set selected article index
    pub fn set_selected_article_index(&mut self, index: usize) {
        self.state.selected_article_index = index;
        self.dirty = true;
    }

    /// Get selected article category
    pub fn selected_category(&self) -> ArticleCategory {
        self.state.selected_category.clone().into()
    }

    /// Set selected article category
    pub fn set_selected_category(&mut self, category: ArticleCategory) {
        self.state.selected_category = category.into();
        self.dirty = true;
    }

    /// Get article scroll position
    pub fn article_scroll_offset(&self) -> usize {
        self.state.article_scroll_offset
    }

    /// Set article scroll position
    pub fn set_article_scroll_offset(&mut self, position: usize) {
        self.state.article_scroll_offset = position;
        self.dirty = true;
    }

    /// Get last active settings tab
    pub fn last_settings_tab(&self) -> SettingsTab {
        self.state.last_settings_tab.clone().into()
    }

    /// Set last active settings tab
    pub fn set_last_settings_tab(&mut self, tab: SettingsTab) {
        self.state.last_settings_tab = tab.into();
        self.dirty = true;
    }

    /// Get Papyrus scroll position
    pub fn papyrus_scroll_offset(&self) -> usize {
        self.state.papyrus_scroll_offset
    }

    /// Set Papyrus scroll position
    pub fn set_papyrus_scroll_offset(&mut self, position: usize) {
        self.state.papyrus_scroll_offset = position;
        self.dirty = true;
    }

    /// Restore session state to app
    pub fn restore_to_app(&self, app: &mut App) {
        // Restore last active screen
        app.ui_state = self.last_screen();

        // Restore scroll positions
        app.scroll_offset = self.output_scroll_offset();
        app.report_scroll_offset = self.report_scroll_offset();

        // Restore selected items
        app.selected_report_index = self.selected_report_index();

        // Restore article state
        app.articles_state.selected_category = self.selected_category();
        app.articles_state.selected_article_index = self.selected_article_index();
        app.articles_state.scroll_offset = self.article_scroll_offset();

        // Restore settings state
        app.settings_state.current_tab = self.last_settings_tab();
    }

    /// Capture current state from app
    pub fn capture_from_app(&mut self, app: &App) {
        // Capture current screen
        self.set_last_screen(app.ui_state);

        // Capture scroll positions
        self.set_output_scroll_offset(app.scroll_offset);
        self.set_report_scroll_offset(app.report_scroll_offset);

        // Capture selected items
        self.set_selected_report_index(app.selected_report_index);

        // Capture article state
        self.set_selected_category(app.articles_state.selected_category);
        self.set_selected_article_index(app.articles_state.selected_article_index);
        self.set_article_scroll_offset(app.articles_state.scroll_offset);

        // Capture settings state
        self.set_last_settings_tab(app.settings_state.current_tab);
    }

    /// Save state to disk if dirty
    pub fn save_if_dirty(&mut self) -> Result<()> {
        if self.dirty {
            self.state.save()?;
            self.dirty = false;
        }
        Ok(())
    }

    /// Force save state to disk
    pub fn save(&mut self) -> Result<()> {
        self.state.save()?;
        self.dirty = false;
        Ok(())
    }

    /// Check if state has unsaved changes
    pub fn is_dirty(&self) -> bool {
        self.dirty
    }
}

impl Default for SessionManager {
    fn default() -> Self {
        Self::with_defaults()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_session_manager_creation() {
        let manager = SessionManager::with_defaults();
        assert!(matches!(manager.last_screen(), UiState::MainScreen));
        assert!(!manager.is_dirty());
    }

    #[test]
    fn test_dirty_tracking() {
        let mut manager = SessionManager::with_defaults();
        assert!(!manager.is_dirty());

        manager.set_output_scroll_offset(42);
        assert!(manager.is_dirty());
        assert_eq!(manager.output_scroll_offset(), 42);
    }

    #[test]
    fn test_screen_tracking() {
        let mut manager = SessionManager::with_defaults();
        manager.set_last_screen(UiState::ResultsScreen);
        assert!(matches!(manager.last_screen(), UiState::ResultsScreen));
        assert!(manager.is_dirty());
    }

    #[test]
    fn test_selected_items() {
        let mut manager = SessionManager::with_defaults();

        manager.set_selected_report_index(5);
        assert_eq!(manager.selected_report_index(), 5);

        manager.set_selected_article_index(2);
        assert_eq!(manager.selected_article_index(), 2);
    }
}
