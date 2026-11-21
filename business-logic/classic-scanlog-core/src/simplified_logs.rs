//! Simplified Logs: the copies Simplify Logs writes.
//!
//! Simplify Logs never rewrites a Crash Log. For each Crash Log a run analyzes
//! successfully, it writes the reformatted lines (redundant lines removed,
//! plugin load-order brackets zero-padded) to `{stem}-simple.log` in the
//! `Simplified Logs` folder of the main CLASSIC directory.
//!
//! The folder sits beside `Crash Logs/`, never inside it. Standard discovery
//! globs `Crash Logs/**/crash-*.log` and a copy's name still matches that
//! pattern, so a copy inside `Crash Logs/` would be rediscovered on the next
//! run and simplified again. For the same reason, a Targeted input or Custom
//! Scan Folder inside `Simplified Logs` is not scanned (audit S7).

use crate::error::{Result, ScanLogError};
use classic_file_io_core::FileIOCore;
use std::ffi::OsString;
use std::path::{Path, PathBuf};

/// Folder name, under the main CLASSIC directory, that holds Simplified Logs copies.
pub(crate) const SIMPLIFIED_LOGS_DIRECTORY_NAME: &str = "Simplified Logs";

/// Suffix added to a Crash Log's file stem to name its Simplified Logs copy.
const SIMPLIFIED_LOG_SUFFIX: &str = "-simple";

/// Returns the `Simplified Logs` folder for the CLASSIC installation at `installation_root`.
///
/// The path is derived only; nothing is created or checked on disk.
#[must_use]
pub fn simplified_logs_directory(installation_root: &Path) -> PathBuf {
    installation_root.join(SIMPLIFIED_LOGS_DIRECTORY_NAME)
}

/// Returns where the Simplified Logs copy of `crash_log` goes inside `directory`.
///
/// `crash-2024-06-05-08-20-22.log` becomes `crash-2024-06-05-08-20-22-simple.log`.
/// The name is built from `OsStr` parts, so a non-UTF-8 file name keeps its bytes.
#[must_use]
pub(crate) fn simplified_log_path(directory: &Path, crash_log: &Path) -> PathBuf {
    let mut file_name = crash_log
        .file_stem()
        .map(OsString::from)
        .unwrap_or_else(|| OsString::from("unknown"));
    file_name.push(SIMPLIFIED_LOG_SUFFIX);
    if let Some(extension) = crash_log.extension() {
        file_name.push(".");
        file_name.push(extension);
    }
    directory.join(file_name)
}

/// Returns the canonical `Simplified Logs` folder, or `None` when it does not exist.
///
/// Callers compare canonical paths so that letter case, `..` segments, and
/// junctions on Windows cannot make a path inside the folder look outside it.
#[must_use]
pub(crate) fn canonical_simplified_logs_directory(installation_root: &Path) -> Option<PathBuf> {
    simplified_logs_directory(installation_root)
        .canonicalize()
        .ok()
}

/// Returns whether `path` is the installation's `Simplified Logs` folder or inside it.
///
/// Both paths are canonicalized before comparison. A folder or path that does not
/// exist returns `false`: a missing folder holds no copies that could be scanned.
#[must_use]
pub fn is_inside_simplified_logs(installation_root: &Path, path: &Path) -> bool {
    let Some(directory) = canonical_simplified_logs_directory(installation_root) else {
        return false;
    };
    path.canonicalize()
        .is_ok_and(|path| path.starts_with(&directory))
}

/// Writes the Simplified Logs copy of `crash_log` into `directory` and returns its path.
///
/// Creates `directory` when it is missing and replaces an existing copy, so a
/// rescan of the same Crash Log refreshes its copy. Lines are joined with `\n`
/// and end with one trailing newline. The Crash Log itself is never opened for
/// writing.
///
/// # Errors
///
/// Returns [`ScanLogError::ReportError`] when the folder cannot be created or the
/// copy cannot be written.
pub(crate) async fn write_simplified_log(
    file_io: &FileIOCore,
    directory: &Path,
    crash_log: &Path,
    lines: &[String],
) -> Result<PathBuf> {
    tokio::fs::create_dir_all(directory)
        .await
        .map_err(|error| {
            ScanLogError::ReportError(format!(
                "Failed to create Simplified Logs folder {}: {}",
                directory.display(),
                error
            ))
        })?;

    let path = simplified_log_path(directory, crash_log);
    let mut content = lines.join("\n");
    content.push('\n');
    file_io.write_file(&path, &content).await.map_err(|error| {
        ScanLogError::ReportError(format!(
            "Failed to write simplified log {}: {}",
            path.display(),
            error
        ))
    })?;
    Ok(path)
}

#[cfg(test)]
#[path = "simplified_logs_tests.rs"]
mod tests;
