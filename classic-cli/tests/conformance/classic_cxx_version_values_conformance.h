// Public version value observations via generated CXX APIs.

/// Observe parsing and Fallout enum accessors without reconstructing domain decisions.
json execute_version_values_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end())
        throw RunnerError("undeclared version value fixture");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const auto fixture = json::parse(stream);
    const auto family = plan.at("familyId").get<std::string>();
    if (family == "game-version-parse") {
        const auto v = classic::version_registry::parse_game_version(fixture.at("request").at("version").get<std::string>());
        const auto legacy = classic::game::parse_game_version(fixture.at("request").at("version").get<std::string>());
        if (legacy.valid != v.valid || legacy.major != v.major || legacy.minor != v.minor || legacy.patch != v.patch || legacy.build != v.build)
            throw RunnerError("legacy and modern game-version parsers disagree");
        if (!v.valid) return json{{"parsed", nullptr}};
        return json{{"parsed", std::to_string(v.major) + "." + std::to_string(v.minor) + "." + std::to_string(v.patch) + "." + std::to_string(v.build)}};
    }
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(), scenario.at("id").get<std::string>());
    const auto path = temporary.path() / "CLASSIC Main.yaml";
    { std::ofstream output(path, std::ios::binary); output << fixture.at("registryYaml").get<std::string>(); if (!output) throw RunnerError("cannot write version configuration"); }
    using Version = classic::version_registry::Fallout4Version;
    json values = json::array();
    for (const auto v : {Version::Original, Version::NextGen, Version::AnniversaryEdition, Version::Vr}) {
        if (family == "fallout4-identity") values.push_back(json{{"isVr", classic::version_registry::fallout4_version_is_vr(v)}, {"exeName", std::string(classic::version_registry::fallout4_version_exe_name(v))}, {"steamAppId", classic::version_registry::fallout4_version_steam_app_id(v)}});
        else values.push_back(json{{"token", std::string(classic::version_registry::fallout4_version_as_str(v))}, {"docsName", std::string(classic::version_registry::fallout4_version_docs_folder_name(v))}, {"standard", classic::version_registry::fallout4_version_is_standard(v)}, {"registryId", std::string(classic::version_registry::fallout4_version_registry_id(v))}});
    }
    std::ifstream input(path, std::ios::binary);
    const std::string content{std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
    return json{{"variants", values}, {"files", json::array({json{{"path", "CLASSIC Main.yaml"}, {"content", content}}})}};
}
