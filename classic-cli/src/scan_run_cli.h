#pragma once

#include "cli_args.h"
#include "user_settings_action.h"

#include "classic_cxx_bridge/scanner.h"

#include <functional>
#include <iosfwd>
#include <memory>
#include <optional>
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
/// expresses dismissal by settling the pending recovery with no decision, which Rust turns into a
/// cancelled run that touches no file.
enum class CliLocalIgnoreRecoveryChoice {
    ProceedWithoutIgnore,
    ResetToDefault,
    Cancel,
};

/// One Local Ignore recovery decision as Rust describes it, flattened into CLI-owned values.
///
/// A copy rather than a view onto the bridged envelope: the prompt seam is a plain value a test can
/// build and a caller can hold after the envelope has moved on.
struct CliLocalIgnoreRecoveryDecisionOption {
    /// The decision to hand back when this option is chosen.
    classic::scanner::ScanRunLocalIgnoreRecoveryDecision decision =
        classic::scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore;
    /// The decision's Display Label, as Rust resolved it.
    std::string label;
    /// What choosing it will actually do, in Rust's words.
    std::string description;
    /// Whether this run can honor the decision.
    ///
    /// False when the selected Main YAML Data retained no usable default Local Ignore to publish.
    /// Offering it anyway spends the one-shot continuation on a typed failure, leaving the user
    /// with no scan, no repair, and no second attempt without re-running from scratch.
    ///
    /// Defaults to false so a partially built option is withheld rather than offered. Rust decides
    /// this; the CLI never infers it.
    bool available = false;
};

/// Run-level facts the native CLI presents before it asks for an explicit recovery decision.
///
/// Availability travels on each decision rather than as one flag beside them, which is what makes
/// honouring it take no separate lookup: a menu cannot print an option without having read the
/// field that says whether it can succeed. The bracketed letters beside the labels are still this
/// frontend's own — the labels and the sentences are not.
struct CliLocalIgnoreRecoveryPresentation {
    /// Lines explaining why recovery is required, in the order they should be printed.
    std::vector<CliScanRunMessage> details;
    /// Every decision the continuation contract accepts, in Rust's declared order.
    ///
    /// Carries the unavailable ones too. A menu that must explain the absence it is about to
    /// create can only do so if it is told what is being withheld, so filtering happens where the
    /// option is printed rather than where the list is built.
    std::vector<CliLocalIgnoreRecoveryDecisionOption> decisions;
};

/// Console decision seam invoked while the CLI holds the run's unsettled pending recovery.
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
/// reach an Autoscan Report. Every word of them, and every word of the decision descriptions, comes
/// from Rust: the run's rendered display lines on the envelope, and `prompt`, the Display Content
/// the pending recovery carries (`scan_run_pending_recovery_prompt`). The CLI applies no policy of
/// its own beyond what the run reported.
///
/// This takes the whole execution envelope rather than the run result, because the rendered display
/// lines travel on the envelope. It presents all of them rather than trying to pick the Installed
/// YAML Data block back out: Rust exposes that block only as part of the rendered run, so selecting
/// it by position would be a structural assumption about a sequence that carries no structure. Every
/// surrounding line describes the very run the user is being asked to decide about.
///
/// Rust's own prompt lines are appended last so the question sits immediately above the menu in a
/// scrolling terminal, rather than at the top of a block the user has already scrolled past.
CliLocalIgnoreRecoveryPresentation describe_cli_local_ignore_recovery(
    const classic::scanner::ScanRunContractExecutionResult& execution,
    const classic::scanner::ScanRunRecoveryPrompt& prompt);

