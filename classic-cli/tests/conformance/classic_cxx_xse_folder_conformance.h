// SPDX-License-Identifier: MIT
// Resolve XSE folders with isolated metadata and Local.yaml inputs.

/// Execute the public resolver and traverse its actual optional-path sentinel.
json execute_xse_folder_scenario(const json& plan, const json& scenario) {
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
