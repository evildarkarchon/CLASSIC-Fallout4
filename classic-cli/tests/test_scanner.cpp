// SPDX-License-Identifier: MIT

#include <catch2/catch_test_macros.hpp>

#include "scan_run_cli.h"

#include <cstddef>
#include <cstdint>
#include <istream>
#include <sstream>
#include <streambuf>
#include <string>
#include <stdexcept>
#include <utility>
#include <vector>

namespace {

namespace scanner = classic::scanner;

/// Executes an opaque bridge operation and moves out its typed terminal envelope.
scanner::ScanRunContractExecutionResult execute_result(
    const scanner::ScanRunRequest& request, const scanner::ScanRunCancellation& cancellation,
    const scanner::ScanRunObserver* observer) {
    auto operation = scanner::scan_run_contract_execute(request, cancellation, observer);
    return scanner::scan_run_contract_execution_take_result(*operation);
}

std::vector<std::string> message_text(const std::vector<CliScanRunMessage>& messages) {
    std::vector<std::string> lines;
    lines.reserve(messages.size());
    for (const auto& message : messages) {
        lines.push_back(message.text);
    }
    return lines;
}

scanner::ScanRunContractExecutionResult execution_with_result(scanner::ScanRunContractStatus status) {
    scanner::ScanRunContractExecutionResult execution{};
    execution.has_result = true;
    execution.result.status = status;
    return execution;
}

scanner::ScanRunContractLogResult log_result(std::size_t index, std::string path,
                                             scanner::ScanRunContractLogDisposition disposition) {
    scanner::ScanRunContractLogResult result{};
    result.discovery_index = index;
    result.crash_log = std::move(path);
    result.disposition = disposition;
    return result;
}

// Display Content is decided in Rust and pinned exactly once, by
// `business-logic/classic-scan-presentation/src/lib_tests.rs`. Asserting the same wording again here
// would mean one rewording produced two diffs and two chances to disagree, which is the drift this
// work removes. The fixtures below therefore carry deliberately unreal words: what they prove is
// that the CLI prints what it was handed, in the order it was handed it, and nothing more.

scanner::ScanRunDisplaySegment segment(scanner::ScanRunDisplaySegmentKind kind, std::string text) {
    scanner::ScanRunDisplaySegment value{};
    value.kind = kind;
    value.text = std::move(text);
    return value;
}

scanner::ScanRunDisplaySegment path_segment(std::string path) {
    scanner::ScanRunDisplaySegment value{};
    value.kind = scanner::ScanRunDisplaySegmentKind::Path;
    value.path = std::move(path);
    return value;
}

/// Builds a count segment the way the bridge does: the noun rides in `text`, already resolved.
scanner::ScanRunDisplaySegment count_segment(std::uint64_t count, std::string noun) {
    scanner::ScanRunDisplaySegment value{};
    value.kind = scanner::ScanRunDisplaySegmentKind::Count;
    value.text = std::move(noun);
    value.count = count;
    return value;
}

scanner::ScanRunDisplayLine display_line(scanner::ScanRunDisplaySeverity severity,
                                         std::vector<scanner::ScanRunDisplaySegment> segments) {
    scanner::ScanRunDisplayLine line{};
    line.severity = severity;
    for (auto& value : segments) {
        line.segments.push_back(std::move(value));
    }
    return line;
}

/// Builds a one-segment informational line, which is all most fixtures need.
scanner::ScanRunDisplayLine text_line(std::string text) {
    return display_line(scanner::ScanRunDisplaySeverity::Info,
                        {segment(scanner::ScanRunDisplaySegmentKind::Text, std::move(text))});
}

void push_lines(rust::Vec<scanner::ScanRunDisplayLine>& target, std::vector<scanner::ScanRunDisplayLine> lines) {
    for (auto& line : lines) {
        target.push_back(std::move(line));
    }
}

/// Serves console input one character at a time and cancels as the answer's newline is consumed.
///
/// Models Ctrl+C landing while a console read is already in flight: the answer is fully entered,
/// but cancellation is visible by the time the prompt inspects it.
class CancellingInputBuffer final : public std::streambuf {
public:
    /// Borrows the cancellation owner, which must outlive every read through this buffer.
    CancellingInputBuffer(std::string contents, CliScanRunCancellation& cancellation)
        : contents_(std::move(contents))
        , cancellation_(cancellation) {}

protected:
    /// Peeks the next character without consuming it, so no cancellation is published.
    int_type underflow() override {
        if (position_ >= contents_.size()) {
            return traits_type::eof();
        }
        return traits_type::to_int_type(contents_[position_]);
    }

