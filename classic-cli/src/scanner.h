#pragma once

#include "cli_args.h"

/// Orchestrates the full scan pipeline:
///   1. Find data root (YAML dirs)
///   2. Project typed User Settings into a Standard or Targeted request
///   3. Execute and observe the single Rust-owned Crash Log Scan Run operation
///   4. Present typed discovery, setup, cancellation, and terminal outcomes
///
/// Returns exit code (0 = success, 1 = scan errors, 2 = fatal error, 130 = cancelled).
int run_scan(const CliArgs& args);
