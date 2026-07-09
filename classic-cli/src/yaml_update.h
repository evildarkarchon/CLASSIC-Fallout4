#pragma once

#include "cli_args.h"

/// CLI handlers for YAML Data update actions exposed by the bridge.
///
/// The CLI dispatches to exactly one of these when `--check-yaml-updates`
/// `--apply-yaml-updates`, or `--rollback-yaml-updates` is supplied — the
/// normal scan pipeline is skipped in that case. Each handler initialises the
/// Rust runtime and returns a process exit code. Check/apply honor
/// `CLASSIC_Settings.Update Check: false`; rollback is local-only and does
/// not require network/update-check policy.
///
/// Returns:
///   0 = success (for check: status was reported; for apply: at least one
///       file was installed OR the installed data was already current; for
///       rollback: no per-file rollback failures were reported)
///   1 = failure / blocked apply (network error, settings disabled,
///       checksum mismatch, user declined, etc.)
///   2 = fatal (runtime init or settings load failed)
int run_check_yaml_updates(const CliArgs& args);
int run_apply_yaml_updates(const CliArgs& args);
int run_rollback_yaml_updates(const CliArgs& args);
