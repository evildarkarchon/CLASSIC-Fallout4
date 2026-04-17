#include "cli_args.h"
#include "scanner.h"

#include "classic_cxx_bridge/config.h"
#include "rust/cxx.h"

#include <fmt/core.h>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

/// Enable UTF-8 console output and ANSI escape sequences on Windows.
static void setup_console() {
#ifdef _WIN32
    // UTF-8 output codepage
    SetConsoleOutputCP(65001);
    SetConsoleCP(65001);

    // Enable ANSI virtual terminal processing for progress bar
    HANDLE hOut = GetStdHandle(STD_OUTPUT_HANDLE);
    if (hOut != INVALID_HANDLE_VALUE) {
        DWORD mode = 0;
        if (GetConsoleMode(hOut, &mode)) {
            mode |= ENABLE_VIRTUAL_TERMINAL_PROCESSING;
            SetConsoleMode(hOut, mode);
        }
    }
#endif
}

/// Print version string using the YAML-loaded classic_version.
static void print_version() {
    // We need to load config to get the version, but for a lightweight
    // version print we'll use a hardcoded format with build info
    fmt::print("CLASSIC CLI Scanner v9.0.0\n");
    fmt::print("C++ native build using Rust CXX bindings\n");
}

int main(int argc, char* argv[]) {
    setup_console();

    // Parse CLI arguments (may exit on --help or error)
    CliArgs args = parse_args(argc, argv);

    if (args.version_flag) {
        print_version();
        return 0;
    }

    // Print banner
    std::string mode_suffix;
    if (args.game_version != "auto") {
        mode_suffix += " " + args.game_version;
    }
    if (args.fcx_mode)
        mode_suffix += " [FCX]";

    fmt::print("CLASSIC v9.0.0 - Crash Log Scanner ({}{})\n\n", args.game, mode_suffix);

    // Run the scan pipeline
    return run_scan(args);
}