    /// Consumes one character and publishes cancellation once the entered line terminates.
    int_type uflow() override {
        if (position_ >= contents_.size()) {
            return traits_type::eof();
        }
        const char character = contents_[position_++];
        if (character == '\n') {
            cancellation_.request();
        }
        return traits_type::to_int_type(character);
    }

private:
    std::string contents_;
    CliScanRunCancellation& cancellation_;
    std::size_t position_ = 0;
};

PreparedScanUserSettings minimal_settings() {
    PreparedScanUserSettings settings{};
    settings.game = "Fallout4";
    settings.game_version = "auto";
    return settings;
}

} // namespace

TEST_CASE("CLI scan adapter submits Standard intent to the single execution operation", "[scanner][scan-run]") {
    const CliArgs args{};
    const auto request = build_cli_scan_run_request(args, minimal_settings(), ".", ".");
    const auto cancellation = scanner::scan_run_cancellation_new();
    scanner::scan_run_cancellation_cancel(*cancellation);

    const auto execution = execute_result(*request, *cancellation, nullptr);

    REQUIRE(execution.has_result);
    REQUIRE_FALSE(execution.has_error);
    REQUIRE(execution.result.status == scanner::ScanRunContractStatus::CancelledBeforeDiscovery);
}

TEST_CASE("CLI scan adapter submits raw Targeted inputs to Rust discovery", "[scanner][scan-run]") {
    CliArgs args{};
    args.input_paths.push_back("C:/not-a-crash-log.txt");
    auto settings = minimal_settings();
    settings.move_unsolved_logs = true;
    const auto request = build_cli_scan_run_request(args, settings, ".", ".");
    const auto cancellation = scanner::scan_run_cancellation_new();

    const auto execution = execute_result(*request, *cancellation, nullptr);

    REQUIRE(execution.has_result);
    REQUIRE_FALSE(execution.has_error);
    REQUIRE(execution.result.status == scanner::ScanRunContractStatus::NoCrashLogsFound);
    REQUIRE(execution.result.has_discovery);
    REQUIRE(execution.result.discovery.source == scanner::ScanRunContractDiscoverySource::Targeted);
    REQUIRE(execution.result.discovery.accepted_logs.empty());
    REQUIRE(execution.result.discovery.rejected_inputs.size() == 1);
    REQUIRE(std::string(execution.result.discovery.rejected_inputs[0].path) == "C:/not-a-crash-log.txt");
}

TEST_CASE("CLI scan request builder maps every supported game to the scanner-local typed identity",
          "[scanner][scan-run]") {
    const CliArgs args{};
    for (const std::string game : {"Fallout4", "Fallout4VR", "Skyrim", "Starfield"}) {
        auto settings = minimal_settings();
        settings.game = game;
        const auto request = build_cli_scan_run_request(args, settings, ".", ".");
        const auto cancellation = scanner::scan_run_cancellation_new();
        scanner::scan_run_cancellation_cancel(*cancellation);
        const auto execution = execute_result(*request, *cancellation, nullptr);
        REQUIRE(execution.has_result);
        REQUIRE(execution.result.status == scanner::ScanRunContractStatus::CancelledBeforeDiscovery);
    }

    auto invalid = minimal_settings();
    invalid.game = "UnknownGame";
    REQUIRE_THROWS_AS(build_cli_scan_run_request(args, invalid, ".", "."), std::invalid_argument);
}

TEST_CASE("CLI display line rendering concatenates Rust's segments in order", "[scanner][scan-run][render]") {
    const auto line = display_line(scanner::ScanRunDisplaySeverity::Info,
                                   {segment(scanner::ScanRunDisplaySegmentKind::Text, "fixed prose"),
                                    segment(scanner::ScanRunDisplaySegmentKind::Label, "a display label"),
                                    count_segment(3, "widgets"),
                                    path_segment("C:/one two/three.log"),
                                    segment(scanner::ScanRunDisplaySegmentKind::Name, "a domain name"),
                                    segment(scanner::ScanRunDisplaySegmentKind::Emphasis, "set apart")});

    REQUIRE(render_cli_display_line(line) ==
            "fixed prose a display label 3 widgets C:/one two/three.log a domain name set apart");
}

