#pragma once

#include "cli_args.h"

/// CLI handler for the app-update notification manifest check.
///
/// Dispatched from main.cpp when `--check-app-update` is supplied. It first
/// opens typed Update Preferences from an explicit CLASSIC root through
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
///   2 = fatal (runtime init failed)
int run_check_app_update(const CliArgs& args);
