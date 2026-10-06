//! Core path management for CLASSIC.
//!
//! This crate provides unified path management functionality for CLASSIC, including:
//!
//! - **Game Path Detection**: Automatic detection of game installations via registry queries,
//!   XSE log parsing, and platform-specific heuristics
//! - **Documents Path Management**: Cross-platform documents folder detection with support
//!   for Windows registry and Linux Steam/Proton paths
//! - **Path Validation**: Game and Documents settings-path validation and required-file checks
//! - **Documents Checking**: INI file validation and configuration integrity checks
//!
//! # Architecture
//!
//! The crate is organized into modular components:
//!
//! - `game_path`: Game installation detection and path generation
//! - `docs_path`: Documents folder detection and INI management
//! - `validator`: Game/Documents settings-path and required-file verification
//! - `checker`: Documents configuration validation
//! - `ini_parser`: INI file parsing and validation
//! - `platform`: Platform-specific implementations (Windows/Linux)
//! - `error`: Unified error types
//! - `yaml_cache` / `notification_cache`: Per-user cache directories under the OS cache root
//!
//! The generic path primitives (existence, file/directory, permission, drive, and read-only
//! checks, the OS cache root, and the [`PathError`](classic_shared_core::path_core::PathError)
//! they report) are owned by `classic_shared_core::path_core`. This crate builds on them but does
//! not re-export them, so callers that need only a neutral path check depend on shared core alone.
//!
//! Custom-scan folder policy (`is_restricted_path`, `validate_custom_scan_path`, and the combined
//! `validate_settings_paths` check) is owned by `classic_scanlog_core::custom_scan`. Scanlog depends
//! on this crate, so path core neither depends on nor re-exports it. The `RestrictedPath` variant of
//! [`ValidationError`] stays here as shared validation vocabulary that the scanlog policy reports.
//!
//! The version-labelled backup (`VersionBackupManager`, `XseVersion`) is resource policy and is
//! owned by `classic_resource_core`. This crate neither depends on nor re-exports it, so path
//! discovery and validation never pull backup behavior along with them.
//!
//! # Design Principles
//!
//! 1. **Pure Rust Business Logic**: No PyO3 dependencies in this crate
//! 2. **Synchronous Operations**: All I/O is synchronous (fast enough for path operations)
//! 3. **Platform Abstraction**: Conditional compilation for Windows/Linux differences
//! 4. **Error Context**: Rich error types with context using `thiserror`
//!
//! # Examples
//!
//! ```rust,no_run
//! use classic_path_core::{validate_settings_path, GamePathFinder};
//! use std::path::PathBuf;
//!
//! // Settings paths must exist
//! let path = PathBuf::from("Z:\\definitely\\missing\\game");
//! assert!(validate_settings_path(&path, "Game Path", None).is_err());
//!
//! // Find game path (requires YAML settings)
//! // let finder = GamePathFinder::new("Fallout4.exe", Some("f4se_loader.exe"));
//! // let game_path = finder.find_game_path()?;
//! ```

mod error;
mod validator;

// Platform-specific modules
mod platform;

// Component modules
mod checker;
mod docs_path;
mod game_path;
mod ini_parser;
mod notification_cache;
mod yaml_cache;

pub use checker::{DocumentsCheckResult, DocumentsCheckState, DocumentsChecker, IniCheckResult};
pub use docs_path::DocsPathFinder;
pub use error::{
    DocsPathError, DocsPathResult, GamePathError, GamePathResult, ValidationError, ValidationResult,
};
pub use game_path::{GamePathFinder, parse_xse_log};
pub use ini_parser::IniFile;
pub use notification_cache::{
    ensure_notification_cache_dir, ensure_notification_cache_dir_with_env, notification_cache_dir,
    notification_cache_dir_with_env,
};
pub use validator::{
    validate_game_and_documents_paths, validate_required_files, validate_settings_path,
};
pub use yaml_cache::{
    ensure_yaml_cache_dir, ensure_yaml_cache_dir_with_env, yaml_cache_dir, yaml_cache_dir_with_env,
};

// Re-export platform utilities
pub use platform::{get_system_documents_path, parse_steam_library};

// Re-export platform-specific Windows functions
#[cfg(target_os = "windows")]
pub use platform::windows::query_game_registry;

// Module exports (to be uncommented as modules are implemented)
// pub use game_path::GamePathFinder;
// pub use docs_path::DocumentsPathManager;
// pub use checker::DocumentsChecker;
