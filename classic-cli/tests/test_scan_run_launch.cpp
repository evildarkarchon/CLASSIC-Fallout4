// SPDX-License-Identifier: MIT
//
// Catch2 bridge tests for how the native CLI launches a Crash Log Scan Run.
//
// Which saved value wins, how the game-differs rule withholds values, and how degraded User
// Settings fall back to defaults are Crash Log Scan Launch rules, pinned once by the
// `crash-log-scan-launch` conformance family. What stays the CLI's is mapping each documented flag
// onto a per-run override, saving the Unsolved Logs Destination before the launch, and showing
// the launch's Rust-rendered diagnostics. These tests pin exactly that.

#include <catch2/catch_test_macros.hpp>

#include "../src/scan_run_cli.h"

#include "classic_cxx_bridge/scanner.h"
#include "classic_cxx_bridge/settings.h"

#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>
#include <system_error>
#include <vector>

namespace {

namespace fs = std::filesystem;
namespace scanner = classic::scanner;

/// Owns one isolated Installation Root (or unrelated folder) for a single test.
class TemporaryDirectory final {
public:
    /// Creates a unique directory beneath the platform temporary directory.
    explicit TemporaryDirectory(const std::string& prefix) {
        const auto suffix = std::to_string(std::chrono::steady_clock::now().time_since_epoch().count());
        path_ = fs::temp_directory_path() / (prefix + "-" + suffix);
        fs::create_directories(path_);
    }

    /// Removes the directory without letting cleanup failures replace a test outcome.
    ~TemporaryDirectory() {
        std::error_code error;
        fs::remove_all(path_, error);
    }

    TemporaryDirectory(const TemporaryDirectory&) = delete;
    TemporaryDirectory& operator=(const TemporaryDirectory&) = delete;

    /// Returns the directory retained for this test's lifetime.
    [[nodiscard]] const fs::path& path() const noexcept { return path_; }

private:
    fs::path path_;
};

/// Restores the process working directory after a test deliberately runs from elsewhere.
class ScopedCurrentPath final {
public:
    /// Switches the working directory to `path` for this scope.
    explicit ScopedCurrentPath(const fs::path& path)
        : previous_(fs::current_path()) {
        fs::current_path(path);
    }

    /// Returns to the previous working directory, ignoring a failure during unwinding.
    ~ScopedCurrentPath() {
        std::error_code error;
        fs::current_path(previous_, error);
    }

    ScopedCurrentPath(const ScopedCurrentPath&) = delete;
    ScopedCurrentPath& operator=(const ScopedCurrentPath&) = delete;

private:
    fs::path previous_;
};

/// Writes one User Settings document beneath `root`.
void write_settings(const fs::path& root, const std::string& yaml) {
    std::ofstream settings(root / "CLASSIC Settings.yaml", std::ios::binary);
    settings << yaml;
}

/// A current Fallout 4 document that saves a concrete value for every flag-backed option.
const std::string SAVED_FALLOUT4_SETTINGS = "schema_version: \"1.0\"\n"
                                            "CLASSIC_Settings:\n"
                                            "  Managed Game: Fallout 4\n"
                                            "  Game Version: NextGen\n"
                                            "  Max Concurrent Scans: 5\n"
                                            "  SCAN Custom Path: 'D:/CLASSIC/Saved Crash Logs'\n";

/// Launches through the CLI seam and returns the launched request's read-only view.
scanner::ScanRunLaunchRequestDto launch_view(const CliArgs& args, const fs::path& root) {
    auto launch = launch_cli_scan_run(args, root.string());
    REQUIRE(launch.has_value());
    REQUIRE_FALSE(scanner::scan_run_launch_error(**launch).has_error);
    return scanner::scan_run_launch_view(**launch);
}

} // namespace

TEST_CASE("CLI value flags win over saved User Settings for this run", "[cli][scan-launch]") {
    TemporaryDirectory root("classic-cli-launch-values");
    write_settings(root.path(), SAVED_FALLOUT4_SETTINGS);
    CliArgs args{};
    args.game_version = "Original";
    args.game_version_was_explicit = true;
    args.scan_path = "E:/One Shot Logs";
    args.max_concurrent = 7;
    args.max_concurrent_was_explicit = true;

    const auto view = launch_view(args, root.path());

    REQUIRE(std::string(view.configuration.game_version) == "Original");
    REQUIRE(view.configuration.has_max_concurrent);
    REQUIRE(view.configuration.max_concurrent == 7u);
    REQUIRE(view.standard_source.has_custom_scan_directory);
    REQUIRE(std::string(view.standard_source.custom_scan_directory) == "E:/One Shot Logs");
}

