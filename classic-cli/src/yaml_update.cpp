#include "yaml_update.h"

#include "rust/cxx.h"

#include "classic_cxx_bridge/message.h"
#include "classic_cxx_bridge/runtime.h"
#include "classic_cxx_bridge/settings.h"
#include "classic_cxx_bridge/update.h"

#include <fmt/core.h>

#include <cstdint>
#include <iostream>
#include <string>

// ── Constants ─────────────────────────────────────────────────────────
//
// Channel coordinates, accepted schema ranges, and the shippable file set
// are owned by the first-party YAML Data Update Channel in Rust. The CLI
// keeps only bridge DTO discriminator constants for user-facing reporting.

namespace {

// Tag discriminator constants — mirror `TAG_*` in
// `cpp-bindings/classic-cpp-bridge/src/update.rs`.
constexpr std::uint32_t kYamlTagDisabled = 0u;
constexpr std::uint32_t kYamlTagUpdateAvailable = 1u;
constexpr std::uint32_t kYamlTagUpToDate = 2u;
constexpr std::uint32_t kYamlTagUnknown = 3u;
constexpr std::uint32_t kYamlTagError = 4u;

/// Opens the typed update-policy snapshot and surfaces any read or migration diagnostics.
bool read_update_check_setting(const std::string& classic_root) {
    const auto preferences = classic::settings::user_settings_open_update_preferences(classic_root);
    for (const auto& diagnostic : preferences.diagnostics) {
        fmt::print(stderr, "User Settings warning [{}]: {}\n", std::string(diagnostic.code),
                   std::string(diagnostic.message));
    }
    if (std::string(preferences.commit_eligibility) == "requires_migration") {
        fmt::print(stderr,
                   "User Settings notice: this {} document must be explicitly migrated before "
                   "updates can be committed; the YAML Data command is using its typed read-only policy.\n",
                   std::string(preferences.classification));
    }
    return preferences.update_check_enabled;
}

// ── Runtime bootstrap ─────────────────────────────────────────────────
//
// Smaller than `run_scan`'s bootstrap: we don't need the registry wiring or
// log-startup framing — the YAML update flow doesn't touch per-game state.

bool init_runtime_for_yaml_update() {
    try {
        classic::message::init_logging();
        classic::runtime::init_runtime();
        return true;
    } catch (const rust::Error& e) {
        fmt::print(stderr, "Fatal: failed to initialize runtime: {}\n", std::string(e.what()));
        return false;
    }
}

// ── Status formatting ─────────────────────────────────────────────────

int report_status(const classic::update::YamlUpdateStatusDto& status) {
    switch (status.tag) {
    case kYamlTagDisabled:
        fmt::print("Data update check is disabled by User Settings.\n"
                   "Enable the Update Check preference to receive data updates.\n");
        return 0;
    case kYamlTagUpdateAvailable: {
        fmt::print("Data update available in release {}.\n", std::string(status.release_tag));
        fmt::print("Compatible files:\n");
        for (std::size_t i = 0; i < status.compatible_files.size(); ++i) {
            const auto& f = status.compatible_files[i];
            fmt::print("  - {} ({} bytes, schema {})\n", std::string(f.name), f.size_bytes,
                       std::string(f.schema_version));
        }
        if (!status.incompatible_files.empty()) {
            fmt::print("Incompatible files (skipped):\n");
            for (std::size_t i = 0; i < status.incompatible_files.size(); ++i) {
                const auto& f = status.incompatible_files[i];
                const std::string reason = (i < status.incompatible_reasons.size())
                                               ? std::string(status.incompatible_reasons[i])
                                               : std::string("(no reason reported)");
                fmt::print("  - {} ({})\n", std::string(f.name), reason);
            }
        }
        return 0;
    }
    case kYamlTagUpToDate:
        // Distinguish genuinely-in-sync from "newer feed exists but this
        // build cannot install any of it". The core status model carries
        // rejected files on UpToDate so the user can be told that a
        // CLASSIC upgrade (not a data refresh) is what unlocks the newer
        // data.
        if (status.incompatible_files.empty()) {
            fmt::print("Your data files are up to date (release {}).\n", std::string(status.release_tag));
        } else {
            fmt::print("Your installed data files are current, but release {} advertises "
                       "{} file(s) this CLASSIC build cannot install. Upgrade CLASSIC to "
                       "consume the newer data.\n",
                       std::string(status.release_tag), status.incompatible_files.size());
            fmt::print("Incompatible files (skipped):\n");
            for (std::size_t i = 0; i < status.incompatible_files.size(); ++i) {
                const auto& f = status.incompatible_files[i];
                const std::string reason = (i < status.incompatible_reasons.size())
                                               ? std::string(status.incompatible_reasons[i])
                                               : std::string("(no reason reported)");
                fmt::print("  - {} ({})\n", std::string(f.name), reason);
            }
        }
        return 0;
    case kYamlTagUnknown:
        fmt::print("Data update status unknown: {}\n", std::string(status.unknown_reason));
        return 1;
    case kYamlTagError:
        fmt::print(stderr, "Data update check failed: {}\n", std::string(status.error_message));
        return 1;
    default:
        fmt::print(stderr, "Data update check returned an unrecognised status (tag={}).\n", status.tag);
        return 1;
    }
}

int report_rollback(const classic::update::YamlRollbackReportDto& report) {
    for (const auto& file_name : report.rolled_back) {
        fmt::print("Rolled back: {}\n", std::string(file_name));
    }
    for (const auto& file_name : report.no_previous_version) {
        fmt::print("No previous version: {}\n", std::string(file_name));
    }
    for (std::size_t i = 0; i < report.failed_files.size(); ++i) {
        const std::string file_name = std::string(report.failed_files[i]);
        const std::string reason =
            i < report.failure_reasons.size() ? std::string(report.failure_reasons[i]) : std::string("unknown error");
        fmt::print(stderr, "Failed rollback: {} ({})\n", file_name, reason);
    }

    fmt::print("\nRollback Complete\n");
    fmt::print("  Restored:            {}\n", report.rolled_back.size());
    fmt::print("  No previous version: {}\n", report.no_previous_version.size());
    fmt::print("  Failed:              {}\n", report.failed_files.size());

    return report.failed_files.empty() ? 0 : 1;
}

// ── User prompt (interactive apply) ───────────────────────────────────

bool confirm_apply_prompt() {
    std::cout << "Apply these updates? [y/N]: " << std::flush;
    std::string answer;
    if (!std::getline(std::cin, answer)) {
        return false;
    }
    return !answer.empty() && (answer[0] == 'y' || answer[0] == 'Y');
}

} // namespace

