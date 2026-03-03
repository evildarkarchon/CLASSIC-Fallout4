#pragma once

#include <cstdint>
#include <string>

/// Parsed CLI arguments, mirroring Python's CLASSIC_ScanLogs.py argparse.
struct CliArgs {
    std::string game = "Fallout4";
    std::string game_version = "auto";
    bool fcx_mode = false;
    bool show_fid_values = false;
    bool simplify_logs = false;
    std::string scan_path;          // Empty = auto-detect
    uint32_t max_concurrent = 0;    // 0 = auto (cpu_count - 2, min 2)
    bool version_flag = false;
};

/// Parse command-line arguments using CLI11.
/// Exits the process on --help or parse error.
CliArgs parse_args(int argc, char* argv[]);
