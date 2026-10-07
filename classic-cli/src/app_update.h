#pragma once

#include "cli_args.h"
#include "installation_root.h"

/// CLI handler for the app-update notification manifest check.
///
/// Dispatched from main.cpp when `--check-app-update` is supplied. It first
/// locates the Installation Root through Config's shared locator (stopping with
/// "CLASSIC Data not found" when there is none), then opens typed Update
/// Preferences from that root through
/// `classic-user-settings-core`; a disabled or untrusted preference returns
/// before runtime initialization or network access. Allowed checks call the
/// CXX notification bridge, which wraps the Pages-first + Releases-fallback
/// pipeline in `business-logic/classic-update-core::notification`. See
/// `docs/api/app-update-notification-delivery.md` for the client contract.
///
/// Returns:
///   0 = success or policy-disabled (classification `up_to_date`, `update_available`,
///       `deprecated_client`, or `not_published` — the check reached a
///       definite benign conclusion)
///   1 = inconclusive (`unknown` classification with parse error, or the
///       notification fetch failed on both Pages and Releases channels)
///   2 = fatal (no Installation Root, or runtime init failed)
int run_check_app_update(const CliArgs& args);

/// Runs the app-update check with the Installation Root search starting from `location`.
///
/// `run_check_app_update(args)` passes this process's own location; tests pass theirs.
int run_check_app_update(const CliArgs& args, const CliProcessLocation& location);
