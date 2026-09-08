// Public typed registry operations through the generated CXX bridge.

/// Reset isolated registry state on exceptions as well as normal completion.
struct RegistryConformanceReset {
    ~RegistryConformanceReset() { classic::registry::registry_clear_all(); }
};

/// Observe convenience operations without replacing the bridge's actual values.
json execute_registry_accessor_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end())
        throw RunnerError("registry fixture is not declared by the scenario");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const auto request = json::parse(stream).at("request");
    classic::registry::registry_clear_all();
    const RegistryConformanceReset reset;
    if (plan.at("familyId") == "registry-game") {
        classic::registry::registry_set_game(request.at("game").get<std::string>());
        const auto game = owned_string(classic::registry::registry_get_game());
        classic::registry::registry_set_game(request.at("replacement").get<std::string>());
        const auto replacement = owned_string(classic::registry::registry_get_game());
        classic::registry::registry_clear_all();
        const auto key = classic::registry::registry_key_game();
        return json{{"key", owned_string(key)}, {"game", game}, {"replacement", replacement},
                    {"afterClearPresent", classic::registry::registry_is_registered(key)}};
    }
    if (plan.at("familyId") != "registry-gui") throw RunnerError("unknown registry accessor family");
    const auto key = classic::registry::registry_key_is_gui_mode();
    const bool initial = classic::registry::registry_is_gui_mode();
    classic::registry::registry_set_bool(key, true);
    const bool enabled = classic::registry::registry_is_gui_mode();
    classic::registry::registry_set_bool(key, false);
    const bool disabled = classic::registry::registry_is_gui_mode();
    classic::registry::registry_clear_all();
    return json{{"key", owned_string(key)}, {"default", initial}, {"enabled", enabled}, {"disabled", disabled},
                {"afterClear", classic::registry::registry_is_gui_mode()}};
}

/// Exercise typed state, overwrite, unregister and clear in this isolated process.
json execute_registry_operations_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end())
        throw RunnerError("registry fixture is not declared by the scenario");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const auto request = json::parse(stream).at("request");
    classic::registry::registry_clear_all();
    const RegistryConformanceReset reset;
    const bool initial = classic::registry::registry_is_registered("conformance-string");
    classic::registry::registry_set_string("conformance-string", request.at("stringValue").get<std::string>());
    classic::registry::registry_set_bool("conformance-bool", request.at("boolValue").get<bool>());
    classic::registry::registry_set_i32("conformance-int", request.at("intValue").get<std::int32_t>());
    const json stored{{"stringValue", owned_string(classic::registry::registry_get_string("conformance-string"))},
                      {"boolValue", classic::registry::registry_get_bool("conformance-bool")},
                      {"intValue", classic::registry::registry_get_i32("conformance-int")}};
    classic::registry::registry_set_string("conformance-string", request.at("replacement").get<std::string>());
    const auto replacement = owned_string(classic::registry::registry_get_string("conformance-string"));
    classic::registry::registry_set_string("gamevars_version", request.at("gameVersion").get<std::string>());
    const auto game_version = owned_string(classic::registry::registry_get_string("gamevars_version"));
    classic::registry::registry_unregister("conformance-string");
    const bool removed = classic::registry::registry_is_registered("conformance-string");
    classic::registry::registry_clear_all();
    const bool cleared = classic::registry::registry_is_registered("conformance-bool") || classic::registry::registry_is_registered("conformance-int");
    return json{{"initiallyPresent", initial}, {"stored", stored}, {"replacement", replacement},
                {"afterRemovePresent", removed}, {"afterClearPresent", cleared}, {"gameVersion", game_version}};
}
