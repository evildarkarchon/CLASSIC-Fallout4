// Actual bridge-owned UI operations with independent golden content and file effects.

/// Preserve exact bytes in a portable snapshot without newline or encoding normalization.
std::string interface_bytes_hex(const std::vector<unsigned char>& bytes) {
    std::ostringstream output;
    output << std::hex << std::setfill('0');
    for (const auto byte : bytes) output << std::setw(2) << static_cast<unsigned>(byte);
    return output.str();
}

/// Snapshot every actual file/directory so unrequested writes are visible to the comparator.
json interface_snapshot(const fs::path& root) {
    std::map<std::string, json> files;
    std::set<std::string> directories;
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (entry.is_symlink()) throw RunnerError("unexpected interface fixture symlink");
        const auto relative = relative_path(root, entry.path());
        if (entry.is_directory()) { directories.insert(relative); continue; }
        std::ifstream input(entry.path(), std::ios::binary);
        const std::vector<unsigned char> bytes{std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
        if (!input || input.bad()) throw RunnerError("cannot snapshot interface fixture");
        files.emplace(relative, json{{"path", relative}, {"hex", interface_bytes_hex(bytes)}});
    }
    auto values = json::array();
    for (const auto& [path, item] : files) values.push_back(item);
    return json{{"files", values}, {"directories", directories}};
}

/// Call public CXX rendering/discovery functions without inventing a Rust core counterpart.
json execute_interface_helpers_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const auto fixture = json::parse(stream);
    if (plan.at("familyId") == "markdown-rendering") {
        const auto input = fixture.at("markdown").get<std::string>();
        const std::string normalized(classic::markdown::normalize_markdown(input));
        const std::string document(classic::markdown::markdown_to_html(input));
        const std::string marker = "</style></head><body>";
        const auto opening = document.find(marker);
        if (opening == std::string::npos || !document.ends_with("</body></html>")) throw RunnerError("incomplete rendered document");
        const auto body_start = opening + marker.size();
        const auto body = document.substr(body_start, document.size() - body_start - std::string("</body></html>").size());
        return json{{"normalized", normalized}, {"htmlBody", body}, {"documentComplete", document.starts_with("<html><head><style>")}};
    }
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(), scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    for (const auto& directory : fixture.at("directories")) fs::create_directories(root / directory.get<std::string>());
    // One shared clock offset preserves exact relative ordering across file-clock epochs.
    const auto system_anchor = std::chrono::system_clock::now();
    const auto file_anchor = fs::file_time_type::clock::now();
    for (const auto& item : fixture.at("files")) {
        const auto path = root / item.at("path").get<std::string>();
        fs::create_directories(path.parent_path());
        { std::ofstream output(path, std::ios::binary); output << item.at("content").get<std::string>(); if (!output) throw RunnerError("cannot write interface fixture"); }
        const auto time = std::chrono::sys_seconds(std::chrono::seconds(item.at("modifiedSeconds").get<std::int64_t>()));
        fs::last_write_time(path, file_anchor + std::chrono::duration_cast<fs::file_time_type::duration>(time - system_anchor));
    }
    const auto target = fixture.at("missing").get<bool>() ? root / "missing" : root;
    auto reports = json::array();
    for (const auto& report : classic::files::discover_report_files(target.generic_string()))
        reports.push_back(relative_path(root, fs::path(std::string(report))));
    auto snapshot = interface_snapshot(root);
    snapshot["reports"] = reports;
    return snapshot;
}
