#include "scan_run_cli.h"
#include "user_settings_action.h"

#include "classic_cxx_bridge/shared.h"

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

#include <algorithm>
#include <atomic>
#include <cctype>
#include <chrono>
#include <cstdint>
#include <fmt/format.h>
#include <istream>
#include <optional>
#include <ostream>
#include <stdexcept>
#include <string_view>
#include <thread>
#include <utility>

namespace {

namespace scanner = classic::scanner;

#ifdef _WIN32
std::atomic_bool g_console_cancel_requested{false};

/// Publishes Ctrl+C/Break without crossing into Rust from the system callback thread.
BOOL WINAPI handle_console_control(DWORD control_type) {
    if (control_type != CTRL_C_EVENT && control_type != CTRL_BREAK_EVENT) {
        return FALSE;
    }

    // The console callback may run on a system thread. It only publishes an
    // atomic request; the monitor thread calls Rust outside the callback.
    g_console_cancel_requested.store(true, std::memory_order_release);
    return TRUE;
}
#endif

std::string to_std_string(const rust::String& value) {
    return std::string(value.data(), value.size());
}

/// Chooses a noun form for the one sentence this frontend still writes.
///
/// Exactly one caller remains: the Local Ignore recovery prompt's retained-discovery line. That
/// prompt's prose is still the CLI's because the recovery renderer lands with the gated recovery
/// phase, not with this one. Every other count the CLI prints is now a `Count` segment whose noun
/// Rust already agreed with its value. The TUI kept its own copy on the same terms.
std::string plural(std::size_t count, std::string singular, std::string plural_value) {
    return count == 1 ? std::move(singular) : std::move(plural_value);
}

// What a Crash Log Scan Run says is decided in Rust, by `classic-scan-presentation`, and reaches
// this file already rendered into display lines on the execution envelope and on every observed
// event. This file used to compose those sentences itself, next to a GUI and a TUI composing their
// own, which is why the same run read differently depending on which frontend a user opened.
//
// What survives here is Display Layout, and only that: which section comes first, which event kinds
// earn a durable line, which stream a line is routed to, the exit code, and the run-level totals
// this process measured and Rust never saw. None of it changes a word.
//
// Display Labels are no longer read through the seven `scan_run_*_label` bridge entry points either.
// Those entry points remain the correct surface for labelling a domain enum *outside* a display
// line, and the GUI still uses them; this frontend simply no longer renders any enum that way, since
// every label it prints now arrives inside a `Label` segment. Re-deriving one would risk disagreeing
// with the sentence built around it.
//
// `tests/test_display_label_audit.cpp` is what stops local vocabulary growing back. It reads this
// file as text, so it catches shapes the compiler cannot object to.

/// Which output stream a block of rendered display lines is routed to.
enum class CliLineRouting {
    /// Route each line by the severity Rust gave it.
    ///
    /// `Warning` and `Failure` go to stderr; `Info`, `Notice`, and `Success` go to stdout. The cut
    /// falls there because stderr is where this frontend has always put what needs the user's
    /// attention — a failed log, a setup failure, a run paused awaiting a Local Ignore decision —
    /// while stdout carries the run's ordinary narrative. Rust names the severity; which stream
    /// that means is this frontend's choice, and no wording changes either way.
    BySeverity,
    /// Route every line to stderr, whatever its severity.
    ///
    /// Used for the two failure envelopes, whose detail lines are neutral facts about a failure
    /// rather than failures themselves. Routing them by severity would split one diagnostic across
    /// two streams, so redirecting stdout would separate "failed during discovery" from the path it
    /// failed on.
    AllToStderr,
};

/// Returns whether one observed event is worth a durable console line.
///
/// This is the whole of the CLI's remaining say over live progress. Rust renders every event
/// kind; queued and phase events are dropped here because the progress display already conveys
/// both, and a line per phase per log would bury the discovery and outcome lines around them.
/// Omitting whole lines is what an adapter may do — rewording the ones it keeps is not.
bool event_earns_a_durable_line(scanner::ScanRunContractEventKind kind) {
    switch (kind) {
    case scanner::ScanRunContractEventKind::LogQueued:
    case scanner::ScanRunContractEventKind::LogPhase:
        return false;
    case scanner::ScanRunContractEventKind::DiscoveryCompleted:
    case scanner::ScanRunContractEventKind::EffectiveConcurrencySelected:
    case scanner::ScanRunContractEventKind::LogStarted:
    case scanner::ScanRunContractEventKind::LogFinished:
        break;
    }
    return true;
}

/// Returns whether a line of this severity belongs on stderr.
bool severity_reaches_stderr(scanner::ScanRunDisplaySeverity severity) {
    switch (severity) {
    case scanner::ScanRunDisplaySeverity::Warning:
    case scanner::ScanRunDisplaySeverity::Failure:
        return true;
    case scanner::ScanRunDisplaySeverity::Info:
    case scanner::ScanRunDisplaySeverity::Notice:
    case scanner::ScanRunDisplaySeverity::Success:
        break;
    }
    return false;
}

/// Appends one rendered block, preserving Rust's line order.
///
/// Returns whether anything was appended, so a caller reporting a failure can tell a described
/// failure apart from one that crossed the bridge with nothing to say.
bool append_display_lines(const rust::Vec<scanner::ScanRunDisplayLine>& lines,
                          std::vector<CliScanRunMessage>& messages,
                          CliLineRouting routing = CliLineRouting::BySeverity) {
    for (const auto& line : lines) {
        const bool to_stderr =
            routing == CliLineRouting::AllToStderr || severity_reaches_stderr(line.severity);
        messages.push_back({to_stderr, render_cli_display_line(line)});
    }
    return !lines.empty();
}

/// Appends all present run-scoped FCX setup facts, diagnostics, and actions.
void append_setup_messages(const scanner::ScanRunContractRunResult& result, std::vector<CliScanRunMessage>& messages) {
    if (!result.has_setup) {
        return;
    }

    messages.push_back({false, fmt::format("FCX setup: {}", to_std_string(result.setup.status))});
    if (result.setup.has_message) {
        messages.push_back({false, fmt::format("  {}", to_std_string(result.setup.message))});
    }
    if (!result.setup.rendered_report.empty()) {
        messages.push_back({false, to_std_string(result.setup.rendered_report)});
    }
    for (const auto& check : result.setup.checks) {
        messages.push_back({false, fmt::format("  [{}] {}: {}", to_std_string(check.state), to_std_string(check.kind),
                                               to_std_string(check.message))});
        for (const auto& detail : check.details) {
            messages.push_back({false, fmt::format("    {}", to_std_string(detail))});
        }
    }
    for (const auto& update : result.setup.path_updates) {
        messages.push_back(
            {false, fmt::format("  Proposed {} path: {}", to_std_string(update.kind), to_std_string(update.path))});
    }
    for (const auto& issue : result.setup.configuration_issues) {
        const auto section = issue.has_section ? fmt::format("/[{}]", to_std_string(issue.section_or_empty)) : "";
        messages.push_back(
            {false, fmt::format("  [{}] {}{} {}: {} (current: {}, recommended: {})", to_std_string(issue.severity),
                                to_std_string(issue.file_path), section, to_std_string(issue.setting),
                                to_std_string(issue.description), to_std_string(issue.current_value),
                                to_std_string(issue.recommended_value))});
    }
    for (const auto& action : result.setup.actions) {
        messages.push_back({false, fmt::format("  Action: {}", to_std_string(action))});
    }
    for (const auto& error : result.setup.fatal_errors) {
        messages.push_back({true, fmt::format("  Setup error: {}", to_std_string(error))});
    }
}

/// Trims surrounding whitespace and lowercases one console answer for choice matching.
std::string normalize_console_answer(const std::string& answer) {
    const auto first = answer.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) {
        return {};
    }
    const auto last = answer.find_last_not_of(" \t\r\n");
    std::string normalized = answer.substr(first, last - first + 1);
    std::transform(normalized.begin(), normalized.end(), normalized.begin(),
                   [](unsigned char character) { return static_cast<char>(std::tolower(character)); });
    return normalized;
}

