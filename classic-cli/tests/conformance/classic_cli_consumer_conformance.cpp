// SPDX-License-Identifier: MIT
//
// Test-only Crash Log Scan Run consumer receipt runner for the native CLI.

#include "scan_run_cli.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <vector>

namespace {

namespace fs = std::filesystem;
namespace scanner = classic::scanner;
using json = nlohmann::json;

constexpr int SKIP_RETURN_CODE = 125;
constexpr std::string_view RUN_PLAN_ENV = "CLASSIC_CONSUMER_CONFORMANCE_RUN_PLAN";
constexpr std::string_view OUTPUT_ENV = "CLASSIC_CONSUMER_CONFORMANCE_OUTPUT";
constexpr std::string_view RUNNER_ID = "classic-cli-consumer-conformance";
constexpr std::string_view TOOLCHAIN = CLASSIC_CLI_CONSUMER_CONFORMANCE_TOOLCHAIN;

class RunnerError final : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

/// Reads one process environment value without retaining runtime-owned memory.
std::optional<std::string> read_environment(std::string_view name) {
#ifdef _WIN32
    char* value = nullptr;
    std::size_t length = 0;
    if (_dupenv_s(&value, &length, std::string(name).c_str()) != 0) {
        throw RunnerError("cannot read process environment");
    }
    std::optional<std::string> result;
    if (value != nullptr) {
        result = std::string(value);
        std::free(value);
    }
    return result;
#else
    const char* value = std::getenv(std::string(name).c_str());
    return value == nullptr ? std::nullopt : std::optional<std::string>(value);
#endif
}

/// Sets or clears one process environment variable for the isolated recovery run.
void set_environment(std::string_view name, const std::optional<std::string>& value) {
#ifdef _WIN32
    if (_putenv_s(std::string(name).c_str(), value.value_or("").c_str()) != 0) {
        throw RunnerError("cannot update isolated process environment");
    }
#else
    const int result =
        value.has_value() ? setenv(std::string(name).c_str(), value->c_str(), 1) : unsetenv(std::string(name).c_str());
    if (result != 0) {
        throw RunnerError("cannot update isolated process environment");
    }
#endif
}

/// Owns a fresh, invocation-bound directory for a real recovery interaction.
class TemporaryDirectory final {
public:
    /// Creates a short directory name so reset backups remain within legacy Windows path limits.
    TemporaryDirectory(std::string_view invocation_id, std::string_view scenario_id) {
        const std::string invocation(invocation_id.substr(0, std::min<std::size_t>(8, invocation_id.size())));
        path_ = fs::temp_directory_path() / ("clc-" + invocation + "-" + std::string(scenario_id));
        if (!fs::create_directory(path_)) {
            throw RunnerError("CLI consumer scenario directory is not fresh: " + path_.string());
        }
    }

    /// Removes all isolated inputs and run effects without masking the receipt outcome.
    ~TemporaryDirectory() {
        std::error_code error;
        fs::remove_all(path_, error);
    }

    TemporaryDirectory(const TemporaryDirectory&) = delete;
    TemporaryDirectory& operator=(const TemporaryDirectory&) = delete;

    /// Returns the absolute root borrowed by the synchronous recovery run.
    [[nodiscard]] const fs::path& path() const noexcept { return path_; }

private:
    fs::path path_;
};

/// Isolates cache lookup and current-directory state for one real recovery interaction.
class RuntimeEnvironment final {
public:
    /// Redirects user cache state beneath the scenario root.
    explicit RuntimeEnvironment(const fs::path& root)
        : previous_directory_(fs::current_path()) {
        for (const auto name : {"LOCALAPPDATA", "XDG_CACHE_HOME"}) {
            previous_environment_.emplace(name, read_environment(name));
        }
        const fs::path cache = root / "isolated-cache";
        fs::create_directories(cache);
        set_environment("LOCALAPPDATA", cache.string());
        set_environment("XDG_CACHE_HOME", cache.string());
        fs::current_path(root);
    }

