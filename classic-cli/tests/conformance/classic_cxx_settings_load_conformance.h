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

/// Retains counters and bounded storage without platform-specific capacity.
json settings_load_statistics() {
    const auto stats = classic::settings::settings_cache_stats();
    const auto alias = classic::config::settings_cache_stats();
    if (stats.hits != alias.hits || stats.misses != alias.misses || stats.size != classic::config::settings_cache_size()) throw RunnerError("settings cache aliases disagree");
    return json{{"hits", stats.hits}, {"misses", stats.misses}, {"hitRateZero", stats.hit_rate == 0.0}, {"size", stats.size}, {"bounded", stats.capacity > 0}};
}

/// Projects CXX typed YAML values, using the vector accessor for sequence values.
json settings_yaml_value(const classic::settings::YamlOps& ops, const std::string& key) {
    const auto value = classic::settings::yaml_ops_get_setting_value(ops, key);
    const std::string type(value.value_type), text(value.value);
    if (value.is_null) return nullptr;
    if (type == "string") return text;
    if (type == "bool") return text == "true";
    if (type == "integer") return std::stoll(text);
    if (type == "complex") {
        json result = json::array();
        for (const auto& item : classic::settings::yaml_ops_get_vec(ops, key)) result.push_back(std::string(item));
        return result;
    }
    throw RunnerError("unexpected YAML value type");
}

/// Clears scenario-owned YAML cache state before the referenced handle is destroyed.
struct SettingsYamlReset {
    const classic::settings::YamlOps& ops;
    ~SettingsYamlReset() { classic::settings::yaml_ops_clear_cache(ops); }
};

