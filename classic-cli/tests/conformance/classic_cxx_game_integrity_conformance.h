// SPDX-License-Identifier: MIT
/// Run the public aggregate integrity bridge over owned executable fixture bytes.
json execute_game_integrity_scenario(const json& plan, const json& scenario) {
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    if (std::find(scenario.at("fixtureRefs").begin(), scenario.at("fixtureRefs").end(), reference) ==
        scenario.at("fixtureRefs").end())
        throw RunnerError("integrity fixture not declared");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    for (const auto& [name, content] : fixture.at("files").items()) {
        const auto path = runtime_path(root, name, "integrity fixture");
        fs::create_directories(path.parent_path());
        std::ofstream output(path, std::ios::binary);
        output << content.get<std::string>();
        if (!output)
            throw RunnerError("cannot write integrity fixture");
    }
    if (!fixture.at("steamIni").is_null() || !fixture.at("rootWarn").is_null())
        throw RunnerError("CXX aggregate cannot accept optional integrity builders");
    rust::Vec<rust::String> hashes;
    for (const auto& hash : fixture.at("hashes"))
        hashes.push_back(hash.get<std::string>());
    const auto results = classic::scangame::integrity_run_all_checks(
        (root / fixture.at("exe").get<std::string>()).string(),
        rust::Slice<const rust::String>(hashes.data(), hashes.size()), fixture.at("rootName").get<std::string>());
    json checks = json::array();
    std::string report;
    for (const auto& result : results) {
        using T = classic::scangame::CheckType;
        std::string kind;
        if (result.check_type == T::ExecutableVersion)
            kind = "ExecutableVersion";
        else if (result.check_type == T::InstallationLocation)
            kind = "InstallationLocation";
        else
            throw RunnerError("unknown integrity check type");
        const auto message = owned_string(result.message);
        checks.push_back(json{{"isValid", result.is_valid}, {"message", message}, {"checkType", kind}});
        report += message;
    }
    std::map<std::string, json> ordered;
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (entry.is_symlink())
            throw RunnerError("unexpected integrity symlink");
        if (entry.is_regular_file()) {
            const auto content = read_optional_file(entry.path());
            if (!content)
                throw RunnerError("integrity fixture disappeared");
            const auto path = relative_path(root, entry.path());
            ordered[path] = json{{"path", path}, {"content", std::string(content->begin(), content->end())}};
        }
    }
    json files = json::array();
    for (const auto& [path, value] : ordered)
        files.push_back(value);
    return json{{"checks", checks}, {"report", report}, {"files", files}};
}
