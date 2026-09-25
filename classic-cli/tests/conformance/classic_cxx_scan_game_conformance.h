// SPDX-License-Identifier: MIT
// Controlled Scan Game observations through the public CXX bridge.

/// Records directory artifacts that would be invisible in a file-only snapshot.
json scan_game_directories(const fs::path& root) {
    std::set<std::string> ordered;
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (entry.is_directory()) ordered.insert(entry.path().lexically_relative(root).generic_string());
    }
    return json(ordered);
}

/// Normalizes only the owned root and platform separators in native path-bearing text.
std::string scan_game_text(std::string value, const fs::path& root) {
    const std::string prefix = root.string();
    std::size_t offset = 0;
    while ((offset = value.find(prefix, offset)) != std::string::npos) {
        value.replace(offset, prefix.size(), "<ROOT>");
        offset += 6;
    }
    std::replace(value.begin(), value.end(), '\\', '/');
    return value;
}

/// Transports every known native INI severity, rejecting future unmapped variants.
std::string scan_game_severity(classic::scangame::IssueSeverity value) {
    switch (value) {
    case classic::scangame::IssueSeverity::Error: return "Error";
    case classic::scangame::IssueSeverity::Warning: return "Warning";
    case classic::scangame::IssueSeverity::Info: return "Info";
    default: throw RunnerError("unknown Scan Game issue severity");
    }
}

/// Executes input-only INI/ENB fixtures in a fresh game root and re-reads durable effects.
json execute_scan_game(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end()) throw RunnerError("scan game fixture is not declared");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    const auto operation = fixture.at("operation").get<std::string>();
    const auto game = fixture.at("game").get<std::string>();
    if (operation != "validate-ini" && operation != "validate-enb") throw RunnerError("unsupported scan game operation");
    if (scenario.at("action") != "scan-game." + operation) throw RunnerError("scan game action does not match its fixture");
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(), scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    for (const auto& relative : fixture.at("directories")) fs::create_directories(file_operation_path(root, relative.get<std::string>()));
    for (const auto& [relative, content] : fixture.at("files").items()) {
        const auto target = file_operation_path(root, relative);
        fs::create_directories(target.parent_path());
        std::ofstream output(target, std::ios::binary | std::ios::trunc);
        const auto bytes = content.get<std::string>();
        output.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
        output.close();
        if (!output) throw RunnerError("cannot materialize Scan Game fixture");
    }
    json observation{{"operation", operation}, {"game", game}, {"beforeFiles", file_operation_files(root)}, {"beforeDirectories", scan_game_directories(root)}};
    if (operation == "validate-ini") {
        const auto report = classic::scangame::ini_validator_validate_inis(game, root.string());
        const auto values = classic::scangame::ini_validator_detect_all_issues_for_root(game, root.string());
        json issues = json::array();
        for (const auto& issue : values) {
            issues.push_back(json{{"filePath", fs::path(owned_string(issue.file_path)).lexically_relative(root).generic_string()},
                {"section", owned_string(issue.section)}, {"setting", owned_string(issue.setting)},
                {"currentValue", owned_string(issue.current_value)}, {"recommendedValue", owned_string(issue.recommended_value)},
                {"description", owned_string(issue.description)}, {"severity", scan_game_severity(issue.severity)}});
        }
        observation["result"] = json{{"report", scan_game_text(owned_string(report), root)}, {"issues", issues}};
    } else {
        const auto result = classic::scangame::enb_checker_validate(root.string());
        std::string binaries;
        switch (result.binaries) {
        case classic::scangame::EnbResult::Present: binaries = "Present"; break;
        case classic::scangame::EnbResult::Partial: binaries = "Partial"; break;
        case classic::scangame::EnbResult::NotInstalled: binaries = "NotInstalled"; break;
        default: throw RunnerError("unknown ENB binaries result");
        }
        std::string config;
        switch (result.config) {
        case classic::scangame::EnbConfigResult::Valid: config = "Valid"; break;
        case classic::scangame::EnbConfigResult::NotFound: config = "NotFound"; break;
        case classic::scangame::EnbConfigResult::Unreadable: config = "Unreadable"; break;
        default: throw RunnerError("unknown ENB config result");
        }
        observation["result"] = json{{"binaries", binaries}, {"config", config}};
    }
    observation["files"] = file_operation_files(root);
    observation["directories"] = scan_game_directories(root);
    return observation;
}
