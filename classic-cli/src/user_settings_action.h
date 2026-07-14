#pragma once

#include "cli_args.h"

#include <string>

/// Persists an explicitly requested Unsolved Logs Destination through the revision-aware Rust
/// User Settings commit path. Returns false after printing a diagnostic when preview or commit
/// cannot complete; a call with no destination option is a successful no-op.
bool persist_unsolved_logs_destination_option(const CliArgs& args, const std::string& classic_root);
