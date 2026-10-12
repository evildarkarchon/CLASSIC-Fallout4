// SPDX-License-Identifier: MIT
//
// Bridge-only semantic conformance participant. This executable is
// hosted by the CLI build but does not link or compile any frontend source.

#include "classic_cxx_bridge/config.h"
#include "classic_cxx_bridge/files.h"
#include "classic_cxx_bridge/path.h"
#include "classic_cxx_bridge/database.h"
#include "classic_cxx_bridge/version_registry.h"
#include "classic_cxx_bridge/game.h"
#include "classic_cxx_bridge/scangame.h"
#include "classic_cxx_bridge/scanner.h"
#include "classic_cxx_bridge/settings.h"
#include "classic_cxx_bridge/xse.h"
#include "classic_cxx_bridge/perf.h"
#include "classic_cxx_bridge/update.h"
#include "classic_cxx_bridge/shared.h"

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <io.h>
#include <cstdio>

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <atomic>
#include <charconv>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <initializer_list>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <iterator>
#include <map>
#include <mutex>
#include <optional>
#include <regex>
#include <set>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <thread>
#include <utility>
#include <vector>

namespace {

namespace fs = std::filesystem;
namespace scanner = classic::scanner;
using json = nlohmann::json;

constexpr int SKIP_RETURN_CODE = 125;
constexpr std::string_view RUN_PLAN_ENV = "CLASSIC_CONFORMANCE_RUN_PLAN";
constexpr std::string_view OUTPUT_ENV = "CLASSIC_CONFORMANCE_OUTPUT";
constexpr std::string_view RUNNER_ID = "classic-cxx-conformance";
constexpr std::string_view TOOLCHAIN = CLASSIC_CXX_CONFORMANCE_TOOLCHAIN;

/// Computes SHA-256 locally so durable receipt evidence never depends on an adapter utility.
class Sha256 final {
public:
    /// Hashes exact file bytes and returns the lowercase hexadecimal digest used by Rust.
    [[nodiscard]] static std::string digest(std::span<const std::uint8_t> bytes) {
        Sha256 hash;
        hash.update(bytes);
        return hash.finish();
    }

private:
    static constexpr std::array<std::uint32_t, 64> ROUND_CONSTANTS{
        0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U, 0x3956c25bU, 0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U,
        0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U, 0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U, 0xc19bf174U,
        0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU, 0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU,
        0x983e5152U, 0xa831c66dU, 0xb00327c8U, 0xbf597fc7U, 0xc6e00bf3U, 0xd5a79147U, 0x06ca6351U, 0x14292967U,
        0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU, 0x53380d13U, 0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
        0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U, 0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U,
        0x19a4c116U, 0x1e376c08U, 0x2748774cU, 0x34b0bcb5U, 0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U,
        0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U, 0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U};

    static constexpr std::array<std::uint32_t, 8> INITIAL_STATE{0x6a09e667U, 0xbb67ae85U, 0x3c6ef372U, 0xa54ff53aU,
                                                                0x510e527fU, 0x9b05688cU, 0x1f83d9abU, 0x5be0cd19U};

    static constexpr std::uint32_t rotate_right(std::uint32_t value, unsigned count) noexcept {
        return (value >> count) | (value << (32U - count));
    }

    /// Absorbs bytes into the digest state, compressing each complete 64-byte block.
    void update(std::span<const std::uint8_t> bytes) {
        byte_count_ += bytes.size();
        for (const std::uint8_t byte : bytes) {
            buffer_[buffer_size_++] = byte;
            if (buffer_size_ == buffer_.size()) {
                transform(buffer_);
                buffer_size_ = 0;
            }
        }
    }