TEST_CASE("CLI display line rendering prints the noun Rust resolved for a count",
          "[scanner][scan-run][render]") {
    // The singular case is the one that matters: a frontend re-deriving the form from the value
    // would have to agree with Rust by luck. Reading the noun Rust sent cannot disagree, so a
    // deliberately mismatched pair still round-trips exactly.
    REQUIRE(render_cli_display_line(display_line(scanner::ScanRunDisplaySeverity::Info,
                                                 {count_segment(1, "log")})) == "1 log");
    REQUIRE(render_cli_display_line(display_line(scanner::ScanRunDisplaySeverity::Info,
                                                 {count_segment(0, "logs")})) == "0 logs");
    REQUIRE(render_cli_display_line(display_line(scanner::ScanRunDisplaySeverity::Info,
                                                 {count_segment(7, "crash log")})) == "7 crash log");
}

TEST_CASE("CLI display line rendering keeps a path whole", "[scanner][scan-run][render]") {
    // Truncating would make the path useless to the command a user pipes this output into.
    const auto rendered = render_cli_display_line(
        display_line(scanner::ScanRunDisplaySeverity::Info,
                     {segment(scanner::ScanRunDisplaySegmentKind::Text, "Report:"),
                      path_segment("C:/CLASSIC/Crash Logs/crash-2026-08-06-AUTOSCAN.md")}));

    REQUIRE(rendered == "Report: C:/CLASSIC/Crash Logs/crash-2026-08-06-AUTOSCAN.md");
}

TEST_CASE("CLI display line rendering introduces no terminal styling", "[scanner][scan-run][render]") {
    // Shared wording must not push escape sequences into a user's logs, so the CLI's per-segment
    // styling is deliberately the empty choice for every kind, emphasis included.
    const auto rendered =
        render_cli_display_line(display_line(scanner::ScanRunDisplaySeverity::Failure,
                                             {segment(scanner::ScanRunDisplaySegmentKind::Emphasis, "loud")}));

    REQUIRE(rendered == "loud");
}

TEST_CASE("CLI scan presentation states a terminal result in Rust's words and order",
          "[scanner][scan-run][render]") {
    auto execution = execution_with_result(scanner::ScanRunContractStatus::NoCrashLogsFound);
    push_lines(execution.display_lines,
               {text_line("first"), text_line("second"), text_line("third")});

    const auto presentation = present_cli_scan_run_execution(execution, 0.25);
    const auto lines = message_text(presentation.messages);

    REQUIRE(presentation.exit_code == 0);
    REQUIRE(lines == std::vector<std::string>{"first", "second", "third"});
}

TEST_CASE("CLI scan presentation routes a line by the severity Rust gave it", "[scanner][scan-run][render]") {
    auto execution = execution_with_result(scanner::ScanRunContractStatus::Completed);
    push_lines(execution.display_lines,
               {display_line(scanner::ScanRunDisplaySeverity::Info,
                             {segment(scanner::ScanRunDisplaySegmentKind::Text, "neutral")}),
                display_line(scanner::ScanRunDisplaySeverity::Notice,
                             {segment(scanner::ScanRunDisplaySegmentKind::Text, "worth noticing")}),
                display_line(scanner::ScanRunDisplaySeverity::Warning,
                             {segment(scanner::ScanRunDisplaySegmentKind::Text, "incomplete")}),
                display_line(scanner::ScanRunDisplaySeverity::Failure,
                             {segment(scanner::ScanRunDisplaySegmentKind::Text, "broken")}),
                display_line(scanner::ScanRunDisplaySeverity::Success,
                             {segment(scanner::ScanRunDisplaySegmentKind::Text, "done")})});

    const auto presentation = present_cli_scan_run_execution(execution, 1.0);

    // stderr carries what needs attention; stdout carries the run's ordinary narrative.
    REQUIRE_FALSE(presentation.messages[0].error); // Info
    REQUIRE_FALSE(presentation.messages[1].error); // Notice
    REQUIRE(presentation.messages[2].error);       // Warning
    REQUIRE(presentation.messages[3].error);       // Failure
    REQUIRE_FALSE(presentation.messages[4].error); // Success
}

TEST_CASE("CLI scan events are stated in Rust's words", "[scanner][scan-run][render]") {
    for (const auto kind : {scanner::ScanRunContractEventKind::DiscoveryCompleted,
                            scanner::ScanRunContractEventKind::EffectiveConcurrencySelected,
                            scanner::ScanRunContractEventKind::LogStarted,
                            scanner::ScanRunContractEventKind::LogFinished}) {
        scanner::ScanRunContractEvent event{};
        event.kind = kind;
        push_lines(event.display_lines, {text_line("what happened"), text_line("and a second thing")});

        REQUIRE(message_text(describe_cli_scan_run_event(event)) ==
                std::vector<std::string>{"what happened", "and a second thing"});
    }
}

