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
//! use classic_path_core::{is_valid_path, GamePathFinder};
//! use std::path::PathBuf;
//!
//! // Validate a path
//! let path = PathBuf::from("C:\\Games\\Fallout4");
//! assert!(is_valid_path(&path));
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
mod backup;
mod checker;
mod docs_path;
mod game_path;
mod ini_parser;
mod notification_cache;
mod yaml_cache;

pub use backup::{BackupManager, XseVersion};
pub use checker::{DocumentsCheckResult, DocumentsCheckState, DocumentsChecker, IniCheckResult};
pub use docs_path::DocsPathFinder;
pub use error::{
    BackupError, BackupResult, DocsPathError, DocsPathResult, GamePathError, GamePathResult,
    PathError, PathResult, ValidationError, ValidationResult,
};
pub use game_path::{GamePathFinder, parse_xse_log};
pub use ini_parser::IniFile;
pub use notification_cache::{
    ensure_notification_cache_dir, ensure_notification_cache_dir_with_env, notification_cache_dir,
    notification_cache_dir_with_env,
};
pub use validator::{
    check_drive_exists,
    check_read_permissions,
    check_write_permissions,
    // Boolean convenience wrappers
    drive_exists,
    has_read_permission,
    has_write_permission,
    is_restricted_path,
    // Permission and accessibility checks
    is_valid_executable_path,
    is_valid_path,
    remove_readonly_attribute,
    validate_custom_scan_path,
    validate_is_directory,
    validate_is_file,
    validate_path_exists,
    validate_path_with_permissions,
    validate_required_files,
    validate_settings_path,
    validate_settings_paths,
};
pub use yaml_cache::{
    ensure_yaml_cache_dir, ensure_yaml_cache_dir_with_env, yaml_cache_dir, yaml_cache_dir_with_env,
};

// Re-export platform utilities
pub use platform::{get_system_documents_path, parse_steam_library};

// Re-export platform-specific Windows functions
#[cfg(target_os = "windows")]
pub use platform::{remove_readonly, windows::query_game_registry};

// Module exports (to be uncommented as modules are implemented)
// pub use game_path::GamePathFinder;
// pub use docs_path::DocumentsPathManager;
// pub use backup::BackupManager;
// pub use checker::DocumentsChecker;
