// SPDX-License-Identifier: MIT
//
// Catch2 bridge tests for the fallible timing-sample contract of
// `classic::perf::perf_record_timing`.
//
// The JSON conformance fixtures cannot represent NaN or infinity, so these
// direct C++ tests are the CXX counterpart of the Python
// (`python-bindings/tests/test_timing_contract.py`) and Node
// (`node-bindings/classic-node/__test__/shared.spec.ts`) invalid-timing tests:
// every rejected sample throws `rust::Error` whose message begins with the
// stable error token, and no rejection changes the metrics store. The
// Rust-side unit tests in `cpp-bindings/classic-cpp-bridge/src/perf_tests.rs`
// pin the same mapping without crossing the FFI boundary.
//
// The metrics store is process-global, so each test clears it on entry and
// exit. Invoke via `classic-cli/build_cli.ps1 -Test` rather than raw ctest.

#include <catch2/catch_test_macros.hpp>

// The generated bridge header declares only the cxx runtime pieces it uses;
// `rust::Error` (what a fallible bridge call throws) comes from the full header.
#include "rust/cxx.h"
#include "classic_cxx_bridge/perf.h"

#include <limits>
#include <string>
#include <utility>
#include <vector>

namespace {

/// Copy the bridge's rendered metrics summary so two snapshots can be compared.
std::vector<std::string> summary_snapshot() {
    std::vector<std::string> lines;
    for (const auto& line : classic::perf::perf_get_summary()) {
        lines.emplace_back(line);
    }
    return lines;
}

/// Record `seconds` for `operation` and return the thrown bridge message,
/// failing the test if the sample was accepted.
std::string rejected_message(const std::string& operation, double seconds) {
    try {
        classic::perf::perf_record_timing(operation, seconds);
    } catch (const rust::Error& error) {
        return error.what();
    }
    FAIL("perf_record_timing accepted an invalid sample for " << operation);
    return {};
}

/// Clears the process-global metrics store on construction and destruction.
struct ClearedMetrics {
    ClearedMetrics() { classic::perf::perf_clear_metrics(); }
    ~ClearedMetrics() { classic::perf::perf_clear_metrics(); }
    ClearedMetrics(const ClearedMetrics&) = delete;
    ClearedMetrics& operator=(const ClearedMetrics&) = delete;
};

} // namespace

TEST_CASE("perf_record_timing rejects invalid samples without mutation", "[perf][bridge]") {
    ClearedMetrics cleared;
    classic::perf::perf_record_timing("cxx_cli_kept", 0.25);
    const auto before = summary_snapshot();

    const std::vector<std::pair<double, std::string>> cases = {
        {std::numeric_limits<double>::quiet_NaN(), "timing_sample_not_finite: "},
        {std::numeric_limits<double>::infinity(), "timing_sample_not_finite: "},
        {-std::numeric_limits<double>::infinity(), "timing_sample_not_finite: "},
        {-0.5, "timing_sample_negative: "},
        {1e300, "timing_sample_out_of_range: "},
    };
    for (const auto& [seconds, token] : cases) {
        INFO("sample " << seconds);
        // An existing operation and one that was never recorded both reject.
        for (const std::string operation : {"cxx_cli_kept", "cxx_cli_never_created"}) {
            const auto message = rejected_message(operation, seconds);
            INFO("message: " << message);
            CHECK(message.rfind(token, 0) == 0);
        }
    }

    CHECK(summary_snapshot() == before);
    CHECK(classic::perf::perf_get_operation_count("cxx_cli_kept") == 1);
    CHECK(classic::perf::perf_get_operation_count("cxx_cli_never_created") == 0);
}

TEST_CASE("perf_record_timing treats negative zero as zero", "[perf][bridge]") {
    ClearedMetrics cleared;

    classic::perf::perf_record_timing("cxx_cli_zero", -0.0);

    CHECK(classic::perf::perf_get_operation_count("cxx_cli_zero") == 1);
    CHECK(classic::perf::perf_get_operation_average("cxx_cli_zero") == 0.0);
}
