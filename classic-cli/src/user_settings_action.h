#pragma once

#include "cli_args.h"

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

/// Safety-adjusted User Settings facts used to build one native Crash Log Scan Run request.
///
/// The values are already typed by Rust. Relative FormID database paths remain unresolved so
/// Crash Log Scan Intake can interpret them under the YAML Data directory without exposing a
/// first-party User Settings key path to native code.
struct PreparedScanUserSettings {
    std::string game;
    std::string game_version;
    bool fcx_mode = false;
    bool show_formid_values = false;
    bool simplify_logs = false;
    bool move_unsolved_logs = false;
    std::string unsolved_logs_destination;
    std::string custom_scan_directory;
    uint32_t max_concurrent = 0;
    std::vector<std::string> formid_database_paths;
    std::string configured_documents_root;
    std::string setup_game_root;
    std::string setup_docs_root;
    std::string setup_game_exe_path;
    std::string setup_xse_log_path;
    std::string classification;
    std::string commit_eligibility;
};

/// Persists an explicitly requested Unsolved Logs Destination through the revision-aware Rust
/// User Settings commit path, explicitly bootstrapping Rust-owned defaults when the document is
/// missing. Returns false after printing a diagnostic when preview or commit cannot complete; a
/// call with no destination option is a successful no-op.
bool persist_unsolved_logs_destination_option(const CliArgs& args, const std::string& classic_root);

/// Opens typed User Settings snapshots and merges explicit CLI overrides into scan-ready facts.
///
/// An explicitly requested Unsolved Logs Destination update is previewed and committed before
/// the snapshot is opened. Returns `std::nullopt` after printing an actionable diagnostic when
/// that accepted-update workflow cannot complete; read-only degraded snapshots remain usable.
std::optional<PreparedScanUserSettings> prepare_scan_user_settings(const CliArgs& args,
                                                                   const std::string& classic_root);
