// SPDX-License-Identifier: MIT
//
// Native round-trip tests for the final Crash Log Scan Run CXX contract.
// Invoke through `classic-cli/build_cli.ps1 -Test`; the wrapper owns the
// vcpkg, MSVC, generated-header, and Rust bridge setup.

#include <catch2/catch_test_macros.hpp>

#include "classic_cxx_bridge/scanner.h"
#include "scan_run_fixture_config.h"

#include <array>
#include <chrono>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <vector>

namespace {

namespace fs = std::filesystem;
namespace scanner = classic::scanner;
namespace fixture = classic::scan_run_fixture;

/// Executes an opaque bridge operation and moves out its typed terminal envelope.
scanner::ScanRunContractExecutionResult execute_result(
    const scanner::ScanRunRequest& request, const scanner::ScanRunCancellation& cancellation,
    const scanner::ScanRunObserver* observer) {
    auto operation = scanner::scan_run_contract_execute(request, cancellation, observer);
    return scanner::scan_run_contract_execution_take_result(*operation);
}

const fs::path SHARED_FIXTURE_ROOT = fs::path(CLASSIC_REPO_ROOT) / "tests" / "fixtures" / "crash_log_scan_run";

/// Owns an isolated directory and removes it after a bridge test finishes.
class TemporaryDirectory final {
public:
    /// Creates a unique directory beneath the platform temporary directory.
    TemporaryDirectory() {
        const auto suffix = std::to_string(std::chrono::steady_clock::now().time_since_epoch().count());
        path_ = fs::temp_directory_path() / ("classic-scan-run-contract-" + suffix);
        fs::create_directories(path_);
    }

    /// Removes all test artifacts without allowing cleanup errors to escape.
    ~TemporaryDirectory() {
        std::error_code error;
        fs::remove_all(path_, error);
    }

    TemporaryDirectory(const TemporaryDirectory&) = delete;
    TemporaryDirectory& operator=(const TemporaryDirectory&) = delete;

    /// Returns the directory retained for this test's lifetime.
    [[nodiscard]] const fs::path& path() const noexcept { return path_; }

private:
    fs::path path_;
};

/// Models an adapter delivery failure by retaining the event and requesting
/// cancellation through the separate monotonic control.
class CancellingObserver final : public scanner::ScanRunObserver {
public:
    /// Borrows the cancellation control that remains live for bridge execution.
    explicit CancellingObserver(const scanner::ScanRunCancellation& cancellation) noexcept
        : cancellation_(cancellation) {}

    /// Records serialized delivery and translates the simulated adapter failure
    /// into cooperative cancellation without throwing across CXX.
    void on_scan_run_event(const scanner::ScanRunContractEvent& event) const noexcept override {
        event_kind_ = event.kind;
        event_count_ += 1;
        delivery_failed_ = true;
        scanner::scan_run_cancellation_cancel(cancellation_);
    }

    /// Returns the only event kind expected before observer-requested cancellation.
    [[nodiscard]] scanner::ScanRunContractEventKind event_kind() const noexcept { return event_kind_; }

    /// Returns the number of serialized callback deliveries.
    [[nodiscard]] std::size_t event_count() const noexcept { return event_count_; }

