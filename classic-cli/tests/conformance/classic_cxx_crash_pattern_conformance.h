// Separate canonical tokens from the preserved legacy main-error text contract.
namespace {

/// Executes the exact planned public bridge operation on authored input content.
json execute_crash_pattern(const json& plan,const json& scenario){
    const auto reference=scenario.at("input").at("fixtureRef").get<std::string>();const auto& refs=scenario.at("fixtureRefs");
    if(std::find(refs.begin(),refs.end(),reference)==refs.end())throw RunnerError("undeclared crash-pattern fixture");
    std::ifstream input(plan.at("fixtures").at(reference).get<std::string>(),std::ios::binary);const auto fixture=json::parse(input);
    const auto content=fixture.at("content").get<std::string>();
    if(scenario.at("action")=="crash-pattern.vr" && fixture.at("operation")=="vr")return json{{"vr",scanner::detect_vr_log(content)}};
    if(scenario.at("action")=="crash-pattern.classify" && fixture.at("operation")=="classify"){
        const auto token=owned_string(scanner::classify_crash_pattern(content));
        return json{{"token",token.empty()?json(nullptr):json(token)}};
    }
    if(scenario.at("action")=="crash-pattern.legacy" && fixture.at("operation")=="legacy")return json{{"mainError",owned_string(scanner::detect_crash_pattern(content))}};
    throw RunnerError("unknown crash-pattern action");
}
}
