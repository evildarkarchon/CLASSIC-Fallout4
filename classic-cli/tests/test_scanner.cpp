// SPDX-License-Identifier: MIT

#include <catch2/catch_test_macros.hpp>

#include "scan_run_cli.h"

#include <string>
#include <vector>

namespace {

namespace scanner = classic::scanner;

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

PreparedScanUserSettings minimal_settings() {
    PreparedScanUserSettings settings{};
    settings.game = "Fallout4";
    settings.game_version = "auto";
    return settings;
}

} // namespace

TEST_CASE("CLI scan adapter submits Standard intent to the single execution operation", "[scanner][scan-run]") {
    const CliArgs args{};
    const auto request = build_cli_scan_run_request(args, minimal_settings(), ".", ".", ".");
    const auto cancellation = scanner::scan_run_cancellation_new();
    scanner::scan_run_cancellation_cancel(*cancellation);

    const auto execution = scanner::scan_run_contract_execute(*request, *cancellation, nullptr);

    REQUIRE(execution.has_result);
    REQUIRE_FALSE(execution.has_error);
    REQUIRE(execution.result.status == scanner::ScanRunContractStatus::CancelledBeforeDiscovery);
}

TEST_CASE("CLI scan adapter submits raw Targeted inputs to Rust discovery", "[scanner][scan-run]") {
    CliArgs args{};
    args.input_paths.push_back("C:/not-a-crash-log.txt");
    auto settings = minimal_settings();
    settings.move_unsolved_logs = true;
    const auto request = build_cli_scan_run_request(args, settings, ".", ".", ".");
    const auto cancellation = scanner::scan_run_cancellation_new();

    const auto execution = scanner::scan_run_contract_execute(*request, *cancellation, nullptr);

    REQUIRE(execution.has_result);
    REQUIRE_FALSE(execution.has_error);
    REQUIRE(execution.result.status == scanner::ScanRunContractStatus::NoCrashLogsFound);
    REQUIRE(execution.result.has_discovery);
    REQUIRE(execution.result.discovery.source == scanner::ScanRunContractDiscoverySource::Targeted);
    REQUIRE(execution.result.discovery.accepted_logs.empty());
    REQUIRE(execution.result.discovery.rejected_inputs.size() == 1);
    REQUIRE(std::string(execution.result.discovery.rejected_inputs[0].path) == "C:/not-a-crash-log.txt");
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