/// Reads one explicit recovery choice from an interactive console stream pair.
///
/// Returns `Cancel` without consuming input when `cancellation` was already requested, and returns
/// `Cancel` on end-of-input or after `CLI_LOCAL_IGNORE_RECOVERY_PROMPT_ATTEMPTS` unusable answers.
/// No input path can ever select `ResetToDefault` implicitly.
///
/// A decision whose `available` is false is neither printed nor accepted: its letter and its long
/// word are rejected exactly like any other unrecognized answer, and the bracketed letters narrow
/// to just the offered ones. An option the run has already reported it cannot honor is not an
/// option, and choosing it would spend the single-use pending recovery on a guaranteed failure. The
/// menu, the bracketed letters, the retry hint, and the accepted answers are all derived from
/// `decisions`, so none of them can advertise something another withheld.
///
/// Cancel is always offered and is never in `decisions`: Rust models backing out as the *absence*
/// of a decision, settled with no decision, so its letter and its wording stay this frontend's own.
///
/// Responsiveness caveat: cancellation is re-checked only after the console read returns, so Ctrl+C
/// pressed while the read is still blocked is honored when the read completes rather than
/// immediately. That affects only how quickly the question closes; the answer is discarded either
/// way, so a late Ctrl+C can never authorize a reset.
CliLocalIgnoreRecoveryChoice read_cli_local_ignore_recovery_choice(
    std::istream& input, std::ostream& output, const CliScanRunCancellation& cancellation,
    const std::vector<CliLocalIgnoreRecoveryDecisionOption>& decisions);

/// The native CLI's observer delivery failure policy, passed to both execution and settling.
///
/// The CLI has always stopped a run whose progress presentation failed, so it asks Rust to cancel
/// the run's own control at the first failed delivery. Rust applies the policy and reports the
/// failure on the envelope; the CLI's observer only reports that a delivery failed.
inline constexpr classic::scanner::ScanRunObserverFailurePolicy CLI_SCAN_RUN_OBSERVER_FAILURE_POLICY =
    classic::scanner::ScanRunObserverFailurePolicy::CancelRun;

/// Terminal envelope after any pending Local Ignore recovery has been settled.
struct CliScanRunExecutionOutcome {
    classic::scanner::ScanRunContractExecutionResult execution;
    /// True when the run's pending recovery was settled, with or without a decision.
    ///
    /// Cancel counts, and so does a run already cancelled before the question could be asked:
    /// both settle with no decision. False for a non-interactive run, which reports the paused
    /// envelope without settling.
    bool local_ignore_recovery_settled = false;
    /// The decision the CLI passed to settling; empty when it settled with no decision or did not
    /// settle at all.
    std::optional<classic::scanner::ScanRunLocalIgnoreRecoveryDecision> settled_decision;
};

/// Executes one Crash Log Scan Run and settles any pending Local Ignore recovery through `prompt`.
///
/// Executes under `CLI_SCAN_RUN_OBSERVER_FAILURE_POLICY`, then hands the operation to
/// `resolve_cli_local_ignore_recovery`. A `Local Ignore Recovery Required` result is an expected
/// outcome, not a failure.
CliScanRunExecutionOutcome execute_cli_scan_run(const classic::scanner::ScanRunRequest& request,
                                                CliScanRunCancellation& cancellation,
                                                const classic::scanner::ScanRunObserver* observer,
                                                const CliLocalIgnoreRecoveryPrompt& prompt);

/// Settles the pending recovery of an already executed operation, if it has one.
///
/// The recovery flow is: check for a pending recovery; when the pending recovery reports its run
/// already cancelled, settle with no decision and never call `prompt`; otherwise describe the
/// pending recovery's prompt, ask `prompt`, and settle with the chosen decision, or with no
/// decision when the user cancels. The pending recovery is settled exactly once, under
/// `CLI_SCAN_RUN_OBSERVER_FAILURE_POLICY`, and the settled envelope replaces the paused one.
///
/// When the operation has no pending recovery its envelope is returned as is. When `prompt` is
/// empty the paused envelope is returned unsettled, so a non-interactive caller never makes an
/// implicit choice.
///
/// Exposed separately from `execute_cli_scan_run` so a test can cancel the run's control between
/// the pause and the check, which in production only Ctrl+C can do. `operation` must have been
/// executed with `CLI_SCAN_RUN_OBSERVER_FAILURE_POLICY`.
CliScanRunExecutionOutcome resolve_cli_local_ignore_recovery(classic::scanner::ScanRunContractExecution& operation,
                                                             const classic::scanner::ScanRunObserver* observer,
                                                             const CliLocalIgnoreRecoveryPrompt& prompt);

/// Produces the terminal CLI presentation for one resolved scan-run outcome.
///
/// An observer delivery failure the run reported is printed first, on stderr, as a warning. It
/// does not change the exit code: Rust already applied the CLI's cancel policy to the run, and
/// its status already decides the exit code.
CliScanRunPresentation present_cli_scan_run_outcome(const CliScanRunExecutionOutcome& outcome,
                                                    double duration_seconds);
