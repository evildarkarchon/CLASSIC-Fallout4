//! CLASSIC GUI - Rust-native graphical interface
//!
//! This crate provides the Slint-based GUI for CLASSIC crash log analyzer.
//! It uses the existing Tokio runtime from classic-shared-core and the
//! AsyncBridge for coordinating between UI and async operations.

pub mod dialogs;
pub mod logging;
pub mod markdown;
pub mod results;
pub mod scan;
pub mod settings;
pub mod state;
pub mod worker;

// Re-export for convenience
pub use classic_shared_core::AsyncBridge;
pub use logging::init_logging;
pub use dialogs::browse_folder;
pub use markdown::{parse_markdown, MarkdownBlock};
pub use results::{copy_to_clipboard, get_report_content, prepare_report_entries, ReportData};
pub use scan::{scan_crash_logs, ScanResult};
pub use state::{load_window_state, save_window_state, state_file_path, TabGeometry, WindowState};
pub use settings::{
    detect_game_version, game_version_index_to_string, game_version_string_to_index,
    load_settings, reset_to_defaults, save_full_config, save_path_setting, save_setting_bool,
    save_setting_string, settings_file_path, update_source_index_to_string,
    update_source_string_to_index,
};
pub use worker::{simulate_scan, ScanWindowProperties};