    /// Returns whether the adapter simulated a downstream delivery failure.
    [[nodiscard]] bool delivery_failed() const noexcept { return delivery_failed_; }

private:
    const scanner::ScanRunCancellation& cancellation_;
    mutable scanner::ScanRunContractEventKind event_kind_ = scanner::ScanRunContractEventKind::DiscoveryCompleted;
    mutable std::size_t event_count_ = 0;
    mutable bool delivery_failed_ = false;
};

/// Builds the smallest valid shared configuration needed to reach discovery.
scanner::ScanRunConfigurationDto make_configuration(const fs::path& root) {
    scanner::ScanRunConfigurationDto configuration{};
    configuration.installation_root = root.string();
    configuration.game = scanner::ScanRunGameId::Fallout4;
    configuration.game_version = "auto";
    return configuration;
}

/// Copies the immutable shared YAML corpus into one isolated execution root.
void copy_shared_yaml_tree(const fs::path& root) {
    const auto database = root / "CLASSIC Data" / "databases";
    fs::create_directories(database);
    fs::copy_file(SHARED_FIXTURE_ROOT / "CLASSIC Data" / "CLASSIC Ignore.yaml",
                  root / "CLASSIC Data" / "CLASSIC Ignore.yaml");
    fs::copy_file(SHARED_FIXTURE_ROOT / "CLASSIC Data" / "databases" / "CLASSIC Main.yaml",
                  database / "CLASSIC Main.yaml");
    fs::copy_file(SHARED_FIXTURE_ROOT / "CLASSIC Data" / "databases" / "CLASSIC Fallout4.yaml",
                  database / "CLASSIC Fallout4.yaml");
}

/// Materializes one named Crash Log from the shared valid-log template.
fs::path copy_shared_log(const fs::path& root, const fs::path& relative) {
    const auto destination = root / relative;
    fs::create_directories(destination.parent_path());
    fs::copy_file(SHARED_FIXTURE_ROOT / "valid-crash.log", destination);
    return destination;
}

/// Reads one generated report or retained YAML file as exact binary bytes.
std::string read_file_bytes(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("cannot read fixture output: " + path.string());
    }
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

/// Converts a generated CXX string into the native filesystem representation.
fs::path native_path(const rust::String& value) {
    return fs::path(std::string(value));
}

/// Returns one manifest-relative, slash-normalized path from a generated CXX string.
std::string relative_path(const fs::path& root, const rust::String& value) {
    return fs::relative(native_path(value), root).generic_string();
}

/// Converts a typed discovery source to the stable manifest identifier.
std::string_view source_name(scanner::ScanRunContractDiscoverySource source) {
    switch (source) {
    case scanner::ScanRunContractDiscoverySource::Standard:
        return "standard";
    case scanner::ScanRunContractDiscoverySource::Targeted:
        return "targeted";
    }
    return "unknown";
}

/// Converts a typed log disposition to the stable manifest identifier.
std::string_view disposition_name(scanner::ScanRunContractLogDisposition disposition) {
    switch (disposition) {
    case scanner::ScanRunContractLogDisposition::Succeeded:
        return "succeeded";
    case scanner::ScanRunContractLogDisposition::Failed:
        return "failed";
    case scanner::ScanRunContractLogDisposition::CancelledBeforeStart:
        return "cancelled_before_start";
    }
    return "unknown";
}

/// Records serialized public CXX events without controlling core execution.
class RecordingObserver final : public scanner::ScanRunObserver {
public:
    /// Retains the stable event kind in callback order.
    void on_scan_run_event(const scanner::ScanRunContractEvent& event) const noexcept override {
        if (count_ < kinds_.size()) {
            kinds_[count_++] = event.kind;
        }
    }

    /// Returns the stable set of event variants observed by this adapter.
    [[nodiscard]] std::set<scanner::ScanRunContractEventKind> kinds() const {
        return {kinds_.begin(), kinds_.begin() + static_cast<std::ptrdiff_t>(count_)};
    }

    /// Returns how many callbacks were retained without allocating in the observer.
    [[nodiscard]] std::size_t count() const noexcept { return count_; }

private:
    mutable std::array<scanner::ScanRunContractEventKind, 64> kinds_{};
    mutable std::size_t count_ = 0;
};

/// Retains cancellation-boundary facts and cancels at one selected public event.
class BoundaryCancellingObserver final : public scanner::ScanRunObserver {
public:
    /// Selects an event kind and, optionally, one discovery index as the safe seam.
    BoundaryCancellingObserver(const scanner::ScanRunCancellation& cancellation,
                               scanner::ScanRunContractEventKind trigger, bool has_trigger_index = false,
                               std::size_t trigger_index = 0) noexcept
        : cancellation_(cancellation)
        , trigger_(trigger)
        , has_trigger_index_(has_trigger_index)
        , trigger_index_(trigger_index) {}

    /// Records only trivial event facts before requesting monotonic cancellation.
    void on_scan_run_event(const scanner::ScanRunContractEvent& event) const noexcept override {
        if (count_ < events_.size()) {
            events_[count_++] = EventSnapshot{event.kind, event.discovery_index, event.disposition};
        }
        if (!triggered_ && event.kind == trigger_ && (!has_trigger_index_ || event.discovery_index == trigger_index_)) {
            triggered_ = true;
            scanner::scan_run_cancellation_cancel(cancellation_);
        }
    }

