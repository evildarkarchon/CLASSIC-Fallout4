// Public typed registry operations through the generated CXX bridge.

/// Exercise typed state, overwrite, unregister and clear in this isolated process.
json execute_registry_operations_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end())
        throw RunnerError("registry fixture is not declared by the scenario");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const auto request = json::parse(stream).at("request");
    classic::registry::registry_clear_all();
    const bool initial = classic::registry::registry_is_registered("conformance-string");
    classic::registry::registry_set_string("conformance-string", request.at("stringValue").get<std::string>());
    classic::registry::registry_set_bool("conformance-bool", request.at("boolValue").get<bool>());
    classic::registry::registry_set_i32("conformance-int", request.at("intValue").get<std::int32_t>());
    const json stored{{"stringValue", owned_string(classic::registry::registry_get_string("conformance-string"))},
                      {"boolValue", classic::registry::registry_get_bool("conformance-bool")},
                      {"intValue", classic::registry::registry_get_i32("conformance-int")}};
    classic::registry::registry_set_string("conformance-string", request.at("replacement").get<std::string>());
    const auto replacement = owned_string(classic::registry::registry_get_string("conformance-string"));
    classic::registry::registry_unregister("conformance-string");
    const bool removed = classic::registry::registry_is_registered("conformance-string");
    classic::registry::registry_clear_all();
    const bool cleared = classic::registry::registry_is_registered("conformance-bool") || classic::registry::registry_is_registered("conformance-int");
    return json{{"initiallyPresent", initial}, {"stored", stored}, {"replacement", replacement},
                {"afterRemovePresent", removed}, {"afterClearPresent", cleared}};
}
