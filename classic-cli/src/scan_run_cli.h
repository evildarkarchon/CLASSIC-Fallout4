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

/// Flattens one Rust-rendered display line into plain CLI text.
///
/// Segments are concatenated in the order Rust put them in, separated by single spaces, with no
/// styling of any kind: a `Path` prints whole, a `Count` prints its value followed by the noun Rust
/// already agreed with that value, and a `Label` prints as handed over. Shared wording must not push
/// terminal styling into a user's logs, so this frontend's per-segment "styling" is the empty
/// choice.
///
/// Exposed for the renderer-conformance test, which asserts ordering and the count's noun without
/// re-pinning wording that `classic-scan-presentation` already pins once.
std::string render_cli_display_line(const classic::scanner::ScanRunDisplayLine& line);

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
/// The words come from Rust, already rendered on the observer callback before the event crossed the
/// bridge. What stays the CLI's own choice is which event kinds are worth a durable console line at
/// all: `LogQueued` and `LogPhase` are omitted because the progress display already covers them and
/// a line per phase per log would bury everything else. Omitting whole lines is what an adapter is
/// allowed to do; rewording the ones it keeps is not.
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

/// Run-level facts the native CLI presents before it asks for an explicit recovery decision.
///
/// `reset_available` travels with the diagnostics rather than beside them so a prompt cannot offer
/// Reset To Default without having been handed the fact that decides whether it can succeed. The
/// TUI's `LocalIgnoreRecoveryPrompt` has the same shape for the same reason.
struct CliLocalIgnoreRecoveryPresentation {
    /// Lines explaining why recovery is required, in the order they should be printed.
    std::vector<CliScanRunMessage> details;
    /// Whether Reset To Default is a decision this run can actually satisfy.
    ///
    /// False when the selected Main YAML Data retained no usable default Local Ignore to publish.
    /// Offering it anyway spends the one-shot continuation on a typed failure, leaving the user
    /// with no scan, no repair, and no second attempt without re-running from scratch.
    bool reset_available = true;
};

/// Console decision seam invoked while Rust still retains the single-use recovery continuation.
///
/// The callback receives the run-level recovery presentation and owns printing it, so tests can
/// assert the offered facts without driving a real terminal.
using CliLocalIgnoreRecoveryPrompt =
    std::function<CliLocalIgnoreRecoveryChoice(const CliLocalIgnoreRecoveryPresentation& recovery)>;

/// Number of malformed console answers tolerated before the prompt gives up and cancels.
inline constexpr int CLI_LOCAL_IGNORE_RECOVERY_PROMPT_ATTEMPTS = 3;

/// Builds the run-level presentation explaining why Local Ignore recovery is required.
///
/// The lines carry retained Installed YAML Data facts and structured diagnostics only; they never
/// reach an Autoscan Report. `reset_available` is read straight from the retained Installed YAML
/// Data, so the CLI applies no policy of its own beyond what the run reported.
///
/// This takes the whole execution envelope rather than the run result, because the rendered display
/// lines travel on the envelope. It presents all of them rather than trying to pick the Installed
/// YAML Data block back out: Rust exposes that block only as part of the rendered run, so selecting
/// it by position would be a structural assumption about a sequence that carries no structure. Every
/// surrounding line describes the very run the user is being asked to decide about.
CliLocalIgnoreRecoveryPresentation describe_cli_local_ignore_recovery(
    const classic::scanner::ScanRunContractExecutionResult& execution);

/// Reads one explicit recovery choice from an interactive console stream pair.
///
/// Returns `Cancel` without consuming input when `cancellation` was already requested, and returns
/// `Cancel` on end-of-input or after `CLI_LOCAL_IGNORE_RECOVERY_PROMPT_ATTEMPTS` unusable answers.
/// No input path can ever select `ResetToDefault` implicitly.
///
/// When `reset_available` is false the reset option is neither printed nor accepted: `r` and
/// `reset` are rejected exactly like any other unrecognized word, and the bracketed letters narrow
/// to `[P/C]`. An option the run has already reported it cannot honor is not an option, and
/// choosing it would spend the single-use continuation on a guaranteed failure.
///
/// Responsiveness caveat: cancellation is re-checked only after the console read returns, so Ctrl+C
/// pressed while the read is still blocked is honored when the read completes rather than
/// immediately. That affects only how quickly the question closes; the answer is discarded either
/// way, so a late Ctrl+C can never authorize a reset.
CliLocalIgnoreRecoveryChoice read_cli_local_ignore_recovery_choice(std::istream& input, std::ostream& output,
                                                                   const CliScanRunCancellation& cancellation,
                                                                   bool reset_available);

/// Terminal envelope after any Local Ignore recovery decision has been applied.
struct CliScanRunExecutionOutcome {
    classic::scanner::ScanRunContractExecutionResult execution;
    /// True when the retained single-use continuation was consumed by one explicit answer.
    ///
    /// Cancel counts: it is an explicit answer that consumes the continuation with a
    /// non-destructive decision after cancellation has already been requested.
    bool local_ignore_continuation_consumed = false;
    /// Actionable lines for a recovery invariant the CLI could not honor. Empty in every normal run.
    std::vector<CliScanRunMessage> recovery_diagnostics;
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

/// Produces the terminal CLI presentation for one resolved scan-run outcome.
///
/// Recovery invariant diagnostics are reported ahead of the terminal envelope and force the
/// infrastructure exit code, because a recovery the CLI could not honor is never a usable result.
CliScanRunPresentation present_cli_scan_run_outcome(const CliScanRunExecutionOutcome& outcome,
                                                    double duration_seconds);