    /// Returns whether the configured cancellation boundary was observed.
    [[nodiscard]] bool triggered() const noexcept { return triggered_; }

    /// Counts retained callbacks of one stable event kind.
    [[nodiscard]] std::size_t count(scanner::ScanRunContractEventKind kind) const noexcept {
        std::size_t matches = 0;
        for (std::size_t index = 0; index < count_; ++index) {
            matches += events_[index].kind == kind ? 1U : 0U;
        }
        return matches;
    }

    /// Returns discovery indices retained for one stable event kind.
    [[nodiscard]] std::vector<std::size_t> discovery_indices(scanner::ScanRunContractEventKind kind) const {
        std::vector<std::size_t> indices;
        for (std::size_t index = 0; index < count_; ++index) {
            if (events_[index].kind == kind) {
                indices.push_back(events_[index].discovery_index);
            }
        }
        return indices;
    }

    /// Returns terminal dispositions retained for one stable event kind.
    [[nodiscard]] std::vector<scanner::ScanRunContractLogDisposition>
    dispositions(scanner::ScanRunContractEventKind kind) const {
        std::vector<scanner::ScanRunContractLogDisposition> dispositions;
        for (std::size_t index = 0; index < count_; ++index) {
            if (events_[index].kind == kind) {
                dispositions.push_back(events_[index].disposition);
            }
        }
        return dispositions;
    }

private:
    struct EventSnapshot {
        scanner::ScanRunContractEventKind kind{};
        std::size_t discovery_index = 0;
        scanner::ScanRunContractLogDisposition disposition{};
    };

    const scanner::ScanRunCancellation& cancellation_;
    scanner::ScanRunContractEventKind trigger_;
    bool has_trigger_index_;
    std::size_t trigger_index_;
    mutable std::array<EventSnapshot, 64> events_{};
    mutable std::size_t count_ = 0;
    mutable bool triggered_ = false;
};

} // namespace

TEST_CASE("CXX executes the shared Standard fixture with Rust-owned facts", "[bridge][scan-run][parity]") {
    // shared Standard fixture
    TemporaryDirectory temporary;
    copy_shared_yaml_tree(temporary.path());
    for (const auto log : fixture::STANDARD_LOGS) {
        copy_shared_log(temporary.path(), log);
    }
    fs::create_directories(temporary.path() / "Documents");

    auto configuration = make_configuration(temporary.path());
    configuration.has_max_concurrent = true;
    configuration.max_concurrent = fixture::STANDARD_MAX_CONCURRENT;
    scanner::ScanRunStandardSourceDto source{};
    source.base_directory = temporary.path().string();
    source.has_configured_documents_root = true;
    source.configured_documents_root = (temporary.path() / "Documents").string();
    const auto request =
        scanner::scan_run_request_standard(configuration, source, *scanner::scan_run_unsolved_logs_leave_in_place());
    const auto cancellation = scanner::scan_run_cancellation_new();
    const RecordingObserver observer;

    const auto execution = execute_result(*request, *cancellation, &observer);

    INFO("scan-run error: " << std::string(execution.error.message));
    REQUIRE(execution.has_result);
    REQUIRE_FALSE(execution.has_error);
    REQUIRE(execution.result.status == scanner::ScanRunContractStatus::Completed);
    REQUIRE(execution.result.has_installed_yaml_data);
    REQUIRE(execution.result.installed_yaml_data.main.role == scanner::ScanRunInstalledYamlDataRole::Main);
    REQUIRE(execution.result.installed_yaml_data.game_file.role == scanner::ScanRunInstalledYamlDataRole::Game);
    REQUIRE(execution.result.installed_yaml_data.local_ignore_state ==
            scanner::ScanRunLocalIgnoreYamlDataState::Existing);
    REQUIRE(source_name(execution.result.discovery.source) == fixture::STANDARD_SOURCE);
    REQUIRE(execution.result.discovery.accepted_logs.size() == fixture::STANDARD_LOGS.size());
    for (std::size_t index = 0; index < fixture::STANDARD_LOGS.size(); ++index) {
        REQUIRE(relative_path(temporary.path(), execution.result.discovery.accepted_logs[index]) ==
                fixture::STANDARD_LOGS[index]);
    }
    REQUIRE(execution.result.has_effective_concurrency);
    REQUIRE(execution.result.effective_concurrency == fixture::STANDARD_EFFECTIVE_CONCURRENCY);
    REQUIRE(execution.result.logs.size() == fixture::STANDARD_LOGS.size());
    for (std::size_t index = 0; index < execution.result.logs.size(); ++index) {
        const auto& log = execution.result.logs[index];
        REQUIRE(relative_path(temporary.path(), log.crash_log) == fixture::STANDARD_LOGS[index]);
        REQUIRE(log.discovery_index == fixture::STANDARD_DISCOVERY_ORDER[index]);
        REQUIRE(disposition_name(log.disposition) == fixture::STANDARD_DISPOSITIONS[index]);
        REQUIRE(log.has_autoscan_report);
        const auto report = native_path(log.autoscan_report);
        REQUIRE(report.generic_string().ends_with(fixture::STANDARD_ARTIFACT_SUFFIX));
        REQUIRE(fs::is_regular_file(report));
    }
    const std::set expected_event_kinds{
        scanner::ScanRunContractEventKind::DiscoveryCompleted,
        scanner::ScanRunContractEventKind::EffectiveConcurrencySelected,
        scanner::ScanRunContractEventKind::LogQueued,
        scanner::ScanRunContractEventKind::LogStarted,
        scanner::ScanRunContractEventKind::LogPhase,
        scanner::ScanRunContractEventKind::LogFinished,
    };
    REQUIRE(observer.kinds() == expected_event_kinds);
}

