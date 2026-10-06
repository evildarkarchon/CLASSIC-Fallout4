#pragma once

#include <optional>
#include <string>

/// The two process facts the CLI's Installation Root search starts from.
///
/// Both are UTF-8 path strings. An empty field means the fact was unavailable, and Config's
/// locator then skips only the candidates derived from it. Commands take this as an explicit
/// input (see the `run_*` overloads) so tests can point the search at a folder that holds no
/// `CLASSIC Data` regardless of where the test binary itself was built.
struct CliProcessLocation {
    std::string executable_dir;
    std::string working_dir;
};

/// Exit code every CLI command returns when no Installation Root was found.
///
/// It matches the commands' existing "fatal before any work" code: nothing was scanned,
/// checked, or written.
inline constexpr int kCliInstallationRootNotFoundExitCode = 2;

/// Reads this process's executable folder and working directory.
///
/// Either field is left empty when the platform cannot report it; neither is substituted for
/// the other.
CliProcessLocation current_cli_process_location();

/// Locates the Installation Root through Config's shared locator.
///
/// Delegates the whole candidate search to `classic::config::locate_installation_root`, the
/// same search the GUI, TUI, and update-core use. Returns `std::nullopt` when no candidate holds
/// `CLASSIC Data`; there is deliberately no working-directory fallback, because opening User
/// Settings or scanning somewhere else would silently treat the wrong folder as the installation.
std::optional<std::string> locate_cli_installation_root(const CliProcessLocation& location);

/// Builds the user-facing "CLASSIC Data not found" message for a failed search.
///
/// Names both search starts so a user can see which folders were tried from.
std::string cli_installation_root_not_found_message(const CliProcessLocation& location);

/// Locates the Installation Root, printing the "CLASSIC Data not found" message to stderr on a miss.
///
/// Callers return `kCliInstallationRootNotFoundExitCode` when this yields `std::nullopt`, before
/// initializing the runtime or doing any scan or update work.
std::optional<std::string> require_cli_installation_root(const CliProcessLocation& location);
