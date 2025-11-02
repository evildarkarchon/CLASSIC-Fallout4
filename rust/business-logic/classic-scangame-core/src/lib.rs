//! CLASSIC ScanGame Core - Pure Rust business logic for game scanning and validation
//!
//! This crate provides high-performance game data analysis with:
//! - Configuration duplicate detection
//! - Unpacked file scanning
//! - Log file processing
//! - INI file validation
//! - TOML configuration validation
//! - XSE plugin checking
//! - BA2 archive handling
//! - DDS texture validation
//!
//! **NO PyO3 DEPENDENCIES** - Pure Rust business logic only.
//! For Python bindings, see `classic-scangame-py`.

// Module declarations - will be implemented in Phase 3B-3C
pub mod config;      // Config.py duplicate detection (Phase 3B) - IMPLEMENTED
pub mod unpacked;    // unpacked_scanner.py (Phase 3B) - IMPLEMENTED
pub mod logs;        // log_processor.py (Phase 3C) - IMPLEMENTED
pub mod ini;         // ScanModInis.py validation (Phase 3C) - IMPLEMENTED
pub mod toml;        // CheckCrashgen.py TOML validation (Phase 3C) - IMPLEMENTED
pub mod xse;         // CheckXsePlugins.py (Phase 3C) - IMPLEMENTED
pub mod integrity;   // GameIntegrity.py validation (Phase 5) - IMPLEMENTED

pub mod ba2;         // BA2 archive handling (Phase 3B) - IMPLEMENTED
pub mod error;

// Re-export key types for convenience
pub use ba2::{BA2Error, BA2Issues, BA2Scanner};
pub use config::{ConfigDuplicateDetector, ConfigError, DuplicateGroup};
pub use error::ScanGameError;
pub use ini::{ConfigIssue, IniError, IniValidator, IssueSeverity};
pub use integrity::{
    CheckType, GameIntegrityChecker, IntegrityCheckResult, IntegrityConfig, IntegrityError,
};
pub use logs::{LogError, LogErrorEntry, LogProcessor};
pub use toml::{CrashgenChecker, TomlConfigIssue, TomlError, TomlIssueSeverity};
pub use unpacked::{UnpackedError, UnpackedIssues, UnpackedScanner};
pub use xse::{AddressLibInfo, GameVersion, ValidationResult, XseChecker, XseError};

/// Version of the classic-scangame-core crate
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
