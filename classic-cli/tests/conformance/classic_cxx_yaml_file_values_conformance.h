// Source-owned YAML file kind values through the public CXX reader functions.

/// Read each bridged enum value and description from the actual Rust-backed API.
json execute_yaml_file_values_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    if (json::parse(stream) != json{{"request", json::object()}}) throw RunnerError("unsupported YAML file value request");
    json kinds = json::array();
    for (auto value : {classic::settings::YamlFile::Main, classic::settings::YamlFile::Ignore, classic::settings::YamlFile::Game, classic::settings::YamlFile::GameLocal, classic::settings::YamlFile::Test, classic::settings::YamlFile::Cache}) {
        kinds.push_back(json{{"token", owned_string(classic::settings::yaml_file_as_str(value))}, {"description", owned_string(classic::settings::yaml_file_description(value))}});
    }
    return json{{"kinds", kinds}};
}