/// The console affordance this frontend binds to one Rust-owned recovery decision.
///
/// Display Layout, and all that is left of a choice line the CLI still decides: the label and the
/// sentence beside it arrive already worded on the bridged prompt.
struct CliRecoveryAffordance {
    /// The bracketed letter shown in the menu and in the offered-letters hint.
    char letter;
    /// The spelled-out word accepted as an equivalent answer.
    std::string_view word;
    /// The presentation-level choice this decision resolves to when chosen.
    CliLocalIgnoreRecoveryChoice choice;
};

/// Returns the letter, long word, and resolved choice for one decision.
///
/// One switch rather than two beside each other: a decision's key and the choice that key produces
/// are the same fact seen twice, and two exhaustive switches over one enum can drift by exactly one
/// clause. Exhaustive rather than table-driven so a third decision added to the contract trips
/// `-Wswitch` here — a decision the menu cannot name is one it must not print, and silently falling
/// through to a placeholder letter would print exactly that.
CliRecoveryAffordance recovery_affordance(scanner::ScanRunLocalIgnoreRecoveryDecision decision) {
    switch (decision) {
    case scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore:
        return {'P', "proceed", CliLocalIgnoreRecoveryChoice::ProceedWithoutIgnore};
    case scanner::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault:
        return {'R', "reset", CliLocalIgnoreRecoveryChoice::ResetToDefault};
    }
    // Unreachable for a valid enumerator. An empty word and a letter no answer can spell keep an
    // unrecognized decision unofferable rather than mapping it onto another decision's key, and
    // Cancel is the safe resolution if one is somehow chosen: it cannot touch the user's files.
    return {'?', "", CliLocalIgnoreRecoveryChoice::Cancel};
}