// ── Public entry points ───────────────────────────────────────────────

int run_check_yaml_updates(const CliArgs& args) {
    return run_check_yaml_updates(args, current_cli_process_location());
}

int run_check_yaml_updates(const CliArgs& /*args*/, const CliProcessLocation& location) {
    // Locate first: with no Installation Root there are no User Settings to read and no installed
    // YAML Data to compare, so the command stops before the runtime or network is touched. The
    // old private search fell back to the working directory and read typed defaults there.
    const auto installation_root = require_cli_installation_root(location);
    if (!installation_root) {
        return kCliInstallationRootNotFoundExitCode;
    }

    if (!init_runtime_for_yaml_update()) {
        return 2;
    }

    const bool enabled = read_update_check_setting(*installation_root);

    int exit_code;
    try {
        auto status = classic::update::yaml_data_check_update(enabled);
        exit_code = report_status(status);
    } catch (const rust::Error& e) {
        fmt::print(stderr, "Data update check failed: {}\n", std::string(e.what()));
        exit_code = 1;
    } catch (const std::exception& e) {
        fmt::print(stderr, "Data update check failed: {}\n", e.what());
        exit_code = 1;
    }

    classic::runtime::shutdown_runtime();
    return exit_code;
}

int run_apply_yaml_updates(const CliArgs& args) {
    return run_apply_yaml_updates(args, current_cli_process_location());
}

