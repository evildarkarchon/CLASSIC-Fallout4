// SPDX-License-Identifier: MIT
//
// Catch2 policy tests for the native CLI app-update path.

#include <catch2/catch_test_macros.hpp>

#include "../src/app_update.h"

#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>
#include <system_error>

namespace {

namespace fs = std::filesystem;

struct ScopedCurrentPath {
    /// Switches the process working directory for one policy-check scope.
    explicit ScopedCurrentPath(const fs::path& path) : original(fs::current_path()) {
        fs::current_path(path);
    }

    /// Restores the original directory without allowing cleanup to throw.
    ~ScopedCurrentPath() {
        std::error_code ec;
        // Destructors cannot safely surface a current-directory cleanup failure.
        fs::current_path(original, ec);
    }

    fs::path original;
};

/// Creates an isolated CLASSIC root containing the requested User Settings YAML.
fs::path make_settings_root(const std::string& settings_yaml) {
    const auto unique_suffix =
        std::to_string(std::chrono::steady_clock::now().time_since_epoch().count());
    const fs::path root =
        fs::temp_directory_path() / ("classic-cli-app-update-" + unique_suffix);
    fs::create_directories(root / "CLASSIC Data");

    std::ofstream settings(root / "CLASSIC Settings.yaml", std::ios::binary);
    settings << settings_yaml;
    settings.close();

    return root;
}

} // namespace

TEST_CASE("App update honors disabled typed User Settings before checking the network",
          "[cli][update][app]") {
    const fs::path root = make_settings_root(
        "schema_version: \"1.0\"\n"
        "CLASSIC_Settings:\n"
        "  Update Check: false\n");

    int exit_code = -1;
    {
        const ScopedCurrentPath cwd(root);
        exit_code = run_check_app_update(CliArgs{});
    }

    std::error_code ec;
    fs::remove_all(root, ec);

    // The test target's CLASSIC_CLI_VERSION is deliberately invalid. Reaching
    // the notification bridge would return an error, so success proves the
    // typed preference short-circuited before validation or network access.
    REQUIRE(exit_code == 0);
}

TEST_CASE("App update fails closed for malformed User Settings",
          "[cli][update][app]") {
    const fs::path root = make_settings_root(
        "schema_version: \"1.0\"\n"
        "CLASSIC_Settings:\n"
        "  Update Check: [broken\n");

    int exit_code = -1;
    {
        const ScopedCurrentPath cwd(root);
        exit_code = run_check_app_update(CliArgs{});
    }

    std::error_code ec;
    fs::remove_all(root, ec);

    REQUIRE(exit_code == 0);
}
