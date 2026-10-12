// SPDX-License-Identifier: MIT
// Game Local path persistence observations traverse the public generated bridge.

namespace config_operations = classic::config;

/// Re-read every durable file after native execution, preserving exact UTF-8 bytes.
json config_operations_files(const fs::path& root) {
    json result = json::array();
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (entry.is_symlink())
            throw RunnerError("unexpected link in config workspace");
        if (entry.is_directory())
            continue;
        const auto bytes = read_optional_file(entry.path());
        if (!bytes)
            throw RunnerError("config workspace file disappeared during observation");
        result.push_back(
            json{{"path", relative_path(root, entry.path())}, {"content", std::string(bytes->begin(), bytes->end())}});
    }
    std::sort(result.begin(), result.end(), [](const json& a, const json& b) { return a.at("path") < b.at("path"); });
    return result;
}

/// Execute one fixture-selected Game Local path persistence and re-read the workspace.
///
/// Only `persist-local` reaches CXX: the explicit-load and main-version operations
/// have no production bridge caller, so those scenarios are Rust-only.
json execute_config_operations_scenario(const json& plan, const json& scenario) {
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const fs::path& root = temporary.path();
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end()) {
        throw RunnerError("config operation fixture is not declared by scenario");
    }
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    if (fixture.at("operation") != "persist-local" || fixture.size() != 4) {
        throw RunnerError("unsupported config operation fixture");
    }
    for (const auto& [name, content] : fixture.at("files").items()) {
        if ((name != "local.yaml" && name != "CLASSIC Settings.yaml") || !content.is_string()) {
            throw RunnerError("config fixture requires owned YAML filenames and UTF-8 text");
        }
        std::ofstream output(root / name, std::ios::binary);
        output << content.get<std::string>();
        output.close();
        if (!output)
            throw RunnerError("cannot write config fixture file");
    }
    config_operations::save_local_yaml_paths(
        (root / "local.yaml").string(),
        fixture.at("gameRoot").is_null() ? "" : fixture.at("gameRoot").get<std::string>(),
        fixture.at("docsRoot").is_null() ? "" : fixture.at("docsRoot").get<std::string>());
    return json{{"result", nullptr}, {"error", nullptr}, {"files", config_operations_files(root)}};
}

