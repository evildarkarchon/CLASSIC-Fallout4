//! CLASSIC TUI (Text User Interface) Library
//!
//! Provides terminal-based interface components for the CLASSIC crash log analyzer.
//! Built with the Textual framework for modern, responsive TUI experience.

/// Application state and main TUI logic
pub mod app;
/// Event handling and message passing
pub mod events;
/// Input and action handlers
pub mod handlers;
/// UI rendering and screens
pub mod ui;
/// Reusable UI widgets
pub mod widgets;

pub use app::App;
pub use classic_config_core::{ClassicConfig, PathConfig};
pub use events::{ScanMessage, UiMessage};
