// PE version extraction transported through the generated CXX bridge.
//
// The URL, user-agent and mod-site operations left CXX with their bridge exports (#309), so
// only the version-pe family remains here; delete this header together with that family.

/// Keep PE fixture bytes in the invocation-owned temporary directory.
fs::path aux_pe_path(const fs::path& root, const std::string& path) {
    if (path.empty() || path.find_first_of("\\:") != std::string::npos || path.front() == '/' ||
        path.back() == '/' || path.find("//") != std::string::npos)
        throw RunnerError("invalid PE fixture path");
    for (const auto& part : fs::path(path))
        if (part == "." || part == "..") throw RunnerError("invalid PE fixture path");
    return root / path;
}

/// Execute PE version extraction from an input-only fixture.
json execute_aux_operations_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end())
        throw RunnerError("PE fixture is not declared by the scenario");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const auto fixture = json::parse(stream);
    const auto& request = fixture.at("request");
    if (request.value("operation", "") != "pe-extract") throw RunnerError("unsupported auxiliary operation");
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