/// Returns the bracketed hint printed beside the cursor, such as `[P/R/C]`.
std::string format_offered_letters(const std::vector<char>& offered) {
    std::string joined;
    for (const char letter : offered) {
        if (!joined.empty()) {
            joined += '/';
        }
        joined += letter;
    }
    return fmt::format("[{}]", joined);
}

/// Returns the sentence printed after an unusable answer, such as `Enter P, R, or C.`.
///
/// Derived from the same letters the bracketed hint is, so the two cannot disagree about what was
/// offered. Separate from that hint because a retry is a sentence the user reads after a mistake
/// rather than a label beside the cursor: the serial comma appears only for three or more, which is
/// what keeps two options reading as `Enter P or C.` instead of as a list.
std::string format_retry_hint(const std::vector<char>& offered) {
    std::string hint = "Unrecognized answer. Enter ";
    for (std::size_t index = 0; index < offered.size(); ++index) {
        if (index > 0) {
            hint += index + 1 == offered.size() ? (offered.size() > 2 ? ", or " : " or ") : ", ";
        }
        hint += offered[index];
    }
    hint += ".\n";
    return hint;
}

/// Maps one normalized console answer onto an explicit choice, or nothing when unusable.
///
/// Every other answer is rejected rather than defaulted, because a mistyped answer must never
/// mutate Local Ignore YAML Data.
///
/// The accepted set is derived from `decisions` rather than written out, so it is the same list the
/// menu printed from and the two cannot disagree. An unavailable decision is skipped here for the
/// same reason it is skipped there: the menu did not print it, so accepting its letter anyway would
/// honor a decision the run was never offered — and spend its one-shot continuation on a failure.
bool match_recovery_choice(std::string_view answer,
                           const std::vector<CliLocalIgnoreRecoveryDecisionOption>& decisions,
                           CliLocalIgnoreRecoveryChoice& choice) {
    if (answer == "c" || answer == "cancel") {
        choice = CliLocalIgnoreRecoveryChoice::Cancel;
        return true;
    }
    for (const auto& option : decisions) {
        if (!option.available) {
            continue;
        }
        const auto affordance = recovery_affordance(option.decision);
        const std::string letter(1, static_cast<char>(std::tolower(static_cast<unsigned char>(affordance.letter))));
        if (answer == letter || (!affordance.word.empty() && answer == affordance.word)) {
            choice = affordance.choice;
            return true;
        }
    }
    return false;
}

/// Renders one segment as plain text, reading only the field its kind selects.
///
/// The bridge flattens Rust's six-variant segment into a kind tag plus a text, a path, and a count
/// field, so every branch here is a read rather than a decision. The one branch that composes,
/// `Count`, prints the value beside the noun Rust already resolved to agree with it — it never
/// re-decides that noun, which is what stops a CLI user ever reading "1 logs".
std::string render_cli_display_segment(const scanner::ScanRunDisplaySegment& segment) {
    switch (segment.kind) {
    case scanner::ScanRunDisplaySegmentKind::Count:
        return fmt::format("{} {}", segment.count, to_std_string(segment.text));
    case scanner::ScanRunDisplaySegmentKind::Path:
        // Whole and untruncated. Truncating is a choice this frontend declines to make: its output
        // is meant to be piped, and a shortened path is not one a later command can open.
        return to_std_string(segment.path);
    case scanner::ScanRunDisplaySegmentKind::Text:
    case scanner::ScanRunDisplaySegmentKind::Label:
    case scanner::ScanRunDisplaySegmentKind::Name:
    case scanner::ScanRunDisplaySegmentKind::Emphasis:
        break;
    }
    return to_std_string(segment.text);
}

