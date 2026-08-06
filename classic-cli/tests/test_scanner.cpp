// SPDX-License-Identifier: MIT

#include <catch2/catch_test_macros.hpp>

#include "scan_run_cli.h"

#include <cstddef>
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

TEST_CASE("CLI scan presentation explains a no-logs terminal result", "[scanner][scan-run]") {
    auto execution = execution_with_result(scanner::ScanRunContractStatus::NoCrashLogsFound);
    execution.result.has_discovery = true;
    execution.result.discovery.searched_locations.push_back("C:/Crash Logs");

    const auto presentation = present_cli_scan_run_execution(execution, 0.25);
    const auto lines = message_text(presentation.messages);

    REQUIRE(presentation.exit_code == 0);
    REQUIRE(lines == std::vector<std::string>{"No crash logs found.", "  Searched: C:/Crash Logs"});
}

TEST_CASE("CLI scan discovery reports Targeted rejections", "[scanner][scan-run]") {
    scanner::ScanRunContractEvent event{};
    event.kind = scanner::ScanRunContractEventKind::DiscoveryCompleted;
    event.discovery.source = scanner::ScanRunContractDiscoverySource::Targeted;
    event.discovery.accepted_logs.push_back("C:/accepted.log");
    scanner::ScanRunContractRejectedInput rejected{};
    rejected.path = "C:/notes.txt";
    rejected.reason = "unsupported file type";
    event.discovery.rejected_inputs.push_back(std::move(rejected));

    const auto lines = message_text(describe_cli_scan_run_event(event));

    REQUIRE(lines == std::vector<std::string>{
                         "Found 1 crash log",
                         "Rejected 1 targeted input:",
                         "  C:/notes.txt (unsupported file type)",
                     });
}

TEST_CASE("CLI scan events report Rust-selected concurrency and live progress", "[scanner][scan-run]") {
    scanner::ScanRunContractEvent concurrency{};
    concurrency.kind = scanner::ScanRunContractEventKind::EffectiveConcurrencySelected;
    concurrency.effective_concurrency = 2;

    scanner::ScanRunContractEvent started{};
    started.kind = scanner::ScanRunContractEventKind::LogStarted;
    started.discovery_index = 1;
    started.total = 3;
    started.crash_log = "C:/two.log";

    scanner::ScanRunContractEvent finished{};
    finished.kind = scanner::ScanRunContractEventKind::LogFinished;
    finished.discovery_index = 1;
    finished.total = 3;
    finished.crash_log = "C:/two.log";
    finished.disposition = scanner::ScanRunContractLogDisposition::Failed;

    REQUIRE(message_text(describe_cli_scan_run_event(concurrency)) ==
            std::vector<std::string>{"Scanning with 2 concurrent scans"});
    REQUIRE(message_text(describe_cli_scan_run_event(started)) == std::vector<std::string>{"Scanning 2/3: C:/two.log"});
    REQUIRE(message_text(describe_cli_scan_run_event(finished)) ==
            std::vector<std::string>{"Finished 2/3: C:/two.log - failed"});
}

TEST_CASE("CLI scan cancellation is actionable and has a distinct terminal result", "[scanner][scan-run]") {
    CliScanRunCancellation cancellation(false);
    cancellation.request();
    REQUIRE(scanner::scan_run_cancellation_is_cancelled(cancellation.token()));

    auto execution = execution_with_result(scanner::ScanRunContractStatus::Cancelled);
    execution.result.total = 3;
    execution.result.succeeded = 1;
    execution.result.cancelled = 2;

    const auto presentation = present_cli_scan_run_execution(execution, 0.5);

    REQUIRE(presentation.exit_code == 130);
    REQUIRE(message_text(presentation.messages).back() == "Scan cancelled safely: 1 completed, 2 not started.");
}

