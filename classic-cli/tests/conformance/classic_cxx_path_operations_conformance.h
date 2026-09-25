// Input-only path validation transport, included inside the runner namespace.

/// Rejects any authored path that escapes the disposable fixture workspace.
fs::path path_operation_owned(const fs::path& root, const std::string& relative) {
    const fs::path path(relative);
    if (relative.empty() || path.is_absolute() || relative.find('\\') != std::string::npos ||
        relative.find(':') != std::string::npos)
        throw RunnerError("fixture path must be a contained relative path");
    for (const auto& component : path) {
        if (component == ".." || component == "." || component.empty())
            throw RunnerError("fixture path must be a contained relative path");
    }
    return root / path;
}

/// Preserves actual domain prose while removing only the owned root and native separators.
std::string path_operation_portable(std::string value, const fs::path& root) {
    const auto prefix = root.string() + static_cast<char>(fs::path::preferred_separator);
    for (auto offset = value.find(prefix); offset != std::string::npos; offset = value.find(prefix))
        value.erase(offset, prefix.size());
    std::replace(value.begin(), value.end(), '\\', '/');
    return value;
}

/// Exercises the generated CXX path bridge using fixture bytes and declared requests only.
json execute_path_operations_scenario(const json& plan, const json& scenario) {
    const std::string reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end())
        throw RunnerError("path fixture is not declared by the scenario");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    for (const auto& relative : fixture.at("directories"))
        fs::create_directories(path_operation_owned(root, relative.get<std::string>()));
    for (const auto& [relative, content] : fixture.at("files").items()) {
        const auto path = path_operation_owned(root, relative);
        fs::create_directories(path.parent_path());
        std::ofstream output(path, std::ios::binary);
        output.exceptions(std::ios::badbit | std::ios::failbit);
        output << content.get<std::string>();
    }
    const auto& request = fixture.at("request");
    const auto relative = request.at("path").get<std::string>();
    const auto path = path_operation_owned(root, relative).string();
    const bool exists = classic::path::is_valid_path(path);
    // Compatibility aliases in both namespaces are separate public obligations;
    // observe each so neither can diverge while borrowing the primary result.
    if (classic::path::validate_path(path) != exists ||
        classic::game::validate_path(path) != exists)
        throw RunnerError("path compatibility alias disagrees with is_valid_path");
    json error = nullptr;
    const auto required = semantic_strings(request.at("requiredFiles"));
    try {
        classic::path::path_validate_required_files(
            path, rust::Slice<const rust::String>(required.data(), required.size()));
    } catch (const rust::Error& failure) {
        // Only the generated bridge's domain-error carrier becomes conformance evidence.
        error = path_operation_portable(failure.what(), root);
    }
    return json{
        {"path", relative}, {"exists", exists}, {"requiredFiles", {{"accepted", error.is_null()}, {"error", error}}}};
}
