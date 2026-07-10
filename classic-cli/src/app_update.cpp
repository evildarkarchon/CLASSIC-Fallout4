#include "app_update.h"

#include "rust/cxx.h"

#include "classic_cxx_bridge/message.h"
#include "classic_cxx_bridge/runtime.h"
#include "classic_cxx_bridge/settings.h"
#include "classic_cxx_bridge/update.h"

#include <fmt/core.h>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

#include <filesystem>
#include <optional>
#include <string>

namespace fs = std::filesystem;

namespace {

// ── Classification discriminator labels ──────────────────────────────
//
// Keep in sync with `CLASSIFICATION_*` constants in
// `cpp-bindings/classic-cpp-bridge/src/update.rs`. Comparing against the
// literal label rather than a numeric tag keeps the C++ side robust to
// future additions — any unrecognised string falls through to the
// default "unknown status" branch.

constexpr const char* kClassificationUpToDate = "up_to_date";
constexpr const char* kClassificationUpdateAvailable = "update_available";
constexpr const char* kClassificationDeprecated = "deprecated_client";
constexpr const char* kClassificationUnknown = "unknown";
constexpr const char* kClassificationNotPublished = "not_published";
constexpr const char* kClassificationError = "error";

/// Resolve the install root without interpreting User Settings in C++.
///
/// The selected path is passed explicitly to the Rust-owned User Settings module.
std::optional<fs::path> resolve_classic_root() {
    std::error_code ec;

#ifdef _WIN32
    wchar_t buffer[MAX_PATH];
    const DWORD length = GetModuleFileNameW(nullptr, buffer, MAX_PATH);
    if (length > 0 && length < MAX_PATH) {
        const fs::path executable_root = fs::path(buffer).parent_path();
        if (fs::is_directory(executable_root / "CLASSIC Data", ec)) {
            return executable_root;
        }
        ec.clear();
    }
#endif

    const fs::path current_root = fs::current_path(ec);
    if (ec) {
        return std::nullopt;
    }
    if (fs::is_directory(current_root / "CLASSIC Data", ec)) {
        return current_root;
    }
    return std::nullopt;
}

/// Open the typed Rust group and enforce its already safety-adjusted policy.
///
/// Returns `false` before the runtime, cache, or network notification pipeline
/// is touched when Rust disables the check or applies a degraded fallback.
bool update_check_enabled_for_root(const fs::path& classic_root) {
    const std::string root = classic_root.string();
    const auto preferences =
        classic::settings::user_settings_open_update_preferences(root);

    for (const auto& diagnostic : preferences.diagnostics) {
        fmt::print(
            stderr,
            "User Settings warning [{}]: {}\n",
            std::string(diagnostic.code),
            std::string(diagnostic.message));
    }

    if (!preferences.update_check_enabled) {
        fmt::print(
            "App update check is disabled by User Settings "
            "(source={}, classification={}, origin={}).\n",
            std::string(preferences.source_location), std::string(preferences.classification),
            std::string(preferences.update_check_origin));
        return false;
    }

    return true;
}

bool is_classification(const rust::String& classification, const char* expected) {
    return std::string(classification) == expected;
}

// Convert an empty-string sentinel DTO field to a human-readable fallback.
// Empty-string sentinels on `NotificationStatusDto` indicate an absent
// manifest field per `docs/api/error-contract.md`.
std::string or_unknown(const rust::String& value) {
    const std::string s(value);
    return s.empty() ? std::string("unknown") : s;
}

int report_notification(const classic::update::NotificationStatusDto& status) {
    if (is_classification(status.classification, kClassificationUpToDate)) {
        fmt::print("You are up to date (latest v{}, published {}).\n", std::string(status.latest_version),
                   or_unknown(status.published_at));
        return 0;
    }

    if (is_classification(status.classification, kClassificationUpdateAvailable)) {
        fmt::print("Update available: v{} (published {}).\n", std::string(status.latest_version),
                   or_unknown(status.published_at));
        // Optional display payload — present only when the publisher
        // attached a `display` block. Empty-string sentinels on every
        // display_* field mean the source manifest had no display object.
        const std::string title(status.display_title);
        const std::string body(status.display_body);
        const std::string cta(status.display_cta_url);
        if (!title.empty()) {
            fmt::print("{}\n", title);
        }
        if (!body.empty()) {
            fmt::print("{}\n", body);
        }
        if (!cta.empty()) {
            fmt::print("See: {}\n", cta);
        }
        return 0;
    }

    if (is_classification(status.classification, kClassificationDeprecated)) {
        fmt::print("Your CLASSIC build is deprecated.\n"
                   "  minimum supported: v{}\n"
                   "  latest:            v{} (published {})\n"
                   "Upgrade to the latest release to continue receiving support.\n",
                   or_unknown(status.min_supported_version), std::string(status.latest_version),
                   or_unknown(status.published_at));
        return 0;
    }

    if (is_classification(status.classification, kClassificationUnknown)) {
        const std::string parse_error(status.parse_error);
        if (!parse_error.empty()) {
            fmt::print(stderr, "Update check inconclusive: {}\n", parse_error);
        } else {
            fmt::print(stderr, "Update check inconclusive (unknown classification).\n");
        }
        return 1;
    }

    if (is_classification(status.classification, kClassificationNotPublished)) {
        fmt::print("No update information is currently published.\n");
        return 0;
    }

    if (is_classification(status.classification, kClassificationError)) {
        const std::string error_message(status.error_message);
        fmt::print(stderr, "Update check failed: {}\n",
                   error_message.empty() ? std::string("unknown error") : error_message);
        return 1;
    }

    fmt::print(stderr, "Update check returned an unrecognised classification: {}\n",
               std::string(status.classification));
    return 1;
}

bool init_runtime_for_app_update() {
    try {
        classic::message::init_logging();
        classic::runtime::init_runtime();
        return true;
    } catch (const rust::Error& e) {
        fmt::print(stderr, "Fatal: failed to initialize runtime: {}\n", std::string(e.what()));
        return false;
    }
}

} // namespace