TEST_CASE("CLI scan presentation explains FCX setup outcomes", "[scanner][scan-run]") {
    auto execution = execution_with_result(scanner::ScanRunContractStatus::SetupFailed);
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
    REQUIRE(lines[0] == "Crash Log Scan setup failed.");
    REQUIRE(lines[1] == "FCX setup: action_required");
    REQUIRE(lines[2] == "  Select the Fallout 4 installation.");
    REQUIRE(lines[3] == "  [missing] game_executable: Fallout4.exe was not found");
    REQUIRE(lines[4] == "    Expected under the configured game root.");
    REQUIRE(lines[5] == "  Action: Configure the game path and retry.");
}

TEST_CASE("CLI scan presentation acknowledges generated Local Ignore metadata and diagnostics",
          "[scanner][scan-run]") {
    auto execution = execution_with_result(scanner::ScanRunContractStatus::Completed);
    execution.result.has_installed_yaml_data = true;
    auto& installed = execution.result.installed_yaml_data;
    installed.main.role = scanner::ScanRunInstalledYamlDataRole::Main;
    installed.main.provenance = scanner::ScanRunInstalledYamlDataProvenance::Bundled;
    installed.main.schema_version = "2.0";
    installed.main.sha256 = "main-hash";
    installed.main.byte_len = 64;
    installed.game_file.role = scanner::ScanRunInstalledYamlDataRole::Game;
    installed.game_file.provenance = scanner::ScanRunInstalledYamlDataProvenance::Previous;
    installed.game_file.schema_version = "1.0";
    installed.game_file.sha256 = "game-hash";
    installed.game_file.byte_len = 48;
    installed.local_ignore_state = scanner::ScanRunLocalIgnoreYamlDataState::Generated;
    installed.local_ignore_identity.sha256 = "ignore-hash";
    installed.local_ignore_identity.byte_len = 32;
    scanner::ScanRunInstalledYamlDataDiagnosticDto diagnostic{};
    diagnostic.kind = scanner::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated;
    diagnostic.has_path = true;
    diagnostic.path = "C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml";
    diagnostic.message = "generated missing Local Ignore YAML Data";
    installed.diagnostics.push_back(std::move(diagnostic));

    const auto lines = message_text(present_cli_scan_run_execution(execution, 1.0).messages);

    REQUIRE(lines[0] == "Installed YAML Data:");
    REQUIRE(lines[1].find("Main: bundled schema 2.0") != std::string::npos);
    REQUIRE(lines[2].find("Game: previous schema 1.0") != std::string::npos);
    // Both are canonical Display Labels the configuration crate settled, reached
    // through the bridge rather than a CLI table. `generated from selected Main
    // defaults` replaces the bare `generated` this frontend used to print, and
    // `Local Ignore generated` carries the glossary capitalization of a domain
    // term that no transform of the `local_ignore_generated` token could infer.
    REQUIRE(lines[3].find("Local Ignore: generated from selected Main defaults") != std::string::npos);
    REQUIRE(lines[4].find("Local Ignore generated") != std::string::npos);
    REQUIRE(lines[4].find("CLASSIC Ignore.yaml") != std::string::npos);
}

TEST_CASE("CLI scan presentation keeps Local Ignore recovery distinct from setup and infrastructure failures",
          "[scanner][scan-run]") {
    auto execution = execution_with_result(scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired);
    execution.result.has_message = true;
    execution.result.message = "Local Ignore recovery is required";
    execution.result.has_installed_yaml_data = true;
    execution.result.installed_yaml_data.local_ignore_state =
        scanner::ScanRunLocalIgnoreYamlDataState::RecoveryRequired;

    const auto presentation = present_cli_scan_run_execution(execution, 0.5);

    REQUIRE(presentation.exit_code == 1);
    REQUIRE(presentation.messages.back().error);
    REQUIRE(presentation.messages.back().text == "Local Ignore recovery is required");
}