/// Concatenates a bare segment list, in Rust's order, into one plain-text string.
///
/// Split out of `render_cli_display_line` because a recovery decision's description is a segment
/// list with no line around it: it is drawn inside a menu row this frontend composes, so there is
/// no severity to route on. The concatenation rule is deliberately the same one rather than a
/// second copy of it.
std::string render_cli_display_segments(const rust::Vec<scanner::ScanRunDisplaySegment>& segments) {
    std::string rendered;
    for (const auto& segment : segments) {
        if (!rendered.empty()) {
            rendered += ' ';
        }
        rendered += render_cli_display_segment(segment);
    }
    return rendered;
}

} // namespace

std::string render_cli_display_line(const scanner::ScanRunDisplayLine& line) {
    return render_cli_display_segments(line.segments);
}

scanner::ScanRunLaunchOverridesDto make_cli_scan_run_launch_overrides(const CliArgs& args) {
    scanner::ScanRunLaunchOverridesDto overrides{};
    if (args.game_was_explicit) {
        // `--game` admits only `Fallout4` (cli_args.cpp rejects anything else at parse time), so an
        // explicit flag can only ever name that game. Widening the flag is a separate CLI decision;
        // which saved values then apply to the named game is Crash Log Scan Launch's game-differs
        // rule, not something decided here.
        overrides.has_game = true;
        overrides.game = scanner::ScanRunGameId::Fallout4;
    }
    if (args.game_version_was_explicit) {
        overrides.has_game_version = true;
        overrides.game_version = args.game_version;
    }
    if (!args.scan_path.empty()) {
        overrides.has_scan_path = true;
        overrides.scan_path = args.scan_path;
    }
    if (args.max_concurrent_was_explicit) {
        // Zero is passed through rather than dropped: Rust reads it as the explicit adaptive
        // override, which is how `--max-concurrent 0` beats a saved limit.
        overrides.has_max_concurrent = true;
        overrides.max_concurrent = args.max_concurrent;
    }
    overrides.show_formid_values = args.show_fid_values;
    overrides.simplify_logs = args.simplify_logs;
    overrides.fcx_mode = args.fcx_mode;
    return overrides;
}

std::optional<rust::Box<scanner::ScanRunLaunch>> launch_cli_scan_run(const CliArgs& args,
                                                                      const std::string& installation_root) {
    // The one User Settings write the CLI makes, deliberately ahead of the launch: Crash Log Scan
    // Launch only reads User Settings, so this ordering is what lets the scan use the destination
    // the user just asked to save.
    if (!persist_unsolved_logs_destination_option(args, installation_root)) {
        return std::nullopt;
    }

    const auto overrides = make_cli_scan_run_launch_overrides(args);
    if (args.input_paths.empty()) {
        return scanner::scan_run_launch_standard(installation_root, overrides);
    }
    rust::Vec<rust::String> inputs;
    for (const auto& input : args.input_paths) {
        inputs.push_back(input);
    }
    return scanner::scan_run_launch_targeted(installation_root, inputs, overrides);
}

std::vector<CliScanRunMessage> describe_cli_scan_run_launch(const scanner::ScanRunLaunchRequestDto& view) {
    std::vector<CliScanRunMessage> messages;
    append_display_lines(view.display_lines, messages);
    return messages;
}

std::string cli_scan_run_game_token(scanner::ScanRunGameId game) {
    // CXX bridge modules cannot share an enum, so the scanner and shared bridges each mirror
    // `classic_shared_core::GameId`. These checks make a drift between the two mirrors a compile
    // error instead of a mislabelled game.
    static_assert(static_cast<std::uint8_t>(scanner::ScanRunGameId::Fallout4) ==
                  static_cast<std::uint8_t>(classic::shared::GameId::Fallout4));
    static_assert(static_cast<std::uint8_t>(scanner::ScanRunGameId::Fallout4VR) ==
                  static_cast<std::uint8_t>(classic::shared::GameId::Fallout4VR));
    static_assert(static_cast<std::uint8_t>(scanner::ScanRunGameId::Skyrim) ==
                  static_cast<std::uint8_t>(classic::shared::GameId::Skyrim));
    static_assert(static_cast<std::uint8_t>(scanner::ScanRunGameId::Starfield) ==
                  static_cast<std::uint8_t>(classic::shared::GameId::Starfield));
    return to_std_string(
        classic::shared::game_id_as_str(static_cast<classic::shared::GameId>(static_cast<std::uint8_t>(game))));
}

