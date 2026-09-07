// SPDX-License-Identifier: MIT
// Inspect deterministic local XSE files through the public bridge.

/// Execute typed and string-form detection and preserve their absence sentinel.
json execute_xse_operations_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    if (scenario.at("fixtureRefs") != json::array({reference})) throw RunnerError("undeclared XSE fixture");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    if (fixture.size() != 1 || !fixture.at("files").is_array()) throw RunnerError("unsupported XSE fixture");
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(), scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    for (const auto& value : fixture.at("files")) {
        const auto name = value.get<std::string>();
        if (name != "f4se_loader.exe" && name != "f4se_1_10_163.dll") throw RunnerError("unsupported XSE filename");
        std::ofstream output(root / name, std::ios::binary);
        if (!output) throw RunnerError("cannot seed XSE fixture");
    }
    const auto kind = classic::xse::XseType::F4SE;
    const auto root_string = root.string();
    const auto loader = (root / "f4se_loader.exe").string();
    const auto version = owned_string(classic::xse::detect_xse_version(loader, kind));
    const bool installed = classic::xse::is_xse_installed(root_string, kind);
    if (version != owned_string(classic::xse::detect_xse_version_string(loader, "F4SE"))
        || installed != classic::xse::is_xse_installed_check(root_string, "F4SE")
        || version != owned_string(classic::game::detect_xse_version_string(loader, "F4SE"))
        || installed != classic::game::is_xse_installed_check(root_string, "F4SE")) {
        throw RunnerError("typed and string-form XSE operations disagree");
    }
    const auto info = classic::xse::xse_get_info(root_string, kind);
    json files = json::array();
    for (const auto& entry : fs::directory_iterator(root)) {
        files.push_back(json{{"path", entry.path().filename().string()}, {"hex", autoscan_bytes_hex(autoscan_file_bytes(entry.path()))}});
    }
    std::sort(files.begin(), files.end(), [](const json& left, const json& right) { return left.at("path") < right.at("path"); });
    return json{{"typeName", owned_string(info.xse_type)}, {"loaderName", owned_string(classic::xse::xse_get_loader_name(kind))},
        {"dllPrefix", owned_string(classic::xse::xse_get_dll_prefix(kind))}, {"installed", installed},
        {"version", version.empty() ? json(nullptr) : json(version)},
        {"info", {{"typeName", owned_string(info.xse_type)}, {"installed", info.installed},
                  {"version", info.version.empty() ? json(nullptr) : json(owned_string(info.version))}}}, {"files", files}};
}
