#pragma once

#include "cli_args.h"
#include <string>
#include <vector>

/// Result of scanning a single crash log (C++ side mirror).
struct LogScanResult {
    std::string log_path;
    bool success = false;
    std::vector<std::string> report_lines;
    std::string error_message;
    uint64_t processing_time_ms = 0;
};

/// Orchestrates the full scan pipeline:
///   1. Find data root (YAML dirs)
///   2. Load config via Rust bridge
///   3. Create orchestrator
///   4. Discover crash logs
///   5. Scan all logs with thread pool + progress display
///   6. Write AUTOSCAN.md reports
///   7. Print summary
///
/// Returns exit code (0 = success, 1 = scan errors, 2 = fatal error).
int run_scan(const CliArgs& args);