std::vector<CliScanRunMessage> describe_cli_scan_run_event(const scanner::ScanRunContractEvent& event) {
    std::vector<CliScanRunMessage> messages;
    if (event_earns_a_durable_line(event.kind)) {
        append_display_lines(event.display_lines, messages);
    }
    return messages;
}

CliScanRunPresentation present_cli_scan_run_execution(const scanner::ScanRunContractExecutionResult& execution,
                                                      double duration_seconds) {
    CliScanRunPresentation presentation{};
    if (execution.has_error || execution.has_resume_error) {
        // One exit code for both, because both mean the same thing to a caller: the run produced no
        // usable terminal result. Which of the two it was is in the words Rust rendered, and the
        // machine-facing distinction stays on `error` and `resume_error` for a consumer that wants
        // it — including `resume_error.code`, which the rendered sentence deliberately omits.
        presentation.exit_code = 2;
        if (!append_display_lines(execution.display_lines, presentation.messages,
                                  CliLineRouting::AllToStderr)) {
            // Unreachable through the bridge: both failure renderers always produce at least a
            // headline. Guarded anyway because the alternative is exiting 2 in silence, which
            // reads to a user as the process dying rather than as a run that failed. Like the
            // missing-envelope line below, this reports a broken bridge promise rather than
            // anything a run said, so it is the CLI's own sentence to write.
            presentation.messages.push_back(
                {true, "Fatal: Crash Log Scan Run failed without describing the failure."});
        }
        return presentation;
    }
    if (!execution.has_result) {
        // Not a run outcome and so not something Rust rendered: the bridge promises exactly one of
        // three payloads, and this is the CLI reporting that promise broken. It stays composed here
        // because there is no run to describe.
        presentation.exit_code = 2;
        presentation.messages.push_back(
            {true, "Fatal: Crash Log Scan Run returned neither a result nor an infrastructure error."});
        return presentation;
    }

    // Section ordering, and only section ordering, is decided below. The FCX Mode setup projection
    // is still composed locally, because its check state, check kind, issue severity, and update
    // kind belong to a subsystem that has not adopted the shared vocabulary and so is not rendered
    // by Rust yet. It leads for a run that reached a real outcome, where it reports on the
    // installation rather than on the run; it follows for a setup failure, where the outcome is the
    // headline and the setup detail explains it. Both orderings predate this change and are kept.
    // Everything Rust does render is emitted in Rust's order, unsplit.
    const auto& result = execution.result;
    switch (result.status) {
    case scanner::ScanRunContractStatus::NoCrashLogsFound:
        append_display_lines(execution.display_lines, presentation.messages);
        return presentation;
    case scanner::ScanRunContractStatus::SetupFailed:
        presentation.exit_code = 1;
        append_display_lines(execution.display_lines, presentation.messages);
        append_setup_messages(result, presentation.messages);
        return presentation;
    case scanner::ScanRunContractStatus::CancelledBeforeDiscovery:
        presentation.exit_code = 130;
        append_display_lines(execution.display_lines, presentation.messages);
        return presentation;
    case scanner::ScanRunContractStatus::Cancelled:
        presentation.exit_code = 130;
        append_setup_messages(result, presentation.messages);
        append_display_lines(execution.display_lines, presentation.messages);
        return presentation;
    case scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired:
        presentation.exit_code = 1;
        append_setup_messages(result, presentation.messages);
        append_display_lines(execution.display_lines, presentation.messages);
        return presentation;
    case scanner::ScanRunContractStatus::Completed:
        break;
    }

    append_setup_messages(result, presentation.messages);
    append_display_lines(execution.display_lines, presentation.messages);

    // The four totals below are the only run-level facts this process holds that Rust never saw:
    // two aggregates over the per-log outcomes, and two derived from a clock the contract does not
    // carry. Everything Rust does report — what was scanned, what failed, what never started — is
    // already stated above, so restating it here would be this frontend inventing a second account
    // of the same run.
    std::size_t reports_written = 0;
    std::size_t moved_to_unsolved_logs = 0;
    for (const auto& log : result.logs) {
        reports_written += log.has_autoscan_report ? 1 : 0;
        moved_to_unsolved_logs += log.moved_to_unsolved_logs ? 1 : 0;
    }

    presentation.messages.push_back({false, "Scan Complete"});
    presentation.messages.push_back({false, fmt::format("  Reports: {} written", reports_written)});
    if (moved_to_unsolved_logs > 0) {
        presentation.messages.push_back({false, fmt::format("  Unsolved: {} moved", moved_to_unsolved_logs)});
    }
    presentation.messages.push_back({false, fmt::format("  Duration: {:.2f}s", duration_seconds)});
    const auto speed = duration_seconds > 0.0 ? static_cast<double>(result.total) / duration_seconds : 0.0;
    presentation.messages.push_back({false, fmt::format("  Speed: {:.1f} logs/sec", speed)});
    presentation.exit_code = result.failed > 0 ? 1 : 0;
    return presentation;
}