int run_check_app_update(const CliArgs& /*args*/) {
    const auto classic_root = resolve_classic_root();
    if (!classic_root) {
        fmt::print(stderr,
                   "User Settings warning [classic_root_unavailable]: could not resolve the "
                   "CLASSIC root.\n");
        fmt::print("App update check is disabled because User Settings could not be trusted.\n");
        return 0;
    }

    if (!update_check_enabled_for_root(*classic_root)) {
        return 0;
    }

    if (!init_runtime_for_app_update()) {
        return 2;
    }

    // `CLASSIC_CLI_VERSION` is injected by CMake from CLASSIC_Info.version
    // in `CLASSIC Data/databases/CLASSIC Main.yaml` (see classic-cli/
    // CMakeLists.txt). That YAML field is the documented single source of
    // truth for the application version — the Qt GUI reads the same field
    // at startup and feeds it to this same `check_app_notification` bridge
    // entry point. To bump the CLI's reported installed version, edit the
    // YAML; the CMake build picks up the new value at configure time and
    // fails if the CMake `project(... VERSION ...)` ever drifts from it.
#ifndef CLASSIC_CLI_VERSION
#error "CLASSIC_CLI_VERSION must be defined by the build system (see CMakeLists.txt)"
#endif
    const std::string current_version = CLASSIC_CLI_VERSION;

    int exit_code;
    try {
        auto status =
            classic::update::check_app_notification(rust::Str("evildarkarchon"), rust::Str("CLASSIC-Fallout4"),
                                                    rust::Str(current_version.c_str(), current_version.size()));
        exit_code = report_notification(status);
    } catch (const rust::Error& e) {
        fmt::print(stderr, "App update check failed: {}\n", std::string(e.what()));
        exit_code = 1;
    } catch (const std::exception& e) {
        fmt::print(stderr, "App update check failed: {}\n", e.what());
        exit_code = 1;
    }

    classic::runtime::shutdown_runtime();
    return exit_code;
}