TEST_CASE("CLI scan events omit whole lines rather than rewording them", "[scanner][scan-run][render]") {
    // Queued and phase events are rendered by Rust like every other event; this frontend declines to
    // print them because the progress display already covers them. Omitting is what an adapter may
    // do, and it is the only thing this frontend does to them.
    for (const auto kind :
         {scanner::ScanRunContractEventKind::LogQueued, scanner::ScanRunContractEventKind::LogPhase}) {
        scanner::ScanRunContractEvent event{};
        event.kind = kind;
        push_lines(event.display_lines, {text_line("would have been printed")});

        REQUIRE(describe_cli_scan_run_event(event).empty());
    }
}

TEST_CASE("CLI scan events route a failed outcome to stderr", "[scanner][scan-run][render]") {
    scanner::ScanRunContractEvent event{};
    event.kind = scanner::ScanRunContractEventKind::LogFinished;
    push_lines(event.display_lines,
               {display_line(scanner::ScanRunDisplaySeverity::Failure,
                             {segment(scanner::ScanRunDisplaySegmentKind::Label, "failed"),
                              path_segment("C:/two.log")})});

    const auto messages = describe_cli_scan_run_event(event);

    REQUIRE(messages.size() == 1);
    REQUIRE(messages[0].error);
    REQUIRE(messages[0].text == "failed C:/two.log");
}

TEST_CASE("CLI scan cancellation is actionable and has a distinct terminal result", "[scanner][scan-run]") {
    CliScanRunCancellation cancellation(false);
    cancellation.request();
    REQUIRE(scanner::scan_run_cancellation_is_cancelled(cancellation.token()));

    auto execution = execution_with_result(scanner::ScanRunContractStatus::Cancelled);
    execution.result.total = 3;
    execution.result.succeeded = 1;
    execution.result.cancelled = 2;
    push_lines(execution.display_lines, {text_line("the run stopped early")});

    const auto presentation = present_cli_scan_run_execution(execution, 0.5);

    REQUIRE(presentation.exit_code == 130);
    REQUIRE(message_text(presentation.messages).back() == "the run stopped early");
}

TEST_CASE("CLI scan presentation explains FCX setup outcomes", "[scanner][scan-run]") {
    // The FCX Mode setup projection is still composed by this frontend. Its check state, check kind,
    // issue severity, and update kind belong to a subsystem that has not adopted the shared
    // vocabulary, so Rust renders no lines for it and there is nothing here to replace yet.
    auto execution = execution_with_result(scanner::ScanRunContractStatus::SetupFailed);
    push_lines(execution.display_lines, {text_line("the run could not start")});
    execution.result.has_setup = true;
    execution.result.setup.status = "action_required";
    execution.result.setup.has_message = true;
    execution.result.setup.message = "Select the Fallout 4 installation.";
    scanner::ScanRunSetupCheckDto check{};
    check.kind = "game_executable";
    check.state = "missing";
    check.message = "Fallout4.exe was not found";
    check.details.push_back("Expected under the configured game root.");
    execution.result.setup.checks.push_back(std::move(check));
    execution.result.setup.actions.push_back("Configure the game path and retry.");

    const auto presentation = present_cli_scan_run_execution(execution, 0.25);
    const auto lines = message_text(presentation.messages);

    REQUIRE(presentation.exit_code == 1);
    REQUIRE(lines[0] == "the run could not start");
    REQUIRE(lines[1] == "FCX setup: action_required");
    REQUIRE(lines[2] == "  Select the Fallout 4 installation.");
    REQUIRE(lines[3] == "  [missing] game_executable: Fallout4.exe was not found");
    REQUIRE(lines[4] == "    Expected under the configured game root.");
    REQUIRE(lines[5] == "  Action: Configure the game path and retry.");
}

TEST_CASE("CLI scan presentation leads a completed run with the setup projection it still owns",
          "[scanner][scan-run]") {
    auto execution = execution_with_result(scanner::ScanRunContractStatus::Completed);
    execution.result.has_setup = true;
    execution.result.setup.status = "ok";
    push_lines(execution.display_lines, {text_line("what the run says")});

    const auto lines = message_text(present_cli_scan_run_execution(execution, 1.0).messages);

    REQUIRE(lines[0] == "FCX setup: ok");
    REQUIRE(lines[1] == "what the run says");
}

