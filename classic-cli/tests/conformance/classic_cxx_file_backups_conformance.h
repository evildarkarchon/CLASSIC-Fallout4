// SPDX-License-Identifier: MIT
/// Preserve every owned file after backup or restore handles have completed.
json managed_backup_files(const fs::path& root) {
    json files = json::object();
    for (const auto& entry : fs::recursive_directory_iterator(root))
        if (entry.is_regular_file()) {
            std::ifstream input(entry.path(), std::ios::binary);
            files[fs::relative(entry.path(), root).generic_string()] =
                std::string((std::istreambuf_iterator<char>(input)), {});
        }
    return files;
}

/// Exercise CXX manager constructors and public lifecycle operations on disposable files.
json execute_file_backups_scenario(const json& plan, const json& scenario) {
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    std::ifstream fixture_input(
        plan.at("fixtures").at(scenario.at("input").at("fixtureRef").get<std::string>()).get<std::string>());
    const auto fixture = json::parse(fixture_input);
    const auto kind = fixture.at("kind").get<std::string>();
    const auto game = kind == "game-files" ? root / "game" : root;
    fs::create_directories(game);
    const auto source = game / "f4se_fixture.dll";
    const auto write = [](const fs::path& path, const std::string& value) {
        std::ofstream output(path, std::ios::binary);
        output << value;
        if (!output)
            throw RunnerError("cannot write backup fixture");
    };
    const auto read = [](const fs::path& path) {
        std::ifstream input(path, std::ios::binary);
        if (!input)
            throw RunnerError("missing restored backup file");
        return std::string((std::istreambuf_iterator<char>(input)), {});
    };
    write(source, fixture.at("content").get<std::string>());
    write(game / "sentinel.txt", "keep\n");
    if (kind != "game-files") {
        auto manager = classic::files::backup_manager_new(game.string());
        const auto initial = classic::files::backup_manager_exists(*manager, "xse");
        const auto created = owned_string(classic::files::backup_manager_create(*manager, "xse"));
        const auto exists = classic::files::backup_manager_exists(*manager, "xse");
        const auto copy = read(game / "CLASSIC_Backups" / "XSE_Backup" / "f4se_fixture.dll");
        write(source, "changed\n");
        const auto restored = classic::files::backup_manager_restore(*manager, "xse");
        if (kind == "remove") {
            classic::files::backup_manager_remove(*manager, "xse");
            return json{{"exists", classic::files::backup_manager_exists(*manager, "xse")},
                        {"files", managed_backup_files(root)}};
        }
        return json{{"initial", initial},
                    {"exists", exists},
                    {"created", created},
                    {"restored", restored},
                    {"copy", copy},
                    {"source", read(source)},
                    {"files", managed_backup_files(root)}};
    }
    auto manager = classic::files::game_files_manager_new(game.string(), (root / "backups").string());
    rust::Vec<rust::String> patterns;
    patterns.push_back("f4se_");
    const auto slice = rust::Slice<const rust::String>(patterns.data(), patterns.size());
    const auto backup = owned_string(classic::files::game_files_backup(*manager, "fixture", slice));
    write(source, "changed\n");
    const auto restore = owned_string(classic::files::game_files_restore(*manager, "fixture", slice));
    const auto restored = read(source);
    const auto remove = owned_string(classic::files::game_files_remove(*manager, "fixture", slice));
    return json{{"backup", backup},
                {"restore", restore},
                {"remove", remove},
                {"restored", restored},
                {"files", managed_backup_files(root)}};
}
