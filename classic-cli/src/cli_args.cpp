#include "cli_args.h"
#include <algorithm>
#include <CLI/CLI.hpp>
#include <filesystem>
#include <fmt/core.h>
#include <thread>

namespace fs = std::filesystem;

uint32_t auto_concurrency_for_cpu_count(uint32_t cpu_count) {
    auto recommended = std::max(cpu_count, 4u) - 2u;
    return std::min(recommended, 32u);
}

uint32_t effective_concurrency(uint32_t requested, uint32_t cpu_count) {
    if (requested > 0) {
        return requested;
    }
    return auto_concurrency_for_cpu_count(cpu_count);
}

CliArgs parse_args(int argc, char* argv[]) {
    CliArgs args;

    CLI::App app{"CLASSIC - Crash Log Auto Scanner & Setup Integrity Checker"};

    auto* game_option = app.add_option("--game", args.game, "Game to scan (Fallout4, Skyrim)")
        ->default_val("Fallout4")
        ->check(CLI::IsMember({"Fallout4", "Skyrim"}));

    auto* game_version_option = app.add_option(
        "--game-version", args.game_version,
        "Game version mode (auto, Original, NextGen, AnniversaryEdition/AE, VR)")
        ->default_val("auto")
        ->check(CLI::IsMember({"auto", "Original", "NextGen", "AnniversaryEdition", "AE", "VR"}));
    app.add_flag("--fcx-mode", args.fcx_mode, "Enable FCX local file checks and enhanced analysis");
    app.add_flag("--show-fid-values", args.show_fid_values, "Show FormID database values");
    app.add_flag("--simplify-logs", args.simplify_logs, "Remove specified strings from logs");

    app.add_option("--scan-path", args.scan_path, "Custom crash log directory");
    app.add_option("--unsolved-logs-destination", args.unsolved_logs_destination,
                   "Persist an absolute folder for Unsolved Logs relocation");
    app.add_flag("--reset-unsolved-logs-destination", args.reset_unsolved_logs_destination,
                 "Reset Unsolved Logs relocation to the canonical CLASSIC backup folder");

    auto cpu_count = std::thread::hardware_concurrency();
    auto recommended = auto_concurrency_for_cpu_count(cpu_count);
    auto* max_concurrent_option = app.add_option(
        "--max-concurrent", args.max_concurrent,
        "Max parallel scans (0=auto, recommended: " + std::to_string(recommended) + " for " +
            std::to_string(cpu_count) + " cores)")
        ->default_val(0)
        ->check(CLI::Range(0u, 32u));

    app.add_flag("--version", args.version_flag, "Print version and exit");

    app.add_flag("--check-yaml-updates", args.check_yaml_updates,
                 "Check for CLASSIC data-file updates and print the result (no install)");
    app.add_flag("--apply-yaml-updates", args.apply_yaml_updates,
                 "Prompt for and apply any available CLASSIC data-file updates");
    app.add_flag("--rollback-yaml-updates", args.rollback_yaml_updates,
                 "Roll back installed CLASSIC data files to their previous cached generation");
    app.add_flag("--check-app-update", args.check_app_update,
                 "Check the CLASSIC app-update notification manifest and print the result");

    app.add_option("input_paths", args.input_paths, "Crash log files or directories to scan (targeted mode)");

    try {
        app.parse(argc, argv);
    } catch (const CLI::ParseError& e) {
        std::exit(app.exit(e));
    }

    if (!args.input_paths.empty() && !args.scan_path.empty()) {
        fmt::print(stderr, "Error: cannot combine --scan-path with positional input paths.\n"
                           "Use --scan-path OR positional paths, not both.\n");
        std::exit(1);
    }

    if (!args.unsolved_logs_destination.empty() && args.reset_unsolved_logs_destination) {
        fmt::print(stderr, "Error: cannot combine --unsolved-logs-destination with "
                           "--reset-unsolved-logs-destination.\n");
        std::exit(1);
    }

    if (!args.unsolved_logs_destination.empty() && !fs::path(args.unsolved_logs_destination).is_absolute()) {
        fmt::print(stderr, "Error: --unsolved-logs-destination must be an absolute path.\n");
        std::exit(1);
    }

    if (args.game_version == "AE") {
        args.game_version = "AnniversaryEdition";
    }

    // CLI11 applies default values before returning, so retain presence separately
    // to distinguish an explicit override from a value that should come from User Settings.
    args.game_was_explicit = game_option->count() > 0;
    args.game_version_was_explicit = game_version_option->count() > 0;
    args.max_concurrent_was_explicit = max_concurrent_option->count() > 0;

    return args;
}
