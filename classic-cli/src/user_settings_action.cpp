#include "user_settings_action.h"

#include "rust/cxx.h"

#include "classic_cxx_bridge/settings.h"

#include <fmt/core.h>
#include <string>

namespace {

std::string to_std_string(const rust::String& value) {
    return std::string(value.data(), value.size());
}

} // namespace

/// Delegates the whole transition to Rust; only a migration that could not run is reported.
void migrate_user_settings_silently(const std::string& classic_root) {
    const auto outcome = classic::settings::user_settings_migrate_if_required(classic_root);
    const std::string status = to_std_string(outcome.status);
    if (status == "not_required" || status == "applied") {
        return;
    }
    for (const auto& diagnostic : outcome.diagnostics) {
        fmt::print(stderr, "User Settings migration {} [{}]: {}\n", status, to_std_string(diagnostic.code),
                   to_std_string(diagnostic.message));
    }
}

/// Persists the destination only after Rust validates the request and anchors it to a revision.
bool persist_unsolved_logs_destination_option(const CliArgs& args, const std::string& classic_root) {
    if (args.unsolved_logs_destination.empty() && !args.reset_unsolved_logs_destination) {
        return true;
    }

    classic::settings::UserSettingsUpdateDto update{};
    update.has_unsolved_logs_destination = true;
    update.has_unsolved_logs_destination_value = !args.reset_unsolved_logs_destination;
    update.unsolved_logs_destination = args.unsolved_logs_destination;

    const auto current = classic::settings::user_settings_open_crash_log_scan_settings(classic_root);
    const bool bootstrap = to_std_string(current.classification) == "missing";
    const auto preview = bootstrap ? classic::settings::user_settings_preview_bootstrap(classic_root, update)
                                   : classic::settings::user_settings_preview_update(classic_root, update);
    if (!preview.accepted) {
        for (const auto& diagnostic : preview.diagnostics) {
            fmt::print(stderr, "Error: User Settings update rejected [{}] {}: {}\n", std::string(diagnostic.code),
                       std::string(diagnostic.field_path), std::string(diagnostic.message));
        }
        return false;
    }

    classic::settings::UserSettingsCommitResultDto result{};
    try {
        result = bootstrap
                     ? classic::settings::user_settings_commit_bootstrap(classic_root, preview.base_revision, update)
                     : classic::settings::user_settings_commit_update(classic_root, preview.base_revision, update);
    } catch (const rust::Error& error) {
        fmt::print(stderr, "Error: could not commit Unsolved Logs Destination: {}\n", std::string(error.what()));
        return false;
    }
    const std::string status(result.status);
    if (status == "committed") {
        return true;
    }
    if (status == "conflict") {
        fmt::print(stderr,
                   "Error: User Settings changed while the Unsolved Logs Destination update "
                   "was being committed (expected {}, found {}). Retry the command.\n",
                   std::string(result.expected_revision), std::string(result.actual_revision));
        return false;
    }
    if (status == "rejected") {
        for (const auto& diagnostic : result.diagnostics) {
            fmt::print(stderr, "Error: User Settings update rejected [{}] {}: {}\n", std::string(diagnostic.code),
                       std::string(diagnostic.field_path), std::string(diagnostic.message));
        }
        return false;
    }

    fmt::print(stderr, "Error: unexpected User Settings commit status: {}\n", status);
    return false;
}
