#pragma once

#include "cli_args.h"

/// CLI handler for the app-update notification manifest check.
///
/// Dispatched from main.cpp when `--check-app-update` is supplied. Calls the
/// CXX bridge entry point `classic::update::check_app_notification`, which
/// wraps the Pages-first + Releases-fallback notification pipeline in
/// `business-logic/classic-update-core::notification`. See
/// `docs/api/app-update-notification-delivery.md` for the client contract.
///
/// Returns:
///   0 = success (classification `up_to_date`, `update_available`,
///       `deprecated_client`, or `not_published` — the check reached a
///       definite benign conclusion)
///   1 = inconclusive (`unknown` classification with parse error, or the
///       notification fetch failed on both Pages and Releases channels)
///   2 = fatal (runtime init failed)
int run_check_app_update(const CliArgs& args);
