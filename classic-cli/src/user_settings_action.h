#pragma once

#include "cli_args.h"

#include <string>

/// Persists an explicitly requested Unsolved Logs Destination through the revision-aware Rust
/// User Settings commit path, explicitly bootstrapping Rust-owned defaults when the document is
/// missing. Returns false after printing a diagnostic when preview or commit cannot complete; a
/// call with no destination option is a successful no-op.
///
/// This is the CLI's only User Settings write. It runs before Crash Log Scan Launch, which reads
/// User Settings itself and never writes them, so the launched scan sees the saved destination.
bool persist_unsolved_logs_destination_option(const CliArgs& args, const std::string& classic_root);