    /// Applies one SHA-256 compression round sequence to a complete message block.
    void transform(const std::array<std::uint8_t, 64>& block) {
        std::array<std::uint32_t, 64> words{};
        for (std::size_t index = 0; index < 16; ++index) {
            const std::size_t offset = index * 4;
            words[index] = (static_cast<std::uint32_t>(block[offset]) << 24U) |
                           (static_cast<std::uint32_t>(block[offset + 1]) << 16U) |
                           (static_cast<std::uint32_t>(block[offset + 2]) << 8U) |
                           static_cast<std::uint32_t>(block[offset + 3]);
        }
        for (std::size_t index = 16; index < words.size(); ++index) {
            const std::uint32_t small_zero =
                rotate_right(words[index - 15], 7U) ^ rotate_right(words[index - 15], 18U) ^ (words[index - 15] >> 3U);
            const std::uint32_t small_one =
                rotate_right(words[index - 2], 17U) ^ rotate_right(words[index - 2], 19U) ^ (words[index - 2] >> 10U);
            words[index] = words[index - 16] + small_zero + words[index - 7] + small_one;
        }

        auto working = state_;
        for (std::size_t index = 0; index < words.size(); ++index) {
            const std::uint32_t big_one =
                rotate_right(working[4], 6U) ^ rotate_right(working[4], 11U) ^ rotate_right(working[4], 25U);
            const std::uint32_t choice = (working[4] & working[5]) ^ (~working[4] & working[6]);
            const std::uint32_t round_t1 = working[7] + big_one + choice + ROUND_CONSTANTS[index] + words[index];
            const std::uint32_t big_zero =
                rotate_right(working[0], 2U) ^ rotate_right(working[0], 13U) ^ rotate_right(working[0], 22U);
            const std::uint32_t majority =
                (working[0] & working[1]) ^ (working[0] & working[2]) ^ (working[1] & working[2]);
            const std::uint32_t round_t2 = big_zero + majority;
            for (std::size_t position = working.size() - 1; position > 0; --position) {
                working[position] = working[position - 1];
            }
            working[4] += round_t1;
            working[0] = round_t1 + round_t2;
        }
        for (std::size_t index = 0; index < state_.size(); ++index) {
            state_[index] += working[index];
        }
    }

    /// Finalizes the padded message and returns its lowercase hexadecimal digest.
    [[nodiscard]] std::string finish() {
        const std::uint64_t bit_count = byte_count_ * 8U;
        buffer_[buffer_size_++] = 0x80U;
        if (buffer_size_ > 56) {
            while (buffer_size_ < buffer_.size()) {
                buffer_[buffer_size_++] = 0;
            }
            transform(buffer_);
            buffer_size_ = 0;
        }
        while (buffer_size_ < 56) {
            buffer_[buffer_size_++] = 0;
        }
        for (unsigned index = 0; index < 8; ++index) {
            buffer_[63U - index] = static_cast<std::uint8_t>(bit_count >> (index * 8U));
        }
        transform(buffer_);

        constexpr std::string_view HEX = "0123456789abcdef";
        std::string result;
        result.reserve(64);
        for (const std::uint32_t word : state_) {
            for (int shift = 28; shift >= 0; shift -= 4) {
                result.push_back(HEX[(word >> static_cast<unsigned>(shift)) & 0x0fU]);
            }
        }
        return result;
    }

    std::array<std::uint32_t, 8> state_ = INITIAL_STATE;
    std::array<std::uint8_t, 64> buffer_{};
    std::size_t buffer_size_ = 0;
    std::uint64_t byte_count_ = 0;
};

class RunnerError final : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

/// Owns an isolated scenario directory and removes it after observation.
class TemporaryDirectory final {
public:
    /// Creates a fresh directory whose identity is bound to this invocation.
    TemporaryDirectory(const std::string& invocation_id, const std::string& scenario_id)
        : path_([&] {
            const std::string identity = invocation_id + ":" + scenario_id;
            const std::vector<std::uint8_t> bytes(identity.begin(), identity.end());
            // Reset backup names are intentionally descriptive, so the scenario root must stay
            // short enough for the complete durable path to fit legacy Windows path limits.
            return fs::temp_directory_path() / ("cxc-" + Sha256::digest(bytes).substr(0, 16));
        }()) {
        if (!fs::create_directory(path_)) {
            throw RunnerError("scenario directory is not fresh: " + path_.string());
        }
    }