TEST_CASE("CLI scan presentation keeps Local Ignore recovery distinct from setup and infrastructure failures",
          "[scanner][scan-run]") {
    auto execution = execution_with_result(scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired);
    push_lines(execution.display_lines,
               {display_line(scanner::ScanRunDisplaySeverity::Warning,
                             {segment(scanner::ScanRunDisplaySegmentKind::Text, "a decision is needed")})});

    const auto presentation = present_cli_scan_run_execution(execution, 0.5);

    // Exit 1 rather than 2: a run awaiting a decision is a status, not an infrastructure failure.
    REQUIRE(presentation.exit_code == 1);
    REQUIRE(presentation.messages.back().text == "a decision is needed");
    // A run that stopped to ask a question has always reached the user on stderr, and Rust marks
    // that status `Warning` — which is exactly why the severity cut for this frontend puts
    // `Warning` there rather than only `Failure`.
    REQUIRE(presentation.messages.back().error);
}

TEST_CASE("CLI scan presentation never exits on a failure it could not describe", "[scanner][scan-run][render]") {
    // Unreachable through the bridge, since both failure renderers always produce a headline. The
    // point is that exit 2 is never silent: a process that dies wordlessly reads as a crash rather
    // than as a run that failed.
    scanner::ScanRunContractExecutionResult execution{};
    execution.has_error = true;

    const auto presentation = present_cli_scan_run_execution(execution, 0.5);

    REQUIRE(presentation.exit_code == 2);
    REQUIRE(presentation.messages.size() == 1);
    REQUIRE(presentation.messages[0].error);
    REQUIRE_FALSE(presentation.messages[0].text.empty());
}

TEST_CASE("CLI Local Ignore recovery description offers retained discovery and diagnostics",
          "[scanner][scan-run][local-ignore]") {
    auto execution = execution_with_result(scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired);
    // The rendered run already opens with why it paused and carries the Installed YAML Data block,
    // so the description presents all of it rather than picking a sub-block back out by position.
    push_lines(execution.display_lines,
               {text_line("why the run paused"), text_line("what is wrong with the file")});
    execution.result.has_discovery = true;
    execution.result.discovery.accepted_logs.push_back("C:/one.log");
    execution.result.discovery.accepted_logs.push_back("C:/two.log");
    execution.result.has_installed_yaml_data = true;
    execution.result.installed_yaml_data.local_ignore_state =
        scanner::ScanRunLocalIgnoreYamlDataState::RecoveryRequired;
    execution.result.installed_yaml_data.local_ignore_reset_available = false;

    const auto recovery = describe_cli_local_ignore_recovery(execution);
    const auto lines = message_text(recovery.details);

    REQUIRE(lines[0] == "why the run paused");
    REQUIRE(lines[1] == "what is wrong with the file");
    // Still the CLI's own sentence: the recovery prompt renderer lands with the gated recovery
    // phase, not with this change. It is the only count this frontend still pluralizes.
    REQUIRE(lines.back() == "  Retained discovery: 2 crash logs will be scanned once you decide.");
    // This fixture's retained Installed YAML Data reports no usable default, so the description
    // must carry that through rather than leaving the prompt to assume the decision can succeed.
    REQUIRE_FALSE(recovery.reset_available);
}

TEST_CASE("CLI Local Ignore recovery description offers reset only when the run can honor it",
          "[scanner][scan-run][local-ignore]") {
    SECTION("an available reset is offered") {
        auto execution = execution_with_result(scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired);
        execution.result.has_installed_yaml_data = true;
        execution.result.installed_yaml_data.local_ignore_reset_available = true;

        REQUIRE(describe_cli_local_ignore_recovery(execution).reset_available);
    }

    SECTION("absent Installed YAML Data keeps offering the decision") {
        // Silence is not a denial. A recovery-required result always carries Installed YAML Data in
        // practice, but withdrawing an option because the run said nothing about it would remove a
        // choice that may well work, and would regress the behavior that shipped before this fact
        // existed. The TUI resolves the same ambiguity the same way.
        auto execution = execution_with_result(scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired);
        execution.result.has_installed_yaml_data = false;

        REQUIRE(describe_cli_local_ignore_recovery(execution).reset_available);
    }
}

