#include "user_settings_action.h"

#include "rust/cxx.h"

#include "classic_cxx_bridge/settings.h"

#include <fmt/core.h>
#include <string>
#include <unordered_set>

namespace {

std::string to_std_string(const rust::String& value) {
    return std::string(value.data(), value.size());
}

/// Reports one typed snapshot's diagnostics and state once across the settings groups opened by the CLI.
template <typename Snapshot>
void report_snapshot_diagnostics(const Snapshot& snapshot, std::unordered_set<std::string>& reported) {
    for (const auto& diagnostic : snapshot.diagnostics) {
        const std::string code = to_std_string(diagnostic.code);
        const std::string message = to_std_string(diagnostic.message);
        if (reported.insert("diagnostic\x1f" + code + "\x1f" + message).second) {
            fmt::print(stderr, "User Settings warning [{}]: {}\n", code, message);
        }
    }

    const std::string eligibility = to_std_string(snapshot.commit_eligibility);
    const std::string classification = to_std_string(snapshot.classification);
    if (!reported.insert("state\x1f" + eligibility + "\x1f" + classification).second) {
        return;
    }
    if (eligibility == "requires_migration") {
        fmt::print(stderr,
                   "User Settings notice: this {} document must be explicitly migrated before "
                   "CLI settings updates can be committed. Read-only scans will use its typed snapshot.\n",
                   classification);
    } else if (eligibility == "blocked_untrusted") {
        fmt::print(stderr,
                   "User Settings warning: this {} document is not trusted for updates. "
                   "Correct the diagnostics above; read-only scans will use safety-adjusted values.\n",
                   classification);
    }
}

/// Reports both typed scan/setup snapshots while suppressing their shared document diagnostics.
void report_open_diagnostics(const classic::settings::CrashLogScanSettingsDto& scan,
                             const classic::settings::GameSetupSettingsDto& setup) {
    std::unordered_set<std::string> reported;
    report_snapshot_diagnostics(scan, reported);
    report_snapshot_diagnostics(setup, reported);
}

} // namespace

/// Persists the destination only after Rust validates the request and anchors it to a revision.
bool persist_unsolved_logs_destination_option(const CliArgs& args, const std::string& classic_root) {
    if (args.unsolved_logs_destination.empty() && !args.reset_unsolved_logs_destination) {
        return true;
    }

    classic::settings::UserSettingsUpdateDto update{};
    update.has_unsolved_logs_destination = true;
    update.has_unsolved_logs_destination_value = !args.reset_unsolved_logs_destination;
    update.unsolved_logs_destination = args.unsolved_logs_destination;

    const auto preview = classic::settings::user_settings_preview_update(classic_root, update);
    if (!preview.accepted) {
        for (const auto& diagnostic : preview.diagnostics) {
            fmt::print(stderr, "Error: User Settings update rejected [{}] {}: {}\n", std::string(diagnostic.code),
                       std::string(diagnostic.field_path), std::string(diagnostic.message));
        }
        return false;
    }

    classic::settings::UserSettingsCommitResultDto result{};
    try {
        result = classic::settings::user_settings_commit_update(classic_root, preview.base_revision, update);
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

std::optional<PreparedScanUserSettings> prepare_scan_user_settings(const CliArgs& args,
                                                                   const std::string& classic_root) {
    if (!persist_unsolved_logs_destination_option(args, classic_root)) {
        return std::nullopt;
    }

    const auto scan = classic::settings::user_settings_open_crash_log_scan_settings(classic_root);
    const auto setup = classic::settings::user_settings_open_game_setup_settings(classic_root);
    report_open_diagnostics(scan, setup);

    PreparedScanUserSettings prepared{};
    const std::string managed_game = to_std_string(setup.managed_game);
    prepared.game = args.game_was_explicit ? args.game : managed_game;
    const bool uses_managed_game = prepared.game == managed_game;
    prepared.game_version = args.game_version_was_explicit
                                ? args.game_version
                                : (uses_managed_game ? to_std_string(scan.game_version_selection) : "auto");
    prepared.fcx_mode = scan.fcx_mode || args.fcx_mode;
    prepared.show_formid_values = scan.formid_value_lookup || args.show_fid_values;
    prepared.simplify_logs = scan.simplify_logs || args.simplify_logs;
    prepared.move_unsolved_logs = scan.move_unsolved_logs;
    if (scan.has_unsolved_logs_destination) {
        prepared.unsolved_logs_destination = to_std_string(scan.unsolved_logs_destination);
    }
    prepared.custom_scan_directory =
        !args.scan_path.empty()
            ? args.scan_path
            : (uses_managed_game && scan.has_custom_scan_input ? to_std_string(scan.custom_scan_input)
                                                               : std::string{});
    prepared.max_concurrent =
        args.max_concurrent_was_explicit ? args.max_concurrent : scan.max_concurrent_scans;

    for (const auto& row : scan.formid_database_paths) {
        if (to_std_string(row.game) == prepared.game) {
            prepared.formid_database_paths.push_back(to_std_string(row.path));
        }
    }

    // Setup paths belong to the managed game. A cross-game CLI override must fall
    // back to Rust discovery instead of feeding paths for a different installation.
    if (uses_managed_game) {
        if (setup.has_documents_root) {
            prepared.configured_documents_root = to_std_string(setup.documents_root);
            prepared.setup_docs_root = prepared.configured_documents_root;
        }
        if (setup.has_game_root) {
            prepared.setup_game_root = to_std_string(setup.game_root);
        }
        if (setup.has_game_executable) {
            prepared.setup_game_exe_path = to_std_string(setup.game_executable);
        }
    }
    prepared.classification = to_std_string(scan.classification);
    prepared.commit_eligibility = to_std_string(scan.commit_eligibility);
    return prepared;
}
