#pragma once

#include "cli_args.h"
#include "user_settings_action.h"

#include "classic_cxx_bridge/scanner.h"

#include <memory>
#include <string>
#include <vector>

/// One line of native CLI presentation derived from a typed Crash Log Scan Run value.
struct CliScanRunMessage {
    bool error = false;
    std::string text;
};

/// Terminal native CLI presentation for one Crash Log Scan Run execution envelope.
struct CliScanRunPresentation {
    int exit_code = 0;
    std::vector<CliScanRunMessage> messages;
};

/// Projects CLI arguments and typed User Settings into one invariant-preserving C++ request.
///
/// Standard intent carries Rust-owned discovery facts and Unsolved Logs policy. Targeted intent
/// carries only the explicit candidate paths, so it cannot express Unsolved Logs movement.
rust::Box<classic::scanner::ScanRunRequest> build_cli_scan_run_request(const CliArgs& args,
                                                                       const PreparedScanUserSettings& settings,
                                                                       const std::string& installation_root,
                                                                       const std::string& base_directory);

/// Produces user-facing lines for one serialized Crash Log Scan Run lifecycle event.
///
/// The caller may render progress independently; returned lines contain only facts that are
/// meaningful to a CLI user, including discovery, Targeted rejections, and effective concurrency.
std::vector<CliScanRunMessage> describe_cli_scan_run_event(const classic::scanner::ScanRunContractEvent& event);

/// Produces the terminal CLI result, error diagnostics, and process exit code.
///
/// Per-log lines preserve the order supplied by the Rust contract, which is discovery order.
CliScanRunPresentation present_cli_scan_run_execution(const classic::scanner::ScanRunContractExecutionResult& execution,
                                                      double duration_seconds);

/// Owns one monotonic scan cancellation control and optionally monitors Ctrl+C on Windows.
class CliScanRunCancellation final {
public:
    /// Creates a fresh control. Tests may disable console monitoring and call request directly.
    explicit CliScanRunCancellation(bool monitor_console = true);

    /// Stops console monitoring before releasing the Rust-owned cancellation control.
    ~CliScanRunCancellation();

    CliScanRunCancellation(const CliScanRunCancellation&) = delete;
    CliScanRunCancellation& operator=(const CliScanRunCancellation&) = delete;

    /// Requests cooperative cancellation at the next Rust-owned safe seam.
    void request();

    /// Returns the cancellation control borrowed by synchronous scan execution.
    [[nodiscard]] const classic::scanner::ScanRunCancellation& token() const noexcept;

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};
