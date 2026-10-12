// SPDX-License-Identifier: MIT
//
// Catch2 bridge tests for the YAML update-delivery FFI surface.
//
// These exercises target the first-party `classic::update::yaml_data_*`
// entry points native callers use; the lower-level generic `yaml_*`
// compatibility functions left the bridge with no frontend caller (#309).
// The Rust-side unit tests in
// `cpp-bindings/classic-cpp-bridge/src/update.rs` cover the same DTO
// mapping, but the tests here prove the full FFI round-trip works end to
// end from C++.
//
// This translation unit only runs when the bridge target is linked in
// (see `classic-cli/CMakeLists.txt`). Invoke via
// `classic-cli/build_cli.ps1 -Test` rather than raw ctest — the PowerShell
// wrapper owns the vcpkg + MSVC environment setup.

#include <catch2/catch_test_macros.hpp>

#include "../src/yaml_update.h"

#include "classic_cxx_bridge/update.h"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string>
#include <system_error>
#include <vector>

namespace {

namespace fs = std::filesystem;

/// Tags mirror `TAG_*` constants in
/// `cpp-bindings/classic-cpp-bridge/src/update.rs`. Keep in sync when
/// the bridge adds a new status case.
constexpr std::uint32_t kTagDisabled = 0u;


struct ScopedCurrentPath {
    explicit ScopedCurrentPath(const fs::path& path) : original(fs::current_path()) {
        fs::current_path(path);
    }

    ~ScopedCurrentPath() {
        std::error_code ec;
        fs::current_path(original, ec);
    }

    fs::path original;
};

fs::path make_disabled_settings_root() {
    const auto unique_suffix =
        std::to_string(std::chrono::steady_clock::now().time_since_epoch().count());
    const fs::path root =
        fs::temp_directory_path() / ("classic-cli-yaml-update-" + unique_suffix);

    fs::create_directories(root / "CLASSIC Data");

    std::ofstream settings(root / "CLASSIC Settings.yaml", std::ios::binary);
    settings << "---\n"
                "CLASSIC_Settings:\n"
                "  Update Check: false\n";
    settings.close();

    return root;
}

} // namespace

TEST_CASE("yaml_data_check_update returns Disabled when enabled=false",
          "[bridge][update][yaml]") {
    auto status = classic::update::yaml_data_check_update(/*enabled=*/false);

    REQUIRE(status.tag == kTagDisabled);
    REQUIRE(std::string(status.error_message).empty());
    REQUIRE(status.compatible_files.empty());
    REQUIRE(status.incompatible_files.empty());
}

TEST_CASE("yaml_data_apply_update refuses when enabled=false without installing",
          "[bridge][update][yaml]") {
    // The production apply path: with Update Check off, the core refuses before
    // any HTTP, so no approved file can be installed even with a decision attached.
    classic::update::ApprovedUpdateDto approved{};
    approved.release_tag = "yaml-data-v-test";
    approved.file_names.push_back("CLASSIC Main.yaml");
    approved.file_sha256.push_back("deadbeef");

    const auto report = classic::update::yaml_data_apply_update(/*enabled=*/false, approved);

    REQUIRE(report.installed.empty());
    REQUIRE(report.failed.empty());
    REQUIRE(std::string(report.error_message).rfind("update check disabled:", 0) == 0);
}

TEST_CASE("yaml_data_rollback_update covers first-party shippable files",
          "[bridge][update][yaml]") {
    const fs::path root = make_disabled_settings_root();
    {
        const ScopedCurrentPath cwd(root);
        const auto report = classic::update::yaml_data_rollback_update();

        std::vector<std::string> names;
        for (const auto& fileName : report.rolled_back) {
            names.emplace_back(fileName);
        }
        for (const auto& fileName : report.no_previous_version) {
            names.emplace_back(fileName);
        }
        for (const auto& fileName : report.failed_files) {
            names.emplace_back(fileName);
        }

        REQUIRE(std::find(names.begin(), names.end(), "CLASSIC Main.yaml") != names.end());
        REQUIRE(std::find(names.begin(), names.end(), "CLASSIC Fallout4.yaml") != names.end());
        REQUIRE(report.failed_files.size() == report.failure_reasons.size());
    }

    std::error_code ec;
    fs::remove_all(root, ec);
}

TEST_CASE("run_check_yaml_updates reports disabled setting without failing",
          "[cli][update][yaml]") {
    const fs::path root = make_disabled_settings_root();
    int exit_code = -1;
    {
        const ScopedCurrentPath cwd(root);
        exit_code = run_check_yaml_updates(CliArgs{});
    }

    std::error_code ec;
    fs::remove_all(root, ec);

    REQUIRE(exit_code == 0);
}

TEST_CASE("run_apply_yaml_updates fails when updates are disabled in settings",
          "[cli][update][yaml]") {
    const fs::path root = make_disabled_settings_root();
    int exit_code = -1;
    {
        const ScopedCurrentPath cwd(root);
        exit_code = run_apply_yaml_updates(CliArgs{});
    }

    std::error_code ec;
    fs::remove_all(root, ec);

    REQUIRE(exit_code == 1);
}
