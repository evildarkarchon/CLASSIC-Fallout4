// SPDX-License-Identifier: MIT
// Launch Crash Log Scans from isolated User Settings through the CXX scanner bridge.

/// Returns the pack's game token for the scanner-local bridge game identity.
std::string crash_log_scan_launch_game_token(classic::scanner::ScanRunGameId game) {
    switch (game) {
    case classic::scanner::ScanRunGameId::Fallout4:
        return "Fallout4";
    case classic::scanner::ScanRunGameId::Fallout4VR:
        return "Fallout4VR";
    case classic::scanner::ScanRunGameId::Skyrim:
        return "Skyrim";
    case classic::scanner::ScanRunGameId::Starfield:
        return "Starfield";
    }
    throw RunnerError("unsupported launched game");
}

/// Returns the pack's snake_case token for one launched Unsolved Logs intent.
std::string crash_log_scan_launch_unsolved_token(classic::scanner::ScanRunLaunchUnsolvedLogs value) {
    switch (value) {
    case classic::scanner::ScanRunLaunchUnsolvedLogs::LeaveInPlace:
        return "leave_in_place";
    case classic::scanner::ScanRunLaunchUnsolvedLogs::MoveToConfiguredOrDefault:
        return "move_to_configured_or_default";
    case classic::scanner::ScanRunLaunchUnsolvedLogs::MoveToCustom:
        return "move_to_custom";
    }
    throw RunnerError("unsupported launched Unsolved Logs intent");
}

/// Returns the pack's snake_case token for one launch diagnostic kind.
std::string crash_log_scan_launch_diagnostic_token(classic::scanner::ScanRunLaunchDiagnosticKind kind) {
    switch (kind) {
    case classic::scanner::ScanRunLaunchDiagnosticKind::UserSettings:
        return "user_settings";
    case classic::scanner::ScanRunLaunchDiagnosticKind::GameVersionNotApplied:
        return "game_version_not_applied";
    case classic::scanner::ScanRunLaunchDiagnosticKind::FcxModeNotApplied:
        return "fcx_mode_not_applied";
    case classic::scanner::ScanRunLaunchDiagnosticKind::CustomScanFolderNotApplied:
        return "custom_scan_folder_not_applied";
    case classic::scanner::ScanRunLaunchDiagnosticKind::SetupFoldersNotApplied:
        return "setup_folders_not_applied";
    }
    throw RunnerError("unsupported launch diagnostic kind");
}

/// Returns a presence-flagged bridge path relative to the Installation Root, or null.
json crash_log_scan_launch_optional_path(const fs::path& root, bool present, const rust::String& value) {
    return present ? json(relative_path(root, fs::path(owned_string(value)))) : json(nullptr);
}

/// Builds presence-flagged bridge overrides from the scenario's overrides.
classic::scanner::ScanRunLaunchOverridesDto crash_log_scan_launch_overrides(const fs::path& root, const json& value) {
    classic::scanner::ScanRunLaunchOverridesDto overrides{};
    if (value.contains("game")) {
        const auto game = value.at("game").get<std::string>();
        overrides.has_game = true;
        overrides.game = game == "Fallout4"     ? classic::scanner::ScanRunGameId::Fallout4
                         : game == "Fallout4VR" ? classic::scanner::ScanRunGameId::Fallout4VR
                         : game == "Skyrim"     ? classic::scanner::ScanRunGameId::Skyrim
                         : game == "Starfield"  ? classic::scanner::ScanRunGameId::Starfield
                                                : throw RunnerError("unsupported game override");
    }
    if (value.contains("gameVersion")) {
        overrides.has_game_version = true;
        overrides.game_version = value.at("gameVersion").get<std::string>();
    }
    if (value.contains("scanPath")) {
        overrides.has_scan_path = true;
        overrides.scan_path = runtime_path(root, value.at("scanPath"), "scanPath").string();
    }
    if (value.contains("maxConcurrent")) {
        overrides.has_max_concurrent = true;
        overrides.max_concurrent = value.at("maxConcurrent").get<std::size_t>();
    }
    overrides.show_formid_values = value.value("showFormidValues", false);
    overrides.simplify_logs = value.value("simplifyLogs", false);
    return overrides;
}

