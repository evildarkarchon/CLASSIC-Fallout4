// SPDX-License-Identifier: MIT
/// Verify native timestamp paths are owned and within the call's time interval before normalization.
json execute_path_backups_scenario(const json& plan, const json& scenario) {
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    std::ifstream input(
        plan.at("fixtures").at(scenario.at("input").at("fixtureRef").get<std::string>()).get<std::string>());
    const auto fixture = json::parse(input);
    const auto source = root / "settings.ini";
    const auto hex = fixture.at("hex").get<std::string>();
    if (hex.size() % 2 || hex.find_first_not_of("0123456789abcdef") != std::string::npos)
        throw RunnerError("invalid backup hex");
    std::string bytes;
    for (std::size_t i = 0; i < hex.size(); i += 2)
        bytes.push_back(static_cast<char>(std::stoi(hex.substr(i, 2), nullptr, 16)));
    {
        std::ofstream output(source, std::ios::binary);
        output.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
    }
    const auto game = fixture.at("game").get<std::string>();
    const auto initial = classic::path::backup_list_existing(source.string(), game);
    const auto before =
        std::chrono::duration_cast<std::chrono::seconds>(std::chrono::system_clock::now().time_since_epoch()).count();
    const fs::path created(owned_string(classic::path::backup_create_timestamped(source.string(), game)));
    const auto after =
        std::chrono::duration_cast<std::chrono::seconds>(std::chrono::system_clock::now().time_since_epoch()).count();
    const auto listed = classic::path::backup_list_existing(source.string(), game);
    const auto stamp = created.parent_path().filename().string();
    if (stamp.empty() || stamp.find_first_not_of("0123456789") != std::string::npos)
        throw RunnerError("backup timestamp is not decimal");
    const auto seconds = std::stoll(stamp);
    if (seconds < before || seconds > after || created != root / "CLASSIC Backups" / game / stamp / "settings.ini" ||
        listed.size() != 1 || owned_string(listed[0]) != stamp || !initial.empty())
        throw RunnerError("timestamp backup escaped expected root or time interval");
    std::ifstream copied(created, std::ios::binary);
    const std::string copy((std::istreambuf_iterator<char>(copied)), {});
    std::ifstream original(source, std::ios::binary);
    const std::string original_bytes((std::istreambuf_iterator<char>(original)), {});
    if (copy != bytes || original_bytes != bytes)
        throw RunnerError("timestamp backup changed bytes");
    std::vector<std::string> files;
    for (const auto& entry : fs::recursive_directory_iterator(root))
        if (entry.is_regular_file()) {
            auto relative = fs::relative(entry.path(), root).generic_string();
            const auto position = relative.find(stamp);
            if (position != std::string::npos)
                relative.replace(position, stamp.size(), "<timestamp>");
            files.push_back(relative);
        }
    std::sort(files.begin(), files.end());
    return json{{"initial", json::array()},
                {"listed", {"<timestamp>"}},
                {"created", "CLASSIC Backups/Fallout4/<timestamp>/settings.ini"},
                {"sourceHex", fixture.at("hex")},
                {"copyHex", fixture.at("hex")},
                {"files", files}};
}
