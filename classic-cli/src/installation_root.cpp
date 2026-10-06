#include "installation_root.h"

#include "rust/cxx.h"

#include "classic_cxx_bridge/config.h"

#include <fmt/core.h>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

#include <cstdio>
#include <filesystem>
#include <system_error>

namespace fs = std::filesystem;

namespace {

/// Converts a filesystem path to UTF-8 without going through the ANSI code page.
///
/// `fs::path::string()` narrows through the active code page on Windows, which mangles (or throws
/// on) characters outside it. The CXX bridge takes UTF-8 `&str`, so the path is narrowed as UTF-8.
std::string path_to_utf8(const fs::path& path) {
    const std::u8string utf8 = path.u8string();
    return std::string(utf8.begin(), utf8.end());
}

/// Renders an optional process fact for the not-found message.
std::string describe(const std::string& path) {
    return path.empty() ? std::string("(unavailable)") : path;
}

} // namespace

CliProcessLocation current_cli_process_location() {
    CliProcessLocation location;

#ifdef _WIN32
    wchar_t buffer[MAX_PATH];
    const DWORD length = GetModuleFileNameW(nullptr, buffer, MAX_PATH);
    // A zero length is a failure and MAX_PATH means the path was truncated; either way the
    // executable folder is unknown, so it stays empty rather than naming a wrong folder.
    if (length > 0 && length < MAX_PATH) {
        location.executable_dir = path_to_utf8(fs::path(buffer).parent_path());
    }
#endif

    std::error_code ec;
    const fs::path working_dir = fs::current_path(ec);
    if (!ec) {
        location.working_dir = path_to_utf8(working_dir);
    }
    return location;
}

std::optional<std::string> locate_cli_installation_root(const CliProcessLocation& location) {
    const rust::String located = classic::config::locate_installation_root(
        rust::Str(location.executable_dir.data(), location.executable_dir.size()),
        rust::Str(location.working_dir.data(), location.working_dir.size()));
    if (located.empty()) {
        return std::nullopt;
    }
    return std::string(located.data(), located.size());
}

std::string cli_installation_root_not_found_message(const CliProcessLocation& location) {
    return fmt::format("CLASSIC Data not found. Run classic-cli from the CLASSIC installation folder, or place "
                       "it next to the CLASSIC Data folder.\n  Executable folder: {}\n  Working directory: {}",
                       describe(location.executable_dir), describe(location.working_dir));
}

std::optional<std::string> require_cli_installation_root(const CliProcessLocation& location) {
    auto root = locate_cli_installation_root(location);
    if (!root) {
        fmt::print(stderr, "{}\n", cli_installation_root_not_found_message(location));
    }
    return root;
}
