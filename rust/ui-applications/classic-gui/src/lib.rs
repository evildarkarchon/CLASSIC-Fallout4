//! CLASSIC GUI - Rust-native graphical interface
//!
//! This crate provides the Slint-based GUI for CLASSIC crash log analyzer.
//! It uses the existing Tokio runtime from classic-shared-core and the
//! AsyncBridge for coordinating between UI and async operations.

pub mod dialogs;
pub mod results;
pub mod scan;
pub mod state;
pub mod worker;

// Re-export for convenience
pub use classic_shared_core::AsyncBridge;
pub use dialogs::browse_folder;
pub use results::{copy_to_clipboard, get_report_content, prepare_report_entries, ReportData};
pub use scan::{scan_crash_logs, ScanResult};
pub use state::{load_window_state, save_window_state, TabGeometry, WindowState};
pub use worker::{simulate_scan, ScanWindowProperties};
