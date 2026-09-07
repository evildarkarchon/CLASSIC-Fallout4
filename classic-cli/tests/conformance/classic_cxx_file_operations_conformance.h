// SPDX-License-Identifier: MIT
// Actual text I/O observations through the generated Rust file bridge.

/// Rejects nonportable fixture paths before invoking native file operations.
fs::path file_operation_path(const fs::path& root, const std::string& path) {
    if (path.empty() || path.find(':') != std::string::npos || path.find('\\') != std::string::npos ||
        path.front() == '/' || path.back() == '/' || path.find("//") != std::string::npos) {
        throw RunnerError("file operation needs a contained relative path");
    }
    for (const auto& part : fs::path(path)) {
        if (part == "." || part == "..") {
            throw RunnerError("file operation needs a contained relative path");
        }
    }
    return root / path;
}

/// Reads exact durable UTF-8 text and includes unexpected native file writes.
json file_operation_files(const fs::path& root) {
    std::map<std::string, std::string> ordered;
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (entry.is_regular_file()) {
            std::ifstream input(entry.path(), std::ios::binary);
            if (!input) {
                throw RunnerError("cannot read durable file operation result");
            }
            const std::string content{std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
            if (input.bad()) {
                throw RunnerError("cannot finish reading durable file operation result");
            }
            ordered.emplace(entry.path().lexically_relative(root).generic_string(), content);
        } else if (!entry.is_directory()) {
            throw RunnerError("unexpected non-file durable artifact");
        }
    }
    json result = json::array();
    for (const auto& [path, content] : ordered) {
        result.push_back(json{{"path", path}, {"content", content}});
    }
    return result;
}

/// Executes a single input-only fixture in a fresh invocation-owned directory.
json execute_file_operations(const json& plan, const json& scenario) {
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const fs::path& root = temporary.path();
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end()) {
        throw RunnerError("file operation fixture is not declared by the scenario");
    }
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    const std::string operation = fixture.at("operation").get<std::string>();
    if (operation != "read-text" && operation != "write-text") {
        throw RunnerError("unsupported file operation");
    }
    if (scenario.at("action") != "file-operations." + operation) {
        throw RunnerError("file operation action does not match its fixture");
    }
    const auto path = fixture.at("path").get<std::string>();
    const auto target = file_operation_path(root, path);
    for (const auto& [relative, content] : fixture.at("files").items()) {
        const auto destination = file_operation_path(root, relative);
        fs::create_directories(destination.parent_path());
        std::ofstream output(destination, std::ios::binary | std::ios::trunc);
        const auto bytes = content.get<std::string>();
        output.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
        output.close();
        if (!output) {
            throw RunnerError("cannot materialize file operation fixture");
        }
    }
    json result{{"operation", operation}, {"path", path}, {"content", nullptr}, {"error", nullptr},
                {"beforeFiles", file_operation_files(root)}, {"files", json::array()}};
    try {
        if (operation == "read-text") {
            result["content"] = owned_string(classic::files::read_file_with_encoding(target.string()));
        } else {
            classic::files::write_file_string(target.string(), fixture.at("content").get<std::string>());
        }
    } catch (const rust::Error& error) {
        // The bridge retains the Rust error category before platform-specific prose.
        if (!std::string_view(error.what()).starts_with("I/O error: ")) {
            throw;
        }
        result["error"] = "io_error";
    }
    if (operation == "read-text") {
        json alias{{"content", nullptr}, {"error", nullptr}};
        try {
            alias["content"] = owned_string(classic::files::read_report_file(target.string()));
        } catch (const rust::Error& error) {
            // Both public read entry points must preserve the same native I/O category.
            if (!std::string_view(error.what()).starts_with("I/O error: ")) {
                throw;
            }
            alias["error"] = "io_error";
        }
        if (alias.at("content") != result.at("content") || alias.at("error") != result.at("error")) {
            throw RunnerError("public read_report_file result differs from read_file_with_encoding");
        }
    }
    result["files"] = file_operation_files(root);
    return result;
}
