#pragma once

#include "cli_args.h"
#include "user_settings_action.h"

#include "classic_cxx_bridge/scanner.h"

#include <functional>
#include <iosfwd>
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

/// Explicit native CLI response to a malformed Local Ignore file found by an active scan run.
///
/// `Cancel` is a presentation-only outcome. Rust owns exactly two recovery decisions, so the CLI
/// expresses dismissal by requesting cancellation before it resumes the retained continuation.
enum class CliLocalIgnoreRecoveryChoice {
    ProceedWithoutIgnore,
    ResetToDefault,
    Cancel,
};

/// Console decision seam invoked while Rust still retains the single-use recovery continuation.
///
/// The callback receives the run-level recovery diagnostics and owns presenting them, so tests can
/// assert the offered facts without driving a real terminal.
using CliLocalIgnoreRecoveryPrompt =
    std::function<CliLocalIgnoreRecoveryChoice(const std::vector<CliScanRunMessage>& recovery_details)>;

/// Number of malformed console answers tolerated before the prompt gives up and cancels.
inline constexpr int CLI_LOCAL_IGNORE_RECOVERY_PROMPT_ATTEMPTS = 3;

/// Builds the run-level lines explaining why Local Ignore recovery is required.
///
/// The lines carry retained Installed YAML Data facts and structured diagnostics only; they never
/// reach an Autoscan Report.
std::vector<CliScanRunMessage> describe_cli_local_ignore_recovery(
    const classic::scanner::ScanRunContractRunResult& result);

/// Reads one explicit recovery choice from an interactive console stream pair.
///
/// Returns `Cancel` without consuming input when `cancellation` was already requested, and returns
/// `Cancel` on end-of-input or after `CLI_LOCAL_IGNORE_RECOVERY_PROMPT_ATTEMPTS` unusable answers.
/// No input path can ever select `ResetToDefault` implicitly.
CliLocalIgnoreRecoveryChoice read_cli_local_ignore_recovery_choice(std::istream& input, std::ostream& output,
                                                                   const CliScanRunCancellation& cancellation);

/// Terminal envelope after any Local Ignore recovery decision has been applied.
struct CliScanRunExecutionOutcome {
    classic::scanner::ScanRunContractExecutionResult execution;
    /// True when a retained continuation was consumed by one explicit user choice.
    bool resumed_after_local_ignore_recovery = false;
};

/// Executes one Crash Log Scan Run and resolves Local Ignore recovery through `prompt`.
///
/// A `Local Ignore Recovery Required` result is an expected outcome, not a failure: the retained
/// continuation is consumed exactly once with the chosen decision and resumes the same discovery.
/// When no prompt is supplied, or the run did not retain a continuation, the initial recovery
/// envelope is returned unchanged so non-interactive callers never make an implicit choice.
CliScanRunExecutionOutcome execute_cli_scan_run(const classic::scanner::ScanRunRequest& request,
                                                CliScanRunCancellation& cancellation,
                                                const classic::scanner::ScanRunObserver* observer,
                                                const CliLocalIgnoreRecoveryPrompt& prompt);