    /// Removes scenario inputs and generated reports without masking the result.
    ~TemporaryDirectory() {
        std::error_code error;
        fs::remove_all(path_, error);
    }

    TemporaryDirectory(const TemporaryDirectory&) = delete;
    TemporaryDirectory& operator=(const TemporaryDirectory&) = delete;

    /// Returns the absolute scenario filesystem root.
    [[nodiscard]] const fs::path& path() const noexcept { return path_; }

private:
    fs::path path_;
};

/// Sets one process environment variable for the current platform.
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
    return value == nullptr ? std::nullopt : std::optional(std::string(value));
#endif
}

/// Temporarily isolates cache lookup and current-directory state for one run.
class RuntimeEnvironment final {
public:
    /// Redirects user cache paths beneath the fresh scenario root using the family's fixture directory name.
    explicit RuntimeEnvironment(const fs::path& root, std::string_view cache_name = "isolated-cache")
        : previous_directory_(fs::current_path()) {
        for (const auto name : {"LOCALAPPDATA", "XDG_CACHE_HOME"}) {
            previous_environment_.emplace(name, read_environment(name));
        }
        const auto cache = root / cache_name;
        fs::create_directories(cache);
        set_environment("LOCALAPPDATA", cache.string());
        set_environment("XDG_CACHE_HOME", cache.string());
        fs::current_path(root);
    }

