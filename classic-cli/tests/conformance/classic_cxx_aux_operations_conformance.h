// Public URL operations transported through the generated CXX bridge.

/// Keep PE fixture bytes in the invocation-owned temporary directory.
fs::path aux_pe_path(const fs::path& root, const std::string& path) {
    if (path.empty() || path.find_first_of("\\:") != std::string::npos || path.front() == '/' ||
        path.back() == '/' || path.find("//") != std::string::npos)
        throw RunnerError("invalid PE fixture path");
    for (const auto& part : fs::path(path))
        if (part == "." || part == "..") throw RunnerError("invalid PE fixture path");
    return root / path;
}

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
    if (request.value("operation", "") == "pe-extract") {
        TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                     scenario.at("id").get<std::string>());
        const auto& root = temporary.path();
        for (const auto& [relative, hex_value] : fixture.at("files").items()) {
            const auto target = aux_pe_path(root, relative);
            fs::create_directories(target.parent_path());
            const auto hex = hex_value.get<std::string>();
            if (hex.size() % 2 != 0) throw RunnerError("invalid PE fixture hex");
            std::ofstream output(target, std::ios::binary);
            for (std::size_t i = 0; i < hex.size(); i += 2) {
                const auto pair = hex.substr(i, 2);
                if (pair.find_first_not_of("0123456789abcdef") != std::string::npos)
                    throw RunnerError("invalid PE fixture hex");
                output.put(static_cast<char>(std::stoul(pair, nullptr, 16)));
            }
            if (!output) throw RunnerError("cannot write PE fixture");
        }
        const auto target = aux_pe_path(root, request.at("path").get<std::string>());
        return json{{"peVersion", std::string(classic::game::extract_pe_version_string(target.generic_string()))}};
    }
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
