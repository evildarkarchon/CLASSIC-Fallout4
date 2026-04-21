#include "yaml_update.h"

#include "rust/cxx.h"

#include "classic_cxx_bridge/message.h"
#include "classic_cxx_bridge/runtime.h"
#include "classic_cxx_bridge/settings.h"
#include "classic_cxx_bridge/update.h"

#include <fmt/core.h>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

#include <cstdint>
#include <filesystem>
#include <iostream>
#include <string>

namespace fs = std::filesystem;

// ── Constants ─────────────────────────────────────────────────────────
//
// Pages URL / tag prefix come from `docs/api/yaml-update-delivery.md`. The
// owner segment of the Pages URL matches the hard-coded owner/repo the Rust
// bridge passes to `GithubClient::new` (`cpp-bindings/classic-cpp-bridge/
// src/update.rs` line ~138). If the repo is ever renamed, update both
// places in the same change.

namespace {

constexpr const char* kYamlPagesUrl =
    "https://evildarkarchon.github.io/CLASSIC-Fallout4/yaml-data/manifest-latest.json";
constexpr const char* kYamlTagPrefix = "yaml-data-v";

// Tag discriminator constants — mirror `TAG_*` in
// `cpp-bindings/classic-cpp-bridge/src/update.rs`.
constexpr std::uint32_t kYamlTagDisabled = 0u;
constexpr std::uint32_t kYamlTagUpdateAvailable = 1u;
constexpr std::uint32_t kYamlTagUpToDate = 2u;
constexpr std::uint32_t kYamlTagUnknown = 3u;
constexpr std::uint32_t kYamlTagError = 4u;

// ── Data-root discovery ───────────────────────────────────────────────
//
// A trimmed variant of `find_data_root()` in scanner.cpp — we only need the
// path to the settings file. Duplicated here instead of pulled out of
// scanner.cpp because scanner.cpp is a heavier translation unit that also
// wires the thread pool; sharing a tiny helper is cheaper than a header
// dependency.

struct SettingsPaths {
    std::string data_root;
    std::string settings_file;
};

SettingsPaths resolve_settings_paths() {
    std::error_code ec;
    fs::path cwd = fs::current_path(ec);

    auto try_root = [&](const fs::path& candidate) -> SettingsPaths {
        const fs::path settings = candidate / "CLASSIC Settings.yaml";
        return {candidate.string(), settings.string()};
    };

#ifdef _WIN32
    wchar_t buf[MAX_PATH];
    const DWORD len = GetModuleFileNameW(nullptr, buf, MAX_PATH);
    if (len > 0 && len < MAX_PATH) {
        fs::path exe_dir = fs::path(buf).parent_path();
        if (fs::is_directory(exe_dir / "CLASSIC Data", ec)) {
            return try_root(exe_dir);
        }
    }
#endif

    if (fs::is_directory(cwd / "CLASSIC Data", ec)) {
        return try_root(cwd);
    }

    // Fall back to cwd; yaml_ops_load_file will fail loudly if missing.
    return try_root(cwd);
}

bool read_update_check_setting(const std::string& settings_path) {
    // Bridge pattern taken from mainwindow.cpp:858 — construct ops, load file,
    // read the boolean with a `true` default (matches `CLASSIC Main.yaml`
    // default for `Update Check`).
    //
    // Fail-closed on load/parse/permission failures: a user who has disabled
    // `CLASSIC_Settings.Update Check` must still have their opt-out honored
    // when the settings file is missing, unreadable, or malformed. Defaulting
    // to `true` on failure lets the YAML-update commands reach the network
    // against the user's expressed preference. Regression for the Codex
    // adversarial review finding "CLI falls back to enabled when the settings
    // file cannot be read".
    try {
        auto ops = classic::settings::yaml_ops_new();
        classic::settings::yaml_ops_load_file(*ops, settings_path);
        auto value =
            classic::settings::yaml_ops_get_setting_value(*ops, "CLASSIC_Settings.Update Check");
        if (value.value_type == "bool") {
            return value.value == "true";
        }
        // Key absent or non-bool: the merged-YAML loader resolves the
        // `CLASSIC Main.yaml` default (`true`) when the user's file doesn't
        // override. Preserve that here so a first-run user isn't silently
        // opted out of updates they never disabled.
        return true;
    } catch (const rust::Error& e) {
        fmt::print(stderr,
                   "Warning: could not read Update Check setting from {}: {}\n"
                   "Treating as disabled to honor any prior opt-out.\n",
                   settings_path, std::string(e.what()));
        return false;
    } catch (const std::exception& e) {
        fmt::print(stderr,
                   "Warning: could not read Update Check setting from {}: {}\n"
                   "Treating as disabled to honor any prior opt-out.\n",
                   settings_path, e.what());
        return false;
    }
}

// ── Schema-entry builder ──────────────────────────────────────────────
//
// Keep in sync with `business-logic/classic-config-core/src/client_schemas.rs`:
// both entries are `SchemaCompat::new(1, 0)`. The schema-version gate in
// tools/schema_version_gate.py enforces that the bundled YAML matches.
//
// `has_installed` is intentionally left at `false`. The Rust orchestrator
// (`check_yaml_update`) reads each installed file from the yaml-cache
// directory and extracts its `schema_version` header, so sending `false`
// here delegates that detection to Rust and guarantees all three bindings
// (C++ CLI, C++ GUI, Node, Python) converge on the same behavior.

rust::Vec<classic::update::YamlClientSchemaEntryDto> build_yaml_schema_entries() {
    rust::Vec<classic::update::YamlClientSchemaEntryDto> entries;

    classic::update::YamlClientSchemaEntryDto main{};
    main.name = "CLASSIC Main.yaml";
    main.accepted_major = 1u;
    main.accepted_minimum_minor = 0u;
    main.has_installed = false;
    entries.push_back(std::move(main));

    classic::update::YamlClientSchemaEntryDto fallout4{};
    fallout4.name = "CLASSIC Fallout4.yaml";
    fallout4.accepted_major = 1u;
    fallout4.accepted_minimum_minor = 0u;
    fallout4.has_installed = false;
    entries.push_back(std::move(fallout4));

    return entries;
}

// ── Runtime bootstrap ─────────────────────────────────────────────────
//
// Smaller than `run_scan`'s bootstrap: we don't need the registry wiring or
// log-startup framing — the YAML update flow doesn't touch per-game state.

bool init_runtime_for_yaml_update() {
    try {
        classic::message::init_logging();
        classic::runtime::init_runtime();
        return true;
    } catch (const rust::Error& e) {
        fmt::print(stderr, "Fatal: failed to initialize runtime: {}\n", std::string(e.what()));
        return false;
    }
}

// ── Status formatting ─────────────────────────────────────────────────

int report_status(const classic::update::YamlUpdateStatusDto& status) {
    switch (status.tag) {
    case kYamlTagDisabled:
        fmt::print("Data update check is disabled (CLASSIC_Settings.Update Check = false).\n"
                   "Enable it in CLASSIC Settings.yaml to receive data updates.\n");
        return 0;
    case kYamlTagUpdateAvailable: {
        fmt::print("Data update available in release {}.\n",
                   std::string(status.release_tag));
        fmt::print("Compatible files:\n");
        for (std::size_t i = 0; i < status.compatible_files.size(); ++i) {
            const auto& f = status.compatible_files[i];
            fmt::print("  - {} ({} bytes, schema {})\n", std::string(f.name),
                       f.size_bytes, std::string(f.schema_version));
        }
        if (!status.incompatible_files.empty()) {
            fmt::print("Incompatible files (skipped):\n");
            for (std::size_t i = 0; i < status.incompatible_files.size(); ++i) {
                const auto& f = status.incompatible_files[i];
                const std::string reason = (i < status.incompatible_reasons.size())
                                               ? std::string(status.incompatible_reasons[i])
                                               : std::string("(no reason reported)");
                fmt::print("  - {} ({})\n", std::string(f.name), reason);
            }
        }
        return 0;
    }
    case kYamlTagUpToDate:
        // Distinguish genuinely-in-sync from "newer feed exists but this
        // build cannot install any of it". The core status model carries
        // rejected files on UpToDate so the user can be told that a
        // CLASSIC upgrade (not a data refresh) is what unlocks the newer
        // data.
        if (status.incompatible_files.empty()) {
            fmt::print("Your data files are up to date (release {}).\n",
                       std::string(status.release_tag));
        } else {
            fmt::print("Your installed data files are current, but release {} advertises "
                       "{} file(s) this CLASSIC build cannot install. Upgrade CLASSIC to "
                       "consume the newer data.\n",
                       std::string(status.release_tag),
                       status.incompatible_files.size());
            fmt::print("Incompatible files (skipped):\n");
            for (std::size_t i = 0; i < status.incompatible_files.size(); ++i) {
                const auto& f = status.incompatible_files[i];
                const std::string reason = (i < status.incompatible_reasons.size())
                                               ? std::string(status.incompatible_reasons[i])
                                               : std::string("(no reason reported)");
                fmt::print("  - {} ({})\n", std::string(f.name), reason);
            }
        }
        return 0;
    case kYamlTagUnknown:
        fmt::print("Data update status unknown: {}\n",
                   std::string(status.unknown_reason));
        return 1;
    case kYamlTagError:
        fmt::print(stderr, "Data update check failed: {}\n",
                   std::string(status.error_message));
        return 1;
    default:
        fmt::print(stderr, "Data update check returned an unrecognised status (tag={}).\n",
                   status.tag);
        return 1;
    }
}

// ── User prompt (interactive apply) ───────────────────────────────────

bool confirm_apply_prompt() {
    std::cout << "Apply these updates? [y/N]: " << std::flush;
    std::string answer;
    if (!std::getline(std::cin, answer)) {
        return false;
    }
    return !answer.empty() && (answer[0] == 'y' || answer[0] == 'Y');
}

} // namespace