TEST_CASE("CLI Local Ignore recovery description offers retained discovery and diagnostics",
          "[scanner][scan-run][local-ignore]") {
    auto execution = execution_with_result(scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired);
    execution.result.has_message = true;
    execution.result.message = "Local Ignore YAML Data is malformed";
    execution.result.has_discovery = true;
    execution.result.discovery.accepted_logs.push_back("C:/one.log");
    execution.result.discovery.accepted_logs.push_back("C:/two.log");
    execution.result.has_installed_yaml_data = true;
    auto& installed = execution.result.installed_yaml_data;
    installed.local_ignore_state = scanner::ScanRunLocalIgnoreYamlDataState::RecoveryRequired;
    installed.local_ignore_identity.sha256 = "malformed-hash";
    installed.local_ignore_identity.byte_len = 12;
    scanner::ScanRunInstalledYamlDataDiagnosticDto diagnostic{};
    diagnostic.kind = scanner::ScanRunInstalledYamlDataDiagnosticKind::Parse;
    diagnostic.has_path = true;
    diagnostic.path = "C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml";
    diagnostic.message = "mapping values are not allowed here";
    installed.diagnostics.push_back(std::move(diagnostic));

    const auto lines = message_text(describe_cli_local_ignore_recovery(execution.result));

    REQUIRE(lines[0] == "Local Ignore YAML Data is malformed");
    REQUIRE(lines[1] == "Installed YAML Data:");
    REQUIRE(lines[4].find("Local Ignore: recovery required") != std::string::npos);
    REQUIRE(lines[5].find("mapping values are not allowed here") != std::string::npos);
    REQUIRE(lines[5].find("CLASSIC Ignore.yaml") != std::string::npos);
    REQUIRE(lines.back() == "  Retained discovery: 2 crash logs will be scanned once you decide.");
}

TEST_CASE("CLI Local Ignore recovery prompt accepts both Rust-defined decisions",
          "[scanner][scan-run][local-ignore]") {
    for (const auto& answer : {std::string("p"), std::string("Proceed"), std::string("  P  ")}) {
        std::istringstream input(answer + "\n");
        std::ostringstream output;
        const CliScanRunCancellation cancellation(false);
        REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation) ==
                CliLocalIgnoreRecoveryChoice::ProceedWithoutIgnore);
    }

    for (const auto& answer : {std::string("r"), std::string("RESET")}) {
        std::istringstream input(answer + "\n");
        std::ostringstream output;
        const CliScanRunCancellation cancellation(false);
        REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation) ==
                CliLocalIgnoreRecoveryChoice::ResetToDefault);
    }

    std::istringstream input("c\n");
    std::ostringstream output;
    const CliScanRunCancellation cancellation(false);
    REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation) ==
            CliLocalIgnoreRecoveryChoice::Cancel);
    REQUIRE(output.str().find("[R] Reset to default") != std::string::npos);
}

TEST_CASE("CLI Local Ignore recovery prompt never infers Reset To Default", "[scanner][scan-run][local-ignore]") {
    SECTION("end of input cancels instead of answering") {
        std::istringstream input("");
        std::ostringstream output;
        const CliScanRunCancellation cancellation(false);
        REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation) ==
                CliLocalIgnoreRecoveryChoice::Cancel);
        REQUIRE(output.str().find("No answer was available") != std::string::npos);
    }

    SECTION("exhausted invalid answers cancel instead of defaulting") {
        std::istringstream input("yes\nreset to default please\n1\nr\n");
        std::ostringstream output;
        const CliScanRunCancellation cancellation(false);
        REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation) ==
                CliLocalIgnoreRecoveryChoice::Cancel);
        REQUIRE(output.str().find("No usable answer after 3 attempts") != std::string::npos);
    }

    SECTION("only the advertised P/R/C answers are honored") {
        // `q` is deliberately not a synonym: the offered menu is the whole input surface.
        std::istringstream input("q\nquit\ny\nr\n");
        std::ostringstream output;
        const CliScanRunCancellation cancellation(false);
        REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation) ==
                CliLocalIgnoreRecoveryChoice::Cancel);
        REQUIRE(output.str().find("No usable answer after 3 attempts") != std::string::npos);
    }

    SECTION("cancellation observed before the question consumes no input") {
        std::istringstream input("r\n");
        std::ostringstream output;
        CliScanRunCancellation cancellation(false);
        cancellation.request();
        REQUIRE(read_cli_local_ignore_recovery_choice(input, output, cancellation) ==
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
        REQUIRE(read_cli_local_ignore_recovery_choice(racing_input, output, cancellation) ==
                CliLocalIgnoreRecoveryChoice::Cancel);
    }
}

