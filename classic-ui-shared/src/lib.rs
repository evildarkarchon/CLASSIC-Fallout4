//! # classic-ui-shared
//!
//! Shared UI coordination logic for CLASSIC CLI, TUI, and GUI interfaces.
//!
//! This crate provides common functionality that is shared across all three
//! user interface implementations but doesn't belong in the pure business logic
//! crates (`-core` crates). This includes:
//!
//! - Clipboard operations (copy/paste)
//! - Update checking (GitHub releases)
//! - Folder validation and selection helpers
//! - Scan coordination patterns
//!
//! ## Architecture
//!
//! This crate sits between the pure business logic crates and the interface-specific
//! implementations:
//!
//! ```text
//! ┌─────────────────────────────────────────┐
//! │  CLI / TUI / GUI (interface-specific)   │
//! └─────────────────┬───────────────────────┘
//!                   │
//!         ┌─────────▼──────────┐
//!         │ classic-ui-shared  │  ← This crate
//!         └─────────┬──────────┘
//!                   │
//!     ┌─────────────▼─────────────┐
//!     │  -core crates (business)  │
//!     └───────────────────────────┘
//! ```
//!
//! ## Usage
//!
//! Add this crate as a dependency in your interface crate's `Cargo.toml`:
//!
//! ```toml
//! [dependencies]
//! classic-ui-shared = { path = "../classic-ui-shared" }
//! ```
//!
//! Then use the modules as needed:
//!
//! ```rust,ignore
//! use classic_ui_shared::clipboard::copy_to_clipboard;
//! use classic_ui_shared::update_check::check_for_updates;
//! use classic_ui_shared::folder_validation::validate_folder_path;
//! ```

pub mod clipboard;
pub mod folder_validation;
pub mod scan_coordinator;
pub mod update_check;

// Re-export commonly used types
pub use clipboard::{clear_clipboard, copy_to_clipboard, get_clipboard_text};
pub use folder_validation::{validate_folder_path, FolderValidationResult};
pub use update_check::{check_for_updates, UpdateInfo, UpdateStatus};