TEST_CASE("CLI Local Ignore recovery prompt accepts both Rust-defined decisions when reset is available",
          "[scanner][scan-run][local-ignore]") {
    for (const auto& answer : {std::string("p"), std::string("Proceed"), std::string("  P  ")}) {
        std::istringstream input(answer + "\n");
        std::ostringstream output;
        const CliScanRunCancellation cancellation(false);
        REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation, true) ==
                CliLocalIgnoreRecoveryChoice::ProceedWithoutIgnore);
    }

    for (const auto& answer : {std::string("r"), std::string("RESET")}) {
        std::istringstream input(answer + "\n");
        std::ostringstream output;
        const CliScanRunCancellation cancellation(false);
        REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation, true) ==
                CliLocalIgnoreRecoveryChoice::ResetToDefault);
    }

    std::istringstream input("c\n");
    std::ostringstream output;
    const CliScanRunCancellation cancellation(false);
    REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation, true) ==
            CliLocalIgnoreRecoveryChoice::Cancel);
    REQUIRE(output.str().find("[R] Reset to default") != std::string::npos);
    REQUIRE(output.str().find("[P/R/C]") != std::string::npos);
}

TEST_CASE("CLI Local Ignore recovery prompt withholds Reset To Default when it cannot succeed",
          "[scanner][scan-run][local-ignore]") {
    SECTION("the option is neither listed nor advertised") {
        std::istringstream input("c\n");
        std::ostringstream output;
        const CliScanRunCancellation cancellation(false);
        REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation, false) ==
                CliLocalIgnoreRecoveryChoice::Cancel);
        const auto printed = output.str();
        REQUIRE(printed.find("[R] Reset to default") == std::string::npos);
        REQUIRE(printed.find("[P/R/C]") == std::string::npos);
        REQUIRE(printed.find("[P/C]") != std::string::npos);
        // The remaining decisions are untouched, and the omission is explained rather than silent.
        REQUIRE(printed.find("[P] Proceed without Ignore") != std::string::npos);
        REQUIRE(printed.find("[C] Cancel") != std::string::npos);
        REQUIRE(printed.find("Reset To Default is unavailable") != std::string::npos);
    }

    SECTION("the reset letter is refused if it is entered anyway") {
        // Spending the one-shot continuation on a decision the run already reported it cannot
        // satisfy costs the user the whole scan, so an unlisted letter is rejected like any other
        // unrecognized word rather than honored.
        for (const auto& answer : {std::string("r"), std::string("RESET"), std::string("  reset  ")}) {
            std::istringstream input(answer + "\n" + answer + "\n" + answer + "\n");
            std::ostringstream output;
            const CliScanRunCancellation cancellation(false);
            REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation, false) ==
                    CliLocalIgnoreRecoveryChoice::Cancel);
            REQUIRE(output.str().find("Unrecognized answer. Enter P or C.") != std::string::npos);
            REQUIRE(output.str().find("No usable answer after 3 attempts") != std::string::npos);
        }
    }

    SECTION("the decisions that can succeed still work") {
        std::istringstream proceed_input("p\n");
        std::ostringstream proceed_output;
        const CliScanRunCancellation proceed_cancellation(false);
        REQUIRE(read_cli_local_ignore_recovery_choice(proceed_input, proceed_output, proceed_cancellation, false) ==
                CliLocalIgnoreRecoveryChoice::ProceedWithoutIgnore);

        std::istringstream cancel_input("cancel\n");
        std::ostringstream cancel_output;
        const CliScanRunCancellation cancel_cancellation(false);
        REQUIRE(read_cli_local_ignore_recovery_choice(cancel_input, cancel_output, cancel_cancellation, false) ==
                CliLocalIgnoreRecoveryChoice::Cancel);
    }

    SECTION("end of input still cancels without answering") {
        std::istringstream input("");
        std::ostringstream output;
        const CliScanRunCancellation cancellation(false);
        REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation, false) ==
                CliLocalIgnoreRecoveryChoice::Cancel);
        REQUIRE(output.str().find("No answer was available") != std::string::npos);
    }
}

