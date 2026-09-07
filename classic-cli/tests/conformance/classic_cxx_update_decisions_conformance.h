// SPDX-License-Identifier: MIT
// Valid strict-version decisions share the existing boolean bridge contract.

/// Compare fixture versions without fetching releases or consulting an installed app.
json execute_update_decisions_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    if (scenario.at("fixtureRefs") != json::array({reference})) throw RunnerError("undeclared update decision fixture");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    if (fixture.size() != 2 || !fixture.at("current").is_string() || !fixture.at("latest").is_string()) {
        throw RunnerError("unsupported update decision fixture");
    }
    return json{{"hasUpdate", classic::update::github_has_update(fixture.at("current").get<std::string>(),
        fixture.at("latest").get<std::string>())}, {"error", nullptr}};
}
