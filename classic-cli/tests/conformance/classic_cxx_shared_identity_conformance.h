// Stable shared-core GameId transport, included in runner namespace.

/// Reads shared GameId tokens through the public bridge.
json execute_shared_identity_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end())
        throw RunnerError("shared identity fixture is not declared");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const auto fixture = json::parse(stream);
    const auto family = plan.at("familyId").get<std::string>();
    if (fixture != json{{"request", json::object()}})
        throw RunnerError("unsupported shared identity request");
    if (family == "game-identity") {
        json tokens = json::array();
        for (const auto game : {classic::shared::GameId::Fallout4, classic::shared::GameId::Fallout4VR,
                                classic::shared::GameId::Skyrim, classic::shared::GameId::Starfield})
            tokens.push_back(std::string(classic::shared::game_id_as_str(game)));
        return json{{"tokens", tokens}};
    }
    throw RunnerError("unsupported shared identity family");
}