TEST_CASE("CLI Local Ignore recovery prompt never infers Reset To Default", "[scanner][scan-run][local-ignore]") {
    SECTION("end of input cancels instead of answering") {
        std::istringstream input("");
        std::ostringstream output;
        const CliScanRunCancellation cancellation(false);
        REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation, true) ==
                CliLocalIgnoreRecoveryChoice::Cancel);
        REQUIRE(output.str().find("No answer was available") != std::string::npos);
    }

    SECTION("exhausted invalid answers cancel instead of defaulting") {
        std::istringstream input("yes\nreset to default please\n1\nr\n");
        std::ostringstream output;
        const CliScanRunCancellation cancellation(false);
        REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation, true) ==
                CliLocalIgnoreRecoveryChoice::Cancel);
        REQUIRE(output.str().find("No usable answer after 3 attempts") != std::string::npos);
    }

    SECTION("only the advertised P/R/C answers are honored") {
        // `q` is deliberately not a synonym: the offered menu is the whole input surface.
        std::istringstream input("q\nquit\ny\nr\n");
        std::ostringstream output;
        const CliScanRunCancellation cancellation(false);
        REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation, true) ==
                CliLocalIgnoreRecoveryChoice::Cancel);
        REQUIRE(output.str().find("No usable answer after 3 attempts") != std::string::npos);
    }

    SECTION("cancellation observed before the question consumes no input") {
        std::istringstream input("r\n");
        std::ostringstream output;
        CliScanRunCancellation cancellation(false);
        cancellation.request();
        REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation, true) ==
                CliLocalIgnoreRecoveryChoice::Cancel);
        REQUIRE(output.str().empty());
        std::string unread;
        REQUIRE(static_cast<bool>(std::getline(input, unread)));
        REQUIRE(unread == "r");
    }

    SECTION("cancellation racing the answer overrides an entered reset") {
        std::ostringstream output;
        CliScanRunCancellation cancellation(false);
        CancellingInputBuffer buffer("r\n", cancellation);
        std::istream racing_input(&buffer);
        REQUIRE(read_cli_local_ignore_recovery_choice(racing_input, output, cancellation, true) ==
                CliLocalIgnoreRecoveryChoice::Cancel);
    }
}

TEST_CASE("CLI scan presentation states a resume failure in Rust's words and keeps its code machine-facing",
          "[scanner][scan-run][render]") {
    scanner::ScanRunContractExecutionResult execution{};
    execution.has_resume_error = true;
    execution.resume_error.kind = scanner::ScanRunContractResumeErrorKind::ContinuationConsumed;
    execution.resume_error.code = "scan_run_continuation_consumed";
    execution.resume_error.message = "Crash Log Scan Run continuation was already consumed";
    push_lines(execution.display_lines,
               {text_line("this decision was already applied"), text_line("start again to retry")});

    const auto presentation = present_cli_scan_run_execution(execution, 0.5);
    const auto lines = message_text(presentation.messages);

    REQUIRE(presentation.exit_code == 2);
    REQUIRE(lines == std::vector<std::string>{"this decision was already applied", "start again to retry"});
    // The stable code stays on the DTO for a consumer that matches on it, and stays out of the
    // prose a person reads. Printing it was how a machine identifier used to reach a sentence.
    for (const auto& line : lines) {
        REQUIRE(line.find("scan_run_continuation_consumed") == std::string::npos);
    }
}

TEST_CASE("CLI recovery invariant diagnostics outrank the terminal envelope",
          "[scanner][scan-run][local-ignore]") {
    CliScanRunExecutionOutcome outcome{};
    outcome.execution = execution_with_result(scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired);
    push_lines(outcome.execution.display_lines, {text_line("a decision is needed")});
    outcome.recovery_diagnostics.push_back(
        {true, "Fatal: Crash Log Scan Run requested Local Ignore recovery without retaining its continuation."});

    const auto presentation = present_cli_scan_run_outcome(outcome, 0.5);
    const auto lines = message_text(presentation.messages);

    // A recovery the CLI could not honor is an infrastructure failure, not a status worth exit 1.
    // The diagnostic stays composed here because it reports a broken bridge promise rather than
    // anything a run said, so there is no Rust-rendered line for it to replace.
    REQUIRE(presentation.exit_code == 2);
    REQUIRE(lines[0] ==
            "Fatal: Crash Log Scan Run requested Local Ignore recovery without retaining its continuation.");
    REQUIRE(presentation.messages[0].error);
    REQUIRE(lines.back() == "a decision is needed");
}

TEST_CASE("CLI outcome presentation is unchanged without recovery diagnostics",
          "[scanner][scan-run][local-ignore]") {
    CliScanRunExecutionOutcome outcome{};
    outcome.execution = execution_with_result(scanner::ScanRunContractStatus::Completed);
    outcome.execution.result.total = 1;
    outcome.execution.result.succeeded = 1;
    outcome.local_ignore_continuation_consumed = true;

    const auto direct = present_cli_scan_run_execution(outcome.execution, 1.0);
    const auto via_outcome = present_cli_scan_run_outcome(outcome, 1.0);

    REQUIRE(via_outcome.exit_code == direct.exit_code);
    REQUIRE(message_text(via_outcome.messages) == message_text(direct.messages));
}

