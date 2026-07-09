// SPDX-License-Identifier: MIT
//
// Catch2 bridge tests for the YAML update-delivery FFI surface.
//
// These exercises target the first-party `classic::update::yaml_data_*`
// entry points used by native callers plus the lower-level generic
// `yaml_*` compatibility functions retained by the yaml-update-delivery
// change. The Rust-side unit tests in
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

rust::Vec<classic::update::YamlClientSchemaEntryDto> make_entries() {
    rust::Vec<classic::update::YamlClientSchemaEntryDto> entries;
    classic::update::YamlClientSchemaEntryDto entry{};
    entry.name = "CLASSIC Main.yaml";
    entry.accepted_major = 1u;
    entry.accepted_minimum_minor = 0u;
    entry.has_installed = false;
    entry.installed_major = 0u;
    entry.installed_minor = 0u;
    entries.push_back(std::move(entry));
    return entries;
}

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

TEST_CASE("yaml_check_update returns Disabled when enabled=false", "[bridge][update][yaml]") {
    // Pass an unroutable Pages URL. If the Disabled short-circuit regressed,
    // this would either hang on the HTTP GET or come back with tag=Error.
    auto entries = make_entries();
    auto status = classic::update::yaml_check_update(
        "http://127.0.0.1:1/manifest-latest.json",
        "yaml-data-v",
        entries,
        /*enabled=*/false,
        /*bundled_yaml_dir=*/rust::Str(""));

    REQUIRE(status.tag == kTagDisabled);
    REQUIRE(std::string(status.error_message).empty());
    REQUIRE(status.compatible_files.empty());
    REQUIRE(status.incompatible_files.empty());
}

TEST_CASE("yaml_data_check_update returns Disabled when enabled=false",
          "[bridge][update][yaml]") {
    auto status = classic::update::yaml_data_check_update(/*enabled=*/false);

    REQUIRE(status.tag == kTagDisabled);
    REQUIRE(std::string(status.error_message).empty());
    REQUIRE(status.compatible_files.empty());
    REQUIRE(status.incompatible_files.empty());
}

TEST_CASE("yaml_rollback_update on unknown file does not error",
          "[bridge][update][yaml]") {
    // The yaml-cache dir may not be populated on this machine; rollback
    // must surface that as a graceful outcome (rolled_back=false + either
    // empty error_message or a resolvable Generic error) rather than
    // aborting the caller.
    auto outcome = classic::update::yaml_rollback_update(
        "__cpp_bridge_definitely_nonexistent_file_xyzzy__.yaml");
    if (std::string(outcome.error_message).empty()) {
        REQUIRE_FALSE(outcome.rolled_back);
    }
    // If the test environment has no LOCALAPPDATA/APPDATA, the bridge
    // produces a Generic error — still acceptable; the guard here is
    // only against a panic reaching C++.
    SUCCEED("yaml_rollback_update FFI round-trip produced a valid outcome");
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
