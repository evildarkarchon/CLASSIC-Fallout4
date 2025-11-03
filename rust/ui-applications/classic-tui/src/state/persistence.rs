//! Session state persistence for TUI
//!
//! This module provides functionality to save and restore session state,
//! including last active screen, scroll positions, and selected items.

use crate::app::UiState;
use crate::ui::{ArticleCategory, SettingsTab};
use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

/// Session state that persists between application runs
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionState {
    /// Last active screen when app was closed
    pub last_screen: UiStateData,

    /// Output viewer scroll position (main screen) - maps to App.scroll_offset
    pub output_scroll_offset: usize,

    /// Results list scroll position (for navigating report list)
    pub results_list_scroll: usize,

    /// Selected report index in results viewer - maps to App.selected_report_index
    pub selected_report_index: usize,

    /// Report viewer scroll position - maps to App.report_scroll_offset
    pub report_scroll_offset: usize,

    /// Selected article title in articles screen - maps to ArticlesState.selected_article_title
    pub selected_article_title: Option<String>,

    /// Selected article category - maps to ArticlesState.selected_category
    pub selected_category: ArticleCategoryData,

    /// Article viewer scroll position - maps to ArticlesState.scroll_offset
    pub article_scroll_offset: usize,

    /// Last active settings tab
    pub last_settings_tab: SettingsTabData,

    /// Papyrus screen log scroll position
    pub papyrus_scroll_offset: usize,
}

/// Serializable version of UiState
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum UiStateData {
    MainScreen,
    HelpScreen,
    SettingsScreen,
    PapyrusScreen,
    BackupScreen,
    ResultsScreen,
    ArticlesScreen,
}

/// Serializable version of ArticleCategory
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum ArticleCategoryData {
    Installation,
    CommonIssues,
    Advanced,
    Shortcuts,
}

/// Serializable version of SettingsTab
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum SettingsTabData {
    General,
    Paths,
    Advanced,
}

impl Default for SessionState {
    fn default() -> Self {
        Self {
            last_screen: UiStateData::MainScreen,
            output_scroll_offset: 0,
            results_list_scroll: 0,
            selected_report_index: 0,
            report_scroll_offset: 0,
            selected_article_title: None,
            selected_category: ArticleCategoryData::Installation,
            article_scroll_offset: 0,
            last_settings_tab: SettingsTabData::General,
            papyrus_scroll_offset: 0,
        }
    }
}

impl SessionState {
    /// Get the path to the session state file
    fn get_session_path() -> Result<PathBuf> {
        // Store in user's config directory
        let config_dir = dirs::config_dir()
            .context("Failed to determine config directory")?;

        let classic_dir = config_dir.join("CLASSIC");
        fs::create_dir_all(&classic_dir)
            .context("Failed to create CLASSIC config directory")?;

        Ok(classic_dir.join("tui_session.yaml"))
    }

    /// Load session state from disk
    pub fn load() -> Result<Self> {
        let path = Self::get_session_path()?;

        if !path.exists() {
            // No saved session, return default
            return Ok(Self::default());
        }

        let content = fs::read_to_string(&path)
            .context("Failed to read session file")?;

        let state: Self = serde_yaml::from_str(&content)
            .context("Failed to parse session YAML")?;

        Ok(state)
    }

    /// Save session state to disk
    pub fn save(&self) -> Result<()> {
        let path = Self::get_session_path()?;

        let yaml = serde_yaml::to_string(self)
            .context("Failed to serialize session state")?;

        fs::write(&path, yaml)
            .context("Failed to write session file")?;

        Ok(())
    }

    /// Clear saved session state
    #[allow(dead_code)]
    pub fn clear() -> Result<()> {
        let path = Self::get_session_path()?;

        if path.exists() {
            fs::remove_file(&path)
                .context("Failed to remove session file")?;
        }

        Ok(())
    }
}

// Conversion functions between runtime types and serializable types

