//! File logging infrastructure for the GUI application.
//!
//! When distributed as a Windows subsystem application (`windows_subsystem = "windows"`),
//! stderr is not available. This module sets up file-based logging via `tracing-appender`
//! so that all `tracing::warn!`, `tracing::error!`, etc. output is captured to a log file
//! in the user's data directory.
//!
//! The log file is overwritten on each launch (not appended) to keep it small and relevant
//! to the most recent session only.

use std::fs;

use directories::ProjectDirs;
use tracing_appender::non_blocking::WorkerGuard;

/// Initialize file logging and return the [`WorkerGuard`] that keeps the writer alive.
///
/// The log file is written to the platform-specific data directory:
/// - **Windows:** `%APPDATA%\classic\classic-gui\data\classic-gui.log`
/// - **Linux:** `~/.local/share/classic-gui/classic-gui.log`
/// - **macOS:** `~/Library/Application Support/com.classic.classic-gui/classic-gui.log`
///
/// If the data directory cannot be determined, falls back to the current working directory.
///
/// # Important
///
/// The returned [`WorkerGuard`] **must** be held for the entire application lifetime.
/// Dropping the guard will flush remaining log entries and stop the background writer.
/// Assign it to a variable in `main()` that lives until the end of the function:
///
/// ```rust,ignore
/// fn main() {
///     let _log_guard = init_logging();
///     // ... rest of application ...
///     // _log_guard is dropped here, flushing final logs
/// }
/// ```
pub fn init_logging() -> WorkerGuard {
    // Determine log directory: prefer user data dir, fall back to cwd
    let log_dir = ProjectDirs::from("com", "classic", "classic-gui")
        .map(|dirs| dirs.data_dir().to_path_buf())
        .unwrap_or_else(|| std::env::current_dir().unwrap_or_default());

    // Ensure log directory exists
    let _ = fs::create_dir_all(&log_dir);

    // Truncate the log file so each launch starts fresh
    let log_file_path = log_dir.join("classic-gui.log");
    let _ = fs::File::create(&log_file_path);

    // Set up non-rotating file appender (always writes to the same file)
    let file_appender = tracing_appender::rolling::never(&log_dir, "classic-gui.log");
    let (non_blocking, guard) = tracing_appender::non_blocking(file_appender);

    // Initialize the global tracing subscriber
    tracing_subscriber::fmt()
        .with_writer(non_blocking)
        .with_ansi(false)
        .with_target(true)
        .with_level(true)
        .init();

    guard
}