// ── Public entry points ───────────────────────────────────────────────

int run_check_yaml_updates(const CliArgs& /*args*/) {
    if (!init_runtime_for_yaml_update()) {
        return 2;
    }

    const auto paths = resolve_settings_paths();
    const bool enabled = read_update_check_setting(paths.settings_file);

    int exit_code;
    try {
        auto entries = build_yaml_schema_entries();
        // Empty `bundled_yaml_dir` keeps the bridge's `current_exe()`
        // fallback — correct for the native CLI binary that lives next to
        // `CLASSIC Data/`. See the bridge header for non-native cases.
        auto status = classic::update::yaml_check_update(
            kYamlPagesUrl, kYamlTagPrefix, entries, enabled, rust::Str(""));
        exit_code = report_status(status);
    } catch (const rust::Error& e) {
        fmt::print(stderr, "Data update check failed: {}\n", std::string(e.what()));
        exit_code = 1;
    } catch (const std::exception& e) {
        fmt::print(stderr, "Data update check failed: {}\n", e.what());
        exit_code = 1;
    }

    classic::runtime::shutdown_runtime();
    return exit_code;
}

int run_apply_yaml_updates(const CliArgs& /*args*/) {
    if (!init_runtime_for_yaml_update()) {
        return 2;
    }

    const auto paths = resolve_settings_paths();
    const bool enabled = read_update_check_setting(paths.settings_file);

    int exit_code = 0;
    try {
        auto entries = build_yaml_schema_entries();

        // Step 1: check (gated by enabled). Empty bundled dir = native-exe fallback.
        auto status = classic::update::yaml_check_update(
            kYamlPagesUrl, kYamlTagPrefix, entries, enabled, rust::Str(""));
        const int status_exit_code = report_status(status);

        if (status.tag != kYamlTagUpdateAvailable) {
            // A blocked or failed apply must surface as a failing exit code so
            // scripts can distinguish "already current" from "apply was not
            // allowed / could not proceed".
            classic::runtime::shutdown_runtime();
            return (status.tag == kYamlTagDisabled) ? 1 : status_exit_code;
        }

        // Step 2: confirm with the user.
        if (!confirm_apply_prompt()) {
            fmt::print("Apply cancelled.\n");
            classic::runtime::shutdown_runtime();
            return 1;
        }

        // Step 3: apply the reviewed decision.
        //
        // We pass the exact release_tag + per-file `(name, sha256)` pairs the
        // user just confirmed via `report_status`. The bridge re-checks that
        // identity against the live manifest and refuses to install if the
        // publisher rotated to a different release or replaced an approved
        // asset in place.
        rust::Vec<rust::String> approved_file_names;
        rust::Vec<rust::String> approved_file_sha256;
        approved_file_names.reserve(status.compatible_files.size());
        approved_file_sha256.reserve(status.compatible_files.size());
        for (const auto& f : status.compatible_files) {
            approved_file_names.push_back(f.name);
            approved_file_sha256.push_back(f.sha256);
        }

        classic::update::ApprovedUpdateDto approved{};
        approved.release_tag = status.release_tag;
        approved.file_names = std::move(approved_file_names);
        approved.file_sha256 = std::move(approved_file_sha256);

        classic::update::YamlApplyRequestDto request{};
        request.pages_url = kYamlPagesUrl;
        request.tag_prefix = kYamlTagPrefix;
        request.entries = std::move(entries);
        request.enabled = enabled;
        request.approved = std::move(approved);
        request.bundled_yaml_dir = rust::String("");

        auto report = classic::update::yaml_apply_update(request);

        const auto installed = report.installed.size();
        const auto failed = report.failed.size();

        for (std::size_t i = 0; i < installed; ++i) {
            const auto& f = report.installed[i];
            fmt::print("Installed: {} (schema {}{})\n", std::string(f.name),
                       std::string(f.schema_version),
                       f.created_prev ? ", previous version retained" : "");
        }
        for (std::size_t i = 0; i < failed; ++i) {
            const auto& f = report.failed[i];
            fmt::print(stderr, "Failed: {} ({})\n", std::string(f.name),
                       std::string(f.failure_reason));
        }

        if (!std::string(report.error_message).empty()) {
            fmt::print(stderr, "Apply reported error: {}\n", std::string(report.error_message));
        }

        fmt::print("\nApply Complete\n");
        fmt::print("  Installed: {}\n", installed);
        fmt::print("  Failed:    {}\n", failed);

        exit_code = (failed == 0u && installed > 0u) ? 0 : 1;
    } catch (const rust::Error& e) {
        fmt::print(stderr, "Apply failed: {}\n", std::string(e.what()));
        exit_code = 1;
    } catch (const std::exception& e) {
        fmt::print(stderr, "Apply failed: {}\n", e.what());
        exit_code = 1;
    }

    classic::runtime::shutdown_runtime();
    return exit_code;
}
