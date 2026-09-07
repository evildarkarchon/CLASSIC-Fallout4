// Generic settings cache loader transport, included inside the receipt runner namespace.

/// Clears the dedicated process cache on both successful and exceptional exits.
struct SettingsLoadReset {
    ~SettingsLoadReset() { classic::settings::settings_clear_cache(); }
};

/// Contains authored filenames before materializing settings input bytes.
fs::path settings_load_owned(const fs::path& root, const std::string& relative) {
    const fs::path path(relative);
    if (relative.empty() || path.is_absolute() || relative.find('\\') != std::string::npos || relative.find(':') != std::string::npos)
        throw RunnerError("settings fixture requires a contained relative path");
    for (const auto& part : path) if (part == "." || part == ".." || part.empty()) throw RunnerError("settings fixture path escapes");
    return root / path;
}

/// Projects only attributed core loader errors; unrelated native errors propagate.
json settings_load_error(const std::string& message, const fs::path& root, const std::vector<std::string>& paths) {
    for (const auto& [prefix, kind] : std::vector<std::pair<std::string, std::string>>{{"Failed to read file ", "io"}, {"Failed to parse YAML from ", "yaml-parse"}}) {
        for (const auto& relative : paths) {
            if (message.starts_with(prefix + settings_load_owned(root, relative).string() + ": "))
                return json{{"kind", kind}, {"path", relative}};
        }
    }
    throw RunnerError(message);
}

/// Exercises actual sync and async-blocking settings APIs and records cache/file effects.
json execute_settings_load_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end()) throw RunnerError("settings fixture is not declared");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const auto fixture = json::parse(stream);
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(), scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    SettingsLoadReset reset;
    for (const auto& [relative, content] : fixture.at("files").items()) {
        const auto path = settings_load_owned(root, relative); fs::create_directories(path.parent_path());
        std::ofstream output(path, std::ios::binary); output << content.get<std::string>();
        if (!output) throw RunnerError("cannot materialize settings input");
    }
    json observed = json::object();
    for (const std::string operation : {"sync", "async", "batchSync", "batchAsync"}) {
        classic::settings::settings_clear_cache();
        const bool batch = operation.starts_with("batch");
        const auto relatives = batch ? fixture.at("request").at("batch").get<std::vector<std::string>>() : std::vector<std::string>{fixture.at("request").at("single").get<std::string>()};
        std::vector<std::string> paths;
        for (const auto& relative : relatives) paths.push_back(settings_load_owned(root, relative).string());
        const auto keys = batch ? paths : std::vector<std::string>{"conformance.single"};
        json count = nullptr, error = nullptr;
        try {
            if (operation == "sync") count = classic::settings::settings_load_sync(keys[0], paths[0]);
            else if (operation == "async") count = classic::settings::settings_load_async_blocking(keys[0], paths[0]);
            else {
                rust::Vec<rust::String> native_paths;
                for (const auto& path : paths) native_paths.push_back(rust::String(path));
                count = operation == "batchSync" ? classic::settings::settings_load_batch_sync(std::move(native_paths)) : classic::settings::settings_load_batch_async_blocking(std::move(native_paths));
            }
        } catch (const rust::Error& failure) { error = settings_load_error(failure.what(), root, relatives); }
        json cached = json::array(), after_clear = json::array();
        for (const auto& key : keys) cached.push_back(classic::settings::settings_is_cached(key));
        classic::settings::settings_clear_cache();
        for (const auto& key : keys) after_clear.push_back(classic::settings::settings_is_cached(key));
        observed[operation] = json{{"count", count}, {"error", error}, {"cached", cached}, {"afterClear", after_clear}};
    }
    json files = json::object();
    for (const auto& entry : fs::recursive_directory_iterator(root)) if (entry.is_regular_file()) {
        std::ifstream input(entry.path(), std::ios::binary);
        files[fs::relative(entry.path(), root).generic_string()] = std::string(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
    }
    observed["files"] = files;
    return observed;
}
