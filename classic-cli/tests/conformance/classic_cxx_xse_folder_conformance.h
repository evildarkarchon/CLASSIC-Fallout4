// SPDX-License-Identifier: MIT
// Resolve XSE folders with isolated metadata and Local.yaml inputs.

json execute_xse_log_scenario(const json& plan, const json& scenario);

/// Execute the public resolver and traverse its actual optional-path sentinel.
json execute_xse_folder_scenario(const json& plan, const json& scenario) {
    if (scenario.at("action").get<std::string>() == "xse-folder.log") return execute_xse_log_scenario(plan, scenario);
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(), scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    const auto game = fixture.at("game").get<std::string>();
    if (game != "Fallout4" && game != "Fallout4VR" && game != "Unknown") throw RunnerError("unsupported XSE folder game");
    {
        std::ofstream output(root / "CLASSIC Main.yaml", std::ios::binary);
        output << fixture.at("registryYaml").get<std::string>();
        output.close();
        // An incomplete registry could send configured-path resolution into host discovery.
        if (!output) throw RunnerError("cannot seed controlled XSE registry");
    }
    if (!fixture.at("localYaml").is_null()) {
        std::ofstream output(root / ("CLASSIC " + game + " Local.yaml"), std::ios::binary);
        output << fixture.at("localYaml").get<std::string>();
        output.close();
        if (!output) throw RunnerError("cannot seed XSE Local.yaml");
    }
    {
        // The registry singleton must initialize before cwd leaves the owned root.
        VersionRegistryWorkingDirectory cwd(root);
        (void)classic::version_registry::version_registry_get_all_count();
    }
    auto folder = owned_string(classic::xse::resolve_xse_folder_for_scan(root.string(), game,
        fixture.at("selectedVersion").get<std::string>(), fixture.at("configuredDocs").get<std::string>()));
    std::replace(folder.begin(), folder.end(), '\\', '/');
    json files = json::array();
    for (const auto& entry : fs::directory_iterator(root)) {
        const auto bytes = autoscan_file_bytes(entry.path());
        files.push_back(json{{"path", entry.path().filename().string()}, {"content", std::string(bytes.begin(), bytes.end())}});
    }
    std::sort(files.begin(), files.end(), [](const json& a, const json& b) { return a.at("path") < b.at("path"); });
    return json{{"folder", folder.empty() ? json(nullptr) : json(folder)}, {"files", files}};
}

/// Locate the XSE log (`xse-folder.log`) against owned registry, Local.yaml and empty logs.
///
/// The resolver runs with the owned root as cwd so the relative fixture folders resolve inside
/// it and the returned log stays root-relative. The bridge's empty-string sentinel is absence;
/// only the core's "cannot inspect XSE log" `rust::Error` is the typed operational failure.
json execute_xse_log_scenario(const json& plan, const json& scenario) {
    static const std::set<std::string> controlled_log_files{
        "configured-docs/F4SE/f4se.log", "configured-docs/F4SE/f4sevr.log", "local-docs/F4SE/f4se.log",
        "explicit-xse/f4se.log"};
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(), scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    const auto game = fixture.at("game").get<std::string>();
    if (game != "Fallout4" && game != "Fallout4VR") throw RunnerError("unsupported XSE log game");
    {
        std::ofstream output(root / "CLASSIC Main.yaml", std::ios::binary);
        output << fixture.at("registryYaml").get<std::string>();
        output.close();
        if (!output) throw RunnerError("cannot seed controlled XSE registry");
    }
    if (!fixture.at("localYaml").is_null()) {
        std::ofstream output(root / ("CLASSIC " + game + " Local.yaml"), std::ios::binary);
        output << fixture.at("localYaml").get<std::string>();
        output.close();
        if (!output) throw RunnerError("cannot seed XSE Local.yaml");
    }
    for (const auto& file : fixture.at("logFiles")) {
        const auto relative = file.get<std::string>();
        if (!controlled_log_files.contains(relative)) throw RunnerError("uncontrolled XSE log file");
        const auto path = root / fs::path(relative);
        fs::create_directories(path.parent_path());
        std::ofstream output(path, std::ios::binary);
        output.close();
        if (!output) throw RunnerError("cannot seed XSE log");
    }
    // The registry singleton must initialize, and relative folders must resolve, inside the owned root.
    VersionRegistryWorkingDirectory cwd(root);
    (void)classic::version_registry::version_registry_get_all_count();
    try {
        auto log = owned_string(classic::xse::resolve_xse_log_for_scan(root.string(), game,
            fixture.at("selectedVersion").get<std::string>(), fixture.at("configuredDocs").get<std::string>()));
        std::replace(log.begin(), log.end(), '\\', '/');
        return json{{"log", log.empty() ? json(nullptr) : json(log)}, {"error", nullptr}};
    } catch (const rust::Error& error) {
        if (!std::string_view(error.what()).starts_with("cannot inspect XSE log ")) throw;
        return json{{"log", nullptr}, {"error", "inspect"}};
    }
}
