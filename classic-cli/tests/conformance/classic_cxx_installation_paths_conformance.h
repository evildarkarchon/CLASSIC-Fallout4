// SPDX-License-Identifier: MIT
// Public bridge observation of Installation Root discovery.

/// Locate the Installation Root inside an owned tree and prove the search wrote nothing.
/// The fixed search starts keep every derived candidate (parent, grandparent, both `install`
/// folders) inside the temporary root, so no host folder can satisfy the lookup.
json execute_installation_root_scenario(const json& plan, const json& scenario, const json& fixture) {
    if (fixture.at("operation") != "locate" || fixture.at("executableDir") != "tree/build/bin" ||
        fixture.at("workingDir") != "tree/work" || !fixture.at("classicDataIn").is_array()) {
        throw RunnerError("unsupported installation root fixture");
    }
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(), scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    const auto executable_dir = root / fs::path(fixture.at("executableDir").get<std::string>());
    const auto working_dir = root / fs::path(fixture.at("workingDir").get<std::string>());
    fs::create_directories(executable_dir);
    fs::create_directories(working_dir);
    for (const auto& location : fixture.at("classicDataIn")) {
        fs::create_directories(root / fs::path(location.get<std::string>()) / "CLASSIC Data");
    }
    const auto located = owned_string(classic::config::locate_installation_root(executable_dir.string(), working_dir.string()));
    // The bridge reports "no Installation Root" as an empty string; the observation uses null.
    const json installation_root = located.empty() ? json(nullptr) : json(fs::path(located).lexically_relative(root).generic_string());
    json directories = json::array();
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (!entry.is_directory()) throw RunnerError("the Installation Root search wrote a file");
        directories.push_back(entry.path().lexically_relative(root).generic_string());
    }
    std::sort(directories.begin(), directories.end());
    return json{{"installationRoot", installation_root}, {"directories", directories}};
}

/// Dispatch installation-path scenarios; only `installation-paths.locate` still runs on CXX.
///
/// The cached-path inspection (`installation-paths.inspect`) left CXX with the path
/// detection and validation exports it called (#309); Rust keeps that evidence.
json execute_installation_paths_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    if (scenario.at("action") != "installation-paths.locate") {
        throw RunnerError("unsupported installation-paths action");
    }
    return execute_installation_root_scenario(plan, scenario, fixture);
}
