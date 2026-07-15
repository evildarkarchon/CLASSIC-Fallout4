// SPDX-License-Identifier: MIT
//
// Native round-trip tests for the final Crash Log Scan Run CXX contract.
// Invoke through `classic-cli/build_cli.ps1 -Test`; the wrapper owns the
// vcpkg, MSVC, generated-header, and Rust bridge setup.

#include <catch2/catch_test_macros.hpp>

#include "classic_cxx_bridge/scanner.h"

#include <chrono>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <string>
#include <system_error>

namespace {

namespace fs = std::filesystem;
namespace scanner = classic::scanner;

/// Owns an isolated directory and removes it after a bridge test finishes.
class TemporaryDirectory final {
public:
    /// Creates a unique directory beneath the platform temporary directory.
    TemporaryDirectory() {
        const auto suffix =
            std::to_string(std::chrono::steady_clock::now().time_since_epoch().count());
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
    [[nodiscard]] const fs::path& path() const noexcept {
        return path_;
    }

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
    [[nodiscard]] scanner::ScanRunContractEventKind event_kind() const noexcept {
        return event_kind_;
    }

    /// Returns the number of serialized callback deliveries.
    [[nodiscard]] std::size_t event_count() const noexcept {
        return event_count_;
    }

    /// Returns whether the adapter simulated a downstream delivery failure.
    [[nodiscard]] bool delivery_failed() const noexcept {
        return delivery_failed_;
    }

private:
    const scanner::ScanRunCancellation& cancellation_;
    mutable scanner::ScanRunContractEventKind event_kind_ =
        scanner::ScanRunContractEventKind::DiscoveryCompleted;
    mutable std::size_t event_count_ = 0;
    mutable bool delivery_failed_ = false;
};

/// Builds the smallest valid shared configuration needed to reach discovery.
scanner::ScanRunConfigurationDto make_configuration(const fs::path& root) {
    scanner::ScanRunConfigurationDto configuration{};
    configuration.yaml_dir_root = root.string();
    configuration.yaml_dir_data = root.string();
    configuration.game = "Fallout4";
    configuration.game_version = "auto";
    return configuration;
}

} // namespace

TEST_CASE("Scan Run observer can cancel after adapter delivery failure", "[bridge][scan-run]") {
    TemporaryDirectory temporary;
    const fs::path crash_log = temporary.path() / "crash-2026-07-14-00-00-00.log";
    {
        std::ofstream output(crash_log, std::ios::binary);
        output << "targeted bridge test";
    }

    scanner::ScanRunTargetedSourceDto source{};
    source.inputs.push_back(crash_log.string());
    const auto request = scanner::scan_run_request_targeted(
        make_configuration(temporary.path()), source);
    const auto cancellation = scanner::scan_run_cancellation_new();
    const CancellingObserver observer(*cancellation);

    const auto execution =
        scanner::scan_run_contract_execute(*request, *cancellation, &observer);

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
