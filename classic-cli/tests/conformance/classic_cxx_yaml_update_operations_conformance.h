// SPDX-License-Identifier: MIT

/// Own cache fallbacks, dotenv discovery and network egress for each synchronous update scenario.
class YamlUpdateEnvironment final {
public:
    /// Restore every overridden value after calls complete, including partial setup failure.
    YamlUpdateEnvironment(const fs::path& root, const std::string& service)
        : runtime_(root, "cache") {
        fs::create_directories(root / "bundled");
        std::ofstream dotenv(root / ".env", std::ios::binary);
        dotenv.close();
        if (!dotenv)
            throw RunnerError("cannot own YAML update dotenv discovery");
        for (const auto name : {"APPDATA", "HOME", "GITHUB_TOKEN", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
                                "http_proxy", "https_proxy", "all_proxy", "no_proxy"})
            previous_[name] = read_environment(name);
        try {
            set_environment("APPDATA", (root / "cache").string());
            set_environment("HOME", (root / "cache").string());
            set_environment("GITHUB_TOKEN", std::nullopt);
            // Generic manifests permit a local Pages URL, but release assets stay allowlisted to GitHub.
            // A non-forwarding proxy prevents a guard regression from contacting production endpoints.
            for (const auto name : {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"})
                set_environment(name, service);
            set_environment("NO_PROXY", "127.0.0.1,localhost");
            set_environment("no_proxy", "127.0.0.1,localhost");
        } catch (...) {
            restore();
            throw;
        }
    }
    /// Restore process state before the temporary directory owner removes its files.
    ~YamlUpdateEnvironment() { restore(); }
    YamlUpdateEnvironment(const YamlUpdateEnvironment&) = delete;
    YamlUpdateEnvironment& operator=(const YamlUpdateEnvironment&) = delete;

private:
    /// Cleanup must not mask the original conformance failure.
    void restore() noexcept {
        for (const auto& [name, value] : previous_) {
            try {
                set_environment(name.c_str(), value);
            } catch (...) { /* A teardown failure cannot replace the primary native result. */
            }
        }
    }
    RuntimeEnvironment runtime_;
    std::map<std::string, std::optional<std::string>> previous_;
};

/// Record exact final bytes; parse only manifest JSON to ignore irrelevant serialization ordering.
json yaml_update_files(const fs::path& root) {
    std::map<std::string, json> ordered;
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (entry.is_symlink())
            throw RunnerError("unexpected YAML update link");
        if (!entry.is_regular_file())
            continue;
        const auto bytes = read_optional_file(entry.path());
        if (!bytes)
            throw RunnerError("YAML update file disappeared during observation");
        const auto path = relative_path(root, entry.path());
        if (entry.path().filename() == "manifest-latest.json")
            ordered[path] = json{{"path", path}, {"json", json::parse(bytes->begin(), bytes->end())}};
        else
            ordered[path] = json{{"path", path}, {"hex", settings_bytes_hex(*bytes)}};
    }
    json result = json::array();
    for (const auto& [path, value] : ordered)
        result.push_back(value);
    return result;
}

/// Normalize only stable documented refusal prefixes; unexpected failures remain runner errors.
std::string yaml_update_error_kind(const std::string& message) {
    if (message.starts_with("update check disabled:"))
        return "disabled";
    if (message.starts_with("decision stale:"))
        return "stale_decision";
    if (message.starts_with("apply_yaml_update failed: Update error: approved decision malformed:"))
        return "malformed_approval";
    if (message.starts_with("manifest invalid:") &&
        message.find("not a valid plain cache-dir basename") != std::string::npos)
        return "invalid_name";
    if (message == "Update error: rollback refused: Local Ignore YAML Data is user-owned")
        return "local_ignore_refused";
    throw RunnerError("unexpected YAML update error: " + message);
}

/// Read the native status union and every public compatible-file metadata field.
json yaml_update_status(const std::string& api, const classic::update::YamlUpdateStatusDto& status) {
    if ((status.tag != 0 && status.tag != 1) || !status.error_message.empty())
        throw RunnerError("unexpected YAML update status: " + owned_string(status.error_message));
    if (status.incompatible_files.size() != status.incompatible_reasons.size())
        throw RunnerError("YAML rejection vectors differ in length");
    const auto file = [](const auto& item) {
        return json{{"name", owned_string(item.name)},
                    {"schemaVersion", owned_string(item.schema_version)},
                    {"sha256", owned_string(item.sha256)},
                    {"sizeBytes", item.size_bytes},
                    {"downloadUrl", owned_string(item.download_url)}};
    };
    json compatible = json::array(), incompatible = json::array(), reasons = json::array();
    for (const auto& item : status.compatible_files)
        compatible.push_back(file(item));
    for (const auto& item : status.incompatible_files)
        incompatible.push_back(file(item));
    for (const auto& reason : status.incompatible_reasons)
        reasons.push_back(owned_string(reason));
    return json{{"api", api},
                {"tag", status.tag},
                {"releaseTag", owned_string(status.release_tag)},
                {"publishedAt", owned_string(status.published_at)},
                {"compatible", compatible},
                {"incompatible", incompatible},
                {"incompatibleReasons", reasons},
                {"unknownReason", owned_string(status.unknown_reason)},
                {"error", nullptr}};
}

/// Empty reviewed selections and explicit refusals must not produce per-file install outcomes.
json yaml_update_report(const std::string& api, const classic::update::YamlUpdateReportDto& result) {
    if (!result.installed.empty() || !result.failed.empty())
        throw RunnerError("empty consent unexpectedly selected YAML payloads");
    return json{{"api", api},
                {"installed", json::array()},
                {"failed", json::array()},
                {"error", result.error_message.empty()
                              ? json(nullptr)
                              : json(yaml_update_error_kind(owned_string(result.error_message)))}};
}

/// Supply an explicit schema entry and reviewed decision, without deriving updater policy in C++.
classic::update::YamlApplyRequestDto yaml_update_request(const json& fixture, const std::string& pages,
                                                         const fs::path& root, bool enabled) {
    classic::update::YamlApplyRequestDto request{};
    request.pages_url = pages;
    request.tag_prefix = "yaml-data-v";
    request.enabled = enabled;
    request.bundled_yaml_dir = (root / "bundled").string();
    classic::update::YamlClientSchemaEntryDto entry{};
    entry.name = "CLASSIC Main.yaml";
    entry.accepted_major = 2;
    entry.accepted_minimum_minor = 0;
    entry.has_installed = false;
    request.entries.push_back(std::move(entry));
    if (fixture.contains("approved")) {
        request.approved.release_tag = fixture.at("approved").at("releaseTag").get<std::string>();
        for (const auto& name : fixture.at("approved").at("names"))
            request.approved.file_names.push_back(name.get<std::string>());
        for (const auto& digest : fixture.at("approved").at("digests"))
            request.approved.file_sha256.push_back(digest.get<std::string>());
    }
    return request;
}

/// Execute public YAML update operations against a non-forwarding service and owned cache files.
json execute_yaml_update_operations_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    if (scenario.at("fixtureRefs") != json::array({reference}))
        throw RunnerError("undeclared YAML update fixture");
    std::ifstream input(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(input);
    const auto service_value = read_environment("CLASSIC_CONFORMANCE_SERVICE");
    if (!service_value || !service_value->starts_with("http://127.0.0.1:"))
        throw RunnerError("YAML update service must be loopback");
    const auto port = service_value->substr(std::string("http://127.0.0.1:").size());
    if (port.empty() ||
        !std::all_of(port.begin(), port.end(), [](unsigned char ch) { return ch >= '0' && ch <= '9'; }) ||
        std::stoul(port) == 0 || std::stoul(port) > 65535)
        throw RunnerError("invalid loopback service port");
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    YamlUpdateEnvironment environment(root, *service_value);
    for (const auto& [name, content] : fixture.at("files").items()) {
        if (!name.starts_with("cache/"))
            throw RunnerError("YAML update fixture must stay in owned cache");
        const auto path = runtime_path(root, name, "YAML update fixture");
        fs::create_directories(path.parent_path());
        std::ofstream output(path, std::ios::binary);
        output << content.get<std::string>();
        output.close();
        if (!output)
            throw RunnerError("cannot write YAML update fixture");
    }
    const auto before = yaml_update_files(root);
    const auto operation = fixture.at("operation").get<std::string>();
    const auto request = yaml_update_request(
        fixture, *service_value + "/" + scenario.at("id").get<std::string>() + "/pages", root, operation != "disabled");
    json results = json::array();
    if (operation == "disabled") {
        results.push_back(yaml_update_status(
            "yaml_check_update", classic::update::yaml_check_update(request.pages_url, request.tag_prefix,
                                                                    request.entries, false, request.bundled_yaml_dir)));
        results.push_back(yaml_update_status("yaml_data_check_update", classic::update::yaml_data_check_update(false)));
        results.push_back(yaml_update_report("yaml_apply_update", classic::update::yaml_apply_update(request)));
        results.push_back(yaml_update_report("yaml_data_apply_update",
                                             classic::update::yaml_data_apply_update(false, request.approved)));
    } else if (operation == "controlled-consent") {
        results.push_back(yaml_update_status(
            "yaml_check_update", classic::update::yaml_check_update(request.pages_url, request.tag_prefix,
                                                                    request.entries, true, request.bundled_yaml_dir)));
        results.push_back(yaml_update_report("yaml_apply_update", classic::update::yaml_apply_update(request)));
    } else if (operation == "malformed-approval" || operation == "stale-decision") {
        results.push_back(yaml_update_report("yaml_apply_update", classic::update::yaml_apply_update(request)));
    } else if (operation == "rollback") {
        const auto result = classic::update::yaml_rollback_update(fixture.at("fileName").get<std::string>());
        results.push_back(json{{"api", "yaml_rollback_update"},
                               {"fileName", owned_string(result.file_name)},
                               {"rolledBack", result.rolled_back},
                               {"error", result.error_message.empty()
                                             ? json(nullptr)
                                             : json(yaml_update_error_kind(owned_string(result.error_message)))}});
    } else if (operation == "rollback-bulk") {
        const auto result = classic::update::yaml_data_rollback_update();
        if (result.failed_files.size() != result.failure_reasons.size())
            throw RunnerError("bulk rollback failure vectors differ");
        json rolled = json::array(), absent = json::array(), failed = json::array(), reasons = json::array();
        for (const auto& name : result.rolled_back)
            rolled.push_back(owned_string(name));
        for (const auto& name : result.no_previous_version)
            absent.push_back(owned_string(name));
        for (const auto& name : result.failed_files)
            failed.push_back(owned_string(name));
        for (const auto& reason : result.failure_reasons)
            reasons.push_back(yaml_update_error_kind(owned_string(reason)));
        results.push_back(json{{"api", "yaml_data_rollback_update"},
                               {"rolledBack", rolled},
                               {"noPrevious", absent},
                               {"failedFiles", failed},
                               {"failureReasons", reasons}});
    } else
        throw RunnerError("unsupported YAML update operation");
    return json{{"results", results}, {"beforeFiles", before}, {"files", yaml_update_files(root)}};
}