TEST_CASE("CXX executes the shared Targeted fixture without Unsolved Logs movement", "[bridge][scan-run][parity]") {
    // shared Targeted fixture
    TemporaryDirectory temporary;
    copy_shared_yaml_tree(temporary.path());
    for (const auto accepted : fixture::TARGETED_ACCEPTED) {
        copy_shared_log(temporary.path(), accepted);
    }

    auto configuration = make_configuration(temporary.path());
    configuration.has_max_concurrent = true;
    configuration.max_concurrent = fixture::TARGETED_MAX_CONCURRENT;
    scanner::ScanRunTargetedSourceDto source{};
    for (const auto input : fixture::TARGETED_INPUTS) {
        source.inputs.push_back((temporary.path() / input).string());
    }
    const auto request = scanner::scan_run_request_targeted(configuration, source);

    const auto execution = execute_result(*request, *scanner::scan_run_cancellation_new(), nullptr);

    INFO("scan-run error: " << std::string(execution.error.message));
    REQUIRE(execution.has_result);
    REQUIRE_FALSE(execution.has_error);
    REQUIRE(source_name(execution.result.discovery.source) == fixture::TARGETED_SOURCE);
    REQUIRE(execution.result.discovery.accepted_logs.size() == fixture::TARGETED_ACCEPTED.size());
    for (std::size_t index = 0; index < fixture::TARGETED_ACCEPTED.size(); ++index) {
        REQUIRE(relative_path(temporary.path(), execution.result.discovery.accepted_logs[index]) ==
                fixture::TARGETED_ACCEPTED[index]);
    }
    REQUIRE(execution.result.discovery.rejected_inputs.size() == fixture::TARGETED_REJECTED.size());
    REQUIRE(relative_path(temporary.path(), execution.result.discovery.rejected_inputs[0].path) ==
            fixture::TARGETED_REJECTED[0]);
    REQUIRE(execution.result.effective_concurrency == fixture::TARGETED_EFFECTIVE_CONCURRENCY);
    REQUIRE(execution.result.logs.size() == fixture::TARGETED_ACCEPTED.size());
    for (std::size_t index = 0; index < execution.result.logs.size(); ++index) {
        const auto& log = execution.result.logs[index];
        REQUIRE(relative_path(temporary.path(), log.crash_log) == fixture::TARGETED_ACCEPTED[index]);
        REQUIRE(log.discovery_index == fixture::TARGETED_DISCOVERY_ORDER[index]);
        REQUIRE(disposition_name(log.disposition) == fixture::TARGETED_DISPOSITIONS[index]);
        REQUIRE(log.has_autoscan_report);
        const auto report = native_path(log.autoscan_report);
        REQUIRE(report.generic_string().ends_with(fixture::TARGETED_ARTIFACT_SUFFIX));
        REQUIRE(fs::is_regular_file(report));
        REQUIRE_FALSE(log.moved_to_unsolved_logs);
    }
    REQUIRE(fixture::TARGETED_UNSOLVED_ARTIFACT_COUNT == 0);
    REQUIRE_FALSE(fs::exists(temporary.path() / "Unsolved Logs"));
}

