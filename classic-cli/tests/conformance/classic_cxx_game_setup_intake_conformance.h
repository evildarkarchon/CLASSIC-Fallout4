// SPDX-License-Identifier: MIT
/// Run the public settings-backed intake against fully explicit owned setup paths.
json execute_game_setup_intake_scenario(const json& plan, const json& scenario) {
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    if (std::find(scenario.at("fixtureRefs").begin(), scenario.at("fixtureRefs").end(), reference) ==
        scenario.at("fixtureRefs").end())
        throw RunnerError("undeclared setup fixture");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    if (fixture.at("operation") != "run")
        throw RunnerError("CXX intake has no primitive normalization export");
    for (const auto& [name, value] : fixture.at("files").items()) {
        const auto path = runtime_path(root, name, "setup fixture");
        fs::create_directories(path.parent_path());
        std::string content = value.get<std::string>();
        const auto replacement = root.generic_string();
        for (std::size_t at = 0; (at = content.find("<ROOT>", at)) != std::string::npos; at += replacement.size())
            content.replace(at, 6, replacement);
        std::ofstream output(path, std::ios::binary);
        output << content;
        if (!output)
            throw RunnerError("cannot write setup fixture");
    }
    const auto before = settings_tree_snapshot(root);
    const auto result = classic::scangame::run_game_setup_intake_from_user_settings(root.string(), "");
    const auto report = owned_string(result.rendered_report);
    json updates = json::array();
    for (const auto& update : result.path_updates)
        updates.push_back(json{{"kind", owned_string(update.kind)},
                               {"path", relative_path(root, fs::path(owned_string(update.path)))}});
    const auto after = settings_tree_snapshot(root);
    json files = json::array();
    for (const auto& [path, item] : after.items())
        if (item.at("kind") == "file")
            files.push_back(path);
    return json{{"status", owned_string(result.status)},
                {"hasErrors", result.has_errors},
                {"totalChecks", result.total_checks},
                {"failedChecks", result.failed_checks},
                {"actionCount", result.action_count},
                {"pathUpdateCount", result.path_update_count},
                {"pathUpdates", updates},
                {"gameRoot", relative_path(root, fs::path(owned_string(result.game_root)))},
                {"docsRoot", relative_path(root, fs::path(owned_string(result.docs_root)))},
                {"gameExecutable", relative_path(root, fs::path(owned_string(result.game_executable)))},
                {"reportFlags",
                 json{{"gameNamed", report.find("Game Setup Intake: Starfield") != std::string::npos},
                      {"metadataUnsupported", report.find("[unsupported] registry_metadata:") != std::string::npos},
                      {"versionWarning", report.find("[warning] executable_version:") != std::string::npos},
                      {"documentsPassed", report.find("[passed] documents_folder:") != std::string::npos},
                      {"loaderFailed", report.find("[failed] xse_loader:") != std::string::npos}}},
                {"files", files},
                {"unchanged", before == after}};
}
