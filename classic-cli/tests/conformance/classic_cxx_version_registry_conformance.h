// SPDX-License-Identifier: MIT
// Fixture-seeded version metadata crosses both supported public CXX namespaces.

/// Restore process cwd before the temporary registry directory is destroyed.
class VersionRegistryWorkingDirectory final {
public:
    /// Change cwd only within the dedicated serial family participant process.
    explicit VersionRegistryWorkingDirectory(const fs::path& root) : previous_(fs::current_path()) {
        fs::current_path(root);
    }
    /// Avoid throwing during stack unwinding; failure terminates this isolated runner.
    ~VersionRegistryWorkingDirectory() {
        std::error_code error;
        fs::current_path(previous_, error);
        if (error) std::terminate();
    }
    VersionRegistryWorkingDirectory(const VersionRegistryWorkingDirectory&) = delete;
    VersionRegistryWorkingDirectory& operator=(const VersionRegistryWorkingDirectory&) = delete;
private:
    fs::path previous_;
};

/// Project both native metadata DTO types while retaining the found sentinel.
template <typename Info>
json version_registry_metadata(const Info& info) {
    if (!info.found) return nullptr;
    return json{{"id", owned_string(info.id)}, {"version", owned_string(info.version_string)},
                {"shortName", owned_string(info.short_name)}, {"game", owned_string(info.game)},
                {"docsName", owned_string(info.docs_name)}, {"steamId", info.steam_id}, {"isVr", info.is_vr}};
}

