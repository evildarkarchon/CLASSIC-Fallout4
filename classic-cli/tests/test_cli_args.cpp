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
        : args(list) {
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
    REQUIRE_FALSE(args.game_was_explicit);
    REQUIRE_FALSE(args.game_version_was_explicit);
    REQUIRE(args.fcx_mode == false);
    REQUIRE(args.show_fid_values == false);
    REQUIRE(args.simplify_logs == false);
    REQUIRE(args.scan_path.empty());
    REQUIRE(args.unsolved_logs_destination.empty());
    REQUIRE(args.reset_unsolved_logs_destination == false);
    REQUIRE(args.max_concurrent == 0);
    REQUIRE_FALSE(args.max_concurrent_was_explicit);
    REQUIRE(args.version_flag == false);
    REQUIRE(args.check_yaml_updates == false);
    REQUIRE(args.apply_yaml_updates == false);
    REQUIRE(args.rollback_yaml_updates == false);
}

TEST_CASE("Auto concurrency helper preserves floor and cap", "[cli_args]") {
    REQUIRE(auto_concurrency_for_cpu_count(1) == 2);
    REQUIRE(auto_concurrency_for_cpu_count(2) == 2);
    REQUIRE(auto_concurrency_for_cpu_count(3) == 2);
    REQUIRE(auto_concurrency_for_cpu_count(8) == 6);
    REQUIRE(auto_concurrency_for_cpu_count(40) == 32);
}

TEST_CASE("Effective concurrency helper preserves explicit overrides", "[cli_args]") {
    REQUIRE(effective_concurrency(5, 3) == 5);
    REQUIRE(effective_concurrency(0, 3) == 2);
}

TEST_CASE("CliArgs game selection", "[cli_args]") {
    SECTION("Fallout4 (explicit)") {
        ArgvBuilder ab({"classic-cli", "--game", "Fallout4"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.game == "Fallout4");
        REQUIRE(args.game_was_explicit);
    }

    SECTION("Skyrim") {
        ArgvBuilder ab({"classic-cli", "--game", "Skyrim"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.game == "Skyrim");
        REQUIRE(args.game_was_explicit);
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
        REQUIRE(args.game_version_was_explicit);
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

    SECTION("--check-yaml-updates sets YAML check flag") {
        ArgvBuilder ab({"classic-cli", "--check-yaml-updates"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.check_yaml_updates == true);
    }

    SECTION("--apply-yaml-updates sets YAML apply flag") {
        ArgvBuilder ab({"classic-cli", "--apply-yaml-updates"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.apply_yaml_updates == true);
    }

    SECTION("--rollback-yaml-updates sets YAML rollback flag") {
        ArgvBuilder ab({"classic-cli", "--rollback-yaml-updates"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.rollback_yaml_updates == true);
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
        REQUIRE(args.max_concurrent_was_explicit);
    }

    SECTION("--unsolved-logs-destination sets persistent destination") {
        ArgvBuilder ab({"classic-cli", "--unsolved-logs-destination", "C:/CLASSIC/Unsolved"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.unsolved_logs_destination == "C:/CLASSIC/Unsolved");
        REQUIRE(args.reset_unsolved_logs_destination == false);
    }

    SECTION("--reset-unsolved-logs-destination requests canonical reset") {
        ArgvBuilder ab({"classic-cli", "--reset-unsolved-logs-destination"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.reset_unsolved_logs_destination == true);
        REQUIRE(args.unsolved_logs_destination.empty());
    }
}

TEST_CASE("CliArgs combined flags", "[cli_args]") {
    ArgvBuilder ab({"classic-cli", "--game", "Skyrim", "--game-version", "VR", "--fcx-mode", "--scan-path",
                    "/tmp/crashes", "--max-concurrent", "4"});
    CliArgs args = parse_args(ab.argc(), ab.argv());

    REQUIRE(args.game == "Skyrim");
    REQUIRE(args.game_version == "VR");
    REQUIRE(args.fcx_mode == true);
    REQUIRE(args.scan_path == "/tmp/crashes");
    REQUIRE(args.max_concurrent == 4);
}

TEST_CASE("CliArgs positional input paths", "[cli_args]") {
    SECTION("single positional path") {
        ArgvBuilder ab({"classic-cli", "C:/my/crash-2024-01-01.log"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.input_paths.size() == 1);
        REQUIRE(args.input_paths[0] == "C:/my/crash-2024-01-01.log");
        REQUIRE(args.scan_path.empty());
    }

    SECTION("multiple positional paths") {
        ArgvBuilder ab({"classic-cli", "C:/logs/crash-a.log", "D:/other/dir"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.input_paths.size() == 2);
        REQUIRE(args.input_paths[0] == "C:/logs/crash-a.log");
        REQUIRE(args.input_paths[1] == "D:/other/dir");
    }

    SECTION("no positional paths leaves input_paths empty") {
        ArgvBuilder ab({"classic-cli"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.input_paths.empty());
    }

    SECTION("positional paths with flags") {
        ArgvBuilder ab({"classic-cli", "--fcx-mode", "C:/logs/crash-a.log", "--max-concurrent", "4"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.fcx_mode == true);
        REQUIRE(args.max_concurrent == 4);
        REQUIRE(args.input_paths.size() == 1);
        REQUIRE(args.input_paths[0] == "C:/logs/crash-a.log");
    }
}

TEST_CASE("CliArgs scan-path still works without positional inputs", "[cli_args]") {
    ArgvBuilder ab({"classic-cli", "--scan-path", "D:/custom"});
    CliArgs args = parse_args(ab.argc(), ab.argv());
    REQUIRE(args.scan_path == "D:/custom");
    REQUIRE(args.input_paths.empty());
}

// NOTE: Mixed --scan-path + positional inputs causes std::exit(1)
// inside parse_args, so we cannot test it with Catch2 in-process.
// That scenario is validated by the PowerShell integration test.