int run_apply_yaml_updates(const CliArgs& /*args*/, const CliProcessLocation& location) {
    // Same ordering as the check: no Installation Root, no runtime, no download, no install.
    const auto installation_root = require_cli_installation_root(location);
    if (!installation_root) {
        return kCliInstallationRootNotFoundExitCode;
    }

    if (!init_runtime_for_yaml_update()) {
        return 2;
    }

    const bool enabled = read_update_check_setting(*installation_root);

    int exit_code = 0;
    try {
        // Step 1: check (gated by enabled). Rust owns the first-party
        // channel recipe and installed-file enrichment.
        auto status = classic::update::yaml_data_check_update(enabled);
        const int status_exit_code = report_status(status);

        if (status.tag != kYamlTagUpdateAvailable) {
            // A blocked or failed apply must surface as a failing exit code so
            // scripts can distinguish "already current" from "apply was not
            // allowed / could not proceed".
            classic::runtime::shutdown_runtime();
            return (status.tag == kYamlTagDisabled) ? 1 : status_exit_code;
        }

        // Step 2: confirm with the user.
        if (!confirm_apply_prompt()) {
            fmt::print("Apply cancelled.\n");
            classic::runtime::shutdown_runtime();
            return 1;
        }

        // Step 3: apply the reviewed decision.
        //
        // We pass the exact release_tag + per-file `(name, sha256)` pairs the
        // user just confirmed via `report_status`. The bridge re-checks that
        // identity against the live manifest and refuses to install if the
        // publisher rotated to a different release or replaced an approved
        // asset in place.
        rust::Vec<rust::String> approved_file_names;
        rust::Vec<rust::String> approved_file_sha256;
        approved_file_names.reserve(status.compatible_files.size());
        approved_file_sha256.reserve(status.compatible_files.size());
        for (const auto& f : status.compatible_files) {
            approved_file_names.push_back(f.name);
            approved_file_sha256.push_back(f.sha256);
        }

        classic::update::ApprovedUpdateDto approved{};
        approved.release_tag = status.release_tag;
        approved.file_names = std::move(approved_file_names);
        approved.file_sha256 = std::move(approved_file_sha256);

        auto report = classic::update::yaml_data_apply_update(enabled, approved);

        const auto installed = report.installed.size();
        const auto failed = report.failed.size();

        for (std::size_t i = 0; i < installed; ++i) {
            const auto& f = report.installed[i];
            fmt::print("Installed: {} (schema {}{})\n", std::string(f.name), std::string(f.schema_version),
                       f.created_prev ? ", previous version retained" : "");
        }
        for (std::size_t i = 0; i < failed; ++i) {
            const auto& f = report.failed[i];
            fmt::print(stderr, "Failed: {} ({})\n", std::string(f.name), std::string(f.failure_reason));
        }

        if (!std::string(report.error_message).empty()) {
            fmt::print(stderr, "Apply reported error: {}\n", std::string(report.error_message));
        }

        fmt::print("\nApply Complete\n");
        fmt::print("  Installed: {}\n", installed);
        fmt::print("  Failed:    {}\n", failed);

        exit_code = (failed == 0u && installed > 0u) ? 0 : 1;
    } catch (const rust::Error& e) {
        fmt::print(stderr, "Apply failed: {}\n", std::string(e.what()));
        exit_code = 1;
    } catch (const std::exception& e) {
        fmt::print(stderr, "Apply failed: {}\n", e.what());
        exit_code = 1;
    }

    classic::runtime::shutdown_runtime();
    return exit_code;
}

int run_rollback_yaml_updates(const CliArgs& /*args*/) {
    if (!init_runtime_for_yaml_update()) {
        return 2;
    }

    int exit_code = 0;
    try {
        auto report = classic::update::yaml_data_rollback_update();
        exit_code = report_rollback(report);
    } catch (const rust::Error& e) {
        fmt::print(stderr, "Rollback failed: {}\n", std::string(e.what()));
        exit_code = 1;
    } catch (const std::exception& e) {
        fmt::print(stderr, "Rollback failed: {}\n", e.what());
        exit_code = 1;
    }

    classic::runtime::shutdown_runtime();
    return exit_code;
}