class CliScanRunCancellation::Impl final {
public:
    /// Creates the Rust control before installing any platform monitor that can request it.
    explicit Impl(bool monitor_console)
        : token_(scanner::scan_run_cancellation_new()) {
#ifdef _WIN32
        if (monitor_console) {
            g_console_cancel_requested.store(false, std::memory_order_release);
            handler_installed_ = SetConsoleCtrlHandler(handle_console_control, TRUE) != 0;
            monitor_ = std::thread([this] {
                while (!stop_.load(std::memory_order_acquire)) {
                    if (g_console_cancel_requested.load(std::memory_order_acquire)) {
                        request();
                        return;
                    }
                    std::this_thread::sleep_for(std::chrono::milliseconds(25));
                }
            });
        }
#else
        (void)monitor_console;
#endif
    }

    /// Joins the monitor before unregistering the callback and releasing the token.
    ~Impl() {
        stop_.store(true, std::memory_order_release);
        if (monitor_.joinable()) {
            monitor_.join();
        }
#ifdef _WIN32
        if (handler_installed_) {
            SetConsoleCtrlHandler(handle_console_control, FALSE);
        }
        g_console_cancel_requested.store(false, std::memory_order_release);
#endif
    }

    /// Makes the monotonic request exactly once even if the Ctrl+C monitor and a direct caller race.
    ///
    /// The scan observer no longer calls this: Rust cancels on a failed delivery under the CLI's
    /// observer failure policy.
    void request() {
        if (!requested_.exchange(true, std::memory_order_acq_rel)) {
            scanner::scan_run_cancellation_cancel(*token_);
        }
    }

    /// Returns the live Rust control for the synchronous execution call.
    [[nodiscard]] const scanner::ScanRunCancellation& token() const noexcept { return *token_; }

private:
    rust::Box<scanner::ScanRunCancellation> token_;
    std::atomic_bool requested_{false};
    std::atomic_bool stop_{false};
    std::thread monitor_;
#ifdef _WIN32
    bool handler_installed_ = false;
#endif
};

CliScanRunCancellation::CliScanRunCancellation(bool monitor_console)
    : impl_(std::make_unique<Impl>(monitor_console)) {}

CliScanRunCancellation::~CliScanRunCancellation() = default;

void CliScanRunCancellation::request() {
    impl_->request();
}

const scanner::ScanRunCancellation& CliScanRunCancellation::token() const noexcept {
    return impl_->token();
}