    /// Restores process state without replacing a primary conformance failure.
    ~RuntimeEnvironment() {
        std::error_code error;
        fs::current_path(previous_directory_, error);
        for (const auto& [name, value] : previous_environment_) {
            try {
                set_environment(name, value);
            } catch (const RunnerError&) {
                // Destruction cannot safely replace the primary conformance outcome.
            }
        }
    }

    RuntimeEnvironment(const RuntimeEnvironment&) = delete;
    RuntimeEnvironment& operator=(const RuntimeEnvironment&) = delete;

private:
    fs::path previous_directory_;
    std::map<std::string, std::optional<std::string>> previous_environment_;
};

/// Returns one Rust-owned string as an ordinary C++ value.
std::string owned_string(const rust::String& value) {
    return std::string(value.data(), value.size());
}

/// Returns the stable receipt token for one Display Content severity.
std::string_view severity_token(scanner::ScanRunDisplaySeverity severity) {
    switch (severity) {
    case scanner::ScanRunDisplaySeverity::Info:
        return "info";
    case scanner::ScanRunDisplaySeverity::Notice:
        return "notice";
    case scanner::ScanRunDisplaySeverity::Warning:
        return "warning";
    case scanner::ScanRunDisplaySeverity::Failure:
        return "failure";
    case scanner::ScanRunDisplaySeverity::Success:
        return "success";
    }
    throw RunnerError("unrecognized CLI Display Content severity");
}

/// Returns the stable receipt token for one typed Display Content segment.
std::string_view segment_kind_token(scanner::ScanRunDisplaySegmentKind kind) {
    switch (kind) {
    case scanner::ScanRunDisplaySegmentKind::Text:
        return "text";
    case scanner::ScanRunDisplaySegmentKind::Label:
        return "label";
    case scanner::ScanRunDisplaySegmentKind::Path:
        return "path";
    case scanner::ScanRunDisplaySegmentKind::Count:
        return "count";
    case scanner::ScanRunDisplaySegmentKind::Name:
        return "name";
    case scanner::ScanRunDisplaySegmentKind::Emphasis:
        return "emphasis";
    }
    throw RunnerError("unrecognized CLI Display Content segment kind");
}

/// Serializes the complete frozen segment carrier, including empty unused fields.
json serialize_segment(const scanner::ScanRunDisplaySegment& segment) {
    return json{{"kind", segment_kind_token(segment.kind)},
                {"text", owned_string(segment.text)},
                {"path", owned_string(segment.path)},
                {"count", segment.count}};
}

/// Builds one deliberately unreal segment so the consumer cannot pass with copied Rust prose.
scanner::ScanRunDisplaySegment display_segment(scanner::ScanRunDisplaySegmentKind kind, std::string text,
                                               std::string path = {}, std::uint64_t count = 0) {
    scanner::ScanRunDisplaySegment segment{};
    segment.kind = kind;
    segment.text = std::move(text);
    segment.path = std::move(path);
    segment.count = count;
    return segment;
}

/// Builds the stable synthetic Display Content profile exercised at the maintained CLI seam.
scanner::ScanRunContractExecutionResult synthetic_display_execution() {
    scanner::ScanRunContractExecutionResult execution{};
    execution.has_result = true;
    execution.result.status = scanner::ScanRunContractStatus::NoCrashLogsFound;

    scanner::ScanRunDisplayLine line{};
    line.severity = scanner::ScanRunDisplaySeverity::Info;
    line.segments.push_back(display_segment(scanner::ScanRunDisplaySegmentKind::Text, "unowned preface"));
    line.segments.push_back(display_segment(scanner::ScanRunDisplaySegmentKind::Label, "unowned label"));
    // The deliberately mismatched noun proves the CLI transports Rust's selected noun unchanged.
    line.segments.push_back(display_segment(scanner::ScanRunDisplaySegmentKind::Count, "singular-widget", {}, 7));
    line.segments.push_back(
        display_segment(scanner::ScanRunDisplaySegmentKind::Path, {}, "C:/Receipt Fixture/unowned crash.log"));
    line.segments.push_back(display_segment(scanner::ScanRunDisplaySegmentKind::Name, "unowned name"));
    line.segments.push_back(display_segment(scanner::ScanRunDisplaySegmentKind::Emphasis, "unowned emphasis"));
    execution.display_lines.push_back(std::move(line));
    return execution;
}

/// Observes typed delivery and actual plain rendering through the production presentation seam.
json observe_display_content_delivery() {
    const auto execution = synthetic_display_execution();
    const auto presentation = present_cli_scan_run_execution(execution, 1.0);
    if (presentation.messages.size() != execution.display_lines.size()) {
        throw RunnerError("CLI display delivery changed the number of Rust-owned lines");
    }

    json lines = json::array();
    for (std::size_t index = 0; index < execution.display_lines.size(); ++index) {
        const auto& source = execution.display_lines[index];
        const auto& rendered = presentation.messages[index];
        json segments = json::array();
        for (const auto& segment : source.segments) {
            segments.push_back(serialize_segment(segment));
        }
        lines.push_back(json{{"severity", severity_token(source.severity)},
                             {"segments", std::move(segments)},
                             {"renderedText", rendered.text},
                             {"stream", rendered.error ? "stderr" : "stdout"}});
    }
    return json{{"lines", std::move(lines)}};
}

/// Creates an execution envelope for one stable stream or exit-code profile case.
scanner::ScanRunContractExecutionResult synthetic_routing_execution(std::string_view scenario_id) {
    scanner::ScanRunContractExecutionResult execution{};
    if (scenario_id == "standard-happy-path") {
        execution.has_result = true;
        execution.result.status = scanner::ScanRunContractStatus::Completed;
        execution.result.total = 1;
        execution.result.succeeded = 1;
        scanner::ScanRunDisplayLine info{};
        info.severity = scanner::ScanRunDisplaySeverity::Info;
        info.segments.push_back(display_segment(scanner::ScanRunDisplaySegmentKind::Text, "ordinary output"));
        scanner::ScanRunDisplayLine success{};
        success.severity = scanner::ScanRunDisplaySeverity::Success;
        success.segments.push_back(display_segment(scanner::ScanRunDisplaySegmentKind::Text, "successful output"));
        execution.display_lines.push_back(std::move(info));
        execution.display_lines.push_back(std::move(success));
        return execution;
    }
    if (scenario_id == "intake-failure") {
        execution.has_error = true;
        scanner::ScanRunDisplayLine failure{};
        failure.severity = scanner::ScanRunDisplaySeverity::Failure;
        failure.segments.push_back(display_segment(scanner::ScanRunDisplaySegmentKind::Text, "unowned failure"));
        scanner::ScanRunDisplayLine detail{};
        detail.severity = scanner::ScanRunDisplaySeverity::Info;
        detail.segments.push_back(display_segment(scanner::ScanRunDisplaySegmentKind::Text, "unowned detail"));
        execution.display_lines.push_back(std::move(failure));
        execution.display_lines.push_back(std::move(detail));
        return execution;
    }
    if (scenario_id == "pre-discovery-cancelled") {
        execution.has_result = true;
        execution.result.status = scanner::ScanRunContractStatus::CancelledBeforeDiscovery;
        return execution;
    }
    if (scenario_id == "proceed-without-ignore-recovery") {
        execution.has_result = true;
        execution.result.status = scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired;
        return execution;
    }
    throw RunnerError("unsupported CLI routing profile scenario: " + std::string(scenario_id));
}

/// Observes the per-line stream selected by the production presentation seam.
json observe_stream_case(std::string_view scenario_id) {
    const auto execution = synthetic_routing_execution(scenario_id);
    const auto presentation = present_cli_scan_run_execution(execution, 1.0);
    if (presentation.messages.size() < execution.display_lines.size()) {
        throw RunnerError("CLI stream profile dropped a Rust-owned line");
    }
    json routes = json::array();
    for (std::size_t index = 0; index < execution.display_lines.size(); ++index) {
        routes.push_back(presentation.messages[index].error ? "stderr" : "stdout");
    }
    return json{{"scenarioId", scenario_id}, {"routes", std::move(routes)}};
}

/// Observes the process exit code selected by the production presentation seam.
json observe_exit_code_case(std::string_view scenario_id) {
    const auto execution = synthetic_routing_execution(scenario_id);
    const auto presentation = present_cli_scan_run_execution(execution, 1.0);
    return json{{"scenarioId", scenario_id}, {"exitCode", presentation.exit_code}};
}

/// Copies one launcher-declared fixture to an isolated consumer-profile path.
void copy_fixture(const json& plan, std::string_view fixture_ref, const fs::path& destination) {
    const auto fixture = plan.at("fixtures").find(std::string(fixture_ref));
    if (fixture == plan.at("fixtures").end() || !fixture->is_string()) {
        throw RunnerError("CLI recovery profile requires fixture " + std::string(fixture_ref));
    }
    fs::create_directories(destination.parent_path());
    fs::copy_file(fs::path(fixture->get<std::string>()), destination, fs::copy_options::overwrite_existing);
}

/// Maps one recovery scenario identity onto the explicit answer supplied by the consumer profile.
CliLocalIgnoreRecoveryChoice recovery_choice(std::string_view scenario_id) {
    if (scenario_id == "proceed-without-ignore-recovery") {
        return CliLocalIgnoreRecoveryChoice::ProceedWithoutIgnore;
    }
    if (scenario_id == "reset-to-default-recovery") {
        return CliLocalIgnoreRecoveryChoice::ResetToDefault;
    }
    if (scenario_id == "abandon-local-ignore-recovery") {
        return CliLocalIgnoreRecoveryChoice::Cancel;
    }
    throw RunnerError("unsupported CLI recovery profile scenario: " + std::string(scenario_id));
}

/// Returns the stable token for the explicit answer supplied to the CLI recovery callback.
std::string_view recovery_choice_token(CliLocalIgnoreRecoveryChoice choice) {
    switch (choice) {
    case CliLocalIgnoreRecoveryChoice::ProceedWithoutIgnore:
        return "proceed_without_ignore";
    case CliLocalIgnoreRecoveryChoice::ResetToDefault:
        return "reset_to_default";
    case CliLocalIgnoreRecoveryChoice::Cancel:
        return "cancel";
    }
    throw RunnerError("unrecognized CLI recovery choice");
}

/// Returns the stable token for one Rust-owned recovery decision.
std::string_view recovery_decision_token(scanner::ScanRunLocalIgnoreRecoveryDecision decision) {
    switch (decision) {
    case scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore:
        return "proceed_without_ignore";
    case scanner::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault:
        return "reset_to_default";
    }
    throw RunnerError("unrecognized CLI recovery decision");
}

/// Executes one real retained Local Ignore continuation through the production CLI callback seam.
json observe_recovery_case(const json& plan, std::string_view scenario_id) {
    const std::string invocation_id = plan.at("invocation").at("id").get<std::string>();
    TemporaryDirectory temporary(invocation_id, scenario_id);
    copy_fixture(plan, "mainYaml", temporary.path() / "CLASSIC Data/databases/CLASSIC Main.yaml");
    copy_fixture(plan, "gameYaml", temporary.path() / "CLASSIC Data/databases/CLASSIC Fallout4.yaml");
    copy_fixture(plan, "malformedLocalIgnoreYaml", temporary.path() / "CLASSIC Data/CLASSIC Ignore.yaml");
    const fs::path crash_log = temporary.path() / (std::string(scenario_id) + ".log");
    copy_fixture(plan, "validCrashLog", crash_log);

    RuntimeEnvironment environment(temporary.path());
    scanner::ScanRunConfigurationDto configuration{};
    configuration.installation_root = temporary.path().string();
    configuration.game = scanner::ScanRunGameId::Fallout4;
    configuration.game_version = "auto";
    configuration.has_max_concurrent = true;
    configuration.max_concurrent = 1;
    scanner::ScanRunTargetedSourceDto source{};
    source.inputs.push_back(crash_log.string());
    const auto request = scanner::scan_run_request_targeted(configuration, source);

    CliScanRunCancellation cancellation(false);
    const auto selected = recovery_choice(scenario_id);
    bool prompted = false;
    json offered = json::array();
    const auto outcome =
        execute_cli_scan_run(*request, cancellation, nullptr, [&](const CliLocalIgnoreRecoveryPresentation& recovery) {
            prompted = true;
            for (const auto& option : recovery.decisions) {
                if (option.available) {
                    offered.push_back(
                        json{{"decision", recovery_decision_token(option.decision)}, {"available", true}});
                }
            }
            const std::string answer = selected == CliLocalIgnoreRecoveryChoice::ProceedWithoutIgnore ? "p\n"
                                       : selected == CliLocalIgnoreRecoveryChoice::ResetToDefault     ? "r\n"
                                                                                                      : "c\n";
            std::istringstream input(answer);
            std::ostringstream output;
            const auto read_choice =
                read_cli_local_ignore_recovery_choice(input, output, cancellation, recovery.decisions);
            if (read_choice != selected) {
                throw RunnerError("CLI recovery input selected an unexpected decision");
            }
            return read_choice;
        });
    const auto presentation = present_cli_scan_run_outcome(outcome, 1.0);
    return json{{"scenarioId", scenario_id},
                {"prompted", prompted},
                {"offered", std::move(offered)},
                {"selected", recovery_choice_token(selected)},
                {"continuationConsumed", outcome.local_ignore_continuation_consumed},
                {"terminalExitCode", presentation.exit_code}};
}

/// Requires an obligation to carry exactly its catalog-owned scenario identity list.
void validate_scenario_ids(const json& obligation, const std::vector<std::string>& expected) {
    const auto actual = obligation.at("scenarioIds").get<std::vector<std::string>>();
    if (actual != expected) {
        throw RunnerError("CLI consumer obligation has an unexpected scenario profile");
    }
}

/// Executes one named consumer obligation and returns its narrow actual observation.
json execute_obligation(const json& plan, const json& obligation) {
    const std::string id = obligation.at("id").get<std::string>();
    if (id == "cli.display-content-delivery") {
        validate_scenario_ids(obligation, {"standard-happy-path"});
        return observe_display_content_delivery();
    }
    if (id == "cli.stream-selection") {
        validate_scenario_ids(obligation, {"standard-happy-path", "intake-failure"});
        json cases = json::array();
        cases.push_back(observe_stream_case("standard-happy-path"));
        cases.push_back(observe_stream_case("intake-failure"));
        return json{{"cases", std::move(cases)}};
    }
    if (id == "cli.exit-code-routing") {
        validate_scenario_ids(obligation, {"standard-happy-path", "intake-failure", "pre-discovery-cancelled",
                                           "proceed-without-ignore-recovery"});
        json cases = json::array();
        cases.push_back(observe_exit_code_case("standard-happy-path"));
        cases.push_back(observe_exit_code_case("intake-failure"));
        cases.push_back(observe_exit_code_case("pre-discovery-cancelled"));
        cases.push_back(observe_exit_code_case("proceed-without-ignore-recovery"));
        return json{{"cases", std::move(cases)}};
    }
    if (id == "cli.recovery-interaction") {
        validate_scenario_ids(obligation, {"proceed-without-ignore-recovery", "reset-to-default-recovery",
                                           "abandon-local-ignore-recovery"});
        json cases = json::array();
        for (const auto& scenario_id : obligation.at("scenarioIds")) {
            cases.push_back(observe_recovery_case(plan, scenario_id.get<std::string>()));
        }
        return json{{"cases", std::move(cases)}};
    }
    throw RunnerError("unsupported CLI consumer obligation: " + id);
}

/// Retains one obligation-local runner failure inside an otherwise valid receipt.
json obligation_receipt(const json& plan, const json& obligation) {
    try {
        return json{{"id", obligation.at("id")},
                    {"executionStatus", "completed"},
                    {"observation", execute_obligation(plan, obligation)},
                    {"failure", nullptr}};
    } catch (const std::exception& error) {
        return json{{"id", obligation.value("id", "unknown")},
                    {"executionStatus", "failed"},
                    {"observation", nullptr},
                    {"failure", json{{"kind", "cli-consumer-runner-error"}, {"message", error.what()}}}};
    }
}

/// Rejects semantic inputs and plans for any other execution identity.
void validate_plan(const json& plan) {
    if (!plan.is_object() || plan.at("schemaVersion") != 1 || plan.at("familyId") != "crash-log-scan-run") {
        throw RunnerError("unsupported CLI consumer conformance run plan");
    }
    const json& participant = plan.at("participant");
    const std::string expected_instance = "windows-" + std::string(TOOLCHAIN);
    if (participant.at("id") != "cli" || participant.at("role") != "consumer" ||
        participant.at("executionInstanceId") != expected_instance) {
        throw RunnerError("run plan does not match this CLI consumer execution instance");
    }
    if (plan.contains("scenarios") || plan.contains("expected")) {
        throw RunnerError("CLI consumer run plan exposed semantic scenarios or expected observations");
    }
}

/// Builds one consumer receipt while copying only centrally prepared identity fields.
json build_receipt(const json& plan) {
    validate_plan(plan);
    json obligations = json::array();
    for (const auto& obligation : plan.at("obligations")) {
        obligations.push_back(obligation_receipt(plan, obligation));
    }
    return json{{"schemaVersion", plan.at("schemaVersion")},
                {"familyId", plan.at("familyId")},
                {"familyVersion", plan.at("familyVersion")},
                {"expectationDigest", plan.at("expectationDigest")},
                {"invocation", plan.at("invocation")},
                {"participant", plan.at("participant")},
                {"runner", json{{"id", RUNNER_ID}, {"version", 1}, {"platform", "windows"}, {"toolchain", TOOLCHAIN}}},
                {"obligations", std::move(obligations)}};
}

/// Reads one UTF-8 JSON document from a launcher-owned path.
json read_json(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw RunnerError("cannot open CLI consumer conformance run plan: " + path.string());
    }
    return json::parse(input, nullptr, true, true);
}

