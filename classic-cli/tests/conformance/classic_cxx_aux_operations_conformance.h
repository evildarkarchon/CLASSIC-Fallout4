// Public URL operations transported through the generated CXX bridge.

/// Preserve public Result errors without catching runner or fixture failures.
template <typename Operation>
json aux_web_result(Operation operation) {
    try {
        return json{{"value", std::string(operation())}, {"error", nullptr}};
    } catch (const rust::Error& failure) {
        return json{{"value", nullptr}, {"error", std::string(failure.what())}};
    }
}

/// Execute URL validation, domain extraction and composition from an input-only fixture.
json execute_aux_operations_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end())
        throw RunnerError("URL fixture is not declared by the scenario");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const auto fixture = json::parse(stream);
    const auto& request = fixture.at("request");
    const auto url = request.at("url").get<std::string>();
    const auto path = request.at("path").get<std::string>();
    std::vector<rust::String> keys;
    std::vector<rust::String> values;
    for (const auto& pair : request.at("params")) {
        keys.emplace_back(pair.at(0).get<std::string>());
        values.emplace_back(pair.at(1).get<std::string>());
    }
    return json{
        {"valid", classic::web::is_valid_url(url)},
        {"validated", aux_web_result([&] { return classic::web::validate_url_string(url); })},
        {"domain", aux_web_result([&] { return classic::web::extract_domain_string(url); })},
        {"joined", aux_web_result([&] { return classic::web::web_join_url(url, path); })},
        {"query", aux_web_result([&] { return classic::web::web_build_url_with_query(
            url, rust::Slice<const rust::String>(keys.data(), keys.size()),
            rust::Slice<const rust::String>(values.data(), values.size())); })}};
}
