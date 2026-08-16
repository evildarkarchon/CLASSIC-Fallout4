// SPDX-License-Identifier: MIT
//
// Bridge-only Crash Log Scan Run conformance participant. This executable is
// hosted by the CLI build but does not link or compile any frontend source.

#include "classic_cxx_bridge/scanner.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <charconv>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <map>
#include <mutex>
#include <optional>
#include <span>
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
            const std::uint32_t first = working[7] + big_one + choice + ROUND_CONSTANTS[index] + words[index];
            const std::uint32_t big_zero =
                rotate_right(working[0], 2U) ^ rotate_right(working[0], 13U) ^ rotate_right(working[0], 22U);
            const std::uint32_t majority =
                (working[0] & working[1]) ^ (working[0] & working[2]) ^ (working[1] & working[2]);
            const std::uint32_t second = big_zero + majority;
            for (std::size_t position = working.size() - 1; position > 0; --position) {
                working[position] = working[position - 1];
            }
            working[4] += first;
            working[0] = first + second;
        }
        for (std::size_t index = 0; index < state_.size(); ++index) {
            state_[index] += working[index];
        }
    }

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
    /// Redirects user cache paths beneath the fresh scenario root.
    explicit RuntimeEnvironment(const fs::path& root)
        : previous_directory_(fs::current_path()) {
        for (const auto name : {"LOCALAPPDATA", "XDG_CACHE_HOME"}) {
            previous_environment_.emplace(name, read_environment(name));
        }
        const auto cache = root / "isolated-cache";
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

/// Returns the exhaustive stable token for one run status.
std::string_view status_token(scanner::ScanRunContractStatus value) {
    switch (value) {
    case scanner::ScanRunContractStatus::Completed:
        return "completed";
    case scanner::ScanRunContractStatus::NoCrashLogsFound:
        return "no_crash_logs_found";
    case scanner::ScanRunContractStatus::SetupFailed:
        return "setup_failed";
    case scanner::ScanRunContractStatus::CancelledBeforeDiscovery:
        return "cancelled_before_discovery";
    case scanner::ScanRunContractStatus::Cancelled:
        return "cancelled";
    case scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired:
        return "local_ignore_recovery_required";
    }
    throw RunnerError("unrecognized CXX run status");
}

/// Returns the exhaustive stable token for one discovery source.
std::string_view discovery_source_token(scanner::ScanRunContractDiscoverySource value) {
    switch (value) {
    case scanner::ScanRunContractDiscoverySource::Standard:
        return "standard";
    case scanner::ScanRunContractDiscoverySource::Targeted:
        return "targeted";
    }
    throw RunnerError("unrecognized CXX discovery source");
}

/// Returns the exhaustive stable token for one log disposition.
std::string_view disposition_token(scanner::ScanRunContractLogDisposition value) {
    switch (value) {
    case scanner::ScanRunContractLogDisposition::Succeeded:
        return "succeeded";
    case scanner::ScanRunContractLogDisposition::Failed:
        return "failed";
    case scanner::ScanRunContractLogDisposition::CancelledBeforeStart:
        return "cancelled_before_start";
    }
    throw RunnerError("unrecognized CXX log disposition");
}

/// Returns the exhaustive stable token for one log failure stage.
std::string_view failure_stage_token(scanner::ScanRunContractLogFailureStage value) {
    switch (value) {
    case scanner::ScanRunContractLogFailureStage::Analysis:
        return "analysis";
    case scanner::ScanRunContractLogFailureStage::ReportWrite:
        return "report_write";
    case scanner::ScanRunContractLogFailureStage::UnsolvedLogsFinalization:
        return "unsolved_logs_finalization";
    }
    throw RunnerError("unrecognized CXX log failure stage");
}

/// Returns the exhaustive stable token for one progress phase.
std::string_view phase_token(scanner::ScanRunContractProgressPhase value) {
    switch (value) {
    case scanner::ScanRunContractProgressPhase::Setup:
        return "setup";
    case scanner::ScanRunContractProgressPhase::Parse:
        return "parse";
    case scanner::ScanRunContractProgressPhase::Analyze:
        return "analyze";
    case scanner::ScanRunContractProgressPhase::Finalize:
        return "finalize";
    }
    throw RunnerError("unrecognized CXX progress phase");
}

/// Returns the exhaustive stable token for one Installed YAML Data role.
std::string_view yaml_role_token(scanner::ScanRunInstalledYamlDataRole value) {
    switch (value) {
    case scanner::ScanRunInstalledYamlDataRole::Main:
        return "main";
    case scanner::ScanRunInstalledYamlDataRole::Game:
        return "game";
    }
    throw RunnerError("unrecognized CXX YAML Data role");
}

/// Returns the exhaustive stable token for one Installed YAML Data provenance.
std::string_view yaml_provenance_token(scanner::ScanRunInstalledYamlDataProvenance value) {
    switch (value) {
    case scanner::ScanRunInstalledYamlDataProvenance::Updated:
        return "updated";
    case scanner::ScanRunInstalledYamlDataProvenance::Previous:
        return "previous";
    case scanner::ScanRunInstalledYamlDataProvenance::Bundled:
        return "bundled";
    }
    throw RunnerError("unrecognized CXX YAML Data provenance");
}

/// Returns the exhaustive stable token for one Installed YAML Data diagnostic.
std::string_view yaml_diagnostic_token(scanner::ScanRunInstalledYamlDataDiagnosticKind value) {
    switch (value) {
    case scanner::ScanRunInstalledYamlDataDiagnosticKind::CacheUnavailable:
        return "cache_unavailable";
    case scanner::ScanRunInstalledYamlDataDiagnosticKind::Missing:
        return "missing";
    case scanner::ScanRunInstalledYamlDataDiagnosticKind::Read:
        return "read";
    case scanner::ScanRunInstalledYamlDataDiagnosticKind::InvalidUtf8:
        return "invalid_utf8";
    case scanner::ScanRunInstalledYamlDataDiagnosticKind::Parse:
        return "parse";
    case scanner::ScanRunInstalledYamlDataDiagnosticKind::InvalidSchema:
        return "invalid_schema";
    case scanner::ScanRunInstalledYamlDataDiagnosticKind::IncompatibleSchema:
        return "incompatible_schema";
    case scanner::ScanRunInstalledYamlDataDiagnosticKind::InvalidRoleData:
        return "invalid_role_data";
    case scanner::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated:
        return "local_ignore_generated";
    case scanner::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreReset:
        return "local_ignore_reset";
    }
    throw RunnerError("unrecognized CXX YAML Data diagnostic kind");
}

/// Returns the exhaustive stable token for Local Ignore snapshot state.
std::string_view local_ignore_state_token(scanner::ScanRunLocalIgnoreYamlDataState value) {
    switch (value) {
    case scanner::ScanRunLocalIgnoreYamlDataState::Existing:
        return "existing";
    case scanner::ScanRunLocalIgnoreYamlDataState::Generated:
        return "generated";
    case scanner::ScanRunLocalIgnoreYamlDataState::RecoveryRequired:
        return "recovery_required";
    case scanner::ScanRunLocalIgnoreYamlDataState::ProceedWithoutIgnore:
        return "proceed_without_ignore";
    case scanner::ScanRunLocalIgnoreYamlDataState::ResetToDefault:
        return "reset_to_default";
    }
    throw RunnerError("unrecognized CXX Local Ignore state");
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

/// Serializes frozen Display Content while preserving every unused carrier field.
json serialize_display(const rust::Vec<scanner::ScanRunDisplayLine>& lines, const fs::path& root) {
    json result = json::array();
    for (const auto& line : lines) {
        json segments = json::array();
        for (const auto& segment : line.segments) {
            std::string path = owned_string(segment.path);
            if (!path.empty()) {
                path = relative_path(root, fs::path(path));
            }
            segments.push_back(json{{"kind", segment_kind_token(segment.kind)},
                                    {"text", owned_string(segment.text)},
                                    {"path", path},
                                    {"count", segment.count}});
        }
        result.push_back(json{{"severity", severity_token(line.severity)}, {"segments", std::move(segments)}});
    }
    return result;
}

/// Serializes one retained exact-byte YAML Data identity.
json serialize_identity(const scanner::ScanRunYamlDataContentIdentityDto& identity) {
    return json{{"sha256", owned_string(identity.sha256)}, {"byteLength", identity.byte_len}};
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

/// Projects an exact byte identity using the same lowercase SHA-256 representation as Rust.
json exact_identity(std::span<const std::uint8_t> bytes) {
    return json{{"sha256", Sha256::digest(bytes)}, {"byteLength", bytes.size()}};
}

/// Preserves only the ordered severities from public Display Content.
json display_severities(const rust::Vec<scanner::ScanRunDisplayLine>& lines) {
    json result = json::array();
    for (const auto& line : lines) {
        result.push_back(severity_token(line.severity));
    }
    return result;
}

/// Parses the generated bridge's major.minor schema representation.
std::pair<std::uint64_t, std::uint64_t> parse_schema_version(const rust::String& raw) {
    const std::string value = owned_string(raw);
    const std::size_t separator = value.find('.');
    if (separator == std::string::npos || value.find('.', separator + 1) != std::string::npos) {
        throw RunnerError("CXX YAML Data schema version is not major.minor: " + value);
    }
    std::uint64_t major = 0;
    std::uint64_t minor = 0;
    const auto major_result = std::from_chars(value.data(), value.data() + separator, major);
    const auto minor_result = std::from_chars(value.data() + separator + 1, value.data() + value.size(), minor);
    if (major_result.ec != std::errc{} || major_result.ptr != value.data() + separator ||
        minor_result.ec != std::errc{} || minor_result.ptr != value.data() + value.size()) {
        throw RunnerError("CXX YAML Data schema version is not numeric: " + value);
    }
    return {major, minor};
}

/// Serializes one selected Installed YAML Data file.
json serialize_yaml_file(const scanner::ScanRunInspectedYamlDataFileDto& file) {
    const auto [major, minor] = parse_schema_version(file.schema_version);
    return json{{"role", yaml_role_token(file.role)},
                {"provenance", yaml_provenance_token(file.provenance)},
                {"schemaMajor", major},
                {"schemaMinor", minor},
                {"identity", json{{"sha256", owned_string(file.sha256)}, {"byteLength", file.byte_len}}}};
}

/// Serializes Installed YAML Data identities, provenance, state, and diagnostics.
json serialize_installed_yaml_data(const scanner::ScanRunInstalledYamlDataRunDataDto& installed, const fs::path& root) {
    json diagnostics = json::array();
    for (const auto& diagnostic : installed.diagnostics) {
        diagnostics.push_back(json{
            {"role", diagnostic.has_role ? json(yaml_role_token(diagnostic.role)) : json(nullptr)},
            {"candidate", diagnostic.has_candidate ? json(yaml_provenance_token(diagnostic.candidate)) : json(nullptr)},
            {"path", diagnostic.has_path ? path_carrier(root, fs::path(owned_string(diagnostic.path))) : json(nullptr)},
            {"kind", yaml_diagnostic_token(diagnostic.kind)},
            {"message", owned_string(diagnostic.message)}});
    }
    return json{{"main", serialize_yaml_file(installed.main)},
                {"gameFile", serialize_yaml_file(installed.game_file)},
                {"localIgnoreState", local_ignore_state_token(installed.local_ignore_state)},
                {"localIgnoreIdentity", serialize_identity(installed.local_ignore_identity)},
                {"diagnostics", std::move(diagnostics)},
                {"localIgnoreResetAvailable", installed.local_ignore_reset_available}};
}

/// Serializes stable Local Ignore recovery fields while omitting path-bearing diagnostic prose.
json serialize_local_ignore_installed_yaml_data(const scanner::ScanRunInstalledYamlDataRunDataDto& installed,
                                                const fs::path& root) {
    json diagnostics = json::array();
    for (const auto& diagnostic : installed.diagnostics) {
        diagnostics.push_back(json{
            {"role", diagnostic.has_role ? json(yaml_role_token(diagnostic.role)) : json(nullptr)},
            {"candidate", diagnostic.has_candidate ? json(yaml_provenance_token(diagnostic.candidate)) : json(nullptr)},
            {"path", diagnostic.has_path ? path_carrier(root, fs::path(owned_string(diagnostic.path))) : json(nullptr)},
            {"kind", yaml_diagnostic_token(diagnostic.kind)}});
    }

    json reset = nullptr;
    if (installed.has_local_ignore_reset) {
        const auto& receipt = installed.local_ignore_reset;
        const fs::path backup_path(owned_string(receipt.backup_path));
        const fs::path backup_parent = backup_path.parent_path();
        if (backup_parent.empty()) {
            throw RunnerError("Local Ignore reset backup has no parent directory");
        }
        const auto backup_bytes = read_optional_file(backup_path);
        const bool identity_matches = backup_bytes.has_value() &&
                                      Sha256::digest(*backup_bytes) == owned_string(receipt.backup_identity.sha256) &&
                                      backup_bytes->size() == receipt.backup_identity.byte_len;
        reset = json{{"localIgnorePath", path_carrier(root, fs::path(owned_string(receipt.local_ignore_path)))},
                     {"backup", json{{"parentPath", relative_path(root, backup_parent)},
                                     {"exists", backup_bytes.has_value()},
                                     {"identityMatchesReceipt", identity_matches}}},
                     {"malformedIdentity", serialize_identity(receipt.malformed_identity)},
                     {"backupIdentity", serialize_identity(receipt.backup_identity)},
                     {"replacementIdentity", serialize_identity(receipt.replacement_identity)}};
    }

    return json{{"mainIdentity",
                 json{{"sha256", owned_string(installed.main.sha256)}, {"byteLength", installed.main.byte_len}}},
                {"gameIdentity", json{{"sha256", owned_string(installed.game_file.sha256)},
                                      {"byteLength", installed.game_file.byte_len}}},
                {"localIgnoreState", local_ignore_state_token(installed.local_ignore_state)},
                {"localIgnoreIdentity", serialize_identity(installed.local_ignore_identity)},
                {"diagnostics", std::move(diagnostics)},
                {"localIgnoreResetAvailable", installed.local_ignore_reset_available},
                {"localIgnoreReset", std::move(reset)}};
}

/// Serializes ordered Standard or Targeted discovery facts.
json serialize_discovery(const scanner::ScanRunContractDiscoveryResult& discovery, const fs::path& root) {
    json accepted = json::array();
    for (const auto& path : discovery.accepted_logs) {
        accepted.push_back(path_carrier(root, fs::path(owned_string(path))));
    }
    json rejected = json::array();
    for (const auto& item : discovery.rejected_inputs) {
        rejected.push_back(json{{"path", relative_path(root, fs::path(owned_string(item.path)))},
                                {"reason", owned_string(item.reason)}});
    }
    json searched = json::array();
    for (const auto& path : discovery.searched_locations) {
        searched.push_back(path_carrier(root, fs::path(owned_string(path))));
    }
    return json{{"source", discovery_source_token(discovery.source)},
                {"acceptedLogs", std::move(accepted)},
                {"rejectedInputs", std::move(rejected)},
                {"searchedLocations", std::move(searched)}};
}

/// Serializes one discovery-ordered terminal log result without timing fields.
json serialize_log(const scanner::ScanRunContractLogResult& log, const fs::path& root) {
    json failures = json::array();
    for (const auto& failure : log.failures) {
        failures.push_back(
            json{{"stage", failure_stage_token(failure.stage)}, {"message", owned_string(failure.message)}});
    }
    return json{{"discoveryIndex", log.discovery_index},
                {"crashLog", path_carrier(root, fs::path(owned_string(log.crash_log)))},
                {"autoscanReport", log.has_autoscan_report
                                       ? path_carrier(root, fs::path(owned_string(log.autoscan_report)))
                                       : json(nullptr)},
                {"disposition", disposition_token(log.disposition)},
                {"failures", std::move(failures)},
                {"message", log.has_message ? json(owned_string(log.message)) : json(nullptr)},
                {"movedToUnsolvedLogs", log.moved_to_unsolved_logs}};
}

/// Snapshots borrowed generated events into CXX-owned normalized JSON.
class RecordingObserver final : public scanner::ScanRunObserver {
public:
    /// Borrows the stable scenario root used to normalize callback paths.
    explicit RecordingObserver(const fs::path& root)
        : root_(root) {}

    /// Traverses every borrowed DTO field before the synchronous callback returns.
    void on_scan_run_event(const scanner::ScanRunContractEvent& event) const noexcept override {
        std::lock_guard lock(mutex_);
        if (!error_.empty()) {
            return;
        }
        try {
            json value{{"displayContent", serialize_display(event.display_lines, root_)}};
            switch (event.kind) {
            case scanner::ScanRunContractEventKind::DiscoveryCompleted:
                value["kind"] = "discovery_completed";
                run_events_.push_back(std::move(value));
                return;
            case scanner::ScanRunContractEventKind::EffectiveConcurrencySelected:
                value["kind"] = "effective_concurrency_selected";
                value["effectiveConcurrency"] = event.effective_concurrency;
                run_events_.push_back(std::move(value));
                return;
            case scanner::ScanRunContractEventKind::LogQueued:
                value["kind"] = "log_queued";
                break;
            case scanner::ScanRunContractEventKind::LogStarted:
                value["kind"] = "log_started";
                break;
            case scanner::ScanRunContractEventKind::LogPhase:
                value["kind"] = "log_phase";
                value["phase"] = phase_token(event.phase);
                break;
            case scanner::ScanRunContractEventKind::LogFinished:
                value["kind"] = "log_finished";
                value["disposition"] = disposition_token(event.disposition);
                break;
            }
            auto& stream = log_events_[event.discovery_index];
            const std::string crash_log = relative_path(root_, fs::path(owned_string(event.crash_log)));
            if (stream.crash_log.empty()) {
                stream.crash_log = crash_log;
            } else if (stream.crash_log != crash_log) {
                throw RunnerError("event Crash Log identity changed within one discovery index");
            }
            stream.trace.push_back(std::move(value));
        } catch (const std::exception& error) {
            error_ = error.what();
        } catch (...) {
            error_ = "unknown CXX observer serialization failure";
        }
    }

    /// Returns partitioned run and per-log traces in result discovery order.
    json observation(const scanner::ScanRunContractRunResult& result) const {
        std::lock_guard lock(mutex_);
        if (!error_.empty()) {
            throw RunnerError("observer delivery failed: " + error_);
        }
        json logs = json::array();
        for (const auto& log : result.logs) {
            const auto found = log_events_.find(log.discovery_index);
            const json trace = found == log_events_.end() ? json::array() : found->second.trace;
            logs.push_back(json{{"discoveryIndex", log.discovery_index},
                                {"crashLog", path_carrier(root_, fs::path(owned_string(log.crash_log)))},
                                {"trace", trace}});
        }
        return json{{"run", run_events_}, {"logs", std::move(logs)}};
    }

    /// Returns stable event tokens while preserving run and per-log ordering.
    json compact_observation(const scanner::ScanRunContractRunResult& result) const {
        std::lock_guard lock(mutex_);
        if (!error_.empty()) {
            throw RunnerError("observer delivery failed: " + error_);
        }
        json run = json::array();
        for (const auto& event : run_events_) {
            run.push_back(event.at("kind"));
        }
        json logs = json::array();
        for (const auto& log : result.logs) {
            json trace = json::array();
            const auto found = log_events_.find(log.discovery_index);
            if (found != log_events_.end()) {
                if (found->second.crash_log != relative_path(root_, fs::path(owned_string(log.crash_log)))) {
                    throw RunnerError("compact event references a different Crash Log");
                }
                for (const auto& event : found->second.trace) {
                    const std::string kind = event.at("kind").get<std::string>();
                    if (kind == "log_phase") {
                        trace.push_back(kind + ":" + event.at("phase").get<std::string>());
                    } else if (kind == "log_finished") {
                        trace.push_back(kind + ":" + event.at("disposition").get<std::string>());
                    } else {
                        trace.push_back(kind);
                    }
                }
            }
            logs.push_back(json{{"discoveryIndex", log.discovery_index}, {"trace", std::move(trace)}});
        }
        return json{{"run", std::move(run)}, {"logs", std::move(logs)}};
    }

private:
    struct LogEventStream {
        std::string crash_log;
        json trace = json::array();
    };

    fs::path root_;
    mutable std::mutex mutex_;
    mutable std::string error_;
    mutable json run_events_ = json::array();
    mutable std::map<std::size_t, LogEventStream> log_events_;
};

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

/// Applies ordered after-pause mutations only after the retained continuation is claimed.
void materialize_post_pause_data(const json& plan, const json& scenario, const json& flow, const fs::path& root) {
    std::size_t index = 0;
    for (const auto& placement : flow.value("postPauseData", json::array())) {
        copy_fixture(plan, scenario, placement, root, "postPauseData[" + std::to_string(index++) + "]");
    }
}

/// Materializes only scenario inputs and returns the closed input object.
const json& materialize_inputs(const json& plan, const json& scenario, const fs::path& root) {
    if (scenario.contains("expected")) {
        throw RunnerError("input-only run plan exposed expected observations");
    }
    const json& input = scenario.at("input");
    std::size_t index = 0;
    for (const auto& placement : input.at("installationData")) {
        copy_fixture(plan, scenario, placement, root, "installationData[" + std::to_string(index++) + "]");
    }
    const std::string intent = input.at("intent").get<std::string>();
    const std::string input_field = intent == "standard" ? "logInputs" : "targetedInputs";
    index = 0;
    for (const auto& placement : input.at(input_field)) {
        copy_fixture(plan, scenario, placement, root, input_field + "[" + std::to_string(index++) + "]");
    }
    if (intent == "standard") {
        const json& source = input.at("standardSource");
        fs::create_directories(
            runtime_path(root, source.at("baseDirectory").at("path"), "standard baseDirectory.path"));
        fs::create_directories(runtime_path(root, source.at("configuredDocumentsRoot").at("path"),
                                            "standard configuredDocumentsRoot.path"));
    } else if (intent != "targeted") {
        throw RunnerError("scenario intent must be standard or targeted");
    }
    return input;
}

/// Builds the shared CXX request entirely from one input-only scenario.
rust::Box<scanner::ScanRunRequest> build_request(const json& input, const fs::path& root) {
    if (input.at("game") != "fallout4") {
        throw RunnerError("base CXX scenario game must be fallout4");
    }
    scanner::ScanRunConfigurationDto configuration{};
    configuration.installation_root = root.string();
    configuration.game = scanner::ScanRunGameId::Fallout4;
    configuration.game_version = input.at("gameVersion").get<std::string>();
    configuration.show_formid_values = input.at("showFormidValues").get<bool>();
    configuration.simplify_logs = input.at("simplifyLogs").get<bool>();
    for (const auto& raw_path : input.at("formidDatabasePaths")) {
        const json& carrier = raw_path.is_object() ? raw_path.at("path") : raw_path;
        configuration.formid_database_paths.push_back(
            runtime_path(root, carrier, "formidDatabasePaths entry").string());
    }
    configuration.has_max_concurrent = true;
    configuration.max_concurrent = input.at("maxConcurrent").get<std::size_t>();

    const std::string intent = input.at("intent").get<std::string>();
    if (intent == "standard") {
        if (input.at("unsolvedLogs") != "leave-in-place") {
            throw RunnerError("base CXX Standard scenario must leave Unsolved Logs in place");
        }
        const json& raw_source = input.at("standardSource");
        scanner::ScanRunStandardSourceDto source{};
        source.base_directory =
            runtime_path(root, raw_source.at("baseDirectory").at("path"), "baseDirectory.path").string();
        source.has_configured_documents_root = true;
        source.configured_documents_root =
            runtime_path(root, raw_source.at("configuredDocumentsRoot").at("path"), "configuredDocumentsRoot.path")
                .string();
        const auto movement = scanner::scan_run_unsolved_logs_leave_in_place();
        return scanner::scan_run_request_standard(configuration, source, *movement);
    }
    scanner::ScanRunTargetedSourceDto source{};
    for (const auto& raw_input : input.at("targetedInputs")) {
        source.inputs.push_back(runtime_path(root, raw_input.at("path"), "targetedInputs path").string());
    }
    return scanner::scan_run_request_targeted(configuration, source);
}

/// Projects one regular file's existence and exact identity, retaining absence as null identity.
json project_file_effect(const fs::path& root, const fs::path& path) {
    std::error_code error;
    const bool exists = fs::exists(path, error);
    if (error) {
        throw RunnerError("cannot inspect durable effect: " + path.string() + ": " + error.message());
    }
    json identity = nullptr;
    if (exists && fs::is_regular_file(path, error)) {
        const auto bytes = read_optional_file(path);
        if (!bytes.has_value()) {
            throw RunnerError("durable effect disappeared while being observed: " + path.string());
        }
        identity = exact_identity(*bytes);
    }
    if (error) {
        throw RunnerError("cannot classify durable effect: " + path.string() + ": " + error.message());
    }
    return json{{"path", relative_path(root, path)}, {"exists", exists}, {"identity", std::move(identity)}};
}

/// Projects one report's exact durable identity alongside existence and non-empty facts.
json project_exact_report_effect(const fs::path& root, const fs::path& path) {
    const auto bytes = read_optional_file(path);
    return json{{"path", relative_path(root, path)},
                {"exists", bytes.has_value()},
                {"nonEmpty", bytes.has_value() && !bytes->empty()},
                {"identity", bytes.has_value() ? exact_identity(*bytes) : json(nullptr)}};
}

/// Projects Local Ignore, backup, report, and explicitly forbidden filesystem effects.
json project_local_ignore_effects(const fs::path& root, const json& input,
                                  const scanner::ScanRunContractRunResult& result) {
    const fs::path backup_directory = root / "CLASSIC Backup/YAML Data/Local Ignore";
    std::vector<fs::path> backup_paths;
    if (fs::is_directory(backup_directory)) {
        for (const auto& entry : fs::directory_iterator(backup_directory)) {
            if (entry.is_regular_file()) {
                backup_paths.push_back(entry.path());
            }
        }
    }
    std::sort(backup_paths.begin(), backup_paths.end());
    json backups = json::array();
    for (const auto& path : backup_paths) {
        const auto bytes = read_optional_file(path);
        if (!bytes.has_value()) {
            throw RunnerError("enumerated Local Ignore backup disappeared before observation");
        }
        backups.push_back(
            json{{"parentPath", relative_path(root, path.parent_path())}, {"identity", exact_identity(*bytes)}});
    }

    json reports = json::array();
    for (const auto& log : result.logs) {
        if (log.has_autoscan_report) {
            reports.push_back(project_exact_report_effect(root, fs::path(owned_string(log.autoscan_report))));
        }
    }
    json forbidden = json::array();
    for (const auto& relative : input.value("forbiddenEffectPaths", json::array())) {
        forbidden.push_back(project_file_effect(root, runtime_path(root, relative, "forbiddenEffectPaths entry")));
    }
    return json{{"localIgnore", project_file_effect(root, root / "CLASSIC Data/CLASSIC Ignore.yaml")},
                {"backups", std::move(backups)},
                {"reports", std::move(reports)},
                {"forbidden", std::move(forbidden)}};
}

/// Projects one initial or terminal Local Ignore envelope without reading durable effects.
json project_local_ignore_phase(const scanner::ScanRunContractExecutionResult& execution,
                                const RecordingObserver& observer, const fs::path& root, bool continuation_available,
                                bool include_recovery_prompt) {
    if (execution.has_error) {
        throw RunnerError("CXX scan returned infrastructure error: " + owned_string(execution.error.message));
    }
    if (execution.has_resume_error) {
        throw RunnerError("CXX scan returned resume error: " + owned_string(execution.resume_error.message));
    }
    if (!execution.has_result) {
        throw RunnerError("CXX scan returned no result or error");
    }
    const auto& result = execution.result;
    if (result.has_setup) {
        throw RunnerError("Local Ignore CXX scenario unexpectedly returned setup data");
    }
    json logs = json::array();
    for (const auto& log : result.logs) {
        logs.push_back(serialize_log(log, root));
    }

    json prompt = nullptr;
    if (include_recovery_prompt) {
        if (!execution.has_recovery_prompt) {
            throw RunnerError("Local Ignore recovery result omitted its public recovery prompt");
        }
        json decisions = json::array();
        for (const auto& decision : execution.recovery_prompt.decisions) {
            decisions.push_back(json{{"decision", recovery_decision_token(decision.decision)},
                                     {"label", owned_string(decision.label)},
                                     {"available", decision.available}});
        }
        prompt = json{{"displaySeverities", display_severities(execution.recovery_prompt.lines)},
                      {"decisions", std::move(decisions)}};
    }

    return json{{"run", json{{"status", status_token(result.status)},
                             {"message", result.has_message ? json(owned_string(result.message)) : json(nullptr)},
                             {"total", result.total},
                             {"succeeded", result.succeeded},
                             {"failed", result.failed},
                             {"cancelled", result.cancelled},
                             {"effectiveConcurrency",
                              result.has_effective_concurrency ? json(result.effective_concurrency) : json(nullptr)}}},
                {"discovery", result.has_discovery ? serialize_discovery(result.discovery, root) : json(nullptr)},
                {"installedYamlData", result.has_installed_yaml_data
                                          ? serialize_local_ignore_installed_yaml_data(result.installed_yaml_data, root)
                                          : json(nullptr)},
                {"logs", std::move(logs)},
                {"events", observer.compact_observation(result)},
                {"continuationAvailable", continuation_available},
                {"recoveryPrompt", std::move(prompt)}};
}

/// Projects a complete single-stage Local Ignore observation and its durable effects.
json project_local_ignore_observation(const scanner::ScanRunContractExecutionResult& execution,
                                      const RecordingObserver& observer, const fs::path& root, const json& input,
                                      bool continuation_available) {
    json observation =
        project_local_ignore_phase(execution, observer, root, continuation_available, execution.has_recovery_prompt);
    observation["durableEffects"] = project_local_ignore_effects(root, input, execution.result);
    return observation;
}

/// Maps one validated plan decision to the generated public CXX enumeration.
scanner::ScanRunLocalIgnoreRecoveryDecision parse_recovery_decision(const json& action) {
    if (!action.contains("decision") || !action.at("decision").is_string()) {
        throw RunnerError("Resume continuation action has no recovery decision");
    }
    const std::string decision = action.at("decision").get<std::string>();
    if (decision == "proceed-without-ignore") {
        return scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore;
    }
    if (decision == "reset-to-default") {
        return scanner::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault;
    }
    throw RunnerError("unsupported Local Ignore recovery decision: " + decision);
}

/// Invokes one public continuation action without inferring intent from a scenario identifier.
rust::Box<scanner::ScanRunContractExecution> run_continuation_action(const scanner::ScanRunContinuation& continuation,
                                                                     const json& action,
                                                                     const scanner::ScanRunCancellation& cancellation,
                                                                     const scanner::ScanRunObserver* observer) {
    const std::string operation = action.at("operation").get<std::string>();
    if (operation == "resume") {
        return scanner::scan_run_continuation_resume(continuation, parse_recovery_decision(action), cancellation,
                                                     observer);
    }
    if (operation == "abandon") {
        if (action.contains("decision") && !action.at("decision").is_null()) {
            throw RunnerError("Abandon continuation action must not have a recovery decision");
        }
        return scanner::scan_run_continuation_abandon(continuation, cancellation, observer);
    }
    throw RunnerError("unsupported continuation operation: " + operation);
}

/// Projects one typed consumed-continuation replay through the public CXX presentation envelope.
json project_replay(const json& action, const scanner::ScanRunContractExecutionResult& execution) {
    if (execution.has_result || execution.has_error || !execution.has_resume_error) {
        throw RunnerError("a replayed continuation action unexpectedly succeeded");
    }
    const std::string operation = action.at("operation").get<std::string>();
    json decision = nullptr;
    if (operation == "resume") {
        decision = recovery_decision_token(parse_recovery_decision(action));
    }
    return json{{"operation", operation},
                {"decision", std::move(decision)},
                {"error", json{{"kind", owned_string(execution.resume_error.code)},
                               {"message", owned_string(execution.resume_error.message)},
                               {"displaySeverities", display_severities(execution.display_lines)}}}};
}

/// Projects the complete public CXX terminal envelope and durable effects.
json project_observation(const scanner::ScanRunContractExecutionResult& execution, const RecordingObserver& observer,
                         const fs::path& root) {
    if (execution.has_error) {
        throw RunnerError("CXX scan returned infrastructure error: " + owned_string(execution.error.message));
    }
    if (execution.has_resume_error) {
        throw RunnerError("CXX scan returned resume error: " + owned_string(execution.resume_error.message));
    }
    if (!execution.has_result) {
        throw RunnerError("CXX scan returned no result or error");
    }
    const auto& result = execution.result;
    if (result.has_setup) {
        throw RunnerError("non-FCX base CXX scenario unexpectedly returned setup data");
    }

    json logs = json::array();
    json reports = json::array();
    for (const auto& log : result.logs) {
        logs.push_back(serialize_log(log, root));
        if (log.has_autoscan_report) {
            const fs::path report(owned_string(log.autoscan_report));
            std::error_code error;
            const bool exists = fs::is_regular_file(report, error);
            const bool non_empty = exists && fs::file_size(report, error) > 0 && !error;
            reports.push_back(json{{"path", relative_path(root, report)}, {"exists", exists}, {"nonEmpty", non_empty}});
        }
    }
    const fs::path unsolved_logs = root / "Unsolved Logs";
    return json{{"run", json{{"status", status_token(result.status)},
                             {"message", result.has_message ? json(owned_string(result.message)) : json(nullptr)},
                             {"total", result.total},
                             {"succeeded", result.succeeded},
                             {"failed", result.failed},
                             {"cancelled", result.cancelled},
                             {"setup", nullptr},
                             {"effectiveConcurrency",
                              result.has_effective_concurrency ? json(result.effective_concurrency) : json(nullptr)}}},
                {"discovery", result.has_discovery ? serialize_discovery(result.discovery, root) : json(nullptr)},
                {"installedYamlData", result.has_installed_yaml_data
                                          ? serialize_installed_yaml_data(result.installed_yaml_data, root)
                                          : json(nullptr)},
                {"logs", std::move(logs)},
                {"events", observer.observation(result)},
                {"displayContent", serialize_display(execution.display_lines, root)},
                {"durableEffects",
                 json{{"reports", std::move(reports)},
                      {"unsolvedLogs", json{{"path", "Unsolved Logs"}, {"exists", fs::exists(unsolved_logs)}}}}}};
}

/// Executes one scenario through the generated public CXX bridge.
json execute_scenario(const json& plan, const json& scenario) {
    const std::string invocation_id = plan.at("invocation").at("id").get<std::string>();
    const std::string scenario_id = scenario.at("id").get<std::string>();
    TemporaryDirectory temporary(invocation_id, scenario_id);
    const json& input = materialize_inputs(plan, scenario, temporary.path());
    RuntimeEnvironment environment(temporary.path());
    const auto request = build_request(input, temporary.path());
    const auto cancellation = scanner::scan_run_cancellation_new();
    const RecordingObserver observer(temporary.path());
    auto operation = scanner::scan_run_contract_execute(*request, *cancellation, &observer);
    const bool continuation_available = scanner::scan_run_contract_execution_has_continuation(*operation);
    const auto execution = scanner::scan_run_contract_execution_take_result(*operation);
    if (input.contains("continuationFlow") && !input.at("continuationFlow").is_null()) {
        if (!continuation_available) {
            throw RunnerError("continuationFlow initial result has no continuation");
        }
        const json initial = project_local_ignore_phase(execution, observer, temporary.path(), true, true);
        auto continuation = scanner::scan_run_contract_execution_take_continuation(*operation);
        const json& flow = input.at("continuationFlow");
        materialize_post_pause_data(plan, scenario, flow, temporary.path());

        const bool cancelled_before_terminal = scanner::scan_run_cancellation_is_cancelled(*cancellation);
        const RecordingObserver terminal_observer(temporary.path());
        auto terminal_operation =
            run_continuation_action(*continuation, flow.at("action"), *cancellation, &terminal_observer);
        const auto terminal_execution = scanner::scan_run_contract_execution_take_result(*terminal_operation);
        const bool cancelled_after_terminal = scanner::scan_run_cancellation_is_cancelled(*cancellation);
        const json terminal =
            project_local_ignore_phase(terminal_execution, terminal_observer, temporary.path(), false, false);

        json replays = json::array();
        for (const auto& action : flow.value("replays", json::array())) {
            auto replay_operation = run_continuation_action(*continuation, action, *cancellation, nullptr);
            const auto replay_execution = scanner::scan_run_contract_execution_take_result(*replay_operation);
            replays.push_back(project_replay(action, replay_execution));
        }
        return json{
            {"initial", initial},
            {"terminal", terminal},
            {"replays", std::move(replays)},
            {"cancellation", json{{"beforeTerminal", cancelled_before_terminal},
                                  {"afterTerminal", cancelled_after_terminal},
                                  {"afterReplays", scanner::scan_run_cancellation_is_cancelled(*cancellation)}}},
            {"durableEffects", project_local_ignore_effects(temporary.path(), input, terminal_execution.result)}};
    }
    if (input.value("observationProfile", "base") == "local-ignore") {
        return project_local_ignore_observation(execution, observer, temporary.path(), input, continuation_available);
    }
    return project_observation(execution, observer, temporary.path());
}

/// Executes one planned case while retaining runner failures as receipt evidence.
json scenario_receipt(const json& plan, const json& scenario) {
    try {
        return json{{"id", scenario.at("id")},
                    {"executionStatus", "completed"},
                    {"capabilityIds", scenario.at("capabilityIds")},
                    {"observation", execute_scenario(plan, scenario)},
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
    if (!plan.is_object() || plan.at("schemaVersion") != 1 || plan.at("familyId") != "crash-log-scan-run") {
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