CliLocalIgnoreRecoveryPresentation describe_cli_local_ignore_recovery(
    const scanner::ScanRunContractExecutionResult& execution, const scanner::ScanRunRecoveryPrompt& prompt) {
    const auto& result = execution.result;
    CliLocalIgnoreRecoveryPresentation recovery;
    // The rendered run opens with why it paused and carries the Installed YAML Data block that says
    // what is wrong, so the CLI no longer restates either. It used to lead with the run message; now
    // that message is one of the lines below.
    append_display_lines(execution.display_lines, recovery.details);
    if (result.has_discovery) {
        // The retained discovery set is the reason recovery is a choice rather than a restart:
        // whichever decision the user makes resumes these exact Crash Logs. Still this frontend's
        // own sentence, and the last one it writes about a run: `render_local_ignore_recovery`
        // reads Installed YAML Data, which carries no discovery count.
        const auto accepted = result.discovery.accepted_logs.size();
        recovery.details.push_back({false, fmt::format("  Retained discovery: {} {} will be scanned once you decide.",
                                                       accepted, plural(accepted, "crash log", "crash logs"))});
    }
    // Rust's question, last, so it sits immediately above the menu rather than at the top of a
    // block the user has already scrolled past. This is where the CLI used to resolve absent
    // Installed YAML Data into an availability flag for itself, next to the GUI and the TUI each
    // resolving it for themselves; `render_local_ignore_recovery` takes that `Option` so the rule
    // is written once. A prompt describing no decision leaves Cancel as the only offered answer —
    // the safe reading of a contract violation.
    append_display_lines(prompt.lines, recovery.details);
    for (const auto& description : prompt.decisions) {
        recovery.decisions.push_back({description.decision, to_std_string(description.label),
                                      render_cli_display_segments(description.description),
                                      description.available});
    }
    return recovery;
}

CliLocalIgnoreRecoveryChoice read_cli_local_ignore_recovery_choice(
    std::istream& input, std::ostream& output, const CliScanRunCancellation& cancellation,
    const std::vector<CliLocalIgnoreRecoveryDecisionOption>& decisions) {
    // Ctrl+C observed before the question is asked already decided the run; never offer a
    // destructive default to a user who is on their way out.
    if (scanner::scan_run_cancellation_is_cancelled(cancellation.token())) {
        return CliLocalIgnoreRecoveryChoice::Cancel;
    }

    // The menu, the bracketed letters, and the retry hint are all built in this one pass over
    // `decisions`, so the question can never advertise an answer the menu withheld. Why an
    // unavailable decision is missing was already stated by Rust's own prompt lines, printed just
    // above this menu, so nothing is said about the absence here.
    output << "Choose how to continue:\n";
    std::vector<char> offered;
    for (const auto& option : decisions) {
        // Omitted rather than listed-and-refused: a bracketed letter the prompt will not accept
        // reads as a bug.
        if (!option.available) {
            continue;
        }
        const auto affordance = recovery_affordance(option.decision);
        output << fmt::format("  [{}] {} - {}\n", affordance.letter, option.label, option.description);
        offered.push_back(affordance.letter);
    }
    // Cancel is always last and always offered. Rust has no decision for backing out — it is spelled
    // as the absence of one — so its letter and its sentence are this frontend's to write.
    output << "  [C] Cancel - stop this scan without changing any file\n";
    offered.push_back('C');

    // Both hints are derived from the one list of letters the menu just printed, so neither can
    // advertise an answer the menu withheld.
    const std::string letters_hint = format_offered_letters(offered);
    const std::string retry_hint = format_retry_hint(offered);

    for (int attempt = 0; attempt < CLI_LOCAL_IGNORE_RECOVERY_PROMPT_ATTEMPTS; ++attempt) {
        output << "Local Ignore recovery " << letters_hint << ": " << std::flush;
        std::string answer;
        if (!std::getline(input, answer)) {
            // End of input is not an answer. Treat it as dismissal so redirected or closed stdin
            // cannot silently authorize a reset.
            output << "\nNo answer was available; cancelling without changing Local Ignore YAML Data.\n";
            return CliLocalIgnoreRecoveryChoice::Cancel;
        }
        if (scanner::scan_run_cancellation_is_cancelled(cancellation.token())) {
            return CliLocalIgnoreRecoveryChoice::Cancel;
        }

        CliLocalIgnoreRecoveryChoice choice = CliLocalIgnoreRecoveryChoice::Cancel;
        if (match_recovery_choice(normalize_console_answer(answer), decisions, choice)) {
            return choice;
        }
        output << retry_hint;
    }

    output << "No usable answer after " << CLI_LOCAL_IGNORE_RECOVERY_PROMPT_ATTEMPTS
           << " attempts; cancelling without changing Local Ignore YAML Data.\n";
    return CliLocalIgnoreRecoveryChoice::Cancel;
}

CliScanRunExecutionOutcome execute_cli_scan_run(const scanner::ScanRunRequest& request,
                                                CliScanRunCancellation& cancellation,
                                                const scanner::ScanRunObserver* observer,
                                                const CliLocalIgnoreRecoveryPrompt& prompt) {
    auto operation = scanner::scan_run_contract_execute(request, cancellation.token(), observer,
                                                        CLI_SCAN_RUN_OBSERVER_FAILURE_POLICY);
    return resolve_cli_local_ignore_recovery(*operation, observer, prompt);
}