TEST_CASE("CLI scan presentation preserves consumed continuation replay details", "[scanner][scan-run]") {
    scanner::ScanRunContractExecutionResult execution{};
    execution.has_resume_error = true;
    execution.resume_error.kind = scanner::ScanRunContractResumeErrorKind::ContinuationConsumed;
    execution.resume_error.code = "scan_run_continuation_consumed";
    execution.resume_error.message = "Crash Log Scan Run continuation was already consumed";

    const auto presentation = present_cli_scan_run_execution(execution, 0.5);

    REQUIRE(presentation.exit_code == 2);
    REQUIRE(presentation.messages.size() == 1);
    REQUIRE(presentation.messages[0].error);
    REQUIRE(presentation.messages[0].text ==
            "Fatal: Crash Log Scan recovery failed (scan_run_continuation_consumed): Crash Log Scan Run continuation "
            "was already consumed");
}

TEST_CASE("CLI recovery invariant diagnostics outrank the terminal envelope",
          "[scanner][scan-run][local-ignore]") {
    CliScanRunExecutionOutcome outcome{};
    outcome.execution = execution_with_result(scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired);
    outcome.execution.result.has_message = true;
    outcome.execution.result.message = "Local Ignore recovery is required";
    outcome.recovery_diagnostics.push_back(
        {true, "Fatal: Crash Log Scan Run requested Local Ignore recovery without retaining its continuation."});

    const auto presentation = present_cli_scan_run_outcome(outcome, 0.5);
    const auto lines = message_text(presentation.messages);

    // A recovery the CLI could not honor is an infrastructure failure, not a status worth exit 1.
    REQUIRE(presentation.exit_code == 2);
    REQUIRE(lines[0] ==
            "Fatal: Crash Log Scan Run requested Local Ignore recovery without retaining its continuation.");
    REQUIRE(presentation.messages[0].error);
    REQUIRE(lines.back() == "Local Ignore recovery is required");
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

TEST_CASE("CLI scan presentation makes typed reset failures actionable", "[scanner][scan-run][local-ignore]") {
    scanner::ScanRunContractExecutionResult execution{};
    execution.has_resume_error = true;
    execution.resume_error.kind = scanner::ScanRunContractResumeErrorKind::LocalIgnoreResetConflict;
    execution.resume_error.code = "scan_run_local_ignore_reset_conflict";
    execution.resume_error.message = "Local Ignore YAML Data changed while the decision was pending";
    execution.resume_error.has_path = true;
    execution.resume_error.path = "C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml";
    execution.resume_error.has_expected_identity = true;
    execution.resume_error.expected_identity.sha256 = "expected-hash";
    execution.resume_error.expected_identity.byte_len = 12;
    execution.resume_error.has_actual_identity = true;
    execution.resume_error.actual_identity.sha256 = "actual-hash";
    execution.resume_error.actual_identity.byte_len = 30;

    const auto presentation = present_cli_scan_run_execution(execution, 0.5);
    const auto lines = message_text(presentation.messages);

    REQUIRE(presentation.exit_code == 2);
    REQUIRE(lines[1] == "  Path: C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml");
    REQUIRE(lines[2] == "  Expected identity: sha256 expected-hash (12 bytes)");
    REQUIRE(lines[3] == "  Actual identity: sha256 actual-hash (30 bytes)");
    for (const auto& message : presentation.messages) {
        REQUIRE(message.error);
    }
}

TEST_CASE("CLI scan presentation reports a durable reset that outlived its failed resume",
          "[scanner][scan-run][local-ignore]") {
    scanner::ScanRunContractExecutionResult execution{};
    execution.has_resume_error = true;
    execution.resume_error.kind = scanner::ScanRunContractResumeErrorKind::LocalIgnoreResetDurabilityUnknown;
    execution.resume_error.code = "scan_run_local_ignore_reset_durability_unknown";
    execution.resume_error.message = "Local Ignore reset durability could not be confirmed";
    execution.resume_error.has_stage = true;
    execution.resume_error.stage = scanner::ScanRunLocalIgnoreResetFailureStage::Sync;
    execution.resume_error.has_backup_path = true;
    execution.resume_error.backup_path = "C:/CLASSIC/CLASSIC Backup/YAML Data/Local Ignore/ignore.yaml";
    execution.resume_error.has_durability_receipt = true;
    execution.resume_error.malformed_identity.sha256 = "malformed-hash";
    execution.resume_error.backup_identity.sha256 = "backup-hash";
    execution.resume_error.replacement_identity.sha256 = "replacement-hash";

    const auto lines = message_text(present_cli_scan_run_execution(execution, 0.5).messages);

    REQUIRE(lines[1] == "  Stage: sync");
    REQUIRE(lines[2] == "  Verified backup: C:/CLASSIC/CLASSIC Backup/YAML Data/Local Ignore/ignore.yaml");
    REQUIRE(lines[3] == "  Durable reset receipt: malformed sha256 malformed-hash, backup sha256 backup-hash, "
                        "replacement sha256 replacement-hash");
}

TEST_CASE("CLI scan presentation distinguishes mixed per-log outcomes", "[scanner][scan-run]") {
    auto execution = execution_with_result(scanner::ScanRunContractStatus::Cancelled);
    execution.result.total = 3;
    execution.result.succeeded = 1;
    execution.result.failed = 1;
    execution.result.cancelled = 1;

    auto succeeded = log_result(0, "C:/one.log", scanner::ScanRunContractLogDisposition::Succeeded);
    succeeded.has_autoscan_report = true;
    succeeded.autoscan_report = "C:/one-AUTOSCAN.md";
    execution.result.logs.push_back(std::move(succeeded));

    auto failed = log_result(1, "C:/two.log", scanner::ScanRunContractLogDisposition::Failed);
    scanner::ScanRunContractLogFailure failure{};
    failure.stage = scanner::ScanRunContractLogFailureStage::ReportWrite;
    failure.message = "access denied";
    failed.failures.push_back(std::move(failure));
    execution.result.logs.push_back(std::move(failed));

    execution.result.logs.push_back(
        log_result(2, "C:/three.log", scanner::ScanRunContractLogDisposition::CancelledBeforeStart));

    const auto presentation = present_cli_scan_run_execution(execution, 2.0);
    const auto lines = message_text(presentation.messages);

    REQUIRE(presentation.exit_code == 130);
    REQUIRE(lines[1] == "  1. C:/one.log - succeeded (report: C:/one-AUTOSCAN.md)");
    REQUIRE(lines[2] == "  2. C:/two.log - failed [report write: access denied]");
    REQUIRE(lines[3] == "  3. C:/three.log - cancelled before start");
    REQUIRE(lines.back() == "Scan cancelled safely: 2 completed, 1 not started.");
}

TEST_CASE("CLI scan summaries retain the Rust-provided discovery order", "[scanner][scan-run]") {
    auto execution = execution_with_result(scanner::ScanRunContractStatus::Completed);
    execution.result.total = 3;
    execution.result.succeeded = 3;
    execution.result.logs.push_back(log_result(0, "C:/z-first.log", scanner::ScanRunContractLogDisposition::Succeeded));
    execution.result.logs.push_back(
        log_result(1, "C:/a-second.log", scanner::ScanRunContractLogDisposition::Succeeded));
    execution.result.logs.push_back(log_result(2, "C:/m-third.log", scanner::ScanRunContractLogDisposition::Succeeded));

    const auto lines = message_text(present_cli_scan_run_execution(execution, 1.0).messages);

    REQUIRE(lines[1].find("z-first.log") != std::string::npos);
    REQUIRE(lines[2].find("a-second.log") != std::string::npos);
    REQUIRE(lines[3].find("m-third.log") != std::string::npos);
}
