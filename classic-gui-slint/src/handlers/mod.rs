//! Handler modules for GUI event callbacks
//!
//! This module contains all business logic handlers for the Slint GUI,
//! organized by functional area. All handlers follow async-first patterns
//! and use proper error handling with `anyhow::Result`.
//!
//! # Handler Modules
//!
//! - [`articles`]: URL opening for resource links and documentation
//! - [`backup`]: Game file backup/restore/remove operations
//! - [`clipboard`]: Copy-to-clipboard functionality for reports and logs
//! - [`folders`]: Native folder selection dialogs for game/mod directories
//! - [`help`]: Context-sensitive help system and tooltips
//! - [`markdown`]: Report markdown loading and rendering
//! - [`papyrus`]: Real-time Papyrus log monitoring with crash detection
//! - [`pastebin`]: Download crash logs from Pastebin URLs
//! - [`results`]: Report list management and operations
//! - [`scan`]: Crash log and game file scanning orchestration
//! - [`settings`]: Application settings utilities and state management
//! - [`settings_dialog`]: Settings dialog event handlers
//! - [`update_check`]: Automatic update checking via GitHub API
//!
//! # Async Patterns
//!
//! All async handlers use `AsyncBridge::run_with_ui_update()` when called from
//! Slint callbacks to ensure proper UI thread safety and event loop integration.

pub mod articles;
pub mod backup;
pub mod clipboard;
pub mod folders;
pub mod help;
pub mod markdown;
pub mod papyrus;
pub mod pastebin;
pub mod results;
pub mod scan;
pub mod settings;
pub mod settings_dialog;
pub mod update_check;