CliScanRunExecutionOutcome resolve_cli_local_ignore_recovery(scanner::ScanRunContractExecution& operation,
                                                             const scanner::ScanRunObserver* observer,
                                                             const CliLocalIgnoreRecoveryPrompt& prompt) {
    CliScanRunExecutionOutcome outcome{};
    const bool has_pending_recovery = scanner::scan_run_contract_execution_has_pending_recovery(operation);
    outcome.execution = scanner::scan_run_contract_execution_take_result(operation);
    if (!has_pending_recovery || !prompt) {
        // No pending recovery means nothing to settle; Rust owns every other outcome, including
        // abandoning a recovery whose run already failed to deliver an event. An empty prompt is
        // the non-interactive path: report the paused envelope and make no choice.
        return outcome;
    }

    // Taken before the prompt runs so a decision can never observe a half-owned operation, and so a
    // prompt that throws cannot leave the run resumable.
    auto pending = scanner::scan_run_contract_execution_take_pending_recovery(operation);

    std::optional<scanner::ScanRunLocalIgnoreRecoveryDecision> decision;
    // Ctrl+C observed between the pause and this check already decided the run, so the question is
    // never printed: settling with no decision is the only answer a cancelled run can take.
    if (!scanner::scan_run_pending_recovery_cancellation_requested(*pending)) {
        const auto choice = prompt(
            describe_cli_local_ignore_recovery(outcome.execution, scanner::scan_run_pending_recovery_prompt(*pending)));

        // Cancel maps to *no decision*, which is how settling spells abandonment. The switch stays
        // exhaustive so a choice added later trips `-Wswitch` here rather than silently resolving
        // to Proceed Without Ignore. The same `optional`-shaped mapping is what the Node and Python
        // bindings use, for the same reason: `LocalIgnoreRecoveryDecision` deliberately has no
        // abandonment variant, so absence is how abandonment is spelled everywhere.
        switch (choice) {
        case CliLocalIgnoreRecoveryChoice::ProceedWithoutIgnore:
            decision = scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore;
            break;
        case CliLocalIgnoreRecoveryChoice::ResetToDefault:
            decision = scanner::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault;
            break;
        case CliLocalIgnoreRecoveryChoice::Cancel:
            // Leaves `decision` empty. So does a value this build does not recognize, since no case
            // assigns it: abandonment is the one outcome that cannot touch the user's files.
            break;
        }
    }

    // Settling with no decision cancels the run's own control, the one handed to execute, so
    // nothing here asks for cancellation first — and deliberately not through
    // `CliScanRunCancellation::request()`, whose one-shot guard belongs to the Ctrl+C monitor.
    // Rust's control is monotonic, so a later `request()` is inert rather than a second cancel. The settled envelope cannot carry another pending
    // recovery, so a second recovery request is unrepresentable rather than checked for.
    scanner::ScanRunLocalIgnoreRecoverySettlement settlement{};
    settlement.has_decision = decision.has_value();
    // `decision` is read only beside `has_decision`; the placeholder is never applied.
    settlement.decision = decision.value_or(scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore);
    outcome.execution =
        scanner::scan_run_pending_recovery_settle(*pending, settlement, observer, CLI_SCAN_RUN_OBSERVER_FAILURE_POLICY);
    outcome.local_ignore_recovery_settled = true;
    outcome.settled_decision = decision;
    return outcome;
}

CliScanRunPresentation present_cli_scan_run_outcome(const CliScanRunExecutionOutcome& outcome,
                                                    double duration_seconds) {
    auto presentation = present_cli_scan_run_execution(outcome.execution, duration_seconds);
    if (!outcome.execution.has_observer_delivery_failure) {
        return presentation;
    }

    // Read from the run result rather than from the CLI's own observer: Rust stops delivering after
    // the first failure and has already applied the CLI's policy, so the envelope is the one place
    // that knows a failure happened. The sentence stays this frontend's own because Rust renders no
    // line for it; the exit code stays the run's.
    presentation.messages.insert(
        presentation.messages.begin(),
        CliScanRunMessage{true, "Warning: scan progress presentation failed; safe cancellation was requested."});
    return presentation;
}