TEST_CASE("CLI value flags left out keep the saved values", "[cli][scan-launch]") {
    TemporaryDirectory root("classic-cli-launch-saved");
    write_settings(root.path(), SAVED_FALLOUT4_SETTINGS);

    // CLI11 fills `game_version` and `max_concurrent` with their defaults even when the flag is
    // absent; only the `*_was_explicit` facts may turn them into overrides.
    const auto view = launch_view(CliArgs{}, root.path());

    REQUIRE(std::string(view.configuration.game_version) == "NextGen");
    REQUIRE(view.configuration.has_max_concurrent);
    REQUIRE(view.configuration.max_concurrent == 5u);
    REQUIRE(std::string(view.standard_source.custom_scan_directory) == "D:/CLASSIC/Saved Crash Logs");
}

TEST_CASE("CLI --max-concurrent 0 overrides a saved limit with adaptive concurrency", "[cli][scan-launch]") {
    TemporaryDirectory root("classic-cli-launch-adaptive");
    write_settings(root.path(), SAVED_FALLOUT4_SETTINGS);
    CliArgs args{};
    args.max_concurrent = 0;
    args.max_concurrent_was_explicit = true;

    const auto view = launch_view(args, root.path());

    REQUIRE_FALSE(view.configuration.has_max_concurrent);
}

TEST_CASE("CLI on-only flags turn their option on for this run", "[cli][scan-launch]") {
    TemporaryDirectory root("classic-cli-launch-on-only");
    write_settings(root.path(), "schema_version: \"1.0\"\n"
                                "CLASSIC_Settings:\n"
                                "  Managed Game: Fallout 4\n"
                                "  FCX Mode: false\n"
                                "  Simplify Logs: false\n"
                                "  Show FormID Values: false\n");

    const auto saved = launch_view(CliArgs{}, root.path());
    REQUIRE_FALSE(saved.configuration.show_formid_values);
    REQUIRE_FALSE(saved.configuration.simplify_logs);
    REQUIRE_FALSE(saved.fcx_enabled);

    CliArgs args{};
    args.show_fid_values = true;
    args.simplify_logs = true;
    args.fcx_mode = true;
    const auto overridden = launch_view(args, root.path());
    REQUIRE(overridden.configuration.show_formid_values);
    REQUIRE(overridden.configuration.simplify_logs);
    REQUIRE(overridden.fcx_enabled);
}

TEST_CASE("CLI on-only flags left out never turn a saved option off", "[cli][scan-launch]") {
    TemporaryDirectory root("classic-cli-launch-on-saved");
    write_settings(root.path(), "schema_version: \"1.0\"\n"
                                "CLASSIC_Settings:\n"
                                "  Managed Game: Fallout 4\n"
                                "  Simplify Logs: true\n"
                                "  Show FormID Values: true\n");

    const auto view = launch_view(CliArgs{}, root.path());

    REQUIRE(view.configuration.show_formid_values);
    REQUIRE(view.configuration.simplify_logs);
}

TEST_CASE("CLI --game names the scanned game only when it is given", "[cli][scan-launch]") {
    TemporaryDirectory root("classic-cli-launch-game");
    write_settings(root.path(), "schema_version: \"1.0\"\n"
                                "CLASSIC_Settings:\n"
                                "  Managed Game: Fallout 4 VR\n");

    // CLI11 defaults `game` to Fallout4, so an absent flag must leave the managed game in charge.
    const auto managed = launch_view(CliArgs{}, root.path());
    REQUIRE(managed.configuration.game == scanner::ScanRunGameId::Fallout4VR);

    CliArgs args{};
    args.game = "Fallout4";
    args.game_was_explicit = true;
    const auto explicit_game = launch_view(args, root.path());
    REQUIRE(explicit_game.configuration.game == scanner::ScanRunGameId::Fallout4);
}

