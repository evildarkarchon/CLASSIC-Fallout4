// SPDX-License-Identifier: MIT
//
// Catch2 tests for how every native CLI command finds its Installation Root.
//
// Each command receives its two process facts (executable folder, working directory) as an
// explicit input, so these tests start the search inside a temporary tree. Every candidate the
// Config locator derives from them (parent, grandparent, `install` children) stays inside that
// tree, so where this test binary was built cannot change the outcome.

#include <catch2/catch_test_macros.hpp>

#include "../src/app_update.h"
#include "../src/installation_root.h"
#include "../src/scanner.h"
#include "../src/yaml_update.h"

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <string>
#include <system_error>
#include <vector>

namespace {

namespace fs = std::filesystem;

/// A temporary search tree with a `build/bin` executable folder and a separate `work` folder.
struct SearchTree {
    SearchTree() {
        const auto unique_suffix = std::to_string(std::chrono::steady_clock::now().time_since_epoch().count());
        root = fs::temp_directory_path() / ("classic-cli-installation-root-" + unique_suffix);
        fs::create_directories(executable_dir());
        fs::create_directories(working_dir());
    }

    /// Removes the tree without letting cleanup throw out of a destructor.
    ~SearchTree() {
        std::error_code ec;
        // A leftover temp folder is harmless and must not mask the test's own result.
        fs::remove_all(root, ec);
    }

    SearchTree(const SearchTree&) = delete;
    SearchTree& operator=(const SearchTree&) = delete;

    [[nodiscard]] fs::path executable_dir() const { return root / "build" / "bin"; }
    [[nodiscard]] fs::path working_dir() const { return root / "work"; }

    [[nodiscard]] CliProcessLocation location() const {
        return CliProcessLocation{executable_dir().string(), working_dir().string()};
    }

    /// Lists every path in the tree, so a test can prove a command created nothing.
    [[nodiscard]] std::vector<std::string> inventory() const {
        std::vector<std::string> entries;
        for (const auto& entry : fs::recursive_directory_iterator(root)) {
            entries.push_back(fs::relative(entry.path(), root).generic_string());
        }
        std::sort(entries.begin(), entries.end());
        return entries;
    }

    fs::path root;
};

} // namespace

TEST_CASE("CLI states CLASSIC Data not found and names both search starts", "[cli][installation-root]") {
    const SearchTree tree;
    const auto location = tree.location();

    REQUIRE_FALSE(locate_cli_installation_root(location).has_value());

    const std::string message = cli_installation_root_not_found_message(location);
    REQUIRE(message.rfind("CLASSIC Data not found", 0) == 0);
    REQUIRE(message.find(location.executable_dir) != std::string::npos);
    REQUIRE(message.find(location.working_dir) != std::string::npos);
}

TEST_CASE("CLI scan, app update and YAML Data update stop before any work when CLASSIC Data is missing",
          "[cli][installation-root]") {
    const SearchTree tree;
    const auto location = tree.location();
    const auto before = tree.inventory();

    // The old copies fell back to the working directory; the scan and YAML paths then opened
    // User Settings there. A non-zero exit with an unchanged tree proves neither happened.
    CHECK(run_scan(CliArgs{}, location) == kCliInstallationRootNotFoundExitCode);
    CHECK(run_check_app_update(CliArgs{}, location) == kCliInstallationRootNotFoundExitCode);
    CHECK(run_check_yaml_updates(CliArgs{}, location) == kCliInstallationRootNotFoundExitCode);
    CHECK(run_apply_yaml_updates(CliArgs{}, location) == kCliInstallationRootNotFoundExitCode);

    REQUIRE(kCliInstallationRootNotFoundExitCode != 0);
    REQUIRE(tree.inventory() == before);
}

TEST_CASE("CLI finds the Installation Root through Config's shared search", "[cli][installation-root]") {
    SECTION("the working directory when it holds CLASSIC Data") {
        const SearchTree tree;
        fs::create_directories(tree.working_dir() / "CLASSIC Data");

        REQUIRE(locate_cli_installation_root(tree.location()) == tree.working_dir().string());
    }

    SECTION("the executable folder's grandparent, which the CLI's own copies never searched") {
        const SearchTree tree;
        fs::create_directories(tree.root / "CLASSIC Data");

        REQUIRE(locate_cli_installation_root(tree.location()) == tree.root.string());
    }

    SECTION("nothing when only the unavailable working directory would have matched") {
        const SearchTree tree;
        fs::create_directories(tree.working_dir() / "CLASSIC Data");
        const CliProcessLocation executable_only{tree.executable_dir().string(), ""};

        REQUIRE_FALSE(locate_cli_installation_root(executable_only).has_value());
    }
}
