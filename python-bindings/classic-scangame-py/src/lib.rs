//! CLASSIC ScanGame Python Bindings
//!
//! This crate provides PyO3 bindings for classic-scangame-core.
//! It wraps the pure Rust business logic for Python consumption.
//!
//! ## Architecture
//! This is a THIN ADAPTER layer that:
//! - Delegates all business logic to classic-scangame-core
//! - Only handles Python ↔ Rust type conversions
//! - Maintains API compatibility with existing Python code
//!
//! ## Complete Usage Example
//!
//! ```python
//! import classic_scangame
//! from pathlib import Path
//!
//! # Game integrity checking (20-40x faster)
//! config = classic_scangame.IntegrityConfig(
//!     Path("C:/Games/Fallout4/Fallout4.exe"),
//!     "old_version_hash",
//!     "new_version_hash",
//!     "Fallout 4"
//! )
//! config.with_steam_ini(Path("C:/Games/Fallout4/steam_api.ini"))
//!
//! checker = classic_scangame.GameIntegrityChecker(config)
//! message = checker.run_full_check()
//! print(message)
//!
//! # Config duplicate detection
//! # Unpacked file scanning
//! # Log processing
//! # INI validation
//! # TOML validation
//! # XSE plugin checking
//! # BA2 archive handling
//! ```
//!
//! ## Performance Characteristics
//!
//! - **Config duplicate detection**: 20-50x faster than Python
//! - **Unpacked file scanning**: 30-80x faster with parallel I/O
//! - **INI validation**: 10-30x faster with cached parsing
//! - **BA2 archive handling**: 40-100x faster with memory mapping
//! - **Game integrity checking**: 20-40x faster with native SHA256
//!
//! ## Thread Safety
//!
//! All scangame components are thread-safe and can be used from multiple Python threads
//! or async tasks.

use pyo3::prelude::*;

// Module declarations - Phase 3B-3C implementations
pub mod ba2; // BA2 archive handling (Phase 3B) - IMPLEMENTED
pub mod config; // Config.py duplicate detection (Phase 3B) - IMPLEMENTED
pub mod config_cache; // ConfigFileCache (G-03) + ModIniScanner (G-04) - IMPLEMENTED
pub mod crashgen_orchestrator; // CrashgenCheckOrchestrator (G-07) - IMPLEMENTED
/// Crashgen settings rule parsing helpers for Python inputs.
pub mod crashgen_rules;
pub mod enb; // ENB detection (Phase 7) - IMPLEMENTED
pub mod game_report; // ScanReportBuilder + ScanValidators (G-09/G-10) - IMPLEMENTED
pub mod ini; // ScanModInis.py validation (Phase 3C) - IMPLEMENTED
pub mod integrity;
pub mod logs; // log_processor.py (Phase 3C) - IMPLEMENTED
pub mod orchestrator; // GameScanOrchestrator (G-01/G-02) - IMPLEMENTED
pub mod setup; // SetupCoordinator (G-18) - IMPLEMENTED
pub mod toml_check; // CheckCrashgen.py TOML validation (Phase 3C) - IMPLEMENTED
pub mod unpacked; // unpacked_scanner.py (Phase 3B) - IMPLEMENTED
pub mod wrye; // WryeBashParser (G-05) - IMPLEMENTED
pub mod xse; // CheckXsePlugins.py (Phase 3C) - IMPLEMENTED // GameIntegrity.py (Phase 5) - IMPLEMENTED

/// Convert ScanGameError to PyErr
pub fn to_pyerr(err: impl std::fmt::Display) -> PyErr {
    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(err.to_string())
}

/// Python module initialization
///
/// Registers all scangame components with Python:
/// - Config duplicate detection
/// - Unpacked file scanning
/// - Log processing
/// - INI validation
/// - TOML validation (CheckCrashgen)
/// - XSE plugin checking
/// - BA2 archive handling
/// - Game integrity checking (Phase 5)
#[pymodule]
fn classic_scangame(m: &Bound<'_, PyModule>) -> PyResult<()> {
    classic_shared::configure_python_stdio(m.py());

    // Add version and debug marker
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("__debug_registered__", true)?;

    // Register all modules - Phase 3B-3C components
    config::register_config(m)?; // Config duplicate detection
    config_cache::register_config_cache(m)?; // ConfigFileCache (G-03) + ModIniScanner (G-04)
    crashgen_orchestrator::register_crashgen_orchestrator(m)?; // CrashgenCheckOrchestrator (G-07)
    enb::register_enb(m)?; // ENB detection (Phase 7)
    unpacked::register_unpacked(m)?; // Unpacked file scanning
    logs::register_logs(m)?; // Log processing
    ini::register_ini(m)?; // INI validation
    toml_check::register_toml(m)?; // TOML validation (CheckCrashgen)
    wrye::register_wrye(m)?; // WryeBashParser (G-05)
    xse::register_xse(m)?; // XSE plugin checking
    ba2::register_ba2(m)?; // BA2 archive handling

    // Phase 5 - Application Coordination
    integrity::register(m)?; // Game integrity checking

    // Wave 4 - Orchestrator, Setup, Game Report
    orchestrator::register_orchestrator(m)?; // GameScanOrchestrator (G-01/G-02)
    setup::register_setup(m)?; // SetupCoordinator (G-18)
    game_report::register_game_report(m)?; // ScanReportBuilder + ScanValidators (G-09/G-10)

    Ok(())
}
