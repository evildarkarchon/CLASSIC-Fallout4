// SPDX-License-Identifier: MIT
// Observe real notification DTOs and exact durable cache bytes.

/// Convert the bridge's documented error display into a portable domain code.
std::string update_service_error(const std::string& message) {
    if (message.starts_with("notification fetch failed")) return "fetch_failed";
    if (message.starts_with("notification manifest decode failure:")) return "decode";
    if (message.starts_with("installed version `")) return "installed_version";
    if (message.starts_with("manifest_version ") && message.find(" not supported ") != std::string::npos) return "unsupported_version";
    throw RunnerError("unexpected notification error: " + message);
}

/// Execute configured native checks and traverse each returned DTO directly.
json execute_update_services_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    if (scenario.at("fixtureRefs") != json::array({reference})) throw RunnerError("undeclared update service fixture");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(), scenario.at("id").get<std::string>());
    const auto cache = temporary.path() / "cache";
    fs::create_directory(cache);
    const char* service = std::getenv("CLASSIC_CONFORMANCE_SERVICE");
    if (!service) throw RunnerError("CLASSIC_CONFORMANCE_SERVICE is required");
    std::string base(service);
    if (base.ends_with('/')) base.pop_back();
    base += "/" + scenario.at("id").get<std::string>();
    const auto config = json{{"github_api_base_url", base + "/api"}, {"notification_pages_url", base + "/pages"}, {"timeout_ms", fixture.at("timeoutMs")}}.dump();
    json results = json::array();
    for (int check = 0; check < fixture.at("checks").get<int>(); ++check) {
        const auto status = classic::update::check_app_notification_configured("conformance", "updates", fixture.at("installedVersion").get<std::string>(), config, cache.string());
        if (owned_string(status.classification) == "error") {
            results.push_back(json{{"status", nullptr}, {"error", {{"code", update_service_error(owned_string(status.error_message))}}}});
            continue;
        }
        const auto nullable = [](const rust::String& value) -> json { return value.empty() ? json(nullptr) : json(owned_string(value)); };
        json display = nullptr;
        if (!status.display_title.empty() || !status.display_body.empty() || !status.display_cta_url.empty()) {
            display = json{{"title", owned_string(status.display_title)}, {"body", owned_string(status.display_body)}, {"ctaUrl", nullable(status.display_cta_url)}};
        }
        results.push_back(json{{"status", {{"classification", owned_string(status.classification)}, {"latestVersion", owned_string(status.latest_version)},
            {"publishedAt", owned_string(status.published_at)}, {"minSupportedVersion", nullable(status.min_supported_version)},
            {"display", display}, {"parseError", nullable(status.parse_error)}}}, {"error", nullptr}});
    }
    std::map<std::string, std::string> ordered;
    for (const auto& entry : fs::recursive_directory_iterator(cache)) {
        if (!entry.is_regular_file()) continue;
        std::ifstream input(entry.path(), std::ios::binary);
        const std::vector<std::uint8_t> bytes{std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
        if (!input || input.bad()) throw RunnerError("cannot read notification cache");
        ordered.emplace(relative_path(temporary.path(), entry.path()), autoscan_bytes_hex(bytes));
    }
    json files = json::array();
    for (const auto& [path, hex] : ordered) files.push_back(json{{"path", path}, {"hex", hex}});
    return json{{"results", results}, {"files", files}};
}
