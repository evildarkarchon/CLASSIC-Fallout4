// SPDX-License-Identifier: MIT
// Native DTO traversal for the FormID lookup family, included inside the runner namespace.
//
// The focused scanner analyzer families left CXX with their bridge exports (#309). What
// remains is formid-lookup and `semantic_string_values`, which the ba2-scan and
// crashgen-check runners still use; delete each piece together with its last caller.

/// Projects a bridge-owned string vector without relying on Rust JSON serialization.
json semantic_string_values(const rust::Vec<rust::String>& values) {
    json result = json::array();
    for (const auto& value : values)
        result.push_back(owned_string(value));
    return result;
}

/// Preserves the authoritative presence bit for a nullable bridge string.
json semantic_optional(bool present, const rust::String& value) {
    return present ? json(owned_string(value)) : json(nullptr);
}

/// Preserves the strict lookup error code and optional input-key context.
json semantic_lookup_error(const classic::database::FormIdValueLookupErrorDto& error) {
    namespace database = classic::database;
    std::string code;
    switch (error.code) {
    case database::FormIdValueLookupErrorCode::MalformedResult:
        code = "malformed_result";
        break;
    case database::FormIdValueLookupErrorCode::OperationalFailure:
        code = "operational_failure";
        break;
    default:
        throw RunnerError("unknown lookup error");
    }
    return json{{"analyzerKind", nullptr},
                {"result", nullptr},
                {"error", json{{"analyzerKind", nullptr},
                               {"code", code},
                               {"message", owned_string(error.message)},
                               {"formid", semantic_optional(error.has_formid, error.formid)},
                               {"plugin", semantic_optional(error.has_plugin, error.plugin)}}}};
}

/// Traverses the public outcome and verifies its returned key matches the requested position.
json semantic_lookup_outcome(const classic::database::FormIdValueLookupOutcomeDto& value, const json& request) {
    namespace database = classic::database;
    std::string kind;
    switch (value.kind) {
    case database::FormIdValueLookupOutcomeKind::Disabled:
        kind = "disabled";
        break;
    case database::FormIdValueLookupOutcomeKind::Missing:
        kind = "missing";
        break;
    case database::FormIdValueLookupOutcomeKind::Found:
        kind = "found";
        break;
    default:
        throw RunnerError("unknown lookup outcome");
    }
    if (owned_string(value.formid) != request.at("formid").get<std::string>() ||
        owned_string(value.plugin) != request.at("plugin").get<std::string>())
        throw RunnerError("lookup outcome key changed");
    return json{{"kind", kind}, {"value", kind == "found" ? json(owned_string(value.value)) : json(nullptr)}};
}

/// Executes a fixture against one reusable native lookup handle, including optional warmup.
json execute_semantic_fixture(const std::string& family, const json& fixture) {
    const auto& c = fixture.at("configuration");
    const auto& request = fixture.at("request");
    if (family == "formid-lookup") {
        namespace database = classic::database;
        const auto lookup = [&]() {
            if (c.at("mode") == "disabled")
                return database::formid_value_lookup_disabled_new();
            if (c.at("mode") == "sqlite-missing")
                return database::formid_value_lookup_sqlite_new(c.at("databasePath").get<std::string>(),
                                                                c.at("gameTable").get<std::string>());
            if (c.at("mode") == "shared-pool") {
                const auto pool = database::db_pool_new(c.at("gameTable").get<std::string>(), 1, 60);
                return database::formid_value_lookup_shared_pool_new(*pool);
            }
            if (c.at("mode") != "in-memory")
                throw RunnerError("unsupported lookup mode");
            database::FormIdValueLookupInMemoryConfigurationDto config{};
            for (const auto& v : c.at("entries")) {
                database::FormIdValueLookupInMemoryEntryDto entry{};
                entry.formid = v.at("formid").get<std::string>();
                entry.plugin = v.at("plugin").get<std::string>();
                if (!v.at("operationalFailure").is_null()) {
                    entry.reply_kind = database::FormIdValueLookupReplyKind::OperationalFailure;
                    entry.error_message = v.at("operationalFailure").get<std::string>();
                } else if (v.at("value").is_null())
                    entry.reply_kind = database::FormIdValueLookupReplyKind::Missing;
                else {
                    entry.reply_kind = database::FormIdValueLookupReplyKind::Found;
                    entry.value = v.at("value").get<std::string>();
                }
                config.entries.push_back(std::move(entry));
            }
            return database::formid_value_lookup_in_memory_new(std::move(config));
        }();
        const auto status = database::formid_value_lookup_construction_result(*lookup);
        if (status.has_lookup == status.has_error)
            throw RunnerError("invalid lookup constructor presence flags");
        if (status.has_error)
            return semantic_lookup_error(status.error);
        if (c.at("mode") == "sqlite-missing")
            throw RunnerError("missing SQLite fixture unexpectedly exists");
        if (request.contains("pairs")) {
            database::FormIdValueLookupBatchInputDto input{};
            for (const auto& pair : request.at("pairs"))
                input.pairs.push_back(database::FormIdValueLookupKeyDto{pair.at("formid").get<std::string>(),
                                                                        pair.at("plugin").get<std::string>()});
            const auto result = database::formid_value_lookup_lookup_batch(*lookup, std::move(input));
            if (result.has_outcomes == result.has_error)
                throw RunnerError("invalid lookup batch presence flags");
            if (result.has_error)
                return semantic_lookup_error(result.error);
            if (result.outcomes.size() != request.at("pairs").size())
                throw RunnerError("lookup batch length changed");
            json outcomes = json::array();
            for (std::size_t i = 0; i < result.outcomes.size(); ++i)
                outcomes.push_back(semantic_lookup_outcome(result.outcomes[i], request.at("pairs").at(i)));
            return json{{"analyzerKind", nullptr}, {"result", json{{"outcomes", outcomes}}}, {"error", nullptr}};
        }
        const auto run = [&](const json& r) {
            return database::formid_value_lookup_lookup(*lookup, r.at("formid").get<std::string>(),
                                                        r.at("plugin").get<std::string>());
        };
        if (fixture.contains("warmupRequest")) {
            const auto warmup = run(fixture.at("warmupRequest"));
            if (!warmup.has_outcome || warmup.has_error)
                throw RunnerError("lookup warmup failed");
        }
        const auto result = run(request);
        if (result.has_outcome == result.has_error)
            throw RunnerError("invalid lookup presence flags");
        if (result.has_error)
            return semantic_lookup_error(result.error);
        return json{{"analyzerKind", nullptr},
                    {"result", semantic_lookup_outcome(result.outcome, request)},
                    {"error", nullptr}};
    }
    throw RunnerError("unsupported semantic family");
}

/// Resolves an explicitly declared input fixture without reading scenario expectations.
json execute_semantic_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end())
        throw RunnerError("undeclared semantic fixture");
    std::ifstream stream(fs::path(plan.at("fixtures").at(reference).get<std::string>()), std::ios::binary);
    if (!stream)
        throw RunnerError("cannot read semantic fixture");
    return execute_semantic_fixture(plan.at("familyId").get<std::string>(), json::parse(stream));
}

/// Identifies the repository-owned semantic family contract still run through this header.
bool is_semantic_family(const json& family) {
    return family == "formid-lookup";
}
