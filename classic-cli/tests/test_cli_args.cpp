#include <catch2/catch_test_macros.hpp>

#include "cli_args.h"

#include <string>
#include <vector>

/// Helper: convert a vector of strings into argc/argv suitable for parse_args.
/// The first element should be the program name (convention).
struct ArgvBuilder {
    std::vector<std::string> args;
    std::vector<char*> ptrs;

    explicit ArgvBuilder(std::initializer_list<std::string> list)
        : args(list)
    {
        ptrs.reserve(args.size());
        for (auto& s : args) {
            ptrs.push_back(s.data());
        }
    }

    int argc() const { return static_cast<int>(ptrs.size()); }
    char** argv() { return ptrs.data(); }
};

TEST_CASE("CliArgs defaults", "[cli_args]") {
    ArgvBuilder ab({"classic-cli"});
    CliArgs args = parse_args(ab.argc(), ab.argv());

    REQUIRE(args.game == "Fallout4");
    REQUIRE(args.game_version == "auto");
    REQUIRE(args.fcx_mode == false);
    REQUIRE(args.show_fid_values == false);
    REQUIRE(args.simplify_logs == false);
    REQUIRE(args.scan_path.empty());
    REQUIRE(args.max_concurrent == 0);
    REQUIRE(args.version_flag == false);
}

TEST_CASE("CliArgs game selection", "[cli_args]") {
    SECTION("Fallout4 (explicit)") {
        ArgvBuilder ab({"classic-cli", "--game", "Fallout4"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.game == "Fallout4");
    }

    SECTION("Skyrim") {
        ArgvBuilder ab({"classic-cli", "--game", "Skyrim"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.game == "Skyrim");
    }

    // NOTE: Invalid --game values cause CLI11 to call std::exit(),
    // so we can't test rejection here. That's covered by the
    // PowerShell integration test (Test 7).
}

TEST_CASE("CliArgs boolean flags", "[cli_args]") {
    SECTION("--game-version sets version mode") {
        ArgvBuilder ab({"classic-cli", "--game-version", "VR"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.game_version == "VR");
    }

    SECTION("--fcx-mode enables FCX") {
        ArgvBuilder ab({"classic-cli", "--fcx-mode"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.fcx_mode == true);
    }

    SECTION("--show-fid-values enables FormID display") {
        ArgvBuilder ab({"classic-cli", "--show-fid-values"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.show_fid_values == true);
    }

    SECTION("--simplify-logs enables log simplification") {
        ArgvBuilder ab({"classic-cli", "--simplify-logs"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.simplify_logs == true);
    }

    SECTION("--version sets version flag") {
        ArgvBuilder ab({"classic-cli", "--version"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.version_flag == true);
    }
}

TEST_CASE("CliArgs scan-path and max-concurrent", "[cli_args]") {
    SECTION("--scan-path sets custom directory") {
        ArgvBuilder ab({"classic-cli", "--scan-path", "C:/my/logs"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.scan_path == "C:/my/logs");
    }

    SECTION("--max-concurrent sets thread limit") {
        ArgvBuilder ab({"classic-cli", "--max-concurrent", "8"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.max_concurrent == 8);
    }
}

TEST_CASE("CliArgs combined flags", "[cli_args]") {
    ArgvBuilder ab({"classic-cli",
                    "--game", "Skyrim",
                    "--game-version", "VR",
                    "--fcx-mode",
                    "--scan-path", "/tmp/crashes",
                    "--max-concurrent", "4"});
    CliArgs args = parse_args(ab.argc(), ab.argv());

    REQUIRE(args.game == "Skyrim");
    REQUIRE(args.game_version == "VR");
    REQUIRE(args.fcx_mode == true);
    REQUIRE(args.scan_path == "/tmp/crashes");
    REQUIRE(args.max_concurrent == 4);
}
