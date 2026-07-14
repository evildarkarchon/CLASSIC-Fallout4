// SPDX-License-Identifier: MIT
//
// Catch2 bridge tests for the native User Settings commit action.

#include <catch2/catch_test_macros.hpp>

#include "../src/user_settings_action.h"

#include "classic_cxx_bridge/settings.h"

#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>

namespace {

namespace fs = std::filesystem;

/// Creates a unique CLASSIC root with unknown and compatibility-alias content.
fs::path make_settings_root() {
    const auto suffix = std::to_string(std::chrono::steady_clock::now().time_since_epoch().count());
    const fs::path root = fs::temp_directory_path() / ("classic-cli-user-settings-" + suffix);
    fs::create_directories(root);
    std::ofstream settings(root / "CLASSIC Settings.yaml", std::ios::binary);
    settings << "schema_version: \"1.0\"\n"
                "CLASSIC_Settings:\n"
                "  Custom Scan Folder: E:/Legacy Alias\n"
                "ThirdPartyPlugin:\n"
                "  enabled: true\n";
    settings.close();
    return root;
}

} // namespace

TEST_CASE("native destination action commits and resets through typed User Settings", "[bridge][settings][commit]") {
    const fs::path root = make_settings_root();
    CliArgs set_args{};
    set_args.unsolved_logs_destination = "D:/CLASSIC/Unsolved";

    REQUIRE(persist_unsolved_logs_destination_option(set_args, root.string()));
    auto set_snapshot = classic::settings::user_settings_open_crash_log_scan_settings(root.string());
    REQUIRE(set_snapshot.has_unsolved_logs_destination);
    REQUIRE(std::string(set_snapshot.unsolved_logs_destination) == "D:/CLASSIC/Unsolved");

    CliArgs reset_args{};
    reset_args.reset_unsolved_logs_destination = true;
    REQUIRE(persist_unsolved_logs_destination_option(reset_args, root.string()));
    auto reset_snapshot = classic::settings::user_settings_open_crash_log_scan_settings(root.string());
    REQUIRE_FALSE(reset_snapshot.has_unsolved_logs_destination);

    std::ifstream persisted(root / "CLASSIC Settings.yaml", std::ios::binary);
    const std::string content((std::istreambuf_iterator<char>(persisted)), std::istreambuf_iterator<char>());
    REQUIRE(content.find("Custom Scan Folder") != std::string::npos);
    REQUIRE(content.find("ThirdPartyPlugin") != std::string::npos);

    std::error_code ec;
    fs::remove_all(root, ec);
}
