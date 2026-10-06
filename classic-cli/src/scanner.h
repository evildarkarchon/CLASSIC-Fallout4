#pragma once

#include "cli_args.h"
#include "installation_root.h"

/// Orchestrates the full scan pipeline:
///   1. Locate the Installation Root (stops with "CLASSIC Data not found" when there is none)
///   2. Launch a Standard or Targeted request through Rust's Crash Log Scan Launch, which merges
///      the saved User Settings with this run's flags
///   3. Execute and observe the single Rust-owned Crash Log Scan Run operation
///   4. Present typed discovery, setup, cancellation, and terminal outcomes
///
/// Returns exit code (0 = success, 1 = scan errors, 2 = fatal error or no Installation Root,
/// 130 = cancelled).
int run_scan(const CliArgs& args);

/// Runs the scan pipeline with the Installation Root search starting from `location`.
///
/// `run_scan(args)` passes this process's executable folder and working directory; tests pass
/// their own so the search cannot reach where the test binary was built.
int run_scan(const CliArgs& args, const CliProcessLocation& location);
