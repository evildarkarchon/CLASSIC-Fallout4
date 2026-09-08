// SPDX-License-Identifier: MIT
// Public bridge observations from valid cached installation paths.

/// Traverse each public installation path surface using only fixture-owned inputs.
json execute_installation_paths_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    const auto game = fixture.at("gamePath").get<std::string>();
    const auto docs = fixture.at("docsPath").get<std::string>();
    if (!((game == "game" && docs == "docs") || (game == "Game Folder" && docs == "Docs Folder"))) {
        throw RunnerError("unsupported installation cache paths");
    }
    if (fixture.at("files") != json{{game + "/Fallout4.exe", "owned executable marker"}}) {
        throw RunnerError("installation fixture needs a valid cached executable");
    }
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(), scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    fs::create_directory(root / game); fs::create_directory(root / docs);
    {
        std::ofstream output(root / "CLASSIC Main.yaml", std::ios::binary);
        output << fixture.at("registryYaml").get<std::string>();
        output.close();
        // Failed metadata publication must stop before singleton initialization.
        if (!output) throw RunnerError("cannot write owned installation metadata");
    }
    {
        std::ofstream output(root / game / "Fallout4.exe", std::ios::binary);
        output << "owned executable marker";
        output.close();
        if (!output) throw RunnerError("cannot write owned installation executable");
    }
    // Registry-dependent Fallout4 aliases initialize inside the same controlled
    // cwd. Relative inputs exclude host parent names from document checks.
    VersionRegistryWorkingDirectory cwd(root);
    (void)classic::version_registry::version_registry_get_all_count();
    rust::Vec<rust::String> required;
    required.push_back(rust::String("Fallout4.exe"));
    classic::path::path_validate_required_files(game, rust::Slice<const rust::String>(required.data(), required.size()));
    classic::path::path_validate_is_directory(docs);
    const auto game_path = owned_string(classic::path::find_game_path("Fallout4.exe", "", "Fallout4", false, game, ""));
    if (owned_string(classic::game::find_game_path("Fallout4.exe", "", "Fallout4", false, game, "")) != game_path ||
        owned_string(classic::path::detect_fallout4_game_path(game, "OG")) != game_path) {
        throw RunnerError("public game path aliases disagree");
    }
    const auto docs_path = owned_string(classic::path::detect_fallout4_docs_path(docs, "OG"));
    json checks = json::array();
    for (const auto& message : classic::path::docs_checker_run_all_checks(docs, "Fallout4")) checks.push_back(owned_string(message));
    json directories = json::array();
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (entry.is_directory()) directories.push_back(entry.path().lexically_relative(root).generic_string());
    }
    std::sort(directories.begin(), directories.end());
    return json{{"gamePath", game_path}, {"docsPath", docs_path}, {"checks", checks},
                {"files", file_operation_files(root)}, {"directories", directories}};
}