/// Traverses the bridge's launched-request view into the pack's observation shape.
json crash_log_scan_launch_request_view(const fs::path& root, const classic::scanner::ScanRunLaunchRequestDto& view) {
    const bool standard = view.intent == classic::scanner::ScanRunLaunchIntent::Standard;
    const auto& configuration = view.configuration;
    json formid_paths = json::array();
    for (const auto& path : configuration.formid_database_paths) {
        auto text = owned_string(path);
        std::replace(text.begin(), text.end(), '\\', '/');
        formid_paths.push_back(text);
    }
    json targeted = nullptr;
    if (!standard) {
        targeted = json::array();
        for (const auto& input : view.targeted_source.inputs) {
            targeted.push_back(relative_path(root, fs::path(owned_string(input))));
        }
    }
    return json{
        {"intent", standard ? "standard" : "targeted"},
        {"game", crash_log_scan_launch_game_token(configuration.game)},
        {"gameVersion", owned_string(configuration.game_version)},
        {"showFormidValues", configuration.show_formid_values},
        {"simplifyLogs", configuration.simplify_logs},
        {"formidDatabasePaths", formid_paths},
        {"unsolvedLogsDestination",
         crash_log_scan_launch_optional_path(root, configuration.has_configured_unsolved_logs_destination,
                                             configuration.configured_unsolved_logs_destination)},
        {"maxConcurrent", configuration.has_max_concurrent ? json(configuration.max_concurrent) : json(nullptr)},
        {"baseDirectory",
         standard ? json(relative_path(root, fs::path(owned_string(view.standard_source.base_directory))))
                  : json(nullptr)},
        {"customScanDirectory",
         standard ? crash_log_scan_launch_optional_path(root, view.standard_source.has_custom_scan_directory,
                                                        view.standard_source.custom_scan_directory)
                  : json(nullptr)},
        {"configuredDocumentsRoot",
         standard ? crash_log_scan_launch_optional_path(root, view.standard_source.has_configured_documents_root,
                                                        view.standard_source.configured_documents_root)
                  : json(nullptr)},
        {"unsolvedLogs", standard ? json(crash_log_scan_launch_unsolved_token(view.unsolved_logs)) : json(nullptr)},
        {"targetedInputs", targeted},
        {"fcxEnabled", view.fcx_enabled},
    };
}

/// Launches one scenario in a fresh Installation Root and observes the bridge's DTOs.
json execute_crash_log_scan_launch_scenario(const json& plan, const json& scenario) {
    const json& input = scenario.at("input");
    const auto reference = input.at("settingsFixtureRef").get<std::string>();
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    const fs::path settings = root / "CLASSIC Settings.yaml";
    fs::copy_file(fs::path(plan.at("fixtures").at(reference).get<std::string>()), settings);
    const auto before = autoscan_file_bytes(settings);
    const auto overrides = crash_log_scan_launch_overrides(root, input.at("overrides"));

    const auto intent = input.at("intent").get<std::string>();
    rust::Box<classic::scanner::ScanRunLaunch> launch = [&] {
        if (intent == "standard") {
            return classic::scanner::scan_run_launch_standard(root.string(), overrides);
        }
        if (intent != "targeted") {
            throw RunnerError("unsupported launch intent");
        }
        rust::Vec<rust::String> inputs;
        for (const auto& item : input.at("targetedInputs")) {
            inputs.push_back(runtime_path(root, item, "targetedInputs").string());
        }
        return classic::scanner::scan_run_launch_targeted(root.string(), inputs, overrides);
    }();

    const bool unchanged = autoscan_file_bytes(settings) == before;
    const auto error = classic::scanner::scan_run_launch_error(*launch);
    if (error.has_error) {
        if (error.kind != classic::scanner::ScanRunLaunchErrorKind::TargetedWithoutInputs) {
            throw RunnerError("unsupported launch error kind");
        }
        return json{{"outcome", "error"},
                    {"errorKind", "targeted_without_inputs"},
                    {"request", nullptr},
                    {"diagnostics", json::array()},
                    {"settingsUnchanged", unchanged}};
    }
    const auto view = classic::scanner::scan_run_launch_view(*launch);
    // Every launch must yield an executable copy; executing is the scan-run family's job.
    (void)classic::scanner::scan_run_launch_request(*launch);
    json diagnostics = json::array();
    for (const auto& diagnostic : view.diagnostics) {
        diagnostics.push_back(json{{"kind", crash_log_scan_launch_diagnostic_token(diagnostic.kind)},
                                   {"code", owned_string(diagnostic.code)}});
    }
    // The bridge renders one Display Content line per diagnostic; a mismatch would mean a
    // frontend showing these lines silently drops or invents a diagnostic.
    if (view.display_lines.size() != view.diagnostics.size()) {
        throw RunnerError("launch display lines do not match its diagnostics");
    }
    return json{{"outcome", "launched"},
                {"errorKind", nullptr},
                {"request", crash_log_scan_launch_request_view(root, view)},
                {"diagnostics", diagnostics},
                {"settingsUnchanged", unchanged}};
}
