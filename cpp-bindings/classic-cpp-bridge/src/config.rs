//! Configuration bridge for CXX FFI.
//!
//! Exposes the two `classic_config_core` entry points the CLI and GUI call:
//! Installation Root discovery and Game Local YAML path persistence. YAML Data
//! loading stays Rust-only behind the scan-run and settings surfaces.

use classic_config_core::{
    locate_installation_root as core_locate_installation_root, persist_game_local_paths,
};
use classic_shared_core::get_runtime;
use std::path::Path;

/// Locate the Installation Root through config's one shared candidate search.
///
/// An empty `executable_dir` or `working_dir` means that input is unavailable and
/// skips only the candidates derived from it. Returns the matching root verbatim
/// (built from the caller's input), or an empty string when no candidate holds
/// `CLASSIC Data`; the caller owns its "CLASSIC Data not found" message.
fn locate_installation_root(executable_dir: &str, working_dir: &str) -> String {
    // CXX strings cannot express an optional borrowed path, so an empty string is "absent".
    let executable_dir = (!executable_dir.is_empty()).then(|| Path::new(executable_dir));
    let working_dir = (!working_dir.is_empty()).then(|| Path::new(working_dir));
    core_locate_installation_root(executable_dir, working_dir)
        .map(|root| root.to_string_lossy().into_owned())
        .unwrap_or_default()
}

/// Persist optional game and documents paths through the standalone Game Local writer.
///
/// Empty path strings mean "leave this key unchanged". Failures are returned as
/// strings for the existing CXX `Result` contract.
fn save_local_yaml_paths(
    local_yaml_path: &str,
    game_root: &str,
    docs_root: &str,
) -> Result<(), String> {
    // CXX strings cannot express optional borrowed paths, so empty values retain
    // the established adapter meaning of "do not update this field".
    let game_root = (!game_root.is_empty()).then(|| Path::new(game_root));
    let docs_root = (!docs_root.is_empty()).then(|| Path::new(docs_root));

    get_runtime()
        .block_on(persist_game_local_paths(
            Path::new(local_yaml_path),
            game_root,
            docs_root,
        ))
        .map_err(|e| format!("{e}"))
}

#[cxx::bridge(namespace = "classic::config")]
mod ffi {
    extern "Rust" {
        fn save_local_yaml_paths(
            local_yaml_path: &str,
            game_root: &str,
            docs_root: &str,
        ) -> Result<()>;

        /// Installation Root from the executable folder and working
        /// directory: the first of the six documented candidates that
        /// holds `CLASSIC Data`. Empty input = that input is unavailable;
        /// empty result = no Installation Root (no fallback).
        fn locate_installation_root(executable_dir: &str, working_dir: &str) -> String;
    }
}

#[cfg(test)]
#[path = "config_tests.rs"]
mod tests;
