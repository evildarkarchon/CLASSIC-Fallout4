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
pub mod config; // Config.py duplicate detection (Phase 3B) - IMPLEMENTED
pub mod enb; // ENB detection (Phase 7) - IMPLEMENTED
pub mod ini; // ScanModInis.py validation (Phase 3C) - IMPLEMENTED
pub mod integrity;
pub mod logs; // log_processor.py (Phase 3C) - IMPLEMENTED
pub mod toml; // CheckCrashgen.py TOML validation (Phase 3C) - IMPLEMENTED
pub mod unpacked; // unpacked_scanner.py (Phase 3B) - IMPLEMENTED
pub mod xse; // CheckXsePlugins.py (Phase 3C) - IMPLEMENTED // GameIntegrity.py validation (Phase 5) - IMPLEMENTED

pub mod ba2; // BA2 archive handling (Phase 3B) - IMPLEMENTED
pub mod config_cache; // ConfigFileCache with encoding detection (G-03) - IMPLEMENTED
pub mod crashgen_orchestrator; // CrashgenCheckOrchestrator (G-07) - IMPLEMENTED
pub mod error;
pub mod game_report; // ScanReportBuilder + ScanValidators (G-09/G-10) - IMPLEMENTED
pub mod mod_ini; // ModIniScanner orchestrator (G-04) - IMPLEMENTED
pub mod orchestrator; // GameScanOrchestrator (G-01/G-02) - IMPLEMENTED
pub mod setup; // SetupCoordinator orchestration (G-18) - IMPLEMENTED
pub mod wrye; // WryeBashParser (G-05) - IMPLEMENTED

// Re-export key types for convenience
pub use ba2::{BA2Error, BA2Issues, BA2Scanner};
pub use config::{ConfigDuplicateDetector, ConfigError, DuplicateGroup};
pub use config_cache::{CachedConfigFile, ConfigCacheError, ConfigFileCache};
pub use crashgen_orchestrator::{
    CrashgenCheckOrchestrator, CrashgenOrchestratorError, CrashgenReport,
};
pub use enb::{EnbChecker, EnbConfigResult, EnbError, EnbResult, EnbValidationResult};
pub use error::ScanGameError;
pub use game_report::{ScanReportBuilder, ScanValidators};
pub use ini::{ConfigIssue, IniError, IniValidator, IssueSeverity};
pub use integrity::{
    CheckType, GameIntegrityChecker, IntegrityCheckResult, IntegrityConfig, IntegrityError,
};
pub use logs::{LogError, LogErrorEntry, LogProcessor};
pub use mod_ini::{DuplicateEntry, ModIniScanResult, ModIniScanner, VsyncEntry};
pub use orchestrator::{
    CheckResult, GameScanConfig, GameScanOrchestrator, GameScanResult, ModScanResult,
    OrchestratorError,
};
pub use setup::{
    SetupCheckConfig, SetupCheckResults, SetupError, SetupResult, get_config_suffix,
    migrate_vr_setting, needs_path_detection, resolve_effective_game_version, run_combined_checks,
};
pub use toml::{CrashgenChecker, TomlConfigIssue, TomlError, TomlIssueSeverity};
pub use unpacked::{UnpackedError, UnpackedIssues, UnpackedScanner};
pub use wrye::{WryeBashParser, WryeError, WryeIssue, WryeSeverity};
pub use xse::{AddressLibInfo, GameVersion, ValidationResult, XseChecker, XseError};

/// Version of the classic-scangame-core crate
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
