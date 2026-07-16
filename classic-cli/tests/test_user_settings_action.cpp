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
#include <vector>

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

/// Creates a current User Settings document covering the complete native scan input group.
fs::path make_scan_settings_root() {
    const auto suffix = std::to_string(std::chrono::steady_clock::now().time_since_epoch().count());
    const fs::path root = fs::temp_directory_path() / ("classic-cli-scan-settings-" + suffix);
    fs::create_directories(root);
    std::ofstream settings(root / "CLASSIC Settings.yaml", std::ios::binary);
    settings << "schema_version: \"1.0\"\n"
                "CLASSIC_Settings:\n"
                "  Managed Game: Fallout 4\n"
                "  Game Version: NextGen\n"
                "  FCX Mode: true\n"
                "  Simplify Logs: true\n"
                "  Show FormID Values: true\n"
                "  Move Unsolved Logs: true\n"
                "  Unsolved Logs Destination: 'D:/CLASSIC/Unsolved'\n"
                "  SCAN Custom Path: 'D:/CLASSIC/Crash Logs'\n"
                "  Max Concurrent Scans: 5\n"
                "  FormID Databases:\n"
                "    Fallout4:\n"
                "      - databases/custom.db\n"
                "  Game Folder Path: 'D:/Games/Fallout 4'\n"
                "  Game EXE Path: 'D:/Games/Fallout 4/Fallout4.exe'\n"
                "  Documents Folder Path: 'D:/Documents/My Games/Fallout4'\n";
    settings.close();
    return root;
}

/// Creates an untrusted User Settings document for degraded-read adapter coverage.
fs::path make_malformed_scan_settings_root() {
    const auto suffix = std::to_string(std::chrono::steady_clock::now().time_since_epoch().count());
    const fs::path root = fs::temp_directory_path() / ("classic-cli-malformed-scan-settings-" + suffix);
    fs::create_directories(root);
    std::ofstream settings(root / "CLASSIC Settings.yaml", std::ios::binary);
    settings << "CLASSIC_Settings: [\n";
    settings.close();
    return root;
}