TEST_CASE("A CLI Standard scan from an unrelated folder looks for Crash Logs under the Installation Root",
          "[cli][scan-launch]") {
    TemporaryDirectory root("classic-cli-launch-root");
    TemporaryDirectory unrelated("classic-cli-launch-elsewhere");
    ScopedCurrentPath cwd(unrelated.path());

    const auto view = launch_view(CliArgs{}, root.path());

    REQUIRE(view.intent == scanner::ScanRunLaunchIntent::Standard);
    REQUIRE(fs::path(std::string(view.standard_source.base_directory)) == root.path());
    REQUIRE(fs::path(std::string(view.configuration.installation_root)) == root.path());
}

TEST_CASE("CLI positional paths launch a Targeted scan of exactly those inputs", "[cli][scan-launch]") {
    TemporaryDirectory root("classic-cli-launch-targeted");
    CliArgs args{};
    args.input_paths = {"C:/one crash.log", "C:/two"};

    const auto view = launch_view(args, root.path());

    REQUIRE(view.intent == scanner::ScanRunLaunchIntent::Targeted);
    REQUIRE(view.targeted_source.inputs.size() == 2);
    REQUIRE(std::string(view.targeted_source.inputs[0]) == "C:/one crash.log");
    REQUIRE(std::string(view.targeted_source.inputs[1]) == "C:/two");
}

TEST_CASE("CLI saves --unsolved-logs-destination before the launch reads User Settings", "[cli][scan-launch]") {
    TemporaryDirectory root("classic-cli-launch-destination");
    CliArgs args{};
    args.unsolved_logs_destination = "D:/CLASSIC/Unsolved";

    const auto view = launch_view(args, root.path());

    // The launch read the destination the explicit User Settings Update had just committed.
    REQUIRE(view.configuration.has_configured_unsolved_logs_destination);
    REQUIRE(std::string(view.configuration.configured_unsolved_logs_destination) == "D:/CLASSIC/Unsolved");
    const auto saved = classic::settings::user_settings_open_crash_log_scan_settings(root.path().string());
    REQUIRE(std::string(saved.unsolved_logs_destination) == "D:/CLASSIC/Unsolved");

    CliArgs reset{};
    reset.reset_unsolved_logs_destination = true;
    const auto after_reset = launch_view(reset, root.path());
    REQUIRE_FALSE(after_reset.configuration.has_configured_unsolved_logs_destination);
}

TEST_CASE("CLI does not launch when the Unsolved Logs Destination cannot be saved", "[cli][scan-launch]") {
    TemporaryDirectory root("classic-cli-launch-rejected");
    write_settings(root.path(), "CLASSIC_Settings: [\n");
    CliArgs args{};
    args.unsolved_logs_destination = "D:/CLASSIC/Unsolved";

    REQUIRE_FALSE(launch_cli_scan_run(args, root.path().string()).has_value());
}

TEST_CASE("CLI shows launch diagnostics from their Display Content lines", "[cli][scan-launch][render]") {
    TemporaryDirectory root("classic-cli-launch-diagnostics");
    write_settings(root.path(), "CLASSIC_Settings: [\n");

    const auto view = launch_view(CliArgs{}, root.path());
    const auto messages = describe_cli_scan_run_launch(view);

    // A malformed document still launches; what the CLI shows about it is Rust's lines, in order,
    // one message each, routed by the severity Rust gave them.
    REQUIRE_FALSE(view.display_lines.empty());
    REQUIRE(messages.size() == view.display_lines.size());
    for (std::size_t index = 0; index < messages.size(); ++index) {
        REQUIRE(messages[index].text == render_cli_display_line(view.display_lines[index]));
        const bool attention = view.display_lines[index].severity == scanner::ScanRunDisplaySeverity::Warning ||
                               view.display_lines[index].severity == scanner::ScanRunDisplaySeverity::Failure;
        REQUIRE(messages[index].error == attention);
    }
}

TEST_CASE("CLI names the launched game with Rust's game token", "[cli][scan-launch]") {
    REQUIRE(cli_scan_run_game_token(scanner::ScanRunGameId::Fallout4) == "Fallout4");
    REQUIRE(cli_scan_run_game_token(scanner::ScanRunGameId::Fallout4VR) == "Fallout4VR");
}