TEST_CASE("CXX final result preserves generated Local Ignore metadata and diagnostics", "[bridge][scan-run][parity]") {
    TemporaryDirectory temporary;
    copy_shared_yaml_tree(temporary.path());
    fs::remove(temporary.path() / "CLASSIC Data" / "CLASSIC Ignore.yaml");
    const auto crash_log = copy_shared_log(temporary.path(), "crash-generated-ignore.log");
    scanner::ScanRunTargetedSourceDto source{};
    source.inputs.push_back(crash_log.string());
    const auto request = scanner::scan_run_request_targeted(make_configuration(temporary.path()), source);

    const auto execution = execute_result(*request, *scanner::scan_run_cancellation_new(), nullptr);

    INFO("scan-run error: " << std::string(execution.error.message));
    REQUIRE(execution.has_result);
    REQUIRE_FALSE(execution.has_error);
    REQUIRE(execution.result.has_installed_yaml_data);
    REQUIRE(execution.result.installed_yaml_data.local_ignore_state ==
            scanner::ScanRunLocalIgnoreYamlDataState::Generated);
    REQUIRE(execution.result.installed_yaml_data.local_ignore_identity.byte_len > 0);
    bool saw_generation = false;
    for (const auto& diagnostic : execution.result.installed_yaml_data.diagnostics) {
        saw_generation = saw_generation ||
                         diagnostic.kind == scanner::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated;
    }
    REQUIRE(saw_generation);
}

