//! CLASSIC TUI (Text User Interface) Library
//!
//! Provides terminal-based interface components for the CLASSIC crash log analyzer.
//! Built with [Ratatui](https://ratatui.rs/) for modern, responsive TUI experience.
//!
//! ## Module Organization
//!
//! - [`app`] - Application state and main TUI logic
//! - [`events`] - Event handling and message passing between components
//! - [`handlers`] - Input handlers, scan operations, backup management
//! - [`ui`] - UI rendering and screen implementations
//! - [`widgets`] - Reusable UI components (folder picker, error dialog, markdown viewer)
//!
//! ## Example
//!
//! ```no_run
//! use classic_tui::{App, ClassicConfig};
//!
//! # #[tokio::main]
//! # async fn main() -> anyhow::Result<()> {
//! // Load configuration
//! let config = ClassicConfig::load_or_default().await?;
//!
//! // Create application
//! let app = App::with_config(config);
//!
//! // Run TUI event loop
//! // ... terminal setup and rendering loop
//! # Ok(())
//! # }
//! ```

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
