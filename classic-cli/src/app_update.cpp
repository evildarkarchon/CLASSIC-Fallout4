#include "app_update.h"

#include "rust/cxx.h"

#include "classic_cxx_bridge/message.h"
#include "classic_cxx_bridge/runtime.h"
#include "classic_cxx_bridge/update.h"

#include <fmt/core.h>

#include <string>

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
constexpr const char* kClassificationError = "error";

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
        fmt::print("You are up to date (latest v{}, published {}).\n",
                   std::string(status.latest_version),
                   or_unknown(status.published_at));
        return 0;
    }

    if (is_classification(status.classification, kClassificationUpdateAvailable)) {
        fmt::print("Update available: v{} (published {}).\n",
                   std::string(status.latest_version),
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
                   or_unknown(status.min_supported_version),
                   std::string(status.latest_version),
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

    if (is_classification(status.classification, kClassificationError)) {
        const std::string error_message(status.error_message);
        fmt::print(stderr, "Update check failed: {}\n",
                   error_message.empty() ? std::string("unknown error") : error_message);
        return 1;
    }

    fmt::print(stderr,
               "Update check returned an unrecognised classification: {}\n",
               std::string(status.classification));
    return 1;
}

bool init_runtime_for_app_update() {
    try {
        classic::message::init_logging();
        classic::runtime::init_runtime();
        return true;
    } catch (const rust::Error& e) {
        fmt::print(stderr, "Fatal: failed to initialize runtime: {}\n",
                   std::string(e.what()));
        return false;
    }
}

} // namespace

int run_check_app_update(const CliArgs& /*args*/) {
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
#    error "CLASSIC_CLI_VERSION must be defined by the build system (see CMakeLists.txt)"
#endif
    const std::string current_version = CLASSIC_CLI_VERSION;

    int exit_code;
    try {
        auto status = classic::update::check_app_notification(
            rust::Str("evildarkarchon"),
            rust::Str("CLASSIC-Fallout4"),
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
