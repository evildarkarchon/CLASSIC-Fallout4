//! Core path management for CLASSIC.
//!
//! This crate provides unified path management functionality for CLASSIC, including:
//!
//! - **Game Path Detection**: Automatic detection of game installations via registry queries,
//!   XSE log parsing, and platform-specific heuristics
//! - **Documents Path Management**: Cross-platform documents folder detection with support
//!   for Windows registry and Linux Steam/Proton paths
//! - **Path Validation**: Comprehensive path validation with restriction checks for custom scans
//! - **Backup Management**: Version-aware backup creation with metadata preservation
//! - **Documents Checking**: INI file validation and configuration integrity checks
//!
//! # Architecture
//!
//! The crate is organized into modular components:
//!
//! - `game_path`: Game installation detection and path generation
//! - `docs_path`: Documents folder detection and INI management
//! - `validator`: Path validation and settings verification
//! - `backup`: Backup creation and XSE version extraction
//! - `checker`: Documents configuration validation
//! - `ini_parser`: INI file parsing and validation
//! - `platform`: Platform-specific implementations (Windows/Linux)
//! - `error`: Unified error types
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
//! use classic_path_core::{validator, GamePathFinder};
//! use std::path::PathBuf;
//!
//! // Validate a path
//! let path = PathBuf::from("C:\\Games\\Fallout4");
//! assert!(validator::is_valid_path(&path));
//!
//! // Find game path (requires YAML settings)
//! // let finder = GamePathFinder::new("Fallout4.exe", Some("f4se_loader.exe"));
//! // let game_path = finder.find_game_path()?;
//! ```

mod error;
mod validator;

// Platform-specific modules
mod platform;

// Component modules (to be implemented)
// mod game_path;
// mod docs_path;
// mod backup;
// mod checker;
// mod ini_parser;

pub use error::{
    PathError, ValidationError, GamePathError, DocsPathError, BackupError,
    PathResult, ValidationResult, GamePathResult, DocsPathResult, BackupResult,
};
pub use validator::{
    is_valid_path, is_restricted_path, validate_settings_paths,
    validate_path_exists, validate_is_directory, validate_is_file,
    validate_required_files, validate_custom_scan_path, validate_settings_path,
};

// Re-export platform utilities
pub use platform::{get_system_documents_path, parse_steam_library};

// Re-export platform-specific Windows functions
#[cfg(target_os = "windows")]
pub use platform::windows::query_game_registry;

// Module exports (to be uncommented as modules are implemented)
// pub use game_path::GamePathFinder;
// pub use docs_path::DocumentsPathManager;
// pub use backup::BackupManager;
// pub use checker::DocumentsChecker;
