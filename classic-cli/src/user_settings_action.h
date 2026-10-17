#pragma once

#include "cli_args.h"

#include <string>

/// Silently applies a required User Settings migration at `classic_root`, through the Rust core.
///
/// Every command that resolves an Installation Root calls this before it first opens User
/// Settings. Success and no-op print nothing; a migration that cannot run prints its diagnostics
/// to stderr and leaves the document read-only, and the command continues regardless.
void migrate_user_settings_silently(const std::string& classic_root);

/// Persists an explicitly requested Unsolved Logs Destination through the revision-aware Rust
/// User Settings commit path, explicitly bootstrapping Rust-owned defaults when the document is
/// missing. Returns false after printing a diagnostic when preview or commit cannot complete; a
/// call with no destination option is a successful no-op.
///
/// Apart from the silent startup migration, this is the CLI's only User Settings write. It runs
/// before Crash Log Scan Launch, which reads User Settings itself and never writes them, so the
/// launched scan sees the saved destination.
bool persist_unsolved_logs_destination_option(const CliArgs& args, const std::string& classic_root);
