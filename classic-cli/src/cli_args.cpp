#include "cli_args.h"
#include <CLI/CLI.hpp>
#include <thread>

CliArgs parse_args(int argc, char* argv[]) {
    CliArgs args;

    CLI::App app{"CLASSIC - Crash Log Auto Scanner & Setup Integrity Checker"};

    app.add_option("--game", args.game, "Game to scan (Fallout4, Skyrim)")
        ->default_val("Fallout4")
        ->check(CLI::IsMember({"Fallout4", "Skyrim"}));

    app.add_option("--game-version", args.game_version,
                   "Game version mode (auto, Original, NextGen, AnniversaryEdition/AE, VR)")
        ->default_val("auto")
        ->check(CLI::IsMember({"auto", "Original", "NextGen", "AnniversaryEdition", "AE", "VR"}));
    app.add_flag("--fcx-mode", args.fcx_mode, "Enable FCX enhanced analysis");
    app.add_flag("--show-fid-values", args.show_fid_values, "Show FormID database values");
    app.add_flag("--simplify-logs", args.simplify_logs, "Remove specified strings from logs");

    app.add_option("--scan-path", args.scan_path, "Custom crash log directory");

    auto cpu_count = std::thread::hardware_concurrency();
    auto recommended = (cpu_count > 2) ? (cpu_count - 2) : 2u;
    app.add_option("--max-concurrent", args.max_concurrent,
                   "Max parallel scans (0=auto, recommended: " + std::to_string(recommended) + " for " +
                       std::to_string(cpu_count) + " cores)")
        ->default_val(0)
        ->check(CLI::Range(0u, 32u));

    app.add_flag("--version", args.version_flag, "Print version and exit");

    try {
        app.parse(argc, argv);
    } catch (const CLI::ParseError& e) {
        std::exit(app.exit(e));
    }

    if (args.game_version == "AE") {
        args.game_version = "AnniversaryEdition";
    }

    return args;
}