impl From<UiState> for UiStateData {
    fn from(state: UiState) -> Self {
        match state {
            UiState::MainScreen => UiStateData::MainScreen,
            UiState::HelpScreen => UiStateData::HelpScreen,
            UiState::SettingsScreen => UiStateData::SettingsScreen,
            UiState::PapyrusScreen => UiStateData::PapyrusScreen,
            UiState::BackupScreen => UiStateData::BackupScreen,
            UiState::ResultsScreen => UiStateData::ResultsScreen,
            UiState::ArticlesScreen => UiStateData::ArticlesScreen,
        }
    }
}

impl From<UiStateData> for UiState {
    fn from(data: UiStateData) -> Self {
        match data {
            UiStateData::MainScreen => UiState::MainScreen,
            UiStateData::HelpScreen => UiState::HelpScreen,
            UiStateData::SettingsScreen => UiState::SettingsScreen,
            UiStateData::PapyrusScreen => UiState::PapyrusScreen,
            UiStateData::BackupScreen => UiState::BackupScreen,
            UiStateData::ResultsScreen => UiState::ResultsScreen,
            UiStateData::ArticlesScreen => UiState::ArticlesScreen,
        }
    }
}

impl From<ArticleCategory> for ArticleCategoryData {
    fn from(category: ArticleCategory) -> Self {
        match category {
            ArticleCategory::Installation => ArticleCategoryData::Installation,
            ArticleCategory::CommonIssues => ArticleCategoryData::CommonIssues,
            ArticleCategory::Advanced => ArticleCategoryData::Advanced,
            ArticleCategory::Shortcuts => ArticleCategoryData::Shortcuts,
        }
    }
}

impl From<ArticleCategoryData> for ArticleCategory {
    fn from(data: ArticleCategoryData) -> Self {
        match data {
            ArticleCategoryData::Installation => ArticleCategory::Installation,
            ArticleCategoryData::CommonIssues => ArticleCategory::CommonIssues,
            ArticleCategoryData::Advanced => ArticleCategory::Advanced,
            ArticleCategoryData::Shortcuts => ArticleCategory::Shortcuts,
        }
    }
}

impl From<SettingsTab> for SettingsTabData {
    fn from(tab: SettingsTab) -> Self {
        match tab {
            SettingsTab::General => SettingsTabData::General,
            SettingsTab::Paths => SettingsTabData::Paths,
            SettingsTab::Advanced => SettingsTabData::Advanced,
        }
    }
}

impl From<SettingsTabData> for SettingsTab {
    fn from(data: SettingsTabData) -> Self {
        match data {
            SettingsTabData::General => SettingsTab::General,
            SettingsTabData::Paths => SettingsTab::Paths,
            SettingsTabData::Advanced => SettingsTab::Advanced,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_session_state() {
        let state = SessionState::default();
        assert!(matches!(state.last_screen, UiStateData::MainScreen));
        assert_eq!(state.output_scroll_offset, 0);
        assert_eq!(state.results_list_scroll, 0);
        assert_eq!(state.selected_report_index, 0);
    }

    #[test]
    fn test_ui_state_conversion() {
        let runtime = UiState::ArticlesScreen;
        let data: UiStateData = runtime.into();
        let back: UiState = data.into();
        assert!(matches!(back, UiState::ArticlesScreen));
    }

    #[test]
    fn test_serialization() {
        let state = SessionState::default();
        let yaml = serde_yaml::to_string(&state).unwrap();
        assert!(yaml.contains("last_screen"));
        assert!(yaml.contains("MainScreen"));
    }

    #[test]
    fn test_deserialization() {
        let yaml = r#"
last_screen: ResultsScreen
output_scroll_offset: 42
results_list_scroll: 10
selected_report_index: 5
report_scroll_offset: 20
selected_article_title: "Configuration"
selected_category: CommonIssues
article_scroll_offset: 15
last_settings_tab: Paths
papyrus_scroll_offset: 8
"#;
        let state: SessionState = serde_yaml::from_str(yaml).unwrap();
        assert!(matches!(state.last_screen, UiStateData::ResultsScreen));
        assert_eq!(state.output_scroll_offset, 42);
        assert_eq!(state.selected_report_index, 5);
    }
}
