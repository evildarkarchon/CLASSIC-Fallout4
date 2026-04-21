#pragma once

#include "cli_args.h"

/// yaml-update-delivery Section 12.3: CLI handlers for the three bridge
/// entry points exposed by the yaml-update-delivery change.
///
/// The CLI dispatches to exactly one of these when `--check-yaml-updates`
/// or `--apply-yaml-updates` is supplied — the normal scan pipeline is
/// skipped in that case. Each handler initialises the Rust runtime, honors
/// `CLASSIC_Settings.Update Check: false` via the bridge's built-in
/// short-circuit, and returns a process exit code.
///
/// Returns:
///   0 = success (for check: status was reported; for apply: at least one
///       file was installed OR the installed data was already current)
///   1 = failure / blocked apply (network error, settings disabled,
///       checksum mismatch, user declined, etc.)
///   2 = fatal (runtime init or settings load failed)
int run_check_yaml_updates(const CliArgs& args);
int run_apply_yaml_updates(const CliArgs& args);