/// Exercises public YAML handles with typed updates and scenario-owned persistence.
json execute_settings_yaml(const json& fixture, const fs::path& root) {
    auto ops = classic::settings::yaml_ops_new();
    SettingsYamlReset reset{*ops};
    if (classic::settings::yaml_ops_has_document(*ops)) throw RunnerError("new YAML handle unexpectedly populated");
    classic::settings::yaml_ops_clear_cache(*ops);
    classic::settings::yaml_ops_parse(*ops, fixture.at("content").get<std::string>());
    if (!classic::settings::yaml_ops_has_document(*ops)) throw RunnerError("parsed YAML handle is empty");
    json items = json::array();
    for (const auto& item : classic::settings::yaml_ops_get_vec(*ops, "items")) items.push_back(std::string(item));
    const json before{{"name", std::string(classic::settings::yaml_ops_get_string(*ops, "name", "fallback"))}, {"missing", std::string(classic::settings::yaml_ops_get_string(*ops, "absent", "fallback"))}, {"items", items}, {"mapping", {{"left", std::string(classic::settings::yaml_ops_get_string(*ops, "mapping.left", ""))}, {"right", std::string(classic::settings::yaml_ops_get_string(*ops, "mapping.right", ""))}}}};
    for (const auto& key : fixture.at("updateOrder").get<std::vector<std::string>>()) {
        const auto& value = fixture.at("updates").at(key);
        if (value.is_boolean()) classic::settings::yaml_ops_set_bool_setting(*ops, key, value.get<bool>());
        else if (value.is_number_integer()) classic::settings::yaml_ops_set_integer_setting(*ops, key, value.get<std::int64_t>());
        else if (value.is_string()) classic::settings::yaml_ops_set_string_setting(*ops, key, value.get<std::string>());
        else {
            rust::Vec<rust::String> values;
            for (const auto& item : value) values.push_back(rust::String(item.get<std::string>()));
            classic::settings::yaml_ops_set_vec_setting(*ops, key, std::move(values));
        }
    }
    const std::string dumped(classic::settings::yaml_ops_dump(*ops));
    classic::settings::yaml_ops_parse(*ops, dumped);
    json after = json::object();
    for (const auto& [key, value] : fixture.at("updates").items()) after[key] = settings_yaml_value(*ops, key);
    const auto path = root / "saved.yaml";
    classic::settings::yaml_ops_save_file(*ops, path.string());
    const auto initial = classic::settings::yaml_ops_cache_stats(*ops);
    classic::settings::yaml_ops_load_file(*ops, path.string());
    classic::settings::yaml_ops_load_file(*ops, path.string());
    const auto stats = classic::settings::yaml_ops_cache_stats(*ops);
    json persisted = json::object(), files = json::object();
    for (const auto& [key, value] : fixture.at("updates").items()) persisted[key] = settings_yaml_value(*ops, key);
    for (const auto& entry : fs::directory_iterator(root)) if (entry.is_regular_file()) {
        std::ifstream input(entry.path(), std::ios::binary);
        files[entry.path().filename().string()] = std::string(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
    }
    classic::settings::yaml_ops_clear_cache(*ops);
    return json{{"before", before}, {"after", after}, {"persisted", persisted}, {"files", files}, {"cache", {{"hits", stats.hits - initial.hits}, {"misses", stats.misses - initial.misses}, {"size", stats.size}, {"afterClear", classic::settings::yaml_ops_cache_size(*ops)}}}};
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
    if (fixture.value("kind", "") == "yaml") return execute_settings_yaml(fixture, root);
    SettingsLoadReset reset;
    for (const auto& [relative, content] : fixture.at("files").items()) {
        const auto path = settings_load_owned(root, relative); fs::create_directories(path.parent_path());
        std::ofstream output(path, std::ios::binary); output << content.get<std::string>();
        if (!output) throw RunnerError("cannot materialize settings input");
    }
    classic::settings::settings_reset_cache_stats();
    classic::config::reset_settings_cache_stats();
    auto yaml_cache = classic::settings::yaml_ops_new();
    classic::settings::yaml_ops_clear_cache(*yaml_cache);
    if (classic::settings::yaml_ops_cache_size(*yaml_cache) != 0) throw RunnerError("YAML cache clear failed");
    json observed = json::object();
    for (const std::string operation : {"sync", "async", "batchSync", "batchAsync"}) {
        classic::settings::settings_clear_cache();
        classic::config::settings_cache_clear();
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
        std::vector<std::string> normalized_keys;
        for (const auto& key : classic::settings::settings_cache_keys()) normalized_keys.push_back(batch ? fs::relative(fs::path(std::string(key)), root).generic_string() : std::string(key));
        std::sort(normalized_keys.begin(), normalized_keys.end());
        const auto size = classic::settings::settings_cache_size();
        const auto stats = settings_load_statistics();
        json invalidated = json::array(), invalidated_again = json::array();
        for (const auto& key : keys) invalidated.push_back(classic::settings::settings_invalidate(key));
        for (const auto& key : keys) invalidated_again.push_back(classic::settings::settings_invalidate(key));
        const auto after_invalidate = classic::settings::settings_cache_size();
        classic::settings::settings_reset_cache_stats();
        const json cache_state{{"keys", normalized_keys}, {"size", size}, {"stats", stats}, {"invalidated", invalidated}, {"invalidatedAgain", invalidated_again}, {"afterInvalidate", after_invalidate}, {"resetStats", settings_load_statistics()}};
        // Refill entries so clear is checked independently of invalidation.
        for (std::size_t index = 0; index < keys.size(); ++index) if (cached[index].get<bool>()) classic::settings::settings_load_sync(keys[index], paths[index]);
        classic::config::settings_cache_clear();
        for (const auto& key : keys) if (classic::settings::settings_is_cached(key)) throw RunnerError("config cache clear alias retained an entry");
        for (std::size_t index = 0; index < keys.size(); ++index) if (cached[index].get<bool>()) classic::settings::settings_load_sync(keys[index], paths[index]);
        classic::settings::settings_clear_cache();
        for (const auto& key : keys) after_clear.push_back(classic::settings::settings_is_cached(key));
        observed[operation] = json{{"count", count}, {"error", error}, {"cached", cached}, {"afterClear", after_clear}, {"cacheState", cache_state}};
    }
    json files = json::object();
    for (const auto& entry : fs::recursive_directory_iterator(root)) if (entry.is_regular_file()) {
        std::ifstream input(entry.path(), std::ios::binary);
        files[fs::relative(entry.path(), root).generic_string()] = std::string(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
    }
    observed["files"] = files;
    return observed;
}
