#include "scan_run_cli.h"

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

#include <algorithm>
#include <atomic>
#include <cctype>
#include <chrono>
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

/// Projects typed User Settings into the shared final-contract configuration DTO.
scanner::ScanRunConfigurationDto make_configuration(const PreparedScanUserSettings& settings,
                                                     const std::string& installation_root) {
    scanner::ScanRunConfigurationDto configuration{};
    configuration.installation_root = installation_root;
    if (settings.game == "Fallout4") {
        configuration.game = scanner::ScanRunGameId::Fallout4;
    } else if (settings.game == "Fallout4VR") {
        configuration.game = scanner::ScanRunGameId::Fallout4VR;
    } else if (settings.game == "Skyrim") {
        configuration.game = scanner::ScanRunGameId::Skyrim;
    } else if (settings.game == "Starfield") {
        configuration.game = scanner::ScanRunGameId::Starfield;
    } else {
        throw std::invalid_argument(fmt::format("unsupported Crash Log Scan game: {}", settings.game));
    }
    configuration.game_version = settings.game_version;
    configuration.show_formid_values = settings.show_formid_values;
    configuration.simplify_logs = settings.simplify_logs;
    for (const auto& path : settings.formid_database_paths) {
        configuration.formid_database_paths.push_back(path);
    }
    configuration.has_configured_unsolved_logs_destination = !settings.unsolved_logs_destination.empty();
    configuration.configured_unsolved_logs_destination = settings.unsolved_logs_destination;
    configuration.has_max_concurrent = settings.max_concurrent > 0;
    configuration.max_concurrent = settings.max_concurrent;
    return configuration;
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

/// Projects optional typed setup paths into explicit presence/value pairs for FCX requests.
scanner::ScanRunSetupContextDto make_setup_context(const PreparedScanUserSettings& settings) {
    scanner::ScanRunSetupContextDto setup{};
    setup.has_game_root = !settings.setup_game_root.empty();
    setup.game_root = settings.setup_game_root;
    setup.has_docs_root = !settings.setup_docs_root.empty();
    setup.docs_root = settings.setup_docs_root;
    setup.has_game_exe_path = !settings.setup_game_exe_path.empty();
    setup.game_exe_path = settings.setup_game_exe_path;
    setup.has_xse_log_path = !settings.setup_xse_log_path.empty();
    setup.xse_log_path = settings.setup_xse_log_path;
    return setup;
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

rust::Box<scanner::ScanRunRequest> build_cli_scan_run_request(const CliArgs& args,
                                                              const PreparedScanUserSettings& settings,
                                                              const std::string& installation_root,
                                                              const std::string& base_directory) {
    const auto configuration = make_configuration(settings, installation_root);
    const auto setup = make_setup_context(settings);

    if (!args.input_paths.empty()) {
        scanner::ScanRunTargetedSourceDto source{};
        for (const auto& input : args.input_paths) {
            source.inputs.push_back(input);
        }
        return settings.fcx_mode ? scanner::scan_run_request_targeted_with_fcx(configuration, source, setup)
                                 : scanner::scan_run_request_targeted(configuration, source);
    }

    scanner::ScanRunStandardSourceDto source{};
    source.base_directory = base_directory;
    source.has_custom_scan_directory = !settings.custom_scan_directory.empty();
    source.custom_scan_directory = settings.custom_scan_directory;
    source.has_configured_documents_root = !settings.configured_documents_root.empty();
    source.configured_documents_root = settings.configured_documents_root;

    const auto unsolved_logs = settings.move_unsolved_logs
                                   ? scanner::scan_run_unsolved_logs_move_to_configured_or_default()
                                   : scanner::scan_run_unsolved_logs_leave_in_place();
    return settings.fcx_mode ? scanner::scan_run_request_standard_with_fcx(configuration, source, *unsolved_logs, setup)
                             : scanner::scan_run_request_standard(configuration, source, *unsolved_logs);
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

    /// Makes the monotonic request exactly once even if Ctrl+C and adapter failure race.
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
    const scanner::ScanRunContractExecutionResult& execution) {
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
    // is written once. Both vectors are empty when the envelope carries no prompt, which leaves
    // Cancel as the only offered answer — the safe reading of a contract violation.
    append_display_lines(execution.recovery_prompt.lines, recovery.details);
    for (const auto& description : execution.recovery_prompt.decisions) {
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
    CliScanRunExecutionOutcome outcome{};
    auto operation = scanner::scan_run_contract_execute(request, cancellation.token(), observer);
    const bool has_continuation = scanner::scan_run_contract_execution_has_continuation(*operation);
    outcome.execution = scanner::scan_run_contract_execution_take_result(*operation);

    const bool recovery_required =
        outcome.execution.has_result &&
        outcome.execution.result.status == scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired;
    if (!recovery_required) {
        return outcome;
    }
    if (!has_continuation) {
        // Rust always retains a continuation with this status, so its absence is a broken contract
        // rather than a user decision. Say so instead of presenting an unanswerable question.
        outcome.recovery_diagnostics.push_back(
            {true, "Fatal: Crash Log Scan Run requested Local Ignore recovery without retaining its continuation."});
        return outcome;
    }
    if (!prompt) {
        // Expected for a non-interactive invocation: report the typed outcome and make no choice.
        return outcome;
    }

    // The continuation must be taken before the prompt runs so a decision can never observe a
    // half-owned operation, and so a prompt that throws cannot leave the run resumable.
    auto continuation = scanner::scan_run_contract_execution_take_continuation(*operation);
    const auto choice = prompt(describe_cli_local_ignore_recovery(outcome.execution));

    // Cancel maps to *no decision*, which is exactly what the shared abandon operation takes. The
    // switch stays exhaustive so a choice added later trips `-Wswitch` here rather than silently
    // resolving to Proceed Without Ignore. The same `optional`-shaped mapping is what the Node and
    // Python bindings use, for the same reason: `LocalIgnoreRecoveryDecision` deliberately has no
    // abandonment variant, so absence is how abandonment is spelled everywhere.
    const auto decision = [&]() -> std::optional<scanner::ScanRunLocalIgnoreRecoveryDecision> {
        switch (choice) {
        case CliLocalIgnoreRecoveryChoice::ProceedWithoutIgnore:
            return scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore;
        case CliLocalIgnoreRecoveryChoice::ResetToDefault:
            return scanner::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault;
        case CliLocalIgnoreRecoveryChoice::Cancel:
            return std::nullopt;
        }
        // Unreachable for a valid enumerator. Abandonment is the safe resolution for a value this
        // build does not recognize: it is the one outcome that cannot touch the user's files.
        return std::nullopt;
    }();

    // `scan_run_continuation_abandon` performs the cancel-then-resume-with-a-placeholder sequence
    // that used to live here, so the CLI cannot reorder it, cannot pick a different placeholder,
    // and cannot drift from what the Qt GUI and the TUI do. It cancels the shared control itself,
    // which is why nothing here asks for cancellation first — and deliberately not through
    // `cancellation.request()`, whose one-shot guard exists to stop the Ctrl+C monitor and an
    // adapter failure from racing. Rust's control is monotonic, so a later `request()` is inert
    // rather than a second cancel.
    auto resumed = decision ? scanner::scan_run_continuation_resume(*continuation, *decision,
                                                                    cancellation.token(), observer)
                            : scanner::scan_run_continuation_abandon(*continuation, cancellation.token(), observer);
    outcome.execution = scanner::scan_run_contract_execution_take_result(*resumed);
    outcome.local_ignore_continuation_consumed = true;

    if (outcome.execution.has_result &&
        outcome.execution.result.status == scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired) {
        // The continuation is single-use, so a resumed run can never ask again. Refuse to present a
        // second question the CLI has no continuation left to answer.
        outcome.recovery_diagnostics.push_back(
            {true, "Fatal: Crash Log Scan recovery returned an unexpected second recovery request."});
    }
    return outcome;
}

CliScanRunPresentation present_cli_scan_run_outcome(const CliScanRunExecutionOutcome& outcome,
                                                    double duration_seconds) {
    auto presentation = present_cli_scan_run_execution(outcome.execution, duration_seconds);
    if (outcome.recovery_diagnostics.empty()) {
        return presentation;
    }

    presentation.messages.insert(presentation.messages.begin(), outcome.recovery_diagnostics.begin(),
                                 outcome.recovery_diagnostics.end());
    presentation.exit_code = 2;
    return presentation;
}