/// Publishes a fresh compact receipt with a same-directory atomic rename.
void publish_receipt(const fs::path& output_path, const json& receipt) {
    if (fs::exists(output_path)) {
        throw RunnerError("CLI consumer receipt destination already exists");
    }
    fs::create_directories(output_path.parent_path());
    const fs::path temporary = output_path.parent_path() / ("." + output_path.filename().string() + ".tmp");
    try {
        std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
        if (!output) {
            throw RunnerError("cannot create temporary CLI consumer receipt");
        }
        output << receipt.dump();
        output.flush();
        if (!output) {
            throw RunnerError("cannot flush temporary CLI consumer receipt");
        }
        output.close();
        fs::rename(temporary, output_path);
    } catch (...) {
        std::error_code error;
        fs::remove(temporary, error);
        throw;
    }
}

} // namespace

/// Reads launcher-only state, executes every CLI obligation, and emits one receipt.
int main() {
    try {
        const auto run_plan_value = read_environment(RUN_PLAN_ENV);
        const auto output_value = read_environment(OUTPUT_ENV);
        if (!run_plan_value.has_value() || run_plan_value->empty() || !output_value.has_value() ||
            output_value->empty()) {
            std::cout << "SKIP: " << RUN_PLAN_ENV << " and " << OUTPUT_ENV
                      << " are required for native CLI consumer conformance\n";
            return SKIP_RETURN_CODE;
        }
        const fs::path raw_run_plan(*run_plan_value);
        const fs::path raw_output(*output_value);
        if (!raw_run_plan.is_absolute() || !raw_output.is_absolute()) {
            throw RunnerError("run plan and receipt must be absolute sibling paths");
        }
        const fs::path run_plan = raw_run_plan.lexically_normal();
        const fs::path output = raw_output.lexically_normal();
        if (run_plan.parent_path() != output.parent_path()) {
            throw RunnerError("run plan and receipt must be absolute sibling paths");
        }
        publish_receipt(output, build_receipt(read_json(run_plan)));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << RUNNER_ID << ": " << error.what() << '\n';
        return 2;
    }
}