/// Distinguish parse failure sentinels from a completed match with no candidate.
template <typename Match>
json version_registry_match(const Match& matched) {
    std::string confidence = owned_string(matched.confidence);
    const auto message = owned_string(matched.message);
    if (confidence == "None") {
        if (matched.is_match || !matched.matched_id.empty() || !message.starts_with("Failed to parse version: Invalid version string:")) {
            throw RunnerError("invalid version registry parse-failure sentinel");
        }
        return json{{"result", nullptr}, {"error", {{"code", "invalid_version"}}}};
    }
    std::transform(confidence.begin(), confidence.end(), confidence.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    if (matched.is_match == matched.matched_id.empty()) throw RunnerError("invalid version registry match presence flag");
    return json{{"result", {{"matchedId", matched.is_match ? json(owned_string(matched.matched_id)) : json(nullptr)},
                              {"confidence", confidence}, {"message", message}}}, {"error", nullptr}};
}

/// Preserve all common crash-generator metadata and its empty missing sentinel.
template <typename Config>
json version_registry_crashgen(const Config& config) {
    if (config.version.empty()) return nullptr;
    return json{{"version", owned_string(config.version)}, {"name", owned_string(config.name)},
        {"acronym", owned_string(config.acronym)}, {"dllFile", owned_string(config.dll_file)},
        {"description", owned_string(config.description)}, {"downloadUrl", owned_string(config.download_url)}};
}

/// Preserve every public extender field and the native found flag.
template <typename Config>
json version_registry_xse(const Config& config) {
    if (!config.found) return nullptr;
    return json{{"acronym", owned_string(config.acronym)}, {"fullName", owned_string(config.full_name)},
        {"compatibleVersion", owned_string(config.compatible_version)}, {"loader", owned_string(config.loader)},
        {"fileCount", config.file_count}};
}

/// Execute promoted and legacy public operations and inventory all fixture bytes.
json execute_version_registry_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end()) {
        throw RunnerError("version registry fixture is not declared by scenario");
    }
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    const auto operation = fixture.at("operation").get<std::string>();
    if (fixture.size() != 3 || (operation != "lookup" && operation != "match" && operation != "enumerate" && operation != "crashgen" && operation != "xse")) {
        throw RunnerError("unsupported version registry fixture");
    }
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(), scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    std::ofstream output(root / "CLASSIC Main.yaml", std::ios::binary);
    output << fixture.at("registryYaml").get<std::string>();
    output.close();
    if (!output) throw RunnerError("cannot write version registry fixture");
    // OnceLock reads only on first public access. All family scenarios carry the
    // same source bytes and execute in a dedicated process, independent of user YAML.
    VersionRegistryWorkingDirectory working_directory(root);
    const auto& request = fixture.at("request");
    json observation;
    json legacy;
    if (operation == "enumerate") {
        json ids = json::array();
        json old_ids = json::array();
        for (const auto& id : classic::version_registry::version_registry_get_all_ids()) ids.push_back(owned_string(id));
        for (const auto& id : classic::game::version_registry_get_all_ids()) old_ids.push_back(owned_string(id));
        std::sort(ids.begin(), ids.end());
        std::sort(old_ids.begin(), old_ids.end());
        json filtered = json::array();
        for (const auto& info : classic::version_registry::version_registry_get_all_for_game(request.at("game").get<std::string>(), request.at("isVr").get<bool>())) filtered.push_back(owned_string(info.id));
        std::sort(filtered.begin(), filtered.end());
        observation = json{{"result", {{"ids", ids}, {"count", classic::version_registry::version_registry_get_all_count()}, {"filteredIds", filtered}}}, {"error", nullptr}};
        // The legacy namespace exposes enumeration/count, but no filtered query.
        legacy = json{{"result", {{"ids", old_ids}, {"count", classic::game::version_registry_get_all_count()}, {"filteredIds", filtered}}}, {"error", nullptr}};
    } else if (operation == "crashgen") {
        const auto id = request.at("id").get<std::string>();
        const auto version = request.at("version").get<std::string>();
        json configs = json::array();
        json old_configs = json::array();
        for (const auto& config : classic::version_registry::version_registry_get_crashgen_configs(id)) configs.push_back(version_registry_crashgen(config));
        for (const auto& config : classic::game::version_registry_get_crashgen_configs(id)) old_configs.push_back(version_registry_crashgen(config));
        observation = json{{"result", {{"configs", configs}, {"selected", version_registry_crashgen(classic::version_registry::version_registry_get_crashgen_config(id, version))}}}, {"error", nullptr}};
        legacy = json{{"result", {{"configs", old_configs}, {"selected", version_registry_crashgen(classic::game::version_registry_get_crashgen_config(id, version))}}}, {"error", nullptr}};
    } else if (operation == "xse") {
        const auto id = request.at("id").get<std::string>();
        observation = json{{"result", version_registry_xse(classic::version_registry::version_registry_get_xse_config(id))}, {"error", nullptr}};
        legacy = json{{"result", version_registry_xse(classic::game::version_registry_get_xse_config(id))}, {"error", nullptr}};
    } else if (operation == "lookup") {
        const auto id = request.at("id").get<std::string>();
        observation = json{{"result", version_registry_metadata(classic::version_registry::version_registry_get_by_id(id))}, {"error", nullptr}};
        legacy = json{{"result", version_registry_metadata(classic::game::version_registry_get_by_id(id))}, {"error", nullptr}};
    } else {
        const auto version = request.at("version").get<std::string>();
        const auto game = request.at("game").get<std::string>();
        const bool is_vr = request.at("isVr").get<bool>();
        observation = version_registry_match(classic::version_registry::version_registry_match_version(version, game, is_vr));
        legacy = version_registry_match(classic::game::version_registry_match_version(version, game, is_vr));
    }
    if (observation != legacy) throw RunnerError("legacy and promoted version registry operations disagree");
    json files = json::array();
    for (const auto& entry : fs::directory_iterator(root)) {
        if (entry.is_symlink() || !entry.is_regular_file()) throw RunnerError("unexpected non-file in version registry workspace");
        const auto bytes = read_optional_file(entry.path());
        if (!bytes) throw RunnerError("version registry fixture file disappeared");
        files.push_back(json{{"path", entry.path().filename().string()}, {"content", std::string(bytes->begin(), bytes->end())}});
    }
    std::sort(files.begin(), files.end(), [](const json& a, const json& b) { return a.at("path") < b.at("path"); });
    observation["files"] = std::move(files);
    return observation;
}