TEST_CASE("CLI scan presentation keeps one failure diagnostic on one stream",
          "[scanner][scan-run][local-ignore][render]") {
    // The detail lines of a failure are neutral facts about it, so Rust marks most of them Info.
    // Routing them by severity would put "failed during discovery" on stderr and the path it failed
    // on into stdout, and redirecting stdout would separate the two.
    scanner::ScanRunContractExecutionResult execution{};
    execution.has_resume_error = true;
    execution.resume_error.kind = scanner::ScanRunContractResumeErrorKind::LocalIgnoreResetConflict;
    execution.resume_error.code = "scan_run_local_ignore_reset_conflict";
    push_lines(execution.display_lines,
               {display_line(scanner::ScanRunDisplaySeverity::Failure,
                             {segment(scanner::ScanRunDisplaySegmentKind::Text, "the reset conflicted")}),
                display_line(scanner::ScanRunDisplaySeverity::Info,
                             {segment(scanner::ScanRunDisplaySegmentKind::Text, "Expected sha256"),
                              segment(scanner::ScanRunDisplaySegmentKind::Emphasis, "expected-hash")}),
                display_line(scanner::ScanRunDisplaySeverity::Notice,
                             {segment(scanner::ScanRunDisplaySegmentKind::Text, "nothing was replaced")})});

    const auto presentation = present_cli_scan_run_execution(execution, 0.5);

    REQUIRE(presentation.exit_code == 2);
    REQUIRE(message_text(presentation.messages) ==
            std::vector<std::string>{"the reset conflicted", "Expected sha256 expected-hash",
                                     "nothing was replaced"});
    for (const auto& message : presentation.messages) {
        REQUIRE(message.error);
    }
}

TEST_CASE("CLI scan presentation never reorders the lines Rust rendered", "[scanner][scan-run][render]") {
    // An adapter may reorder, group, or omit whole lines; this one keeps Rust's order for the block
    // it renders, so per-log outcomes still arrive in discovery order without the CLI sorting them.
    auto execution = execution_with_result(scanner::ScanRunContractStatus::Completed);
    execution.result.total = 3;
    execution.result.succeeded = 3;
    push_lines(execution.display_lines,
               {text_line("z-first.log"), text_line("a-second.log"), text_line("m-third.log")});

    const auto lines = message_text(present_cli_scan_run_execution(execution, 1.0).messages);

    REQUIRE(lines[0] == "z-first.log");
    REQUIRE(lines[1] == "a-second.log");
    REQUIRE(lines[2] == "m-third.log");
}

TEST_CASE("CLI completed summary reports only what this process measured", "[scanner][scan-run]") {
    // Scanned, failed, and not-started totals are stated by Rust in the lines above. What remains
    // here is the two aggregates over per-log outcomes and the two facts derived from a clock the
    // contract does not carry, so the CLI is not writing a second account of the same run.
    auto execution = execution_with_result(scanner::ScanRunContractStatus::Completed);
    execution.result.total = 2;
    execution.result.succeeded = 2;

    auto reported = log_result(0, "C:/one.log", scanner::ScanRunContractLogDisposition::Succeeded);
    reported.has_autoscan_report = true;
    reported.autoscan_report = "C:/one-AUTOSCAN.md";
    reported.moved_to_unsolved_logs = true;
    execution.result.logs.push_back(std::move(reported));
    execution.result.logs.push_back(log_result(1, "C:/two.log", scanner::ScanRunContractLogDisposition::Succeeded));

    const auto presentation = present_cli_scan_run_execution(execution, 2.0);
    const auto lines = message_text(presentation.messages);

    REQUIRE(presentation.exit_code == 0);
    REQUIRE(lines == std::vector<std::string>{"Scan Complete", "  Reports: 1 written", "  Unsolved: 1 moved",
                                              "  Duration: 2.00s", "  Speed: 1.0 logs/sec"});
}

TEST_CASE("A real Crash Log Scan Run reaches the CLI already carrying what it says",
          "[scanner][scan-run][render]") {
    // The fixtures above hand-build envelopes, which is what lets them assert rendering without
    // pinning wording. This one runs the real contract, so it is what proves the display lines are
    // actually populated on the way across rather than merely rendered correctly once present.
    const CliArgs args{};
    const auto request = build_cli_scan_run_request(args, minimal_settings(), ".", ".");
    const auto cancellation = scanner::scan_run_cancellation_new();
    scanner::scan_run_cancellation_cancel(*cancellation);

    const auto execution = execute_result(*request, *cancellation, nullptr);

    REQUIRE(execution.has_result);
    REQUIRE_FALSE(execution.display_lines.empty());
    const auto presentation = present_cli_scan_run_execution(execution, 0.1);
    REQUIRE_FALSE(presentation.messages.empty());
    REQUIRE_FALSE(presentation.messages[0].text.empty());
}
