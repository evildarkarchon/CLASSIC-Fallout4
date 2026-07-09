#pragma once

#include <cstdint>
#include <string>
#include <vector>

/// Parsed CLI arguments, mirroring Python's CLASSIC_ScanLogs.py argparse.
struct CliArgs {
    std::string game = "Fallout4";
    std::string game_version = "auto";
    bool fcx_mode = false;
    bool show_fid_values = false;
    bool simplify_logs = false;
    std::string scan_path;                 // Empty = auto-detect
    std::string unsolved_logs_destination; // Empty = use configured/canonical destination
    uint32_t max_concurrent = 0;           // 0 = auto (cpu_count - 2, min 2, max 32)
    bool version_flag = false;
    bool reset_unsolved_logs_destination = false;
    std::vector<std::string> input_paths; // Explicit crash-log files or directories

    // yaml-update-delivery (Section 12.3): data-file update flags. Each is a
    // standalone action; if set, the CLI short-circuits the normal scan
    // pipeline and dispatches to the YAML update handler instead.
    bool check_yaml_updates = false;
    bool apply_yaml_updates = false;
    bool rollback_yaml_updates = false;

    // app-update-manifest-notification: binary-release notification check
    // via the Pages-first notification manifest. Short-circuits the scan
    // pipeline like the yaml-update flags.
    bool check_app_update = false;
};

uint32_t auto_concurrency_for_cpu_count(uint32_t cpu_count);
uint32_t effective_concurrency(uint32_t requested, uint32_t cpu_count);

/// Parse command-line arguments using CLI11.
/// Exits the process on --help or parse error.
CliArgs parse_args(int argc, char* argv[]);