    /// Restores shared process state after the synchronous bridge call finishes.
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

/// Converts one generated bridge string into an owned standard string.
std::string owned_string(const rust::String& value) {
    return std::string(value);
}

/// Joins a validated clean relative plan path beneath one scenario root.
fs::path runtime_path(const fs::path& root, const json& carrier, std::string_view label) {
    if (!carrier.is_string()) {
        throw RunnerError(std::string(label) + " must be a string");
    }
    const fs::path relative(carrier.get<std::string>());
    if (relative.empty() || relative.is_absolute()) {
        throw RunnerError(std::string(label) + " must be a non-empty relative path");
    }
    for (const auto& component : relative) {
        if (component == "." || component == "..") {
            throw RunnerError(std::string(label) + " must be a clean relative path");
        }
    }
    return root / relative;
}

/// Converts an observed absolute path to portable scenario-root-relative form.
std::string relative_path(const fs::path& root, const fs::path& observed) {
    const fs::path normalized_root = fs::absolute(root).lexically_normal();
    const fs::path normalized_observed = fs::absolute(observed).lexically_normal();
    const fs::path relative = normalized_observed.lexically_relative(normalized_root);
    if (relative.empty() && normalized_observed != normalized_root) {
        throw RunnerError("observed path cannot be made scenario-root-relative: " + normalized_observed.string());
    }
    for (const auto& component : relative) {
        if (component == "..") {
            throw RunnerError("observed path escapes scenario root: " + normalized_observed.string());
        }
    }
    return relative.empty() ? "." : relative.generic_string();
}

/// Wraps one normalized path in the common structured path carrier.
json path_carrier(const fs::path& root, const fs::path& observed) {
    return json{{"path", relative_path(root, observed)}};
}

/// Returns the stable public token for one Local Ignore recovery decision.
std::string_view recovery_decision_token(scanner::ScanRunLocalIgnoreRecoveryDecision value) {
    switch (value) {
    case scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore:
        return "proceed_without_ignore";
    case scanner::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault:
        return "reset_to_default";
    }
    throw RunnerError("unrecognized CXX Local Ignore recovery decision");
}

/// Returns the exhaustive stable token for Display Content severity.
std::string_view severity_token(scanner::ScanRunDisplaySeverity value) {
    switch (value) {
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
    throw RunnerError("unrecognized CXX display severity");
}

/// Returns the exhaustive stable token for one flattened Display Segment kind.
std::string_view segment_kind_token(scanner::ScanRunDisplaySegmentKind value) {
    switch (value) {
    case scanner::ScanRunDisplaySegmentKind::Text:
        return "text";
    case scanner::ScanRunDisplaySegmentKind::Label:
        return "label";
    case scanner::ScanRunDisplaySegmentKind::Count:
        return "count";
    case scanner::ScanRunDisplaySegmentKind::Path:
        return "path";
    case scanner::ScanRunDisplaySegmentKind::Name:
        return "name";
    case scanner::ScanRunDisplaySegmentKind::Emphasis:
        return "emphasis";
    }
    throw RunnerError("unrecognized CXX display segment kind");
}

/// Reads exact bytes when a path is a regular file and distinguishes absence from I/O failure.
std::optional<std::vector<std::uint8_t>> read_optional_file(const fs::path& path) {
    std::error_code status_error;
    const fs::file_status status = fs::status(path, status_error);
    if (status_error == std::errc::no_such_file_or_directory || status.type() == fs::file_type::not_found) {
        return std::nullopt;
    }
    if (status_error) {
        throw RunnerError("cannot inspect durable effect: " + path.string() + ": " + status_error.message());
    }
    if (!fs::is_regular_file(status)) {
        return std::vector<std::uint8_t>{};
    }
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw RunnerError("cannot read durable effect: " + path.string());
    }
    return std::vector<std::uint8_t>(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
}

/// Copies one centrally declared fixture placement into the isolated root.
void copy_fixture(const json& plan, const json& scenario, const json& placement, const fs::path& root,
                  std::string_view label) {
    if (!placement.contains("fixtureRef")) {
        return;
    }
    const std::string reference = placement.at("fixtureRef").get<std::string>();
    const auto& declared_references = scenario.at("fixtureRefs");
    if (std::find(declared_references.begin(), declared_references.end(), reference) == declared_references.end()) {
        throw RunnerError(std::string(label) + " references a fixture outside the scenario");
    }
    const auto fixture = plan.at("fixtures").find(reference);
    if (fixture == plan.at("fixtures").end() || !fixture->is_string()) {
        throw RunnerError(std::string(label) + " references an undeclared fixture");
    }
    const fs::path source(fixture->get<std::string>());
    const fs::path destination = runtime_path(root, placement.at("path"), label);
    fs::create_directories(destination.parent_path());
    fs::copy_file(source, destination, fs::copy_options::overwrite_existing);
}

/// Reads a required durable file, rejecting directories and missing or unreadable evidence.
std::vector<std::uint8_t> autoscan_file_bytes(const fs::path& path) {
    if (!fs::is_regular_file(path)) {
        throw RunnerError("Autoscan Report evidence is not a regular file: " + path.string());
    }
    std::ifstream stream(path, std::ios::binary);
    if (!stream) {
        throw RunnerError("cannot open Autoscan Report evidence: " + path.string());
    }
    std::vector<std::uint8_t> bytes{std::istreambuf_iterator<char>(stream), std::istreambuf_iterator<char>()};
    if (stream.bad()) {
        throw RunnerError("cannot read Autoscan Report evidence: " + path.string());
    }
    return bytes;
}

#include "classic_cxx_semantic_conformance.h"
#include "classic_cxx_aux_operations_conformance.h"
#include "classic_cxx_version_values_conformance.h"
#include "classic_cxx_update_rejection_conformance.h"
#include "classic_cxx_interface_helpers_conformance.h"
#include "classic_cxx_performance_conformance.h"
#include "classic_cxx_shared_identity_conformance.h"
#include "classic_cxx_config_operations_conformance.h"
#include "classic_cxx_file_backups_conformance.h"
#include "classic_cxx_database_operations_conformance.h"
#include "classic_cxx_version_registry_conformance.h"
#include "classic_cxx_xse_folder_conformance.h"
#include "classic_cxx_file_operations_conformance.h"
#include "classic_cxx_installation_paths_conformance.h"
#include "classic_cxx_user_settings_conformance.h"
#include "classic_cxx_game_setup_intake_conformance.h"
#include "classic_cxx_crash_log_scan_launch_conformance.h"

/// Rejects a run plan for a family no CXX runner implements.
///
/// Crash Log Scan Run and Autoscan Report left CXX with the request constructors
/// their runner needed (#309), so the dispatch chain ends here instead of in a
/// scan-run executor.
json unsupported_family_scenario(const json& plan) {
    throw RunnerError("unsupported CXX conformance family: " + plan.at("familyId").get<std::string>());
}

/// Executes one planned case while retaining runner failures as receipt evidence.
json scenario_receipt(const json& plan, const json& scenario) {
    try {
        return json{{"id", scenario.at("id")},
                    {"executionStatus", "completed"},
                    {"capabilityIds", scenario.at("capabilityIds")},
                    {"observation", is_semantic_family(plan.at("familyId")) ? execute_semantic_scenario(plan, scenario)
                                    : plan.at("familyId") == "game-setup-intake" ? execute_game_setup_intake_scenario(plan, scenario)
                                    : plan.at("familyId") == "file-backups" ? execute_file_backups_scenario(plan, scenario)
                                    : plan.at("familyId") == "config-operations" ? execute_config_operations_scenario(plan, scenario)
                                    : plan.at("familyId") == "file-operations" ? execute_file_operations(plan, scenario)
                                    : plan.at("familyId") == "database-operations" ? execute_database_operations_scenario(plan, scenario)
                                    : plan.at("familyId") == "version-registry" ? execute_version_registry_scenario(plan, scenario)
                                    : (plan.at("familyId") == "game-version-parse" || plan.at("familyId") == "fallout4-identity" || plan.at("familyId") == "fallout4-paths") ? execute_version_values_scenario(plan, scenario)
                                      : plan.at("familyId") == "version-pe" ? execute_aux_operations_scenario(plan, scenario)
                                    : plan.at("familyId") == "installation-paths" ? execute_installation_paths_scenario(plan, scenario)
                                    : plan.at("familyId") == "xse-folder" ? execute_xse_folder_scenario(plan, scenario)
                                    : plan.at("familyId") == "report-discovery" ? execute_interface_helpers_scenario(plan, scenario)
                                    : plan.at("familyId") == "update-rejection" ? execute_update_rejection_scenario(plan, scenario)
                                    : plan.at("familyId") == "performance" ? execute_performance_scenario(plan, scenario)
                                    : plan.at("familyId") == "game-identity" ? execute_shared_identity_scenario(plan, scenario)
                                    : plan.at("familyId") == "crash-log-scan-launch"
                                        ? execute_crash_log_scan_launch_scenario(plan, scenario)
                                    : plan.at("familyId") == "user-settings"
                                        ? execute_user_settings_scenario(plan, scenario)
                                        : unsupported_family_scenario(plan)},
                    {"failure", nullptr}};
    } catch (const std::exception& error) {
        return json{{"id", scenario.value("id", "unknown")},
                    {"executionStatus", "failed"},
                    {"capabilityIds", scenario.value("capabilityIds", json::array())},
                    {"observation", json::object()},
                    {"failure", json{{"kind", "cxx-runner-error"}, {"message", error.what()}}}};
    }
}

/// Validates the closed header and rejects any accidental oracle exposure.
void validate_plan(const json& plan) {
    if (!plan.is_object() || plan.at("schemaVersion") != 1 ||
        (plan.at("familyId") != "user-settings" &&
         plan.at("familyId") != "crash-log-scan-launch" &&
         plan.at("familyId") != "game-setup-intake" &&
         plan.at("familyId") != "file-backups" &&
         plan.at("familyId") != "config-operations" && plan.at("familyId") != "file-operations" &&
           plan.at("familyId") != "version-pe" && plan.at("familyId") != "game-version-parse" && plan.at("familyId") != "fallout4-identity" && plan.at("familyId") != "fallout4-paths" &&
           plan.at("familyId") != "report-discovery" && plan.at("familyId") != "update-rejection" && plan.at("familyId") != "xse-folder" && plan.at("familyId") != "installation-paths" &&
         plan.at("familyId") != "performance" &&
         plan.at("familyId") != "game-identity" &&
         plan.at("familyId") != "database-operations" && plan.at("familyId") != "version-registry" &&
         !is_semantic_family(plan.at("familyId")))) {
        throw RunnerError("unsupported CXX conformance run plan");
    }
    const json& participant = plan.at("participant");
    const std::string expected_instance = "windows-" + std::string(TOOLCHAIN);
    if (participant.at("id") != "cxx" || participant.at("role") != "semantic-adapter" ||
        participant.at("executionInstanceId") != expected_instance) {
        throw RunnerError("run plan does not match this CXX execution instance");
    }
    for (const auto& scenario : plan.at("scenarios")) {
        if (scenario.contains("expected")) {
            throw RunnerError("input-only run plan exposed expected observations");
        }
    }
}

/// Builds one receipt while copying only centrally owned invocation identity.
json build_receipt(const json& plan) {
    validate_plan(plan);
    json scenarios = json::array();
    for (const auto& scenario : plan.at("scenarios")) {
        scenarios.push_back(scenario_receipt(plan, scenario));
    }
    return json{{"schemaVersion", plan.at("schemaVersion")},
                {"familyId", plan.at("familyId")},
                {"familyVersion", plan.at("familyVersion")},
                {"expectationDigest", plan.at("expectationDigest")},
                {"invocation", plan.at("invocation")},
                {"participant", plan.at("participant")},
                {"runner", json{{"id", RUNNER_ID}, {"version", 1}, {"platform", "windows"}, {"toolchain", TOOLCHAIN}}},
                {"scenarios", std::move(scenarios)}};
}

/// Reads one UTF-8 JSON document from an absolute launcher-owned path.
json read_json(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw RunnerError("cannot open CXX conformance run plan: " + path.string());
    }
    return json::parse(input, nullptr, true, true);
}

/// Publishes a fresh compact receipt through a same-directory atomic rename.
void publish_receipt(const fs::path& output_path, const json& receipt) {
    if (fs::exists(output_path)) {
        throw RunnerError("CXX conformance receipt destination already exists");
    }
    fs::create_directories(output_path.parent_path());
    const fs::path temporary = output_path.parent_path() / ("." + output_path.filename().string() + ".tmp");
    try {
        std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
        if (!output) {
            throw RunnerError("cannot create temporary CXX conformance receipt");
        }
        output << receipt.dump();
        output.flush();
        if (!output) {
            throw RunnerError("cannot flush temporary CXX conformance receipt");
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

/// Reads launcher-only state, executes every input scenario, and emits one receipt.
int main() {
    try {
        const auto run_plan_value = read_environment(RUN_PLAN_ENV);
        const auto output_value = read_environment(OUTPUT_ENV);
        if (!run_plan_value.has_value() || run_plan_value->empty() || !output_value.has_value() ||
            output_value->empty()) {
            std::cout << "SKIP: " << RUN_PLAN_ENV << " and " << OUTPUT_ENV
                      << " are required for native CXX conformance\n";
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
        const json plan = read_json(run_plan);
        publish_receipt(output, build_receipt(plan));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << RUNNER_ID << ": " << error.what() << '\n';
        return 2;
    }
}
