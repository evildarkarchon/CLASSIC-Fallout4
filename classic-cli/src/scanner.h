#pragma once

#include "cli_args.h"

/// Orchestrates the full scan pipeline:
///   1. Find data root (YAML dirs)
///   2. Discover crash logs
///   3. Execute the Rust Crash Log Scan Run
///   4. Print summary
///
/// Returns exit code (0 = success, 1 = scan errors, 2 = fatal error).
int run_scan(const CliArgs& args);