TEST_CASE("CXX shared Local Ignore recovery retains snapshots and rejects replay", "[bridge][scan-run][parity]") {
    TemporaryDirectory temporary;
    copy_shared_yaml_tree(temporary.path());
    const auto crash_log = copy_shared_log(temporary.path(), fixture::INSTALLED_YAML_INPUT);
    scanner::ScanRunTargetedSourceDto source{};
    source.inputs.push_back(crash_log.string());
    const auto request = scanner::scan_run_request_targeted(make_configuration(temporary.path()), source);

    const auto baseline = execute_result(*request, *scanner::scan_run_cancellation_new(), nullptr);
    REQUIRE(baseline.has_result);
    REQUIRE(baseline.result.status == scanner::ScanRunContractStatus::Completed);
    const auto baseline_report = read_file_bytes(native_path(baseline.result.logs[0].autoscan_report));
    const auto ignore_path = temporary.path() / "CLASSIC Data" / "CLASSIC Ignore.yaml";
    {
        std::ofstream malformed(ignore_path, std::ios::binary | std::ios::trunc);
        malformed << fixture::MALFORMED_LOCAL_IGNORE;
    }

    auto initial_operation = scanner::scan_run_contract_execute(
        *request, *scanner::scan_run_cancellation_new(), nullptr);
    REQUIRE(scanner::scan_run_contract_execution_has_continuation(*initial_operation));
    const auto initial = scanner::scan_run_contract_execution_take_result(*initial_operation);
    REQUIRE(initial.has_result);
    REQUIRE(initial.result.status == scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired);
    REQUIRE(initial.result.installed_yaml_data.local_ignore_state ==
            scanner::ScanRunLocalIgnoreYamlDataState::RecoveryRequired);
    REQUIRE(initial.result.discovery.accepted_logs.size() == 1);
    const auto retained_log = std::string(initial.result.discovery.accepted_logs[0]);
    const auto retained_main_sha = std::string(initial.result.installed_yaml_data.main.sha256);
    const auto retained_game_sha = std::string(initial.result.installed_yaml_data.game_file.sha256);
    auto continuation = scanner::scan_run_contract_execution_take_continuation(*initial_operation);

    {
        std::ofstream changed(temporary.path() / "CLASSIC Data" / "databases" / "CLASSIC Main.yaml",
                              std::ios::binary | std::ios::trunc);
        changed << "invalid: [unterminated";
    }
    const RecordingObserver observer;
    auto resumed_operation = scanner::scan_run_continuation_resume(
        *continuation, scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
        *scanner::scan_run_cancellation_new(), &observer);
    const auto resumed = scanner::scan_run_contract_execution_take_result(*resumed_operation);

    REQUIRE(resumed.has_result);
    REQUIRE(resumed.result.status == scanner::ScanRunContractStatus::Completed);
    REQUIRE(std::string(resumed.result.discovery.accepted_logs[0]) == retained_log);
    REQUIRE(std::string(resumed.result.installed_yaml_data.main.sha256) == retained_main_sha);
    REQUIRE(std::string(resumed.result.installed_yaml_data.game_file.sha256) == retained_game_sha);
    REQUIRE(resumed.result.installed_yaml_data.local_ignore_state ==
            scanner::ScanRunLocalIgnoreYamlDataState::ProceedWithoutIgnore);
    REQUIRE_FALSE(observer.kinds().contains(scanner::ScanRunContractEventKind::DiscoveryCompleted));
    REQUIRE(read_file_bytes(native_path(resumed.result.logs[0].autoscan_report)) == baseline_report);
    REQUIRE(read_file_bytes(ignore_path) == fixture::MALFORMED_LOCAL_IGNORE);

    auto replay_operation = scanner::scan_run_continuation_resume(
        *continuation, scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
        *scanner::scan_run_cancellation_new(), nullptr);
    const auto replay = scanner::scan_run_contract_execution_take_result(*replay_operation);
    REQUIRE_FALSE(replay.has_result);
    REQUIRE_FALSE(replay.has_error);
    REQUIRE(replay.has_resume_error);
    REQUIRE(replay.resume_error.kind == scanner::ScanRunContractResumeErrorKind::ContinuationConsumed);
    REQUIRE(std::string(replay.resume_error.code) == "scan_run_continuation_consumed");
}