/// Creates a first-run CLASSIC root without a User Settings document.
fs::path make_missing_settings_root() {
    const auto suffix = std::to_string(std::chrono::steady_clock::now().time_since_epoch().count());
    const fs::path root = fs::temp_directory_path() / ("classic-cli-missing-settings-" + suffix);
    fs::create_directories(root);
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

TEST_CASE("native destination action explicitly bootstraps missing User Settings", "[bridge][settings][commit]") {
    const fs::path root = make_missing_settings_root();
    CliArgs args{};
    args.unsolved_logs_destination = "D:/CLASSIC/First Run Unsolved";

    REQUIRE(persist_unsolved_logs_destination_option(args, root.string()));

    const auto snapshot = classic::settings::user_settings_open_crash_log_scan_settings(root.string());
    REQUIRE(std::string(snapshot.classification) == "current");
    REQUIRE(snapshot.has_unsolved_logs_destination);
    REQUIRE(std::string(snapshot.unsolved_logs_destination) == "D:/CLASSIC/First Run Unsolved");

    std::error_code ec;
    fs::remove_all(root, ec);
}

TEST_CASE("native scan preparation inherits typed User Settings facts", "[bridge][settings][scan]") {
    const fs::path root = make_scan_settings_root();

    const auto prepared = prepare_scan_user_settings(CliArgs{}, root.string());

    REQUIRE(prepared.has_value());
    REQUIRE(prepared->game == "Fallout4");
    REQUIRE(prepared->game_version == "NextGen");
    REQUIRE(prepared->fcx_mode);
    REQUIRE(prepared->simplify_logs);
    REQUIRE(prepared->show_formid_values);
    REQUIRE(prepared->move_unsolved_logs);
    REQUIRE(prepared->unsolved_logs_destination == "D:/CLASSIC/Unsolved");
    REQUIRE(prepared->custom_scan_directory == "D:/CLASSIC/Crash Logs");
    REQUIRE(prepared->max_concurrent == 5u);
    REQUIRE(prepared->formid_database_paths == std::vector<std::string>{"databases/custom.db"});
    REQUIRE(prepared->setup_game_root == "D:/Games/Fallout 4");
    REQUIRE(prepared->setup_game_exe_path == "D:/Games/Fallout 4/Fallout4.exe");
    REQUIRE(prepared->setup_docs_root == "D:/Documents/My Games/Fallout4");
    REQUIRE(prepared->classification == "current");
    REQUIRE(prepared->commit_eligibility == "eligible");

    std::error_code ec;
    fs::remove_all(root, ec);
}

TEST_CASE("native scan preparation preserves explicit CLI overrides", "[bridge][settings][scan]") {
    const fs::path root = make_scan_settings_root();
    CliArgs args{};
    args.game = "Fallout4";
    args.game_was_explicit = true;
    args.game_version = "Original";
    args.game_version_was_explicit = true;
    args.scan_path = "E:/One Shot Logs";
    args.max_concurrent = 0;
    args.max_concurrent_was_explicit = true;

    const auto prepared = prepare_scan_user_settings(args, root.string());

    REQUIRE(prepared.has_value());
    REQUIRE(prepared->game == "Fallout4");
    REQUIRE(prepared->game_version == "Original");
    REQUIRE(prepared->custom_scan_directory == "E:/One Shot Logs");
    REQUIRE(prepared->max_concurrent == 0u);

    std::error_code ec;
    fs::remove_all(root, ec);
}

TEST_CASE("native scan preparation isolates cross-game CLI overrides", "[bridge][settings][scan]") {
    const fs::path root = make_scan_settings_root();
    CliArgs args{};
    args.game = "Skyrim";
    args.game_was_explicit = true;

    const auto prepared = prepare_scan_user_settings(args, root.string());

    REQUIRE(prepared.has_value());
    REQUIRE(prepared->game == "Skyrim");
    REQUIRE(prepared->game_version == "auto");
    REQUIRE_FALSE(prepared->fcx_mode);
    REQUIRE(prepared->custom_scan_directory.empty());
    REQUIRE(prepared->configured_documents_root.empty());
    REQUIRE(prepared->setup_game_root.empty());
    REQUIRE(prepared->setup_docs_root.empty());
    REQUIRE(prepared->setup_game_exe_path.empty());
    REQUIRE(prepared->formid_database_paths.empty());

    std::error_code ec;
    fs::remove_all(root, ec);
}

TEST_CASE("native scan preparation lets explicit FCX override cross-game isolation", "[bridge][settings][scan]") {
    const fs::path root = make_scan_settings_root();
    CliArgs args{};
    args.game = "Skyrim";
    args.game_was_explicit = true;
    args.fcx_mode = true;

    const auto prepared = prepare_scan_user_settings(args, root.string());

    REQUIRE(prepared.has_value());
    REQUIRE(prepared->fcx_mode);

    std::error_code ec;
    fs::remove_all(root, ec);
}

TEST_CASE("native Fallout 4 VR scans reuse Fallout 4 FormID database rows", "[bridge][settings][scan]") {
    const fs::path root = make_scan_settings_root();
    CliArgs args{};
    args.game = "Fallout4VR";
    args.game_was_explicit = true;

    const auto prepared = prepare_scan_user_settings(args, root.string());

    REQUIRE(prepared.has_value());
    REQUIRE(prepared->formid_database_paths == std::vector<std::string>{"databases/custom.db"});

    std::error_code ec;
    fs::remove_all(root, ec);
}

TEST_CASE("native scan preparation exposes degraded typed snapshot metadata", "[bridge][settings][scan]") {
    const fs::path root = make_malformed_scan_settings_root();

    const auto prepared = prepare_scan_user_settings(CliArgs{}, root.string());

    REQUIRE(prepared.has_value());
    REQUIRE(prepared->classification == "malformed");
    REQUIRE(prepared->commit_eligibility == "blocked_untrusted");
    REQUIRE_FALSE(prepared->fcx_mode);
    REQUIRE_FALSE(prepared->show_formid_values);
    REQUIRE_FALSE(prepared->move_unsolved_logs);

    std::error_code ec;
    fs::remove_all(root, ec);
}
