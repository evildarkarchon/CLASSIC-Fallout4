// SPDX-License-Identifier: MIT
// Database pool observations use the generated bridge and owned SQLite input bytes.

namespace database_operations = classic::database;

/// Decode input bytes strictly so malformed transport never becomes database evidence.
std::vector<std::uint8_t> database_operations_decode_hex(const std::string& value) {
    if (value.size() % 2 != 0) throw RunnerError("database bytes require lowercase hex");
    std::vector<std::uint8_t> bytes;
    for (std::size_t index = 0; index < value.size(); index += 2) {
        const auto digit = [](char c) -> unsigned {
            if (c >= '0' && c <= '9') return static_cast<unsigned>(c - '0');
            if (c >= 'a' && c <= 'f') return static_cast<unsigned>(c - 'a' + 10);
            throw RunnerError("database bytes require lowercase hex");
        };
        bytes.push_back(static_cast<std::uint8_t>(digit(value[index]) * 16 + digit(value[index + 1])));
    }
    return bytes;
}

/// Observe every durable file after close, including unexpected database sidecars.
json database_operations_files(const fs::path& root) {
    json files = json::array();
    constexpr char digits[] = "0123456789abcdef";
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (entry.is_symlink()) throw RunnerError("unexpected link in database workspace");
        if (entry.is_directory()) continue;
        const auto bytes = read_optional_file(entry.path());
        if (!bytes) throw RunnerError("database workspace file disappeared");
        std::string hex;
        for (const auto byte : *bytes) { hex += digits[byte >> 4]; hex += digits[byte & 15]; }
        files.push_back(json{{"path", relative_path(root, entry.path())}, {"hex", hex}});
    }
    std::sort(files.begin(), files.end(), [](const json& a, const json& b) { return a.at("path") < b.at("path"); });
    return files;
}

/// Traverse typed hit flags so empty entries remain distinct from misses in native receipts.
json execute_database_operations_scenario(const json& plan, const json& scenario) {
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(), scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end()) throw RunnerError("database fixture is not declared by scenario");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const auto fixture = json::parse(stream);
    if (fixture.size() != 3 || fixture.at("operation") != "pool" || !fixture.contains("databaseHex") || !fixture.contains("queries")) throw RunnerError("unsupported database operation fixture");
    const auto path = root / "formids.db";
    if (!fixture.at("databaseHex").is_null()) {
        const auto bytes = database_operations_decode_hex(fixture.at("databaseHex").get<std::string>());
        std::ofstream output(path, std::ios::binary);
        output.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
        output.close();
        if (!output) throw RunnerError("cannot write database fixture");
    }
    rust::Vec<rust::String> formids, plugins, paths;
    if (!fixture.at("queries").is_array()) throw RunnerError("database queries require string pairs");
    for (const auto& pair : fixture.at("queries")) {
        if (!pair.is_array() || pair.size() != 2 || !pair.at(0).is_string() || !pair.at(1).is_string()) throw RunnerError("database queries require string pairs");
        formids.push_back(pair.at(0).get<std::string>());
        plugins.push_back(pair.at(1).get<std::string>());
    }
    paths.push_back(path.string());
    const rust::Slice<const rust::String> path_slice(paths.data(), paths.size());
    const rust::Slice<const rust::String> formid_slice(formids.data(), formids.size());
    const rust::Slice<const rust::String> plugin_slice(plugins.data(), plugins.size());
    auto pool = database_operations::db_pool_new("Fallout4", 1, 300);
    json observation{{"table", owned_string(database_operations::db_pool_game_table(*pool))}, {"initialAvailable", database_operations::db_pool_is_available(*pool)}, {"error", nullptr}, {"single", json::array()}, {"batch", json::array()}};
    try {
        try { database_operations::db_pool_initialize(*pool, path_slice); }
        catch (const rust::Error& failure) {
            // CXX exposes the core Display string, including its debug-quoted filesystem path.
            const std::string message(failure.what());
            const auto quoted = json(path.string()).dump();
            if (!message.starts_with("Failed to open database:") || message.find(quoted) == std::string::npos) throw;
            observation["error"] = json{{"code", "open"}, {"path", "formids.db"}};
        }
        observation["available"] = database_operations::db_pool_is_available(*pool);
        if (observation["error"].is_null()) {
            for (std::size_t index = 0; index < formids.size(); ++index) {
                const auto entry = database_operations::db_pool_get_entry_typed(*pool, formids[index], plugins[index]);
                if (entry.formid != formids[index] || entry.plugin != plugins[index] || (!entry.found && !entry.value.empty())) throw RunnerError("database single result violated typed presence or identity");
                const auto legacy = database_operations::db_pool_get_entry(*pool, formids[index], plugins[index]);
                if (legacy != entry.value) throw RunnerError("legacy database single result disagrees with typed value");
                observation["single"].push_back(entry.found ? json(owned_string(entry.value)) : json(nullptr));
            }
            const auto batch = database_operations::db_pool_get_entries_batch_typed(*pool, formid_slice, plugin_slice);
            if (batch.size() != formids.size()) throw RunnerError("database batch lost positional outcomes");
            json legacy_hits = json::object();
            for (const auto& raw : database_operations::db_pool_get_entries_batch(*pool, formid_slice, plugin_slice)) {
                const auto line = owned_string(raw);
                const auto separator = line.find('\t');
                if (separator == std::string::npos || legacy_hits.contains(line.substr(0, separator))) throw RunnerError("legacy database batch has malformed or duplicate keys");
                legacy_hits[line.substr(0, separator)] = line.substr(separator + 1);
            }
            json typed_hits = json::object();
            for (std::size_t index = 0; index < batch.size(); ++index) {
                const auto& entry = batch[index];
                if (entry.formid != formids[index] || entry.plugin != plugins[index] || (!entry.found && !entry.value.empty())) throw RunnerError("database batch violated typed presence or identity");
                if (entry.found) typed_hits[owned_string(entry.formid) + ":" + owned_string(entry.plugin)] = owned_string(entry.value);
                observation["batch"].push_back(entry.found ? json(owned_string(entry.value)) : json(nullptr));
            }
            if (legacy_hits != typed_hits) throw RunnerError("legacy database batch disagrees with typed hits or miss omission");
        }
        observation["cleared"] = database_operations::db_pool_clear_cache(*pool, false);
        observation["afterClear"] = database_operations::db_pool_clear_cache(*pool, false);
    } catch (...) {
        // Release SQLite handles before TemporaryDirectory cleans its Windows files.
        database_operations::db_pool_close(*pool);
        throw;
    }
    database_operations::db_pool_close(*pool);
    observation["closedAvailable"] = database_operations::db_pool_is_available(*pool);
    observation["closedCache"] = database_operations::db_pool_clear_cache(*pool, false);
    observation["files"] = database_operations_files(root);
    return observation;
}