TEST_CASE("CXX shared cancellation fixture distinguishes every safe seam", "[bridge][scan-run][parity]") {
    // All sections use the same two manifest-owned Targeted logs so only the
    // cancellation boundary changes between executions.
    TemporaryDirectory temporary;
    copy_shared_yaml_tree(temporary.path());
    for (const auto accepted : fixture::TARGETED_ACCEPTED) {
        copy_shared_log(temporary.path(), accepted);
    }

    auto make_request = [&temporary]() {
        auto configuration = make_configuration(temporary.path());
        configuration.has_max_concurrent = true;
        configuration.max_concurrent = 1;
        scanner::ScanRunTargetedSourceDto source{};
        for (const auto accepted : fixture::TARGETED_ACCEPTED) {
            source.inputs.push_back((temporary.path() / accepted).string());
        }
        return scanner::scan_run_request_targeted(configuration, source);
    };

    SECTION("pre-discovery cancellation has no retained discovery or work") {
        const auto cancellation = scanner::scan_run_cancellation_new();
        scanner::scan_run_cancellation_cancel(*cancellation);
        const RecordingObserver observer;

        const auto execution = execute_result(*make_request(), *cancellation, &observer);

        REQUIRE(execution.has_result);
        REQUIRE(execution.result.status == scanner::ScanRunContractStatus::CancelledBeforeDiscovery);
        REQUIRE_FALSE(execution.result.has_discovery);
        REQUIRE_FALSE(execution.result.has_effective_concurrency);
        REQUIRE(execution.result.logs.empty());
        REQUIRE(observer.count() == 0);
    }

    SECTION("post-discovery queued cancellation never admits work") {
        const auto cancellation = scanner::scan_run_cancellation_new();
        const BoundaryCancellingObserver observer(*cancellation, scanner::ScanRunContractEventKind::LogQueued);

        const auto execution = execute_result(*make_request(), *cancellation, &observer);

        REQUIRE(observer.triggered());
        REQUIRE(execution.result.status == scanner::ScanRunContractStatus::Cancelled);
        REQUIRE(execution.result.has_discovery);
        REQUIRE(execution.result.succeeded == 0);
        REQUIRE(execution.result.cancelled == fixture::TARGETED_ACCEPTED.size());
        REQUIRE(observer.count(scanner::ScanRunContractEventKind::LogStarted) == 0);
        REQUIRE(observer.count(scanner::ScanRunContractEventKind::LogFinished) == fixture::TARGETED_ACCEPTED.size());
        REQUIRE(observer.dispositions(scanner::ScanRunContractEventKind::LogFinished) ==
                std::vector{scanner::ScanRunContractLogDisposition::CancelledBeforeStart,
                            scanner::ScanRunContractLogDisposition::CancelledBeforeStart});
        for (const auto& log : execution.result.logs) {
            REQUIRE(log.disposition == scanner::ScanRunContractLogDisposition::CancelledBeforeStart);
            REQUIRE_FALSE(log.has_autoscan_report);
        }
    }

    SECTION("admitted work crosses its durable boundary before cancellation") {
        const auto cancellation = scanner::scan_run_cancellation_new();
        const BoundaryCancellingObserver observer(*cancellation, scanner::ScanRunContractEventKind::LogStarted, true,
                                                  0);

        const auto execution = execute_result(*make_request(), *cancellation, &observer);

        REQUIRE(observer.triggered());
        REQUIRE(execution.result.status == scanner::ScanRunContractStatus::Cancelled);
        REQUIRE(execution.result.succeeded == 1);
        REQUIRE(execution.result.cancelled == 1);
        REQUIRE(observer.discovery_indices(scanner::ScanRunContractEventKind::LogStarted) ==
                std::vector<std::size_t>{0});
        REQUIRE(execution.result.logs[0].disposition == scanner::ScanRunContractLogDisposition::Succeeded);
        REQUIRE(execution.result.logs[0].has_autoscan_report);
        REQUIRE(fs::is_regular_file(native_path(execution.result.logs[0].autoscan_report)));
        REQUIRE(execution.result.logs[1].disposition == scanner::ScanRunContractLogDisposition::CancelledBeforeStart);
        REQUIRE_FALSE(execution.result.logs[1].has_autoscan_report);
        REQUIRE(observer.discovery_indices(scanner::ScanRunContractEventKind::LogFinished) ==
                std::vector<std::size_t>{0, 1});
        REQUIRE(observer.dispositions(scanner::ScanRunContractEventKind::LogFinished) ==
                std::vector{scanner::ScanRunContractLogDisposition::Succeeded,
                            scanner::ScanRunContractLogDisposition::CancelledBeforeStart});
    }
}

TEST_CASE("Scan Run observer can cancel after adapter delivery failure", "[bridge][scan-run]") {
    TemporaryDirectory temporary;
    const fs::path crash_log = temporary.path() / "crash-2026-07-14-00-00-00.log";
    {
        std::ofstream output(crash_log, std::ios::binary);
        output << "targeted bridge test";
    }

    scanner::ScanRunTargetedSourceDto source{};
    source.inputs.push_back(crash_log.string());
    const auto request = scanner::scan_run_request_targeted(make_configuration(temporary.path()), source);
    const auto cancellation = scanner::scan_run_cancellation_new();
    const CancellingObserver observer(*cancellation);

    const auto execution = execute_result(*request, *cancellation, &observer);

    REQUIRE(observer.delivery_failed());
    REQUIRE(observer.event_count() == 1);
    REQUIRE(observer.event_kind() == scanner::ScanRunContractEventKind::DiscoveryCompleted);
    REQUIRE(scanner::scan_run_cancellation_is_cancelled(*cancellation));
    REQUIRE(execution.has_result);
    REQUIRE_FALSE(execution.has_error);
    REQUIRE(execution.result.status == scanner::ScanRunContractStatus::Cancelled);
    REQUIRE(execution.result.has_discovery);
    REQUIRE(execution.result.discovery.accepted_logs.size() == 1);
}
